"""Aggregation engine for statistical operations and data summarization."""

from typing import List, Dict, Any, Optional, Union, Callable
import statistics
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import numpy as np


class AggregationEngine:
    """Engine for performing data aggregations and statistical operations."""
    
    def __init__(self):
        """Initialize aggregation engine with operation mappings."""
        self.operations = {
            'count': self._count,
            'sum': self._sum,
            'avg': self._average,
            'mean': self._average,
            'median': self._median,
            'mode': self._mode,
            'min': self._minimum,
            'max': self._maximum,
            'std': self._standard_deviation,
            'var': self._variance,
            'percentile': self._percentile,
            'range': self._range,
            'distinct_count': self._distinct_count,
            'first': self._first,
            'last': self._last,
        }
    
    def aggregate(self, data: List[Dict[str, Any]], aggregations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform multiple aggregations on data."""
        results = {}
        
        for agg_config in aggregations:
            operation = agg_config.get('operation')
            field = agg_config.get('field')
            alias = agg_config.get('alias', f"{operation}_{field}")
            group_by = agg_config.get('group_by')
            
            if operation not in self.operations:
                raise ValueError(f"Unsupported aggregation operation: {operation}")
            
            if group_by:
                results[alias] = self._group_aggregate(data, field, operation, group_by)
            else:
                results[alias] = self._single_aggregate(data, field, operation, agg_config)
        
        return results
    
    def _single_aggregate(self, data: List[Dict[str, Any]], field: str, 
                         operation: str, config: Dict[str, Any]) -> Any:
        """Perform single aggregation on field."""
        values = self._extract_values(data, field)
        
        if not values:
            return None
        
        agg_func = self.operations[operation]
        
        # Handle operations that need additional parameters
        if operation == 'percentile':
            percentile = config.get('percentile', 50)
            return agg_func(values, percentile)
        
        return agg_func(values)
    
    def _group_aggregate(self, data: List[Dict[str, Any]], field: str, 
                        operation: str, group_by: str) -> Dict[str, Any]:
        """Perform grouped aggregation."""
        groups = defaultdict(list)
        
        # Group data by the specified field
        for item in data:
            group_value = self._get_nested_value(item, group_by)
            if group_value is not None:
                field_value = self._get_nested_value(item, field)
                if field_value is not None:
                    groups[str(group_value)].append(field_value)
        
        # Apply aggregation to each group
        results = {}
        agg_func = self.operations[operation]
        
        for group_key, group_values in groups.items():
            if group_values:
                results[group_key] = agg_func(group_values)
        
        return results
    
    def _extract_values(self, data: List[Dict[str, Any]], field: str) -> List[Any]:
        """Extract values for a specific field from data."""
        values = []
        
        for item in data:
            value = self._get_nested_value(item, field)
            if value is not None:
                values.append(value)
        
        return values
    
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
    
    # Aggregation operation implementations
    
    def _count(self, values: List[Any]) -> int:
        """Count non-null values."""
        return len([v for v in values if v is not None])
    
    def _sum(self, values: List[Any]) -> Union[int, float]:
        """Sum of numeric values."""
        numeric_values = self._to_numeric_list(values)
        return sum(numeric_values) if numeric_values else 0
    
    def _average(self, values: List[Any]) -> Optional[float]:
        """Average of numeric values."""
        numeric_values = self._to_numeric_list(values)
        return statistics.mean(numeric_values) if numeric_values else None
    
    def _median(self, values: List[Any]) -> Optional[float]:
        """Median of numeric values."""
        numeric_values = self._to_numeric_list(values)
        return statistics.median(numeric_values) if numeric_values else None
    
    def _mode(self, values: List[Any]) -> Any:
        """Mode (most common value)."""
        if not values:
            return None
        
        try:
            return statistics.mode(values)
        except statistics.StatisticsError:
            # No unique mode, return most common
            counter = Counter(values)
            return counter.most_common(1)[0][0] if counter else None
    
    def _minimum(self, values: List[Any]) -> Any:
        """Minimum value."""
        if not values:
            return None
        
        try:
            numeric_values = self._to_numeric_list(values)
            return min(numeric_values) if numeric_values else min(values)
        except (TypeError, ValueError):
            return min(values)
    
    def _maximum(self, values: List[Any]) -> Any:
        """Maximum value."""
        if not values:
            return None
        
        try:
            numeric_values = self._to_numeric_list(values)
            return max(numeric_values) if numeric_values else max(values)
        except (TypeError, ValueError):
            return max(values)
    
    def _standard_deviation(self, values: List[Any]) -> Optional[float]:
        """Standard deviation of numeric values."""
        numeric_values = self._to_numeric_list(values)
        if len(numeric_values) < 2:
            return None
        return statistics.stdev(numeric_values)
    
    def _variance(self, values: List[Any]) -> Optional[float]:
        """Variance of numeric values."""
        numeric_values = self._to_numeric_list(values)
        if len(numeric_values) < 2:
            return None
        return statistics.variance(numeric_values)
    
    def _percentile(self, values: List[Any], percentile: float = 50) -> Optional[float]:
        """Percentile of numeric values."""
        numeric_values = self._to_numeric_list(values)
        if not numeric_values:
            return None
        
        try:
            return np.percentile(numeric_values, percentile)
        except ImportError:
            # Fallback without numpy
            sorted_values = sorted(numeric_values)
            n = len(sorted_values)
            index = (percentile / 100) * (n - 1)
            
            if index.is_integer():
                return sorted_values[int(index)]
            else:
                lower = sorted_values[int(index)]
                upper = sorted_values[int(index) + 1]
                return lower + (upper - lower) * (index - int(index))
    
    def _range(self, values: List[Any]) -> Optional[float]:
        """Range (max - min) of numeric values."""
        numeric_values = self._to_numeric_list(values)
        if not numeric_values:
            return None
        return max(numeric_values) - min(numeric_values)
    
    def _distinct_count(self, values: List[Any]) -> int:
        """Count of distinct values."""
        return len(set(values))
    
    def _first(self, values: List[Any]) -> Any:
        """First value."""
        return values[0] if values else None
    
    def _last(self, values: List[Any]) -> Any:
        """Last value."""
        return values[-1] if values else None
    
    def _to_numeric_list(self, values: List[Any]) -> List[Union[int, float]]:
        """Convert values to numeric list, filtering out non-numeric values."""
        numeric_values = []
        
        for value in values:
            try:
                if isinstance(value, (int, float)):
                    numeric_values.append(value)
                elif isinstance(value, str):
                    # Try to convert string to number
                    if '.' in value:
                        numeric_values.append(float(value))
                    else:
                        numeric_values.append(int(value))
            except (ValueError, TypeError):
                continue
        
        return numeric_values


class AdvancedAggregationEngine(AggregationEngine):
    """Advanced aggregation engine with additional statistical operations."""
    
    def __init__(self):
        """Initialize advanced aggregation engine."""
        super().__init__()
        self.operations.update({
            'correlation': self._correlation,
            'covariance': self._covariance,
            'zscore': self._zscore,
            'rank': self._rank,
            'rolling_avg': self._rolling_average,
            'cumulative_sum': self._cumulative_sum,
            'growth_rate': self._growth_rate,
            'quartiles': self._quartiles,
        })
    
    def compare_aggregations(self, data1: List[Dict[str, Any]], data2: List[Dict[str, Any]], 
                           field: str, operations: List[str]) -> Dict[str, Dict[str, Any]]:
        """Compare aggregations between two datasets."""
        results = {}
        
        for operation in operations:
            if operation not in self.operations:
                continue
            
            agg_func = self.operations[operation]
            values1 = self._extract_values(data1, field)
            values2 = self._extract_values(data2, field)
            
            result1 = agg_func(values1) if values1 else None
            result2 = agg_func(values2) if values2 else None
            
            results[operation] = {
                'dataset1': result1,
                'dataset2': result2,
                'difference': self._calculate_difference(result1, result2),
                'percent_change': self._calculate_percent_change(result1, result2)
            }
        
        return results
    
    def time_series_aggregation(self, data: List[Dict[str, Any]], 
                              time_field: str, value_field: str, 
                              interval: str = 'day') -> Dict[str, Any]:
        """Perform time-series aggregation."""
        time_groups = defaultdict(list)
        
        for item in data:
            time_value = self._get_nested_value(item, time_field)
            value = self._get_nested_value(item, value_field)
            
            if time_value and value is not None:
                time_key = self._get_time_key(time_value, interval)
                time_groups[time_key].append(value)
        
        # Calculate aggregations for each time period
        results = {}
        for time_key, values in sorted(time_groups.items()):
            results[time_key] = {
                'count': len(values),
                'sum': sum(self._to_numeric_list(values)),
                'avg': statistics.mean(self._to_numeric_list(values)) if values else 0,
                'min': min(self._to_numeric_list(values)) if values else 0,
                'max': max(self._to_numeric_list(values)) if values else 0,
            }
        
        return results
    
    def ranking_aggregation(self, data: List[Dict[str, Any]], 
                          rank_field: str, group_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """Create rankings based on field values."""
        if group_by:
            return self._grouped_ranking(data, rank_field, group_by)
        else:
            return self._simple_ranking(data, rank_field)
    
    def _simple_ranking(self, data: List[Dict[str, Any]], rank_field: str) -> List[Dict[str, Any]]:
        """Create simple ranking."""
        # Extract values with original items
        items_with_values = []
        for item in data:
            value = self._get_nested_value(item, rank_field)
            if value is not None:
                items_with_values.append((item, value))
        
        # Sort by value (descending)
        items_with_values.sort(key=lambda x: x[1], reverse=True)
        
        # Add rank to items
        ranked_items = []
        for rank, (item, value) in enumerate(items_with_values, 1):
            ranked_item = item.copy()
            ranked_item['rank'] = rank
            ranked_item['rank_value'] = value
            ranked_items.append(ranked_item)
        
        return ranked_items
    
    def _grouped_ranking(self, data: List[Dict[str, Any]], 
                        rank_field: str, group_by: str) -> List[Dict[str, Any]]:
        """Create grouped ranking."""
        groups = defaultdict(list)
        
        # Group data
        for item in data:
            group_value = self._get_nested_value(item, group_by)
            if group_value is not None:
                groups[str(group_value)].append(item)
        
        # Rank within each group
        all_ranked_items = []
        for group_key, group_items in groups.items():
            ranked_group = self._simple_ranking(group_items, rank_field)
            for item in ranked_group:
                item['group'] = group_key
            all_ranked_items.extend(ranked_group)
        
        return all_ranked_items
    
    # Advanced aggregation implementations
    
    def _correlation(self, values: List[Any], other_values: List[Any] = None) -> Optional[float]:
        """Calculate correlation coefficient."""
        if other_values is None or len(values) != len(other_values):
            return None
        
        numeric_values1 = self._to_numeric_list(values)
        numeric_values2 = self._to_numeric_list(other_values)
        
        if len(numeric_values1) < 2 or len(numeric_values1) != len(numeric_values2):
            return None
        
        try:
            return statistics.correlation(numeric_values1, numeric_values2)
        except (statistics.StatisticsError, AttributeError):
            # Fallback calculation
            return self._manual_correlation(numeric_values1, numeric_values2)
    
    def _manual_correlation(self, x: List[float], y: List[float]) -> float:
        """Manual correlation calculation."""
        n = len(x)
        if n == 0:
            return 0
        
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        sum_sq_x = sum((x[i] - mean_x) ** 2 for i in range(n))
        sum_sq_y = sum((y[i] - mean_y) ** 2 for i in range(n))
        
        denominator = (sum_sq_x * sum_sq_y) ** 0.5
        
        return numerator / denominator if denominator != 0 else 0
    
    def _quartiles(self, values: List[Any]) -> Optional[Dict[str, float]]:
        """Calculate quartiles."""
        numeric_values = self._to_numeric_list(values)
        if not numeric_values:
            return None
        
        return {
            'q1': self._percentile(values, 25),
            'q2': self._percentile(values, 50),  # median
            'q3': self._percentile(values, 75),
            'iqr': self._percentile(values, 75) - self._percentile(values, 25)
        }
    
    def _get_time_key(self, time_value: Any, interval: str) -> str:
        """Get time key for grouping."""
        if isinstance(time_value, str):
            try:
                from dateutil.parser import parse as parse_date
                dt = parse_date(time_value)
            except:
                return str(time_value)
        elif hasattr(time_value, 'strftime'):
            dt = time_value
        else:
            return str(time_value)
        
        if interval == 'hour':
            return dt.strftime('%Y-%m-%d %H:00')
        elif interval == 'day':
            return dt.strftime('%Y-%m-%d')
        elif interval == 'week':
            return dt.strftime('%Y-W%U')
        elif interval == 'month':
            return dt.strftime('%Y-%m')
        elif interval == 'year':
            return dt.strftime('%Y')
        else:
            return dt.strftime('%Y-%m-%d')
    
    def _calculate_difference(self, value1: Any, value2: Any) -> Optional[float]:
        """Calculate difference between two values."""
        try:
            if value1 is None or value2 is None:
                return None
            return float(value2) - float(value1)
        except (TypeError, ValueError):
            return None
    
    def _calculate_percent_change(self, value1: Any, value2: Any) -> Optional[float]:
        """Calculate percent change between two values."""
        try:
            if value1 is None or value2 is None or float(value1) == 0:
                return None
            return ((float(value2) - float(value1)) / float(value1)) * 100
        except (TypeError, ValueError, ZeroDivisionError):
            return None