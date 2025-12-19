"""
gRPC client for API Gateway.
Note: This is a placeholder. Actual implementation requires proto files from API Gateway.
"""

from agent.utils.logging import get_logger
from typing import Any, Dict, Optional

from .base_client import BaseAPIClient, APIClientError

logger = get_logger(__name__)


class APIGatewayGRPCClient(BaseAPIClient):
    """
    gRPC client for API Gateway.
    
    TODO: Implement when API Gateway proto files are available.
    For now, this is a placeholder that delegates to HTTP client.
    """

    def __init__(
        self,
        base_url: str = "localhost:50051",
        timeout: float = 10.0,
        max_retries: int = 3,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
    ):
        super().__init__(
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            circuit_breaker_threshold=circuit_breaker_threshold,
            circuit_breaker_timeout=circuit_breaker_timeout,
        )
        logger.warning(
            "gRPC client is not fully implemented yet. "
            "Please use APIGatewayHTTPClient for now."
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
        Placeholder for gRPC call.
        
        TODO: Implement actual gRPC communication when proto files are available.
        """
        raise NotImplementedError(
            "gRPC client not yet implemented. Use APIGatewayHTTPClient instead."
        )

    async def close(self):
        """Close gRPC channel."""
        pass
