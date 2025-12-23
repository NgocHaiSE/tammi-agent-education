"""
Extract Input Node.

Handles Text and Image inputs to extract text content for processing.
"""
import logging
from typing import Dict, Any, List, Union

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from agent.graph.node_services.correct_exercise.subgraph.schema import CorrectExerciseState

logger = logging.getLogger(__name__)


class ExtractInputNode:
    """Node for identifying and extracting input types (Text or Image)."""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def run(self, state: CorrectExerciseState) -> Dict[str, Any]:
        """
        Run the extract input node.

        Logic:
        1. Parse input payload.
        2. If Image URL present -> Call Vision LLM -> extracted_text.
        3. If Text only -> extracted_text = text.
        4. Extract trace_id.
        """
        try:
            request = state.get("request", {})
            payload = request.get("payload", {})
            content = payload.get("content", "")
            
            # Extract trace_id
            trace_id = request.get("request_id") or request.get("session_id")
            
            # Check for Image Input (Multimodal)
            has_image = False
            image_urls = []
            
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "image_url":
                        has_image = True
                        url = item.get("image_url", {}).get("url", "")
                        if url:
                            image_urls.append(url)
            
            extracted_text = ""
            
            if has_image:
                logger.info(f"[extract_input] Detected {len(image_urls)} images. Running OCR/Vision analysis.")
                extracted_text = await self._perform_ocr(content)
            else:
                # Standard Text Input
                if isinstance(content, str):
                    extracted_text = content
                elif isinstance(content, list):
                    # Combine text parts if list
                    texts = [item.get("text", "") for item in content if item.get("type") == "text"]
                    extracted_text = "\n".join(texts)
                
            extracted_text = extracted_text.strip()
            
            if not extracted_text:
                logger.warning("[extract_input] Empty input extracted.")
                return {
                    "error_message": "Xin lỗi, tôi không đọc được nội dung câu hỏi. Vui lòng thử lại.",
                    "next_node": "format_output"
                }

            logger.info(f"[extract_input] Extracted text: {extracted_text[:100]}...")

            return {
                "extracted_text": extracted_text,
                "question": extracted_text, # Backward compatibility
                "trace_id": trace_id,
                "next_node": "lookup_history"
            }

        except Exception as e:
            logger.error(f"[extract_input] Error: {e}", exc_info=True)
            return {
                "error_message": "Lỗi khi xử lý đầu vào.",
                "next_node": "format_output"
            }

    async def _perform_ocr(self, content_payload: List[Dict[str, Any]]) -> str:
        """Use Vision LLM to extract text/problem from image."""
        try:
            # System prompt for OCR
            system_msg = SystemMessage(content=(
                "You are an OCR expert for educational content. "
                "Extract all text, formulas, and diagrams from the image into clear text. "
                "Preserve formatting where possible."
            ))
            
            # Construct User Message with Image
            # Content payload is already in LangChain/OpenAI format: [{"type": "text", ...}, {"type": "image_url", ...}]
            user_msg = HumanMessage(content=content_payload)
            
            response = await self.llm.ainvoke([system_msg, user_msg])
            return response.content
            
        except Exception as e:
            logger.error(f"[_perform_ocr] Vision analysis failed: {e}")
            return ""
