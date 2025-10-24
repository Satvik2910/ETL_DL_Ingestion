"""
Cache manager with TTL caching and persistent storage support.
"""
import time
import json
import os
import hashlib
from typing import Any, Dict, Optional
from pathlib import Path
from cachetools import TTLCache
from threading import Lock


class CacheManager:
    """Manages TTL-based caching with optional persistent storage."""
    
    def __init__(
        self,
        ttl_seconds: int = 3600,
        max_size: int = 1000,
        enable_persistent: bool = False,
        persistent_path: str = "./cache_storage"
    ):
        """
        Initialize cache manager.
        
        Args:
            ttl_seconds: Time-to-live for cached items in seconds
            max_size: Maximum number of items in cache
            enable_persistent: Enable persistent caching to disk
            persistent_path: Path for persistent cache storage
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.enable_persistent = enable_persistent
        self.persistent_path = Path(persistent_path)
        
        # In-memory TTL cache
        self._cache = TTLCache(maxsize=max_size, ttl=ttl_seconds)
        self._lock = Lock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        
        # Create persistent storage directory
        if self.enable_persistent:
            self.persistent_path.mkdir(parents=True, exist_ok=True)
    
    def _generate_key(self, key_data: Any) -> str:
        """
        Generate deterministic cache key from data.
        
        Args:
            key_data: Data to generate key from
            
        Returns:
            SHA256 hash as cache key
        """
        # Convert to JSON string for hashing
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def _get_persistent_path(self, cache_key: str) -> Path:
        """Get file path for persistent cache entry."""
        return self.persistent_path / f"{cache_key}.json"
    
    def _load_from_persistent(self, cache_key: str) -> Optional[Any]:
        """Load cached data from persistent storage."""
        if not self.enable_persistent:
            return None
        
        cache_file = self._get_persistent_path(cache_key)
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
            
            # Check if expired
            expiry = cached_data.get('expiry')
            if expiry and time.time() > expiry:
                # Remove expired cache
                cache_file.unlink()
                return None
            
            return cached_data.get('data')
        
        except (json.JSONDecodeError, IOError):
            return None
    
    def _save_to_persistent(self, cache_key: str, data: Any) -> None:
        """Save data to persistent storage."""
        if not self.enable_persistent:
            return
        
        cache_file = self._get_persistent_path(cache_key)
        cached_data = {
            'data': data,
            'timestamp': time.time(),
            'expiry': time.time() + self.ttl_seconds
        }
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(cached_data, f)
        except (IOError, TypeError):
            # Silently fail if data is not JSON serializable
            pass
    
    def get(self, key_data: Any) -> Optional[Any]:
        """
        Get cached data.
        
        Args:
            key_data: Key data to look up
            
        Returns:
            Cached data or None if not found/expired
        """
        cache_key = self._generate_key(key_data)
        
        with self._lock:
            # Try in-memory cache first
            if cache_key in self._cache:
                self._hits += 1
                return self._cache[cache_key]
            
            # Try persistent cache
            persistent_data = self._load_from_persistent(cache_key)
            if persistent_data is not None:
                # Load into in-memory cache
                self._cache[cache_key] = persistent_data
                self._hits += 1
                return persistent_data
            
            self._misses += 1
            return None
    
    def set(self, key_data: Any, value: Any) -> None:
        """
        Set cached data.
        
        Args:
            key_data: Key data
            value: Value to cache
        """
        cache_key = self._generate_key(key_data)
        
        with self._lock:
            self._cache[cache_key] = value
            self._save_to_persistent(cache_key, value)
    
    def delete(self, key_data: Any) -> None:
        """
        Delete cached data.
        
        Args:
            key_data: Key data to delete
        """
        cache_key = self._generate_key(key_data)
        
        with self._lock:
            # Remove from memory cache
            if cache_key in self._cache:
                del self._cache[cache_key]
            
            # Remove from persistent cache
            if self.enable_persistent:
                cache_file = self._get_persistent_path(cache_key)
                if cache_file.exists():
                    cache_file.unlink()
    
    def clear(self) -> None:
        """Clear all cached data."""
        with self._lock:
            self._cache.clear()
            
            # Clear persistent cache
            if self.enable_persistent and self.persistent_path.exists():
                for cache_file in self.persistent_path.glob("*.json"):
                    cache_file.unlink()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'hits': self._hits,
                'misses': self._misses,
                'total_requests': total_requests,
                'hit_rate': hit_rate,
                'cache_size': len(self._cache),
                'max_size': self.max_size,
                'ttl_seconds': self.ttl_seconds
            }
    
    def reset_stats(self) -> None:
        """Reset cache statistics."""
        with self._lock:
            self._hits = 0
            self._misses = 0
    
    def contains(self, key_data: Any) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key_data: Key data to check
            
        Returns:
            True if key exists and not expired
        """
        return self.get(key_data) is not None
    
    def get_or_compute(
        self,
        key_data: Any,
        compute_fn: callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Get cached data or compute and cache if not found.
        
        Args:
            key_data: Key data
            compute_fn: Function to compute value if not cached
            *args: Arguments for compute function
            **kwargs: Keyword arguments for compute function
            
        Returns:
            Cached or newly computed value
        """
        cached_value = self.get(key_data)
        if cached_value is not None:
            return cached_value
        
        # Compute new value
        computed_value = compute_fn(*args, **kwargs)
        self.set(key_data, computed_value)
        
        return computed_value
    
    async def get_or_compute_async(
        self,
        key_data: Any,
        compute_fn: callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Async version of get_or_compute.
        
        Args:
            key_data: Key data
            compute_fn: Async function to compute value if not cached
            *args: Arguments for compute function
            **kwargs: Keyword arguments for compute function
            
        Returns:
            Cached or newly computed value
        """
        cached_value = self.get(key_data)
        if cached_value is not None:
            return cached_value
        
        # Compute new value asynchronously
        computed_value = await compute_fn(*args, **kwargs)
        self.set(key_data, computed_value)
        
        return computed_value


class ResultCache:
    """Specialized cache for tool results with batch support."""
    
    def __init__(self, cache_manager: CacheManager):
        """
        Initialize result cache.
        
        Args:
            cache_manager: Underlying cache manager
        """
        self.cache_manager = cache_manager
    
    def cache_tool_result(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Any
    ) -> None:
        """Cache tool execution result."""
        key = {
            'tool': tool_name,
            'params': parameters
        }
        self.cache_manager.set(key, result)
    
    def get_tool_result(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Optional[Any]:
        """Get cached tool result."""
        key = {
            'tool': tool_name,
            'params': parameters
        }
        return self.cache_manager.get(key)
    
    def cache_batch_result(
        self,
        batch_id: str,
        result: Any
    ) -> None:
        """Cache batch processing result."""
        key = {'batch': batch_id}
        self.cache_manager.set(key, result)
    
    def get_batch_result(
        self,
        batch_id: str
    ) -> Optional[Any]:
        """Get cached batch result."""
        key = {'batch': batch_id}
        return self.cache_manager.get(key)
