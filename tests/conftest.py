"""
Pytest configuration and fixtures.
"""

import pytest
from unittest.mock import Mock

from cache.cache_manager import CacheManager, InMemoryCacheBackend
from services.api_client import APIClient
from services.driver_insight_agent import DriverInsightAgent
from services.validator import Validator
from mcp_tools.mcp_invoker import MCPInvoker


@pytest.fixture
def mock_cache_backend():
    """Provide a mock cache backend."""
    return InMemoryCacheBackend()


@pytest.fixture
def cache_manager(mock_cache_backend):
    """Provide a cache manager with in-memory backend."""
    return CacheManager(backend=mock_cache_backend)


@pytest.fixture
def validator():
    """Provide a validator instance."""
    return Validator(required_fields=["driver_id", "name"])


@pytest.fixture
def api_client():
    """Provide an API client instance."""
    return APIClient()


@pytest.fixture
def mcp_invoker():
    """Provide an MCP invoker instance."""
    return MCPInvoker()


@pytest.fixture
def driver_insight_agent(api_client, validator, cache_manager, mcp_invoker):
    """Provide a fully configured DriverInsightAgent."""
    return DriverInsightAgent(
        api_client=api_client,
        validator=validator,
        cache_manager=cache_manager,
        mcp_invoker=mcp_invoker,
    )


@pytest.fixture
def sample_driver_data():
    """Provide sample driver data for testing."""
    return {
        "driver_id": "D12345",
        "name": "John Doe",
        "vehicle": "Tesla Model Y",
        "rating": 4.8,
    }


@pytest.fixture
def sample_drivers_batch():
    """Provide sample batch driver data."""
    return [
        {"driver_id": "D1", "name": "Driver 1", "rating": 4.5},
        {"driver_id": "D2", "name": "Driver 2", "rating": 4.7},
        {"driver_id": "D3", "name": "Driver 3", "rating": 4.9},
    ]
