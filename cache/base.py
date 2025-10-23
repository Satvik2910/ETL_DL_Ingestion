from __future__ import annotations

import abc
from typing import Any, Optional


class AsyncCache(abc.ABC):
    @abc.abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    @abc.abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def close(self) -> None:
        raise NotImplementedError
