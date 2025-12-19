from typing import Dict, Any
from agent.graph.node_base import NodeBase
from agent.graph.node_services.create_exercise.subgraph.state import CreateExerciseState
from agent.graph.node_services.create_exercise.exercise_memory import ExerciseMemory
from langchain_core.messages import AIMessage
from agent.utils.logging import get_logger

logger = get_logger(__name__)


"""Response Builder Node - Build final response"""

class ResponseBuilderNode(NodeBase):
    def __init__(self, llm=None, **kwargs):
        super().__init__(name="response_builder_node", llm=llm, **kwargs)
    
    async def run(self, state: CreateExerciseState) -> Dict[str, Any]:
        """
        Build final response với format chuẩn.
        
        - Format exercises
        - Generate suggestions
        - Create AIMessage cho parent graph
        - Save to ExerciseMemory if successful
        """
        # Check for errors first
        if not state.get("validated"):
            return self._build_error_response(state)
        
        if not state.get("quality_passed"):
            return self._build_quality_error_response(state)
        
        # Build success response
        exercises = state.get("exercises", [])
        grade = state.get("grade")
        subject = state.get("subject")
        topic = state.get("topic")
        difficulty = state.get("difficulty")
        exercise_type = state.get("exercise_type", "Tổng hợp")
        
        # Save to ExerciseMemory
        request = state.get("request", {})
        session_id = request.get("session_id", "default")
        memory = ExerciseMemory(session_id=session_id)
        
        memory.add_exercise_record(
            request_params={
                "grade": grade,
                "subject": subject,
                "topic": topic,
                "difficulty": difficulty,
                "exercise_type": exercise_type,
                "num_exercises": state.get("num_exercises", 5)
            },
            exercises=exercises,
            generation_metadata=state.get("generation_metadata", {})
        )
        
        # Track AI response in conversation history
        response_text = self._format_exercises(exercises, grade, subject, exercise_type, topic, difficulty)
        memory.add_conversation_message(
            role="ai",
            content=response_text,
            metadata={
                "exercises_count": len(exercises),
                "generation_tier": state.get("tier", 0),
                "grade": grade,
                "subject": subject,
                "topic": topic
            }
        )
        
        memory.save_to_file()
        
        logger.info(
            f"Saved {len(exercises)} exercises to memory: "
            f"{subject} lớp {grade}, topic={topic}"
        )
        
        # Generate suggestions
        suggestions = self._generate_suggestions(grade, subject, exercise_type)
        
        # Create AIMessage
        message = AIMessage(
            content=response_text,
            additional_kwargs={
                "tts_message": f"Đã tạo {len(exercises)} bài tập {exercise_type} cho lớp {grade}."
            }
        )
        
        return {
            "node_responses": [message],
            "suggestions": suggestions,
            "next_node": "END"
        }
    
    def _build_error_response(self, state: CreateExerciseState) -> Dict[str, Any]:
        """Build error response for validation failures."""
        error_messages = state.get("error_messages", "Thông tin không hợp lệ.")
        
        message = AIMessage(
            content=error_messages,
            additional_kwargs={
                "tts_message": error_messages,
                "error_code": state.get("validation_errors", "E00")
            }
        )
        
        return {
            "node_responses": [message],
            "suggestions": [],
            "next_node": "END"
        }
    
    def _build_quality_error_response(self, state: CreateExerciseState) -> Dict[str, Any]:
        """Build response when quality check fails."""
        exercises = state.get("exercises", [])
        quality_issues = state.get("quality_issues", [])
        
        message = AIMessage(
            content=f"Đã tạo {len(exercises)} bài tập nhưng có một số vấn đề về chất lượng. Vui lòng kiểm tra lại.",
            additional_kwargs={
                "tts_message": "Đã tạo bài tập nhưng có một số vấn đề về chất lượng.",
                "quality_issues": quality_issues
            }
        )
        
        return {
            "node_responses": [message],
            "suggestions": [],
            "next_node": "END"
        }
    
    def _format_exercises(self, exercises: list, grade: int, subject: str, exercise_type: str, topic: str = "", difficulty: str = "") -> str:
        """Format exercises into readable text."""
        if not exercises:
            return "Không thể tạo bài tập. Vui lòng thử lại."
        
        lines = [f"Đây là {len(exercises)} bài tập {subject} lớp {grade} ({exercise_type}):\n"]
        
        for i, exercise in enumerate(exercises, 1):
            question = exercise.get("question", "")
            # answer = exercise.get("answer", "")
            
            lines.append(f"\n{i}. {question}")
            # User requested to hide answers in the output
            # if answer:
            #     lines.append(f"   Đáp án: {answer}")
        
        # Add friendly suggestion footer
        difficulty_text = difficulty.lower() if difficulty else "cơ bản"
        if not topic:
            topic_str = ""
        else:
            topic_str = f" chủ đề '{topic}'"
            
        footer = f"\n\nTrên đây là {len(exercises)} bài tập {subject} lớp {grade}{topic_str} với mức độ {difficulty_text}.\nBạn có muốn tôi tăng/giảm độ khó hay giải các bài tập này không?"
        lines.append(footer)

        return "\n".join(lines)
    
    def _generate_suggestions(self, grade: int, subject: str, exercise_type: str) -> list:
        """Generate suggestions for next actions."""
        suggestions = [
            "Tăng độ khó",
            "Giảm độ khó",
            "Giải bài tập trên",
        ]
        
        return suggestions
