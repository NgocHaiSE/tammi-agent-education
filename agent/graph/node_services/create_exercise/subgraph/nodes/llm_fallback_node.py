from typing import Dict, Any
from agent.graph.node_base import NodeBase
from agent.graph.node_services.create_exercise.subgraph.state import CreateExerciseState


class LLMFallbackNode(NodeBase):
    def __init__(self, llm=None, **kwargs):
        super().__init__(name="llm_fallback_node", llm=llm, **kwargs)

    async def run(self, state: CreateExerciseState) -> Dict[str, Any]:
        grade = state.get("grade")
        subject = state.get("subject")
        topic = state.get("topic")
        num_exercises = state.get("num_exercises", 5)
        difficulty = state.get("difficulty", "")  # Get difficulty from state

        # Build prompt for LLM
        prompt = self._build_generation_prompt(grade, subject, topic, num_exercises, difficulty)

        # Call LLM
        response = await self.llm.ainvoke(prompt)

        # Parse response
        exercises = self._parse_llm_response(response.content)

        return {
            "exercises": exercises,
            "generation_metadata": {
                "method": "llm_fallback",
                "tier": 3,
                "model": getattr(self.llm, "model_name", "unknown"),
            },
            "next_node": "quality_check",
        }

    def _build_generation_prompt(
        self, grade: int, subject: str, topic: str, num_exercises: int, difficulty: str = ""
    ) -> str:
        """Build prompt for LLM to generate exercises."""
        
        # Build difficulty description
        if difficulty and difficulty.strip():
            difficulty_normalized = difficulty.strip().lower()
            difficulty_map = {
                "dễ": "Dễ - phù hợp với học sinh trung bình",
                "trung bình": "Trung bình - cần tư duy và vận dụng",
                "khó": "Khó - đòi hỏi tư duy cao và kiến thức nâng cao"
            }
            difficulty_desc = difficulty_map.get(difficulty_normalized, f"{difficulty.capitalize()} - phù hợp với yêu cầu")
        else:
            difficulty_desc = f"Phù hợp với lớp {grade}"
        
        prompt = f"""BẮT BUỘC: Bạn phải trả lời HOÀN TOÀN BẰNG TIẾNG VIỆT.

Bạn là giáo viên {subject} giỏi ở Việt Nam. Hãy tạo {num_exercises} bài tập {subject} cho học sinh lớp {grade} về chủ đề "{topic}".

Yêu cầu BẮT BUỘC:
- BẮT BUỘC: Câu hỏi và đáp án phải HOÀN TOÀN BẰNG TIẾNG VIỆT
- Tạo đúng {num_exercises} bài tập
- Độ khó: {difficulty_desc}
- Bài tập liên quan đến chủ đề "{topic}"
- Mỗi bài tập phải có câu hỏi và đáp án rõ ràng BẰNG TIẾNG VIỆT

Format trả về (JSON) - CHỈ TIẾNG VIỆT:
[
  {{"question": "Câu hỏi 1", "answer": "Đáp án 1"}},
  {{"question": "Câu hỏi 2", "answer": "Đáp án 2"}},
  ...
]

QUAN TRỌNG: Chỉ trả về JSON array tiếng Việt, không thêm text khác. Tất cả câu hỏi và đáp án phải bằng tiếng Việt.

Hãy tạo bài tập ngay:"""

        return prompt

    def _parse_llm_response(self, content: str) -> list:
        """Parse LLM response to extract exercises."""
        import json
        import re

        try:
            # Try to find JSON array in response
            json_match = re.search(r"\[.*\]", content, re.DOTALL)
            if json_match:
                exercises = json.loads(json_match.group())
                return exercises

            # Fallback: Parse line by line
            exercises = []
            lines = content.split("\n")
            current_question = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Detect question
                if re.match(r"^\d+\.", line) or line.lower().startswith("câu"):
                    if current_question:
                        exercises.append(current_question)
                    current_question = {"question": line, "answer": ""}

                # Detect answer
                elif current_question and (
                    "đáp án" in line.lower() or "answer" in line.lower()
                ):
                    current_question["answer"] = re.sub(r"^.*?:", "", line).strip()

            if current_question:
                exercises.append(current_question)

            return (
                exercises
                if exercises
                else [{"question": "Bài tập mẫu", "answer": "Đáp án mẫu"}]
            )

        except Exception as e:
            # Return dummy exercise if parsing fails
            return [{"question": "Không thể parse response", "answer": str(e)}]
