"""
Simple test - invoke LLM
"""
import asyncio
from dotenv import load_dotenv

load_dotenv('../.env')

async def test():
    from agent.llm_service.llm_config_service import create_agent_llm_client
    
    try:
        llm = create_agent_llm_client(version="v1")
        print("Client created")
        
        response = await llm.ainvoke("Say hello in Vietnamese")
        print(f"SUCCESS! Response: {response.content}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
