"""
Vector Database Manager
Singleton pattern for managing vector database instances
"""
from agent.utils.logging import get_logger
from typing import Dict, Optional, Any
from threading import Lock

from agent.services.vector_db.vector_db_interface import VectorDB
from agent.config.settings import get_settings


logger = get_logger(__name__)


class VectorDBManager:
    """
    Singleton manager for vector database instances
    
    Manages creation, caching, and retrieval of vector database connections.
    Supports multiple database providers (Qdrant, Elasticsearch, etc.)
    """
    
    _instance: Optional['VectorDBManager'] = None
    _lock: Lock = Lock()
    
    def __new__(cls) -> 'VectorDBManager':
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
        
        self._db_instances: Dict[str, VectorDB] = {}
        self._settings = get_settings()
        self._default_provider = getattr(self._settings, 'VECTOR_DB_PROVIDER', 'qdrant').lower()
        self._initialized = True
        
        logger.info(f"VectorDBManager initialized with default provider: {self._default_provider}")
    
    def _get_config_for_provider(self, provider: str) -> Dict[str, Any]:
        """
        Get configuration for a specific provider
        
        Args:
            provider: Database provider name (qdrant, elasticsearch)
        
        Returns:
            Dict[str, Any]: Configuration dictionary for the provider
        """
        provider = provider.lower()
        
        if provider == "qdrant":
            return {
                "url": getattr(self._settings, 'QDRANT_URL', 'http://localhost:6333'),
                "api_key": getattr(self._settings, 'QDRANT_API_KEY', ''),
                "collection_name": getattr(self._settings, 'QDRANT_COLLECTION_NAME', 'education_intents'),
                "timeout": getattr(self._settings, 'QDRANT_TIMEOUT', 30),
                "prefer_grpc": getattr(self._settings, 'QDRANT_PREFER_GRPC', False),
                "grpc_port": getattr(self._settings, 'QDRANT_GRPC_PORT', 6334),
                "embedding_dim": getattr(self._settings, 'VECTOR_EMBEDDING_DIM', 1536),
                "similarity_metric": getattr(self._settings, 'VECTOR_SIMILARITY_METRIC', 'cosine'),
            }
        elif provider == "elasticsearch":
            return {
                "url": getattr(self._settings, 'ELASTICSEARCH_URL', 'http://localhost:9200'),
                "api_key": getattr(self._settings, 'ELASTICSEARCH_API_KEY', ''),
                "username": getattr(self._settings, 'ELASTICSEARCH_USERNAME', ''),
                "password": getattr(self._settings, 'ELASTICSEARCH_PASSWORD', ''),
                "index_name": getattr(self._settings, 'ELASTICSEARCH_INDEX_NAME', 'education_intents'),
                "timeout": getattr(self._settings, 'ELASTICSEARCH_TIMEOUT', 30),
                "verify_certs": getattr(self._settings, 'ELASTICSEARCH_VERIFY_CERTS', True),
                "ca_certs": getattr(self._settings, 'ELASTICSEARCH_CA_CERTS', ''),
                "embedding_dim": getattr(self._settings, 'VECTOR_EMBEDDING_DIM', 1536),
                "similarity_metric": getattr(self._settings, 'VECTOR_SIMILARITY_METRIC', 'cosine'),
            }
        else:
            raise ValueError(f"Unsupported vector database provider: {provider}")
    
    def _create_db_instance(self, provider: str) -> VectorDB:
        """
        Create a new database instance for the given provider
        
        Args:
            provider: Database provider name
        
        Returns:
            VectorDB: Instance of the vector database
        
        Raises:
            ValueError: If provider is not supported
            ImportError: If required library is not installed
        """
        provider = provider.lower()
        config = self._get_config_for_provider(provider)
        
        try:
            if provider == "qdrant":
                from agent.services.vector_db.qdrant.qdrant_db import QdrantDB
                return QdrantDB(config)
            
            elif provider == "elasticsearch":
                from agent.services.vector_db.elasticsearch.elasticsearch_db import ElasticsearchDB
                return ElasticsearchDB(config)
            
            else:
                raise ValueError(f"Unsupported vector database provider: {provider}")
        
        except ImportError as e:
            logger.error(f"Failed to import {provider} module: {e}")
            raise ImportError(
                f"Required library for {provider} is not installed. "
                f"Please install it using: pip install {provider}-client"
            )
    
    def get_db(self, provider: Optional[str] = None) -> VectorDB:
        """
        Get or create a vector database instance
        
        Args:
            provider: Database provider name. If None, uses default provider
        
        Returns:
            VectorDB: Vector database instance
        
        Raises:
            ValueError: If provider is not supported
            ImportError: If required library is not installed
        """
        if provider is None:
            provider = self._default_provider
        
        provider = provider.lower()
        
        # Return existing instance if available
        if provider in self._db_instances:
            logger.debug(f"Returning existing {provider} instance")
            return self._db_instances[provider]
        
        # Create new instance
        with self._lock:
            # Double-check after acquiring lock
            if provider not in self._db_instances:
                logger.info(f"Creating new {provider} instance")
                db_instance = self._create_db_instance(provider)
                self._db_instances[provider] = db_instance
        
        return self._db_instances[provider]
    
    async def initialize_db(self, provider: Optional[str] = None) -> bool:
        """
        Initialize and connect to the database
        
        Args:
            provider: Database provider name. If None, uses default provider
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            db = self.get_db(provider)
            success = await db.connect()
            
            if success:
                logger.info(f"Successfully initialized {provider or self._default_provider} database")
            else:
                logger.error(f"Failed to initialize {provider or self._default_provider} database")
            
            return success
        
        except Exception as e:
            logger.error(f"Error initializing database: {e}", exc_info=True)
            return False
    
    async def close_db(self, provider: Optional[str] = None) -> bool:
        """
        Close database connection
        
        Args:
            provider: Database provider name. If None, closes default provider
        
        Returns:
            bool: True if closure successful, False otherwise
        """
        if provider is None:
            provider = self._default_provider
        
        provider = provider.lower()
        
        if provider not in self._db_instances:
            logger.warning(f"No active instance found for {provider}")
            return True
        
        try:
            db = self._db_instances[provider]
            success = await db.disconnect()
            
            if success:
                # Remove from cache after successful disconnection
                with self._lock:
                    del self._db_instances[provider]
                logger.info(f"Successfully closed {provider} database connection")
            else:
                logger.error(f"Failed to close {provider} database connection")
            
            return success
        
        except Exception as e:
            logger.error(f"Error closing database connection: {e}", exc_info=True)
            return False
    
    async def close_all(self) -> bool:
        """
        Close all active database connections
        
        Returns:
            bool: True if all closures successful, False otherwise
        """
        all_success = True
        providers = list(self._db_instances.keys())
        
        for provider in providers:
            success = await self.close_db(provider)
            all_success = all_success and success
        
        return all_success
    
    def get_active_providers(self) -> list:
        """
        Get list of active database providers
        
        Returns:
            list: List of provider names with active connections
        """
        return list(self._db_instances.keys())
    
    def get_default_provider(self) -> str:
        """
        Get the default database provider
        
        Returns:
            str: Default provider name
        """
        return self._default_provider
    
    def set_default_provider(self, provider: str) -> None:
        """
        Set the default database provider
        
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
        Check health of database connection
        
        Args:
            provider: Database provider name. If None, checks default provider
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            db = self.get_db(provider)
            return await db.health_check()
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            return False
    
    def __repr__(self) -> str:
        """String representation of the manager"""
        return (
            f"VectorDBManager(default_provider='{self._default_provider}', "
            f"active_instances={self.get_active_providers()})"
        )


# Global singleton instance
_manager_instance: Optional[VectorDBManager] = None


def get_vector_db_manager() -> VectorDBManager:
    """
    Get the global VectorDBManager singleton instance
    
    Returns:
        VectorDBManager: Singleton manager instance
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = VectorDBManager()
    return _manager_instance
