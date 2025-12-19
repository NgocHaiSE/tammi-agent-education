""" Node that analyze educational images to a report.
"""
import os
import logging

from typing import Dict, Any, List, Union

from agent.graph.node_services.search_material.subgraph.node_interface import HealthAdviceNodeInterface
from agent.graph.node_services.search_material.subgraph.state import SubgraphHealthAdviceState
from agent.graph.node_services.search_material.subgraph.node_register import register_node
from agent.graph.node_register import get_node_class
from agent.graph.node_services.search_material.symptom_memory import SymptomMemory

from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage

logger = logging.getLogger(__name__)

@register_node
class ImageAnalysisNode(HealthAdviceNodeInterface):
    """ Node that analyze educational images to a report.
    
    Attributes:
        name (str): The node's unique name.
        main_agent (SearchMaterialAgent): The main search material agent instance.
        llm (LLM): The language model used to generate the final response.
    """
    name = "image_analysis_node"

    def __init__(self, main_agent=None):
        """Initialize the ImageAnalysisNode."""
        if main_agent:
            self.main_agent = main_agent
        else:
            from agent.graph.node_register import get_node_instance
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
        """ Run the image analysis node.

        Args:
            state (SubgraphHealthAdviceState): The current subgraph execution state.
            
        Returns:
            Dict[str, Any]: A dictionary containing the AI message with the final response,
            and optionally an error message.
        """
        try:
            prompt_messages = await self._build_prompt(state)
            response: BaseMessage = await self.llm.ainvoke(prompt_messages)
            
            # Store in symptom memory with session_id
            inner_state = state.get("state", {})
            request = inner_state.get("request", {})
            session_id = request.get("session_id", "default")
            
            symptom_memory = SymptomMemory(session_id=session_id)
            symptom_memory.add_message("human", prompt_messages[0].content) # Lấy content của thằng system prompt
            symptom_memory.add_message("ai", response.content)
            symptom_memory.save_to_file()

            return {"node_responses": [response]}

        except Exception as e:
            logger.error(f"[ImageAnalysisNode] Error during image analysis: {e}", exc_info=True)
            return {"node_name": self.name, "error": str(e)}

    async def _build_prompt(self, state: SubgraphHealthAdviceState) -> List[BaseMessage]:
        """ Build the prompt messages for the LLM.

        Args:
            state (SubgraphHealthAdviceState): The current subgraph execution state.

        Returns:
            List[BaseMessage]: A formatted prompt for the LLM.
        """
        try:
            # Build system prompt using local template with PromptFormatter
            # Template path: agent/graph/prompts/ImageAnalysisNode/ImageAnalysisNode-system-prompt.txt
            system_prompt_content = self.build_prompt(
                prompt_type="system"
            )
            
            logger.info(f"[{self.name}] Built system prompt ({len(system_prompt_content)} chars)")
            messages = [SystemMessage(content=system_prompt_content)]
            
        except Exception as e:
            logger.error(f"[{self.name}] Error building system prompt from local template: {e}", exc_info=True)
            # Fallback to simple prompt if template fails
            system_prompt_content = "You are an educational image analysis assistant. Analyze the provided image and provide a detailed explanation relevant to learning."
            messages = [SystemMessage(content=system_prompt_content)]

        # Build the user message content (multimodal)
        inner_state = state.get("state", {})
        request = inner_state.get("request", {})
        payload = request.get("payload", {})
        
        # For image analysis, we expect payload.content to be a list of content items
        # or we check payload.metadata for image URLs
        user_content = payload.get("content", "")
        human_message_content = self._get_image_user_input(user_content)

        # Add the human message with multimodal content
        if human_message_content:
            messages.append(HumanMessage(content=human_message_content))
        else:
            logger.warning(f"[{self.name}] No image content found in user input")
            
        return messages
    
    def _get_image_user_input(
        self, user_input: Union[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Process the user input to extract image URLs.

        Args:
            user_input (Union[str, List[Dict[str, Any]]]): The raw user input.

        Returns:
            List[Dict[str, Any]],  # multimodal content for HumanMessage
        """
        human_message_content: List[Dict[str, Any]] = []

        if isinstance(user_input, list):
            for item in user_input:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "image_url":
                    image_url_data = item.get("image_url", {})
                    human_message_content.append(
                        {"type": "image_url", "image_url": {"url": image_url_data.get("url", "")}}
                    )
        else:
            raise ValueError("user_input must be a list of content items.")

        return human_message_content