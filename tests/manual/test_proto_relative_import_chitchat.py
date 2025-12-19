import os


def test_medical_agents_pb2_grpc_uses_relative_import():
    proto_dir = os.path.join(os.path.dirname(__file__), os.pardir, 'agent', 'proto')
    proto_dir = os.path.normpath(proto_dir)
    stub_path = os.path.join(proto_dir, 'agents_pb2_grpc.py')
    assert os.path.exists(stub_path), f"Stub file not found: {stub_path}"
    with open(stub_path, 'r', encoding='utf-8') as f:
        content = f.read()
    assert 'from . import agents_pb2 as agents__pb2' in content, 'agents_pb2_grpc.py must import agents_pb2 relatively'

