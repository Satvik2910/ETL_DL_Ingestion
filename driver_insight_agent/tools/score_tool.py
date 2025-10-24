"""Score aggregation tool for rankings and comparisons."""

from typing import Dict, List, Any, Optional, Union
import asyncio
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date

from ..utils.validation import TimeRange, ValidationError
from ..utils.filter_engine import FilterEngine
from ..utils.aggregation_engine import AggregationEngine, AdvancedAggregationEngine
from ..cache.cache_manager import get_cache_manager


@dataclass
class ScoreRecord:
    """Individual score record."""
    score_id: str
    driver_id: str
    score_type: str  # overall, safety, efficiency, customer_service, etc.
    score_value: float
    max_score: float
    percentage: float
    date_recorded: datetime
    period_start: datetime
    period_end: datetime
    contributing_factors: Dict[str, float]
    metadata: Optional[Dict[str, Any]] = None


class ScoreDataSource:
    """Mock data source for score information."""
    
    def __init__(self):
        """Initialize with sample score data."""
        self.scores = self._generate_sample_scores()
    
    def _generate_sample_scores(self) -> List[ScoreRecord]:
        """Generate sample score data."""
        scores = []
        driver_ids = ["DRV001", "DRV002", "DRV003", "DRV004", "DRV005"]
        score_types = ["overall", "safety", "efficiency", "customer_service", "punctuality"]
        
        # Generate scores for the last 12 weeks (weekly scores)
        base_date = datetime.now() - timedelta(weeks=12)
        
        score_id = 1
        for week in range(12):
            week_start = base_date + timedelta(weeks=week)
            week_end = week_start + timedelta(days=6)
            
            for driver_id in driver_ids:
                for score_type in score_types:
                    # Generate realistic score with some consistency per driver
                    base_score = {
                        "DRV001": 85,  # Consistent good performer
                        "DRV002": 78,  # Average performer
                        "DRV003": 92,  # Top performer
                        "DRV004": 71,  # Below average
                        "DRV005": 88   # Good performer
                    }[driver_id]
                    
                    # Add some variation based on score type
                    type_modifier = {
                        "overall": 0,
                        "safety": random.uniform(-5, 5),
                        "efficiency": random.uniform(-8, 8),
                        "customer_service": random.uniform(-10, 10),
                        "punctuality": random.uniform(-6, 6)
                    }[score_type]
                    
                    # Add weekly variation
                    weekly_variation = random.uniform(-3, 3)
                    
                    final_score = max(0, min(100, base_score + type_modifier + weekly_variation))
                    
                    # Generate contributing factors
                    factors = {
                        "trip_completion": random.uniform(0.8, 1.0),
                        "route_efficiency": random.uniform(0.7, 1.0),
                        "customer_ratings": random.uniform(0.6, 1.0),
                        "safety_incidents": random.uniform(0.9, 1.0),
                        "on_time_performance": random.uniform(0.7, 1.0)
                    }
                    
                    score = ScoreRecord(
                        score_id=f"SCR{score_id:06d}",
                        driver_id=driver_id,
                        score_type=score_type,
                        score_value=round(final_score, 2),
                        max_score=100.0,
                        percentage=round(final_score, 2),
                        date_recorded=week_end,
                        period_start=week_start,
                        period_end=week_end,
                        contributing_factors=factors,
                        metadata={
                            "calculation_method": "weighted_average",
                            "data_quality": random.choice(["high", "medium", "low"]),
                            "sample_size": random.randint(5, 50)
                        }
                    )
                    scores.append(score)
                    score_id += 1
        
        return scores
    
    async def get_scores_by_driver(self, driver_id: str, 
                                 score_type: Optional[str] = None,
                                 time_range: Optional[TimeRange] = None) -> List[ScoreRecord]:
        """Get scores for a specific driver."""
        driver_scores = [score for score in self.scores if score.driver_id == driver_id]
        
        if score_type:
            driver_scores = [score for score in driver_scores if score.score_type == score_type]
        
        if time_range:
            driver_scores = [
                score for score in driver_scores
                if time_range.start_date <= score.date_recorded <= time_range.end_date
            ]
        
        return driver_scores
    
    async def get_scores_by_type(self, score_type: str,
                               time_range: Optional[TimeRange] = None) -> List[ScoreRecord]:
        """Get all scores of a specific type."""
        type_scores = [score for score in self.scores if score.score_type == score_type]
        
        if time_range:
            type_scores = [
                score for score in type_scores
                if time_range.start_date <= score.date_recorded <= time_range.end_date
            ]
        
        return type_scores
    
    async def get_latest_scores(self, driver_ids: Optional[List[str]] = None,
                              score_type: Optional[str] = None) -> List[ScoreRecord]:
        """Get the latest scores for drivers."""
        # Group scores by driver and score type, then get the latest
        latest_scores = {}
        
        for score in self.scores:
            if driver_ids and score.driver_id not in driver_ids:
                continue
            if score_type and score.score_type != score_type:
                continue
            
            key = (score.driver_id, score.score_type)
            if key not in latest_scores or score.date_recorded > latest_scores[key].date_recorded:
                latest_scores[key] = score
        
        return list(latest_scores.values())
    
    async def get_all_scores(self) -> List[ScoreRecord]:
        """Get all scores."""
        return self.scores.copy()


class ScoreTool:
    """Tool for score aggregation, rankings, and comparisons."""
    
    def __init__(self):
        """Initialize score tool."""
        self.data_source = ScoreDataSource()
        self.filter_engine = FilterEngine()
        self.aggregation_engine = AdvancedAggregationEngine()
        self.cache_manager = get_cache_manager()
        
        # Tool metadata
        self.name = "score_tool"
        self.description = "Score aggregation, rankings, and performance comparisons"
        self.version = "1.0.0"
    
    async def get_driver_scores(self, driver_id: str,
                              score_types: Optional[List[str]] = None,
                              time_range: Optional[Dict[str, str]] = None,
                              aggregations: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Get scores for a specific driver."""
        try:
            # Check cache first
            cache_key = self._generate_cache_key("driver_scores", driver_id, score_types, time_range, aggregations)
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
            
            # Get scores from data source
            all_driver_scores = []
            
            if score_types:
                for score_type in score_types:
                    scores = await self.data_source.get_scores_by_driver(driver_id, score_type, parsed_time_range)
                    all_driver_scores.extend(scores)
            else:
                all_driver_scores = await self.data_source.get_scores_by_driver(driver_id, None, parsed_time_range)
            
            score_data = [self._score_to_dict(score) for score in all_driver_scores]
            
            # Calculate aggregations if requested
            aggregation_results = {}
            if aggregations and score_data:
                aggregation_results = self.aggregation_engine.aggregate(score_data, aggregations)
            
            # Calculate summary statistics
            summary_stats = await self._calculate_score_summary(score_data)
            
            result = {
                "success": True,
                "data": {
                    "driver_id": driver_id,
                    "scores": score_data,
                    "summary": summary_stats,
                    "aggregations": aggregation_results,
                    "filters": {
                        "score_types": score_types,
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
            await self.cache_manager.set(cache_key, result, ttl=1800, 
                                       tags=['driver_scores', f'driver_{driver_id}'])
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get driver scores: {str(e)}",
                "data": None
            }
    
    async def get_score_rankings(self, score_type: str = "overall",
                               time_range: Optional[Dict[str, str]] = None,
                               limit: int = 10,
                               include_percentiles: bool = True) -> Dict[str, Any]:
        """Get driver rankings based on scores."""
        try:
            # Check cache first
            cache_key = self._generate_cache_key("score_rankings", score_type, time_range, limit, include_percentiles)
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
            
            # Get latest scores for the specified type
            latest_scores = await self.data_source.get_latest_scores(score_type=score_type)
            
            # Filter by time range if specified
            if parsed_time_range:
                latest_scores = [
                    score for score in latest_scores
                    if parsed_time_range.start_date <= score.date_recorded <= parsed_time_range.end_date
                ]
            
            # Convert to dictionaries and calculate rankings
            score_data = [self._score_to_dict(score) for score in latest_scores]
            ranked_data = self.aggregation_engine.ranking_aggregation(score_data, "score_value")
            
            # Apply limit
            top_performers = ranked_data[:limit]
            
            # Calculate percentiles if requested
            percentile_data = {}
            if include_percentiles and score_data:
                score_values = [score["score_value"] for score in score_data]
                percentile_data = {
                    "25th_percentile": self.aggregation_engine._percentile(score_values, 25),
                    "50th_percentile": self.aggregation_engine._percentile(score_values, 50),
                    "75th_percentile": self.aggregation_engine._percentile(score_values, 75),
                    "90th_percentile": self.aggregation_engine._percentile(score_values, 90)
                }
            
            result = {
                "success": True,
                "data": {
                    "score_type": score_type,
                    "rankings": top_performers,
                    "percentiles": percentile_data,
                    "summary": {
                        "total_drivers": len(score_data),
                        "displayed_count": len(top_performers),
                        "time_range": time_range,
                        "average_score": sum(s["score_value"] for s in score_data) / len(score_data) if score_data else 0
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
                                       tags=['score_rankings', f'score_type_{score_type}'])
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get score rankings: {str(e)}",
                "data": None
            }
    
    async def compare_driver_scores(self, driver_ids: List[str],
                                  score_types: Optional[List[str]] = None,
                                  time_range: Optional[Dict[str, str]] = None,
                                  comparison_type: str = "latest") -> Dict[str, Any]:
        """Compare scores between multiple drivers."""
        try:
            score_types = score_types or ["overall"]
            
            # Check cache first
            cache_key = self._generate_cache_key("compare_scores", driver_ids, score_types, time_range, comparison_type)
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
            
            # Get scores for each driver
            driver_comparisons = {}
            
            for driver_id in driver_ids:
                driver_scores = {}
                
                for score_type in score_types:
                    scores = await self.data_source.get_scores_by_driver(driver_id, score_type, parsed_time_range)
                    
                    if scores:
                        score_values = [score.score_value for score in scores]
                        
                        if comparison_type == "latest":
                            # Get the most recent score
                            latest_score = max(scores, key=lambda s: s.date_recorded)
                            driver_scores[score_type] = {
                                "value": latest_score.score_value,
                                "date": latest_score.date_recorded.isoformat(),
                                "percentage": latest_score.percentage
                            }
                        elif comparison_type == "average":
                            # Calculate average score
                            import statistics
                            driver_scores[score_type] = {
                                "value": round(statistics.mean(score_values), 2),
                                "count": len(score_values),
                                "std_dev": round(statistics.stdev(score_values) if len(score_values) > 1 else 0, 2)
                            }
                        elif comparison_type == "trend":
                            # Calculate trend (improvement/decline)
                            if len(scores) >= 2:
                                sorted_scores = sorted(scores, key=lambda s: s.date_recorded)
                                first_score = sorted_scores[0].score_value
                                last_score = sorted_scores[-1].score_value
                                trend = last_score - first_score
                                
                                driver_scores[score_type] = {
                                    "first_value": first_score,
                                    "last_value": last_score,
                                    "trend": round(trend, 2),
                                    "trend_percentage": round((trend / first_score) * 100, 2) if first_score != 0 else 0
                                }
                
                driver_comparisons[driver_id] = driver_scores
            
            # Calculate relative performance
            relative_performance = await self._calculate_score_relative_performance(driver_comparisons, score_types)
            
            result = {
                "success": True,
                "data": {
                    "driver_comparisons": driver_comparisons,
                    "relative_performance": relative_performance,
                    "comparison_settings": {
                        "driver_ids": driver_ids,
                        "score_types": score_types,
                        "comparison_type": comparison_type,
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
            cache_tags = ['score_comparison'] + [f'driver_{driver_id}' for driver_id in driver_ids]
            await self.cache_manager.set(cache_key, result, ttl=3600, tags=cache_tags)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to compare driver scores: {str(e)}",
                "data": None
            }
    
    async def get_score_analytics(self, score_types: Optional[List[str]] = None,
                                time_range: Optional[Dict[str, str]] = None,
                                group_by: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive score analytics."""
        try:
            score_types = score_types or ["overall"]
            
            # Check cache first
            cache_key = self._generate_cache_key("score_analytics", score_types, time_range, group_by)
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
            
            # Get all scores for analysis
            all_scores = []
            for score_type in score_types:
                scores = await self.data_source.get_scores_by_type(score_type, parsed_time_range)
                all_scores.extend(scores)
            
            score_data = [self._score_to_dict(score) for score in all_scores]
            
            # Calculate comprehensive analytics
            analytics = await self._calculate_comprehensive_analytics(score_data, group_by)
            
            result = {
                "success": True,
                "data": {
                    "analytics": analytics,
                    "summary": {
                        "total_scores": len(score_data),
                        "unique_drivers": len(set(score["driver_id"] for score in score_data)),
                        "score_types": score_types,
                        "time_range": time_range,
                        "grouped_by": group_by
                    }
                },
                "metadata": {
                    "tool": self.name,
                    "version": self.version,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Cache result
            cache_tags = ['score_analytics'] + [f'score_type_{st}' for st in score_types]
            await self.cache_manager.set(cache_key, result, ttl=3600, tags=cache_tags)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get score analytics: {str(e)}",
                "data": None
            }
    
    async def identify_score_trends(self, driver_ids: Optional[List[str]] = None,
                                  score_type: str = "overall",
                                  time_range: Optional[Dict[str, str]] = None,
                                  trend_period: str = "weekly") -> Dict[str, Any]:
        """Identify trends in driver scores."""
        try:
            # Check cache first
            cache_key = self._generate_cache_key("score_trends", driver_ids, score_type, time_range, trend_period)
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
            
            # Get scores for analysis
            if driver_ids:
                all_scores = []
                for driver_id in driver_ids:
                    scores = await self.data_source.get_scores_by_driver(driver_id, score_type, parsed_time_range)
                    all_scores.extend(scores)
            else:
                all_scores = await self.data_source.get_scores_by_type(score_type, parsed_time_range)
            
            score_data = [self._score_to_dict(score) for score in all_scores]
            
            # Analyze trends
            trend_analysis = await self._analyze_score_trends(score_data, trend_period)
            
            result = {
                "success": True,
                "data": {
                    "trend_analysis": trend_analysis,
                    "settings": {
                        "driver_ids": driver_ids,
                        "score_type": score_type,
                        "time_range": time_range,
                        "trend_period": trend_period
                    },
                    "summary": {
                        "total_scores_analyzed": len(score_data),
                        "unique_drivers": len(set(score["driver_id"] for score in score_data))
                    }
                },
                "metadata": {
                    "tool": self.name,
                    "version": self.version,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Cache result
            cache_tags = ['score_trends', f'score_type_{score_type}']
            if driver_ids:
                cache_tags.extend([f'driver_{driver_id}' for driver_id in driver_ids])
            
            await self.cache_manager.set(cache_key, result, ttl=3600, tags=cache_tags)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to identify score trends: {str(e)}",
                "data": None
            }
    
    def _score_to_dict(self, score: ScoreRecord) -> Dict[str, Any]:
        """Convert score record to dictionary."""
        return {
            "score_id": score.score_id,
            "driver_id": score.driver_id,
            "score_type": score.score_type,
            "score_value": score.score_value,
            "max_score": score.max_score,
            "percentage": score.percentage,
            "date_recorded": score.date_recorded.isoformat(),
            "period_start": score.period_start.isoformat(),
            "period_end": score.period_end.isoformat(),
            "contributing_factors": score.contributing_factors,
            "metadata": score.metadata or {}
        }
    
    async def _calculate_score_summary(self, score_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics for scores."""
        if not score_data:
            return {}
        
        import statistics
        
        score_values = [score["score_value"] for score in score_data]
        score_types = list(set(score["score_type"] for score in score_data))
        
        summary = {
            "total_scores": len(score_data),
            "score_types": score_types,
            "overall_statistics": {
                "avg": round(statistics.mean(score_values), 2),
                "median": round(statistics.median(score_values), 2),
                "min": round(min(score_values), 2),
                "max": round(max(score_values), 2),
                "std_dev": round(statistics.stdev(score_values) if len(score_values) > 1 else 0, 2)
            }
        }
        
        # Calculate statistics by score type
        type_statistics = {}
        for score_type in score_types:
            type_scores = [score["score_value"] for score in score_data if score["score_type"] == score_type]
            if type_scores:
                type_statistics[score_type] = {
                    "count": len(type_scores),
                    "avg": round(statistics.mean(type_scores), 2),
                    "min": round(min(type_scores), 2),
                    "max": round(max(type_scores), 2)
                }
        
        summary["by_score_type"] = type_statistics
        
        return summary
    
    async def _calculate_score_relative_performance(self, driver_comparisons: Dict[str, Any], 
                                                  score_types: List[str]) -> Dict[str, Any]:
        """Calculate relative performance between drivers."""
        relative_performance = {}
        
        for score_type in score_types:
            driver_values = {}
            
            # Extract values for comparison
            for driver_id, scores in driver_comparisons.items():
                score_data = scores.get(score_type, {})
                if score_data:
                    # Use 'value' field or fall back to other available fields
                    value = score_data.get('value') or score_data.get('last_value') or 0
                    driver_values[driver_id] = value
            
            if driver_values:
                # Calculate rankings and statistics
                sorted_drivers = sorted(driver_values.items(), key=lambda x: x[1], reverse=True)
                
                # Calculate performance gaps
                if len(sorted_drivers) > 1:
                    best_score = sorted_drivers[0][1]
                    worst_score = sorted_drivers[-1][1]
                    performance_gap = best_score - worst_score
                else:
                    performance_gap = 0
                
                relative_performance[score_type] = {
                    "rankings": [
                        {"driver_id": driver, "value": value, "rank": i+1}
                        for i, (driver, value) in enumerate(sorted_drivers)
                    ],
                    "best_performer": sorted_drivers[0][0] if sorted_drivers else None,
                    "worst_performer": sorted_drivers[-1][0] if sorted_drivers else None,
                    "performance_gap": round(performance_gap, 2),
                    "average_score": round(sum(driver_values.values()) / len(driver_values), 2) if driver_values else 0
                }
        
        return relative_performance
    
    async def _calculate_comprehensive_analytics(self, score_data: List[Dict[str, Any]], 
                                               group_by: Optional[str] = None) -> Dict[str, Any]:
        """Calculate comprehensive analytics for scores."""
        if not score_data:
            return {}
        
        # Basic aggregations
        aggregations = [
            {"operation": "count", "field": "score_id", "alias": "total_scores"},
            {"operation": "avg", "field": "score_value", "alias": "avg_score"},
            {"operation": "min", "field": "score_value", "alias": "min_score"},
            {"operation": "max", "field": "score_value", "alias": "max_score"},
            {"operation": "std", "field": "score_value", "alias": "score_std_dev"}
        ]
        
        if group_by:
            for agg in aggregations:
                agg["group_by"] = group_by
        
        basic_stats = self.aggregation_engine.aggregate(score_data, aggregations)
        
        # Distribution analysis
        distribution_analysis = self._analyze_score_distributions(score_data)
        
        # Performance tier analysis
        tier_analysis = self._analyze_performance_tiers(score_data)
        
        analytics = {
            "basic_statistics": basic_stats,
            "distribution_analysis": distribution_analysis,
            "performance_tiers": tier_analysis
        }
        
        return analytics
    
    def _analyze_score_distributions(self, score_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze score distributions."""
        distributions = {}
        
        # Score type distribution
        score_types = {}
        for score in score_data:
            score_type = score.get("score_type", "unknown")
            score_types[score_type] = score_types.get(score_type, 0) + 1
        distributions["by_score_type"] = score_types
        
        # Score range distribution
        score_ranges = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
        for score in score_data:
            value = score.get("score_value", 0)
            if value <= 20:
                score_ranges["0-20"] += 1
            elif value <= 40:
                score_ranges["21-40"] += 1
            elif value <= 60:
                score_ranges["41-60"] += 1
            elif value <= 80:
                score_ranges["61-80"] += 1
            else:
                score_ranges["81-100"] += 1
        
        distributions["by_score_range"] = score_ranges
        
        return distributions
    
    def _analyze_performance_tiers(self, score_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance tiers."""
        if not score_data:
            return {}
        
        import statistics
        
        score_values = [score["score_value"] for score in score_data]
        avg_score = statistics.mean(score_values)
        std_dev = statistics.stdev(score_values) if len(score_values) > 1 else 0
        
        tiers = {
            "excellent": 0,      # > avg + std_dev
            "good": 0,          # avg to avg + std_dev
            "average": 0,       # avg - std_dev to avg
            "needs_improvement": 0  # < avg - std_dev
        }
        
        for value in score_values:
            if value > avg_score + std_dev:
                tiers["excellent"] += 1
            elif value >= avg_score:
                tiers["good"] += 1
            elif value >= avg_score - std_dev:
                tiers["average"] += 1
            else:
                tiers["needs_improvement"] += 1
        
        return {
            "tier_counts": tiers,
            "tier_thresholds": {
                "excellent_threshold": round(avg_score + std_dev, 2),
                "good_threshold": round(avg_score, 2),
                "average_threshold": round(avg_score - std_dev, 2)
            },
            "statistics": {
                "average_score": round(avg_score, 2),
                "standard_deviation": round(std_dev, 2)
            }
        }
    
    async def _analyze_score_trends(self, score_data: List[Dict[str, Any]], 
                                  trend_period: str) -> Dict[str, Any]:
        """Analyze score trends over time."""
        if not score_data:
            return {}
        
        # Group scores by driver and time period
        from collections import defaultdict
        driver_trends = defaultdict(list)
        
        for score in score_data:
            driver_id = score["driver_id"]
            date_recorded = parse_date(score["date_recorded"])
            
            driver_trends[driver_id].append({
                "date": date_recorded,
                "score": score["score_value"]
            })
        
        # Calculate trends for each driver
        trend_analysis = {}
        
        for driver_id, scores in driver_trends.items():
            # Sort by date
            scores.sort(key=lambda x: x["date"])
            
            if len(scores) >= 2:
                first_score = scores[0]["score"]
                last_score = scores[-1]["score"]
                trend_change = last_score - first_score
                trend_percentage = (trend_change / first_score) * 100 if first_score != 0 else 0
                
                # Determine trend direction
                if trend_change > 2:
                    trend_direction = "improving"
                elif trend_change < -2:
                    trend_direction = "declining"
                else:
                    trend_direction = "stable"
                
                trend_analysis[driver_id] = {
                    "first_score": round(first_score, 2),
                    "last_score": round(last_score, 2),
                    "trend_change": round(trend_change, 2),
                    "trend_percentage": round(trend_percentage, 2),
                    "trend_direction": trend_direction,
                    "score_count": len(scores),
                    "time_span_days": (scores[-1]["date"] - scores[0]["date"]).days
                }
        
        # Overall trend summary
        improving_count = sum(1 for t in trend_analysis.values() if t["trend_direction"] == "improving")
        declining_count = sum(1 for t in trend_analysis.values() if t["trend_direction"] == "declining")
        stable_count = sum(1 for t in trend_analysis.values() if t["trend_direction"] == "stable")
        
        summary = {
            "total_drivers_analyzed": len(trend_analysis),
            "improving_drivers": improving_count,
            "declining_drivers": declining_count,
            "stable_drivers": stable_count,
            "improvement_rate": improving_count / len(trend_analysis) if trend_analysis else 0
        }
        
        return {
            "driver_trends": trend_analysis,
            "summary": summary
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
                    "name": "get_driver_scores",
                    "description": "Get scores for a specific driver",
                    "parameters": {
                        "driver_id": {"type": "string", "description": "Driver ID"},
                        "score_types": {"type": "array", "description": "Types of scores to retrieve"},
                        "time_range": {"type": "object", "description": "Time range filter"},
                        "aggregations": {"type": "array", "description": "Aggregation operations"}
                    }
                },
                {
                    "name": "get_score_rankings",
                    "description": "Get driver rankings based on scores",
                    "parameters": {
                        "score_type": {"type": "string", "description": "Type of score for ranking"},
                        "time_range": {"type": "object", "description": "Time range filter"},
                        "limit": {"type": "integer", "description": "Number of top performers"},
                        "include_percentiles": {"type": "boolean", "description": "Include percentile data"}
                    }
                },
                {
                    "name": "compare_driver_scores",
                    "description": "Compare scores between multiple drivers",
                    "parameters": {
                        "driver_ids": {"type": "array", "description": "Driver IDs to compare"},
                        "score_types": {"type": "array", "description": "Types of scores to compare"},
                        "time_range": {"type": "object", "description": "Time range filter"},
                        "comparison_type": {"type": "string", "description": "Type of comparison"}
                    }
                },
                {
                    "name": "get_score_analytics",
                    "description": "Get comprehensive score analytics",
                    "parameters": {
                        "score_types": {"type": "array", "description": "Types of scores to analyze"},
                        "time_range": {"type": "object", "description": "Time range filter"},
                        "group_by": {"type": "string", "description": "Group by field"}
                    }
                },
                {
                    "name": "identify_score_trends",
                    "description": "Identify trends in driver scores",
                    "parameters": {
                        "driver_ids": {"type": "array", "description": "Optional driver IDs"},
                        "score_type": {"type": "string", "description": "Type of score for trend analysis"},
                        "time_range": {"type": "object", "description": "Time range filter"},
                        "trend_period": {"type": "string", "description": "Period for trend analysis"}
                    }
                }
            ]
        }
    
    async def execute_method(self, method_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool method."""
        if method_name == "get_driver_scores":
            return await self.get_driver_scores(
                parameters.get("driver_id"),
                parameters.get("score_types"),
                parameters.get("time_range"),
                parameters.get("aggregations")
            )
        elif method_name == "get_score_rankings":
            return await self.get_score_rankings(
                parameters.get("score_type", "overall"),
                parameters.get("time_range"),
                parameters.get("limit", 10),
                parameters.get("include_percentiles", True)
            )
        elif method_name == "compare_driver_scores":
            return await self.compare_driver_scores(
                parameters.get("driver_ids", []),
                parameters.get("score_types"),
                parameters.get("time_range"),
                parameters.get("comparison_type", "latest")
            )
        elif method_name == "get_score_analytics":
            return await self.get_score_analytics(
                parameters.get("score_types"),
                parameters.get("time_range"),
                parameters.get("group_by")
            )
        elif method_name == "identify_score_trends":
            return await self.identify_score_trends(
                parameters.get("driver_ids"),
                parameters.get("score_type", "overall"),
                parameters.get("time_range"),
                parameters.get("trend_period", "weekly")
            )
        else:
            return {
                "success": False,
                "error": f"Unknown method: {method_name}",
                "data": None
            }