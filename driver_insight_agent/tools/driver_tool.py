"""Driver resolution tool for ID, name, email, and phone lookups."""

from typing import Dict, List, Any, Optional, Union
import asyncio
import re
from dataclasses import dataclass
from datetime import datetime

from ..utils.validation import DriverIdentifier, ValidationError
from ..utils.filter_engine import FilterEngine
from ..cache.cache_manager import get_cache_manager


@dataclass
class DriverProfile:
    """Complete driver profile information."""
    driver_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    license_number: Optional[str] = None
    status: str = "active"
    created_date: Optional[datetime] = None
    last_active: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class DriverDataSource:
    """Mock data source for driver information."""
    
    def __init__(self):
        """Initialize with sample driver data."""
        self.drivers = [
            DriverProfile(
                driver_id="DRV001",
                name="John Smith",
                email="john.smith@example.com",
                phone="+1-555-0101",
                license_number="DL123456789",
                status="active",
                created_date=datetime(2023, 1, 15),
                last_active=datetime(2024, 10, 20),
                metadata={"region": "north", "vehicle_type": "sedan", "experience_years": 5}
            ),
            DriverProfile(
                driver_id="DRV002",
                name="Sarah Johnson",
                email="sarah.johnson@example.com",
                phone="+1-555-0102",
                license_number="DL987654321",
                status="active",
                created_date=datetime(2023, 3, 22),
                last_active=datetime(2024, 10, 23),
                metadata={"region": "south", "vehicle_type": "suv", "experience_years": 3}
            ),
            DriverProfile(
                driver_id="DRV003",
                name="Michael Brown",
                email="m.brown@example.com",
                phone="+1-555-0103",
                license_number="DL456789123",
                status="inactive",
                created_date=datetime(2022, 11, 10),
                last_active=datetime(2024, 9, 15),
                metadata={"region": "east", "vehicle_type": "truck", "experience_years": 8}
            ),
            DriverProfile(
                driver_id="DRV004",
                name="Emily Davis",
                email="emily.davis@example.com",
                phone="+1-555-0104",
                license_number="DL789123456",
                status="active",
                created_date=datetime(2023, 6, 5),
                last_active=datetime(2024, 10, 24),
                metadata={"region": "west", "vehicle_type": "sedan", "experience_years": 2}
            ),
            DriverProfile(
                driver_id="DRV005",
                name="Robert Wilson",
                email="robert.wilson@example.com",
                phone="+1-555-0105",
                license_number="DL321654987",
                status="active",
                created_date=datetime(2023, 2, 18),
                last_active=datetime(2024, 10, 22),
                metadata={"region": "north", "vehicle_type": "van", "experience_years": 6}
            )
        ]
    
    async def get_all_drivers(self) -> List[DriverProfile]:
        """Get all drivers."""
        return self.drivers.copy()
    
    async def get_driver_by_id(self, driver_id: str) -> Optional[DriverProfile]:
        """Get driver by ID."""
        for driver in self.drivers:
            if driver.driver_id == driver_id:
                return driver
        return None
    
    async def search_drivers(self, query: str, field: str = "name") -> List[DriverProfile]:
        """Search drivers by field."""
        results = []
        query_lower = query.lower()
        
        for driver in self.drivers:
            if field == "name" and query_lower in driver.name.lower():
                results.append(driver)
            elif field == "email" and driver.email and query_lower in driver.email.lower():
                results.append(driver)
            elif field == "phone" and driver.phone and query in driver.phone:
                results.append(driver)
            elif field == "license" and driver.license_number and query_lower in driver.license_number.lower():
                results.append(driver)
        
        return results


class DriverTool:
    """Tool for driver resolution and management."""
    
    def __init__(self):
        """Initialize driver tool."""
        self.data_source = DriverDataSource()
        self.filter_engine = FilterEngine()
        self.cache_manager = get_cache_manager()
        
        # Tool metadata
        self.name = "driver_tool"
        self.description = "Resolve driver information by ID, name, email, or phone"
        self.version = "1.0.0"
    
    async def resolve_drivers(self, identifiers: List[Dict[str, Any]], 
                            options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Resolve multiple drivers from identifiers."""
        try:
            # Validate identifiers
            validated_identifiers = []
            for identifier in identifiers:
                try:
                    validated_identifiers.append(DriverIdentifier(**identifier))
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Invalid driver identifier: {str(e)}",
                        "data": None
                    }
            
            # Check cache first
            cache_key = self._generate_cache_key("resolve_drivers", identifiers, options)
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                return cached_result
            
            # Resolve drivers
            resolved_drivers = []
            unresolved_identifiers = []
            
            for identifier in validated_identifiers:
                driver = await self._resolve_single_driver(identifier)
                if driver:
                    resolved_drivers.append(self._driver_to_dict(driver))
                else:
                    unresolved_identifiers.append(identifier.dict(exclude_none=True))
            
            # Apply filters if specified
            if options and options.get('filters'):
                resolved_drivers = self.filter_engine.apply_filters(
                    resolved_drivers, 
                    options['filters']
                )
            
            result = {
                "success": True,
                "data": {
                    "resolved_drivers": resolved_drivers,
                    "unresolved_identifiers": unresolved_identifiers,
                    "resolution_rate": len(resolved_drivers) / len(identifiers) if identifiers else 0,
                    "total_requested": len(identifiers),
                    "total_resolved": len(resolved_drivers)
                },
                "metadata": {
                    "tool": self.name,
                    "version": self.version,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Cache result
            await self.cache_manager.set(cache_key, result, ttl=3600, tags=['driver_resolution'])
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Driver resolution failed: {str(e)}",
                "data": None
            }
    
    async def get_driver_details(self, driver_id: str, 
                               include_metadata: bool = True) -> Dict[str, Any]:
        """Get detailed information for a specific driver."""
        try:
            # Check cache first
            cache_key = self._generate_cache_key("driver_details", driver_id, include_metadata)
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                return cached_result
            
            driver = await self.data_source.get_driver_by_id(driver_id)
            
            if not driver:
                return {
                    "success": False,
                    "error": f"Driver not found: {driver_id}",
                    "data": None
                }
            
            driver_data = self._driver_to_dict(driver)
            
            if not include_metadata:
                driver_data.pop('metadata', None)
            
            result = {
                "success": True,
                "data": driver_data,
                "metadata": {
                    "tool": self.name,
                    "version": self.version,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Cache result
            await self.cache_manager.set(cache_key, result, ttl=3600, 
                                       tags=['driver_details', f'driver_{driver_id}'])
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get driver details: {str(e)}",
                "data": None
            }
    
    async def search_drivers(self, query: str, search_fields: Optional[List[str]] = None,
                           filters: Optional[List[Dict[str, Any]]] = None,
                           limit: int = 50) -> Dict[str, Any]:
        """Search for drivers using various criteria."""
        try:
            search_fields = search_fields or ["name", "email", "phone"]
            
            # Check cache first
            cache_key = self._generate_cache_key("search_drivers", query, search_fields, filters, limit)
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                return cached_result
            
            # Perform search across specified fields
            all_results = []
            seen_driver_ids = set()
            
            for field in search_fields:
                field_results = await self.data_source.search_drivers(query, field)
                
                for driver in field_results:
                    if driver.driver_id not in seen_driver_ids:
                        all_results.append(self._driver_to_dict(driver))
                        seen_driver_ids.add(driver.driver_id)
            
            # Apply additional filters
            if filters:
                all_results = self.filter_engine.apply_filters(all_results, filters)
            
            # Apply limit
            limited_results = all_results[:limit]
            
            result = {
                "success": True,
                "data": {
                    "drivers": limited_results,
                    "total_found": len(all_results),
                    "total_returned": len(limited_results),
                    "search_query": query,
                    "search_fields": search_fields,
                    "truncated": len(all_results) > limit
                },
                "metadata": {
                    "tool": self.name,
                    "version": self.version,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Cache result
            await self.cache_manager.set(cache_key, result, ttl=1800, tags=['driver_search'])
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Driver search failed: {str(e)}",
                "data": None
            }
    
    async def get_driver_statistics(self, filters: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Get statistics about drivers in the system."""
        try:
            # Check cache first
            cache_key = self._generate_cache_key("driver_statistics", filters)
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                return cached_result
            
            all_drivers = await self.data_source.get_all_drivers()
            driver_data = [self._driver_to_dict(driver) for driver in all_drivers]
            
            # Apply filters if specified
            if filters:
                driver_data = self.filter_engine.apply_filters(driver_data, filters)
            
            # Calculate statistics
            total_drivers = len(driver_data)
            active_drivers = len([d for d in driver_data if d.get('status') == 'active'])
            inactive_drivers = total_drivers - active_drivers
            
            # Region distribution
            regions = {}
            vehicle_types = {}
            experience_distribution = {"0-2": 0, "3-5": 0, "6-10": 0, "10+": 0}
            
            for driver in driver_data:
                metadata = driver.get('metadata', {})
                
                # Region stats
                region = metadata.get('region', 'unknown')
                regions[region] = regions.get(region, 0) + 1
                
                # Vehicle type stats
                vehicle_type = metadata.get('vehicle_type', 'unknown')
                vehicle_types[vehicle_type] = vehicle_types.get(vehicle_type, 0) + 1
                
                # Experience distribution
                experience = metadata.get('experience_years', 0)
                if experience <= 2:
                    experience_distribution["0-2"] += 1
                elif experience <= 5:
                    experience_distribution["3-5"] += 1
                elif experience <= 10:
                    experience_distribution["6-10"] += 1
                else:
                    experience_distribution["10+"] += 1
            
            result = {
                "success": True,
                "data": {
                    "overview": {
                        "total_drivers": total_drivers,
                        "active_drivers": active_drivers,
                        "inactive_drivers": inactive_drivers,
                        "activity_rate": active_drivers / total_drivers if total_drivers > 0 else 0
                    },
                    "distributions": {
                        "by_region": regions,
                        "by_vehicle_type": vehicle_types,
                        "by_experience": experience_distribution
                    },
                    "filters_applied": filters is not None,
                    "filter_count": len(filters) if filters else 0
                },
                "metadata": {
                    "tool": self.name,
                    "version": self.version,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Cache result
            await self.cache_manager.set(cache_key, result, ttl=3600, tags=['driver_statistics'])
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get driver statistics: {str(e)}",
                "data": None
            }
    
    async def validate_driver_identifiers(self, identifiers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate driver identifiers without resolving them."""
        try:
            validation_results = []
            
            for i, identifier in enumerate(identifiers):
                try:
                    validated = DriverIdentifier(**identifier)
                    validation_results.append({
                        "index": i,
                        "identifier": identifier,
                        "valid": True,
                        "errors": []
                    })
                except Exception as e:
                    validation_results.append({
                        "index": i,
                        "identifier": identifier,
                        "valid": False,
                        "errors": [str(e)]
                    })
            
            valid_count = sum(1 for result in validation_results if result["valid"])
            
            return {
                "success": True,
                "data": {
                    "validation_results": validation_results,
                    "total_identifiers": len(identifiers),
                    "valid_identifiers": valid_count,
                    "invalid_identifiers": len(identifiers) - valid_count,
                    "validation_rate": valid_count / len(identifiers) if identifiers else 0
                },
                "metadata": {
                    "tool": self.name,
                    "version": self.version,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Validation failed: {str(e)}",
                "data": None
            }
    
    async def _resolve_single_driver(self, identifier: DriverIdentifier) -> Optional[DriverProfile]:
        """Resolve a single driver from identifier."""
        # Try by driver_id first (most specific)
        if identifier.driver_id:
            driver = await self.data_source.get_driver_by_id(identifier.driver_id)
            if driver:
                return driver
        
        # Try by email
        if identifier.email:
            results = await self.data_source.search_drivers(identifier.email, "email")
            if results:
                return results[0]  # Return first exact match
        
        # Try by phone
        if identifier.phone:
            results = await self.data_source.search_drivers(identifier.phone, "phone")
            if results:
                return results[0]
        
        # Try by name (less reliable)
        if identifier.name:
            results = await self.data_source.search_drivers(identifier.name, "name")
            # For name matching, we need exact match to avoid ambiguity
            exact_matches = [r for r in results if r.name.lower() == identifier.name.lower()]
            if len(exact_matches) == 1:
                return exact_matches[0]
        
        return None
    
    def _driver_to_dict(self, driver: DriverProfile) -> Dict[str, Any]:
        """Convert driver profile to dictionary."""
        return {
            "driver_id": driver.driver_id,
            "name": driver.name,
            "email": driver.email,
            "phone": driver.phone,
            "license_number": driver.license_number,
            "status": driver.status,
            "created_date": driver.created_date.isoformat() if driver.created_date else None,
            "last_active": driver.last_active.isoformat() if driver.last_active else None,
            "metadata": driver.metadata or {}
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
                    "name": "resolve_drivers",
                    "description": "Resolve multiple drivers from identifiers",
                    "parameters": {
                        "identifiers": {"type": "array", "description": "List of driver identifiers"},
                        "options": {"type": "object", "description": "Additional options"}
                    }
                },
                {
                    "name": "get_driver_details",
                    "description": "Get detailed information for a specific driver",
                    "parameters": {
                        "driver_id": {"type": "string", "description": "Driver ID"},
                        "include_metadata": {"type": "boolean", "description": "Include metadata"}
                    }
                },
                {
                    "name": "search_drivers",
                    "description": "Search for drivers using various criteria",
                    "parameters": {
                        "query": {"type": "string", "description": "Search query"},
                        "search_fields": {"type": "array", "description": "Fields to search"},
                        "filters": {"type": "array", "description": "Additional filters"},
                        "limit": {"type": "integer", "description": "Result limit"}
                    }
                },
                {
                    "name": "get_driver_statistics",
                    "description": "Get statistics about drivers in the system",
                    "parameters": {
                        "filters": {"type": "array", "description": "Optional filters"}
                    }
                },
                {
                    "name": "validate_driver_identifiers",
                    "description": "Validate driver identifiers without resolving them",
                    "parameters": {
                        "identifiers": {"type": "array", "description": "List of driver identifiers"}
                    }
                }
            ]
        }
    
    async def execute_method(self, method_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool method."""
        if method_name == "resolve_drivers":
            return await self.resolve_drivers(
                parameters.get("identifiers", []),
                parameters.get("options")
            )
        elif method_name == "get_driver_details":
            return await self.get_driver_details(
                parameters.get("driver_id"),
                parameters.get("include_metadata", True)
            )
        elif method_name == "search_drivers":
            return await self.search_drivers(
                parameters.get("query"),
                parameters.get("search_fields"),
                parameters.get("filters"),
                parameters.get("limit", 50)
            )
        elif method_name == "get_driver_statistics":
            return await self.get_driver_statistics(
                parameters.get("filters")
            )
        elif method_name == "validate_driver_identifiers":
            return await self.validate_driver_identifiers(
                parameters.get("identifiers", [])
            )
        else:
            return {
                "success": False,
                "error": f"Unknown method: {method_name}",
                "data": None
            }