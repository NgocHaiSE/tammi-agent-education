"""
Quick health check for all components
"""
import httpx
import grpc
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.proto import agents_pb2_grpc

print("="*80)
print("QUICK HEALTH CHECK - ALL COMPONENTS")
print("="*80)

# Check 1: Agent HTTP
print("\n1️⃣  Agent HTTP (port 8001)...")
try:
    resp = httpx.get("http://localhost:8001/management/health", timeout=3)
    if resp.status_code == 200:
        print(f"   ✅ RUNNING - {resp.json()}")
    else:
        print(f"   ❌ Error: {resp.status_code}")
except Exception as e:
    print(f"   ❌ NOT ACCESSIBLE: {e}")

# Check 2: Agent gRPC  
print("\n2️⃣  Agent gRPC (port 50052)...")
try:
    channel = grpc.insecure_channel('localhost:50052')
    grpc.channel_ready_future(channel).result(timeout=3)
    print(f"   ✅ RUNNING and CONNECTED")
    channel.close()
except Exception as e:
    print(f"   ❌ NOT ACCESSIBLE: {e}")

# Check 3: Gateway HTTP
print("\n3️⃣  Gateway HTTP (port 8000)...")
try:
    resp = httpx.get("http://localhost:8000/management/health", timeout=3)
    print(f"   ✅ RUNNING - Status {resp.status_code}")
except Exception as e:
    print(f"   ❌ NOT ACCESSIBLE: {e}")

# Check 4: Gateway gRPC
print("\n4️⃣  Gateway gRPC (port 50051)...")
try:
    channel = grpc.insecure_channel('localhost:50051')
    grpc.channel_ready_future(channel).result(timeout=3)
    print(f"   ✅ RUNNING and CONNECTED")
    channel.close()
except Exception as e:
    print(f"   ❌ NOT ACCESSIBLE: {e}")

# Check 5: Ollama
print("\n5️⃣  Ollama (port 11434)...")
try:
    resp = httpx.get("http://localhost:11434/api/tags", timeout=3)
    if resp.status_code == 200:
        models = resp.json().get('models', [])
        print(f"   ✅ RUNNING - {len(models)} models available")
        for m in models:
            print(f"      - {m.get('name')}")
    else:
        print(f"   ❌ Error: {resp.status_code}")
except Exception as e:
    print(f"   ❌ NOT ACCESSIBLE: {e}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("✅ = Component is running and accessible")
print("❌ = Component is not accessible or has errors")
print("\n📝 Note: All services should be ✅ for full functionality")
print("="*80)
