"""
Correct Exercise Subgraph Builder.

Handles the correct exercise flow from question extraction to response formatting.
"""
import logging

from langchain_core.language_models import BaseChatModel
from langgraph.constants import START, END
from langgraph.graph import StateGraph

from agent.graph.node_services.correct_exercise.subgraph.nodes import CorrectExerciseNodes
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


def build_correct_exercise_graph(nodes_instance):
    """
    Build and compile correct exercise subgraph WITHOUT checkpointer.

    State persistence is handled by parent graph if needed.

    Flow:
    START → extract_question → retrieve_context → call_llm → format_output → END

    Args:
        nodes_instance: CorrectExerciseNodes instance with methods for each node

    Returns:
        Compiled correct exercise graph
    """
    # Track cache statistics
    _increment_cache_stat("correct_exercise_graph", "misses")
    _increment_cache_stat("correct_exercise_graph", "builds")

    logger.info("Building correct exercise subgraph")

    correct_exercise_workflow = StateGraph(CorrectExerciseState)

    # Add Nodes - using instance methods
    correct_exercise_workflow.add_node("extract_question", nodes_instance.extract_question)
    correct_exercise_workflow.add_node("retrieve_context", nodes_instance.retrieve_context)
    correct_exercise_workflow.add_node("call_llm", nodes_instance.call_llm)
    correct_exercise_workflow.add_node("format_output", nodes_instance.format_output)

    # Logic Flow
    correct_exercise_workflow.add_edge(START, "extract_question")

    # Conditional routing from extract_question
    def route_after_extract(state: CorrectExerciseState) -> str:
        """Route after question extraction."""
        next_node = state.get("next_node", "retrieve_context")
        logger.debug(f"After extract_question: next_node={next_node}")
        return next_node

    correct_exercise_workflow.add_conditional_edges(
        "extract_question",
        route_after_extract,
        {
            "retrieve_context": "retrieve_context",
            "format_output": "format_output"
        }
    )

    # Conditional routing from retrieve_context
    def route_after_retrieval(state: CorrectExerciseState) -> str:
        """Route after context retrieval."""
        next_node = state.get("next_node", "call_llm")
        logger.debug(f"After retrieve_context: next_node={next_node}")
        return next_node

    correct_exercise_workflow.add_conditional_edges(
        "retrieve_context",
        route_after_retrieval,
        {
            "call_llm": "call_llm",
            "format_output": "format_output"
        }
    )

    # Conditional routing from call_llm
    def route_after_llm(state: CorrectExerciseState) -> str:
        """Route after LLM call."""
        next_node = state.get("next_node", "format_output")
        logger.debug(f"After call_llm: next_node={next_node}")
        return next_node

    correct_exercise_workflow.add_conditional_edges(
        "call_llm",
        route_after_llm,
        {
            "format_output": "format_output"
        }
    )

    # format_output always goes to END
    correct_exercise_workflow.add_edge("format_output", END)

    # Compile
    compiled_graph = correct_exercise_workflow.compile()

    logger.info("Correct exercise subgraph compiled successfully")

    return compiled_graph


def create_correct_exercise_graph(llm: BaseChatModel):
    """
    Create correct exercise graph with LLM initialization.

    This function:
    1. Creates a CorrectExerciseNodes instance with the provided LLM
    2. Builds and returns the compiled graph

    Args:
        llm: Language model instance

    Returns:
        Compiled correct exercise graph
    """
    # Create nodes instance with LLM
    nodes = CorrectExerciseNodes(llm)

    # Build and return graph
    graph = build_correct_exercise_graph(nodes)
    logger.info("Correct exercise graph created successfully")
    return graph
