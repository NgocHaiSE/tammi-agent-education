import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import AIMessage, HumanMessage
from agent.graph.graph_state import GraphState
from agent.graph.node_services.create_exercise.create_exercise import CreateExerciseNode
from agent.external_clients.http_client import APIGatewayHTTPClient
from agent.config.settings import Settings
import unittest

@pytest.fixture
def mock_llm():
    """Fixture to mock the BaseChatModel."""
    llm = AsyncMock()
    llm.ainvoke.return_value = AIMessage(content="Đây là bài tập trắc nghiệm tiếng anh lớp 10.")
    return llm

@pytest.fixture
def mock_api_gateway_client():
    """Fixture to mock APIGatewayHTTPClient."""
    client = MagicMock(spec=APIGatewayHTTPClient)
    client.tavily_search = AsyncMock(return_value={
        "data": {
            "results": [
                {"title": "English Grade 10 Exercises", "url": "http://example.com/english-grade10", "content": "Nội dung bài tập tiếng anh lớp 10.", "score": 0.9},
            ],
            "answer": "Bài tập tiếng anh lớp 10 bao gồm ngữ pháp và từ vựng.",
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
    # Update to patch the correct location in subgraph nodes
    with unittest.mock.patch('agent.graph.node_services.create_exercise.subgraph.nodes.create_exercise_nodes.get_settings', return_value=settings_mock):
        yield

@pytest.mark.asyncio
async def test_create_exercise_run(mock_llm, mock_api_gateway_client):
    """Test the run method of CreateExerciseNode."""
    with unittest.mock.patch('agent.external_clients.http_client.APIGatewayHTTPClient', return_value=mock_api_gateway_client), \
         unittest.mock.patch('agent.graph.node_services.create_exercise.create_exercise.create_service_llm_client', return_value=mock_llm):
        node = CreateExerciseNode(llm=mock_llm)
        
        state = GraphState(
            request={
                "payload": {"content": "Tạo bài tập trắc nghiệm tiếng anh lớp 10"},
                "request_id": "test_req_123"
            },
            messages=[]
        )
        
        result = await node.run(state)
        
        # Assertions
        assert "node_responses" in result
        assert isinstance(result["node_responses"][0], AIMessage)
        assert "Đây là bài tập trắc nghiệm tiếng anh lớp 10." in result["node_responses"][0].content
        
        assert "data_artifacts" in result
        assert "retrieval_summary" in result["data_artifacts"]
        assert result["data_artifacts"]["retrieval_summary"]["query"] == "Tạo bài tập trắc nghiệm tiếng anh lớp 10"
        assert result["data_artifacts"]["retrieval_summary"]["returned_results"] == 1
        assert result["data_artifacts"]["retrieval_summary"]["has_answer"] is True
        
        mock_llm.ainvoke.assert_called_once()
        mock_api_gateway_client.tavily_search.assert_called_once_with(
            query="Tạo bài tập trắc nghiệm tiếng anh lớp 10",
            search_depth="advanced",
            max_results=2,
            include_answer=True,
            trace_id="test_req_123"
        )

@pytest.mark.asyncio
async def test_create_exercise_run_no_tavily_results(mock_llm, mock_api_gateway_client):
    """Test the run method when Tavily returns no results."""
    mock_api_gateway_client.tavily_search.return_value = {"data": {"results": [], "answer": ""}}
    with unittest.mock.patch('agent.external_clients.http_client.APIGatewayHTTPClient', return_value=mock_api_gateway_client), \
         unittest.mock.patch('agent.graph.node_services.create_exercise.create_exercise.create_service_llm_client', return_value=mock_llm):
        node = CreateExerciseNode(llm=mock_llm)
        
        state = GraphState(
            request={
                "payload": {"content": "Tạo bài tập trắc nghiệm tiếng anh lớp 10"},
                "request_id": "test_req_123"
            },
            messages=[]
        )
        
        result = await node.run(state)
        
        assert "node_responses" in result
        assert isinstance(result["node_responses"][0], AIMessage)
        assert "Đây là bài tập trắc nghiệm tiếng anh lớp 10." in result["node_responses"][0].content # LLM still responds
        
        assert "data_artifacts" in result
        assert result["data_artifacts"]["retrieval_summary"]["returned_results"] == 0
        assert result["data_artifacts"]["retrieval_summary"]["has_answer"] is False

@pytest.mark.asyncio
async def test_create_exercise_run_exception_in_tavily(mock_llm, mock_api_gateway_client):
    """Test the run method when Tavily search raises an exception."""
    mock_api_gateway_client.tavily_search.side_effect = Exception("Tavily error")
    with unittest.mock.patch('agent.external_clients.http_client.APIGatewayHTTPClient', return_value=mock_api_gateway_client), \
         unittest.mock.patch('agent.graph.node_services.create_exercise.create_exercise.create_service_llm_client', return_value=mock_llm):
        node = CreateExerciseNode(llm=mock_llm)
        
        state = GraphState(
            request={
                "payload": {"content": "Tạo bài tập trắc nghiệm tiếng anh lớp 10"},
                "request_id": "test_req_123"
            },
            messages=[]
        )
        
        result = await node.run(state)
        
        assert "node_responses" in result
        assert isinstance(result["node_responses"][0], AIMessage)
        assert "Xin lỗi, tôi gặp khó khăn trong việc" in result["node_responses"][0].content
        # Note: data_artifacts will be empty dict on error in the new subgraph architecture
        assert "data_artifacts" in result
        assert result["data_artifacts"] == {}
