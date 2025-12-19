#!/usr/bin/env python3
"""
Test both streaming and non-streaming modes
"""
import requests
import json

url = "http://localhost:8001/api/v1/chat"

payload_base = {
    "session_id": "session-1234",
    "request_id": "req-4561",
    "flow_id": "flow-7891",
    "agent": "medical",
    "payload": {
        "type": "text",
        "content": "xin chào",
        "intent": "greeting",
        "sub_intent": "hello",
        "metadata": {}
    },
    "user_context": {
        "user_id": "user-001",
        "family_id": "fam-001",
        "name": "Nguyễn Văn A"
    },
    "client_context": {
        "box_id": "box-123",
        "type_box": "tammi-v2",
        "device_model": "iPhone 14",
        "os_type": "iOS",
        "os_version": "17.0",
        "app_version": "2.1.0",
        "timestamp": "2025-10-21T10:30:00Z",
        "location": {
            "latitude": 21.0285,
            "longitude": 105.8542
        }
    },
    "history": []
}

print("=" * 80)
print("🧪 TEST 1: NON-STREAMING MODE (stream=false)")
print("=" * 80)

payload_non_stream = {**payload_base, "stream": False}

try:
    response = requests.post(
        url,
        json=payload_non_stream,
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    
    print(f"📊 Status Code: {response.status_code}")
    print(f"📋 Content-Type: {response.headers.get('content-type')}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n✅ RESPONSE STRUCTURE:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # Verify all required fields
        print("\n🔍 FIELD VALIDATION:")
        required_fields = ["status", "flow_id", "session_id", "request_id", "user_context", "data"]
        for field in required_fields:
            present = field in data
            print(f"  {'✅' if present else '❌'} {field}: {present}")
        
        if "data" in data:
            data_fields = ["payload", "metadata"]
            for field in data_fields:
                present = field in data["data"]
                print(f"  {'✅' if present else '❌'} data.{field}: {present}")
        
        if "data" in data and "payload" in data["data"]:
            payload_fields = ["intent", "sub_intent", "display_message", "tts_message", "ui_elements", "suggestions"]
            for field in payload_fields:
                present = field in data["data"]["payload"]
                print(f"  {'✅' if present else '❌'} data.payload.{field}: {present}")
    else:
        print(f"❌ Error: {response.text}")

except Exception as e:
    print(f"❌ Exception: {e}")

print("\n" + "=" * 80)
print("🧪 TEST 2: STREAMING MODE (stream=true)")
print("=" * 80)

payload_stream = {**payload_base, "stream": True}

try:
    response = requests.post(
        url,
        json=payload_stream,
        headers={"Content-Type": "application/json"},
        stream=True,
        timeout=30
    )
    
    print(f"📊 Status Code: {response.status_code}")
    print(f"📋 Content-Type: {response.headers.get('content-type')}")
    
    if response.status_code == 200:
        print("\n📨 SSE STREAM:")
        
        chunk_count = 0
        last_response = None
        
        for line in response.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                data_str = line[6:]
                
                if data_str == "[DONE]":
                    print(f"\n✅ [DONE] signal received")
                    break
                
                try:
                    data = json.loads(data_str)
                    
                    if "complete" in data:
                        print(f"\n✅ Completion: {data}")
                    
                    elif "error" in data:
                        print(f"\n❌ Error: {data}")
                    
                    elif "data" in data and "payload" in data["data"]:
                        # This is a full response chunk!
                        chunk_count += 1
                        last_response = data
                        display_message = data["data"]["payload"]["display_message"]
                        is_partial = data.get("is_partial", False)
                        
                        print(f"\n📦 Chunk #{chunk_count} (partial={is_partial}):")
                        print(f"  display_message: {repr(display_message)}")
                
                except json.JSONDecodeError:
                    print(f"⚠️ Invalid JSON: {data_str}")
        
        print(f"\n📊 Total chunks: {chunk_count}")
        
        if last_response:
            print("\n� FINAL STREAMING RESPONSE STRUCTURE:")
            print(json.dumps(last_response, indent=2, ensure_ascii=False))
            
            print("\n🔍 STRUCTURE VALIDATION:")
            required_fields = ["status", "flow_id", "session_id", "request_id", "user_context", "data"]
            for field in required_fields:
                present = field in last_response
                print(f"  {'✅' if present else '❌'} {field}: {present}")
            
            print("\n💡 COMPARISON: Streaming vs Non-Streaming structure")
            print("  Both should have IDENTICAL structure ✅")
            print("  Only difference: display_message builds incrementally")
    else:
        print(f"❌ Error: {response.text}")

except Exception as e:
    print(f"❌ Exception: {e}")

print("\n" + "=" * 80)
