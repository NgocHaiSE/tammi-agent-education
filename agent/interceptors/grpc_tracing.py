"""
gRPC interceptor for tracing and performance monitoring.

This interceptor adds request_id and trace_id to all gRPC calls and logs
detailed performance metrics for each stage of request processing.
"""

import time
import uuid
import logging
from typing import Callable, Any, Optional
import grpc
from grpc import ServicerContext

from agent.utils.performance_logger import async_performance_context
from agent.utils.performance_dashboard import log_grpc_latency
from agent.utils.trace_context import (
    set_current_trace_id,
    set_current_request_id
)

logger = logging.getLogger(__name__)

class GrpcTracingInterceptor(grpc.aio.ServerInterceptor):
    """
    gRPC interceptor that adds tracing information and detailed performance logging.
    
    This interceptor:
    1. Attaches request_id and trace_id to all requests
    2. Logs detailed timing breakdown for each processing stage
    3. Tracks method execution, serialization, and response times
    4. Provides structured performance data for monitoring
    """
    
    async def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], grpc.RpcMethodHandler],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        """Intercept gRPC service calls to add tracing and performance logging."""
        
        def wrapper(original_handler):
            """Wrap the original handler with tracing and performance logging."""
            
            async def traced_handler(request, context: ServicerContext):
                # Extract or generate tracing IDs
                request_id = self._get_or_generate_request_id(context)
                trace_id = self._get_or_generate_trace_id(context)
                idempotency_key = self._get_idempotency_key(context)
                
                # Set context variables so all logs automatically include these IDs
                set_current_request_id(request_id)
                set_current_trace_id(trace_id)

                # Set tracing context in initial metadata
                metadata_to_send = [
                    ("x-trace-id", trace_id),
                    ("x-request-id", request_id),
                ]
                if idempotency_key:
                    metadata_to_send.append(("x-idempotency-key", idempotency_key))
                await context.send_initial_metadata(metadata_to_send)

                method_name = handler_call_details.method
                
                async with async_performance_context(
                    f"grpc_request_{method_name.split('/')[-1]}", 
                    log_threshold_ms=50
                ) as timer:
                    
                    # Stage 1: Request processing and validation
                    timer.start_stage("request_processing")
                    try:
                        # Log request start
                        logger.info(
                            f"{method_name.split('/')[-1]} called",
                            extra={
                                "trace_id": trace_id,
                                "request_id": request_id,
                                "method": method_name,
                                "request_size_bytes": len(str(request)) if request else 0
                            }
                        )
                        timer.end_stage(
                            success=True,
                            request_size_bytes=len(str(request)) if request else 0
                        )
                    except Exception as e:
                        timer.end_stage(success=False, error=str(e)[:200])
                        raise
                    
                    # Stage 2: Business logic execution
                    timer.start_stage("business_logic_execution")
                    try:
                        start_time = time.perf_counter()
                        response = await original_handler(request, context)
                        execution_time_ms = (time.perf_counter() - start_time) * 1000
                        
                        timer.end_stage(
                            success=True,
                            execution_time_ms=round(execution_time_ms, 2),
                            response_size_bytes=len(str(response)) if response else 0
                        )
                    except Exception as e:
                        execution_time_ms = (time.perf_counter() - start_time) * 1000
                        timer.end_stage(
                            success=False, 
                            error=str(e)[:200],
                            execution_time_ms=round(execution_time_ms, 2)
                        )
                        raise
                    
                    # Stage 3: Response serialization and finalization
                    timer.start_stage("response_serialization")
                    try:
                        # Response is already created, just measure serialization overhead
                        start_time = time.perf_counter()
                        response_str = str(response) if response else ""
                        serialization_time_ms = (time.perf_counter() - start_time) * 1000
                        
                        timer.end_stage(
                            success=True,
                            serialization_time_ms=round(serialization_time_ms, 2),
                            response_size_bytes=len(response_str)
                        )
                        
                        return response
                        
                    except Exception as e:
                        timer.end_stage(success=False, error=str(e)[:200])
                        raise
            
            return traced_handler
        
        handler = await continuation(handler_call_details)
        if handler and hasattr(handler, 'unary_unary') and handler.unary_unary:
            return grpc.unary_unary_rpc_method_handler(
                wrapper(handler.unary_unary),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )
        
        return handler
    
    def _get_or_generate_request_id(self, context: ServicerContext) -> str:
        """Generate a new unique request_id.

        Note: request_id is ALWAYS generated by this service, never from client.
        This ensures uniqueness and proper request tracking within this service.
        """
        # ALWAYS generate new request_id - do NOT accept from client
        return str(uuid.uuid4()).replace("-", "")

    def _get_or_generate_trace_id(self, context: ServicerContext) -> str:
        """Get trace_id from metadata or generate a new one.

        For distributed tracing:
        - If client sends x-trace-id metadata -> PROPAGATE it (part of existing trace)
        - If no trace_id -> GENERATE new one (start of new trace)
        """
        metadata = dict(context.invocation_metadata())
        trace_id = metadata.get("x-trace-id") or metadata.get("trace_id")
        if not trace_id:
            trace_id = str(uuid.uuid4()).replace("-", "")
        return trace_id
    
    def _get_idempotency_key(self, context: ServicerContext) -> Optional[str]:
        """Get idempotency key from metadata if present."""
        metadata = dict(context.invocation_metadata())
        return metadata.get("idempotency_key")

    async def intercept_unary_unary(self, continuation, client_call_details, request):
        """Intercept unary-unary gRPC calls with detailed performance tracking."""
        start_time = time.perf_counter()
        request_id = str(uuid.uuid4())
        trace_id = str(uuid.uuid4())
        
        # Extract existing IDs from metadata if available
        metadata = dict(client_call_details.metadata or [])
        if 'request-id' in metadata:
            request_id = metadata['request-id']
        if 'trace-id' in metadata:
            trace_id = metadata['trace-id']
        
        # Generate idempotency key if not present
        idempotency_key = metadata.get('idempotency-key')
        
        # Add trace and request IDs to metadata
        new_metadata = list(client_call_details.metadata or [])
        new_metadata.extend([
            ('request-id', request_id),
            ('trace-id', trace_id),
        ])
        
        # Create new client call details with updated metadata
        new_client_call_details = client_call_details._replace(metadata=new_metadata)
        
        method_name = client_call_details.method
        success = True
        error_details = None
        
        try:
            # Use performance context for detailed timing
            async with async_performance_context(
                operation="grpc_request",
                trace_id=trace_id,
                request_id=request_id
            ) as perf_ctx:
                
                # Track request processing stage
                async with perf_ctx.stage("request_processing") as stage:
                    stage.add_metric("method", method_name)
                    stage.add_metric("request_size_bytes", len(str(request)))
                
                # Track business logic execution
                async with perf_ctx.stage("business_logic_execution") as stage:
                    response = await continuation(new_client_call_details, request)
                    stage.add_metric("success", True)
                
                # Track response serialization
                async with perf_ctx.stage("response_serialization") as stage:
                    response_size = len(str(response)) if response else 0
                    stage.add_metric("response_size_bytes", response_size)
                    stage.add_metric("serialization_ms", (time.perf_counter() - start_time) * 1000)
            
            return response
            
        except Exception as e:
            success = False
            error_details = str(e)
            logger.error(
                f"gRPC request failed: {method_name}",
                extra={
                    "trace_id": trace_id,
                    "request_id": request_id,
                    "error": error_details
                }
            )
            raise
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            
            # Log to existing system
            logger.info(
                "gRPC request completed",
                extra={
                    "trace_id": trace_id,
                    "request_id": request_id,
                    "method": method_name,
                    "idempotency_key": idempotency_key,
                    "duration_ms": duration_ms
                }
            )
            
            # Log to performance dashboard
            log_grpc_latency(
                handler_name=method_name.split('/')[-2] if '/' in method_name else "unknown",
                method=method_name,
                duration_ms=duration_ms,
                success=success,
                trace_id=trace_id,
                request_id=request_id
            )