import os
import re
import sys
import json
import hashlib

sys.path.insert(0, os.path.abspath('.'))

print("=================================================================")
print("AIRSENSE-V2 FORENSIC INTEGRITY AUDIT: BRANDING & STATIC ASSETS")
print("=================================================================")

# Mode check: Development Mode
print("\n[PHASE 1: GROUND TRUTH & INTEGRITY MODE CHECK]")
print("Integrity mode from ORIGINAL_REQUEST.md: DEVELOPMENT")
print("Enforcement focus: Zero hardcoding, genuine logic, no facade implementations, zero fabricated outputs")

# 1. Binary Assets Integrity
print("\n[CHECK 1: BINARY ASSETS FORENSIC AUDIT]")
files = [
    'favicon.ico', 'favicon-16x16.png', 'favicon-32x32.png',
    'apple-touch-icon.png', 'android-chrome-192x192.png',
    'android-chrome-512x512.png', 'site.webmanifest'
]

dirs = [
    'assets/logo-files',
    'public',
    'apps/web',
    'public/assets/logo-files',
    'apps/web/assets/logo-files'
]

PNG_MAGIC = b'\x89PNG\r\n\x1a\n'
ICO_MAGIC = b'\x00\x00\x01\x00'

asset_audit_pass = True
for d in dirs:
    print(f"\nDirectory: {d}")
    for f in files:
        p = os.path.join(d, f)
        if not os.path.exists(p):
            print(f"  FAIL - Missing: {p}")
            asset_audit_pass = False
            continue
        size = os.path.getsize(p)
        if size == 0:
            print(f"  FAIL - Zero byte file: {p}")
            asset_audit_pass = False
            continue
        with open(p, 'rb') as fp:
            data = fp.read()
        sha = hashlib.sha256(data).hexdigest()[:12]
        
        magic_ok = False
        if f.endswith('.png'):
            magic_ok = data.startswith(PNG_MAGIC)
        elif f.endswith('.ico'):
            magic_ok = data.startswith(ICO_MAGIC)
        elif f.endswith('.webmanifest'):
            magic_ok = data.strip().startswith(b'{') and data.strip().endswith(b'}')
            
        if not magic_ok:
            print(f"  FAIL - Invalid magic/format: {f}")
            asset_audit_pass = False
        else:
            print(f"  PASS - {f:26} size={size:7d} B | sha={sha} | magic_ok={magic_ok}")

print(f"Result Check 1: {'PASS' if asset_audit_pass else 'FAIL'}")

# 2. HTML Files Audit
print("\n[CHECK 2: HTML HEAD & NAVBAR BRANDING AUDIT]")
html_files = [
    'index.html', 'hardware.html', 'diagnostics.html',
    'command.html', 'opensource.html', 'enterprise.html',
    'sensor-health.html'
]
html_dirs = ['public', 'apps/web']

html_audit_pass = True
for d in html_dirs:
    print(f"\nDirectory: {d}")
    for h in html_files:
        p = os.path.join(d, h)
        if not os.path.exists(p):
            print(f"  FAIL - Missing: {p}")
            html_audit_pass = False
            continue
        with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
            c = fp.read()
            
        has_fav_ico = ('/favicon.ico' in c) and ('rel="icon"' in c or "rel='icon'" in c)
        has_fav_32 = ('/favicon-32x32.png' in c) and ('32x32' in c)
        has_fav_16 = ('/favicon-16x16.png' in c) and ('16x16' in c)
        has_apple = ('/apple-touch-icon.png' in c) and ('apple-touch-icon' in c)
        has_manifest = ('/site.webmanifest' in c) and ('manifest' in c)
        
        has_brand_logo = bool(re.search(r'<img[^>]+class=[\'"][^\'"]*brand-logo[^\'"]*[\'"]', c))
        has_legacy_as = '<div class="brand-mark">AS</div>' in c
        
        head_ok = has_fav_ico and has_fav_32 and has_fav_16 and has_apple and has_manifest
        file_ok = head_ok and has_brand_logo and (not has_legacy_as)
        if not file_ok:
            html_audit_pass = False
            print(f"  FAIL - {h:20} head_ok={head_ok} brand_logo={has_brand_logo} legacy_as={has_legacy_as}")
        else:
            print(f"  PASS - {h:20} (5/5 head links present, brand-logo img verified, 0 legacy 'AS')")

print(f"Result Check 2: {'PASS' if html_audit_pass else 'FAIL'}")

# 3. FastAPI Static Mounts & Route Handlers Source Analysis
print("\n[CHECK 3: FASTAPI STATIC MOUNTS & ROUTE HANDLERS CODE AUDIT]")
main_path = 'apps/api/main.py'
with open(main_path, 'r', encoding='utf-8') as fp:
    main_code = fp.read()

has_mount_logo = "app.mount(\"/assets/logo-files\"" in main_code
has_mount_assets = "app.mount(\"/assets\"" in main_code
has_favicon_dict = "FAVICON_ROUTES" in main_code and '"/favicon.ico"' in main_code and '"/apple-touch-icon.png"' in main_code and '"/site.webmanifest"' in main_code
has_dynamic_route_registration = "app.get(route_path" in main_code
uses_fileresponse = "FileResponse(" in main_code

# Facade check: ensure route handler does not return a hardcoded dummy string or mock dict
has_dummy_string_return = 'return "favicon"' in main_code or 'return "icon"' in main_code or 'return b""' in main_code

api_audit_pass = has_mount_logo and has_mount_assets and has_favicon_dict and has_dynamic_route_registration and uses_fileresponse and (not has_dummy_string_return)

print(f"  Mount /assets/logo-files    : {'PASS' if has_mount_logo else 'FAIL'}")
print(f"  Mount /assets               : {'PASS' if has_mount_assets else 'FAIL'}")
print(f"  FAVICON_ROUTES registration : {'PASS' if has_favicon_dict else 'FAIL'}")
print(f"  app.get(route_path) binder  : {'PASS' if has_dynamic_route_registration else 'FAIL'}")
print(f"  Returns FileResponse (disk) : {'PASS' if uses_fileresponse else 'FAIL'}")
print(f"  Zero facade/dummy returns   : {'PASS' if not has_dummy_string_return else 'FAIL'}")
print(f"Result Check 3: {'PASS' if api_audit_pass else 'FAIL'}")

# 4. Live API TestClient Behavioral Verification
print("\n[CHECK 4: LIVE FASTAPI ASGI / TESTCLIENT BEHAVIORAL VERIFICATION]")
import asyncio
from httpx import AsyncClient, ASGITransport

async def run_live_api_tests():
    from apps.api.main import app
    transport = ASGITransport(app=app)
    
    endpoints = [
        ('/favicon.ico', 'image/x-icon', 15406),
        ('/favicon-16x16.png', 'image/png', 505),
        ('/favicon-32x32.png', 'image/png', 1263),
        ('/apple-touch-icon.png', 'image/png', 31835),
        ('/android-chrome-192x192.png', 'image/png', 34542),
        ('/android-chrome-512x512.png', 'image/png', 182311),
        ('/site.webmanifest', 'application/manifest+json', 384),
        ('/assets/logo-files/favicon.ico', 'image/x-icon', 15406),
        ('/assets/logo-files/apple-touch-icon.png', 'image/png', 31835),
        ('/assets/logo-files/android-chrome-192x192.png', 'image/png', 34542),
        ('/assets/logo-files/site.webmanifest', None, 384)
    ]
    
    all_ok = True
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path, exp_ct, exp_size in endpoints:
            resp = await client.get(path)
            status_ok = (resp.status_code == 200)
            len_ok = (len(resp.content) == exp_size)
            ct_ok = True
            if exp_ct:
                actual_ct = resp.headers.get('content-type', '')
                ct_ok = exp_ct in actual_ct
                
            if not (status_ok and len_ok and ct_ok):
                print(f"  FAIL - {path:40} status={resp.status_code} len={len(resp.content)} (exp {exp_size}) ct={resp.headers.get('content-type')}")
                all_ok = False
            else:
                print(f"  PASS - {path:40} status=200 len={len(resp.content):7d} B ct={resp.headers.get('content-type')}")
    return all_ok

live_client_pass = asyncio.run(run_live_api_tests())
print(f"Result Check 4: {'PASS' if live_client_pass else 'FAIL'}")

# 5. README.md Documentation Branding
print("\n[CHECK 5: README.MD DOCUMENTATION BRANDING AUDIT]")
with open('README.md', 'r', encoding='utf-8') as fp:
    readme = fp.read()

has_logo_mention = ('android-chrome-192x192.png' in readme or 'apple-touch-icon.png' in readme)
m = re.search(r'<img[^>]+src=["\']([^"\']*(?:logo|icon|android)[^"\']*)["\']', readme)
readme_path = m.group(1) if m else None
readme_path_exists = os.path.exists(readme_path) if readme_path else False

print(f"  Logo mentioned in README    : {'PASS' if has_logo_mention else 'FAIL'}")
print(f"  Relative path in README     : {readme_path}")
print(f"  Target exists on disk       : {'PASS' if readme_path_exists else 'FAIL'}")
readme_audit_pass = has_logo_mention and readme_path_exists
print(f"Result Check 5: {'PASS' if readme_audit_pass else 'FAIL'}")

# 6. Test Suite Forensic Code Analysis
print("\n[CHECK 6: TEST SUITE FORENSIC CODE ANALYSIS]")
test_file = 'tests/unit/test_branding_and_static_assets.py'
with open(test_file, 'r', encoding='utf-8') as fp:
    test_code = fp.read()

tautology_true = bool(re.search(r'\bassert\s+True\b', test_code))
tautology_1_1 = bool(re.search(r'\bassert\s+1\s*==\s*1\b', test_code))
empty_test_pattern = bool(re.search(r'def\s+test_[a-zA-Z0-9_]+\([^)]*\):\s*(?:pass|\.\.\.)', test_code))
mocking_branding = 'unittest.mock' in test_code or 'MagicMock' in test_code
real_asgi_client = 'ASGITransport(app=app)' in test_code or 'TestClient(app)' in test_code
test_count = len(re.findall(r'def\s+test_', test_code))

print(f"  Total test functions defined: {test_count}")
print(f"  Zero 'assert True'          : {'PASS' if not tautology_true else 'FAIL'}")
print(f"  Zero 'assert 1 == 1'        : {'PASS' if not tautology_1_1 else 'FAIL'}")
print(f"  Zero empty stub tests       : {'PASS' if not empty_test_pattern else 'FAIL'}")
print(f"  Zero mock shortcuts         : {'PASS' if not mocking_branding else 'FAIL'}")
print(f"  Real Live App Transport used: {'PASS' if real_asgi_client else 'FAIL'}")

test_code_pass = (not tautology_true) and (not tautology_1_1) and (not empty_test_pattern) and (not mocking_branding) and real_asgi_client and (test_count >= 10)
print(f"Result Check 6: {'PASS' if test_code_pass else 'FAIL'}")

# 7. Pre-populated Fake Log or Result Artifact Check
print("\n[CHECK 7: PRE-POPULATED ARTIFACT DETECTION]")
suspicious_artifacts = []
for root, dirs, fnames in os.walk('.'):
    # ignore .git, .venv, .agents, node_modules
    if any(ignore in root for ignore in ['.git', '.venv', 'node_modules']):
        continue
    for fname in fnames:
        if fname.endswith('.log') or 'result' in fname.lower() or 'fake' in fname.lower():
            if not fname.endswith(('.py', '.html', '.css', '.js', '.md', '.png', '.ico', '.webmanifest', '.json')):
                suspicious_artifacts.append(os.path.join(root, fname))

print(f"  Suspicious result/log artifacts found: {len(suspicious_artifacts)}")
for a in suspicious_artifacts:
    print(f"    - {a}")
artifact_check_pass = (len(suspicious_artifacts) == 0)
print(f"Result Check 7: {'PASS' if artifact_check_pass else 'FAIL'}")

# Final Verdict Calculation
all_checks = [
    ("Check 1: Binary Assets", asset_audit_pass),
    ("Check 2: HTML Branding", html_audit_pass),
    ("Check 3: FastAPI Mounts/Routes", api_audit_pass),
    ("Check 4: Live Client Responses", live_client_pass),
    ("Check 5: README Branding", readme_audit_pass),
    ("Check 6: Test Suite Quality", test_code_pass),
    ("Check 7: Artifact Detection", artifact_check_pass),
]

print("\n=================================================================")
print("FORENSIC AUDIT SUMMARY TABLE")
print("=================================================================")
all_pass = True
for name, res in all_checks:
    status_str = "PASS" if res else "FAIL"
    if not res:
        all_pass = False
    print(f"  {name:35}: {status_str}")

print("=================================================================")
if all_pass:
    print("FINAL VERDICT: CLEAN")
else:
    print("FINAL VERDICT: INTEGRITY VIOLATION")
print("=================================================================")


