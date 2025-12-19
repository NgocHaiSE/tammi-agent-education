"""
External API clients for calling API Gateway services.
Supports both HTTP and gRPC protocols.
"""

from .http_client import APIGatewayHTTPClient
from .grpc_client import APIGatewayGRPCClient

__all__ = [
    "APIGatewayHTTPClient",
    "APIGatewayGRPCClient",
]
