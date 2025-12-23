"""
Correct Exercise Subgraph Builder.

Handles the correct exercise flow from input extraction to response formatting.
"""
import logging

from langchain_core.language_models import BaseChatModel
from langgraph.constants import START, END
from langgraph.graph import StateGraph

from agent.graph.node_services.correct_exercise.subgraph.nodes import (
    ExtractInputNode,
    # LookupHistoryNode,
    # RetrieveContextNode,
    CallLLMNode,
    EvaluateNode,
    FormatOutputNode
)
from agent.graph.node_services.correct_exercise.subgraph.schema import CorrectExerciseState


logger = logging.getLogger(__name__)


# Cache statistics for monitoring
_cache_stats = {
    "correct_exercise_graph": {
        "hits": 0,
        "misses": 0,
        "builds": 0
    }
}


def _increment_cache_stat(graph_name: str, stat_type: str):
    """Increment cache statistics."""
    if graph_name in _cache_stats and stat_type in _cache_stats[graph_name]:
        _cache_stats[graph_name][stat_type] += 1


def get_cache_stats() -> dict:
    """Get current cache statistics."""
    return _cache_stats.copy()


def build_correct_exercise_graph(llm: BaseChatModel):
    """
    Build and compile correct exercise subgraph.

    Flow:
    START → extract_input → lookup_history
         → (found) → call_llm → format_output
         → (not found) → retrieve_context → call_llm → format_output

    Args:
        llm: Language model instance

    Returns:
        Compiled correct exercise graph
    """
    # Track cache statistics
    _increment_cache_stat("correct_exercise_graph", "misses")
    _increment_cache_stat("correct_exercise_graph", "builds")

    logger.info("Building correct exercise subgraph")

    correct_exercise_workflow = StateGraph(CorrectExerciseState)

    # Initialize Nodes
    extract_input_node = ExtractInputNode(llm)
    # lookup_history_node = LookupHistoryNode() # Removed per request
    # retrieve_context_node = RetrieveContextNode() # Removed per request
    call_llm_node = CallLLMNode(llm)
    evaluate_node = EvaluateNode(llm)
    format_output_node = FormatOutputNode()

    # Add Nodes
    correct_exercise_workflow.add_node("extract_input", extract_input_node.run)
    # correct_exercise_workflow.add_node("lookup_history", lookup_history_node.run) # Removed
    # correct_exercise_workflow.add_node("retrieve_context", retrieve_context_node.run) # Removed
    correct_exercise_workflow.add_node("call_llm", call_llm_node.run)
    correct_exercise_workflow.add_node("evaluate_node", evaluate_node.run)
    correct_exercise_workflow.add_node("format_output", format_output_node.run)

    # Logic Flow
    correct_exercise_workflow.add_edge(START, "extract_input")
    
    # After extract_input, always go to call_llm (unless error)
    def route_after_extract(state: CorrectExerciseState) -> str:
        if state.get("error_message"):
             return "format_output"
        return "call_llm"

    correct_exercise_workflow.add_conditional_edges(
        "extract_input",
        route_after_extract,
        {
            "call_llm": "call_llm",
            "format_output": "format_output"
        }
    )

    # From lookup_history -> call_llm (Removed)
    
    # From retrieve_context -> call_llm (Removed edge)
    # correct_exercise_workflow.add_edge("retrieve_context", "call_llm")

    # From call_llm -> evaluate_node
    correct_exercise_workflow.add_edge("call_llm", "evaluate_node")

    # From evaluate_node -> format_output
    correct_exercise_workflow.add_edge("evaluate_node", "format_output")

    # format_output -> END
    correct_exercise_workflow.add_edge("format_output", END)

    # Compile
    compiled_graph = correct_exercise_workflow.compile()

    logger.info("Correct exercise subgraph compiled successfully")

    return compiled_graph


def create_correct_exercise_graph(llm: BaseChatModel):
    """
    Create correct exercise graph with LLM initialization.

    Args:
        llm: Language model instance

    Returns:
        Compiled correct exercise graph
    """
    return build_correct_exercise_graph(llm)
