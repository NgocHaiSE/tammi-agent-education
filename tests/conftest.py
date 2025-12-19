"""
Pytest configuration and shared fixtures for tammi-agent-medical tests.

This module provides:
- Test environment setup
- Shared fixtures for all tests
- Mock LLM setup
- Common test utilities
"""

import sys
import os
from pathlib import Path
from typing import Generator
import pytest
from unittest.mock import MagicMock

# Add project root to sys.path for imports like agent.*
# Look for directory containing 'agent' folder
p = Path(__file__).resolve()
project_root = p.parent.parent  # tests/ -> project root
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment() -> Generator:
    """
    Setup test environment variables to allow LLM initialization in tests.
    
    These dummy values satisfy Azure OpenAI validation but won't actually
    be used when tests properly mock the LLM client.
    
    This fixture runs once per test session and automatically applies to all tests.
    """
    # Save original env vars
    original_env = {}
    test_env_vars = {
        "AZURE_OPENAI_API_KEY": "dummy-test-key-12345",
        "AZURE_OPENAI_ENDPOINT": "https://dummy-test.openai.azure.com/",
        "OPENAI_API_VERSION": "2024-02-15-preview",
    }
    
    for key, value in test_env_vars.items():
        if key in os.environ:
            original_env[key] = os.environ[key]
        os.environ[key] = value
    
    yield
    
    # Restore original env vars
    for key in test_env_vars:
        if key in original_env:
            os.environ[key] = original_env[key]
        else:
            os.environ.pop(key, None)


@pytest.fixture
def mock_llm():
    """
    Create a basic mocked LLM for testing.
    
    Returns a MagicMock that returns "[mocked] Test response" when invoked.
    
    Usage:
        def test_with_mock_llm(mock_llm, monkeypatch):
            monkeypatch.setattr('agent.llm_service.llm_config_service.create_medical_llm_client', 
                              lambda **kwargs: mock_llm)
            # ... test code ...
    """
    from langchain_core.messages import AIMessage
    
    def mock_invoke(messages):
        return AIMessage(content="[mocked] Test response")
    
    mock = MagicMock()
    mock.invoke = mock_invoke
    return mock


@pytest.fixture
def clear_graph_cache():
    """
    Fixture to clear the graph builder cache.
    
    Use this when you need to rebuild the graph with fresh mocks.
    
    Usage:
        def test_with_fresh_graph(clear_graph_cache):
            # Graph cache is automatically cleared before test
            # ... test code ...
    """
    from agent.graph import builder
    builder._get_cached_graph.cache_clear()
    yield
    # Clean up after test
    builder._get_cached_graph.cache_clear()


@pytest.fixture
def sample_request():
    """
    Provide a sample agent request for testing.
    
    Returns a basic medical request with emotional_support sub-intent.
    """
    return {
        'session_id': 'test-session-1',
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
