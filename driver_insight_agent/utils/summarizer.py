"""Token-efficient summarization utilities for downstream LLM consumption."""

from typing import Dict, List, Any, Optional, Union
import json
from dataclasses import dataclass, asdict
from datetime import datetime
import statistics


@dataclass
class SummaryMetadata:
    """Metadata for summaries."""
    generated_at: datetime
    total_records: int
    summary_type: str
    compression_ratio: float
    token_count_estimate: int


@dataclass
class SummaryConfig:
    """Configuration for summarization."""
    max_tokens: int = 2000
    include_metadata: bool = True
    compression_ratio: float = 0.3
    include_raw_samples: bool = False
    sample_size: int = 3
    precision: int = 2


class TokenEstimator:
    """Utility for estimating token counts."""
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        # Rough estimation: 1 token ≈ 4 characters for English text
        return len(text) // 4
    
    @staticmethod
    def estimate_json_tokens(data: Dict[str, Any]) -> int:
        """Estimate token count for JSON data."""
        json_str = json.dumps(data, separators=(',', ':'))
        return TokenEstimator.estimate_tokens(json_str)


class DataSummarizer:
    """Main summarization engine for driver analytics data."""
    
    def __init__(self, config: Optional[SummaryConfig] = None):
        """Initialize summarizer with configuration."""
        self.config = config or SummaryConfig()
        self.token_estimator = TokenEstimator()
    
    def summarize_driver_data(self, data: List[Dict[str, Any]], 
                            summary_type: str = "general") -> Dict[str, Any]:
        """Create a comprehensive summary of driver data."""
        if not data:
            return self._empty_summary(summary_type)
        
        # Generate different summary types
        summary_generators = {
            "general": self._general_summary,
            "score": self._score_summary,
            "trip": self._trip_summary,
            "trend": self._trend_summary,
            "comparison": self._comparison_summary,
            "ranking": self._ranking_summary
        }
        
        generator = summary_generators.get(summary_type, self._general_summary)
        summary = generator(data)
        
        # Add metadata
        if self.config.include_metadata:
            summary['metadata'] = asdict(SummaryMetadata(
                generated_at=datetime.now(),
                total_records=len(data),
                summary_type=summary_type,
                compression_ratio=self._calculate_compression_ratio(data, summary),
                token_count_estimate=self.token_estimator.estimate_json_tokens(summary)
            ))
        
        # Ensure token limit
        summary = self._enforce_token_limit(summary)
        
        return summary
    
    def _general_summary(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate general summary of data."""
        summary = {
            "overview": {
                "total_records": len(data),
                "unique_drivers": len(set(item.get('driver_id', item.get('id', '')) for item in data)),
                "date_range": self._get_date_range(data)
            },
            "key_metrics": self._extract_key_metrics(data),
            "distributions": self._calculate_distributions(data),
            "insights": self._generate_insights(data)
        }
        
        if self.config.include_raw_samples:
            summary["samples"] = data[:self.config.sample_size]
        
        return summary
    
    def _score_summary(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate score-focused summary."""
        scores = self._extract_numeric_values(data, ['score', 'rating', 'performance'])
        
        if not scores:
            return {"error": "No score data found"}
        
        return {
            "score_statistics": {
                "count": len(scores),
                "average": round(statistics.mean(scores), self.config.precision),
                "median": round(statistics.median(scores), self.config.precision),
                "min": round(min(scores), self.config.precision),
                "max": round(max(scores), self.config.precision),
                "std_dev": round(statistics.stdev(scores) if len(scores) > 1 else 0, self.config.precision)
            },
            "score_distribution": self._score_distribution(scores),
            "performance_tiers": self._performance_tiers(data, scores),
            "top_performers": self._get_top_performers(data, 'score', 5),
            "improvement_opportunities": self._identify_low_performers(data, 'score', 5)
        }
    
    def _trip_summary(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate trip-focused summary."""
        trip_metrics = self._extract_trip_metrics(data)
        
        return {
            "trip_overview": {
                "total_trips": len(data),
                "unique_drivers": len(set(item.get('driver_id', '') for item in data)),
                "date_range": self._get_date_range(data)
            },
            "distance_stats": trip_metrics.get('distance', {}),
            "duration_stats": trip_metrics.get('duration', {}),
            "efficiency_metrics": self._calculate_efficiency_metrics(data),
            "patterns": self._identify_trip_patterns(data),
            "anomalies": self._detect_trip_anomalies(data)
        }
    
    def _trend_summary(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate trend-focused summary."""
        time_series = self._create_time_series(data)
        
        return {
            "trend_analysis": {
                "time_period": self._get_date_range(data),
                "data_points": len(time_series),
                "trend_direction": self._calculate_trend_direction(time_series),
                "volatility": self._calculate_volatility(time_series)
            },
            "periodic_patterns": self._identify_periodic_patterns(time_series),
            "growth_metrics": self._calculate_growth_metrics(time_series),
            "forecasting_indicators": self._generate_forecasting_indicators(time_series)
        }
    
    def _comparison_summary(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comparison summary."""
        groups = self._group_data_for_comparison(data)
        
        return {
            "comparison_overview": {
                "groups_compared": len(groups),
                "total_records": len(data)
            },
            "group_statistics": {
                group_name: self._calculate_group_stats(group_data)
                for group_name, group_data in groups.items()
            },
            "relative_performance": self._calculate_relative_performance(groups),
            "significant_differences": self._identify_significant_differences(groups)
        }
    
    def _ranking_summary(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate ranking summary."""
        ranked_data = sorted(data, key=lambda x: x.get('score', 0), reverse=True)
        
        return {
            "ranking_overview": {
                "total_ranked": len(ranked_data),
                "ranking_criteria": "score"
            },
            "top_performers": ranked_data[:10],
            "bottom_performers": ranked_data[-5:],
            "percentile_breakdown": self._percentile_breakdown(ranked_data),
            "performance_gaps": self._calculate_performance_gaps(ranked_data)
        }
    
    def _extract_key_metrics(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract key metrics from data."""
        numeric_fields = ['score', 'distance', 'duration', 'speed', 'efficiency']
        metrics = {}
        
        for field in numeric_fields:
            values = self._extract_numeric_values(data, [field])
            if values:
                metrics[field] = {
                    "count": len(values),
                    "avg": round(statistics.mean(values), self.config.precision),
                    "min": round(min(values), self.config.precision),
                    "max": round(max(values), self.config.precision)
                }
        
        return metrics
    
    def _extract_numeric_values(self, data: List[Dict[str, Any]], 
                              fields: List[str]) -> List[float]:
        """Extract numeric values from specified fields."""
        values = []
        
        for item in data:
            for field in fields:
                value = self._get_nested_value(item, field)
                if isinstance(value, (int, float)):
                    values.append(float(value))
                elif isinstance(value, str):
                    try:
                        values.append(float(value))
                    except ValueError:
                        continue
        
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
    
    def _calculate_distributions(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate data distributions."""
        distributions = {}
        
        # Categorical distributions
        categorical_fields = ['status', 'type', 'category', 'region']
        for field in categorical_fields:
            values = [str(item.get(field, '')) for item in data if item.get(field)]
            if values:
                from collections import Counter
                counter = Counter(values)
                distributions[field] = dict(counter.most_common(5))
        
        return distributions
    
    def _generate_insights(self, data: List[Dict[str, Any]]) -> List[str]:
        """Generate actionable insights from data."""
        insights = []
        
        # Score-based insights
        scores = self._extract_numeric_values(data, ['score'])
        if scores:
            avg_score = statistics.mean(scores)
            if avg_score < 70:
                insights.append(f"Average score ({avg_score:.1f}) is below target threshold")
            elif avg_score > 90:
                insights.append(f"Excellent average score ({avg_score:.1f}) indicates strong performance")
        
        # Volume insights
        if len(data) > 1000:
            insights.append(f"Large dataset ({len(data)} records) provides robust statistical significance")
        elif len(data) < 50:
            insights.append(f"Small dataset ({len(data)} records) may limit statistical reliability")
        
        # Trend insights
        time_series = self._create_time_series(data)
        if len(time_series) > 2:
            trend = self._calculate_trend_direction(time_series)
            if trend > 0.1:
                insights.append("Positive upward trend detected in performance metrics")
            elif trend < -0.1:
                insights.append("Declining trend detected - requires attention")
        
        return insights[:5]  # Limit to top 5 insights
    
    def _get_date_range(self, data: List[Dict[str, Any]]) -> Dict[str, str]:
        """Get date range from data."""
        date_fields = ['date', 'timestamp', 'created_at', 'trip_date']
        dates = []
        
        for item in data:
            for field in date_fields:
                date_value = item.get(field)
                if date_value:
                    try:
                        if isinstance(date_value, str):
                            from dateutil.parser import parse as parse_date
                            dates.append(parse_date(date_value))
                        elif hasattr(date_value, 'isoformat'):
                            dates.append(date_value)
                    except:
                        continue
        
        if dates:
            return {
                "start": min(dates).isoformat(),
                "end": max(dates).isoformat(),
                "span_days": (max(dates) - min(dates)).days
            }
        
        return {"start": None, "end": None, "span_days": 0}
    
    def _create_time_series(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create time series from data."""
        # Simplified time series creation
        time_series = []
        
        for item in data:
            date_value = item.get('date') or item.get('timestamp')
            metric_value = item.get('score') or item.get('value', 0)
            
            if date_value and metric_value is not None:
                time_series.append({
                    'date': date_value,
                    'value': float(metric_value)
                })
        
        return sorted(time_series, key=lambda x: x['date'])
    
    def _calculate_trend_direction(self, time_series: List[Dict[str, Any]]) -> float:
        """Calculate trend direction (-1 to 1)."""
        if len(time_series) < 2:
            return 0
        
        values = [point['value'] for point in time_series]
        n = len(values)
        
        # Simple linear trend calculation
        sum_x = sum(range(n))
        sum_y = sum(values)
        sum_xy = sum(i * values[i] for i in range(n))
        sum_x2 = sum(i * i for i in range(n))
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return 0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Normalize slope to -1 to 1 range
        max_value = max(values)
        min_value = min(values)
        value_range = max_value - min_value
        
        if value_range == 0:
            return 0
        
        normalized_slope = slope / (value_range / n)
        return max(-1, min(1, normalized_slope))
    
    def _enforce_token_limit(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure summary stays within token limits."""
        current_tokens = self.token_estimator.estimate_json_tokens(summary)
        
        if current_tokens <= self.config.max_tokens:
            return summary
        
        # Progressively remove less important sections
        removal_priority = ['samples', 'raw_data', 'detailed_breakdown', 'metadata']
        
        for section in removal_priority:
            if section in summary:
                del summary[section]
                current_tokens = self.token_estimator.estimate_json_tokens(summary)
                if current_tokens <= self.config.max_tokens:
                    break
        
        # If still too large, truncate arrays
        if current_tokens > self.config.max_tokens:
            summary = self._truncate_arrays(summary, target_tokens=self.config.max_tokens)
        
        return summary
    
    def _truncate_arrays(self, data: Dict[str, Any], target_tokens: int) -> Dict[str, Any]:
        """Truncate arrays to meet token targets."""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 3:
                    # Keep first 3 items of large arrays
                    result[key] = value[:3]
                elif isinstance(value, dict):
                    result[key] = self._truncate_arrays(value, target_tokens)
                else:
                    result[key] = value
            return result
        
        return data
    
    def _empty_summary(self, summary_type: str) -> Dict[str, Any]:
        """Return empty summary structure."""
        return {
            "summary_type": summary_type,
            "total_records": 0,
            "message": "No data available for summarization"
        }
    
    def _calculate_compression_ratio(self, original_data: List[Dict[str, Any]], 
                                   summary: Dict[str, Any]) -> float:
        """Calculate compression ratio."""
        original_tokens = self.token_estimator.estimate_json_tokens(original_data)
        summary_tokens = self.token_estimator.estimate_json_tokens(summary)
        
        if original_tokens == 0:
            return 0
        
        return summary_tokens / original_tokens
    
    # Additional helper methods for specific summary types
    def _score_distribution(self, scores: List[float]) -> Dict[str, int]:
        """Calculate score distribution buckets."""
        buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
        
        for score in scores:
            if score <= 20:
                buckets["0-20"] += 1
            elif score <= 40:
                buckets["21-40"] += 1
            elif score <= 60:
                buckets["41-60"] += 1
            elif score <= 80:
                buckets["61-80"] += 1
            else:
                buckets["81-100"] += 1
        
        return buckets
    
    def _performance_tiers(self, data: List[Dict[str, Any]], scores: List[float]) -> Dict[str, int]:
        """Categorize performance into tiers."""
        if not scores:
            return {}
        
        avg_score = statistics.mean(scores)
        std_dev = statistics.stdev(scores) if len(scores) > 1 else 0
        
        tiers = {"excellent": 0, "good": 0, "average": 0, "needs_improvement": 0}
        
        for score in scores:
            if score >= avg_score + std_dev:
                tiers["excellent"] += 1
            elif score >= avg_score:
                tiers["good"] += 1
            elif score >= avg_score - std_dev:
                tiers["average"] += 1
            else:
                tiers["needs_improvement"] += 1
        
        return tiers
    
    def _get_top_performers(self, data: List[Dict[str, Any]], field: str, limit: int) -> List[Dict[str, Any]]:
        """Get top performers based on field."""
        sorted_data = sorted(data, key=lambda x: x.get(field, 0), reverse=True)
        return sorted_data[:limit]
    
    def _identify_low_performers(self, data: List[Dict[str, Any]], field: str, limit: int) -> List[Dict[str, Any]]:
        """Identify low performers for improvement opportunities."""
        sorted_data = sorted(data, key=lambda x: x.get(field, 0))
        return sorted_data[:limit]