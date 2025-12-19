import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional
from agent.config.env_manager import get_env, get_int, get_float, get_str


@dataclass
class Settings:
    """Settings class for Education Agent. All values loaded from environment via EnvManager."""
    
    # ========================================================================
    # AZURE OPENAI CONFIGURATION
    # ========================================================================
    AZURE_OPENAI_API_KEY: str = get_env("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT: str = get_env("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_VERSION: str = get_env("AZURE_OPENAI_API_VERSION")
    
    # Azure deployment name overrides (optional)
    AZURE_OPENAI_DEPLOYMENT_GPT4O_MINI: str = get_env("AZURE_OPENAI_DEPLOYMENT_GPT4O_MINI")
    AZURE_OPENAI_DEPLOYMENT_GPT4O: str = get_env("AZURE_OPENAI_DEPLOYMENT_GPT4O")
    
    # ========================================================================
    # OPENAI CONFIGURATION
    # ========================================================================
    OPENAI_API_KEY: str = get_env("OPENAI_API_KEY")
    OPENAI_ORG_ID: str = get_env("OPENAI_ORG_ID", default="")
    OPENAI_BASE_URL: str = get_env("OPENAI_BASE_URL", default="")  # Optional custom endpoint
    
    # ========================================================================
    # OLLAMA CONFIGURATION (Local LLM)
    # ========================================================================
    OLLAMA_BASE_URL: str = get_env("OLLAMA_BASE_URL")
    OLLAMA_MODEL: str = get_env("OLLAMA_MODEL")
    
    # ========================================================================
    # OPENROUTER CONFIGURATION
    # ========================================================================
    OPENROUTER_API_KEY: str = get_env("OPENROUTER_API_KEY", default="")
    OPENROUTER_BASE_URL: str = get_env("OPENROUTER_BASE_URL")
    
    # ========================================================================
    # CUSTOM OPENAI-COMPATIBLE ENDPOINT
    # ========================================================================
    CUSTOM_OPENAI_BASE_URL: str = get_env("CUSTOM_OPENAI_BASE_URL", default="")
    CUSTOM_OPENAI_API_KEY: str = get_env("CUSTOM_OPENAI_API_KEY", default="")
    
    # ========================================================================
    # LLM CONFIGURATION PATHS
    # ========================================================================
    base_dir: str = os.path.dirname(os.path.dirname(__file__))

    LLM_CONFIG_PATH: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "llm_config.json")

    VERSION_CONFIG_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "versions")

    DEFAULT_VERSION: str = get_env("DEFAULT_LLM_VERSION")
    
    # ========================================================================
    # LEGACY COMPATIBILITY (DEPRECATED)
    # ========================================================================
    # These are kept for backward compatibility but will be removed
    # Use LLMConfigService with .env variables instead
    LLM_PROVIDER: str = get_env("LLM_PROVIDER")
    OPENAI_MODEL: str = get_env("OPENAI_MODEL")
    llm_model: str = get_env("LLM_MODEL")

    # ========================================================================
    # AGENT CONFIGURATION
    # ========================================================================
    # Agent name used for logging, service identification
    # Can be overridden via AGENT_NAME environment variable
    AGENT_NAME: str = get_env("AGENT_NAME")
    AGENT_SERVICE_NAME: str = get_env("AGENT_SERVICE_NAME")
    
    # ========================================================================
    # SERVICE SETTINGS
    # ========================================================================
    # Support both generic AGENT_* and legacy medical_* env vars for backward compatibility
    GRPC_HOST: str = get_env("AGENT_GRPC_HOST")
    GRPC_PORT: int = get_int("AGENT_GRPC_PORT")
    request_timeout_seconds: int = get_int("AGENT_REQUEST_TIMEOUT")

    # gRPC Advanced Configuration - REQUIRED
    grpc_max_concurrent_streams: int = get_int("GRPC_MAX_CONCURRENT_STREAMS")
    grpc_keepalive_time_ms: int = get_int("GRPC_KEEPALIVE_TIME_MS")
    grpc_keepalive_timeout_ms: int = get_int("GRPC_KEEPALIVE_TIMEOUT_MS")
    grpc_min_ping_interval_ms: int = get_int("GRPC_MIN_PING_INTERVAL_MS")
    grpc_max_ping_strikes: int = get_int("GRPC_MAX_PING_STRIKES")
    grpc_max_message_size_mb: int = get_int("GRPC_MAX_MESSAGE_SIZE_MB")

    # ========================================================================
    # API GATEWAY SETTINGS
    # ========================================================================
    API_GATEWAY_HTTP_URL: str = get_env("API_GATEWAY_HTTP_URL")
    API_GATEWAY_GRPC_URL: str = get_env("API_GATEWAY_GRPC_URL")
    
    # ========================================================================
    # EXTERNAL API CLIENT SETTINGS
    # ========================================================================
    EXTERNAL_CLIENT_TIMEOUT: float = get_float("EXTERNAL_CLIENT_TIMEOUT")
    EXTERNAL_CLIENT_MAX_RETRIES: int = get_int("EXTERNAL_CLIENT_MAX_RETRIES")
    CIRCUIT_BREAKER_THRESHOLD: int = get_int("CIRCUIT_BREAKER_THRESHOLD")
    CIRCUIT_BREAKER_TIMEOUT: int = get_int("CIRCUIT_BREAKER_TIMEOUT")
    
    # ========================================================================
    # SEARCH CACHE SETTINGS
    # ========================================================================
    SEARCH_CACHE_ENABLED: bool = get_env("SEARCH_CACHE_ENABLED", default="true").lower() == "true"
    SEARCH_CACHE_TTL_SECONDS: int = int(os.getenv("SEARCH_CACHE_TTL_SECONDS", 3600))
    SEARCH_CACHE_MAX_SIZE: int = int(os.getenv("SEARCH_CACHE_MAX_SIZE", 1000))
    
    # ========================================================================
    # VECTOR DATABASE CONFIGURATION
    # ========================================================================
    # Qdrant Configuration
    QDRANT_URL: str = get_env("QDRANT_URL")
    QDRANT_API_KEY: str = get_env("QDRANT_API_KEY")
    QDRANT_COLLECTION_NAME: str = get_env("QDRANT_COLLECTION_NAME")
    QDRANT_TIMEOUT: int = int(get_env("QDRANT_TIMEOUT"))
    QDRANT_PREFER_GRPC: bool = get_env("QDRANT_PREFER_GRPC").lower() == "true"
    QDRANT_GRPC_PORT: int = int(get_env("QDRANT_GRPC_PORT"))
    
    # Elasticsearch Configuration
    ELASTICSEARCH_URL: str = get_env("ELASTICSEARCH_URL")
    ELASTICSEARCH_API_KEY: str = get_env("ELASTICSEARCH_API_KEY")
    ELASTICSEARCH_USERNAME: str = get_env("ELASTICSEARCH_USERNAME")
    ELASTICSEARCH_PASSWORD: str = get_env("ELASTICSEARCH_PASSWORD")
    ELASTICSEARCH_INDEX_NAME: str = get_env("ELASTICSEARCH_INDEX_NAME")
    ELASTICSEARCH_TIMEOUT: int = get_int("ELASTICSEARCH_TIMEOUT")
    ELASTICSEARCH_VERIFY_CERTS: bool = get_env("ELASTICSEARCH_VERIFY_CERTS").lower() == "true"
    ELASTICSEARCH_CA_CERTS: str = get_env("ELASTICSEARCH_CA_CERTS")
    
    # Elasticsearch Exercise Templates Index for RAG
    ELASTICSEARCH_EXERCISE_INDEX: str = get_env("ELASTICSEARCH_EXERCISE_INDEX")
    ELASTICSEARCH_EXERCISE_TOP_K: int = get_int("ELASTICSEARCH_EXERCISE_TOP_K")
    ELASTICSEARCH_EXERCISE_SIMILARITY_THRESHOLD: float = get_float("ELASTICSEARCH_EXERCISE_SIMILARITY_THRESHOLD")
    
    # Vector DB General Settings
    VECTOR_DB_PROVIDER: str = get_env("VECTOR_DB_PROVIDER")
    VECTOR_EMBEDDING_DIM: int = get_int("VECTOR_EMBEDDING_DIM")
    VECTOR_SIMILARITY_METRIC: str = get_env("VECTOR_SIMILARITY_METRIC")
    VECTOR_TOP_K: int = get_int("VECTOR_TOP_K")
    VECTOR_SCORE_THRESHOLD: float = get_float("VECTOR_SCORE_THRESHOLD")

    # ========================================================================
    # EXERCISE GENERATION DEFAULTS
    # ========================================================================
    # Use get_env directly to support default values
    DEFAULT_GRADE: int = get_env("DEFAULT_GRADE", int, 4)
    DEFAULT_SUBJECT: str = get_env("DEFAULT_SUBJECT", str, "toán")
    DEFAULT_DIFFICULTY: str = get_env("DEFAULT_DIFFICULTY", str, "trung bình")

    # Intent Samples Vector DB Collection Name
    INTENT_SAMPLES_COLLECTION_NAME: str = get_env("INTENT_SAMPLES_COLLECTION_NAME")
    
    # Enable/disable vector DB routing (fallback to keyword matching if disabled)
    ENABLE_VECTOR_DB_ROUTING: bool = get_env("ENABLE_VECTOR_DB_ROUTING").lower() == "true"

    # ========================================================================
    # EMBEDDING SERVICE CONFIGURATION
    # ========================================================================
    # Azure Text-3 Embedding Configuration
    ENDPOINT_TEXT3_EMBEDDING: str = get_env("ENDPOINT_TEXT3_EMBEDDING", str, "")
    API_KEY_TEXT3_EMBEDDING: str = get_env("API_KEY_TEXT3_EMBEDDING", str, "")
    EMBEDDING_MODEL: str = get_env("EMBEDDING_MODEL", str, "text-embedding-3-small")
    EMBEDDING_DIMENSION: int = get_env("EMBEDDING_DIMENSION", int, 1536)
    EMBEDDING_PROVIDER: str = get_env("EMBEDDING_PROVIDER", str, "azure")

    # ========================================================================
    # PROMPT TEMPLATES
    # ========================================================================
    prompt_dir: str = os.path.join(base_dir, "prompt_templates")
    emotional_support_prompt: str = os.path.join(prompt_dir, "emotional_support.txt")

    # ========================================================================
    # LLM RETRY/BACKOFF
    # ========================================================================
    # Support both generic AGENT_* and legacy medical_* env vars
    llm_retry_count: int = get_int("AGENT_LLM_RETRY_COUNT")
    llm_backoff_base_seconds: float = get_float("AGENT_LLM_BACKOFF_BASE")

    # ========================================================================
    # GRAPH SETTINGS
    # ========================================================================
    GRAPH_CACHE_ENABLED: bool = get_env("GRAPH_CACHE_ENABLED").lower() == "true"
    GRAPH_STREAM_MODE: str = get_env("GRAPH_STREAM_MODE")
    
    # LangGraph Migration Feature Flag (Phase 0)
    # Set to "true" to use new LangGraph orchestrator
    # Set to "false" to use old if/else routing (default during migration)
    USE_LANGGRAPH_AGENT: bool = get_env("USE_LANGGRAPH_AGENT", default="false").lower() == "true"

    # ========================================================================
    # ENVIRONMENT & LOGGING
    # ========================================================================
    ENVIRONMENT: str = get_env("ENVIRONMENT")
    LOG_LEVEL: str = get_env("LOG_LEVEL")
    
    # ========================================================================
    # HELPER PROPERTIES
    # ========================================================================
    @property
    def agent_display_name(self) -> str:
        """Get formatted agent display name for service identification."""
        # Convert "medical" -> "medical_Agent"
        return f"{self.AGENT_NAME.capitalize()}_Agent"
    
    @property
    def has_azure_config(self) -> bool:
        """Check if Azure OpenAI is configured."""
        return bool(self.AZURE_OPENAI_API_KEY and self.AZURE_OPENAI_ENDPOINT)
    
    @property
    def has_openai_config(self) -> bool:
        """Check if OpenAI is configured."""
        return bool(self.OPENAI_API_KEY)
    
    @property
    def has_ollama_config(self) -> bool:
        """Check if Ollama is configured."""
        return bool(self.OLLAMA_BASE_URL)
    
    @property
    def has_openrouter_config(self) -> bool:
        """Check if OpenRouter is configured."""
        return bool(self.OPENROUTER_API_KEY)
    
    @property
    def has_custom_openai_config(self) -> bool:
        """Check if custom OpenAI-compatible endpoint is configured."""
        return bool(self.CUSTOM_OPENAI_BASE_URL and self.CUSTOM_OPENAI_API_KEY)
    
    @property
    def has_any_llm_config(self) -> bool:
        """Check if at least one LLM provider is configured."""
        return (
            self.has_azure_config or 
            self.has_openai_config or 
            self.has_ollama_config or 
            self.has_openrouter_config or
            self.has_custom_openai_config
        )
    
    def get_azure_deployment_override(self, model_name: str) -> Optional[str]:
        """
        Get Azure deployment name override from environment variables.
        
        Args:
            model_name: Model name like "gpt-4o-mini", "gpt-4o"
            
        Returns:
            Deployment name if env var is set, None otherwise
        """
        env_var_map = {
            "gpt-4o-mini": self.AZURE_OPENAI_DEPLOYMENT_GPT4O_MINI,
            "gpt-4o": self.AZURE_OPENAI_DEPLOYMENT_GPT4O,
        }
        deployment = env_var_map.get(model_name, "")
        return deployment if deployment else None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Legacy global instance
settings = Settings()
