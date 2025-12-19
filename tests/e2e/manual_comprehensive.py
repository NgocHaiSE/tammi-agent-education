"""
Comprehensive Test Suite for medical Agent
Tests both direct agent endpoints and communication with API Gateway
"""
import sys
import os
import json
import time
from typing import Dict, Any, List
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import grpc
    from agent.proto import agents_pb2, agents_pb2_grpc
    from google.protobuf import json_format
    import httpx
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Install: pip install grpcio grpcio-tools protobuf httpx")
    sys.exit(1)


class TestResult:
    """Store test result details"""
    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category
        self.success = False
        self.error = None
        self.response_time_ms = 0
        self.details = {}
        
    def mark_success(self, response_time_ms: float, details: Dict = None):
        self.success = True
        self.response_time_ms = response_time_ms
        self.details = details or {}
        
    def mark_failure(self, error: str, details: Dict = None):
        self.success = False
        self.error = error
        self.details = details or {}


class ComprehensiveTestSuite:
    """Comprehensive test suite for all endpoints"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.agent_http_url = "http://localhost:8001"
        self.agent_grpc_url = "localhost:50052"
        self.gateway_http_url = "http://localhost:8001"
        self.gateway_grpc_url = "localhost:50051"
        
    def print_header(self, title: str):
        """Print formatted header"""
        print("\n" + "="*80)
        print(f"  {title}")
        print("="*80)
        
    def print_test_header(self, test_name: str):
        """Print test name"""
        print(f"\n🧪 TEST: {test_name}")
        print("-" * 80)
        
    def create_sample_request(self, content: str, intent: str = "medical", 
                            sub_intent: str = "greeting", stream: bool = False) -> Dict[str, Any]:
        """Create a sample request payload"""
        return {
            "session_id": f"test-session-{int(time.time())}",
            "flow_id": f"test-flow-{int(time.time())}",
            "request_id": f"test-req-{int(time.time())}",
            "user_context": {
                "user_id": "test-user-123",
                "family_id": "test-family-456",
                "name": "Test User"
            },
            "client_context": {
                "box_id": "test-box-001",
                "type_box": "smart_speaker",
                "device_model": "Tammi Gen2",
                "os_type": "linux",
                "os_version": "5.10",
                "app_version": "1.0.0",
                "location": {
                    "latitude": 21.0285,
                    "longitude": 105.8542
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            },
            "payload": {
                "type": "text",
                "content": content,
                "intent": intent,
                "sub_intent": sub_intent,
                "metadata": {}
            },
            "history": [],
            "stream": stream
        }
    
    def create_grpc_request(self, content: str, intent: str = "medical",
                          sub_intent: str = "greeting", stream: bool = False) -> agents_pb2.AgentRequest:
        """Create a gRPC request"""
        return agents_pb2.AgentRequest(
            session_id=f"grpc-test-{int(time.time())}",
            flow_id=f"grpc-flow-{int(time.time())}",
            request_id=f"grpc-req-{int(time.time())}",
            user_context=agents_pb2.UserContext(
                user_id="grpc-user-123",
                family_id="grpc-family-456",
                name="gRPC Tester"
            ),
            client_context=agents_pb2.ClientContext(
                box_id="grpc-box-001",
                type_box="smart_speaker",
                device_model="Tammi Gen2",
                os_type="linux",
                os_version="5.10",
                app_version="1.0.0",
                location=agents_pb2.Location(
                    latitude=21.0285,
                    longitude=105.8542
                ),
                timestamp=datetime.utcnow().isoformat() + "Z"
            ),
            payload=agents_pb2.Payload(
                type="text",
                content=content,
                intent=intent,
                sub_intent=sub_intent
            ),
            stream=stream
        )
    
    # =========================================================================
    # TEST 1: Agent HTTP Health Check
    # =========================================================================
    def test_agent_http_health(self):
        """Test agent HTTP health endpoint"""
        result = TestResult("Agent HTTP Health Check", "Agent Direct")
        self.print_test_header(result.name)
        
        try:
            start = time.time()
            response = httpx.get(f"{self.agent_http_url}/management/health", timeout=10)
            elapsed = (time.time() - start) * 1000
            
            print(f"📤 GET {self.agent_http_url}/management/health")
            print(f"📥 Status: {response.status_code}")
            print(f"📥 Response: {response.text}")
            print(f"⏱️  Response time: {elapsed:.2f}ms")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    result.mark_success(elapsed, {"status": "ok"})
                    print("✅ PASSED: Health check successful")
                else:
                    result.mark_failure(f"Unexpected status: {data}")
                    print("❌ FAILED: Unexpected response")
            else:
                result.mark_failure(f"HTTP {response.status_code}")
                print(f"❌ FAILED: HTTP {response.status_code}")
                
        except Exception as e:
            result.mark_failure(str(e))
            print(f"❌ FAILED: {e}")
            
        self.results.append(result)
    
    # =========================================================================
    # TEST 2: Agent HTTP Non-Stream Request
    # =========================================================================
    def test_agent_http_non_stream(self):
        """Test agent HTTP non-streaming request"""
        result = TestResult("Agent HTTP Non-Stream", "Agent Direct")
        self.print_test_header(result.name)
        
        try:
            req_data = self.create_sample_request(
                "Xin chào! Hôm nay trời đẹp nhỉ?",
                "medical",
                "greeting",
                False
            )
            
            print(f"📤 POST {self.agent_http_url}/api/v1/chat")
            print(f"   Content: {req_data['payload']['content']}")
            print(f"   Intent: {req_data['payload']['intent']}/{req_data['payload']['sub_intent']}")
            print(f"   Stream: {req_data['stream']}")
            
            start = time.time()
            response = httpx.post(
                f"{self.agent_http_url}/api/v1/chat",
                json=req_data,
                timeout=60
            )
            elapsed = (time.time() - start) * 1000
            
            print(f"📥 Status: {response.status_code}")
            print(f"⏱️  Response time: {elapsed:.2f}ms")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📥 Session: {data.get('session_id')}")
                print(f"📥 Status: {data.get('status', {}).get('code')} - {data.get('status', {}).get('message')}")
                
                if 'data' in data and 'payload' in data['data']:
                    msg = data['data']['payload'].get('display_message', '')
                    print(f"💬 Message: {msg[:200]}...")
                    result.mark_success(elapsed, {
                        "message_length": len(msg),
                        "status_code": data.get('status', {}).get('code')
                    })
                    print("✅ PASSED: Received valid response")
                else:
                    result.mark_failure("Missing data/payload in response")
                    print("❌ FAILED: Missing data in response")
            else:
                result.mark_failure(f"HTTP {response.status_code}")
                print(f"❌ FAILED: HTTP {response.status_code}")
                
        except Exception as e:
            result.mark_failure(str(e))
            print(f"❌ FAILED: {e}")
            
        self.results.append(result)
    
    # =========================================================================
    # TEST 3: Agent HTTP Stream Request
    # =========================================================================
    def test_agent_http_stream(self):
        """Test agent HTTP streaming request"""
        result = TestResult("Agent HTTP Stream", "Agent Direct")
        self.print_test_header(result.name)
        
        try:
            req_data = self.create_sample_request(
                "Gợi ý một số hoạt động vui vẻ cho cuối tuần này",
                "medical",
                "weekend_idea",
                True
            )
            
            print(f"📤 POST {self.agent_http_url}/api/v1/chat (streaming)")
            print(f"   Content: {req_data['payload']['content']}")
            print(f"   Stream: {req_data['stream']}")
            
            chunks_received = 0
            total_content = ""
            
            start = time.time()
            with httpx.stream("POST", f"{self.agent_http_url}/api/v1/chat", 
                            json=req_data, timeout=60) as response:
                print(f"📥 Status: {response.status_code}")
                print(f"📥 Content-Type: {response.headers.get('content-type')}")
                print("\n💬 Streaming response:")
                
                for line in response.iter_lines():
                    if line.strip():
                        chunks_received += 1
                        try:
                            chunk_data = json.loads(line)
                            if 'data' in chunk_data and 'payload' in chunk_data['data']:
                                msg = chunk_data['data']['payload'].get('display_message', '')
                                total_content += msg
                                print(f"   Chunk {chunks_received}: {msg[:100]}...")
                        except json.JSONDecodeError:
                            print(f"   ⚠️  Invalid JSON in chunk: {line[:100]}")
                            
            elapsed = (time.time() - start) * 1000
            print(f"\n⏱️  Response time: {elapsed:.2f}ms")
            print(f"📊 Total chunks: {chunks_received}")
            print(f"📊 Total content length: {len(total_content)}")
            
            if chunks_received > 0:
                result.mark_success(elapsed, {
                    "chunks": chunks_received,
                    "content_length": len(total_content)
                })
                print("✅ PASSED: Received streaming response")
            else:
                result.mark_failure("No chunks received")
                print("❌ FAILED: No chunks received")
                
        except Exception as e:
            result.mark_failure(str(e))
            print(f"❌ FAILED: {e}")
            
        self.results.append(result)
    
    # =========================================================================
    # TEST 4: Agent gRPC Non-Stream Request
    # =========================================================================
    def test_agent_grpc_non_stream(self):
        """Test agent gRPC non-streaming request"""
        result = TestResult("Agent gRPC Non-Stream", "Agent Direct")
        self.print_test_header(result.name)
        
        try:
            channel = grpc.insecure_channel(self.agent_grpc_url)
            stub = agents_pb2_grpc.AgentServiceStub(channel)
            
            request = self.create_grpc_request(
                "Xin chào! Hôm nay trời đẹp nhỉ?",
                "medical",
                "greeting",
                False
            )
            
            print(f"📤 gRPC Call to {self.agent_grpc_url}")
            print(f"   Method: Chat (unary mode)")
            print(f"   Content: {request.payload.content}")
            print(f"   Stream: {request.stream}")
            
            start = time.time()
            # Use unified Chat RPC - consume first response for non-stream mode
            for response in stub.Chat(request, timeout=60):
                break
            elapsed = (time.time() - start) * 1000
            
            print(f"📥 Response received")
            print(f"   Status: {response.status.code} - {response.status.message}")
            print(f"   Session: {response.session_id}")
            print(f"   Intent: {response.data.payload.intent}/{response.data.payload.sub_intent}")
            print(f"💬 Message: {response.data.payload.display_message[:200]}...")
            print(f"⏱️  Response time: {elapsed:.2f}ms")
            
            if response.status.code == 200:
                result.mark_success(elapsed, {
                    "message_length": len(response.data.payload.display_message),
                    "status_code": response.status.code
                })
                print("✅ PASSED: Received valid gRPC response")
            else:
                result.mark_failure(f"Status code: {response.status.code}")
                print(f"❌ FAILED: Status code {response.status.code}")
                
            channel.close()
            
        except grpc.RpcError as e:
            result.mark_failure(f"gRPC Error: {e.code()} - {e.details()}")
            print(f"❌ FAILED: gRPC Error {e.code()}: {e.details()}")
        except Exception as e:
            result.mark_failure(str(e))
            print(f"❌ FAILED: {e}")
            
        self.results.append(result)
    
    # =========================================================================
    # TEST 5: Agent gRPC Stream Request
    # =========================================================================
    def test_agent_grpc_stream(self):
        """Test agent gRPC streaming request"""
        result = TestResult("Agent gRPC Stream", "Agent Direct")
        self.print_test_header(result.name)
        
        try:
            channel = grpc.insecure_channel(self.agent_grpc_url)
            stub = agents_pb2_grpc.AgentServiceStub(channel)
            
            request = self.create_grpc_request(
                "Gợi ý một số hoạt động vui vẻ cho cuối tuần này",
                "medical",
                "weekend_idea",
                True
            )
            
            print(f"📤 gRPC Call to {self.agent_grpc_url}")
            print(f"   Method: Chat (streaming mode)")
            print(f"   Content: {request.payload.content}")
            print(f"   Stream: {request.stream}")
            
            chunks_received = 0
            total_content = ""
            
            print("\n💬 Streaming response:")
            start = time.time()
            
            # Use unified Chat RPC for streaming
            for response in stub.Chat(request, timeout=60):
                chunks_received += 1
                msg = response.data.payload.display_message
                total_content += msg
                print(f"   Chunk {chunks_received}: {msg[:100]}...")
                
            elapsed = (time.time() - start) * 1000
            
            print(f"\n⏱️  Response time: {elapsed:.2f}ms")
            print(f"📊 Total chunks: {chunks_received}")
            print(f"📊 Total content length: {len(total_content)}")
            
            if chunks_received > 0:
                result.mark_success(elapsed, {
                    "chunks": chunks_received,
                    "content_length": len(total_content)
                })
                print("✅ PASSED: Received gRPC streaming response")
            else:
                result.mark_failure("No chunks received")
                print("❌ FAILED: No chunks received")
                
            channel.close()
            
        except grpc.RpcError as e:
            result.mark_failure(f"gRPC Error: {e.code()} - {e.details()}")
            print(f"❌ FAILED: gRPC Error {e.code()}: {e.details()}")
        except Exception as e:
            result.mark_failure(str(e))
            print(f"❌ FAILED: {e}")
            
        self.results.append(result)
    
    # =========================================================================
    # TEST 6: API Gateway HTTP Health Check
    # =========================================================================
    def test_gateway_http_health(self):
        """Test API Gateway HTTP health endpoint"""
        result = TestResult("API Gateway HTTP Health", "Gateway Communication")
        self.print_test_header(result.name)
        
        try:
            start = time.time()
            response = httpx.get(f"{self.gateway_http_url}/management/health", timeout=10)
            elapsed = (time.time() - start) * 1000
            
            print(f"📤 GET {self.gateway_http_url}/management/health")
            print(f"📥 Status: {response.status_code}")
            print(f"📥 Response: {response.text}")
            print(f"⏱️  Response time: {elapsed:.2f}ms")
            
            if response.status_code == 200:
                result.mark_success(elapsed, {"response": response.text})
                print("✅ PASSED: API Gateway health check successful")
            else:
                result.mark_failure(f"HTTP {response.status_code}")
                print(f"❌ FAILED: HTTP {response.status_code}")
                
        except Exception as e:
            result.mark_failure(str(e))
            print(f"❌ FAILED: {e}")
            
        self.results.append(result)
    
    # =========================================================================
    # TEST 7: Gateway HTTP to Agent Communication
    # =========================================================================
    def test_gateway_http_to_agent(self):
        """Test communication from Gateway HTTP to Agent"""
        result = TestResult("Gateway HTTP → Agent", "Gateway Communication")
        self.print_test_header(result.name)
        
        try:
            # Check if gateway has a medical endpoint
            # This depends on your gateway implementation
            # Adjust the endpoint as needed
            
            req_data = self.create_sample_request(
                "Xin chào từ API Gateway",
                "medical",
                "greeting",
                False
            )
            
            print(f"📤 POST {self.gateway_http_url}/api/v1/medical/api/v1/chat")
            print(f"   Content: {req_data['payload']['content']}")
            print(f"   Note: Testing if Gateway can route to Agent")
            
            start = time.time()
            response = httpx.post(
                f"{self.gateway_http_url}/api/v1/medical/api/v1/chat",
                json=req_data,
                timeout=60
            )
            elapsed = (time.time() - start) * 1000
            
            print(f"📥 Status: {response.status_code}")
            print(f"⏱️  Response time: {elapsed:.2f}ms")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📥 Response: {json.dumps(data, indent=2)[:500]}...")
                result.mark_success(elapsed, {"gateway_routing": "success"})
                print("✅ PASSED: Gateway successfully routed to Agent")
            elif response.status_code == 404:
                result.mark_failure("Endpoint not found - Gateway may not have medical route configured")
                print("⚠️  SKIPPED: Gateway endpoint not found (may need configuration)")
            else:
                result.mark_failure(f"HTTP {response.status_code}")
                print(f"❌ FAILED: HTTP {response.status_code}")
                print(f"   Response: {response.text[:500]}")
                
        except httpx.ConnectError:
            result.mark_failure("Cannot connect to Gateway")
            print("❌ FAILED: Cannot connect to API Gateway")
        except Exception as e:
            result.mark_failure(str(e))
            print(f"❌ FAILED: {e}")
            
        self.results.append(result)
    
    # =========================================================================
    # TEST 8: Gateway gRPC to Agent Communication
    # =========================================================================
    def test_gateway_grpc_to_agent(self):
        """Test communication from Gateway gRPC to Agent"""
        result = TestResult("Gateway gRPC → Agent", "Gateway Communication")
        self.print_test_header(result.name)
        
        try:
            channel = grpc.insecure_channel(self.gateway_grpc_url)
            
            # Try to connect - Gateway should have AgentService if configured
            stub = agents_pb2_grpc.AgentServiceStub(channel)
            
            request = self.create_grpc_request(
                "Xin chào từ Gateway gRPC",
                "medical",
                "greeting",
                False
            )
            
            print(f"📤 gRPC Call to {self.gateway_grpc_url}")
            print(f"   Method: Chat (via Gateway)")
            print(f"   Content: {request.payload.content}")
            print(f"   Note: Testing if Gateway gRPC can route to Agent")
            
            start = time.time()
            # Use unified Chat RPC - consume first response
            for response in stub.Chat(request, timeout=60):
                break
            elapsed = (time.time() - start) * 1000
            
            print(f"📥 Response received")
            print(f"   Status: {response.status.code} - {response.status.message}")
            print(f"⏱️  Response time: {elapsed:.2f}ms")
            
            if response.status.code == 200:
                result.mark_success(elapsed, {"gateway_routing": "success"})
                print("✅ PASSED: Gateway gRPC successfully routed to Agent")
            else:
                result.mark_failure(f"Status code: {response.status.code}")
                print(f"❌ FAILED: Status code {response.status.code}")
                
            channel.close()
            
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.UNIMPLEMENTED:
                result.mark_failure("Gateway gRPC service not implemented")
                print("⚠️  SKIPPED: Gateway gRPC service not implemented for medical")
            else:
                result.mark_failure(f"gRPC Error: {e.code()} - {e.details()}")
                print(f"❌ FAILED: gRPC Error {e.code()}: {e.details()}")
        except Exception as e:
            result.mark_failure(str(e))
            print(f"❌ FAILED: {e}")
            
        self.results.append(result)
    
    # =========================================================================
    # Generate Report
    # =========================================================================
    def generate_report(self):
        """Generate comprehensive test report"""
        self.print_header("TEST REPORT")
        
        # Group by category
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = []
            categories[result.category].append(result)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 OVERALL SUMMARY")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {passed_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        for category, results in categories.items():
            print(f"\n{'='*80}")
            print(f"📂 Category: {category}")
            print(f"{'='*80}")
            
            for result in results:
                status_icon = "✅" if result.success else "❌"
                print(f"\n{status_icon} {result.name}")
                
                if result.success:
                    print(f"   ⏱️  Response Time: {result.response_time_ms:.2f}ms")
                    if result.details:
                        print(f"   📋 Details: {json.dumps(result.details, indent=6)}")
                else:
                    print(f"   ❌ Error: {result.error}")
                    if result.details:
                        print(f"   📋 Details: {json.dumps(result.details, indent=6)}")
        
        # Performance summary
        successful_tests = [r for r in self.results if r.success]
        if successful_tests:
            avg_response_time = sum(r.response_time_ms for r in successful_tests) / len(successful_tests)
            max_response_time = max(r.response_time_ms for r in successful_tests)
            min_response_time = min(r.response_time_ms for r in successful_tests)
            
            print(f"\n{'='*80}")
            print(f"⚡ PERFORMANCE SUMMARY (Successful Tests Only)")
            print(f"{'='*80}")
            print(f"   Average Response Time: {avg_response_time:.2f}ms")
            print(f"   Min Response Time: {min_response_time:.2f}ms")
            print(f"   Max Response Time: {max_response_time:.2f}ms")
        
        # Recommendations
        print(f"\n{'='*80}")
        print(f"💡 RECOMMENDATIONS")
        print(f"{'='*80}")
        
        if failed_tests > 0:
            print("\n⚠️  Issues Found:")
            for result in self.results:
                if not result.success:
                    print(f"   • {result.name}: {result.error}")
        
        # Check Gateway communication
        gateway_tests = [r for r in self.results if r.category == "Gateway Communication"]
        gateway_passed = sum(1 for r in gateway_tests if r.success)
        
        if gateway_passed < len(gateway_tests):
            print("\n📝 Gateway Communication Issues:")
            print("   • Make sure API Gateway is properly configured to route to medical Agent")
            print("   • Check Gateway routing configuration for /api/v1/medical/* endpoints")
            print("   • Verify Gateway gRPC service includes AgentService for medical")
        
        if all(r.success for r in self.results if r.category == "Agent Direct"):
            print("\n✅ Agent Direct Endpoints: All working perfectly!")
        
        print("\n" + "="*80)
    
    # =========================================================================
    # Run All Tests
    # =========================================================================
    def run_all_tests(self):
        """Run all test cases"""
        self.print_header("COMPREHENSIVE TEST SUITE - medical AGENT")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\nTest Configuration:")
        print(f"   Agent HTTP: {self.agent_http_url}")
        print(f"   Agent gRPC: {self.agent_grpc_url}")
        print(f"   Gateway HTTP: {self.gateway_http_url}")
        print(f"   Gateway gRPC: {self.gateway_grpc_url}")
        
        # Run tests
        self.test_agent_http_health()
        time.sleep(1)
        
        self.test_agent_http_non_stream()
        time.sleep(1)
        
        self.test_agent_http_stream()
        time.sleep(1)
        
        self.test_agent_grpc_non_stream()
        time.sleep(1)
        
        self.test_agent_grpc_stream()
        time.sleep(1)
        
        self.test_gateway_http_health()
        time.sleep(1)
        
        self.test_gateway_http_to_agent()
        time.sleep(1)
        
        self.test_gateway_grpc_to_agent()
        
        # Generate report
        self.generate_report()


if __name__ == "__main__":
    suite = ComprehensiveTestSuite()
    suite.run_all_tests()
