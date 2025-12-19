"""
State definition for medical Agent graph.

Stores the complete state for graph execution including:
- Original request from user
- Chat history
- Node responses and outputs
"""

from typing import Any, Annotated, Dict, List, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class GraphState(TypedDict, total=False):
    """
    State for medical Agent graph execution.
    
    Stores all information needed during graph execution including
    original request, conversation history, and node responses.
    
    Examples:
    
    >>> state = {
    ...     "request": {
    ...         "session_id": "sess_12345",
    ...         "request_id": "req_67890",
    ...         "user_context": {
    ...             "user_id": "user_001",
    ...             "family_id": "fam_001",
    ...             "name": "Anh",
    ...         },
    ...         "client_context": {
    ...             "box_id": "box_123",
    ...             "type_box": "speaker",
    ...             "device_model": "TM",
    ...             "os_type": "Linux",
    ...             "location": {
    ...                 "latitude": 21.0285,
    ...                 "longitude": 105.8542,
    ...             },
    ...             "timestamp": 1730866800,
    ...         },
    ...         "payload": {
    ...             "type": "text",
    ...             "content": "Hôm nay mặc gì đi?",
    ...             "intent": "medical",
    ...             "sub_intent": None,  # Will be classified
    ...             "metadata": {},
    ...         },
    ...         "history": [
    ...             {
    ...                 "role": "user",
    ...                 "content": "Xin chào",
    ...                 "intent": "medical",
    ...                 "sub_intent": "emotional_support",
    ...             },
    ...             {
    ...                 "role": "assistant",
    ...                 "content": "Xin chào! Mình là Tammi, sẵn sàng giúp bạn.",
    ...                 "intent": "response",
    ...                 "sub_intent": "emotional_support",
    ...             },
    ...         ],
    ...         "stream": False,
    ...     },
    ...     "history_chat": {
    ...         "msg_1": HumanMessage(content="Xin chào"),
    ...         "msg_2": AIMessage(content="Xin chào! Mình là Tammi, sẵn sàng giúp bạn."),
    ...     },
    ...     "node_responses": [
    ...         HumanMessage(content="outfit_suggestion"),  # From classification node
    ...     ],
    ... }
    """
    
    # Original request from user - Contains all request metadata and payload
    # Structure:
    # {
    #     "session_id": str,              # Session identifier
    #     "request_id": str,              # Request identifier
    #     "flow_id": str,                 # Flow identifier
    #     "user_context": {
    #         "user_id": str,             # User ID
    #         "family_id": str,           # Family ID
    #         "name": str,                # User name
    #     },
    #     "client_context": {
    #         "box_id": str,              # Device/box ID
    #         "type_box": str,            # Box type (e.g., "speaker")
    #         "device_model": str,        # Device model
    #         "os_type": str,             # OS type
    #         "os_version": str,          # OS version
    #         "app_version": str,         # App version
    #         "location": {
    #             "latitude": float,      # Latitude
    #             "longitude": float,     # Longitude
    #         },
    #         "timestamp": int,           # Unix timestamp
    #     },
    #     "payload": {
    #         "type": str,                # Content type (e.g., "text", "audio")
    #         "content": str,             # User input text
    #         "intent": str,              # Primary intent (e.g., "medical")
    #         "sub_intent": str | None,   # Sub-intent (filled by classifier)
    #         "metadata": dict,           # Additional metadata
    #     },
    #     "history": list[dict],          # Conversation history
    #     "stream": bool,                 # Whether streaming is enabled
    # }
    request: Dict[str, Any]
    
    # Chat history - Maintains conversation context
    # Structure:
    # {
    #     "msg_1": HumanMessage(...),
    #     "msg_2": AIMessage(...),
    #     ...
    # }
    # 
    # Example:
    # {
    #     "msg_1": HumanMessage(content="Xin chào"),
    #     "msg_2": AIMessage(content="Xin chào! Mình là Tammi."),
    # }
    # history_chat: Dict[str, BaseMessage]
    history_chat: Annotated[List[BaseMessage], add_messages]
    
    # Node responses - Accumulated outputs from each node (with add_messages reducer)
    # Stored as list of BaseMessage objects for easy aggregation
    # Structure:
    # [
    #     AIMessage(content="outfit_suggestion"),  # From classification node
    #     AIMessage(content="Dựa trên thời tiết..."),  # From outfit node
    # ]
    #
    # The add_messages reducer automatically:
    # - Deduplicates consecutive messages from the same sender
    # - Maintains message order
    # - Enables streaming
    node_responses: Annotated[List[BaseMessage], add_messages]

    # Data artifacts - Signal container for builders
    # Nodes write data here, builders read from it
    # Structure:
    # {
    #     "weather_data": {...},     # From outfit/food/activity nodes
    #     "restaurant_data": {...},  # From food node
    #     "location": "Hanoi",       # Common metadata
    #     ...
    # }
    # This enables metadata-driven output building without hardcoding
    data_artifacts: Dict[str, Any]


# Type alias for convenience
GraphState = GraphState
