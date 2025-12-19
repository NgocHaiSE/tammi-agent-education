import subprocess
import sys
from pathlib import Path

pidfile = Path(__file__).parent / 'medical.pid'
entry = Path(__file__).parent.parent / 'entrypoint' / 'grpc_server.py'

p = subprocess.Popen([sys.executable, str(entry)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
pidfile.write_text(str(p.pid))
print(f"Started medical server pid={p.pid}, pidfile={pidfile}")
try:
    p.wait()
finally:
    if pidfile.exists():
        pidfile.unlink()

