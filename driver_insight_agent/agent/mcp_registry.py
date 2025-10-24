"""MCP tool registry for dynamic tool discovery, registration, and invocation."""

from typing import Dict, List, Any, Optional, Callable, Type
import asyncio
import inspect
from dataclasses import dataclass
from datetime import datetime
import structlog

from ..tools.driver_tool import DriverTool
from ..tools.trip_tool import TripTool
from ..tools.score_tool import ScoreTool
from ..tools.trend_tool import TrendTool
from ..cache.cache_manager import get_cache_manager


logger = structlog.get_logger(__name__)


@dataclass
class ToolRegistration:
    """Tool registration information."""
    name: str
    instance: Any
    description: str
    version: str
    methods: List[Dict[str, Any]]
    registered_at: datetime
    enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ToolInvocationResult:
    """Result of tool invocation."""
    tool_name: str
    method_name: str
    success: bool
    result: Any
    execution_time_ms: float
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MCPRegistry:
    """MCP tool registry for managing and invoking tools."""
    
    def __init__(self):
        """Initialize MCP registry."""
        self.tools: Dict[str, ToolRegistration] = {}
        self.cache_manager = get_cache_manager()
        self.invocation_stats: Dict[str, Dict[str, Any]] = {}
        
        # Initialize with built-in tools
        self._register_builtin_tools()
    
    def _register_builtin_tools(self) -> None:
        """Register built-in analytics tools."""
        builtin_tools = [
            DriverTool(),
            TripTool(),
            ScoreTool(),
            TrendTool()
        ]
        
        for tool in builtin_tools:
            try:
                self.register_tool(tool)
                logger.info(f"Registered built-in tool: {tool.name}")
            except Exception as e:
                logger.error(f"Failed to register built-in tool {tool.name}: {str(e)}")
    
    def register_tool(self, tool_instance: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Register a tool with the MCP registry."""
        try:
            # Get tool information
            if hasattr(tool_instance, 'get_tool_info'):
                tool_info = tool_instance.get_tool_info()
            else:
                raise ValueError("Tool must implement get_tool_info() method")
            
            # Validate required fields
            required_fields = ['name', 'description', 'version', 'methods']
            for field in required_fields:
                if field not in tool_info:
                    raise ValueError(f"Tool info missing required field: {field}")
            
            # Validate methods
            for method in tool_info['methods']:
                if 'name' not in method or 'description' not in method:
                    raise ValueError("Tool method missing name or description")
            
            # Check if tool already registered
            tool_name = tool_info['name']
            if tool_name in self.tools:
                logger.warning(f"Tool {tool_name} already registered, updating registration")
            
            # Create registration
            registration = ToolRegistration(
                name=tool_name,
                instance=tool_instance,
                description=tool_info['description'],
                version=tool_info['version'],
                methods=tool_info['methods'],
                registered_at=datetime.now(),
                metadata=metadata
            )
            
            self.tools[tool_name] = registration
            
            # Initialize invocation stats
            self.invocation_stats[tool_name] = {
                'total_invocations': 0,
                'successful_invocations': 0,
                'failed_invocations': 0,
                'average_execution_time_ms': 0,
                'last_invocation': None
            }
            
            logger.info(f"Successfully registered tool: {tool_name} v{tool_info['version']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register tool: {str(e)}")
            return False
    
    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool from the registry."""
        try:
            if tool_name not in self.tools:
                logger.warning(f"Tool {tool_name} not found in registry")
                return False
            
            del self.tools[tool_name]
            if tool_name in self.invocation_stats:
                del self.invocation_stats[tool_name]
            
            logger.info(f"Successfully unregistered tool: {tool_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister tool {tool_name}: {str(e)}")
            return False
    
    def get_registered_tools(self) -> List[Dict[str, Any]]:
        """Get list of all registered tools."""
        return [
            {
                'name': reg.name,
                'description': reg.description,
                'version': reg.version,
                'enabled': reg.enabled,
                'registered_at': reg.registered_at.isoformat(),
                'methods': reg.methods,
                'metadata': reg.metadata
            }
            for reg in self.tools.values()
        ]
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific tool."""
        if tool_name not in self.tools:
            return None
        
        registration = self.tools[tool_name]
        stats = self.invocation_stats.get(tool_name, {})
        
        return {
            'name': registration.name,
            'description': registration.description,
            'version': registration.version,
            'enabled': registration.enabled,
            'registered_at': registration.registered_at.isoformat(),
            'methods': registration.methods,
            'metadata': registration.metadata,
            'invocation_stats': stats
        }
    
    def enable_tool(self, tool_name: str) -> bool:
        """Enable a tool."""
        if tool_name not in self.tools:
            return False
        
        self.tools[tool_name].enabled = True
        logger.info(f"Enabled tool: {tool_name}")
        return True
    
    def disable_tool(self, tool_name: str) -> bool:
        """Disable a tool."""
        if tool_name not in self.tools:
            return False
        
        self.tools[tool_name].enabled = False
        logger.info(f"Disabled tool: {tool_name}")
        return True
    
    async def invoke_tool(self, tool_name: str, method_name: str, 
                         parameters: Dict[str, Any]) -> ToolInvocationResult:
        """Invoke a tool method."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Check if tool exists and is enabled
            if tool_name not in self.tools:
                return ToolInvocationResult(
                    tool_name=tool_name,
                    method_name=method_name,
                    success=False,
                    result=None,
                    execution_time_ms=0,
                    error=f"Tool '{tool_name}' not found in registry"
                )
            
            registration = self.tools[tool_name]
            if not registration.enabled:
                return ToolInvocationResult(
                    tool_name=tool_name,
                    method_name=method_name,
                    success=False,
                    result=None,
                    execution_time_ms=0,
                    error=f"Tool '{tool_name}' is disabled"
                )
            
            # Check if method exists
            method_exists = any(method['name'] == method_name for method in registration.methods)
            if not method_exists:
                return ToolInvocationResult(
                    tool_name=tool_name,
                    method_name=method_name,
                    success=False,
                    result=None,
                    execution_time_ms=0,
                    error=f"Method '{method_name}' not found in tool '{tool_name}'"
                )
            
            # Check cache first
            cache_key = self._generate_invocation_cache_key(tool_name, method_name, parameters)
            cached_result = await self.cache_manager.get(cache_key)
            
            if cached_result:
                execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
                logger.info(f"Cache hit for {tool_name}.{method_name}")
                
                return ToolInvocationResult(
                    tool_name=tool_name,
                    method_name=method_name,
                    success=True,
                    result=cached_result,
                    execution_time_ms=execution_time,
                    metadata={'from_cache': True}
                )
            
            # Invoke the tool method
            tool_instance = registration.instance
            
            if hasattr(tool_instance, 'execute_method'):
                result = await tool_instance.execute_method(method_name, parameters)
            else:
                # Fallback to direct method invocation
                if hasattr(tool_instance, method_name):
                    method = getattr(tool_instance, method_name)
                    if inspect.iscoroutinefunction(method):
                        result = await method(**parameters)
                    else:
                        result = method(**parameters)
                else:
                    raise AttributeError(f"Method '{method_name}' not found")
            
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Cache successful results
            if isinstance(result, dict) and result.get('success', False):
                await self.cache_manager.set(
                    cache_key, 
                    result, 
                    ttl=1800,  # 30 minutes default
                    tags=[f'tool_{tool_name}', f'method_{method_name}']
                )
            
            # Update invocation stats
            self._update_invocation_stats(tool_name, True, execution_time)
            
            logger.info(f"Successfully invoked {tool_name}.{method_name} in {execution_time:.2f}ms")
            
            return ToolInvocationResult(
                tool_name=tool_name,
                method_name=method_name,
                success=True,
                result=result,
                execution_time_ms=execution_time,
                metadata={'from_cache': False}
            )
            
        except Exception as e:
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
            error_message = str(e)
            
            # Update invocation stats
            self._update_invocation_stats(tool_name, False, execution_time)
            
            logger.error(f"Failed to invoke {tool_name}.{method_name}: {error_message}")
            
            return ToolInvocationResult(
                tool_name=tool_name,
                method_name=method_name,
                success=False,
                result=None,
                execution_time_ms=execution_time,
                error=error_message
            )
    
    async def batch_invoke_tools(self, invocations: List[Dict[str, Any]]) -> List[ToolInvocationResult]:
        """Invoke multiple tools concurrently."""
        tasks = []
        
        for invocation in invocations:
            task = self.invoke_tool(
                invocation.get('tool_name'),
                invocation.get('method_name'),
                invocation.get('parameters', {})
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions in results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                invocation = invocations[i]
                processed_results.append(ToolInvocationResult(
                    tool_name=invocation.get('tool_name', 'unknown'),
                    method_name=invocation.get('method_name', 'unknown'),
                    success=False,
                    result=None,
                    execution_time_ms=0,
                    error=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    def select_tools_for_request(self, request_type: str, 
                               request_data: Dict[str, Any]) -> List[str]:
        """Select appropriate tools based on request type and data."""
        selected_tools = []
        
        # Tool selection logic based on request type
        if request_type == "score":
            selected_tools = ["score_tool"]
        elif request_type == "trip":
            selected_tools = ["trip_tool"]
        elif request_type == "trend":
            selected_tools = ["trend_tool"]
        elif request_type == "combined":
            selected_tools = ["driver_tool", "trip_tool", "score_tool"]
        elif request_type == "comparison":
            selected_tools = ["driver_tool", "score_tool", "trip_tool"]
        elif request_type == "ranking":
            selected_tools = ["score_tool"]
        else:
            # Default: include driver tool for resolution
            selected_tools = ["driver_tool"]
        
        # Always include driver tool if we have driver identifiers to resolve
        if request_data.get('drivers') and "driver_tool" not in selected_tools:
            selected_tools.insert(0, "driver_tool")
        
        # Filter to only enabled tools
        enabled_tools = [
            tool_name for tool_name in selected_tools 
            if tool_name in self.tools and self.tools[tool_name].enabled
        ]
        
        logger.info(f"Selected tools for request type '{request_type}': {enabled_tools}")
        return enabled_tools
    
    def get_tool_chain_for_request(self, request_type: str, 
                                 request_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get recommended tool execution chain for a request."""
        chains = {
            "score": [
                {"tool": "driver_tool", "method": "resolve_drivers", "required": True},
                {"tool": "score_tool", "method": "get_driver_scores", "required": True}
            ],
            "trip": [
                {"tool": "driver_tool", "method": "resolve_drivers", "required": True},
                {"tool": "trip_tool", "method": "get_driver_trips", "required": True}
            ],
            "trend": [
                {"tool": "driver_tool", "method": "resolve_drivers", "required": True},
                {"tool": "trend_tool", "method": "analyze_driver_trends", "required": True}
            ],
            "combined": [
                {"tool": "driver_tool", "method": "resolve_drivers", "required": True},
                {"tool": "score_tool", "method": "get_driver_scores", "required": False},
                {"tool": "trip_tool", "method": "get_driver_trips", "required": False}
            ],
            "comparison": [
                {"tool": "driver_tool", "method": "resolve_drivers", "required": True},
                {"tool": "score_tool", "method": "compare_driver_scores", "required": True},
                {"tool": "trip_tool", "method": "compare_trip_performance", "required": False}
            ],
            "ranking": [
                {"tool": "score_tool", "method": "get_score_rankings", "required": True}
            ]
        }
        
        return chains.get(request_type, [])
    
    def get_invocation_stats(self) -> Dict[str, Any]:
        """Get overall invocation statistics."""
        total_invocations = sum(stats['total_invocations'] for stats in self.invocation_stats.values())
        total_successful = sum(stats['successful_invocations'] for stats in self.invocation_stats.values())
        total_failed = sum(stats['failed_invocations'] for stats in self.invocation_stats.values())
        
        return {
            'total_tools_registered': len(self.tools),
            'enabled_tools': len([t for t in self.tools.values() if t.enabled]),
            'total_invocations': total_invocations,
            'successful_invocations': total_successful,
            'failed_invocations': total_failed,
            'success_rate': total_successful / total_invocations if total_invocations > 0 else 0,
            'tool_stats': self.invocation_stats
        }
    
    def _generate_invocation_cache_key(self, tool_name: str, method_name: str, 
                                     parameters: Dict[str, Any]) -> str:
        """Generate cache key for tool invocation."""
        from ..cache.cache_manager import CacheKeyGenerator
        return CacheKeyGenerator.generate_key(f"tool_invocation_{tool_name}_{method_name}", **parameters)
    
    def _update_invocation_stats(self, tool_name: str, success: bool, execution_time_ms: float) -> None:
        """Update invocation statistics for a tool."""
        if tool_name not in self.invocation_stats:
            self.invocation_stats[tool_name] = {
                'total_invocations': 0,
                'successful_invocations': 0,
                'failed_invocations': 0,
                'average_execution_time_ms': 0,
                'last_invocation': None
            }
        
        stats = self.invocation_stats[tool_name]
        stats['total_invocations'] += 1
        stats['last_invocation'] = datetime.now().isoformat()
        
        if success:
            stats['successful_invocations'] += 1
        else:
            stats['failed_invocations'] += 1
        
        # Update average execution time
        current_avg = stats['average_execution_time_ms']
        total_invocations = stats['total_invocations']
        stats['average_execution_time_ms'] = (
            (current_avg * (total_invocations - 1) + execution_time_ms) / total_invocations
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all registered tools."""
        health_results = {}
        
        for tool_name, registration in self.tools.items():
            try:
                # Try to get tool info as a basic health check
                if hasattr(registration.instance, 'get_tool_info'):
                    tool_info = registration.instance.get_tool_info()
                    health_results[tool_name] = {
                        'status': 'healthy',
                        'enabled': registration.enabled,
                        'version': tool_info.get('version', 'unknown'),
                        'methods_count': len(tool_info.get('methods', []))
                    }
                else:
                    health_results[tool_name] = {
                        'status': 'unhealthy',
                        'error': 'Tool does not implement get_tool_info method'
                    }
            except Exception as e:
                health_results[tool_name] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
        
        overall_health = all(
            result.get('status') == 'healthy' 
            for result in health_results.values()
        )
        
        return {
            'overall_status': 'healthy' if overall_health else 'degraded',
            'total_tools': len(self.tools),
            'healthy_tools': len([r for r in health_results.values() if r.get('status') == 'healthy']),
            'tool_health': health_results,
            'timestamp': datetime.now().isoformat()
        }
    
    async def clear_tool_cache(self, tool_name: Optional[str] = None) -> int:
        """Clear cache for specific tool or all tools."""
        if tool_name:
            return await self.cache_manager.clear_by_tags([f'tool_{tool_name}'])
        else:
            # Clear all tool-related cache entries
            tool_tags = [f'tool_{name}' for name in self.tools.keys()]
            return await self.cache_manager.clear_by_tags(tool_tags)


# Global registry instance
_registry: Optional[MCPRegistry] = None


def get_mcp_registry() -> MCPRegistry:
    """Get the global MCP registry instance."""
    global _registry
    if _registry is None:
        _registry = MCPRegistry()
    return _registry


def initialize_mcp_registry() -> MCPRegistry:
    """Initialize and return the global MCP registry."""
    global _registry
    _registry = MCPRegistry()
    return _registry