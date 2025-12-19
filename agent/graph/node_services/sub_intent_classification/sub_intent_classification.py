"""
Sub-intent classification node.

Classifies sub-intent if not provided in request.
Uses IntentRouter with Vector DB semantic search and keyword fallback.
"""

import logging
from langchain_core.language_models import BaseChatModel

from agent.graph.node_base import NodeBase
from agent.graph.node_register import node_register
from agent.graph.graph_state import GraphState
from agent.intent_router.intent_routing import get_intent_router

logger = logging.getLogger(__name__)


@node_register(
    name="sub_intent_classification",
    priority=100,
    produces=[],  # Only routes, doesn't produce data
    needs_builders=[],  # No builders needed
    parallel_suggestions=False  # Classification happens first
)
class SubIntentClassificationNode(NodeBase):
    """
    Sub-intent classification node.
    
    Classifies sub-intent if not provided in request.
    Uses IntentRouter for semantic-based routing with Vector DB and keyword matching fallback.
    """
    
    def __init__(self, llm: BaseChatModel, **kwargs):
        super().__init__(name="sub_intent_classification", llm=llm, **kwargs)
        self.intent_router = get_intent_router()
    
    async def run(self, state: GraphState) -> dict:
        """
        Classify sub-intent based on user input.
        
        If sub_intent is already provided in request.payload, return as-is.
        Otherwise, use IntentRouter to classify based on semantic similarity
        and keyword patterns.
        """
        from langchain_core.messages import AIMessage
        
        request = state.get("request", {})
        payload = request.get("payload", {})
        sub_intent = payload.get("sub_intent")
        
        # If sub_intent already provided, pass through
        # Education intents
        if sub_intent in ["create_exercise", "search_material", "correct_exercise", "tutor_subject",
                          # Medical intents (legacy)
                          "health_advice", "diet_recommendation", "exercise_recommendation", 
                          "book_appointment", "purchase_medicine", "health_record"]:
            logger.info(f"Sub-intent already provided: {sub_intent}")
            return {
                "request": {
                    **request,
                    "payload": {
                        **payload,
                        "sub_intent": sub_intent,
                    }
                }
            }
        
        # Get user input for routing (from payload.content)
        user_input = payload.get("content", "")
        
        if not user_input:
            logger.warning("No user input provided in payload for sub-intent classification")
            return {
                "request": {
                    **request,
                    "payload": {
                        **payload,
                        "sub_intent": "health_advice",  # Default fallback
                    }
                }
            }
        
        try:
            # Use IntentRouter to classify sub-intent
            classified_intent = await self.intent_router.route_intent(user_input)
            
            logger.info(f"Classified sub-intent: {classified_intent}")
            
            return {
                "request": {
                    **request,
                    "payload": {
                        **payload,
                        "sub_intent": classified_intent,
                    }
                }
            }
        
        except Exception as e:
            logger.error(f"Error in sub-intent classification: {e}", exc_info=True)
            # Default to health_advice on error
            default_intent = "health_advice"
            return {
                "request": {
                    **request,
                    "payload": {
                        **payload,
                        "sub_intent": default_intent,
                    }
                }
            }
