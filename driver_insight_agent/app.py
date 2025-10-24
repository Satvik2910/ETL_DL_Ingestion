"""Main application entry point for the Driver Insight Agent."""

import asyncio
import sys
import json
import argparse
from typing import Dict, Any, Optional
from datetime import datetime
import structlog

from agent.core import DriverInsightAgentCore
from config.config import get_config, initialize_cache_manager
from cache.cache_manager import get_cache_manager


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class DriverInsightAgentApp:
    """Main application class for the Driver Insight Agent."""
    
    def __init__(self):
        """Initialize the application."""
        self.config = get_config()
        self.agent_core: Optional[DriverInsightAgentCore] = None
        self.cache_manager = None
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        log_level = self.config.logging.level
        
        # Configure Python logging
        import logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format='%(message)s'
        )
    
    async def initialize(self) -> None:
        """Initialize the agent and all components."""
        try:
            logger.info("Initializing Driver Insight Agent...")
            
            # Initialize cache manager
            cache_config = {
                'memory_cache_size': 1000,
                'persistent_cache_size_mb': self.config.cache.max_cache_size // 1024,
                'default_ttl': self.config.cache.ttl_seconds,
                'cache_dir': './cache_data'
            }
            self.cache_manager = initialize_cache_manager(cache_config)
            
            # Initialize agent core
            self.agent_core = DriverInsightAgentCore()
            
            # Perform health check
            health_status = await self.agent_core.get_agent_status()
            
            if health_status['system_status']['status'] != 'healthy':
                logger.warning("Agent initialized with degraded status", status=health_status)
            else:
                logger.info("Agent initialized successfully", 
                          tools_count=health_status['tool_registry']['registered_tools'])
            
        except Exception as e:
            logger.error("Failed to initialize agent", error=str(e))
            raise
    
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single request."""
        if not self.agent_core:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
        
        try:
            # Add request timestamp if not present
            if 'request_id' not in request_data:
                request_data['request_id'] = f"req_{int(datetime.now().timestamp())}"
            
            logger.info("Processing request", request_id=request_data['request_id'])
            
            # Process the request
            result = await self.agent_core.process_request(request_data)
            
            # Log result summary
            if result.get('success'):
                logger.info("Request processed successfully", 
                          request_id=request_data['request_id'],
                          execution_time_ms=result.get('execution_info', {}).get('execution_time_ms', 0))
            else:
                logger.error("Request processing failed", 
                           request_id=request_data['request_id'],
                           error=result.get('error', 'Unknown error'))
            
            return result
            
        except Exception as e:
            logger.error("Unexpected error processing request", 
                        request_id=request_data.get('request_id', 'unknown'),
                        error=str(e))
            return {
                "success": False,
                "request_id": request_data.get('request_id', 'unknown'),
                "error": f"Unexpected error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_status(self) -> Dict[str, Any]:
        """Get agent status information."""
        if not self.agent_core:
            return {
                "status": "not_initialized",
                "message": "Agent not initialized",
                "timestamp": datetime.now().isoformat()
            }
        
        return await self.agent_core.get_agent_status()
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities information."""
        if not self.agent_core:
            return {
                "error": "Agent not initialized",
                "timestamp": datetime.now().isoformat()
            }
        
        return await self.agent_core.get_capabilities()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            if not self.agent_core:
                return {
                    "status": "unhealthy",
                    "message": "Agent not initialized",
                    "timestamp": datetime.now().isoformat()
                }
            
            status = await self.agent_core.get_agent_status()
            
            return {
                "status": status['system_status']['status'],
                "details": {
                    "tools_healthy": status['tool_health']['healthy_tools'],
                    "tools_total": status['tool_health']['total_tools'],
                    "cache_status": "healthy" if self.cache_manager else "unavailable",
                    "execution_stats": status['execution_stats']
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def shutdown(self) -> None:
        """Shutdown the agent gracefully."""
        logger.info("Shutting down Driver Insight Agent...")
        
        try:
            # Clear any pending cache operations
            if self.cache_manager:
                # Perform any cleanup if needed
                pass
            
            logger.info("Agent shutdown completed")
            
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))


# CLI Interface Functions

async def run_interactive_mode(app: DriverInsightAgentApp) -> None:
    """Run the agent in interactive mode."""
    print("Driver Insight Agent - Interactive Mode")
    print("Type 'help' for available commands, 'quit' to exit")
    print("-" * 50)
    
    while True:
        try:
            user_input = input("\n> ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            elif user_input.lower() == 'help':
                print_help()
            elif user_input.lower() == 'status':
                status = await app.get_status()
                print(json.dumps(status, indent=2))
            elif user_input.lower() == 'capabilities':
                capabilities = await app.get_capabilities()
                print(json.dumps(capabilities, indent=2))
            elif user_input.lower() == 'health':
                health = await app.health_check()
                print(json.dumps(health, indent=2))
            elif user_input.startswith('{'):
                # Try to parse as JSON request
                try:
                    request_data = json.loads(user_input)
                    result = await app.process_request(request_data)
                    print(json.dumps(result, indent=2))
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON: {e}")
                except Exception as e:
                    print(f"Error processing request: {e}")
            elif user_input:
                print("Invalid command. Type 'help' for available commands.")
                
        except KeyboardInterrupt:
            break
        except EOFError:
            break
    
    print("\nGoodbye!")


def print_help() -> None:
    """Print help information."""
    help_text = """
Available commands:
  help         - Show this help message
  status       - Show agent status
  capabilities - Show agent capabilities
  health       - Perform health check
  quit/exit/q  - Exit the application

To process a request, enter a JSON object with the following structure:
{
  "request_id": "optional_request_id",
  "drivers": [
    {"driver_id": "DRV001"} or {"name": "John Doe"} or {"email": "john@example.com"}
  ],
  "report_type": "score|trip|combined|trend|comparison|ranking",
  "time_range": {
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-01-31T23:59:59Z"
  },
  "filters": [...],
  "aggregations": [...]
}

Example requests:
1. Score analysis:
{
  "drivers": [{"driver_id": "DRV001"}],
  "report_type": "score",
  "time_range": {"start_date": "2024-01-01", "end_date": "2024-01-31"}
}

2. Trip comparison:
{
  "drivers": [{"driver_id": "DRV001"}, {"driver_id": "DRV002"}],
  "report_type": "comparison"
}

3. Rankings:
{
  "report_type": "ranking",
  "time_range": {"start_date": "2024-01-01", "end_date": "2024-01-31"}
}
"""
    print(help_text)


async def process_file_requests(app: DriverInsightAgentApp, file_path: str) -> None:
    """Process requests from a file."""
    try:
        with open(file_path, 'r') as f:
            requests_data = json.load(f)
        
        if isinstance(requests_data, dict):
            # Single request
            requests_data = [requests_data]
        
        for i, request_data in enumerate(requests_data):
            print(f"\nProcessing request {i+1}/{len(requests_data)}...")
            result = await app.process_request(request_data)
            
            # Save result to file
            output_file = f"result_{i+1}_{request_data.get('request_id', 'unknown')}.json"
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"Result saved to: {output_file}")
            
            if result.get('success'):
                print(f"✓ Request processed successfully")
            else:
                print(f"✗ Request failed: {result.get('error', 'Unknown error')}")
    
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file '{file_path}': {e}")
    except Exception as e:
        print(f"Error processing file '{file_path}': {e}")


async def main() -> None:
    """Main application entry point."""
    parser = argparse.ArgumentParser(description="Driver Insight Agent")
    parser.add_argument('--mode', choices=['interactive', 'file', 'single'], 
                       default='interactive', help='Execution mode')
    parser.add_argument('--file', help='JSON file containing requests (for file mode)')
    parser.add_argument('--request', help='JSON request string (for single mode)')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Initialize application
    app = DriverInsightAgentApp()
    
    try:
        # Initialize the agent
        await app.initialize()
        
        # Run based on mode
        if args.mode == 'interactive':
            await run_interactive_mode(app)
        
        elif args.mode == 'file':
            if not args.file:
                print("Error: --file argument required for file mode")
                sys.exit(1)
            await process_file_requests(app, args.file)
        
        elif args.mode == 'single':
            if not args.request:
                print("Error: --request argument required for single mode")
                sys.exit(1)
            
            try:
                request_data = json.loads(args.request)
                result = await app.process_request(request_data)
                print(json.dumps(result, indent=2))
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON request: {e}")
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        logger.error("Application error", error=str(e))
        print(f"Error: {e}")
        sys.exit(1)
    
    finally:
        # Shutdown gracefully
        await app.shutdown()


if __name__ == "__main__":
    # Run the application
    asyncio.run(main())