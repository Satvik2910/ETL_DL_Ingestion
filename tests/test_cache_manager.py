"""
Tests for the CacheManager module.
"""

import pytest

from cache.cache_manager import CacheManager, InMemoryCacheBackend


class TestInMemoryCacheBackend:
    """Test suite for InMemoryCacheBackend."""

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test basic set and get operations."""
        backend = InMemoryCacheBackend()
        await backend.set("key1", "value1")
        value = await backend.get("key1")
        assert value == "value1"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self):
        """Test getting non-existent key."""
        backend = InMemoryCacheBackend()
        value = await backend.get("nonexistent")
        assert value is None

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test delete operation."""
        backend = InMemoryCacheBackend()
        await backend.set("key1", "value1")
        result = await backend.delete("key1")
        assert result is True
        value = await backend.get("key1")
        assert value is None

    @pytest.mark.asyncio
    async def test_exists(self):
        """Test exists check."""
        backend = InMemoryCacheBackend()
        await backend.set("key1", "value1")
        assert await backend.exists("key1") is True
        assert await backend.exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clear all entries."""
        backend = InMemoryCacheBackend()
        await backend.set("key1", "value1")
        await backend.set("key2", "value2")
        await backend.clear()
        assert await backend.get("key1") is None
        assert await backend.get("key2") is None

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test TTL expiration."""
        backend = InMemoryCacheBackend()
        await backend.set("key1", "value1", ttl=1)
        
        # Should exist immediately
        value = await backend.get("key1")
        assert value == "value1"
        
        # Wait for expiration
        import asyncio
        await asyncio.sleep(1.1)
        
        # Should be expired
        value = await backend.get("key1")
        assert value is None


class TestCacheManager:
    """Test suite for CacheManager."""

    @pytest.mark.asyncio
    async def test_cache_manager_initialization(self):
        """Test cache manager initializes correctly."""
        backend = InMemoryCacheBackend()
        manager = CacheManager(backend=backend)
        assert manager is not None
        assert manager.enabled is True

    @pytest.mark.asyncio
    async def test_generate_key(self):
        """Test cache key generation."""
        manager = CacheManager(backend=InMemoryCacheBackend())
        key = manager.generate_key("driver", "D12345")
        assert key == "driver:D12345"
        
        key = manager.generate_key("driver", "D12345", "profile")
        assert key == "driver:D12345:profile"

    @pytest.mark.asyncio
    async def test_cache_operations(self):
        """Test full cache operation flow."""
        manager = CacheManager(backend=InMemoryCacheBackend())
        
        # Set value
        result = await manager.set("test_key", {"data": "value"})
        assert result is True
        
        # Get value
        value = await manager.get("test_key")
        assert value == {"data": "value"}
        
        # Check exists
        exists = await manager.exists("test_key")
        assert exists is True
        
        # Delete value
        deleted = await manager.delete("test_key")
        assert deleted is True
        
        # Verify deleted
        value = await manager.get("test_key")
        assert value is None
