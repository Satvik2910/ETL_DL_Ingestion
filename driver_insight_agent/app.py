"""Main FastAPI application for Driver Insight Agent."""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from .config import load_config, get_config
from .driver_insight_agent import get_driver_insight_agent
from .routes import driver_router, health_router
from .services import get_logger


# Global variables for graceful shutdown
shutdown_event = asyncio.Event()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    logger = get_logger()
    
    # Startup
    try:
        logger.info("Starting Driver Insight Agent service")
        
        # Load configuration
        config = load_config()
        logger.info(f"Configuration loaded successfully")
        
        # Initialize the agent
        agent = get_driver_insight_agent()
        await agent.initialize()
        logger.info("Driver Insight Agent initialized successfully")
        
        # Store agent in app state
        app.state.agent = agent
        
        logger.info("Driver Insight Agent service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start service: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    try:
        logger.info("Shutting down Driver Insight Agent service")
        
        # Close the agent and clean up resources
        if hasattr(app.state, 'agent'):
            await app.state.agent.close()
        
        logger.info("Driver Insight Agent service shut down successfully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    # Create FastAPI app with lifespan
    app = FastAPI(
        title="Driver Insight Agent",
        description="""
        A modular agent service for fetching and managing driver data efficiently from external APIs.
        
        ## Features
        
        * **Single & Batch Operations**: Fetch individual drivers or multiple drivers in batch
        * **Smart Caching**: Configurable caching layer with TTL support (memory or Redis)
        * **Data Validation**: Comprehensive validation of driver data with detailed error reporting
        * **MCP Tool Integration**: Leverages Model Context Protocol tools for enhanced processing
        * **Graceful Error Handling**: Robust error handling with fallback mechanisms
        * **Health Monitoring**: Comprehensive health checks for all system components
        
        ## MCP Tool Integration
        
        The service integrates with an external MCP Tool Server that provides:
        - **FetchTool**: Enhanced data retrieval with advanced filtering
        - **ValidateTool**: Advanced validation with custom rules
        - **CacheTool**: Distributed caching operations
        - **SummarizeTool**: Data summarization and analytics
        
        ## Configuration
        
        The service can be configured via environment variables or YAML configuration file.
        See the documentation for detailed configuration options.
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # Add middleware
    setup_middleware(app)
    
    # Add routes
    app.include_router(health_router)
    app.include_router(driver_router)
    
    # Add exception handlers
    setup_exception_handlers(app)
    
    return app


def setup_middleware(app: FastAPI):
    """Setup middleware for the FastAPI application."""
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Trusted host middleware (configure for production)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure appropriately for production
    )


def setup_exception_handlers(app: FastAPI):
    """Setup global exception handlers."""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        logger = get_logger()
        logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "timestamp": "2025-10-23T09:10:00Z"
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger = get_logger()
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "status_code": 500,
                "timestamp": "2025-10-23T09:10:00Z"
            }
        )


# Create the app instance
app = create_app()


# Add root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Driver Insight Agent",
        "version": "1.0.0",
        "description": "A modular agent for fetching and managing driver data efficiently",
        "docs": "/docs",
        "health": "/health",
        "status": "/status"
    }


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger = get_logger()
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def run_server():
    """Run the FastAPI server with uvicorn."""
    try:
        # Load configuration
        config = load_config()
        server_config = config.server
        
        # Setup signal handlers
        setup_signal_handlers()
        
        # Configure uvicorn
        uvicorn_config = uvicorn.Config(
            app=app,
            host=server_config.host,
            port=server_config.port,
            log_level="info",
            access_log=True,
            workers=server_config.workers if server_config.workers > 1 else None,
            reload=server_config.debug,
            reload_dirs=["driver_insight_agent"] if server_config.debug else None,
        )
        
        server = uvicorn.Server(uvicorn_config)
        
        # Run server
        logger = get_logger()
        logger.info(f"Starting server on {server_config.host}:{server_config.port}")
        
        if server_config.workers > 1:
            logger.info(f"Running with {server_config.workers} workers")
        
        # Run the server
        server.run()
        
    except KeyboardInterrupt:
        logger = get_logger()
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger = get_logger()
        logger.error(f"Server startup failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    run_server()