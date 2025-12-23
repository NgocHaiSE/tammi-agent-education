"""
Format Output Node.

Formats the final response from the subgraph.
"""
import logging
from typing import Dict, Any, List

from langchain_core.messages import AIMessage, BaseMessage

from agent.graph.node_services.correct_exercise.subgraph.schema import CorrectExerciseState

logger = logging.getLogger(__name__)


class FormatOutputNode:
    """Node for formatting final output."""

    def __init__(self):
        pass

    async def run(self, state: CorrectExerciseState) -> Dict[str, Any]:
        """
        Run format output.

        Logic:
        1. Check for errors.
        2. Get LLM response.
        3. Wrap in AIMessage.
        4. Return node_responses and data_artifacts.
        """
        try:
            error_message = state.get("error_message")
            if error_message:
                return {
                    "node_responses": [AIMessage(content=error_message)],
                    "data_artifacts": {}
                }

            llm_response = state.get("llm_response")
            
            # Helper to extract content
            content = ""
            if isinstance(llm_response, BaseMessage):
                content = llm_response.content
            elif isinstance(llm_response, str):
                content = llm_response
            else:
                 # Fallback
                 if not llm_response:
                      content = "Xin lỗi, tôi đã gặp lỗi không xác định."
                 else:
                      content = str(llm_response)

            response_message = AIMessage(content=content)

            # Preserve retrieval summary in artifacts
            retrieval_summary = state.get("retrieval_summary", {})
            data_artifacts = {}
            if retrieval_summary:
                data_artifacts["retrieval_summary"] = retrieval_summary

            return {
                "node_responses": [response_message],
                "data_artifacts": data_artifacts
            }

        except Exception as e:
            logger.error(f"[format_output] Error: {e}", exc_info=True)
            return {
                "node_responses": [AIMessage(content="Đã xảy ra lỗi khi tạo phản hồi.")],
                "data_artifacts": {}
            }
