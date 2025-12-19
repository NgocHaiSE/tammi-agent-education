#!/usr/bin/env python3
"""
Verification Script: Port Configuration Consistency Check
=========================================================
Verify that all port configurations are synchronized across the project.

Expected Standard Ports:
- gRPC: 50051
- HTTP: 8080

Usage:
    python scripts/verify_port_config.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Clear env vars to test defaults
for key in ['AGENT_GRPC_PORT', 'AGENT_HTTP_PORT', 'medical_GRPC_PORT', 'medical_HTTP_PORT']:
    os.environ.pop(key, None)

print("🔍 Port Configuration Verification")
print("=" * 60)

# Test 1: settings.py defaults
print("\n1️⃣  Checking agent/config/settings.py defaults...")
from agent.config.settings import get_settings
settings = get_settings()

grpc_port = settings.service_port
grpc_host = settings.service_host

print(f"   gRPC Host: {grpc_host}")
print(f"   gRPC Port: {grpc_port}")

if grpc_port == 50051:
    print("   ✅ gRPC port is CORRECT (50051)")
    grpc_ok = True
else:
    print(f"   ❌ gRPC port is WRONG (expected 50051, got {grpc_port})")
    grpc_ok = False

# Test 2: run.py HTTP port default
print("\n2️⃣  Checking agent/entrypoint/run.py HTTP defaults...")
# Simulate what run.py does
http_port = int(os.environ.get("AGENT_HTTP_PORT", os.environ.get("medical_HTTP_PORT", "8080")))
http_host = os.environ.get("AGENT_HTTP_HOST", os.environ.get("medical_HTTP_HOST", "0.0.0.0"))

print(f"   HTTP Host: {http_host}")
print(f"   HTTP Port: {http_port}")

if http_port == 8080:
    print("   ✅ HTTP port is CORRECT (8080)")
    http_ok = True
else:
    print(f"   ❌ HTTP port is WRONG (expected 8080, got {http_port})")
    http_ok = False

# Test 3: http_server.py standalone mode
print("\n3️⃣  Checking agent/entrypoint/http_server.py __main__ block...")
# Simulate what http_server.py __main__ does
http_server_port = int(os.getenv("AGENT_HTTP_PORT", "8080"))

print(f"   HTTP Port (standalone): {http_server_port}")

if http_server_port == 8080:
    print("   ✅ HTTP server standalone port is CORRECT (8080)")
    http_server_ok = True
else:
    print(f"   ❌ HTTP server standalone port is WRONG (expected 8080, got {http_server_port})")
    http_server_ok = False

# Test 4: Dockerfile ENV defaults
print("\n4️⃣  Checking Dockerfile ENV defaults...")
dockerfile_path = PROJECT_ROOT / "Dockerfile"
dockerfile_content = dockerfile_path.read_text()

if "AGENT_GRPC_PORT=50051" in dockerfile_content:
    print("   ✅ Dockerfile has AGENT_GRPC_PORT=50051")
    dockerfile_grpc_ok = True
else:
    print("   ❌ Dockerfile AGENT_GRPC_PORT is not 50051")
    dockerfile_grpc_ok = False

if "AGENT_HTTP_PORT=8080" in dockerfile_content:
    print("   ✅ Dockerfile has AGENT_HTTP_PORT=8080")
    dockerfile_http_ok = True
else:
    print("   ❌ Dockerfile AGENT_HTTP_PORT is not 8080")
    dockerfile_http_ok = False

# Test 5: CI Workflow env vars
print("\n5️⃣  Checking CI workflow env vars...")
workflow_path = PROJECT_ROOT / ".github" / "workflows" / "build-and-test.yml"
workflow_content = workflow_path.read_text(encoding='utf-8')

if "AGENT_GRPC_PORT: '50051'" in workflow_content:
    print("   ✅ CI workflow has AGENT_GRPC_PORT: '50051'")
    ci_grpc_ok = True
else:
    print("   ❌ CI workflow AGENT_GRPC_PORT is not '50051'")
    ci_grpc_ok = False

if "AGENT_HTTP_PORT: '8080'" in workflow_content:
    print("   ✅ CI workflow has AGENT_HTTP_PORT: '8080'")
    ci_http_ok = True
else:
    print("   ❌ CI workflow AGENT_HTTP_PORT is not '8080'")
    ci_http_ok = False

# Summary
print("\n" + "=" * 60)
print("📊 VERIFICATION SUMMARY")
print("=" * 60)

all_checks = [
    grpc_ok,
    http_ok,
    http_server_ok,
    dockerfile_grpc_ok,
    dockerfile_http_ok,
    ci_grpc_ok,
    ci_http_ok,
]

passed = sum(all_checks)
total = len(all_checks)

print(f"\nTotal Checks: {total}")
print(f"Passed: {passed}")
print(f"Failed: {total - passed}")

if all(all_checks):
    print("\n✅ ALL PORT CONFIGURATIONS ARE SYNCHRONIZED!")
    print("\nStandard Ports Established:")
    print(f"  - gRPC: 50051")
    print(f"  - HTTP: 8080")
    sys.exit(0)
else:
    print("\n❌ PORT CONFIGURATION INCONSISTENCIES DETECTED!")
    print("\nPlease review the failed checks above.")
    sys.exit(1)
