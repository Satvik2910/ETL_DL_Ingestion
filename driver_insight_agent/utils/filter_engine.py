"""Filtering engine for numeric and string operations."""

from typing import List, Dict, Any, Union, Callable
import re
from datetime import datetime
from dateutil.parser import parse as parse_date


class FilterEngine:
    """Engine for applying filters to data."""
    
    def __init__(self):
        """Initialize filter engine with operator mappings."""
        self.operators = {
            'eq': self._equals,
            'ne': self._not_equals,
            'gt': self._greater_than,
            'lt': self._less_than,
            'gte': self._greater_than_or_equal,
            'lte': self._less_than_or_equal,
            'in': self._in_list,
            'not_in': self._not_in_list,
            'contains': self._contains,
            'not_contains': self._not_contains,
            'startswith': self._starts_with,
            'endswith': self._ends_with,
            'regex': self._regex_match,
            'between': self._between,
            'is_null': self._is_null,
            'is_not_null': self._is_not_null,
        }
    
    def apply_filters(self, data: List[Dict[str, Any]], filters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply multiple filters to data."""
        if not filters:
            return data
        
        filtered_data = data.copy()
        
        for filter_criteria in filters:
            filtered_data = self._apply_single_filter(filtered_data, filter_criteria)
        
        return filtered_data
    
    def _apply_single_filter(self, data: List[Dict[str, Any]], filter_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply a single filter to data."""
        field = filter_criteria.get('field')
        operator = filter_criteria.get('operator')
        value = filter_criteria.get('value')
        
        if not field or not operator:
            return data
        
        if operator not in self.operators:
            raise ValueError(f"Unsupported operator: {operator}")
        
        filter_func = self.operators[operator]
        
        return [
            item for item in data
            if self._evaluate_filter(item, field, filter_func, value)
        ]
    
    def _evaluate_filter(self, item: Dict[str, Any], field: str, filter_func: Callable, value: Any) -> bool:
        """Evaluate filter condition for a single item."""
        try:
            # Handle nested field access (e.g., "driver.score")
            field_value = self._get_nested_value(item, field)
            return filter_func(field_value, value)
        except (KeyError, TypeError, AttributeError):
            return False
    
    def _get_nested_value(self, item: Dict[str, Any], field: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        keys = field.split('.')
        value = item
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        
        return value
    
    # Filter operator implementations
    
    def _equals(self, field_value: Any, filter_value: Any) -> bool:
        """Equality comparison."""
        return self._normalize_value(field_value) == self._normalize_value(filter_value)
    
    def _not_equals(self, field_value: Any, filter_value: Any) -> bool:
        """Not equals comparison."""
        return not self._equals(field_value, filter_value)
    
    def _greater_than(self, field_value: Any, filter_value: Any) -> bool:
        """Greater than comparison."""
        try:
            return self._to_comparable(field_value) > self._to_comparable(filter_value)
        except (TypeError, ValueError):
            return False
    
    def _less_than(self, field_value: Any, filter_value: Any) -> bool:
        """Less than comparison."""
        try:
            return self._to_comparable(field_value) < self._to_comparable(filter_value)
        except (TypeError, ValueError):
            return False
    
    def _greater_than_or_equal(self, field_value: Any, filter_value: Any) -> bool:
        """Greater than or equal comparison."""
        try:
            return self._to_comparable(field_value) >= self._to_comparable(filter_value)
        except (TypeError, ValueError):
            return False
    
    def _less_than_or_equal(self, field_value: Any, filter_value: Any) -> bool:
        """Less than or equal comparison."""
        try:
            return self._to_comparable(field_value) <= self._to_comparable(filter_value)
        except (TypeError, ValueError):
            return False
    
    def _in_list(self, field_value: Any, filter_value: List[Any]) -> bool:
        """In list comparison."""
        if not isinstance(filter_value, list):
            return False
        return self._normalize_value(field_value) in [self._normalize_value(v) for v in filter_value]
    
    def _not_in_list(self, field_value: Any, filter_value: List[Any]) -> bool:
        """Not in list comparison."""
        return not self._in_list(field_value, filter_value)
    
    def _contains(self, field_value: Any, filter_value: Any) -> bool:
        """Contains substring comparison."""
        try:
            return str(filter_value).lower() in str(field_value).lower()
        except (TypeError, AttributeError):
            return False
    
    def _not_contains(self, field_value: Any, filter_value: Any) -> bool:
        """Not contains substring comparison."""
        return not self._contains(field_value, filter_value)
    
    def _starts_with(self, field_value: Any, filter_value: Any) -> bool:
        """Starts with comparison."""
        try:
            return str(field_value).lower().startswith(str(filter_value).lower())
        except (TypeError, AttributeError):
            return False
    
    def _ends_with(self, field_value: Any, filter_value: Any) -> bool:
        """Ends with comparison."""
        try:
            return str(field_value).lower().endswith(str(filter_value).lower())
        except (TypeError, AttributeError):
            return False
    
    def _regex_match(self, field_value: Any, filter_value: Any) -> bool:
        """Regular expression match."""
        try:
            pattern = re.compile(str(filter_value), re.IGNORECASE)
            return bool(pattern.search(str(field_value)))
        except (TypeError, re.error):
            return False
    
    def _between(self, field_value: Any, filter_value: List[Any]) -> bool:
        """Between range comparison."""
        if not isinstance(filter_value, list) or len(filter_value) != 2:
            return False
        
        try:
            comparable_value = self._to_comparable(field_value)
            min_val = self._to_comparable(filter_value[0])
            max_val = self._to_comparable(filter_value[1])
            return min_val <= comparable_value <= max_val
        except (TypeError, ValueError):
            return False
    
    def _is_null(self, field_value: Any, filter_value: Any) -> bool:
        """Is null comparison."""
        return field_value is None
    
    def _is_not_null(self, field_value: Any, filter_value: Any) -> bool:
        """Is not null comparison."""
        return field_value is not None
    
    # Helper methods
    
    def _normalize_value(self, value: Any) -> Any:
        """Normalize value for comparison."""
        if isinstance(value, str):
            return value.lower().strip()
        return value
    
    def _to_comparable(self, value: Any) -> Union[int, float, datetime, str]:
        """Convert value to comparable type."""
        if value is None:
            raise ValueError("Cannot compare None value")
        
        # Try to parse as number
        if isinstance(value, (int, float)):
            return value
        
        if isinstance(value, str):
            # Try to parse as number
            try:
                if '.' in value:
                    return float(value)
                else:
                    return int(value)
            except ValueError:
                pass
            
            # Try to parse as date
            try:
                return parse_date(value)
            except (ValueError, TypeError):
                pass
            
            # Return as string
            return value.lower()
        
        # Try to parse as datetime
        if hasattr(value, 'isoformat'):
            return value
        
        return str(value).lower()


class AdvancedFilterEngine(FilterEngine):
    """Advanced filtering engine with additional capabilities."""
    
    def __init__(self):
        """Initialize advanced filter engine."""
        super().__init__()
        self.operators.update({
            'fuzzy_match': self._fuzzy_match,
            'date_range': self._date_range,
            'percentile': self._percentile,
            'top_n': self._top_n,
            'bottom_n': self._bottom_n,
        })
    
    def apply_conditional_filters(self, data: List[Dict[str, Any]], 
                                conditional_filters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply conditional filters (AND/OR logic)."""
        if not conditional_filters:
            return data
        
        filtered_data = []
        
        for item in data:
            if self._evaluate_conditional_filters(item, conditional_filters):
                filtered_data.append(item)
        
        return filtered_data
    
    def _evaluate_conditional_filters(self, item: Dict[str, Any], 
                                    conditional_filters: List[Dict[str, Any]]) -> bool:
        """Evaluate conditional filter logic."""
        for condition in conditional_filters:
            logic = condition.get('logic', 'AND')
            filters = condition.get('filters', [])
            
            if logic == 'AND':
                if not all(self._evaluate_filter(item, f['field'], 
                                               self.operators[f['operator']], f['value']) 
                          for f in filters):
                    return False
            elif logic == 'OR':
                if not any(self._evaluate_filter(item, f['field'], 
                                               self.operators[f['operator']], f['value']) 
                          for f in filters):
                    return False
        
        return True
    
    def _fuzzy_match(self, field_value: Any, filter_value: Any) -> bool:
        """Fuzzy string matching."""
        try:
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, str(field_value).lower(), 
                                       str(filter_value).lower()).ratio()
            return similarity >= 0.8  # 80% similarity threshold
        except ImportError:
            # Fallback to contains if difflib not available
            return self._contains(field_value, filter_value)
    
    def _date_range(self, field_value: Any, filter_value: Dict[str, Any]) -> bool:
        """Date range filtering."""
        try:
            if isinstance(field_value, str):
                field_date = parse_date(field_value)
            elif hasattr(field_value, 'isoformat'):
                field_date = field_value
            else:
                return False
            
            start_date = parse_date(filter_value.get('start'))
            end_date = parse_date(filter_value.get('end'))
            
            return start_date <= field_date <= end_date
        except (ValueError, TypeError, KeyError):
            return False
    
    def _percentile(self, field_value: Any, filter_value: Dict[str, Any]) -> bool:
        """Percentile-based filtering."""
        # This would require the full dataset context
        # Implementation would depend on having access to all values
        return True  # Placeholder
    
    def _top_n(self, field_value: Any, filter_value: int) -> bool:
        """Top N filtering."""
        # This would require sorting context
        # Implementation would depend on having access to sorted data
        return True  # Placeholder
    
    def _bottom_n(self, field_value: Any, filter_value: int) -> bool:
        """Bottom N filtering."""
        # This would require sorting context
        # Implementation would depend on having access to sorted data
        return True  # Placeholder