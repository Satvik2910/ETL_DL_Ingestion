"""
Example MCP Tool Server
Demonstrates how MCP tools can be hosted separately and invoked by the Driver Insight Agent.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI(
    title="MCP Tool Server",
    version="1.0.0",
    description="Model Context Protocol Tool Server for Driver Insight Agent",
)


# Request/Response Models
class ToolInvocationRequest(BaseModel):
    """Request model for tool invocation."""
    tool_name: str
    parameters: Dict[str, Any]


class ToolInvocationResponse(BaseModel):
    """Response model for tool invocation."""
    tool_name: str
    status: str
    data: Any
    timestamp: str


# MCP Tool Implementations
class FetchTool:
    """Tool for fetching data from external APIs."""

    @staticmethod
    async def execute(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute fetch operation.

        Args:
            parameters: Should contain endpoint, method, params, data.

        Returns:
            Fetched data.
        """
        endpoint = parameters.get("endpoint")
        method = parameters.get("method", "GET")
        params = parameters.get("params", {})
        data = parameters.get("data")

        # In a real implementation, this would call the actual external API
        # For demo purposes, return mock data
        if "/drivers/" in endpoint and method == "GET":
            driver_id = endpoint.split("/")[-1]
            return {
                "data": {
                    "driver_id": driver_id,
                    "name": f"Driver {driver_id}",
                    "vehicle": "Tesla Model Y",
                    "rating": 4.8,
                }
            }
        elif endpoint == "/drivers" and method == "GET":
            # Return paginated list
            limit = params.get("limit", 100)
            return {
                "data": {
                    "drivers": [
                        {
                            "driver_id": f"D{i:05d}",
                            "name": f"Driver {i}",
                            "vehicle": "Tesla Model Y",
                            "rating": 4.5 + (i % 10) * 0.05,
                        }
                        for i in range(1, min(limit + 1, 101))
                    ],
                    "total": limit,
                    "has_next": False,
                }
            }

        return {"data": None, "error": "Endpoint not found"}


class ValidateTool:
    """Tool for validating data fields."""

    @staticmethod
    async def execute(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute validation operation.

        Args:
            parameters: Should contain data, required_fields, strict.

        Returns:
            Validation result.
        """
        data = parameters.get("data", {})
        required_fields = parameters.get("required_fields", [])
        strict = parameters.get("strict", False)

        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                missing_fields.append(field)

        is_valid = len(missing_fields) == 0

        return {
            "valid": is_valid,
            "missing_fields": missing_fields,
            "strict_mode": strict,
        }


class CacheTool:
    """Tool for cache operations."""

    # Simple in-memory cache for demo
    _cache: Dict[str, tuple[Any, Optional[float]]] = {}

    @classmethod
    async def execute(cls, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute cache operation.

        Args:
            parameters: Should contain operation, key, value, ttl.

        Returns:
            Cache operation result.
        """
        operation = parameters.get("operation", "get")
        key = parameters.get("key")
        value = parameters.get("value")
        ttl = parameters.get("ttl")

        if operation == "get":
            if key in cls._cache:
                cached_value, expiry = cls._cache[key]
                if expiry is None or asyncio.get_event_loop().time() < expiry:
                    return {"status": "hit", "value": cached_value}
                else:
                    del cls._cache[key]
            return {"status": "miss", "value": None}

        elif operation == "set":
            import time
            expiry = time.time() + ttl if ttl else None
            cls._cache[key] = (value, expiry)
            return {"status": "success", "key": key}

        elif operation == "delete":
            if key in cls._cache:
                del cls._cache[key]
                return {"status": "success", "deleted": True}
            return {"status": "success", "deleted": False}

        return {"status": "error", "message": "Invalid operation"}


class SummarizeTool:
    """Tool for summarizing data."""

    @staticmethod
    async def execute(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute summarization operation.

        Args:
            parameters: Should contain data, fields.

        Returns:
            Summary result.
        """
        data = parameters.get("data", [])
        fields = parameters.get("fields", [])

        summary = {
            "total_records": len(data),
            "fields_summary": {},
        }

        # Generate field statistics
        if "rating" in str(data):
            ratings = [
                record.get("rating")
                for record in data
                if isinstance(record, dict) and "rating" in record
            ]
            if ratings:
                summary["fields_summary"]["rating"] = {
                    "count": len(ratings),
                    "average": sum(ratings) / len(ratings),
                    "min": min(ratings),
                    "max": max(ratings),
                }

        # Count unique values
        if "vehicle" in str(data):
            vehicles = [
                record.get("vehicle")
                for record in data
                if isinstance(record, dict) and "vehicle" in record
            ]
            summary["fields_summary"]["vehicle"] = {
                "unique_count": len(set(vehicles)),
                "total": len(vehicles),
            }

        return summary


# Tool Registry
TOOL_REGISTRY = {
    "FetchTool": FetchTool,
    "ValidateTool": ValidateTool,
    "CacheTool": CacheTool,
    "SummarizeTool": SummarizeTool,
}


# Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "MCP Tool Server",
        "version": "1.0.0",
        "available_tools": list(TOOL_REGISTRY.keys()),
    }


@app.post("/mcp-tools/invoke", response_model=ToolInvocationResponse)
async def invoke_tool(request: ToolInvocationRequest):
    """
    Invoke an MCP tool.

    Args:
        request: Tool invocation request.

    Returns:
        Tool execution result.
    """
    tool_name = request.tool_name
    parameters = request.parameters

    if tool_name not in TOOL_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_name}' not found. Available tools: {list(TOOL_REGISTRY.keys())}",
        )

    try:
        tool_class = TOOL_REGISTRY[tool_name]
        result = await tool_class.execute(parameters)

        return ToolInvocationResponse(
            tool_name=tool_name,
            status="success",
            data=result,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}",
        )


@app.get("/mcp-tools/list")
async def list_tools():
    """List all available MCP tools."""
    return {
        "tools": [
            {
                "name": tool_name,
                "description": tool_class.__doc__.strip() if tool_class.__doc__ else "",
            }
            for tool_name, tool_class in TOOL_REGISTRY.items()
        ]
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8081, reload=True)
