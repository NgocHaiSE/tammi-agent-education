# New orchestrator using LangGraph architecture
# Routes to graph-based agent with streaming support
from typing import Any, Dict, AsyncIterator
import logging

from agent.graph.graph_handler import GraphHandler
from agent.graph.constants import SubIntents
from agent.models import GeneratorResponse, StreamChunkResponse, StreamError, Status, ResponseData, DataPayload, \
    Parameters, ResponseMetadata
from agent.config.settings import get_settings
from agent.config.suggestions import get_suggestions
from agent.intent_router.intent_routing import get_intent_router

logger = logging.getLogger(__name__)


def _request_verifing(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare and normalize request data for processing.
    
    Extracts and validates:
    - Basic identifiers (session_id, request_id)
    - Intent and sub_intent with routing logic
    - User input with location enhancement
    
    Args:
        request: Raw request dictionary
        
    Returns:
        Prepared request dictionary with:
        - session_id, request_id
        - intent, sub_intent (normalized)
        - user_input (enhanced with location if needed)
        - user_context
    """
    settings = get_settings()
    
    # Extract identifiers
    session_id = request.get("session_id")
    request_id = request.get("request_id")
    
    # Extract and normalize intent
    raw_sub_intent = request.get("payload", {}).get("sub_intent")
    
    # Treat generic "medical" or empty string as None for routing
    if not raw_sub_intent or raw_sub_intent.lower() in ["medical", settings.AGENT_NAME.lower()]:
        sub_intent = None  # Will be determined by IntentRouter
        logger.info("Generic or empty sub_intent received, will use IntentRouter for dynamic routing")
    else:
        sub_intent = raw_sub_intent
    
    intent = request.get("payload", {}).get("intent") or "medical"

    # Extract location for enhancement
    user_context = request.get("user_context") or {}
    location = user_context.get("city") or request.get("payload", {}).get("metadata", {}).get("city")
    
    # Pass location via metadata instead of mutating user input
    if sub_intent in ["health_advice", "diet_recommendation", "exercise_recommendation",
                      "book_appointment", "purchase_medicine", "health_record"]:
        if not location:
            location = "Hanoi"  # Default location

        # Store location in metadata for nodes to use
        if "metadata" not in request["payload"]:
            request["payload"]["metadata"] = {}
        request["payload"]["metadata"]["location"] = location

        logger.info(f"{sub_intent} request with location: {location}")
        
    history = request.get("history", [])
    
    request["history"] = history
    request["session_id"] = session_id
    request["request_id"] = request_id
    request["payload"]["intent"] = intent
    request["payload"]["sub_intent"] = sub_intent
    # Don't mutate user_input - keep original content
    request["user_context"] = user_context
    
    return request

async def handle_request(request: Dict[str, Any]) -> GeneratorResponse:
    """
    Main entry for agent logic using LangGraph.

    Uses graph-based architecture with create_react_agent for handling requests.
    Supports external API calls via tools.
    
    ✅ ASYNC - No event loop creation needed, direct await
    ✅ Returns Pydantic model for type safety
    ✅ Modular design: _prepare_request → _build_response
    ✅ Orchestrates full request processing pipeline
    """
    settings = get_settings()
    
    try:
        # Step 1: Prepare request data
        request = _request_verifing(request)
        session_id = request["session_id"]
        request_id = request["request_id"]
        
        logger.info(
            "%s generator handling request: session=%s request=%s sub_intent=%s",
            settings.agent_display_name,
            session_id,
            request_id,
            request["payload"]["sub_intent"],
        )

        # Create streaming handler for LLM response (invoke_response for non-streaming)
        graph_handler = GraphHandler(trace_id=request_id)

        # Step 2: Build response (includes routing, handler invocation, LLM calls)
        return await graph_handler.invoke_response(
            request=request,
            timeout=120,  # Increased timeout for local LLM models (Ollama)
        )
    except Exception as e:
        logger.exception("Error while handling agent request: %s", str(e))
        payload = request.get("payload", {}) if isinstance(request, dict) else {}
        intent = payload.get("intent") or "EDUCATION"
        sub_intent = payload.get("sub_intent") or SubIntents.SEARCH_MATERIAL
        return GeneratorResponse(
                status=Status(code=500, message=f"error {e}"),
                data=ResponseData(
                    payload=DataPayload(
                        intent=intent,
                        sub_intent=sub_intent,
                        parameters=Parameters(
                            display_message="Có lỗi xảy ra, vui lòng thử lại sau",
                            tts_message="Có lỗi xảy ra, vui lòng thử lại sau",
                        ),
                    ),
                    metadata=ResponseMetadata(
                        service=settings.agent_display_name,
                    )
                ),
            )


async def handle_request_stream(request: Dict[str, Any]) -> AsyncIterator[StreamChunkResponse]:
    """
    Server-side streaming generator using LangGraph's astream with stream_mode="messages".

    Yields StreamChunkResponse with SAME structure as non-streaming response.
    Only difference: display_message builds incrementally chunk by chunk.
    
    ✅ ASYNC - Direct async generator with token-by-token streaming
    ✅ Returns full response structure for consistency
    ✅ Fetches context data (ui_elements) without double LLM calls
    ✅ Modular design with _prepare_request → _build_stream_response
    """
    settings = get_settings()
    
    try:
        # Step 1: Prepare request data
        request = _request_verifing(request)
        session_id = request["session_id"]
        request_id = request["request_id"]
        
        logger.info(
            "%s generator streaming request: session=%s request=%s sub_intent=%s",
            settings.agent_display_name,
            session_id,
            request_id,
            request["payload"]["sub_intent"],
        )
        # Step 2: Build streaming response (includes routing, context fetching, token streaming)
        async for chunk in GraphHandler(trace_id=request_id).stream_response(
                request=request,
        ):
            yield chunk

    except Exception as e:
        logger.exception("Error during streaming agent request: %s", str(e))
        payload = request.get("payload", {}) if isinstance(request, dict) else {}
        intent = payload.get("intent") or "EDUCATION"
        sub_intent = payload.get("sub_intent") or SubIntents.SEARCH_MATERIAL
        yield StreamChunkResponse(
                status=Status(code=500, message=f"error: {e}"),
                data=ResponseData(
                    payload=DataPayload(
                        intent=intent,
                        sub_intent=sub_intent,
                        parameters=Parameters(
                            display_message="Xin lỗi, đã xảy ra lỗi trong quá trình xử lý yêu cầu của bạn.",
                            tts_message="Xin lỗi, đã xảy ra lỗi trong quá trình xử lý yêu cầu của bạn.",
                            # ui_elements=ui_elements,
                            # suggestions=suggestions,
                            # additional=additional_params,  # Empty dict for streaming
                        ),
                    ),
                    metadata=ResponseMetadata(
                        service=settings.agent_display_name,
                    )
                ),
                is_partial=True,  # Indicates this is still streaming
            )
