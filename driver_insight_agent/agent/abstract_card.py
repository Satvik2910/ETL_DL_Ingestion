"""
Agent Abstract Card - Metadata, capabilities, and description.
Provides information about the Driver Insight Agent's capabilities.
"""
from typing import Any, Dict, List
from datetime import datetime


class AgentAbstractCard:
    """Abstract card describing the Driver Insight Agent's capabilities."""
    
    def __init__(self):
        self.name = "Driver Insight Agent"
        self.version = "1.0.0"
        self.description = (
            "Modular analytics agent for comprehensive driver insights, "
            "supporting score analysis, trip summaries, trend detection, "
            "rankings, comparisons, and batch operations."
        )
        self.created_at = datetime.now().isoformat()
    
    def get_card(self) -> Dict[str, Any]:
        """
        Get complete agent abstract card.
        
        Returns:
            Dictionary with agent metadata and capabilities
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "created_at": self.created_at,
            "capabilities": self.get_capabilities(),
            "supported_reports": self.get_supported_reports(),
            "features": self.get_features(),
            "technical_specs": self.get_technical_specs(),
            "usage_examples": self.get_usage_examples()
        }
    
    def get_capabilities(self) -> List[Dict[str, Any]]:
        """Get list of agent capabilities."""
        return [
            {
                "name": "Driver Resolution",
                "description": "Resolve drivers by ID, name, email, or phone number",
                "inputs": ["driver_ids", "driver_names", "driver_emails", "driver_phones"],
                "outputs": ["driver_info"]
            },
            {
                "name": "Score Analysis",
                "description": "Aggregate and analyze driver performance scores",
                "inputs": ["driver_ids", "time_range", "aggregation_type"],
                "outputs": ["scores", "rankings", "comparisons"]
            },
            {
                "name": "Trip Analytics",
                "description": "Analyze trip data with filtering and summaries",
                "inputs": ["driver_ids", "time_range", "filters"],
                "outputs": ["trips", "trip_summary"]
            },
            {
                "name": "Trend Analysis",
                "description": "Detect and analyze time-series trends",
                "inputs": ["driver_ids", "metric", "time_range", "granularity"],
                "outputs": ["trends", "anomalies", "moving_averages"]
            },
            {
                "name": "Batch Processing",
                "description": "Process multiple drivers concurrently",
                "inputs": ["multiple_driver_ids"],
                "outputs": ["aggregated_results"]
            },
            {
                "name": "Rankings & Comparisons",
                "description": "Rank drivers and perform side-by-side comparisons",
                "inputs": ["driver_ids", "metric"],
                "outputs": ["rankings", "comparison_matrix"]
            },
            {
                "name": "Filtering & Aggregation",
                "description": "Apply complex filters and aggregations",
                "inputs": ["filters", "aggregations"],
                "outputs": ["filtered_data", "aggregated_metrics"]
            },
            {
                "name": "Caching",
                "description": "Cache results for improved performance",
                "inputs": ["cache_enabled"],
                "outputs": ["cached_results", "cache_stats"]
            }
        ]
    
    def get_supported_reports(self) -> List[Dict[str, str]]:
        """Get list of supported report types."""
        return [
            {
                "type": "score_only",
                "description": "Driver scores with rankings and comparisons",
                "tools_used": ["driver_tool", "score_tool"]
            },
            {
                "type": "trip_only",
                "description": "Trip analytics with summaries",
                "tools_used": ["driver_tool", "trip_tool"]
            },
            {
                "type": "combined",
                "description": "Combined score and trip analytics",
                "tools_used": ["driver_tool", "score_tool", "trip_tool"]
            },
            {
                "type": "trend",
                "description": "Time-series trend analysis",
                "tools_used": ["driver_tool", "score_tool", "trend_tool"]
            },
            {
                "type": "ranking",
                "description": "Driver rankings by performance metrics",
                "tools_used": ["driver_tool", "score_tool"]
            },
            {
                "type": "comparison",
                "description": "Side-by-side driver comparisons",
                "tools_used": ["driver_tool", "score_tool", "trip_tool"]
            }
        ]
    
    def get_features(self) -> List[str]:
        """Get list of key features."""
        return [
            "Deterministic and idempotent operations",
            "Modular and scalable architecture",
            "Concurrent batch processing",
            "TTL and persistent caching",
            "Retry mechanism with exponential backoff",
            "Token-efficient summarization",
            "Comprehensive error handling",
            "Schema validation",
            "Time-range filtering",
            "Complex filtering operations",
            "Multiple aggregation functions",
            "Pagination and chunking",
            "Tool-to-tool data passing",
            "Dynamic tool selection",
            "MCP tool registry",
            "Configurable via YAML"
        ]
    
    def get_technical_specs(self) -> Dict[str, Any]:
        """Get technical specifications."""
        return {
            "architecture": "Modular MCP-based agent system",
            "language": "Python 3.9+",
            "async_support": True,
            "concurrency": "asyncio with configurable workers",
            "caching": {
                "type": "TTL-based with persistent storage",
                "default_ttl": "3600 seconds",
                "max_cache_size": "1000 entries"
            },
            "pagination": {
                "default_page_size": 100,
                "max_page_size": 1000,
                "supports_offset_limit": True
            },
            "retry": {
                "max_attempts": 3,
                "backoff_strategy": "exponential",
                "backoff_base": 2
            },
            "performance": {
                "optimized_for": "Large datasets",
                "supports_streaming": True,
                "batch_processing": True
            }
        }
    
    def get_usage_examples(self) -> List[Dict[str, Any]]:
        """Get usage examples."""
        return [
            {
                "scenario": "Get driver score rankings",
                "request": {
                    "request_id": "req_001",
                    "report_type": "ranking",
                    "driver_ids": ["D001", "D002", "D003"],
                    "start_date": "2024-01-01T00:00:00Z",
                    "end_date": "2024-01-31T23:59:59Z"
                },
                "description": "Ranks drivers by average score for January 2024"
            },
            {
                "scenario": "Batch trip summary",
                "request": {
                    "request_id": "req_002",
                    "report_type": "trip_only",
                    "driver_ids": ["D001", "D002", "D003", "D004", "D005"],
                    "start_date": "2024-01-01T00:00:00Z",
                    "end_date": "2024-03-31T23:59:59Z",
                    "filters": [
                        {
                            "field": "distance",
                            "operator": "gt",
                            "value": 50
                        }
                    ]
                },
                "description": "Trip summaries for multiple drivers with distance filter"
            },
            {
                "scenario": "Trend analysis",
                "request": {
                    "request_id": "req_003",
                    "report_type": "trend",
                    "driver_ids": ["D001"],
                    "start_date": "2024-01-01T00:00:00Z",
                    "end_date": "2024-03-31T23:59:59Z",
                    "aggregations": ["avg"]
                },
                "description": "Analyze score trends over Q1 2024"
            },
            {
                "scenario": "Driver comparison",
                "request": {
                    "request_id": "req_004",
                    "report_type": "comparison",
                    "driver_ids": ["D001", "D002"],
                    "start_date": "2024-01-01T00:00:00Z",
                    "end_date": "2024-01-31T23:59:59Z"
                },
                "description": "Side-by-side comparison of two drivers"
            }
        ]
    
    def get_schema(self) -> Dict[str, Any]:
        """Get request/response schemas."""
        return {
            "request_schema": {
                "request_id": "string (required)",
                "report_type": "enum (score_only|trip_only|combined|trend|ranking|comparison)",
                "driver_ids": "list[string] (optional)",
                "driver_names": "list[string] (optional)",
                "driver_emails": "list[string] (optional)",
                "driver_phones": "list[string] (optional)",
                "start_date": "string ISO8601 (optional)",
                "end_date": "string ISO8601 (optional)",
                "filters": "list[FilterCondition] (optional)",
                "aggregations": "list[string] (optional)",
                "limit": "integer (optional)",
                "offset": "integer (optional)",
                "sort_by": "string (optional)",
                "sort_order": "enum (asc|desc) (optional)"
            },
            "response_schema": {
                "request_id": "string",
                "success": "boolean",
                "data": "dict (optional)",
                "summary": "string (optional)",
                "error": "string (optional)",
                "execution_time_ms": "float",
                "tools_executed": "list[string]",
                "cache_hits": "integer"
            }
        }
    
    def print_card(self) -> None:
        """Print the abstract card in a readable format."""
        card = self.get_card()
        
        print("=" * 80)
        print(f"Agent: {card['name']}")
        print(f"Version: {card['version']}")
        print(f"Description: {card['description']}")
        print("=" * 80)
        
        print("\nCapabilities:")
        for cap in card['capabilities']:
            print(f"  - {cap['name']}: {cap['description']}")
        
        print("\nSupported Reports:")
        for report in card['supported_reports']:
            print(f"  - {report['type']}: {report['description']}")
        
        print("\nKey Features:")
        for feature in card['features']:
            print(f"  - {feature}")
        
        print("=" * 80)
