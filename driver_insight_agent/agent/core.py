from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Tuple

from loguru import logger

from ..cache.cache_manager import CacheManager
from ..config.config import AppConfig
from ..utils.aggregation_engine import aggregate, compare, rank
from ..utils.pagination import chunk_list, paginate_list
from ..utils.summarizer import summarize_results
from ..utils.validation import (
    AggregationSpec,
    DriverSelector,
    FilterCondition,
    PlannerRequest,
    PlannerResponse,
    RankingSpec,
    ReportType,
    ToolError,
    TrendSpec,
)
from .mcp_registry import MCPRegistry


class DriverInsightAgent:
    def __init__(self, config: AppConfig, registry: MCPRegistry, cache: CacheManager) -> None:
        self.config = config
        self.registry = registry
        self.cache = cache

    # --------------------------- Planning ---------------------------
    @staticmethod
    def _select_tools(request: PlannerRequest) -> List[str]:
        selection: List[str] = []
        if request.report_type == "score":
            selection = ["driver_tool", "score_tool"]
        elif request.report_type == "trip":
            selection = ["driver_tool", "trip_tool"]
        elif request.report_type == "trend":
            selection = ["driver_tool", "trend_tool"]
        else:  # combined
            selection = ["driver_tool", "score_tool", "trip_tool"]
        return selection

    # --------------------------- Execution helpers ---------------------------
    async def _resolve_drivers(self, drivers: DriverSelector) -> Dict[str, Dict[str, Any]]:
        resolved = await self.registry.run_with_retries(
            "driver_tool",
            ids=drivers.ids,
            names=drivers.names,
            emails=drivers.emails,
            phones=drivers.phones,
        )
        return resolved

    async def _fetch_scores(self, driver_ids: List[str], aggregations: List[AggregationSpec]) -> Dict[str, Dict[str, Any]]:
        return await self.registry.run_with_retries(
            "score_tool",
            driver_ids=driver_ids,
            aggregations=aggregations,
        )

    async def _fetch_trips(
        self,
        driver_ids: List[str],
        time_range: Tuple[str, str],
        filters: List[FilterCondition],
        limit: int | None = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        return await self.registry.run_with_retries(
            "trip_tool",
            driver_ids=driver_ids,
            start=time_range[0],
            end=time_range[1],
            filters=filters,
            limit=limit,
        )

    async def _fetch_trends(
        self,
        driver_ids: List[str],
        time_range: Tuple[str, str],
        trend: TrendSpec,
    ) -> Dict[str, List[Dict[str, Any]]]:
        return await self.registry.run_with_retries(
            "trend_tool",
            driver_ids=driver_ids,
            start=time_range[0],
            end=time_range[1],
            trend=trend,
        )

    # --------------------------- Caching ---------------------------
    async def _maybe_cached(self, key_obj: Any, compute_coro):
        key = self.cache.key_for(key_obj)
        cached = await self.cache.get(key)
        if cached is not None:
            return cached
        result = await compute_coro
        await self.cache.set(key, result)
        return result

    # --------------------------- Orchestration ---------------------------
    async def handle(self, raw_request: Dict[str, Any]) -> PlannerResponse:
        req = PlannerRequest(**raw_request)
        tools = self._select_tools(req)

        # Pagination token handling
        page_size = self.config.pagination.page_size
        pagination_token = req.pagination_token

        # Resolve drivers first (cached)
        resolved_drivers = await self._maybe_cached(
            {"kind": "drivers", "drivers": req.drivers.model_dump()},
            self._resolve_drivers(req.drivers),
        )
        driver_ids = sorted(resolved_drivers.keys())
        if not driver_ids:
            return PlannerResponse(
                request_id=req.request_id,
                report_type=req.report_type,
                results={},
                summary="No drivers resolved.",
                errors=[],
                pagination_token=None,
            )

        # Chunks for concurrency
        driver_chunks = chunk_list(driver_ids, self.config.concurrency.batch_size)

        errors: List[ToolError] = []
        results: Dict[str, Any] = {}

        async def gather_scores():
            try:
                parts = await asyncio.gather(
                    *[
                        self._maybe_cached(
                            {"kind": "scores", "driver_ids": chunk, "aggs": [a.model_dump() for a in req.aggregations]},
                            self._fetch_scores(chunk, req.aggregations),
                        )
                        for chunk in driver_chunks
                    ]
                )
                merged: Dict[str, Any] = {}
                for p in parts:
                    merged.update(p)
                return merged
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    ToolError(tool="score_tool", code="runtime_error", message=str(exc), retry_count=0)
                )
                return {}

        async def gather_trips():
            try:
                parts = await asyncio.gather(
                    *[
                        self._maybe_cached(
                            {
                                "kind": "trips",
                                "driver_ids": chunk,
                                "start": req.time_range.start,
                                "end": req.time_range.end,
                                "filters": [f.model_dump() for f in req.filters],
                            },
                            self._fetch_trips(chunk, (req.time_range.start, req.time_range.end), req.filters),
                        )
                        for chunk in driver_chunks
                    ]
                )
                merged: Dict[str, Any] = {}
                for p in parts:
                    merged.update(p)
                return merged
            except Exception as exc:  # noqa: BLE001
                errors.append(ToolError(tool="trip_tool", code="runtime_error", message=str(exc), retry_count=0))
                return {}

        async def gather_trends():
            if not req.trend:
                return {}
            try:
                parts = await asyncio.gather(
                    *[
                        self._maybe_cached(
                            {
                                "kind": "trends",
                                "driver_ids": chunk,
                                "start": req.time_range.start,
                                "end": req.time_range.end,
                                "trend": req.trend.model_dump(),
                            },
                            self._fetch_trends(chunk, (req.time_range.start, req.time_range.end), req.trend),
                        )
                        for chunk in driver_chunks
                    ]
                )
                merged: Dict[str, Any] = {}
                for p in parts:
                    merged.update(p)
                return merged
            except Exception as exc:  # noqa: BLE001
                errors.append(ToolError(tool="trend_tool", code="runtime_error", message=str(exc), retry_count=0))
                return {}

        # Execute based on selected tools in parallel where possible
        coros = []
        if "score_tool" in tools:
            coros.append(gather_scores())
        if "trip_tool" in tools:
            coros.append(gather_trips())
        if "trend_tool" in tools:
            coros.append(gather_trends())

        outputs = await asyncio.gather(*coros)
        for out in outputs:
            # Use keys to place results
            if out and isinstance(next(iter(out.values()), None), dict) and "score" in next(iter(out.values())).keys():
                results["scores"] = out
            elif out and isinstance(next(iter(out.values()), None), list) and out and isinstance(next(iter(out.values())), list):
                # Could be trips or trends; disambiguate by list element keys
                sample_list = next(iter(out.values()))
                if sample_list and isinstance(sample_list[0], dict) and "trip_id" in sample_list[0]:
                    results["trips"] = out
                else:
                    results["trends"] = out

        # Rankings/comparisons after base results
        if req.rankings and "scores" in results:
            ranked = rank(results["scores"], req.rankings)
            results["ranking"] = [{"driver_id": d, "value": v} for d, v in ranked]
        if req.comparison and "scores" in results:
            results["comparison"] = compare(results["scores"], req.comparison.drivers, req.comparison.field)
        if req.aggregations:
            # apply to trips as an example on distance_miles
            if "trips" in results:
                flat = [t for trips in results["trips"].values() for t in trips]
                agg_res = aggregate(flat, req.aggregations)
                results.setdefault("aggregates", {}).update(agg_res)

        # Pagination (deterministic ordering by driver_id)
        # For trips/trends we paginate driver list, not inside individual driver arrays
        next_token = None
        if "trips" in results or "trends" in results:
            ordered_driver_ids = sorted(driver_ids)
            page, next_token = paginate_list(ordered_driver_ids, req.request_id, page_size, pagination_token)
            if "trips" in results:
                results["trips"] = {d: results["trips"].get(d, []) for d in page}
            if "trends" in results:
                results["trends"] = {d: results["trends"].get(d, []) for d in page}

        summary = summarize_results(results, req.report_type, self.config.summarization.max_tokens)

        return PlannerResponse(
            request_id=req.request_id,
            report_type=req.report_type,
            results=results,
            summary=summary,
            errors=errors,
            pagination_token=next_token,
        )
