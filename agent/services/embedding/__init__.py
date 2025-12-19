"""
Embedding Service Module
Provides text embedding functionality for vector search and similarity matching
"""
from agent.services.embedding.embedding_interface import (
    EmbeddingService,
    EmbeddingResult
)
from agent.services.embedding.embedding_manager import (
    EmbeddingManager,
    get_embedding_manager
)

__all__ = [
    'EmbeddingService',
    'EmbeddingResult',
    'EmbeddingManager',
    'get_embedding_manager',
]
