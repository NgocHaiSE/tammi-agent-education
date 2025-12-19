import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage
from agent.graph.graph_state import GraphState
from agent.graph.node_services.tutor_subject.tutor_subject import TutorSubjectNode
from agent.external_clients.http_client import APIGatewayHTTPClient
from agent.config.settings import Settings


@pytest.fixture
def mock_llm():
    """Fixture to mock the BaseChatModel."""
    llm = AsyncMock()
    llm.ainvoke.return_value = AIMessage(content="Đây là hướng dẫn học tiếng Anh cho trẻ lớp 5.")
    return llm


@pytest.fixture
def mock_api_gateway_client():
    """Fixture to mock APIGatewayHTTPClient."""
    client = MagicMock(spec=APIGatewayHTTPClient)
    client.tavily_search = AsyncMock(return_value={
        "data": {
            "results": [
                {"title": "English for 5th Graders", "url": "http://example.com/english-grade5", "content": "Nội dung hướng dẫn tiếng Anh lớp 5.", "score": 0.9},
            ],
            "answer": "Phương pháp học tiếng Anh hiệu quả cho trẻ lớp 5.",
        }
    })
    return client


@pytest.fixture(autouse=True)
def mock_settings():
    """Fixture to mock settings in the subgraph nodes."""
    settings_mock = MagicMock(spec=Settings)
    settings_mock.API_GATEWAY_HTTP_URL = "http://mock-api-gateway.com"
    settings_mock.EXTERNAL_CLIENT_TIMEOUT = 1.0
    settings_mock.EXTERNAL_CLIENT_MAX_RETRIES = 1
    settings_mock.CIRCUIT_BREAKER_THRESHOLD = 1
    settings_mock.CIRCUIT_BREAKER_TIMEOUT = 1
    # Patch in the subgraph nodes module where get_settings is actually used
    with patch('agent.graph.node_services.tutor_subject.subgraph.nodes.tutor_subject_nodes.get_settings', return_value=settings_mock):
        yield


@pytest.mark.asyncio
async def test_tutor_subject_run(mock_llm, mock_api_gateway_client):
    """Test the run method of TutorSubjectNode with subgraph."""
    with patch('agent.external_clients.http_client.APIGatewayHTTPClient', return_value=mock_api_gateway_client), \
         patch('agent.graph.node_services.tutor_subject.tutor_subject.create_service_llm_client', return_value=mock_llm):
        node = TutorSubjectNode(llm=mock_llm)

        state = GraphState(
            request={
                "payload": {"content": "trẻ lớp 5 nên học tiếng anh thế nào"},
                "request_id": "test_req_123"
            }
        )

        result = await node.run(state)

        # Assertions
        assert "node_responses" in result
        assert isinstance(result["node_responses"][0], AIMessage)
        assert "Đây là hướng dẫn học tiếng Anh cho trẻ lớp 5." in result["node_responses"][0].content

        assert "data_artifacts" in result
        assert "retrieval_summary" in result["data_artifacts"]
        assert result["data_artifacts"]["retrieval_summary"]["query"] == "trẻ lớp 5 nên học tiếng anh thế nào"
        assert result["data_artifacts"]["retrieval_summary"]["returned_results"] == 1
        assert result["data_artifacts"]["retrieval_summary"]["has_answer"] is True

        mock_llm.ainvoke.assert_called_once()
        mock_api_gateway_client.tavily_search.assert_called_once_with(
            query="trẻ lớp 5 nên học tiếng anh thế nào",
            search_depth="advanced",
            max_results=2,
            include_answer=True,
            trace_id="test_req_123"
        )


@pytest.mark.asyncio
async def test_tutor_subject_run_no_tavily_results(mock_llm, mock_api_gateway_client):
    """Test the run method when Tavily returns no results."""
    mock_api_gateway_client.tavily_search.return_value = {"data": {"results": [], "answer": ""}}
    with patch('agent.external_clients.http_client.APIGatewayHTTPClient', return_value=mock_api_gateway_client), \
         patch('agent.graph.node_services.tutor_subject.tutor_subject.create_service_llm_client', return_value=mock_llm):
        node = TutorSubjectNode(llm=mock_llm)

        state = GraphState(
            request={
                "payload": {"content": "trẻ lớp 5 nên học tiếng anh thế nào"},
                "request_id": "test_req_123"
            }
        )

        result = await node.run(state)

        assert "node_responses" in result
        assert isinstance(result["node_responses"][0], AIMessage)
        assert "Đây là hướng dẫn học tiếng Anh cho trẻ lớp 5." in result["node_responses"][0].content # LLM still responds

        assert "data_artifacts" in result
        assert result["data_artifacts"]["retrieval_summary"]["returned_results"] == 0
        assert result["data_artifacts"]["retrieval_summary"]["has_answer"] is False


@pytest.mark.asyncio
async def test_tutor_subject_run_exception_in_tavily(mock_llm, mock_api_gateway_client):
    """Test the run method when Tavily search raises an exception."""
    mock_api_gateway_client.tavily_search.side_effect = Exception("Tavily error")
    with patch('agent.external_clients.http_client.APIGatewayHTTPClient', return_value=mock_api_gateway_client), \
         patch('agent.graph.node_services.tutor_subject.tutor_subject.create_service_llm_client', return_value=mock_llm):
        node = TutorSubjectNode(llm=mock_llm)

        state = GraphState(
            request={
                "payload": {"content": "trẻ lớp 5 nên học tiếng anh thế nào"},
                "request_id": "test_req_123"
            }
        )

        result = await node.run(state)

        assert "node_responses" in result
        assert isinstance(result["node_responses"][0], AIMessage)
        assert "Xin lỗi, tôi gặp khó khăn trong việc hướng dẫn học tập." in result["node_responses"][0].content

