"""
Token-efficient summarization utilities for LLM consumption.
"""
from typing import Any, Dict, List, Optional
import json
from datetime import datetime


class Summarizer:
    """Generate token-efficient summaries of analytics results."""
    
    def __init__(self, max_tokens: int = 500):
        """
        Initialize summarizer.
        
        Args:
            max_tokens: Approximate maximum tokens for summary
        """
        self.max_tokens = max_tokens
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough estimate of tokens (1 token ≈ 4 characters)."""
        return len(text) // 4
    
    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to approximate token count."""
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        return text[:max_chars - 3] + "..."
    
    def summarize_driver_data(
        self,
        driver_data: Dict[str, Any],
        include_details: bool = False
    ) -> str:
        """
        Summarize driver information.
        
        Args:
            driver_data: Driver data dictionary
            include_details: Include detailed information
            
        Returns:
            Token-efficient summary string
        """
        summary_parts = []
        
        # Basic info
        driver_id = driver_data.get('driver_id', 'unknown')
        name = driver_data.get('name', 'N/A')
        summary_parts.append(f"Driver {driver_id} ({name})")
        
        if include_details:
            email = driver_data.get('email')
            phone = driver_data.get('phone')
            if email:
                summary_parts.append(f"email: {email}")
            if phone:
                summary_parts.append(f"phone: {phone}")
        
        return " | ".join(summary_parts)
    
    def summarize_scores(
        self,
        score_data: List[Dict[str, Any]]
    ) -> str:
        """
        Summarize score data.
        
        Args:
            score_data: List of score dictionaries
            
        Returns:
            Token-efficient summary
        """
        if not score_data:
            return "No score data available"
        
        summary_parts = []
        
        for score in score_data[:5]:  # Limit to top 5
            driver_id = score.get('driver_id', 'unknown')
            value = score.get('score', 0)
            rank = score.get('rank')
            
            part = f"Driver {driver_id}: {value:.2f}"
            if rank:
                part += f" (rank {rank})"
            summary_parts.append(part)
        
        if len(score_data) > 5:
            summary_parts.append(f"... and {len(score_data) - 5} more drivers")
        
        return " | ".join(summary_parts)
    
    def summarize_trips(
        self,
        trip_data: List[Dict[str, Any]]
    ) -> str:
        """
        Summarize trip data.
        
        Args:
            trip_data: List of trip dictionaries
            
        Returns:
            Token-efficient summary
        """
        if not trip_data:
            return "No trip data available"
        
        total_trips = len(trip_data)
        total_distance = sum(t.get('distance', 0) for t in trip_data)
        total_duration = sum(t.get('duration', 0) for t in trip_data)
        
        avg_distance = total_distance / total_trips if total_trips > 0 else 0
        avg_duration = total_duration / total_trips if total_trips > 0 else 0
        
        return (
            f"{total_trips} trips | "
            f"Total: {total_distance:.1f}mi, {total_duration:.1f}min | "
            f"Avg: {avg_distance:.1f}mi, {avg_duration:.1f}min per trip"
        )
    
    def summarize_trends(
        self,
        trend_data: List[Dict[str, Any]]
    ) -> str:
        """
        Summarize trend data.
        
        Args:
            trend_data: List of trend data points
            
        Returns:
            Token-efficient summary
        """
        if not trend_data or len(trend_data) < 2:
            return "Insufficient data for trend analysis"
        
        # Get first and last values
        first_point = trend_data[0]
        last_point = trend_data[-1]
        
        field = first_point.get('field', 'value')
        first_value = first_point.get('value', 0)
        last_value = last_point.get('value', 0)
        
        # Calculate change
        change = last_value - first_value
        pct_change = (change / first_value * 100) if first_value != 0 else 0
        
        direction = "increased" if change > 0 else "decreased" if change < 0 else "remained stable"
        
        return (
            f"{field.capitalize()} {direction} from {first_value:.2f} to {last_value:.2f} "
            f"({pct_change:+.1f}%) over {len(trend_data)} data points"
        )
    
    def summarize_comparison(
        self,
        comparison_data: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Summarize comparison data.
        
        Args:
            comparison_data: Dictionary of entity comparisons
            
        Returns:
            Token-efficient summary
        """
        if not comparison_data:
            return "No comparison data available"
        
        entities = list(comparison_data.keys())
        if len(entities) == 0:
            return "No entities to compare"
        
        summary_parts = [f"Comparing {len(entities)} entities:"]
        
        for entity_id in entities[:3]:  # Limit to 3 entities
            entity_data = comparison_data[entity_id]
            metrics = [f"{k}={v}" for k, v in list(entity_data.items())[:3]]
            summary_parts.append(f"{entity_id}: {', '.join(metrics)}")
        
        if len(entities) > 3:
            summary_parts.append(f"... and {len(entities) - 3} more")
        
        return " | ".join(summary_parts)
    
    def summarize_aggregation(
        self,
        agg_data: Dict[str, Any]
    ) -> str:
        """
        Summarize aggregation results.
        
        Args:
            agg_data: Dictionary of aggregation results
            
        Returns:
            Token-efficient summary
        """
        if not agg_data:
            return "No aggregation data available"
        
        summary_parts = []
        for key, value in list(agg_data.items())[:5]:  # Limit to 5 metrics
            if isinstance(value, float):
                summary_parts.append(f"{key}: {value:.2f}")
            else:
                summary_parts.append(f"{key}: {value}")
        
        return " | ".join(summary_parts)
    
    def create_comprehensive_summary(
        self,
        data: Dict[str, Any],
        report_type: str
    ) -> str:
        """
        Create comprehensive summary based on report type.
        
        Args:
            data: Complete response data
            report_type: Type of report
            
        Returns:
            Comprehensive token-efficient summary
        """
        summary_parts = [f"Report Type: {report_type}"]
        
        # Add component summaries
        if 'drivers' in data:
            driver_count = len(data['drivers'])
            summary_parts.append(f"Drivers: {driver_count}")
        
        if 'scores' in data:
            score_summary = self.summarize_scores(data['scores'])
            summary_parts.append(f"Scores: {score_summary}")
        
        if 'trips' in data:
            trip_summary = self.summarize_trips(data['trips'])
            summary_parts.append(f"Trips: {trip_summary}")
        
        if 'trends' in data:
            trend_summary = self.summarize_trends(data['trends'])
            summary_parts.append(f"Trends: {trend_summary}")
        
        if 'aggregations' in data:
            agg_summary = self.summarize_aggregation(data['aggregations'])
            summary_parts.append(f"Aggregations: {agg_summary}")
        
        if 'comparison' in data:
            comp_summary = self.summarize_comparison(data['comparison'])
            summary_parts.append(comp_summary)
        
        # Combine and truncate if needed
        full_summary = "\n".join(summary_parts)
        return self._truncate_to_tokens(full_summary, self.max_tokens)
    
    def compress_data(
        self,
        data: Any,
        preserve_keys: Optional[List[str]] = None
    ) -> Any:
        """
        Compress data by removing verbose fields.
        
        Args:
            data: Data to compress
            preserve_keys: Keys to always preserve
            
        Returns:
            Compressed data
        """
        preserve_keys = preserve_keys or []
        
        if isinstance(data, dict):
            compressed = {}
            for key, value in data.items():
                # Skip verbose fields unless in preserve list
                if key in preserve_keys or key in ['id', 'name', 'value', 'score']:
                    compressed[key] = self.compress_data(value, preserve_keys)
            return compressed
        
        elif isinstance(data, list):
            # Limit list size for compression
            if len(data) > 10:
                return [self.compress_data(item, preserve_keys) for item in data[:10]]
            return [self.compress_data(item, preserve_keys) for item in data]
        
        else:
            return data
