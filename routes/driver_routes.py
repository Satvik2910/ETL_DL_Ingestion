"""
FastAPI routes for driver-related endpoints.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from services.api_client import APIError
from services.driver_insight_agent import DriverInsightAgent
from services.validator import ValidationError
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/drivers", tags=["drivers"])

# Global agent instance (will be set by app initialization)
agent: Optional[DriverInsightAgent] = None


def set_agent(driver_agent: DriverInsightAgent):
    """Set the global agent instance."""
    global agent
    agent = driver_agent


# Response Models
class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    status: str = "error"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    details: Optional[dict] = None


class DriverResponse(BaseModel):
    """Single driver response model."""
    driver_id: str
    name: str
    vehicle: Optional[str] = None
    rating: Optional[float] = None


class BatchDriverRequest(BaseModel):
    """Batch driver request model."""
    driver_ids: List[str] = Field(..., min_items=1, max_items=100)
    use_cache: bool = Field(default=True)
    use_mcp: bool = Field(default=False)


class BatchDriverResponse(BaseModel):
    """Batch driver response model."""
    total_requested: int
    successful: int
    failed: int
    drivers: List[dict]
    errors: List[dict]
    validation: dict


class AllDriversResponse(BaseModel):
    """All drivers response model."""
    total: int
    drivers: List[dict]
    validation: dict


class SummaryResponse(BaseModel):
    """Driver summary response model."""
    total_drivers: int
    summary: dict


@router.get("/{driver_id}", response_model=dict, responses={
    200: {"description": "Driver information retrieved successfully"},
    404: {"description": "Driver not found", "model": ErrorResponse},
    503: {"description": "Service unavailable", "model": ErrorResponse},
})
async def get_driver(
    driver_id: str,
    use_cache: bool = Query(default=True, description="Use cache for retrieval"),
    use_mcp: bool = Query(default=False, description="Use MCP tools for fetching"),
):
    """
    Get driver information by ID.

    Args:
        driver_id: Driver ID.
        use_cache: Whether to use cache.
        use_mcp: Whether to use MCP tools.

    Returns:
        Driver information dictionary.
    """
    try:
        logger.info(f"GET /drivers/{driver_id}", extra={
            "driver_id": driver_id,
            "use_cache": use_cache,
            "use_mcp": use_mcp,
        })

        driver_data = await agent.get_driver(
            driver_id=driver_id,
            use_cache=use_cache,
            use_mcp=use_mcp,
        )

        return driver_data

    except APIError as e:
        logger.error(f"API error fetching driver", extra={
            "driver_id": driver_id,
            "error": str(e),
            "status_code": e.status_code,
        })

        if e.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error=f"Driver not found: {driver_id}",
                    status="not_found",
                ).dict(),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=ErrorResponse(
                    error="Driver API unavailable",
                    status="retrying",
                    details={"driver_id": driver_id, "reason": str(e)},
                ).dict(),
            )

    except ValidationError as e:
        logger.error(f"Validation error for driver", extra={
            "driver_id": driver_id,
            "error": str(e),
        })

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ErrorResponse(
                error="Driver data validation failed",
                status="validation_error",
                details={"missing_fields": e.missing_fields},
            ).dict(),
        )

    except Exception as e:
        logger.error(f"Unexpected error fetching driver", extra={
            "driver_id": driver_id,
            "error": str(e),
        }, exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="Internal server error",
                status="error",
                details={"driver_id": driver_id},
            ).dict(),
        )


@router.post("/batch", response_model=BatchDriverResponse, responses={
    200: {"description": "Batch driver information retrieved"},
    503: {"description": "Service unavailable", "model": ErrorResponse},
})
async def get_drivers_batch(request: BatchDriverRequest):
    """
    Get multiple driver records in batch.

    Args:
        request: Batch request containing driver IDs and options.

    Returns:
        Batch result with drivers and errors.
    """
    try:
        logger.info(f"POST /drivers/batch", extra={
            "count": len(request.driver_ids),
            "use_cache": request.use_cache,
            "use_mcp": request.use_mcp,
        })

        result = await agent.get_drivers_batch(
            driver_ids=request.driver_ids,
            use_cache=request.use_cache,
            use_mcp=request.use_mcp,
        )

        return BatchDriverResponse(**result)

    except Exception as e:
        logger.error(f"Unexpected error in batch fetch", extra={
            "error": str(e),
        }, exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="Batch fetch failed",
                status="error",
                details={"reason": str(e)},
            ).dict(),
        )


@router.get("/", response_model=AllDriversResponse, responses={
    200: {"description": "All drivers retrieved"},
    503: {"description": "Service unavailable", "model": ErrorResponse},
})
async def get_all_drivers(
    limit: Optional[int] = Query(default=None, description="Maximum number of drivers to return"),
    use_cache: bool = Query(default=True, description="Use cache for retrieval"),
    use_mcp: bool = Query(default=False, description="Use MCP tools for fetching"),
):
    """
    Get all drivers with pagination.

    Args:
        limit: Maximum number of drivers to return.
        use_cache: Whether to use cache.
        use_mcp: Whether to use MCP tools.

    Returns:
        All drivers with validation results.
    """
    try:
        logger.info(f"GET /drivers", extra={
            "limit": limit,
            "use_cache": use_cache,
            "use_mcp": use_mcp,
        })

        result = await agent.get_all_drivers(
            limit=limit,
            use_cache=use_cache,
            use_mcp=use_mcp,
        )

        return AllDriversResponse(**result)

    except APIError as e:
        logger.error(f"API error fetching all drivers", extra={
            "error": str(e),
        })

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error="Driver API unavailable",
                status="retrying",
                details={"reason": str(e)},
            ).dict(),
        )

    except Exception as e:
        logger.error(f"Unexpected error fetching all drivers", extra={
            "error": str(e),
        }, exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="Failed to fetch all drivers",
                status="error",
            ).dict(),
        )


@router.post("/summary", response_model=SummaryResponse)
async def get_drivers_summary(
    driver_ids: Optional[List[str]] = None,
    use_mcp: bool = Query(default=True, description="Use MCP SummarizeTool"),
):
    """
    Get a summary of driver data.

    Args:
        driver_ids: Optional list of driver IDs to summarize. If None, summarizes all.
        use_mcp: Whether to use MCP tools for summarization.

    Returns:
        Driver summary statistics.
    """
    try:
        logger.info(f"POST /drivers/summary", extra={
            "driver_ids": driver_ids,
            "use_mcp": use_mcp,
        })

        # Fetch drivers
        if driver_ids:
            result = await agent.get_drivers_batch(driver_ids=driver_ids)
            drivers = result["drivers"]
        else:
            result = await agent.get_all_drivers()
            drivers = result["drivers"]

        # Generate summary
        summary = await agent.summarize_drivers(drivers=drivers, use_mcp=use_mcp)

        return SummaryResponse(
            total_drivers=len(drivers),
            summary=summary,
        )

    except Exception as e:
        logger.error(f"Unexpected error generating summary", extra={
            "error": str(e),
        }, exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="Failed to generate summary",
                status="error",
            ).dict(),
        )
