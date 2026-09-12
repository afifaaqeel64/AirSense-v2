"""Adversarial stress-test and empirical challenge suite for AirSense branding,
HTTP static routes, asset availability, byte integrity, edge cases, and HTML link consistency.
"""

import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

from apps.api.main import app

ROOT_DIR = Path(__file__).resolve().parent.parent

BRANDING_ASSET_NAMES = [
    "favicon.ico",
    "favicon-16x16.png",
    "favicon-32x32.png",
    "apple-touch-icon.png",
    "android-chrome-192x192.png",
    "android-chrome-512x512.png",
    "site.webmanifest",
]

EXPECTED_CONTENT_TYPES = {
    "favicon.ico": ["image/x-icon", "image/vnd.microsoft.icon"],
    "favicon-16x16.png": ["image/png"],
    "favicon-32x32.png": ["image/png"],
    "apple-touch-icon.png": ["image/png"],
    "android-chrome-192x192.png": ["image/png"],
    "android-chrome-512x512.png": ["image/png"],
    "site.webmanifest": ["application/manifest+json", "application/json"],
}

ALL_HTML_FILES = [
    # 7 primary public/ files
    ROOT_DIR / "public" / "index.html",
    ROOT_DIR / "public" / "hardware.html",
    ROOT_DIR / "public" / "diagnostics.html",
    ROOT_DIR / "public" / "command.html",
    ROOT_DIR / "public" / "opensource.html",
    ROOT_DIR / "public" / "enterprise.html",
    ROOT_DIR / "public" / "sensor-health.html",
    # 7 primary apps/web/ files
    ROOT_DIR / "apps" / "web" / "index.html",
    ROOT_DIR / "apps" / "web" / "hardware.html",
    ROOT_DIR / "apps" / "web" / "diagnostics.html",
    ROOT_DIR / "apps" / "web" / "command.html",
    ROOT_DIR / "apps" / "web" / "opensource.html",
    ROOT_DIR / "apps" / "web" / "enterprise.html",
    ROOT_DIR / "apps" / "web" / "sensor-health.html",
]

SUPPLEMENTAL_HTML_FILES = [
    ROOT_DIR / "public" / "command_center.html",
    ROOT_DIR / "apps" / "web" / "command_center.html",
    ROOT_DIR / "apps" / "web" / "hardware_dashboard.html",
    ROOT_DIR / "apps" / "web" / "opensource_dashboard.html",
    ROOT_DIR / "apps" / "web" / "diagnostics_dashboard.html",
    ROOT_DIR / "apps" / "web_enterprise" / "index.html",
]


class TestEmpiricalAssetIntegrityOnDisk:
    """Empirically inspects file sizes, hashes, and parity across directories."""

    @pytest.mark.parametrize("asset_name", BRANDING_ASSET_NAMES)
    def test_disk_asset_byte_level_parity(self, asset_name: str):
        src_file = ROOT_DIR / "assets" / "logo-files" / asset_name
        assert src_file.exists(), f"Missing source file: {src_file}"
        src_bytes = src_file.read_bytes()
        src_hash = hashlib.sha256(src_bytes).hexdigest()
        assert len(src_bytes) > 0, f"Source asset {asset_name} is 0 bytes"

        # Check in public/
        pub_file = ROOT_DIR / "public" / asset_name
        assert pub_file.exists(), f"Missing in public/: {asset_name}"
        assert hashlib.sha256(pub_file.read_bytes()).hexdigest() == src_hash, (
            f"Hash mismatch in public/{asset_name}"
        )

        # Check in apps/web/
        web_file = ROOT_DIR / "apps" / "web" / asset_name
        assert web_file.exists(), f"Missing in apps/web/: {asset_name}"
        assert hashlib.sha256(web_file.read_bytes()).hexdigest() == src_hash, (
            f"Hash mismatch in apps/web/{asset_name}"
        )


class TestEmpiricalFastApiEndpoints:
    """Stress tests FastAPI route responses at / and /assets/logo-files/."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("asset_name", BRANDING_ASSET_NAMES)
    async def test_root_endpoints_get_status_type_and_payload(self, asset_name: str):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/{asset_name}")
            assert resp.status_code == 200, f"GET /{asset_name} returned status {resp.status_code}"
            assert len(resp.content) > 0, f"GET /{asset_name} returned empty body"

            # Check content-type header
            ct = resp.headers.get("content-type", "")
            valid_types = EXPECTED_CONTENT_TYPES[asset_name]
            assert any(vt in ct for vt in valid_types), (
                f"GET /{asset_name} returned unexpected content-type '{ct}', expected one of {valid_types}"
            )

            # Byte parity with disk file
            disk_bytes = (ROOT_DIR / "assets" / "logo-files" / asset_name).read_bytes()
            assert resp.content == disk_bytes, f"GET /{asset_name} content does not match disk file"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("asset_name", BRANDING_ASSET_NAMES)
    async def test_assets_logo_files_endpoints_get_status_type_and_payload(self, asset_name: str):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/assets/logo-files/{asset_name}")
            assert resp.status_code == 200, f"GET /assets/logo-files/{asset_name} returned {resp.status_code}"
            assert len(resp.content) > 0

            # Check content-type header
            ct = resp.headers.get("content-type", "")
            valid_types = EXPECTED_CONTENT_TYPES[asset_name]
            assert any(vt in ct for vt in valid_types), (
                f"GET /assets/logo-files/{asset_name} returned '{ct}', expected {valid_types}"
            )

            # Byte parity
            disk_bytes = (ROOT_DIR / "assets" / "logo-files" / asset_name).read_bytes()
            assert resp.content == disk_bytes, f"GET /assets/logo-files/{asset_name} body mismatch"


class TestAdversarialEdgeCasesAndErrorHandling:
    """Stress tests 404s, unsupported methods, path traversal, and cache busting."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalid_path",
        [
            "/favicon-fake.ico",
            "/favicon-999x999.png",
            "/fake-manifest.webmanifest",
            "/apple-touch-icon-120x120.png",
            "/assets/logo-files/nonexistent-icon.png",
            "/assets/logo-files/fake.ico",
            "/assets/logo-files/secret.env",
        ],
    )
    async def test_invalid_assets_return_http_404(self, invalid_path: str):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(invalid_path)
            assert resp.status_code == 404, (
                f"Expected 404 for invalid asset {invalid_path}, got {resp.status_code}"
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("asset_name", ["favicon.ico", "site.webmanifest"])
    async def test_post_on_static_asset_returns_405(self, asset_name: str):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(f"/{asset_name}")
            assert resp.status_code == 405, (
                f"Expected 405 Method Not Allowed for POST /{asset_name}, got {resp.status_code}"
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("asset_name", ["favicon.ico", "apple-touch-icon.png", "site.webmanifest"])
    async def test_head_request_on_mounted_static_assets(self, asset_name: str):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.head(f"/assets/logo-files/{asset_name}")
            assert resp.status_code == 200, f"HEAD /assets/logo-files/{asset_name} returned {resp.status_code}"
            assert len(resp.content) == 0, f"HEAD response body should be empty, got {len(resp.content)} bytes"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("asset_name", ["favicon.ico", "apple-touch-icon.png", "site.webmanifest"])
    async def test_head_request_on_root_fastapi_endpoints(self, asset_name: str):
        """Root routes registered with app.get() return 405 for HEAD under Starlette/FastAPI."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.head(f"/{asset_name}")
            assert resp.status_code == 405, (
                f"Expected 405 for HEAD /{asset_name} on app.get() route, got {resp.status_code}"
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("asset_name", ["favicon.ico", "site.webmanifest"])
    async def test_cache_busting_query_params(self, asset_name: str):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/{asset_name}?v=20260912&build=final")
            assert resp.status_code == 200
            assert len(resp.content) > 0

    @pytest.mark.asyncio
    async def test_path_traversal_protection(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/assets/logo-files/../../apps/api/main.py")
            assert resp.status_code in [400, 404], (
                f"Path traversal check should return 400/404, got {resp.status_code}"
            )


class HeadAndBodyParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.imgs = []

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        if tag == "link":
            self.links.append(attr_dict)
        elif tag == "img":
            self.imgs.append(attr_dict)


class TestHtmlDocumentLinkVerification:
    """Validates that all 14 specified HTML files (and 6 supplemental HTML files)
    contain complete favicon suite tags and valid, non-broken asset references."""

    @pytest.mark.parametrize("html_path", ALL_HTML_FILES)
    def test_all_14_html_files_contain_complete_branding_tags(self, html_path: Path):
        assert html_path.exists(), f"Target HTML file does not exist: {html_path}"
        html_content = html_path.read_text(encoding="utf-8")
        parser = HeadAndBodyParser()
        parser.feed(html_content)

        # 1. Verify link tags in <head>
        icon_hrefs = [l.get("href") for l in parser.links if "icon" in l.get("rel", "")]
        assert "/favicon.ico" in icon_hrefs, f"{html_path.name} missing /favicon.ico"
        assert "/favicon-32x32.png" in icon_hrefs, f"{html_path.name} missing /favicon-32x32.png"
        assert "/favicon-16x16.png" in icon_hrefs, f"{html_path.name} missing /favicon-16x16.png"

        # 2. Verify apple-touch-icon
        apple_hrefs = [l.get("href") for l in parser.links if "apple-touch-icon" in l.get("rel", "")]
        assert "/apple-touch-icon.png" in apple_hrefs, f"{html_path.name} missing /apple-touch-icon.png"

        # 3. Verify manifest
        manifest_hrefs = [l.get("href") for l in parser.links if "manifest" in l.get("rel", "")]
        assert "/site.webmanifest" in manifest_hrefs, f"{html_path.name} missing /site.webmanifest"

        # 4. Verify logo img tag
        logo_imgs = [img for img in parser.imgs if "brand-logo" in img.get("class", "")]
        assert len(logo_imgs) > 0, f"{html_path.name} has no img.brand-logo"
        logo_src = logo_imgs[0].get("src")
        assert logo_src in ["/apple-touch-icon.png", "/android-chrome-192x192.png"], (
            f"Unexpected logo src '{logo_src}' in {html_path.name}"
        )

        # 5. Verify absence of legacy placeholder
        assert '<div class="brand-mark">AS</div>' not in html_content, (
            f"Found legacy placeholder <div class=\"brand-mark\">AS</div> in {html_path.name}"
        )

    @pytest.mark.parametrize("html_path", SUPPLEMENTAL_HTML_FILES)
    def test_supplemental_html_files_contain_branding_tags(self, html_path: Path):
        assert html_path.exists(), f"Supplemental HTML file missing: {html_path}"
        html_content = html_path.read_text(encoding="utf-8")
        assert "/favicon.ico" in html_content
        assert "/favicon-32x32.png" in html_content
        assert "/favicon-16x16.png" in html_content
        assert "/apple-touch-icon.png" in html_content
        assert "/site.webmanifest" in html_content
        assert '<div class="brand-mark">AS</div>' not in html_content


class TestManifestPwaAssetsIntegrity:
    """Verifies that icons listed inside site.webmanifest are accessible over HTTP."""

    @pytest.mark.asyncio
    async def test_manifest_icons_accessible_via_fastapi(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/site.webmanifest")
            assert resp.status_code == 200
            manifest_data = resp.json()

            assert "icons" in manifest_data and len(manifest_data["icons"]) >= 2
            for icon in manifest_data["icons"]:
                src = icon["src"]
                icon_resp = await client.get(src)
                assert icon_resp.status_code == 200, (
                    f"Manifest icon '{src}' returned HTTP {icon_resp.status_code}"
                )
                assert len(icon_resp.content) > 0
                assert "image/png" in icon_resp.headers.get("content-type", "")
