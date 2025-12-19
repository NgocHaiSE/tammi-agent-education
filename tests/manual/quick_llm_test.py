"""Quick test of LLM service"""
import sys
sys.path.insert(0, '/')

try:
    print("1. Testing LLM client creation...")
    from agent.llm_service import create_medical_llm_client
    
    llm = create_medical_llm_client()
    print(f"✅ LLM client created: {type(llm)}")
    
    print("\n2. Testing simple invoke...")
    from langchain_core.messages import HumanMessage
    
    response = llm.invoke([HumanMessage(content="Say 'test' only")])
    print(f"✅ Response received: {response.content[:100]}")
    
    print("\n🎉 LLM service working!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
