"""FastAPI HTTP Application - Education Agent

Provides HTTP endpoints for agent services (Intent Routing, QA, Education)
and health monitoring.
"""

from __future__ import annotations

# Load environment configuration EARLY, before any other imports
from agent.config.env_manager import EnvManager

env_manager = EnvManager()
env_manager.load_environment()

# OPTIMIZATION: Install uvloop for 2-4x faster async performance
try:
    import uvloop
    uvloop.install()
    print("[OK] uvloop installed - Using high-performance event loop")
except ImportError:
    print("[WARN] uvloop not available - Using default asyncio event loop")

import time
import os
from typing import Any, Dict, AsyncGenerator
from contextlib import asynccontextmanager
import json
from agent.utils.logging import (
    get_logger, log_request, log_response, log_stream_chunk
)
from agent.utils.performance import RequestTracer

from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse

from agent.graph import graph_execution
from agent.utils.request_converter import dict_to_request_schema
from agent.config.settings import get_settings
from agent.models import StreamError

settings = get_settings()

# Don't setup logging at module level - let run.py handle it
# setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for application startup and shutdown.

    Startup: Initialize services eagerly (IntentRouter, etc.)
    Shutdown: Cleanup resources
    """
    # Startup
    from agent.entrypoint.startup_services import initialize_all_services, cleanup_services

    logger.info("=" * 70)
    logger.info("HTTP Server: Starting service initialization...")
    logger.info("=" * 70)

    await initialize_all_services()

    logger.info("=" * 70)
    logger.info("HTTP Server: Ready to accept requests")
    logger.info("=" * 70)

    yield  # Application runs here

    # Shutdown
    logger.info("HTTP Server: Shutting down...")
    await cleanup_services()
    logger.info("HTTP Server: Shutdown complete")


app = FastAPI(lifespan=lifespan)
logger = get_logger(f"{settings.AGENT_NAME}_HTTP")


@app.get("/management/health")
async def health() -> Dict[str, Any]:
    """Health check endpoint - returns basic status"""
    import uuid
    timestamp = int(time.time())
    app_name = os.environ.get("APPLICATION_NAME", "Education_Agent")

    logger.debug(f"Health check: {app_name}")

    return {
        "status": "ok",
        "application": app_name,
        "timestamp": timestamp,
        "message": f"Application Name: {app_name} is up and running",
        "request_id": str(uuid.uuid4())
    }

@app.post("/api/v1/chat")
async def chat(request: Request) -> Response:
    """Accept JSON matching AgentRequest proto. If `stream` is true, return a StreamingResponse
    that yields JSON chunks. Otherwise return full JSON response."""
    
    start_time = time.time()
    payload = await request.body()
    
    # Parse and validate request
    try:
        request_json = json.loads(payload.decode("utf-8"))
        validated_schema = dict_to_request_schema(request_json)
        req_dict = validated_schema.to_dict()
        
    except ValueError as e:
        logger.exception("Failed to validate request: %s", e)
        return JSONResponse(status_code=400, content={"error": f"invalid request format: {str(e)}"})
    except Exception as e:
        logger.exception("Failed to parse request JSON: %s", e)
        return JSONResponse(status_code=400, content={"error": "invalid request format"})
    
    # Extract metadata from request
    session_id = req_dict.get("session_id", "unknown")
    request_id = req_dict.get("request_id", "unknown")
    user_id = req_dict.get("user_context", {}).get("user_id", "unknown")
    payload_data = req_dict.get("payload", {})
    intent = payload_data.get("intent", "")
    sub_intent = payload_data.get("sub_intent", "")
    is_streaming = req_dict.get("stream", False)
    
    # Log incoming request
    log_request(
        logger,
        endpoint="/api/v1/chat",
        session_id=session_id,
        request_id=request_id,
        user_id=user_id,
        intent=intent,
        sub_intent=sub_intent,
        stream=is_streaming,
        content_length=len(payload_data.get("content", "")),
        history_length=len(req_dict.get("history", []))
    )
    
    # Create request tracer
    tracer = RequestTracer(
        "http_chat_request",
        session_id=session_id,
        request_id=request_id,
        user_id=user_id,
        intent=intent,
        sub_intent=sub_intent,
        is_streaming=is_streaming,
        use_langgraph=settings.USE_LANGGRAPH_AGENT,
        payload_size_bytes=len(payload)
    )
    
    try:
        logger.info(
            f"HTTP processing request: session={session_id} "
            f"intent={intent} stream={is_streaming}"
        )
        
        # Handle streaming vs non-streaming
        if is_streaming:
            # Streaming response using SSE
            async def stream_generator() -> AsyncGenerator[str, None]:
                """Stream response chunks with detailed tracing"""
                try:
                    accumulated_text = ""
                    chunks_sent = 0
                    first_chunk_time = None

                    logger.info("[STREAM] Starting SSE stream...")

                    # Stream chunks from graph_execution
                    async for chunk_response in graph_execution.handle_request_stream(req_dict):
                        if isinstance(chunk_response, StreamError):
                            logger.error(
                                "[STREAM] Error chunk received: %s",
                                chunk_response.error,
                            )

                            error_payload = chunk_response.model_dump()
                            yield f"data: {json.dumps(error_payload)}\n\n"
                            yield "data: [DONE]\n\n"

                            duration_ms = (time.time() - start_time) * 1000
                            log_response(
                                logger,
                                duration_ms=duration_ms,
                                endpoint="/api/v1/chat",
                                session_id=session_id,
                                request_id=request_id,
                                status="error",
                                error=chunk_response.error,
                                stream=True,
                                chunks_sent=chunks_sent,
                            )

                            tracer.finalize(status="error", error=chunk_response.error)
                            return

                        chunks_sent += 1

                        if first_chunk_time is None:
                            first_chunk_time = time.perf_counter()

                        payload = chunk_response.data.payload
                        text = payload.display_message or ""

                        accumulated_text = text

                        # Log every 10th chunk
                        if chunks_sent % 10 == 0:
                            log_stream_chunk(
                                logger,
                                chunk_num=chunks_sent,
                                chunk_size=len(text),
                                total_chars=len(accumulated_text)
                            )

                        # Convert to JSON for SSE
                        response_dict = chunk_response.model_dump()
                        yield f"data: {json.dumps(response_dict)}\n\n"

                    # Send completion signal
                    yield "data: [DONE]\n\n"

                    # Log streaming response completion
                    duration_ms = (time.time() - start_time) * 1000
                    log_response(
                        logger,
                        duration_ms=duration_ms,
                        endpoint="/api/v1/chat",
                        session_id=session_id,
                        request_id=request_id,
                        response_length=len(accumulated_text),
                        status="success",
                        stream=True,
                        chunks_sent=chunks_sent,
                        response_preview=accumulated_text[:200] if accumulated_text else ""
                    )

                    tracer.add_metadata(
                        streaming_chunks=chunks_sent,
                        streaming_chars=len(accumulated_text),
                        ttfb_ms=round((first_chunk_time - start_time) * 1000, 2) if first_chunk_time else 0
                    )
                    tracer.finalize(status="success")

                except Exception as e:
                    logger.error(f"[STREAM] Error: {e}", exc_info=True)
                    error_response = {
                        "error": str(e),
                        "status": {"code": 500, "message": "Internal error"}
                    }
                    yield f"data: {json.dumps(error_response)}\n\n"
                    yield "data: [DONE]\n\n"

                    duration_ms = (time.time() - start_time) * 1000
                    log_response(
                        logger,
                        duration_ms=duration_ms,
                        endpoint="/api/v1/chat",
                        session_id=session_id,
                        request_id=request_id,
                        status="error",
                        error=str(e)
                    )
                    tracer.finalize(status="error", error=str(e))

            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
            )
        else:
            # Non-streaming invocation
            response = await graph_execution.handle_request(req_dict)
            
            # Calculate and log response timing
            duration_ms = (time.time() - start_time) * 1000

            # Extract message/intent safely for both AgentResponse and GeneratorResponse
            payload = getattr(response, "data", None)
            payload = getattr(payload, "payload", None) if payload else None
            params = getattr(payload, "parameters", None) if payload else None

            response_message = getattr(params, "display_message", "") or ""
            final_intent = getattr(payload, "intent", "") or ""
            final_sub_intent = getattr(payload, "sub_intent", "") or ""

            log_response(
                logger,
                duration_ms=duration_ms,
                endpoint="/api/v1/chat",
                session_id=session_id,
                request_id=request_id,
                response_length=len(response_message),
                final_intent=final_intent,
                final_sub_intent=final_sub_intent,
                status="success",
                stream=False,
                response_preview=response_message[:200] if response_message else ""
            )

            tracer.add_metadata(
                response_length=len(response_message),
                final_intent=final_intent,
                final_sub_intent=final_sub_intent
            )

            tracer.finalize(status="success")
            return JSONResponse(content=response.model_dump())
            
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"[ERROR] Request failed after {duration_ms:.2f}ms: {e}", exc_info=True)
        
        log_response(
            logger,
            duration_ms=duration_ms,
            endpoint="/api/v1/chat",
            session_id=session_id,
            request_id=request_id,
            status="error",
            error=str(e)
        )
        
        tracer.finalize(status="error", error=str(e))
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "status": {"code": 500, "message": "Internal error"}
            }
        )


if __name__ == "__main__":
    import uvicorn
    import os
    
    # Read configuration from environment variables (consistent with Dockerfile)
    http_host = os.getenv("AGENT_HTTP_HOST", "0.0.0.0")
    http_port = int(os.getenv("AGENT_HTTP_PORT", "8080"))
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    logger.info(
        "Starting HTTP server in standalone mode",
        extra={"extra_fields": {
            "host": http_host,
            "port": http_port,
            "log_level": log_level,
            "mode": "standalone"
        }}
    )
    
    # Run uvicorn server
    # Use string import format for hot-reload support in development
    uvicorn.run(
        "agent.entrypoint.http_server:app",
        host=http_host,
        port=http_port,
        log_level=log_level,
        access_log=True,
    )
