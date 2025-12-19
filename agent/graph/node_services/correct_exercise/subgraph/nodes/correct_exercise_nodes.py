"""
Correct Exercise Nodes Implementation.

Class-based nodes for correct exercise flow with async methods.
"""
import logging
import os
from functools import lru_cache
from typing import Dict, Any, Tuple, List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage

from agent.graph.node_services.correct_exercise.subgraph.schema import CorrectExerciseState
from agent.external_clients.http_client import APIGatewayHTTPClient
from agent.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CorrectExerciseNodes:
    """Class containing all correct exercise flow nodes as async methods."""

    def __init__(self, llm: BaseChatModel):
        """
        Initialize correct exercise nodes.

        Args:
            llm: LLM instance for generating responses
        """
        self.llm = llm
        logger.info("CorrectExerciseNodes initialized with LLM")

    async def extract_question(self, state: CorrectExerciseState) -> Dict[str, Any]:
        """
        Node 1: Extract Question

        Steps:
        1. Extract user question from state
        2. Extract trace_id for logging
        3. Store question and trace_id in state

        Args:
            state: Current correct exercise state

        Returns:
            Updated state with question and trace_id
        """
        try:
            # Step 1: Extract question with validation
            question = state.get("question", "").strip()
            
            if not question:
                logger.warning("[extract_question] Empty question provided")
                error_msg = "Xin lỗi, tôi không nhận được câu hỏi nào. Vui lòng cung cấp bài tập cần chữa."
                return {
                    "error_message": error_msg,
                    "next_node": "format_output"
                }
            
            logger.info(f"[extract_question] Processing question: {question[:100]}...")

            # Step 2: Extract trace_id
            request_meta = state.get("request", {})
            trace_id = request_meta.get("request_id") or request_meta.get("session_id")

            logger.info(f"[extract_question] Question extracted, trace_id: {trace_id}")

            # Step 3: Store in state
            return {
                "question": question,
                "trace_id": trace_id,
                "next_node": "retrieve_context"
            }

        except Exception as e:
            logger.error(f"[extract_question] Error: {e}", exc_info=True)
            error_msg = "Xin lỗi, tôi gặp khó khăn trong việc đọc câu hỏi. Vui lòng thử lại."
            return {
                "error_message": error_msg,
                "next_node": "format_output"
            }

    async def retrieve_context(self, state: CorrectExerciseState) -> Dict[str, Any]:
        """
        Node 2: Retrieve Context

        Steps:
        1. Get question and trace_id from state
        2. Perform Tavily search via API Gateway
        3. Parse and format search results
        4. Store combined_text and retrieval_summary in state

        Args:
            state: Current correct exercise state

        Returns:
            Updated state with combined_text and retrieval_summary
        """
        try:
            # Check if we have an error from previous node
            if state.get("error_message"):
                return {"next_node": "format_output"}

            # Step 1: Get question and trace_id
            question = state.get("question", "")
            history = state.get("messages", [])
            trace_id = state.get("trace_id")

            if not question:
                logger.warning("[retrieve_context] No question provided")
                return {
                    "combined_text": "No query provided for search.",
                    "retrieval_summary": {},
                    "next_node": "call_llm"
                }

            # Step 2: Perform Tavily search
            combined_text, retrieval_summary = await self._retrieval_result(question, trace_id)
            logger.info(
                f"[retrieve_context] Retrieval summary: "
                f"results={retrieval_summary.get('returned_results', 0)}, "
                f"has_answer={retrieval_summary.get('has_answer', False)}"
            )

            # Step 3: Store in state
            return {
                "combined_text": combined_text,
                "retrieval_summary": retrieval_summary,
                "next_node": "call_llm"
            }

        except Exception as e:
            logger.error(f"[retrieve_context] Error: {e}", exc_info=True)
            # Continue to LLM even on retrieval error (with empty context)
            return {
                "combined_text": "Không tìm thấy tài liệu tham khảo.",
                "retrieval_summary": {},
                "next_node": "call_llm"
            }

    async def call_llm(self, state: CorrectExerciseState) -> Dict[str, Any]:
        """
        Node 3: Call LLM

        Steps:
        1. Check if LLM call is needed
        2. Load prompt template
        3. Format prompt with context and question
        4. Call LLM to generate response
        5. Store response in state

        Args:
            state: Current correct exercise state

        Returns:
            Updated state with llm_response
        """
        try:
            # Check if we have an error from previous node
            if state.get("error_message"):
                return {"next_node": "format_output"}

            question = state.get("question", "")
            history = state.get("messages", [])
            context = state.get("combined_text", "")

            if not question:
                logger.error("[call_llm] No question available")
                return {
                    "error_message": "Xin lỗi, không tìm thấy câu hỏi để xử lý.",
                    "next_node": "format_output"
                }

            # 1. Load system prompt template
            system_template = self._load_prompt_template()

            # 2. Format system message with context and question
            system_message = {
                "role": "system",
                "content": system_template.format(context=context, question=question)
            }

            # 3. Convert history messages to dict format
            # History contains BaseMessage objects, convert to dict format
            history_dicts = []
            for msg in history:
                if hasattr(msg, 'type'):
                    # LangChain message
                    role = "assistant" if msg.type == "ai" else "user"
                    history_dicts.append({
                        "role": role,
                        "content": msg.content
                    })
                elif isinstance(msg, dict):
                    # Already in dict format
                    history_dicts.append(msg)

            # 4. Convert question to user message
            user_message = {
                "role": "user",
                "content": question or ""
            }

            # 5. Build final messages list: [system, ...history, user]
            messages = [system_message] + history_dicts + [user_message]

            # Step 3: Call LLM
            response = await self.llm.ainvoke(messages)

            logger.info(f"[call_llm] Generated response: {len(response.content)} chars")

            # Step 4: Store response
            return {
                "llm_response": response,
                "next_node": "format_output"
            }

        except Exception as e:
            logger.error(f"[call_llm] Error: {e}", exc_info=True)
            error_msg = "Xin lỗi, tôi gặp khó khăn trong việc tạo câu trả lời. Vui lòng thử lại."
            return {
                "error_message": error_msg,
                "next_node": "format_output"
            }

    async def format_output(self, state: CorrectExerciseState) -> Dict[str, Any]:
        """
        Node 4: Format Output

        Steps:
        1. Check for errors
        2. Format final response as AIMessage
        3. Prepare data artifacts with retrieval summary
        4. Return formatted output

        Args:
            state: Current correct exercise state

        Returns:
            Updated state with node_responses and data_artifacts
        """
        try:
            # Step 1: Check for errors
            error_message = state.get("error_message")
            if error_message:
                logger.warning(f"[format_output] Returning error message: {error_message}")
                return {
                    "node_responses": [AIMessage(content=error_message)],
                    "data_artifacts": {}
                }

            # Step 2: Get LLM response
            llm_response = state.get("llm_response")
            if not llm_response:
                fallback_msg = (
                    "Xin lỗi, tôi gặp khó khăn trong việc chữa bài tập. "
                    "Vui lòng thử lại hoặc cung cấp thêm thông tin về bài tập."
                )
                logger.warning("[format_output] No LLM response, using fallback")
                return {
                    "node_responses": [AIMessage(content=fallback_msg)],
                    "data_artifacts": {}
                }

            # Step 3: Extract content from AIMessage
            # llm_response is already an AIMessage from call_llm
            if isinstance(llm_response, AIMessage):
                response_content = llm_response.content
            elif isinstance(llm_response, str):
                response_content = llm_response
            else:
                response_content = str(llm_response)
            
            response_message = AIMessage(content=response_content)

            # Step 4: Prepare data artifacts
            retrieval_summary = state.get("retrieval_summary", {})
            data_artifacts = {}
            
            if retrieval_summary:
                data_artifacts["retrieval_summary"] = retrieval_summary

            logger.info(f"[format_output] Final response length: {len(response_content)} chars")

            return {
                "node_responses": [response_message],
                "data_artifacts": data_artifacts
            }

        except Exception as e:
            logger.error(f"[format_output] Error: {e}", exc_info=True)
            fallback_msg = (
                "Xin lỗi, tôi gặp khó khăn trong việc chữa bài tập. "
                "Vui lòng thử lại hoặc cung cấp thêm thông tin về bài tập."
            )
            return {
                "node_responses": [AIMessage(content=fallback_msg)],
                "data_artifacts": {}
            }

    # ========== Helper Methods ==========

    async def _retrieval_result(
        self, 
        query: str, 
        trace_id: str | None = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Perform Tavily search and produce combined text.

        Args:
            query: Search query string
            trace_id: Optional trace ID for logging

        Returns:
            Tuple of:
                - combined_text: Formatted search results as string
                - retrieval_summary: Dict with search metadata
        """
        try:
            if not query:
                logger.info("[_retrieval_result] No query provided for Tavily search.")
                return "No query provided for search.", {}

            # Initialize API Gateway HTTP Client
            api_gateway_url = settings.API_GATEWAY_HTTP_URL
            logger.info(f"[_retrieval_result] Using API Gateway at: {api_gateway_url}")
            
            timeout = getattr(settings, "EXTERNAL_CLIENT_TIMEOUT", 30.0) or 30.0
            max_retries = getattr(settings, "EXTERNAL_CLIENT_MAX_RETRIES", 3) or 3
            cb_threshold = getattr(settings, "CIRCUIT_BREAKER_THRESHOLD", 5) or 5
            cb_timeout = getattr(settings, "CIRCUIT_BREAKER_TIMEOUT", 60) or 60

            async with APIGatewayHTTPClient(
                base_url=api_gateway_url,
                timeout=float(timeout),
                max_retries=int(max_retries),
                circuit_breaker_threshold=int(cb_threshold),
                circuit_breaker_timeout=int(cb_timeout),
            ) as client:
                # Call Tavily search via API Gateway
                logger.info(f"[_retrieval_result] Calling Tavily search for query: {query!r}")
                response = await client.tavily_search(
                    query=query,
                    search_depth="advanced",
                    max_results=2,
                    include_answer=True,
                    trace_id=trace_id,
                )
                
                # Parse Tavily response
                if not response or not isinstance(response, dict):
                    logger.warning("[_retrieval_result] Empty or invalid response from Tavily")
                    return "No search results found.", {}
                
                # Extract data from API Gateway response wrapper
                tavily_data = response.get("data", response)
                
                # Extract results from Tavily response
                results = tavily_data.get("results", [])
                answer = tavily_data.get("answer", "")
                
                if not results and not answer:
                    logger.info("[_retrieval_result] No results from Tavily search")
                    return "No search results found.", {}
                
                # Build combined text from Tavily results
                entry_parts: List[str] = []
                
                # Add the AI-generated answer if available
                if answer:
                    entry_parts.append(f"=== Tóm tắt từ Tavily AI ===\n{answer}\n")
                
                # Add individual search results
                for idx, result in enumerate(results, 1):
                    title = result.get("title", "")
                    url = result.get("url", "")
                    content = result.get("content", "")
                    score = result.get("score", 0)
                    
                    header_lines = [f"--- Kết quả {idx} ---"]
                    if title:
                        header_lines.append(f"Tiêu đề: {title}")
                    if url:
                        header_lines.append(f"Nguồn: {url}")
                    if score:
                        header_lines.append(f"Độ liên quan: {score:.2f}")
                    
                    header = "\n".join(header_lines)
                    entry = f"{header}\n{content}\n"
                    entry_parts.append(entry)
                
                combined_text = "\n".join(entry_parts).strip()
                
                if not combined_text:
                    combined_text = "No search results content available."
                
                logger.info(f"[_retrieval_result] Retrieved {len(results)} results from Tavily for query: {query!r}")
                
                return combined_text, {
                    "query": query,
                    "search_method": "tavily",
                    "returned_results": len(results),
                    "has_answer": bool(answer)
                }

        except Exception as e:
            logger.error(f"[_retrieval_result] Error during Tavily search: {e}", exc_info=True)
            return f"ERROR: Tavily search failed: {e}", {}

    @lru_cache(maxsize=1)
    def _load_prompt_template(self) -> str:
        """Load prompt template from file."""
        prompt_dir = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "..",
            "prompts",
            "correct_exercise"
        )
        prompt_file = os.path.join(prompt_dir, "correct_exercise-default-prompt.txt")

        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                template = f.read()
            logger.info(f"[_load_prompt_template] Loaded template from: {prompt_file}")
            return template
        except Exception as e:
            logger.warning(f"[_load_prompt_template] Failed to load prompt template: {e}")
            # Fallback template
            return (
                "Bạn là giáo viên chuyên nghiệp. QUAN TRỌNG: Trả lời bằng tiếng Việt.\n\n"
                "Dựa trên thông tin sau:\n{context}\n\n"
                "Hãy chữa bài tập: {question}\n\n"
                "Giải thích chi tiết, chỉ ra lỗi sai và hướng dẫn cách làm đúng."
            )
