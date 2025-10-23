"""
Driver Insight Agent - Main orchestrator for driver data management.
Coordinates API fetching, validation, caching, and MCP tool invocation.
"""

from typing import Any, Dict, List, Optional

from cache.cache_manager import CacheManager
from mcp_tools.mcp_invoker import MCPInvoker, MCPInvokerError
from services.api_client import APIClient, APIError
from services.validator import ValidationError, Validator
from utils.logger import get_logger

logger = get_logger(__name__)


class DriverInsightAgent:
    """
    Main orchestrator for driver data operations.
    Integrates API client, validator, cache manager, and MCP tool invoker.
    """

    def __init__(
        self,
        api_client: Optional[APIClient] = None,
        validator: Optional[Validator] = None,
        cache_manager: Optional[CacheManager] = None,
        mcp_invoker: Optional[MCPInvoker] = None,
    ):
        """
        Initialize Driver Insight Agent.

        Args:
            api_client: API client instance.
            validator: Validator instance.
            cache_manager: Cache manager instance.
            mcp_invoker: MCP invoker instance.
        """
        self.api_client = api_client or APIClient()
        self.validator = validator or Validator()
        self.cache_manager = cache_manager or CacheManager()
        self.mcp_invoker = mcp_invoker or MCPInvoker()

        logger.info("Driver Insight Agent initialized")

    async def close(self):
        """Close all client connections."""
        await self.api_client.close()
        await self.mcp_invoker.close()
        logger.info("Driver Insight Agent closed")

    async def get_driver(
        self,
        driver_id: str,
        use_cache: bool = True,
        use_mcp: bool = False,
    ) -> Dict[str, Any]:
        """
        Get driver information by ID.

        Args:
            driver_id: Driver ID.
            use_cache: Whether to use cache.
            use_mcp: Whether to use MCP tools for fetching.

        Returns:
            Driver information dictionary.

        Raises:
            APIError: If API request fails.
            ValidationError: If validation fails in strict mode.
        """
        logger.info(f"Getting driver information", extra={
            "driver_id": driver_id,
            "use_cache": use_cache,
            "use_mcp": use_mcp,
        })

        # Check cache first
        if use_cache:
            cache_key = self.cache_manager.generate_key("driver", driver_id)
            cached_data = await self.cache_manager.get(cache_key)

            if cached_data:
                logger.info(f"Returning cached driver data", extra={"driver_id": driver_id})
                return cached_data

        # Fetch from API or MCP
        try:
            if use_mcp:
                driver_data = await self._fetch_driver_via_mcp(driver_id)
            else:
                driver_data = await self.api_client.fetch_driver(driver_id)

            # Validate data
            if not self.validator.validate_driver(driver_data):
                logger.warning(f"Driver data validation failed", extra={
                    "driver_id": driver_id,
                })
                # Continue with invalid data but mark it
                driver_data["_validation_failed"] = True

            # Cache the result
            if use_cache:
                cache_key = self.cache_manager.generate_key("driver", driver_id)
                await self.cache_manager.set(cache_key, driver_data)

            return driver_data

        except APIError as e:
            logger.error(f"Failed to fetch driver", extra={
                "driver_id": driver_id,
                "error": str(e),
            })
            raise

        except Exception as e:
            logger.error(f"Unexpected error fetching driver", extra={
                "driver_id": driver_id,
                "error": str(e),
            }, exc_info=True)
            raise

    async def get_drivers_batch(
        self,
        driver_ids: List[str],
        use_cache: bool = True,
        use_mcp: bool = False,
    ) -> Dict[str, Any]:
        """
        Get multiple drivers in batch.

        Args:
            driver_ids: List of driver IDs.
            use_cache: Whether to use cache.
            use_mcp: Whether to use MCP tools.

        Returns:
            Dictionary containing successful and failed driver fetches.
        """
        logger.info(f"Getting batch driver information", extra={
            "count": len(driver_ids),
            "use_cache": use_cache,
            "use_mcp": use_mcp,
        })

        drivers = []
        errors = []

        for driver_id in driver_ids:
            try:
                driver_data = await self.get_driver(
                    driver_id=driver_id,
                    use_cache=use_cache,
                    use_mcp=use_mcp,
                )
                drivers.append(driver_data)

            except Exception as e:
                logger.error(f"Failed to get driver in batch", extra={
                    "driver_id": driver_id,
                    "error": str(e),
                })
                errors.append({
                    "driver_id": driver_id,
                    "error": str(e),
                })

        # Validate batch
        validation_result = self.validator.validate_drivers(drivers)

        result = {
            "total_requested": len(driver_ids),
            "successful": len(drivers),
            "failed": len(errors),
            "drivers": drivers,
            "errors": errors,
            "validation": validation_result,
        }

        logger.info(f"Batch driver fetch completed", extra={
            "total_requested": result["total_requested"],
            "successful": result["successful"],
            "failed": result["failed"],
            "valid": validation_result["valid_count"],
            "invalid": validation_result["invalid_count"],
        })

        return result

    async def get_all_drivers(
        self,
        limit: Optional[int] = None,
        use_cache: bool = True,
        use_mcp: bool = False,
    ) -> Dict[str, Any]:
        """
        Get all drivers with pagination.

        Args:
            limit: Maximum number of drivers to fetch.
            use_cache: Whether to use cache.
            use_mcp: Whether to use MCP tools.

        Returns:
            Dictionary containing all driver data and validation results.
        """
        logger.info(f"Getting all drivers", extra={"limit": limit})

        # Check cache for full list
        if use_cache:
            cache_key = self.cache_manager.generate_key("drivers", "all", str(limit or "unlimited"))
            cached_data = await self.cache_manager.get(cache_key)

            if cached_data:
                logger.info("Returning cached all drivers data")
                return cached_data

        # Fetch all drivers
        try:
            if use_mcp:
                drivers = await self._fetch_all_drivers_via_mcp(limit)
            else:
                drivers = await self.api_client.fetch_all_drivers(limit)

            # Validate all drivers
            validation_result = self.validator.validate_drivers(drivers)

            result = {
                "total": len(drivers),
                "drivers": drivers,
                "validation": validation_result,
            }

            # Cache the result
            if use_cache:
                cache_key = self.cache_manager.generate_key("drivers", "all", str(limit or "unlimited"))
                await self.cache_manager.set(cache_key, result)

            logger.info(f"All drivers fetch completed", extra={
                "total": result["total"],
                "valid": validation_result["valid_count"],
                "invalid": validation_result["invalid_count"],
            })

            return result

        except Exception as e:
            logger.error(f"Failed to fetch all drivers", extra={
                "error": str(e),
            }, exc_info=True)
            raise

    async def summarize_drivers(
        self,
        drivers: List[Dict[str, Any]],
        use_mcp: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate a summary of driver data.

        Args:
            drivers: List of driver data dictionaries.
            use_mcp: Whether to use MCP SummarizeTool.

        Returns:
            Summary statistics and information.
        """
        logger.info(f"Summarizing drivers", extra={"count": len(drivers)})

        if use_mcp:
            try:
                summary = await self.mcp_invoker.summarize_data(drivers)
                return summary
            except MCPInvokerError as e:
                logger.warning(f"Failed to use MCP for summarization, falling back to local", extra={
                    "error": str(e),
                })

        # Local summarization fallback
        summary = {
            "total_drivers": len(drivers),
            "drivers_with_ratings": sum(1 for d in drivers if "rating" in d),
            "average_rating": None,
            "top_rated_drivers": [],
        }

        # Calculate average rating
        ratings = [d.get("rating") for d in drivers if "rating" in d and d.get("rating") is not None]
        if ratings:
            summary["average_rating"] = sum(ratings) / len(ratings)

            # Get top rated drivers
            sorted_drivers = sorted(
                [d for d in drivers if "rating" in d],
                key=lambda x: x.get("rating", 0),
                reverse=True,
            )
            summary["top_rated_drivers"] = sorted_drivers[:5]

        logger.info("Driver summary generated", extra=summary)
        return summary

    async def _fetch_driver_via_mcp(self, driver_id: str) -> Dict[str, Any]:
        """
        Fetch driver data using MCP FetchTool.

        Args:
            driver_id: Driver ID.

        Returns:
            Driver data dictionary.
        """
        logger.debug(f"Fetching driver via MCP", extra={"driver_id": driver_id})

        result = await self.mcp_invoker.fetch_data(
            endpoint=f"/drivers/{driver_id}",
            method="GET",
        )

        # Extract data from MCP response
        return result.get("data", result)

    async def _fetch_all_drivers_via_mcp(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch all drivers using MCP FetchTool.

        Args:
            limit: Maximum number of drivers to fetch.

        Returns:
            List of driver data dictionaries.
        """
        logger.debug("Fetching all drivers via MCP", extra={"limit": limit})

        params = {}
        if limit:
            params["limit"] = limit

        result = await self.mcp_invoker.fetch_data(
            endpoint="/drivers",
            method="GET",
            params=params,
        )

        # Extract data from MCP response
        drivers = result.get("data", result)
        if isinstance(drivers, dict):
            drivers = drivers.get("drivers", [])

        return drivers

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all components.

        Returns:
            Health status of all components.
        """
        logger.info("Performing health check")

        health = {
            "status": "healthy",
            "components": {},
        }

        # Check MCP Tool Server
        mcp_health = await self.mcp_invoker.health_check()
        health["components"]["mcp_tool_server"] = mcp_health

        # Check cache
        try:
            test_key = "health_check_test"
            await self.cache_manager.set(test_key, "test_value", ttl=5)
            cache_value = await self.cache_manager.get(test_key)
            await self.cache_manager.delete(test_key)

            health["components"]["cache"] = {
                "status": "healthy" if cache_value == "test_value" else "degraded",
            }
        except Exception as e:
            health["components"]["cache"] = {
                "status": "unhealthy",
                "error": str(e),
            }

        # Overall status
        unhealthy_components = [
            name for name, status in health["components"].items()
            if status.get("status") != "healthy"
        ]

        if unhealthy_components:
            health["status"] = "degraded"
            health["unhealthy_components"] = unhealthy_components

        logger.info("Health check completed", extra={"status": health["status"]})
        return health
