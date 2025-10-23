"""Routes package for Driver Insight Agent FastAPI application."""

from .driver_routes import router as driver_router
from .health_routes import router as health_router

__all__ = [
    "driver_router",
    "health_router",
]