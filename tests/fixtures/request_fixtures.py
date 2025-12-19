"""Shared test data for agent requests and responses."""

# Sample agent requests
SAMPLE_medical_REQUEST = {
    'session_id': 'test-session-1',
    'flow_id': 'test-flow-1',
    'request_id': 'test-req-1',
    'user_context': {'user_id': 'test-user-1'},
    'client_context': {},
    'payload': {
        'type': 'text',
        'content': 'Tôi buồn',
        'intent': 'medical',
        'sub_intent': 'emotional_support',
        'metadata': {}
    },
    'history': [],
    'stream': False,
}

SAMPLE_WEEKEND_REQUEST = {
    'session_id': 'test-session-2',
    'flow_id': 'test-flow-2',
    'request_id': 'test-req-2',
    'user_context': {'user_id': 'test-user-2'},
    'client_context': {},
    'payload': {
        'type': 'text',
        'content': 'Gợi ý cuối tuần',
        'intent': 'medical',
        'sub_intent': 'weekend_ideas',
        'metadata': {}
    },
    'history': [],
    'stream': False,
}

SAMPLE_STREAMING_REQUEST = {
    'session_id': 'test-session-3',
    'flow_id': 'test-flow-3',
    'request_id': 'test-req-3',
    'user_context': {'user_id': 'test-user-3'},
    'client_context': {},
    'payload': {
        'type': 'text',
        'content': 'Cho tôi lời khuyên',
        'intent': 'medical',
        'sub_intent': 'general',
        'metadata': {}
    },
    'history': [],
    'stream': True,
}

# Sample conversation history
SAMPLE_HISTORY = [
    {
        'role': 'user',
        'content': 'Xin chào'
    },
    {
        'role': 'assistant',
        'content': 'Chào bạn! Tôi có thể giúp gì cho bạn?'
    },
]

# Expected response structure
EXPECTED_RESPONSE_KEYS = {
    'session_id',
    'flow_id',
    'request_id',
    'sub_intent',
    'display_message',
    'metadata',
}
