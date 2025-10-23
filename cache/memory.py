from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from .base import AsyncCache


class InMemoryCache(AsyncCache):
    def __init__(self, default_ttl_seconds: int = 600) -> None:
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()
        self._default_ttl = max(0, int(default_ttl_seconds))

    async def get(self, key: str) -> Optional[Any]:
        now = time.time()
        async with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            expires_at, value = item
            if expires_at and expires_at < now:
                # expired
                self._data.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        ttl = self._default_ttl if ttl_seconds is None else max(0, int(ttl_seconds))
        expires_at = 0.0 if ttl == 0 else time.time() + ttl
        async with self._lock:
            self._data[key] = (expires_at, value)

    async def close(self) -> None:
        async with self._lock:
            self._data.clear()
