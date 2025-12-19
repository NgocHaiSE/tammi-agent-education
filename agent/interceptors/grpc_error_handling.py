from __future__ import annotations

import grpc
from agent.utils.logging import get_logger

logger = get_logger(__name__)


_EXCEPTION_CODE_MAP = {
    ValueError: grpc.StatusCode.INVALID_ARGUMENT,
    PermissionError: grpc.StatusCode.PERMISSION_DENIED,
    FileNotFoundError: grpc.StatusCode.NOT_FOUND,
}


class GrpcErrorHandlingInterceptor(grpc.aio.ServerInterceptor):
    """Maps common Python exceptions to gRPC status codes for unary-unary RPCs."""

    async def intercept_service(self, continuation, handler_call_details):  # type: ignore[override]
        handler = await continuation(handler_call_details)
        if handler is None:
            return None

        if handler.unary_unary:
            original = handler.unary_unary
            
            # Check if the original handler is a coroutine function
            import inspect
            is_async = inspect.iscoroutinefunction(original)

            async def safe_unary_unary(request, context):
                try:
                    if is_async:
                        return await original(request, context)
                    else:
                        # Call sync function directly (e.g., health check handlers)
                        return original(request, context)
                except Exception as e:  # pylint: disable=broad-except
                    # Find mapped status code or default to INTERNAL
                    status = grpc.StatusCode.INTERNAL
                    for etype, code in _EXCEPTION_CODE_MAP.items():
                        if isinstance(e, etype):
                            status = code
                            break
                    logger.exception("Unhandled exception in gRPC handler: %s", e)
                    await context.abort(status, str(e) if status != grpc.StatusCode.INTERNAL else "Internal error")

            return grpc.unary_unary_rpc_method_handler(
                safe_unary_unary,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        return handler
