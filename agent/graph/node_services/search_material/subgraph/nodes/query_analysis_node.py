""" Query Analysis Node for Search Material Assistant Agent
"""
import os
import logging

from typing import Dict, Any, List, Callable, Union, Tuple

from agent.graph.node_services.search_material.subgraph.node_interface import HealthAdviceNodeInterface
from agent.graph.node_services.search_material.subgraph.state import SubgraphHealthAdviceState
from agent.graph.node_services.search_material.subgraph.node_register import register_node
from agent.graph.node_register import get_node_class, get_node_instance
from agent.graph.node_services.search_material.symptom_memory import SymptomMemory
from agent.external_clients.http_client import APIGatewayHTTPClient
from agent.config.settings import get_settings

from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage, AIMessage

logger = logging.getLogger(__name__)
settings = get_settings()

@register_node
class QueryAnalysisNode(HealthAdviceNodeInterface):
    """Node that uses a Step-back Strategy to analyze the user's query.
    
    Attributes:
        name (str): The node's unique name.
        main_agent (SearchMaterialAgent): The main search material agent instance.
        llm (LLM): The language model used to generate the final response.
    """
    name = "query_analysis_node"

    def __init__(self, main_agent=None):
        """Initializes the QueryAnalysisNode by setting up the main agent and LLM."""
        if main_agent:
            self.main_agent = main_agent
        else:
            agent = get_node_instance(name="search_material")
            if agent:
                self.main_agent = agent
            else:
                raise ValueError("Search Material Agent is not registered.")
        self.llm = self.main_agent.llm
        
        # Call parent __init__ to set up prompt_template_dir and other attributes
        super().__init__(
            main_agent=self.main_agent,
            name=self.name,
            llm=self.llm
        )

    async def run(self, state: SubgraphHealthAdviceState) -> Dict[str, Any]:
        """Run the query analysis node.

        Args:
            state (SubgraphHealthAdviceState): The current subgraph execution state.
            
        Returns:
            Dict[str, Any]: A dictionary containing the AI message with the final response,
            and optionally an error message.
        """
        try:
            # Access request from nested state dict (SubgraphHealthAdviceState wraps GraphState)
            inner_state = state.get("state", {})
            request = inner_state.get("request", {})
            payload = request.get("payload", {})
            question = payload.get("content", "")

            symptom_user_history = self._get_symptom_user_history(state) + "\n" + question
            retrieval_result_text, retrieval_summary = await self._retrieval_result(state, symptom_user_history)
            
            prediction = await self._create_final_response(state, retrieval_result_text, symptom_user_history)
            
            # Store in symptom memory with session_id
            session_id = request.get("session_id", "default")
            symptom_memory = SymptomMemory(session_id=session_id)
            node_responses = inner_state.get("node_responses", [])
            logger.info(f"[{self.name}] Node responses from state: {len(node_responses)} messages")
            
            # Save last AI message if exists
            if node_responses:
                last_ai_msg = node_responses[-1]
                if isinstance(last_ai_msg, BaseMessage):
                    symptom_memory.add_message("ai", last_ai_msg.content)
            
            symptom_memory.add_message("human", question)
            symptom_memory.save_to_file()
            
            return {
                "node_responses": [prediction],
                "health_report": prediction.content,
                "retrieval_summary": retrieval_summary
            }

        except Exception as e:
            logger.error(f"[QueryAnalysisNode] Error during query analysis: {e}", exc_info=True)
            return {"node_name": self.name, "error": str(e)}
        
    async def _create_final_response(
        self, state: SubgraphHealthAdviceState, retrieval_result: str, symptom_user_history: str = ""
    ) -> AIMessage:
        """Create the final response by combining retrieval results and symptom history.

        Args:
            state (SubgraphHealthAdviceState): The current subgraph execution state.
            retrieval_result (str): The result from the retrieval node.
            symptom_user_history (str): The user's symptom history.
        
        Returns:
            AIMessage: The AI message containing the final response.
        """
        prompt_messages = await self._build_prompt(state, retrieval_result, symptom_user_history)
                
        # call llm.invoke; support both sync and async invocations
        if not self.llm:
            logger.error("[QueryAnalysisNode] LLM is not available on main_agent.")
            return AIMessage(content="LLM is not available.")
        
        logger.info(f"[{self.name}] Sending prompt to LLM with messages: {prompt_messages}")
        
        response: BaseMessage = await self.llm.ainvoke(prompt_messages)
        
        if not isinstance(response, AIMessage):
            logger.warning("[QueryAnalysisNode] LLM response is not an AIMessage; converting.")
            response = AIMessage(content=str(response))
        
        return response

    async def _retrieval_result(self, state: SubgraphHealthAdviceState, query: str) -> Tuple[str, Dict[str, Any]]:
        """Thực hiện truy vấn bằng Tavily Search và trả về nội dung kết hợp của các kết quả.

        Hàm sẽ:
        - Lấy `query` nếu được truyền vào.
        - Gọi Tavily Search API thông qua API Gateway để tìm kiếm thông tin y tế.
        - Parse kết quả từ Tavily.
        - Trả về `combined_text` (chuỗi) — nếu không có kết quả sẽ trả chuỗi thông báo phù hợp.
        - Trong trường hợp lỗi, ghi log và trả về một chuỗi mô tả lỗi.

        Args:
            state (SubgraphHealthAdviceState): Subgraph state (chứa thông tin như node_responses, user_input, ...).
            query (str): Câu truy vấn.

        Returns:
            Tuple[str, Dict[str, Any]]: combined_text (chuỗi kết quả truy vấn) và retrieval_summary (tóm tắt thông tin truy vấn).
        """
        try:
            # Validate query
            if not query:
                logger.info(f"[{self.name}] No query provided for Tavily search.")
                return "No query provided for search.", {}

            # Initialize API Gateway HTTP Client
            api_gateway_url = settings.API_GATEWAY_HTTP_URL
            logger.info(f"[{self.name}] Using API Gateway at: {api_gateway_url}")
            
            async with APIGatewayHTTPClient(
                base_url=api_gateway_url,
                timeout=30.0,
                max_retries=3
            ) as client:
                # Call Tavily search via API Gateway
                logger.info(f"[{self.name}] Calling Tavily search for query: {query!r}")
                response = await client.tavily_search(
                    query=query,
                    search_depth="advanced",  # Use advanced search for educational queries
                    max_results=2,
                    include_answer=True
                )
                
                # Parse Tavily response
                if not response or not isinstance(response, dict):
                    logger.warning(f"[{self.name}] Empty or invalid response from Tavily")
                    return "No search results found.", {}
                
                # Extract data from API Gateway response wrapper
                # API Gateway wraps Tavily response in {"data": {...}, "error": "", "status_code": 200}
                tavily_data = response.get("data", response)  # Fallback to response if no "data" key
                
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
                        header_lines.append(f"Điểm liên quan: {score:.2f}")
                    
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
    
    def _get_symptom_user_history(self, state: SubgraphHealthAdviceState) -> str:
        """Trả về lịch sử triệu chứng của người dùng từ SymptomMemory dưới dạng chuỗi.
        
        Chỉ lấy trường content trong symptom memory.
        
        Args:
            state (SubgraphHealthAdviceState): The current subgraph execution state.
        
        Returns:
            str: Chuỗi lịch sử triệu chứng của người dùng.
        """
        # Extract session_id from state
        inner_state = state.get("state", {})
        request = inner_state.get("request", {})
        session_id = request.get("session_id", "default")
        
        symptom_memory = SymptomMemory(session_id=session_id)
        parsed_history = symptom_memory.get_parsed_history()
        
        if not parsed_history:
            logger.info(f"[{self.name}] No symptom history found.")
        else:
            logger.info(f"[{self.name}] Symptom history content: {parsed_history}")
        
        return parsed_history


    async def _build_prompt(self, state: SubgraphHealthAdviceState, retrieval_result: str, symptom_user_history: str) -> List[BaseMessage]:
        """Build the prompt for the query analysis using local prompt template.

        Args:
            state (SubgraphHealthAdviceState): The current subgraph execution state.
            retrieval_result (str): The text result from the retrieval/search node.
            symptom_user_history (str): The user's symptom history.

        Returns:
            List[BaseMessage]: A formatted prompt for the LLM.
        """
        # Build prompt using local template with PromptFormatter
        # Template path: agent/graph/prompts/query_analysis_node/query_analysis_node-single-prompt.txt
        try:
            single_prompt_content = self.build_prompt(
                prompt_type="single",
                retrieval_result=retrieval_result,
                symptom_user_history=symptom_user_history
            )
            
            logger.info(f"[{self.name}] Built prompt with retrieval results ({len(retrieval_result)} chars) and symptom history ({len(symptom_user_history)} chars)")
            
        except Exception as e:
            logger.error(f"[{self.name}] Error building prompt from local template: {e}", exc_info=True)
            # Fallback to simple prompt if template fails
            single_prompt_content = f"""# Nhiệm vụ:
* Bạn hãy giúp tôi làm bài tập dự đoán bệnh dựa trên triệu chứng.
* Tôi có context về kiến thức và tập hợp các triệu chứng. Các triệu chứng sau có thể dẫn đến bị bệnh lý gì?

# Context (Kiến thức):

{retrieval_result}

# Triệu chứng:
 
{symptom_user_history}
"""
        
        messages = [HumanMessage(content=single_prompt_content)]
        return messages