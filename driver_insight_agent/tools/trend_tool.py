"""
Trend Tool - Time-series and trend analysis.
Analyzes trends and patterns in driver metrics over time.
"""
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict


class TrendTool:
    """Tool for time-series and trend analysis."""
    
    def __init__(self):
        self.name = "trend_tool"
        self.description = "Analyzes time-series trends in driver metrics"
        self.version = "1.0.0"
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute trend analysis.
        
        Args:
            parameters: Dictionary containing:
                - driver_ids: List of driver IDs
                - metric: Metric to analyze (score, distance, trips, etc.)
                - start_date: Start date (ISO 8601)
                - end_date: End date (ISO 8601)
                - granularity: Time granularity (daily, weekly, monthly)
                - raw_data: Raw time-series data from other tools
                
        Returns:
            Dictionary with execution results
        """
        start_time = time.time()
        
        try:
            trends = await self._analyze_trends(parameters)
            
            execution_time = (time.time() - start_time) * 1000
            
            return {
                "success": True,
                "data": trends,
                "count": len(trends),
                "execution_time_ms": execution_time,
                "error": None
            }
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return {
                "success": False,
                "data": None,
                "count": 0,
                "execution_time_ms": execution_time,
                "error": str(e)
            }
    
    async def _analyze_trends(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze trends from provided data."""
        driver_ids = parameters.get('driver_ids', [])
        metric = parameters.get('metric', 'score')
        granularity = parameters.get('granularity', 'daily')
        raw_data = parameters.get('raw_data', [])
        
        # Group data by driver and time period
        grouped_data = self._group_by_time_period(raw_data, granularity, metric)
        
        # Calculate trends for each driver
        trends = []
        for driver_id in driver_ids:
            if driver_id in grouped_data:
                driver_trends = self._calculate_driver_trend(
                    driver_id,
                    grouped_data[driver_id],
                    metric
                )
                trends.extend(driver_trends)
        
        return trends
    
    def _group_by_time_period(
        self,
        data: List[Dict[str, Any]],
        granularity: str,
        metric: str
    ) -> Dict[str, Dict[str, List[float]]]:
        """Group data by time period and driver."""
        grouped = defaultdict(lambda: defaultdict(list))
        
        for item in data:
            driver_id = item.get('driver_id')
            date_str = item.get('date') or item.get('start_time')
            metric_value = item.get(metric)
            
            if not all([driver_id, date_str, metric_value is not None]):
                continue
            
            try:
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                period_key = self._get_period_key(date, granularity)
                grouped[driver_id][period_key].append(float(metric_value))
            except (ValueError, AttributeError):
                continue
        
        return grouped
    
    def _get_period_key(self, date: datetime, granularity: str) -> str:
        """Get period key based on granularity."""
        if granularity == 'daily':
            return date.strftime('%Y-%m-%d')
        elif granularity == 'weekly':
            return date.strftime('%Y-W%U')
        elif granularity == 'monthly':
            return date.strftime('%Y-%m')
        else:
            return date.strftime('%Y-%m-%d')
    
    def _calculate_driver_trend(
        self,
        driver_id: str,
        period_data: Dict[str, List[float]],
        metric: str
    ) -> List[Dict[str, Any]]:
        """Calculate trend data for a driver."""
        trend_points = []
        
        # Sort periods chronologically
        sorted_periods = sorted(period_data.keys())
        
        for period in sorted_periods:
            values = period_data[period]
            
            if not values:
                continue
            
            avg_value = sum(values) / len(values)
            
            trend_point = {
                "driver_id": driver_id,
                "period": period,
                "metric": metric,
                "value": round(avg_value, 2),
                "count": len(values),
                "min": round(min(values), 2),
                "max": round(max(values), 2)
            }
            
            trend_points.append(trend_point)
        
        # Add trend indicators
        if len(trend_points) >= 2:
            trend_points = self._add_trend_indicators(trend_points)
        
        return trend_points
    
    def _add_trend_indicators(
        self,
        trend_points: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Add trend direction and change indicators."""
        for i in range(len(trend_points)):
            if i == 0:
                trend_points[i]['trend'] = 'baseline'
                trend_points[i]['change'] = 0
                trend_points[i]['pct_change'] = 0
            else:
                prev_value = trend_points[i - 1]['value']
                curr_value = trend_points[i]['value']
                
                change = curr_value - prev_value
                pct_change = (change / prev_value * 100) if prev_value != 0 else 0
                
                if change > 0:
                    trend = 'increasing'
                elif change < 0:
                    trend = 'decreasing'
                else:
                    trend = 'stable'
                
                trend_points[i]['trend'] = trend
                trend_points[i]['change'] = round(change, 2)
                trend_points[i]['pct_change'] = round(pct_change, 2)
        
        return trend_points
    
    def calculate_moving_average(
        self,
        data: List[Dict[str, Any]],
        window: int = 7
    ) -> List[Dict[str, Any]]:
        """Calculate moving average for trend smoothing."""
        if len(data) < window:
            return data
        
        smoothed = []
        for i in range(len(data)):
            if i < window - 1:
                smoothed.append(data[i])
            else:
                window_data = data[i - window + 1:i + 1]
                avg_value = sum(d['value'] for d in window_data) / window
                
                smoothed_point = data[i].copy()
                smoothed_point['smoothed_value'] = round(avg_value, 2)
                smoothed.append(smoothed_point)
        
        return smoothed
    
    def detect_anomalies(
        self,
        data: List[Dict[str, Any]],
        threshold: float = 2.0
    ) -> List[Dict[str, Any]]:
        """Detect anomalies using standard deviation."""
        if len(data) < 3:
            return []
        
        values = [d['value'] for d in data]
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        
        anomalies = []
        for point in data:
            z_score = abs((point['value'] - mean) / std_dev) if std_dev > 0 else 0
            
            if z_score > threshold:
                anomaly = point.copy()
                anomaly['z_score'] = round(z_score, 2)
                anomaly['anomaly_type'] = 'high' if point['value'] > mean else 'low'
                anomalies.append(anomaly)
        
        return anomalies
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return tool capabilities."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parameters": {
                "driver_ids": {"type": "list", "required": True},
                "metric": {"type": "string", "required": True},
                "start_date": {"type": "string", "required": False},
                "end_date": {"type": "string", "required": False},
                "granularity": {"type": "string", "required": False, "default": "daily"},
                "raw_data": {"type": "list", "required": True}
            },
            "output_schema": {
                "success": "boolean",
                "data": "list[dict]",
                "count": "integer",
                "execution_time_ms": "float"
            }
        }
