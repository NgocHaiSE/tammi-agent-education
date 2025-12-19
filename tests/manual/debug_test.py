"""
Test with detailed error logging
"""
import sys
import os
import httpx
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("="*80)
print("DETAILED TEST WITH ERROR LOGGING")
print("="*80)

# Simple test
req = {
    "session_id": "debug-s1",
    "flow_id": "debug-f1",
    "request_id": "debug-r1",
    "user_context": {"user_id": "u1", "family_id": "f1", "name": "Debug"},
    "client_context": {
        "box_id": "b1", "type_box": "phone", "device_model": "X",
        "os_type": "Android", "os_version": "12", "app_version": "1.0",
        "location": {"latitude": 21.0, "longitude": 105.0},
        "timestamp": "2025-10-22T00:00:00Z"
    },
    "payload": {
        "type": "text",
        "content": "Xin chào, bạn có khỏe không?",
        "intent": "medical",
        "sub_intent": "greeting",
        "metadata": {}
    },
    "history": [],
    "stream": False
}

print("\n📤 Sending request to agent...")
print(f"   Content: {req['payload']['content']}")
print(f"   URL: http://localhost:8001/api/v1/chat")

try:
    response = httpx.post("http://localhost:8001/api/v1/chat", json=req, timeout=30)
    print(f"\n📥 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n📋 Full Response:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        msg = data.get('data', {}).get('payload', {}).get('display_message', '')
        print(f"\n💬 Display Message:")
        print(f"   {msg}")
        
        if "lỗi" in msg.lower():
            print(f"\n⚠️  Error detected in response!")
            print(f"   Check the agent terminal window for detailed error logs")
    else:
        print(f"❌ HTTP Error: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"\n❌ Exception: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("TIP: Check the agent's PowerShell window for detailed error logs")
print("="*80)
