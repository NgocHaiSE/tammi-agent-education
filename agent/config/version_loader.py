"""
Version Configuration Loader for medical Agent.

Ported from old_code with adapted imports for agent/ structure.
Manages loading and parsing of version-specific configurations with inheritance support.
"""
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Any, Optional
import copy

import yaml
from agent.utils.logging import get_logger

logger = get_logger(__name__)


def deep_merge(base_dict: Dict, override_dict: Dict) -> Dict:
    """
    Deep merge two dictionaries, with override_dict values taking precedence.
    
    Args:
        base_dict: Base dictionary
        override_dict: Override dictionary
        
    Returns:
        Merged dictionary
    """
    result = copy.deepcopy(base_dict)
    
    for key, value in override_dict.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    
    return result


class VersionConfig:
    """Configuration class for version-specific settings with inheritance support."""
    
    def __init__(self, config_data: Dict[str, Any]):
        self.config_data = config_data
        self.version = config_data.get("version", "unknown")
        self.description = config_data.get("description", "")
        
    def get_llm_config(self, component: str = None, component_type: str = None) -> Dict[str, Any]:
        """
        Get LLM configuration for a specific component (agent or service).
        
        Applies DRY logic: if 'model' or 'backup_models' is omitted, use
        'default_model' and 'default_backup_models' from the root llm config.
        Always returns model/backup_models as dict(s), not strings.
        
        Args:
            component: Component name (e.g., 'medical_agent')
            component_type: Component type ('agent' or 'service')
            
        Returns:
            LLM configuration dictionary with model/backup_models as dict(s)
        """
        llm_config = self.config_data.get("llm", {})
        default_model = llm_config.get("default_model", {"name": "gpt-4o-mini", "provider": "azure"})
        default_backup_models = llm_config.get("default_backup_models", [
            {"name": "gpt-4o", "provider": "azure"},
            {"name": "gpt-4o-mini", "provider": "azure"}
        ])
        default_temperature = llm_config.get("default_temperature", 0.7)
        default_max_tokens = llm_config.get("default_max_tokens", 1000)
        
        def ensure_model_dict(val):
            if isinstance(val, dict):
                return val
            if isinstance(val, str):
                # Assume default provider if not specified
                return {"name": val, "provider": llm_config.get("default_provider", "azure")}
            return default_model
            
        def ensure_backup_models(val):
            if isinstance(val, list):
                return [ensure_model_dict(v) for v in val]
            if isinstance(val, dict):
                return [val]
            if isinstance(val, str):
                return [{"name": val, "provider": llm_config.get("default_provider", "azure")}]
            return default_backup_models
            
        # 1. Find the config for the component (agent/service)
        config = None
        if not component:
            config = llm_config
        elif component_type == "agent":
            agents_config = llm_config.get("agents", {})
            if component in agents_config:
                base_agent = agents_config.get("base_agent", {})
                specific_config = agents_config.get(component, {})
                config = deep_merge(base_agent, specific_config)
            elif "base_agent" in agents_config:
                config = agents_config["base_agent"]
        elif component_type == "service":
            services_config = llm_config.get("services", {})
            if component in services_config:
                base_service = services_config.get("base_service", {})
                specific_config = services_config.get(component, {})
                config = deep_merge(base_service, specific_config)
            elif "base_service" in services_config:
                config = services_config["base_service"]
                
        if config is None and component:
            # Fallback to general component lookup
            config = llm_config.get(component, {})
        if config is None:
            config = {}
            
        # 2. Apply DRY logic for model/backup_models
        model = config.get("model")
        if model is None:
            model = default_model
        else:
            model = ensure_model_dict(model)
            
        backup_models = config.get("backup_models")
        if backup_models is None:
            backup_models = default_backup_models
        else:
            backup_models = ensure_backup_models(backup_models)
            
        # 3. Compose final config
        result = dict(config)
        result["model"] = model
        result["backup_models"] = backup_models
        if "temperature" not in result:
            result["temperature"] = default_temperature
        if "max_tokens" not in result:
            result["max_tokens"] = default_max_tokens
        return result
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Get configuration for a specific agent."""
        agent_configs = self.config_data.get("agent_configs", {})
        return agent_configs.get(agent_name, {})
    
    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """Get configuration for a specific service."""
        # First check in services section for general service config
        services_config = self.config_data.get("services", {}).get("services", {})
        service_general_config = services_config.get(service_name, {})
        
        # Then check for LLM-specific config
        service_llm_config = self.get_llm_config(service_name, "service")
        
        # Merge both configs
        return deep_merge(service_general_config, {"llm": service_llm_config})
    
    @property
    def agent_tools(self) -> Dict[str, List[str]]:
        """Get agent-specific tool configurations for this version."""
        # Check both old format and new format
        old_format = self.config_data.get("agent_tools", {})
        new_format = {}
        
        agent_configs = self.config_data.get("agent_configs", {})
        for agent_name, config in agent_configs.items():
            if "tools" in config:
                new_format[agent_name] = config["tools"]
        
        return deep_merge(new_format, old_format)
    
    @property
    def agents(self) -> List[str]:
        """Get list of enabled agents for this version."""
        # Get from main agents list
        main_agents = self.config_data.get("agents", [])
        
        # Also check agent_configs for enabled agents
        agent_configs = self.config_data.get("agent_configs", {})
        enabled_agents = [
            name for name, config in agent_configs.items() 
            if config.get("enabled", True)
        ]
        
        # Combine and deduplicate
        all_agents = list(set(main_agents + enabled_agents))
        return all_agents
    
    @property
    def limits(self) -> Dict[str, Any]:
        """Get resource limits for this version."""
        return self.config_data.get("limits", {})
    
    @property
    def features(self) -> Dict[str, bool]:
        """Get feature flags for this version."""
        return self.config_data.get("features", {})
    
    @property
    def services(self) -> Dict[str, Any]:
        """Get service configurations for this version."""
        return self.config_data.get("services", {})
    
    def is_agent_enabled(self, agent_name: str) -> bool:
        """Check if a specific agent is enabled in this version."""
        return agent_name in self.agents
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a specific feature is enabled in this version."""
        return self.features.get(feature_name, False)
    
    def get_agent_tools(self, agent_name: str) -> Optional[List[str]]:
        """
        Get the list of allowed tools for a specific agent in this version.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            List of tool names if configured, None if agent should use all tools
        """
        return self.agent_tools.get(agent_name)
    
    def get_limit(self, limit_name: str, default: Any = None) -> Any:
        """Get a specific resource limit."""
        return self.limits.get(limit_name, default)
    
    def get_intent_classify_config(self) -> Dict[str, Any]:
        """Get LLM configuration for intent classification."""
        return self.services.get("intent_classify", {})


class VersionConfigLoader:
    """Loader for version-specific configurations with inheritance support."""
    
    def __init__(self, config_dir: Optional[str] = None, defaults_dir: Optional[str] = None):
        if config_dir is None:
            # Default to agent/config/versions
            agent_dir = Path(__file__).parent
            config_dir = agent_dir / "versions"
        
        if defaults_dir is None:
            # Default to agent/config/defaults
            agent_dir = Path(__file__).parent
            defaults_dir = agent_dir / "defaults"
        
        self.config_dir = Path(config_dir)
        self.defaults_dir = Path(defaults_dir)
        self._configs: Dict[str, VersionConfig] = {}
        self._default_config: Optional[Dict[str, Any]] = None
        self._load_default_config()
        self._load_all_configs()
    
    def _load_sub_config(self, config_path: Path) -> Dict[str, Any]:
        """Load a sub-configuration file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load sub-config from {config_path}: {e}")
            return {}
    
    def _load_default_config(self):
        """Load the default configuration with all sub-configs."""
        default_file = self.defaults_dir / "default.yaml"
        
        if not default_file.exists():
            logger.warning(f"Default config file not found: {default_file}")
            self._default_config = {}
            return
        
        try:
            with open(default_file, 'r', encoding='utf-8') as f:
                default_config = yaml.safe_load(f) or {}
            
            # Load and merge sub-configurations
            imports = default_config.get("imports", [])
            for import_file in imports:
                import_path = self.defaults_dir / import_file
                if import_path.exists():
                    sub_config = self._load_sub_config(import_path)
                    default_config = deep_merge(default_config, sub_config)
                    logger.debug(f"Merged sub-config: {import_file}")
                else:
                    logger.warning(f"Imported config file not found: {import_path}")
            
            self._default_config = default_config
            logger.info(f"Loaded default configuration from {default_file}")
            
        except Exception as e:
            logger.error(f"Failed to load default config: {e}")
            self._default_config = {}
    
    def _load_all_configs(self):
        """Load all available version configurations."""
        if not self.config_dir.exists():
            logger.warning(f"Version config directory not found: {self.config_dir}")
            return
        
        for config_file in self.config_dir.glob("*.yaml"):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                
                # Merge with default config
                if self._default_config:
                    config_data = deep_merge(self._default_config, config_data)
                
                version_name = config_data.get("version", config_file.stem)
                self._configs[version_name] = VersionConfig(config_data)
                
                logger.info(f"Loaded version config: {version_name} from {config_file}")
                
            except Exception as e:
                logger.error(f"Failed to load config from {config_file}: {e}")

    @lru_cache(maxsize=10)
    def get_config(self, version: str) -> VersionConfig:
        """Get configuration for a specific version."""
        if version not in self._configs:
            logger.warning(f"Version config not found: {version}, falling back to v1")
            version = "v1"
        
        if version not in self._configs:
            logger.error(f"Fallback version v1 not found, using default config")
            return self._get_default_config()
        
        return self._configs[version]
    
    def _get_default_config(self) -> VersionConfig:
        """Get a default configuration when no version configs are available."""
        if self._default_config:
            return VersionConfig(self._default_config)
            
        # Fallback to hardcoded default for medical agent
        default_config = {
            "version": "default",
            "description": "Hardcoded fallback configuration for medical agent",
            "llm": {
                "default_model": {"name": "gpt-4o-mini", "provider": "azure"},
                "default_backup_models": [
                    {"name": "gpt-4o", "provider": "azure"}
                ],
                "default_temperature": 0.7,
                "default_max_tokens": 512,
                "services": {
                    "medical_agent": {
                        "temperature": 0.7,
                        "max_tokens": 512
                    }
                }
            },
            "limits": {
                "max_conversation_length": 50,
                "max_tools_per_request": 5,
                "timeout_seconds": 30
            },
            "features": {
                "streaming": True,
                "tool_calling": True
            }
        }
        return VersionConfig(default_config)
    
    def get_available_versions(self) -> List[str]:
        """Get list of all available versions."""
        return list(self._configs.keys())
    
    def reload_configs(self):
        """Reload all configuration files."""
        self._configs.clear()
        self._load_all_configs()


@lru_cache(maxsize=1)
def get_version_loader() -> VersionConfigLoader:
    """Get cached version config loader instance."""
    return VersionConfigLoader()


@lru_cache(maxsize=8)
def load_version_config(version: str) -> VersionConfig:
    """
    Load configuration for a specific version.
    
    Args:
        version: Version name (e.g., "v1", "dev", "demo")
        
    Returns:
        VersionConfig instance for the specified version
    """
    loader = get_version_loader()
    return loader.get_config(version)


@lru_cache(maxsize=1)
def get_available_versions() -> List[str]:
    """
    Get list of all available versions.
    
    Returns:
        List of version names
    """
    loader = get_version_loader()
    return loader.get_available_versions()
