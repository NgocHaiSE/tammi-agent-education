"""
Create Exercise Subgraph Builder

Builds the subgraph for create exercise functionality with dynamic routing:
1. ValidationNode - Validates input and extracts parameters
2. ScopeClassifierNode - Routes to Rule-based (Tier 1) or LLM Fallback (Tier 3)
3. RuleBasedNode - Template-based generation for simple cases
4. LLMFallbackNode - LLM-based generation for complex cases
5. QualityCheckNode - Validates generated exercises
6. ResponseBuilderNode - Formats final response

Architecture:
- Entry: ValidationNode
- Router: ScopeClassifierNode (tier-based)
- Executors: RuleBasedNode OR LLMFallbackNode
- Quality: QualityCheckNode
- Output: ResponseBuilderNode
"""

import logging
from typing import Any, Dict

from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage

from agent.graph.node_services.create_exercise.subgraph.state import CreateExerciseState
from agent.graph.node_services.create_exercise.subgraph.nodes.validation_node import ValidationNode
from agent.graph.node_services.create_exercise.subgraph.nodes.scope_classifier_node import ScopeClassifierNode
from agent.graph.node_services.create_exercise.subgraph.nodes.rule_based_node import RuleBasedNode
from agent.graph.node_services.create_exercise.subgraph.nodes.llm_fallback_node import LLMFallbackNode
from agent.graph.node_services.create_exercise.subgraph.nodes.quality_check_node import QualityCheckNode
from agent.graph.node_services.create_exercise.subgraph.nodes.response_builder_node import ResponseBuilderNode
from agent.graph.node_services.create_exercise.subgraph.nodes.rag_node import RAGNode

logger = logging.getLogger(__name__)


def _transform_input_state(parent_state: Dict[str, Any]) -> CreateExerciseState:
    """
    Transform parent GraphState to CreateExerciseState.
    
    Maps fields from parent graph to subgraph state schema.
    
    Args:
        parent_state: State from parent graph (GraphState)
        
    Returns:
        CreateExerciseState with initialized fields
    """
    request = parent_state.get("request", {})
    payload = request.get("payload", {})
    metadata = payload.get("metadata", {})
    
    # Initialize subgraph state with all required fields
    subgraph_state = CreateExerciseState(
        # Input from parent
        request=request,
        history_chat=parent_state.get("history_chat", []),
        
        # Validation phase (will be filled by ValidationNode)
        validated=False,
        validation_errors=None,
        error_messages=None,
        
        grade=None,
        subject=None,
        topic=None,
        difficulty=None,
        exercise_type=None,
        num_exercises=metadata.get("num_exercises", 5),
        
        # Routing phase (will be filled by ScopeClassifierNode)
        tier=0,
        processing_method="",
        
        # Generation phase (will be filled by execution nodes)
        exercises=None,
        generation_metadata={},
        
        # Quality check phase (will be filled by QualityCheckNode)
        quality_passed=False,
        quality_issues=[],
        
        # Output (will be filled by ResponseBuilderNode)
        node_responses=[],
        suggestions=[],
        
        # Control
        next_node=None,
        
        # Context
        metadata=metadata,
        debug_info={},
        
        # Memory context (will be filled by ValidationNode from ExerciseMemory)
        last_context=None,
        exercise_history=None,
        user_preferences=None
    )
    
    logger.debug(f"Transformed parent state to subgraph state: {list(subgraph_state.keys())}")
    return subgraph_state


def _transform_output_state(subgraph_state: CreateExerciseState) -> Dict[str, Any]:
    """
    Transform CreateExerciseState back to parent GraphState format.
    
    Extracts relevant fields from subgraph to return to parent.
    
    Args:
        subgraph_state: Final state from subgraph execution
        
    Returns:
        Dict with fields to merge into parent GraphState
    """
    # Extract responses
    node_responses = subgraph_state.get("node_responses", [])
    
    # If no responses generated, create a default message
    if not node_responses:
        logger.warning("No node_responses from subgraph, creating default")
        default_message = AIMessage(
            content="Đã xử lý yêu cầu tạo bài tập.",
            additional_kwargs={"tts_message": "Đã xử lý yêu cầu tạo bài tập."}
        )
        node_responses = [default_message]
    
    # Build artifacts with exercises data
    data_artifacts = {
        "exercises": subgraph_state.get("exercises", []),
        "generation_metadata": subgraph_state.get("generation_metadata", {}),
        "quality_passed": subgraph_state.get("quality_passed", False),
        "quality_issues": subgraph_state.get("quality_issues", []),
        "tier": subgraph_state.get("tier", 0),
        "processing_method": subgraph_state.get("processing_method", ""),
    }
    
    # Include error info if validation failed
    if not subgraph_state.get("validated", False):
        data_artifacts["validation_errors"] = subgraph_state.get("validation_errors")
        data_artifacts["error_messages"] = subgraph_state.get("error_messages")
    
    logger.debug(f"Transformed subgraph state to parent format: {len(node_responses)} responses")
    
    return {
        "node_responses": node_responses,
        "data_artifacts": data_artifacts
    }


def build_create_exercise_subgraph(llm: Any, main_agent: Any = None):
    """
    Build and compile the create exercise subgraph with dynamic routing.
    
    Architecture:
    1. MetadataExtractionNode - Extract metadata from natural language content
    2. ValidationNode - Validates input and extracts parameters
    3. ScopeClassifierNode - Routes to Rule-based (Tier 1), RAG (Tier 2), or LLM Fallback (Tier 3)
    4. RuleBasedNode / RAGNode / LLMFallbackNode - Generate exercises
    5. QualityCheckNode - Validates generated exercises
    6. ResponseBuilderNode - Formats final response
    
    Args:
        llm: Language model for LLM-based nodes
        main_agent: Reference to main agent (optional, for context)
        
    Returns:
        Compiled subgraph ready for execution
    """
    from agent.graph.node_services.create_exercise.subgraph.nodes.metadata_extraction_node import MetadataExtractionNode
    from agent.graph.node_services.create_exercise.subgraph.nodes.validation_node import ValidationNode
    from agent.graph.node_services.create_exercise.subgraph.nodes.scope_classifier_node import ScopeClassifierNode
    from agent.graph.node_services.create_exercise.subgraph.nodes.rule_based_node import RuleBasedNode
    from agent.graph.node_services.create_exercise.subgraph.nodes.rag_node import RAGNode
    from agent.graph.node_services.create_exercise.subgraph.nodes.llm_fallback_node import LLMFallbackNode
    from agent.graph.node_services.create_exercise.subgraph.nodes.quality_check_node import QualityCheckNode
    from agent.graph.node_services.create_exercise.subgraph.nodes.response_builder_node import ResponseBuilderNode
    
    logger.info("Building create exercise subgraph with metadata extraction...")
    
    # Initialize nodes
    metadata_extraction_node = MetadataExtractionNode(llm=llm)
    validation_node = ValidationNode(llm=llm)
    classifier_node = ScopeClassifierNode(llm=llm)
    rule_based_node = RuleBasedNode(llm=llm)
    rag_node = RAGNode(llm=llm)
    llm_fallback_node = LLMFallbackNode(llm=llm)
    quality_check_node = QualityCheckNode(llm=llm)
    response_builder_node = ResponseBuilderNode(llm=llm)
    
    # Create state graph
    workflow = StateGraph(CreateExerciseState)
    
    # Add nodes
    workflow.add_node("metadata_extraction", metadata_extraction_node.run)
    workflow.add_node("validation", validation_node.run)
    workflow.add_node("classifier", classifier_node.run)
    workflow.add_node("rule_based", rule_based_node.run)
    workflow.add_node("rag", rag_node.run)
    workflow.add_node("llm_fallback", llm_fallback_node.run)
    workflow.add_node("quality_check", quality_check_node.run)
    workflow.add_node("response_builder", response_builder_node.run)
    
    # Set entry point
    workflow.set_entry_point("metadata_extraction")
    
    # Add edges
    # metadata_extraction → validation (always)
    workflow.add_edge("metadata_extraction", "validation")
    
    # validation → classifier OR response_builder (if validation failed)
    def route_after_validation(state: CreateExerciseState) -> str:
        if state.get("validated"):
            logger.debug("Validation passed, routing to classifier")
            return "classifier"
        else:
            logger.warning(f"Validation failed: {state.get('validation_errors')}")
            return "response_builder"
    
    workflow.add_conditional_edges(
        "validation",
        route_after_validation,
        {
            "classifier": "classifier",
            "response_builder": "response_builder"
        }
    )
    
    # classifier → rule_based OR rag OR llm_fallback
    def route_by_tier(state: CreateExerciseState) -> str:
        next_node = state.get("next_node")
        tier = state.get("tier", 3)
        
        if next_node:
            logger.debug(f"Routing to {next_node} (Tier {tier})")
            return next_node
            
        if tier == 1:
            logger.debug("Tier 1 (Rule-based) - routing to rule_based")
            return "rule_based"
        elif tier == 2:
            logger.debug("Tier 2 (RAG) - routing to rag")
            return "rag"
        else:
            logger.debug(f"Tier {tier} (LLM Fallback) - routing to llm_fallback")
            return "llm_fallback"
    
    workflow.add_conditional_edges(
        "classifier",
        route_by_tier,
        {
            "rule_based": "rule_based",
            "rag": "rag",
            "llm_fallback": "llm_fallback"
        }
    )
    
    # All generation nodes → quality_check
    workflow.add_edge("rule_based", "quality_check")
    workflow.add_edge("rag", "quality_check")
    workflow.add_edge("llm_fallback", "quality_check")
    
    # quality_check → response_builder (always, even if quality failed)
    workflow.add_edge("quality_check", "response_builder")
    
    # Response builder is the final step
    workflow.add_edge("response_builder", END)
    
    # Compile the graph
    compiled = workflow.compile()
    
    logger.info("Create exercise subgraph compiled successfully with metadata extraction")
    return compiled


async def run_create_exercise_subgraph(
    parent_state: Dict[str, Any],
    llm: Any,
    config: RunnableConfig = None
) -> Dict[str, Any]:
    """
    Execute create exercise subgraph with state transformation.
    
    This function:
    1. Transforms parent GraphState to CreateExerciseState
    2. Executes the subgraph
    3. Transforms CreateExerciseState back to parent format
    
    Args:
        parent_state: State from parent graph (GraphState)
        llm: Language model instance
        config: Optional runnable config
        
    Returns:
        Dict with node_responses and data_artifacts to merge into parent state
    """
    logger.info("🚀 Running Create Exercise Subgraph")
    
    try:
        # Step 1: Transform input state
        subgraph_input = _transform_input_state(parent_state)
        
        # Step 2: Create and execute subgraph
        subgraph = build_create_exercise_subgraph(llm)
        final_state = await subgraph.ainvoke(subgraph_input, config=config)
        
        # Step 3: Transform output state
        output = _transform_output_state(final_state)
        
        logger.info("✅ Create Exercise Subgraph completed successfully")
        return output
        
    except Exception as e:
        logger.error(f"❌ Error running create exercise subgraph: {e}", exc_info=True)
        
        # Return error response
        error_message = AIMessage(
            content=f"Xin lỗi, đã xảy ra lỗi khi tạo bài tập: {str(e)}",
            additional_kwargs={
                "tts_message": "Xin lỗi, đã xảy ra lỗi khi tạo bài tập.",
                "error": str(e)
            }
        )
        
        return {
            "node_responses": [error_message],
            "data_artifacts": {
                "error": str(e),
                "error_type": type(e).__name__
            }
        }


# Alias for backward compatibility
create_create_exercise_graph = build_create_exercise_subgraph


# Export for easy import
__all__ = [
    "build_create_exercise_subgraph",
    "create_create_exercise_graph",
    "run_create_exercise_subgraph",
]
