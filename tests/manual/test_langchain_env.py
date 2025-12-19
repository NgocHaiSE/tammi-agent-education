"""
Test to see if LangChain ChatOpenAI reads OPENAI_BASE_URL from environment
"""
from dotenv import load_dotenv
import os

# Load .env
load_dotenv('../.env')

print(f"OPENAI_API_KEY: {repr(os.getenv('OPENAI_API_KEY')[:20])}...")  
print(f"OPENAI_BASE_URL: {repr(os.getenv('OPENAI_BASE_URL'))}")

# Try to init ChatOpenAI WITHOUT passing base_url
try:
    from langchain_openai import ChatOpenAI
    
    print("\n=== Test 1: Init ChatOpenAI without base_url parameter ===")
    client = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=os.getenv('OPENAI_API_KEY')
    )
    print(f"Client created successfully!")
    print(f"Client base_url: {getattr(client, 'openai_api_base', 'N/A')}")
    print(f"Client client attributes: {dir(client)}")
    
    # Try to check the actual httpx client config
    if hasattr(client, 'client'):
        print(f"\nClient.client type: {type(client.client)}")
        if hasattr(client.client, '_base_url'):
            print(f"Client.client._base_url: {client.client._base_url}")
            
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
