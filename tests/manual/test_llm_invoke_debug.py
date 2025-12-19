"""
Test actual LLM invocation - simulating a real API call
"""
import asyncio
from dotenv import load_dotenv

print("Loading .env...")
load_dotenv('../.env')

async def test_llm_invoke():
    print("\n" + "=" * 80)
    print("Test: Invoke LLM with a simple message")
    print("=" * 80)
    
    from agent.llm_service.llm_config_service import create_agent_llm_client
    
    try:
        print("\n1. Creating LLM client...")
        llm = create_agent_llm_client(version="v1")
        print(f"✓ Client created: {type(llm)}")
        
        print("\n2. Invoking LLM with test message...")
        response = await llm.ainvoke("Say 'Hello, World!' in Vietnamese")
        print(f"✓ Response received: {response.content[:100]}...")
        
    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {e}")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()
        
        # Check if it's the httpcore error
        if "httpcore" in str(type(e)) or "UnsupportedProtocol" in str(e):
            print("\n🎯 THIS IS THE ERROR WE'RE LOOKING FOR!")
            print("It happens during INVOCATION, not during client initialization!")

if __name__ == "__main__":
    asyncio.run(test_llm_invoke())
