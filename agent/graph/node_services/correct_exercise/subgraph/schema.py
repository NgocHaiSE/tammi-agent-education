"""
Correct Exercise State Schema.

Defines the state structure for the correct exercise subgraph.
"""
from typing import TypedDict, Optional, Dict, Any, List, Tuple
from langchain_core.messages import BaseMessage


class CorrectExerciseState(TypedDict, total=False):
    """
    State for correct exercise subgraph.

    Flow:
    1. extract_question: Extract user question from state
    2. retrieve_context: Search Tavily for solution methods
    3. call_llm: Generate detailed corrections using LLM
    4. format_output: Format the final response
    """
    # Input from parent graph
    messages: List[BaseMessage]
    request: Dict[str, Any]

    # Internal state
    question: Optional[str]
    trace_id: Optional[str]
    combined_text: Optional[str]
    retrieval_summary: Optional[Dict[str, Any]]
    llm_response: Optional[BaseMessage]  # Changed: Now stores BaseMessage (AIMessage)

    # Output
    node_responses: List[BaseMessage]
    data_artifacts: Optional[Dict[str, Any]]

    # Control flow
    next_node: Optional[str]
    error_message: Optional[str]
