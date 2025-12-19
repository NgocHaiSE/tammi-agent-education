from typing import Dict, Any, List, Optional


def build_agent_response(
    *,
    session_id: str,
    request_id: str,
    status_code: int = 200,
    status_message: str = "OK",
    display_message: str = "",
    tts_message: Optional[str] = None,
    intent: str = "learning_resource",  # Default to education agent
    sub_intent: str = "",
    parameters: Optional[Dict[str, Any]] = None,
    ui_elements: Optional[List[Dict[str, Any]]] = None,
    suggestions: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    user_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "status": {"code": status_code, "message": status_message},
        "session_id": session_id,
        "request_id": request_id,
        "user_context": user_context or {},
        "data": {
            "payload": {
                "intent": intent,
                "sub_intent": sub_intent,
                "parameters": parameters or {},
                "display_message": display_message,
                "tts_message": tts_message or display_message,
                "ui_elements": ui_elements or [],
                "suggestions": suggestions or [],
            },
            "metadata": metadata or {},
        },
    }
