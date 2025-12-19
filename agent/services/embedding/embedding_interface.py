"""
Embedding Service Interface
Defines the abstract base class for embedding service implementations
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class EmbeddingResult:
    """Represents the result of an embedding operation"""
    embeddings: List[List[float]]
    model: str
    usage: Dict[str, int]
    dimension: int


class EmbeddingService(ABC):
    """
    Abstract base class for embedding service operations
    
    All embedding service implementations (Azure, OpenAI, local models, etc.) 
    should inherit from this class and implement all abstract methods.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize embedding service
        
        Args:
            config: Configuration dictionary containing service parameters
        """
        self.config = config
        self._client = None
    
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text to embed
        
        Returns:
            List[float]: Embedding vector
        """
        pass
    
    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch
        
        Args:
            texts: List of input texts to embed
        
        Returns:
            List[List[float]]: List of embedding vectors
        """
        pass
    
    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query
        
        Some models may treat queries differently from documents.
        
        Args:
            query: Search query text
        
        Returns:
            List[float]: Query embedding vector
        """
        pass
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to embedding service
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Close connection to embedding service
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if embedding service connection is healthy
        
        Returns:
            bool: True if healthy, False otherwise
        """
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """
        Get the embedding dimension size
        
        Returns:
            int: Embedding vector dimension
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get the model name being used
        
        Returns:
            str: Model name/identifier
        """
        pass
    
    def get_max_batch_size(self) -> int:
        """
        Get maximum batch size for embedding requests
        
        Returns:
            int: Maximum number of texts that can be embedded in one request
        """
        return self.config.get("max_batch_size", 100)
    
    def get_max_text_length(self) -> int:
        """
        Get maximum text length (in tokens/characters)
        
        Returns:
            int: Maximum text length supported
        """
        return self.config.get("max_text_length", 8191)
    
    def is_connected(self) -> bool:
        """
        Check if client is connected
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self._client is not None
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get current configuration
        
        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        return self.config.copy()
    
    async def embed_documents_with_metadata(
        self,
        texts: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings with associated metadata
        
        Args:
            texts: List of texts to embed
            metadata: Optional list of metadata dicts for each text
        
        Returns:
            List[Dict[str, Any]]: List of dicts containing embeddings and metadata
        """
        embeddings = await self.embed_texts(texts)
        
        results = []
        for i, embedding in enumerate(embeddings):
            result = {
                "text": texts[i],
                "embedding": embedding,
                "metadata": metadata[i] if metadata and i < len(metadata) else {}
            }
            results.append(result)
        
        return results
    
    def truncate_text(self, text: str, max_length: Optional[int] = None) -> str:
        """
        Truncate text to maximum length
        
        Args:
            text: Input text
            max_length: Maximum length (uses config default if None)
        
        Returns:
            str: Truncated text
        """
        if max_length is None:
            max_length = self.get_max_text_length()
        
        if len(text) <= max_length:
            return text
        
        return text[:max_length]
    
    async def embed_with_retry(
        self,
        text: str,
        max_retries: int = 3,
        backoff_factor: float = 1.5
    ) -> Optional[List[float]]:
        """
        Embed text with retry logic
        
        Args:
            text: Input text to embed
            max_retries: Maximum number of retry attempts
            backoff_factor: Multiplier for exponential backoff
        
        Returns:
            Optional[List[float]]: Embedding vector or None if all retries fail
        """
        import asyncio
        
        for attempt in range(max_retries):
            try:
                return await self.embed_text(text)
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = backoff_factor ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    return None
        
        return None
