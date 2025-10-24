"""
Score Tool - Score aggregation, rankings, and comparisons.
Calculates and analyzes driver performance scores.
"""
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import random


class ScoreTool:
    """Tool for driver score analysis and comparisons."""
    
    def __init__(self):
        self.name = "score_tool"
        self.description = "Calculates driver scores, rankings, and comparisons"
        self.version = "1.0.0"
        
        # Mock score database
        self._score_db = self._initialize_mock_data()
    
    def _initialize_mock_data(self) -> List[Dict[str, Any]]:
        """Initialize mock score data for demonstration."""
        scores = []
        driver_ids = ["D001", "D002", "D003", "D004", "D005"]
        
        # Generate daily scores for the last 90 days
        base_date = datetime.now() - timedelta(days=90)
        
        for driver_id in driver_ids:
            # Base score varies by driver
            base_score = random.uniform(70, 95)
            
            for day in range(90):
                score_date = base_date + timedelta(days=day)
                
                # Add daily variation
                daily_score = base_score + random.uniform(-10, 10)
                daily_score = max(0, min(100, daily_score))  # Clamp to 0-100
                
                scores.append({
                    "driver_id": driver_id,
                    "date": score_date.isoformat(),
                    "score": round(daily_score, 2),
                    "safety_score": round(random.uniform(70, 100), 2),
                    "efficiency_score": round(random.uniform(60, 100), 2),
                    "reliability_score": round(random.uniform(80, 100), 2),
                    "customer_rating": round(random.uniform(3.5, 5.0), 1),
                    "trips_count": random.randint(0, 10)
                })
        
        return scores
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute score analysis.
        
        Args:
            parameters: Dictionary containing:
                - driver_ids: List of driver IDs
                - start_date: Start date (ISO 8601) (optional)
                - end_date: End date (ISO 8601) (optional)
                - aggregation: Aggregation type (avg, min, max) (optional)
                - ranking: Include ranking (optional)
                - comparison: Enable comparison mode (optional)
                
        Returns:
            Dictionary with execution results
        """
        start_time = time.time()
        
        try:
            scores = await self._get_scores(parameters)
            
            # Apply aggregation
            aggregation_type = parameters.get('aggregation', 'avg')
            aggregated_scores = self._aggregate_scores(scores, aggregation_type)
            
            # Apply ranking if requested
            if parameters.get('ranking', False):
                aggregated_scores = self._rank_scores(aggregated_scores)
            
            # Apply comparison if requested
            comparison = None
            if parameters.get('comparison', False):
                comparison = self._compare_drivers(aggregated_scores)
            
            execution_time = (time.time() - start_time) * 1000
            
            return {
                "success": True,
                "data": aggregated_scores,
                "comparison": comparison,
                "count": len(aggregated_scores),
                "execution_time_ms": execution_time,
                "error": None
            }
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return {
                "success": False,
                "data": None,
                "comparison": None,
                "count": 0,
                "execution_time_ms": execution_time,
                "error": str(e)
            }
    
    async def _get_scores(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get scores based on parameters."""
        driver_ids = parameters.get('driver_ids', [])
        start_date = parameters.get('start_date')
        end_date = parameters.get('end_date')
        
        # Filter by driver IDs
        scores = [score for score in self._score_db if score['driver_id'] in driver_ids]
        
        # Filter by date range
        if start_date or end_date:
            from utils.filter_engine import FilterEngine
            filter_engine = FilterEngine()
            
            if start_date and end_date:
                scores = filter_engine.filter_by_time_range(
                    scores,
                    'date',
                    start_date,
                    end_date
                )
        
        return scores
    
    def _aggregate_scores(
        self,
        scores: List[Dict[str, Any]],
        aggregation_type: str
    ) -> List[Dict[str, Any]]:
        """Aggregate scores by driver."""
        from utils.aggregation_engine import AggregationEngine
        from collections import defaultdict
        
        agg_engine = AggregationEngine()
        driver_scores = defaultdict(list)
        
        # Group scores by driver
        for score in scores:
            driver_scores[score['driver_id']].append(score)
        
        # Aggregate for each driver
        aggregated = []
        for driver_id, driver_score_list in driver_scores.items():
            agg_result = {
                "driver_id": driver_id,
                "score": agg_engine.aggregate(driver_score_list, 'score', aggregation_type),
                "safety_score": agg_engine.aggregate(driver_score_list, 'safety_score', aggregation_type),
                "efficiency_score": agg_engine.aggregate(driver_score_list, 'efficiency_score', aggregation_type),
                "reliability_score": agg_engine.aggregate(driver_score_list, 'reliability_score', aggregation_type),
                "customer_rating": agg_engine.aggregate(driver_score_list, 'customer_rating', aggregation_type),
                "total_trips": sum(s['trips_count'] for s in driver_score_list),
                "data_points": len(driver_score_list),
                "aggregation_type": aggregation_type
            }
            aggregated.append(agg_result)
        
        return aggregated
    
    def _rank_scores(self, scores: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank drivers by score."""
        from utils.aggregation_engine import AggregationEngine
        
        agg_engine = AggregationEngine()
        ranked = agg_engine.rank(scores, 'score', descending=True)
        
        return ranked
    
    def _compare_drivers(self, scores: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comparison summary."""
        if not scores:
            return {}
        
        comparison = {
            "drivers": [s['driver_id'] for s in scores],
            "scores": {s['driver_id']: s['score'] for s in scores},
            "best_performer": max(scores, key=lambda x: x['score'])['driver_id'],
            "worst_performer": min(scores, key=lambda x: x['score'])['driver_id'],
            "average_score": sum(s['score'] for s in scores) / len(scores),
            "score_range": max(s['score'] for s in scores) - min(s['score'] for s in scores)
        }
        
        return comparison
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return tool capabilities."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parameters": {
                "driver_ids": {"type": "list", "required": True},
                "start_date": {"type": "string", "required": False},
                "end_date": {"type": "string", "required": False},
                "aggregation": {"type": "string", "required": False, "default": "avg"},
                "ranking": {"type": "boolean", "required": False, "default": False},
                "comparison": {"type": "boolean", "required": False, "default": False}
            },
            "output_schema": {
                "success": "boolean",
                "data": "list[dict]",
                "comparison": "dict",
                "count": "integer",
                "execution_time_ms": "float"
            }
        }
