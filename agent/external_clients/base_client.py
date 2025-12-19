"""
Base client with retry, timeout, circuit-breaking, and logging capabilities.
"""

from agent.utils.logging import get_logger
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from functools import wraps

from pybreaker import CircuitBreaker, CircuitBreakerError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = get_logger(__name__)


class APIClientError(Exception):
    """Base exception for API client errors."""
    pass


class APITimeoutError(APIClientError):
    """Raised when API call times out."""
    pass


class APIConnectionError(APIClientError):
    """Raised when connection to API fails."""
    pass


class APIResponseError(APIClientError):
    """Raised when API returns an error response."""
    pass


class BaseAPIClient(ABC):
    """
    Base class for API clients with built-in retry, timeout, and circuit-breaking.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        max_retries: int = 3,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Circuit breaker to prevent cascading failures
        self.circuit_breaker = CircuitBreaker(
            fail_max=circuit_breaker_threshold,
            reset_timeout=circuit_breaker_timeout,
            name=f"{self.__class__.__name__}_breaker"
        )
        
        logger.info(
            f"Initialized {self.__class__.__name__} with base_url={base_url}, "
            f"timeout={timeout}s, max_retries={max_retries}"
        )

    def _log_request(self, method: str, endpoint: str, **kwargs):
        """Log outgoing request."""
        logger.info(
            f"API Request: {method} {endpoint}",
            extra={
                "event": "api_request",
                "method": method,
                "endpoint": endpoint,
                "client": self.__class__.__name__,
            }
        )

    def _log_response(self, method: str, endpoint: str, status: int, duration: float):
        """Log API response."""
        logger.info(
            f"API Response: {method} {endpoint} - {status} ({duration:.3f}s)",
            extra={
                "event": "api_response",
                "method": method,
                "endpoint": endpoint,
                "status": status,
                "duration_sec": duration,
                "client": self.__class__.__name__,
            }
        )

    def _log_error(self, method: str, endpoint: str, error: Exception):
        """Log API error."""
        logger.error(
            f"API Error: {method} {endpoint} - {error}",
            extra={
                "event": "api_error",
                "method": method,
                "endpoint": endpoint,
                "error": str(error),
                "client": self.__class__.__name__,
            },
            exc_info=True
        )

    @abstractmethod
    async def call(
        self,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make an API call. Must be implemented by subclasses.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            data: Request payload
            headers: Additional headers
            **kwargs: Additional parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            APIClientError: For any API-related errors
        """
        pass
