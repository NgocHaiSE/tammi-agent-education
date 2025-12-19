"""
Tutor Subject State Schema.

Defines the state structure for the tutor subject subgraph.
"""
from typing import TypedDict, Optional, Dict, Any, List
from langchain_core.messages import BaseMessage


class TutorSubjectState(TypedDict, total=False):
    """
    State for tutor subject subgraph.

    Flow:
    1. collect_context: Extract question and retrieve educational content via Tavily
    2. call_llm: Generate tutoring guidance using LLM
    3. format_output: Format the final response with retrieval artifacts
    """
    # Input from parent graph
    messages: List[BaseMessage]
    request: Dict[str, Any]

    # Internal state
    question: Optional[str]
    context: Optional[str]
    retrieval_summary: Optional[Dict[str, Any]]
    llm_response: Optional[BaseMessage]  # Changed: Now stores BaseMessage (AIMessage)

    # Output
    node_responses: List[BaseMessage]
    data_artifacts: Optional[Dict[str, Any]]

    # Control flow
    next_node: Optional[str]
    error_message: Optional[str]

