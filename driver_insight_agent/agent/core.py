"""
Core Agent Orchestrator - Main orchestration logic for Driver Insight Agent.
Handles tool selection, execution, caching, error handling, and summarization.
"""
import asyncio
import time
from typing import Any, Dict, List, Optional
from agent.mcp_registry import MCPRegistry
from agent.abstract_card import AgentAbstractCard
from cache.cache_manager import CacheManager, ResultCache
from utils.validation import AgentRequest, AgentResponse, validate_request
from utils.filter_engine import FilterEngine
from utils.aggregation_engine import AggregationEngine
from utils.pagination import Pagination
from utils.summarizer import Summarizer
from config.config import config
import structlog

logger = structlog.get_logger()


class DriverInsightAgent:
    """Core orchestrator for Driver Insight Agent."""
    
    def __init__(self):
        """Initialize the Driver Insight Agent."""
        self.mcp_registry = MCPRegistry()
        self.abstract_card = AgentAbstractCard()
        
        # Initialize cache
        self.cache_manager = CacheManager(
            ttl_seconds=config.cache_ttl,
            max_size=config.cache_max_size,
            enable_persistent=config.get('cache.enable_persistent', True),
            persistent_path=config.get('cache.persistent_path', './cache_storage')
        )
        self.result_cache = ResultCache(self.cache_manager)
        
        # Initialize utilities
        self.filter_engine = FilterEngine()
        self.aggregation_engine = AggregationEngine()
        self.pagination = Pagination(page_size=config.default_page_size)
        self.summarizer = Summarizer(max_tokens=config.summarization_max_tokens)
        
        # Statistics
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
    
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a request from the Planner Agent.
        
        Args:
            request_data: Request dictionary with driver IDs, time range, filters, etc.
            
        Returns:
            AgentResponse dictionary with results
        """
        start_time = time.time()
        self._total_requests += 1
        
        try:
            # Validate request
            request = validate_request(request_data)
            is_valid, error_msg = request.validate_request()
            
            if not is_valid:
                self._failed_requests += 1
                return self._create_error_response(
                    request.request_id,
                    f"Validation error: {error_msg}",
                    start_time
                )
            
            # Check cache
            cached_result = self.result_cache.get_batch_result(request.request_id)
            if cached_result is not None:
                logger.info("cache_hit", request_id=request.request_id)
                cached_result['cache_hits'] = cached_result.get('cache_hits', 0) + 1
                return cached_result
            
            # Select and execute tools
            result = await self._execute_workflow(request, start_time)
            
            # Cache result
            if result['success']:
                self.result_cache.cache_batch_result(request.request_id, result)
                self._successful_requests += 1
            else:
                self._failed_requests += 1
            
            return result
        
        except Exception as e:
            self._failed_requests += 1
            logger.error("request_processing_error", error=str(e))
            return self._create_error_response(
                request_data.get('request_id', 'unknown'),
                f"Processing error: {str(e)}",
                start_time
            )
    
    async def _execute_workflow(
        self,
        request: AgentRequest,
        start_time: float
    ) -> Dict[str, Any]:
        """
        Execute the complete workflow for a request.
        
        Args:
            request: Validated agent request
            start_time: Request start time
            
        Returns:
            AgentResponse dictionary
        """
        tools_executed = []
        cache_hits = 0
        combined_data = {}
        
        try:
            # Step 1: Discover required tools
            tools_to_execute = self.mcp_registry.discover_tools_for_request(
                report_type=request.report_type.value,
                has_time_range=bool(request.start_date or request.end_date),
                needs_trends=(request.report_type.value == 'trend')
            )
            
            # Step 2: Determine execution order
            ordered_tools = self.mcp_registry.get_tool_execution_order(tools_to_execute)
            
            logger.info(
                "workflow_planned",
                request_id=request.request_id,
                tools=ordered_tools
            )
            
            # Step 3: Execute driver resolution first
            driver_result = await self._execute_with_retry(
                'driver_tool',
                self._prepare_driver_params(request)
            )
            
            if not driver_result['success']:
                return self._create_error_response(
                    request.request_id,
                    f"Driver resolution failed: {driver_result.get('error')}",
                    start_time
                )
            
            tools_executed.append('driver_tool')
            combined_data['drivers'] = driver_result['data']
            driver_ids = [d['driver_id'] for d in driver_result['data']]
            
            # Step 4: Execute remaining tools in parallel or sequentially
            remaining_tools = [t for t in ordered_tools if t != 'driver_tool']
            
            if 'trend_tool' in remaining_tools:
                # Trend tool needs data from other tools, execute sequentially
                results = await self._execute_sequential(
                    remaining_tools,
                    driver_ids,
                    request
                )
            else:
                # Execute other tools in parallel
                results = await self._execute_parallel(
                    remaining_tools,
                    driver_ids,
                    request
                )
            
            # Step 5: Combine results
            for tool_name, result in zip(remaining_tools, results):
                tools_executed.append(tool_name)
                
                if result['success']:
                    self._merge_tool_result(combined_data, tool_name, result)
                else:
                    logger.warning(
                        "tool_execution_failed",
                        tool=tool_name,
                        error=result.get('error')
                    )
            
            # Step 6: Apply post-processing
            processed_data = await self._post_process(combined_data, request)
            
            # Step 7: Generate summary
            summary = self.summarizer.create_comprehensive_summary(
                processed_data,
                request.report_type.value
            )
            
            # Step 8: Create response
            execution_time = (time.time() - start_time) * 1000
            
            return {
                'request_id': request.request_id,
                'success': True,
                'data': processed_data,
                'summary': summary,
                'error': None,
                'execution_time_ms': execution_time,
                'tools_executed': tools_executed,
                'cache_hits': cache_hits
            }
        
        except Exception as e:
            logger.error("workflow_execution_error", error=str(e))
            return self._create_error_response(
                request.request_id,
                f"Workflow execution error: {str(e)}",
                start_time
            )
    
    def _prepare_driver_params(self, request: AgentRequest) -> Dict[str, Any]:
        """Prepare parameters for driver tool."""
        params = {}
        
        if request.driver_ids:
            params['driver_ids'] = request.driver_ids
        if request.driver_names:
            params['driver_names'] = request.driver_names
        if request.driver_emails:
            params['driver_emails'] = request.driver_emails
        if request.driver_phones:
            params['driver_phones'] = request.driver_phones
        
        return params
    
    async def _execute_with_retry(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        max_attempts: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute tool with retry logic.
        
        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
            max_attempts: Maximum retry attempts
            
        Returns:
            Tool execution result
        """
        max_attempts = max_attempts or config.max_retry_attempts
        backoff_base = config.backoff_base
        
        for attempt in range(max_attempts):
            try:
                # Check cache first
                cached_result = self.result_cache.get_tool_result(tool_name, parameters)
                if cached_result is not None:
                    cached_result['cached'] = True
                    return cached_result
                
                # Execute tool
                result = await self.mcp_registry.invoke_tool(tool_name, parameters)
                
                # Cache successful result
                if result['success']:
                    self.result_cache.cache_tool_result(tool_name, parameters, result)
                
                return result
            
            except Exception as e:
                if attempt < max_attempts - 1:
                    # Calculate backoff delay
                    delay = backoff_base ** attempt
                    logger.warning(
                        "tool_retry",
                        tool=tool_name,
                        attempt=attempt + 1,
                        delay=delay,
                        error=str(e)
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "tool_max_retries_exceeded",
                        tool=tool_name,
                        error=str(e)
                    )
                    return {
                        'success': False,
                        'data': None,
                        'error': f"Max retries exceeded: {str(e)}",
                        'execution_time_ms': 0
                    }
        
        return {
            'success': False,
            'data': None,
            'error': "Unknown error in retry logic",
            'execution_time_ms': 0
        }
    
    async def _execute_parallel(
        self,
        tool_names: List[str],
        driver_ids: List[str],
        request: AgentRequest
    ) -> List[Dict[str, Any]]:
        """Execute multiple tools in parallel."""
        tasks = []
        
        for tool_name in tool_names:
            params = self._prepare_tool_params(tool_name, driver_ids, request)
            task = self._execute_with_retry(tool_name, params)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append({
                    'success': False,
                    'data': None,
                    'error': str(result),
                    'execution_time_ms': 0
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _execute_sequential(
        self,
        tool_names: List[str],
        driver_ids: List[str],
        request: AgentRequest
    ) -> List[Dict[str, Any]]:
        """Execute tools sequentially (for dependent tools)."""
        results = []
        intermediate_data = {}
        
        for tool_name in tool_names:
            params = self._prepare_tool_params(
                tool_name,
                driver_ids,
                request,
                intermediate_data
            )
            
            result = await self._execute_with_retry(tool_name, params)
            results.append(result)
            
            # Store intermediate data for next tool
            if result['success'] and result['data']:
                intermediate_data[tool_name] = result['data']
        
        return results
    
    def _prepare_tool_params(
        self,
        tool_name: str,
        driver_ids: List[str],
        request: AgentRequest,
        intermediate_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Prepare parameters for a specific tool."""
        params = {'driver_ids': driver_ids}
        
        # Add time range if available
        if request.start_date:
            params['start_date'] = request.start_date
        if request.end_date:
            params['end_date'] = request.end_date
        
        # Add filters
        if request.filters:
            params['filters'] = request.filters
        
        # Add pagination
        if request.limit:
            params['limit'] = request.limit
        if request.offset:
            params['offset'] = request.offset
        
        # Tool-specific parameters
        if tool_name == 'score_tool':
            params['aggregation'] = request.aggregations[0] if request.aggregations else 'avg'
            params['ranking'] = (request.report_type.value == 'ranking')
            params['comparison'] = (request.report_type.value == 'comparison')
        
        elif tool_name == 'trend_tool':
            params['metric'] = 'score'  # Default metric
            params['granularity'] = 'daily'
            
            # Pass raw data from previous tools
            if intermediate_data and 'score_tool' in intermediate_data:
                params['raw_data'] = intermediate_data['score_tool']
        
        return params
    
    def _merge_tool_result(
        self,
        combined_data: Dict[str, Any],
        tool_name: str,
        result: Dict[str, Any]
    ) -> None:
        """Merge tool result into combined data."""
        if tool_name == 'trip_tool':
            combined_data['trips'] = result['data']
            combined_data['trip_summary'] = result.get('summary')
        
        elif tool_name == 'score_tool':
            combined_data['scores'] = result['data']
            if result.get('comparison'):
                combined_data['comparison'] = result['comparison']
        
        elif tool_name == 'trend_tool':
            combined_data['trends'] = result['data']
    
    async def _post_process(
        self,
        data: Dict[str, Any],
        request: AgentRequest
    ) -> Dict[str, Any]:
        """Apply post-processing to combined data."""
        processed = data.copy()
        
        # Apply aggregations if requested
        if request.aggregations and 'scores' in processed:
            aggregation_specs = [
                {'field': 'score', 'operation': agg}
                for agg in request.aggregations
            ]
            agg_results = self.aggregation_engine.aggregate_multiple(
                processed['scores'],
                aggregation_specs
            )
            processed['aggregations'] = agg_results
        
        # Apply sorting if requested
        if request.sort_by and 'scores' in processed:
            reverse = (request.sort_order == 'desc')
            try:
                processed['scores'] = sorted(
                    processed['scores'],
                    key=lambda x: x.get(request.sort_by, 0),
                    reverse=reverse
                )
            except (TypeError, KeyError):
                pass  # Skip if sorting fails
        
        return processed
    
    def _create_error_response(
        self,
        request_id: str,
        error_message: str,
        start_time: float
    ) -> Dict[str, Any]:
        """Create error response."""
        execution_time = (time.time() - start_time) * 1000
        
        return {
            'request_id': request_id,
            'success': False,
            'data': None,
            'summary': None,
            'error': error_message,
            'execution_time_ms': execution_time,
            'tools_executed': [],
            'cache_hits': 0
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        cache_stats = self.cache_manager.get_stats()
        
        return {
            'agent': {
                'total_requests': self._total_requests,
                'successful_requests': self._successful_requests,
                'failed_requests': self._failed_requests,
                'success_rate': (
                    self._successful_requests / self._total_requests * 100
                    if self._total_requests > 0 else 0
                )
            },
            'cache': cache_stats,
            'tools': self.mcp_registry.list_tools()
        }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities."""
        return self.abstract_card.get_card()
