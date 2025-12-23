"""
Evaluate Node.

Reviews and corrects the generated solution for accuracy and spelling.
"""
import logging
from typing import Dict, Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from agent.graph.node_services.correct_exercise.subgraph.schema import CorrectExerciseState

logger = logging.getLogger(__name__)


class EvaluateNode:
    """Node for evaluating and refining AI response."""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def run(self, state: CorrectExerciseState) -> Dict[str, Any]:
        """
        Run Evaluation.

        Logic:
        1. Get original question and generated draft response.
        2. use LLM to review for:
           - Correctness (Math/Logic/Fact)
           - Spelling/Grammar (Vietnamese)
        3. Return improved response.
        """
        try:
            # Inputs
            extracted_text = state.get("extracted_text", "")
            draft_response = state.get("llm_response", "")

            # If draft is an AIMessage, get content
            if isinstance(draft_response, AIMessage):
                draft_content = draft_response.content
            elif hasattr(draft_response, "content"):
                draft_content = draft_response.content
            else:
                draft_content = str(draft_response)

            if not draft_content:
                logger.warning("[evaluate_node] No draft response to evaluate.")
                return {"next_node": "format_output"}

            # Construct Prompt
            system_content = (
                "Bạn là một Chuyên gia Kiểm định chất lượng giáo dục (QA/Reviewer).\n"
                "Nhiệm vụ: Kiểm tra lời giải bài tập được đưa ra bởi AI giáo viên.\n"
                "TIÊU CHÍ ĐÁNH GIÁ:\n"
                "1. TÍNH CHÍNH XÁC: Lời giải có đúng về mặt toán học/khoa học không? Logic có chặt chẽ không?\n"
                "2. CHÍNH TẢ & NGỮ PHÁP: Kiểm tra lỗi chính tả tiếng Việt, câu từ có mượt mà, dễ hiểu với học sinh không?\n\n"
                "HÀNH ĐỘNG:\n"
                "- Nếu lời giải hoàn hảo: Trả lại nguyên văn lời giải đó (bạn có thể chỉnh lại format cho đẹp).\n"
                "- Nếu có lỗi sai (dù nhỏ): Hãy viết lại lời giải đã được sửa chữa hoàn chỉnh.\n"
                "- KHÔNG thêm các câu như 'Lời giải này đã đúng', 'Tôi đã sửa lại...'. Chỉ đưa ra KẾT QUẢ CUỐI CÙNG (lời giải bài tập) để gửi cho học sinh.\n"
            )

            user_content = (
                f"CÂU HỎI TRUY VẤN CỦA HỌC SINH:\n{extracted_text}\n\n"
                f"LỜI GIẢI DỰ THẢO:\n{draft_content}\n\n"
                "Hãy đưa ra bản lời giải cuối cùng tốt nhất:"
            )

            messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=user_content)
            ]

            logger.info("[evaluate_node] Evaluating draft response...")
            
            # Bind max_tokens to ensure complete response
            llm_with_config = self.llm.bind(max_tokens=4096)
            response = await llm_with_config.ainvoke(messages)

            return {
                "llm_response": response,
                "next_node": "format_output"
            }

        except Exception as e:
            logger.error(f"[evaluate_node] Error: {e}", exc_info=True)
            # If eval fails, pass through the original draft (better than nothing)
            return {
                "next_node": "format_output"
            }
