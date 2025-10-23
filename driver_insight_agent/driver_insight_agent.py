"""Main Driver Insight Agent orchestrator."""

import asyncio
from typing import Any, Dict, List, Optional, Union

from .cache import get_cache_manager
from .config import get_config
from .mcp_tools import get_tool_orchestrator, ToolHandlerError
from .services import get_api_client, get_logger, get_validator, APIError, ValidationError


class DriverInsightAgentError(Exception):
    """Custom exception for Driver Insight Agent errors."""
    pass


class DriverInsightAgent:
    """Main orchestrator for driver data operations."""
    
    def __init__(self):
        """Initialize the Driver Insight Agent."""
        self.logger = get_logger()
        self.validator = get_validator()
        self.cache_manager = get_cache_manager()
        self.api_client = get_api_client()
        self.tool_orchestrator = get_tool_orchestrator()
        self._initialized = False
    
    async def initialize(self):
        """Initialize the agent and its dependencies."""
        if self._initialized:
            return
        
        try:
            # Initialize API client
            await self.api_client._ensure_client()
            
            # Log initialization
            self.logger.info("Driver Insight Agent initialized successfully")
            self._initialized = True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Driver Insight Agent: {str(e)}")
            raise DriverInsightAgentError(f"Initialization failed: {str(e)}")
    
    async def fetch_driver(self, driver_id: str, use_cache: bool = True, use_mcp_tools: bool = True) -> Dict[str, Any]:
        """Fetch single driver data with validation and caching.
        
        Args:
            driver_id: Driver ID to fetch
            use_cache: Whether to use caching
            use_mcp_tools: Whether to use MCP tools for enhanced processing
            
        Returns:
            Driver data with metadata
            
        Raises:
            DriverInsightAgentError: If fetch operation fails
        """
        await self.initialize()
        
        if not driver_id or not isinstance(driver_id, str):
            raise DriverInsightAgentError("Invalid driver_id provided")
        
        driver_id = driver_id.strip()
        if not driver_id:
            raise DriverInsightAgentError("Driver ID cannot be empty")
        
        self.logger.info(f"Fetching driver: {driver_id}", use_cache=use_cache, use_mcp_tools=use_mcp_tools)
        
        try:
            if use_mcp_tools:
                # Use MCP tools for enhanced processing
                result = await self.tool_orchestrator.fetch_and_validate_driver(driver_id, use_cache)
                
                return {
                    "driver_id": driver_id,
                    "data": result["driver_data"],
                    "validation": result["validation"],
                    "metadata": {
                        "source": result["source"],
                        "cached": result["cached"],
                        "processed_with_mcp": True,
                        "timestamp": asyncio.get_event_loop().time()
                    }
                }
            else:
                # Direct API approach with local validation and caching
                cache_key = self.cache_manager.generate_cache_key("driver", driver_id)
                
                # Try cache first
                if use_cache:
                    cached_data = await self.cache_manager.get(cache_key)
                    if cached_data:
                        self.logger.info(f"Retrieved driver {driver_id} from local cache")
                        return {
                            **cached_data,
                            "metadata": {
                                **cached_data.get("metadata", {}),
                                "cached": True,
                                "processed_with_mcp": False
                            }
                        }
                
                # Fetch from API
                async with self.api_client as client:
                    driver_data = await client.fetch_driver(driver_id)
                
                # Validate data
                is_valid, errors = self.validator.validate_driver_data(driver_data)
                
                # Sanitize data
                sanitized_data = self.validator.sanitize_driver_data(driver_data)
                
                result = {
                    "driver_id": driver_id,
                    "data": sanitized_data,
                    "validation": {
                        "is_valid": is_valid,
                        "errors": errors,
                        "warnings": []
                    },
                    "metadata": {
                        "source": "api",
                        "cached": False,
                        "processed_with_mcp": False,
                        "timestamp": asyncio.get_event_loop().time()
                    }
                }
                
                # Cache if valid
                if use_cache and is_valid:
                    await self.cache_manager.set(cache_key, result)
                
                return result
                
        except APIError as e:
            self.logger.error(f"API error fetching driver {driver_id}: {str(e)}")
            raise DriverInsightAgentError(f"Failed to fetch driver {driver_id}: {str(e)}")
        
        except ToolHandlerError as e:
            self.logger.error(f"MCP tool error fetching driver {driver_id}: {str(e)}")
            # Fallback to direct API if MCP tools fail
            if use_mcp_tools:
                self.logger.info(f"Falling back to direct API for driver {driver_id}")
                return await self.fetch_driver(driver_id, use_cache, use_mcp_tools=False)
            else:
                raise DriverInsightAgentError(f"Failed to fetch driver {driver_id}: {str(e)}")
        
        except Exception as e:
            self.logger.error(f"Unexpected error fetching driver {driver_id}: {str(e)}")
            raise DriverInsightAgentError(f"Unexpected error fetching driver {driver_id}: {str(e)}")
    
    async def fetch_drivers_batch(self, driver_ids: List[str], use_cache: bool = True, use_mcp_tools: bool = True) -> List[Dict[str, Any]]:
        """Fetch multiple drivers in batch with validation and caching.
        
        Args:
            driver_ids: List of driver IDs to fetch
            use_cache: Whether to use caching
            use_mcp_tools: Whether to use MCP tools for enhanced processing
            
        Returns:
            List of driver data with metadata
            
        Raises:
            DriverInsightAgentError: If batch fetch operation fails
        """
        await self.initialize()
        
        # Validate input
        is_valid, errors = self.validator.validate_driver_ids(driver_ids)
        if not is_valid:
            raise DriverInsightAgentError(f"Invalid driver IDs: {', '.join(errors)}")
        
        # Remove duplicates while preserving order
        unique_ids = list(dict.fromkeys(driver_ids))
        
        self.logger.info(f"Fetching batch of {len(unique_ids)} drivers", use_cache=use_cache, use_mcp_tools=use_mcp_tools)
        
        try:
            if use_mcp_tools:
                # Use MCP tools for enhanced processing
                results = await self.tool_orchestrator.fetch_and_validate_drivers_batch(unique_ids, use_cache)
                
                return [
                    {
                        "driver_id": result["driver_data"].get("driver_id", "unknown"),
                        "data": result["driver_data"],
                        "validation": result["validation"],
                        "metadata": {
                            "source": result["source"],
                            "cached": result["cached"],
                            "processed_with_mcp": True,
                            "timestamp": asyncio.get_event_loop().time()
                        }
                    }
                    for result in results
                ]
            else:
                # Direct API approach
                results = []
                cached_count = 0
                
                # Check cache for each driver if enabled
                uncached_ids = []
                if use_cache:
                    for driver_id in unique_ids:
                        cache_key = self.cache_manager.generate_cache_key("driver", driver_id)
                        cached_data = await self.cache_manager.get(cache_key)
                        if cached_data:
                            results.append({
                                **cached_data,
                                "metadata": {
                                    **cached_data.get("metadata", {}),
                                    "cached": True,
                                    "processed_with_mcp": False
                                }
                            })
                            cached_count += 1
                        else:
                            uncached_ids.append(driver_id)
                else:
                    uncached_ids = unique_ids
                
                # Fetch uncached drivers
                if uncached_ids:
                    async with self.api_client as client:
                        drivers_data = await client.fetch_drivers_batch(uncached_ids)
                    
                    # Validate batch
                    all_valid, errors_by_index = self.validator.validate_driver_batch(drivers_data)
                    
                    # Process each driver
                    for i, driver_data in enumerate(drivers_data):
                        driver_id = driver_data.get("driver_id", uncached_ids[i] if i < len(uncached_ids) else f"unknown_{i}")
                        
                        # Get validation results for this driver
                        is_valid = i not in errors_by_index
                        errors = errors_by_index.get(i, [])
                        
                        # Sanitize data
                        sanitized_data = self.validator.sanitize_driver_data(driver_data)
                        
                        result = {
                            "driver_id": driver_id,
                            "data": sanitized_data,
                            "validation": {
                                "is_valid": is_valid,
                                "errors": errors,
                                "warnings": []
                            },
                            "metadata": {
                                "source": "api",
                                "cached": False,
                                "processed_with_mcp": False,
                                "timestamp": asyncio.get_event_loop().time()
                            }
                        }
                        
                        results.append(result)
                        
                        # Cache if valid
                        if use_cache and is_valid:
                            cache_key = self.cache_manager.generate_cache_key("driver", driver_id)
                            await self.cache_manager.set(cache_key, result)
                
                self.logger.info(f"Batch fetch completed: {len(results)} drivers ({cached_count} from cache)")
                return results
                
        except APIError as e:
            self.logger.error(f"API error in batch fetch: {str(e)}")
            raise DriverInsightAgentError(f"Failed to fetch driver batch: {str(e)}")
        
        except ToolHandlerError as e:
            self.logger.error(f"MCP tool error in batch fetch: {str(e)}")
            # Fallback to direct API if MCP tools fail
            if use_mcp_tools:
                self.logger.info("Falling back to direct API for batch fetch")
                return await self.fetch_drivers_batch(driver_ids, use_cache, use_mcp_tools=False)
            else:
                raise DriverInsightAgentError(f"Failed to fetch driver batch: {str(e)}")
        
        except Exception as e:
            self.logger.error(f"Unexpected error in batch fetch: {str(e)}")
            raise DriverInsightAgentError(f"Unexpected error in batch fetch: {str(e)}")
    
    async def get_driver_summary(self, driver_ids: List[str]) -> Dict[str, Any]:
        """Get summary of multiple drivers.
        
        Args:
            driver_ids: List of driver IDs to summarize
            
        Returns:
            Summary data
            
        Raises:
            DriverInsightAgentError: If summary generation fails
        """
        await self.initialize()
        
        try:
            # Use MCP tools for summary if available
            summary = await self.tool_orchestrator.get_drivers_summary(driver_ids)
            return summary
            
        except ToolHandlerError as e:
            self.logger.warning(f"MCP summary failed, generating basic summary: {str(e)}")
            
            # Fallback to basic summary
            try:
                drivers = await self.fetch_drivers_batch(driver_ids, use_mcp_tools=False)
                valid_drivers = [d for d in drivers if d["validation"]["is_valid"]]
                
                # Basic statistics
                total_rating = sum(d["data"].get("rating", 0) for d in valid_drivers if d["data"].get("rating"))
                avg_rating = total_rating / len(valid_drivers) if valid_drivers else 0
                
                return {
                    "summary": {
                        "total_drivers": len(driver_ids),
                        "valid_drivers": len(valid_drivers),
                        "invalid_drivers": len(drivers) - len(valid_drivers),
                        "average_rating": round(avg_rating, 2),
                        "generated_by": "fallback_method"
                    },
                    "total_requested": len(driver_ids),
                    "valid_drivers": len(valid_drivers),
                    "invalid_drivers": len(drivers) - len(valid_drivers)
                }
                
            except Exception as fallback_error:
                raise DriverInsightAgentError(f"Failed to generate summary: {str(fallback_error)}")
        
        except Exception as e:
            self.logger.error(f"Unexpected error generating summary: {str(e)}")
            raise DriverInsightAgentError(f"Failed to generate summary: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check.
        
        Returns:
            Health check results for all components
        """
        health_results = {
            "agent": {"status": "healthy", "timestamp": asyncio.get_event_loop().time()},
            "api": {"status": "unknown"},
            "cache": {"status": "unknown"},
            "mcp_tools": {"status": "unknown"}
        }
        
        try:
            await self.initialize()
            
            # Check API health
            try:
                async with self.api_client as client:
                    api_health = await client.health_check()
                health_results["api"] = api_health
            except Exception as e:
                health_results["api"] = {"status": "unhealthy", "error": str(e)}
            
            # Check cache health
            try:
                cache_stats = await self.cache_manager.get_stats()
                health_results["cache"] = {"status": "healthy", "stats": cache_stats}
            except Exception as e:
                health_results["cache"] = {"status": "unhealthy", "error": str(e)}
            
            # Check MCP tools health
            try:
                mcp_health = await self.tool_orchestrator.mcp_invoker.health_check()
                health_results["mcp_tools"] = mcp_health
            except Exception as e:
                health_results["mcp_tools"] = {"status": "unhealthy", "error": str(e)}
            
            # Overall status
            all_healthy = all(
                component.get("status") == "healthy" 
                for component in health_results.values()
            )
            health_results["overall"] = {
                "status": "healthy" if all_healthy else "degraded",
                "timestamp": asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            health_results["agent"] = {"status": "unhealthy", "error": str(e)}
            health_results["overall"] = {"status": "unhealthy", "error": str(e)}
        
        return health_results
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Cache statistics
        """
        try:
            return await self.cache_manager.get_stats()
        except Exception as e:
            self.logger.error(f"Failed to get cache stats: {str(e)}")
            return {"error": str(e)}
    
    async def clear_cache(self) -> bool:
        """Clear all cached data.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            success = await self.cache_manager.clear()
            if success:
                self.logger.info("Cache cleared successfully")
            else:
                self.logger.warning("Failed to clear cache")
            return success
        except Exception as e:
            self.logger.error(f"Error clearing cache: {str(e)}")
            return False
    
    async def close(self):
        """Close the agent and clean up resources."""
        try:
            await self.api_client.close()
            await self.cache_manager.close()
            await self.tool_orchestrator.mcp_invoker.close()
            self.logger.info("Driver Insight Agent closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing Driver Insight Agent: {str(e)}")


# Global agent instance
_driver_insight_agent: Optional[DriverInsightAgent] = None


def get_driver_insight_agent() -> DriverInsightAgent:
    """Get the global Driver Insight Agent instance.
    
    Returns:
        DriverInsightAgent: The agent instance
    """
    global _driver_insight_agent
    if _driver_insight_agent is None:
        _driver_insight_agent = DriverInsightAgent()
    return _driver_insight_agent