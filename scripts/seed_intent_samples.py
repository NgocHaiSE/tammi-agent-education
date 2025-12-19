"""
Seed Vector Database with Intent Samples

Populates the vector database with education intent examples for semantic routing.
Each example includes Vietnamese/English text with associated sub_intent metadata.
"""
import asyncio
import logging
import sys
import uuid
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agent.config.settings import get_settings
from agent.services.vector_db.vector_db_manager import get_vector_db_manager
from agent.services.vector_db.vector_db_interface import VectorDocument
from agent.services.embedding.embedding_manager import get_embedding_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Intent samples for education agent
INTENT_SAMPLES = {
    "search_material": [
        # Tìm kiếm tài liệu học tập
        "Tìm tài liệu học python cơ bản",
        "Tìm sách học tiếng anh lớp 10",
        "Tài liệu học toán lớp 12",
        "Tìm giáo trình học Java",
        "Tài liệu ôn thi THPT quốc gia",
        "Tìm video học React",
        "Sách học tiếng anh giao tiếp",
        "Tài liệu học machine learning",
        "Giáo trình hóa học đại cương",
        "Tìm bài giảng vật lý 11",
        "Tài liệu luyện thi IELTS",
        "Khóa học lập trình web",
        "Tìm tài liệu học văn 12",
        "Sách học SQL cơ bản",
        "Tài liệu học lịch sử Việt Nam",
        # Tìm tài liệu cho các môn học
        "Tìm tài liệu học toán nâng cao",
        "Giáo trình tiếng anh thiếu nhi",
        "Tài liệu luyện đề văn",
        "Sách học sinh học lớp 9",
        "Tài liệu học hóa hữu cơ",
        "Tìm bài tập vật lý có lời giải",
        "Video học ngữ pháp tiếng anh",
        "Tài liệu học trắc nghiệm toán",
        "Khóa học online miễn phí",
        "Nguồn học lập trình cho người mới",
        "Tài liệu ôn tập cuối kỳ",
        "Sách học tiếng anh cho trẻ em",
        "Tìm đề thi thử đại học",
        "Giáo trình học vẽ cơ bản",
        "Tài liệu học kế toán",
    ],
    "create_exercise": [
        # Tạo bài tập và câu hỏi
        "Tạo bài tập trắc nghiệm tiếng anh lớp 10",
        "Ra đề toán lớp 8",
        "Tạo câu hỏi ôn tập vật lý",
        "Tạo bài tập lập trình Python",
        "Ra đề kiểm tra 15 phút hóa học",
        "Tạo quiz tiếng anh về ngữ pháp",
        "Tạo bài tập toán về phương trình",
        "Ra đề thi giữa kỳ văn học",
        "Tạo câu hỏi trắc nghiệm lịch sử",
        "Tạo bài tập về thì tiếng anh",
        "Ra đề thi thử THPT quốc gia",
        "Tạo bài tập luyện dịch",
        "Tạo câu hỏi ôn tập địa lý",
        "Ra đề kiểm tra SQL",
        "Tạo bài tập về thuật toán",
        # Tạo bài tập theo chủ đề
        "Tạo đề cương ôn tập cuối kỳ",
        "Ra bài tập về mạch điện",
        "Tạo câu hỏi về chiến tranh Việt Nam",
        "Tạo bài tập hình học không gian",
        "Ra đề kiểm tra tiếng anh A2",
        "Tạo quiz về hóa vô cơ",
        "Tạo bài tập văn nghị luận",
        "Ra câu hỏi về sinh học tế bào",
        "Tạo đề luyện thi IELTS",
        "Tạo bài tập code Java",
        "Ra đề kiểm tra ngữ văn",
        "Tạo câu hỏi về hàm số",
        "Tạo bài tập lập trình C++",
        "Ra đề thi cuối kỳ database",
        "Tạo quiz từ vựng tiếng anh",
    ],
    "correct_exercise": [
        # Chữa bài tập, sửa lỗi
        "Giúp tôi chữa bài toán này",
        "Sửa lỗi code Python cho tôi",
        "Kiểm tra bài văn của tôi",
        "Chấm bài tập toán",
        "Sửa lỗi ngữ pháp tiếng anh",
        "Giải thích bài hóa này",
        "Debug code Java giúp tôi",
        "Chữa bài tập vật lý",
        "Kiểm tra đáp án của tôi",
        "Sai ở đâu trong bài này",
        "Giải chi tiết bài toán",
        "Chữa bài viết tiếng anh",
        "Sửa lỗi SQL query",
        "Hướng dẫn giải bài tập",
        "Review code của tôi",
        # Yêu cầu giải thích và sửa lỗi
        "Tại sao bài tôi sai",
        "Cách giải đúng là gì",
        "Giải thích lỗi trong code",
        "Chữa bài tập lập trình",
        "Kiểm tra lời giải toán",
        "Sửa bài luận tiếng anh",
        "Giải đáp thắc mắc bài tập",
        "Phân tích lỗi sai",
        "Hướng dẫn làm lại bài",
        "Chữa bài tiếng anh có giải thích",
        "Debug lỗi runtime",
        "Kiểm tra bài làm của con",
        "Sửa bài tập hóa học",
        "Giải thích phương pháp làm",
        "Review bài viết của tôi",
    ],
    "tutor_subject": [
        # Hướng dẫn học và phương pháp
        "Trẻ lớp 5 nên học tiếng anh thế nào",
        "Cách học toán hiệu quả",
        "Hướng dẫn học lập trình cho người mới",
        "Phương pháp học tiếng anh giao tiếp",
        "Lộ trình học Python từ cơ bản",
        "Con tôi học kém văn nên làm sao",
        "Cách dạy trẻ học chữ",
        "Nên học tiếng anh như thế nào",
        "Phương pháp học hóa hiệu quả",
        "Bắt đầu học lập trình từ đâu",
        "Mẹo học thuộc từ vựng tiếng anh",
        "Chiến lược ôn thi THPT quốc gia",
        "Cách học toán lớp 12",
        "Hướng dẫn học vật lý cơ bản",
        "Phương pháp tự học tiếng anh",
        # Tư vấn giáo dục
        "Học sinh cấp 2 nên học gì",
        "Kỹ năng học tập hiệu quả",
        "Lộ trình học IELTS",
        "Nên cho con học thêm gì",
        "Cách dạy toán cho trẻ tiểu học",
        "Phương pháp học tốt ở lớp 10",
        "Học văn thế nào cho hay",
        "Cách chuẩn bị thi đại học",
        "Dạy con học tiếng anh tại nhà",
        "Phương pháp học ngữ pháp",
        "Lộ trình học web development",
        "Cách ôn tập hiệu quả",
        "Nên học tiếng anh hay tiếng Trung",
        "Phương pháp học tập chủ động",
        "Kỹ năng làm bài thi trắc nghiệm",
    ],
}

async def seed_vector_database():
    """Seed vector database with intent samples."""
    settings = get_settings()
    
    logger.info("Starting vector database seeding process...")
    
    # Get managers
    vector_db_manager = get_vector_db_manager()
    embedding_manager = get_embedding_manager()
    
    try:
        # Initialize services
        logger.info("Connecting to vector database...")
        db = vector_db_manager.get_db()
        await db.connect()
        
        logger.info("Connecting to embedding service...")
        embedding_service = embedding_manager.get_embedding_service()
        await embedding_service.connect()
        
        # Health checks
        if not await db.health_check():
            logger.error("Vector DB health check failed")
            return False
        
        if not await embedding_service.health_check():
            logger.error("Embedding service health check failed")
            return False
        
        logger.info("Services connected successfully")
        
        # Collection setup
        collection_name = settings.INTENT_SAMPLES_COLLECTION_NAME
        embedding_dim = settings.VECTOR_EMBEDDING_DIM
        
        # Check if collection exists
        if await db.collection_exists(collection_name):
            logger.info(f"Collection '{collection_name}' exists. Deleting for fresh seed...")
            await db.delete_collection(collection_name)
        
        # Create collection
        logger.info(f"Creating collection '{collection_name}'...")
        success = await db.create_collection(
            collection_name=collection_name,
            vector_dim=embedding_dim,
            distance_metric=settings.VECTOR_SIMILARITY_METRIC
        )
        
        if not success:
            logger.error("Failed to create collection")
            return False
        
        # Prepare all documents
        all_documents = []
        
        for sub_intent, samples in INTENT_SAMPLES.items():
            logger.info(f"Processing {len(samples)} samples for '{sub_intent}'...")
            
            # Generate embeddings in batch
            embeddings = await embedding_service.embed_texts(samples)
            
            # Create documents
            for text, embedding in zip(samples, embeddings):
                doc = VectorDocument(
                    id=str(uuid.uuid4()),  # Use UUID instead of integer
                    text=text,
                    vector=embedding,
                    metadata={
                        "sub_intent": sub_intent,
                        "language": "vi" if any(ord(c) > 127 for c in text) else "en"
                    }
                )
                all_documents.append(doc)
        
        # Insert all documents
        logger.info(f"Inserting {len(all_documents)} documents into vector database...")
        success, count = await db.insert_documents(collection_name, all_documents)
        
        if success:
            logger.info(f"✅ Successfully seeded {count} intent samples")
            
            # Verify
            total_docs = await db.count_documents(collection_name)
            logger.info(f"Total documents in collection: {total_docs}")
            
            # Test search
            logger.info("\nTesting semantic search...")
            test_queries = [
                "Hôm nay tôi nên mặc gì?",
                "Ăn gì cho bữa trưa?",
                "Tôi đang buồn",
                "Làm gì cho vui?"
            ]
            
            for query in test_queries:
                query_embedding = await embedding_service.embed_query(query)
                search_result = await db.search(
                    collection_name=collection_name,
                    query_vector=query_embedding,
                    top_k=1,
                    score_threshold=0.5
                )
                
                if search_result.documents:
                    top_doc = search_result.documents[0]
                    logger.info(
                        f"Query: '{query}' -> "
                        f"Intent: {top_doc.metadata['sub_intent']} "
                        f"(score: {top_doc.score:.3f})"
                    )
                else:
                    logger.warning(f"No match for query: '{query}'")
            
            return True
        else:
            logger.error("Failed to insert documents")
            return False
        
    except Exception as e:
        logger.error(f"Error seeding database: {e}", exc_info=True)
        return False
    
    finally:
        # Cleanup
        logger.info("Closing connections...")
        await embedding_manager.close_all()
        await vector_db_manager.close_all()


async def main():
    """Main entry point."""
    settings = get_settings()
    
    logger.info("=" * 60)
    logger.info("Vector Database Seeding Script")
    logger.info("=" * 60)
    logger.info(f"Vector DB Provider: {settings.VECTOR_DB_PROVIDER}")
    logger.info(f"Collection Name: {settings.INTENT_SAMPLES_COLLECTION_NAME}")
    logger.info(f"Embedding Provider: {settings.EMBEDDING_PROVIDER}")
    logger.info(f"Embedding Model: {settings.EMBEDDING_MODEL}")
    logger.info(f"Embedding Dimension: {settings.EMBEDDING_DIMENSION}")
    logger.info("=" * 60)
    
    # Check configuration
    if not settings.ENDPOINT_TEXT3_EMBEDDING or not settings.API_KEY_TEXT3_EMBEDDING:
        logger.error("❌ Embedding service not configured!")
        logger.error("Please set ENDPOINT_TEXT3_EMBEDDING and API_KEY_TEXT3_EMBEDDING in .env")
        return
    
    success = await seed_vector_database()
    
    if success:
        logger.info("=" * 60)
        logger.info("✅ Seeding completed successfully!")
        logger.info("=" * 60)
        logger.info("You can now use vector DB-based intent routing.")
        logger.info("Set ENABLE_VECTOR_DB_ROUTING=true in .env to enable it.")
    else:
        logger.error("=" * 60)
        logger.error("❌ Seeding failed!")
        logger.error("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
