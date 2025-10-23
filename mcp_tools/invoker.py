from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

import httpx

from services.logger import get_logger


class MCPInvoker:
    def __init__(self, base_url: str, http_client: httpx.AsyncClient) -> None:
        self._base_url = base_url.rstrip("/")
        self._http = http_client
        self._log = get_logger("mcp.invoker")

    async def invoke(self, tool_name: str, payload: Dict[str, Any], *, retries: int = 2) -> Optional[Dict[str, Any]]:
        url = f"{self._base_url}/{tool_name}"
        last_exc: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                resp = await self._http.post(url, json=payload)
                if resp.status_code >= 500:
                    raise httpx.HTTPStatusError("server error", request=resp.request, response=resp)
                resp.raise_for_status()
                data = resp.json()
                self._log.info("mcp.invoke.success", tool=tool_name, status=resp.status_code)
                return data
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                self._log.warning(
                    "mcp.invoke.error",
                    tool=tool_name,
                    attempt=attempt,
                    error=str(exc),
                )
                await asyncio.sleep(min(0.5 * (2 ** attempt), 2.0))
        self._log.error("mcp.invoke.failed", tool=tool_name, error=str(last_exc) if last_exc else None)
        return None
