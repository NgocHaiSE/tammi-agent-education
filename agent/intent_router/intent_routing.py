"""
Intent routing for Education Agent.

Routes user queries to appropriate sub_intent handlers based on semantic similarity.
Uses Vector DB for semantic search, with keyword matching as fallback.
"""

import asyncio
from agent.utils.logging import get_logger
from typing import Dict, List, Optional

from agent.config.settings import get_settings
from agent.graph.constants import SubIntents

logger = get_logger(__name__)


class IntentRouter:
    """
    Routes education queries to appropriate sub_intent handlers.
    
    Uses Vector DB (Qdrant) with embedding-based semantic search for intent detection.
    Falls back to keyword matching if Vector DB is disabled or unavailable.
    """
    
    def __init__(self):
        """Initialize intent router with vector DB and embedding managers."""
        self._initialized = False
        self._use_vector_db = False
        self._vector_db_manager = None
        self._embedding_manager = None
        self._intent_patterns = self._load_intent_patterns()
        self._init_lock = asyncio.Lock()  # Prevent race conditions during initialization

        settings = get_settings()
        logger.info(
            f"IntentRouter initialized for education agent "
            f"(vector_db_enabled={settings.ENABLE_VECTOR_DB_ROUTING})"
        )
    
    def _load_intent_patterns(self) -> Dict[str, List[str]]:
        """
        Load intent detection patterns for education (keyword fallback).
        
        Returns:
            Dict mapping sub_intent to keyword patterns
        """
        return {
            "search_material": [
                "tìm tài liệu", "tìm kiếm", "tài liệu học", "giáo trình", "sách", "bài giảng",
                "học python", "học java", "học toán", "học lý", "học hóa", "học văn", "học anh",
                "tài liệu tiếng anh", "tài liệu lập trình", "video học", "khóa học",
                "học cơ bản", "học nâng cao", "tìm bài học", "nguồn học", "học online",
            ],
            "create_exercise": [
                "tạo bài tập", "ra đề", "tạo câu hỏi", "bài tập trắc nghiệm", "đề thi",
                "câu hỏi ôn tập", "bài kiểm tra", "đề cương", "câu hỏi luyện tập",
                "tạo quiz", "tạo đề", "bài tập toán", "bài tập tiếng anh", "bài tập lập trình",
                "tạo bài tập lớp 10", "đề thi thử", "câu hỏi kiểm tra",
            ],
            "correct_exercise": [
                "chữa bài", "sửa bài", "sửa lỗi", "kiểm tra bài", "đánh giá bài",
                "giải bài tập", "giải thích bài", "chấm bài", "review code", "debug",
                "sai ở đâu", "lỗi nào", "cách giải", "hướng dẫn giải", "giải chi tiết",
                "chữa bài toán", "sửa code", "kiểm tra đáp án", "đúng hay sai",
            ],
            "tutor_subject": [
                "hướng dẫn học", "cách học", "học thế nào", "nên học", "phương pháp học",
                "lộ trình học", "bắt đầu học", "học tốt", "học hiệu quả", "mẹo học",
                "trẻ lớp", "học sinh", "con tôi", "dạy con", "dạy trẻ", "giáo dục",
                "học tiếng anh", "học toán", "học lập trình", "học văn", "học lý",
                "ôn thi", "luyện thi", "chuẩn bị thi", "chiến lược học", "kỹ năng học",
            ],
        }
    
    async def initialize(self) -> None:
        """
        Public method to initialize IntentRouter eagerly.

        Should be called during application startup to:
        - Avoid latency spike on first request (500-1000ms saved)
        - Catch configuration errors early (fail-fast)
        - Prevent race conditions from concurrent requests

        This method is thread-safe and idempotent (safe to call multiple times).
        If initialization fails, the router will fallback to keyword-based routing.
        """
        async with self._init_lock:
            if self._initialized:
                logger.debug("IntentRouter already initialized, skipping")
                return

            try:
                await self._initialize()
            except Exception as e:
                # Log error but don't crash - fallback to keyword matching
                logger.error(
                    f"Failed to initialize IntentRouter: {e}",
                    exc_info=True,
                    extra={"event": "intent_router_init_error", "error": str(e)}
                )
                logger.warning("Will fallback to keyword-based routing")
                # Mark as initialized to prevent repeated attempts
                self._initialized = True
                self._use_vector_db = False

    async def route_intent(self, user_query: str) -> str:
        """
        Route user query to appropriate sub_intent.
        
        Uses vector DB semantic search if available, falls back to keyword matching.
        
        Args:
            user_query: The user's question/statement
            
        Returns:
            str: Detected sub_intent or SubIntents.SEARCH_MATERIAL as default
        """
        try:
            # Check if initialized (should be called during startup)
            if not self._initialized:
                logger.warning(
                    "IntentRouter not initialized - using keyword fallback. "
                    "Call initialize() during application startup for better performance."
                )
                return self._route_with_keywords(user_query)

            # Try vector DB routing first if enabled
            if self._use_vector_db:
                try:
                    intent = await self._route_with_vector_db(user_query)
                    if intent:
                        return intent
                except Exception as e:
                    logger.warning(f"Vector DB routing failed, falling back to keywords: {e}")
            
            # Fallback to keyword matching
            return self._route_with_keywords(user_query)
            
        except Exception as e:
            logger.error(f"Error in intent routing: {e}", exc_info=True)
            return SubIntents.SEARCH_MATERIAL

    async def _route_with_vector_db(self, user_query: str) -> Optional[str]:
        """
        Route intent using vector database semantic search.
        
        Args:
            user_query: The user's question/statement
            
        Returns:
            Optional[str]: Detected sub_intent or None if no match above threshold
        """
        if not self._vector_db_manager or not self._embedding_manager:
            return None
        
        try:
            settings = get_settings()
            
            # Get services
            db = self._vector_db_manager.get_db()
            embedding_service = self._embedding_manager.get_embedding_service()
            
            # Check if services are healthy
            if not await db.health_check() or not await embedding_service.health_check():
                logger.warning("Vector DB or embedding service not healthy")
                return None
            
            # Generate query embedding
            query_vector = await embedding_service.embed_query(user_query)
            
            # Search in vector database
            collection_name = settings.INTENT_SAMPLES_COLLECTION_NAME
            search_result = await db.search(
                collection_name=collection_name,
                query_vector=query_vector,
                top_k=settings.VECTOR_TOP_K,
                score_threshold=settings.VECTOR_SCORE_THRESHOLD
            )
            
            # Extract sub_intent from top result
            if search_result.documents:
                top_doc = search_result.documents[0]
                sub_intent = top_doc.metadata.get('sub_intent', SubIntents.SEARCH_MATERIAL)
                logger.info(
                    f"Vector DB routing: '{user_query[:50]}...' -> '{sub_intent}' "
                    f"(score: {top_doc.score:.3f}, matched: '{top_doc.text[:50]}...')"
                )
                return sub_intent
            
            logger.info(f"No vector DB match above threshold for: {user_query[:50]}...")
            return None
            
        except Exception as e:
            logger.error(f"Vector DB search error: {e}", exc_info=True)
            return None
    
    def _route_with_keywords(self, user_query: str) -> str:
        """
        Route intent using keyword pattern matching (fallback).
        
        Args:
            user_query: The user's question/statement
            
        Returns:
            str: Detected sub_intent or "SEARCH_MATERIAL" as default
        """
        # Normalize query for matching
        query_lower = user_query.lower()
        
        # Count matches for each intent
        intent_scores: Dict[str, int] = {}
        
        for intent, patterns in self._intent_patterns.items():
            score = sum(1 for pattern in patterns if pattern in query_lower)
            if score > 0:
                intent_scores[intent] = score
        
        # Return intent with highest score
        if intent_scores:
            detected_intent = max(intent_scores, key=intent_scores.get)
            logger.info(f"Keyword routing: {detected_intent} (scores: {intent_scores})")
            return detected_intent
        
        # Default fallback
        logger.info(f"No keyword match for query: {user_query[:50]}... - using {SubIntents.SEARCH_MATERIAL}")
        return SubIntents.SEARCH_MATERIAL

    async def _initialize(self):
        """
        Initialize intent router with Vector DB and embedding services.
        
        Sets up connections to vector database and embedding service.
        Falls back to keyword matching if initialization fails.
        """
        if self._initialized:
            return
        
        try:
            settings = get_settings()
            
            # Check if vector DB routing is enabled
            if not settings.ENABLE_VECTOR_DB_ROUTING:
                logger.info("Vector DB routing is disabled, using keyword matching only")
                self._use_vector_db = False
                self._initialized = True
                return
            
            # Check if required configuration exists
            if not settings.ENDPOINT_TEXT3_EMBEDDING or not settings.API_KEY_TEXT3_EMBEDDING:
                logger.warning(
                    "Embedding service not configured (missing ENDPOINT_TEXT3_EMBEDDING or API_KEY_TEXT3_EMBEDDING), "
                    "falling back to keyword matching"
                )
                self._use_vector_db = False
                self._initialized = True
                return
            
            # Import managers (lazy import to avoid circular dependencies)
            from agent.services.vector_db.vector_db_manager import get_vector_db_manager
            from agent.services.embedding.embedding_manager import get_embedding_manager
            
            # Initialize managers
            self._vector_db_manager = get_vector_db_manager()
            self._embedding_manager = get_embedding_manager()
            
            # Get services
            db = self._vector_db_manager.get_db()
            embedding_service = self._embedding_manager.get_embedding_service()
            
            # Connect to services
            db_connected = await db.connect()
            embedding_connected = await embedding_service.connect()
            
            if db_connected and embedding_connected:
                # Check if collection exists
                collection_name = settings.INTENT_SAMPLES_COLLECTION_NAME
                if await db.collection_exists(collection_name):
                    self._use_vector_db = True
                    logger.info(f"Vector DB routing enabled with collection: {collection_name}")
                else:
                    logger.warning(
                        f"Vector DB collection '{collection_name}' does not exist. "
                        f"Falling back to keyword matching. "
                        f"Run seed script to populate intent samples."
                    )
                    self._use_vector_db = False
            else:
                logger.warning("Failed to connect to Vector DB or embedding service, using keyword matching")
                self._use_vector_db = False
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize Vector DB routing: {e}", exc_info=True)
            logger.info("Falling back to keyword-based routing")
            self._use_vector_db = False
            self._initialized = True


# Global singleton instance
_intent_router_instance: Optional[IntentRouter] = None


def get_intent_router() -> IntentRouter:
    """
    Get the global IntentRouter singleton instance.
    
    Returns:
        IntentRouter: Singleton router instance
    """
    global _intent_router_instance
    if _intent_router_instance is None:
        _intent_router_instance = IntentRouter()
    return _intent_router_instance

