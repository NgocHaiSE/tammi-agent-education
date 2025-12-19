"""
Deep inspect OpenAI client's httpx configuration
"""
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.DEBUG)

print("Loading .env...")
load_dotenv('../.env')

from agent.llm_service.llm_config_service import create_agent_llm_client
from langchain_openai import ChatOpenAI

llm = create_agent_llm_client(version="v1")

# Get the actual ChatOpenAI instance
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

if not chat_openai:
    print("Could not find ChatOpenAI!")
    exit(1)

print("\n" + "=" * 80)
print("Inspecting OpenAI SDK client configuration")
print("=" * 80)

# Get the root async client from ChatOpenAI
if hasattr(chat_openai, 'root_async_client'):
    root_client = chat_openai.root_async_client
    print(f"\nroot_async_client: {type(root_client)}")
    print(f"  base_url: {repr(root_client.base_url)}")
    print(f"  base_url str: '{str(root_client.base_url)}'")
    print(f"  base_url type: {type(root_client.base_url)}")
    
    # This is the smoking gun!
    base_url_str = str(root_client.base_url)
    if not base_url_str or not base_url_str.startswith(('http://', 'https://')):
        print(f"\n  🔥 FOUND THE BUG!")
        print(f"  base_url is: '{base_url_str}'")
        print(f"  This will cause httpcore.UnsupportedProtocol!")
    else:
        print(f"\n  ✓ base_url looks valid")

# Also check http_client and http_async_client passed during init
if hasattr(chat_openai, 'http_client'):
    print(f"\nhttp_client: {chat_openai.http_client}")
    if chat_openai.http_client:
        print(f"  Type: {type(chat_openai.http_client)}")
        if hasattr(chat_openai.http_client, 'base_url'):
            print(f"  base_url: {chat_openai.http_client.base_url}")

if hasattr(chat_openai, 'http_async_client'):
    print(f"\nhttp_async_client: {chat_openai.http_async_client}")
    if chat_openai.http_async_client:
        print(f"  Type: {type(chat_openai.http_async_client)}")
        if hasattr(chat_openai.http_async_client, 'base_url'):
            print(f"  base_url: {chat_openai.http_async_client.base_url}")

print("\n" + "=" * 80)
