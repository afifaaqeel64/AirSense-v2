import urllib.request
import json
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

req = urllib.request.Request(
    'https://api.github.com/repos/afifaaqeel64/AirSense-v2/actions/workflows',
    headers={'Authorization': f'Bearer {token}', 'User-Agent': 'AirSense'}
)
with urllib.request.urlopen(req) as resp:
    wf = json.loads(resp.read().decode('utf-8'))

for w in wf.get('workflows', []):
    print(f"Workflow ID: {w['id']} | Name: {w['name']} | Path: {w['path']} | State: {w['state']}")
    runs_req = urllib.request.Request(
        f"https://api.github.com/repos/afifaaqeel64/AirSense-v2/actions/workflows/{w['id']}/runs",
        headers={'Authorization': f'Bearer {token}', 'User-Agent': 'AirSense'}
    )
    with urllib.request.urlopen(runs_req) as r_resp:
        runs = json.loads(r_resp.read().decode('utf-8'))
        print(f"  Total runs: {runs.get('total_count', 0)}")
        for r in runs.get('workflow_runs', [])[:5]:
            print(f"    Run {r['id']}: {r['status']} | {r['conclusion']} | Created: {r['created_at']} | Event: {r['event']}")

# Check secrets configured in repo
sec_req = urllib.request.Request(
    'https://api.github.com/repos/afifaaqeel64/AirSense-v2/actions/secrets',
    headers={'Authorization': f'Bearer {token}', 'User-Agent': 'AirSense'}
)
try:
    with urllib.request.urlopen(sec_req) as s_resp:
        sec = json.loads(s_resp.read().decode('utf-8'))
        print("\nConfigured GitHub Action Secrets:")
        print(f"Total secrets: {sec.get('total_count', 0)}")
        for s in sec.get('secrets', []):
            print(f"  - {s['name']} (created: {s['created_at']}, updated: {s['updated_at']})")
except Exception as e:
    print(f"\nCould not fetch secrets: {e}")
