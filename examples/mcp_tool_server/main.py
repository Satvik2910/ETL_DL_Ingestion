from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Example MCP Tool Server")


class FetchPayload(BaseModel):
    driver_id: Optional[str] = None
    driver_ids: Optional[List[str]] = None
    api_base_url: str
    pagination_size: int = 100
    max_retries: int = 3


@app.post("/mcp-tools/FetchTool")
async def fetch_tool(payload: FetchPayload):
    async with httpx.AsyncClient() as client:
        if payload.driver_id:
            url = f"{payload.api_base_url}/drivers/{payload.driver_id}"
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.json()
            except Exception:
                return None
        elif payload.driver_ids:
            url = f"{payload.api_base_url}/drivers/batch"
            try:
                resp = await client.post(url, json={"driver_ids": payload.driver_ids})
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, dict) and "items" in data:
                    return {"items": data["items"]}
                if isinstance(data, list):
                    return data
                return data
            except Exception:
                return None
        else:
            return None


class ValidatePayload(BaseModel):
    record: Dict[str, Any]
    required_fields: List[str]


@app.post("/mcp-tools/ValidateTool")
async def validate_tool(payload: ValidatePayload):
    missing = [k for k in payload.required_fields if k not in payload.record or payload.record.get(k) in (None, "")]
    return {"valid": len(missing) == 0, "missing": missing}


class CachePayload(BaseModel):
    op: str
    key: Optional[str] = None
    keys: Optional[List[str]] = None
    value: Optional[Any] = None
    ttl: Optional[int] = None

_memory_cache: dict[str, Any] = {}


@app.post("/mcp-tools/CacheTool")
async def cache_tool(payload: CachePayload):
    if payload.op == "get" and payload.key:
        return {"value": _memory_cache.get(payload.key)}
    if payload.op == "set" and payload.key is not None:
        _memory_cache[payload.key] = payload.value
        return {"ok": True}
    if payload.op == "mget" and payload.keys:
        return {"values": [_memory_cache.get(k) for k in payload.keys]}
    return {"ok": False}


class SummarizePayload(BaseModel):
    record: Dict[str, Any]


@app.post("/mcp-tools/SummarizeTool")
async def summarize_tool(payload: SummarizePayload):
    record = payload.record
    summary = {
        "driver_id": record.get("driver_id"),
        "name": record.get("name"),
        "vehicle": record.get("vehicle"),
        "rating": record.get("rating"),
    }
    return {"summary": {k: v for k, v in summary.items() if v is not None}}


# To run: uvicorn examples.mcp_tool_server.main:app --host 0.0.0.0 --port 8081
