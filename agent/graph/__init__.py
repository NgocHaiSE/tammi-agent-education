"""
LangGraph implementation for Education Agent.

This module provides the graph-based architecture for the education agent,
supporting both streaming and non-streaming execution modes.

Main exports:
- GraphState: State definition for the graph
- NodeBase: Base class for all nodes
- node_register: Decorator for registering nodes
- get_education_graph: Function to build and retrieve the graph
"""

from .graph_state import GraphState, GraphState
from .node_base import NodeBase
# Import module first to avoid name conflict
from . import node_register as node_register_module
# Then import functions
from .node_register import (
    node_register,
    get_node_class,
    get_node_metadata,
    list_nodes,
)
from .graph_builder import (
    build_agent_graph
)

__all__ = [
    # State
    "GraphState",
    "GraphState",
    
    # Node base
    "NodeBase",
    
    # Node registration
    "node_register",
    "node_register_module",  # Module export for testing
    "get_node_class",
    "get_node_metadata",
    "list_nodes",

    # Graph building
    "build_agent_graph"
]
