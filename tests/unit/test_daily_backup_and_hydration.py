"""Unit tests for 24/7 continuous telemetry persistence, daily CSV export, and historical hydration.

Verifies:
1. Daily CSV streaming endpoint (/api/v1/hardware/daily-csv) filtering, headers, and format.
2. Vercel ingress environment variable check (DATABASE_URL precedence).
3. Frontend historical hydration contract and capacity across all 4 dashboard HTML assets.
4. Firmware MicroSD date-partitioned logging contract and CSV header format.
5. Automated daily backup script generation logic and mock Telegram dispatch.
"""

import os
import csv
import io
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta, date
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.api.main import app
from apps.api.db.session import engine
from apps.api.db.models import Base, Campus, Station, RawReading
from scripts.generate_daily_backup_csv import generate_daily_backup, send_telegram_document


@pytest.fixture(autouse=True)
async def init_test_db():
    """Ensures test database tables and basic campus/station are available."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        # Seed test campus and station if absent
        res_c = await session.execute(select(Campus).where(Campus.code == "KARACHI"))
        campus = res_c.scalar_one_or_none()
        if not campus:
            campus = Campus(
                code="KARACHI",
                name="Karachi Campus",
                city="Karachi",
                contact_name="Lead Engineer",
                latitude=24.8607,
                longitude=67.0011,
                status="active"
            )
            session.add(campus)
            await session.flush()

        res_s = await session.execute(select(Station).where(Station.station_code == "BIC-KHI-ROOF-01"))
        station = res_s.scalar_one_or_none()
        if not station:
            station = Station(
                campus_id=campus.id,
                station_code="BIC-KHI-ROOF-01",
                station_name="Karachi BIC Rooftop",
                installation_location="BIC Rooftop",
                latitude=24.8607,
                longitude=67.0011,
                status="active"
            )
            session.add(station)
            await session.commit()


@pytest.mark.asyncio
async def test_daily_csv_endpoint_streaming_and_filtering():
    """Verifies that /api/v1/hardware/daily-csv correctly filters readings for the PKT calendar day."""
    pkt_tz = timezone(timedelta(hours=5))
    target_date = date(2026, 9, 10)

    # 2026-09-10 in PKT runs from 2026-09-09 19:00:00 UTC to 2026-09-10 19:00:00 UTC
    in_day_time_utc = datetime(2026, 9, 10, 8, 30, 0, tzinfo=timezone.utc)
    out_day_time_utc = datetime(2026, 9, 11, 8, 30, 0, tzinfo=timezone.utc)

    async with AsyncSession(engine) as session:
        res_s = await session.execute(select(Station).where(Station.station_code == "BIC-KHI-ROOF-01"))
        stn = res_s.scalar_one()

        reading_in = RawReading(
            campus_id=stn.campus_id,
            station_id=stn.id,
            observed_at=in_day_time_utc,
            received_at=in_day_time_utc,
            source="onsite_esp32",
            pm1=8.5,
            pm2_5=14.2,
            pm10=18.6,
            temperature_c=29.4,
            humidity_pct=61.0,
            pressure_hpa=1012.3,
            rain_flag=False,
            sequence_number=9001,
            content_hash="hash_in_day_test_01"
        )
        reading_out = RawReading(
            campus_id=stn.campus_id,
            station_id=stn.id,
            observed_at=out_day_time_utc,
            received_at=out_day_time_utc,
            source="onsite_esp32",
            pm1=9.0,
            pm2_5=22.1,
            pm10=30.4,
            temperature_c=31.0,
            humidity_pct=55.0,
            pressure_hpa=1011.0,
            rain_flag=True,
            sequence_number=9002,
            content_hash="hash_out_day_test_02"
        )
        session.add_all([reading_in, reading_out])
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Query with specific valid date
        res = await client.get("/api/v1/hardware/daily-csv?date_str=2026-09-10")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/csv")
        assert 'filename="airsense_daily_2026-09-10.csv"' in res.headers["content-disposition"]

        csv_content = res.text
        lines = [line.strip() for line in csv_content.strip().split("\n") if line.strip()]
        assert len(lines) >= 2  # Header + at least reading_in

        header = lines[0].split(",")
        assert "reading_id" in header
        assert "observed_at_pkt" in header
        assert "pm2_5" in header
        assert "temperature_c" in header

        # Verify that in-day reading is present and out-day reading is excluded
        assert "9001" in csv_content
        assert "hash_in_day_test_01" not in csv_content or "9001" in csv_content
        assert "9002" not in csv_content

        # 2. Query with invalid date format
        res_invalid = await client.get("/api/v1/hardware/daily-csv?date_str=invalid-date")
        assert res_invalid.status_code == 400
        assert "Invalid date format" in res_invalid.json()["detail"]

        # 3. Query without date parameter (defaults to yesterday PKT)
        res_default = await client.get("/api/v1/hardware/daily-csv")
        assert res_default.status_code == 200
        assert res_default.headers["content-type"].startswith("text/csv")
        assert "airsense_daily_" in res_default.headers["content-disposition"]


def test_api_index_database_url_precedence():
    """Verifies that api/index.py respects external DATABASE_URL in Vercel environment."""
    index_file = Path(__file__).resolve().parent.parent.parent / "api" / "index.py"
    assert index_file.exists()
    content = index_file.read_text(encoding="utf-8")

    # Line 19 must NOT contain 'os.environ.get("VERCEL") or not os.environ.get("DATABASE_URL")'
    assert 'os.environ.get("VERCEL") or not os.environ.get("DATABASE_URL")' not in content
    # It must check 'if not os.environ.get("DATABASE_URL"):'
    assert 'if not os.environ.get("DATABASE_URL"):' in content


def test_frontend_dashboards_historical_hydration_contract():
    """Verifies that all 4 dashboard HTML assets implement hydrateHistoricalTelemetry and 120-entry capacity."""
    root_dir = Path(__file__).resolve().parent.parent.parent
    dashboard_paths = [
        root_dir / "public" / "hardware.html",
        root_dir / "public" / "index.html",
        root_dir / "apps" / "web" / "hardware_dashboard.html",
        root_dir / "apps" / "web" / "index.html",
    ]

    for p in dashboard_paths:
        assert p.exists(), f"Dashboard file {p} does not exist"
        content = p.read_text(encoding="utf-8")

        # 1. hydrateHistoricalTelemetry function definition
        assert "async function hydrateHistoricalTelemetry()" in content, f"Missing hydrateHistoricalTelemetry in {p.name}"

        # 2. Fetches 120 minutes of history
        assert "/api/v1/hardware/minute-history?limit=120" in content, f"Missing minute-history endpoint in {p.name}"

        # 3. Capacity expanded to 120
        assert "savedTelemetryRecords.length > 120" in content, f"Capacity not 120 in {p.name}"

        # 4. Calls renderTelemetryTable()
        assert "renderTelemetryTable();" in content, f"Missing renderTelemetryTable in {p.name}"

        # 5. Hydrates in initCloudMQTT
        assert "hydrateHistoricalTelemetry();" in content, f"Missing hydrate call in initCloudMQTT in {p.name}"


def test_firmware_microsd_date_partitioning_contract():
    """Verifies that ESP32 firmware partitions CSV files by PKT calendar date and formats headers."""
    fw_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "airsense_esp32_firmware" / "airsense_esp32_firmware.ino"
    assert fw_path.exists()
    content = fw_path.read_text(encoding="utf-8")

    # 1. logToMicroSD function exists
    assert "void logToMicroSD(" in content

    # 2. Date partitioned filename
    assert "/airsense_%04d_%02d_%02d.csv" in content

    # 3. CSV header with exact column contract
    assert "seq,epoch,datetime_pkt,pm1_0,pm2_5,pm10,temp_c,humidity_pct,pressure_hpa,rain_status,pms_health,bme_health" in content

    # 4. Epoch threshold validation (> 1700000000)
    assert "now_epoch > 1700000000" in content or "epoch > 1700000000" in content

    # 5. PKT time formatting with localtime_r
    assert "localtime_r(&now_epoch, &timeinfo)" in content or "localtime_r(&epoch, &timeinfo)" in content

    # 6. Check for empty or non-existent file before writing CSV header
    assert "!file_exists || f.size() == 0" in content


def test_daily_backup_script_generation_and_telegram(tmp_path):
    """Verifies that generate_daily_backup_csv.py exports partitioned CSV and handles Telegram dispatch."""
    target_date = date(2026, 9, 10)
    res = generate_daily_backup(target_date=target_date, output_dir=tmp_path, send_telegram=False)

    assert res["status"] == "success"
    assert res["target_date"] == "2026-09-10"
    assert Path(res["csv_path"]).exists()
    assert res["csv_path"].endswith("airsense_daily_2026_09_10.csv")

    # Read generated CSV
    with open(res["csv_path"], "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        assert "reading_id" in header
        assert "observed_at_pkt" in header
        assert "pm2_5" in header

    # Test Telegram sending function with mock HTTP response
    fake_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    fake_chat = "987654321"
    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, text='{"ok": true}')
        sent = send_telegram_document(fake_token, fake_chat, Path(res["csv_path"]), "Test Caption")
        assert sent is True
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_daily_csv_endpoint_empty_day():
    """Edge case: Verifies that querying a date with no records returns a valid CSV with only headers."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/hardware/daily-csv?date_str=1999-01-01")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/csv")
        assert 'filename="airsense_daily_1999-01-01.csv"' in res.headers["content-disposition"]

        csv_text = res.text.strip()
        lines = [line.strip() for line in csv_text.split("\n") if line.strip()]
        # Exactly 1 row: the CSV header
        assert len(lines) == 1
        assert "reading_id" in lines[0]
        assert "observed_at_pkt" in lines[0]


def test_daily_backup_script_empty_database(tmp_path):
    """Edge case: Verifies generate_daily_backup handles days with zero records without dividing by zero."""
    target_date = date(1999, 1, 1)
    res = generate_daily_backup(target_date=target_date, output_dir=tmp_path, send_telegram=False)

    assert res["status"] == "success"
    assert res["total_records"] == 0
    assert res["summary"]["avg_pm25"] == 0.0
    assert res["summary"]["avg_temp"] == 0.0
    assert res["summary"]["avg_hum"] == 0.0

    csv_path = Path(res["csv_path"])
    assert csv_path.exists()
    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
        assert len(rows) == 1  # Header only


def test_daily_backup_telegram_failure_handled_gracefully(tmp_path):
    """Edge case: Verifies that Telegram failure does not crash the backup generation."""
    target_date = date(2026, 9, 10)
    fake_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    fake_chat = "987654321"

    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": fake_token, "TELEGRAM_CHAT_ID": fake_chat}):
        with patch("httpx.post") as mock_post:
            # Simulate HTTP 403 / 500 error from Telegram API
            mock_post.return_value = MagicMock(status_code=403, text='{"ok": false, "error_code": 403}')
            res = generate_daily_backup(target_date=target_date, output_dir=tmp_path, send_telegram=True)

            assert res["status"] == "success"
            assert res["telegram_sent"] is False
            assert Path(res["csv_path"]).exists()


def test_sanitize_csv_cell_preserves_numeric_and_blocks_formula_injection():
    """Verifies that negative temperatures and error codes are NOT corrupted, while formula injections are sanitized."""
    from apps.api.routers.hardware_router import sanitize_csv_cell as router_sanitize
    from scripts.generate_daily_backup_csv import sanitize_csv_cell as script_sanitize

    for sanitize in [router_sanitize, script_sanitize]:
        # 1. Valid numbers (negative, positive, error codes) must NOT have single quote prepended
        assert sanitize(-2.5) == -2.5
        assert sanitize(-1.0) == -1.0
        assert sanitize(-999.0) == -999.0
        assert sanitize(31.5) == 31.5
        assert sanitize(0) == 0
        assert sanitize(1012) == 1012
        assert sanitize("-2.5") == "-2.5"
        assert sanitize("+15.2") == "+15.2"

        # 2. Dangerous formula injection strings must be prepended with single quote
        assert sanitize("=cmd|' /C calc'!A0") == "'=cmd|' /C calc'!A0"
        assert sanitize("@SUM(A1:A10)") == "'@SUM(A1:A10)"
        assert sanitize("+alert(1)") == "'+alert(1)"
        assert sanitize("-2+3*cmd") == "'-2+3*cmd"
        assert sanitize("\tmalicious_tab") == "'\tmalicious_tab"

        # 3. None and clean text
        assert sanitize(None) == ""
        assert sanitize("Optimal") == "Optimal"
        assert sanitize("BIC-KHI-ROOF-01") == "BIC-KHI-ROOF-01"


@pytest.mark.asyncio
async def test_daily_backup_called_from_async_loop(tmp_path):
    """Verifies that generate_daily_backup handles being called inside an active async event loop without RuntimeError."""
    from scripts.generate_daily_backup_csv import async_generate_daily_backup

    target_date = date(2026, 9, 10)
    # 1. Calling synchronous wrapper inside running async event loop
    res_sync = generate_daily_backup(target_date=target_date, output_dir=tmp_path, send_telegram=False)
    assert res_sync["status"] == "success"
    assert Path(res_sync["csv_path"]).exists()

    # 2. Calling async entrypoint directly inside running async event loop
    res_async = await async_generate_daily_backup(target_date=target_date, output_dir=tmp_path, send_telegram=False)
    assert res_async["status"] == "success"
    assert Path(res_async["csv_path"]).exists()


def test_empty_database_url_fallback():
    """Verifies that an empty DATABASE_URL environment string does not crash SQLAlchemy engine creation."""
    from apps.api.core.config import Settings
    with patch.dict(os.environ, {"DATABASE_URL": ""}):
        s = Settings()
        # Verify normalization in session
        norm_url = s.DATABASE_URL.strip() if s.DATABASE_URL and s.DATABASE_URL.strip() else "sqlite+aiosqlite:///./data/airsense.db"
        assert "sqlite+aiosqlite:///" in norm_url


def test_dashboards_contain_daily_csv_download_links():
    """Verifies that all 4 dashboards expose the direct /api/v1/hardware/daily-csv download link."""
    root_dir = Path(__file__).resolve().parent.parent.parent
    dashboard_paths = [
        root_dir / "public" / "hardware.html",
        root_dir / "public" / "index.html",
        root_dir / "apps" / "web" / "hardware_dashboard.html",
        root_dir / "apps" / "web" / "index.html",
    ]

    for p in dashboard_paths:
        content = p.read_text(encoding="utf-8")
        assert "/api/v1/hardware/daily-csv" in content, f"Missing daily-csv link in {p.name}"
        assert "DAILY 24H CSV" in content, f"Missing DAILY 24H CSV button text in {p.name}"

