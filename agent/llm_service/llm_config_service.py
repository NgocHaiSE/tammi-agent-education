"""
Centralized LLM Configuration Service for medical Agent.

Ported from old_code with adapted imports for agent/ structure.
Provides version-based LLM configuration management with multi-provider fallback support.
"""
import os
from agent.utils.logging import get_logger
from typing import Dict, Any, Optional, List
from functools import lru_cache

from langchain_openai import ChatOpenAI

from agent.config.version_loader import load_version_config
from agent.llm_service.llm_service import LLMService
from agent.config.settings import get_settings

logger = get_logger(__name__)


class LLMConfigService:
    """Service to manage LLM configurations for all agent services."""
    
    def __init__(self, version: str = "v1"):
        self.version = version
        self.version_config = load_version_config(version)
    
    def get_service_llm_config(self, service_name: str) -> Dict[str, Any]:
        """
        Get LLM configuration for a specific service.
        
        Returns provider-centric config with model and backup_models as dicts.
        
        Args:
            service_name: Name of the service (e.g., "medical_agent")
            
        Returns:
            Dict with keys: model, backup_models, temperature, max_tokens, available_models
        """
        config = self.version_config.get_llm_config(service_name, "service")
        # Always expect model and backup_models as dict(s) - no single provider assumption
        model = config.get("model", {"name": "gpt-4o-mini", "provider": "azure"})
        backup_models = config.get("backup_models", [
            {"name": "gpt-4o", "provider": "azure"},
            {"name": "gpt-4o-mini", "provider": "azure"}
        ])
        # Remove single provider assumption - each model has its own provider
        return {
            "model": model,
            "backup_models": backup_models,
            "temperature": config.get("temperature", 0.7),
            "max_tokens": config.get("max_tokens", 1000),
            "available_models": config.get("available_models", []),
        }
    
    def create_llm_client(self, service_name: str, **model_kwargs) -> ChatOpenAI:
        """
        Create an LLM client with fallbacks for a specific service.
        
        Supports multi-provider configuration with automatic fallback chaining.
        
        Args:
            service_name: Name of the service
            **model_kwargs: Additional model configuration (temperature, max_tokens, etc.)
            
        Returns:
            ChatOpenAI client with configured fallbacks
        """
        config = self.get_service_llm_config(service_name)
        temperature = model_kwargs.get("temperature", config["temperature"])
        max_tokens = model_kwargs.get("max_tokens", config["max_tokens"])
        main_model = config["model"]
        backup_models = config["backup_models"]
        model_config = {
            "temperature": temperature,
            "max_tokens": max_tokens,
            **model_kwargs
        }
        llm_service = get_llm_service(self.version)
        
        # Compose provider:model string for main and backups - each can have different providers
        def to_provider_model_str(model_dict):
            return f"{model_dict.get('provider', 'openai')}:{model_dict.get('name', 'gpt-4o-mini')}"
        
        main_model_str = to_provider_model_str(main_model)
        backup_model_strs = [to_provider_model_str(bm) for bm in backup_models]
        
        # Try to create main client - if it fails (e.g., missing Azure credentials),
        # try first available backup as main instead
        main_client = None
        fallback_clients = []
        all_model_strs = [main_model_str] + backup_model_strs
        
        for i, model_str in enumerate(all_model_strs):
            try:
                client = llm_service.get_client2(model_str, **model_config)
                if main_client is None:
                    # First successful client becomes main
                    main_client = client
                    logger.info(f"Using {model_str} as main LLM for {service_name}")
                else:
                    # Subsequent successful clients become fallbacks
                    fallback_clients.append(client)
            except Exception as e:
                logger.warning(f"Failed to create client for {model_str}: {e}")
        
        if main_client is None:
            raise ValueError(f"No valid LLM provider available for {service_name}. Please configure API keys.")
        
        # Attach fallbacks if any
        if fallback_clients:
            main_client = main_client.with_fallbacks(fallback_clients)
        
        providers_used = [main_model.get('provider')] + [bm.get('provider') for bm in backup_models]
        logger.info(f"Created LLM client for {service_name} with model {main_model_str} and {len(fallback_clients)} fallbacks across providers: {list(set(providers_used))}")
        return main_client
    
    def get_model_hierarchy(self, service_name: str) -> List[str]:
        """
        Get the complete model hierarchy for a service (main + backups) as provider:model strings.
        
        Args:
            service_name: Name of the service
            
        Returns:
            List of "provider:model" strings in fallback order
        """
        config = self.get_service_llm_config(service_name)
        def to_provider_model_str(model_dict):
            return f"{model_dict.get('provider', 'azure')}:{model_dict.get('name', 'gpt-4o-mini')}"
        return [to_provider_model_str(config["model"])] + [to_provider_model_str(bm) for bm in config["backup_models"]]
    
    def update_version(self, version: str):
        """
        Update the version configuration.
        
        Args:
            version: New version to use
        """
        self.version = version
        self.version_config = load_version_config(version)
        logger.info(f"Updated LLMConfigService to version: {version}")


# Global instance - can be updated per request
_llm_config_service: Optional[LLMConfigService] = None


def get_llm_config_service(version: str = "v1") -> LLMConfigService:
    """
    Get the LLM configuration service for a specific version.
    
    Args:
        version: Version to use for configuration
        
    Returns:
        LLMConfigService instance for the specified version
    """
    global _llm_config_service
    
    # Create new instance if version changed or doesn't exist
    if _llm_config_service is None or _llm_config_service.version != version:
        _llm_config_service = LLMConfigService(version)
    
    return _llm_config_service


def create_service_llm_client(
    service_name: Optional[str] = None, 
    version: str = "v1", 
    **model_kwargs
) -> ChatOpenAI:
    """
    Convenience function to create an LLM client for any agent service.
    
    Generic function that works with any agent type.
    Service name defaults to configured AGENT_SERVICE_NAME from settings.
    
    Args:
        service_name: Name of the service (default: from AGENT_SERVICE_NAME env var or "medical_agent")
        version: Version configuration to use (default: "v1")
        **model_kwargs: Additional model configuration parameters (temperature, max_tokens, etc.)
        
    Returns:
        ChatOpenAI client with configured fallbacks
        
    Example:
        >>> # Simple usage - use defaults from environment
        >>> llm = create_service_llm_client()
        
        >>> # Override temperature
        >>> llm = create_service_llm_client(temperature=0.8)
        
        >>> # Use different version
        >>> llm = create_service_llm_client(version="dev")
        
        >>> # Specify service explicitly
        >>> llm = create_service_llm_client(service_name="weather_agent")
    """
    # Get default service name from settings if not provided
    if service_name is None:
        from agent.config.settings import get_settings
        settings = get_settings()
        service_name = settings.AGENT_SERVICE_NAME
    
    config_service = get_llm_config_service(version)
    return config_service.create_llm_client(service_name, **model_kwargs)


def create_agent_llm_client(version: str = "v1", **model_kwargs) -> ChatOpenAI:
    """
    Generic helper for creating LLM clients for any agent.
    
    This is the recommended way to create LLM clients in this codebase.
    Uses AGENT_SERVICE_NAME from environment or defaults to "medical_agent".
    
    Args:
        version: Version configuration to use (default: "v1")
        **model_kwargs: Additional model configuration (temperature, max_tokens, etc.)
        
    Returns:
        ChatOpenAI client with configured fallbacks
        
    Example:
        >>> from agent.llm_service import create_agent_llm_client
        >>> 
        >>> # Use default settings from v1.yaml
        >>> llm = create_agent_llm_client()
        >>> 
        >>> # Override temperature for more creative responses
        >>> llm = create_agent_llm_client(temperature=0.9)
    """
    return create_service_llm_client(service_name=None, version=version, **model_kwargs)


def create_medical_llm_client(version: str = "v1", **model_kwargs) -> ChatOpenAI:
    """
    Simplified helper specifically for medical agent.
    
    DEPRECATED: Use create_agent_llm_client() instead.
    Kept for backward compatibility with existing code.
    
    Args:
        version: Version configuration to use (default: "v1")
        **model_kwargs: Additional model configuration (temperature, max_tokens, etc.)
        
    Returns:
        ChatOpenAI client with configured fallbacks
        
    Example:
        >>> from agent.llm_service import create_medical_llm_client
        >>> 
        >>> # Use default settings from v1.yaml
        >>> llm = create_medical_llm_client()
        >>> 
        >>> # Override temperature for more creative responses
        >>> llm = create_medical_llm_client(temperature=0.9)
    """
    return create_service_llm_client(service_name="medical_agent", version=version, **model_kwargs)


@lru_cache(maxsize=4)
def get_llm_service(version: str = "v1") -> LLMService:
    """
    Get LLM service instance with version-specific configuration.
    
    Args:
        version: Configuration version to use (v1, dev, demo, etc.)
        
    Returns:
        Configured LLMService instance
    """
    settings = get_settings()
    config_path = settings.LLM_CONFIG_PATH if hasattr(settings, 'LLM_CONFIG_PATH') else None
    
    if not config_path:
        # Fallback to default path
        base_dir = os.path.dirname(os.path.dirname(__file__))
        config_path = os.path.join(base_dir, "config", "llm_config.json")
    
    if not os.path.exists(config_path):
        logger.warning(f"LLM config file not found at {config_path}, LLMService will fail. Please create config file.")
    
    return LLMService(config_path=config_path)
