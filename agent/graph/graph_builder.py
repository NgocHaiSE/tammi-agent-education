"""
Graph builder for medical Agent using LangGraph.
"""

import logging
from typing import Optional
from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent.config.settings import get_settings
from agent.graph.graph_state import GraphState
from agent.graph.constants import SubIntents
# Import node_services to auto-register all nodes via @node_register decorators
from agent.graph.node_base import NodeBase
import agent.graph.node_services  # noqa: F401
from agent.graph.node_register import list_nodes, get_node_class, get_node_metadata
from agent.llm_service import create_agent_llm_client

logger = logging.getLogger(__name__)


# ==================== Graph Builder ====================

def _route_to_node(state: GraphState) -> str:
    """
    Route to appropriate node based on sub_intent.
    
    Routes based on request.payload.sub_intent which is set by classification node.
    Returns the name of the next node to execute.
    """
    request = state.get("request", {})
    payload = request.get("payload", {})
    sub_intent = payload.get("sub_intent")
    
    # Map sub_intent to node name
    node_mapping = {
        SubIntents.SEARCH_MATERIAL: SubIntents.SEARCH_MATERIAL,
        SubIntents.CORRECT_EXERCISE: SubIntents.CORRECT_EXERCISE,
        SubIntents.CREATE_EXERCISE: SubIntents.CREATE_EXERCISE,
        SubIntents.TUTOR_SUBJECT: SubIntents.TUTOR_SUBJECT,
    }
    
    result = node_mapping.get(sub_intent, SubIntents.SEARCH_MATERIAL)  # Default to health_advice
    logger.debug(f"Routing from sub_intent_classification to: {result} (sub_intent: {sub_intent})")
    return result


def _build_agent_graph_internal(
    llm: Optional[BaseChatModel] = None,
    version: str = "v1",
) -> CompiledStateGraph:
    """
    Internal function to build and compile the medical Agent graph DYNAMICALLY.
    
    This function does the actual graph construction and should only be called
    by the cached wrapper build_agent_graph().

    NO HARDCODING! Graph structure determined by:
    - Node registry (@node_register decorators)
    - Node metadata (produces, needs_builders)
    - Builder registry (data_type → builder functions)

    Architecture:
    1. Auto-register all nodes from registry
    2. Create shared builder nodes (polymorphic)
    3. Wire edges based on metadata
    4. Register builders at startup

    Args:
        llm: Language model (will create from config if not provided)
        version: Config version to use (default: "v1")
        
    Returns:
        Compiled LangGraph with dynamic node/edge configuration
    """
    logger.info(f"🏗️  Building medical Agent graph DYNAMICALLY (version: {version})...")

    # Create LLM if not provided
    if llm is None:
        llm = create_agent_llm_client(version=version)

    # Get registered nodes from registry
    registered_nodes = list_nodes()
    logger.info(f"📦 Found {len(registered_nodes)} registered nodes")

    # Initialize graph
    graph_builder = StateGraph(GraphState)
    
    # ========================================================================
    # STEP 1: Add ALL domain nodes dynamically
    # ========================================================================

    domain_nodes = []
    classification_node = None

    for node_info in registered_nodes:
        node_name = node_info["name"]
        node_class = node_info["class"]
        metadata = node_info.get("metadata")

        # Create instance
        node_instance = node_class(llm=llm)

        # Add to graph
        graph_builder.add_node(node_name, node_instance.run)

        # Track node types
        if node_name == "sub_intent_classification":
            classification_node = node_name
        else:
            domain_nodes.append(node_name)

        if metadata:
            logger.info(
                f"  ✅ {node_name}: produces={metadata.produces_data_types}, "
                f"needs={metadata.needs_builders}"
            )
        else:
            logger.info(f"  ✅ {node_name}")

    # ========================================================================
    # STEP 2: Wire edges DYNAMICALLY based on metadata
    # ========================================================================

    # Entry point
    if classification_node:
        graph_builder.set_entry_point(classification_node)
        logger.info(f"🚀 Entry point: {classification_node}")

    # Classification → domain nodes (dynamic routing)
    if classification_node and domain_nodes:
        path_map = {node: node for node in domain_nodes}

        graph_builder.add_conditional_edges(
            source=classification_node,
            path=_route_to_node,
            path_map=path_map
        )

        logger.info(f"🔀 Dynamic routing: {classification_node} → {domain_nodes}")

    # All domain nodes eventually → END
    for node_info in registered_nodes:
        node_name = node_info["name"]
        if node_name != "sub_intent_classification":
            graph_builder.add_edge(node_name, "__end__")

    # ========================================================================
    # STEP 3: Compile graph
    # ========================================================================

    graph = graph_builder.compile()
    logger.info("✅ Graph compiled successfully (metadata-driven, zero hardcoding!)")

    return graph


@lru_cache(maxsize=4)
def build_agent_graph(
    version: str = "v1",
    llm: Optional[BaseChatModel] = None,
) -> CompiledStateGraph:
    """
    Build and compile the medical Agent graph with LRU caching.
    
    This is the PUBLIC API - it wraps _build_agent_graph_internal() with caching.
    Graphs are cached by version string. Same version = same graph instance.
    
    ⚠️ IMPORTANT: llm parameter is NOT part of cache key!
    If llm=None, a new LLM will be created inside _build_agent_graph_internal().
    To ensure cache hits, always pass version parameter and let LLM be created internally.
    
    Args:
        version: Config version (default: "v1"). This is the CACHE KEY.
        llm: Optional pre-created LLM (not recommended, breaks caching)
        
    Returns:
        Cached compiled graph for the given version
        
    Example:
        >>> graph1 = build_agent_graph(version="v1")  # Cache miss - builds graph
        >>> graph2 = build_agent_graph(version="v1")  # Cache hit - returns same instance
        >>> graph1 is graph2
        True
    """
    logger.debug(f"build_agent_graph called with version={version}, checking cache...")
    return _build_agent_graph_internal(llm=llm, version=version)


def get_graph_cache_info():
    """Get cache statistics for build_agent_graph."""
    return build_agent_graph.cache_info()


@lru_cache(maxsize=4)
def _get_cached_graph(version: str) -> CompiledStateGraph:
    """
    DEPRECATED: Use build_agent_graph() instead.
    
    Kept for backward compatibility with tests.
    """
    return _build_agent_graph_internal(version=version)
