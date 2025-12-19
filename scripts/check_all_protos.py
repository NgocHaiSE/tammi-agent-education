import importlib
import sys
import os
import traceback

print('RUNNING check_all_protos.py')

# Ensure repo root is on sys.path so imports work regardless of how script is invoked
_THIS_DIR = os.path.dirname(__file__)
REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, '..', '..', '..', '..'))
print('REPO_ROOT=', REPO_ROOT)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# List of agent package paths to check
AGENTS = [
    'new_backend.Sub_Agents.medical_Agent',
    'new_backend.Sub_Agents.QA_Agent',
    'new_backend.Sub_Agents.Medical_Agent',
    'new_backend.Sub_Agents.Knowledge_QA_Agent',
    'new_backend.Sub_Agents.Education_Agent',
]

errors = []
for pkg in AGENTS:
    proto_pkg = pkg + '.proto'
    try:
        print('\nChecking', pkg)
        m1 = importlib.import_module(proto_pkg + '.agents_pb2')
        m2 = importlib.import_module(proto_pkg + '.agents_pb2_grpc')
        ok1 = hasattr(m1, 'AgentRequest')
        ok2 = hasattr(m1, 'AgentResponse')
        ok3 = hasattr(m2, 'AgentServiceStub')
        ok4 = hasattr(m2, 'AgentServiceServicer')
        print(f'{pkg}: agents_pb2 AgentRequest={ok1} AgentResponse={ok2}; pb2_grpc Stub={ok3} Servicer={ok4}')
        if not (ok1 and ok2 and ok3 and ok4):
            errors.append((pkg, 'missing symbols'))
    except Exception as e:
        tb = traceback.format_exc()
        print(f'ERROR importing protos for {pkg}:', e)
        print(tb)
        errors.append((pkg, repr(e)))

if errors:
    print('\nIMPORT ERRORS:')
    for pkg, err in errors:
        print(pkg, '->', err)
    sys.exit(2)

print('\nALL PROTOS IMPORTED OK')
