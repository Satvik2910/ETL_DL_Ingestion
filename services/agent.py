from __future__ import annotations

import asyncio
from typing import Any, Dict, Iterable, List, Optional

import httpx

from cache.base import AsyncCache
from config.loader import AppConfig
from mcp_tools.invoker import MCPInvoker
from services.logger import get_logger
from services.validator import Validator
from services.api_client import APIClient


class DriverInsightAgent:
    def __init__(
        self,
        config: AppConfig,
        cache: AsyncCache,
        mcp_invoker: MCPInvoker,
        http_client: httpx.AsyncClient,
    ) -> None:
        self._config = config
        self._cache = cache
        self._mcp = mcp_invoker
        self._log = get_logger("agent")
        self._validator = Validator(config)
        self._api_client = APIClient(config=config, http_client=http_client)

    def _cache_key(self, driver_id: str) -> str:
        return f"driver:{driver_id}"

    async def get_driver(self, driver_id: str) -> Dict[str, Any]:
        key = self._cache_key(driver_id)
        cached = await self._cache.get(key)
        if cached:
            self._log.info("cache.hit", key=key)
            return _ensure_dict(cached)
        self._log.info("cache.miss", key=key)

        # Try remote cache via MCP tool (optional)
        remote_cached = await self._mcp.invoke("CacheTool", {"op": "get", "key": key})
        if remote_cached and remote_cached.get("value"):
            value = remote_cached["value"]
            await self._cache.set(key, value, ttl_seconds=self._config.cache_ttl)
            return _ensure_dict(value)

        # Fetch via MCP tool; fallback to direct API client
        payload = {
            "driver_id": driver_id,
            "api_base_url": self._config.api_base_url,
            "pagination_size": self._config.pagination_size,
            "max_retries": self._config.max_retries,
        }
        data = await self._mcp.invoke("FetchTool", payload)
        if data is None:
            # Fallback
            self._log.warning("mcp.fetch.failed_fallback", driver_id=driver_id)
            data = await self._api_client.fetch_driver(driver_id)

        if not data:
            raise ServiceError("Driver API unavailable or returned no data", reason="API_UNAVAILABLE")

        # Validate via MCP tool; fallback to local validator
        validation = await self._mcp.invoke("ValidateTool", {"record": data, "required_fields": self._config.required_fields})
        is_valid = bool(validation.get("valid")) if validation is not None else self._validator.validate_minimum(data)
        if not is_valid:
            raise ServiceError("Missing required fields in driver record", reason="VALIDATION_FAILED")

        # Cache locally and remotely
        await self._cache.set(key, data, ttl_seconds=self._config.cache_ttl)
        _ = await self._mcp.invoke("CacheTool", {"op": "set", "key": key, "value": data, "ttl": self._config.cache_ttl})

        # Optional summarize
        summary = await self._mcp.invoke("SummarizeTool", {"record": data})
        if summary and isinstance(summary.get("summary"), dict):
            data["summary"] = summary["summary"]
        return data

    async def get_drivers_batch(self, driver_ids: Iterable[str]) -> List[Dict[str, Any]]:
        ids = list(dict.fromkeys([i for i in driver_ids if i]))  # dedupe, preserve order
        if not ids:
            return []

        results: list[dict] = []
        misses: list[str] = []

        # Check local cache first
        for driver_id in ids:
            key = self._cache_key(driver_id)
            cached = await self._cache.get(key)
            if cached:
                self._log.info("cache.hit", key=key)
                results.append(_ensure_dict(cached))
            else:
                misses.append(driver_id)

        if not misses:
            return results

        # Try remote cache bulk get
        remote = await self._mcp.invoke("CacheTool", {"op": "mget", "keys": [self._cache_key(i) for i in misses]})
        if remote and isinstance(remote.get("values"), list):
            remote_values = remote["values"]
            for driver_id, value in zip(misses, remote_values, strict=False):
                if value:
                    results.append(_ensure_dict(value))
                else:
                    # still missing
                    pass
            # Recompute misses
            found_ids = {r.get("driver_id") for r in results if isinstance(r, dict)}
            misses = [i for i in misses if i not in found_ids]

        if misses:
            # Batch fetch via MCP FetchTool with pagination-aware chunks
            chunk_size = max(1, int(self._config.pagination_size))
            fetched: list[dict] = []
            for i in range(0, len(misses), chunk_size):
                chunk = misses[i : i + chunk_size]
                payload = {
                    "driver_ids": chunk,
                    "api_base_url": self._config.api_base_url,
                    "pagination_size": self._config.pagination_size,
                    "max_retries": self._config.max_retries,
                }
                data = await self._mcp.invoke("FetchTool", payload)
                if data is None:
                    # Fallback to direct API client
                    self._log.warning("mcp.fetch.batch.failed_fallback", count=len(chunk))
                    data = await self._api_client.fetch_drivers_batch(chunk)
                # Normalize
                items: list[dict] = []
                if isinstance(data, dict) and "items" in data:
                    items = list(data["items"])  # type: ignore[assignment]
                elif isinstance(data, list):
                    items = data  # type: ignore[assignment]
                elif data:
                    items = [data]  # type: ignore[list-item]

                # Validate
                valid_items = self._validator.validate_many(items)
                fetched.extend(valid_items)

            # Cache results
            for rec in fetched:
                if rec and isinstance(rec, dict) and rec.get("driver_id"):
                    await self._cache.set(self._cache_key(rec["driver_id"]), rec, ttl_seconds=self._config.cache_ttl)
            results.extend(fetched)

        return results


class ServiceError(Exception):
    def __init__(self, message: str, *, reason: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.reason = reason
        self.status_code = status_code


def _ensure_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    # For Redis, we might get JSON string; try to decode
    try:
        import json

        if isinstance(value, (bytes, str)):
            return json.loads(value)
    except Exception:  # noqa: BLE001
        pass
    return {"value": value}
