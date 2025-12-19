"""
Tutor Subject Node.

Handles tutoring guidance for language learning and various school subjects.
Now refactored to use a subgraph with separate nodes for each step.
"""
import logging
from typing import Dict, Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from agent.graph.node_base import NodeBase
from agent.graph.node_register import node_register
from agent.graph.graph_state import GraphState
from agent.graph.node_services.tutor_subject.subgraph import create_tutor_subject_graph
from agent.llm_service import create_service_llm_client

logger = logging.getLogger(__name__)


@node_register(
    name="tutor_subject",
    priority=75,
    produces=[],
    needs_builders=[],
    parallel_suggestions=False
)
class TutorSubjectNode(NodeBase):
    """
    Tutor Subject Node.

    Now uses a subgraph with separate nodes:
    1. collect_context: Extract question and retrieve educational content via Tavily
    2. call_llm: Generate tutoring guidance using LLM
    3. format_output: Format the final response with retrieval artifacts
    """

    def __init__(self, llm: BaseChatModel, **kwargs):
        super().__init__(name="tutor_subject", llm=llm, **kwargs)
        self.llm = create_service_llm_client()
        # Initialize the subgraph
        self.subgraph = create_tutor_subject_graph(self.llm)
        logger.info(f"[{self.name}] Subgraph initialized")

    async def run(self, state: GraphState) -> Dict[str, Any]:
        """
        Run tutor subject flow using subgraph.

        The subgraph handles:
        1. collect_context: Extract question and retrieve educational content
        2. call_llm: Generate tutoring guidance using LLM
        3. format_output: Format final response

        Args:
            state: Current GraphState with user request

        Returns:
            dict: Updated state with node_responses containing tutoring guidance
        """
        try:
            logger.info(f"[{self.name}] Starting tutor subject subgraph")
            question = state.get("request", {}).get("payload", {}).get("content", "")
            history = state.get("history_chat", [])

            logger.info(f"[{self.name}] Extracted question: '{question[:100] if question else '(empty)'}...'")
            logger.info(f"[{self.name}] History count: {len(history)}")

            # Prepare input for subgraph
            subgraph_input = {
                "messages": history,
                "question": question,
                "request": state.get("request", {})
            }
            
            logger.info(f"[{self.name}] Subgraph input keys: {list(subgraph_input.keys())}")
            logger.info(f"[{self.name}] Subgraph question field: '{subgraph_input.get('question', '(not set)')[:100]}...')")

            # Invoke subgraph
            result = await self.subgraph.ainvoke(subgraph_input)

            # Extract results from subgraph
            node_responses = result.get("node_responses", [])
            data_artifacts = result.get("data_artifacts", {})

            logger.info(
                f"[{self.name}] Subgraph completed. "
                f"Response count: {len(node_responses)}"
            )

            return {
                "node_responses": node_responses,
                "data_artifacts": data_artifacts
            }

        except Exception as e:
            logger.error(f"[{self.name}] Error in subgraph: {e}", exc_info=True)
            error_message = (
                "Xin lỗi, tôi gặp khó khăn trong việc hướng dẫn học tập. "
                "Vui lòng thử lại sau."
            )
            return {
                "node_responses": [AIMessage(content=error_message)]
            }

