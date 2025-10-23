"""API client service for Driver Insight Agent."""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx

from ..config import get_config
from .logger import get_logger


class APIError(Exception):
    """Custom exception for API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        """Initialize API error.
        
        Args:
            message: Error message
            status_code: HTTP status code
            response_data: Response data if available
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class APIClient:
    """HTTP client for external driver API with retry logic and pagination support."""
    
    def __init__(self):
        """Initialize API client."""
        self.logger = get_logger()
        self.client: Optional[httpx.AsyncClient] = None
        self._config = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self.client is None:
            try:
                config = get_config()
                self._config = config.api
            except RuntimeError:
                # Fallback configuration
                self._config = type('APIConfig', (), {
                    'base_url': 'https://external.driver.api',
                    'timeout': 30.0,
                    'max_retries': 3,
                    'retry_delay': 1.0,
                    'pagination_size': 100,
                })()
            
            self.client = httpx.AsyncClient(
                base_url=self._config.base_url,
                timeout=httpx.Timeout(self._config.timeout),
                headers={
                    'User-Agent': 'DriverInsightAgent/1.0',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                }
            )
    
    async def close(self):
        """Close the HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    async def fetch_driver(self, driver_id: str) -> Dict[str, Any]:
        """Fetch single driver data.
        
        Args:
            driver_id: Driver ID to fetch
            
        Returns:
            Driver data dictionary
            
        Raises:
            APIError: If API request fails
        """
        await self._ensure_client()
        
        url = f"/drivers/{driver_id}"
        start_time = time.time()
        
        try:
            response_data = await self._make_request_with_retry("GET", url)
            duration = time.time() - start_time
            
            self.logger.log_api_request(
                "GET", url, 200, duration,
                driver_id=driver_id
            )
            
            return response_data
            
        except APIError as e:
            duration = time.time() - start_time
            self.logger.log_api_request(
                "GET", url, e.status_code, duration,
                driver_id=driver_id, error=str(e)
            )
            raise
    
    async def fetch_drivers_batch(self, driver_ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch multiple drivers in batch.
        
        Args:
            driver_ids: List of driver IDs to fetch
            
        Returns:
            List of driver data dictionaries
            
        Raises:
            APIError: If API request fails
        """
        await self._ensure_client()
        
        url = "/drivers/batch"
        start_time = time.time()
        
        try:
            payload = {"driver_ids": driver_ids}
            response_data = await self._make_request_with_retry("POST", url, json=payload)
            duration = time.time() - start_time
            
            self.logger.log_api_request(
                "POST", url, 200, duration,
                batch_size=len(driver_ids)
            )
            
            # Ensure response is a list
            if isinstance(response_data, dict) and "drivers" in response_data:
                return response_data["drivers"]
            elif isinstance(response_data, list):
                return response_data
            else:
                raise APIError("Invalid batch response format", response_data=response_data)
            
        except APIError as e:
            duration = time.time() - start_time
            self.logger.log_api_request(
                "POST", url, e.status_code, duration,
                batch_size=len(driver_ids), error=str(e)
            )
            raise
    
    async def fetch_all_drivers(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch all drivers with pagination support.
        
        Args:
            limit: Maximum number of drivers to fetch (None for all)
            
        Returns:
            List of all driver data dictionaries
            
        Raises:
            APIError: If API request fails
        """
        await self._ensure_client()
        
        all_drivers = []
        page = 1
        page_size = self._config.pagination_size
        
        while True:
            url = f"/drivers?page={page}&size={page_size}"
            start_time = time.time()
            
            try:
                response_data = await self._make_request_with_retry("GET", url)
                duration = time.time() - start_time
                
                # Extract drivers from response
                if isinstance(response_data, dict):
                    drivers = response_data.get("drivers", response_data.get("data", []))
                    has_more = response_data.get("has_more", False)
                    total_pages = response_data.get("total_pages", 1)
                elif isinstance(response_data, list):
                    drivers = response_data
                    has_more = len(drivers) == page_size
                    total_pages = None
                else:
                    raise APIError("Invalid pagination response format", response_data=response_data)
                
                all_drivers.extend(drivers)
                
                self.logger.log_api_request(
                    "GET", url, 200, duration,
                    page=page, page_size=len(drivers), total_fetched=len(all_drivers)
                )
                
                # Check stopping conditions
                if not has_more or len(drivers) == 0:
                    break
                
                if limit and len(all_drivers) >= limit:
                    all_drivers = all_drivers[:limit]
                    break
                
                page += 1
                
                # Add small delay between requests to be respectful
                await asyncio.sleep(0.1)
                
            except APIError as e:
                duration = time.time() - start_time
                self.logger.log_api_request(
                    "GET", url, e.status_code, duration,
                    page=page, error=str(e)
                )
                raise
        
        self.logger.info(f"Fetched {len(all_drivers)} drivers total")
        return all_drivers
    
    async def _make_request_with_retry(
        self, 
        method: str, 
        url: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic.
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            APIError: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(self._config.max_retries + 1):
            try:
                response = await self.client.request(method, url, **kwargs)
                
                # Handle different response status codes
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    raise APIError(
                        f"Resource not found: {url}",
                        status_code=response.status_code
                    )
                elif response.status_code == 429:
                    # Rate limited - wait longer before retry
                    if attempt < self._config.max_retries:
                        wait_time = self._config.retry_delay * (2 ** attempt)
                        self.logger.warning(
                            f"Rate limited, waiting {wait_time}s before retry",
                            attempt=attempt + 1, url=url
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise APIError(
                            "Rate limit exceeded",
                            status_code=response.status_code
                        )
                elif 500 <= response.status_code < 600:
                    # Server error - retry
                    if attempt < self._config.max_retries:
                        wait_time = self._config.retry_delay * (attempt + 1)
                        self.logger.warning(
                            f"Server error {response.status_code}, retrying in {wait_time}s",
                            attempt=attempt + 1, url=url
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise APIError(
                            f"Server error: {response.status_code}",
                            status_code=response.status_code
                        )
                else:
                    # Client error - don't retry
                    try:
                        error_data = response.json()
                    except:
                        error_data = {"message": response.text}
                    
                    raise APIError(
                        f"Client error: {response.status_code}",
                        status_code=response.status_code,
                        response_data=error_data
                    )
                
            except httpx.RequestError as e:
                last_exception = e
                if attempt < self._config.max_retries:
                    wait_time = self._config.retry_delay * (attempt + 1)
                    self.logger.warning(
                        f"Request error, retrying in {wait_time}s: {str(e)}",
                        attempt=attempt + 1, url=url
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise APIError(f"Request failed after {self._config.max_retries} retries: {str(e)}")
            
            except Exception as e:
                last_exception = e
                raise APIError(f"Unexpected error: {str(e)}")
        
        # This should not be reached, but just in case
        raise APIError(f"Request failed after {self._config.max_retries} retries: {str(last_exception)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the external API.
        
        Returns:
            Health check result
        """
        await self._ensure_client()
        
        start_time = time.time()
        
        try:
            # Try a simple endpoint or health check endpoint
            response = await self.client.get("/health")
            duration = time.time() - start_time
            
            if response.status_code == 200:
                self.logger.log_api_request("GET", "/health", 200, duration)
                return {
                    "status": "healthy",
                    "response_time": duration,
                    "timestamp": time.time()
                }
            else:
                self.logger.log_api_request("GET", "/health", response.status_code, duration)
                return {
                    "status": "unhealthy",
                    "response_time": duration,
                    "status_code": response.status_code,
                    "timestamp": time.time()
                }
        
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error("API health check failed", error=str(e), duration=duration)
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time": duration,
                "timestamp": time.time()
            }


# Global API client instance
_api_client: Optional[APIClient] = None


def get_api_client() -> APIClient:
    """Get the global API client instance.
    
    Returns:
        APIClient: The API client instance
    """
    global _api_client
    if _api_client is None:
        _api_client = APIClient()
    return _api_client