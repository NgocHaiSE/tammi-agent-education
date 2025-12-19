"""Builds the state graph for the Search Material Assistant Subgraph.
"""
import os
import logging

from typing import Any, Literal, Dict

from langgraph.graph import StateGraph
from langgraph.graph import START, END  # nếu cần

from agent.graph.node_services.search_material.subgraph.node_register import get_nodes_register
from agent.graph.node_services.search_material.subgraph.state import SubgraphHealthAdviceState

# Import to trigger node registration
import agent.graph.node_services.search_material.subgraph.nodes.query_analysis_node
import agent.graph.node_services.search_material.subgraph.nodes.image_analysis_node
import agent.graph.node_services.search_material.subgraph.nodes.reasoning_node

logger = logging.getLogger(__name__)


def build_graph(llm: Any, main_agent: Any):
    """Builds the state graph for the Search Material Assistant Subgraph.
    Args:
        llm (Any): The language model to use for generating responses.
        main_agent (Any): The main agent managing the subgraph (SearchMaterialNode).
    Returns:
        CompiledStateGraph: The constructed state graph for the Search Material Assistant Subgraph.
    Raises:
        ValueError: If no nodes are registered in the Search Material Assistant Subgraph.
    """
    nodes = get_nodes_register()
    if not nodes:
        raise ValueError("No nodes registered in the Search Material Assistant Subgraph.")
    logger.info(f"Building graph with nodes: {list(nodes.keys())}")

    nodes_run = {}

    for name, node_class in nodes.items():
        # Pass main_agent to node constructor
        async def make_node_func(state, cls=node_class, agent=main_agent):
            instance = cls(main_agent=agent)
            return await instance.run(state)
        nodes_run[name] = make_node_func

    # Path function that returns a key we will map
    def detect_question_type(state) -> Literal["image", "text"]:
        # tùy vào logic của bạn, bạn có thể trả về "image" hoặc "text"
        question_type = state.get("question_type", "text")
        if question_type == "image":
            return "image"
        return "text"
    
    # Hàm cho entry node
    async def entry_node(state: SubgraphHealthAdviceState) -> Dict[str, Any]:
        inner_state = state.get("state", {})
        request = inner_state.get("request", {})
        payload = request.get("payload", {})
        content = payload.get("content", "")
        
        # Check if content contains image URLs or if metadata has images
        metadata = payload.get("metadata", {})
        
        # Check for image in content (if it's a list with image_url type)
        if isinstance(content, list) and any(
            isinstance(item, dict) and item.get("type") == "image_url"
            for item in content
        ):
            return {"question_type": "image"}
        
        # Check for image in metadata
        if "image_url" in metadata or "images" in metadata:
            return {"question_type": "image"}
            
        return {"question_type": "text"}

    # Tạo graph
    graph = StateGraph(SubgraphHealthAdviceState)

    # Entry point
    graph.add_node("EntryNode", entry_node)
    graph.set_entry_point("EntryNode")  
    
    # Thêm reasoning node
    graph.add_node("reasoning_node", nodes_run["reasoning_node"])
    
    # Nodes xử lý image
    graph.add_node("image_analysis_node", nodes_run["image_analysis_node"])
    graph.add_edge("image_analysis_node", "reasoning_node")

    # Nodes xử lý text
    graph.add_node("query_analysis_node", nodes_run["query_analysis_node"])
    graph.add_edge("query_analysis_node", "reasoning_node")

    # conditional routing sử dụng path + path_map
    graph.add_conditional_edges(
        "EntryNode",
        detect_question_type,  # đây là path
        {
            "image": "image_analysis_node",
            "text": "query_analysis_node"
        }
    )

    return graph.compile()