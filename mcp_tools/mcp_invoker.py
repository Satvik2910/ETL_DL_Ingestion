"""
MCP Tool Invoker for Driver Insight Agent.
Handles dynamic invocation of MCP tools hosted on an external MCP Tool Server.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

from config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)


class MCPToolType(str, Enum):
    """Enumeration of available MCP tool types."""
    FETCH = "FetchTool"
    VALIDATE = "ValidateTool"
    CACHE = "CacheTool"
    SUMMARIZE = "SummarizeTool"


class MCPInvokerError(Exception):
    """Custom exception for MCP invocation errors."""

    def __init__(self, message: str, tool_name: Optional[str] = None, details: Optional[Any] = None):
        """
        Initialize MCP invoker error.

        Args:
            message: Error message.
            tool_name: Name of the MCP tool.
            details: Additional error details.
        """
        super().__init__(message)
        self.tool_name = tool_name
        self.details = details


class MCPInvoker:
    """
    Invoker for MCP tools hosted on an external MCP Tool Server.
    Provides methods to invoke different MCP tools dynamically.
    """

    def __init__(self, server_url: Optional[str] = None):
        """
        Initialize MCP invoker.

        Args:
            server_url: URL of the MCP Tool Server. Uses config default if None.
        """
        config = get_config()
        self.server_url = server_url or config.mcp_tool_server.url
        self.timeout = config.mcp_tool_server.timeout
        self.enabled = config.mcp_tool_server.enabled

        self.client = httpx.AsyncClient(
            base_url=self.server_url,
            timeout=self.timeout,
        )

        logger.info("MCP invoker initialized", extra={
            "server_url": self.server_url,
            "enabled": self.enabled,
        })

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        logger.debug("MCP invoker closed")

    async def invoke_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Invoke an MCP tool with given parameters.

        Args:
            tool_name: Name of the MCP tool to invoke.
            parameters: Parameters to pass to the tool.

        Returns:
            Tool execution result.

        Raises:
            MCPInvokerError: If the tool invocation fails.
        """
        if not self.enabled:
            logger.warning(f"MCP invoker is disabled, skipping tool invocation", extra={
                "tool_name": tool_name,
            })
            return {"status": "skipped", "reason": "MCP invoker disabled"}

        logger.info(f"Invoking MCP tool", extra={
            "tool_name": tool_name,
            "parameters": parameters,
        })

        try:
            response = await self.client.post(
                "/invoke",
                json={
                    "tool_name": tool_name,
                    "parameters": parameters,
                }
            )

            if response.status_code >= 400:
                error_msg = f"MCP tool invocation failed with status {response.status_code}"
                logger.error(error_msg, extra={
                    "tool_name": tool_name,
                    "status_code": response.status_code,
                    "response": response.text,
                })
                raise MCPInvokerError(
                    error_msg,
                    tool_name=tool_name,
                    details=response.text,
                )

            result = response.json()
            logger.info(f"MCP tool invocation successful", extra={
                "tool_name": tool_name,
            })

            return result

        except httpx.RequestError as e:
            error_msg = f"Failed to connect to MCP Tool Server: {str(e)}"
            logger.error(error_msg, extra={
                "tool_name": tool_name,
                "error": str(e),
            })
            raise MCPInvokerError(error_msg, tool_name=tool_name, details=str(e))

        except Exception as e:
            error_msg = f"Unexpected error invoking MCP tool: {str(e)}"
            logger.error(error_msg, extra={
                "tool_name": tool_name,
                "error": str(e),
            }, exc_info=True)
            raise MCPInvokerError(error_msg, tool_name=tool_name, details=str(e))

    async def fetch_data(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Invoke FetchTool to fetch data from an API.

        Args:
            endpoint: API endpoint to fetch from.
            method: HTTP method (GET, POST, etc.).
            params: Query parameters.
            data: Request body data.

        Returns:
            Fetch result from the tool.
        """
        parameters = {
            "endpoint": endpoint,
            "method": method,
            "params": params or {},
            "data": data or {},
        }

        return await self.invoke_tool(MCPToolType.FETCH, parameters)

    async def validate_data(
        self,
        data: Dict[str, Any],
        required_fields: List[str],
        strict: bool = False,
    ) -> Dict[str, Any]:
        """
        Invoke ValidateTool to validate data fields.

        Args:
            data: Data to validate.
            required_fields: List of required field names.
            strict: Whether to use strict validation mode.

        Returns:
            Validation result from the tool.
        """
        parameters = {
            "data": data,
            "required_fields": required_fields,
            "strict": strict,
        }

        return await self.invoke_tool(MCPToolType.VALIDATE, parameters)

    async def cache_data(
        self,
        key: str,
        value: Any,
        operation: str = "set",
        ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Invoke CacheTool to handle cache operations.

        Args:
            key: Cache key.
            value: Value to cache (for set operation).
            operation: Cache operation (get, set, delete).
            ttl: Time to live in seconds.

        Returns:
            Cache operation result from the tool.
        """
        parameters = {
            "key": key,
            "value": value,
            "operation": operation,
            "ttl": ttl,
        }

        return await self.invoke_tool(MCPToolType.CACHE, parameters)

    async def summarize_data(
        self,
        data: List[Dict[str, Any]],
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Invoke SummarizeTool to summarize data.

        Args:
            data: Data to summarize.
            fields: Specific fields to include in summary.

        Returns:
            Summary result from the tool.
        """
        parameters = {
            "data": data,
            "fields": fields or [],
        }

        return await self.invoke_tool(MCPToolType.SUMMARIZE, parameters)

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of the MCP Tool Server.

        Returns:
            Health status information.
        """
        if not self.enabled:
            return {
                "status": "disabled",
                "message": "MCP invoker is disabled",
            }

        try:
            response = await self.client.get("/health")

            if response.status_code == 200:
                logger.info("MCP Tool Server is healthy")
                return {
                    "status": "healthy",
                    "server_url": self.server_url,
                    "response": response.json(),
                }
            else:
                logger.warning(f"MCP Tool Server health check failed", extra={
                    "status_code": response.status_code,
                })
                return {
                    "status": "unhealthy",
                    "server_url": self.server_url,
                    "status_code": response.status_code,
                }

        except Exception as e:
            logger.error(f"Failed to check MCP Tool Server health", extra={
                "error": str(e),
            })
            return {
                "status": "unreachable",
                "server_url": self.server_url,
                "error": str(e),
            }
