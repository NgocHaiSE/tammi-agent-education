"""
Ollama BGE-M3 Embedding Service Implementation
Implements EmbeddingService interface for Ollama with BGE-M3 model
"""
from agent.utils.logging import get_logger
from typing import List, Dict, Any, Optional
import aiohttp
import asyncio

from agent.services.embedding.embedding_interface import EmbeddingService


logger = get_logger(__name__)


class OllamaEmbeddingService(EmbeddingService):
    """
    Ollama embedding service implementation for BGE-M3
    
    Provides concrete implementation of EmbeddingService interface for Ollama.
    Uses BGE-M3 model running locally via Ollama for generating embeddings.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Ollama BGE-M3 embedding service
        
        Args:
            config: Configuration dictionary with Ollama parameters
                - base_url: Ollama server URL (default: http://localhost:11434)
                - model: Model name (default: bge-m3)
                - dimension: Embedding dimension (1024 for BGE-M3)
                - max_batch_size: Maximum batch size for requests
                - max_text_length: Maximum text length
                - timeout: Request timeout in seconds
        """
        super().__init__(config)
        base_url = config.get("base_url", "http://localhost:11434")
        # Remove /v1 suffix if present (Ollama native API doesn't use /v1)
        self.base_url = base_url.rstrip('/').replace('/v1', '')
        self.model = config.get("model", "bge-m3")
        self.dimension = config.get("dimension", 1024)  # BGE-M3 default
        self.max_batch_size = config.get("max_batch_size", 10)
        self.max_text_length = config.get("max_text_length", 8191)
        self.timeout = config.get("timeout", 60)
        
        self._session: Optional[aiohttp.ClientSession] = None
        
        logger.info(
            f"Initialized OllamaEmbeddingService with base_url={self.base_url}, "
            f"model={self.model}, dimension={self.dimension}"
        )
    
    async def connect(self) -> bool:
        """
        Establish connection to Ollama service
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
            
            # Test connection with a health check
            async with self._session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    models = await response.json()
                    model_names = [m.get('name', '') for m in models.get('models', [])]
                    
                    if self.model in model_names or any(self.model in name for name in model_names):
                        logger.info(f"Successfully connected to Ollama, model '{self.model}' is available")
                        return True
                    else:
                        logger.warning(
                            f"Connected to Ollama but model '{self.model}' not found. "
                            f"Available models: {model_names}. "
                            f"Please run: ollama pull {self.model}"
                        )
                        return False
                else:
                    logger.error(f"Failed to connect to Ollama: HTTP {response.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}", exc_info=True)
            if self._session:
                await self._session.close()
                self._session = None
            return False
    
    async def disconnect(self) -> bool:
        """
        Close connection to Ollama service
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        try:
            if self._session:
                await self._session.close()
                self._session = None
                logger.info("Disconnected from Ollama embedding service")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from Ollama: {e}", exc_info=True)
            return False
    
    async def health_check(self) -> bool:
        """
        Check if Ollama connection is healthy
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            if not self._session:
                logger.warning("Ollama client not connected")
                return False
            
            # Test with a simple embedding
            test_embedding = await self._generate_single_embedding("health check")
            
            if test_embedding and len(test_embedding) == self.dimension:
                logger.info("Ollama health check passed")
                return True
            else:
                logger.error(f"Ollama health check failed: invalid embedding dimension")
                return False
        
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}", exc_info=True)
            return False
    
    async def _generate_single_embedding(self, text: str) -> List[float]:
        """
        Internal method to generate embedding for a single text
        
        Args:
            text: Input text to embed
        
        Returns:
            List[float]: Embedding vector
        
        Raises:
            RuntimeError: If embedding generation fails
        """
        if not self._session:
            raise RuntimeError("Ollama client not connected. Call connect() first.")
        
        try:
            payload = {
                "model": self.model,
                "prompt": text
            }
            
            async with self._session.post(
                f"{self.base_url}/api/embeddings",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    embedding = result.get("embedding", [])
                    
                    if not embedding:
                        raise RuntimeError("Empty embedding returned from Ollama")
                    
                    return embedding
                else:
                    error_text = await response.text()
                    raise RuntimeError(
                        f"Ollama API error {response.status}: {error_text}"
                    )
        
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}")
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text to embed
        
        Returns:
            List[float]: Embedding vector
        
        Raises:
            RuntimeError: If client is not connected or embedding fails
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return [0.0] * self.dimension
        
        # Truncate if too long
        if len(text) > self.max_text_length:
            logger.warning(
                f"Text length {len(text)} exceeds max {self.max_text_length}, truncating"
            )
            text = text[:self.max_text_length]
        
        try:
            embedding = await self._generate_single_embedding(text)
            logger.debug(f"Generated embedding for text of length {len(text)}")
            return embedding
        
        except Exception as e:
            logger.error(f"Failed to embed text: {e}")
            raise
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of input texts to embed
        
        Returns:
            List[List[float]]: List of embedding vectors
        
        Raises:
            RuntimeError: If client is not connected or embedding fails
        """
        if not texts:
            logger.warning("Empty text list provided for embedding")
            return []
        
        # Filter empty texts and truncate long ones
        processed_texts = []
        for text in texts:
            if not text or not text.strip():
                processed_texts.append("")
            elif len(text) > self.max_text_length:
                logger.warning(
                    f"Text length {len(text)} exceeds max {self.max_text_length}, truncating"
                )
                processed_texts.append(text[:self.max_text_length])
            else:
                processed_texts.append(text)
        
        try:
            # Process in batches to avoid overwhelming the server
            all_embeddings = []
            
            for i in range(0, len(processed_texts), self.max_batch_size):
                batch = processed_texts[i:i + self.max_batch_size]
                
                # Generate embeddings concurrently within batch
                tasks = [self._generate_single_embedding(text) for text in batch]
                batch_embeddings = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Handle any errors
                for j, result in enumerate(batch_embeddings):
                    if isinstance(result, Exception):
                        logger.error(f"Failed to embed text {i+j}: {result}")
                        # Use zero vector as fallback
                        all_embeddings.append([0.0] * self.dimension)
                    else:
                        all_embeddings.append(result)
                
                logger.debug(
                    f"Generated {len(batch)} embeddings in batch "
                    f"{i // self.max_batch_size + 1}"
                )
            
            logger.info(f"Generated {len(all_embeddings)} embeddings total")
            return all_embeddings
        
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}", exc_info=True)
            raise RuntimeError(f"Batch embedding generation failed: {e}")
    
    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query
        
        For BGE-M3, query and document embeddings use the same process.
        
        Args:
            query: Search query text
        
        Returns:
            List[float]: Query embedding vector
        
        Raises:
            RuntimeError: If client is not connected or embedding fails
        """
        return await self.embed_text(query)
    
    async def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """
        Generate embeddings for documents
        
        For BGE-M3, query and document embeddings use the same process.
        
        Args:
            documents: List of document texts
        
        Returns:
            List[List[float]]: List of document embedding vectors
        
        Raises:
            RuntimeError: If client is not connected or embedding fails
        """
        return await self.embed_texts(documents)
    
    def get_dimension(self) -> int:
        """
        Get embedding vector dimension
        
        Returns:
            int: Dimension of embedding vectors (1024 for BGE-M3)
        """
        return self.dimension
    
    def get_model_name(self) -> str:
        """
        Get model name
        
        Returns:
            str: Name of the embedding model
        """
        return self.model
