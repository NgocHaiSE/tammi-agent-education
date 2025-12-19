"""ReasoningNode: Decide whether to call tools for more info or provide the final answer.
"""

import logging
from typing import Dict, Any, List

from agent.graph.node_services.search_material.subgraph.node_interface import HealthAdviceNodeInterface
from agent.graph.node_services.search_material.subgraph.state import SubgraphHealthAdviceState
from agent.graph.node_services.search_material.subgraph.node_register import register_node
from agent.graph.node_register import get_node_class, get_node_instance
from agent.graph.node_services.search_material.symptom_memory import SymptomMemory

from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage, AIMessage
from langgraph.prebuilt import ToolNode

logger = logging.getLogger(__name__)


@register_node
class ReasoningNode(HealthAdviceNodeInterface):
    """Node that performs reasoning with optional tool-calling.

    Keeps the original flow: build system + conversation prompts, bind tools,
    get tool calls from the LLM, then execute them via ToolNode.
    """

    name = "reasoning_node"

    def __init__(self, main_agent=None):
        if main_agent:
            self.main_agent = main_agent
        else:
            main_agent = get_node_instance(name="search_material")
            if not main_agent:
                raise ValueError("Search Material Agent is not registered.")
            self.main_agent = main_agent

        # LLM có thể không tồn tại trong mock -> dùng getattr với default None
        self.llm = getattr(self.main_agent, "llm", None)

        # Initialize base interface (sets prompt dir, formatters, etc.)
        super().__init__(
            main_agent=self.main_agent,
            name=self.name,
            llm=self.llm,
        )

    async def run(self, state: SubgraphHealthAdviceState) -> Dict[str, Any]:
        """Main execution: tool-calling flow preserved."""
        try:
            symptom_history = self._get_symptom_user_history(state)
            health_report = self._get_health_report(state)

            # Build messages (System + Human) dùng template địa phương
            messages = await self._build_prompt(state, question="", health_report=health_report, symptom_user_history=symptom_history)

            # Lấy tools: thử nhiều phương thức phổ biến
            tools = []
            for method_name in ["get_registered_tools", "get_tools", "tools"]:
                meth = getattr(self.main_agent, method_name, None)
                if callable(meth):
                    try:
                        tools = meth() or []
                    except Exception:
                        tools = []
                    break
                elif isinstance(meth, list):
                    tools = meth
                    break

            if tools and self.llm:
                try:
                    tool_calling_llm = self.llm.bind_tools(
                        tools=tools,
                        tool_choice="required",
                        strict=False,
                        parallel_tool_calls=False,
                    )
                    response: BaseMessage = await tool_calling_llm.ainvoke(messages)
                    tool_executor = ToolNode(
                        name="ToolExecutionNode",
                        tools=tools,
                        messages_key="node_responses",
                    )
                    existing_responses: List[BaseMessage] = state.get("node_responses", []) or []
                    new_state = {**state, "node_responses": [*existing_responses, response]}
                    tool_result = await tool_executor.ainvoke(new_state)
                    # Chuẩn hóa output
                    last_msg = (tool_result.get("node_responses") or [None])[-1]
                    reasoning_result = getattr(last_msg, "content", "") if last_msg else ""
                    return {**tool_result, "reasoning_result": reasoning_result, "health_report": reasoning_result or health_report}
                except Exception as tool_err:
                    logger.error(f"[{self.name}] Lỗi gọi tool: {tool_err}", exc_info=True)
                    # Fallback tiếp xuống reasoning trực tiếp

            # Fallback: reasoning trực tiếp
            if not self.llm:
                fallback_text = "Không có LLM khả dụng để suy luận." if not health_report else health_report
                ai_resp = AIMessage(content=fallback_text)
                return {
                    "node_responses": [ai_resp],
                    "health_report": fallback_text,
                    "reasoning_result": fallback_text,
                }
            try:
                ai_resp: BaseMessage = await self.llm.ainvoke(messages)
                if not isinstance(ai_resp, AIMessage):
                    ai_resp = AIMessage(content=str(ai_resp))
                content = ai_resp.content
            except Exception as llm_err:
                logger.error(f"[{self.name}] LLM error: {llm_err}", exc_info=True)
                content = "Không thể truy cập LLM (offline)." if not health_report else health_report
                ai_resp = AIMessage(content=content)
            return {
                "node_responses": [ai_resp],
                "health_report": content,
                "reasoning_result": content,
            }
        except Exception as e:
            logger.error(f"[{self.name}] Lỗi tổng quát: {e}", exc_info=True)
            fallback_text = "Đã xảy ra lỗi nội bộ khi xử lý reasoning." 
            ai_resp = AIMessage(content=fallback_text)
            return {
                "node_responses": [ai_resp],
                "health_report": fallback_text,
                "reasoning_result": fallback_text,
            }

    def _get_symptom_user_history(self, state: SubgraphHealthAdviceState) -> str:
        """Return user symptom history from SymptomMemory as a single string."""
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

    def _get_health_report(self, state: SubgraphHealthAdviceState) -> str:
        """Return health_report from state if available, otherwise an empty string."""
        health_report = state.get("health_report", "")
        if not health_report:
            logger.info(f"[{self.name}] No health report found in state.")
        else:
            logger.info(f"[{self.name}] Health report content: {health_report}")
        return health_report

    async def _build_prompt(
        self,
        state: SubgraphHealthAdviceState,
        question: str = "",
        health_report: str = "",
        symptom_user_history: str = "",
    ) -> List[BaseMessage]:
        """Tạo prompt cho LLM; chữ ký tương thích tests: (state, question, health_report, symptom_user_history)."""
        if not symptom_user_history:
            symptom_user_history = self._get_symptom_user_history(state)
        if not health_report:
            health_report = self._get_health_report(state)

        messages: List[BaseMessage] = []

        # System message
        try:
            system_prompt = self.build_prompt(
                prompt_type="system",
                question=question,
                symptom_user_history=symptom_user_history,
                health_report=health_report,
            )
        except Exception as e:
            logger.warning(f"[{self.name}] Missing system prompt template, using fallback: {e}")
            system_prompt = (
                "You are an educational reasoning assistant. If tools are provided, "
                "choose and call them to gather precise info before answering."
            )
        messages.append(SystemMessage(content=system_prompt))

        # Conversation/Human message
        try:
            conversation_prompt = self.build_prompt(
                prompt_type="conversation_context",
                question=question,
                symptom_user_history=symptom_user_history,
                health_report=health_report,
            )
        except Exception as e:
            logger.warning(f"[{self.name}] Missing conversation prompt template, using fallback: {e}")
            conversation_prompt = (
                "Here is the current health assessment and user symptom history.\n\n"
                f"Health report:\n{health_report}\n\n"
                f"Symptom history:\n{symptom_user_history}\n\n"
                "Decide whether to call tools to verify or augment details; then provide the final advice."
            )
        messages.append(HumanMessage(content=conversation_prompt))

        return messages