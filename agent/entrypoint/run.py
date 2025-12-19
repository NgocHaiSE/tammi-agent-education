"""Service Main - Unified Entry Point for Education Agent

Runs both HTTP (FastAPI) and gRPC servers concurrently.
This is the main entry point for the complete Agent service.
"""

from __future__ import annotations

import asyncio
import signal
import sys
from typing import Optional
from agent.utils.logging import get_logger

import uvicorn
from agent.config.settings import get_settings
from agent.config.env_manager import get_str, get_int

# Get settings for dynamic logger name
settings = get_settings()
logger = get_logger(f"{settings.AGENT_NAME}_ServiceMain")


class ServiceMain:
    """Main service orchestrator for HTTP and gRPC servers."""

    def __init__(self):
        self.http_server: Optional[uvicorn.Server] = None
        self.grpc_task: Optional[asyncio.Task] = None
        self.shutdown_event = asyncio.Event()

    async def start_http_server(self):
        """Start FastAPI HTTP server."""
        from agent.entrypoint.http_server import app
        from agent.utils.logging import setup_logging

        # Setup logging in this process
        setup_logging()

        http_host = get_str("AGENT_HTTP_HOST")
        http_port = get_int("AGENT_HTTP_PORT")

        config = uvicorn.Config(
            app,
            host=http_host,
            port=http_port,
            log_level="warning",  # Reduce uvicorn noise
            access_log=False,     # Disable uvicorn access log (we have our own)
            log_config=None,      # Don't use uvicorn's logging config
        )
        self.http_server = uvicorn.Server(config)

        logger.info(f"🚀 Starting HTTP server on {http_host}:{http_port}")
        await self.http_server.serve()

    async def start_grpc_server(self):
        """Start gRPC server."""
        from agent.entrypoint.grpc_server import serve
        from agent.utils.logging import setup_logging

        # Setup logging in this process
        setup_logging()

        logger.info(f"🚀 Starting gRPC server on {settings.GRPC_HOST}:{settings.GRPC_PORT}")
        await serve()

    async def run(self):
        """Run both HTTP and gRPC servers concurrently."""
        logger.info("=" * 80)
        logger.info(f"🚀 {settings.AGENT_NAME} Service Starting")
        logger.info("=" * 80)
        logger.info(f"   HTTP Server: http://{get_str('AGENT_HTTP_HOST')}:{get_int('AGENT_HTTP_PORT')}")
        logger.info(f"   gRPC Server: {settings.GRPC_HOST}:{settings.GRPC_PORT}")
        logger.info("=" * 80)

        # Create tasks for both servers
        http_task = asyncio.create_task(self.start_http_server())
        grpc_task = asyncio.create_task(self.start_grpc_server())
        self.grpc_task = grpc_task

        # Wait for either server to complete (or error out)
        done, pending = await asyncio.wait(
            {http_task, grpc_task},
            return_when=asyncio.FIRST_COMPLETED
        )

        # If one server stops, stop the other
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Check if any task raised an exception
        for task in done:
            if task.exception():
                logger.error(f"❌ Server task failed with exception: {task.exception()}")
                raise task.exception()

    async def shutdown(self):
        """Gracefully shutdown both servers."""
        logger.info(f"🛑 Shutting down {settings.AGENT_NAME} Service...")

        # Shutdown HTTP server
        if self.http_server:
            logger.info("   Stopping HTTP server...")
            self.http_server.should_exit = True

        # Cancel gRPC task
        if self.grpc_task and not self.grpc_task.done():
            logger.info("   Stopping gRPC server...")
            self.grpc_task.cancel()
            try:
                await self.grpc_task
            except asyncio.CancelledError:
                pass

        logger.info(f"✅ {settings.AGENT_NAME} Service stopped")


def main():
    """Main entry point."""
    from agent.utils.logging import setup_logging
    
    # Setup logging at the very beginning
    setup_logging()
    
    service = ServiceMain()

    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, initiating shutdown...")
        asyncio.create_task(service.shutdown())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(service.run())
    except KeyboardInterrupt:
        logger.info("⛔ Service stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Service failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

