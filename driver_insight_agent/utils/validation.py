"""Input validation and schema enforcement utilities."""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from dateutil.parser import parse as parse_date


class TimeRange(BaseModel):
    """Time range validation model."""
    start_date: datetime = Field(..., description="Start date in ISO 8601 format")
    end_date: datetime = Field(..., description="End date in ISO 8601 format")
    
    @validator('end_date')
    def end_after_start(cls, v, values):
        """Validate that end date is after start date."""
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v


class DriverIdentifier(BaseModel):
    """Driver identification model."""
    driver_id: Optional[str] = Field(None, description="Driver ID")
    name: Optional[str] = Field(None, description="Driver name")
    email: Optional[str] = Field(None, description="Driver email")
    phone: Optional[str] = Field(None, description="Driver phone")
    
    @validator('*', pre=True)
    def at_least_one_identifier(cls, v, values):
        """Ensure at least one identifier is provided."""
        if not any(values.values()) and not v:
            raise ValueError('At least one driver identifier must be provided')
        return v


class FilterCriteria(BaseModel):
    """Filter criteria model."""
    field: str = Field(..., description="Field to filter on")
    operator: str = Field(..., description="Filter operator (eq, ne, gt, lt, gte, lte, in, contains)")
    value: Union[str, int, float, List[Union[str, int, float]]] = Field(..., description="Filter value")
    
    @validator('operator')
    def valid_operator(cls, v):
        """Validate filter operator."""
        valid_ops = ['eq', 'ne', 'gt', 'lt', 'gte', 'lte', 'in', 'contains', 'startswith', 'endswith']
        if v not in valid_ops:
            raise ValueError(f'Invalid operator: {v}. Must be one of {valid_ops}')
        return v


class AgentRequest(BaseModel):
    """Main agent request validation model."""
    request_id: str = Field(..., description="Unique request identifier")
    drivers: List[DriverIdentifier] = Field(..., description="Driver identifiers")
    time_range: Optional[TimeRange] = Field(None, description="Time range filter")
    report_type: str = Field(..., description="Report type (score, trip, combined, trend)")
    filters: Optional[List[FilterCriteria]] = Field(default_factory=list, description="Additional filters")
    aggregations: Optional[List[str]] = Field(default_factory=list, description="Requested aggregations")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional options")
    
    @validator('report_type')
    def valid_report_type(cls, v):
        """Validate report type."""
        valid_types = ['score', 'trip', 'combined', 'trend', 'comparison', 'ranking']
        if v not in valid_types:
            raise ValueError(f'Invalid report_type: {v}. Must be one of {valid_types}')
        return v


class ValidationError(Exception):
    """Custom validation error."""
    
    def __init__(self, message: str, field: Optional[str] = None, errors: Optional[List[str]] = None):
        self.message = message
        self.field = field
        self.errors = errors or []
        super().__init__(self.message)


class RequestValidator:
    """Request validation utility."""
    
    @staticmethod
    def validate_request(request_data: Dict[str, Any]) -> AgentRequest:
        """Validate incoming request data."""
        try:
            # Parse time range strings to datetime objects if needed
            if 'time_range' in request_data and request_data['time_range']:
                time_range = request_data['time_range']
                if isinstance(time_range.get('start_date'), str):
                    time_range['start_date'] = parse_date(time_range['start_date'])
                if isinstance(time_range.get('end_date'), str):
                    time_range['end_date'] = parse_date(time_range['end_date'])
            
            return AgentRequest(**request_data)
        
        except Exception as e:
            raise ValidationError(f"Request validation failed: {str(e)}")
    
    @staticmethod
    def validate_driver_identifiers(drivers: List[Dict[str, Any]]) -> List[DriverIdentifier]:
        """Validate driver identifier list."""
        validated_drivers = []
        
        for i, driver_data in enumerate(drivers):
            try:
                validated_drivers.append(DriverIdentifier(**driver_data))
            except Exception as e:
                raise ValidationError(f"Driver {i} validation failed: {str(e)}", field=f"drivers[{i}]")
        
        return validated_drivers
    
    @staticmethod
    def validate_filters(filters: List[Dict[str, Any]]) -> List[FilterCriteria]:
        """Validate filter criteria list."""
        validated_filters = []
        
        for i, filter_data in enumerate(filters):
            try:
                validated_filters.append(FilterCriteria(**filter_data))
            except Exception as e:
                raise ValidationError(f"Filter {i} validation failed: {str(e)}", field=f"filters[{i}]")
        
        return validated_filters
    
    @staticmethod
    def validate_time_range(start_date: Union[str, datetime], end_date: Union[str, datetime]) -> TimeRange:
        """Validate time range."""
        try:
            if isinstance(start_date, str):
                start_date = parse_date(start_date)
            if isinstance(end_date, str):
                end_date = parse_date(end_date)
            
            return TimeRange(start_date=start_date, end_date=end_date)
        
        except Exception as e:
            raise ValidationError(f"Time range validation failed: {str(e)}", field="time_range")


class ResponseValidator:
    """Response validation utility."""
    
    @staticmethod
    def validate_tool_response(tool_name: str, response_data: Any) -> Dict[str, Any]:
        """Validate tool response format."""
        if not isinstance(response_data, dict):
            raise ValidationError(f"Tool {tool_name} response must be a dictionary")
        
        required_fields = ['success', 'data']
        for field in required_fields:
            if field not in response_data:
                raise ValidationError(f"Tool {tool_name} response missing required field: {field}")
        
        return response_data
    
    @staticmethod
    def validate_aggregation_result(result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate aggregation result format."""
        required_fields = ['metric', 'value', 'count']
        for field in required_fields:
            if field not in result:
                raise ValidationError(f"Aggregation result missing required field: {field}")
        
        return result