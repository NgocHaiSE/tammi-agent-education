import sys

try:
    from agent.proto import agents_pb2, agents_pb2_grpc
    print('OK: imported agents_pb2 and agents_pb2_grpc')
    print('AgentRequest exists:', hasattr(agents_pb2, 'AgentRequest'))
    print('AgentResponse exists:', hasattr(agents_pb2, 'AgentResponse'))
    print('AgentServiceStub exists:', hasattr(agents_pb2_grpc, 'AgentServiceStub'))
    print('AgentServiceServicer exists:', hasattr(agents_pb2_grpc, 'AgentServiceServicer'))
except Exception as e:
    print('IMPORT ERROR (proto):', e)
    sys.exit(2)

# Also check combined entrypoint runner can be imported
try:
    from agent.entrypoint import run
    print('OK: imported entrypoint.run')
except Exception as e:
    print('IMPORT ERROR (entrypoint.run):', e)
    sys.exit(3)
