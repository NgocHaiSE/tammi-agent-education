"""Subgraph package initialization - registers all nodes."""

# Import all nodes to trigger @register_node decorator
from agent.graph.node_services.search_material.subgraph.nodes.query_analysis_node import QueryAnalysisNode
from agent.graph.node_services.search_material.subgraph.nodes.image_analysis_node import ImageAnalysisNode
from agent.graph.node_services.search_material.subgraph.nodes.reasoning_node import ReasoningNode

__all__ = [
    "QueryAnalysisNode",
    "ImageAnalysisNode",
    "ReasoningNode",
]
