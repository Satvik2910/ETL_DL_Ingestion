"""FastAPI routes for driver operations."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..driver_insight_agent import get_driver_insight_agent, DriverInsightAgentError
from ..services import get_logger


# Request/Response models
class DriverBatchRequest(BaseModel):
    """Request model for batch driver fetch."""
    driver_ids: List[str] = Field(..., description="List of driver IDs to fetch", min_items=1, max_items=100)
    use_cache: bool = Field(default=True, description="Whether to use caching")
    use_mcp_tools: bool = Field(default=True, description="Whether to use MCP tools for enhanced processing")


class DriverSummaryRequest(BaseModel):
    """Request model for driver summary."""
    driver_ids: List[str] = Field(..., description="List of driver IDs to summarize", min_items=1, max_items=50)


class ValidationResult(BaseModel):
    """Validation result model."""
    is_valid: bool = Field(..., description="Whether the data is valid")
    errors: List[str] = Field(default=[], description="List of validation errors")
    warnings: List[str] = Field(default=[], description="List of validation warnings")


class DriverMetadata(BaseModel):
    """Driver metadata model."""
    source: str = Field(..., description="Data source (api, cache)")
    cached: bool = Field(..., description="Whether data was retrieved from cache")
    processed_with_mcp: bool = Field(..., description="Whether MCP tools were used")
    timestamp: float = Field(..., description="Timestamp when data was processed")


class DriverResponse(BaseModel):
    """Response model for single driver."""
    driver_id: str = Field(..., description="Driver ID")
    data: dict = Field(..., description="Driver data")
    validation: ValidationResult = Field(..., description="Validation results")
    metadata: DriverMetadata = Field(..., description="Processing metadata")


class DriverBatchResponse(BaseModel):
    """Response model for batch driver fetch."""
    drivers: List[DriverResponse] = Field(..., description="List of driver responses")
    total_count: int = Field(..., description="Total number of drivers processed")
    valid_count: int = Field(..., description="Number of valid drivers")
    cached_count: int = Field(..., description="Number of drivers retrieved from cache")


class DriverSummaryResponse(BaseModel):
    """Response model for driver summary."""
    summary: dict = Field(..., description="Summary data")
    total_requested: int = Field(..., description="Total number of drivers requested")
    valid_drivers: int = Field(..., description="Number of valid drivers")
    invalid_drivers: int = Field(..., description="Number of invalid drivers")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    status: str = Field(default="error", description="Status indicator")
    timestamp: str = Field(..., description="Error timestamp")


# Create router
router = APIRouter(prefix="/drivers", tags=["drivers"])
logger = get_logger()


@router.get("/{driver_id}", response_model=DriverResponse)
async def get_driver(
    driver_id: str,
    use_cache: bool = Query(default=True, description="Whether to use caching"),
    use_mcp_tools: bool = Query(default=True, description="Whether to use MCP tools")
):
    """
    Fetch single driver information.
    
    - **driver_id**: Driver ID to fetch
    - **use_cache**: Whether to use caching (default: true)
    - **use_mcp_tools**: Whether to use MCP tools for enhanced processing (default: true)
    
    Returns driver data with validation results and metadata.
    """
    try:
        agent = get_driver_insight_agent()
        result = await agent.fetch_driver(driver_id, use_cache, use_mcp_tools)
        
        logger.info(f"Successfully fetched driver: {driver_id}")
        
        return DriverResponse(
            driver_id=result["driver_id"],
            data=result["data"],
            validation=ValidationResult(**result["validation"]),
            metadata=DriverMetadata(**result["metadata"])
        )
        
    except DriverInsightAgentError as e:
        logger.error(f"Agent error fetching driver {driver_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch driver: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching driver {driver_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/batch", response_model=DriverBatchResponse)
async def get_drivers_batch(request: DriverBatchRequest):
    """
    Fetch multiple drivers in batch.
    
    Request body should contain:
    - **driver_ids**: List of driver IDs to fetch (1-100 items)
    - **use_cache**: Whether to use caching (optional, default: true)
    - **use_mcp_tools**: Whether to use MCP tools (optional, default: true)
    
    Returns list of driver data with validation results and metadata.
    """
    try:
        agent = get_driver_insight_agent()
        results = await agent.fetch_drivers_batch(
            request.driver_ids, 
            request.use_cache, 
            request.use_mcp_tools
        )
        
        # Calculate statistics
        total_count = len(results)
        valid_count = sum(1 for r in results if r["validation"]["is_valid"])
        cached_count = sum(1 for r in results if r["metadata"]["cached"])
        
        logger.info(f"Successfully fetched batch: {total_count} drivers ({valid_count} valid, {cached_count} cached)")
        
        return DriverBatchResponse(
            drivers=[
                DriverResponse(
                    driver_id=result["driver_id"],
                    data=result["data"],
                    validation=ValidationResult(**result["validation"]),
                    metadata=DriverMetadata(**result["metadata"])
                )
                for result in results
            ],
            total_count=total_count,
            valid_count=valid_count,
            cached_count=cached_count
        )
        
    except DriverInsightAgentError as e:
        logger.error(f"Agent error in batch fetch: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch driver batch: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in batch fetch: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/summary", response_model=DriverSummaryResponse)
async def get_drivers_summary(request: DriverSummaryRequest):
    """
    Get summary of multiple drivers.
    
    Request body should contain:
    - **driver_ids**: List of driver IDs to summarize (1-50 items)
    
    Returns aggregated summary data for the specified drivers.
    """
    try:
        agent = get_driver_insight_agent()
        summary_result = await agent.get_driver_summary(request.driver_ids)
        
        logger.info(f"Successfully generated summary for {len(request.driver_ids)} drivers")
        
        return DriverSummaryResponse(**summary_result)
        
    except DriverInsightAgentError as e:
        logger.error(f"Agent error generating summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to generate summary: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error generating summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics.
    
    Returns current cache statistics including hit rate, size, and configuration.
    """
    try:
        agent = get_driver_insight_agent()
        stats = await agent.get_cache_stats()
        
        logger.debug("Retrieved cache statistics")
        
        return {
            "cache_stats": stats,
            "timestamp": stats.get("timestamp", "unknown")
        }
        
    except Exception as e:
        logger.error(f"Error retrieving cache stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache statistics"
        )


@router.delete("/cache")
async def clear_cache():
    """
    Clear all cached data.
    
    Removes all cached driver data. Use with caution as this will impact performance
    until the cache is repopulated.
    """
    try:
        agent = get_driver_insight_agent()
        success = await agent.clear_cache()
        
        if success:
            logger.info("Cache cleared successfully")
            return {
                "message": "Cache cleared successfully",
                "status": "success",
                "timestamp": "2025-10-23T09:10:00Z"
            }
        else:
            logger.warning("Failed to clear cache")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to clear cache"
            )
        
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )


# Error handlers
@router.exception_handler(DriverInsightAgentError)
async def driver_agent_exception_handler(request, exc: DriverInsightAgentError):
    """Handle DriverInsightAgentError exceptions."""
    logger.error(f"Driver agent error: {str(exc)}")
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(exc)
    )


@router.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    """Handle ValueError exceptions."""
    logger.error(f"Value error: {str(exc)}")
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid input: {str(exc)}"
    )