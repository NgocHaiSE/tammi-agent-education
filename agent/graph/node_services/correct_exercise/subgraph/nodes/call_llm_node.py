"""
Call LLM Node.

Generates the correction/grading response using the LLM.
"""
import logging
from typing import Dict, Any, List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from agent.graph.node_services.correct_exercise.subgraph.schema import CorrectExerciseState

logger = logging.getLogger(__name__)


class CallLLMNode:
    """Node for generating AI response (Grading/Correction)."""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def run(self, state: CorrectExerciseState) -> Dict[str, Any]:
        """
        Run LLM.

        Logic:
        1. Construct Prompt (Teacher Persona).
        2. Inject Context (Reference Context + Ground Truth).
        3. Inject User Input (Extracted Text).
        4. Generate Response.
        """
        try:
            extracted_text = state.get("extracted_text", "")
            reference_context = state.get("reference_context", "")
            ground_truth = state.get("ground_truth", "")
            history = state.get("messages", [])

            if not extracted_text:
                return {
                    "error_message": "Không có nội dung để xử lý.",
                    "next_node": "format_output"
                }

            # Construct System Prompt
            context_block = ""
            if reference_context:
                context_block += f"THÔNG TIN BÀI TẬP/KIẾN THỨC:\n{reference_context}\n\n"
            if ground_truth:
                context_block += f"ĐÁP ÁN ĐÚNG/GỢI Ý:\n{ground_truth}\n\n"
            
            system_content = (
                "Bạn là một Giáo viên tận tâm và chuyên nghiệp.\n"
                "Nhiệm vụ: Chấm bài, chữa bài, hoặc giải đáp thắc mắc của học sinh.\n\n"
                f"{context_block}"
                "HƯỚNG DẪN XỬ LÝ:\n"
                "1. Nếu học sinh đưa ra đáp án cho bài tập có trong 'THÔNG TIN BÀI TẬP':\n"
                "   - So sánh với 'ĐÁP ÁN ĐÚNG'.\n"
                "   - Nhận xét Đúng/Sai.\n"
                "   - Giải thích chi tiết tại sao.\n"
                "2. Nếu học sinh hỏi bài tập ngoài (Context là từ tìm kiếm):\n"
                "   - Giải bài tập đó chi tiết từng bước.\n"
                "3. Luôn dùng giọng văn khích lệ, thân thiện.\n"
                "4. Nếu nội dung không rõ ràng, hãy hỏi lại khéo léo."
            )

            messages = [SystemMessage(content=system_content)]
            
            # Add History
            for msg in history:
                if isinstance(msg, (SystemMessage, HumanMessage, AIMessage)):
                     messages.append(msg)
                elif isinstance(msg, dict):
                    role = msg.get("role")
                    content = msg.get("content")
                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))

            # Add Current Input
            # Note: extracted_text might be OCR result, so we treat it as what the user "sent"
            messages.append(HumanMessage(content=extracted_text))

            logger.info(f"[call_llm] Generating response with context len: {len(context_block)}")
            
            # Bind max_tokens to ensure complete response
            # 4096 tokens should be enough for long reasoning
            llm_with_config = self.llm.bind(max_tokens=4096)
            response = await llm_with_config.ainvoke(messages)

            return {
                "llm_response": response,
                "next_node": "format_output"
            }

        except Exception as e:
            logger.error(f"[call_llm] Error: {e}", exc_info=True)
            return {
                "error_message": "Lỗi khi tạo câu trả lời.",
                "next_node": "format_output"
            }
