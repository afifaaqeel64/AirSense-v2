import sys
import urllib.request
import json
import zipfile
import io
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts.check_workflows as cw

# Get jobs for the run
req = urllib.request.Request(
    'https://api.github.com/repos/afifaaqeel64/AirSense-v2/actions/runs/34649559025/jobs',
    headers={'Authorization': f'Bearer {cw.token}', 'User-Agent': 'AirSense'}
)
with urllib.request.urlopen(req) as resp:
    jobs = json.loads(resp.read().decode('utf-8'))

for j in jobs.get('jobs', []):
    print(f"Job: {j['name']} | Status: {j['status']} | Conclusion: {j['conclusion']}")
    for s in j.get('steps', []):
        print(f"  Step: {s['name']} | Status: {s['status']} | Conclusion: {s['conclusion']}")

# Download logs
log_req = urllib.request.Request(
    'https://api.github.com/repos/afifaaqeel64/AirSense-v2/actions/runs/34649559025/logs',
    headers={'Authorization': f'Bearer {cw.token}', 'User-Agent': 'AirSense'}
)
try:
    with urllib.request.urlopen(log_req) as resp:
        z = zipfile.ZipFile(io.BytesIO(resp.read()))
        for name in z.namelist():
            print(f"\n--- Log file: {name} ---")
            content = z.read(name).decode('utf-8', 'replace')
            for line in content.splitlines():
                if any(k in line.lower() for k in ['telegram', 'backup', 'error', 'warning', 'skipped', 'sent', 'csv', 'python']):
                    print(line[:140])
except Exception as e:
    print(f"Error downloading logs: {e}")
