"""
Driver Insight Agent - Main FastAPI Application
"""

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_config
from routes import driver_routes
from services.driver_insight_agent import DriverInsightAgent
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Global agent instance
agent: DriverInsightAgent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for application startup and shutdown.
    """
    global agent

    # Startup
    logger.info("Starting Driver Insight Agent service")
    config = get_config()

    try:
        # Initialize agent
        agent = DriverInsightAgent()
        driver_routes.set_agent(agent)

        logger.info("Driver Insight Agent service started successfully", extra={
            "version": config.service.version,
            "port": config.service.port,
        })

        yield

    except Exception as e:
        logger.error("Failed to start service", extra={"error": str(e)}, exc_info=True)
        sys.exit(1)

    finally:
        # Shutdown
        logger.info("Shutting down Driver Insight Agent service")

        if agent:
            await agent.close()

        logger.info("Driver Insight Agent service stopped")


# Create FastAPI app
config = get_config()
app = FastAPI(
    title=config.service.name,
    version=config.service.version,
    description="A modular agent for fetching and managing driver data efficiently",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint.

    Returns:
        Health status of the service and its components.
    """
    logger.debug("Health check requested")

    try:
        health = await agent.health_check()
        return JSONResponse(
            status_code=200 if health["status"] == "healthy" else 503,
            content=health,
        )
    except Exception as e:
        logger.error("Health check failed", extra={"error": str(e)}, exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
            },
        )


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint with service information.

    Returns:
        Service information.
    """
    return {
        "service": config.service.name,
        "version": config.service.version,
        "description": "Driver Insight Agent - A modular agent for driver data management",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "drivers": "/drivers",
        },
    }


# Include routers
app.include_router(driver_routes.router)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(
        "Unhandled exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc),
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status": "error",
            "path": request.url.path,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=config.service.host,
        port=config.service.port,
        reload=False,
        log_level=config.logging.level.lower(),
    )
