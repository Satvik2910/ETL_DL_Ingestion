"""
Filtering engine for numeric and string operations.
"""
from typing import Any, List, Dict, Callable
from utils.validation import FilterCondition, FilterOperator


class FilterEngine:
    """Engine for applying filters to datasets."""
    
    def __init__(self):
        self._operators: Dict[FilterOperator, Callable] = {
            FilterOperator.EQUAL: lambda x, y: x == y,
            FilterOperator.NOT_EQUAL: lambda x, y: x != y,
            FilterOperator.GREATER_THAN: lambda x, y: x > y if self._is_numeric(x, y) else False,
            FilterOperator.GREATER_EQUAL: lambda x, y: x >= y if self._is_numeric(x, y) else False,
            FilterOperator.LESS_THAN: lambda x, y: x < y if self._is_numeric(x, y) else False,
            FilterOperator.LESS_EQUAL: lambda x, y: x <= y if self._is_numeric(x, y) else False,
            FilterOperator.IN: lambda x, y: x in y if isinstance(y, (list, tuple)) else False,
            FilterOperator.NOT_IN: lambda x, y: x not in y if isinstance(y, (list, tuple)) else True,
            FilterOperator.CONTAINS: lambda x, y: str(y) in str(x),
            FilterOperator.STARTS_WITH: lambda x, y: str(x).startswith(str(y)),
            FilterOperator.ENDS_WITH: lambda x, y: str(x).endswith(str(y)),
        }
    
    @staticmethod
    def _is_numeric(x: Any, y: Any) -> bool:
        """Check if both values are numeric."""
        return isinstance(x, (int, float)) and isinstance(y, (int, float))
    
    def _get_nested_value(self, obj: Dict[str, Any], field: str) -> Any:
        """Get nested field value using dot notation."""
        keys = field.split('.')
        value = obj
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return None
            else:
                return None
        
        return value
    
    def apply_filter(self, data: List[Dict[str, Any]], condition: FilterCondition) -> List[Dict[str, Any]]:
        """
        Apply a single filter condition to dataset.
        
        Args:
            data: List of dictionaries to filter
            condition: Filter condition to apply
            
        Returns:
            Filtered list of dictionaries
        """
        operator_func = self._operators.get(condition.operator)
        if not operator_func:
            return data
        
        filtered = []
        for item in data:
            field_value = self._get_nested_value(item, condition.field)
            
            if field_value is not None:
                try:
                    if operator_func(field_value, condition.value):
                        filtered.append(item)
                except (TypeError, ValueError):
                    # Skip items that can't be compared
                    continue
        
        return filtered
    
    def apply_filters(self, data: List[Dict[str, Any]], conditions: List[FilterCondition]) -> List[Dict[str, Any]]:
        """
        Apply multiple filter conditions (AND logic).
        
        Args:
            data: List of dictionaries to filter
            conditions: List of filter conditions
            
        Returns:
            Filtered list of dictionaries
        """
        result = data
        for condition in conditions:
            result = self.apply_filter(result, condition)
        
        return result
    
    def filter_by_range(
        self, 
        data: List[Dict[str, Any]], 
        field: str, 
        min_value: Any = None, 
        max_value: Any = None
    ) -> List[Dict[str, Any]]:
        """
        Filter data by numeric range.
        
        Args:
            data: List of dictionaries to filter
            field: Field name to filter on
            min_value: Minimum value (inclusive)
            max_value: Maximum value (inclusive)
            
        Returns:
            Filtered list of dictionaries
        """
        filtered = []
        for item in data:
            value = self._get_nested_value(item, field)
            
            if value is None:
                continue
            
            if min_value is not None and value < min_value:
                continue
            
            if max_value is not None and value > max_value:
                continue
            
            filtered.append(item)
        
        return filtered
    
    def filter_by_time_range(
        self,
        data: List[Dict[str, Any]],
        field: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Filter data by time range.
        
        Args:
            data: List of dictionaries to filter
            field: Date field name
            start_date: Start date (ISO 8601)
            end_date: End date (ISO 8601)
            
        Returns:
            Filtered list of dictionaries
        """
        from datetime import datetime
        
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        filtered = []
        for item in data:
            date_str = self._get_nested_value(item, field)
            
            if not date_str:
                continue
            
            try:
                date = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
                if start <= date <= end:
                    filtered.append(item)
            except (ValueError, AttributeError):
                continue
        
        return filtered
