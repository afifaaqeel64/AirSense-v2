import urllib.request
import json
import time
import sys
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

# Workflow 355748443 is daily_backup_sync.yml
workflow_id = 355748443
dispatch_url = f"https://api.github.com/repos/afifaaqeel64/AirSense-v2/actions/workflows/{workflow_id}/dispatches"
target_date = sys.argv[1] if len(sys.argv) > 1 else "2026-09-13"
payload = json.dumps({
    "ref": "main",
    "inputs": {
        "date": target_date
    }
}).encode('utf-8')

req = urllib.request.Request(dispatch_url, data=payload, headers=headers, method='POST')
try:
    with urllib.request.urlopen(req) as resp:
        print(f"Triggered workflow_dispatch: HTTP {resp.status}")
except Exception as e:
    print(f"Failed to dispatch workflow: {e}")
    sys.exit(1)

print("Waiting for workflow run to register...")
time.sleep(6)

runs_url = f"https://api.github.com/repos/afifaaqeel64/AirSense-v2/actions/workflows/{workflow_id}/runs?per_page=5"
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

print("\nFetching job logs...")
jobs_url = f"https://api.github.com/repos/afifaaqeel64/AirSense-v2/actions/runs/{latest_run_id}/jobs"
req = urllib.request.Request(jobs_url, headers=headers)
with urllib.request.urlopen(req) as resp:
    jobs_data = json.loads(resp.read().decode('utf-8'))

job_id = None
for job in jobs_data.get('jobs', []):
    job_id = job['id']
    print(f"\nJob {job_id} ({job['name']}) steps:")
    for step in job.get('steps', []):
        print(f"  Step: {step['name']} | Conclusion: {step.get('conclusion')} | Status: {step.get('status')}")

if job_id:
    print("\nFetching step log...")
    log_url = f"https://api.github.com/repos/afifaaqeel64/AirSense-v2/actions/jobs/{job_id}/logs"
    req = urllib.request.Request(log_url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            raw_logs = resp.read().decode('utf-8', errors='replace')
            print("\n--- JOB LOG HIGHLIGHTS ---")
            lines = raw_logs.splitlines()
            for l in lines:
                if any(k in l.lower() for k in ["telegram", "airsense_daily", "backup", "csv", "querying", "404", "400", "403", "200"]):
                    print(l)
            print("--- JOB LOG END ---")
    except Exception as e:
        print(f"Could not fetch raw logs directly: {e}")
