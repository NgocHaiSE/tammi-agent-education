from typing import Dict, Any, List, Optional, Tuple
from agent.graph.node_base import NodeBase
from agent.graph.node_services.create_exercise.subgraph.state import CreateExerciseState
from agent.services.embedding.embedding_manager import EmbeddingManager
from agent.services.vector_db.vector_db_manager import VectorDBManager
from agent.utils.logging import get_logger
from agent.config.settings import get_settings
import json
import re
import random

logger = get_logger(__name__)


class RAGNode(NodeBase):

    def __init__(self, llm=None, **kwargs):
        super().__init__(name="rag_node", llm=llm, **kwargs)
        
        settings = get_settings()

        self.vector_db_manager = VectorDBManager()
        self.embedding_manager = EmbeddingManager()

        self.collection_name = getattr(settings, 'ELASTICSEARCH_EXERCISE_INDEX', 'search-math')
        self.top_k = getattr(settings, 'ELASTICSEARCH_EXERCISE_TOP_K', 5)
        self.similarity_threshold = getattr(settings, 'ELASTICSEARCH_EXERCISE_SIMILARITY_THRESHOLD', 0.7)

        logger.info(
            f"RAGNode initialized: index={self.collection_name}, "
            f"top_k={self.top_k}, threshold={self.similarity_threshold}"
        )

    async def run(self, state: CreateExerciseState) -> Dict[str, Any]:
        topic = state.get("topic", "")
        subject = state.get("subject", "")
        grade = state.get("grade", 1)
        exercise_type = state.get("exercise_type", "Trắc nghiệm")
        num_exercises = state.get("num_exercises", 5)
        
        # Extract difficulty from request metadata
        request = state.get("request", {})
        session_id = request.get("session_id", "default")
        metadata = request.get("payload", {}).get("metadata", {})
        difficulty = metadata.get("difficulty", "").strip()

        logger.info(
            "RAGNode: Retrieving relevant contents for topic '%s', subject '%s', grade %d, difficulty '%s'",
            topic,
            subject,
            grade,
            difficulty,
        )

        try:
            # Load ExerciseMemory to get previous questions
            from agent.graph.node_services.create_exercise.exercise_memory import ExerciseMemory
            memory = ExerciseMemory(session_id=session_id)
            previous_questions = memory.get_previous_questions(limit=20)
            
            if previous_questions:
                logger.info(f"RAGNode: Found {len(previous_questions)} previous questions to avoid duplicates")
            
            context, retrieval_metadata = await self._retrieve_context(
                grade=grade, topic=topic, subject=subject, exercise_type=exercise_type, difficulty=difficulty
            )

            prompt = self._build_rag_prompt(
                context=context,
                grade=grade,
                subject=subject,
                topic=topic,
                exercise_type=exercise_type,
                num_exercises=num_exercises,
                difficulty=difficulty,  # Add difficulty parameter
                previous_questions=previous_questions,  # Add previous questions
            )

            logger.info(f"RAGNode calling LLM with {len(context)} context chars")
            # Increase max_tokens to prevent truncation for complex answers
            response = await self.llm.ainvoke(prompt, max_tokens=2048)

            exercises = self._parse_llm_response(response.content)

            logger.info(f"RAGNode generated {len(exercises)} exercises")

            return {
                "exercises": exercises,
                "generation_metadata": {
                    "method": "rag",
                    "tier": 2,
                    "model": getattr(self.llm, "model_name", "unknown"),
                    "retrieval_metadata": retrieval_metadata,
                },
                "next_node": "quality_check",
            }
        except Exception as e:
            logger.error(f"RAGNode encountered an error: {e}")
            logger.warning(f"RAGNode falling back to LLM")
            return {
                "exercises": [],
                "generation_metadata": {
                    "method": "rag_failed",
                    "tier": 2,
                    "error": str(e),
                },
                "next_node": "llm_fallback",
            }

    async def _retrieve_context(
        self, grade: int, subject: str, topic: str, exercise_type: str, difficulty: str = ""
    ) -> Tuple[str, Dict[str, Any]]:
        try:
            query = self._build_search_query(grade, subject, topic, exercise_type, difficulty)
            logger.info(f"RAGNode: Search query: {query}")

            embedding_service = self.embedding_manager.get_embedding_service()
            await embedding_service.connect()
            query_vector = await embedding_service.embed_query(query)
            logger.info(f"RAGNode generated query embedding {len(query_vector)} dims")

            vector_db = self.vector_db_manager.get_db()
            await vector_db.connect()

            # Build keyword fields dynamically - only include non-empty fields
            keyword_fields = {}
            
            # Always include grade and subject (required fields)
            if grade:
                keyword_fields["grade"] = str(grade)
            if subject:
                keyword_fields["subject"] = subject.lower()
            
            # Optional filters - only add if non-empty
            if topic and topic.strip():
                keyword_fields["topic"] = topic.lower().strip()
            
            if difficulty and difficulty.strip():
                keyword_fields["difficulty"] = difficulty.lower().strip()
            
            logger.info(f"RAGNode: Keyword fields for hybrid search: {keyword_fields}")

            # Define candidate pool size (larger than top_k to allow for randomization)
            candidate_k = 50 
            
            # Use hybrid search (combines semantic + keyword matching)
            search_result = await vector_db.hybrid_search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_text=query,
                top_k=candidate_k,  # Fetch larger pool
                score_threshold=self.similarity_threshold,
                keyword_fields=keyword_fields,
                semantic_weight=0.6,  # 60% semantic similarity
                keyword_weight=0.4,   # 40% keyword matching
            )

            if not search_result.documents:
                logger.warning("RAGNode: No relevant documents found")
                return "", {"found": 0, "used": 0, "query": query}

            # Valid documents found
            found_docs = search_result.documents
            total_found = len(found_docs)
            
            # Randomly select top_k documents from the candidates if we have more than enough
            if total_found > self.top_k:
                selected_docs = random.sample(found_docs, self.top_k)
                logger.info(f"RAGNode: Randomly selected {self.top_k} documents from {total_found} candidates")
            else:
                selected_docs = found_docs
                logger.info(f"RAGNode: Used all {total_found} found documents (less than requested top_k={self.top_k})")

            context = self._format_context(selected_docs)

            metadata = {
                "found": total_found,
                "used": len(selected_docs),
                "query": query,
                "avg_score": sum([doc.score for doc in selected_docs])
                / len(selected_docs) if selected_docs else 0,
                "query_time_ms": search_result.query_time_ms,
            }

            logger.info(
                f"RAGNode: Retrieved {len(selected_docs)} documents, avg_score={metadata['avg_score']:.4f}"
            )

            return context, metadata

        except Exception as e:
            logger.error(f"RAGNode: Error during context retrieval: {e}")
            return "", {
                "error": str(e),
                "found": 0,
                "used": 0,
            }

    def _build_search_query(
        self, grade: int, subject: str, topic: str, exercise_type: str, difficulty: str = ""
    ) -> str:
        # Build semantic search query focused on topic and content
        query_parts = [
            f"Bài tập {subject} lớp {grade}",
        ]
        
        if topic and topic.strip():
            query_parts.append(f"về chủ đề {topic}")
        
        if difficulty and difficulty.strip():
            query_parts.append(f"mức độ {difficulty}")
        
        if exercise_type and exercise_type.strip():
            query_parts.append(f"dạng {exercise_type}")
        
        return " ".join(query_parts)

    def _format_context(self, documents: List[Any]) -> str:
        if not documents:
            return ""
        context_parts = ["## Các ví dụ bài tập tham khảo:\n"]
        for i, doc in enumerate(documents, 1):
            try:
                # Handle both nested metadata and top-level fields
                metadata = doc.metadata or {}
                
                # Try to get from source fields first (new structure)
                grade = getattr(doc, 'grade', None) or metadata.get("grade", "unknown")
                subject = getattr(doc, 'subject', None) or metadata.get("subject", "unknown")
                difficulty = getattr(doc, 'difficulty', None) or metadata.get("difficulty", "")
                topic = getattr(doc, 'topic', None) or metadata.get("topic", "")
                score = doc.score or 0
                
                # Build metadata display
                meta_parts = [f"Lớp {grade}", f"Môn {subject}"]
                if difficulty:
                    meta_parts.append(f"Độ khó: {difficulty}")
                if topic:
                    meta_parts.append(f"Chủ đề: {topic}")
                meta_parts.append(f"Điểm: {score:.4f}")
                
                context_parts.append(
                    f"\n### Ví dụ {i} ({', '.join(meta_parts)})\n"
                )

                if doc.text:
                    # New structure: text is direct question content, not JSON
                    # Just display the text directly (truncate if too long)
                    text_content = doc.text.strip()
                    if len(text_content) > 500:
                        text_content = text_content[:500] + "..."
                    
                    context_parts.append(f"Nội dung:\n{text_content}\n")

            except Exception as e:
                logger.warning(f"RAGNode failed to parse document {i}: {e}")
                continue

        return "\n".join(context_parts)

    def _build_rag_prompt(
        self,
        grade: int,
        subject: str,
        topic: str,
        exercise_type: str,
        num_exercises: int,
        context: str,
        difficulty: str = "",  # Add difficulty parameter
        previous_questions: list = None,
    ) -> str:
        """Build prompt with retrieved context for LLM.
        
        Format optimized for Qwen2-Math/Qwen2.5-Math models:
        - Uses step-by-step reasoning approach
        - Clear Vietnamese language instruction
        - Structured output format (JSON)
        - Duplicate avoidance if previous questions provided
        - Dynamic difficulty from metadata extraction
        """

        # System-like instruction at the beginning (Qwen2-Math format)
        prompt = f"""Bạn là giáo viên {subject} giỏi ở Việt Nam với chuyên môn cao. 
Nhiệm vụ của bạn là tạo bài tập chất lượng cao cho học sinh.

BẮT BUỘC: Toàn bộ câu hỏi và đáp án phải viết BẰNG TIẾNG VIỆT.
"""

        # Add context if available - emphasize following the style
        if context:
            prompt += f"""
## CÁC VÍ DỤ BÀI TẬP THAM KHẢO (ĐỂ THAM KHẢO DẠNG BÀI VÀ CẤU TRÚC):

{context}

**HƯỚNG DẪN SỬ DỤNG VÍ DỤ**:
- Tham khảo SỐ LIỆU và CÁCH TRÌNH BÀY của ví dụ.
- **ƯU TIÊN LỚN NHẤT**: Phải đúng Chủ đề "{topic}" và Độ khó "{difficulty}" mà người dùng yêu cầu.
- Nếu ví dụ KHÔNG khớp với chủ đề hoặc độ khó yêu cầu, hãy **SÁNG TẠO** bài mới phù hợp hơn, chỉ cần giữ style trình bày tương tự.
- Đừng copy y nguyên ví dụ nếu nó quá đơn giản so với yêu cầu "Khó".

---

"""
        
        # Add previous questions to avoid duplicates
        if previous_questions:
            prompt += "## Các câu hỏi đã tạo trước đó (KHÔNG được lặp lại):\n\n"
            for i, q in enumerate(previous_questions[:10], 1):  # Show max 10
                prompt += f"{i}. {q}\n"
            prompt += "\n**LƯU Ý**: Tạo câu hỏi MỚI, KHÁC BIỆT hoàn toàn với các câu trên.\n\n"
            prompt += "---\n\n"

        # Main task description
        prompt += f"""## Nhiệm vụ:
Dựa vào các ví dụ bài tập tham khảo ở trên, hãy tạo {num_exercises} bài tập {exercise_type} {subject} cho học sinh lớp {grade}"""
        
        if topic:
            prompt += f" về chủ đề '{topic}'"
        
        prompt += ".\n"

        # Requirements - clear and structured
        prompt += f"""
## Yêu cầu khi tạo bài tập:

1. **Ngôn ngữ**: Câu hỏi và đáp án phải HOÀN TOÀN BẰNG TIẾNG VIỆT
2. **Số lượng**: Tạo đúng {num_exercises} bài tập
3. **Độ khó**: """
        
        # Use extracted difficulty or default
        if difficulty and difficulty.strip():
            difficulty_normalized = difficulty.strip().lower()
            difficulty_map = {
                "dễ": "Dễ - phù hợp với học sinh trung bình",
                "trung bình": "Trung bình - cần tư duy và vận dụng",
                "khó": "Khó - đòi hỏi tư duy cao và kiến thức nâng cao"
            }
            difficulty_desc = difficulty_map.get(difficulty_normalized, f"{difficulty.capitalize()} - phù hợp với yêu cầu")
            prompt += difficulty_desc
        else:
            prompt += f"Phù hợp với trình độ học sinh lớp {grade}"
        
        prompt += f"""
4. **Dạng bài**: {exercise_type}"""
        
        if topic:
            prompt += f"""
5. **Nội dung**: Liên quan trực tiếp đến chủ đề '{topic}'"""
        
        if context:
            prompt += """
6. **Linh hoạt dựa trên ví dụ**: 
   - Tham khảo format của ví dụ, nhưng nội dung phải PHÙ HỢP NHẤT với Topic và Difficulty yêu cầu.
   - Nếu yêu cầu "Khó" mà ví dụ "Dễ", hãy nâng cấp bài toán lên (thêm bước, thêm điều kiện)."""
        else:
            prompt += """
6. **Tính độc đáo**: 
   - Tạo nội dung mới với số liệu và tình huống khác biệt"""
        
        if previous_questions:
            prompt += """
7. **TUYỆT ĐỐI KHÔNG lặp lại các câu hỏi đã tạo trước đó**"""
        
        prompt += """

## Chất lượng:
- Câu hỏi phải rõ ràng, dễ hiểu
- Đáp án phải chính xác và đầy đủ
- Nếu là Toán, hãy reasoning từng bước để đảm bảo đáp án đúng

## Format đầu ra (JSON Array):

Trả về ĐÚNG format JSON array như sau, KHÔNG thêm text giải thích:

```json
[
  {
    "question": "Câu hỏi tiếng Việt số 1 ở đây",
    "answer": "Đáp án tiếng Việt số 1 ở đây",
    "difficulty": "Dễ"
  },
  {
    "question": "Câu hỏi tiếng Việt số 2 ở đây",
    "answer": "Đáp án tiếng Việt số 2 ở đây",
    "difficulty": "Trung bình"
  }
]
```

Các mức độ khó: "Dễ", "Trung bình", "Khó"

Bây giờ hãy bắt đầu tạo {num_exercises} bài tập THEO ĐÚNG DẠNG VÍ DỤ THAM KHẢO. Chỉ trả về JSON array, không thêm text khác:"""

        return prompt

    
    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response to extract exercises."""
        try:
            # Check if response is empty
            if not response or not response.strip():
                logger.error(f"[RAGNode] LLM returned empty response")
                return []
            
            # Try to find JSON in response
            response = response.strip()
            logger.debug(f"[RAGNode] Raw response length: {len(response)}, first 200 chars: {response[:200]}")
            
            # Remove markdown code blocks if present
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                response = response.replace("```json", "").replace("```", "").strip()
            
            # Try to find JSON array in the response
            start_idx = response.find("[")
            end_idx = response.rfind("]")
            if start_idx >= 0 and end_idx > start_idx:
                response = response[start_idx:end_idx+1]
                logger.debug(f"[RAGNode] Extracted JSON array: {response[:200]}")
            
            # Parse JSON
            try:
                exercises = json.loads(response)
            except json.JSONDecodeError:
                # If parsing fails, try to sanitize the JSON string
                logger.warning(f"[RAGNode] JSON parsing failed, attempting to sanitize response")
                sanitized_response = self._sanitize_json(response)
                try:
                    exercises = json.loads(sanitized_response)
                except json.JSONDecodeError:
                     # Attempt to repair truncated JSON
                    logger.warning(f"[RAGNode] Sanitization failed, attempting to repair truncated JSON")
                    repaired_response = self._repair_truncated_json(sanitized_response)
                    exercises = json.loads(repaired_response)

            
            if not isinstance(exercises, list):
                logger.warning(f"[RAGNode] Response is not a list, wrapping")
                exercises = [exercises]
            
            logger.info(f"[RAGNode] Successfully parsed {len(exercises)} exercises from JSON")
            return exercises
            
        except json.JSONDecodeError as e:
            logger.error(f"[RAGNode] Failed to parse JSON: {e}")
            logger.error(f"[RAGNode] Raw response (first 500 chars): {response[:500] if response else 'EMPTY'}")
            
            # Fallback: try to extract exercises from text
            return self._fallback_parse(response)
        
    def _fallback_parse(self, text: str) -> List[Dict[str, Any]]:
        """Fallback parser for non-JSON responses."""
        exercises = []
        
        # Simple pattern matching for question-answer pairs
        lines = text.split("\n")
        current_question = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if any(marker in line.lower() for marker in ["câu hỏi", "question", "bài"]):
                if current_question:
                    exercises.append({"question": current_question, "answer": "N/A"})
                current_question = line
            elif any(marker in line.lower() for marker in ["đáp án", "answer", "giải"]):
                if current_question:
                    exercises.append({"question": current_question, "answer": line})
                    current_question = None
        
        if current_question:
            exercises.append({"question": current_question, "answer": "N/A"})
        
        logger.info(f"[RAGNode] Fallback parse extracted {len(exercises)} exercises")
        return exercises

    def _sanitize_json(self, json_str: str) -> str:
        """Sanitize JSON string by escaping invalid backslashes."""
        # Regex to match backslashes that are NOT followed by valid escape characters
        # Valid escapes: " \ / b f n r t u
        # pattern = r'\\(?![/u"\\bfnrt])'
        # return re.sub(pattern, r'\\\\', json_str)
        
        # Simpler approach: Replace single backslashes that are deemed invalid.
        # However, to be safe against complex LaTeX, we might want to just escape ALL backslashes 
        # that are not part of a valid json escape.
        # But for now, let's stick to the previous regex which was verified for simple cases.
        # Improved regex to handle common LaTeX patterns better if needed, 
        # but the previous one: pattern = r'\\(?![/u"\\bfnrt])' matches \ that is NOT followed by valid chars.
        
        pattern = r'\\(?![/u"\\bfnrt])'
        return re.sub(pattern, r'\\\\', json_str)

    def _repair_truncated_json(self, json_str: str) -> str:
        """Attempt to close a truncated JSON array."""
        json_str = json_str.strip()
        
        # If it doesn't end with ']', keep adding chars to close the structure
        if not json_str.endswith("]"):
            # Check if we are inside a string (odd number of quotes?) - simple check
            # This is complex to do perfectly, but acts as a best-effort heuristic
            
            # Close open structures
            # 1. Close string if open
            if json_str.count('"') % 2 != 0:
                json_str += '"'
            
            # 2. Close object if open
            if json_str.rstrip()[-1] != '}':
                 # If we just closed a string, check again
                 # If ends with comma, remove it
                 if json_str.rstrip().endswith(','):
                     json_str = json_str.rstrip().rstrip(',')
                 
                 json_str += '}'
            
            # 3. Close array
            json_str += ']'
            
        return json_str


