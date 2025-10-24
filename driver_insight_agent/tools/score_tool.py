from __future__ import annotations

import random
from typing import Any, Dict, List

from loguru import logger

from ..utils.aggregation_engine import aggregate
from ..utils.validation import AggregationSpec


class ScoreTool:
    name = "score_tool"
    version = "0.1.0"

    def __init__(self, datasource: Any | None = None) -> None:
        self.datasource = datasource

    async def run(
        self,
        driver_ids: List[str],
        aggregations: List[AggregationSpec] | None = None,
    ) -> Dict[str, Dict[str, Any]]:
        # Placeholder deterministic score generator per driver
        logger.debug("Generating scores for {} drivers", len(driver_ids))
        results: Dict[str, Dict[str, Any]] = {}
        for d in sorted(driver_ids):
            rng = random.Random(hash(d) & 0xFFFFFFFF)
            base = 60 + rng.random() * 40
            metrics = {
                "score": round(base, 2),
                "hard_brakes": int(rng.random() * 10),
                "speeding_events": int(rng.random() * 5),
                "miles": round(50 + rng.random() * 200, 1),
            }
            if aggregations:
                metrics.update(aggregate([metrics], aggregations))
            results[d] = metrics
        return results
