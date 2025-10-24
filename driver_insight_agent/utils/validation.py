from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator

ReportType = Literal["score", "trip", "trend", "combined"]


class TimeRange(BaseModel):
    start: str = Field(..., description="ISO 8601 start datetime")
    end: str = Field(..., description="ISO 8601 end datetime")

    @field_validator("start", "end")
    @classmethod
    def validate_iso8601(cls, v: str) -> str:
        # Lightweight check; deep parsing can be done in tools
        if "T" not in v:
            raise ValueError("must be ISO 8601 with time component (e.g., 2024-01-01T00:00:00Z)")
        return v


class DriverSelector(BaseModel):
    ids: Optional[List[str]] = None
    names: Optional[List[str]] = None
    emails: Optional[List[str]] = None
    phones: Optional[List[str]] = None

    def is_empty(self) -> bool:
        return not any([self.ids, self.names, self.emails, self.phones])


class AggregationSpec(BaseModel):
    kind: Literal["sum", "avg", "min", "max", "count"]
    field: str


class RankingSpec(BaseModel):
    field: str
    order: Literal["asc", "desc"] = "desc"
    limit: int = 10


class ComparisonSpec(BaseModel):
    drivers: List[str]  # resolved driver IDs
    field: str


class TrendSpec(BaseModel):
    field: str
    interval: Literal["hour", "day", "week", "month"] = "day"


class FilterCondition(BaseModel):
    field: str
    op: Literal["eq", "neq", "gt", "gte", "lt", "lte", "contains", "in", "nin", "startswith", "endswith"]
    value: Union[str, float, int, bool, List[Union[str, float, int, bool]]]


class PlannerRequest(BaseModel):
    request_id: str
    report_type: ReportType
    drivers: DriverSelector
    time_range: TimeRange
    filters: List[FilterCondition] = Field(default_factory=list)
    aggregations: List[AggregationSpec] = Field(default_factory=list)
    rankings: Optional[RankingSpec] = None
    comparison: Optional[ComparisonSpec] = None
    trend: Optional[TrendSpec] = None
    pagination_token: Optional[str] = None

    @field_validator("drivers")
    @classmethod
    def check_drivers_not_empty(cls, v: DriverSelector):
        if v.is_empty():
            raise ValueError("At least one driver identifier must be provided")
        return v


class ToolError(BaseModel):
    tool: str
    code: str
    message: str
    retry_count: int


class PlannerResponse(BaseModel):
    request_id: str
    report_type: ReportType
    results: Dict[str, Any] = Field(default_factory=dict)
    summary: Optional[str] = None
    errors: List[ToolError] = Field(default_factory=list)
    pagination_token: Optional[str] = None


__all__ = [
    "ReportType",
    "TimeRange",
    "DriverSelector",
    "AggregationSpec",
    "RankingSpec",
    "ComparisonSpec",
    "TrendSpec",
    "FilterCondition",
    "PlannerRequest",
    "PlannerResponse",
    "ToolError",
]
