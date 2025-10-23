"""Tool handlers for MCP tool operations in Driver Insight Agent."""

from typing import Any, Dict, List, Optional, Union

from .mcp_invoker import MCPInvoker, MCPToolError, get_mcp_invoker
from ..services.logger import get_logger


class ToolHandlerError(Exception):
    """Custom exception for tool handler errors."""
    pass


class FetchHandler:
    """Handler for fetch operations using MCP FetchTool."""
    
    def __init__(self, mcp_invoker: Optional[MCPInvoker] = None):
        """Initialize fetch handler.
        
        Args:
            mcp_invoker: MCP invoker instance (optional, will use global if not provided)
        """
        self.mcp_invoker = mcp_invoker or get_mcp_invoker()
        self.logger = get_logger()
    
    async def fetch_single_driver(self, driver_id: str) -> Dict[str, Any]:
        """Fetch single driver using MCP FetchTool.
        
        Args:
            driver_id: Driver ID to fetch
            
        Returns:
            Driver data
            
        Raises:
            ToolHandlerError: If fetch operation fails
        """
        try:
            result = await self.mcp_invoker.invoke_fetch_tool(driver_id=driver_id)
            
            if result.get("success") and "data" in result:
                return result["data"]
            else:
                error_msg = result.get("error", "Unknown fetch error")
                raise ToolHandlerError(f"Failed to fetch driver {driver_id}: {error_msg}")
        
        except MCPToolError as e:
            raise ToolHandlerError(f"MCP FetchTool error: {str(e)}")
        except Exception as e:
            raise ToolHandlerError(f"Unexpected error fetching driver {driver_id}: {str(e)}")
    
    async def fetch_multiple_drivers(self, driver_ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch multiple drivers using MCP FetchTool.
        
        Args:
            driver_ids: List of driver IDs to fetch
            
        Returns:
            List of driver data
            
        Raises:
            ToolHandlerError: If fetch operation fails
        """
        try:
            result = await self.mcp_invoker.invoke_fetch_tool(driver_ids=driver_ids)
            
            if result.get("success") and "data" in result:
                data = result["data"]
                if isinstance(data, list):
                    return data
                else:
                    # Handle case where single driver is returned as dict
                    return [data] if isinstance(data, dict) else []
            else:
                error_msg = result.get("error", "Unknown batch fetch error")
                raise ToolHandlerError(f"Failed to fetch drivers {driver_ids}: {error_msg}")
        
        except MCPToolError as e:
            raise ToolHandlerError(f"MCP FetchTool error: {str(e)}")
        except Exception as e:
            raise ToolHandlerError(f"Unexpected error fetching drivers {driver_ids}: {str(e)}")


class ValidationHandler:
    """Handler for validation operations using MCP ValidateTool."""
    
    def __init__(self, mcp_invoker: Optional[MCPInvoker] = None):
        """Initialize validation handler.
        
        Args:
            mcp_invoker: MCP invoker instance (optional, will use global if not provided)
        """
        self.mcp_invoker = mcp_invoker or get_mcp_invoker()
        self.logger = get_logger()
    
    async def validate_driver_data(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Validate driver data using MCP ValidateTool.
        
        Args:
            data: Driver data to validate (single dict or list of dicts)
            
        Returns:
            Validation result with is_valid flag and errors
            
        Raises:
            ToolHandlerError: If validation operation fails
        """
        try:
            validation_type = "driver_batch" if isinstance(data, list) else "driver"
            result = await self.mcp_invoker.invoke_validate_tool(data, validation_type)
            
            if result.get("success"):
                return {
                    "is_valid": result.get("is_valid", False),
                    "errors": result.get("errors", []),
                    "warnings": result.get("warnings", []),
                    "validated_count": result.get("validated_count", 1 if not isinstance(data, list) else len(data))
                }
            else:
                error_msg = result.get("error", "Unknown validation error")
                raise ToolHandlerError(f"Validation failed: {error_msg}")
        
        except MCPToolError as e:
            raise ToolHandlerError(f"MCP ValidateTool error: {str(e)}")
        except Exception as e:
            raise ToolHandlerError(f"Unexpected error during validation: {str(e)}")


class CacheHandler:
    """Handler for cache operations using MCP CacheTool."""
    
    def __init__(self, mcp_invoker: Optional[MCPInvoker] = None):
        """Initialize cache handler.
        
        Args:
            mcp_invoker: MCP invoker instance (optional, will use global if not provided)
        """
        self.mcp_invoker = mcp_invoker or get_mcp_invoker()
        self.logger = get_logger()
    
    async def get_cached_data(self, key: str) -> Optional[Any]:
        """Get data from cache using MCP CacheTool.
        
        Args:
            key: Cache key
            
        Returns:
            Cached data or None if not found
            
        Raises:
            ToolHandlerError: If cache operation fails
        """
        try:
            result = await self.mcp_invoker.invoke_cache_tool("get", key)
            
            if result.get("success"):
                return result.get("data")
            else:
                # Cache miss is not an error
                return None
        
        except MCPToolError as e:
            self.logger.warning(f"Cache get operation failed for key {key}: {str(e)}")
            return None
        except Exception as e:
            self.logger.warning(f"Unexpected error getting cache key {key}: {str(e)}")
            return None
    
    async def set_cached_data(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Set data in cache using MCP CacheTool.
        
        Args:
            key: Cache key
            data: Data to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.mcp_invoker.invoke_cache_tool("set", key, data, ttl)
            
            return result.get("success", False)
        
        except MCPToolError as e:
            self.logger.warning(f"Cache set operation failed for key {key}: {str(e)}")
            return False
        except Exception as e:
            self.logger.warning(f"Unexpected error setting cache key {key}: {str(e)}")
            return False
    
    async def delete_cached_data(self, key: str) -> bool:
        """Delete data from cache using MCP CacheTool.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.mcp_invoker.invoke_cache_tool("delete", key)
            
            return result.get("success", False)
        
        except MCPToolError as e:
            self.logger.warning(f"Cache delete operation failed for key {key}: {str(e)}")
            return False
        except Exception as e:
            self.logger.warning(f"Unexpected error deleting cache key {key}: {str(e)}")
            return False
    
    async def check_cache_exists(self, key: str) -> bool:
        """Check if key exists in cache using MCP CacheTool.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            result = await self.mcp_invoker.invoke_cache_tool("exists", key)
            
            if result.get("success"):
                return result.get("exists", False)
            else:
                return False
        
        except MCPToolError as e:
            self.logger.warning(f"Cache exists check failed for key {key}: {str(e)}")
            return False
        except Exception as e:
            self.logger.warning(f"Unexpected error checking cache key {key}: {str(e)}")
            return False


class SummarizeHandler:
    """Handler for summarization operations using MCP SummarizeTool."""
    
    def __init__(self, mcp_invoker: Optional[MCPInvoker] = None):
        """Initialize summarize handler.
        
        Args:
            mcp_invoker: MCP invoker instance (optional, will use global if not provided)
        """
        self.mcp_invoker = mcp_invoker or get_mcp_invoker()
        self.logger = get_logger()
    
    async def summarize_driver_data(self, data: Union[Dict[str, Any], List[Dict[str, Any]]], summary_type: str = "driver_summary") -> Dict[str, Any]:
        """Summarize driver data using MCP SummarizeTool.
        
        Args:
            data: Driver data to summarize
            summary_type: Type of summary to generate
            
        Returns:
            Summary data
            
        Raises:
            ToolHandlerError: If summarization operation fails
        """
        try:
            result = await self.mcp_invoker.invoke_summarize_tool(data, summary_type)
            
            if result.get("success") and "summary" in result:
                return result["summary"]
            else:
                error_msg = result.get("error", "Unknown summarization error")
                raise ToolHandlerError(f"Summarization failed: {error_msg}")
        
        except MCPToolError as e:
            raise ToolHandlerError(f"MCP SummarizeTool error: {str(e)}")
        except Exception as e:
            raise ToolHandlerError(f"Unexpected error during summarization: {str(e)}")
    
    async def generate_driver_stats(self, drivers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate statistics summary for multiple drivers.
        
        Args:
            drivers: List of driver data
            
        Returns:
            Statistics summary
        """
        try:
            return await self.summarize_driver_data(drivers, "driver_stats")
        except ToolHandlerError as e:
            self.logger.error(f"Failed to generate driver stats: {str(e)}")
            # Return basic fallback stats
            return {
                "total_drivers": len(drivers),
                "error": "Failed to generate detailed statistics"
            }


class ToolOrchestrator:
    """Orchestrator for coordinating multiple MCP tool operations."""
    
    def __init__(self, mcp_invoker: Optional[MCPInvoker] = None):
        """Initialize tool orchestrator.
        
        Args:
            mcp_invoker: MCP invoker instance (optional, will use global if not provided)
        """
        self.mcp_invoker = mcp_invoker or get_mcp_invoker()
        self.fetch_handler = FetchHandler(mcp_invoker)
        self.validation_handler = ValidationHandler(mcp_invoker)
        self.cache_handler = CacheHandler(mcp_invoker)
        self.summarize_handler = SummarizeHandler(mcp_invoker)
        self.logger = get_logger()
    
    async def fetch_and_validate_driver(self, driver_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """Fetch and validate a single driver with caching.
        
        Args:
            driver_id: Driver ID to fetch
            use_cache: Whether to use caching
            
        Returns:
            Driver data with validation results
        """
        cache_key = f"driver:{driver_id}"
        
        # Try cache first if enabled
        if use_cache:
            cached_data = await self.cache_handler.get_cached_data(cache_key)
            if cached_data:
                self.logger.info(f"Retrieved driver {driver_id} from cache")
                return cached_data
        
        # Fetch from source
        driver_data = await self.fetch_handler.fetch_single_driver(driver_id)
        
        # Validate the data
        validation_result = await self.validation_handler.validate_driver_data(driver_data)
        
        # Combine data and validation results
        result = {
            "driver_data": driver_data,
            "validation": validation_result,
            "source": "api",
            "cached": False
        }
        
        # Cache if validation passed and caching is enabled
        if use_cache and validation_result.get("is_valid", False):
            await self.cache_handler.set_cached_data(cache_key, result)
        
        return result
    
    async def fetch_and_validate_drivers_batch(self, driver_ids: List[str], use_cache: bool = True) -> List[Dict[str, Any]]:
        """Fetch and validate multiple drivers with caching.
        
        Args:
            driver_ids: List of driver IDs to fetch
            use_cache: Whether to use caching
            
        Returns:
            List of driver data with validation results
        """
        results = []
        uncached_ids = []
        
        # Check cache for each driver if enabled
        if use_cache:
            for driver_id in driver_ids:
                cache_key = f"driver:{driver_id}"
                cached_data = await self.cache_handler.get_cached_data(cache_key)
                if cached_data:
                    results.append(cached_data)
                    self.logger.debug(f"Retrieved driver {driver_id} from cache")
                else:
                    uncached_ids.append(driver_id)
        else:
            uncached_ids = driver_ids
        
        # Fetch uncached drivers
        if uncached_ids:
            drivers_data = await self.fetch_handler.fetch_multiple_drivers(uncached_ids)
            
            # Validate batch
            validation_result = await self.validation_handler.validate_driver_data(drivers_data)
            
            # Process each driver
            for i, driver_data in enumerate(drivers_data):
                driver_id = driver_data.get("driver_id", uncached_ids[i] if i < len(uncached_ids) else f"unknown_{i}")
                
                result = {
                    "driver_data": driver_data,
                    "validation": {
                        "is_valid": validation_result.get("is_valid", False),
                        "errors": validation_result.get("errors", []),
                        "warnings": validation_result.get("warnings", [])
                    },
                    "source": "api",
                    "cached": False
                }
                
                results.append(result)
                
                # Cache valid drivers if enabled
                if use_cache and result["validation"].get("is_valid", False):
                    cache_key = f"driver:{driver_id}"
                    await self.cache_handler.set_cached_data(cache_key, result)
        
        return results
    
    async def get_drivers_summary(self, driver_ids: List[str]) -> Dict[str, Any]:
        """Get summary of multiple drivers.
        
        Args:
            driver_ids: List of driver IDs
            
        Returns:
            Summary data
        """
        # Fetch all drivers
        drivers_results = await self.fetch_and_validate_drivers_batch(driver_ids)
        
        # Extract just the driver data for summarization
        drivers_data = [result["driver_data"] for result in drivers_results if result["validation"].get("is_valid", False)]
        
        # Generate summary
        if drivers_data:
            summary = await self.summarize_handler.summarize_driver_data(drivers_data, "driver_batch_summary")
        else:
            summary = {"message": "No valid drivers to summarize"}
        
        return {
            "summary": summary,
            "total_requested": len(driver_ids),
            "valid_drivers": len(drivers_data),
            "invalid_drivers": len(driver_ids) - len(drivers_data)
        }


# Global tool handlers
_tool_orchestrator: Optional[ToolOrchestrator] = None


def get_tool_orchestrator() -> ToolOrchestrator:
    """Get the global tool orchestrator instance.
    
    Returns:
        ToolOrchestrator: The tool orchestrator instance
    """
    global _tool_orchestrator
    if _tool_orchestrator is None:
        _tool_orchestrator = ToolOrchestrator()
    return _tool_orchestrator