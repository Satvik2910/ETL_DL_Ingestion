from __future__ import annotations

import asyncio
from typing import Any, Dict, Iterable, List, Optional

import httpx

from config.loader import AppConfig
from services.logger import get_logger


class APIClient:
    def __init__(self, config: AppConfig, http_client: httpx.AsyncClient) -> None:
        self._config = config
        self._http = http_client
        self._log = get_logger("api.client")

    async def fetch_driver(self, driver_id: str) -> Optional[Dict[str, Any]]:
        url = f"{self._config.api_base_url}/drivers/{driver_id}"
        return await self._request_with_retries(url)

    async def fetch_drivers_batch(self, driver_ids: Iterable[str]) -> List[Dict[str, Any]]:
        # Example: assume POST /drivers/batch accepts list of ids
        url = f"{self._config.api_base_url}/drivers/batch"
        ids = list(driver_ids)
        results: list[dict] = []
        if not ids:
            return results
        # Chunk requests according to pagination_size
        chunk_size = max(1, int(self._config.pagination_size))
        for i in range(0, len(ids), chunk_size):
            chunk = ids[i : i + chunk_size]
            data = await self._request_with_retries(url, method="POST", json={"driver_ids": chunk})
            if isinstance(data, dict) and "items" in data:
                results.extend(data["items"])  # common pattern
            elif isinstance(data, list):
                results.extend(data)
            elif data:
                results.append(data)
        return results

    async def _request_with_retries(self, url: str, *, method: str = "GET", json: Any | None = None) -> Optional[Dict[str, Any]]:
        last_exc: Optional[Exception] = None
        for attempt in range(self._config.max_retries + 1):
            try:
                if method == "GET":
                    resp = await self._http.get(url)
                else:
                    resp = await self._http.post(url, json=json)
                if resp.status_code >= 500:
                    raise httpx.HTTPStatusError("server error", request=resp.request, response=resp)
                resp.raise_for_status()
                self._log.info("api.request.success", url=url, method=method, status=resp.status_code)
                return resp.json()
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                self._log.warning("api.request.error", url=url, method=method, attempt=attempt, error=str(exc))
                await asyncio.sleep(min(0.5 * (2 ** attempt), 2.0))
        self._log.error("api.request.failed", url=url, method=method, error=str(last_exc) if last_exc else None)
        return None
