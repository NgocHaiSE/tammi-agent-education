"""
Centralized Environment Configuration Manager

This module provides a centralized way to manage environment variables with:
- Type validation and conversion
- Default value management
- Configuration schema validation
- Integration with YAML configuration files
- Proper precedence handling (OS > .env > secret.yaml > config.yaml defaults)

The environment variables are loaded from multiple sources:
1. OS environment variables (highest priority)
2. .env file (for local development)
3. env-config.secret.yaml (secret values, not committed)
4. env-config.yaml (public schema and defaults, committed)

Usage:
    from agent.config.env_manager import get_env
    
    redis_host = get_env('REDIS_HOST', str, 'localhost')
    redis_port = get_env('REDIS_PORT', int, 6379)
    enable_metrics = get_env('ENABLE_METRICS', bool, False)
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, List
from dataclasses import dataclass
from agent.utils.logging import get_logger
import logging as log_level

# Load .env file for local development
try:
    from dotenv import load_dotenv
    _project_root = Path(__file__).parent.parent.parent
    _env_file = _project_root / ".env"
    if _env_file.exists():
        load_dotenv(_env_file, override=False)
        # Note: Using override=False to respect OS environment variables
except ImportError:
    # dotenv not installed, skip
    pass

T = TypeVar('T')

logger = get_logger(__name__)


@dataclass
class VariableConfig:
    """Configuration for a single environment variable."""
    name: str
    type: str
    required: bool
    default: Any
    description: str
    sensitive: bool = False
    validation: Optional[Dict[str, Any]] = None


class EnvConfigError(Exception):
    """Exception raised for environment configuration errors."""
    pass


class EnvManager:
    """Centralized environment configuration manager."""
    
    def __init__(self, config_path: Optional[Path] = None, auto_load: bool = True):
        """Initialize the environment manager."""
        self.project_root = Path(__file__).parent.parent.parent
        self.config_path = config_path or (self.project_root / "env-config.yaml")
        self.config: Dict[str, Any] = {}
        self.variables: Dict[str, VariableConfig] = {}
        
        self._load_config_schema()
        
        if auto_load:
            self.load_environment()
    
    def _load_config_schema(self) -> None:
        """Load and parse the env-config.yaml schema."""
        try:
            if not self.config_path.exists():
                logger.warning(f"Config file not found: {self.config_path}")
                return
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            self.variables = {}
            variables = self.config.get('variables', {})
            
            for var_name, var_config in variables.items():
                self.variables[var_name] = VariableConfig(
                    name=var_name,
                    type=var_config.get('type', 'string'),
                    required=var_config.get('required', False),
                    default=var_config.get('default'),
                    description=var_config.get('description', ''),
                    sensitive=var_config.get('sensitive', var_config.get('secret', False)),
                    validation=var_config.get('validation')
                )
                    
            logger.info(f"Loaded {len(self.variables)} environment variables from config")
            
        except Exception as e:
            logger.error(f"Failed to load config schema: {e}")
            raise EnvConfigError(f"Failed to load config schema: {e}")
    
    def load_environment(self) -> None:
        """Load environment variables from YAML configuration files."""
        try:
            secret_config_path = self.project_root / "env-config.secret.yaml"
            secret_values = {}
            
            if secret_config_path.exists():
                with open(secret_config_path, 'r', encoding='utf-8') as f:
                    secret_data = yaml.safe_load(f) or {}
                    # Support both flat structure and nested structure
                    if isinstance(secret_data, dict):
                        # Check if it has secrets/values sections
                        if 'secrets' in secret_data or 'values' in secret_data:
                            secret_values = {**secret_data.get('secrets', {}), **secret_data.get('values', {})}
                        else:
                            # Flat structure - use directly
                            secret_values = secret_data
                logger.info(f"Loaded {len(secret_values)} values from {secret_config_path}")
            
            # Apply values with precedence: OS > secret.yaml > config.yaml defaults
            for key, var_config in self.variables.items():
                if os.environ.get(key) is not None:
                    continue
                
                if key in secret_values:
                    os.environ[key] = str(secret_values[key])
                    continue
                
                if var_config.default is not None:
                    # Don't set empty string values for URL/endpoint variables to avoid
                    # SDK auto-detection issues (e.g., OpenAI SDK reads OPENAI_BASE_URL from env)
                    default_str = str(var_config.default)
                    if default_str or not any(x in key for x in ['URL', 'ENDPOINT', 'BASE']):
                        os.environ[key] = default_str
            
            logger.info("Environment variables loaded (OS > secret.yaml > config.yaml)")
            
        except Exception as e:
            logger.error(f"Failed to load environment variables: {e}")
            raise EnvConfigError(f"Failed to load environment variables: {e}")
    
    def get(self, key: str, expected_type: Type[T] = str, default: Optional[T] = None) -> T:
        """Get an environment variable with type conversion."""
        raw_value = os.environ.get(key)
        
        if raw_value is None:
            if default is not None:
                return self._convert_type(default, expected_type, key)
            raise EnvConfigError(f"Environment variable '{key}' is required but not set.")
        
        try:
            converted_value = self._convert_type(raw_value, expected_type, key)
            
            var_config = self.variables.get(key)
            if var_config and var_config.validation:
                self._validate_value(converted_value, var_config.validation, key)
            
            return converted_value
            
        except (ValueError, TypeError) as e:
            raise EnvConfigError(f"Failed to convert '{key}' to {expected_type.__name__}: {e}")
    
    def _convert_type(self, value: Any, expected_type: Type[T], key: str) -> T:
        """Convert a value to the expected type."""
        if expected_type == str:
            return str(value)
        elif expected_type == int:
            return int(value)
        elif expected_type == float:
            return float(value)
        elif expected_type == bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
            return bool(value)
        elif expected_type == list:
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                return [item.strip() for item in value.split(',') if item.strip()]
            return [value]
        else:
            return expected_type(value)
    
    def _validate_value(self, value: Any, validation: Dict[str, Any], key: str) -> None:
        """Validate a value against validation rules."""
        if 'min' in validation and isinstance(value, (int, float)):
            if value < validation['min']:
                raise ValueError(f"Value {value} is below minimum {validation['min']}")
        
        if 'max' in validation and isinstance(value, (int, float)):
            if value > validation['max']:
                raise ValueError(f"Value {value} is above maximum {validation['max']}")
        
        if 'enum' in validation:
            if value not in validation['enum']:
                raise ValueError(f"Value '{value}' not in allowed values: {validation['enum']}")


_env_manager: Optional[EnvManager] = None


def get_env_manager() -> EnvManager:
    """Get the global environment manager instance."""
    global _env_manager
    if _env_manager is None:
        _env_manager = EnvManager()
    return _env_manager


def get_env(key: str, expected_type: Type[T] = str, default: Optional[T] = None) -> T:
    """
    Convenience function to get an environment variable.
    
    Args:
        key: Environment variable name
        expected_type: Expected Python type
        default: Default value if not found
        
    Returns:
        The environment variable value converted to the expected type
    """
    return get_env_manager().get(key, expected_type, default)


# Convenience functions for common types - NO DEFAULT VALUES
def get_str(key: str) -> str:
    """Get a string environment variable. Raises EnvConfigError if not found."""
    return get_env(key, str, None)


def get_int(key: str) -> int:
    """Get an integer environment variable. Raises EnvConfigError if not found."""
    return get_env(key, int, None)


def get_bool(key: str) -> bool:
    """Get a boolean environment variable. Raises EnvConfigError if not found."""
    return get_env(key, bool, None)


def get_float(key: str) -> float:
    """Get a float environment variable. Raises EnvConfigError if not found."""
    return get_env(key, float, None)


def get_list(key: str) -> List[str]:
    """Get a list environment variable (comma-separated). Raises EnvConfigError if not found."""
    return get_env(key, list, None)
