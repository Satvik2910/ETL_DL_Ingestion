"""Cache management system with TTL and persistent storage capabilities."""

import json
import hashlib
import time
import pickle
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import asyncio
import threading
from pathlib import Path


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0
    tags: List[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.tags is None:
            self.tags = []
        if self.last_accessed is None:
            self.last_accessed = self.created_at


@dataclass
class CacheStats:
    """Cache statistics."""
    total_entries: int
    total_size_bytes: int
    hit_count: int
    miss_count: int
    eviction_count: int
    hit_rate: float
    memory_usage_mb: float


class CacheKeyGenerator:
    """Utility for generating consistent cache keys."""
    
    @staticmethod
    def generate_key(prefix: str, *args, **kwargs) -> str:
        """Generate a consistent cache key from arguments."""
        # Create a deterministic string from arguments
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            if isinstance(arg, (dict, list)):
                key_parts.append(json.dumps(arg, sort_keys=True, separators=(',', ':')))
            else:
                key_parts.append(str(arg))
        
        # Add keyword arguments
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            for key, value in sorted_kwargs:
                if isinstance(value, (dict, list)):
                    key_parts.append(f"{key}={json.dumps(value, sort_keys=True, separators=(',', ':'))}")
                else:
                    key_parts.append(f"{key}={value}")
        
        # Create hash of the combined key
        combined_key = "|".join(key_parts)
        return hashlib.sha256(combined_key.encode()).hexdigest()[:16]
    
    @staticmethod
    def generate_request_key(request_data: Dict[str, Any]) -> str:
        """Generate cache key for agent requests."""
        # Extract key components from request
        drivers = request_data.get('drivers', [])
        time_range = request_data.get('time_range', {})
        report_type = request_data.get('report_type', '')
        filters = request_data.get('filters', [])
        aggregations = request_data.get('aggregations', [])
        
        return CacheKeyGenerator.generate_key(
            'request',
            drivers=drivers,
            time_range=time_range,
            report_type=report_type,
            filters=filters,
            aggregations=aggregations
        )


class InMemoryCache:
    """In-memory cache with TTL support."""
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        """Initialize in-memory cache."""
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = CacheStats(0, 0, 0, 0, 0, 0.0, 0.0)
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats.miss_count += 1
                self._update_hit_rate()
                return None
            
            # Check if expired
            if entry.expires_at and datetime.now() > entry.expires_at:
                del self._cache[key]
                self._stats.miss_count += 1
                self._update_hit_rate()
                return None
            
            # Update access statistics
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            self._stats.hit_count += 1
            self._update_hit_rate()
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, tags: Optional[List[str]] = None) -> bool:
        """Set value in cache."""
        with self._lock:
            # Calculate expiration
            expires_at = None
            if ttl is not None:
                expires_at = datetime.now() + timedelta(seconds=ttl)
            elif self.default_ttl > 0:
                expires_at = datetime.now() + timedelta(seconds=self.default_ttl)
            
            # Calculate size
            size_bytes = self._estimate_size(value)
            
            # Check if we need to evict entries
            if len(self._cache) >= self.max_size:
                self._evict_entries()
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                expires_at=expires_at,
                size_bytes=size_bytes,
                tags=tags or []
            )
            
            self._cache[key] = entry
            self._update_stats()
            
            return True
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._update_stats()
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._update_stats()
    
    def clear_by_tags(self, tags: List[str]) -> int:
        """Clear entries with specific tags."""
        with self._lock:
            keys_to_delete = []
            
            for key, entry in self._cache.items():
                if any(tag in entry.tags for tag in tags):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self._cache[key]
            
            self._update_stats()
            return len(keys_to_delete)
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            return self._stats
    
    def _evict_entries(self) -> None:
        """Evict entries using LRU strategy."""
        if not self._cache:
            return
        
        # Sort by last accessed time (oldest first)
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].last_accessed or x[1].created_at
        )
        
        # Remove oldest 10% of entries
        evict_count = max(1, len(sorted_entries) // 10)
        
        for i in range(evict_count):
            key, _ = sorted_entries[i]
            del self._cache[key]
            self._stats.eviction_count += 1
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of value."""
        try:
            return len(pickle.dumps(value))
        except:
            return len(str(value).encode('utf-8'))
    
    def _update_stats(self) -> None:
        """Update cache statistics."""
        self._stats.total_entries = len(self._cache)
        self._stats.total_size_bytes = sum(entry.size_bytes for entry in self._cache.values())
        self._stats.memory_usage_mb = self._stats.total_size_bytes / (1024 * 1024)
    
    def _update_hit_rate(self) -> None:
        """Update hit rate calculation."""
        total_requests = self._stats.hit_count + self._stats.miss_count
        if total_requests > 0:
            self._stats.hit_rate = self._stats.hit_count / total_requests
        else:
            self._stats.hit_rate = 0.0


class PersistentCache:
    """Persistent cache using file system."""
    
    def __init__(self, cache_dir: str = "./cache_data", max_size_mb: int = 1000):
        """Initialize persistent cache."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_size_mb = max_size_mb
        self.metadata_file = self.cache_dir / "metadata.json"
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._load_metadata()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from persistent cache."""
        if key not in self._metadata:
            return None
        
        entry_meta = self._metadata[key]
        
        # Check if expired
        if entry_meta.get('expires_at'):
            expires_at = datetime.fromisoformat(entry_meta['expires_at'])
            if datetime.now() > expires_at:
                self.delete(key)
                return None
        
        # Load data from file
        try:
            file_path = self.cache_dir / f"{key}.pkl"
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    value = pickle.load(f)
                
                # Update access statistics
                entry_meta['access_count'] = entry_meta.get('access_count', 0) + 1
                entry_meta['last_accessed'] = datetime.now().isoformat()
                self._save_metadata()
                
                return value
        except Exception:
            # Clean up corrupted entry
            self.delete(key)
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, tags: Optional[List[str]] = None) -> bool:
        """Set value in persistent cache."""
        try:
            # Calculate expiration
            expires_at = None
            if ttl is not None:
                expires_at = (datetime.now() + timedelta(seconds=ttl)).isoformat()
            
            # Save data to file
            file_path = self.cache_dir / f"{key}.pkl"
            with open(file_path, 'wb') as f:
                pickle.dump(value, f)
            
            # Update metadata
            self._metadata[key] = {
                'created_at': datetime.now().isoformat(),
                'expires_at': expires_at,
                'access_count': 0,
                'last_accessed': datetime.now().isoformat(),
                'size_bytes': file_path.stat().st_size,
                'tags': tags or []
            }
            
            self._save_metadata()
            self._cleanup_if_needed()
            
            return True
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """Delete entry from persistent cache."""
        try:
            if key in self._metadata:
                del self._metadata[key]
                self._save_metadata()
            
            file_path = self.cache_dir / f"{key}.pkl"
            if file_path.exists():
                file_path.unlink()
            
            return True
        except Exception:
            return False
    
    def clear(self) -> None:
        """Clear all persistent cache entries."""
        try:
            for file_path in self.cache_dir.glob("*.pkl"):
                file_path.unlink()
            
            self._metadata.clear()
            self._save_metadata()
        except Exception:
            pass
    
    def clear_by_tags(self, tags: List[str]) -> int:
        """Clear entries with specific tags."""
        keys_to_delete = []
        
        for key, meta in self._metadata.items():
            entry_tags = meta.get('tags', [])
            if any(tag in entry_tags for tag in tags):
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            self.delete(key)
        
        return len(keys_to_delete)
    
    def _load_metadata(self) -> None:
        """Load metadata from file."""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    self._metadata = json.load(f)
        except Exception:
            self._metadata = {}
    
    def _save_metadata(self) -> None:
        """Save metadata to file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self._metadata, f, indent=2)
        except Exception:
            pass
    
    def _cleanup_if_needed(self) -> None:
        """Clean up cache if size exceeds limit."""
        total_size = sum(meta.get('size_bytes', 0) for meta in self._metadata.values())
        max_size_bytes = self.max_size_mb * 1024 * 1024
        
        if total_size > max_size_bytes:
            # Sort by last accessed (oldest first)
            sorted_entries = sorted(
                self._metadata.items(),
                key=lambda x: x[1].get('last_accessed', x[1].get('created_at', ''))
            )
            
            # Remove oldest entries until under limit
            for key, meta in sorted_entries:
                if total_size <= max_size_bytes * 0.8:  # Leave some buffer
                    break
                
                self.delete(key)
                total_size -= meta.get('size_bytes', 0)


class HybridCacheManager:
    """Hybrid cache manager combining in-memory and persistent caching."""
    
    def __init__(self, 
                 memory_cache_size: int = 1000,
                 persistent_cache_size_mb: int = 1000,
                 default_ttl: int = 3600,
                 cache_dir: str = "./cache_data"):
        """Initialize hybrid cache manager."""
        self.memory_cache = InMemoryCache(memory_cache_size, default_ttl)
        self.persistent_cache = PersistentCache(cache_dir, persistent_cache_size_mb)
        self.default_ttl = default_ttl
        self.key_generator = CacheKeyGenerator()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (memory first, then persistent)."""
        # Try memory cache first
        value = self.memory_cache.get(key)
        if value is not None:
            return value
        
        # Try persistent cache
        value = self.persistent_cache.get(key)
        if value is not None:
            # Promote to memory cache
            self.memory_cache.set(key, value, ttl=self.default_ttl)
            return value
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, 
                 tags: Optional[List[str]] = None, persistent: bool = True) -> bool:
        """Set value in cache."""
        # Always set in memory cache
        memory_success = self.memory_cache.set(key, value, ttl, tags)
        
        # Optionally set in persistent cache
        persistent_success = True
        if persistent:
            persistent_success = self.persistent_cache.set(key, value, ttl, tags)
        
        return memory_success and persistent_success
    
    async def delete(self, key: str) -> bool:
        """Delete from both caches."""
        memory_result = self.memory_cache.delete(key)
        persistent_result = self.persistent_cache.delete(key)
        return memory_result or persistent_result
    
    async def clear(self) -> None:
        """Clear both caches."""
        self.memory_cache.clear()
        self.persistent_cache.clear()
    
    async def clear_by_tags(self, tags: List[str]) -> int:
        """Clear entries with specific tags from both caches."""
        memory_count = self.memory_cache.clear_by_tags(tags)
        persistent_count = self.persistent_cache.clear_by_tags(tags)
        return memory_count + persistent_count
    
    def get_stats(self) -> Dict[str, CacheStats]:
        """Get statistics from both caches."""
        return {
            'memory': self.memory_cache.get_stats(),
            'persistent': CacheStats(
                total_entries=len(self.persistent_cache._metadata),
                total_size_bytes=sum(meta.get('size_bytes', 0) 
                                   for meta in self.persistent_cache._metadata.values()),
                hit_count=0,  # Not tracked for persistent cache
                miss_count=0,
                eviction_count=0,
                hit_rate=0.0,
                memory_usage_mb=sum(meta.get('size_bytes', 0) 
                                  for meta in self.persistent_cache._metadata.values()) / (1024 * 1024)
            )
        }
    
    # Convenience methods for common caching patterns
    
    async def cache_request_result(self, request_data: Dict[str, Any], 
                                 result: Any, ttl: Optional[int] = None) -> str:
        """Cache a request result and return the cache key."""
        cache_key = self.key_generator.generate_request_key(request_data)
        await self.set(cache_key, result, ttl, tags=['request_result'])
        return cache_key
    
    async def get_cached_request_result(self, request_data: Dict[str, Any]) -> Optional[Any]:
        """Get cached request result."""
        cache_key = self.key_generator.generate_request_key(request_data)
        return await self.get(cache_key)
    
    async def cache_tool_result(self, tool_name: str, tool_args: Dict[str, Any], 
                              result: Any, ttl: Optional[int] = None) -> str:
        """Cache a tool result and return the cache key."""
        cache_key = self.key_generator.generate_key(f"tool_{tool_name}", **tool_args)
        await self.set(cache_key, result, ttl, tags=['tool_result', tool_name])
        return cache_key
    
    async def get_cached_tool_result(self, tool_name: str, tool_args: Dict[str, Any]) -> Optional[Any]:
        """Get cached tool result."""
        cache_key = self.key_generator.generate_key(f"tool_{tool_name}", **tool_args)
        return await self.get(cache_key)
    
    async def invalidate_driver_cache(self, driver_ids: List[str]) -> int:
        """Invalidate cache entries for specific drivers."""
        tags_to_clear = [f"driver_{driver_id}" for driver_id in driver_ids]
        return await self.clear_by_tags(tags_to_clear)
    
    async def invalidate_time_range_cache(self, start_date: str, end_date: str) -> int:
        """Invalidate cache entries for a specific time range."""
        # This is a simplified approach - in practice, you might need more sophisticated logic
        return await self.clear_by_tags(['time_sensitive'])


# Global cache manager instance
_cache_manager: Optional[HybridCacheManager] = None


def get_cache_manager() -> HybridCacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = HybridCacheManager()
    return _cache_manager


def initialize_cache_manager(config: Dict[str, Any]) -> HybridCacheManager:
    """Initialize cache manager with configuration."""
    global _cache_manager
    _cache_manager = HybridCacheManager(
        memory_cache_size=config.get('memory_cache_size', 1000),
        persistent_cache_size_mb=config.get('persistent_cache_size_mb', 1000),
        default_ttl=config.get('default_ttl', 3600),
        cache_dir=config.get('cache_dir', './cache_data')
    )
    return _cache_manager