"""Agent metadata, capabilities, and description for the Driver Insight Agent."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AgentCapability:
    """Individual agent capability definition."""
    name: str
    description: str
    input_types: List[str]
    output_types: List[str]
    complexity: str  # "simple", "moderate", "complex"
    estimated_time_ms: int
    dependencies: List[str] = None


@dataclass
class AgentMetadata:
    """Agent metadata and configuration."""
    name: str
    version: str
    description: str
    author: str
    created_date: datetime
    last_updated: datetime
    supported_languages: List[str]
    tags: List[str]
    license: str = "MIT"


class DriverInsightAgentCard:
    """Abstract card defining the Driver Insight Agent's capabilities and metadata."""
    
    def __init__(self):
        """Initialize the agent card."""
        self.metadata = AgentMetadata(
            name="Driver Insight Agent",
            version="1.0.0",
            description="Comprehensive driver analytics and reporting agent for handling all driver-related data analysis tasks",
            author="Driver Analytics Team",
            created_date=datetime.now(),
            last_updated=datetime.now(),
            supported_languages=["en"],
            tags=["analytics", "reporting", "drivers", "performance", "trends", "scoring"],
            license="MIT"
        )
        
        self.capabilities = self._define_capabilities()
        self.supported_request_types = self._define_supported_request_types()
        self.tool_requirements = self._define_tool_requirements()
    
    def _define_capabilities(self) -> List[AgentCapability]:
        """Define agent capabilities."""
        return [
            AgentCapability(
                name="driver_resolution",
                description="Resolve driver identities from various identifiers (ID, name, email, phone)",
                input_types=["driver_identifiers"],
                output_types=["driver_profiles"],
                complexity="simple",
                estimated_time_ms=500,
                dependencies=["driver_tool"]
            ),
            AgentCapability(
                name="trip_analytics",
                description="Analyze trip data with filtering, aggregation, and time range support",
                input_types=["driver_ids", "time_range", "filters"],
                output_types=["trip_analytics", "aggregated_metrics"],
                complexity="moderate",
                estimated_time_ms=2000,
                dependencies=["trip_tool", "driver_tool"]
            ),
            AgentCapability(
                name="score_analysis",
                description="Analyze driver scores with rankings, comparisons, and trend analysis",
                input_types=["driver_ids", "score_types", "time_range"],
                output_types=["score_analytics", "rankings", "comparisons"],
                complexity="moderate",
                estimated_time_ms=1500,
                dependencies=["score_tool", "driver_tool"]
            ),
            AgentCapability(
                name="trend_analysis",
                description="Perform time-series analysis and trend forecasting for driver metrics",
                input_types=["driver_ids", "metrics", "time_range"],
                output_types=["trend_analysis", "forecasts", "anomalies"],
                complexity="complex",
                estimated_time_ms=3000,
                dependencies=["trend_tool", "driver_tool"]
            ),
            AgentCapability(
                name="comparative_analysis",
                description="Compare performance between multiple drivers across various metrics",
                input_types=["driver_ids", "comparison_metrics"],
                output_types=["comparative_analysis", "relative_performance"],
                complexity="complex",
                estimated_time_ms=2500,
                dependencies=["score_tool", "trip_tool", "driver_tool"]
            ),
            AgentCapability(
                name="ranking_generation",
                description="Generate driver rankings based on various performance criteria",
                input_types=["ranking_criteria", "time_range"],
                output_types=["rankings", "percentiles", "performance_tiers"],
                complexity="moderate",
                estimated_time_ms=1200,
                dependencies=["score_tool"]
            ),
            AgentCapability(
                name="anomaly_detection",
                description="Detect anomalies and outliers in driver performance data",
                input_types=["driver_ids", "metrics", "sensitivity"],
                output_types=["anomalies", "categorized_anomalies"],
                complexity="complex",
                estimated_time_ms=2800,
                dependencies=["trend_tool"]
            ),
            AgentCapability(
                name="batch_processing",
                description="Process multiple drivers or requests concurrently with pagination support",
                input_types=["batch_requests", "pagination_config"],
                output_types=["batch_results", "pagination_info"],
                complexity="complex",
                estimated_time_ms=5000,
                dependencies=["all_tools"]
            ),
            AgentCapability(
                name="data_summarization",
                description="Generate token-efficient summaries optimized for downstream LLM consumption",
                input_types=["analytics_results", "summarization_config"],
                output_types=["summaries", "key_insights"],
                complexity="moderate",
                estimated_time_ms=800,
                dependencies=["summarizer"]
            ),
            AgentCapability(
                name="pattern_recognition",
                description="Identify patterns in driver behavior, performance, and operational data",
                input_types=["driver_data", "pattern_types"],
                output_types=["identified_patterns", "pattern_insights"],
                complexity="complex",
                estimated_time_ms=3500,
                dependencies=["trend_tool", "trip_tool"]
            )
        ]
    
    def _define_supported_request_types(self) -> Dict[str, Dict[str, Any]]:
        """Define supported request types and their configurations."""
        return {
            "score": {
                "description": "Score-only analysis and reporting",
                "required_fields": ["drivers"],
                "optional_fields": ["time_range", "score_types", "aggregations"],
                "primary_tools": ["driver_tool", "score_tool"],
                "estimated_time_ms": 2000,
                "complexity": "moderate"
            },
            "trip": {
                "description": "Trip-only analysis and reporting",
                "required_fields": ["drivers"],
                "optional_fields": ["time_range", "filters", "aggregations"],
                "primary_tools": ["driver_tool", "trip_tool"],
                "estimated_time_ms": 2500,
                "complexity": "moderate"
            },
            "combined": {
                "description": "Combined score and trip analysis",
                "required_fields": ["drivers"],
                "optional_fields": ["time_range", "filters", "aggregations"],
                "primary_tools": ["driver_tool", "score_tool", "trip_tool"],
                "estimated_time_ms": 4000,
                "complexity": "complex"
            },
            "trend": {
                "description": "Time-series and trend analysis",
                "required_fields": ["drivers", "metrics"],
                "optional_fields": ["time_range", "aggregation_period"],
                "primary_tools": ["driver_tool", "trend_tool"],
                "estimated_time_ms": 3500,
                "complexity": "complex"
            },
            "comparison": {
                "description": "Side-by-side driver comparisons",
                "required_fields": ["drivers"],
                "optional_fields": ["time_range", "comparison_metrics"],
                "primary_tools": ["driver_tool", "score_tool", "trip_tool"],
                "estimated_time_ms": 3000,
                "complexity": "complex"
            },
            "ranking": {
                "description": "Driver rankings and performance tiers",
                "required_fields": [],
                "optional_fields": ["score_type", "time_range", "limit"],
                "primary_tools": ["score_tool"],
                "estimated_time_ms": 1500,
                "complexity": "moderate"
            }
        }
    
    def _define_tool_requirements(self) -> Dict[str, Dict[str, Any]]:
        """Define tool requirements and dependencies."""
        return {
            "driver_tool": {
                "required": True,
                "description": "Essential for driver resolution and validation",
                "fallback": None,
                "timeout_ms": 10000
            },
            "trip_tool": {
                "required": False,
                "description": "Required for trip-related analysis",
                "fallback": "basic_trip_summary",
                "timeout_ms": 15000
            },
            "score_tool": {
                "required": False,
                "description": "Required for score-related analysis",
                "fallback": "basic_score_summary",
                "timeout_ms": 10000
            },
            "trend_tool": {
                "required": False,
                "description": "Required for trend and time-series analysis",
                "fallback": "basic_trend_summary",
                "timeout_ms": 20000
            }
        }
    
    def get_capability_by_name(self, capability_name: str) -> Optional[AgentCapability]:
        """Get capability by name."""
        for capability in self.capabilities:
            if capability.name == capability_name:
                return capability
        return None
    
    def get_capabilities_for_request_type(self, request_type: str) -> List[AgentCapability]:
        """Get relevant capabilities for a request type."""
        request_config = self.supported_request_types.get(request_type)
        if not request_config:
            return []
        
        relevant_capabilities = []
        primary_tools = request_config.get("primary_tools", [])
        
        for capability in self.capabilities:
            if capability.dependencies:
                # Check if any of the capability's dependencies are in primary tools
                if any(dep in primary_tools for dep in capability.dependencies):
                    relevant_capabilities.append(capability)
            elif "all_tools" in primary_tools:
                relevant_capabilities.append(capability)
        
        return relevant_capabilities
    
    def estimate_request_complexity(self, request_type: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate complexity and resource requirements for a request."""
        request_config = self.supported_request_types.get(request_type, {})
        base_complexity = request_config.get("complexity", "moderate")
        base_time_ms = request_config.get("estimated_time_ms", 2000)
        
        # Adjust based on request data
        complexity_multiplier = 1.0
        
        # Driver count impact
        drivers = request_data.get("drivers", [])
        if len(drivers) > 10:
            complexity_multiplier *= 1.5
        elif len(drivers) > 50:
            complexity_multiplier *= 2.0
        
        # Time range impact
        time_range = request_data.get("time_range")
        if time_range:
            try:
                from dateutil.parser import parse as parse_date
                start_date = parse_date(time_range.get("start_date", ""))
                end_date = parse_date(time_range.get("end_date", ""))
                days_span = (end_date - start_date).days
                
                if days_span > 90:
                    complexity_multiplier *= 1.3
                elif days_span > 365:
                    complexity_multiplier *= 1.8
            except:
                pass
        
        # Filters and aggregations impact
        filters = request_data.get("filters", [])
        aggregations = request_data.get("aggregations", [])
        
        if len(filters) > 5:
            complexity_multiplier *= 1.2
        if len(aggregations) > 3:
            complexity_multiplier *= 1.1
        
        # Calculate final estimates
        estimated_time_ms = int(base_time_ms * complexity_multiplier)
        
        if complexity_multiplier > 2.0:
            final_complexity = "very_complex"
        elif complexity_multiplier > 1.5:
            final_complexity = "complex"
        elif complexity_multiplier > 1.2:
            final_complexity = "moderate"
        else:
            final_complexity = "simple"
        
        return {
            "base_complexity": base_complexity,
            "final_complexity": final_complexity,
            "complexity_multiplier": round(complexity_multiplier, 2),
            "estimated_time_ms": estimated_time_ms,
            "estimated_time_seconds": round(estimated_time_ms / 1000, 1),
            "resource_requirements": {
                "memory_intensive": len(drivers) > 20 or complexity_multiplier > 1.8,
                "cpu_intensive": final_complexity in ["complex", "very_complex"],
                "cache_beneficial": len(drivers) > 5 or complexity_multiplier > 1.3
            }
        }
    
    def validate_request_compatibility(self, request_type: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate if a request is compatible with agent capabilities."""
        if request_type not in self.supported_request_types:
            return {
                "compatible": False,
                "errors": [f"Unsupported request type: {request_type}"],
                "warnings": [],
                "suggestions": list(self.supported_request_types.keys())
            }
        
        request_config = self.supported_request_types[request_type]
        errors = []
        warnings = []
        suggestions = []
        
        # Check required fields
        required_fields = request_config.get("required_fields", [])
        for field in required_fields:
            if field not in request_data:
                errors.append(f"Missing required field: {field}")
        
        # Validate driver identifiers if present
        if "drivers" in request_data:
            drivers = request_data["drivers"]
            if not isinstance(drivers, list):
                errors.append("Drivers field must be a list")
            elif len(drivers) == 0:
                warnings.append("No drivers specified")
            elif len(drivers) > 100:
                warnings.append("Large number of drivers may impact performance")
                suggestions.append("Consider using pagination for better performance")
        
        # Validate time range if present
        if "time_range" in request_data:
            time_range = request_data["time_range"]
            if not isinstance(time_range, dict):
                errors.append("Time range must be an object")
            else:
                if "start_date" not in time_range or "end_date" not in time_range:
                    errors.append("Time range must include start_date and end_date")
        
        # Check for potentially expensive operations
        complexity_estimate = self.estimate_request_complexity(request_type, request_data)
        if complexity_estimate["final_complexity"] in ["complex", "very_complex"]:
            warnings.append("Request may require significant processing time and resources")
            suggestions.append("Consider using caching or breaking down into smaller requests")
        
        return {
            "compatible": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
            "complexity_estimate": complexity_estimate
        }
    
    def get_agent_summary(self) -> Dict[str, Any]:
        """Get comprehensive agent summary."""
        return {
            "metadata": {
                "name": self.metadata.name,
                "version": self.metadata.version,
                "description": self.metadata.description,
                "author": self.metadata.author,
                "license": self.metadata.license,
                "tags": self.metadata.tags
            },
            "capabilities": {
                "total_capabilities": len(self.capabilities),
                "capability_names": [cap.name for cap in self.capabilities],
                "complexity_distribution": {
                    "simple": len([cap for cap in self.capabilities if cap.complexity == "simple"]),
                    "moderate": len([cap for cap in self.capabilities if cap.complexity == "moderate"]),
                    "complex": len([cap for cap in self.capabilities if cap.complexity == "complex"])
                }
            },
            "supported_request_types": {
                "total_types": len(self.supported_request_types),
                "request_types": list(self.supported_request_types.keys()),
                "complexity_range": {
                    "simple": len([rt for rt in self.supported_request_types.values() if rt.get("complexity") == "simple"]),
                    "moderate": len([rt for rt in self.supported_request_types.values() if rt.get("complexity") == "moderate"]),
                    "complex": len([rt for rt in self.supported_request_types.values() if rt.get("complexity") == "complex"])
                }
            },
            "tool_requirements": {
                "required_tools": [name for name, req in self.tool_requirements.items() if req["required"]],
                "optional_tools": [name for name, req in self.tool_requirements.items() if not req["required"]],
                "total_tools": len(self.tool_requirements)
            },
            "performance_characteristics": {
                "avg_response_time_ms": sum(rt.get("estimated_time_ms", 0) for rt in self.supported_request_types.values()) / len(self.supported_request_types),
                "supports_batch_processing": True,
                "supports_caching": True,
                "supports_pagination": True,
                "concurrent_request_capable": True
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent card to dictionary representation."""
        return {
            "metadata": {
                "name": self.metadata.name,
                "version": self.metadata.version,
                "description": self.metadata.description,
                "author": self.metadata.author,
                "created_date": self.metadata.created_date.isoformat(),
                "last_updated": self.metadata.last_updated.isoformat(),
                "supported_languages": self.metadata.supported_languages,
                "tags": self.metadata.tags,
                "license": self.metadata.license
            },
            "capabilities": [
                {
                    "name": cap.name,
                    "description": cap.description,
                    "input_types": cap.input_types,
                    "output_types": cap.output_types,
                    "complexity": cap.complexity,
                    "estimated_time_ms": cap.estimated_time_ms,
                    "dependencies": cap.dependencies or []
                }
                for cap in self.capabilities
            ],
            "supported_request_types": self.supported_request_types,
            "tool_requirements": self.tool_requirements
        }