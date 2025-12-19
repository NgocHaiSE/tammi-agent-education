#!/usr/bin/env python3
"""
Convenience script to generate proto stubs.

This is a wrapper around agent/proto/generate_stubs.py for easier access.

Usage:
    python scripts/generate_proto.py
    
Or from project root:
    python -m scripts.generate_proto
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import and run the actual generator
from agent.proto.generate_stubs import main

if __name__ == "__main__":
    sys.exit(main())
