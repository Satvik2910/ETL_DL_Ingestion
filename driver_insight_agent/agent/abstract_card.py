from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class AgentCard:
    name: str
    version: str
    description: str
    capabilities: List[str]


DRIVER_INSIGHT_CARD = AgentCard(
    name="DriverInsightAgent",
    version="0.1.0",
    description=(
        "Deterministic analytics and reporting agent for driver metrics. "
        "Selects MCP tools dynamically, supports batching, caching, and summarization."
    ),
    capabilities=[
        "score aggregation",
        "trip analytics",
        "trend analysis",
        "filtering",
        "aggregation",
        "rankings",
        "comparisons",
        "pagination",
        "concurrency",
        "caching",
    ],
)


__all__ = ["AgentCard", "DRIVER_INSIGHT_CARD"]
