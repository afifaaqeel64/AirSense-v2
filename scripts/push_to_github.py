import subprocess
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
    raise RuntimeError("Could not retrieve GitHub token from Windows Credential Manager")

git_exe = r"C:\Users\HP\AppData\Local\GitHubDesktop\app-3.6.4\resources\app\git\cmd\git.exe"
remote_url = f"https://x-access-token:{token}@github.com/afifaaqeel64/AirSense-v2.git"

print("Pushing commit to GitHub...")
result = subprocess.run([git_exe, "push", remote_url, "main"], capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)
