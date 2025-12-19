"""State definition for the Medical Assistant Subgraph.
This module defines the `SubgraphMedicalState` typed dictionary, which holds
the state information passed between nodes in the Medical Assistant Subgraph.
"""

from dataclasses import field
from typing import Annotated, List, TypedDict, Optional, Dict
from langchain_core.messages import BaseMessage
import operator

from agent.graph.graph_state import GraphState


class SubgraphHealthAdviceState(TypedDict):
    """State for the Medical Assistant Subgraph.
    This typed dictionary combines selected fields from `HouseholdState`
    with additional fields used by the subgraph, such as collected node
    responses.
    Attributes:
        state (HouseholdState): The current household state, used as the
            base context for the subgraph execution.
        node_responses (Annotated[List[BaseMessage], operator.add]):
            A list of messages returned by nodes during state graph
            execution. Messages are accumulated across node executions.
    """
    state: GraphState = field(default_factory=GraphState)

    # Data returned from graph nodes
    node_responses: Annotated[List[BaseMessage], operator.add] = field(
        default_factory=list,
        metadata={
            "description": (
                "List of responses from nodes in the state graph."
            )
        }
    )

    question_type: str = field(default="", metadata={
        "description": (
            "Type of the user's question, e.g., 'event_creation', 'event_update', etc."
        )
    })
    
    # Summary of retrieval results
    retrieval_summary: Optional[Dict] = field(default_factory=dict, metadata={
        "description": (
            "Summary of retrieval results from the RetrievalNode."
        )
    })
    
    health_report: Optional[str] = field(default="", metadata={
        "description": (
            "Health report generated from the QueryAnalysisNode."
        )
    })