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
    1. extract_input: Handle Text/Image input -> extracted_text
    2. lookup_history: Check Memory -> ground_truth / reference_context
    3. retrieve_context: Tavily Search (if needed) -> reference_context
    4. call_llm: Grade Exercise -> llm_response
    5. format_output: Format final response
    """
    # Input from parent graph
    messages: List[BaseMessage]
    request: Dict[str, Any]

    # Internal state
    raw_input: Optional[Any]        # Original input (text or payload)
    extracted_text: Optional[str]   # Text after OCR/Extraction
    question: Optional[str]         # Legacy field support
    
    student_answer: Optional[str]   # Parsed student answer
    ground_truth: Optional[str]     # Correct answer from memory
    reference_context: Optional[str] # Context from memory or search
    
    trace_id: Optional[str]
    retrieval_summary: Optional[Dict[str, Any]]
    llm_response: Optional[BaseMessage]

    # Output
    node_responses: List[BaseMessage]
    data_artifacts: Optional[Dict[str, Any]]

    # Control flow
    next_node: Optional[str]
    error_message: Optional[str]
