"""Handler for responses from agent graph."""

import logging
import time
from typing import Any, AsyncGenerator, Dict, Optional, Tuple, List

import asyncio
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from agent.graph.config.response_config import get_response
from agent.graph.graph_builder import build_agent_graph
from agent.graph.graph_state import GraphState
from agent.graph.constants import SubIntents, CheckpointPatterns, NodeNames
from agent.intent_router.intent_routing import get_intent_router
from agent.models import DataPayload, Parameters, StreamChunkResponse, GeneratorResponse, Status, ResponseMetadata, \
    ResponseData, UserContext

logger = logging.getLogger(__name__)


class GraphHandler:
    """
    Handler for responses from agent graph.
    
    Generic handler that can work with any agent type.
    Similar to old code's ResponseService.build_streaming_response,
    this class manages streaming token-by-token responses.
    """

    def __init__(self, trace_id: Optional[str] = None, agent_name: Optional[str] = None, version: str = "v1"):
        from agent.config.settings import get_settings
        settings = get_settings()
        
        self.agent_name = agent_name or settings.AGENT_NAME
        self.trace_id = trace_id or f"{self.agent_name}-{int(time.time() * 1000)}"
        # Use cached graph - version is the cache key
        self.graph = build_agent_graph(version=version)
        logger.debug(f"GraphHandler initialized with cached graph (version={version})")

    def build_graph_config(self, request: Dict[str, Any]):
        return {
                    "configurable": {
                        "thread_id": request.get("session_id") or self.trace_id,
                        "user_id": request.get("user_context", {}).get("user_id"),
                        "family_id": request.get("family_id", {}).get("family_id"),
                        "trace_id": request.get("session_id") or self.trace_id,
                    }
                }

    async def stream_response(
        self,
        request: Dict[str, Any]
    ) -> AsyncGenerator[StreamChunkResponse, None]:
        """
        Generate streaming response from the graph.
        
        Yields text chunks as they are generated, similar to old code's
        graph.astream() with stream_mode="messages".
        
        Args:
            user_input: User's message
            session_id: Session identifier
            request_id: Request identifier
            chat_history: Previous conversation messages
            
        Yields:
            Text chunks as they are generated
        """
        stream_start_time = time.time()
        chunks_sent = 0
        intent = request["payload"]["intent"]
        sub_intent = request["payload"]["sub_intent"]
        user_input = request["payload"]["content"]
        
        logger.info(
            f"Starting streaming response for trace_id={self.trace_id}",
            extra={
                "event": "stream_started",
                "trace_id": self.trace_id,
                "session_id": request.get("session_id"),
            }
        )
        
        try:
            # Resolve sub_intent using IntentRouter
            if sub_intent not in ["search_material", "create_exercise", "correct_exercise",
                                  "tutor_subject"]:
                intent_router = get_intent_router()
                sub_intent = await intent_router.route_intent(user_input)

            logger.info(f"Resolved sub_intent for streaming: {sub_intent}")

            # Map sub_intent to intent
            if sub_intent in ["search_material", "create_exercise"]:
                intent = "learning_resource"
            elif sub_intent in ["correct_exercise",
                                "tutor_subject"]:
                intent = "study_guidance"
            # Convert history to messages dict format (matching GraphState)
            history_chat = self._convert_history_to_messages(request.get("history", []))
            
            # Build initial state matching GraphState structure
            init_state: GraphState = {
                "request": request,
                "history_chat": history_chat,
                "node_responses": [],
            }
            
            # Stream from graph using stream_mode="messages" for token-by-token streaming
            accumulated_display = ""
            accumulated_tts = ""
            display_chunks_count = 0
            tts_chunks_count = 0
            
            logger.info("Starting parallel stream tracking for display + tts messages")
            
            async for event in self.graph.astream(
                init_state,
                stream_mode=["messages", "updates", "values"],
                config=self.build_graph_config(request),
                debug=False,
                subgraphs=True,
            ):
                if not isinstance(event, tuple) or len(event) != 3:
                    continue

                namespace_info, stream_mode, data = event

                # data is a tuple: (step, metadata)
                if not isinstance(data, tuple) or len(data) != 2:
                    continue

                # Handle message streaming (LLM tokens)
                if stream_mode != "messages":
                    continue
                step, metadata = data

                # Extract checkpoint namespace and node name
                checkpoint_ns: str = metadata.get("langgraph_checkpoint_ns", "")
                node_name: str = metadata.get("langgraph_node", "")

                # Check if this is from a handler subgraph's agent node
                # Pattern: "invoke_handler:...call_llm:...agent:..."
                # We want messages from "agent" node inside handler subgraphs only
                is_tts_msg = (
                        node_name == NodeNames.TTS_MSG or
                        node_name == NodeNames.CALL_LLM or
                        node_name == NodeNames.AGENT
                )
                is_display_msg: bool = (
                        # CheckpointPatterns.INVOKE_HANDLER in checkpoint_ns and  # Inside handler invocation
                        CheckpointPatterns.CALL_LLM in checkpoint_ns and  # Inside call_llm subgraph
                        (node_name == NodeNames.CALL_LLM or node_name == NodeNames.AGENT)
                    # From the ReAct agent node
                ) or node_name == NodeNames.DISPLAY_MSG
                has_content = hasattr(step, 'content') and step.content
                # print(checkpoint_ns, node_name, is_display_msg, is_tts_msg, step)
                if has_content and is_display_msg:
                    text: str = step.content
                    if text:
                        display_chunks_count += 1
                        accumulated_display += text
                        chunks_sent += 1

                        logger.info(
                            f"ðŸ“º DISPLAY chunk #{display_chunks_count}: '{text[:50]}...' ({len(text)} chars) | "
                            f"Total accumulated: {len(accumulated_display)} chars",
                            extra={
                                "event": "stream_display_chunk",
                                "trace_id": self.trace_id,
                                "chunk_number": display_chunks_count,
                                "chunk_size": len(text),
                                "total_accumulated": len(accumulated_display),
                                "node_name": node_name,
                                "checkpoint_ns": checkpoint_ns,
                            }
                        )

                        yield StreamChunkResponse(
                            status=Status(code=200, message="OK"),
                            data=ResponseData(
                                payload=DataPayload(
                                    intent=intent,
                                    sub_intent=sub_intent,
                                    parameters=Parameters(
                                        display_message=text,
                                    ),
                                ),
                                metadata=ResponseMetadata(
                                    service=self.agent_name,
                                )
                            ),
                            is_partial=True,  # Indicates this is still streaming
                        )

                if has_content and is_tts_msg:
                    text: str = step.content
                    if text:
                        tts_chunks_count += 1
                        accumulated_tts += text
                        chunks_sent += 1
                        
                        logger.info(
                            f"ðŸ”Š TTS chunk #{tts_chunks_count}: '{text[:50]}...' ({len(text)} chars) | "
                            f"Total accumulated: {len(accumulated_tts)} chars",
                            extra={
                                "event": "stream_tts_chunk",
                                "trace_id": self.trace_id,
                                "chunk_number": tts_chunks_count,
                                "chunk_size": len(text),
                                "total_accumulated": len(accumulated_tts),
                                "node_name": node_name,
                                "checkpoint_ns": checkpoint_ns,
                            }
                        )
                        
                        yield StreamChunkResponse(
                            status=Status(code=200, message="OK"),
                            data=ResponseData(
                                payload=DataPayload(
                                    intent=intent,
                                    sub_intent=sub_intent,
                                    parameters=Parameters(
                                        tts_message=text,
                                        # ui_elements=ui_elements,
                                        # suggestions=suggestions,
                                        # additional=additional_params,  # Empty dict for streaming
                                    ),
                                ),
                                metadata=ResponseMetadata(
                                    service=self.agent_name,
                                )
                            ),
                            is_partial=True,  # Indicates this is still streaming
                        )

            # Log completion with detailed summary
            duration = time.time() - stream_start_time
            logger.info(
                f"âœ… Streaming completed in {duration:.3f}s:\n"
                f"  ðŸ“º DISPLAY: {display_chunks_count} chunks, {len(accumulated_display)} chars total\n"
                f"     Final text: '{accumulated_display[:100]}...'\n"
                f"  ðŸ”Š TTS: {tts_chunks_count} chunks, {len(accumulated_tts)} chars total\n"
                f"     Final text: '{accumulated_tts[:100]}...'\n"
                f"  ðŸ“Š Total: {chunks_sent} chunks sent",
                extra={
                    "event": "stream_completed",
                    "trace_id": self.trace_id,
                    "duration_sec": duration,
                    "display_chunks": display_chunks_count,
                    "display_chars": len(accumulated_display),
                    "tts_chunks": tts_chunks_count,
                    "tts_chars": len(accumulated_tts),
                    "total_chunks_sent": chunks_sent,
                }
            )
            
        except Exception as e:
            logger.error(
                f"Streaming error: {e}",
                extra={
                    "event": "stream_error",
                    "trace_id": self.trace_id,
                    "error": str(e),
                },
                exc_info=True
            )
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
                        service=self.agent_name,
                    )
                ),
                is_partial=True,  # Indicates this is still streaming
            )

    async def invoke_response(
        self,
        request: Dict[str, Any],
        timeout: int = 50,
    ) -> GeneratorResponse:
        """
        Generate non-streaming (full) response.
        
        Args:
            request: Request dictionary with payload and metadata
            timeout: Maximum execution time in seconds
            
        Returns:
            Complete response text
        """
        intent = request["payload"]["intent"]
        sub_intent = request["payload"]["sub_intent"]
        user_input = request["payload"]["content"]

        logger.info(
            f"Invoking non-streaming response for trace_id={self.trace_id}",
            extra={
                "event": "invoke_started",
                "trace_id": self.trace_id,
                "session_id": request.get("session_id"),
            }
        )
        
        start_time = time.time()
        result = None  # Initialize to avoid NameError in exception handlers

        try:
            # Resolve sub_intent using IntentRouter
            if sub_intent not in ["search_material", "create_exercise", "correct_exercise",
                                  "tutor_subject"]:
                intent_router = get_intent_router()
                sub_intent = await intent_router.route_intent(user_input)

            logger.info(f"Resolved sub_intent for streaming: {sub_intent}")

            # Map sub_intent to intent
            if sub_intent in ["search_material", "create_exercise"]:
                intent = "learning_resource"
            elif sub_intent in ["correct_exercise",
                                  "tutor_subject"]:
                intent = "study_guidance"

            history_chat = self._convert_history_to_messages(request.get("history", []))
            # Build initial state
            init_state: GraphState = {
                "request": request,
                "history_chat": history_chat,
                "node_responses": []
            }
            
            # Invoke graph (non-streaming)
            result = await asyncio.wait_for(
                self.graph.ainvoke(
                    init_state,
                    config=self.build_graph_config(request)
                ),
                timeout=timeout
            )

            logger.info(f"all result from graph {result}")

            # Get node_responses with fallback
            node_responses_list = result.get("node_responses", [])
            
            # Safety check: ensure we have at least one response
            if not node_responses_list:
                logger.warning("No node_responses in result, using default error message")
                node_responses_list = [
                    AIMessage(
                        content=get_response("general_error"),
                        additional_kwargs={
                            "tts_message": get_response("general_error")
                        }
                    )
                ]
            
            response = node_responses_list[-1]

            # logger.info(f"all result from graph {response}")

            # Extract response from node_responses (primary source)
            display_message = response.content or "Xin lỗi, tôi không thể tạo phản hồi vào lúc này."
            # Fallback to display_message so TTS is never empty even if node did not set tts_message
            tts_message = response.additional_kwargs.get("tts_message") or display_message

            duration = time.time() - start_time
            logger.info(
                f"Non-streaming invoke completed in {duration:.3f}s:\n"
                f"   DISPLAY: {len(display_message)} chars\n"
                f"     Preview: '{display_message[:100]}...'\n"
                f"   TTS: {len(tts_message)} chars\n"
                f"     Preview: '{tts_message[:100]}...'",
                extra={
                    "event": "invoke_completed",
                    "trace_id": self.trace_id,
                    "duration_sec": duration,
                    "display_length": len(display_message),
                    "tts_length": len(tts_message),
                }
            )

            # Return response_text, sub_intent, and full result (for extracting weather_data, etc.)
            sub_intent = result.get("request", {}).get("payload", {}).get("sub_intent", SubIntents.TUTOR_SUBJECT) if isinstance(request, dict) else ""
            return GeneratorResponse(
                status=Status(code=200, message="ok"),
                data=ResponseData(
                    payload=DataPayload(
                        intent=intent,
                        sub_intent=sub_intent,
                        parameters=Parameters(
                            display_message=display_message,
                            tts_message=tts_message,
                        ),
                    ),
                    metadata=ResponseMetadata(
                        service=self.agent_name,
                    )
                ),
            )

        except asyncio.TimeoutError as e:
            logger.error(
                f"Invoke timed out after {timeout}s",
                extra={
                    "event": "invoke_timeout",
                    "trace_id": self.trace_id,
                    "timeout_sec": timeout,
                }
            )
            # Extract sub_intent from original request since result is not available after timeout
            sub_intent = request.get("payload", {}).get("sub_intent", SubIntents.HEALTH_ADVICE)
            return GeneratorResponse(
                status=Status(code=500, message=f"error: {e}"),
                data=ResponseData(
                    payload=DataPayload(
                        intent=intent,
                        sub_intent=sub_intent,
                        parameters=Parameters(
                            display_message="Xin lỗi, quá trình xử lý yêu cầu đã hết thời gian chờ. Vui lòng thử lại.",
                            tts_message="Xin lỗi, quá trình xử lý yêu cầu đã hết thời gian chờ. Vui lòng thử lại.",
                        ),
                    ),
                    metadata=ResponseMetadata(
                        service=self.agent_name,
                    )
                ),
            )

        except Exception as e:
            logger.error(
                f"Invoke error: {e}",
                extra={
                    "event": "invoke_error",
                    "trace_id": self.trace_id,
                    "error": str(e),
                },
                exc_info=True
            )
            # Extract sub_intent from original request since result may not be available
            sub_intent = request.get("payload", {}).get("sub_intent", "health_advice")
            return GeneratorResponse(
                status=Status(code=500, message=f"error: {e}"),
                data=ResponseData(
                    payload=DataPayload(
                        intent=intent,
                        sub_intent=sub_intent,
                        parameters=Parameters(
                            display_message="Xin lỗi, quá trình xử lý yêu cầu đã hết thời gian chờ. Vui lòng thử lại.",
                            tts_message="Xin lỗi, quá trình xử lý yêu cầu đã hết thời gian chờ. Vui lòng thử lại.",
                        ),
                    ),
                    metadata=ResponseMetadata(
                        service=self.agent_name,
                    )
                ),
            )

    def _convert_history_to_messages(self, history: list) -> List[BaseMessage]:
        """
        Convert request history into an ordered list of LangChain messages.
        
        LangGraph's add_messages reducer expects a list of BaseMessage objects,
        so avoid returning a dict (which would create {} entries and break
        message coercion).
        """
        messages: List[BaseMessage] = []
        for msg in history:
            role = msg.get("role")
            content = msg.get("content")

            if not role or content is None:
                continue

            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

        return messages


