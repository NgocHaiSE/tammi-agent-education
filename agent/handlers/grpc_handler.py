from typing import Dict, Any
import time

from google.protobuf import struct_pb2
import grpc

from agent.config.settings import get_settings

# LangGraph imports
from agent.graph.graph_execution import (
    handle_request,
    handle_request_stream,
)
from agent.utils.request_converter import proto_to_request_dict
from agent.models import StreamError, GeneratorResponse

# Generated modules after compiling proto/agents.proto
from agent.proto import agents_pb2, agents_pb2_grpc
from agent.utils.logging import (
    get_logger, 
    log_request, 
    log_response, 
    log_stream_chunk
)
from agent.utils.performance import RequestTracer, trace_span

logger = get_logger(__name__)

# Cache settings at module level to avoid repeated calls
_settings = get_settings()


class AgentServiceHandler(agents_pb2_grpc.AgentServiceServicer):
    async def Chat(
        self, request: agents_pb2.AgentRequest, context
    ):
        """
        Unified chat handler supporting both streaming and non-streaming responses.
        
        Behavior is controlled by the `stream` field in AgentRequest:
        - stream=False: Yields a single response then closes
        - stream=True: Yields multiple responses as LLM generates content
        
        Args:
            request: AgentRequest protobuf message
            context: gRPC ServicerContext for managing RPC lifecycle
            
        Yields:
            AgentResponse protobuf messages
        """
        session_id = request.session_id
        request_id = request.request_id
        request_start = time.perf_counter()  # Track request start time for error logging
        
        # Create request tracer for detailed performance tracking
        tracer = RequestTracer(
            "grpc_chat_request",
            session_id=session_id,
            request_id=request_id,
            user_id=request.user_context.user_id if request.user_context.user_id else "unknown",
            intent=getattr(request.payload, "intent", ""),
            sub_intent=getattr(request.payload, "sub_intent", ""),
            is_streaming=request.stream,
            use_langgraph=_settings.USE_LANGGRAPH_AGENT
        )
        
        try:
            # Step 1: Basic validation on the raw proto
            with trace_span("input_validation"):
                if not session_id:
                    logger.error("Missing required field: session_id")
                    tracer.finalize(status="error", error="missing_session_id")
                    yield _create_error_response("", request_id, "Thiếu session_id", 400)
                    return

                if not request.payload or not request.payload.content:
                    logger.error("Missing payload content for session=%s", session_id)
                    tracer.finalize(status="error", error="missing_payload_content")
                    yield _create_error_response(session_id, request_id, "Thiếu nội dung yêu cầu", 400)
                    return

            # Step 2: Convert proto → validated dict for LangGraph execution
            with trace_span("proto_to_validated_dict"):
                try:
                    req_dict = proto_to_request_dict(request)
                except ValueError as err:
                    logger.error(
                        "Failed to validate AgentRequest session=%s request=%s: %s",
                        session_id,
                        request_id,
                        err,
                        exc_info=True,
                    )
                    tracer.finalize(status="error", error="invalid_request")
                    yield _create_error_response(session_id, request_id, "Dữ liệu yêu cầu không hợp lệ", 400)
                    return

            # Refresh identifiers from validated payload to avoid empty values
            session_id = req_dict.get("session_id") or session_id or "unknown"
            request_id = req_dict.get("request_id") or request_id or "unknown"
            user_id = (req_dict.get("user_context") or {}).get("user_id") or "unknown"

            # Log incoming gRPC request for observability
            log_request(
                logger,
                endpoint="grpc.Chat",
                session_id=session_id,
                request_id=request_id,
                user_id=user_id,
                intent=req_dict.get("payload", {}).get("intent", ""),
                sub_intent=req_dict.get("payload", {}).get("sub_intent", ""),
                stream=request.stream,
                content_length=len(req_dict.get("payload", {}).get("content", "")),
                history_length=len(req_dict.get("history", []))
            )

            logger.info(
                "Received Chat request session=%s request=%s intent=%s sub_intent=%s stream=%s",
                session_id,
                request_id,
                req_dict.get("payload", {}).get("intent", ""),
                req_dict.get("payload", {}).get("sub_intent", ""),
                request.stream,
            )

            if request.stream:
                # Streaming execution via LangGraph helper
                first_chunk_time = None
                chunks_sent = 0
                final_message_length = 0
                stream_start = time.perf_counter()

                async for chunk in handle_request_stream(req_dict):
                    # Handle error chunks gracefully
                    if isinstance(chunk, StreamError):
                        logger.error(
                            "Stream error session=%s request=%s: %s",
                            session_id,
                            request_id,
                            chunk.error,
                        )
                        tracer.finalize(status="error", error=chunk.error)
                        yield _create_error_response(session_id, request_id, chunk.error, 500)
                        return

                    if first_chunk_time is None:
                        first_chunk_time = time.perf_counter()

                    response_json = _build_stream_response_dict(chunk)
                    final_message_length = len(response_json["data"]["payload"]["parameters"]["display_message"])

                    chunks_sent += 1
                    if chunks_sent % 10 == 0:
                        log_stream_chunk(
                            logger,
                            chunk_num=chunks_sent,
                            chunk_size=len(response_json["data"]["payload"]["parameters"]["display_message"]),
                            total_chars=final_message_length,
                            session_id=session_id,
                            request_id=request_id,
                        )

                    yield _json_to_agent_response(response_json)

                if chunks_sent == 0:
                    logger.warning(
                        "Streaming produced no chunks for session=%s request=%s, falling back to non-stream response",
                        session_id,
                        request_id,
                    )
                    with trace_span("stream_fallback_handle_request"):
                        generator_response = await handle_request(req_dict)

                    fallback_json = _build_non_stream_response_dict(
                        generator_response,
                        session_id=session_id,
                        request_id=request_id,
                        user_context=req_dict.get("user_context"),
                    )

                    yield _json_to_agent_response(fallback_json)

                    response_length = len(
                        fallback_json["data"]["payload"]["parameters"]["display_message"]
                    )

                    log_response(
                        logger,
                        duration_ms=round((time.perf_counter() - stream_start) * 1000, 2),
                        endpoint="grpc.Chat",
                        session_id=session_id,
                        request_id=request_id,
                        status="success_fallback",
                        stream=True,
                        chunks_sent=0,
                        response_length=response_length,
                    )

                    tracer.add_metadata(
                        streaming_mode=True,
                        total_chunks=0,
                        total_chars=response_length,
                        fallback_used=True,
                    )

                    tracer.finalize(status="success")
                    return

                stream_duration_ms = (time.perf_counter() - stream_start) * 1000
                tracer.add_metadata(
                    streaming_mode=True,
                    total_chunks=chunks_sent,
                    total_chars=final_message_length,
                    stream_duration_ms=round(stream_duration_ms, 2),
                    ttfb_ms=round((first_chunk_time - stream_start) * 1000, 2) if first_chunk_time else 0,
                )

                log_response(
                    logger,
                    duration_ms=round(stream_duration_ms, 2),
                    endpoint="grpc.Chat",
                    session_id=session_id,
                    request_id=request_id,
                    status="success",
                    stream=True,
                    chunks_sent=chunks_sent,
                    response_length=final_message_length,
                    ttfb_ms=round((first_chunk_time - stream_start) * 1000, 2) if first_chunk_time else 0,
                )

                tracer.finalize(status="success")
                return

            #Non-streaming execution
            with trace_span("handle_request"):
                generator_response = await handle_request(req_dict)

            response_json = _build_non_stream_response_dict(
                generator_response,
                session_id=session_id,
                request_id=request_id,
                user_context=req_dict.get("user_context"),
            )

            response_length = len(response_json["data"]["payload"]["parameters"]["display_message"])

            tracer.add_metadata(
                streaming_mode=False,
                response_length=response_length,
                final_intent=response_json["data"]["payload"].get("intent", ""),
                final_sub_intent=response_json["data"]["payload"].get("sub_intent", ""),
            )

            log_response(
                logger,
                duration_ms=round((time.perf_counter() - request_start) * 1000, 2),
                endpoint="grpc.Chat",
                session_id=session_id,
                request_id=request_id,
                status="success",
                stream=False,
                response_length=response_length,
                response_preview=response_json["data"]["payload"]["parameters"]["display_message"][:200],
            )

            tracer.finalize(status="success")
            yield _json_to_agent_response(response_json)
            return

        except grpc.RpcError as e:
            # Re-raise gRPC errors (from abort() calls)
            error_duration = (time.perf_counter() - request_start) * 1000
            logger.error(
                "[RESPONSE] grpc.Chat | session_id=%s request_id=%s status=grpc_error duration_ms=%.2f error=%s",
                session_id,
                request_id,
                error_duration,
                str(e)
            )
            tracer.finalize(status="error", error="grpc_error")
            raise
        except Exception as e:
            # Catch-all for unexpected errors
            error_duration = (time.perf_counter() - request_start) * 1000
            logger.error(
                "Unexpected error in Chat handler session=%s: %s",
                session_id,
                str(e),
                exc_info=True,
            )
            
            # Log error response with duration
            log_response(
                logger,
                duration_ms=round(error_duration, 2),
                endpoint="grpc.Chat",
                session_id=session_id,
                request_id=request_id,
                status="error",
                error=str(e)[:200]  # Truncate long error messages
            )
            
            tracer.finalize(status="error", error=str(e))
            raise


def _build_non_stream_response_dict(
    generator_response: GeneratorResponse,
    *,
    session_id: str,
    request_id: str,
    user_context: Dict[str, Any] | None,
) -> Dict[str, Any]:
    # Build Parameters structure according to proto definition
    return {
        "status": {"code": 200, "message": "OK"},
        "session_id": session_id,
        "request_id": request_id,
        "user_context": _normalize_user_context(user_context),
        "data": generator_response.data.model_dump(),
    }


def _build_stream_response_dict(chunk: Any) -> Dict[str, Any]:
    payload = chunk.data.payload
    metadata = {}
    if getattr(chunk.data, "metadata", None):
        metadata = chunk.data.metadata.model_dump()
    metadata = metadata or {}
    metadata.update(
        {
            "service": _settings.agent_display_name,
            "session_id": chunk.session_id,
            "request_id": chunk.request_id,
            "is_partial": getattr(chunk, "is_partial", True),
        }
    )
    # Build Parameters structure according to proto definition
    parameters = {
        "display_message": payload.display_message or "",
        "tts_message": payload.tts_message or "",
        "ui_elements": [_ui_element_to_dict(ui) for ui in (payload.ui_elements or [])],
        "suggestions": list(payload.suggestions or []),
        "additional": payload.parameters.additional or {},
    }

    return {
        "status": chunk.status.model_dump(),
        # "session_id": chunk.session_id,
        # "request_id": chunk.request_id,
        # "user_context": _normalize_user_context(chunk.user_context.model_dump()),
        "data": {
            "payload": {
                "intent": payload.intent,
                "sub_intent": payload.sub_intent,
                "parameters": parameters,
            },
            "metadata": metadata,
        },
    }



def _ui_element_to_dict(ui: Any) -> Dict[str, Any]:
    ui_data = ui.model_dump() if hasattr(ui, "model_dump") else dict(ui or {})
    element_type = ui_data.pop("type", "")
    title = ui_data.pop("title", "")
    text = ui_data.pop("text", "")
    payload_data = ui_data.pop("data", {}) or {}
    if title:
        payload_data.setdefault("title", title)
    if text:
        payload_data.setdefault("text", text)
    return {
        "type": element_type,
        "data": payload_data,
    }


def _normalize_user_context(user_context: Dict[str, Any] | None) -> Dict[str, str]:
    ctx = user_context or {}
    return {
        "user_id": ctx.get("user_id") or "",
        "family_id": ctx.get("family_id") or "",
        "name": ctx.get("name") or "",
    }


def _struct_to_dict(st: struct_pb2.Struct) -> Dict[str, Any]:
    if not st:
        return {}
    return {k: v for k, v in st.items()}


def _dict_to_struct(d: Dict[str, Any]) -> struct_pb2.Struct:
    """Convert dict or Pydantic model to protobuf Struct."""
    s = struct_pb2.Struct()
    # Handle Pydantic models
    if hasattr(d, 'model_dump'):
        d = d.model_dump()
    elif hasattr(d, 'dict'):
        d = d.dict()
    s.update(d or {})
    return s


def _json_to_agent_response(data: Dict[str, Any]) -> agents_pb2.AgentResponse:
    """Convert internal JSON response format to AgentResponse protobuf."""
    status = data.get("status", {})
    user_context = data.get("user_context", {})
    payload = data.get("data", {}).get("payload", {})
    metadata = data.get("data", {}).get("metadata", {})

    # Extract parameters structure (already properly formatted)
    params_dict = payload.get("parameters", {})

    # Build Parameters protobuf message according to proto definition
    parameters = agents_pb2.Parameters(
        display_message=params_dict.get("display_message", ""),
        tts_message=params_dict.get("tts_message", ""),
        ui_elements=[
            agents_pb2.UIElement(
                type=el.get("type", ""),
                data=_dict_to_struct(el.get("data", {}))
            )
            for el in params_dict.get("ui_elements", [])
        ],
        suggestions=list(params_dict.get("suggestions", [])),
        additional=_dict_to_struct(params_dict.get("additional", {})),
    )

    return agents_pb2.AgentResponse(
        status=agents_pb2.Status(code=status.get("code", 200), message=status.get("message", "OK")),
        session_id=data.get("session_id", ""),
        request_id=data.get("request_id", ""),
        user_context=agents_pb2.UserContext(
            user_id=user_context.get("user_id", ""),
            family_id=user_context.get("family_id", ""),
            name=user_context.get("name", ""),
        ),
        data=agents_pb2.Data(
            payload=agents_pb2.DataPayload(
                intent=payload.get("intent", ""),
                sub_intent=payload.get("sub_intent", ""),
                parameters=parameters,
            ),
            metadata=_dict_to_struct(metadata),
        ),
    )


def _create_error_response(
    session_id: str,
    request_id: str,
    error_message: str,
    status_code: int = 500,
) -> agents_pb2.AgentResponse:
    """
    Create a standardized error response for gRPC clients.
    
    Args:
        session_id: Session identifier
        request_id: Request identifier
        error_message: Human-readable error description
        status_code: HTTP-style status code (default 500)
        
    Returns:
        AgentResponse with error status and message
    """
    parameters = agents_pb2.Parameters(
        display_message=error_message,
        tts_message=error_message,
        ui_elements=[],
        suggestions=[],
        additional=_dict_to_struct({}),
    )
    
    return agents_pb2.AgentResponse(
        status=agents_pb2.Status(
            code=status_code,
            message=error_message,
        ),
        session_id=session_id,
        request_id=request_id,
        user_context=agents_pb2.UserContext(
            user_id="",
            family_id="",
            name="",
        ),
        data=agents_pb2.Data(
            payload=agents_pb2.DataPayload(
                intent="ERROR",
                sub_intent="PROCESSING_ERROR",
                parameters=parameters,
            ),
            metadata=_dict_to_struct({
                "error": True,
                "error_code": status_code,
                "service": _settings.agent_display_name,
            }),
        ),
    )
