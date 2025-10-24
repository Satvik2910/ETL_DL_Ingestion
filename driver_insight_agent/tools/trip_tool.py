"""Trip analytics tool with filtering and time range support."""

from typing import Dict, List, Any, Optional, Union
import asyncio
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date

from ..utils.validation import TimeRange, ValidationError
from ..utils.filter_engine import FilterEngine
from ..utils.aggregation_engine import AggregationEngine
from ..utils.pagination import PaginationEngine, PaginationConfig
from ..cache.cache_manager import get_cache_manager


@dataclass
class TripRecord:
    """Individual trip record."""
    trip_id: str
    driver_id: str
    start_time: datetime
    end_time: datetime
    distance_miles: float
    duration_minutes: int
    start_location: Dict[str, float]  # {"lat": float, "lng": float}
    end_location: Dict[str, float]
    route_efficiency: float  # 0-1 score
    fuel_consumption: Optional[float] = None
    average_speed: Optional[float] = None
    max_speed: Optional[float] = None
    stops_count: int = 0
    weather_conditions: Optional[str] = None
    traffic_conditions: Optional[str] = None
    trip_type: str = "regular"  # regular, urgent, scheduled
    status: str = "completed"  # completed, cancelled, in_progress
    metadata: Optional[Dict[str, Any]] = None


class TripDataSource:
    """Mock data source for trip information."""
    
    def __init__(self):
        """Initialize with sample trip data."""
        self.trips = self._generate_sample_trips()
    
    def _generate_sample_trips(self) -> List[TripRecord]:
        """Generate sample trip data."""
        trips = []
        driver_ids = ["DRV001", "DRV002", "DRV003", "DRV004", "DRV005"]
        trip_types = ["regular", "urgent", "scheduled"]
        weather_conditions = ["clear", "rain", "snow", "fog"]
        traffic_conditions = ["light", "moderate", "heavy"]
        
        # Generate trips for the last 30 days
        base_date = datetime.now() - timedelta(days=30)
        
        for i in range(500):  # Generate 500 sample trips
            driver_id = random.choice(driver_ids)
            trip_date = base_date + timedelta(
                days=random.randint(0, 30),
                hours=random.randint(6, 22),
                minutes=random.randint(0, 59)
            )
            
            duration = random.randint(15, 180)  # 15 minutes to 3 hours
            distance = random.uniform(5, 150)  # 5 to 150 miles
            efficiency = random.uniform(0.6, 1.0)
            
            trip = TripRecord(
                trip_id=f"TRIP{i+1:04d}",
                driver_id=driver_id,
                start_time=trip_date,
                end_time=trip_date + timedelta(minutes=duration),
                distance_miles=round(distance, 2),
                duration_minutes=duration,
                start_location={
                    "lat": round(40.7128 + random.uniform(-0.1, 0.1), 6),
                    "lng": round(-74.0060 + random.uniform(-0.1, 0.1), 6)
                },
                end_location={
                    "lat": round(40.7128 + random.uniform(-0.1, 0.1), 6),
                    "lng": round(-74.0060 + random.uniform(-0.1, 0.1), 6)
                },
                route_efficiency=round(efficiency, 3),
                fuel_consumption=round(distance * random.uniform(0.05, 0.12), 2),
                average_speed=round(distance / (duration / 60), 1) if duration > 0 else 0,
                max_speed=round(distance / (duration / 60) * random.uniform(1.2, 1.8), 1),
                stops_count=random.randint(0, 5),
                weather_conditions=random.choice(weather_conditions),
                traffic_conditions=random.choice(traffic_conditions),
                trip_type=random.choice(trip_types),
                status="completed",
                metadata={
                    "vehicle_id": f"VEH{random.randint(1, 20):03d}",
                    "fuel_type": random.choice(["gasoline", "diesel", "electric", "hybrid"]),
                    "cost": round(distance * random.uniform(0.3, 0.8), 2)
                }
            )
            trips.append(trip)
        
        return trips
    
    async def get_trips_by_driver(self, driver_id: str, 
                                time_range: Optional[TimeRange] = None) -> List[TripRecord]:
        """Get trips for a specific driver."""
        driver_trips = [trip for trip in self.trips if trip.driver_id == driver_id]
        
        if time_range:
            driver_trips = [
                trip for trip in driver_trips
                if time_range.start_date <= trip.start_time <= time_range.end_date
            ]
        
        return driver_trips
    
    async def get_trips_by_time_range(self, time_range: TimeRange) -> List[TripRecord]:
        """Get all trips within a time range."""
        return [
            trip for trip in self.trips
            if time_range.start_date <= trip.start_time <= time_range.end_date
        ]
    
    async def get_trip_by_id(self, trip_id: str) -> Optional[TripRecord]:
        """Get a specific trip by ID."""
        for trip in self.trips:
            if trip.trip_id == trip_id:
                return trip
        return None
    
    async def get_all_trips(self) -> List[TripRecord]:
        """Get all trips."""
        return self.trips.copy()


class TripTool:
    """Tool for trip analytics and management."""
    
    def __init__(self):
        """Initialize trip tool."""
        self.data_source = TripDataSource()
        self.filter_engine = FilterEngine()
        self.aggregation_engine = AggregationEngine()
        self.pagination_engine = PaginationEngine()
        self.cache_manager = get_cache_manager()
        
        # Tool metadata
        self.name = "trip_tool"
        self.description = "Analyze trip data with filtering and time range support"
        self.version = "1.0.0"
    
    async def get_driver_trips(self, driver_id: str, 
                             time_range: Optional[Dict[str, str]] = None,
                             filters: Optional[List[Dict[str, Any]]] = None,
                             aggregations: Optional[List[Dict[str, Any]]] = None,
                             pagination: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get trips for a specific driver with optional filtering and aggregation."""
        try:
            # Check cache first
            cache_key = self._generate_cache_key("driver_trips", driver_id, time_range, filters, aggregations)
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
            
            # Get trips from data source
            trips = await self.data_source.get_trips_by_driver(driver_id, parsed_time_range)
            trip_data = [self._trip_to_dict(trip) for trip in trips]
            
            # Apply filters
            if filters:
                trip_data = self.filter_engine.apply_filters(trip_data, filters)
            
            # Apply pagination if requested
            paginated_data = trip_data
            pagination_info = None
            
            if pagination:
                config = PaginationConfig(
                    page_size=pagination.get('page_size', 100),
                    offset=pagination.get('offset', 0),
                    total_limit=pagination.get('limit')
                )
                
                pages = list(self.pagination_engine.paginate_data(trip_data, config))
                if pages:
                    page = pages[0]  # Get first page
                    paginated_data = page.data
                    pagination_info = {
                        "page_number": page.page_number,
                        "page_size": page.page_size,
                        "total_items": page.total_items,
                        "total_pages": page.total_pages,
                        "has_next": page.has_next,
                        "has_previous": page.has_previous
                    }
            
            # Calculate aggregations if requested
            aggregation_results = {}
            if aggregations and trip_data:
                aggregation_results = self.aggregation_engine.aggregate(trip_data, aggregations)
            
            result = {
                "success": True,
                "data": {
                    "driver_id": driver_id,
                    "trips": paginated_data,
                    "summary": {
                        "total_trips": len(trip_data),
                        "returned_trips": len(paginated_data),
                        "time_range": time_range,
                        "filters_applied": len(filters) if filters else 0
                    },
                    "aggregations": aggregation_results,
                    "pagination": pagination_info
                },
                "metadata": {
                    "tool": self.name,
                    "version": self.version,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Cache result
            await self.cache_manager.set(cache_key, result, ttl=1800, 
                                       tags=['trip_data', f'driver_{driver_id}'])
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get driver trips: {str(e)}",
                "data": None
            }
    
    async def get_trip_analytics(self, driver_ids: Optional[List[str]] = None,
                               time_range: Optional[Dict[str, str]] = None,
                               filters: Optional[List[Dict[str, Any]]] = None,
                               group_by: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive trip analytics."""
        try:
            # Check cache first
            cache_key = self._generate_cache_key("trip_analytics", driver_ids, time_range, filters, group_by)
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
            
            # Get trips data
            if driver_ids:
                all_trips = []
                for driver_id in driver_ids:
                    driver_trips = await self.data_source.get_trips_by_driver(driver_id, parsed_time_range)
                    all_trips.extend(driver_trips)
            elif parsed_time_range:
                all_trips = await self.data_source.get_trips_by_time_range(parsed_time_range)
            else:
                all_trips = await self.data_source.get_all_trips()
            
            trip_data = [self._trip_to_dict(trip) for trip in all_trips]
            
            # Apply filters
            if filters:
                trip_data = self.filter_engine.apply_filters(trip_data, filters)
            
            # Calculate comprehensive analytics
            analytics = await self._calculate_trip_analytics(trip_data, group_by)
            
            result = {
                "success": True,
                "data": {
                    "analytics": analytics,
                    "summary": {
                        "total_trips": len(trip_data),
                        "driver_count": len(set(trip['driver_id'] for trip in trip_data)),
                        "time_range": time_range,
                        "filters_applied": len(filters) if filters else 0,
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
            cache_tags = ['trip_analytics']
            if driver_ids:
                cache_tags.extend([f'driver_{driver_id}' for driver_id in driver_ids])
            
            await self.cache_manager.set(cache_key, result, ttl=3600, tags=cache_tags)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get trip analytics: {str(e)}",
                "data": None
            }
    
    async def get_trip_efficiency_metrics(self, driver_ids: Optional[List[str]] = None,
                                        time_range: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Get efficiency metrics for trips."""
        try:
            # Check cache first
            cache_key = self._generate_cache_key("efficiency_metrics", driver_ids, time_range)
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
            
            # Get trips data
            if driver_ids:
                all_trips = []
                for driver_id in driver_ids:
                    driver_trips = await self.data_source.get_trips_by_driver(driver_id, parsed_time_range)
                    all_trips.extend(driver_trips)
            elif parsed_time_range:
                all_trips = await self.data_source.get_trips_by_time_range(parsed_time_range)
            else:
                all_trips = await self.data_source.get_all_trips()
            
            trip_data = [self._trip_to_dict(trip) for trip in all_trips]
            
            # Calculate efficiency metrics
            efficiency_metrics = await self._calculate_efficiency_metrics(trip_data)
            
            result = {
                "success": True,
                "data": {
                    "efficiency_metrics": efficiency_metrics,
                    "summary": {
                        "total_trips_analyzed": len(trip_data),
                        "driver_count": len(set(trip['driver_id'] for trip in trip_data)),
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
            cache_tags = ['efficiency_metrics']
            if driver_ids:
                cache_tags.extend([f'driver_{driver_id}' for driver_id in driver_ids])
            
            await self.cache_manager.set(cache_key, result, ttl=3600, tags=cache_tags)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get efficiency metrics: {str(e)}",
                "data": None
            }
    
    async def get_trip_patterns(self, driver_ids: Optional[List[str]] = None,
                              time_range: Optional[Dict[str, str]] = None,
                              pattern_type: str = "temporal") -> Dict[str, Any]:
        """Identify patterns in trip data."""
        try:
            # Check cache first
            cache_key = self._generate_cache_key("trip_patterns", driver_ids, time_range, pattern_type)
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
            
            # Get trips data
            if driver_ids:
                all_trips = []
                for driver_id in driver_ids:
                    driver_trips = await self.data_source.get_trips_by_driver(driver_id, parsed_time_range)
                    all_trips.extend(driver_trips)
            elif parsed_time_range:
                all_trips = await self.data_source.get_trips_by_time_range(parsed_time_range)
            else:
                all_trips = await self.data_source.get_all_trips()
            
            trip_data = [self._trip_to_dict(trip) for trip in all_trips]
            
            # Identify patterns based on type
            patterns = await self._identify_trip_patterns(trip_data, pattern_type)
            
            result = {
                "success": True,
                "data": {
                    "patterns": patterns,
                    "pattern_type": pattern_type,
                    "summary": {
                        "total_trips_analyzed": len(trip_data),
                        "driver_count": len(set(trip['driver_id'] for trip in trip_data)),
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
            cache_tags = ['trip_patterns', f'pattern_{pattern_type}']
            if driver_ids:
                cache_tags.extend([f'driver_{driver_id}' for driver_id in driver_ids])
            
            await self.cache_manager.set(cache_key, result, ttl=3600, tags=cache_tags)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to identify trip patterns: {str(e)}",
                "data": None
            }
    
    async def compare_trip_performance(self, driver_ids: List[str],
                                     time_range: Optional[Dict[str, str]] = None,
                                     metrics: Optional[List[str]] = None) -> Dict[str, Any]:
        """Compare trip performance between drivers."""
        try:
            metrics = metrics or ["distance_miles", "duration_minutes", "route_efficiency", "average_speed"]
            
            # Check cache first
            cache_key = self._generate_cache_key("compare_performance", driver_ids, time_range, metrics)
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
            
            # Get trips for each driver
            driver_comparisons = {}
            
            for driver_id in driver_ids:
                driver_trips = await self.data_source.get_trips_by_driver(driver_id, parsed_time_range)
                trip_data = [self._trip_to_dict(trip) for trip in driver_trips]
                
                if trip_data:
                    # Calculate metrics for this driver
                    driver_metrics = {}
                    for metric in metrics:
                        values = [trip.get(metric, 0) for trip in trip_data if trip.get(metric) is not None]
                        if values:
                            import statistics
                            driver_metrics[metric] = {
                                "count": len(values),
                                "avg": round(statistics.mean(values), 2),
                                "min": round(min(values), 2),
                                "max": round(max(values), 2),
                                "total": round(sum(values), 2) if metric in ["distance_miles", "duration_minutes"] else None
                            }
                    
                    driver_comparisons[driver_id] = {
                        "trip_count": len(trip_data),
                        "metrics": driver_metrics
                    }
            
            # Calculate relative performance
            relative_performance = await self._calculate_relative_performance(driver_comparisons, metrics)
            
            result = {
                "success": True,
                "data": {
                    "driver_comparisons": driver_comparisons,
                    "relative_performance": relative_performance,
                    "compared_metrics": metrics,
                    "summary": {
                        "drivers_compared": len(driver_ids),
                        "time_range": time_range,
                        "total_trips": sum(comp["trip_count"] for comp in driver_comparisons.values())
                    }
                },
                "metadata": {
                    "tool": self.name,
                    "version": self.version,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Cache result
            cache_tags = ['trip_comparison'] + [f'driver_{driver_id}' for driver_id in driver_ids]
            await self.cache_manager.set(cache_key, result, ttl=3600, tags=cache_tags)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to compare trip performance: {str(e)}",
                "data": None
            }
    
    def _trip_to_dict(self, trip: TripRecord) -> Dict[str, Any]:
        """Convert trip record to dictionary."""
        return {
            "trip_id": trip.trip_id,
            "driver_id": trip.driver_id,
            "start_time": trip.start_time.isoformat(),
            "end_time": trip.end_time.isoformat(),
            "distance_miles": trip.distance_miles,
            "duration_minutes": trip.duration_minutes,
            "start_location": trip.start_location,
            "end_location": trip.end_location,
            "route_efficiency": trip.route_efficiency,
            "fuel_consumption": trip.fuel_consumption,
            "average_speed": trip.average_speed,
            "max_speed": trip.max_speed,
            "stops_count": trip.stops_count,
            "weather_conditions": trip.weather_conditions,
            "traffic_conditions": trip.traffic_conditions,
            "trip_type": trip.trip_type,
            "status": trip.status,
            "metadata": trip.metadata or {}
        }
    
    async def _calculate_trip_analytics(self, trip_data: List[Dict[str, Any]], 
                                      group_by: Optional[str] = None) -> Dict[str, Any]:
        """Calculate comprehensive trip analytics."""
        if not trip_data:
            return {}
        
        # Basic aggregations
        aggregations = [
            {"operation": "count", "field": "trip_id", "alias": "total_trips"},
            {"operation": "sum", "field": "distance_miles", "alias": "total_distance"},
            {"operation": "sum", "field": "duration_minutes", "alias": "total_duration"},
            {"operation": "avg", "field": "route_efficiency", "alias": "avg_efficiency"},
            {"operation": "avg", "field": "average_speed", "alias": "avg_speed"},
            {"operation": "sum", "field": "fuel_consumption", "alias": "total_fuel"}
        ]
        
        if group_by:
            for agg in aggregations:
                agg["group_by"] = group_by
        
        basic_stats = self.aggregation_engine.aggregate(trip_data, aggregations)
        
        # Additional analytics
        analytics = {
            "basic_statistics": basic_stats,
            "distribution_analysis": self._analyze_distributions(trip_data),
            "efficiency_analysis": await self._calculate_efficiency_metrics(trip_data),
            "temporal_analysis": self._analyze_temporal_patterns(trip_data)
        }
        
        return analytics
    
    async def _calculate_efficiency_metrics(self, trip_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate efficiency metrics."""
        if not trip_data:
            return {}
        
        # Route efficiency analysis
        efficiency_values = [trip.get("route_efficiency", 0) for trip in trip_data if trip.get("route_efficiency")]
        
        # Fuel efficiency analysis
        fuel_efficiency = []
        for trip in trip_data:
            distance = trip.get("distance_miles", 0)
            fuel = trip.get("fuel_consumption", 0)
            if distance > 0 and fuel > 0:
                fuel_efficiency.append(distance / fuel)  # miles per gallon equivalent
        
        # Speed efficiency analysis
        speed_efficiency = []
        for trip in trip_data:
            avg_speed = trip.get("average_speed", 0)
            max_speed = trip.get("max_speed", 0)
            if max_speed > 0:
                speed_efficiency.append(avg_speed / max_speed)
        
        import statistics
        
        metrics = {}
        
        if efficiency_values:
            metrics["route_efficiency"] = {
                "avg": round(statistics.mean(efficiency_values), 3),
                "min": round(min(efficiency_values), 3),
                "max": round(max(efficiency_values), 3),
                "std": round(statistics.stdev(efficiency_values) if len(efficiency_values) > 1 else 0, 3)
            }
        
        if fuel_efficiency:
            metrics["fuel_efficiency"] = {
                "avg_mpg": round(statistics.mean(fuel_efficiency), 2),
                "min_mpg": round(min(fuel_efficiency), 2),
                "max_mpg": round(max(fuel_efficiency), 2)
            }
        
        if speed_efficiency:
            metrics["speed_efficiency"] = {
                "avg_ratio": round(statistics.mean(speed_efficiency), 3),
                "min_ratio": round(min(speed_efficiency), 3),
                "max_ratio": round(max(speed_efficiency), 3)
            }
        
        return metrics
    
    def _analyze_distributions(self, trip_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze data distributions."""
        distributions = {}
        
        # Trip type distribution
        trip_types = {}
        for trip in trip_data:
            trip_type = trip.get("trip_type", "unknown")
            trip_types[trip_type] = trip_types.get(trip_type, 0) + 1
        distributions["trip_types"] = trip_types
        
        # Weather conditions distribution
        weather = {}
        for trip in trip_data:
            condition = trip.get("weather_conditions", "unknown")
            weather[condition] = weather.get(condition, 0) + 1
        distributions["weather_conditions"] = weather
        
        # Traffic conditions distribution
        traffic = {}
        for trip in trip_data:
            condition = trip.get("traffic_conditions", "unknown")
            traffic[condition] = traffic.get(condition, 0) + 1
        distributions["traffic_conditions"] = traffic
        
        return distributions
    
    def _analyze_temporal_patterns(self, trip_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze temporal patterns in trips."""
        patterns = {}
        
        # Hour of day distribution
        hourly_distribution = {}
        daily_distribution = {}
        
        for trip in trip_data:
            start_time_str = trip.get("start_time")
            if start_time_str:
                try:
                    start_time = parse_date(start_time_str)
                    hour = start_time.hour
                    day = start_time.strftime("%A")
                    
                    hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
                    daily_distribution[day] = daily_distribution.get(day, 0) + 1
                except:
                    continue
        
        patterns["hourly_distribution"] = hourly_distribution
        patterns["daily_distribution"] = daily_distribution
        
        return patterns
    
    async def _identify_trip_patterns(self, trip_data: List[Dict[str, Any]], 
                                    pattern_type: str) -> Dict[str, Any]:
        """Identify specific patterns in trip data."""
        patterns = {}
        
        if pattern_type == "temporal":
            patterns = self._analyze_temporal_patterns(trip_data)
        
        elif pattern_type == "efficiency":
            # Identify efficiency patterns
            high_efficiency_trips = [t for t in trip_data if t.get("route_efficiency", 0) > 0.9]
            low_efficiency_trips = [t for t in trip_data if t.get("route_efficiency", 0) < 0.7]
            
            patterns["high_efficiency_count"] = len(high_efficiency_trips)
            patterns["low_efficiency_count"] = len(low_efficiency_trips)
            patterns["efficiency_rate"] = len(high_efficiency_trips) / len(trip_data) if trip_data else 0
        
        elif pattern_type == "distance":
            # Distance-based patterns
            short_trips = [t for t in trip_data if t.get("distance_miles", 0) < 10]
            medium_trips = [t for t in trip_data if 10 <= t.get("distance_miles", 0) < 50]
            long_trips = [t for t in trip_data if t.get("distance_miles", 0) >= 50]
            
            patterns["short_trips"] = len(short_trips)
            patterns["medium_trips"] = len(medium_trips)
            patterns["long_trips"] = len(long_trips)
        
        return patterns
    
    async def _calculate_relative_performance(self, driver_comparisons: Dict[str, Any], 
                                            metrics: List[str]) -> Dict[str, Any]:
        """Calculate relative performance between drivers."""
        relative_performance = {}
        
        for metric in metrics:
            metric_values = {}
            
            # Collect metric values for all drivers
            for driver_id, data in driver_comparisons.items():
                metric_data = data.get("metrics", {}).get(metric, {})
                if metric_data:
                    metric_values[driver_id] = metric_data.get("avg", 0)
            
            if metric_values:
                # Calculate rankings
                sorted_drivers = sorted(metric_values.items(), key=lambda x: x[1], reverse=True)
                
                relative_performance[metric] = {
                    "rankings": [{"driver_id": driver, "value": value, "rank": i+1} 
                               for i, (driver, value) in enumerate(sorted_drivers)],
                    "best_performer": sorted_drivers[0][0] if sorted_drivers else None,
                    "worst_performer": sorted_drivers[-1][0] if sorted_drivers else None
                }
        
        return relative_performance
    
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
                    "name": "get_driver_trips",
                    "description": "Get trips for a specific driver with filtering and aggregation",
                    "parameters": {
                        "driver_id": {"type": "string", "description": "Driver ID"},
                        "time_range": {"type": "object", "description": "Time range filter"},
                        "filters": {"type": "array", "description": "Additional filters"},
                        "aggregations": {"type": "array", "description": "Aggregation operations"},
                        "pagination": {"type": "object", "description": "Pagination options"}
                    }
                },
                {
                    "name": "get_trip_analytics",
                    "description": "Get comprehensive trip analytics",
                    "parameters": {
                        "driver_ids": {"type": "array", "description": "Optional driver IDs"},
                        "time_range": {"type": "object", "description": "Time range filter"},
                        "filters": {"type": "array", "description": "Additional filters"},
                        "group_by": {"type": "string", "description": "Group by field"}
                    }
                },
                {
                    "name": "get_trip_efficiency_metrics",
                    "description": "Get efficiency metrics for trips",
                    "parameters": {
                        "driver_ids": {"type": "array", "description": "Optional driver IDs"},
                        "time_range": {"type": "object", "description": "Time range filter"}
                    }
                },
                {
                    "name": "get_trip_patterns",
                    "description": "Identify patterns in trip data",
                    "parameters": {
                        "driver_ids": {"type": "array", "description": "Optional driver IDs"},
                        "time_range": {"type": "object", "description": "Time range filter"},
                        "pattern_type": {"type": "string", "description": "Type of pattern to identify"}
                    }
                },
                {
                    "name": "compare_trip_performance",
                    "description": "Compare trip performance between drivers",
                    "parameters": {
                        "driver_ids": {"type": "array", "description": "Driver IDs to compare"},
                        "time_range": {"type": "object", "description": "Time range filter"},
                        "metrics": {"type": "array", "description": "Metrics to compare"}
                    }
                }
            ]
        }
    
    async def execute_method(self, method_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool method."""
        if method_name == "get_driver_trips":
            return await self.get_driver_trips(
                parameters.get("driver_id"),
                parameters.get("time_range"),
                parameters.get("filters"),
                parameters.get("aggregations"),
                parameters.get("pagination")
            )
        elif method_name == "get_trip_analytics":
            return await self.get_trip_analytics(
                parameters.get("driver_ids"),
                parameters.get("time_range"),
                parameters.get("filters"),
                parameters.get("group_by")
            )
        elif method_name == "get_trip_efficiency_metrics":
            return await self.get_trip_efficiency_metrics(
                parameters.get("driver_ids"),
                parameters.get("time_range")
            )
        elif method_name == "get_trip_patterns":
            return await self.get_trip_patterns(
                parameters.get("driver_ids"),
                parameters.get("time_range"),
                parameters.get("pattern_type", "temporal")
            )
        elif method_name == "compare_trip_performance":
            return await self.compare_trip_performance(
                parameters.get("driver_ids", []),
                parameters.get("time_range"),
                parameters.get("metrics")
            )
        else:
            return {
                "success": False,
                "error": f"Unknown method: {method_name}",
                "data": None
            }