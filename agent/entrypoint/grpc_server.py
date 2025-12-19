from __future__ import annotations

# Load environment configuration EARLY, before any other imports
from agent.config.env_manager import EnvManager, get_int
from agent.interceptors.grpc_error_handling import GrpcErrorHandlingInterceptor
from agent.interceptors.grpc_tracing import GrpcTracingInterceptor

env_manager = EnvManager()
env_manager.load_environment()

import asyncio
from agent.utils.logging import get_logger

# Try to use uvloop for better async performance
try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    print("[OK] uvloop installed - Using high-performance event loop for gRPC")
except ImportError:
    print("[INFO] uvloop not available - Using default asyncio event loop")

import grpc.aio
from grpc_reflection.v1alpha import reflection

from agent.config.settings import get_settings
from agent.handlers.grpc_handler import AgentServiceHandler
from agent.proto import agents_pb2_grpc, agents_pb2

settings = get_settings()
logger = get_logger(f"{settings.AGENT_NAME}_gRPC")


async def serve() -> None:
    """Start async gRPC server with grpc.aio for native async/await support."""
    max_message_bytes = settings.grpc_max_message_size_mb * 1024 * 1024

    server_options = [
        # Connection settings (from ENV)
        ('grpc.max_concurrent_streams', settings.grpc_max_concurrent_streams),
        ('grpc.so_reuseport', 1),  # Allow multiple server instances (load balancing)

        # Keepalive settings (from ENV) - reduce connection overhead
        ('grpc.keepalive_time_ms', settings.grpc_keepalive_time_ms),
        ('grpc.keepalive_timeout_ms', settings.grpc_keepalive_timeout_ms),
        ('grpc.keepalive_permit_without_calls', 1),  # Allow keepalive without active calls
        ('grpc.http2.max_pings_without_data', 0),  # No limit on pings without data

        # Performance tuning (from ENV)
        ('grpc.http2.min_time_between_pings_ms', settings.grpc_min_ping_interval_ms),
        ('grpc.http2.max_ping_strikes', settings.grpc_max_ping_strikes),

        # Resource limits (from ENV)
        ('grpc.max_send_message_length', max_message_bytes),
        ('grpc.max_receive_message_length', max_message_bytes),
    ]

    # Create gRPC server with interceptors and optimization settings
    server = grpc.aio.server(
        interceptors=[
            GrpcTracingInterceptor(),
            GrpcErrorHandlingInterceptor()
        ],
        options=server_options  # PHASE 2: Add production settings
    )

    logger.info("[OK] gRPC server configured from ENV variables")
    logger.info(f"   - max_concurrent_streams: {settings.grpc_max_concurrent_streams}")
    logger.info(f"   - keepalive_time: {settings.grpc_keepalive_time_ms}ms")
    logger.info(f"   - keepalive_timeout: {settings.grpc_keepalive_timeout_ms}ms")
    logger.info(f"   - max_message_size: {settings.grpc_max_message_size_mb}MB")

    # Add AgentService
    agents_pb2_grpc.add_AgentServiceServicer_to_server(AgentServiceHandler(), server)

    # Enable gRPC Server Reflection for grpcurl and debugging
    SERVICE_NAMES = (
        agents_pb2.DESCRIPTOR.services_by_name['AgentService'].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)
    logger.info(f"gRPC Reflection enabled - {len(SERVICE_NAMES)} services discoverable")

    bind = f"{settings.GRPC_HOST}:{settings.GRPC_PORT}"
    server.add_insecure_port(bind)
    logger.info(
        "%s gRPC server listening on %s (reflection enabled)",
        settings.agent_display_name,
        bind
    )
    await server.start()
    await server.wait_for_termination()


def main():
    """Main entry point for gRPC server."""
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("gRPC server stopped by user")
    except Exception as e:
        logger.error(f"gRPC server failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()