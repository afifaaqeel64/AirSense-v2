"""Comprehensive automated test suite for AirSense branding, favicon suite,
web manifest metadata, FastAPI static routing, HTML head link integration,
navbar logo rendering, and documentation branding.
"""

import json
import re
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

from apps.api.main import app

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
LOGO_ASSETS = [
    "favicon.ico",
    "favicon-16x16.png",
    "favicon-32x32.png",
    "apple-touch-icon.png",
    "android-chrome-192x192.png",
    "android-chrome-512x512.png",
    "site.webmanifest",
]

TARGET_HTML_FILES = [
    ROOT_DIR / "public" / "index.html",
    ROOT_DIR / "public" / "hardware.html",
    ROOT_DIR / "public" / "diagnostics.html",
    ROOT_DIR / "public" / "command.html",
    ROOT_DIR / "public" / "opensource.html",
    ROOT_DIR / "public" / "enterprise.html",
    ROOT_DIR / "public" / "sensor-health.html",
    ROOT_DIR / "apps" / "web" / "index.html",
    ROOT_DIR / "apps" / "web" / "hardware.html",
    ROOT_DIR / "apps" / "web" / "diagnostics.html",
    ROOT_DIR / "apps" / "web" / "command.html",
    ROOT_DIR / "apps" / "web" / "opensource.html",
    ROOT_DIR / "apps" / "web" / "enterprise.html",
    ROOT_DIR / "apps" / "web" / "sensor-health.html",
]


class TestBrandingFilesOnDisk:
    """Validates physical presence and integrity of all branding assets on disk."""

    @pytest.mark.parametrize("asset_name", LOGO_ASSETS)
    def test_asset_exists_in_assets_logo_files(self, asset_name: str):
        target = ROOT_DIR / "assets" / "logo-files" / asset_name
        assert target.exists(), f"Missing {asset_name} in assets/logo-files"
        assert target.stat().st_size > 0, f"File {asset_name} in assets/logo-files is empty"

    @pytest.mark.parametrize("asset_name", LOGO_ASSETS)
    def test_asset_exists_in_public_root(self, asset_name: str):
        target = ROOT_DIR / "public" / asset_name
        assert target.exists(), f"Missing {asset_name} in public/"
        assert target.stat().st_size > 0, f"File {asset_name} in public/ is empty"

    @pytest.mark.parametrize("asset_name", LOGO_ASSETS)
    def test_asset_exists_in_apps_web_root(self, asset_name: str):
        target = ROOT_DIR / "apps" / "web" / asset_name
        assert target.exists(), f"Missing {asset_name} in apps/web/"
        assert target.stat().st_size > 0, f"File {asset_name} in apps/web/ is empty"


class TestSiteWebmanifestValidity:
    """Validates structure and content of site.webmanifest across directories."""

    @pytest.mark.parametrize("directory", ["assets/logo-files", "public", "apps/web"])
    def test_manifest_schema_and_branding_names(self, directory: str):
        manifest_path = ROOT_DIR / directory / "site.webmanifest"
        assert manifest_path.exists(), f"site.webmanifest not found in {directory}"
        content = json.loads(manifest_path.read_text(encoding="utf-8"))

        assert content.get("name") == "AirSense Pakistan", f"Incorrect name in {directory}/site.webmanifest"
        assert content.get("short_name") == "AirSense", f"Incorrect short_name in {directory}/site.webmanifest"
        assert "icons" in content and len(content["icons"]) > 0, "No icons defined in webmanifest"

        for icon in content["icons"]:
            assert "src" in icon
            assert "sizes" in icon
            assert "type" in icon
            # Verify the referenced icon file exists on disk
            icon_filename = Path(icon["src"]).name
            assert (ROOT_DIR / "assets" / "logo-files" / icon_filename).exists(), (
                f"Referenced icon {icon_filename} missing from assets/logo-files"
            )


class TestFastApiFaviconAndManifestEndpoints:
    """Validates that FastAPI serves all branding assets under root / and /assets/logo-files/."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "route,expected_type",
        [
            ("/favicon.ico", "image/"),
            ("/favicon-16x16.png", "image/png"),
            ("/favicon-32x32.png", "image/png"),
            ("/apple-touch-icon.png", "image/png"),
            ("/android-chrome-192x192.png", "image/png"),
            ("/android-chrome-512x512.png", "image/png"),
            ("/site.webmanifest", "application/manifest+json"),
        ],
    )
    async def test_root_branding_routes_return_http_200(self, route: str, expected_type: str):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(route)
            assert resp.status_code == 200, f"Failed at {route}: code {resp.status_code}"
            assert len(resp.content) > 0, f"Empty response content at {route}"
            assert expected_type in resp.headers.get("content-type", ""), (
                f"Expected {expected_type} in content-type for {route}, got {resp.headers.get('content-type')}"
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("asset_name", LOGO_ASSETS)
    async def test_assets_logo_files_mount_returns_http_200(self, asset_name: str):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/assets/logo-files/{asset_name}")
            assert resp.status_code == 200, f"Failed at /assets/logo-files/{asset_name}: code {resp.status_code}"
            assert len(resp.content) > 0


class TestHtmlPagesHeadTags:
    """Validates that every required HTML dashboard contains standardized head tags."""

    @pytest.mark.parametrize("html_file", TARGET_HTML_FILES)
    def test_html_contains_complete_favicon_suite(self, html_file: Path):
        assert html_file.exists(), f"Target HTML file missing: {html_file}"
        content = html_file.read_text(encoding="utf-8")

        assert '/favicon.ico' in content, f"Missing /favicon.ico in {html_file.name}"
        assert '/favicon-32x32.png' in content, f"Missing /favicon-32x32.png in {html_file.name}"
        assert '/favicon-16x16.png' in content, f"Missing /favicon-16x16.png in {html_file.name}"
        assert '/apple-touch-icon.png' in content, f"Missing /apple-touch-icon.png in {html_file.name}"
        assert '/site.webmanifest' in content, f"Missing /site.webmanifest in {html_file.name}"

    @pytest.mark.parametrize("html_file", TARGET_HTML_FILES)
    def test_html_contains_brand_logo_and_no_placeholder(self, html_file: Path):
        content = html_file.read_text(encoding="utf-8")

        # Must NOT contain the old placeholder <div class="brand-mark">AS</div>
        assert '<div class="brand-mark">AS</div>' not in content, (
            f"Found legacy placeholder <div class=\"brand-mark\">AS</div> in {html_file.name}"
        )

        # Must render the official brand logo
        assert 'class="brand-logo' in content or 'alt="AirSense Logo"' in content, (
            f"Missing brand-logo img in {html_file.name}"
        )


class TestCssAndThemeStyling:
    """Validates CSS files and rules for .brand-logo with zero layout shifts."""

    def test_css_files_exist_and_style_brand_logo(self):
        css_paths = [
            ROOT_DIR / "public" / "css" / "style.css",
            ROOT_DIR / "apps" / "web" / "static" / "css" / "style.css",
        ]
        for css_path in css_paths:
            assert css_path.exists(), f"Missing CSS file: {css_path}"
            css_text = css_path.read_text(encoding="utf-8")
            assert ".brand-logo" in css_text
            assert "border-radius" in css_text
            assert "object-fit" in css_text
            assert ".brand-mark" in css_text, "Legacy .brand-mark class must be preserved"


class TestReadmeDocumentationBranding:
    """Validates centered official logo banner in README.md."""

    def test_readme_banner_image_and_relative_path(self):
        readme_path = ROOT_DIR / "README.md"
        assert readme_path.exists(), "README.md not found"
        readme_text = readme_path.read_text(encoding="utf-8")

        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*alt=["\'][^"\']*AirSense[^"\']*["\']', readme_text)
        assert match is not None, "AirSense logo img tag not found in README.md"

        img_src = match.group(1)
        assert not img_src.startswith("http"), f"Expected relative path in README.md, got {img_src}"
        resolved_img = (ROOT_DIR / img_src).resolve()
        assert resolved_img.exists(), f"Image referenced in README.md ({img_src}) does not exist on disk"
        assert resolved_img.stat().st_size > 0, "Image file referenced in README.md is empty"
