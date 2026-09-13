import urllib.request
import json
import time
import sys
import zipfile
import io
import ctypes
import ctypes.wintypes

advapi32 = ctypes.windll.advapi32

class CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ('Flags', ctypes.wintypes.DWORD),
        ('Type', ctypes.wintypes.DWORD),
        ('TargetName', ctypes.wintypes.LPWSTR),
        ('Comment', ctypes.wintypes.LPWSTR),
        ('LastWritten', ctypes.wintypes.FILETIME),
        ('CredentialBlobSize', ctypes.wintypes.DWORD),
        ('CredentialBlob', ctypes.POINTER(ctypes.c_byte)),
        ('Persist', ctypes.wintypes.DWORD),
        ('AttributeCount', ctypes.wintypes.DWORD),
        ('Attributes', ctypes.c_void_p),
        ('TargetAlias', ctypes.wintypes.LPWSTR),
        ('UserName', ctypes.wintypes.LPWSTR),
    ]

target = 'LegacyGeneric:target=GitHub - https://api.github.com/afifaaqeel64'
pcred = ctypes.POINTER(CREDENTIAL)()
token = ''
if advapi32.CredReadW(target, 1, 0, ctypes.byref(pcred)):
    token = ctypes.string_at(pcred.contents.CredentialBlob, pcred.contents.CredentialBlobSize).decode('utf-8')

if not token:
    print("Could not retrieve GitHub token.")
    sys.exit(1)

headers = {
    'Authorization': f'Bearer {token}',
    'User-Agent': 'AirSense',
    'Accept': 'application/vnd.github+json'
}

dispatch_url = "https://api.github.com/repos/afifaaqeel64/AirSense-v2/actions/workflows/send_announcement.yml/dispatches"
payload = json.dumps({
    "ref": "main",
    "inputs": {}
}).encode('utf-8')

req = urllib.request.Request(dispatch_url, data=payload, headers=headers, method='POST')
try:
    with urllib.request.urlopen(req) as resp:
        print(f"Triggered send_announcement workflow_dispatch: HTTP {resp.status}")
except Exception as e:
    print(f"Failed to dispatch workflow: {e}")
    sys.exit(1)

print("Waiting for workflow run to register...")
time.sleep(6)

runs_url = "https://api.github.com/repos/afifaaqeel64/AirSense-v2/actions/workflows/send_announcement.yml/runs?per_page=5"
latest_run_id = None
for _ in range(10):
    req = urllib.request.Request(runs_url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        runs = data.get('workflow_runs', [])
        if runs:
            latest_run_id = runs[0]['id']
            print(f"Latest run ID: {latest_run_id} | Status: {runs[0]['status']} | Event: {runs[0]['event']} | Created: {runs[0]['created_at']}")
            break
    time.sleep(3)

if not latest_run_id:
    print("No runs found.")
    sys.exit(1)

print(f"\nMonitoring Run {latest_run_id}...")
for attempt in range(40):
    run_url = f"https://api.github.com/repos/afifaaqeel64/AirSense-v2/actions/runs/{latest_run_id}"
    req = urllib.request.Request(run_url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        run = json.loads(resp.read().decode('utf-8'))
        status = run.get('status')
        conclusion = run.get('conclusion')
        print(f"[{attempt+1}] Run {latest_run_id}: status={status}, conclusion={conclusion}")
        if status == 'completed':
            break
    time.sleep(5)

print("\nFetching step log...")
logs_url = f"https://api.github.com/repos/afifaaqeel64/AirSense-v2/actions/runs/{latest_run_id}/logs"
try:
    req = urllib.request.Request(logs_url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        z = zipfile.ZipFile(io.BytesIO(resp.read()))
        for name in z.namelist():
            if "Send" in name or "Dispatch" in name or "0_" in name:
                print(f"=== {name} ===")
                content = z.read(name).decode('utf-8', errors='replace')
                for line in content.splitlines():
                    if any(k in line for k in ["EMAIL", "Attached", "recipient", "SUCCESS", "FAILURE"]):
                        print(line)
except Exception as e:
    print(f"Could not fetch logs: {e}")
