from __future__ import annotations

from typing import Any, Optional

from redis.asyncio import Redis

from .base import AsyncCache


class RedisCache(AsyncCache):
    def __init__(self, client: Redis, default_ttl_seconds: int = 600) -> None:
        self._client = client
        self._default_ttl = max(0, int(default_ttl_seconds))

    async def get(self, key: str) -> Optional[Any]:
        data = await self._client.get(key)
        if data is None:
            return None
        # Redis returns bytes; store JSON strings for simplicity
        if isinstance(data, bytes):
            return data.decode("utf-8")
        return data

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        ttl = self._default_ttl if ttl_seconds is None else max(0, int(ttl_seconds))
        await self._client.set(name=key, value=value, ex=ttl if ttl > 0 else None)

    async def close(self) -> None:
        await self._client.aclose()
