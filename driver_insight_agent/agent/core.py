"""Core orchestration logic for the Driver Insight Agent."""

import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import structlog

from .abstract_card import DriverInsightAgentCard
from .mcp_registry import get_mcp_registry, ToolInvocationResult
from ..utils.validation import RequestValidator, ValidationError
from ..utils.summarizer import DataSummarizer, SummaryConfig
from ..utils.pagination import PaginationEngine, PaginationConfig
from ..cache.cache_manager import get_cache_manager
from ..config.config import get_config


logger = structlog.get_logger(__name__)


class ExecutionContext:
    """Context for request execution."""
    
    def __init__(self, request_id: str, request_data: Dict[str, Any]):
        """Initialize execution context."""
        self.request_id = request_id
        self.request_data = request_data
        self.start_time = time.time()
        self.tool_results: Dict[str, Any] = {}
        self.intermediate_data: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.metadata: Dict[str, Any] = {}
    
    def add_tool_result(self, tool_name: str, method_name: str, result: Any) -> None:
        """Add tool result to context."""
        key = f"{tool_name}.{method_name}"
        self.tool_results[key] = result
    
    def get_tool_result(self, tool_name: str, method_name: str) -> Optional[Any]:
        """Get tool result from context."""
        key = f"{tool_name}.{method_name}"
        return self.tool_results.get(key)
    
    def add_error(self, error: str) -> None:
        """Add error to context."""
        self.errors.append(error)
        logger.error(f"Request {self.request_id}: {error}")
    
    def add_warning(self, warning: str) -> None:
        """Add warning to context."""
        self.warnings.append(warning)
        logger.warning(f"Request {self.request_id}: {warning}")
    
    def get_execution_time_ms(self) -> float:
        """Get execution time in milliseconds."""
        return (time.time() - self.start_time) * 1000


class DriverInsightAgentCore:
    """Core orchestration engine for the Driver Insight Agent."""
    
    def __init__(self):
        """Initialize the agent core."""
        self.agent_card = DriverInsightAgentCard()
        self.mcp_registry = get_mcp_registry()
        self.cache_manager = get_cache_manager()
        self.summarizer = DataSummarizer()
        self.pagination_engine = PaginationEngine()
        self.validator = RequestValidator()
        self.config = get_config()
        
        # Execution statistics
        self.execution_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_execution_time_ms': 0,
            'cache_hit_rate': 0
        }
    
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a driver insight request."""
        request_id = request_data.get('request_id', f"req_{int(time.time())}")
        context = ExecutionContext(request_id, request_data)
        
        try:
            logger.info(f"Processing request {request_id}")
            
            # Update stats
            self.execution_stats['total_requests'] += 1
            
            # Step 1: Validate request
            validation_result = await self._validate_request(request_data, context)
            if not validation_result['valid']:
                return self._create_error_response(context, "Request validation failed", validation_result['errors'])
            
            # Step 2: Check cache
            cache_result = await self._check_cache(request_data, context)
            if cache_result:
                logger.info(f"Cache hit for request {request_id}")
                return cache_result
            
            # Step 3: Select and orchestrate tools
            orchestration_result = await self._orchestrate_tools(request_data, context)
            if not orchestration_result['success']:
                return self._create_error_response(context, "Tool orchestration failed", orchestration_result['errors'])
            
            # Step 4: Post-process and summarize
            final_result = await self._post_process_results(orchestration_result['data'], context)
            
            # Step 5: Cache result
            await self._cache_result(request_data, final_result, context)
            
            # Step 6: Update statistics
            self._update_success_stats(context)
            
            logger.info(f"Successfully processed request {request_id} in {context.get_execution_time_ms():.2f}ms")
            
            return final_result
            
        except Exception as e:
            context.add_error(f"Unexpected error: {str(e)}")
            self.execution_stats['failed_requests'] += 1
            logger.error(f"Failed to process request {request_id}: {str(e)}")
            return self._create_error_response(context, "Internal processing error", [str(e)])
    
    async def _validate_request(self, request_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Validate incoming request."""
        try:
            # Basic validation using RequestValidator
            validated_request = self.validator.validate_request(request_data)
            
            # Agent-specific validation using abstract card
            compatibility_result = self.agent_card.validate_request_compatibility(
                validated_request.report_type, 
                request_data
            )
            
            if not compatibility_result['compatible']:
                return {
                    'valid': False,
                    'errors': compatibility_result['errors'],
                    'warnings': compatibility_result['warnings']
                }
            
            # Add warnings to context
            for warning in compatibility_result['warnings']:
                context.add_warning(warning)
            
            # Store complexity estimate
            context.metadata['complexity_estimate'] = compatibility_result['complexity_estimate']
            
            return {
                'valid': True,
                'validated_request': validated_request,
                'compatibility_result': compatibility_result
            }
            
        except ValidationError as e:
            return {
                'valid': False,
                'errors': [str(e)],
                'warnings': []
            }
        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': []
            }
    
    async def _check_cache(self, request_data: Dict[str, Any], context: ExecutionContext) -> Optional[Dict[str, Any]]:
        """Check if request result is cached."""
        try:
            cached_result = await self.cache_manager.get_cached_request_result(request_data)
            if cached_result:
                # Add cache metadata
                cached_result['metadata'] = cached_result.get('metadata', {})
                cached_result['metadata']['from_cache'] = True
                cached_result['metadata']['cache_hit'] = True
                return cached_result
            return None
        except Exception as e:
            context.add_warning(f"Cache check failed: {str(e)}")
            return None
    
    async def _orchestrate_tools(self, request_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Orchestrate tool selection and execution."""
        try:
            report_type = request_data.get('report_type', 'combined')
            
            # Get tool execution chain
            tool_chain = self.mcp_registry.get_tool_chain_for_request(report_type, request_data)
            
            if not tool_chain:
                return {
                    'success': False,
                    'errors': [f"No tool chain available for report type: {report_type}"],
                    'data': None
                }
            
            # Execute tool chain
            execution_results = await self._execute_tool_chain(tool_chain, request_data, context)
            
            # Check if any required tools failed
            required_failures = [
                result for result in execution_results 
                if not result.success and self._is_tool_required(result.tool_name, tool_chain)
            ]
            
            if required_failures:
                error_messages = [f"{result.tool_name}: {result.error}" for result in required_failures]
                return {
                    'success': False,
                    'errors': error_messages,
                    'data': None
                }
            
            # Combine results
            combined_data = await self._combine_tool_results(execution_results, context)
            
            return {
                'success': True,
                'errors': [],
                'data': combined_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [f"Tool orchestration error: {str(e)}"],
                'data': None
            }
    
    async def _execute_tool_chain(self, tool_chain: List[Dict[str, Any]], 
                                request_data: Dict[str, Any], 
                                context: ExecutionContext) -> List[ToolInvocationResult]:
        """Execute a chain of tool invocations."""
        results = []
        
        # Prepare driver resolution first if needed
        resolved_drivers = None
        if any(step['tool'] == 'driver_tool' for step in tool_chain):
            driver_step = next(step for step in tool_chain if step['tool'] == 'driver_tool')
            driver_result = await self._execute_driver_resolution(request_data, context)
            results.append(driver_result)
            
            if driver_result.success:
                resolved_drivers = driver_result.result.get('data', {}).get('resolved_drivers', [])
                context.intermediate_data['resolved_drivers'] = resolved_drivers
            elif driver_step.get('required', True):
                # If driver resolution is required and failed, stop here
                return results
        
        # Execute remaining tools
        concurrent_tasks = []
        sequential_tasks = []
        
        for step in tool_chain:
            if step['tool'] == 'driver_tool':
                continue  # Already handled
            
            # Determine if this can be run concurrently
            if self._can_run_concurrently(step, tool_chain):
                task_params = self._prepare_tool_parameters(step, request_data, context)
                task = self.mcp_registry.invoke_tool(step['tool'], step['method'], task_params)
                concurrent_tasks.append((step, task))
            else:
                sequential_tasks.append(step)
        
        # Execute concurrent tasks
        if concurrent_tasks:
            concurrent_results = await asyncio.gather(
                *[task for _, task in concurrent_tasks], 
                return_exceptions=True
            )
            
            for i, result in enumerate(concurrent_results):
                if isinstance(result, Exception):
                    step = concurrent_tasks[i][0]
                    error_result = ToolInvocationResult(
                        tool_name=step['tool'],
                        method_name=step['method'],
                        success=False,
                        result=None,
                        execution_time_ms=0,
                        error=str(result)
                    )
                    results.append(error_result)
                else:
                    results.append(result)
        
        # Execute sequential tasks
        for step in sequential_tasks:
            task_params = self._prepare_tool_parameters(step, request_data, context)
            result = await self.mcp_registry.invoke_tool(step['tool'], step['method'], task_params)
            results.append(result)
            
            # Update context with intermediate results
            if result.success:
                context.add_tool_result(step['tool'], step['method'], result.result)
        
        return results
    
    async def _execute_driver_resolution(self, request_data: Dict[str, Any], 
                                       context: ExecutionContext) -> ToolInvocationResult:
        """Execute driver resolution as the first step."""
        drivers = request_data.get('drivers', [])
        options = {
            'filters': request_data.get('filters', [])
        }
        
        return await self.mcp_registry.invoke_tool(
            'driver_tool', 
            'resolve_drivers', 
            {'identifiers': drivers, 'options': options}
        )
    
    def _prepare_tool_parameters(self, step: Dict[str, Any], 
                               request_data: Dict[str, Any], 
                               context: ExecutionContext) -> Dict[str, Any]:
        """Prepare parameters for tool invocation."""
        tool_name = step['tool']
        method_name = step['method']
        
        # Base parameters from request
        params = {}
        
        # Add resolved driver IDs if available
        resolved_drivers = context.intermediate_data.get('resolved_drivers', [])
        if resolved_drivers:
            if method_name in ['get_driver_scores', 'get_driver_trips', 'analyze_driver_trends']:
                # Single driver methods - use first resolved driver
                params['driver_id'] = resolved_drivers[0]['driver_id']
            elif method_name in ['compare_driver_scores', 'compare_trip_performance', 'compare_trend_patterns']:
                # Multi-driver comparison methods
                params['driver_ids'] = [driver['driver_id'] for driver in resolved_drivers]
        
        # Add common parameters
        if 'time_range' in request_data:
            params['time_range'] = request_data['time_range']
        
        if 'filters' in request_data:
            params['filters'] = request_data['filters']
        
        if 'aggregations' in request_data:
            params['aggregations'] = request_data['aggregations']
        
        # Tool-specific parameter mapping
        if tool_name == 'score_tool':
            if 'score_types' in request_data:
                params['score_types'] = request_data['score_types']
        
        elif tool_name == 'trip_tool':
            if 'pagination' in request_data:
                params['pagination'] = request_data['pagination']
        
        elif tool_name == 'trend_tool':
            if 'metrics' in request_data:
                params['metrics'] = request_data['metrics']
            if 'aggregation_period' in request_data:
                params['aggregation_period'] = request_data['aggregation_period']
        
        return params
    
    def _can_run_concurrently(self, step: Dict[str, Any], tool_chain: List[Dict[str, Any]]) -> bool:
        """Determine if a tool step can be run concurrently."""
        # Most analytics tools can run concurrently after driver resolution
        concurrent_tools = ['score_tool', 'trip_tool']
        return step['tool'] in concurrent_tools
    
    def _is_tool_required(self, tool_name: str, tool_chain: List[Dict[str, Any]]) -> bool:
        """Check if a tool is required in the chain."""
        for step in tool_chain:
            if step['tool'] == tool_name:
                return step.get('required', True)
        return False
    
    async def _combine_tool_results(self, execution_results: List[ToolInvocationResult], 
                                  context: ExecutionContext) -> Dict[str, Any]:
        """Combine results from multiple tool executions."""
        combined_data = {
            'driver_resolution': None,
            'score_analysis': None,
            'trip_analysis': None,
            'trend_analysis': None,
            'execution_summary': {
                'total_tools_executed': len(execution_results),
                'successful_tools': len([r for r in execution_results if r.success]),
                'failed_tools': len([r for r in execution_results if not r.success]),
                'total_execution_time_ms': sum(r.execution_time_ms for r in execution_results)
            }
        }
        
        # Process each tool result
        for result in execution_results:
            if not result.success:
                context.add_warning(f"Tool {result.tool_name} failed: {result.error}")
                continue
            
            # Extract data based on tool type
            if result.tool_name == 'driver_tool':
                combined_data['driver_resolution'] = result.result
            elif result.tool_name == 'score_tool':
                combined_data['score_analysis'] = result.result
            elif result.tool_name == 'trip_tool':
                combined_data['trip_analysis'] = result.result
            elif result.tool_name == 'trend_tool':
                combined_data['trend_analysis'] = result.result
        
        return combined_data
    
    async def _post_process_results(self, combined_data: Dict[str, Any], 
                                  context: ExecutionContext) -> Dict[str, Any]:
        """Post-process and summarize results."""
        try:
            # Generate summary
            summary_config = SummaryConfig(
                max_tokens=self.config.summarization.max_summary_tokens,
                include_metadata=self.config.summarization.include_metadata,
                compression_ratio=self.config.summarization.compression_ratio
            )
            
            # Determine summary type based on available data
            if combined_data.get('trend_analysis'):
                summary_type = "trend"
            elif combined_data.get('score_analysis') and combined_data.get('trip_analysis'):
                summary_type = "combined"
            elif combined_data.get('score_analysis'):
                summary_type = "score"
            elif combined_data.get('trip_analysis'):
                summary_type = "trip"
            else:
                summary_type = "general"
            
            # Create data for summarization
            summary_data = []
            for key, value in combined_data.items():
                if value and isinstance(value, dict) and value.get('success'):
                    data_section = value.get('data', {})
                    if isinstance(data_section, dict):
                        summary_data.extend(self._flatten_data_for_summary(data_section))
            
            # Generate summary
            if summary_data:
                self.summarizer.config = summary_config
                summary = self.summarizer.summarize_driver_data(summary_data, summary_type)
            else:
                summary = {"message": "No data available for summarization"}
            
            # Create final response
            final_result = {
                "success": True,
                "request_id": context.request_id,
                "data": combined_data,
                "summary": summary,
                "execution_info": {
                    "execution_time_ms": context.get_execution_time_ms(),
                    "tools_executed": context.metadata.get('tools_executed', []),
                    "cache_used": False,
                    "warnings": context.warnings,
                    "complexity_estimate": context.metadata.get('complexity_estimate')
                },
                "metadata": {
                    "agent_name": self.agent_card.metadata.name,
                    "agent_version": self.agent_card.metadata.version,
                    "timestamp": datetime.now().isoformat(),
                    "request_type": context.request_data.get('report_type', 'unknown')
                }
            }
            
            return final_result
            
        except Exception as e:
            context.add_error(f"Post-processing failed: {str(e)}")
            return self._create_error_response(context, "Post-processing error", [str(e)])
    
    def _flatten_data_for_summary(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Flatten nested data structure for summarization."""
        flattened = []
        
        # Handle different data structures
        if 'drivers' in data:
            drivers_data = data['drivers']
            if isinstance(drivers_data, list):
                flattened.extend(drivers_data)
        
        if 'trips' in data:
            trips_data = data['trips']
            if isinstance(trips_data, list):
                flattened.extend(trips_data)
        
        if 'scores' in data:
            scores_data = data['scores']
            if isinstance(scores_data, list):
                flattened.extend(scores_data)
        
        # If no specific structure found, try to extract any list data
        if not flattened:
            for key, value in data.items():
                if isinstance(value, list) and value:
                    flattened.extend(value)
                    break
        
        return flattened
    
    async def _cache_result(self, request_data: Dict[str, Any], 
                          result: Dict[str, Any], context: ExecutionContext) -> None:
        """Cache the result for future requests."""
        try:
            # Determine TTL based on data type and complexity
            complexity = context.metadata.get('complexity_estimate', {})
            if complexity.get('final_complexity') in ['complex', 'very_complex']:
                ttl = 7200  # 2 hours for complex queries
            else:
                ttl = 3600  # 1 hour for simple queries
            
            await self.cache_manager.cache_request_result(request_data, result, ttl)
            
        except Exception as e:
            context.add_warning(f"Failed to cache result: {str(e)}")
    
    def _create_error_response(self, context: ExecutionContext, 
                             error_message: str, errors: List[str]) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            "success": False,
            "request_id": context.request_id,
            "error": error_message,
            "errors": errors,
            "warnings": context.warnings,
            "execution_info": {
                "execution_time_ms": context.get_execution_time_ms(),
                "failed_at": "validation" if not context.tool_results else "execution"
            },
            "metadata": {
                "agent_name": self.agent_card.metadata.name,
                "agent_version": self.agent_card.metadata.version,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def _update_success_stats(self, context: ExecutionContext) -> None:
        """Update execution statistics for successful request."""
        self.execution_stats['successful_requests'] += 1
        
        # Update average execution time
        total_requests = self.execution_stats['total_requests']
        current_avg = self.execution_stats['average_execution_time_ms']
        new_time = context.get_execution_time_ms()
        
        self.execution_stats['average_execution_time_ms'] = (
            (current_avg * (total_requests - 1) + new_time) / total_requests
        )
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status."""
        # Get MCP registry status
        registry_stats = self.mcp_registry.get_invocation_stats()
        
        # Get cache statistics
        cache_stats = self.cache_manager.get_stats()
        
        # Get tool health
        tool_health = await self.mcp_registry.health_check()
        
        return {
            "agent_info": self.agent_card.get_agent_summary(),
            "execution_stats": self.execution_stats,
            "tool_registry": {
                "registered_tools": len(self.mcp_registry.tools),
                "enabled_tools": len([t for t in self.mcp_registry.tools.values() if t.enabled]),
                "tool_invocation_stats": registry_stats
            },
            "cache_performance": cache_stats,
            "tool_health": tool_health,
            "system_status": {
                "status": "healthy" if tool_health.get('overall_status') == 'healthy' else "degraded",
                "uptime_info": "Available",
                "last_updated": datetime.now().isoformat()
            }
        }
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities information."""
        return {
            "agent_card": self.agent_card.to_dict(),
            "registered_tools": self.mcp_registry.get_registered_tools(),
            "supported_operations": {
                "request_types": list(self.agent_card.supported_request_types.keys()),
                "capabilities": [cap.name for cap in self.agent_card.capabilities],
                "features": [
                    "batch_processing",
                    "caching",
                    "pagination",
                    "concurrent_execution",
                    "error_recovery",
                    "result_summarization"
                ]
            }
        }