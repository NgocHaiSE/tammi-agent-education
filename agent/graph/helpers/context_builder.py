"""
Context builder utilities for graph nodes.

Provides:
- Location extraction from request
- Message building and prompt enhancement
- Response formatting
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Builds context information from requests for graph nodes."""
    
    @staticmethod
    def extract_location(request: Dict[str, Any]) -> str:
        """
        Extract location from request object.
        
        Tries multiple sources in priority order:
        1. payload.metadata.city
        2. user_context.city
        3. payload.metadata.location
        4. Default: "Hanoi"
        """
        payload = request.get("payload", {})
        metadata = payload.get("metadata", {})
        user_context = request.get("user_context", {})
        
        location = (
            metadata.get("city") or
            user_context.get("city") or
            metadata.get("location") or
            "Hanoi"
        )
        
        logger.debug(f"Extracted location: {location}")
        return location
    
    @staticmethod
    def extract_user_input(request: Dict[str, Any]) -> str:
        """
        Extract user input from request.
        
        Gets content from payload.content field.
        """
        payload = request.get("payload", {})
        user_input = payload.get("content", "")
        
        logger.debug(f"Extracted user input: {user_input[:50]}...")
        return user_input
    
    @staticmethod
    def build_enhanced_prompt(
        user_input: str,
        context_str: str
    ) -> str:
        """
        Build enhanced prompt with context.
        
        Combines user input with weather/context information.
        """
        return f"{user_input}\n\n{context_str}"
    
    @staticmethod
    def build_response(
        intent: str,
        sub_intent: str,
        display_message: str,
        parameters: Optional[Dict[str, Any]] = None,
        ui_elements: Optional[list] = None,
        suggestions: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Build standardized response dictionary.
        
        Returns:
            Dict compatible with formatter.build_agent_response()
        """
        return {
            "intent": intent,
            "sub_intent": sub_intent,
            "parameters": parameters or {},
            "display_message": display_message,
            "tts_message": display_message,
            "ui_elements": ui_elements or [],
            "suggestions": suggestions or [],
        }
