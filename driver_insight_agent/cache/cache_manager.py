"""Cache management for Driver Insight Agent."""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from ..config import get_config
from ..services.logger import get_logger


class CacheInterface(ABC):
    """Abstract interface for cache implementations."""
    
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
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass


class MemoryCache(CacheInterface):
    """In-memory cache implementation with TTL support."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 600):
        """Initialize memory cache.
        
        Args:
            max_size: Maximum number of items to store
            default_ttl: Default TTL in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_order: List[str] = []  # For LRU eviction
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0,
        }
        self.logger = get_logger()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        if key not in self.cache:
            self.stats['misses'] += 1
            self.logger.log_cache_operation('get', key, hit=False)
            return None
        
        entry = self.cache[key]
        
        # Check if expired
        if entry['expires_at'] and time.time() > entry['expires_at']:
            await self.delete(key)
            self.stats['misses'] += 1
            self.logger.log_cache_operation('get', key, hit=False, reason='expired')
            return None
        
        # Update access order for LRU
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)
        
        self.stats['hits'] += 1
        self.logger.log_cache_operation('get', key, hit=True)
        return entry['value']
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in memory cache."""
        try:
            # Calculate expiration time
            expires_at = None
            if ttl is not None:
                expires_at = time.time() + ttl
            elif self.default_ttl > 0:
                expires_at = time.time() + self.default_ttl
            
            # Evict if at max capacity and key doesn't exist
            if len(self.cache) >= self.max_size and key not in self.cache:
                await self._evict_lru()
            
            # Store the entry
            self.cache[key] = {
                'value': value,
                'expires_at': expires_at,
                'created_at': time.time(),
            }
            
            # Update access order
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
            
            self.stats['sets'] += 1
            self.logger.log_cache_operation('set', key, ttl=ttl)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set cache key {key}", error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from memory cache."""
        if key in self.cache:
            del self.cache[key]
            if key in self.access_order:
                self.access_order.remove(key)
            self.stats['deletes'] += 1
            self.logger.log_cache_operation('delete', key)
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in memory cache."""
        if key not in self.cache:
            return False
        
        entry = self.cache[key]
        if entry['expires_at'] and time.time() > entry['expires_at']:
            await self.delete(key)
            return False
        
        return True
    
    async def clear(self) -> bool:
        """Clear all entries from memory cache."""
        self.cache.clear()
        self.access_order.clear()
        self.logger.log_cache_operation('clear', 'all')
        return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory cache statistics."""
        return {
            **self.stats,
            'size': len(self.cache),
            'max_size': self.max_size,
            'hit_rate': self.stats['hits'] / (self.stats['hits'] + self.stats['misses']) 
                       if (self.stats['hits'] + self.stats['misses']) > 0 else 0,
        }
    
    async def _evict_lru(self):
        """Evict least recently used item."""
        if self.access_order:
            lru_key = self.access_order[0]
            await self.delete(lru_key)
            self.stats['evictions'] += 1
            self.logger.log_cache_operation('evict', lru_key, reason='lru')


class RedisCache(CacheInterface):
    """Redis cache implementation."""
    
    def __init__(self, redis_url: str, default_ttl: int = 600):
        """Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds
        """
        if not REDIS_AVAILABLE:
            raise ImportError("Redis is not available. Install with: pip install redis")
        
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.redis_client: Optional[redis.Redis] = None
        self.logger = get_logger()
    
    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self.redis_client is None:
            self.redis_client = redis.from_url(self.redis_url)
        return self.redis_client
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        try:
            client = await self._get_client()
            value = await client.get(key)
            
            if value is None:
                self.logger.log_cache_operation('get', key, hit=False)
                return None
            
            # Deserialize JSON
            deserialized = json.loads(value.decode('utf-8'))
            self.logger.log_cache_operation('get', key, hit=True)
            return deserialized
            
        except Exception as e:
            self.logger.error(f"Failed to get cache key {key}", error=str(e))
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache."""
        try:
            client = await self._get_client()
            
            # Serialize to JSON
            serialized = json.dumps(value, default=str)
            
            # Use provided TTL or default
            cache_ttl = ttl if ttl is not None else self.default_ttl
            
            if cache_ttl > 0:
                await client.setex(key, cache_ttl, serialized)
            else:
                await client.set(key, serialized)
            
            self.logger.log_cache_operation('set', key, ttl=cache_ttl)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set cache key {key}", error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from Redis cache."""
        try:
            client = await self._get_client()
            result = await client.delete(key)
            
            self.logger.log_cache_operation('delete', key)
            return result > 0
            
        except Exception as e:
            self.logger.error(f"Failed to delete cache key {key}", error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache."""
        try:
            client = await self._get_client()
            result = await client.exists(key)
            return result > 0
            
        except Exception as e:
            self.logger.error(f"Failed to check cache key {key}", error=str(e))
            return False
    
    async def clear(self) -> bool:
        """Clear all entries from Redis cache."""
        try:
            client = await self._get_client()
            await client.flushdb()
            
            self.logger.log_cache_operation('clear', 'all')
            return True
            
        except Exception as e:
            self.logger.error("Failed to clear cache", error=str(e))
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        try:
            client = await self._get_client()
            info = await client.info('memory')
            
            return {
                'type': 'redis',
                'memory_used': info.get('used_memory', 0),
                'memory_used_human': info.get('used_memory_human', '0B'),
                'connected_clients': info.get('connected_clients', 0),
            }
            
        except Exception as e:
            self.logger.error("Failed to get cache stats", error=str(e))
            return {'type': 'redis', 'error': str(e)}
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None


class CacheManager:
    """Main cache manager that handles different cache implementations."""
    
    def __init__(self):
        """Initialize cache manager."""
        self.cache: Optional[CacheInterface] = None
        self.logger = get_logger()
        self._initialize_cache()
    
    def _initialize_cache(self):
        """Initialize cache based on configuration."""
        try:
            config = get_config()
            cache_config = config.cache
        except RuntimeError:
            # Fallback configuration
            cache_config = type('CacheConfig', (), {
                'type': 'memory',
                'ttl': 600,
                'max_size': 1000,
                'redis_url': 'redis://localhost:6379/0'
            })()
        
        if cache_config.type.lower() == 'redis' and REDIS_AVAILABLE:
            self.cache = RedisCache(cache_config.redis_url, cache_config.ttl)
            self.logger.info("Initialized Redis cache")
        else:
            if cache_config.type.lower() == 'redis' and not REDIS_AVAILABLE:
                self.logger.warning("Redis requested but not available, falling back to memory cache")
            
            self.cache = MemoryCache(
                max_size=getattr(cache_config, 'max_size', 1000),
                default_ttl=cache_config.ttl
            )
            self.logger.info("Initialized memory cache")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if self.cache is None:
            return None
        return await self.cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        if self.cache is None:
            return False
        return await self.cache.set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if self.cache is None:
            return False
        return await self.cache.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if self.cache is None:
            return False
        return await self.cache.exists(key)
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        if self.cache is None:
            return False
        return await self.cache.clear()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self.cache is None:
            return {'type': 'none', 'enabled': False}
        
        stats = await self.cache.get_stats()
        stats['enabled'] = True
        return stats
    
    def generate_cache_key(self, prefix: str, *args: Union[str, int]) -> str:
        """Generate a consistent cache key.
        
        Args:
            prefix: Key prefix (e.g., 'driver', 'batch')
            *args: Additional key components
            
        Returns:
            Generated cache key
        """
        key_parts = [prefix] + [str(arg) for arg in args]
        return ":".join(key_parts)
    
    async def close(self):
        """Close cache connections."""
        if isinstance(self.cache, RedisCache):
            await self.cache.close()


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance.
    
    Returns:
        CacheManager: The cache manager instance
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager