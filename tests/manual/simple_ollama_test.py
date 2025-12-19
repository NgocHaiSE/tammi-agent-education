"""
Simple test to verify agent works with Ollama
"""
import httpx
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("="*80)
print("SIMPLE AGENT TEST WITH OLLAMA")
print("="*80)

# Test 1: Health check
print("\n1️⃣  Agent Health Check...")
try:
    resp = httpx.get("http://localhost:8001/management/health", timeout=5)
    if resp.status_code == 200:
        print(f"   ✅ Agent is running: {resp.json()}")
    else:
        print(f"   ❌ Health check failed: {resp.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Cannot connect to agent: {e}")
    sys.exit(1)

# Test 2: Simple request
print("\n2️⃣  Testing Simple Request...")
req = {
    "session_id": "test-ollama-1",
    "flow_id": "flow-1",
    "request_id": "req-1",
    "user_context": {"user_id": "u1", "family_id": "f1", "name": "Test"},
    "client_context": {
        "box_id": "b1", "type_box": "phone", "device_model": "X",
        "os_type": "Android", "os_version": "12", "app_version": "1.0",
        "location": {"latitude": 21.0, "longitude": 105.0},
        "timestamp": "2025-10-22T00:00:00Z"
    },
    "payload": {
        "type": "text",
        "content": "Xin chào, bạn là ai?",
        "intent": "medical",
        "sub_intent": "greeting",
        "metadata": {}
    },
    "history": [],
    "stream": False
}

print(f"   Sending: {req['payload']['content']}")

try:
    resp = httpx.post("http://localhost:8001/api/v1/chat", json=req, timeout=60)
    
    if resp.status_code == 200:
        data = resp.json()
        msg = data.get('data', {}).get('payload', {}).get('display_message', '')
        
        print(f"\n   ✅ Status: {resp.status_code}")
        print(f"   📝 Response:")
        print(f"   {msg}")
        
        if "lỗi" in msg.lower() or "error" in msg.lower():
            print(f"\n   ⚠️  Warning: Response contains error message")
            print(f"   Check the agent window for detailed logs")
        else:
            print(f"\n   ✅ SUCCESS! Agent is working with Ollama!")
    else:
        print(f"   ❌ HTTP {resp.status_code}")
        print(f"   Response: {resp.text[:500]}")
        
except httpx.TimeoutException:
    print(f"   ⏱️  Request timed out (this is normal for Ollama on first run)")
    print(f"   Ollama may be downloading the model. Try again in a moment.")
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
