"""
HTTP client for API Gateway using httpx.
"""

import asyncio
from agent.utils.logging import get_logger
import time
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base_client import (
    BaseAPIClient,
    APIClientError,
    APITimeoutError,
    APIConnectionError,
    APIResponseError,
)

logger = get_logger(__name__)


class APIGatewayHTTPClient(BaseAPIClient):
    """
    Generic HTTP client for calling API Gateway endpoints.
    Supports all API Gateway services: Weather, SERP, Tavily, VietMap, etc.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        timeout: float = 10.0,
        max_retries: int = 3,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
    ):
        # Ensure we always have a usable gateway URL; fall back to localhost:8001
        base_url = base_url or "http://localhost:8001"
        super().__init__(
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            circuit_breaker_threshold=circuit_breaker_threshold,
            circuit_breaker_timeout=circuit_breaker_timeout,
        )
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        reraise=True,
    )
    async def call(
        self,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make an HTTP API call to API Gateway.
        
        Args:
            endpoint: API endpoint path (e.g., "/api/weather/current")
            method: HTTP method (GET, POST, etc.)
            data: Request payload (for POST/PUT)
            headers: Additional headers
            **kwargs: Additional httpx parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            APITimeoutError: Request timed out
            APIConnectionError: Connection failed
            APIResponseError: API returned error response
        """
        start_time = time.time()
        
        # Prepare headers
        req_headers = {
            "Content-Type": "application/json",
            "X-Trace-Id": kwargs.pop("trace_id", f"education-{int(time.time() * 1000)}"),
        }
        if headers:
            req_headers.update(headers)

        self._log_request(method, endpoint, data=data, headers=req_headers)

        try:
            # Call directly without circuit breaker for async (pybreaker has issues with Python 3.12+)
            # TODO: Replace with async-compatible circuit breaker library
            response = await self._make_request(
                method=method,
                endpoint=endpoint,
                data=data,
                headers=req_headers,
                **kwargs
            )
            
            duration = time.time() - start_time
            self._log_response(method, endpoint, response.status_code, duration)
            
            # Handle response
            if response.status_code >= 400:
                error_msg = f"API returned {response.status_code}: {response.text}"
                raise APIResponseError(error_msg)
            
            try:
                return response.json()
            except Exception as json_err:
                logger.error(f"Failed to parse JSON response from {endpoint}: {response.text[:500]}")
                raise APIClientError(f"Invalid JSON response: {str(json_err)}") from json_err
            
        except httpx.TimeoutException as e:
            self._log_error(method, endpoint, e)
            raise APITimeoutError(f"Request to {endpoint} timed out") from e
            
        except httpx.ConnectError as e:
            self._log_error(method, endpoint, e)
            raise APIConnectionError(f"Failed to connect to {endpoint}") from e
            
        except Exception as e:
            self._log_error(method, endpoint, e)
            raise APIClientError(f"API call failed: {str(e)}") from e

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> httpx.Response:
        """Internal method to make the actual HTTP request."""
        if method.upper() == "GET":
            return await self.client.get(endpoint, headers=headers, **kwargs)
        elif method.upper() == "POST":
            return await self.client.post(endpoint, json=data, headers=headers, **kwargs)
        elif method.upper() == "PUT":
            return await self.client.put(endpoint, json=data, headers=headers, **kwargs)
        elif method.upper() == "DELETE":
            return await self.client.delete(endpoint, headers=headers, **kwargs)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

    # ==================== Weather APIs ====================
    
    async def get_current_weather(
        self,
        location: str,
        units: str = "metric",
        lang: str = "vi",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get current weather for a location.
        
        Args:
            location: City name or coordinates
            units: Temperature units (metric/imperial)
            lang: Language code
            
        Returns:
            Weather data
        """
        return await self.call(
            endpoint="/api/v1/weather/current",
            method="POST",
            data={"location": location, "units": units, "lang": lang},
            **kwargs
        )

    async def get_weather_forecast(
        self,
        location: str,
        days: int = 5,
        units: str = "metric",
        lang: str = "vi",
        **kwargs
    ) -> Dict[str, Any]:
        """Get weather forecast."""
        return await self.call(
            endpoint="/api/v1/weather/forecast",
            method="POST",
            data={"location": location, "days": days, "units": units, "lang": lang},
            **kwargs
        )

    async def get_air_quality(
        self,
        location: str,
        lang: str = "vi",
        **kwargs
    ) -> Dict[str, Any]:
        """Get air quality data."""
        return await self.call(
            endpoint="/api/v1/weather/air-quality",
            method="POST",
            data={"location": location, "lang": lang},
            **kwargs
        )

    # ==================== Search APIs ====================
    
    async def google_search(
        self,
        query: str,
        num_results: int = 5,
        location: str = "Vietnam",
        language: str = "vi",
        **kwargs
    ) -> Dict[str, Any]:
        """Perform Google search."""
        return await self.call(
            endpoint="/api/v1/serp/search",
            method="POST",
            data={
                "query": query,
                "num_results": num_results,
                "location": location,
                "language": language
            },
            **kwargs
        )

    async def news_search(
        self,
        query: str,
        num_results: int = 5,
        tbs: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Search Google News."""
        data = {"query": query, "num_results": num_results}
        if tbs:
            data["tbs"] = tbs
        return await self.call(
            endpoint="/api/v1/search/news",
            method="POST",
            data=data,
            **kwargs
        )

    async def tavily_search(
        self,
        query: str,
        search_depth: str = "basic",
        max_results: int = 5,
        include_answer: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Search using Tavily AI."""
        return await self.call(
            endpoint="/api/v1/tavily/search",
            method="POST",
            data={
                "query": query,
                "search_depth": search_depth,
                "max_results": max_results,
                "include_answer": include_answer
            },
            **kwargs
        )

    # ==================== Map APIs ====================
    
    async def geocode(
        self,
        address: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Convert address to coordinates."""
        return await self.call(
            endpoint="/api/v1/map/geocode",
            method="POST",
            data={"address": address},
            **kwargs
        )

    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        **kwargs
    ) -> Dict[str, Any]:
        """Convert coordinates to address."""
        return await self.call(
            endpoint="/api/v1/map/reverse-geocode",
            method="POST",
            data={"latitude": latitude, "longitude": longitude},
            **kwargs
        )

    async def get_directions(
        self,
        origin: Dict[str, Any],
        destination: Dict[str, Any],
        mode: str = "drive",
        **kwargs
    ) -> Dict[str, Any]:
        """Get directions between two locations."""
        return await self.call(
            endpoint="/api/v1/map/directions",
            method="POST",
            data={
                "origin": origin,
                "destination": destination,
                "mode": mode
            },
            **kwargs
        )
