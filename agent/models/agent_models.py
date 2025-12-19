"""
Pydantic models for agent requests and responses.

Provides type-safe data structures with validation.
Generic agent models that can be reused across different agent types.
"""
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, validator


# ============================================================================
# Request Models
# ============================================================================

class UserContext(BaseModel):
    """User context information with validation - All fields optional"""
    user_id: Optional[str] = Field(None, description="(Optional) ID người dùng trong hệ thống (ánh xạ từ profile_id)")
    family_id: Optional[str] = Field(None, description="(Optional) ID gia đình")
    name: Optional[str] = Field(None, description="(Optional) Tên người dùng")
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_456",
                "family_id": "family_789",
                "name": "Cường"
            }
        }


class Location(BaseModel):
    """Geographic location with validation - Optional"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")

    class Config:
        json_schema_extra = {
            "example": {
                "latitude": 21.0285,
                "longitude": 105.8542
            }
        }


class ClientContext(BaseModel):
    """Client/device context information with validation - Most fields optional"""
    box_id: str = Field(..., min_length=1, description="(Bắt buộc) Định danh box")
    type_box: Optional[str] = Field(None, description="(Tùy chọn) Mã định danh loại thiết bị/box")
    device_model: Optional[str] = Field(None, description="(Tùy chọn) Tên model thiết bị")
    os_type: Optional[str] = Field(None, description="(Tùy chọn) Hệ điều hành")
    os_version: Optional[str] = Field(None, description="(Tùy chọn) Phiên bản HĐH")
    app_version: Optional[str] = Field(None, description="(Tùy chọn) Phiên bản ứng dụng client")
    location: Optional[Location] = Field(None, description="(Tùy chọn) Vị trí của người dùng")
    timestamp: str = Field(..., description="(Bắt buộc) Thời gian gửi request (ISO 8601 UTC)")

    class Config:
        json_schema_extra = {
            "example": {
                "box_id": "box_001",
                "type_box": "1",
                "device_model": "MA4000",
                "os_type": "Android",
                "os_version": "12.1",
                "app_version": "1.2.0",
                "location": {
                    "latitude": 21.0285,
                    "longitude": 105.8542
                },
                "timestamp": "2025-10-09T14:35:00Z"
            }
        }


class Payload(BaseModel):
    """Request payload with user message - Optional"""
    type: Literal["text", "image", "audio"] = Field(default="text", description="(Bắt buộc) Loại tin nhắn: text, image, audio")
    content: str = Field(..., description="(Bắt buộc) Nội dung tin nhắn")
    intent: str = Field(..., min_length=1, description="(Bắt buộc) Intent chính")
    sub_intent: str = Field(default="", description="(Tùy chọn) Sub-intent cho phân loại")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="(Tùy chọn) JSON bổ sung (ví dụ: tv360 extras)")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "text",
                "content": "Mở Youtube tìm nhạc thiếu nhi",
                "intent": "OPEN_APP",
                "sub_intent": "YOUTUBE",
                "metadata": {}
            }
        }


class HistoryItem(BaseModel):
    """Chat history item"""
    role: str = Field(..., description='(Bắt buộc) Role: "user" hoặc "assistant"')
    content: str = Field(..., description="(Bắt buộc) Nội dung tin nhắn")
    intent: Optional[str] = Field(None, description="(Tùy chọn) Intent của tin nhắn")
    sub_intent: Optional[str] = Field(None, description="(Tùy chọn) Sub-intent của tin nhắn")
    agent: Optional[str] = Field(None, description="(Tùy chọn) Agent tạo ra phản hồi")

    @validator("role")
    def validate_role(cls, v):
        """Validate role"""
        allowed = {"user", "assistant"}
        if v not in allowed:
            raise ValueError(f"role must be one of {allowed}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "Xin chào",
                "intent": "GREET",
                "sub_intent": "",
                "agent": "medical_agent"
            }
        }


class AgentRequest(BaseModel):
    """
    Complete validated agent request schema.
    
    Theo mô tả từ phía client/frontend:
    - session_id: Từ lúc tami ơi đến lúc kết thúc cuộc trò chuyện
    - request_id: Định danh request
    - user_context: (Tùy chọn) Thông tin người dùng
    - client_context: (Tùy chọn) Thông tin thiết bị, nhưng box_id và timestamp bắt buộc
    - payload: (Tùy chọn) Nội dung tin nhắn
    - history: (Tùy chọn) Lịch sử trò chuyện
    - stream: (Tùy chọn, mặc định: false) Yêu cầu phản hồi streaming
    """
    session_id: str = Field(..., min_length=1, description="(Bắt buộc) Định danh session từ lúc bắt đầu đến kết thúc")
    request_id: str = Field(..., min_length=1, description="(Bắt buộc) Định danh request")
    user_context: Optional[UserContext] = Field(None, description="(Tùy chọn) Thông tin người dùng")
    client_context: Optional[ClientContext] = Field(None, description="(Tùy chọn) Thông tin thiết bị")
    payload: Optional[Payload] = Field(None, description="(Tùy chọn) Nội dung tin nhắn hiện tại")
    history: List[HistoryItem] = Field(default_factory=list, description="(Tùy chọn) Lịch sử hội thoại")
    stream: bool = Field(default=False, description="(Tùy chọn, mặc định: false) Yêu cầu phản hồi streaming hay không")
    agent: Optional[str] = Field(None, description="(Tùy chọn) Tên agent để routing")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_123",
                "request_id": "req_456",
                "user_context": {
                    "user_id": "user_456",
                    "family_id": "family_789",
                    "name": "Cường"
                },
                "client_context": {
                    "box_id": "box_001",
                    "type_box": "1",
                    "device_model": "MA4000",
                    "os_type": "Android",
                    "os_version": "12.1",
                    "app_version": "1.2.0",
                    "location": {
                        "latitude": 21.0285,
                        "longitude": 105.8542
                    },
                    "timestamp": "2025-10-09T14:35:00Z"
                },
                "payload": {
                    "type": "text",
                    "content": "Mở Youtube tìm nhạc thiếu nhi",
                    "intent": "OPEN_APP",
                    "sub_intent": "YOUTUBE",
                    "metadata": {}
                },
                "history": [
                    {
                        "role": "user",
                        "content": "Xin chào",
                        "intent": "GREET",
                        "sub_intent": "",
                        "agent": "medical_agent"
                    },
                    {
                        "role": "assistant",
                        "content": "Xin chào! Tôi có thể giúp gì cho bạn?",
                        "intent": "GREET",
                        "sub_intent": "",
                        "agent": "medical_agent"
                    }
                ],
                "stream": False
            }
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for backward compatibility"""
        return self.model_dump()

    class Config:
        # Allow extra fields to be ignored (for forward compatibility)
        extra = "ignore"


# ============================================================================
# Response Models
# ============================================================================

class UIElement(BaseModel):
    """UI element for rich responses"""
    type: str
    title: str = ""
    text: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)


class Parameters(BaseModel):
    """Parameters structure matching proto definition"""
    display_message: str = ""
    tts_message: str = ""
    ui_elements: List[UIElement] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    additional: Dict[str, Any] = Field(default_factory=dict)


class DataPayload(BaseModel):
    """Response data payload matching proto definition"""
    intent: str
    sub_intent: str = ""
    parameters: Parameters = Field(default_factory=Parameters)

    # For backward compatibility - keep these as deprecated properties
    @property
    def display_message(self) -> str:
        return self.parameters.display_message

    @property
    def tts_message(self) -> str:
        return self.parameters.tts_message

    @property
    def ui_elements(self) -> List[UIElement]:
        return self.parameters.ui_elements

    @property
    def suggestions(self) -> List[str]:
        return self.parameters.suggestions


class ResponseMetadata(BaseModel):
    """Response metadata"""
    service: str  # Dynamic service name (e.g., "medical_Agent", "Weather_Agent")
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    @classmethod
    def with_defaults(cls, service: Optional[str] = None, **kwargs):
        """Create ResponseMetadata with default service name from settings if not provided."""
        if service is None:
            from agent.config.settings import get_settings
            settings = get_settings()
            service = settings.agent_display_name
        return cls(service=service, **kwargs)


class ResponseData(BaseModel):
    """Response data container"""
    payload: DataPayload
    metadata: ResponseMetadata


class Status(BaseModel):
    """Response status"""
    code: int = 200
    message: str = "OK"


class AgentResponse(BaseModel):
    """Complete agent response (for non-streaming, generic for all agents)"""
    status: Status = Field(default_factory=Status)
    session_id: str
    request_id: str
    user_context: UserContext
    data: ResponseData

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        return self.model_dump()


# ============================================================================
# Streaming Models
# ============================================================================

class GeneratorResponse(BaseModel):
    """
    Streaming chunk with SAME structure as AgentResponse.
    Only difference: display_message builds incrementally.
    """
    status: Status = Field(default_factory=Status)
    session_id: str = ""
    request_id: str = ""
    user_context: UserContext = None
    data: ResponseData


class StreamChunkResponse(GeneratorResponse):
    """
    Streaming chunk with SAME structure as AgentResponse.
    Only difference: display_message builds incrementally.
    """
    # Streaming-specific metadata
    is_partial: bool = True  # Indicates this is a partial/streaming response

    def to_sse(self) -> str:
        """Convert to SSE format: data: {json}\n\n"""
        import json
        return f"data: {json.dumps(self.model_dump(), ensure_ascii=False)}\n\n"


# Legacy simple chunk model (for backward compatibility if needed)
class StreamChunk(BaseModel):
    """Simple streaming chunk (legacy)"""
    chunk: str = ""
    type: str = "text"
    intent: Optional[str] = None
    sub_intent: Optional[str] = None

    def to_sse(self) -> str:
        """Convert to SSE format: data: {json}\n\n"""
        import json
        return f"data: {json.dumps(self.model_dump(), ensure_ascii=False)}\n\n"


class StreamComplete(BaseModel):
    """Stream completion signal"""
    complete: bool = True
    content_type: Optional[str] = None

    def to_sse(self) -> str:
        """Convert to SSE format"""
        import json
        return f"data: {json.dumps(self.model_dump(), ensure_ascii=False)}\n\n"


class StreamError(BaseModel):
    """Stream error message"""
    error: str
    type: str = "error"

    def to_sse(self) -> str:
        """Convert to SSE format"""
        import json
        return f"data: {json.dumps(self.model_dump(), ensure_ascii=False)}\n\n"
