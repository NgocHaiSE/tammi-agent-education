"""
Embedding Service Manager
Singleton pattern for managing embedding service instances
"""
from agent.utils.logging import get_logger
from typing import Dict, Optional, Any
from threading import Lock

from agent.services.embedding.embedding_interface import EmbeddingService
from agent.config.settings import get_settings


logger = get_logger(__name__)


class EmbeddingManager:
    """
    Singleton manager for embedding service instances
    
    Manages creation, caching, and retrieval of embedding service connections.
    Supports multiple embedding providers (Azure, OpenAI, local models, etc.)
    """
    
    _instance: Optional['EmbeddingManager'] = None
    _lock: Lock = Lock()
    
    def __new__(cls) -> 'EmbeddingManager':
        """Ensure only one instance exists (Singleton pattern)"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the manager (only once)"""
        if self._initialized:
            return
        
        self._embedding_instances: Dict[str, EmbeddingService] = {}
        self._settings = get_settings()
        self._default_provider = getattr(self._settings, 'EMBEDDING_PROVIDER', 'azure').lower()
        self._initialized = True
        
        logger.info(f"EmbeddingManager initialized with default provider: {self._default_provider}")
    
    def _get_config_for_provider(self, provider: str) -> Dict[str, Any]:
        """
        Get configuration for a specific provider
        
        Args:
            provider: Embedding provider name (azure, openai, local)
        
        Returns:
            Dict[str, Any]: Configuration dictionary for the provider
        """
        provider = provider.lower()
        
        if provider == "azure":
            return {
                "endpoint": getattr(self._settings, 'ENDPOINT_TEXT3_EMBEDDING', ''),
                "api_key": getattr(self._settings, 'API_KEY_TEXT3_EMBEDDING', ''),
                "model": getattr(self._settings, 'EMBEDDING_MODEL', 'text-embedding-3-large'),
                "dimension": getattr(self._settings, 'EMBEDDING_DIMENSION', 1536),
                "max_batch_size": 100,
                "max_text_length": 8191,
            }
        elif provider == "openai":
            return {
                "api_key": getattr(self._settings, 'OPENAI_API_KEY', ''),
                "model": getattr(self._settings, 'EMBEDDING_MODEL', 'text-embedding-3-large'),
                "dimension": getattr(self._settings, 'EMBEDDING_DIMENSION', 1536),
                "max_batch_size": 100,
                "max_text_length": 8191,
            }
        elif provider == "ollama":
            return {
                "base_url": getattr(self._settings, 'OLLAMA_BASE_URL', 'http://localhost:11434'),
                "model": getattr(self._settings, 'OLLAMA_EMBEDDING_MODEL', 'bge-m3'),
                "dimension": getattr(self._settings, 'EMBEDDING_DIMENSION', 1024),
                "max_batch_size": 10,
                "max_text_length": 8191,
                "timeout": 60,
            }
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")
    
    def _create_embedding_instance(self, provider: str) -> EmbeddingService:
        """
        Create a new embedding service instance for the given provider
        
        Args:
            provider: Embedding provider name
        
        Returns:
            EmbeddingService: Instance of the embedding service
        
        Raises:
            ValueError: If provider is not supported
            ImportError: If required library is not installed
        """
        provider = provider.lower()
        config = self._get_config_for_provider(provider)
        
        try:
            if provider == "azure":
                from agent.services.embedding.openai_text3_embedding.text3_embedding import Text3EmbeddingService
                return Text3EmbeddingService(config)
            
            elif provider == "openai":
                # TODO: Implement OpenAI embedding service
                raise NotImplementedError("OpenAI embedding service not implemented yet")
            
            elif provider == "ollama":
                from agent.services.embedding.ollama_embedding.ollama_embedding import OllamaEmbeddingService
                return OllamaEmbeddingService(config)
            
            else:
                raise ValueError(f"Unsupported embedding provider: {provider}")
        
        except ImportError as e:
            logger.error(f"Failed to import {provider} module: {e}")
            raise ImportError(
                f"Required library for {provider} is not installed. "
                f"Please install it using: pip install openai"
            )
    
    def get_embedding_service(self, provider: Optional[str] = None) -> EmbeddingService:
        """
        Get or create an embedding service instance
        
        Args:
            provider: Embedding provider name. If None, uses default provider
        
        Returns:
            EmbeddingService: Embedding service instance
        
        Raises:
            ValueError: If provider is not supported
            ImportError: If required library is not installed
        """
        if provider is None:
            provider = self._default_provider
        
        provider = provider.lower()
        
        # Return existing instance if available
        if provider in self._embedding_instances:
            logger.debug(f"Returning existing {provider} embedding service")
            return self._embedding_instances[provider]
        
        # Create new instance
        with self._lock:
            # Double-check after acquiring lock
            if provider not in self._embedding_instances:
                logger.info(f"Creating new {provider} embedding service")
                embedding_instance = self._create_embedding_instance(provider)
                self._embedding_instances[provider] = embedding_instance
        
        return self._embedding_instances[provider]
    
    async def initialize_service(self, provider: Optional[str] = None) -> bool:
        """
        Initialize and connect to the embedding service
        
        Args:
            provider: Embedding provider name. If None, uses default provider
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            service = self.get_embedding_service(provider)
            success = await service.connect()
            
            if success:
                logger.info(f"Successfully initialized {provider or self._default_provider} embedding service")
            else:
                logger.error(f"Failed to initialize {provider or self._default_provider} embedding service")
            
            return success
        
        except Exception as e:
            logger.error(f"Error initializing embedding service: {e}", exc_info=True)
            return False
    
    async def close_service(self, provider: Optional[str] = None) -> bool:
        """
        Close embedding service connection
        
        Args:
            provider: Embedding provider name. If None, closes default provider
        
        Returns:
            bool: True if closure successful, False otherwise
        """
        if provider is None:
            provider = self._default_provider
        
        provider = provider.lower()
        
        if provider not in self._embedding_instances:
            logger.warning(f"No active instance found for {provider}")
            return True
        
        try:
            service = self._embedding_instances[provider]
            success = await service.disconnect()
            
            if success:
                # Remove from cache after successful disconnection
                with self._lock:
                    del self._embedding_instances[provider]
                logger.info(f"Successfully closed {provider} embedding service connection")
            else:
                logger.error(f"Failed to close {provider} embedding service connection")
            
            return success
        
        except Exception as e:
            logger.error(f"Error closing embedding service connection: {e}", exc_info=True)
            return False
    
    async def close_all(self) -> bool:
        """
        Close all active embedding service connections
        
        Returns:
            bool: True if all closures successful, False otherwise
        """
        all_success = True
        providers = list(self._embedding_instances.keys())
        
        for provider in providers:
            success = await self.close_service(provider)
            all_success = all_success and success
        
        return all_success
    
    def get_active_providers(self) -> list:
        """
        Get list of active embedding providers
        
        Returns:
            list: List of provider names with active connections
        """
        return list(self._embedding_instances.keys())
    
    def get_default_provider(self) -> str:
        """
        Get the default embedding provider
        
        Returns:
            str: Default provider name
        """
        return self._default_provider
    
    def set_default_provider(self, provider: str) -> None:
        """
        Set the default embedding provider
        
        Args:
            provider: Provider name to set as default
        
        Raises:
            ValueError: If provider is not supported
        """
        provider = provider.lower()
        
        # Validate provider
        try:
            self._get_config_for_provider(provider)
            self._default_provider = provider
            logger.info(f"Default provider changed to: {provider}")
        except ValueError as e:
            logger.error(f"Invalid provider: {e}")
            raise
    
    async def health_check(self, provider: Optional[str] = None) -> bool:
        """
        Check health of embedding service connection
        
        Args:
            provider: Embedding provider name. If None, checks default provider
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            service = self.get_embedding_service(provider)
            return await service.health_check()
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            return False
    
    def __repr__(self) -> str:
        """String representation of the manager"""
        return (
            f"EmbeddingManager(default_provider='{self._default_provider}', "
            f"active_instances={self.get_active_providers()})"
        )


# Global singleton instance
_manager_instance: Optional[EmbeddingManager] = None


def get_embedding_manager() -> EmbeddingManager:
    """
    Get the global EmbeddingManager singleton instance
    
    Returns:
        EmbeddingManager: Singleton manager instance
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = EmbeddingManager()
    return _manager_instance
