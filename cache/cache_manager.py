"""
Cache manager for Driver Insight Agent.
Supports both in-memory and Redis caching with configurable TTL.
"""

import json
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

from config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries."""
        pass


class InMemoryCacheBackend(CacheBackend):
    """
    In-memory cache backend using a dictionary.
    Suitable for single-instance deployments and testing.
    """

    def __init__(self):
        """Initialize in-memory cache."""
        self._cache: dict[str, tuple[Any, Optional[float]]] = {}
        logger.info("Initialized in-memory cache backend")

    def _is_expired(self, expiry: Optional[float]) -> bool:
        """Check if a cache entry has expired."""
        if expiry is None:
            return False
        return time.time() > expiry

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self._cache:
            logger.debug(f"Cache miss for key: {key}")
            return None

        value, expiry = self._cache[key]

        # Check expiration
        if self._is_expired(expiry):
            logger.debug(f"Cache entry expired for key: {key}")
            await self.delete(key)
            return None

        logger.debug(f"Cache hit for key: {key}")
        return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        try:
            expiry = time.time() + ttl if ttl else None
            self._cache[key] = (value, expiry)
            logger.debug(f"Cache set for key: {key}", extra={"ttl": ttl})
            return True
        except Exception as e:
            logger.error(f"Failed to set cache for key: {key}", extra={"error": str(e)})
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache deleted for key: {key}")
            return True
        return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if key not in self._cache:
            return False

        _, expiry = self._cache[key]
        if self._is_expired(expiry):
            await self.delete(key)
            return False

        return True

    async def clear(self) -> bool:
        """Clear all cache entries."""
        self._cache.clear()
        logger.info("Cleared in-memory cache")
        return True


class RedisCacheBackend(CacheBackend):
    """
    Redis cache backend for distributed caching.
    Requires redis-py library.
    """

    def __init__(self):
        """Initialize Redis cache backend."""
        try:
            import redis.asyncio as redis
        except ImportError:
            raise ImportError(
                "redis package is required for Redis cache backend. "
                "Install it with: pip install redis"
            )

        config = get_config()
        redis_config = config.cache.redis

        self.redis = redis.Redis(
            host=redis_config.host,
            port=redis_config.port,
            db=redis_config.db,
            password=redis_config.password,
            decode_responses=True,
        )
        logger.info("Initialized Redis cache backend", extra={
            "host": redis_config.host,
            "port": redis_config.port,
            "db": redis_config.db,
        })

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = await self.redis.get(key)
            if value is None:
                logger.debug(f"Cache miss for key: {key}")
                return None

            logger.debug(f"Cache hit for key: {key}")
            return json.loads(value)
        except Exception as e:
            logger.error(f"Failed to get cache for key: {key}", extra={"error": str(e)})
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        try:
            serialized_value = json.dumps(value)
            if ttl:
                await self.redis.setex(key, ttl, serialized_value)
            else:
                await self.redis.set(key, serialized_value)

            logger.debug(f"Cache set for key: {key}", extra={"ttl": ttl})
            return True
        except Exception as e:
            logger.error(f"Failed to set cache for key: {key}", extra={"error": str(e)})
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            result = await self.redis.delete(key)
            logger.debug(f"Cache deleted for key: {key}")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete cache for key: {key}", extra={"error": str(e)})
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check cache existence for key: {key}", extra={"error": str(e)})
            return False

    async def clear(self) -> bool:
        """Clear all cache entries."""
        try:
            await self.redis.flushdb()
            logger.info("Cleared Redis cache")
            return True
        except Exception as e:
            logger.error("Failed to clear Redis cache", extra={"error": str(e)})
            return False


class CacheManager:
    """
    High-level cache manager that abstracts cache backend implementation.
    """

    def __init__(self, backend: Optional[CacheBackend] = None):
        """
        Initialize cache manager.

        Args:
            backend: Cache backend to use. If None, will be created based on config.
        """
        config = get_config()
        self.config = config.cache
        self.enabled = self.config.enabled
        self.default_ttl = self.config.ttl

        if backend:
            self.backend = backend
        else:
            self.backend = self._create_backend()

        logger.info("Cache manager initialized", extra={
            "enabled": self.enabled,
            "type": self.config.type,
            "default_ttl": self.default_ttl,
        })

    def _create_backend(self) -> CacheBackend:
        """Create cache backend based on configuration."""
        if self.config.type == "redis":
            return RedisCacheBackend()
        else:
            return InMemoryCacheBackend()

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found or cache disabled.
        """
        if not self.enabled:
            return None

        return await self.backend.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time to live in seconds. Uses default if not specified.

        Returns:
            True if successful, False otherwise.
        """
        if not self.enabled:
            return False

        ttl = ttl if ttl is not None else self.default_ttl
        return await self.backend.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key.

        Returns:
            True if successful, False otherwise.
        """
        if not self.enabled:
            return False

        return await self.backend.delete(key)

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key.

        Returns:
            True if exists, False otherwise.
        """
        if not self.enabled:
            return False

        return await self.backend.exists(key)

    async def clear(self) -> bool:
        """
        Clear all cache entries.

        Returns:
            True if successful, False otherwise.
        """
        if not self.enabled:
            return False

        return await self.backend.clear()

    def generate_key(self, prefix: str, *parts: str) -> str:
        """
        Generate a cache key from parts.

        Args:
            prefix: Key prefix.
            *parts: Additional key parts.

        Returns:
            Generated cache key.
        """
        return f"{prefix}:{':'.join(str(p) for p in parts)}"
