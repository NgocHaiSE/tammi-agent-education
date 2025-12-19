"""Interface for nodes in the Search Material Assistant Subgraph.
"""
import os
import logging

from langchain_core.language_models.chat_models import BaseChatModel
from agent.graph.node_services.search_material.subgraph.state import SubgraphHealthAdviceState
from agent.graph.helpers.prompt_formatter import PromptFormatter
from typing import Any, Optional, Dict
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class HealthAdviceNodeInterface(ABC):
    """Interface class for Nodes in the Search Material Assistant Subgraph.
    Attributes:
        name (str): The name of the node.
        include_in_graph (bool): Determines whether the node is included in the subgraph.
    """
    name: str
    include_in_graph: bool = True

    def __init__(self, main_agent: Any, name: str, llm: Optional[BaseChatModel] = None, **kwargs):
        """Initialize with name, language model, and the agent it belongs to.
        Args:
            main_agent (Any): The main agent that this node belongs to.
            name (str): The name of the node.
            llm (Optional[BaseChatModel]): The language model used by the node.
            **kwargs: Additional parameters for initialization.
        """
        self.name = name
        self.llm = llm
        self.main_agent = main_agent
        self.prompt_template_dir = os.path.normpath("agent/graph/prompts") # Base directory for prompt templates
        
    @abstractmethod
    async def run(self, state: SubgraphHealthAdviceState, **kwargs):
        """Main execution method of the Node.
        Must be implemented by subclasses.
        Args:
            state (SubgraphHealthAdviceState): The current state of the subgraph.
            **kwargs: Additional parameters for the method.
        """
        pass
    
    def build_prompt(self, prompt_type: str = "default", **kwargs) -> str:
        """
        Build prompt from template using {{variable}} substitution.
        
        Loads prompt template from: prompts/{node_name}/{node_name}-{prompt_type}-prompt.txt
        Supports {{variable}} syntax for template variable substitution via PromptFormatter.
        
        Args:
            prompt_type: Type of prompt (e.g., 'default', 'classification', 'response')
            **kwargs: Template variables for substitution (e.g., user_input="text", location="Hà Nội")
            
        Returns:
            Rendered prompt string with variables substituted
            
        Raises:
            FileNotFoundError: If prompt template file not found
            
        Example:
            >>> prompt = node.build_prompt(
            ...     prompt_type="default",
            ...     user_input="Hello",
            ...     location="Hà Nội"
            ... )
        """
        # Build template file path
        node_dir = os.path.join(self.prompt_template_dir, self.name)
        template_filename = f"{self.name}-{prompt_type}-prompt.txt"
        template_path = os.path.join(node_dir, template_filename)
        
        # Check if template exists
        if not os.path.exists(template_path):
            logger.warning(
                f"Prompt template not found at {template_path}. "
                f"Using node name as default prompt."
            )
            return f"Process {self.name} request"
        
        # Read template
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read().strip()
        except Exception as e:
            logger.error(f"Error reading prompt template from {template_path}: {e}")
            return f"Process {self.name} request"
        
        # Substitute variables using PromptFormatter if provided
        if kwargs:
            try:
                prompt = PromptFormatter.render(template, kwargs, strict=False)
            except Exception as e:
                logger.warning(f"Error rendering template with PromptFormatter: {e}")
                prompt = template
        else:
            prompt = template
        
        logger.debug(f"Built prompt from {template_path}")
        return prompt
