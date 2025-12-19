import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import AIMessage, HumanMessage
from agent.graph.graph_state import GraphState
from agent.graph.node_services.correct_exercise.correct_exercise import CorrectExerciseNode
from agent.external_clients.http_client import APIGatewayHTTPClient
from agent.config.settings import Settings
import unittest

@pytest.fixture
def mock_llm():
    """Fixture to mock the BaseChatModel."""
    llm = AsyncMock()
    llm.ainvoke.return_value = AIMessage(content="Đây là lời giải cho bài toán của bạn.")
    return llm

@pytest.fixture
def mock_api_gateway_client():
    """Fixture to mock APIGatewayHTTPClient."""
    client = MagicMock(spec=APIGatewayHTTPClient)
    client.tavily_search = AsyncMock(return_value={
        "data": {
            "results": [
                {"title": "Math Problem Solutions", "url": "http://example.com/math-solutions", "content": "Nội dung lời giải bài toán.", "score": 0.9},
            ],
            "answer": "Lời giải chi tiết cho bài toán.",
        }
    })
    return client

@pytest.fixture(autouse=True)
def mock_settings():
    """Fixture to mock settings."""
    settings_mock = MagicMock(spec=Settings)
    settings_mock.API_GATEWAY_HTTP_URL = "http://mock-api-gateway.com"
    settings_mock.EXTERNAL_CLIENT_TIMEOUT = 1.0
    settings_mock.EXTERNAL_CLIENT_MAX_RETRIES = 1
    settings_mock.CIRCUIT_BREAKER_THRESHOLD = 1
    settings_mock.CIRCUIT_BREAKER_TIMEOUT = 1
    with unittest.mock.patch('agent.graph.node_services.correct_exercise.correct_exercise.get_settings', return_value=settings_mock):
        yield

@pytest.mark.asyncio
async def test_correct_exercise_run(mock_llm, mock_api_gateway_client):
    """Test the run method of CorrectExerciseNode."""
    with unittest.mock.patch('agent.external_clients.http_client.APIGatewayHTTPClient', return_value=mock_api_gateway_client):
        node = CorrectExerciseNode(llm=mock_llm)
        
        state = GraphState(
            request={
                "payload": {"content": "Giúp tôi chữa bài toán này"},
                "request_id": "test_req_123"
            }
        )
        
        result = await node.run(state)
        
        # Assertions
        assert "node_responses" in result
        assert isinstance(result["node_responses"][0], AIMessage)
        assert "Đây là lời giải cho bài toán của bạn." in result["node_responses"][0].content
        
        assert "data_artifacts" in result
        assert "retrieval_summary" in result["data_artifacts"]
        assert result["data_artifacts"]["retrieval_summary"]["query"] == "Giúp tôi chữa bài toán này"
        assert result["data_artifacts"]["retrieval_summary"]["returned_results"] == 1
        assert result["data_artifacts"]["retrieval_summary"]["has_answer"] is True
        
        mock_llm.ainvoke.assert_called_once()
        mock_api_gateway_client.tavily_search.assert_called_once_with(
            query="Giúp tôi chữa bài toán này",
            search_depth="advanced",
            max_results=2,
            include_answer=True,
            trace_id="test_req_123"
        )

@pytest.mark.asyncio
async def test_correct_exercise_run_no_tavily_results(mock_llm, mock_api_gateway_client):
    """Test the run method when Tavily returns no results."""
    mock_api_gateway_client.tavily_search.return_value = {"data": {"results": [], "answer": ""}}
    with unittest.mock.patch('agent.external_clients.http_client.APIGatewayHTTPClient', return_value=mock_api_gateway_client):
        node = CorrectExerciseNode(llm=mock_llm)
        
        state = GraphState(
            request={
                "payload": {"content": "Giúp tôi chữa bài toán này"},
                "request_id": "test_req_123"
            }
        )
        
        result = await node.run(state)
        
        assert "node_responses" in result
        assert isinstance(result["node_responses"][0], AIMessage)
        assert "Đây là lời giải cho bài toán của bạn." in result["node_responses"][0].content # LLM still responds
        
        assert "data_artifacts" in result
        assert result["data_artifacts"]["retrieval_summary"]["returned_results"] == 0
        assert result["data_artifacts"]["retrieval_summary"]["has_answer"] is False

@pytest.mark.asyncio
async def test_correct_exercise_run_exception_in_tavily(mock_llm, mock_api_gateway_client):
    """Test the run method when Tavily search raises an exception."""
    mock_api_gateway_client.tavily_search.side_effect = Exception("Tavily error")
    with unittest.mock.patch('agent.external_clients.http_client.APIGatewayHTTPClient', return_value=mock_api_gateway_client):
        node = CorrectExerciseNode(llm=mock_llm)
        
        state = GraphState(
            request={
                "payload": {"content": "Giúp tôi chữa bài toán này"},
                "request_id": "test_req_123"
            }
        )
        
        result = await node.run(state)
        
        assert "node_responses" in result
        assert isinstance(result["node_responses"][0], AIMessage)
        assert "Xin lỗi, tôi gặp khó khăn trong việc chữa bài tập." in result["node_responses"][0].content
        assert "data_artifacts" not in result # No data_artifacts on error
