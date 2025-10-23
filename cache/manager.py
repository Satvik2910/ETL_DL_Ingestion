from __future__ import annotations

import os
from typing import Optional

from redis.asyncio import Redis

from .base import AsyncCache
from .memory import InMemoryCache
from .redis_cache import RedisCache


def create_cache_manager(ttl_seconds: int) -> AsyncCache:
    redis_url: Optional[str] = os.getenv("REDIS_URL")
    if redis_url:
        client = Redis.from_url(redis_url, decode_responses=False)
        return RedisCache(client=client, default_ttl_seconds=ttl_seconds)
    return InMemoryCache(default_ttl_seconds=ttl_seconds)
