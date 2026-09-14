import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import urllib.request
import zipfile
import io
import scripts.check_workflows as cw

run_id = 34689794737
req = urllib.request.Request(
    f'https://api.github.com/repos/afifaaqeel64/AirSense-v2/actions/runs/{run_id}/logs',
    headers={'Authorization': f'Bearer {cw.token}', 'User-Agent': 'AirSense'}
)

resp = urllib.request.urlopen(req)
z = zipfile.ZipFile(io.BytesIO(resp.read()))
log_dir = Path("run_logs")
log_dir.mkdir(exist_ok=True)

for name in z.namelist():
    clean_name = name.replace("/", "_").replace("\\", "_")
    target_path = log_dir / clean_name
    target_path.write_bytes(z.read(name))
    print(f"Extracted: {clean_name}")

print("Extraction done.")
