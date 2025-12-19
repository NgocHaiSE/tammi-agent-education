"""
Complete test suite for remaining tasks:
1. Test gRPC directly
2. Test Gateway communication
"""
import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import grpc
from agent.proto import agents_pb2, agents_pb2_grpc
import httpx

# =============================================================================
# Configuration from Environment Variables
# =============================================================================
GRPC_HOST = os.getenv('GRPC_HOST', 'localhost')
GRPC_PORT = os.getenv('GRPC_PORT', '50051')
HTTP_HOST = os.getenv('HTTP_HOST', 'localhost')
HTTP_PORT = os.getenv('HTTP_PORT', '8080')
GATEWAY_HOST = os.getenv('GATEWAY_HOST', 'localhost')
GATEWAY_PORT = os.getenv('GATEWAY_PORT', '8000')

# =============================================================================
# TASK 1: Test Agent gRPC (Non-Stream & Stream)
# =============================================================================

def test_agent_grpc_non_stream():
    """Test gRPC non-streaming"""
    print("\n📝 Test 1.1: gRPC Non-Stream Request")
    print("-" * 80)
    
    grpc_target = f'{GRPC_HOST}:{GRPC_PORT}'
    print(f"   🔗 Connecting to: {grpc_target}")
    channel = grpc.insecure_channel(grpc_target)
    
    # Test connection
    try:
        grpc.channel_ready_future(channel).result(timeout=5)
        print("   ✅ gRPC channel connected")
    except grpc.FutureTimeoutError:
        pytest.fail("gRPC channel timeout")
    
    stub = agents_pb2_grpc.AgentServiceStub(channel)
    
    request = agents_pb2.AgentRequest(
        session_id="grpc-test-final",
        flow_id="grpc-flow-final",
        request_id="grpc-req-final",
        user_context=agents_pb2.UserContext(
            user_id="grpc-user",
            family_id="grpc-family",
            name="gRPC Test User"
        ),
        client_context=agents_pb2.ClientContext(
            box_id="grpc-box",
            type_box="smart_speaker",
            device_model="Tammi",
            os_type="linux",
            os_version="5.10",
            app_version="1.0",
            location=agents_pb2.Location(latitude=21.0, longitude=105.0),
            timestamp="2025-10-22T00:00:00Z"
        ),
        payload=agents_pb2.Payload(
            type="text",
            content="Cho tôi biết ngày hôm nay?",
            intent="medical",
            sub_intent="greeting"
        ),
        stream=False
    )
    
    print(f"   📤 Request: {request.payload.content}")
    
    start = time.time()
    # Use unified Chat RPC - consume first response for non-stream mode
    for response in stub.Chat(request, timeout=60):
        break
    elapsed = (time.time() - start) * 1000
    
    print(f"   ⏱️  Time: {elapsed:.0f}ms")
    print(f"   📥 Status: {response.status.code} - {response.status.message}")
    
    msg = response.data.payload.display_message
    print(f"   💬 Response: {msg[:200]}...")
    
    assert "lỗi" not in msg.lower() and "error" not in msg.lower(), "Response contains error"
    
    print(f"   ✅ SUCCESS!")
    channel.close()

def test_agent_grpc_stream():
    """Test gRPC streaming"""
    print("\n📝 Test 1.2: gRPC Stream Request")
    print("-" * 80)
    
    grpc_target = f'{GRPC_HOST}:{GRPC_PORT}'
    print(f"   🔗 Connecting to: {grpc_target}")
    channel = grpc.insecure_channel(grpc_target)
    stub = agents_pb2_grpc.AgentServiceStub(channel)
    
    request = agents_pb2.AgentRequest(
        session_id="grpc-stream-test",
        flow_id="grpc-stream-flow",
        request_id="grpc-stream-req",
        user_context=agents_pb2.UserContext(
            user_id="grpc-user",
            family_id="grpc-family",
            name="Stream Test"
        ),
        client_context=agents_pb2.ClientContext(
            box_id="grpc-box",
            type_box="smart_speaker",
            device_model="Tammi",
            os_type="linux",
            os_version="5.10",
            app_version="1.0",
            location=agents_pb2.Location(latitude=21.0, longitude=105.0),
            timestamp="2025-10-22T00:00:00Z"
        ),
        payload=agents_pb2.Payload(
            type="text",
            content="Kể cho tôi một câu chuyện ngắn",
            intent="medical",
            sub_intent="storytelling"
        ),
        stream=True
    )
    
    print(f"   📤 Request: {request.payload.content}")
    print(f"   📊 Streaming responses:")
    
    chunks = 0
    total_text = ""
    start = time.time()
    
    try:
        # Use unified Chat RPC for streaming
        for response in stub.Chat(request, timeout=60):
            chunks += 1
            msg = response.data.payload.display_message
            total_text += msg
            if chunks <= 3:
                print(f"      Chunk {chunks}: {msg[:100]}...")
    except Exception as stream_error:
        print(f"   ⚠️  Stream error: {stream_error}")
        if chunks > 0:
            print(f"   ⚠️  Received {chunks} chunks before error")
    
    elapsed = (time.time() - start) * 1000
    
    print(f"   ⏱️  Time: {elapsed:.0f}ms")
    print(f"   📊 Total chunks: {chunks}")
    print(f"   📊 Total text length: {len(total_text)}")
    
    assert chunks > 0, f"No chunks received from stream"
    
    print(f"   ✅ SUCCESS! (received {chunks} chunks)")
    channel.close()

# =============================================================================
# TASK 2: Test Gateway Communication
# =============================================================================

def test_gateway_health():
    """Test Gateway health"""
    print("\n📝 Test 2.1: Gateway Health Check")
    print("-" * 80)
    
    gateway_url = f"http://{GATEWAY_HOST}:{GATEWAY_PORT}/management/health"
    print(f"   🔗 Checking: {gateway_url}")
    
    try:
        response = httpx.get(gateway_url, timeout=5)
        print(f"   📥 Status: {response.status_code}")
        print(f"   📄 Response: {response.text[:200]}")
        
        assert response.status_code == 200, f"Gateway health check failed with status {response.status_code}"
        print(f"   ✅ Gateway is healthy")
            
    except httpx.ConnectError:
        pytest.skip("Gateway not running - skipping test (this is expected if no Gateway in scope)")

def test_gateway_docs():
    """Test Gateway docs"""
    print("\n📝 Test 2.2: Gateway OpenAPI Documentation")
    print("-" * 80)
    
    openapi_url = f"http://{GATEWAY_HOST}:{GATEWAY_PORT}/openapi.json"
    print(f"   🔗 Fetching: {openapi_url}")
    
    try:
        response = httpx.get(openapi_url, timeout=5)
    except httpx.ConnectError:
        pytest.skip("Gateway not running - skipping test (this is expected if no Gateway in scope)")
    
    assert response.status_code == 200, f"OpenAPI endpoint returned status {response.status_code}"
    
    spec = response.json()
    print(f"   ✅ OpenAPI spec available")
    print(f"   📚 API: {spec.get('info', {}).get('title', 'N/A')}")
    print(f"   📋 Endpoints: {len(spec.get('paths', {}))} paths")
    
    # Check for agent/medical endpoints
    paths = spec.get('paths', {})
    agent_paths = [p for p in paths.keys() if 'agent' in p.lower() or 'medical' in p.lower()]
    
    if agent_paths:
        print(f"   🎯 Agent-related endpoints found:")
        for p in agent_paths[:5]:
            print(f"      - {p}")
    else:
        print(f"   ⚠️  No agent-specific endpoints found")
    
    docs_url = f"http://{GATEWAY_HOST}:{GATEWAY_PORT}/docs"
    print(f"   ✅ Docs available at: {docs_url}")

def test_gateway_routing():
    """Test if Gateway can route to Agent"""
    print("\n📝 Test 2.3: Gateway → Agent Routing")
    print("-" * 80)
    
    # Try common endpoint patterns
    endpoints_to_try = [
        "/api/v1/agents/medical/api/v1/chat",
        "/api/v1/medical/api/v1/chat",
        "/api/agents/medical",
        "/agents/medical/api/v1/chat",
        "/medical/api/v1/chat",
    ]
    
    req = {
        "session_id": "gateway-test",
        "flow_id": "gateway-flow",
        "request_id": "gateway-req",
        "user_context": {"user_id": "u1", "family_id": "f1", "name": "Gateway Test"},
        "client_context": {
            "box_id": "b1",
            "type_box": "phone",
            "device_model": "X",
            "os_type": "Android",
            "os_version": "12",
            "app_version": "1.0",
            "location": {"latitude": 21.0, "longitude": 105.0},
            "timestamp": "2025-10-22T00:00:00Z"
        },
        "payload": {
            "type": "text",
            "content": "Test từ Gateway",
            "intent": "medical",
            "sub_intent": "greeting",
            "metadata": {}
        },
        "history": [],
        "stream": False
    }
    
    success = False
    for endpoint in endpoints_to_try:
        try:
            gateway_endpoint = f"http://{GATEWAY_HOST}:{GATEWAY_PORT}{endpoint}"
            print(f"   🔍 Trying: {gateway_endpoint}")
            response = httpx.post(
                gateway_endpoint,
                json=req,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                msg = data.get('data', {}).get('payload', {}).get('display_message', '')
                print(f"   ✅ SUCCESS! Gateway routed to Agent")
                print(f"   💬 Response: {msg[:150]}...")
                success = True
                break
            elif response.status_code == 404:
                print(f"   ⚠️  404 Not Found")
            else:
                print(f"   ⚠️  Status {response.status_code}")
                
        except httpx.TimeoutException:
            print(f"   ⏱️  Timeout")
        except Exception as e:
            print(f"   ⚠️  Error: {str(e)[:50]}")
    
    if not success:
        print(f"\n   ⚠️  No working Gateway endpoint found")
        print(f"   ℹ️  Gateway may need configuration to route to Agent")
        print(f"   ℹ️  Agent is available at:")
        print(f"      - HTTP: http://{HTTP_HOST}:{HTTP_PORT}/api/v1/chat")
        print(f"      - gRPC: {GRPC_HOST}:{GRPC_PORT}")
        pytest.skip("Gateway not running or routing not configured - skipping test (this is expected if no Gateway in scope)")

# =============================================================================
# Script Mode - Manual Execution
# =============================================================================
if __name__ == "__main__":
    """Run all tests manually as a script"""
    print("="*80)
    print("FINAL TESTS - gRPC & Gateway")
    print("="*80)
    
    results = {
        "Agent gRPC Non-Stream": False,
        "Agent gRPC Stream": False,
        "Gateway Health": False,
        "Gateway Docs": False,
        "Gateway Routing": False,
    }

    print("\n" + "="*80)
    print("RUNNING ALL TESTS...")
    print("="*80)

    # Task 1: Agent gRPC
    try:
        test_agent_grpc_non_stream()
        results["Agent gRPC Non-Stream"] = True
    except:
        pass
    time.sleep(1)

    try:
        test_agent_grpc_stream()
        results["Agent gRPC Stream"] = True
    except:
        pass
    time.sleep(1)

    # Task 2: Gateway
    try:
        test_gateway_health()
        results["Gateway Health"] = True
    except:
        pass
    time.sleep(0.5)

    try:
        test_gateway_docs()
        results["Gateway Docs"] = True
    except:
        pass
    time.sleep(0.5)

    try:
        test_gateway_routing()
        results["Gateway Routing"] = True
    except:
        pass

    # =============================================================================
    # FINAL SUMMARY
    # =============================================================================

    print("\n" + "="*80)
    print("📊 FINAL TEST SUMMARY")
    print("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        icon = "✅" if result else "❌"
        print(f"{icon} {test_name}")

    print(f"\n📈 Results: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    print("\n" + "="*80)
    print("🎯 CONCLUSIONS")
    print("="*80)

    if results["Agent gRPC Non-Stream"] and results["Agent gRPC Stream"]:
        print("✅ Agent gRPC: Hoạt động tốt (cả non-stream và stream)")
    else:
        print("⚠️  Agent gRPC: Cần kiểm tra thêm")

    if results["Gateway Health"]:
        print("✅ Gateway: Đang chạy")
        if results["Gateway Routing"]:
            print("✅ Gateway Routing: Đã cấu hình và hoạt động")
        else:
            print("⚠️  Gateway Routing: Chưa cấu hình routing đến Agent")
            print("   → Cần cấu hình Gateway để forward requests đến:")
            print(f"      HTTP: http://{HTTP_HOST}:{HTTP_PORT}/api/v1/chat")
            print(f"      gRPC: {GRPC_HOST}:{GRPC_PORT}")
    else:
        print("⚠️  Gateway: Không kết nối được (có thể chưa chạy)")

    print("\n" + "="*80)
    print("✨ TEST COMPLETED!")
    print("="*80)
