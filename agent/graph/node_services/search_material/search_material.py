import logging
from functools import lru_cache
from typing import Dict, Any, Tuple, List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage

from agent.graph.node_base import NodeBase
from agent.graph.node_register import node_register
from agent.graph.graph_state import GraphState
from agent.external_clients.http_client import APIGatewayHTTPClient
from agent.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@node_register(
    name="search_material",
    priority=90,
    produces=[],
    needs_builders=[],
    parallel_suggestions=False
)
class SearchMaterialNode(NodeBase):
    """
    Search Material Node.
    
    Workflow:
    1. Extract user question from state
    2. Search Tavily for educational content
    3. Format prompt with search results
    4. Call LLM to generate learning materials
    """
    
    def __init__(self, llm: BaseChatModel, **kwargs):
        super().__init__(name="search_material", llm=llm, **kwargs)
    
    async def run(self, state: GraphState) -> Dict[str, Any]:
        """
        Run search material flow.
        
        Args:
            state: Current GraphState with user request
            
        Returns:
            dict: Updated state with node_responses containing learning materials
        """
        try:
            question = state.get("request", {}).get("payload", {}).get("content", "")
            history = state.get("history_chat", [])
            logger.info(f"[{self.name}] Processing question: {question[:100]}...")
            
            # Step 2: Retrieve context using Tavily
            request_meta = state.get("request", {})
            trace_id = request_meta.get("request_id") or request_meta.get("session_id")
            combined_text, retrieval_summary = await self._retrieval_result(question, trace_id)
            logger.info(f"[{self.name}] Retrieval summary: results={retrieval_summary.get('returned_results', 0)}, has_answer={retrieval_summary.get('has_answer', False)}")

            # Step 3: Use combined text as context
            context = combined_text
            
            # Step 4: Load prompt template
            prompt_template = self._load_prompt_template()
            
            # Step 5: Build messages for LLM
            # Format system message with context
            system_message = {
                "role": "system",
                "content": prompt_template.format(context=context)
            }
            
            # Convert history messages to dict format
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
            
            # Convert question to user message
            user_message = {
                "role": "user",
                "content": question
            }
            
            # Build final messages list: [system, ...history, user]
            messages_for_llm = [system_message] + history_dicts + [user_message]
            
            # Step 6: Call LLM
            logger.info(f"[{self.name}] Calling LLM with {len(messages_for_llm)} messages")
            response = await self._call_llm(messages_for_llm)
            
            logger.info(f"[{self.name}] Generated response: {len(response)} chars")
            
            return {
                "node_responses": [AIMessage(content=response)],
                "data_artifacts": {
                    "retrieval_summary": retrieval_summary
                }
            }
            
        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}", exc_info=True)
            error_message = "Xin lỗi, tôi gặp khó khăn trong việc tìm kiếm tài liệu. Vui lòng thử lại hoặc cung cấp thêm thông tin."
            return {
                "node_responses": [AIMessage(content=error_message)]
            }
    
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
                logger.info(f"[{self.name}] No query provided for Tavily search.")
                return "No query provided for search.", {}

            # Initialize API Gateway HTTP Client
            api_gateway_url = settings.API_GATEWAY_HTTP_URL
            logger.info(f"[{self.name}] Using API Gateway at: {api_gateway_url}")
            
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
                logger.info(f"[{self.name}] Calling Tavily search for query: {query!r}")
                response = await client.tavily_search(
                    query=query,
                    search_depth="advanced",
                    max_results=2,
                    include_answer=True,
                    trace_id=trace_id,
                )
                
                # Parse Tavily response
                if not response or not isinstance(response, dict):
                    logger.warning(f"[{self.name}] Empty or invalid response from Tavily")
                    return "No search results found.", {}
                
                # Extract data from API Gateway response wrapper
                tavily_data = response.get("data", response)
                
                # Extract results from Tavily response
                results = tavily_data.get("results", [])
                answer = tavily_data.get("answer", "")
                
                if not results and not answer:
                    logger.info(f"[{self.name}] No results from Tavily search")
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
                
                logger.info(f"[{self.name}] Retrieved {len(results)} results from Tavily for query: {query!r}")
                
                return combined_text, {
                    "query": query,
                    "search_method": "tavily",
                    "returned_results": len(results),
                    "has_answer": bool(answer)
                }

        except Exception as e:
            logger.error(f"[{self.name}] Error during Tavily search in _retrieval_result: {e}", exc_info=True)
            return f"ERROR: Tavily search failed: {e}", {}
    
    @lru_cache(maxsize=1)
    def _load_prompt_template(self) -> str:
        """Load prompt template from file."""
        import os
        
        prompt_dir = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "prompts",
            "search_material"
        )
        prompt_file = os.path.join(prompt_dir, "search_material-default-prompt.txt")
        
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                template = f.read()
            return template
        except Exception as e:
            logger.warning(f"[{self.name}] Failed to load prompt template: {e}")
            # Fallback template
            return (
                "Bạn là một trợ lý tìm kiếm tài liệu học tập. Dựa trên thông tin sau:\n\n"
                "{context}\n\n"
                "Hãy tìm kiếm tài liệu học tập cho yêu cầu: {question}\n\n"
                "Đưa ra các tài liệu liên quan và tóm tắt ngắn gọn nội dung của chúng."
            )
    
    async def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """
        Call LLM to generate response.
        
        Args:
            messages: List of message dicts with role and content
            
        Returns:
            str: LLM response content
        """
        if not self.llm:
            raise ValueError("LLM not initialized")
        
        response = await self.llm.ainvoke(messages)
        
        return response.content