"""
LLM Service - Flexible service to manage and create LLM clients.

Ported from old_code with adapted imports for agent/ structure.
Supports multiple providers (Azure, OpenAI, Ollama, custom APIs) with caching and observability.
"""
import json
import os
from agent.utils.logging import get_logger
from agent.utils.performance import trace_span
from functools import lru_cache
from typing import Any, Dict, Optional

import httpx
from langchain.chat_models import init_chat_model
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from agent.llm_service.llm_callback_handler import LoggingLLMCallbackHandler, Verbosity

logger = get_logger(__name__)


class LLMService:
    """
    Flexible service to manage and create LLM clients (e.g., OpenAI, Azure, custom APIs)
    based on dynamic configuration.

    Configuration file format (JSON):
    {
        "providerKey": {
            "type": "openai",                        # Type of client (openai, azure)
            "model_available": ["gpt-4", "gpt-3.5"], # Supported models
            "default_model": "gpt-4",               # Default model to use
            "api_key_env": "OPENAI_API_KEY",        # Environment variable for API key (optional)
            "api_key": null,                        # Optional hardcoded API key
            "endpoint": null,                       # Direct endpoint URL (e.g., for Ollama or custom APIs)
            "proxy": null                           # Proxy configuration (optional, e.g., "http://proxy:3128")
        }
    }
    """

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()
        # Cache for initialized clients to avoid repeated expensive initialization
        self._client_cache: Dict[str, Any] = {}
        # Cache for HTTP clients to reuse connections
        self._http_client_cache: Dict[str, httpx.Client] = {}
        self._async_http_client_cache: Dict[str, httpx.AsyncClient] = {}

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from a JSON file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def get_client(self, provider_key: Optional[str] = None, model: Optional[str] = None, **kwargs):
        """
        Get a LangChain client based on the provider configuration.
        Uses caching to avoid expensive re-initialization.

        Args:
            provider_key (Optional[str]): The provider name (e.g., "openai", "azure"). If None, will be resolved from model/default_provider.
            model (Optional[str]): The specific model/deployment name to use. Must be in 'provider:model' format (from config logic).
        Returns:
            LangChain BaseChatModel: LangChain-compliant client (e.g., `ChatOpenAI` or `AzureChatOpenAI`).
        """
        with trace_span("llm_service_get_client") as span:
            # --- Provider/model resolution logic ---
            resolved_provider = provider_key
            resolved_model = model
            
            # Always expect model as 'provider:model' (from config loader logic)
            if model and ":" in model:
                resolved_provider, resolved_model = model.split(":", 1)
            if not resolved_provider:
                # Fallback to 'azure' if not specified
                resolved_provider = "azure"
            
            span.add_metadata(
                provider=resolved_provider,
                model=resolved_model,
                has_kwargs=len(kwargs) > 0
            )
            
            if resolved_provider not in self.config:
                span.add_metadata(error="provider_not_found")
                raise ValueError(f"Provider '{resolved_provider}' not found in configuration.")

            provider_config = self.config[resolved_provider]
            provider_type = provider_config.get("type", "openai").lower()
            deployments = provider_config.get("deployments", [])

            # Generate cache key including kwargs for uniqueness
            kwargs_key = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = f"{resolved_provider}:{resolved_model}:{kwargs_key}" if kwargs_key else f"{resolved_provider}:{resolved_model}"

            # Return cached client if available
            if cache_key in self._client_cache:
                logger.debug(f"Returning cached LLM client for {cache_key}")
                span.add_metadata(cache_hit=True, cache_key=cache_key)
                return self._client_cache[cache_key]

            logger.debug(f"Creating new LLM client for {cache_key}")
            span.add_metadata(cache_hit=False, provider_type=provider_type)

        # Deployment lookup logic:
        # 1. Try to match by 'name' field.
        # 2. If not found, try to match by 'model' field.
        # 3. If still not found and only one deployment exists, use it.
        # 4. If ambiguous or not found, raise an error.
        deployment = None
        matched_by_name = [d for d in deployments if d.get("name") == resolved_model]
        matched_by_model = [d for d in deployments if d.get("model") == resolved_model]

        if matched_by_name and matched_by_model:
            # If both match and are not the same deployment, raise an error
            # (e.g., resolved_model matches both a name and a model in different deployments)
            # If they are the same deployment, that's fine.
            deployments_set = set(id(d) for d in matched_by_name + matched_by_model)
            if len(deployments_set) > 1:
                raise ValueError(
                    f"Ambiguous deployment lookup for '{resolved_model}': matches both 'name' and 'model' fields in different deployments."
                )
            deployment = matched_by_name[0]  # or matched_by_model[0], they're the same
        elif matched_by_name:
            if len(matched_by_name) > 1:
                raise ValueError(
                    f"Multiple deployments found with name '{resolved_model}'. Please specify a unique deployment."
                )
            deployment = matched_by_name[0]
        elif matched_by_model:
            if len(matched_by_model) > 1:
                raise ValueError(
                    f"Multiple deployments found with model '{resolved_model}'. Please specify a unique deployment."
                )
            deployment = matched_by_model[0]
        elif len(deployments) == 1:
            deployment = deployments[0]
        else:
            raise ValueError(
                f"No deployment found for provider '{resolved_provider}' and model '{resolved_model}'."
            )

        model_name = deployment.get("model") or deployment.get("name")
        api_key = deployment.get("api_key") or os.getenv(deployment.get("api_key_env", ""))
        if not api_key:
            raise ValueError(
                f"API key for provider '{resolved_provider}' deployment '{model_name}' is missing. "
                f"Set environment variable '{deployment.get('api_key_env')}' or update the config."
            )

        # Extract endpoint (if any) - check deployment first, then provider
        # Support both endpoint_env and base_url_env for backwards compatibility
        endpoint = (deployment.get("endpoint") or 
                   os.getenv(deployment.get("endpoint_env", "")) or
                   os.getenv(deployment.get("base_url_env", "")) or
                   provider_config.get("endpoint") or 
                   os.getenv(provider_config.get("endpoint_env", "")) or
                   os.getenv(provider_config.get("base_url_env", "")))
        
        # Treat empty string as None (no custom endpoint)
        if endpoint:
            endpoint = endpoint.strip()
            if not endpoint:  # If it becomes empty after stripping
                endpoint = None

        # Get or create cached HTTP clients
        proxy = provider_config.get("proxy")
        http_client_key = f"{resolved_provider}:{proxy}" if proxy else resolved_provider

        if http_client_key not in self._http_client_cache:
            self._http_client_cache[http_client_key] = httpx.Client(proxy=proxy, verify=False) if proxy else httpx.Client(verify=False)

        if http_client_key not in self._async_http_client_cache:
            self._async_http_client_cache[http_client_key] = httpx.AsyncClient(proxy=proxy, verify=False) if proxy else httpx.AsyncClient(verify=False)

        http_client = self._http_client_cache[http_client_key]
        async_http_client = self._async_http_client_cache[http_client_key]

        handler = LoggingLLMCallbackHandler(
            logger=logger,
            verbosity=Verbosity.MINIMAL,  # change here to NORMAL, MINIMAL, DEBUG
            redact_patterns=[r"sk-[A-Za-z0-9-]+", r"api_key=[A-Za-z0-9=-]+"],
            external_sink=None,  # or provide your function to push metrics/logs
        )

        # Create corresponding client based on type
        client = None

        if provider_type == "openai":
            if endpoint:
                logger.info(f"Creating OpenAI client WITH custom endpoint: {endpoint}")
                client = ChatOpenAI(
                    model=resolved_model,
                    api_key=api_key,
                    base_url=endpoint,
                    http_client=http_client,
                    http_async_client=async_http_client,
                    callbacks=[handler],
                    **kwargs
                )
            else:
                # When no custom endpoint, don't pass custom http clients
                # to avoid empty base_url issue in OpenAI SDK
                logger.info(f"Creating OpenAI client WITHOUT custom endpoint (using default)")
                client = ChatOpenAI(
                    model=resolved_model,
                    api_key=api_key,
                    http_client=http_client,
                    http_async_client=async_http_client,
                    callbacks=[handler],
                    **kwargs
                )
        elif provider_type == "azure":
            if not endpoint:
                raise ValueError(
                    f"Azure OpenAI configuration requires an endpoint. Ensure it is set for '{resolved_provider}'.")

            # Get deployment name - check for env override first
            deployment_name = resolved_model
            deployment_name_env = deployment.get("deployment_name_env")
            if deployment_name_env:
                env_override = os.getenv(deployment_name_env)
                if env_override:
                    deployment_name = env_override
                    logger.debug(f"Using Azure deployment name override from {deployment_name_env}: {deployment_name}")
            
            # Get API version if specified - check deployment first, then provider
            api_version = (deployment.get("api_version") or 
                          os.getenv(deployment.get("api_version_env", "")) or
                          provider_config.get("api_version") or 
                          os.getenv(provider_config.get("api_version_env", "")))

            client = AzureChatOpenAI(
                azure_deployment=deployment_name,  # Use deployment name (with env override)
                api_key=api_key,  # Use api_key, not credential
                azure_endpoint=endpoint,  # Use azure_endpoint, not base_url
                api_version=api_version,
                model=model_name,
                http_client=http_client,
                http_async_client=async_http_client,
                # callbacks=[handler],
                **kwargs
            )
        elif provider_type == "openai_compatible":
            # Handle OpenAI-compatible endpoints (Ollama, OpenRouter, vLLM, LiteLLM, etc.)
            if not endpoint:
                raise ValueError(
                    f"OpenAI-compatible provider '{resolved_provider}' requires a base_url. "
                    f"Set environment variable '{deployment.get('base_url_env')}' or update the config."
                )
            
            # For OpenAI-compatible, api_key might be optional (e.g., Ollama) or placeholder
            # Use the model name from deployment config
            client = ChatOpenAI(
                model=model_name,
                api_key=api_key or "not-needed",  # Some endpoints don't require real key
                base_url=endpoint,
                http_client=http_client,
                http_async_client=async_http_client,
                callbacks=[handler],
                **kwargs
            )
            logger.info(f"Created OpenAI-compatible client for {resolved_provider} with endpoint {endpoint}")
        elif provider_type == "google":
            # Handle Google Gemini models
            if not api_key:
                raise ValueError(
                    f"Google Gemini provider '{resolved_provider}' requires an API key. "
                    f"Set environment variable '{deployment.get('api_key_env')}' or update the config."
                )
            
            client = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                callbacks=[handler],
                **kwargs
            )
            logger.info(f"Created Google Gemini client for model {model_name}")
        else:
            # Fallback to init_chat_model for other provider types
            params = {"model": f"{provider_type}:{model_name}", "callbacks": [handler]}
            if api_key:
                params["credential"] = api_key
                params["api_key"] = api_key
            if endpoint:
                params["endpoint"] = endpoint
                params["base_url"] = endpoint
            params.update(kwargs)

            client = init_chat_model(**params)
            logger.info(f"Created LLM client using init_chat_model for {provider_type}:{model_name}")

        # Cache the client before returning
        if client:
            self._client_cache[cache_key] = client
            logger.debug(f"Cached new LLM client for {cache_key}")

        return client

    @lru_cache(maxsize=128)
    def get_client2(self, provider_model: str, **kwargs):
        """
        Accepts 'provider:model' (from config logic). If only model is given, uses 'azure' as default provider.
        """
        if ":" in provider_model:
            provider, model = provider_model.split(":", 1)
        else:
            provider, model = "azure", provider_model
        return self.get_client(provider_key=provider, model=model, **kwargs)
    
    def list_providers(self) -> Dict[str, Any]:
        """List all available providers and their configuration."""
        return self.config
