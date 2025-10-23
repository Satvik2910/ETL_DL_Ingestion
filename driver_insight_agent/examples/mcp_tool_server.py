"""Example MCP Tool Server implementation for Driver Insight Agent.

This is a reference implementation of an MCP Tool Server that provides
the tools expected by the Driver Insight Agent. In a real deployment,
this would be a separate service.
"""

import asyncio
import json
import random
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


# Request/Response models
class ToolInvocationRequest(BaseModel):
    """Request model for tool invocation."""
    tool: str = Field(..., description="Name of the tool to invoke")
    parameters: Dict[str, Any] = Field(default={}, description="Tool parameters")


class ToolInvocationResponse(BaseModel):
    """Response model for tool invocation."""
    success: bool = Field(..., description="Whether the tool execution was successful")
    data: Optional[Any] = Field(default=None, description="Tool execution result data")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")
    execution_time: float = Field(..., description="Tool execution time in seconds")
    tool: str = Field(..., description="Name of the executed tool")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Health check timestamp")
    version: str = Field(default="1.0.0", description="Service version")
    available_tools: List[str] = Field(..., description="List of available tools")


# Create FastAPI app
app = FastAPI(
    title="MCP Tool Server",
    description="Example MCP Tool Server for Driver Insight Agent",
    version="1.0.0"
)

# In-memory cache for demonstration
cache_storage: Dict[str, Dict[str, Any]] = {}

# Mock external API client
external_api_client = httpx.AsyncClient(
    base_url="http://mock-driver-api:1080",  # Points to mock server in docker-compose
    timeout=10.0
)


class FetchTool:
    """Tool for fetching driver data from external APIs."""
    
    @staticmethod
    async def execute(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the fetch tool."""
        start_time = time.time()
        
        try:
            driver_id = parameters.get("driver_id")
            driver_ids = parameters.get("driver_ids")
            
            if driver_id:
                # Single driver fetch
                data = await FetchTool._fetch_single_driver(driver_id)
                return {
                    "success": True,
                    "data": data,
                    "execution_time": time.time() - start_time,
                    "tool": "FetchTool"
                }
            
            elif driver_ids:
                # Batch driver fetch
                data = await FetchTool._fetch_multiple_drivers(driver_ids)
                return {
                    "success": True,
                    "data": data,
                    "execution_time": time.time() - start_time,
                    "tool": "FetchTool"
                }
            
            else:
                return {
                    "success": False,
                    "error": "Either driver_id or driver_ids parameter is required",
                    "execution_time": time.time() - start_time,
                    "tool": "FetchTool"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Fetch operation failed: {str(e)}",
                "execution_time": time.time() - start_time,
                "tool": "FetchTool"
            }
    
    @staticmethod
    async def _fetch_single_driver(driver_id: str) -> Dict[str, Any]:
        """Fetch single driver data."""
        try:
            # Try external API first
            response = await external_api_client.get(f"/drivers/{driver_id}")
            if response.status_code == 200:
                return response.json()
        except:
            pass
        
        # Fallback to mock data
        return FetchTool._generate_mock_driver(driver_id)
    
    @staticmethod
    async def _fetch_multiple_drivers(driver_ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch multiple drivers data."""
        try:
            # Try external API batch endpoint
            response = await external_api_client.post("/drivers/batch", json={"driver_ids": driver_ids})
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list):
                    return result
                elif isinstance(result, dict) and "drivers" in result:
                    return result["drivers"]
        except:
            pass
        
        # Fallback to mock data
        return [FetchTool._generate_mock_driver(driver_id) for driver_id in driver_ids]
    
    @staticmethod
    def _generate_mock_driver(driver_id: str) -> Dict[str, Any]:
        """Generate mock driver data."""
        names = ["John Doe", "Jane Smith", "Mike Johnson", "Sarah Wilson", "David Brown"]
        vehicles = ["Tesla Model 3", "Toyota Prius", "Honda Civic", "BMW 3 Series", "Audi A4"]
        statuses = ["active", "inactive", "suspended"]
        
        # Use driver_id as seed for consistent data
        random.seed(hash(driver_id) % 2**32)
        
        return {
            "driver_id": driver_id,
            "name": random.choice(names),
            "vehicle": random.choice(vehicles),
            "rating": round(random.uniform(3.0, 5.0), 1),
            "status": random.choice(statuses),
            "location": {
                "lat": round(random.uniform(37.0, 38.0), 6),
                "lng": round(random.uniform(-122.5, -121.5), 6)
            },
            "total_trips": random.randint(50, 1000),
            "last_active": datetime.utcnow().isoformat()
        }


class ValidateTool:
    """Tool for validating driver data."""
    
    @staticmethod
    async def execute(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the validation tool."""
        start_time = time.time()
        
        try:
            data = parameters.get("data")
            validation_type = parameters.get("validation_type", "driver")
            
            if validation_type == "driver":
                result = ValidateTool._validate_single_driver(data)
            elif validation_type == "driver_batch":
                result = ValidateTool._validate_driver_batch(data)
            else:
                return {
                    "success": False,
                    "error": f"Unknown validation type: {validation_type}",
                    "execution_time": time.time() - start_time,
                    "tool": "ValidateTool"
                }
            
            return {
                "success": True,
                **result,
                "execution_time": time.time() - start_time,
                "tool": "ValidateTool"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Validation failed: {str(e)}",
                "execution_time": time.time() - start_time,
                "tool": "ValidateTool"
            }
    
    @staticmethod
    def _validate_single_driver(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate single driver data."""
        errors = []
        warnings = []
        
        # Required fields
        required_fields = ["driver_id", "name"]
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
            elif not data[field] or (isinstance(data[field], str) and not data[field].strip()):
                errors.append(f"Required field cannot be empty: {field}")
        
        # Optional field validation
        if "rating" in data:
            rating = data["rating"]
            if not isinstance(rating, (int, float)):
                errors.append("Rating must be a number")
            elif rating < 0 or rating > 5:
                errors.append("Rating must be between 0 and 5")
        
        if "status" in data:
            status = data["status"]
            if status not in ["active", "inactive", "suspended", "pending"]:
                warnings.append(f"Unusual status value: {status}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "validated_count": 1
        }
    
    @staticmethod
    def _validate_driver_batch(data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate batch of driver data."""
        if not isinstance(data, list):
            return {
                "is_valid": False,
                "errors": ["Data must be a list for batch validation"],
                "warnings": [],
                "validated_count": 0
            }
        
        all_errors = []
        all_warnings = []
        valid_count = 0
        
        for i, driver_data in enumerate(data):
            result = ValidateTool._validate_single_driver(driver_data)
            if result["is_valid"]:
                valid_count += 1
            else:
                for error in result["errors"]:
                    all_errors.append(f"Driver {i}: {error}")
            
            for warning in result["warnings"]:
                all_warnings.append(f"Driver {i}: {warning}")
        
        return {
            "is_valid": len(all_errors) == 0,
            "errors": all_errors,
            "warnings": all_warnings,
            "validated_count": len(data),
            "valid_count": valid_count
        }


class CacheTool:
    """Tool for cache operations."""
    
    @staticmethod
    async def execute(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the cache tool."""
        start_time = time.time()
        
        try:
            operation = parameters.get("operation")
            key = parameters.get("key")
            
            if operation == "get":
                result = CacheTool._cache_get(key)
            elif operation == "set":
                value = parameters.get("value")
                ttl = parameters.get("ttl")
                result = CacheTool._cache_set(key, value, ttl)
            elif operation == "delete":
                result = CacheTool._cache_delete(key)
            elif operation == "exists":
                result = CacheTool._cache_exists(key)
            elif operation == "clear":
                result = CacheTool._cache_clear()
            else:
                return {
                    "success": False,
                    "error": f"Unknown cache operation: {operation}",
                    "execution_time": time.time() - start_time,
                    "tool": "CacheTool"
                }
            
            return {
                "success": True,
                **result,
                "execution_time": time.time() - start_time,
                "tool": "CacheTool"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Cache operation failed: {str(e)}",
                "execution_time": time.time() - start_time,
                "tool": "CacheTool"
            }
    
    @staticmethod
    def _cache_get(key: str) -> Dict[str, Any]:
        """Get value from cache."""
        if key in cache_storage:
            entry = cache_storage[key]
            # Check TTL
            if entry.get("expires_at") and time.time() > entry["expires_at"]:
                del cache_storage[key]
                return {"data": None}
            return {"data": entry["value"]}
        return {"data": None}
    
    @staticmethod
    def _cache_set(key: str, value: Any, ttl: Optional[int] = None) -> Dict[str, Any]:
        """Set value in cache."""
        expires_at = None
        if ttl and ttl > 0:
            expires_at = time.time() + ttl
        
        cache_storage[key] = {
            "value": value,
            "expires_at": expires_at,
            "created_at": time.time()
        }
        return {"success": True}
    
    @staticmethod
    def _cache_delete(key: str) -> Dict[str, Any]:
        """Delete value from cache."""
        if key in cache_storage:
            del cache_storage[key]
            return {"success": True}
        return {"success": False}
    
    @staticmethod
    def _cache_exists(key: str) -> Dict[str, Any]:
        """Check if key exists in cache."""
        exists = key in cache_storage
        if exists:
            entry = cache_storage[key]
            # Check TTL
            if entry.get("expires_at") and time.time() > entry["expires_at"]:
                del cache_storage[key]
                exists = False
        return {"exists": exists}
    
    @staticmethod
    def _cache_clear() -> Dict[str, Any]:
        """Clear all cache entries."""
        cache_storage.clear()
        return {"success": True}


class SummarizeTool:
    """Tool for summarizing driver data."""
    
    @staticmethod
    async def execute(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the summarize tool."""
        start_time = time.time()
        
        try:
            data = parameters.get("data")
            summary_type = parameters.get("summary_type", "driver_summary")
            
            if summary_type == "driver_summary":
                result = SummarizeTool._summarize_single_driver(data)
            elif summary_type == "driver_batch_summary":
                result = SummarizeTool._summarize_driver_batch(data)
            elif summary_type == "driver_stats":
                result = SummarizeTool._generate_driver_stats(data)
            else:
                return {
                    "success": False,
                    "error": f"Unknown summary type: {summary_type}",
                    "execution_time": time.time() - start_time,
                    "tool": "SummarizeTool"
                }
            
            return {
                "success": True,
                "summary": result,
                "execution_time": time.time() - start_time,
                "tool": "SummarizeTool"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Summarization failed: {str(e)}",
                "execution_time": time.time() - start_time,
                "tool": "SummarizeTool"
            }
    
    @staticmethod
    def _summarize_single_driver(data: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize single driver data."""
        return {
            "driver_id": data.get("driver_id", "unknown"),
            "name": data.get("name", "unknown"),
            "status": data.get("status", "unknown"),
            "rating": data.get("rating", 0),
            "summary_type": "single_driver"
        }
    
    @staticmethod
    def _summarize_driver_batch(data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize batch of drivers."""
        if not isinstance(data, list) or len(data) == 0:
            return {
                "total_drivers": 0,
                "summary_type": "batch_summary"
            }
        
        total_drivers = len(data)
        active_drivers = sum(1 for d in data if d.get("status") == "active")
        total_rating = sum(d.get("rating", 0) for d in data if d.get("rating"))
        avg_rating = total_rating / total_drivers if total_drivers > 0 else 0
        
        return {
            "total_drivers": total_drivers,
            "active_drivers": active_drivers,
            "inactive_drivers": total_drivers - active_drivers,
            "average_rating": round(avg_rating, 2),
            "summary_type": "batch_summary"
        }
    
    @staticmethod
    def _generate_driver_stats(data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate detailed statistics for drivers."""
        if not isinstance(data, list) or len(data) == 0:
            return {
                "total_drivers": 0,
                "summary_type": "driver_stats"
            }
        
        # Calculate various statistics
        ratings = [d.get("rating", 0) for d in data if d.get("rating")]
        statuses = [d.get("status", "unknown") for d in data]
        vehicles = [d.get("vehicle", "unknown") for d in data if d.get("vehicle")]
        
        status_counts = {}
        for status in statuses:
            status_counts[status] = status_counts.get(status, 0) + 1
        
        vehicle_counts = {}
        for vehicle in vehicles:
            vehicle_counts[vehicle] = vehicle_counts.get(vehicle, 0) + 1
        
        return {
            "total_drivers": len(data),
            "rating_stats": {
                "average": round(sum(ratings) / len(ratings), 2) if ratings else 0,
                "min": min(ratings) if ratings else 0,
                "max": max(ratings) if ratings else 0,
                "count": len(ratings)
            },
            "status_distribution": status_counts,
            "top_vehicles": dict(sorted(vehicle_counts.items(), key=lambda x: x[1], reverse=True)[:5]),
            "summary_type": "driver_stats"
        }


# Tool registry
TOOLS = {
    "FetchTool": FetchTool,
    "ValidateTool": ValidateTool,
    "CacheTool": CacheTool,
    "SummarizeTool": SummarizeTool,
}


# API Routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "MCP Tool Server",
        "version": "1.0.0",
        "description": "Example MCP Tool Server for Driver Insight Agent"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        available_tools=list(TOOLS.keys())
    )


@app.get("/tools")
async def list_tools():
    """List available tools."""
    return {
        "tools": list(TOOLS.keys()),
        "count": len(TOOLS)
    }


@app.post("/invoke", response_model=ToolInvocationResponse)
async def invoke_tool(request: ToolInvocationRequest):
    """Invoke a specific tool."""
    tool_name = request.tool
    
    if tool_name not in TOOLS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_name}' not found. Available tools: {list(TOOLS.keys())}"
        )
    
    try:
        tool_class = TOOLS[tool_name]
        result = await tool_class.execute(request.parameters)
        
        return ToolInvocationResponse(**result)
    
    except Exception as e:
        return ToolInvocationResponse(
            success=False,
            error=f"Tool execution failed: {str(e)}",
            execution_time=0.0,
            tool=tool_name
        )


if __name__ == "__main__":
    uvicorn.run(
        "mcp_tool_server:app",
        host="0.0.0.0",
        port=8081,
        reload=True,
        log_level="info"
    )