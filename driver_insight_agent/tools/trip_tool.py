from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from loguru import logger

from ..utils.filter_engine import apply_filters
from ..utils.validation import FilterCondition


class TripTool:
    name = "trip_tool"
    version = "0.1.0"

    def __init__(self, datasource: Any | None = None) -> None:
        self.datasource = datasource

    async def run(
        self,
        driver_ids: List[str],
        start: str,
        end: str,
        filters: List[FilterCondition] | None = None,
        limit: int | None = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        # Placeholder synthetic generator; deterministic based on driver_ids and window
        logger.debug("Generating trips for {} drivers", len(driver_ids))
        rng_seed = hash((tuple(sorted(driver_ids)), start, end)) & 0xFFFFFFFF
        rng = random.Random(rng_seed)

        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        window_hours = max(1, int((end_dt - start_dt).total_seconds() // 3600))

        results: Dict[str, List[Dict[str, Any]]] = {}
        for d in sorted(driver_ids):
            num_trips = max(0, min(window_hours // 4, 50))
            trips: List[Dict[str, Any]] = []
            for i in range(num_trips):
                start_offset = rng.randint(0, max(0, window_hours - 1))
                duration_min = rng.randint(5, 180)
                distance_miles = round(duration_min * (20 + rng.random() * 30) / 60, 2)
                ts = start_dt + timedelta(hours=start_offset)
                trips.append(
                    {
                        "trip_id": f"t_{d[-4:]}_{i}",
                        "driver_id": d,
                        "start_time": ts.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
                        "duration_min": duration_min,
                        "distance_miles": distance_miles,
                    }
                )
            if filters:
                trips = apply_filters(trips, filters)
            if limit is not None:
                trips = trips[:limit]
            results[d] = trips
        return results
