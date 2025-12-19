"""
Qdrant Vector Database Implementation
Implements VectorDB interface for Qdrant vector database
"""
from agent.utils.logging import get_logger
from agent.utils.performance import trace_span
import time
from typing import List, Dict, Any, Optional, Tuple

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from agent.services.vector_db.vector_db_interface import VectorDB, VectorDocument, SearchResult


logger = get_logger(__name__)


class QdrantDB(VectorDB):
    """
    Qdrant vector database implementation
    
    Provides concrete implementation of VectorDB interface for Qdrant.
    Supports both HTTP and gRPC connections.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Qdrant database connection
        
        Args:
            config: Configuration dictionary with Qdrant parameters
                - url: Qdrant server URL
                - api_key: API key for authentication (optional)
                - collection_name: Default collection name
                - timeout: Request timeout in seconds
                - prefer_grpc: Whether to use gRPC instead of HTTP
                - grpc_port: gRPC port if prefer_grpc is True
        """
        super().__init__(config)
        self.url = config.get("url", "http://localhost:6333")
        self.api_key = config.get("api_key")
        self.collection_name = config.get("collection_name", "education_intents")
        self.timeout = config.get("timeout", 30)
        self.prefer_grpc = config.get("prefer_grpc", False)
        self.grpc_port = config.get("grpc_port", 6334)
        self.embedding_dim = config.get("embedding_dim", 1536)
        self.similarity_metric = config.get("similarity_metric", "cosine")
        
        logger.info(
            f"Initialized QdrantDB with url={self.url}, "
            f"collection={self.collection_name}, prefer_grpc={self.prefer_grpc}"
        )
    
    async def connect(self) -> bool:
        """
        Establish connection to Qdrant database
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Parse host and port from URL
            host = self.url.replace("http://", "").replace("https://", "").split(":")[0]
            port = None if ":" not in self.url.split("//")[-1] else int(self.url.split(":")[-1])
            
            # Detect if HTTPS should be used
            https = self.url.startswith("https://")
            
            if self.prefer_grpc and port is None:
                port = self.grpc_port
            
            logger.info(
                f"Connecting to Qdrant at host={host}, port={port}, "
                f"https={https}, prefer_grpc={self.prefer_grpc}"
            )
            
            self._client = QdrantClient(
                host=host,
                port=port,
                api_key=self.api_key,
                timeout=self.timeout,
                prefer_grpc=self.prefer_grpc,
                https=https,
            )
            
            # Test connection
            logger.info("Testing Qdrant connection by fetching collections...")
            collections = self._client.get_collections()
            logger.info(f"Successfully connected to Qdrant. Found {len(collections.collections)} collections.")
            
            # Verify that critical methods exist
            if not hasattr(self._client, 'search'):
                logger.warning(
                    f"Qdrant client (type: {type(self._client)}) does not have 'search' method. "
                    f"Available search methods: {[m for m in dir(self._client) if 'search' in m.lower()]}"
                )
            
            return True
        
        except Exception as e:
            logger.error(
                f"Failed to connect to Qdrant at {self.url} "
                f"(parsed: host={host if 'host' in locals() else 'N/A'}, "
                f"port={port if 'port' in locals() else 'N/A'}, "
                f"https={https if 'https' in locals() else 'N/A'}): {e}", 
                exc_info=True
            )
            self._client = None
            return False
    
    async def disconnect(self) -> bool:
        """
        Close connection to Qdrant database
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        try:
            if self._client:
                self._client.close()
                self._client = None
                logger.info("Disconnected from Qdrant")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from Qdrant: {e}", exc_info=True)
            return False
    
    async def health_check(self) -> bool:
        """
        Check if Qdrant connection is healthy
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            if not self._client:
                return False
            
            # Try to get collections as a health check
            self._client.get_collections()
            return True
        
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False
    
    async def create_collection(
        self,
        collection_name: str,
        vector_dim: int,
        distance_metric: str = "cosine"
    ) -> bool:
        """
        Create a new collection in Qdrant
        
        Args:
            collection_name: Name of the collection to create
            vector_dim: Dimension of the vector embeddings
            distance_metric: Similarity metric (cosine, euclidean, dot)
        
        Returns:
            bool: True if creation successful, False otherwise
        """
        await self.ensure_connected()
        try:
            if not self._client:
                logger.error("Qdrant client not connected")
                return False
            
            # Map distance metric names
            distance_map = {
                "cosine": models.Distance.COSINE,
                "euclidean": models.Distance.EUCLID,
                "dot": models.Distance.DOT,
                "dot_product": models.Distance.DOT,
            }
            
            distance = distance_map.get(distance_metric.lower(), models.Distance.COSINE)
            
            # Create collection
            self._client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_dim,
                    distance=distance,
                ),
            )
            
            logger.info(f"Created Qdrant collection: {collection_name} (dim={vector_dim}, metric={distance_metric})")
            return True
        
        except Exception as e:
            logger.error(f"Failed to create Qdrant collection: {e}", exc_info=True)
            return False
    
    async def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection from Qdrant
        
        Args:
            collection_name: Name of the collection to delete
        
        Returns:
            bool: True if deletion successful, False otherwise
        """
        await self.ensure_connected()
        try:
            if not self._client:
                logger.error("Qdrant client not connected")
                return False
            
            self._client.delete_collection(collection_name=collection_name)
            logger.info(f"Deleted Qdrant collection: {collection_name}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete Qdrant collection: {e}", exc_info=True)
            return False
    
    async def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists in Qdrant
        
        Args:
            collection_name: Name of the collection to check
        
        Returns:
            bool: True if exists, False otherwise
        """
        await self.ensure_connected()
        try:
            if not self._client:
                logger.error("Qdrant client not connected")
                return False
            
            collections = self._client.get_collections()
            return any(col.name == collection_name for col in collections.collections)
        
        except Exception as e:
            logger.error(f"Error checking collection existence: {e}", exc_info=True)
            return False
    
    async def insert_documents(
        self,
        collection_name: str,
        documents: List[VectorDocument]
    ) -> Tuple[bool, int]:
        """
        Insert multiple documents into Qdrant collection
        
        Args:
            collection_name: Name of the collection
            documents: List of VectorDocument objects to insert
        
        Returns:
            Tuple[bool, int]: (Success status, Number of documents inserted)
        """
        await self.ensure_connected()
        try:
            if not self._client:
                logger.error("Qdrant client not connected")
                return False, 0
            
            if not documents:
                logger.warning("No documents to insert")
                return True, 0
            
            # Prepare points for Qdrant
            points = []
            for doc in documents:
                point = models.PointStruct(
                    id=doc.id,
                    vector=doc.vector,
                    payload={
                        "text": doc.text,
                        **(doc.metadata or {}),
                    }
                )
                points.append(point)
            
            # Upload points
            self._client.upsert(
                collection_name=collection_name,
                points=points,
            )
            
            logger.info(f"Inserted {len(documents)} documents into {collection_name}")
            return True, len(documents)
        
        except Exception as e:
            logger.error(f"Failed to insert documents: {e}", exc_info=True)
            return False, 0
    
    async def update_document(
        self,
        collection_name: str,
        document: VectorDocument
    ) -> bool:
        """
        Update a single document in Qdrant collection
        
        Args:
            collection_name: Name of the collection
            document: VectorDocument object with updated data
        
        Returns:
            bool: True if update successful, False otherwise
        """
        await self.ensure_connected()
        try:
            # Qdrant upsert handles both insert and update
            success, count = await self.insert_documents(collection_name, [document])
            return success and count == 1
        
        except Exception as e:
            logger.error(f"Failed to update document: {e}", exc_info=True)
            return False
    
    async def delete_documents(
        self,
        collection_name: str,
        document_ids: List[str]
    ) -> Tuple[bool, int]:
        """
        Delete documents by IDs from Qdrant
        
        Args:
            collection_name: Name of the collection
            document_ids: List of document IDs to delete
        
        Returns:
            Tuple[bool, int]: (Success status, Number of documents deleted)
        """
        await self.ensure_connected()
        try:
            if not self._client:
                logger.error("Qdrant client not connected")
                return False, 0
            
            if not document_ids:
                logger.warning("No document IDs provided for deletion")
                return True, 0
            
            self._client.delete(
                collection_name=collection_name,
                points_selector=models.PointIdsList(
                    points=document_ids,
                ),
            )
            
            logger.info(f"Deleted {len(document_ids)} documents from {collection_name}")
            return True, len(document_ids)
        
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}", exc_info=True)
            return False, 0
    
    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> SearchResult:
        """
        Search for similar vectors in Qdrant collection
        
        Args:
            collection_name: Name of the collection to search
            query_vector: Query vector embedding
            top_k: Number of top results to return
            score_threshold: Minimum similarity score threshold
            filter_conditions: Additional metadata filters
        
        Returns:
            SearchResult: Search results with documents and metadata
        """
        start_time = time.time()
        
        try:
            with trace_span("qdrant_search") as span:
                await self.ensure_connected()
                
                span.add_metadata(
                    collection=collection_name,
                    top_k=top_k,
                    score_threshold=score_threshold if score_threshold else "none",
                    has_filters=bool(filter_conditions),
                    filter_count=len(filter_conditions) if filter_conditions else 0
                )
                
                if not self._client:
                    logger.error("Qdrant client not connected")
                    span.add_metadata(error="client_not_connected")
                    return SearchResult(documents=[], total=0, query_time_ms=0)
                
                # Debug: Check client type and available methods
                logger.debug(f"Qdrant client type: {type(self._client)}")
                logger.debug(f"Qdrant client has 'search' method: {hasattr(self._client, 'search')}")
                if not hasattr(self._client, 'search'):
                    logger.error(f"Qdrant client does not have 'search' method. Available methods: {[m for m in dir(self._client) if not m.startswith('_')]}")
                    span.add_metadata(error="missing_search_method")
                    return SearchResult(documents=[], total=0, query_time_ms=0)
                
                # Build filter if provided
                query_filter = None
                if filter_conditions:
                    with trace_span("build_qdrant_filter"):
                        must_conditions = []
                        for key, value in filter_conditions.items():
                            must_conditions.append(
                                models.FieldCondition(
                                    key=key,
                                    match=models.MatchValue(value=value)
                                )
                            )
                        
                        query_filter = models.Filter(must=must_conditions)
                
                # Perform search
                with trace_span("qdrant_api_call") as api_span:
                    try:
                        # Try using search() method (available in most versions)
                        search_result = self._client.search(
                            collection_name=collection_name,
                            query_vector=query_vector,
                            limit=top_k,
                            score_threshold=score_threshold,
                            query_filter=query_filter,
                        )
                    except AttributeError as e:
                        # Fallback for versions where search() doesn't exist
                        logger.warning(f"search() method not available: {e}. Trying query_points()...")
                        try:
                            from qdrant_client.http import models as qmodels
                            search_result = self._client.query_points(
                                collection_name=collection_name,
                                query=query_vector,
                                limit=top_k,
                                score_threshold=score_threshold,
                                query_filter=query_filter,
                            ).points
                        except AttributeError:
                            # If query_points also doesn't exist, try search_points
                            logger.warning("query_points() also not available. Trying search_points()...")
                            search_result = self._client.search_points(
                                collection_name=collection_name,
                                query_vector=query_vector,
                                limit=top_k,
                                score_threshold=score_threshold,
                                query_filter=query_filter,
                            ).points
                    
                    api_span.add_metadata(
                        results_count=len(search_result),
                        vector_dim=len(query_vector)
                    )
                
                # Convert to VectorDocument objects
                with trace_span("convert_search_results") as convert_span:
                    documents = []
                    for scored_point in search_result:
                        payload = scored_point.payload or {}
                        text = payload.pop("text", "")
                        
                        doc = VectorDocument(
                            id=str(scored_point.id),
                            text=text,
                            vector=scored_point.vector or [],
                            metadata=payload,
                            score=scored_point.score,
                        )
                        documents.append(doc)
                    
                    convert_span.add_metadata(documents_converted=len(documents))
                
                query_time_ms = (time.time() - start_time) * 1000
                
                logger.info(
                    f"Search completed: found {len(documents)} documents in {query_time_ms:.2f}ms"
                )
                
                span.add_metadata(
                    total_results=len(documents),
                    query_time_ms=round(query_time_ms, 2),
                    avg_score=round(sum(d.score for d in documents if d.score) / len(documents), 4) if documents else 0
                )
                
                return SearchResult(
                    documents=documents,
                    total=len(documents),
                    query_time_ms=query_time_ms,
                )
        
        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            query_time_ms = (time.time() - start_time) * 1000
            return SearchResult(documents=[], total=0, query_time_ms=query_time_ms)
    
    async def get_document(
        self,
        collection_name: str,
        document_id: str
    ) -> Optional[VectorDocument]:
        """
        Retrieve a single document by ID from Qdrant
        
        Args:
            collection_name: Name of the collection
            document_id: ID of the document to retrieve
        
        Returns:
            Optional[VectorDocument]: Document if found, None otherwise
        """
        await self.ensure_connected()
        try:
            if not self._client:
                logger.error("Qdrant client not connected")
                return None
            
            points = self._client.retrieve(
                collection_name=collection_name,
                ids=[document_id],
                with_vectors=True,
            )
            
            if not points:
                return None
            
            point = points[0]
            payload = point.payload or {}
            text = payload.pop("text", "")
            
            return VectorDocument(
                id=str(point.id),
                text=text,
                vector=point.vector or [],
                metadata=payload,
            )
        
        except Exception as e:
            logger.error(f"Failed to get document: {e}", exc_info=True)
            return None
    
    async def count_documents(self, collection_name: str) -> int:
        """
        Count total documents in Qdrant collection
        
        Args:
            collection_name: Name of the collection
        
        Returns:
            int: Number of documents in the collection
        """
        await self.ensure_connected()
        try:
            if not self._client:
                logger.error("Qdrant client not connected")
                return 0
            
            collection_info = self._client.get_collection(collection_name=collection_name)
            return collection_info.points_count or 0
        
        except Exception as e:
            logger.error(f"Failed to count documents: {e}", exc_info=True)
            return 0
    
    async def scroll_documents(
        self,
        collection_name: str,
        batch_size: int = 100,
        offset: int = 0
    ) -> List[VectorDocument]:
        """
        Retrieve documents in batches from Qdrant (pagination)
        
        Args:
            collection_name: Name of the collection
            batch_size: Number of documents per batch
            offset: Starting offset for pagination
        
        Returns:
            List[VectorDocument]: List of documents in the batch
        """
        await self.ensure_connected()
        try:
            if not self._client:
                logger.error("Qdrant client not connected")
                return []
            
            # Qdrant scroll with offset
            records, next_offset = self._client.scroll(
                collection_name=collection_name,
                limit=batch_size,
                offset=offset,
                with_vectors=True,
            )
            
            documents = []
            for record in records:
                payload = record.payload or {}
                text = payload.pop("text", "")
                
                doc = VectorDocument(
                    id=str(record.id),
                    text=text,
                    vector=record.vector or [],
                    metadata=payload,
                )
                documents.append(doc)
            
            logger.info(f"Scrolled {len(documents)} documents from {collection_name}")
            return documents
        
        except Exception as e:
            logger.error(f"Failed to scroll documents: {e}", exc_info=True)
            return []

    async def ensure_connected(self):
        """
        Ensure the Qdrant client is connected before performing any operations.

        This version avoids calling `health_check()` (which issues a network request)
        on every operation. It only checks whether the client object exists and
        attempts to reconnect if necessary. Connection failures will propagate as
        exceptions from the actual operations.
        """
        if self._client:
            return

        logger.warning("Qdrant client not connected. Attempting to reconnect...")
        if not await self.connect():
            raise RuntimeError("Failed to connect to Qdrant database.")
