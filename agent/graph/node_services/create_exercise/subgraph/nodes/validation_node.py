from typing import Dict, Any
from agent.graph.node_base import NodeBase
from agent.graph.node_services.create_exercise.subgraph.state import CreateExerciseState
from agent.graph.node_services.create_exercise.exercise_memory import ExerciseMemory
from agent.utils.logging import get_logger

logger = get_logger(__name__)


class ValidationNode(NodeBase):
    def __init__(self, llm=None, **kwargs):
        super().__init__(name="validation_node", llm=llm, **kwargs)
        
        # Valid grade-subject combinations
        self.valid_combinations = {
            "toán": list(range(1, 13)),
            "tiếng việt": list(range(1, 13)),
            "tiếng anh": list(range(3, 13)),
            "vật lý": list(range(6, 13)),
            "hóa học": list(range(8, 13)),
            "sinh học": list(range(6, 13)),
            "lịch sử": list(range(6, 13)),
            "địa lý": list(range(6, 13)),
        }
    
    async def run(self, state: CreateExerciseState) -> Dict[str, Any]:
        # Extract from request
        request = state.get("request", {})
        session_id = request.get("session_id", "default")
        content = request.get("payload", {}).get("content", "")

        # Load ExerciseMemory for this session
        memory = ExerciseMemory(session_id=session_id)
        last_context = memory.get_last_context()
        
        # Track user message in conversation history
        memory.add_conversation_message(
            role="human",
            content=content,
            metadata={"request_type": "create_exercise"}
        )
        
        # Get extracted metadata from state (set by MetadataExtractionNode)
        # These have been extracted from natural language content
        extracted_grade = state.get("grade")
        extracted_subject = state.get("subject", "").lower().strip() if state.get("subject") else ""
        extracted_topic = state.get("topic", "").lower().strip() if state.get("topic") else ""
        extracted_difficulty = state.get("difficulty", "").lower().strip() if state.get("difficulty") else ""
        extracted_exercise_type = state.get("exercise_type", "").lower().strip() if state.get("exercise_type") else ""
        extracted_num_exercises = state.get("num_exercises", 5)
        
        logger.info(f"[ValidationNode] Extracted metadata from state: grade={extracted_grade}, subject={extracted_subject}, topic={extracted_topic}, difficulty={extracted_difficulty}")

        # Save partial context immediately - even if validation fails
        # This allows building context over multiple turns
        memory.update_partial_context(
            grade=extracted_grade,
            subject=extracted_subject if extracted_subject else None,
            topic=extracted_topic if extracted_topic else None,
            difficulty=extracted_difficulty if extracted_difficulty else None,
            exercise_type=extracted_exercise_type if extracted_exercise_type else None
        )
        
        # Now merge: extracted values take priority, then fall back to saved context
        # Finally fall back to defaults from settings (EXCEPT for topic which is mandatory)
        from agent.config.settings import get_settings
        settings = get_settings()
        
        grade = extracted_grade or last_context.get("grade") or settings.DEFAULT_GRADE
        subject = extracted_subject or last_context.get("subject") or settings.DEFAULT_SUBJECT
        difficulty = extracted_difficulty or last_context.get("difficulty") or settings.DEFAULT_DIFFICULTY
        
        topic = extracted_topic or last_context.get("topic", "")
        # No default for topic - it is mandatory
        
        exercise_type = extracted_exercise_type or last_context.get("exercise_type", "")
        num_exercises = extracted_num_exercises
        
        logger.info(f"[ValidationNode] After merging with context and defaults: grade={grade}, subject={subject}, topic={topic}, difficulty={difficulty}")

        # Build list of missing required fields
        missing_fields = []
        if not grade:
            missing_fields.append("lớp")
        if not subject:
            missing_fields.append("môn học")
        if not topic:
            missing_fields.append("chủ đề/dạng bài")
        
        # If missing required fields, ask user to provide
        if missing_fields:
            # Build context summary for what we already know
            known_info = []
            if grade:
                known_info.append(f"lớp {grade}")
            if subject:
                known_info.append(f"môn {subject}")
            if topic:
                known_info.append(f"chủ đề {topic}")
            if difficulty:
                known_info.append(f"độ khó {difficulty}")
            
            return self._ask_for_missing_info(
                missing_fields=missing_fields,
                known_info=known_info,
                grade=grade,
                subject=subject,
                topic=topic,
                difficulty=difficulty,
                memory=memory
            )
        
        # Normalize subject
        subject_normalized = self._normalize_subject(subject)
        
        # E02 - Invalid combination
        if not self._is_valid_combination(subject_normalized, grade):
            # Save what we know before returning error
            return self._error_response(
                "E02", grade, subject_normalized,
                topic=topic, difficulty=difficulty, memory=memory
            )
        
        # Normalize exercise_type
        exercise_type_normalized = self._normalize_exercise_type(exercise_type)
        
        # Update preferences in memory (full context now)
        memory.update_preferences({
            "grade": grade,
            "subject": subject_normalized,
            "topic": topic,
            "difficulty": difficulty,
            "exercise_type": exercise_type_normalized
        })
        memory.save_to_file()
        
        logger.info(
            f"Validation passed: grade={grade}, subject={subject_normalized}, "
            f"topic={topic}, difficulty={difficulty}, exercise_type={exercise_type_normalized}, num_exercises={num_exercises}"
        )
        
        return {
            "validated": True,
            "grade": grade,
            "subject": subject_normalized,
            "topic": topic,
            "difficulty": difficulty,
            "exercise_type": exercise_type_normalized,
            "num_exercises": num_exercises,
            "validation_errors": None,
            "next_node": "classifier",
            # Include memory context in state
            "last_context": memory.get_last_context(),
            "user_preferences": memory.get_preferences()
        }
    
    def _ask_for_missing_info(
        self,
        missing_fields: list,
        known_info: list,
        grade: int,
        subject: str,
        topic: str,
        difficulty: str,
        memory: ExerciseMemory
    ) -> Dict[str, Any]:
        """Generate a friendly prompt asking for missing information."""
        
        # Build the question
        missing_str = " và ".join(missing_fields)
        
        if known_info:
            known_str = ", ".join(known_info)
            message = f"Mình đã ghi nhận {known_str}. Bạn vui lòng cho biết thêm {missing_str} nhé!"
        else:
            message = f"Bạn vui lòng cho biết {missing_str} để mình tạo bài tập nhé!"
        
        # Track this AI response
        memory.add_conversation_message(
            role="ai",
            content=message,
            metadata={
                "type": "clarification_request",
                "missing_fields": missing_fields,
                "known_info": known_info
            }
        )
        memory.save_to_file()
        
        logger.info(f"[ValidationNode] Asking for missing info: {missing_fields}")
        
        return {
            "validated": False,
            "validation_errors": "MISSING_INFO",
            "error_messages": message,
            "grade": grade,
            "subject": subject,
            "topic": topic,
            "difficulty": difficulty,
            "next_node": "response_builder"
        }
    
    def _error_response(
        self,
        error_code: str,
        grade: int,
        subject: str,
        topic: str = None,
        difficulty: str = None,
        memory: ExerciseMemory = None
    ) -> Dict[str, Any]:
        """Generate error response based on error code."""
        error_messages = {
            "E01": "Vui lòng cho biết môn học bạn muốn tạo bài tập.",
            "E02": f"Môn {subject} không có ở lớp {grade}. Vui lòng chọn lớp khác hoặc môn học khác.",
            "E03": "Vui lòng cho biết lớp học.",
            "E04": "Vui lòng cho biết lớp học và môn học."
        }
        
        message = error_messages.get(error_code, "Thông tin không hợp lệ.")
        
        # Track this AI response
        if memory:
            memory.add_conversation_message(
                role="ai",
                content=message,
                metadata={"type": "validation_error", "error_code": error_code}
            )
            memory.save_to_file()
        
        return {
            "validated": False,
            "validation_errors": error_code,
            "error_messages": message,
            "grade": grade,
            "subject": subject,
            "topic": topic,
            "difficulty": difficulty,
            "next_node": "response_builder"
        }
    
    def _normalize_subject(self, subject: str) -> str:
        """Normalize subject name."""
        subject_map = {
            "toán": "toán",
            "toan": "toán",
            "math": "toán",
            "tiếng việt": "tiếng việt",
            "tieng viet": "tiếng việt",
            "vietnamese": "tiếng việt",
            "tiếng anh": "tiếng anh",
            "tieng anh": "tiếng anh",
            "english": "tiếng anh",
            "vật lý": "vật lý",
            "vat ly": "vật lý",
            "physics": "vật lý",
            "hóa học": "hóa học",
            "hoa hoc": "hóa học",
            "chemistry": "hóa học",
            "sinh học": "sinh học",
            "sinh hoc": "sinh học",
            "biology": "sinh học",
            "lịch sử": "lịch sử",
            "lich su": "lịch sử",
            "history": "lịch sử",
            "địa lý": "địa lý",
            "dia ly": "địa lý",
            "geography": "địa lý",
        }
        
        return subject_map.get(subject.lower().strip(), subject)
    
    def _is_valid_combination(self, subject: str, grade: int) -> bool:
        """Check if grade-subject combination is valid."""
        if subject not in self.valid_combinations:
            return False
        
        return grade in self.valid_combinations[subject]
    
    def _detect_exercise_type(self, topic: str, content: str) -> str:
        """Detect exercise type from topic and content."""
        content_lower = content.lower()
        topic_lower = topic.lower()
        
        # Detect specific types
        if "trắc nghiệm" in content_lower or "multiple choice" in content_lower:
            return "Trắc nghiệm"
        elif "tự luận" in content_lower or "essay" in content_lower:
            return "Tự luận"
        elif "điền khuyết" in content_lower or "fill" in content_lower:
            return "Điền khuyết"
        else:
            return "Tổng hợp"
    
    def _normalize_exercise_type(self, exercise_type: str) -> str:
        """Normalize exercise type value."""
        if not exercise_type:
            return "Tổng hợp"
        
        exercise_type_lower = exercise_type.lower().strip()
        
        exercise_type_map = {
            "trắc nghiệm": "Trắc nghiệm",
            "trac nghiem": "Trắc nghiệm",
            "multiple choice": "Trắc nghiệm",
            "mc": "Trắc nghiệm",
            "tự luận": "Tự luận",
            "tu luan": "Tự luận",
            "essay": "Tự luận",
            "tổng hợp": "Tổng hợp",
            "tong hop": "Tổng hợp",
            "mixed": "Tổng hợp",
            "điền khuyết": "Điền khuyết",
            "dien khuyet": "Điền khuyết",
            "fill": "Điền khuyết",
        }
        
        return exercise_type_map.get(exercise_type_lower, "Tổng hợp")
