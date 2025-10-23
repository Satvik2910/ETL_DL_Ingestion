"""
API client for fetching driver data from external APIs.
Handles pagination, retries, and error handling.
"""

import asyncio
from typing import Any, Dict, List, Optional

import httpx

from config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)


class APIError(Exception):
    """Custom exception for API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Any] = None):
        """
        Initialize API error.

        Args:
            message: Error message.
            status_code: HTTP status code.
            response_data: Response data from API.
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class APIClient:
    """
    Client for fetching driver data from external APIs.
    Supports pagination, retries, and timeout handling.
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize API client.

        Args:
            base_url: Base URL for the API. Uses config default if None.
        """
        config = get_config()
        self.base_url = base_url or config.api.base_url
        self.timeout = config.api.timeout
        self.max_retries = config.api.max_retries
        self.retry_delay = config.api.retry_delay
        self.page_size = config.pagination.page_size
        self.max_pages = config.pagination.max_pages

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            follow_redirects=True,
        )

        logger.info("API client initialized", extra={
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
        })

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        logger.debug("API client closed")

    async def fetch_driver(self, driver_id: str) -> Dict[str, Any]:
        """
        Fetch a single driver by ID.

        Args:
            driver_id: Driver ID.

        Returns:
            Driver data dictionary.

        Raises:
            APIError: If the API request fails.
        """
        logger.info(f"Fetching driver data", extra={"driver_id": driver_id})

        endpoint = f"/drivers/{driver_id}"
        data = await self._make_request("GET", endpoint)

        logger.info(f"Successfully fetched driver data", extra={"driver_id": driver_id})
        return data

    async def fetch_drivers_batch(self, driver_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch multiple drivers in batch.

        Args:
            driver_ids: List of driver IDs.

        Returns:
            List of driver data dictionaries.
        """
        logger.info(f"Fetching batch driver data", extra={"count": len(driver_ids)})

        # Create tasks for concurrent fetching
        tasks = [self.fetch_driver(driver_id) for driver_id in driver_ids]

        # Gather results, collecting exceptions
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Separate successful results from errors
        drivers = []
        errors = []

        for driver_id, result in zip(driver_ids, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch driver", extra={
                    "driver_id": driver_id,
                    "error": str(result),
                })
                errors.append({"driver_id": driver_id, "error": str(result)})
            else:
                drivers.append(result)

        logger.info(f"Batch fetch completed", extra={
            "total": len(driver_ids),
            "success": len(drivers),
            "failed": len(errors),
        })

        return drivers

    async def fetch_all_drivers(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch all drivers with pagination.

        Args:
            limit: Maximum number of drivers to fetch. None for all.

        Returns:
            List of all driver data dictionaries.
        """
        logger.info("Fetching all drivers", extra={"limit": limit})

        all_drivers = []
        page = 1
        total_fetched = 0

        while page <= self.max_pages:
            try:
                logger.debug(f"Fetching page {page}")

                endpoint = f"/drivers"
                params = {
                    "page": page,
                    "page_size": self.page_size,
                }

                data = await self._make_request("GET", endpoint, params=params)

                # Handle different response formats
                if isinstance(data, dict):
                    drivers = data.get("drivers", data.get("data", []))
                    total = data.get("total", 0)
                    has_next = data.get("has_next", False)
                else:
                    drivers = data
                    total = len(drivers)
                    has_next = len(drivers) == self.page_size

                all_drivers.extend(drivers)
                total_fetched += len(drivers)

                logger.debug(f"Fetched page {page}", extra={
                    "page": page,
                    "count": len(drivers),
                    "total_so_far": total_fetched,
                })

                # Check if we should stop
                if limit and total_fetched >= limit:
                    all_drivers = all_drivers[:limit]
                    break

                if not has_next or len(drivers) == 0:
                    break

                page += 1

            except APIError as e:
                logger.error(f"Failed to fetch page {page}", extra={
                    "page": page,
                    "error": str(e),
                })
                break

        logger.info(f"Fetched all drivers", extra={"total_count": len(all_drivers)})
        return all_drivers

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Make an HTTP request with retries.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint path.
            params: Query parameters.
            json_data: JSON request body.

        Returns:
            Response data.

        Raises:
            APIError: If the request fails after all retries.
        """
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"Making {method} request", extra={
                    "endpoint": endpoint,
                    "attempt": attempt,
                    "params": params,
                })

                response = await self.client.request(
                    method=method,
                    url=endpoint,
                    params=params,
                    json=json_data,
                )

                # Check for HTTP errors
                if response.status_code >= 400:
                    error_msg = f"API request failed with status {response.status_code}"
                    logger.warning(error_msg, extra={
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "attempt": attempt,
                    })

                    if attempt < self.max_retries:
                        await asyncio.sleep(self.retry_delay * attempt)
                        continue

                    raise APIError(
                        error_msg,
                        status_code=response.status_code,
                        response_data=response.text,
                    )

                # Parse response
                try:
                    data = response.json()
                except Exception:
                    data = response.text

                return data

            except httpx.RequestError as e:
                last_error = e
                logger.warning(f"Request error on attempt {attempt}", extra={
                    "endpoint": endpoint,
                    "error": str(e),
                    "attempt": attempt,
                })

                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                    continue

            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error on attempt {attempt}", extra={
                    "endpoint": endpoint,
                    "error": str(e),
                    "attempt": attempt,
                }, exc_info=True)

                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                    continue

        # All retries exhausted
        error_msg = f"API request failed after {self.max_retries} attempts"
        logger.error(error_msg, extra={
            "endpoint": endpoint,
            "last_error": str(last_error),
        })

        raise APIError(error_msg, response_data=str(last_error))
