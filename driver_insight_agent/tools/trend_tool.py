"""Trend analysis tool for time-series and pattern analysis."""

from typing import Dict, List, Any, Optional, Union, Tuple
import asyncio
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date
import statistics

from ..utils.validation import TimeRange, ValidationError
from ..utils.filter_engine import FilterEngine
from ..utils.aggregation_engine import AdvancedAggregationEngine
from ..utils.pagination import PaginationEngine
from ..cache.cache_manager import get_cache_manager


@dataclass
class TrendDataPoint:
    """Individual trend data point."""
    timestamp: datetime
    metric_name: str
    metric_value: float
    driver_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class TrendDataSource:
    """Mock data source for trend analysis."""
    
    def __init__(self):
        """Initialize with sample trend data."""
        self.trend_data = self._generate_sample_trend_data()
    
    def _generate_sample_trend_data(self) -> List[TrendDataPoint]:
        """Generate sample trend data."""
        data_points = []
        driver_ids = ["DRV001", "DRV002", "DRV003", "DRV004", "DRV005"]
        metrics = ["overall_score", "safety_score", "efficiency_score", "trip_count", "distance_total", "fuel_efficiency"]
        
        # Generate daily data for the last 90 days
        base_date = datetime.now() - timedelta(days=90)
        
        for day in range(90):
            current_date = base_date + timedelta(days=day)
            
            for driver_id in driver_ids:
                # Generate base values with some consistency per driver
                base_values = {
                    "DRV001": {"overall_score": 85, "safety_score": 88, "efficiency_score": 82, "trip_count": 12, "distance_total": 150, "fuel_efficiency": 25},
                    "DRV002": {"overall_score": 78, "safety_score": 75, "efficiency_score": 80, "trip_count": 10, "distance_total": 120, "fuel_efficiency": 23},
                    "DRV003": {"overall_score": 92, "safety_score": 95, "efficiency_score": 89, "trip_count": 15, "distance_total": 180, "fuel_efficiency": 28},
                    "DRV004": {"overall_score": 71, "safety_score": 68, "efficiency_score": 74, "trip_count": 8, "distance_total": 100, "fuel_efficiency": 21},
                    "DRV005": {"overall_score": 88, "safety_score": 90, "efficiency_score": 86, "trip_count": 13, "distance_total": 160, "fuel_efficiency": 26}
                }[driver_id]
                
                for metric in metrics:
                    base_value = base_values[metric]
                    
                    # Add seasonal trends
                    seasonal_factor = 1 + 0.1 * math.sin(2 * math.pi * day / 365)  # Annual cycle
                    weekly_factor = 1 + 0.05 * math.sin(2 * math.pi * day / 7)    # Weekly cycle
                    
                    # Add some random variation
                    random_factor = random.uniform(0.9, 1.1)
                    
                    # Add gradual improvement/decline trend
                    trend_factor = 1 + (day / 365) * random.uniform(-0.1, 0.1)  # Annual trend
                    
                    final_value = base_value * seasonal_factor * weekly_factor * random_factor * trend_factor
                    
                    # Ensure realistic bounds
                    if metric.endswith('_score'):
                        final_value = max(0, min(100, final_value))
                    elif metric == 'trip_count':
                        final_value = max(0, int(final_value))
                    elif metric == 'distance_total':
                        final_value = max(0, final_value)
                    elif metric == 'fuel_efficiency':
                        final_value = max(10, min(40, final_value))
                    
                    data_point = TrendDataPoint(
                        timestamp=current_date,
                        metric_name=metric,
                        metric_value=round(final_value, 2),
                        driver_id=driver_id,
                        context={
                            "day_of_week": current_date.strftime("%A"),
                            "month": current_date.strftime("%B"),
                            "quarter": f"Q{(current_date.month - 1) // 3 + 1}",
                            "is_weekend": current_date.weekday() >= 5
                        }
                    )
                    data_points.append(data_point)
        
        return data_points
    
    async def get_trend_data(self, metric_names: List[str],
                           driver_ids: Optional[List[str]] = None,
                           time_range: Optional[TimeRange] = None) -> List[TrendDataPoint]:
        """Get trend data for specified metrics and drivers."""
        filtered_data = []
        
        for data_point in self.trend_data:
            # Filter by metric names
            if data_point.metric_name not in metric_names:
                continue
            
            # Filter by driver IDs
            if driver_ids and data_point.driver_id not in driver_ids:
                continue
            
            # Filter by time range
            if time_range:
                if not (time_range.start_date <= data_point.timestamp <= time_range.end_date):
                    continue
            
            filtered_data.append(data_point)
        
        return filtered_data
    
    async def get_aggregated_trend_data(self, metric_name: str,
                                      aggregation_period: str = "daily",
                                      driver_ids: Optional[List[str]] = None,
                                      time_range: Optional[TimeRange] = None) -> List[TrendDataPoint]:
        """Get aggregated trend data."""
        # Get raw data
        raw_data = await self.get_trend_data([metric_name], driver_ids, time_range)
        
        # Group by time period
        from collections import defaultdict
        grouped_data = defaultdict(list)
        
        for data_point in raw_data:
            if aggregation_period == "daily":
                key = data_point.timestamp.date()
            elif aggregation_period == "weekly":
                # Get Monday of the week
                monday = data_point.timestamp - timedelta(days=data_point.timestamp.weekday())
                key = monday.date()
            elif aggregation_period == "monthly":
                key = data_point.timestamp.replace(day=1).date()
            else:
                key = data_point.timestamp.date()
            
            grouped_data[key].append(data_point)
        
        # Aggregate each group
        aggregated_data = []
        for period_key, period_data in grouped_data.items():
            values = [dp.metric_value for dp in period_data]
            avg_value = statistics.mean(values) if values else 0
            
            aggregated_point = TrendDataPoint(
                timestamp=datetime.combine(period_key, datetime.min.time()),
                metric_name=metric_name,
                metric_value=round(avg_value, 2),
                driver_id=None,  # Aggregated across drivers
                context={
                    "aggregation_period": aggregation_period,
                    "data_points_count": len(period_data),
                    "min_value": min(values) if values else 0,
                    "max_value": max(values) if values else 0
                }
            )
            aggregated_data.append(aggregated_point)
        
        return sorted(aggregated_data, key=lambda x: x.timestamp)


# Add math import at the top
import math


class TrendTool:
    """Tool for time-series and trend analysis."""
    
    def __init__(self):
        """Initialize trend tool."""
        self.data_source = TrendDataSource()
        self.filter_engine = FilterEngine()
        self.aggregation_engine = AdvancedAggregationEngine()
        self.pagination_engine = PaginationEngine()
        self.cache_manager = get_cache_manager()
        
        # Tool metadata
        self.name = "trend_tool"
        self.description = "Time-series and trend analysis for driver metrics"
        self.version = "1.0.0"
    
    async def analyze_driver_trends(self, driver_id: str,
                                  metrics: List[str],
                                  time_range: Optional[Dict[str, str]] = None,
                                  aggregation_period: str = "daily") -> Dict[str, Any]:
        """Analyze trends for a specific driver."""
        try:
            # Check cache first
            cache_key = self._generate_cache_key("driver_trends", driver_id, metrics, time_range, aggregation_period)
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                return cached_result
            
            # Parse time range if provided
            parsed_time_range = None
            if time_range:
                try:
                    parsed_time_range = TimeRange(
                        start_date=parse_date(time_range['start_date']),
                        end_date=parse_date(time_range['end_date'])
                    )
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Invalid time range: {str(e)}",
                        "data": None
                    }
            
            # Get trend data
            trend_data = await self.data_source.get_trend_data(metrics, [driver_id], parsed_time_range)
            
            # Analyze trends for each metric
            metric_trends = {}
            for metric in metrics:
                metric_data = [dp for dp in trend_data if dp.metric_name == metric]
                if metric_data:
                    trend_analysis = await self._analyze_metric_trend(metric_data, aggregation_period)
                    metric_trends[metric] = trend_analysis
            
            # Calculate overall trend summary
            trend_summary = await self._calculate_trend_summary(metric_trends)
            
            result = {
                "success": True,
                "data": {
                    "driver_id": driver_id,
                    "metric_trends": metric_trends,
                    "trend_summary": trend_summary,
                    "analysis_settings": {
                        "metrics": metrics,
                        "time_range": time_range,
                        "aggregation_period": aggregation_period
                    }
                },
                "metadata": {
                    "tool": self.name,
                    "version": self.version,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Cache result
            await self.cache_manager.set(cache_key, result, ttl=3600, 
                                       tags=['driver_trends', f'driver_{driver_id}'])
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to analyze driver trends: {str(e)}",
                "data": None
            }
    
    async def compare_trend_patterns(self, driver_ids: List[str],
                                   metric: str,
                                   time_range: Optional[Dict[str, str]] = None,
                                   aggregation_period: str = "weekly") -> Dict[str, Any]:
        """Compare trend patterns between multiple drivers."""
        try:
            # Check cache first
            cache_key = self._generate_cache_key("compare_trends", driver_ids, metric, time_range, aggregation_period)
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                return cached_result
            
            # Parse time range if provided
            parsed_time_range = None
            if time_range:
                try:
                    parsed_time_range = TimeRange(
                        start_date=parse_date(time_range['start_date']),
                        end_date=parse_date(time_range['end_date'])
                    )
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Invalid time range: {str(e)}",
                        "data": None
                    }
            
            # Get trend data for each driver
            driver_comparisons = {}
            
            for driver_id in driver_ids:
                trend_data = await self.data_source.get_trend_data([metric], [driver_id], parsed_time_range)
                metric_data = [dp for dp in trend_data if dp.metric_name == metric]
                
                if metric_data:
                    trend_analysis = await self._analyze_metric_trend(metric_data, aggregation_period)
                    driver_comparisons[driver_id] = trend_analysis
            
            # Calculate comparative analysis
            comparative_analysis = await self._calculate_comparative_analysis(driver_comparisons, metric)
            
            result = {
                "success": True,
                "data": {
                    "metric": metric,
                    "driver_comparisons": driver_comparisons,
                    "comparative_analysis": comparative_analysis,
                    "analysis_settings": {
                        "driver_ids": driver_ids,
                        "time_range": time_range,
                        "aggregation_period": aggregation_period
                    }
                },
                "metadata": {
                    "tool": self.name,
                    "version": self.version,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Cache result
            cache_tags = ['trend_comparison'] + [f'driver_{driver_id}' for driver_id in driver_ids]
            await self.cache_manager.set(cache_key, result, ttl=3600, tags=cache_tags)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to compare trend patterns: {str(e)}",
                "data": None
            }
    
    async def detect_anomalies(self, driver_ids: Optional[List[str]] = None,
                             metrics: Optional[List[str]] = None,
                             time_range: Optional[Dict[str, str]] = None,
                             sensitivity: float = 2.0) -> Dict[str, Any]:
        """Detect anomalies in trend data."""
        try:
            metrics = metrics or ["overall_score", "safety_score", "efficiency_score"]
            
            # Check cache first
            cache_key = self._generate_cache_key("detect_anomalies", driver_ids, metrics, time_range, sensitivity)
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                return cached_result
            
            # Parse time range if provided
            parsed_time_range = None
            if time_range:
                try:
                    parsed_time_range = TimeRange(
                        start_date=parse_date(time_range['start_date']),
                        end_date=parse_date(time_range['end_date'])
                    )
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Invalid time range: {str(e)}",
                        "data": None
                    }
            
            # Get trend data
            trend_data = await self.data_source.get_trend_data(metrics, driver_ids, parsed_time_range)
            
            # Detect anomalies for each driver-metric combination
            anomalies = await self._detect_statistical_anomalies(trend_data, sensitivity)
            
            # Categorize anomalies
            categorized_anomalies = await self._categorize_anomalies(anomalies)
            
            result = {
                "success": True,
                "data": {
                    "anomalies": anomalies,
                    "categorized_anomalies": categorized_anomalies,
                    "detection_settings": {
                        "driver_ids": driver_ids,
                        "metrics": metrics,
                        "time_range": time_range,
                        "sensitivity": sensitivity
                    },
                    "summary": {
                        "total_anomalies": len(anomalies),
                        "drivers_affected": len(set(a["driver_id"] for a in anomalies)),
                        "metrics_affected": len(set(a["metric_name"] for a in anomalies))
                    }
                },
                "metadata": {
                    "tool": self.name,
                    "version": self.version,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Cache result
            cache_tags = ['anomaly_detection']
            if driver_ids:
                cache_tags.extend([f'driver_{driver_id}' for driver_id in driver_ids])
            
            await self.cache_manager.set(cache_key, result, ttl=1800, tags=cache_tags)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to detect anomalies: {str(e)}",
                "data": None
            }
    
    async def forecast_trends(self, driver_id: str,
                            metric: str,
                            forecast_days: int = 30,
                            time_range: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Generate trend forecasts for a driver and metric."""
        try:
            # Check cache first
            cache_key = self._generate_cache_key("forecast_trends", driver_id, metric, forecast_days, time_range)
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                return cached_result
            
            # Parse time range if provided
            parsed_time_range = None
            if time_range:
                try:
                    parsed_time_range = TimeRange(
                        start_date=parse_date(time_range['start_date']),
                        end_date=parse_date(time_range['end_date'])
                    )
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Invalid time range: {str(e)}",
                        "data": None
                    }
            
            # Get historical trend data
            trend_data = await self.data_source.get_trend_data([metric], [driver_id], parsed_time_range)
            metric_data = [dp for dp in trend_data if dp.metric_name == metric]
            
            if len(metric_data) < 10:  # Need minimum data points for forecasting
                return {
                    "success": False,
                    "error": "Insufficient historical data for forecasting (minimum 10 data points required)",
                    "data": None
                }
            
            # Generate forecast
            forecast_data = await self._generate_simple_forecast(metric_data, forecast_days)
            
            # Calculate forecast confidence
            forecast_confidence = await self._calculate_forecast_confidence(metric_data, forecast_data)
            
            result = {
                "success": True,
                "data": {
                    "driver_id": driver_id,
                    "metric": metric,
                    "historical_data": [self._data_point_to_dict(dp) for dp in metric_data[-30:]],  # Last 30 points
                    "forecast_data": forecast_data,
                    "forecast_confidence": forecast_confidence,
                    "forecast_settings": {
                        "forecast_days": forecast_days,
                        "historical_data_points": len(metric_data),
                        "time_range": time_range
                    }
                },
                "metadata": {
                    "tool": self.name,
                    "version": self.version,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Cache result
            await self.cache_manager.set(cache_key, result, ttl=7200, 
                                       tags=['trend_forecast', f'driver_{driver_id}'])
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to forecast trends: {str(e)}",
                "data": None
            }
    
    async def get_seasonal_patterns(self, metrics: List[str],
                                  driver_ids: Optional[List[str]] = None,
                                  pattern_type: str = "weekly") -> Dict[str, Any]:
        """Identify seasonal patterns in trend data."""
        try:
            # Check cache first
            cache_key = self._generate_cache_key("seasonal_patterns", metrics, driver_ids, pattern_type)
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                return cached_result
            
            # Get trend data (use full dataset for pattern analysis)
            trend_data = await self.data_source.get_trend_data(metrics, driver_ids)
            
            # Analyze patterns for each metric
            seasonal_patterns = {}
            for metric in metrics:
                metric_data = [dp for dp in trend_data if dp.metric_name == metric]
                if metric_data:
                    patterns = await self._analyze_seasonal_patterns(metric_data, pattern_type)
                    seasonal_patterns[metric] = patterns
            
            # Calculate pattern summary
            pattern_summary = await self._calculate_pattern_summary(seasonal_patterns)
            
            result = {
                "success": True,
                "data": {
                    "seasonal_patterns": seasonal_patterns,
                    "pattern_summary": pattern_summary,
                    "analysis_settings": {
                        "metrics": metrics,
                        "driver_ids": driver_ids,
                        "pattern_type": pattern_type
                    }
                },
                "metadata": {
                    "tool": self.name,
                    "version": self.version,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Cache result
            cache_tags = ['seasonal_patterns'] + [f'metric_{metric}' for metric in metrics]
            if driver_ids:
                cache_tags.extend([f'driver_{driver_id}' for driver_id in driver_ids])
            
            await self.cache_manager.set(cache_key, result, ttl=7200, tags=cache_tags)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to analyze seasonal patterns: {str(e)}",
                "data": None
            }
    
    async def _analyze_metric_trend(self, metric_data: List[TrendDataPoint], 
                                  aggregation_period: str) -> Dict[str, Any]:
        """Analyze trend for a single metric."""
        if not metric_data:
            return {}
        
        # Sort by timestamp
        sorted_data = sorted(metric_data, key=lambda x: x.timestamp)
        values = [dp.metric_value for dp in sorted_data]
        
        # Calculate basic statistics
        trend_stats = {
            "data_points": len(values),
            "start_value": values[0],
            "end_value": values[-1],
            "min_value": min(values),
            "max_value": max(values),
            "avg_value": round(statistics.mean(values), 2),
            "std_dev": round(statistics.stdev(values) if len(values) > 1 else 0, 2)
        }
        
        # Calculate trend direction and magnitude
        if len(values) >= 2:
            # Simple linear trend
            n = len(values)
            x_values = list(range(n))
            
            # Calculate linear regression slope
            x_mean = statistics.mean(x_values)
            y_mean = statistics.mean(values)
            
            numerator = sum((x_values[i] - x_mean) * (values[i] - y_mean) for i in range(n))
            denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
            
            slope = numerator / denominator if denominator != 0 else 0
            
            # Determine trend direction
            if slope > 0.1:
                trend_direction = "increasing"
            elif slope < -0.1:
                trend_direction = "decreasing"
            else:
                trend_direction = "stable"
            
            trend_stats.update({
                "trend_slope": round(slope, 4),
                "trend_direction": trend_direction,
                "total_change": round(values[-1] - values[0], 2),
                "percent_change": round(((values[-1] - values[0]) / values[0]) * 100, 2) if values[0] != 0 else 0
            })
        
        # Calculate volatility
        if len(values) > 1:
            # Calculate rolling changes
            changes = [values[i] - values[i-1] for i in range(1, len(values))]
            volatility = statistics.stdev(changes) if len(changes) > 1 else 0
            trend_stats["volatility"] = round(volatility, 2)
        
        # Time series data for visualization
        time_series = [
            {
                "timestamp": dp.timestamp.isoformat(),
                "value": dp.metric_value
            }
            for dp in sorted_data
        ]
        
        return {
            "statistics": trend_stats,
            "time_series": time_series[-50:],  # Last 50 points for visualization
            "analysis_period": {
                "start": sorted_data[0].timestamp.isoformat(),
                "end": sorted_data[-1].timestamp.isoformat(),
                "duration_days": (sorted_data[-1].timestamp - sorted_data[0].timestamp).days
            }
        }
    
    async def _calculate_trend_summary(self, metric_trends: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall trend summary across metrics."""
        if not metric_trends:
            return {}
        
        # Count trend directions
        trend_directions = {}
        total_metrics = len(metric_trends)
        
        for metric, trend_data in metric_trends.items():
            direction = trend_data.get("statistics", {}).get("trend_direction", "unknown")
            trend_directions[direction] = trend_directions.get(direction, 0) + 1
        
        # Calculate overall performance indicator
        increasing_count = trend_directions.get("increasing", 0)
        decreasing_count = trend_directions.get("decreasing", 0)
        
        if increasing_count > decreasing_count:
            overall_trend = "improving"
        elif decreasing_count > increasing_count:
            overall_trend = "declining"
        else:
            overall_trend = "mixed"
        
        return {
            "overall_trend": overall_trend,
            "trend_distribution": trend_directions,
            "metrics_analyzed": total_metrics,
            "improvement_rate": round(increasing_count / total_metrics, 2) if total_metrics > 0 else 0
        }
    
    async def _calculate_comparative_analysis(self, driver_comparisons: Dict[str, Any], 
                                            metric: str) -> Dict[str, Any]:
        """Calculate comparative analysis between drivers."""
        if not driver_comparisons:
            return {}
        
        # Extract trend statistics for comparison
        driver_stats = {}
        for driver_id, trend_data in driver_comparisons.items():
            stats = trend_data.get("statistics", {})
            driver_stats[driver_id] = {
                "avg_value": stats.get("avg_value", 0),
                "trend_slope": stats.get("trend_slope", 0),
                "volatility": stats.get("volatility", 0),
                "percent_change": stats.get("percent_change", 0)
            }
        
        # Rank drivers by different criteria
        rankings = {}
        
        # Rank by average performance
        avg_ranking = sorted(driver_stats.items(), key=lambda x: x[1]["avg_value"], reverse=True)
        rankings["by_average_performance"] = [
            {"driver_id": driver, "value": stats["avg_value"], "rank": i+1}
            for i, (driver, stats) in enumerate(avg_ranking)
        ]
        
        # Rank by improvement trend
        trend_ranking = sorted(driver_stats.items(), key=lambda x: x[1]["trend_slope"], reverse=True)
        rankings["by_improvement_trend"] = [
            {"driver_id": driver, "value": stats["trend_slope"], "rank": i+1}
            for i, (driver, stats) in enumerate(trend_ranking)
        ]
        
        # Rank by consistency (inverse of volatility)
        consistency_ranking = sorted(driver_stats.items(), key=lambda x: x[1]["volatility"])
        rankings["by_consistency"] = [
            {"driver_id": driver, "value": stats["volatility"], "rank": i+1}
            for i, (driver, stats) in enumerate(consistency_ranking)
        ]
        
        # Calculate performance gaps
        if avg_ranking:
            best_performer = avg_ranking[0][1]["avg_value"]
            worst_performer = avg_ranking[-1][1]["avg_value"]
            performance_gap = best_performer - worst_performer
        else:
            performance_gap = 0
        
        return {
            "rankings": rankings,
            "performance_gap": round(performance_gap, 2),
            "drivers_compared": len(driver_comparisons),
            "metric_analyzed": metric
        }
    
    async def _detect_statistical_anomalies(self, trend_data: List[TrendDataPoint], 
                                          sensitivity: float) -> List[Dict[str, Any]]:
        """Detect statistical anomalies in trend data."""
        anomalies = []
        
        # Group data by driver and metric
        from collections import defaultdict
        grouped_data = defaultdict(list)
        
        for dp in trend_data:
            key = (dp.driver_id, dp.metric_name)
            grouped_data[key].append(dp)
        
        # Detect anomalies for each group
        for (driver_id, metric_name), data_points in grouped_data.items():
            if len(data_points) < 10:  # Need minimum data for statistical analysis
                continue
            
            values = [dp.metric_value for dp in data_points]
            mean_value = statistics.mean(values)
            std_dev = statistics.stdev(values) if len(values) > 1 else 0
            
            if std_dev == 0:  # No variation, skip
                continue
            
            # Detect outliers using z-score
            threshold = sensitivity  # Standard deviations from mean
            
            for dp in data_points:
                z_score = abs(dp.metric_value - mean_value) / std_dev
                
                if z_score > threshold:
                    anomaly_type = "high" if dp.metric_value > mean_value else "low"
                    
                    anomalies.append({
                        "driver_id": driver_id,
                        "metric_name": metric_name,
                        "timestamp": dp.timestamp.isoformat(),
                        "value": dp.metric_value,
                        "expected_range": {
                            "min": round(mean_value - threshold * std_dev, 2),
                            "max": round(mean_value + threshold * std_dev, 2)
                        },
                        "z_score": round(z_score, 2),
                        "anomaly_type": anomaly_type,
                        "severity": "high" if z_score > sensitivity * 1.5 else "medium"
                    })
        
        return sorted(anomalies, key=lambda x: x["z_score"], reverse=True)
    
    async def _categorize_anomalies(self, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Categorize detected anomalies."""
        if not anomalies:
            return {}
        
        categories = {
            "by_severity": {"high": 0, "medium": 0, "low": 0},
            "by_type": {"high": 0, "low": 0},
            "by_metric": {},
            "by_driver": {}
        }
        
        for anomaly in anomalies:
            # By severity
            severity = anomaly.get("severity", "medium")
            categories["by_severity"][severity] += 1
            
            # By type
            anomaly_type = anomaly.get("anomaly_type", "unknown")
            categories["by_type"][anomaly_type] = categories["by_type"].get(anomaly_type, 0) + 1
            
            # By metric
            metric = anomaly.get("metric_name", "unknown")
            categories["by_metric"][metric] = categories["by_metric"].get(metric, 0) + 1
            
            # By driver
            driver = anomaly.get("driver_id", "unknown")
            categories["by_driver"][driver] = categories["by_driver"].get(driver, 0) + 1
        
        return categories
    
    async def _generate_simple_forecast(self, historical_data: List[TrendDataPoint], 
                                      forecast_days: int) -> List[Dict[str, Any]]:
        """Generate simple trend forecast."""
        if len(historical_data) < 2:
            return []
        
        # Sort by timestamp
        sorted_data = sorted(historical_data, key=lambda x: x.timestamp)
        values = [dp.metric_value for dp in sorted_data]
        
        # Calculate trend using linear regression
        n = len(values)
        x_values = list(range(n))
        
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(values)
        
        numerator = sum((x_values[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        intercept = y_mean - slope * x_mean
        
        # Generate forecast points
        forecast_data = []
        last_timestamp = sorted_data[-1].timestamp
        
        for day in range(1, forecast_days + 1):
            forecast_timestamp = last_timestamp + timedelta(days=day)
            forecast_value = intercept + slope * (n + day - 1)
            
            # Add some uncertainty bounds (simple approach)
            std_dev = statistics.stdev(values) if len(values) > 1 else 0
            
            forecast_data.append({
                "timestamp": forecast_timestamp.isoformat(),
                "predicted_value": round(forecast_value, 2),
                "confidence_interval": {
                    "lower": round(forecast_value - 1.96 * std_dev, 2),
                    "upper": round(forecast_value + 1.96 * std_dev, 2)
                }
            })
        
        return forecast_data
    
    async def _calculate_forecast_confidence(self, historical_data: List[TrendDataPoint], 
                                           forecast_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate forecast confidence metrics."""
        if not historical_data or not forecast_data:
            return {}
        
        values = [dp.metric_value for dp in historical_data]
        
        # Calculate historical volatility
        if len(values) > 1:
            volatility = statistics.stdev(values)
            mean_value = statistics.mean(values)
            coefficient_of_variation = volatility / mean_value if mean_value != 0 else 0
        else:
            volatility = 0
            coefficient_of_variation = 0
        
        # Confidence decreases with forecast horizon and increases with data stability
        data_quality_score = min(1.0, len(historical_data) / 30)  # More data = higher quality
        stability_score = max(0.1, 1.0 - coefficient_of_variation)  # Lower volatility = higher stability
        
        base_confidence = (data_quality_score + stability_score) / 2
        
        return {
            "base_confidence": round(base_confidence, 2),
            "data_quality_score": round(data_quality_score, 2),
            "stability_score": round(stability_score, 2),
            "historical_volatility": round(volatility, 2),
            "forecast_horizon_days": len(forecast_data),
            "confidence_note": "Confidence decreases with longer forecast horizons"
        }
    
    async def _analyze_seasonal_patterns(self, metric_data: List[TrendDataPoint], 
                                       pattern_type: str) -> Dict[str, Any]:
        """Analyze seasonal patterns in metric data."""
        if not metric_data:
            return {}
        
        # Group data by pattern type
        from collections import defaultdict
        pattern_groups = defaultdict(list)
        
        for dp in metric_data:
            if pattern_type == "weekly":
                key = dp.timestamp.strftime("%A")  # Day of week
            elif pattern_type == "monthly":
                key = dp.timestamp.strftime("%B")  # Month name
            elif pattern_type == "quarterly":
                quarter = (dp.timestamp.month - 1) // 3 + 1
                key = f"Q{quarter}"
            elif pattern_type == "hourly":
                key = str(dp.timestamp.hour)
            else:
                key = dp.timestamp.strftime("%A")  # Default to weekly
            
            pattern_groups[key].append(dp.metric_value)
        
        # Calculate statistics for each pattern group
        pattern_stats = {}
        for pattern_key, values in pattern_groups.items():
            if values:
                pattern_stats[pattern_key] = {
                    "count": len(values),
                    "avg": round(statistics.mean(values), 2),
                    "min": round(min(values), 2),
                    "max": round(max(values), 2),
                    "std_dev": round(statistics.stdev(values) if len(values) > 1 else 0, 2)
                }
        
        # Identify peak and low periods
        if pattern_stats:
            sorted_by_avg = sorted(pattern_stats.items(), key=lambda x: x[1]["avg"], reverse=True)
            peak_period = sorted_by_avg[0][0] if sorted_by_avg else None
            low_period = sorted_by_avg[-1][0] if sorted_by_avg else None
        else:
            peak_period = None
            low_period = None
        
        return {
            "pattern_statistics": pattern_stats,
            "peak_period": peak_period,
            "low_period": low_period,
            "pattern_type": pattern_type,
            "total_data_points": len(metric_data)
        }
    
    async def _calculate_pattern_summary(self, seasonal_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary of seasonal patterns."""
        if not seasonal_patterns:
            return {}
        
        summary = {
            "metrics_analyzed": len(seasonal_patterns),
            "common_peak_periods": {},
            "common_low_periods": {},
            "pattern_strength": {}
        }
        
        # Count common peak and low periods across metrics
        peak_counts = {}
        low_counts = {}
        
        for metric, patterns in seasonal_patterns.items():
            peak_period = patterns.get("peak_period")
            low_period = patterns.get("low_period")
            
            if peak_period:
                peak_counts[peak_period] = peak_counts.get(peak_period, 0) + 1
            
            if low_period:
                low_counts[low_period] = low_counts.get(low_period, 0) + 1
            
            # Calculate pattern strength (coefficient of variation across periods)
            pattern_stats = patterns.get("pattern_statistics", {})
            if pattern_stats:
                avg_values = [stats["avg"] for stats in pattern_stats.values()]
                if len(avg_values) > 1:
                    pattern_strength = statistics.stdev(avg_values) / statistics.mean(avg_values)
                    summary["pattern_strength"][metric] = round(pattern_strength, 3)
        
        summary["common_peak_periods"] = dict(sorted(peak_counts.items(), key=lambda x: x[1], reverse=True))
        summary["common_low_periods"] = dict(sorted(low_counts.items(), key=lambda x: x[1], reverse=True))
        
        return summary
    
    def _data_point_to_dict(self, data_point: TrendDataPoint) -> Dict[str, Any]:
        """Convert trend data point to dictionary."""
        return {
            "timestamp": data_point.timestamp.isoformat(),
            "metric_name": data_point.metric_name,
            "metric_value": data_point.metric_value,
            "driver_id": data_point.driver_id,
            "context": data_point.context or {}
        }
    
    def _generate_cache_key(self, operation: str, *args, **kwargs) -> str:
        """Generate cache key for operations."""
        from ..cache.cache_manager import CacheKeyGenerator
        return CacheKeyGenerator.generate_key(f"{self.name}_{operation}", *args, **kwargs)
    
    # MCP Tool Interface Methods
    
    def get_tool_info(self) -> Dict[str, Any]:
        """Get tool information for MCP registration."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "methods": [
                {
                    "name": "analyze_driver_trends",
                    "description": "Analyze trends for a specific driver",
                    "parameters": {
                        "driver_id": {"type": "string", "description": "Driver ID"},
                        "metrics": {"type": "array", "description": "Metrics to analyze"},
                        "time_range": {"type": "object", "description": "Time range filter"},
                        "aggregation_period": {"type": "string", "description": "Aggregation period"}
                    }
                },
                {
                    "name": "compare_trend_patterns",
                    "description": "Compare trend patterns between multiple drivers",
                    "parameters": {
                        "driver_ids": {"type": "array", "description": "Driver IDs to compare"},
                        "metric": {"type": "string", "description": "Metric to compare"},
                        "time_range": {"type": "object", "description": "Time range filter"},
                        "aggregation_period": {"type": "string", "description": "Aggregation period"}
                    }
                },
                {
                    "name": "detect_anomalies",
                    "description": "Detect anomalies in trend data",
                    "parameters": {
                        "driver_ids": {"type": "array", "description": "Optional driver IDs"},
                        "metrics": {"type": "array", "description": "Metrics to analyze"},
                        "time_range": {"type": "object", "description": "Time range filter"},
                        "sensitivity": {"type": "number", "description": "Anomaly detection sensitivity"}
                    }
                },
                {
                    "name": "forecast_trends",
                    "description": "Generate trend forecasts",
                    "parameters": {
                        "driver_id": {"type": "string", "description": "Driver ID"},
                        "metric": {"type": "string", "description": "Metric to forecast"},
                        "forecast_days": {"type": "integer", "description": "Number of days to forecast"},
                        "time_range": {"type": "object", "description": "Historical time range"}
                    }
                },
                {
                    "name": "get_seasonal_patterns",
                    "description": "Identify seasonal patterns in trend data",
                    "parameters": {
                        "metrics": {"type": "array", "description": "Metrics to analyze"},
                        "driver_ids": {"type": "array", "description": "Optional driver IDs"},
                        "pattern_type": {"type": "string", "description": "Type of seasonal pattern"}
                    }
                }
            ]
        }
    
    async def execute_method(self, method_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool method."""
        if method_name == "analyze_driver_trends":
            return await self.analyze_driver_trends(
                parameters.get("driver_id"),
                parameters.get("metrics", []),
                parameters.get("time_range"),
                parameters.get("aggregation_period", "daily")
            )
        elif method_name == "compare_trend_patterns":
            return await self.compare_trend_patterns(
                parameters.get("driver_ids", []),
                parameters.get("metric"),
                parameters.get("time_range"),
                parameters.get("aggregation_period", "weekly")
            )
        elif method_name == "detect_anomalies":
            return await self.detect_anomalies(
                parameters.get("driver_ids"),
                parameters.get("metrics"),
                parameters.get("time_range"),
                parameters.get("sensitivity", 2.0)
            )
        elif method_name == "forecast_trends":
            return await self.forecast_trends(
                parameters.get("driver_id"),
                parameters.get("metric"),
                parameters.get("forecast_days", 30),
                parameters.get("time_range")
            )
        elif method_name == "get_seasonal_patterns":
            return await self.get_seasonal_patterns(
                parameters.get("metrics", []),
                parameters.get("driver_ids"),
                parameters.get("pattern_type", "weekly")
            )
        else:
            return {
                "success": False,
                "error": f"Unknown method: {method_name}",
                "data": None
            }