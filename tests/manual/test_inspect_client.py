"""
Inspect the actual OpenAI client configuration
"""
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.DEBUG)

print("Loading .env...")
load_dotenv('../.env')

from agent.llm_service.llm_config_service import create_agent_llm_client

print("\n" + "=" * 80)
print("Creating LLM client and inspecting its configuration")
print("=" * 80)

llm = create_agent_llm_client(version="v1")

print(f"\nLLM type: {type(llm)}")
print(f"LLM class: {llm.__class__.__name__}")

# Fallback wrapper - need to get the actual runnable
if hasattr(llm, 'runnable'):
    actual_llm = llm.runnable
    print(f"\nActual LLM (from fallback wrapper): {type(actual_llm)}")
    print(f"Actual LLM class: {actual_llm.__class__.__name__}")
else:
    actual_llm = llm

# Check if it has fallbacks
if hasattr(llm, 'fallbacks'):
    print(f"\nFallbacks: {len(llm.fallbacks)} fallback(s)")
    for i, fb in enumerate(llm.fallbacks):
        print(f"  Fallback {i+1}: {type(fb).__name__}")

# Get the first actual ChatOpenAI instance
from langchain_openai import ChatOpenAI

def find_chat_openai(obj, depth=0, max_depth=5):
    """Recursively find ChatOpenAI instance"""
    if depth > max_depth:
        return None
    
    if isinstance(obj, ChatOpenAI):
        return obj
    
    # Check runnable attribute
    if hasattr(obj, 'runnable'):
        result = find_chat_openai(obj.runnable, depth+1, max_depth)
        if result:
            return result
    
    # Check fallbacks
    if hasattr(obj, 'fallbacks'):
        for fb in obj.fallbacks:
            result = find_chat_openai(fb, depth+1, max_depth)
            if result:
                return result
    
    return None

chat_openai = find_chat_openai(llm)

if chat_openai:
    print(f"\n" + "=" * 80)
    print("Found ChatOpenAI instance - inspecting configuration")
    print("=" * 80)
    
    print(f"\nChatOpenAI attributes:")
    print(f"  model_name: {chat_openai.model_name}")
    print(f"  openai_api_key: {repr(str(chat_openai.openai_api_key)[:30])}...")
    print(f"  openai_api_base: {repr(chat_openai.openai_api_base)}")
    print(f"  openai_organization: {repr(chat_openai.openai_organization)}")
    print(f"  openai_proxy: {repr(chat_openai.openai_proxy)}")
    
    # Check the actual OpenAI client
    if hasattr(chat_openai, 'client'):
        print(f"\n  OpenAI client: {type(chat_openai.client)}")
        
        # Try to get base_url from the client
        if hasattr(chat_openai.client, 'base_url'):
            base_url = chat_openai.client.base_url
            print(f"  client.base_url: {repr(base_url)}")
            print(f"  client.base_url type: {type(base_url)}")
            print(f"  client.base_url str: {repr(str(base_url))}")
    
    # Check async client too
    if hasattr(chat_openai, 'async_client'):
        print(f"\n  Async OpenAI client: {type(chat_openai.async_client)}")
        
        if hasattr(chat_openai.async_client, 'base_url'):
            base_url = chat_openai.async_client.base_url
            print(f"  async_client.base_url: {repr(base_url)}")
            print(f"  async_client.base_url type: {type(base_url)}")
            print(f"  async_client.base_url str: {repr(str(base_url))}")
            
            # This is likely the issue!
            if str(base_url) == '' or not str(base_url).startswith(('http://', 'https://')):
                print(f"\n  ⚠️ WARNING: Invalid base_url detected!")
                print(f"  This will cause httpcore.UnsupportedProtocol during invocation!")
else:
    print(f"\nCould not find ChatOpenAI instance in the wrapper")

print("\n" + "=" * 80)
print("Inspection complete")
print("=" * 80)
