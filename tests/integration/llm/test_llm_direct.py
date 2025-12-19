"""
Test LLM service với Ollama
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.llm_service import create_medical_llm_client

print("="*80)
print("Testing LLM Service with Ollama")
print("="*80)

try:
    print("\n1️⃣  Creating LLM client...")
    llm = create_medical_llm_client(version="v1")
    print(f"   ✅ LLM client created: {type(llm)}")
    print(f"   Model: {llm}")
    
    print("\n2️⃣  Testing simple invoke...")
    from langchain_core.messages import HumanMessage
    
    response = llm.invoke([HumanMessage(content="Xin chào! Bạn là ai?")])
    print(f"   ✅ Response received")
    print(f"   Type: {type(response)}")
    print(f"   Content: {response.content[:200]}...")
    
    print("\n✅ SUCCESS! Ollama is working correctly")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    
print("\n" + "="*80)
