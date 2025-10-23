"""FastAPI routes for health checks and system status."""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..driver_insight_agent import get_driver_insight_agent
from ..services import get_logger


# Response models
class ComponentHealth(BaseModel):
    """Health status for a single component."""
    status: str = Field(..., description="Component status (healthy, unhealthy, degraded)")
    timestamp: float = Field(..., description="Timestamp of health check")
    response_time: float = Field(default=0.0, description="Response time in seconds")
    error: str = Field(default="", description="Error message if unhealthy")


class HealthResponse(BaseModel):
    """Overall health check response."""
    overall: ComponentHealth = Field(..., description="Overall system health")
    agent: ComponentHealth = Field(..., description="Agent health")
    api: ComponentHealth = Field(..., description="External API health")
    cache: ComponentHealth = Field(..., description="Cache system health")
    mcp_tools: ComponentHealth = Field(..., description="MCP Tools health")


class StatusResponse(BaseModel):
    """System status response."""
    service: str = Field(default="Driver Insight Agent", description="Service name")
    version: str = Field(default="1.0.0", description="Service version")
    status: str = Field(..., description="Service status")
    uptime: str = Field(..., description="Service uptime")
    timestamp: str = Field(..., description="Current timestamp")


# Create router
router = APIRouter(tags=["health"])
logger = get_logger()

# Track service start time for uptime calculation
import time
SERVICE_START_TIME = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Comprehensive health check for all system components.
    
    Checks the health of:
    - Driver Insight Agent
    - External Driver API
    - Cache system (memory/Redis)
    - MCP Tool Server
    
    Returns detailed status for each component and overall system health.
    """
    try:
        agent = get_driver_insight_agent()
        health_results = await agent.health_check()
        
        # Convert to response model format
        def convert_health_data(health_data: Dict[str, Any]) -> ComponentHealth:
            return ComponentHealth(
                status=health_data.get("status", "unknown"),
                timestamp=health_data.get("timestamp", time.time()),
                response_time=health_data.get("response_time", 0.0),
                error=health_data.get("error", "")
            )
        
        response = HealthResponse(
            overall=convert_health_data(health_results.get("overall", {})),
            agent=convert_health_data(health_results.get("agent", {})),
            api=convert_health_data(health_results.get("api", {})),
            cache=convert_health_data(health_results.get("cache", {})),
            mcp_tools=convert_health_data(health_results.get("mcp_tools", {}))
        )
        
        # Log health check result
        overall_status = response.overall.status
        logger.info(f"Health check completed: {overall_status}")
        
        # Return appropriate HTTP status based on overall health
        if overall_status == "unhealthy":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=response.dict()
            )
        elif overall_status == "degraded":
            # Return 200 but log warning
            logger.warning("System is in degraded state")
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "overall": {
                    "status": "unhealthy",
                    "error": f"Health check failed: {str(e)}",
                    "timestamp": time.time()
                }
            }
        )


@router.get("/health/simple")
async def simple_health_check():
    """
    Simple health check endpoint.
    
    Returns basic status without checking external dependencies.
    Useful for load balancer health checks.
    """
    try:
        # Basic agent initialization check
        agent = get_driver_insight_agent()
        
        return {
            "status": "healthy",
            "service": "Driver Insight Agent",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Simple health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """
    Get service status and basic information.
    
    Returns service metadata including version, uptime, and current status.
    """
    try:
        current_time = time.time()
        uptime_seconds = current_time - SERVICE_START_TIME
        
        # Format uptime
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # Get basic health status
        try:
            agent = get_driver_insight_agent()
            health_results = await agent.health_check()
            service_status = health_results.get("overall", {}).get("status", "unknown")
        except Exception:
            service_status = "degraded"
        
        return StatusResponse(
            service="Driver Insight Agent",
            version="1.0.0",
            status=service_status,
            uptime=uptime_str,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get service status: {str(e)}"
        )


@router.get("/ready")
async def readiness_check():
    """
    Readiness check endpoint.
    
    Indicates whether the service is ready to handle requests.
    Checks that all critical dependencies are available.
    """
    try:
        agent = get_driver_insight_agent()
        
        # Initialize the agent to ensure it's ready
        await agent.initialize()
        
        # Check critical dependencies
        health_results = await agent.health_check()
        
        # Service is ready if agent is healthy and at least one data source is available
        agent_healthy = health_results.get("agent", {}).get("status") == "healthy"
        api_available = health_results.get("api", {}).get("status") == "healthy"
        mcp_available = health_results.get("mcp_tools", {}).get("status") == "healthy"
        
        if agent_healthy and (api_available or mcp_available):
            return {
                "ready": True,
                "status": "ready",
                "timestamp": datetime.utcnow().isoformat(),
                "dependencies": {
                    "agent": agent_healthy,
                    "api": api_available,
                    "mcp_tools": mcp_available
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "ready": False,
                    "status": "not_ready",
                    "reason": "Critical dependencies unavailable",
                    "timestamp": datetime.utcnow().isoformat(),
                    "dependencies": {
                        "agent": agent_healthy,
                        "api": api_available,
                        "mcp_tools": mcp_available
                    }
                }
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "ready": False,
                "status": "not_ready",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/live")
async def liveness_check():
    """
    Liveness check endpoint.
    
    Indicates whether the service is alive and running.
    This is a lightweight check that doesn't verify external dependencies.
    """
    try:
        # Just check that the service is running
        return {
            "alive": True,
            "status": "alive",
            "service": "Driver Insight Agent",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": time.time() - SERVICE_START_TIME
        }
        
    except Exception as e:
        logger.error(f"Liveness check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "alive": False,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )