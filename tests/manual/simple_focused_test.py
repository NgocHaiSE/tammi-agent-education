"""
Simple focused tests - one by one
"""
import httpx
import grpc
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.proto import agents_pb2, agents_pb2_grpc

print("="*80)
print("medical AGENT - FOCUSED TESTS")
print("="*80)

# Test 1: Agent HTTP Health
print("\n1️⃣  Testing Agent HTTP Health...")
try:
    resp = httpx.get("http://localhost:8001/management/health", timeout=5)
    print(f"   ✅ Status: {resp.status_code} - {resp.json()}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Agent HTTP Request (Non-Stream)
print("\n2️⃣  Testing Agent HTTP Non-Stream...")
try:
    req = {
        "session_id": "s1", "flow_id": "f1", "request_id": "r1",
        "user_context": {"user_id": "u1", "family_id": "f1", "name": "Test"},
        "client_context": {
            "box_id": "b1", "type_box": "phone", "device_model": "X",
            "os_type": "Android", "os_version": "12", "app_version": "1.0",
            "location": {"latitude": 21.0, "longitude": 105.0},
            "timestamp": "2025-10-22T00:00:00Z"
        },
        "payload": {"type": "text", "content": "Hello", "intent": "medical", "sub_intent": "greeting", "metadata": {}},
        "history": [], "stream": False
    }
    start = time.time()
    resp = httpx.post("http://localhost:8001/api/v1/chat", json=req, timeout=20)
    elapsed_ms = (time.time() - start) * 1000
    
    if resp.status_code == 200:
        data = resp.json()
        msg = data.get('data', {}).get('payload', {}).get('display_message', '')[:100]
        print(f"   ✅ Status: {resp.status_code}")
        print(f"   ⏱️  Time: {elapsed_ms:.0f}ms")
        print(f"   💬 Message: {msg}...")
    else:
        print(f"   ❌ Status: {resp.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Agent gRPC
print("\n3️⃣  Testing Agent gRPC...")
try:
    channel = grpc.insecure_channel('localhost:50052')
    grpc.channel_ready_future(channel).result(timeout=3)
    stub = agents_pb2_grpc.AgentServiceStub(channel)
    
    req_proto = agents_pb2.AgentRequest(
        session_id="s1", flow_id="f1", request_id="r1",
        user_context=agents_pb2.UserContext(user_id="u1", family_id="f1", name="Test"),
        client_context=agents_pb2.ClientContext(
            box_id="b1", type_box="phone", device_model="X",
            os_type="Android", os_version="12", app_version="1.0",
            location=agents_pb2.Location(latitude=21.0, longitude=105.0),
            timestamp="2025-10-22T00:00:00Z"
        ),
        payload=agents_pb2.Payload(type="text", content="Hello gRPC", intent="medical", sub_intent="greeting"),
        stream=False
    )
    
    start = time.time()
    # Use Chat RPC (unified method, always returns stream)
    # For non-stream mode, consume first response
    resp = None
    for r in stub.Chat(req_proto, timeout=20):
        resp = r
        break
    elapsed_ms = (time.time() - start) * 1000
    
    print(f"   ✅ Status: {resp.status.code} - {resp.status.message}")
    print(f"   ⏱️  Time: {elapsed_ms:.0f}ms")
    print(f"   💬 Message: {resp.data.payload.display_message[:100]}...")
    
    channel.close()
except grpc.RpcError as e:
    print(f"   ❌ gRPC Error: {e.code()} - {e.details()}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 4: Gateway HTTP Health
print("\n4️⃣  Testing Gateway HTTP Health...")
try:
    resp = httpx.get("http://localhost:8000/management/health", timeout=5)
    print(f"   ✅ Status: {resp.status_code} - {resp.text[:200]}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 5: Check Gateway OpenAPI
print("\n5️⃣  Checking Gateway OpenAPI docs...")
try:
    resp = httpx.get("http://localhost:8000/openapi.json", timeout=5)
    if resp.status_code == 200:
        api_spec = resp.json()
        print(f"   ✅ OpenAPI spec available")
        print(f"   📚 Title: {api_spec.get('info', {}).get('title', 'N/A')}")
        print(f"   📋 Endpoints:")
        
        paths = api_spec.get('paths', {})
        for path in list(paths.keys())[:10]:  # Show first 10
            methods = list(paths[path].keys())
            print(f"      - {path} [{', '.join(methods).upper()}]")
        
        if len(paths) > 10:
            print(f"      ... and {len(paths) - 10} more")
            
        # Check if there's a medical endpoint
        medical_paths = [p for p in paths.keys() if 'medical' in p.lower()]
        if medical_paths:
            print(f"   🎯 Found medical endpoints:")
            for p in medical_paths:
                print(f"      - {p}")
        else:
            print(f"   ⚠️  No medical-specific endpoints found in Gateway")
            
    else:
        print(f"   ❌ Status: {resp.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 6: Try Gateway → Agent
print("\n6️⃣  Testing Gateway → Agent communication...")
try:
    # Try to get available endpoints first
    resp_openapi = httpx.get("http://localhost:8000/openapi.json", timeout=5)
    if resp_openapi.status_code == 200:
        paths = resp_openapi.json().get('paths', {})
        medical_endpoints = [p for p in paths.keys() if 'medical' in p.lower() or 'agent' in p.lower()]
        
        if medical_endpoints:
            test_endpoint = medical_endpoints[0]
            print(f"   🎯 Found endpoint: {test_endpoint}")
            
            req = {
                "session_id": "gw-s1", "flow_id": "gw-f1", "request_id": "gw-r1",
                "user_context": {"user_id": "u1", "family_id": "f1", "name": "Gateway Test"},
                "client_context": {
                    "box_id": "b1", "type_box": "phone", "device_model": "X",
                    "os_type": "Android", "os_version": "12", "app_version": "1.0",
                    "location": {"latitude": 21.0, "longitude": 105.0},
                    "timestamp": "2025-10-22T00:00:00Z"
                },
                "payload": {"type": "text", "content": "Hello via Gateway", "intent": "medical", "sub_intent": "greeting", "metadata": {}},
                "history": [], "stream": False
            }
            
            resp = httpx.post(f"http://localhost:8000{test_endpoint}", json=req, timeout=20)
            if resp.status_code == 200:
                print(f"   ✅ Gateway successfully routed to Agent!")
                print(f"   💬 Response: {resp.json().get('data', {}).get('payload', {}).get('display_message', '')[:100]}...")
            else:
                print(f"   ❌ Status: {resp.status_code}")
                print(f"   Response: {resp.text[:200]}")
        else:
            print(f"   ⚠️  No medical/agent endpoints found in Gateway OpenAPI")
            print(f"   ℹ️  Gateway may need configuration to route to Agent")
    else:
        print(f"   ⚠️  Cannot get Gateway OpenAPI spec")
        
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "="*80)
print("DONE!")
print("="*80)
