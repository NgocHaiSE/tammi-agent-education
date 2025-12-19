#!/usr/bin/env python3
"""
Script to reorganize test files into proper directories.

Test categorization:
- unit/: Fast unit tests with mocked dependencies
- integration/: Integration tests (graph, grpc, http, llm)
- e2e/: End-to-end tests with running servers
- external/: Tests requiring external APIs
- manual/: Debug and manual test scripts
"""

import shutil
from pathlib import Path

# Test file categorization
TEST_CATEGORIES = {
    # Unit tests - fast, mocked
    'unit': [
        'test_medical_service.py',
        'test_router_mapping.py',
        'test_graph_builder_refactored.py',
        'test_llm_config_service.py',
        'test_refactor_imports.py',
    ],
    
    # Integration tests - components working together
    'integration/grpc': [
        'test_integration_grpc.py',
        'test_integration_grpc_stream.py',
        'test_grpc_async_fix.py',
        'test_grpc_client.py',
        'test_grpc_endpoints.py',
        'test_agent_grpc.py',
        'test_gateway_grpc.py',
        'smoke_test_grpc_async_fix.py',
    ],
    
    'integration/http': [
        'test_integration_http_stream.py',
        'test_sse_stream.py',
    ],
    
    'integration/graph': [
        'test_graph_direct.py',
    ],
    
    'integration/llm': [
        'test_llm_direct.py',
        'test_simple_invoke.py',
    ],
    
    # E2E tests - full system with running servers
    'e2e': [
        'test_both_modes.py',
        'comprehensive_test.py',
        'final_complete_test.py',
    ],
    
    # External API tests
    'external': [
        # Add external API tests here if any
    ],
    
    # Manual/debug scripts
    'manual': [
        'check_env.py',
        'debug_test.py',
        'quick_health_check.py',
        'quick_llm_test.py',
        'quick_test_all.py',
        'simple_focused_test.py',
        'simple_ollama_test.py',
        'test_deep_inspect.py',
        'test_emotional_flow.py',
        'test_env_debug.py',
        'test_fresh_client.py',
        'test_inspect_client.py',
        'test_langchain_env.py',
        'test_llm_flow_debug.py',
        'test_llm_invoke_debug.py',
        'test_proto_relative_import.py',
        'test_proto_relative_import_medical.py',
        'test_stream_generator.py',
        'test_weekend_idea.py',
    ],
}

# Files to keep in tests/ root
ROOT_FILES = [
    'conftest.py',
    'test_http_request.json',
    'test_http_stream.json',
]


def reorganize_tests():
    """Reorganize test files into proper directory structure."""
    tests_dir = Path(__file__).resolve().parents[1] / 'tests'
    
    print(f"📁 Reorganizing tests in: {tests_dir}")
    print()
    
    moved_count = 0
    skipped_count = 0
    
    for category, files in TEST_CATEGORIES.items():
        # Create target directory
        if '/' in category:
            target_dir = tests_dir / category.replace('/', '\\')
        else:
            target_dir = tests_dir / category
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
        for filename in files:
            source = tests_dir / filename
            target = target_dir / filename
            
            if source.exists():
                if not target.exists():
                    print(f"  Moving: {filename}")
                    print(f"    From: tests/")
                    print(f"    To:   tests/{category}/")
                    shutil.move(str(source), str(target))
                    moved_count += 1
                else:
                    print(f"  ⚠️  Skipping {filename} (already exists in target)")
                    skipped_count += 1
            else:
                print(f"  ⚠️  File not found: {filename}")
                skipped_count += 1
        
        print()
    
    print(f"✅ Reorganization complete!")
    print(f"   Moved: {moved_count} files")
    print(f"   Skipped: {skipped_count} files")
    print()
    
    # Print remaining files in tests/
    remaining = [f for f in tests_dir.glob('*.py') if f.name not in ROOT_FILES]
    if remaining:
        print("📋 Remaining test files in tests/ (may need manual categorization):")
        for f in remaining:
            print(f"   - {f.name}")
    else:
        print("✅ All test files have been categorized!")


if __name__ == '__main__':
    reorganize_tests()
