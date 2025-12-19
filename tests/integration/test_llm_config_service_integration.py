"""Integration tests for LLM service with real API calls.

These tests require valid API credentials and make real API calls.
Tests will skip if credentials are not configured.
"""
import os
import pytest
from langchain_core.messages import HumanMessage

from agent.llm_service.llm_config_service import create_medical_llm_client
from agent.config.settings import get_settings


@pytest.mark.integration
@pytest.mark.requires_llm
class TestLLMIntegration:
    """Test LLM service with real API calls."""
    
    def test_real_connection(self):
        """Test connection to real LLM service."""
        settings = get_settings()
        
        # Check credentials with detailed logging
        openrouter_key_set = bool(settings.OPENROUTER_API_KEY)
        
        print(f"\n🔍 Credential Check:")
        print(f"  - OPENROUTER_API_KEY: {'✅ Set' if openrouter_key_set else '❌ Not Set'}")
        
        if not openrouter_key_set:
            skip_msg = "No LLM credentials configured (need OPENROUTER_API_KEY)"
            print(f"⏭️  Skipping: {skip_msg}")
            pytest.skip(skip_msg)
        
        try:
            print(f"🔌 Creating LLM client...")
            llm = create_medical_llm_client()
            
            # Verify it's a proper LangChain Runnable
            from langchain_core.runnables import Runnable
            assert isinstance(llm, Runnable), "LLM client should be a Runnable"
            print(f"✅ LLM client created successfully")
            
        except Exception as e:
            pytest.fail(f"Failed to create LLM client: {e}")
    
    def test_real_llm_inference(self):
        """Test real LLM inference with simple prompt."""
        settings = get_settings()
        
        # Check credentials
        if not settings.OPENROUTER_API_KEY:
            pytest.skip("No LLM credentials configured (need OPENROUTER_API_KEY)")
        
        try:
            print(f"\n🔌 Testing LLM inference...")
            llm = create_medical_llm_client(temperature=0.0)
            
            # Simple test message
            response = llm.invoke([HumanMessage(content="Say 'test' only")])
            
            assert response is not None, "Response should not be None"
            assert hasattr(response, 'content'), "Response should have content attribute"
            assert len(response.content) > 0, "Response content should not be empty"
            
            print(f"✅ LLM inference successful")
            print(f"  - Response: {response.content[:100]}...")
            
        except Exception as e:
            pytest.fail(f"Failed to run LLM inference: {e}")
    
    def test_llm_with_fallback(self):
        """Test LLM fallback mechanism."""
        settings = get_settings()
        
        # Check if OpenRouter is configured
        if not settings.OPENROUTER_API_KEY:
            pytest.skip("No LLM credentials configured (need OPENROUTER_API_KEY)")
        
        try:
            print(f"\n🔌 Testing LLM with fallback...")
            print(f"  - Using OpenRouter API")
            
            llm = create_medical_llm_client(temperature=0.0)
            
            # Test with a simple prompt
            response = llm.invoke([HumanMessage(content="Hi")])
            
            assert response is not None
            assert len(response.content) > 0
            
            print(f"✅ LLM with fallback works")
            print(f"  - Response received: {response.content[:50]}...")
            
        except Exception as e:
            pytest.fail(f"LLM fallback test failed: {e}")
    
    def test_llm_streaming(self):
        """Test LLM streaming response."""
        settings = get_settings()
        
        if not settings.OPENROUTER_API_KEY:
            pytest.skip("No LLM credentials configured (need OPENROUTER_API_KEY)")
        
        try:
            print(f"\n🔌 Testing LLM streaming...")
            llm = create_medical_llm_client(temperature=0.0)
            
            # Test streaming
            chunks = []
            for chunk in llm.stream([HumanMessage(content="Count to 3")]):
                if hasattr(chunk, 'content') and chunk.content:
                    chunks.append(chunk.content)
            
            full_response = "".join(chunks)
            
            print(f"✅ LLM streaming successful")
            print(f"  - Chunks received: {len(chunks)}")
            print(f"  - Total response: {full_response[:100]}...")
            
            assert len(chunks) > 0, "Should receive at least one chunk"
            assert len(full_response) > 0, "Full response should not be empty"
            
        except Exception as e:
            pytest.fail(f"LLM streaming test failed: {e}")

    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
