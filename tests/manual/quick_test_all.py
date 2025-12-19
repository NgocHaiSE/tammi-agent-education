"""
Quick test script to test individual endpoints
"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import httpx
    import grpc
    from agent.proto import agents_pb2, agents_pb2_grpc
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    sys.exit(1)

def test_agent_http_health():
    """Test 1: Agent HTTP Health"""
    print("\n" + "="*80)
    print("TEST 1: Agent HTTP Health Check")
    print("="*80)
    
    try:
        response = httpx.get("http://localhost:8001/management/health", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print("✅ PASSED")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_agent_http_non_stream():
    """Test 2: Agent HTTP Non-Stream"""
    print("\n" + "="*80)
    print("TEST 2: Agent HTTP Non-Stream Request")
    print("="*80)
    
    try:
        req = {
            "session_id": "test-001",
            "flow_id": "flow-001",
            "request_id": "req-001",
            "user_context": {"user_id": "u1", "family_id": "f1", "name": "Test"},
            "client_context": {
                "box_id": "b1", "type_box": "phone", "device_model": "X",
                "os_type": "Android", "os_version": "12", "app_version": "1.0",
                "location": {"latitude": 21.0, "longitude": 105.0},
                "timestamp": "2025-10-22T00:00:00Z"
            },
            "payload": {
                "type": "text",
                "content": "Xin chào!",
                "intent": "medical",
                "sub_intent": "greeting",
                "metadata": {}
            },
            "history": [],
            "stream": False
        }
        
        print(f"Sending request: {req['payload']['content']}")
        start = time.time()
        response = httpx.post("http://localhost:8001/api/v1/chat", json=req, timeout=30)
        elapsed = (time.time() - start) * 1000
        
        print(f"Status: {response.status_code}")
        print(f"Response time: {elapsed:.2f}ms")
        
        if response.status_code == 200:
            data = response.json()
            msg = data.get('data', {}).get('payload', {}).get('display_message', '')
            print(f"Message: {msg[:200]}")
            print("✅ PASSED")
            return True
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_agent_grpc_health():
    """Test 3: Agent gRPC Connection"""
    print("\n" + "="*80)
    print("TEST 3: Agent gRPC Connection Test")
    print("="*80)
    
    try:
        channel = grpc.insecure_channel('localhost:50052')
        
        # Test channel connectivity
        try:
            grpc.channel_ready_future(channel).result(timeout=5)
            print("✅ gRPC channel is ready")
        except grpc.FutureTimeoutError:
            print("❌ gRPC channel timeout")
            return False
            
        stub = agents_pb2_grpc.AgentServiceStub(channel)
        
        request = agents_pb2.AgentRequest(
            session_id="grpc-test-001",
            flow_id="grpc-flow-001",
            request_id="grpc-req-001",
            user_context=agents_pb2.UserContext(
                user_id="grpc-user", family_id="grpc-family", name="gRPC Test"
            ),
            client_context=agents_pb2.ClientContext(
                box_id="b1", type_box="phone", device_model="X",
                os_type="Android", os_version="12", app_version="1.0",
                location=agents_pb2.Location(latitude=21.0, longitude=105.0),
                timestamp="2025-10-22T00:00:00Z"
            ),
            payload=agents_pb2.Payload(
                type="text", content="Xin chào qua gRPC!",
                intent="medical", sub_intent="greeting"
            ),
            stream=False
        )
        
        print(f"Sending gRPC request: {request.payload.content}")
        start = time.time()
        # Use Chat RPC (unified method, always returns stream)
        # For non-stream mode, consume first response
        response = None
        for r in stub.Chat(request, timeout=30):
            response = r
            break
        elapsed = (time.time() - start) * 1000
        
        print(f"Response time: {elapsed:.2f}ms")
        print(f"Status: {response.status.code} - {response.status.message}")
        print(f"Message: {response.data.payload.display_message[:200]}")
        print("✅ PASSED")
        
        channel.close()
        return True
        
    except grpc.RpcError as e:
        print(f"❌ gRPC Error: {e.code()} - {e.details()}")
        return False
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_gateway_http_health():
    """Test 4: API Gateway HTTP Health"""
    print("\n" + "="*80)
    print("TEST 4: API Gateway HTTP Health Check")
    print("="*80)
    
    try:
        response = httpx.get("http://localhost:8000/management/health", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        print("✅ PASSED")
        return True
    except httpx.ConnectError:
        print("❌ Cannot connect to API Gateway")
        return False
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_gateway_docs():
    """Test 5: API Gateway Docs"""
    print("\n" + "="*80)
    print("TEST 5: API Gateway OpenAPI Docs")
    print("="*80)
    
    try:
        response = httpx.get("http://localhost:8000/docs", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Docs available at: http://localhost:8000/docs")
        if response.status_code == 200:
            print("✅ PASSED")
            return True
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_gateway_to_agent_http():
    """Test 6: Gateway HTTP to Agent"""
    print("\n" + "="*80)
    print("TEST 6: API Gateway HTTP → Agent Communication")
    print("="*80)
    
    # Try different possible endpoints
    endpoints = [
        "/api/v1/medical/api/v1/chat",
        "/api/medical/api/v1/chat",
        "/medical/api/v1/chat",
        "/agents/medical/api/v1/chat"
    ]
    
    req = {
        "session_id": "gateway-test-001",
        "flow_id": "gateway-flow-001",
        "request_id": "gateway-req-001",
        "user_context": {"user_id": "u1", "family_id": "f1", "name": "Gateway Test"},
        "client_context": {
            "box_id": "b1", "type_box": "phone", "device_model": "X",
            "os_type": "Android", "os_version": "12", "app_version": "1.0",
            "location": {"latitude": 21.0, "longitude": 105.0},
            "timestamp": "2025-10-22T00:00:00Z"
        },
        "payload": {
            "type": "text",
            "content": "Xin chào từ Gateway!",
            "intent": "medical",
            "sub_intent": "greeting",
            "metadata": {}
        },
        "history": [],
        "stream": False
    }
    
    for endpoint in endpoints:
        print(f"\nTrying: http://localhost:8000{endpoint}")
        try:
            response = httpx.post(f"http://localhost:8000{endpoint}", json=req, timeout=30)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS - Gateway routed to Agent!")
                msg = data.get('data', {}).get('payload', {}).get('display_message', '')
                print(f"Message: {msg[:200]}")
                return True
            elif response.status_code == 404:
                print(f"⚠️  Not found, trying next endpoint...")
            else:
                print(f"❌ HTTP {response.status_code}")
                print(f"Response: {response.text[:500]}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n❌ No working gateway endpoint found")
    print("ℹ️  This may be expected if Gateway hasn't configured medical routing yet")
    return False

def main():
    """Run all quick tests"""
    print("="*80)
    print("  medical AGENT - QUICK TEST SUITE")
    print("="*80)
    
    results = []
    
    # Test Agent Direct
    results.append(("Agent HTTP Health", test_agent_http_health()))
    time.sleep(0.5)
    
    results.append(("Agent HTTP Non-Stream", test_agent_http_non_stream()))
    time.sleep(0.5)
    
    results.append(("Agent gRPC", test_agent_grpc_health()))
    time.sleep(0.5)
    
    # Test Gateway
    results.append(("Gateway HTTP Health", test_gateway_http_health()))
    time.sleep(0.5)
    
    results.append(("Gateway Docs", test_gateway_docs()))
    time.sleep(0.5)
    
    results.append(("Gateway → Agent HTTP", test_gateway_to_agent_http()))
    
    # Summary
    print("\n" + "="*80)
    print("  TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status:12} | {name}")
    
    print(f"\nTotal: {passed}/{total} passed ({passed/total*100:.1f}%)")
    
    print("\n" + "="*80)
    print("  ANALYSIS & RECOMMENDATIONS")
    print("="*80)
    
    agent_tests = results[:3]
    gateway_tests = results[3:]
    
    agent_passed = all(result for _, result in agent_tests)
    gateway_connected = any(result for _, result in gateway_tests[:2])
    gateway_routing = results[-1][1]
    
    print("\n📊 Agent Status:")
    if agent_passed:
        print("   ✅ All agent endpoints working correctly!")
        print("   ✅ HTTP server operational on port 8001")
        print("   ✅ gRPC server operational on port 50052")
    else:
        print("   ❌ Some agent tests failed")
        print("   ℹ️  Check if agent is running: python -m agent.entrypoint.run")
    
    print("\n📊 API Gateway Status:")
    if gateway_connected:
        print("   ✅ API Gateway is running on port 8000")
        if gateway_routing:
            print("   ✅ Gateway successfully routes to Agent")
        else:
            print("   ⚠️  Gateway is up but medical routing not configured")
            print("   ℹ️  Need to configure Gateway to route /api/v1/medical/* to Agent")
    else:
        print("   ❌ Cannot connect to API Gateway")
        print("   ℹ️  Make sure Gateway is running on port 8000")
    
    print("\n💡 Next Steps:")
    if not agent_passed:
        print("   1. Start the agent: python -m agent.entrypoint.run")
    if gateway_connected and not gateway_routing:
        print("   2. Configure Gateway to route medical requests to Agent")
        print("      - HTTP: localhost:8001/api/v1/chat")
        print("      - gRPC: localhost:50052")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
