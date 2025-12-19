"""
Tutor Subject Subgraph Builder.

Handles the tutor subject flow from context collection to response formatting.
"""
import logging

from langchain_core.language_models import BaseChatModel
from langgraph.constants import START, END
from langgraph.graph import StateGraph

from agent.graph.node_services.tutor_subject.subgraph.nodes import TutorSubjectNodes
from agent.graph.node_services.tutor_subject.subgraph.schema import TutorSubjectState


logger = logging.getLogger(__name__)


# Cache statistics for monitoring
_cache_stats = {
    "tutor_subject_graph": {
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


def build_tutor_subject_graph(nodes_instance):
    """
    Build and compile tutor subject subgraph WITHOUT checkpointer.

    State persistence is handled by parent graph if needed.

    Flow:
    START → collect_context → call_llm → format_output → END

    Args:
        nodes_instance: TutorSubjectNodes instance with methods for each node

    Returns:
        Compiled tutor subject graph
    """
    # Track cache statistics
    _increment_cache_stat("tutor_subject_graph", "misses")
    _increment_cache_stat("tutor_subject_graph", "builds")

    logger.info("Building tutor subject subgraph")

    tutor_subject_workflow = StateGraph(TutorSubjectState)

    # Add Nodes - using instance methods
    tutor_subject_workflow.add_node("collect_context", nodes_instance.collect_context)
    tutor_subject_workflow.add_node("call_llm", nodes_instance.call_llm)
    tutor_subject_workflow.add_node("format_output", nodes_instance.format_output)

    # Logic Flow
    tutor_subject_workflow.add_edge(START, "collect_context")

    # Conditional routing from collect_context
    def route_after_context(state: TutorSubjectState) -> str:
        """Route after context collection."""
        next_node = state.get("next_node", "call_llm")
        logger.debug(f"After collect_context: next_node={next_node}")
        return next_node

    tutor_subject_workflow.add_conditional_edges(
        "collect_context",
        route_after_context,
        {
            "call_llm": "call_llm",
            "format_output": "format_output"
        }
    )

    # Conditional routing from call_llm
    def route_after_llm(state: TutorSubjectState) -> str:
        """Route after LLM call."""
        next_node = state.get("next_node", "format_output")
        logger.debug(f"After call_llm: next_node={next_node}")
        return next_node

    tutor_subject_workflow.add_conditional_edges(
        "call_llm",
        route_after_llm,
        {
            "format_output": "format_output"
        }
    )

    # format_output always goes to END
    tutor_subject_workflow.add_edge("format_output", END)

    # Compile
    compiled_graph = tutor_subject_workflow.compile()

    logger.info("Tutor subject subgraph compiled successfully")

    return compiled_graph


def create_tutor_subject_graph(llm: BaseChatModel):
    """
    Create tutor subject graph with LLM initialization.

    This function:
    1. Creates a TutorSubjectNodes instance with the provided LLM
    2. Builds and returns the compiled graph

    Args:
        llm: Language model instance

    Returns:
        Compiled tutor subject graph
    """
    # Create nodes instance with LLM
    nodes = TutorSubjectNodes(llm)

    # Build and return graph
    graph = build_tutor_subject_graph(nodes)
    logger.info("Tutor subject graph created successfully")
    return graph

