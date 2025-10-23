from __future__ import annotations

from typing import Any, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from services.agent import DriverInsightAgent, ServiceError
from pydantic import BaseModel

router = APIRouter(prefix="/drivers")


async def get_agent(request: Request) -> DriverInsightAgent:
    return request.app.state.agent  # type: ignore[attr-defined]


@router.get("/{driver_id}")
async def get_driver(driver_id: str, agent: DriverInsightAgent = Depends(get_agent)) -> dict:
    try:
        data = await agent.get_driver(driver_id)
        return data
    except ServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "error": str(exc),
                "reason": exc.reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "reason": "UNEXPECTED_ERROR",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ) from exc


class BatchRequest(BaseModel):
    driver_ids: List[str]


@router.post("/batch")
async def get_drivers_batch(body: BatchRequest, agent: DriverInsightAgent = Depends(get_agent)) -> list[dict]:
    try:
        data = await agent.get_drivers_batch(body.driver_ids)
        return data
    except ServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "error": str(exc),
                "reason": exc.reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "reason": "UNEXPECTED_ERROR",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ) from exc
