#!/usr/bin/env python3
"""
Test for Import Path Fixes and Backward Compatibility.

This test verifies:
1. All imports use correct paths (agent.* instead of new_backend.Sub_Agents.medical_Agent.*)
2. No imports from deleted llm_clients module
3. Entrypoint servers import correctly
4. Backward compatibility with settings
"""

import os
import sys
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))


class TestImportPaths:
    """Test suite for import path correctness"""

    def test_no_old_backend_imports(self):
        """Verify no files use old new_backend.Sub_Agents.medical_Agent imports"""
        # Search for any files with old imports
        import subprocess
        
        # Use grep to search for old import pattern
        try:
            result = subprocess.run(
                ['grep', '-r', 'new_backend.Sub_Agents.medical_Agent', 'agent/', '--include=*.py'],
                capture_output=True,
                text=True,
                cwd=project_root
            )
            
            # Should find nothing (exit code 1 means no matches)
            if result.returncode == 0:
                pytest.fail(f"Found old import paths:\n{result.stdout}")
            
            print("✅ No old new_backend imports found")
        except FileNotFoundError:
            # grep not available (Windows), manually check key files
            self._manual_check_imports()

    def _manual_check_imports(self):
        """Manual check for old imports (fallback for Windows)"""
        files_to_check = [
            "agent/entrypoint/http_server.py",
            "agent/entrypoint/grpc_server.py",
            "agent/api/v1/chatrs/grpc_handler.py",
            "agent/services/agent_generator.py",
        ]
        
        for file_path in files_to_check:
            full_path = project_root / file_path
            if not full_path.exists():
                continue
                
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if 'new_backend.Sub_Agents.medical_Agent' in content:
                pytest.fail(f"Found old import path in {file_path}")
        
        print("✅ No old imports found (manual check)")

    def test_no_llm_clients_imports(self):
        """Verify no files import from deleted llm_clients module"""
        try:
            import subprocess
            result = subprocess.run(
                ['grep', '-r', 'from agent.llm_clients', 'agent/', '--include=*.py'],
                capture_output=True,
                text=True,
                cwd=project_root
            )
            
            if result.returncode == 0:
                pytest.fail(f"Found imports from deleted llm_clients:\n{result.stdout}")
            
            print("✅ No imports from deleted llm_clients module")
        except FileNotFoundError:
            self._manual_check_llm_clients_imports()

    def _manual_check_llm_clients_imports(self):
        """Manual check for llm_clients imports"""
        files_to_check = [
            "agent/services/emotional_support.py",
            "agent/services/weekend_idea.py",
            "agent/services/agent_generator.py",
        ]
        
        for file_path in files_to_check:
            full_path = project_root / file_path
            if not full_path.exists():
                continue
                
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if 'from agent.llm_clients' in content or 'import agent.llm_clients' in content:
                pytest.fail(f"Found llm_clients import in {file_path}")
        
        print("✅ No llm_clients imports found (manual check)")

    def test_entrypoint_imports_correctly(self):
        """Test that entrypoint files import correctly"""
        # Mock protobuf modules BEFORE any imports
        from unittest.mock import MagicMock, patch
        import sys
        
        # Create comprehensive mocks for all google.protobuf modules
        mock_modules = {
            'google': MagicMock(),
            'google.protobuf': MagicMock(),
            'google.protobuf.json_format': MagicMock(),
            'google.protobuf.descriptor': MagicMock(),
            'google.protobuf.descriptor_pool': MagicMock(),
            'google.protobuf.runtime_version': MagicMock(),
            'google.protobuf.symbol_database': MagicMock(),
            'google.protobuf.internal': MagicMock(),
            'google.protobuf.internal.builder': MagicMock(),
        }
        
        with patch.dict('sys.modules', mock_modules):
            # Mock protobuf-generated files
            mock_agents_pb2 = MagicMock()
            mock_agents_pb2_grpc = MagicMock()
            
            # Add necessary attributes that code expects
            mock_agents_pb2.medicalRequest = MagicMock()
            mock_agents_pb2.medicalResponse = MagicMock()
            mock_agents_pb2_grpc.medicalServiceServicer = MagicMock()
            
            with patch.dict('sys.modules', {
                'agent.proto.agents_pb2': mock_agents_pb2,
                'agent.proto.agents_pb2_grpc': mock_agents_pb2_grpc,
            }):
                # Clear any cached imports of entrypoint modules
                for module in list(sys.modules.keys()):
                    if module.startswith('agent.entrypoint'):
                        del sys.modules[module]
                
                try:
                    from agent.entrypoint import http_server
                    from agent.entrypoint import grpc_server
                    
                    assert hasattr(http_server, 'app')
                    assert hasattr(grpc_server, 'serve')
                    
                    print("✅ Entrypoint files import correctly")
                except ImportError as e:
                    pytest.fail(f"Failed to import entrypoint files: {e}")

    def test_graph_builder_imports(self):
        """Test that graph builder imports correctly"""
        try:
            from agent.graph.builder import build_medical_graph
            from agent.graph.state import AgentState
            from agent.graph.tools import create_api_tools
            
            assert callable(build_medical_graph)
            assert AgentState is not None
            assert callable(create_api_tools)
            
            print("✅ Graph builder imports correctly")
        except ImportError as e:
            pytest.fail(f"Failed to import graph builder: {e}")

    def test_llm_service_imports(self):
        """Test that LLM service imports correctly"""
        try:
            from agent.llm_service import create_medical_llm_client
            from agent.llm_service.llm_config_service import LLMConfigService
            from agent.llm_service.llm_service import LLMService
            
            assert callable(create_medical_llm_client)
            assert LLMConfigService is not None
            assert LLMService is not None
            
            print("✅ LLM service imports correctly")
        except ImportError as e:
            pytest.fail(f"Failed to import LLM service: {e}")

    def test_config_imports(self):
        """Test that config modules import correctly"""
        try:
            from agent.config.settings import get_settings, Settings
            from agent.config.version_loader import load_version_config
            
            assert callable(get_settings)
            assert Settings is not None
            assert callable(load_version_config)
            
            print("✅ Config modules import correctly")
        except ImportError as e:
            pytest.fail(f"Failed to import config modules: {e}")


class TestBackwardCompatibility:
    """Test backward compatibility after refactor"""

    def test_settings_backward_compatibility(self):
        """Test that settings attributes are accessible"""
        from agent.config.settings import get_settings
        
        settings = get_settings()
        
        # Check current attributes exist
        assert hasattr(settings, 'LLM_PROVIDER')
        assert hasattr(settings, 'llm_model')
        assert hasattr(settings, 'OPENAI_API_KEY')
        
        # New attributes should exist
        assert hasattr(settings, 'LLM_CONFIG_PATH')
        assert hasattr(settings, 'VERSION_CONFIG_DIR')
        assert hasattr(settings, 'DEFAULT_VERSION')
        
        print("✅ Settings attributes accessible")

    def test_settings_get_settings_function(self):
        """Test that get_settings() function works (used by grpc_server)"""
        from agent.config.settings import get_settings
        
        settings = get_settings()
        
        # Verify it returns Settings instance
        from agent.config.settings import Settings
        assert isinstance(settings, Settings)
        
        # Verify it's cached (same instance on second call)
        settings2 = get_settings()
        assert settings is settings2
        
        print("✅ get_settings() function works correctly")

    def test_llm_service_public_api(self):
        """Test that LLM service public API is accessible"""
        try:
            # These should all be importable from agent.llm_service
            from agent.llm_service import (
                create_medical_llm_client,
                create_service_llm_client,
                get_llm_config_service,
            )
            
            assert callable(create_medical_llm_client)
            assert callable(create_service_llm_client)
            assert callable(get_llm_config_service)
            
            print("✅ LLM service public API accessible")
        except ImportError as e:
            pytest.fail(f"Failed to import LLM service public API: {e}")


class TestConfigurationFiles:
    """Test that configuration files exist and are valid"""

    def test_llm_config_json_exists(self):
        """Test that llm_config.json exists and is valid"""
        config_path = project_root / "agent" / "config" / "llm_config.json"
        
        assert config_path.exists(), f"llm_config.json not found at {config_path}"
        
        # Verify it's valid JSON
        import json
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Verify structure
        assert "azure" in config or "openai" in config
        
        print("✅ llm_config.json exists and is valid")

    def test_version_config_exists(self):
        """Test that v1.yaml exists and is valid"""
        version_path = project_root / "agent" / "config" / "versions" / "v1.yaml"
        
        assert version_path.exists(), f"v1.yaml not found at {version_path}"
        
        # Verify it's valid YAML
        import yaml
        with open(version_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Verify structure
        assert "version" in config
        assert config["version"] == "v1"
        
        print("✅ v1.yaml exists and is valid")

    def test_default_config_exists(self):
        """Test that default.yaml exists and is valid"""
        default_path = project_root / "agent" / "config" / "defaults" / "default.yaml"
        
        assert default_path.exists(), f"default.yaml not found at {default_path}"
        
        # Verify it's valid YAML
        import yaml
        with open(default_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Verify structure
        assert "llm" in config or "version" in config
        
        print("✅ default.yaml exists and is valid")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
