"""
Aggregation engine for computing statistics and summaries.
"""
from typing import Any, Dict, List, Optional, Callable
from collections import defaultdict


class AggregationEngine:
    """Engine for performing aggregations on datasets."""
    
    def __init__(self):
        self._aggregations: Dict[str, Callable] = {
            'sum': self._sum,
            'avg': self._avg,
            'mean': self._avg,
            'min': self._min,
            'max': self._max,
            'count': self._count,
            'median': self._median,
            'std': self._std,
            'variance': self._variance,
        }
    
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
    
    def _extract_numeric_values(self, data: List[Dict[str, Any]], field: str) -> List[float]:
        """Extract numeric values from field."""
        values = []
        for item in data:
            value = self._get_nested_value(item, field)
            if value is not None and isinstance(value, (int, float)):
                values.append(float(value))
        return values
    
    def _sum(self, values: List[float]) -> float:
        """Calculate sum."""
        return sum(values) if values else 0.0
    
    def _avg(self, values: List[float]) -> float:
        """Calculate average."""
        return sum(values) / len(values) if values else 0.0
    
    def _min(self, values: List[float]) -> Optional[float]:
        """Calculate minimum."""
        return min(values) if values else None
    
    def _max(self, values: List[float]) -> Optional[float]:
        """Calculate maximum."""
        return max(values) if values else None
    
    def _count(self, values: List[Any]) -> int:
        """Count values."""
        return len(values)
    
    def _median(self, values: List[float]) -> Optional[float]:
        """Calculate median."""
        if not values:
            return None
        sorted_values = sorted(values)
        n = len(sorted_values)
        mid = n // 2
        if n % 2 == 0:
            return (sorted_values[mid - 1] + sorted_values[mid]) / 2
        return sorted_values[mid]
    
    def _std(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if not values or len(values) < 2:
            return 0.0
        mean = self._avg(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def _variance(self, values: List[float]) -> float:
        """Calculate variance."""
        if not values or len(values) < 2:
            return 0.0
        mean = self._avg(values)
        return sum((x - mean) ** 2 for x in values) / len(values)
    
    def aggregate(
        self, 
        data: List[Dict[str, Any]], 
        field: str, 
        operation: str
    ) -> Any:
        """
        Perform aggregation on a specific field.
        
        Args:
            data: List of dictionaries
            field: Field name to aggregate
            operation: Aggregation operation (sum, avg, min, max, count, etc.)
            
        Returns:
            Aggregated value
        """
        operation = operation.lower()
        agg_func = self._aggregations.get(operation)
        
        if not agg_func:
            raise ValueError(f"Unsupported aggregation operation: {operation}")
        
        if operation == 'count':
            return agg_func(data)
        
        values = self._extract_numeric_values(data, field)
        return agg_func(values)
    
    def aggregate_multiple(
        self,
        data: List[Dict[str, Any]],
        aggregations: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Perform multiple aggregations.
        
        Args:
            data: List of dictionaries
            aggregations: List of dicts with 'field' and 'operation' keys
            
        Returns:
            Dictionary of aggregation results
        """
        results = {}
        for agg in aggregations:
            field = agg.get('field')
            operation = agg.get('operation')
            
            if not field or not operation:
                continue
            
            key = f"{field}_{operation}"
            try:
                results[key] = self.aggregate(data, field, operation)
            except Exception as e:
                results[key] = None
        
        return results
    
    def group_by(
        self,
        data: List[Dict[str, Any]],
        group_field: str,
        agg_field: str,
        operation: str
    ) -> Dict[str, Any]:
        """
        Group by a field and perform aggregation.
        
        Args:
            data: List of dictionaries
            group_field: Field to group by
            agg_field: Field to aggregate
            operation: Aggregation operation
            
        Returns:
            Dictionary with grouped aggregation results
        """
        groups = defaultdict(list)
        
        for item in data:
            group_value = self._get_nested_value(item, group_field)
            if group_value is not None:
                groups[str(group_value)].append(item)
        
        results = {}
        for group_key, group_data in groups.items():
            try:
                results[group_key] = self.aggregate(group_data, agg_field, operation)
            except Exception:
                results[group_key] = None
        
        return results
    
    def rank(
        self,
        data: List[Dict[str, Any]],
        field: str,
        descending: bool = True,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rank items by a field value.
        
        Args:
            data: List of dictionaries
            field: Field to rank by
            descending: Sort in descending order (highest first)
            limit: Maximum number of results
            
        Returns:
            Sorted and ranked list
        """
        # Filter out items without the field
        valid_items = []
        for item in data:
            value = self._get_nested_value(item, field)
            if value is not None and isinstance(value, (int, float)):
                valid_items.append(item)
        
        # Sort by field value
        sorted_items = sorted(
            valid_items,
            key=lambda x: self._get_nested_value(x, field),
            reverse=descending
        )
        
        # Add rank
        for idx, item in enumerate(sorted_items):
            item['rank'] = idx + 1
        
        # Apply limit
        if limit:
            sorted_items = sorted_items[:limit]
        
        return sorted_items
    
    def compare(
        self,
        data: List[Dict[str, Any]],
        compare_field: str,
        fields_to_compare: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compare multiple entities side-by-side.
        
        Args:
            data: List of dictionaries
            compare_field: Field to identify entities (e.g., 'driver_id')
            fields_to_compare: List of fields to compare
            
        Returns:
            Dictionary with comparison results
        """
        comparison = {}
        
        for item in data:
            entity_id = self._get_nested_value(item, compare_field)
            if entity_id is None:
                continue
            
            entity_id = str(entity_id)
            if entity_id not in comparison:
                comparison[entity_id] = {}
            
            for field in fields_to_compare:
                value = self._get_nested_value(item, field)
                if value is not None:
                    comparison[entity_id][field] = value
        
        return comparison
    
    def percentile(
        self,
        data: List[Dict[str, Any]],
        field: str,
        percentile: float
    ) -> Optional[float]:
        """
        Calculate percentile value.
        
        Args:
            data: List of dictionaries
            field: Field to calculate percentile for
            percentile: Percentile value (0-100)
            
        Returns:
            Percentile value
        """
        values = self._extract_numeric_values(data, field)
        if not values:
            return None
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * (percentile / 100.0))
        index = min(index, len(sorted_values) - 1)
        
        return sorted_values[index]
