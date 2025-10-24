from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import aiosqlite
from cachetools import TTLCache


@dataclass
class CacheKey:
    namespace: str
    key: str

    def composite(self) -> str:
        return f"{self.namespace}:{self.key}"


class CacheManager:
    def __init__(self, namespace: str, ttl_seconds: int, persistent_path: str) -> None:
        self.namespace = namespace
        self.ttl_seconds = ttl_seconds
        self.persistent_path = persistent_path
        self._mem_cache: TTLCache[str, Tuple[float, Any]] = TTLCache(maxsize=10240, ttl=ttl_seconds)
        self._db_initialized = False
        self._db_lock = asyncio.Lock()

    @staticmethod
    def _hash_key(obj: Any) -> str:
        raw = json.dumps(obj, sort_keys=True, separators=(",", ":"))
        return hashlib.sha1(raw.encode()).hexdigest()

    def key_for(self, request_like: Any) -> CacheKey:
        return CacheKey(namespace=self.namespace, key=self._hash_key(request_like))

    async def _ensure_db(self) -> None:
        if self._db_initialized:
            return
        async with self._db_lock:
            if self._db_initialized:
                return
            Path(os.path.dirname(self.persistent_path)).mkdir(parents=True, exist_ok=True)
            async with aiosqlite.connect(self.persistent_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cache (
                        ns TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value BLOB NOT NULL,
                        expires_at REAL NOT NULL,
                        PRIMARY KEY (ns, key)
                    )
                    """
                )
                await db.commit()
            self._db_initialized = True

    async def get(self, key: CacheKey) -> Optional[Any]:
        # memory first
        now = time.time()
        mem_entry = self._mem_cache.get(key.composite())
        if mem_entry is not None:
            expires_at, value = mem_entry
            if expires_at > now:
                return value
            else:
                # stale in mem
                self._mem_cache.pop(key.composite(), None)

        await self._ensure_db()
        async with aiosqlite.connect(self.persistent_path) as db:
            async with db.execute(
                "SELECT value, expires_at FROM cache WHERE ns=? AND key=?", (key.namespace, key.key)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                raw, expires_at = row
                if expires_at <= now:
                    # purge stale
                    await db.execute("DELETE FROM cache WHERE ns=? AND key=?", (key.namespace, key.key))
                    await db.commit()
                    return None
                value = json.loads(raw)
                self._mem_cache[key.composite()] = (expires_at, value)
                return value

    async def set(self, key: CacheKey, value: Any, ttl: Optional[int] = None) -> None:
        expires_at = time.time() + float(ttl or self.ttl_seconds)
        self._mem_cache[key.composite()] = (expires_at, value)
        await self._ensure_db()
        async with aiosqlite.connect(self.persistent_path) as db:
            await db.execute(
                "REPLACE INTO cache(ns, key, value, expires_at) VALUES(?, ?, ?, ?)",
                (key.namespace, key.key, json.dumps(value, separators=(",", ":")), expires_at),
            )
            await db.commit()

    async def clear_namespace(self, namespace: Optional[str] = None) -> None:
        ns = namespace or self.namespace
        self._mem_cache.clear()
        await self._ensure_db()
        async with aiosqlite.connect(self.persistent_path) as db:
            await db.execute("DELETE FROM cache WHERE ns=?", (ns,))
            await db.commit()


__all__ = ["CacheManager", "CacheKey"]
