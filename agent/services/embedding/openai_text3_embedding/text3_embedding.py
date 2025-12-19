"""
Azure OpenAI Text-3 Embedding Service Implementation
Implements EmbeddingService interface for Azure OpenAI text-embedding-3 models
"""
from agent.utils.logging import get_logger
from typing import List, Dict, Any, Optional

from openai import AsyncAzureOpenAI
from openai.types import CreateEmbeddingResponse

from agent.services.embedding.embedding_interface import EmbeddingService


logger = get_logger(__name__)


class Text3EmbeddingService(EmbeddingService):
    """
    Azure OpenAI Text-3 embedding service implementation
    
    Provides concrete implementation of EmbeddingService interface for Azure OpenAI.
    Uses text-embedding-3-large or text-embedding-3-small model for generating embeddings.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Azure OpenAI Text-3 embedding service
        
        Args:
            config: Configuration dictionary with Azure OpenAI parameters
                - endpoint: Azure OpenAI endpoint URL
                - api_key: API key for authentication
                - model: Model name (default: text-embedding-3-large)
                - dimension: Embedding dimension (default: 1536)
                - max_batch_size: Maximum batch size for requests
                - max_text_length: Maximum text length
        """
        super().__init__(config)
        self.endpoint = config.get("endpoint", "")
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "text-embedding-3-large")
        self.dimension = config.get("dimension", 1536)
        self.api_version = config.get("api_version", "2024-02-15-preview")
        
        if not self.endpoint or not self.api_key:
            raise ValueError("Azure OpenAI endpoint and api_key are required")
        
        logger.info(
            f"Initialized Text3EmbeddingService with endpoint={self.endpoint}, "
            f"model={self.model}, dimension={self.dimension}"
        )
    
    async def connect(self) -> bool:
        """
        Establish connection to Azure OpenAI service
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self._client = AsyncAzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                api_version=self.api_version,
            )
            
            logger.info("Successfully connected to Azure OpenAI embedding service")
            return True
        
        except Exception as e:
            logger.error(f"Failed to connect to Azure OpenAI: {e}", exc_info=True)
            self._client = None
            return False
    
    async def disconnect(self) -> bool:
        """
        Close connection to Azure OpenAI service
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        try:
            if self._client:
                await self._client.close()
                self._client = None
                logger.info("Disconnected from Azure OpenAI embedding service")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from Azure OpenAI: {e}", exc_info=True)
            return False
    
    async def health_check(self) -> bool:
        """
        Check if Azure OpenAI connection is healthy
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            if not self._client:
                return False
            
            # Test with a simple embedding request
            test_text = "health check"
            await self.embed_text(test_text)
            return True
        
        except Exception as e:
            logger.error(f"Azure OpenAI health check failed: {e}")
            return False
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text to embed
        
        Returns:
            List[float]: Embedding vector
        """
        if not self._client:
            raise RuntimeError("Azure OpenAI client not connected. Call connect() first.")
        
        try:
            # Truncate text if too long
            text = self.truncate_text(text)
            
            response: CreateEmbeddingResponse = await self._client.embeddings.create(
                model=self.model,
                input=[text],
                dimensions=self.dimension
            )
            
            embedding = response.data[0].embedding
            
            logger.debug(f"Generated embedding for text (length={len(text)})")
            return embedding
        
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}", exc_info=True)
            raise
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch
        
        Args:
            texts: List of input texts to embed
        
        Returns:
            List[List[float]]: List of embedding vectors
        """
        if not self._client:
            raise RuntimeError("Azure OpenAI client not connected. Call connect() first.")
        
        if not texts:
            return []
        
        try:
            # Truncate texts if too long
            truncated_texts = [self.truncate_text(text) for text in texts]
            
            response: CreateEmbeddingResponse = await self._client.embeddings.create(
                model=self.model,
                input=truncated_texts,
                dimensions=self.dimension
            )
            
            # Sort by index to ensure correct order
            embeddings = [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
            
            logger.info(f"Generated {len(embeddings)} embeddings")
            return embeddings
        
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}", exc_info=True)
            raise
    
    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query
        
        For Azure OpenAI, queries and documents are embedded the same way.
        
        Args:
            query: Search query text
        
        Returns:
            List[float]: Query embedding vector
        """
        return await self.embed_text(query)
    
    def get_dimension(self) -> int:
        """
        Get the embedding dimension size
        
        Returns:
            int: Embedding vector dimension
        """
        return self.dimension
    
    def get_model_name(self) -> str:
        """
        Get the model name being used
        
        Returns:
            str: Model name/identifier
        """
        return self.model

    async def embed_with_retry(
            self,
            text: str,
            max_retries: int = 3,
            retry_delay: float = 1.0
    ) -> List[float]:
        """
        Generate embedding with retry logic for robustness

        Args:
            text: Input text to embed
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds

        Returns:
            List[float]: Embedding vector
        """
        import asyncio

        last_exception: Optional[Exception] = None

        for attempt in range(max_retries):
            try:
                return await self.embed_text(text)
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.warning(f"Embedding attempt {attempt + 1} failed: {e}. Retrying...")
                    await asyncio.sleep(retry_delay * (attempt + 1))
                else:
                    logger.error(f"All {max_retries} embedding attempts failed")
                    raise

        # Dòng này đảm bảo luôn có raise rõ ràng nếu vòng lặp kết thúc
        raise RuntimeError(f"Embedding failed after {max_retries} attempts") from last_exception

    async def embed_texts_with_progress(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        callback: Optional[callable] = None
    ) -> List[List[float]]:
        """
        Embed texts in batches with progress callback
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size (uses config default if None)
            callback: Optional callback function(current, total) for progress tracking
        
        Returns:
            List[List[float]]: All embeddings
        """
        if batch_size is None:
            batch_size = self.get_max_batch_size()
        
        all_embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = await self.embed_texts(batch)
            all_embeddings.extend(embeddings)
            
            if callback:
                current_batch = (i // batch_size) + 1
                callback(current_batch, total_batches)
        
        return all_embeddings
    
    def get_token_count_estimate(self, text: str) -> int:
        """
        Estimate token count for a text
        
        Uses rough approximation: 1 token ≈ 4 characters
        
        Args:
            text: Input text
        
        Returns:
            int: Estimated token count
        """
        return len(text) // 4
    
    def __repr__(self) -> str:
        """String representation"""
        return (
            f"Text3EmbeddingService(model='{self.model}', "
            f"dimension={self.dimension}, "
            f"endpoint='{self.endpoint[:50]}...')"
        )
