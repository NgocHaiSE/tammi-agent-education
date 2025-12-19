from typing import Annotated, Dict, Any, List, Optional
from typing_extensions import TypedDict
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage

class CreateExerciseState(TypedDict):
    # Input từ graph cha
    request: Dict[str, Any]
    history_chat: Annotated[List[BaseMessage], add_messages]

    # Validation phase
    validated: bool
    validation_errors: Optional[str]
    error_messages: Optional[str]

    grade: Optional[str]
    subject: Optional[str]
    topic: Optional[str]
    difficulty: Optional[str]
    exercise_type: Optional[str]
    num_exercises: int
    
    # Routing phase
    tier: int
    processing_method: str

    # Generation phase
    exercises: Optional[List[Dict[str, Any]]]
    generation_metadata: Dict[str, Any]

    # Quality check phase
    quality_passed: bool
    quality_issues: List[str]

    # Output
    node_responses: Annotated[List[BaseMessage], add_messages]
    suggestions: List[str]

    # Control
    next_node: Optional[str]    

    # Context 
    metadata: Dict[str, Any]
    debug_info: Dict[str, Any]
    
    # Memory context (optional, from ExerciseMemory)
    last_context: Optional[Dict[str, Any]]
    exercise_history: Optional[List[Dict[str, Any]]]
    user_preferences: Optional[Dict[str, Any]]