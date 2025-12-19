"""
Agent models package.

Pydantic models for type-safe request/response handling.
"""
# Primary generic models (recommended for new code)
from agent.models.agent_models import (
    # Request models
    AgentRequest,
    UserContext,
    ClientContext,
    Location,
    Payload,
    HistoryItem,
    
    # Response models
    AgentResponse,
    ResponseData,
    DataPayload,
    ResponseMetadata,
    Status,
    UIElement,
    Parameters,

    # Streaming models
    StreamChunkResponse,
    StreamChunk,
    StreamComplete,
    StreamError,
    
    # Internal models
    GeneratorResponse,
)



__all__ = [
    # Generic models (recommended)
    "AgentRequest",
    "AgentResponse",
    "GeneratorResponse",
    
    # Backward compatibility (medical-specific)
    "AgentRequest",
    "AgentResponse",
    "GeneratorResponse",
    
    # Shared models
    "UserContext",
    "ClientContext",
    "Location",
    "Payload",
    "HistoryItem",
    "ResponseData",
    "DataPayload",
    "ResponseMetadata",
    "Status",
    "UIElement",
    "Parameters",
    "StreamChunkResponse",
    "StreamChunk",
    "StreamComplete",
    "StreamError",
]
