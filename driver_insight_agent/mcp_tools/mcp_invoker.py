"""MCP Tool invocation layer for Driver Insight Agent."""

import asyncio
import time
from typing import Any, Dict, List, Optional

import httpx

from ..config import get_config
from ..services.logger import get_logger


class MCPToolError(Exception):
    """Custom exception for MCP tool errors."""
    
    def __init__(self, message: str, tool_name: str, status_code: Optional[int] = None):
        """Initialize MCP tool error.
        
        Args:
            message: Error message
            tool_name: Name of the MCP tool that failed
            status_code: HTTP status code if applicable
        """
        super().__init__(message)
        self.tool_name = tool_name
        self.status_code = status_code


class MCPInvoker:
    """Client for invoking MCP tools on external MCP Tool Server."""
    
    def __init__(self):
        """Initialize MCP invoker."""
        self.logger = get_logger()
        self.client: Optional[httpx.AsyncClient] = None
        self._config = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self.client is None:
            try:
                config = get_config()
                self._config = config.mcp_tools
            except RuntimeError:
                # Fallback configuration
                self._config = type('MCPToolsConfig', (), {
                    'server_url': 'http://localhost:8081/mcp-tools',
                    'timeout': 10.0,
                    'max_retries': 2,
                })()
            
            self.client = httpx.AsyncClient(
                base_url=self._config.server_url,
                timeout=httpx.Timeout(self._config.timeout),
                headers={
                    'User-Agent': 'DriverInsightAgent-MCPInvoker/1.0',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                }
            )
    
    async def close(self):
        """Close the HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    async def invoke_fetch_tool(self, driver_id: Optional[str] = None, driver_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Invoke FetchTool for retrieving driver data.
        
        Args:
            driver_id: Single driver ID to fetch
            driver_ids: List of driver IDs for batch fetch
            
        Returns:
            Tool execution result
            
        Raises:
            MCPToolError: If tool invocation fails
        """
        tool_name = "FetchTool"
        start_time = time.time()
        
        try:
            payload = {
                "tool": tool_name,
                "parameters": {}
            }
            
            if driver_id:
                payload["parameters"]["driver_id"] = driver_id
            elif driver_ids:
                payload["parameters"]["driver_ids"] = driver_ids
            else:
                raise MCPToolError("Either driver_id or driver_ids must be provided", tool_name)
            
            result = await self._make_tool_request(payload)
            duration = time.time() - start_time
            
            self.logger.log_mcp_tool_invocation(tool_name, True, duration, **payload["parameters"])
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.log_mcp_tool_invocation(tool_name, False, duration, error=str(e))
            if isinstance(e, MCPToolError):
                raise
            raise MCPToolError(f"FetchTool invocation failed: {str(e)}", tool_name)
    
    async def invoke_validate_tool(self, data: Any, validation_type: str = "driver") -> Dict[str, Any]:
        """Invoke ValidateTool for data validation.
        
        Args:
            data: Data to validate
            validation_type: Type of validation to perform
            
        Returns:
            Tool execution result
            
        Raises:
            MCPToolError: If tool invocation fails
        """
        tool_name = "ValidateTool"
        start_time = time.time()
        
        try:
            payload = {
                "tool": tool_name,
                "parameters": {
                    "data": data,
                    "validation_type": validation_type
                }
            }
            
            result = await self._make_tool_request(payload)
            duration = time.time() - start_time
            
            self.logger.log_mcp_tool_invocation(tool_name, True, duration, validation_type=validation_type)
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.log_mcp_tool_invocation(tool_name, False, duration, error=str(e))
            if isinstance(e, MCPToolError):
                raise
            raise MCPToolError(f"ValidateTool invocation failed: {str(e)}", tool_name)
    
    async def invoke_cache_tool(self, operation: str, key: str, value: Optional[Any] = None, ttl: Optional[int] = None) -> Dict[str, Any]:
        """Invoke CacheTool for cache operations.
        
        Args:
            operation: Cache operation (get, set, delete, exists, clear)
            key: Cache key
            value: Value to cache (for set operation)
            ttl: Time to live in seconds (for set operation)
            
        Returns:
            Tool execution result
            
        Raises:
            MCPToolError: If tool invocation fails
        """
        tool_name = "CacheTool"
        start_time = time.time()
        
        try:
            payload = {
                "tool": tool_name,
                "parameters": {
                    "operation": operation,
                    "key": key
                }
            }
            
            if value is not None:
                payload["parameters"]["value"] = value
            if ttl is not None:
                payload["parameters"]["ttl"] = ttl
            
            result = await self._make_tool_request(payload)
            duration = time.time() - start_time
            
            self.logger.log_mcp_tool_invocation(tool_name, True, duration, operation=operation, key=key)
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.log_mcp_tool_invocation(tool_name, False, duration, error=str(e))
            if isinstance(e, MCPToolError):
                raise
            raise MCPToolError(f"CacheTool invocation failed: {str(e)}", tool_name)
    
    async def invoke_summarize_tool(self, data: Any, summary_type: str = "driver_summary") -> Dict[str, Any]:
        """Invoke SummarizeTool for data summarization.
        
        Args:
            data: Data to summarize
            summary_type: Type of summary to generate
            
        Returns:
            Tool execution result
            
        Raises:
            MCPToolError: If tool invocation fails
        """
        tool_name = "SummarizeTool"
        start_time = time.time()
        
        try:
            payload = {
                "tool": tool_name,
                "parameters": {
                    "data": data,
                    "summary_type": summary_type
                }
            }
            
            result = await self._make_tool_request(payload)
            duration = time.time() - start_time
            
            self.logger.log_mcp_tool_invocation(tool_name, True, duration, summary_type=summary_type)
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.log_mcp_tool_invocation(tool_name, False, duration, error=str(e))
            if isinstance(e, MCPToolError):
                raise
            raise MCPToolError(f"SummarizeTool invocation failed: {str(e)}", tool_name)
    
    async def _make_tool_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make request to MCP Tool Server.
        
        Args:
            payload: Request payload
            
        Returns:
            Tool execution result
            
        Raises:
            MCPToolError: If request fails
        """
        await self._ensure_client()
        
        last_exception = None
        
        for attempt in range(self._config.max_retries + 1):
            try:
                response = await self.client.post("/invoke", json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Check if tool execution was successful
                    if result.get("success", False):
                        return result
                    else:
                        error_msg = result.get("error", "Tool execution failed")
                        raise MCPToolError(error_msg, payload.get("tool", "unknown"))
                
                elif response.status_code == 404:
                    raise MCPToolError(
                        f"Tool not found: {payload.get('tool', 'unknown')}",
                        payload.get("tool", "unknown"),
                        status_code=404
                    )
                
                elif response.status_code == 400:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", "Bad request")
                    except:
                        error_msg = "Bad request"
                    
                    raise MCPToolError(
                        f"Invalid tool parameters: {error_msg}",
                        payload.get("tool", "unknown"),
                        status_code=400
                    )
                
                elif 500 <= response.status_code < 600:
                    # Server error - retry
                    if attempt < self._config.max_retries:
                        wait_time = 1.0 * (attempt + 1)
                        self.logger.warning(
                            f"MCP Tool Server error {response.status_code}, retrying in {wait_time}s",
                            attempt=attempt + 1, tool=payload.get("tool")
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise MCPToolError(
                            f"MCP Tool Server error: {response.status_code}",
                            payload.get("tool", "unknown"),
                            status_code=response.status_code
                        )
                
                else:
                    raise MCPToolError(
                        f"Unexpected response status: {response.status_code}",
                        payload.get("tool", "unknown"),
                        status_code=response.status_code
                    )
            
            except httpx.RequestError as e:
                last_exception = e
                if attempt < self._config.max_retries:
                    wait_time = 1.0 * (attempt + 1)
                    self.logger.warning(
                        f"MCP Tool Server connection error, retrying in {wait_time}s: {str(e)}",
                        attempt=attempt + 1, tool=payload.get("tool")
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise MCPToolError(
                        f"MCP Tool Server connection failed after {self._config.max_retries} retries: {str(e)}",
                        payload.get("tool", "unknown")
                    )
            
            except MCPToolError:
                # Don't retry MCPToolError exceptions
                raise
            
            except Exception as e:
                last_exception = e
                raise MCPToolError(
                    f"Unexpected error invoking MCP tool: {str(e)}",
                    payload.get("tool", "unknown")
                )
        
        # This should not be reached, but just in case
        raise MCPToolError(
            f"Tool invocation failed after {self._config.max_retries} retries: {str(last_exception)}",
            payload.get("tool", "unknown")
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on MCP Tool Server.
        
        Returns:
            Health check result
        """
        await self._ensure_client()
        
        start_time = time.time()
        
        try:
            response = await self.client.get("/health")
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info("MCP Tool Server health check passed", duration=duration)
                return {
                    "status": "healthy",
                    "response_time": duration,
                    "server_info": result,
                    "timestamp": time.time()
                }
            else:
                self.logger.warning(f"MCP Tool Server health check failed: {response.status_code}", duration=duration)
                return {
                    "status": "unhealthy",
                    "response_time": duration,
                    "status_code": response.status_code,
                    "timestamp": time.time()
                }
        
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error("MCP Tool Server health check failed", error=str(e), duration=duration)
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time": duration,
                "timestamp": time.time()
            }
    
    async def list_available_tools(self) -> List[str]:
        """Get list of available tools from MCP Tool Server.
        
        Returns:
            List of available tool names
        """
        await self._ensure_client()
        
        try:
            response = await self.client.get("/tools")
            
            if response.status_code == 200:
                result = response.json()
                tools = result.get("tools", [])
                self.logger.info(f"Retrieved {len(tools)} available MCP tools")
                return tools
            else:
                self.logger.warning(f"Failed to get tool list: {response.status_code}")
                return []
        
        except Exception as e:
            self.logger.error("Failed to get available tools", error=str(e))
            return []


# Global MCP invoker instance
_mcp_invoker: Optional[MCPInvoker] = None


def get_mcp_invoker() -> MCPInvoker:
    """Get the global MCP invoker instance.
    
    Returns:
        MCPInvoker: The MCP invoker instance
    """
    global _mcp_invoker
    if _mcp_invoker is None:
        _mcp_invoker = MCPInvoker()
    return _mcp_invoker