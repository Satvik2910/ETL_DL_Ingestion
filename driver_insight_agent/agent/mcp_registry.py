"""
MCP Registry - Tool discovery, registration, and invocation.
Manages the registry of available tools and their capabilities.
"""
import asyncio
from typing import Any, Dict, List, Optional, Type
from tools.driver_tool import DriverTool
from tools.trip_tool import TripTool
from tools.score_tool import ScoreTool
from tools.trend_tool import TrendTool


class MCPRegistry:
    """Registry for MCP tools with discovery and invocation capabilities."""
    
    def __init__(self):
        self._tools: Dict[str, Any] = {}
        self._tool_metadata: Dict[str, Dict[str, Any]] = {}
        self._initialize_tools()
    
    def _initialize_tools(self) -> None:
        """Initialize and register all available tools."""
        # Register built-in tools
        self.register_tool(DriverTool())
        self.register_tool(TripTool())
        self.register_tool(ScoreTool())
        self.register_tool(TrendTool())
    
    def register_tool(self, tool_instance: Any) -> None:
        """
        Register a tool in the registry.
        
        Args:
            tool_instance: Instance of a tool with execute() and get_capabilities()
        """
        if not hasattr(tool_instance, 'name'):
            raise ValueError("Tool must have a 'name' attribute")
        
        if not hasattr(tool_instance, 'execute'):
            raise ValueError("Tool must have an 'execute' method")
        
        tool_name = tool_instance.name
        self._tools[tool_name] = tool_instance
        
        # Store tool metadata
        if hasattr(tool_instance, 'get_capabilities'):
            self._tool_metadata[tool_name] = tool_instance.get_capabilities()
        else:
            self._tool_metadata[tool_name] = {
                "name": tool_name,
                "description": getattr(tool_instance, 'description', 'No description'),
                "version": getattr(tool_instance, 'version', '1.0.0')
            }
    
    def unregister_tool(self, tool_name: str) -> None:
        """
        Unregister a tool from the registry.
        
        Args:
            tool_name: Name of tool to unregister
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
        if tool_name in self._tool_metadata:
            del self._tool_metadata[tool_name]
    
    def get_tool(self, tool_name: str) -> Optional[Any]:
        """
        Get tool instance by name.
        
        Args:
            tool_name: Name of tool to retrieve
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """
        Get list of all registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def get_tool_metadata(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific tool.
        
        Args:
            tool_name: Name of tool
            
        Returns:
            Tool metadata dictionary or None
        """
        return self._tool_metadata.get(tool_name)
    
    def get_all_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Get metadata for all registered tools.
        
        Returns:
            Dictionary of tool metadata
        """
        return self._tool_metadata.copy()
    
    async def invoke_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Invoke a tool by name with parameters.
        
        Args:
            tool_name: Name of tool to invoke
            parameters: Parameters to pass to tool
            
        Returns:
            Tool execution result
        """
        tool = self.get_tool(tool_name)
        
        if tool is None:
            return {
                "success": False,
                "data": None,
                "error": f"Tool '{tool_name}' not found in registry",
                "execution_time_ms": 0
            }
        
        try:
            result = await tool.execute(parameters)
            return result
        
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Tool execution failed: {str(e)}",
                "execution_time_ms": 0
            }
    
    async def invoke_tools_parallel(
        self,
        tool_requests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Invoke multiple tools in parallel.
        
        Args:
            tool_requests: List of dicts with 'tool_name' and 'parameters'
            
        Returns:
            List of tool execution results
        """
        tasks = []
        for request in tool_requests:
            tool_name = request.get('tool_name')
            parameters = request.get('parameters', {})
            
            if tool_name:
                task = self.invoke_tool(tool_name, parameters)
                tasks.append(task)
        
        if not tasks:
            return []
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "data": None,
                    "error": str(result),
                    "execution_time_ms": 0
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    def discover_tools_for_request(
        self,
        report_type: str,
        has_time_range: bool = False,
        needs_ranking: bool = False,
        needs_comparison: bool = False,
        needs_trends: bool = False
    ) -> List[str]:
        """
        Discover which tools to use based on request characteristics.
        
        Args:
            report_type: Type of report requested
            has_time_range: Whether request includes time range
            needs_ranking: Whether ranking is needed
            needs_comparison: Whether comparison is needed
            needs_trends: Whether trend analysis is needed
            
        Returns:
            List of tool names to execute
        """
        tools = []
        
        # Always need driver resolution
        tools.append('driver_tool')
        
        # Map report types to tools
        if report_type in ['score_only', 'combined', 'ranking', 'comparison']:
            tools.append('score_tool')
        
        if report_type in ['trip_only', 'combined']:
            tools.append('trip_tool')
        
        if report_type == 'trend' or needs_trends:
            # Trends need raw data first
            if 'score_tool' not in tools:
                tools.append('score_tool')
            tools.append('trend_tool')
        
        return tools
    
    def get_tool_execution_order(
        self,
        tool_names: List[str]
    ) -> List[str]:
        """
        Determine optimal execution order for tools.
        
        Args:
            tool_names: List of tool names
            
        Returns:
            Ordered list of tool names
        """
        # Define dependencies
        priority_order = {
            'driver_tool': 1,  # Always first
            'trip_tool': 2,
            'score_tool': 2,
            'trend_tool': 3    # Requires data from other tools
        }
        
        # Sort by priority
        sorted_tools = sorted(
            tool_names,
            key=lambda x: priority_order.get(x, 99)
        )
        
        return sorted_tools
    
    def validate_tool_parameters(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate parameters for a tool.
        
        Args:
            tool_name: Name of tool
            parameters: Parameters to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        metadata = self.get_tool_metadata(tool_name)
        
        if not metadata:
            return False, f"Tool '{tool_name}' not found"
        
        required_params = metadata.get('parameters', {})
        
        for param_name, param_spec in required_params.items():
            is_required = param_spec.get('required', False)
            
            if is_required and param_name not in parameters:
                return False, f"Required parameter '{param_name}' missing for tool '{tool_name}'"
        
        return True, None
    
    def get_tool_chain(
        self,
        start_tool: str,
        end_goal: str
    ) -> List[str]:
        """
        Get a chain of tools needed to achieve an end goal.
        
        Args:
            start_tool: Starting tool
            end_goal: End goal (e.g., 'trend_analysis')
            
        Returns:
            List of tools in execution order
        """
        chains = {
            'trend_analysis': ['driver_tool', 'score_tool', 'trend_tool'],
            'score_ranking': ['driver_tool', 'score_tool'],
            'trip_summary': ['driver_tool', 'trip_tool'],
            'full_report': ['driver_tool', 'trip_tool', 'score_tool', 'trend_tool']
        }
        
        return chains.get(end_goal, [start_tool])
