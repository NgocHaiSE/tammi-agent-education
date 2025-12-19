"""
Prompt formatting utilities with template variable substitution.

Provides:
- Template rendering with {{variable}} syntax
- Safe variable substitution with fallbacks
- Type-aware formatting (string, number, list, dict)
"""

import logging
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PromptFormatter:
    """Format prompts with {{variable}} placeholder substitution."""
    
    # Regex to find {{variable}} patterns
    VARIABLE_PATTERN = re.compile(r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}')
    
    @staticmethod
    def find_variables(template: str) -> list:
        """
        Find all {{variable}} placeholders in template.
        
        Args:
            template: Template string with {{variable}} patterns
        
        Returns:
            List of variable names found
        """
        matches = PromptFormatter.VARIABLE_PATTERN.findall(template)
        return list(set(matches))  # Return unique variables
    
    @staticmethod
    def format_value(value: Any) -> str:
        """
        Format a value for template insertion.
        
        Args:
            value: Value to format (str, int, float, list, dict, etc.)
        
        Returns:
            Formatted string representation
        """
        if value is None:
            return ""
        elif isinstance(value, bool):
            return "yes" if value else "no"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            # Format list with line breaks
            return "\n".join(f"- {PromptFormatter.format_value(item)}" for item in value)
        elif isinstance(value, dict):
            # Format dict with key: value pairs
            return "\n".join(f"{k}: {PromptFormatter.format_value(v)}" for k, v in value.items())
        else:
            return str(value)
    
    @staticmethod
    def render(
        template: str,
        variables: Dict[str, Any],
        strict: bool = False,
    ) -> str:
        """
        Render template with variable substitution.
        
        Args:
            template: Template string with {{variable}} placeholders
            variables: Dict of variable names to values
            strict: If True, raise error on missing variables; if False, leave {{var}} as-is
        
        Returns:
            Rendered template string
        
        Raises:
            ValueError: If strict=True and required variable is missing
        """
        # Find all variables in template
        required_vars = PromptFormatter.find_variables(template)
        
        # Check for missing variables
        missing_vars = [v for v in required_vars if v not in variables]
        if missing_vars:
            if strict:
                raise ValueError(f"Missing required variables: {missing_vars}")
            else:
                logger.warning(f"Missing variables in prompt template: {missing_vars}")
        
        # Replace variables
        def replacer(match):
            var_name = match.group(1)
            if var_name in variables:
                value = variables[var_name]
                formatted = PromptFormatter.format_value(value)
                return formatted
            else:
                # Leave placeholder as-is if not found (and strict=False)
                return match.group(0)
        
        result = PromptFormatter.VARIABLE_PATTERN.sub(replacer, template)
        return result
    
    @staticmethod
    def validate_template(template: str) -> Dict[str, Any]:
        """
        Validate and analyze a template.
        
        Args:
            template: Template string to validate
        
        Returns:
            Dict with analysis:
            - variables: List of required variables
            - count: Number of placeholders
            - valid: Whether template is valid
        """
        variables = PromptFormatter.find_variables(template)
        
        # Count total placeholders (may have duplicates)
        all_matches = PromptFormatter.VARIABLE_PATTERN.findall(template)
        
        return {
            "variables": variables,
            "count": len(all_matches),
            "unique_count": len(variables),
            "valid": len(variables) > 0 or "{{" not in template,  # Valid if has vars or no incomplete braces
        }


class PromptBuilder:
    """Build prompts with structured context and variables."""
    
    def __init__(self, base_prompt: str):
        """
        Initialize prompt builder with base template.
        
        Args:
            base_prompt: Template string with {{variable}} placeholders
        """
        self.base_prompt = base_prompt
        self.variables: Dict[str, Any] = {}
        self.context_sections: Dict[str, str] = {}
    
    def set_variable(self, name: str, value: Any) -> "PromptBuilder":
        """
        Set a single variable.
        
        Args:
            name: Variable name (will be used as {{name}})
            value: Variable value
        
        Returns:
            Self for method chaining
        """
        self.variables[name] = value
        return self
    
    def set_variables(self, **kwargs) -> "PromptBuilder":
        """
        Set multiple variables.
        
        Args:
            **kwargs: Variable name=value pairs
        
        Returns:
            Self for method chaining
        """
        self.variables.update(kwargs)
        return self
    
    def add_context_section(self, section_name: str, content: str) -> "PromptBuilder":
        """
        Add a context section to be included in prompt.
        
        Args:
            section_name: Name of section (e.g., "weather", "history")
            content: Section content
        
        Returns:
            Self for method chaining
        """
        self.context_sections[section_name] = content
        return self
    
    def build(self, strict: bool = False) -> str:
        """
        Build final prompt with all variables substituted.
        
        Args:
            strict: If True, raise on missing variables
        
        Returns:
            Final rendered prompt
        """
        # Render base prompt with variables
        rendered = PromptFormatter.render(
            self.base_prompt,
            self.variables,
            strict=strict
        )
        
        # Append context sections if any
        if self.context_sections:
            rendered += "\n\n" + "\n".join(
                f"### {name}\n{content}"
                for name, content in self.context_sections.items()
            )
        
        return rendered
    
    def validate(self) -> Dict[str, Any]:
        """
        Validate this prompt builder.
        
        Returns:
            Analysis of template and variables
        """
        analysis = PromptFormatter.validate_template(self.base_prompt)
        analysis["provided_variables"] = list(self.variables.keys())
        analysis["missing_variables"] = [
            v for v in analysis["variables"] if v not in self.variables
        ]
        analysis["context_sections"] = list(self.context_sections.keys())
        
        return analysis


# Helper functions
def format_prompt(template: str, **kwargs) -> str:
    """
    Quick format helper for simple templates.
    
    Args:
        template: Template string with {{variable}} placeholders
        **kwargs: Variable name=value pairs
    
    Returns:
        Rendered string
    """
    return PromptFormatter.render(template, kwargs, strict=False)


def build_prompt(base_template: str) -> PromptBuilder:
    """
    Quick builder helper.
    
    Args:
        base_template: Template string
    
    Returns:
        PromptBuilder instance
    """
    return PromptBuilder(base_template)
