"""
Test script to reproduce the exact LLM initialization flow and debug step by step.
This mimics the real flow: load .env → create LLM service → get client
"""

import os
import sys
from dotenv import load_dotenv

print("=" * 80)
print("STEP 1: Load .env file")
print("=" * 80)
load_dotenv('../.env', override=False)

# Check environment variables
print(f"\nEnvironment variables after loading .env:")
print(f"  OPENAI_API_KEY: {repr(os.getenv('OPENAI_API_KEY', 'NOT_SET')[:30])}...")
print(f"  OPENAI_BASE_URL: {repr(os.getenv('OPENAI_BASE_URL', 'NOT_SET'))}")
print(f"  OPENAI_ORG_ID: {repr(os.getenv('OPENAI_ORG_ID', 'NOT_SET'))}")
print(f"  LLM_PROVIDER: {repr(os.getenv('LLM_PROVIDER', 'NOT_SET'))}")
print(f"  LLM_MODEL: {repr(os.getenv('LLM_MODEL', 'NOT_SET'))}")

print("\n" + "=" * 80)
print("STEP 2: Import agent modules")
print("=" * 80)
try:
    from agent.config.settings import get_settings
    from agent.llm_service.llm_config_service import get_llm_service, create_agent_llm_client
    print("✓ Imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("STEP 3: Get settings")
print("=" * 80)
try:
    settings = get_settings()
    print(f"✓ Settings loaded")
    print(f"  AGENT_SERVICE_NAME: {settings.AGENT_SERVICE_NAME}")
    print(f"  LLM_CONFIG_PATH: {settings.LLM_CONFIG_PATH}")
    print(f"  OPENAI_API_KEY (from settings): {repr(settings.OPENAI_API_KEY[:30])}...")
    print(f"  OPENAI_BASE_URL (from settings): {repr(settings.OPENAI_BASE_URL)}")
except Exception as e:
    print(f"✗ Settings failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("STEP 4: Get LLM service (loads llm_config.json)")
print("=" * 80)
try:
    llm_service = get_llm_service(version="v1")
    print(f"✓ LLM service created")
    print(f"  Config path: {llm_service.config_path}")
    print(f"  Providers: {list(llm_service.config.keys())}")
except Exception as e:
    print(f"✗ LLM service failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("STEP 5: Analyze OpenAI provider config from llm_config.json")
print("=" * 80)
try:
    openai_config = llm_service.config.get('openai', {})
    print(f"OpenAI provider config:")
    print(f"  Type: {openai_config.get('type')}")
    print(f"  Deployments: {len(openai_config.get('deployments', []))}")
    
    for deployment in openai_config.get('deployments', []):
        print(f"\n  Deployment: {deployment.get('name')}")
        print(f"    Model: {deployment.get('model')}")
        print(f"    api_key_env: {deployment.get('api_key_env')}")
        print(f"    base_url_env: {deployment.get('base_url_env')}")
        
        # Check actual env values
        api_key_env = deployment.get('api_key_env')
        base_url_env = deployment.get('base_url_env')
        
        if api_key_env:
            api_key_val = os.getenv(api_key_env)
            print(f"    → {api_key_env} = {repr(api_key_val[:30] if api_key_val else None)}...")
        
        if base_url_env:
            base_url_val = os.getenv(base_url_env)
            print(f"    → {base_url_env} = {repr(base_url_val)}")
            print(f"    → bool({base_url_env}) = {bool(base_url_val)}")
except Exception as e:
    print(f"✗ Config analysis failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("STEP 6: Simulate get_client call for 'openai:gpt-4o-mini'")
print("=" * 80)
try:
    # This mimics what llm_config_service does
    provider_model = "openai:gpt-4o-mini"
    print(f"Calling llm_service.get_client2('{provider_model}')")
    
    # Add detailed logging
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('agent.llm_service.llm_service')
    logger.setLevel(logging.DEBUG)
    
    # Manually trace through the logic
    resolved_provider = "openai"
    resolved_model = "gpt-4o-mini"
    
    provider_config = llm_service.config[resolved_provider]
    deployments = provider_config.get("deployments", [])
    
    print(f"\n  Provider: {resolved_provider}")
    print(f"  Model: {resolved_model}")
    print(f"  Deployments count: {len(deployments)}")
    
    # Find deployment
    matched_by_name = [d for d in deployments if d.get("name") == resolved_model]
    print(f"  Matched by name: {len(matched_by_name)}")
    
    if matched_by_name:
        deployment = matched_by_name[0]
        print(f"\n  Selected deployment:")
        print(f"    name: {deployment.get('name')}")
        print(f"    model: {deployment.get('model')}")
        
        # Extract API key
        api_key = deployment.get("api_key") or os.getenv(deployment.get("api_key_env", ""))
        print(f"    api_key (first 30 chars): {repr(api_key[:30])}...")
        
        # Extract endpoint - THIS IS THE CRITICAL PART
        print(f"\n  Extracting endpoint (chain of or operations):")
        
        step1 = deployment.get("endpoint")
        print(f"    1. deployment.get('endpoint'): {repr(step1)}")
        
        step2 = os.getenv(deployment.get("endpoint_env", ""))
        print(f"    2. os.getenv(deployment.get('endpoint_env', '')): {repr(step2)}")
        
        step3_key = deployment.get("base_url_env", "")
        step3 = os.getenv(step3_key)
        print(f"    3. os.getenv(deployment.get('base_url_env', '')): os.getenv('{step3_key}') = {repr(step3)}")
        
        step4 = provider_config.get("endpoint")
        print(f"    4. provider_config.get('endpoint'): {repr(step4)}")
        
        step5 = os.getenv(provider_config.get("endpoint_env", ""))
        print(f"    5. os.getenv(provider_config.get('endpoint_env', '')): {repr(step5)}")
        
        step6_key = provider_config.get("base_url_env", "")
        step6 = os.getenv(step6_key)
        print(f"    6. os.getenv(provider_config.get('base_url_env', '')): os.getenv('{step6_key}') = {repr(step6)}")
        
        # Now the actual or chain
        endpoint = (step1 or step2 or step3 or step4 or step5 or step6)
        print(f"\n    Final endpoint from or chain: {repr(endpoint)}")
        print(f"    bool(endpoint): {bool(endpoint)}")
        
        # Check if this would be passed to ChatOpenAI
        provider_type = provider_config.get("type", "openai").lower()
        print(f"\n  Provider type: {provider_type}")
        
        if provider_type == "openai":
            print(f"\n  Would create ChatOpenAI:")
            print(f"    if endpoint: {bool(endpoint)}")
            if endpoint:
                print(f"    → YES, would pass base_url='{endpoint}' to ChatOpenAI")
                print(f"    → This will cause error if endpoint is empty string!")
            else:
                print(f"    → NO, would NOT pass base_url parameter")

except Exception as e:
    print(f"✗ Client creation simulation failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("STEP 7: Actually try to create the client")
print("=" * 80)
try:
    print("Attempting to create LLM client via create_agent_llm_client()...")
    client = create_agent_llm_client(version="v1")
    print(f"✓ Client created successfully!")
    print(f"  Client type: {type(client)}")
    print(f"  Client model: {client.model_name if hasattr(client, 'model_name') else 'N/A'}")
except Exception as e:
    print(f"✗ Client creation FAILED: {type(e).__name__}: {e}")
    print(f"\n  Full traceback:")
    import traceback
    traceback.print_exc()
    
    print(f"\n  This is the error we're looking for!")

print("\n" + "=" * 80)
print("DEBUG COMPLETE")
print("=" * 80)
