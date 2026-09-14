import asyncio
import hashlib
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from httpx import AsyncClient, ASGITransport
from apps.api.main import app

LOGO_DIR = ROOT_DIR / "assets" / "logo-files"

ASSETS = [
    ("favicon.ico", "image/x-icon", ["image/x-icon", "image/vnd.microsoft.icon"]),
    ("favicon-16x16.png", "image/png", ["image/png"]),
    ("favicon-32x32.png", "image/png", ["image/png"]),
    ("apple-touch-icon.png", "image/png", ["image/png"]),
    ("android-chrome-192x192.png", "image/png", ["image/png"]),
    ("android-chrome-512x512.png", "image/png", ["image/png"]),
    ("site.webmanifest", "application/manifest+json", ["application/manifest+json", "application/json"]),
]

async def run_probes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        print("=== Independent ASGI HTTP Probe ===")
        all_passed = True
        for fname, mime, acceptable_mimes in ASSETS:
            disk_path = LOGO_DIR / fname
            disk_bytes = disk_path.read_bytes()
            disk_hash = hashlib.sha256(disk_bytes).hexdigest()

            # Probe 1: Root route (e.g., /favicon.ico)
            resp_root = await client.get(f"/{fname}")
            content_type_root = resp_root.headers.get("content-type", "").split(";")[0].strip()
            root_hash = hashlib.sha256(resp_root.content).hexdigest()
            root_ok = (
                resp_root.status_code == 200 and
                content_type_root in acceptable_mimes and
                root_hash == disk_hash
            )
            print(f"Route: /{fname:26s} | Status: {resp_root.status_code} | MIME: {content_type_root:25s} | Bytes: {len(resp_root.content):7d} | HashMatch: {root_hash == disk_hash} -> {'PASS' if root_ok else 'FAIL'}")
            if not root_ok:
                all_passed = False

            # Probe 2: Assets route (e.g., /assets/logo-files/favicon.ico)
            resp_mount = await client.get(f"/assets/logo-files/{fname}")
            content_type_mount = resp_mount.headers.get("content-type", "").split(";")[0].strip()
            mount_hash = hashlib.sha256(resp_mount.content).hexdigest()
            mount_ok = (
                resp_mount.status_code == 200 and
                mount_hash == disk_hash
            )
            print(f"Mount: /assets/logo-files/{fname:13s} | Status: {resp_mount.status_code} | MIME: {content_type_mount:25s} | Bytes: {len(resp_mount.content):7d} | HashMatch: {mount_hash == disk_hash} -> {'PASS' if mount_ok else 'FAIL'}")
            if not mount_ok:
                all_passed = False

        # Probe 3: Non-existent file returns 404
        resp_404 = await client.get("/favicon-doesnotexist.ico")
        print(f"404 Test (/favicon-doesnotexist.ico): Status {resp_404.status_code} -> {'PASS' if resp_404.status_code == 404 else 'FAIL'}")
        if resp_404.status_code != 404:
            all_passed = False

        print("\nIndependent HTTP Probe Summary:", "ALL PASS" if all_passed else "FAILURES DETECTED")

asyncio.run(run_probes())
