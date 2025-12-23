"""
Correct Exercise Node.

Provides feedback and corrections for student exercises using Tavily search and LLM.
Now refactored to use a subgraph with separate nodes for each step.
"""
import logging
from typing import Dict, Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from agent.graph.node_base import NodeBase
from agent.graph.node_register import node_register
from agent.graph.graph_state import GraphState
from agent.graph.node_services.correct_exercise.subgraph import create_correct_exercise_graph
from agent.llm_service import create_service_llm_client

logger = logging.getLogger(__name__)


@node_register(
    name="correct_exercise",
    priority=84,
    produces=[],
    needs_builders=[],
    parallel_suggestions=False
)
class CorrectExerciseNode(NodeBase):
    """
    Correct Exercise Node.
    
    Now uses a subgraph with separate nodes:
    1. extract_input: Handle Text/Image input -> extracted_text
    2. lookup_history: Check Memory -> ground_truth / reference_context
    3. retrieve_context: Tavily Search (if needed) -> reference_context
    4. call_llm: Grade Exercise -> llm_response
    5. format_output: Format the final response with data artifacts
    """
    
    def __init__(self, llm: BaseChatModel, **kwargs):
        super().__init__(name="correct_exercise", llm=llm, **kwargs)
        self.llm = create_service_llm_client()
        # Initialize the subgraph
        self.subgraph = create_correct_exercise_graph(self.llm)
        logger.info(f"[{self.name}] Subgraph initialized")
    
    async def run(self, state: GraphState) -> Dict[str, Any]:
        """
        Run correct exercise flow using subgraph.

        The subgraph handles:
        1. extract_input: Handle Text/Image input -> extracted_text
        2. lookup_history: Check Memory -> ground_truth / reference_context
        3. retrieve_context: Tavily Search (if needed) -> reference_context
        4. call_llm: Grade Exercise -> llm_response
        5. format_output: Format final response

        Args:
            state: Current GraphState with user request
            
        Returns:
            dict: Updated state with node_responses containing exercise corrections
        """
        try:
            logger.info(f"[{self.name}] Starting correct exercise subgraph")

            question = state.get("request", {}).get("payload", {}).get("content", "")
            history = state.get("history_chat", [])

            # Prepare input for subgraph
            subgraph_input = {
                "messages": history,
                "question": question,
                "request": state.get("request", {})
            }

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
                "Xin lỗi, tôi gặp khó khăn trong việc chữa bài tập. "
                "Vui lòng thử lại hoặc cung cấp thêm thông tin về bài tập."
            )
            return {
                "node_responses": [AIMessage(content=error_message)]
            }
