#!/usr/bin/env python3
"""
Test LLMConfigService for medical Agent.

This test verifies:
1. LLMConfigService initialization and configuration loading
2. Version-based configuration management
3. Multi-provider LLM client creation with fallbacks
4. Configuration caching and performance
5. Error handling for missing/invalid configurations
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from agent.llm_service.llm_config_service import (
    LLMConfigService,
    get_llm_config_service,
    create_service_llm_client,
    create_medical_llm_client,
    get_llm_service,
)
from agent.config.version_loader import load_version_config


@pytest.mark.unit
class TestLLMConfigService:
    """Test suite for LLMConfigService"""

    def test_llm_config_service_initialization(self):
        """Test that LLMConfigService initializes correctly with v1 config"""
        config_service = LLMConfigService(version="v1")
        
        assert config_service.version == "v1"
        assert config_service.version_config is not None
        print("✅ LLMConfigService initialized successfully")

    def test_get_service_llm_config(self):
        """Test retrieving service-specific LLM configuration"""
        config_service = LLMConfigService(version="v1")
        config = config_service.get_service_llm_config("medical_agent")
        
        # Verify config structure
        assert "model" in config
        assert "backup_models" in config
        assert "temperature" in config
        assert "max_tokens" in config
        
        # Verify model is a dict with provider and name
        assert isinstance(config["model"], dict)
        assert "name" in config["model"]
        assert "provider" in config["model"]
        
        # Verify backup models
        assert isinstance(config["backup_models"], list)
        for backup in config["backup_models"]:
            assert isinstance(backup, dict)
            assert "name" in backup
            assert "provider" in backup
        
        # Verify default values
        assert config["temperature"] == 0.7
        assert config["max_tokens"] == 512
        
        print(f"✅ Service config retrieved: model={config['model']}, backups={len(config['backup_models'])}")

    def test_create_llm_client_with_fallbacks(self):
        """Test creating LLM client with automatic fallback configuration"""
        # Skip if no API keys available
        if not os.getenv("AZURE_OPENAI_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            pytest.skip("No API keys available for testing")
        
        config_service = LLMConfigService(version="v1")
        
        # Mock the LLM service to avoid actual API calls
        with patch('agent.llm_service.llm_config_service.get_llm_service') as mock_get_service:
            mock_service = MagicMock()
            mock_client = MagicMock()
            mock_client.with_fallbacks = MagicMock(return_value=mock_client)
            mock_service.get_client2.return_value = mock_client
            mock_get_service.return_value = mock_service
            
            llm = config_service.create_llm_client("medical_agent")
            
            # Verify client was created
            assert llm is not None
            assert mock_service.get_client2.called
            
            # Verify fallbacks were configured
            assert mock_client.with_fallbacks.called
            
            print("✅ LLM client created with fallbacks")

    def test_create_llm_client_with_overrides(self):
        """Test creating LLM client with parameter overrides"""
        if not os.getenv("AZURE_OPENAI_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            pytest.skip("No API keys available for testing")
        
        config_service = LLMConfigService(version="v1")
        
        with patch('agent.llm_service.llm_config_service.get_llm_service') as mock_get_service:
            mock_service = MagicMock()
            mock_client = MagicMock()
            mock_client.with_fallbacks = MagicMock(return_value=mock_client)
            mock_service.get_client2.return_value = mock_client
            mock_get_service.return_value = mock_service
            
            # Override temperature and max_tokens
            llm = config_service.create_llm_client(
                "medical_agent",
                temperature=0.9,
                max_tokens=1024
            )
            
            # Verify client was created with overrides
            call_args = mock_service.get_client2.call_args
            assert call_args is not None
            assert call_args[1]["temperature"] == 0.9
            assert call_args[1]["max_tokens"] == 1024
            
            print("✅ LLM client created with parameter overrides")

    def test_get_model_hierarchy(self):
        """Test retrieving complete model hierarchy (main + backups)"""
        config_service = LLMConfigService(version="v1")
        hierarchy = config_service.get_model_hierarchy("medical_agent")
        
        # Verify hierarchy is a list of provider:model strings
        assert isinstance(hierarchy, list)
        assert len(hierarchy) > 0
        
        # Verify format: "provider:model"
        for model_str in hierarchy:
            assert ":" in model_str
            provider, model_name = model_str.split(":", 1)
            assert provider in ["azure", "openai", "ollama", "openrouter"]
            assert len(model_name) > 0
        
        print(f"✅ Model hierarchy: {hierarchy}")

    def test_update_version(self):
        """Test updating configuration version at runtime"""
        config_service = LLMConfigService(version="v1")
        assert config_service.version == "v1"
        
        # Update to same version (should work)
        config_service.update_version("v1")
        assert config_service.version == "v1"
        
        print("✅ Version update works correctly")

    def test_get_llm_config_service_singleton(self):
        """Test that get_llm_config_service returns same instance for same version"""
        service1 = get_llm_config_service(version="v1")
        service2 = get_llm_config_service(version="v1")
        
        # Should return same instance (singleton pattern)
        assert service1 is service2
        
        print("✅ Singleton pattern working correctly")

    def test_create_service_llm_client_convenience_function(self):
        """Test convenience function for creating service LLM client"""
        if not os.getenv("AZURE_OPENAI_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            pytest.skip("No API keys available for testing")
        
        with patch('agent.llm_service.llm_config_service.get_llm_service') as mock_get_service:
            mock_service = MagicMock()
            mock_client = MagicMock()
            mock_client.with_fallbacks = MagicMock(return_value=mock_client)
            mock_service.get_client2.return_value = mock_client
            mock_get_service.return_value = mock_service
            
            # Test with default service_name
            llm = create_service_llm_client(version="v1")
            assert llm is not None
            
            # Test with explicit service_name
            llm2 = create_service_llm_client(service_name="medical_agent", version="v1")
            assert llm2 is not None
            
            print("✅ create_service_llm_client works correctly")

    def test_create_medical_llm_client_convenience_function(self):
        """Test simplified convenience function specifically for medical agent"""
        if not os.getenv("AZURE_OPENAI_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            pytest.skip("No API keys available for testing")
        
        with patch('agent.llm_service.llm_config_service.get_llm_service') as mock_get_service:
            mock_service = MagicMock()
            mock_client = MagicMock()
            mock_client.with_fallbacks = MagicMock(return_value=mock_client)
            mock_service.get_client2.return_value = mock_client
            mock_get_service.return_value = mock_service
            
            # Test simple usage
            llm = create_medical_llm_client()
            assert llm is not None
            
            # Test with overrides
            llm2 = create_medical_llm_client(temperature=0.9)
            assert llm2 is not None
            
            print("✅ create_medical_llm_client works correctly")

    def test_error_handling_invalid_service(self):
        """Test error handling for invalid service name"""
        config_service = LLMConfigService(version="v1")
        
        # Should use default config for unknown service
        config = config_service.get_service_llm_config("nonexistent_service")
        
        # Should still return valid config (from defaults)
        assert "model" in config
        assert "backup_models" in config
        
        print("✅ Error handling works for invalid service")

    def test_get_llm_service_caching(self):
        """Test that get_llm_service uses LRU cache correctly"""
        service1 = get_llm_service(version="v1")
        service2 = get_llm_service(version="v1")
        
        # Should return same instance (cached)
        assert service1 is service2
        
        print("✅ Cached config returned for same version")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
