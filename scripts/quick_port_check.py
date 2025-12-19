#!/usr/bin/env python3
"""
Quick Port Config Check - No module imports
"""
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

print("🔍 Port Configuration Quick Check")
print("=" * 60)

checks = []

# Check 1: settings.py
print("\n1️⃣  agent/config/settings.py")
settings_content = (PROJECT_ROOT / "agent/config/settings.py").read_text(encoding='utf-8')
match = re.search(r'service_port.*?medical_GRPC_PORT",\s*"(\d+)"', settings_content, re.DOTALL)
if match:
    port = match.group(1)
    print(f"   gRPC default: {port}")
    if port == "50051":
        print("   ✅ CORRECT")
        checks.append(True)
    else:
        print(f"   ❌ WRONG (expected 50051)")
        checks.append(False)

# Check 2: run.py
print("\n2️⃣  agent/entrypoint/run.py")
run_content = (PROJECT_ROOT / "agent/entrypoint/run.py").read_text(encoding='utf-8')
match = re.search(r'medical_HTTP_PORT",\s*"(\d+)"', run_content)
if match:
    port = match.group(1)
    print(f"   HTTP default: {port}")
    if port == "8080":
        print("   ✅ CORRECT")
        checks.append(True)
    else:
        print(f"   ❌ WRONG (expected 8080)")
        checks.append(False)

# Check 3: Dockerfile
print("\n3️⃣  Dockerfile")
dockerfile_content = (PROJECT_ROOT / "Dockerfile").read_text(encoding='utf-8')
if "AGENT_GRPC_PORT=50051" in dockerfile_content and "AGENT_HTTP_PORT=8080" in dockerfile_content:
    print("   ✅ gRPC=50051, HTTP=8080")
    checks.append(True)
else:
    print("   ❌ Incorrect port values")
    checks.append(False)

# Check 4: CI Workflow
print("\n4️⃣  .github/workflows/build-and-test.yml")
workflow_content = (PROJECT_ROOT / ".github/workflows/build-and-test.yml").read_text(encoding='utf-8')
if "AGENT_GRPC_PORT: '50051'" in workflow_content and "AGENT_HTTP_PORT: '8080'" in workflow_content:
    print("   ✅ gRPC='50051', HTTP='8080'")
    checks.append(True)
else:
    print("   ❌ Incorrect port values")
    checks.append(False)

print("\n" + "=" * 60)
if all(checks):
    print("✅ ALL CHECKS PASSED - Ports are synchronized!")
    exit(0)
else:
    print("❌ Some checks failed")
    exit(1)
