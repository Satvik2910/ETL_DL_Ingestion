"""
Field validation and schema enforcement for Driver Insight Agent.
"""
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ValidationError
from enum import Enum


class ReportType(str, Enum):
    """Supported report types."""
    SCORE_ONLY = "score_only"
    TRIP_ONLY = "trip_only"
    COMBINED = "combined"
    TREND = "trend"
    RANKING = "ranking"
    COMPARISON = "comparison"


class FilterOperator(str, Enum):
    """Supported filter operators."""
    EQUAL = "eq"
    NOT_EQUAL = "ne"
    GREATER_THAN = "gt"
    GREATER_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_EQUAL = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"


class FilterCondition(BaseModel):
    """Filter condition specification."""
    field: str
    operator: FilterOperator
    value: Any


class AgentRequest(BaseModel):
    """Request schema from Planner Agent."""
    request_id: str = Field(..., description="Unique request identifier")
    report_type: ReportType
    driver_ids: Optional[List[str]] = None
    driver_names: Optional[List[str]] = None
    driver_emails: Optional[List[str]] = None
    driver_phones: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    filters: Optional[List[FilterCondition]] = None
    aggregations: Optional[List[str]] = None
    limit: Optional[int] = Field(None, ge=1, le=10000)
    offset: Optional[int] = Field(None, ge=0)
    sort_by: Optional[str] = None
    sort_order: Optional[str] = Field(None, pattern="^(asc|desc)$")
    
    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate ISO 8601 date format."""
        if v is None:
            return v
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError(f"Invalid ISO 8601 date format: {v}")
    
    def validate_request(self) -> tuple[bool, Optional[str]]:
        """
        Validate that request has required fields.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # At least one driver identifier must be present
        if not any([
            self.driver_ids,
            self.driver_names,
            self.driver_emails,
            self.driver_phones
        ]):
            return False, "At least one driver identifier required"
        
        # Date range validation
        if self.start_date and self.end_date:
            start = datetime.fromisoformat(self.start_date.replace('Z', '+00:00'))
            end = datetime.fromisoformat(self.end_date.replace('Z', '+00:00'))
            if start > end:
                return False, "start_date must be before end_date"
        
        return True, None


class ToolRequest(BaseModel):
    """Generic tool request schema."""
    tool_name: str
    parameters: Dict[str, Any]
    timeout: Optional[int] = None
    retry_count: int = 0


class ToolResponse(BaseModel):
    """Generic tool response schema."""
    tool_name: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float
    cached: bool = False


class AgentResponse(BaseModel):
    """Response schema to Planner Agent."""
    request_id: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: float
    tools_executed: List[str] = []
    cache_hits: int = 0


def validate_request(request_data: Dict[str, Any]) -> AgentRequest:
    """
    Validate and parse request data.
    
    Args:
        request_data: Raw request dictionary
        
    Returns:
        Validated AgentRequest object
        
    Raises:
        ValidationError: If validation fails
    """
    return AgentRequest(**request_data)


def validate_tool_response(response_data: Dict[str, Any]) -> ToolResponse:
    """Validate tool response data."""
    return ToolResponse(**response_data)
