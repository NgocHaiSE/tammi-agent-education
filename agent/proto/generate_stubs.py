#!/usr/bin/env python3
"""Generate Python gRPC stubs from .proto files.

Run this script from the project root:
    python agent/proto/generate_stubs.py

It will regenerate protobuf and gRPC stubs and ensure generated imports are
relative so they work in different execution environments.
"""

import re
import subprocess
import sys
from pathlib import Path


def fix_grpc_imports(grpc_file: Path) -> None:
    """Ensure generated *_grpc.py uses relative imports for pb2 modules."""
    if not grpc_file.exists():
        return

    content = grpc_file.read_text(encoding="utf-8")
    pattern = r"from agent\.proto import (\w+_pb2)"
    replacement = r"from . import \1"
    new_content = re.sub(pattern, replacement, content)

    if new_content != content:
        grpc_file.write_text(new_content, encoding="utf-8")
        print(f"   OK. Fixed imports in {grpc_file.name} (relative imports)")


def main() -> int:
    proto_dir = Path(__file__).parent
    workspace_root = proto_dir.parent.parent

    proto_files = [
        "agents.proto",
    ]

    print("=" * 80)
    print("Generating gRPC stubs from proto files")
    print("=" * 80)
    print(f"Proto directory: {proto_dir}")
    print(f"Workspace root: {workspace_root}")
    print()

    success_count = 0
    error_count = 0

    for proto_file in proto_files:
        proto_path = proto_dir / proto_file

        if not proto_path.exists():
            print(f"SKIP: {proto_file} (not found)")
            continue

        print(f"Processing {proto_file}...")

        cmd = [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            f"--proto_path={workspace_root.as_posix()}",
            f"--python_out={workspace_root.as_posix()}",
            f"--grpc_python_out={workspace_root.as_posix()}",
            f"--pyi_out={workspace_root.as_posix()}",
            proto_path.relative_to(workspace_root).as_posix(),
        ]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"   OK. Generated stubs for {proto_file}")
            if result.stdout:
                print(f"   Output: {result.stdout}")

            proto_name = proto_file.replace(".proto", "")
            grpc_file = proto_dir / f"{proto_name}_pb2_grpc.py"
            fix_grpc_imports(grpc_file)
            success_count += 1

        except subprocess.CalledProcessError as e:
            print(f"   FAIL: Failed to generate stubs for {proto_file}")
            print(f"   Error: {e.stderr}")
            error_count += 1

        print()

    print("=" * 80)
    if error_count == 0:
        print(f"All stubs generated successfully ({success_count} files)")
        print("=" * 80)
        return 0

    print(
        f"Completed with errors: {success_count} succeeded, {error_count} failed"
    )
    print("=" * 80)
    return 1


if __name__ == "__main__":
    sys.exit(main())
