"""Test utilities and helper functions."""

from typing import Any, Dict
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage


def create_mock_llm(response_text: str = "[mocked] Test response") -> MagicMock:
    """
    Create a mocked LLM client for testing.
    
    Args:
        response_text: The text to return from mock LLM
        
    Returns:
        MagicMock instance configured as an LLM client
    """
    def mock_invoke(messages):
        return AIMessage(content=response_text)
    
    mock_llm = MagicMock()
    mock_llm.invoke = mock_invoke
    return mock_llm


def create_mock_llm_with_echo(prefix: str = "[mocked]") -> MagicMock:
    """
    Create a mocked LLM that echoes the last user message.
    
    Args:
        prefix: Prefix to add to the echoed message
        
    Returns:
        MagicMock instance configured as an LLM client
    """
    def mock_invoke(messages):
        # Get last user message
        last_user = next(
            (m.content for m in reversed(messages) 
             if hasattr(m, 'type') and m.type == 'human'),
            'no input'
        )
        return AIMessage(content=f"{prefix} {last_user}")
    
    mock_llm = MagicMock()
    mock_llm.invoke = mock_invoke
    return mock_llm


def assert_valid_agent_response(response: Dict[str, Any]) -> None:
    """
    Assert that a response has valid agent response structure.
    
    Args:
        response: The response dict to validate
        
    Raises:
        AssertionError: If response is invalid
    """
    required_keys = {'session_id', 'flow_id', 'request_id', 'sub_intent', 'display_message'}
    
    assert isinstance(response, dict), "Response must be a dict"
    assert required_keys.issubset(response.keys()), f"Missing required keys: {required_keys - response.keys()}"
    assert isinstance(response['display_message'], str), "display_message must be a string"
    assert len(response['display_message']) > 0, "display_message must not be empty"


def clear_graph_cache() -> None:
    """Clear the graph builder cache to force rebuild with new mocks."""
    from agent.graph import builder
    builder._get_cached_graph.cache_clear()
