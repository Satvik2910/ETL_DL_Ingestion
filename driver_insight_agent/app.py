from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any, Dict

from loguru import logger

from .agent.abstract_card import DRIVER_INSIGHT_CARD
from .agent.core import DriverInsightAgent
from .agent.mcp_registry import MCPRegistry
from .cache.cache_manager import CacheManager
from .config.config import load_config
from .tools.driver_tool import DriverTool
from .tools.score_tool import ScoreTool
from .tools.trip_tool import TripTool
from .tools.trend_tool import TrendTool


async def run_agent(request: Dict[str, Any]) -> Dict[str, Any]:
    cfg = load_config()
    logger.remove()
    logger.add(sys.stderr, level=cfg.logging.level, serialize=cfg.logging.json)

    registry = MCPRegistry()
    # Register tools (these are placeholders; wire to real datasources as needed)
    registry.register(DriverTool(), description="Resolve driver identities")
    registry.register(ScoreTool(), description="Score aggregation and metrics")
    registry.register(TripTool(), description="Trip analytics with filters")
    registry.register(TrendTool(), description="Time-series trend analysis")

    cache = CacheManager(cfg.cache.namespace, cfg.cache.ttl_seconds, cfg.cache.persistent_path)
    agent = DriverInsightAgent(cfg, registry, cache)

    resp = await agent.handle(request)
    return resp.model_dump()


def example_request() -> Dict[str, Any]:
    return {
        "request_id": "req_001",
        "report_type": "combined",
        "drivers": {
            "ids": ["abc123"],
            "names": ["Alice"],
        },
        "time_range": {"start": "2024-01-01T00:00:00Z", "end": "2024-01-07T00:00:00Z"},
        "filters": [{"field": "distance_miles", "op": "gt", "value": 20}],
        "aggregations": [{"kind": "sum", "field": "distance_miles"}],
        "rankings": {"field": "score", "order": "desc", "limit": 5},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=DRIVER_INSIGHT_CARD.description)
    parser.add_argument("--request-json", type=str, help="Planner request JSON string")
    parser.add_argument("--request-file", type=str, help="Path to Planner request JSON file")
    args = parser.parse_args()

    if args.request_json:
        request = json.loads(args.request_json)
    elif args.request_file:
        with open(args.request_file, "r", encoding="utf-8") as f:
            request = json.load(f)
    else:
        request = example_request()

    result = asyncio.run(run_agent(request))
    json.dump(result, sys.stdout, separators=(",", ":"), sort_keys=True)


if __name__ == "__main__":
    main()
