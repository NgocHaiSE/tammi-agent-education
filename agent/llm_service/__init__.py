"""
LLM Service Module - Centralized LLM client management with multi-provider support.

This module provides:
- LLMService: Multi-provider LLM client factory
- LLMConfigService: Version-based configuration management  
- LoggingLLMCallbackHandler: Observability and logging
- Helper functions: create_agent_llm_client (recommended), create_service_llm_client, get_llm_config_service
"""

from agent.llm_service.llm_service import LLMService
from agent.llm_service.llm_callback_handler import LoggingLLMCallbackHandler, Verbosity
from agent.llm_service.llm_config_service import (
    LLMConfigService,
    get_llm_config_service,
    create_service_llm_client,
    create_agent_llm_client,  # Recommended: generic for all agents
    create_medical_llm_client,  # Backward compatibility: specific for medical
    get_llm_service,
)

__all__ = [
    "LLMService",
    "LLMConfigService",
    "LoggingLLMCallbackHandler",
    "Verbosity",
    "get_llm_config_service",
    "create_service_llm_client",
    "create_agent_llm_client",  # Recommended for new code
    "create_medical_llm_client",  # Backward compatibility
    "get_llm_service",
]
