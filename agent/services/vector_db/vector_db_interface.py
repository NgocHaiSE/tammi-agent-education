"""
Vector Database Interface
Defines the abstract base class for vector database implementations
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class VectorDocument:
    """Represents a document with vector embedding"""
    id: str
    text: str
    vector: List[float]
    metadata: Optional[Dict[str, Any]] = None
    score: Optional[float] = None


@dataclass
class SearchResult:
    """Represents a search result from vector database"""
    documents: List[VectorDocument]
    total: int
    query_time_ms: float


class VectorDB(ABC):
    """
    Abstract base class for vector database operations
    
    All vector database implementations (Qdrant, etc.) 
    should inherit from this class and implement all abstract methods.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize vector database connection
        
        Args:
            config: Configuration dictionary containing connection parameters
        """
        self.config = config
        self._client = None
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to vector database
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Close connection to vector database
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if database connection is healthy
        
        Returns:
            bool: True if healthy, False otherwise
        """
        pass
    
    @abstractmethod
    async def create_collection(
        self, 
        collection_name: str, 
        vector_dim: int,
        distance_metric: str = "cosine"
    ) -> bool:
        """
        Create a new collection/index for storing vectors
        
        Args:
            collection_name: Name of the collection to create
            vector_dim: Dimension of the vector embeddings
            distance_metric: Similarity metric (cosine, euclidean, dot_product)
        
        Returns:
            bool: True if creation successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection/index
        
        Args:
            collection_name: Name of the collection to delete
        
        Returns:
            bool: True if deletion successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection/index exists
        
        Args:
            collection_name: Name of the collection to check
        
        Returns:
            bool: True if exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def insert_documents(
        self, 
        collection_name: str,
        documents: List[VectorDocument]
    ) -> Tuple[bool, int]:
        """
        Insert multiple documents into the collection
        
        Args:
            collection_name: Name of the collection
            documents: List of VectorDocument objects to insert
        
        Returns:
            Tuple[bool, int]: (Success status, Number of documents inserted)
        """
        pass
    
    @abstractmethod
    async def update_document(
        self,
        collection_name: str,
        document: VectorDocument
    ) -> bool:
        """
        Update a single document in the collection
        
        Args:
            collection_name: Name of the collection
            document: VectorDocument object with updated data
        
        Returns:
            bool: True if update successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def delete_documents(
        self,
        collection_name: str,
        document_ids: List[str]
    ) -> Tuple[bool, int]:
        """
        Delete documents by IDs
        
        Args:
            collection_name: Name of the collection
            document_ids: List of document IDs to delete
        
        Returns:
            Tuple[bool, int]: (Success status, Number of documents deleted)
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> SearchResult:
        """
        Search for similar vectors in the collection
        
        Args:
            collection_name: Name of the collection to search
            query_vector: Query vector embedding
            top_k: Number of top results to return
            score_threshold: Minimum similarity score threshold
            filter_conditions: Additional metadata filters
        
        Returns:
            SearchResult: Search results with documents and metadata
        """
        pass
    
    @abstractmethod
    async def get_document(
        self,
        collection_name: str,
        document_id: str
    ) -> Optional[VectorDocument]:
        """
        Retrieve a single document by ID
        
        Args:
            collection_name: Name of the collection
            document_id: ID of the document to retrieve
        
        Returns:
            Optional[VectorDocument]: Document if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def count_documents(self, collection_name: str) -> int:
        """
        Count total documents in a collection
        
        Args:
            collection_name: Name of the collection
        
        Returns:
            int: Number of documents in the collection
        """
        pass
    
    @abstractmethod
    async def scroll_documents(
        self,
        collection_name: str,
        batch_size: int = 100,
        offset: int = 0
    ) -> List[VectorDocument]:
        """
        Retrieve documents in batches (pagination)
        
        Args:
            collection_name: Name of the collection
            batch_size: Number of documents per batch
            offset: Starting offset for pagination
        
        Returns:
            List[VectorDocument]: List of documents in the batch
        """
        pass
    
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
