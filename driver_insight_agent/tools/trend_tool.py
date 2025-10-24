from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from loguru import logger

from ..utils.validation import TrendSpec


class TrendTool:
    name = "trend_tool"
    version = "0.1.0"

    def __init__(self, datasource: Any | None = None) -> None:
        self.datasource = datasource

    async def run(
        self,
        driver_ids: List[str],
        start: str,
        end: str,
        trend: TrendSpec,
    ) -> Dict[str, List[Dict[str, Any]]]:
        logger.debug("Generating trends for {} drivers", len(driver_ids))
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        delta = end_dt - start_dt
        if trend.interval == "hour":
            step = timedelta(hours=1)
        elif trend.interval == "day":
            step = timedelta(days=1)
        elif trend.interval == "week":
            step = timedelta(weeks=1)
        else:
            step = timedelta(days=30)

        timestamps: List[datetime] = []
        t = start_dt
        while t <= end_dt:
            timestamps.append(t)
            t += step

        results: Dict[str, List[Dict[str, Any]]] = {}
        for d in sorted(driver_ids):
            rng = random.Random(hash((d, trend.field)) & 0xFFFFFFFF)
            series: List[Dict[str, Any]] = []
            level = rng.random() * 10
            for idx, ts in enumerate(timestamps):
                value = level + rng.random() * 5 + idx * 0.1
                series.append(
                    {
                        "driver_id": d,
                        "timestamp": ts.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
                        trend.field: round(value, 3),
                    }
                )
            results[d] = series
        return results
