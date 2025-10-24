from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Protocol

from loguru import logger


class Tool(Protocol):
    name: str
    version: str

    async def run(self, **kwargs: Any) -> Any:  # pragma: no cover - interface
        ...


@dataclass(frozen=True)
class ToolInfo:
    name: str
    version: str
    description: str


class MCPRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}
        self._descriptions: Dict[str, str] = {}

    def register(self, tool: Tool, description: str) -> None:
        logger.debug("Registering tool {} {}", tool.name, tool.version)
        self._tools[tool.name] = tool
        self._descriptions[tool.name] = description

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Tool not registered: {name}")
        return self._tools[name]

    def list(self) -> List[ToolInfo]:
        return [
            ToolInfo(name=t.name, version=t.version, description=self._descriptions.get(t.name, ""))
            for t in self._tools.values()
        ]

    async def run_with_retries(
        self,
        name: str,
        retries: int = 2,
        base_delay: float = 0.25,
        max_delay: float = 2.0,
        **kwargs: Any,
    ) -> Any:
        attempt = 0
        while True:
            try:
                tool = self.get(name)
                logger.debug("Running tool {} attempt {}", name, attempt + 1)
                return await tool.run(**kwargs)
            except Exception as exc:  # noqa: BLE001 - surface tool failures
                attempt += 1
                if attempt > retries:
                    logger.error("Tool {} failed after {} attempts: {}", name, attempt, exc)
                    raise
                delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                await asyncio.sleep(delay)


__all__ = ["MCPRegistry", "Tool", "ToolInfo"]
