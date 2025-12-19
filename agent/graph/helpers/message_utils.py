"""
Message utilities for converting between formats.

Provides:
- Conversion from dict/list to LangChain message format
- Message type detection and handling
"""

import logging
from typing import List, Union, Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage

logger = logging.getLogger(__name__)


def convert_to_langchain_messages(
    messages: Union[List[Dict[str, str]], List[BaseMessage]],
) -> List[BaseMessage]:
    """
    Convert messages to LangChain format.
    
    Args:
        messages: List of dicts with 'role' and 'content' keys,
                 or list of LangChain BaseMessage objects
    
    Returns:
        List of LangChain BaseMessage objects
    """
    if not messages:
        return []
    
    result = []
    
    for msg in messages:
        if isinstance(msg, BaseMessage):
            # Already LangChain format
            result.append(msg)
        elif isinstance(msg, dict):
            # Convert dict to LangChain message
            role = msg.get("role", "user").lower()
            content = msg.get("content", "")
            
            if role == "system":
                result.append(SystemMessage(content=content))
            elif role == "assistant" or role == "ai":
                result.append(AIMessage(content=content))
            else:  # "user" or default
                result.append(HumanMessage(content=content))
        else:
            logger.warning(f"Unknown message type: {type(msg)}, skipping")
    
    return result


def build_message_list(
    system_prompt: str,
    user_input: str,
    history_messages: List[BaseMessage] = None,
) -> List[BaseMessage]:
    """
    Build a complete message list for LLM invocation.
    
    Args:
        system_prompt: System prompt content
        user_input: User's input/question
        history_messages: Optional previous conversation messages
    
    Returns:
        List of BaseMessage objects in order: [system, ...history, user]
    """
    messages = []
    
    # Add system prompt
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    
    # Add history
    if history_messages:
        messages.extend(history_messages)
    
    # Add user input
    if user_input:
        messages.append(HumanMessage(content=user_input))
    
    return messages


def format_for_tts(text: str, max_length: int = 500) -> str:
    """
    Format text for text-to-speech.
    
    - Truncate if too long
    - Remove certain formatting
    
    Args:
        text: Original text
        max_length: Max length for TTS (default 500 chars)
    
    Returns:
        Formatted text suitable for TTS
    """
    if len(text) > max_length:
        # Truncate at sentence boundary if possible
        truncated = text[:max_length]
        last_period = truncated.rfind('.')
        if last_period > max_length * 0.8:  # If period is reasonably close
            return truncated[:last_period + 1]
        return truncated + "..."
    
    return text
