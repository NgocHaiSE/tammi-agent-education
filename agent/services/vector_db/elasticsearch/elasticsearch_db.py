"""
Elasticsearch Vector Database Implementation
Implements VectorDB interface for Elasticsearch vector search
"""
import logging
import time
from typing import List, Dict, Any, Optional, Tuple

from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_bulk

from agent.services.vector_db.vector_db_interface import VectorDB, VectorDocument, SearchResult


logger = logging.getLogger(__name__)


class ElasticsearchDB(VectorDB):
    """
    Elasticsearch vector database implementation
    
    Provides concrete implementation of VectorDB interface for Elasticsearch.
    Uses dense_vector field type and kNN search capabilities.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Elasticsearch database connection
        
        Args:
            config: Configuration dictionary with Elasticsearch parameters
                - url: Elasticsearch server URL
                - api_key: API key for authentication (optional)
                - username: Username for basic auth (optional)
                - password: Password for basic auth (optional)
                - index_name: Default index name
                - timeout: Request timeout in seconds
                - verify_certs: Whether to verify SSL certificates
                - ca_certs: Path to CA certificate file
        """
        super().__init__(config)
        self.url = config.get("url", "http://localhost:9200")
        self.api_key = config.get("api_key")
        self.username = config.get("username", "elastic")
        self.password = config.get("password")
        self.index_name = config.get("index_name", "qa_documents")
        self.timeout = config.get("timeout", 30)
        self.verify_certs = config.get("verify_certs", False)
        self.ca_certs = config.get("ca_certs")
        self.embedding_dim = config.get("embedding_dim", 1536)
        self.similarity_metric = config.get("similarity_metric", "cosine")
        
        logger.info(
            f"Initialized ElasticsearchDB with url={self.url}, "
            f"index={self.index_name}"
        )
    
    async def connect(self) -> bool:
        """
        Establish connection to Elasticsearch database
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Build authentication
            if self.api_key:
                auth = {"api_key": self.api_key}
            elif self.username and self.password:
                auth = {"basic_auth": (self.username, self.password)}
            else:
                auth = {}
            
            # Build client options - only include SSL options if using https
            client_options = {
                **auth,
                "request_timeout": self.timeout,
            }
            
            # Only add SSL options if using HTTPS
            if self.url.startswith("https://"):
                client_options["verify_certs"] = self.verify_certs
                if self.ca_certs:
                    client_options["ca_certs"] = self.ca_certs
            
            # Create async client
            self._client = AsyncElasticsearch(
                [self.url],
                **client_options,
            )
            
            # Test connection
            info = await self._client.info()
            logger.info(
                f"Successfully connected to Elasticsearch. "
                f"Version: {info['version']['number']}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}", exc_info=True)
            self._client = None
            return False
    
    async def disconnect(self) -> bool:
        """
        Close connection to Elasticsearch database
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        try:
            if self._client:
                await self._client.close()
                self._client = None
                logger.info("Disconnected from Elasticsearch")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from Elasticsearch: {e}", exc_info=True)
            return False
    
    async def health_check(self) -> bool:
        """
        Check if Elasticsearch connection is healthy
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            if not self._client:
                return False
            
            # Ping Elasticsearch
            is_alive = await self._client.ping()
            return is_alive
        
        except Exception as e:
            logger.error(f"Elasticsearch health check failed: {e}")
            return False
    
    async def create_collection(
        self,
        collection_name: str,
        vector_dim: int,
        distance_metric: str = "cosine"
    ) -> bool:
        """
        Create a new index in Elasticsearch
        
        Args:
            collection_name: Name of the index to create
            vector_dim: Dimension of the vector embeddings
            distance_metric: Similarity metric (cosine, l2_norm, dot_product)
        
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            if not self._client:
                logger.error("Elasticsearch client not connected")
                return False
            
            # Map distance metric names
            similarity_map = {
                "cosine": "cosine",
                "euclidean": "l2_norm",
                "l2_norm": "l2_norm",
                "dot": "dot_product",
                "dot_product": "dot_product",
            }
            
            similarity = similarity_map.get(distance_metric.lower(), "cosine")
            
            # Define index mapping with dense_vector
            mapping = {
                "mappings": {
                    "properties": {
                        "text": {
                            "type": "text"
                        },
                        "vector": {
                            "type": "dense_vector",
                            "dims": vector_dim,
                            "index": True,
                            "similarity": similarity,
                        },
                        "metadata": {
                            "type": "object",
                            "enabled": True,
                        }
                    }
                }
            }
            
            # Create index
            await self._client.indices.create(
                index=collection_name,
                body=mapping,
            )
            
            logger.info(
                f"Created Elasticsearch index: {collection_name} "
                f"(dim={vector_dim}, similarity={similarity})"
            )
            return True
        
        except Exception as e:
            logger.error(f"Failed to create Elasticsearch index: {e}", exc_info=True)
            return False
    
    async def delete_collection(self, collection_name: str) -> bool:
        """
        Delete an index from Elasticsearch
        
        Args:
            collection_name: Name of the index to delete
        
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            if not self._client:
                logger.error("Elasticsearch client not connected")
                return False
            
            await self._client.indices.delete(index=collection_name)
            logger.info(f"Deleted Elasticsearch index: {collection_name}")
            return True
        
        except NotFoundError:
            logger.warning(f"Index {collection_name} not found for deletion")
            return True
        except Exception as e:
            logger.error(f"Failed to delete Elasticsearch index: {e}", exc_info=True)
            return False
    
    async def collection_exists(self, collection_name: str) -> bool:
        """
        Check if an index exists in Elasticsearch
        
        Args:
            collection_name: Name of the index to check
        
        Returns:
            bool: True if exists, False otherwise
        """
        try:
            if not self._client:
                logger.error("Elasticsearch client not connected")
                return False
            
            exists = await self._client.indices.exists(index=collection_name)
            return exists
        
        except Exception as e:
            logger.error(f"Error checking index existence: {e}", exc_info=True)
            return False
    
    async def insert_documents(
        self,
        collection_name: str,
        documents: List[VectorDocument]
    ) -> Tuple[bool, int]:
        """
        Insert multiple documents into Elasticsearch index
        
        Args:
            collection_name: Name of the index
            documents: List of VectorDocument objects to insert
        
        Returns:
            Tuple[bool, int]: (Success status, Number of documents inserted)
        """
        try:
            if not self._client:
                logger.error("Elasticsearch client not connected")
                return False, 0
            
            if not documents:
                logger.warning("No documents to insert")
                return True, 0
            
            # Prepare bulk actions
            actions = []
            for doc in documents:
                action = {
                    "_index": collection_name,
                    "_id": doc.id,
                    "_source": {
                        "text": doc.text,
                        "vector": doc.vector,
                        "metadata": doc.metadata or {},
                    }
                }
                actions.append(action)
            
            # Bulk insert
            success, failed = await async_bulk(
                self._client,
                actions,
                raise_on_error=False,
            )
            
            # failed is a list of errors
            failed_count = len(failed) if isinstance(failed, list) else 0
            
            if failed_count > 0:
                logger.warning(f"Failed to insert {failed_count} out of {len(documents)} documents")
            
            logger.info(f"Inserted {success} documents into {collection_name}")
            return failed_count == 0, success
        
        except Exception as e:
            logger.error(f"Failed to insert documents: {e}", exc_info=True)
            return False, 0
    
    async def update_document(
        self,
        collection_name: str,
        document: VectorDocument
    ) -> bool:
        """
        Update a single document in Elasticsearch index
        
        Args:
            collection_name: Name of the index
            document: VectorDocument object with updated data
        
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            if not self._client:
                logger.error("Elasticsearch client not connected")
                return False
            
            # Elasticsearch index operation handles both insert and update
            await self._client.index(
                index=collection_name,
                id=document.id,
                body={
                    "text": document.text,
                    "vector": document.vector,
                    "metadata": document.metadata or {},
                }
            )
            
            logger.info(f"Updated document {document.id} in {collection_name}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update document: {e}", exc_info=True)
            return False
    
    async def delete_documents(
        self,
        collection_name: str,
        document_ids: List[str]
    ) -> Tuple[bool, int]:
        """
        Delete documents by IDs from Elasticsearch
        
        Args:
            collection_name: Name of the index
            document_ids: List of document IDs to delete
        
        Returns:
            Tuple[bool, int]: (Success status, Number of documents deleted)
        """
        try:
            if not self._client:
                logger.error("Elasticsearch client not connected")
                return False, 0
            
            if not document_ids:
                logger.warning("No document IDs provided for deletion")
                return True, 0
            
            # Prepare bulk delete actions
            actions = [
                {
                    "_op_type": "delete",
                    "_index": collection_name,
                    "_id": doc_id,
                }
                for doc_id in document_ids
            ]
            
            success, failed = await async_bulk(
                self._client,
                actions,
                raise_on_error=False,
            )
            
            # failed is a list of errors
            failed_count = len(failed) if isinstance(failed, list) else 0
            
            if failed_count > 0:
                logger.warning(f"Failed to delete {failed_count} out of {len(document_ids)} documents")
            
            logger.info(f"Deleted {success} documents from {collection_name}")
            return failed_count == 0, success
        
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
        Search for similar vectors in Elasticsearch index using kNN
        
        Args:
            collection_name: Name of the index to search
            query_vector: Query vector embedding
            top_k: Number of top results to return
            score_threshold: Minimum similarity score threshold
            filter_conditions: Additional metadata filters
        
        Returns:
            SearchResult: Search results with documents and metadata
        """
        start_time = time.time()
        
        try:
            if not self._client:
                logger.error("Elasticsearch client not connected")
                return SearchResult(documents=[], total=0, query_time_ms=0)
            
            # Build kNN query
            knn_query = {
                "field": "vector",
                "query_vector": query_vector,
                "k": top_k,
                "num_candidates": top_k * 10,  # More candidates for better results
            }
            
            # Add filter if provided
            if filter_conditions:
                filter_clauses = []
                for key, value in filter_conditions.items():
                    # Try both top-level field and metadata.field for backward compatibility
                    filter_clauses.append({
                        "bool": {
                            "should": [
                                {"term": {key: value}},  # Top-level field (new structure)
                                {"term": {f"metadata.{key}": value}}  # Nested field (old structure)
                            ],
                            "minimum_should_match": 1
                        }
                    })
                
                knn_query["filter"] = {
                    "bool": {
                        "must": filter_clauses
                    }
                }
            
            # Perform kNN search
            response = await self._client.search(
                index=collection_name,
                knn=knn_query,
                size=top_k,
            )
            
            # Convert results to VectorDocument objects
            documents = []
            for hit in response["hits"]["hits"]:
                score = hit["_score"]
                
                # Apply score threshold if specified
                if score_threshold is not None and score < score_threshold:
                    continue
                
                source = hit["_source"]
                
                # Merge top-level fields into metadata for new structure
                metadata = source.get("metadata", {})
                
                # Add top-level fields to metadata if they exist (new structure)
                for field in ["grade", "subject", "difficulty", "problem_type", "question_number", "created_at"]:
                    if field in source:
                        metadata[field] = source[field]
                
                doc = VectorDocument(
                    id=hit["_id"],
                    text=source.get("text", ""),
                    vector=source.get("vector", []),
                    metadata=metadata,
                    score=score,
                )
                documents.append(doc)
            
            query_time_ms = (time.time() - start_time) * 1000
            
            logger.info(
                f"Search completed: found {len(documents)} documents in {query_time_ms:.2f}ms"
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
        Retrieve a single document by ID from Elasticsearch
        
        Args:
            collection_name: Name of the index
            document_id: ID of the document to retrieve
        
        Returns:
            Optional[VectorDocument]: Document if found, None otherwise
        """
        try:
            if not self._client:
                logger.error("Elasticsearch client not connected")
                return None
            
            response = await self._client.get(
                index=collection_name,
                id=document_id,
            )
            
            source = response["_source"]
            
            return VectorDocument(
                id=response["_id"],
                text=source.get("text", ""),
                vector=source.get("vector", []),
                metadata=source.get("metadata", {}),
            )
        
        except NotFoundError:
            logger.warning(f"Document {document_id} not found in {collection_name}")
            return None
        except Exception as e:
            logger.error(f"Failed to get document: {e}", exc_info=True)
            return None
    
    async def count_documents(self, collection_name: str) -> int:
        """
        Count total documents in Elasticsearch index
        
        Args:
            collection_name: Name of the index
        
        Returns:
            int: Number of documents in the index
        """
        try:
            if not self._client:
                logger.error("Elasticsearch client not connected")
                return 0
            
            response = await self._client.count(index=collection_name)
            return response["count"]
        
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
        Retrieve documents in batches from Elasticsearch (pagination)
        
        Args:
            collection_name: Name of the index
            batch_size: Number of documents per batch
            offset: Starting offset for pagination
        
        Returns:
            List[VectorDocument]: List of documents in the batch
        """
        try:
            if not self._client:
                logger.error("Elasticsearch client not connected")
                return []
            
            # Search with pagination
            response = await self._client.search(
                index=collection_name,
                body={
                    "query": {"match_all": {}},
                    "from": offset,
                    "size": batch_size,
                }
            )
            
            documents = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                
                doc = VectorDocument(
                    id=hit["_id"],
                    text=source.get("text", ""),
                    vector=source.get("vector", []),
                    metadata=source.get("metadata", {}),
                )
                documents.append(doc)
            
            logger.info(f"Scrolled {len(documents)} documents from {collection_name}")
            return documents
        
        except Exception as e:
            logger.error(f"Failed to scroll documents: {e}", exc_info=True)
            return []
    
    async def hybrid_search(
        self,
        collection_name: str,
        query_vector: List[float],
        query_text: str,
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        keyword_fields: Optional[Dict[str, Any]] = None,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> SearchResult:
        """
        Hybrid search combining semantic (kNN) and keyword (BM25) search
        
        Args:
            collection_name: Name of the index to search
            query_vector: Query vector embedding for semantic search
            query_text: Query text for keyword search
            top_k: Number of top results to return
            score_threshold: Minimum similarity score threshold
            keyword_fields: Fields and values for keyword matching (e.g., {"grade": "4", "subject": "toán"})
            semantic_weight: Weight for semantic search score (0-1)
            keyword_weight: Weight for keyword search score (0-1)
        
        Returns:
            SearchResult: Search results with documents and metadata
        """
        start_time = time.time()
        
        try:
            if not self._client:
                logger.error("Elasticsearch client not connected")
                return SearchResult(documents=[], total=0, query_time_ms=0)
            
            # Build the hybrid query
            query_body = {
                "size": top_k,
                "query": {
                    "bool": {
                        "should": []
                    }
                }
            }
            
            # Add kNN semantic search
            knn_query = {
                "field": "vector",
                "query_vector": query_vector,
                "k": top_k,
                "num_candidates": top_k * 10,
                "boost": semantic_weight
            }
            
            # Add BM25 keyword search on text field
            query_body["query"]["bool"]["should"].append({
                "multi_match": {
                    "query": query_text,
                    "fields": ["text^2", "topic", "metadata.topic"],
                    "type": "best_fields",
                    "boost": keyword_weight
                }
            })
            
            # Add keyword field filters if provided (flexible matching)
            if keyword_fields:
                for field, value in keyword_fields.items():
                    if value:  # Only add non-empty values
                        # Create flexible match queries for each field
                        field_query = {
                            "bool": {
                                "should": [
                                    # Exact match on top-level field
                                    {"term": {field: {"value": value, "boost": 2.0}}},
                                    # Match with text analysis (handles "Lớp 4" vs "4")
                                    {"match": {field: {"query": value, "boost": 1.5}}},
                                    # Nested metadata field (backward compatibility)
                                    {"term": {f"metadata.{field}": {"value": value, "boost": 2.0}}},
                                    {"match": {f"metadata.{field}": {"query": value, "boost": 1.5}}}
                                ],
                                "minimum_should_match": 1
                            }
                        }
                        query_body["query"]["bool"]["should"].append(field_query)
            
            # Use kNN parameter for semantic search
            query_body["knn"] = knn_query
            
            # logger.info(f"Hybrid search query: {query_body}")
            
            # Perform hybrid search
            response = await self._client.search(
                index=collection_name,
                body=query_body
            )
            
            # Convert results to VectorDocument objects
            documents = []
            for hit in response["hits"]["hits"]:
                score = hit["_score"]
                
                # Apply score threshold if specified
                if score_threshold is not None and score < score_threshold:
                    continue
                
                source = hit["_source"]
                
                # Extract all fields from source for easier access
                doc = VectorDocument(
                    id=hit["_id"],
                    text=source.get("text", ""),
                    vector=source.get("vector", []),
                    metadata=source.get("metadata", {}),
                    score=score,
                )
                
                # Add top-level fields as attributes for easier access
                for field in ["grade", "subject", "difficulty", "topic", "problem_type", "created_at"]:
                    if field in source:
                        setattr(doc, field, source[field])
                
                documents.append(doc)
            
            query_time_ms = (time.time() - start_time) * 1000
            
            logger.info(
                f"Hybrid search completed: found {len(documents)} documents in {query_time_ms:.2f}ms"
            )
            
            return SearchResult(
                documents=documents,
                total=len(documents),
                query_time_ms=query_time_ms,
            )
        
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}", exc_info=True)
            query_time_ms = (time.time() - start_time) * 1000
            return SearchResult(documents=[], total=0, query_time_ms=query_time_ms)
