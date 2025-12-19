"""
Request conversion and validation utilities.

Provides converter functions from proto messages and dictionaries to validated schemas.
"""
from typing import Any, Dict
from agent.models import AgentRequest


def proto_to_request_dict(proto_request: Any) -> Dict[str, Any]:
    """
    Convert protobuf AgentRequest to validated dictionary.
    
    This function:
    1. Extracts all fields from proto message
    2. Validates using AgentRequest
    3. Returns type-safe dictionary
    
    Args:
        proto_request: agents_pb2.AgentRequest protobuf message
        
    Returns:
        Dictionary with validated request data
        
    Raises:
        ValueError: If validation fails
        AttributeError: If proto message is malformed
    """
    try:
        # Extract user_context if present
        user_context_dict = None
        if proto_request.user_context and (
            proto_request.user_context.user_id or 
            proto_request.user_context.family_id or 
            proto_request.user_context.name
        ):
            user_context_dict = {
                "user_id": proto_request.user_context.user_id or None,
                "family_id": proto_request.user_context.family_id or None,
                "name": proto_request.user_context.name or None,
            }

        # Extract client_context if present and has required fields
        client_context_dict = None
        if proto_request.client_context and proto_request.client_context.box_id:
            location_dict = None
            if proto_request.client_context.location and (
                proto_request.client_context.location.latitude or 
                proto_request.client_context.location.longitude
            ):
                location_dict = {
                    "latitude": proto_request.client_context.location.latitude,
                    "longitude": proto_request.client_context.location.longitude,
                }

            client_context_dict = {
                "box_id": proto_request.client_context.box_id,
                "type_box": proto_request.client_context.type_box or None,
                "device_model": proto_request.client_context.device_model or None,
                "os_type": proto_request.client_context.os_type or None,
                "os_version": proto_request.client_context.os_version or None,
                "app_version": proto_request.client_context.app_version or None,
                "location": location_dict,
                "timestamp": proto_request.client_context.timestamp,
            }

        # Extract payload if present
        payload_dict = None
        if proto_request.payload and proto_request.payload.content:
            payload_dict = {
                "type": proto_request.payload.type or "text",
                "content": proto_request.payload.content,
                "intent": proto_request.payload.intent,
                "sub_intent": proto_request.payload.sub_intent or "",
                "metadata": _struct_to_dict(proto_request.payload.metadata),
            }

        # Build final request dict
        request_dict = {
            "session_id": proto_request.session_id,
            "request_id": proto_request.request_id,
            "user_context": user_context_dict,
            "client_context": client_context_dict,
            "payload": payload_dict,
            "history": [
                {
                    "role": h.role,
                    "content": h.content,
                    "intent": h.intent or None,
                    "sub_intent": h.sub_intent or None,
                    "agent": h.agent or None,
                }
                for h in proto_request.history
            ],
            "stream": proto_request.stream
        }
        
        # Validate using schema
        validated = AgentRequest(**request_dict)
        return validated.to_dict()
        
    except Exception as e:
        raise ValueError(f"Failed to convert proto request to validated dict: {str(e)}")


def dict_to_request_schema(request_dict: Dict[str, Any]) -> AgentRequest:
    """
    Convert dictionary to validated AgentRequest.
    
    Useful for HTTP requests where JSON is parsed into dict.
    
    Args:
        request_dict: Dictionary with request data
        
    Returns:
        Validated AgentRequest instance
        
    Raises:
        ValueError: If validation fails
    """
    try:
        return AgentRequest(**request_dict)
    except Exception as e:
        raise ValueError(f"Failed to validate request dictionary: {str(e)}")


# ============================================================================
# Helper Functions
# ============================================================================

def _struct_to_dict(struct_pb: Any) -> Dict[str, Any]:
    """
    Convert protobuf Struct to dictionary.
    
    Args:
        struct_pb: google.protobuf.struct_pb2.Struct
        
    Returns:
        Dictionary representation
    """
    if not struct_pb:
        return {}
    return {k: v for k, v in struct_pb.items()}


def _dict_to_struct(d: Dict[str, Any]) -> Any:
    """
    Convert dictionary to protobuf Struct.
    
    Args:
        d: Dictionary to convert
        
    Returns:
        google.protobuf.struct_pb2.Struct
    """
    from google.protobuf import struct_pb2
    s = struct_pb2.Struct()
    s.update(d or {})
    return s
