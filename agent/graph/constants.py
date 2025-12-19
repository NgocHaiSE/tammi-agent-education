"""
Graph Constants

Centralized constants for graph components to avoid string duplication
and improve maintainability.
"""

# ============================================================================
# Node Names
# ============================================================================

class NodeNames:
    """Graph node names"""
    SUB_INTENT_CLASSIFICATION = "sub_intent_classification"
    SEARCH_MATERIAL = "search_material"
    CREATE_EXERCISE = "create_exercise"
    CORRECT_EXERCISE = "correct_exercise"
    TUTOR_SUBJECT = "tutor_subject"
    TTS_MSG = "tts_msg"
    DISPLAY_MSG = "display_msg"
    CALL_LLM = "call_llm"
    AGENT = "agent"


# ============================================================================
# Handler Types
# ============================================================================

class HandlerTypes:
    """Handler type identifiers"""
    GUIDANCE = "guidance"
    SERVICE = "service"


# ============================================================================
# Intents & Sub-Intents
# ============================================================================

class Intents:
    """Intent constants"""
    AGENT = "AGENT"
    LEARNING_RESOURCE = "learning_resource"
    STUDY_GUIDANCE = "study_guidance"
    EDUCATION = "EDUCATION"


class SubIntents:
    """Sub-intent constants"""
    SEARCH_MATERIAL = "search_material"
    CREATE_EXERCISE = "create_exercise"
    CORRECT_EXERCISE = "correct_exercise"
    TUTOR_SUBJECT = "tutor_subject"
    HEALTH_ADVICE = "health_advice"


# ============================================================================
# Error Messages (Vietnamese)
# ============================================================================

class ErrorMessages:
    """Error messages for user-facing responses"""
    GENERIC_ERROR = "Xin lỗi, đã có lỗi xảy ra khi xử lý yêu cầu."
    GENERIC_ERROR_TTS = "Xin lỗi, đã có lỗi xảy ra."

    HANDLER_NOT_FOUND = "Xin lỗi, tôi không thể xử lý yêu cầu này."
    HANDLER_NOT_FOUND_TTS = "Xin lỗi, tôi không thể xử lý yêu cầu này."

    FALLBACK_ERROR = "Xin lỗi, tôi đang gặp khó khăn. Vui lòng thử lại sau."
    FALLBACK_ERROR_TTS = "Xin lỗi, tôi đang gặp khó khăn."

    EMPTY_CONTENT = "Xin lỗi, tôi không nhận được nội dung từ bạn."
    EMPTY_CONTENT_TTS = "Xin lỗi, tôi không nhận được nội dung."

    MISSING_SESSION = "Xin lỗi, phiên làm việc không hợp lệ."
    MISSING_SESSION_TTS = "Xin lỗi, phiên làm việc không hợp lệ."

    INVALID_INPUT = "Xin lỗi, thông tin đầu vào không hợp lệ."
    INVALID_INPUT_TTS = "Xin lỗi, thông tin không hợp lệ."


# ============================================================================
# Status Codes
# ============================================================================

class StatusCodes:
    """HTTP-like status codes"""
    OK = 200
    BAD_REQUEST = 400
    INTERNAL_ERROR = 500


# ============================================================================
# State Keys
# ============================================================================

class StateKeys:
    """Keys used in AgentState dictionary"""
    # Request info
    SESSION_ID = "session_id"
    REQUEST_ID = "request_id"
    USER_ID = "user_id"
    FAMILY_ID = "family_id"
    USER_NAME = "user_name"

    # Content
    CONTENT = "content"
    INTENT = "intent"
    SUB_INTENT = "sub_intent"

    # Messages
    MESSAGES = "messages"

    # Handler routing
    HANDLER_TYPE = "handler_type"

    # Context
    COLLECTED_CONTEXT = "collected_context"

    # Response
    DISPLAY_MESSAGE = "display_message"
    TTS_MESSAGE = "tts_message"
    SUGGESTIONS = "suggestions"
    UI_ELEMENTS = "ui_elements"

    # Status
    STATUS_CODE = "status_code"
    ERROR = "error"

    # Streaming
    STREAM = "stream"


# ============================================================================
# Checkpoint Namespace Patterns (for streaming)
# ============================================================================

class CheckpointPatterns:
    """Patterns for identifying checkpoint namespaces in streaming"""
    INVOKE_HANDLER = "invoke_handler:"
    CALL_LLM = "call_llm:"
    AGENT = "agent"


# ============================================================================
# Default Values
# ============================================================================

class Defaults:
    """Default values for various components"""
    STATUS_CODE = StatusCodes.OK
    EMPTY_LIST = []
    EMPTY_DICT = {}
    EMPTY_STRING = ""


# ============================================================================
# Logging Messages
# ============================================================================

class LogMessages:
    """Log message templates"""
    # Orchestrator
    PARSE_REQUEST = "[parse_request] session={session_id}, content={content}"
    ROUTE_HANDLER = "[route_handler] sub_intent='{sub_intent}' → handler_type='{handler_type}'"
    INVOKE_HANDLER = "[invoke_handler] Invoking handler: {handler_type} (sub_intent: {sub_intent})"

    # Handler execution
    HANDLER_NOT_FOUND = "[invoke_handler] Handler '{handler_type}' not found in registry"
    HANDLER_EXECUTING = "[invoke_handler] Executing {handler_type} handler subgraph..."
    HANDLER_COMPLETED = "[invoke_handler] Handler completed successfully"
    HANDLER_FAILED = "[invoke_handler] Handler execution failed: {error}"

    # Fallback
    FALLBACK_ATTEMPT = "[invoke_handler] Attempting fallback to general handler..."
    FALLBACK_SUCCESS = "[invoke_handler] Fallback successful"

    # Streaming
    STREAMING_CHUNK = "[LangGraph] Streaming chunk {chunk_num}: '{preview}...' ({length} chars)"
    STREAMING_COMPLETE = "[LangGraph] Streaming completed: {chunks} chunks, {chars} chars"
    STREAMING_FALLBACK = "[LangGraph] No streaming chunks received, falling back to ainvoke"

