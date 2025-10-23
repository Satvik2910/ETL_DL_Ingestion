from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI

from config.loader import AppConfig, load_config
from services.logger import configure_logger, get_logger
from cache.manager import create_cache_manager
from mcp_tools.invoker import MCPInvoker
from services.agent import DriverInsightAgent
from routes.health import router as health_router
from routes.drivers import router as drivers_router


CONFIG_PATH = "/workspace/config/config.yaml"


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logger()
    log = get_logger("app")
    log.info("app.starting")

    # Load config
    config: AppConfig = load_config(CONFIG_PATH)
    app.state.config = config

    # Shared async HTTP client
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
    app.state.http_client = http_client

    # Cache manager
    cache = create_cache_manager(ttl_seconds=config.cache_ttl)
    app.state.cache = cache

    # MCP invoker
    invoker = MCPInvoker(base_url=config.mcp_tool_server_url, http_client=http_client)

    # Agent orchestrator
    agent = DriverInsightAgent(
        config=config,
        cache=cache,
        mcp_invoker=invoker,
        http_client=http_client,
    )
    app.state.agent = agent

    try:
        yield
    finally:
        await http_client.aclose()
        await cache.close()
        log.info("app.stopped")


app = FastAPI(title="Driver Insight Agent", lifespan=lifespan)
app.include_router(health_router)
app.include_router(drivers_router)
