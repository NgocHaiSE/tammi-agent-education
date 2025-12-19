"""
Test with fresh client (no cache)
"""
import asyncio
from dotenv import load_dotenv

print("Loading .env...")
load_dotenv('../.env')

# Clear cache first
from agent.llm_service.llm_config_service import _llm_config_service, get_llm_service
_llm_config_service = None  # Reset global instance
get_llm_service.cache_clear()  # Clear lru_cache

print("Cache cleared!")

async def test_llm_invoke():
    print("\n" + "=" * 80)
    print("Test: Invoke LLM with a simple message (FRESH CLIENT)")
    print("=" * 80)
    
    from agent.llm_service.llm_config_service import create_agent_llm_client
    
    try:
        print("\n1. Creating FRESH LLM client...")
        llm = create_agent_llm_client(version="v1")
        print(f"✓ Client created: {type(llm)}")
        
        # Inspect it first
        from langchain_openai import ChatOpenAI
        def find_chat_openai(obj, depth=0):
            if depth > 5:
                return None
            if isinstance(obj, ChatOpenAI):
                return obj
            if hasattr(obj, 'runnable'):
                return find_chat_openai(obj.runnable, depth+1)
            if hasattr(obj, 'fallbacks') and obj.fallbacks:
                return find_chat_openai(obj.fallbacks[0], depth+1)
            return None
        
        chat_openai = find_chat_openai(llm)
        if chat_openai and hasattr(chat_openai, 'root_async_client'):
            root_client = chat_openai.root_async_client
            print(f"\n  Inspecting root_async_client.base_url: '{str(root_client.base_url)}'")
            
            if not str(root_client.base_url) or not str(root_client.base_url).startswith(('http://', 'https://')):
                print(f"  ⚠️ STILL INVALID! base_url is: '{str(root_client.base_url)}'")
                return
            else:
                print(f"  ✓ base_url looks valid!")
        
        print("\n2. Invoking LLM with test message...")
        response = await llm.ainvoke("Say 'Hello, World!' in Vietnamese")
        print(f"✓✓✓ SUCCESS! Response received: {response.content[:100]}...")
        
    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {e}")
        if "httpcore" in str(type(e)) or "UnsupportedProtocol" in str(e):
            print("\n❌ Still getting httpcore error after fix!")

if __name__ == "__main__":
    asyncio.run(test_llm_invoke())
