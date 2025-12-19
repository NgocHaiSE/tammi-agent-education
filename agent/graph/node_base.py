"""
Base class for graph nodes.

Provides common functionality for all nodes including:
- Prompt building from templates
- Tool registration
- Node execution with error handling
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from langchain_core.tools import BaseTool
from langchain_core.language_models import BaseChatModel

from agent.graph.graph_state import GraphState
from agent.graph.helpers import PromptFormatter

logger = logging.getLogger(__name__)


class NodeBase(ABC):
    """
    Base class for all graph nodes.
    
    Provides common functionality for node execution, prompt building,
    and tool management. All specific nodes should inherit from this class.
    """
    
    def __init__(
        self,
        name: str,
        llm: BaseChatModel,
        tools: Optional[List[BaseTool]] = None,
        prompt_template_dir: Optional[str] = None,
    ):
        """Initialize node base."""
        self.name = name
        self.llm = llm
        self.tools = tools or []
        
        # Set prompt template directory
        if prompt_template_dir is None:
            # Default to agent/graph/prompts
            current_dir = os.path.dirname(os.path.abspath(__file__))
            prompt_template_dir = os.path.join(current_dir, "prompts")
        
        self.prompt_template_dir = prompt_template_dir
        self._registered_tools: Dict[str, Callable] = {}
        
        logger.info(f"Initialized node '{self.name}' with {len(self.tools)} tools")
    
    def tool_register(self, func: Callable) -> Callable:
        """Decorator to register a function as a tool.
        
        The decorated function will be registered in the node's tool registry.
        This allows for dynamic tool management and discovery.
        
        Args:
            func: Function to register as a tool
            
        Returns:
            The same function (decorator pass-through)
            
        Example:
            >>> @node.tool_register
            ... def my_custom_tool():
            ...     return "tool result"
        """
        tool_name = func.__name__
        self._registered_tools[tool_name] = func
        logger.info(f"Registered tool '{tool_name}' in node '{self.name}'")
        return func
    
    def get_registered_tools(self) -> Dict[str, Callable]:
        """Get all registered tools for this node."""
        return self._registered_tools.copy()
    
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
    
    @abstractmethod
    async def run(self, state: GraphState) -> Dict[str, Any]:
        """
        Execute the node.
        
        This method should be implemented by subclasses to define
        the node's specific logic.
        
        Args:
            state: Current graph state
            
        Returns:
            Updated state dictionary with node's output
            
        Example:
            >>> async def run(self, state):
            ...     prompt = self.build_prompt(prompt_type="default")
            ...     response = await self.llm.ainvoke(prompt)
            ...     return {
            ...         "node_responses": {
            ...             **state["node_responses"],
            ...             self.name: response
            ...         }
            ...     }
        """
        pass
    
    def __repr__(self) -> str:
        """String representation of node."""
        return f"<{self.__class__.__name__} name={self.name} tools={len(self.tools)}>"
