"""
Driver Insight Agent - Main Entry Point
Initializes and runs the Driver Insight Agent.
"""
import asyncio
import json
import sys
from typing import Dict, Any
from agent.core import DriverInsightAgent
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


class DriverInsightAgentApp:
    """Main application class for Driver Insight Agent."""
    
    def __init__(self):
        """Initialize the application."""
        self.agent = DriverInsightAgent()
        logger.info("driver_insight_agent_initialized")
    
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single request.
        
        Args:
            request_data: Request dictionary from Planner Agent
            
        Returns:
            Response dictionary
        """
        logger.info("processing_request", request_id=request_data.get('request_id'))
        
        response = await self.agent.process_request(request_data)
        
        logger.info(
            "request_completed",
            request_id=response.get('request_id'),
            success=response.get('success'),
            execution_time_ms=response.get('execution_time_ms')
        )
        
        return response
    
    def print_capabilities(self) -> None:
        """Print agent capabilities."""
        self.agent.abstract_card.print_card()
    
    def print_stats(self) -> None:
        """Print agent statistics."""
        stats = self.agent.get_stats()
        print("\n" + "=" * 80)
        print("Agent Statistics")
        print("=" * 80)
        print(json.dumps(stats, indent=2))
        print("=" * 80)
    
    async def run_example(self) -> None:
        """Run example requests to demonstrate functionality."""
        print("\n" + "=" * 80)
        print("Running Example Requests")
        print("=" * 80 + "\n")
        
        examples = [
            {
                "name": "Score Rankings",
                "request": {
                    "request_id": "example_001",
                    "report_type": "ranking",
                    "driver_ids": ["D001", "D002", "D003"],
                    "start_date": "2024-01-01T00:00:00Z",
                    "end_date": "2024-03-31T23:59:59Z"
                }
            },
            {
                "name": "Trip Summary",
                "request": {
                    "request_id": "example_002",
                    "report_type": "trip_only",
                    "driver_ids": ["D001"],
                    "start_date": "2024-01-01T00:00:00Z",
                    "end_date": "2024-03-31T23:59:59Z",
                    "limit": 10
                }
            },
            {
                "name": "Driver Comparison",
                "request": {
                    "request_id": "example_003",
                    "report_type": "comparison",
                    "driver_ids": ["D001", "D002"],
                    "start_date": "2024-01-01T00:00:00Z",
                    "end_date": "2024-03-31T23:59:59Z"
                }
            }
        ]
        
        for example in examples:
            print(f"\n--- Example: {example['name']} ---")
            print(f"Request: {json.dumps(example['request'], indent=2)}\n")
            
            response = await self.process_request(example['request'])
            
            print(f"Success: {response['success']}")
            print(f"Execution Time: {response['execution_time_ms']:.2f}ms")
            print(f"Tools Executed: {', '.join(response['tools_executed'])}")
            
            if response['summary']:
                print(f"\nSummary:\n{response['summary']}")
            
            if response['error']:
                print(f"Error: {response['error']}")
            
            print("\n" + "-" * 80)


async def main():
    """Main entry point."""
    print("\n" + "=" * 80)
    print("Driver Insight Agent")
    print("=" * 80)
    
    # Initialize application
    app = DriverInsightAgentApp()
    
    # Print capabilities
    app.print_capabilities()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "capabilities":
            # Already printed above
            pass
        
        elif command == "example":
            # Run example requests
            await app.run_example()
            app.print_stats()
        
        elif command == "request":
            # Process request from JSON file or stdin
            if len(sys.argv) > 2:
                # Read from file
                with open(sys.argv[2], 'r') as f:
                    request_data = json.load(f)
            else:
                # Read from stdin
                request_data = json.load(sys.stdin)
            
            response = await app.process_request(request_data)
            print(json.dumps(response, indent=2))
        
        elif command == "stats":
            app.print_stats()
        
        else:
            print(f"\nUnknown command: {command}")
            print("\nAvailable commands:")
            print("  capabilities  - Show agent capabilities")
            print("  example       - Run example requests")
            print("  request [file]- Process a request from file or stdin")
            print("  stats         - Show agent statistics")
    
    else:
        print("\nUsage: python app.py <command> [args]")
        print("\nCommands:")
        print("  capabilities  - Show agent capabilities")
        print("  example       - Run example requests")
        print("  request [file]- Process a request from file or stdin")
        print("  stats         - Show agent statistics")
        print("\nExample:")
        print("  python app.py example")
        print("  python app.py request request.json")
        print("  echo '{...}' | python app.py request")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error("application_error", error=str(e))
        sys.exit(1)
