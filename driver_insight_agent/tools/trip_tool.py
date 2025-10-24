"""
Trip Tool - Trip analytics with filtering and time range support.
Retrieves and analyzes trip data for drivers.
"""
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import random


class TripTool:
    """Tool for trip analytics and data retrieval."""
    
    def __init__(self):
        self.name = "trip_tool"
        self.description = "Retrieves trip data with filtering and time range support"
        self.version = "1.0.0"
        
        # Mock trip database
        self._trip_db = self._initialize_mock_data()
    
    def _initialize_mock_data(self) -> List[Dict[str, Any]]:
        """Initialize mock trip data for demonstration."""
        trips = []
        driver_ids = ["D001", "D002", "D003", "D004", "D005"]
        
        # Generate mock trips for the last 90 days
        base_date = datetime.now() - timedelta(days=90)
        
        trip_id = 1
        for driver_id in driver_ids:
            # Each driver has 20-40 trips
            num_trips = random.randint(20, 40)
            
            for _ in range(num_trips):
                trip_date = base_date + timedelta(days=random.randint(0, 90))
                
                trips.append({
                    "trip_id": f"T{trip_id:05d}",
                    "driver_id": driver_id,
                    "start_time": trip_date.isoformat(),
                    "end_time": (trip_date + timedelta(minutes=random.randint(10, 120))).isoformat(),
                    "distance": round(random.uniform(5, 150), 2),  # miles
                    "duration": random.randint(10, 120),  # minutes
                    "start_location": f"Location_{random.randint(1, 20)}",
                    "end_location": f"Location_{random.randint(1, 20)}",
                    "fuel_consumption": round(random.uniform(0.5, 8), 2),  # gallons
                    "avg_speed": round(random.uniform(20, 65), 2),  # mph
                    "max_speed": round(random.uniform(50, 85), 2),  # mph
                    "status": random.choice(["completed", "completed", "completed", "cancelled"]),
                })
                
                trip_id += 1
        
        return trips
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute trip analytics.
        
        Args:
            parameters: Dictionary containing:
                - driver_ids: List of driver IDs
                - start_date: Start date (ISO 8601) (optional)
                - end_date: End date (ISO 8601) (optional)
                - filters: Additional filters (optional)
                - limit: Maximum results (optional)
                - offset: Result offset (optional)
                
        Returns:
            Dictionary with execution results
        """
        start_time = time.time()
        
        try:
            trips = await self._get_trips(parameters)
            
            # Apply filters
            if 'filters' in parameters and parameters['filters']:
                from utils.filter_engine import FilterEngine
                filter_engine = FilterEngine()
                trips = filter_engine.apply_filters(trips, parameters['filters'])
            
            # Apply pagination
            offset = parameters.get('offset', 0)
            limit = parameters.get('limit')
            
            total_count = len(trips)
            
            if limit:
                trips = trips[offset:offset + limit]
            else:
                trips = trips[offset:]
            
            # Calculate summary statistics
            summary = self._calculate_summary(trips)
            
            execution_time = (time.time() - start_time) * 1000
            
            return {
                "success": True,
                "data": trips,
                "summary": summary,
                "count": len(trips),
                "total_count": total_count,
                "execution_time_ms": execution_time,
                "error": None
            }
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return {
                "success": False,
                "data": None,
                "summary": None,
                "count": 0,
                "total_count": 0,
                "execution_time_ms": execution_time,
                "error": str(e)
            }
    
    async def _get_trips(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get trips based on parameters."""
        driver_ids = parameters.get('driver_ids', [])
        start_date = parameters.get('start_date')
        end_date = parameters.get('end_date')
        
        # Filter by driver IDs
        trips = [trip for trip in self._trip_db if trip['driver_id'] in driver_ids]
        
        # Filter by date range
        if start_date or end_date:
            from utils.filter_engine import FilterEngine
            filter_engine = FilterEngine()
            
            if start_date and end_date:
                trips = filter_engine.filter_by_time_range(
                    trips,
                    'start_time',
                    start_date,
                    end_date
                )
        
        return trips
    
    def _calculate_summary(self, trips: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics for trips."""
        if not trips:
            return {
                "total_trips": 0,
                "total_distance": 0,
                "total_duration": 0,
                "avg_distance": 0,
                "avg_duration": 0,
                "total_fuel": 0
            }
        
        total_distance = sum(t['distance'] for t in trips)
        total_duration = sum(t['duration'] for t in trips)
        total_fuel = sum(t['fuel_consumption'] for t in trips)
        
        return {
            "total_trips": len(trips),
            "total_distance": round(total_distance, 2),
            "total_duration": round(total_duration, 2),
            "avg_distance": round(total_distance / len(trips), 2),
            "avg_duration": round(total_duration / len(trips), 2),
            "total_fuel": round(total_fuel, 2),
            "avg_fuel_per_trip": round(total_fuel / len(trips), 2)
        }
    
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
                "filters": {"type": "list", "required": False},
                "limit": {"type": "integer", "required": False},
                "offset": {"type": "integer", "required": False}
            },
            "output_schema": {
                "success": "boolean",
                "data": "list[dict]",
                "summary": "dict",
                "count": "integer",
                "total_count": "integer",
                "execution_time_ms": "float"
            }
        }
