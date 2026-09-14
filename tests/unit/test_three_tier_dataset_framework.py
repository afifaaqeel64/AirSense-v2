"""Comprehensive unit tests for the AirSense 3-Tier Filing & Data Validation Framework.

Verifies:
1. Exact 35 targeted schema column contract and ordering.
2. Optical particle bin estimation & Magnus-Tetens dew point computation.
3. Automated cross-validation engine (bounds, deltas, flags, quality scoring, SHA-256 content hashes).
4. Verified open-source atmospheric ingestion & climatological offline fallback.
5. Tier 1 (Hardware + Verified Chemicals) dataset builder.
6. Tier 2 (Pure Open-Source Meteorological & Chemical) dataset builder.
7. Tier 3 (ML Cumulative Validated) dataset builder and cross-sensor evaluation.
8. CSV export sanitization (formula injection blocking while preserving numerics).
9. REST API tiered CSV streaming endpoints (/api/v1/hardware/daily-csv and /api/v1/hardware/tiered-csv/{tier}).
10. Daily backup generation and multi-tier zip archiving.
"""

import os
import csv
import io
import pytest
from pathlib import Path
from datetime import datetime, date, timezone, timedelta
from unittest.mock import patch, MagicMock
import httpx
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.api.main import app
from apps.api.db.session import engine
from apps.api.db.models import Base, Campus, Station, RawReading
from services.quality_control.three_tier_framework import (
    TARGETED_VARIABLES,
    AUXILIARY_VARIABLES,
    FULL_SCHEMA_COLUMNS,
    sanitize_csv_cell,
    calculate_dew_point,
    estimate_particle_bins,
    compute_row_content_hash,
    cross_validate_reading,
    synthesize_climatological_hourly_series,
    fetch_verified_opensource_hourly,
    match_closest_opensource_record,
    build_tier1_dataset,
    build_tier2_dataset,
    build_tier3_dataset,
    export_dataset_to_csv
)
from scripts.generate_daily_backup_csv import generate_daily_backup


@pytest.fixture(autouse=True)
async def init_test_db():
    """Ensures test database tables and basic campus/station are available."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
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


def test_targeted_variables_exact_schema_contract():
    """Verifies that TARGETED_VARIABLES contains the exact 35 variables specified in prompt in exact order."""
    expected_35 = [
        "pm1_raw",
        "pm2_5_raw",
        "pm10_raw",
        "particle_bin_0_3um",
        "particle_bin_0_5um",
        "particle_bin_1_0um",
        "particle_bin_2_5um",
        "particle_bin_5_0um",
        "particle_bin_10_0um",
        "co2_ppm",
        "co_ug_m3",
        "no2_ug_m3",
        "so2_ug_m3",
        "o3_ug_m3",
        "temperature_c",
        "dew_point_c",
        "rain_flag",
        "precipitation_analog_val",
        "precipitation_mm",
        "cloud_cover_pct",
        "solar_radiation_w_m2",
        "station_id",
        "campus_id",
        "device_uid",
        "sequence_number",
        "battery_voltage_v",
        "wifi_rssi_dbm",
        "free_heap_bytes",
        "quality_score",
        "is_valid",
        "is_interpolated",
        "qc_flags",
        "content_hash",
        "observed_at_utc",
        "observed_at_pk",
    ]
    assert TARGETED_VARIABLES == expected_35
    assert len(TARGETED_VARIABLES) == 35

    # Verify FULL_SCHEMA_COLUMNS contains all 35 + auxiliary variables
    for var in expected_35:
        assert var in FULL_SCHEMA_COLUMNS
    for aux in ["humidity_pct", "pressure_hpa", "aqi"]:
        assert aux in FULL_SCHEMA_COLUMNS


def test_optical_particle_bins_and_dew_point():
    """Verifies optical particle bin calculations and Magnus-Tetens dew point accuracy."""
    # 1. Particle bins
    bins = estimate_particle_bins(pm2_5=20.0, pm10=35.0)
    assert bins["particle_bin_0_3um"] == 1240.0
    assert bins["particle_bin_0_5um"] == 360.0
    assert bins["particle_bin_1_0um"] == 56.0
    assert bins["particle_bin_2_5um"] == 7.0
    assert bins["particle_bin_5_0um"] == 2.8
    assert bins["particle_bin_10_0um"] == 0.7

    # 2. Dew point calculation
    # At 30.0 C and 60.0% RH, dew point is approximately 21.4 C
    dp = calculate_dew_point(30.0, 60.0)
    assert dp is not None
    assert 21.0 <= dp <= 21.8

    # Edge cases
    assert calculate_dew_point(None, 60.0) is None
    assert calculate_dew_point(30.0, None) is None
    assert calculate_dew_point(30.0, 0.0) is None
    assert calculate_dew_point(30.0, 110.0) is None


def test_cross_validation_clean_reading():
    """Verifies cross-validation of a high-quality, convergent reading."""
    hw = {
        "temperature_c": 31.0,
        "humidity_pct": 60.0,
        "pressure_hpa": 1010.0,
        "pm1": 10.0,
        "pm2_5": 14.0,
        "pm10": 22.0,
        "rain_flag": False,
        "is_interpolated": False
    }
    os_base = {
        "temperature_c": 31.5,
        "humidity_pct": 58.0,
        "pressure_hpa": 1011.0,
        "pm2_5_raw": 15.0,
        "rain_flag": False,
        "precipitation_mm": 0.0
    }
    score, is_valid, is_interp, flags = cross_validate_reading(hw, os_base)
    assert score >= 0.90
    assert is_valid is True
    assert is_interp is False
    assert "CROSS_VALIDATED" in flags
    assert "TEMP_CONVERGENT" in flags
    assert "PM_CONVERGENT" in flags


def test_cross_validation_fatal_bounds_and_discrepancies():
    """Verifies that physical bounds violations and severe discrepancies trigger penalties and invalidity."""
    # 1. Impossible temperature (75 C)
    hw_bad_temp = {
        "temperature_c": 75.0,
        "humidity_pct": 50.0,
        "pressure_hpa": 1010.0,
        "pm2_5": 15.0,
        "pm1": 10.0,
        "pm10": 20.0
    }
    os_base = {
        "temperature_c": 32.0,
        "humidity_pct": 50.0,
        "pressure_hpa": 1010.0,
        "pm2_5_raw": 15.0
    }
    score, is_valid, _, flags = cross_validate_reading(hw_bad_temp, os_base)
    assert is_valid is False
    assert "IMPOSSIBLE_TEMPERATURE" in flags
    assert score <= 0.50

    # 2. Particle ordering inconsistency (PM1 > PM2.5 + 2)
    hw_bad_pm = {
        "temperature_c": 30.0,
        "humidity_pct": 50.0,
        "pressure_hpa": 1010.0,
        "pm1": 35.0,
        "pm2_5": 10.0,
        "pm10": 12.0
    }
    score2, _, _, flags2 = cross_validate_reading(hw_bad_pm, os_base)
    assert "PM_ORDERING_INCONSISTENCY" in flags2

    # 3. Rain confirmed vs local rain
    hw_rain = {"temperature_c": 28.0, "humidity_pct": 80.0, "rain_flag": True}
    os_rain = {"temperature_c": 28.0, "humidity_pct": 80.0, "rain_flag": True, "precipitation_mm": 5.2}
    _, _, _, flags3 = cross_validate_reading(hw_rain, os_rain)
    assert "RAIN_CONFIRMED" in flags3


def test_climatological_series_synthesis_and_fallback():
    """Verifies diurnal climatological fallback generator produces full 24 hourly records."""
    target_date = date(2026, 9, 12)
    series = synthesize_climatological_hourly_series(target_date)
    assert len(series) == 24

    for idx, rec in enumerate(series):
        assert "observed_at_utc" in rec
        assert "observed_at_pk" in rec
        assert "co2_ppm" in rec and rec["co2_ppm"] > 400.0
        assert "no2_ug_m3" in rec
        assert "so2_ug_m3" in rec
        assert "o3_ug_m3" in rec
        assert "co_ug_m3" in rec
        assert "temperature_c" in rec
        assert "humidity_pct" in rec
        assert "dew_point_c" in rec
        assert "solar_radiation_w_m2" in rec
        assert rec["observed_at_pk"].startswith("2026-09-12")


@pytest.mark.asyncio
async def test_fetch_verified_opensource_offline_fallback():
    """Verifies that fetch_verified_opensource_hourly handles network error gracefully with fallback."""
    target_date = date(2026, 9, 12)
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Network unreachable")):
        records = await fetch_verified_opensource_hourly(target_date)
        assert len(records) == 24
        assert records[0]["co2_ppm"] >= 400.0


def test_tier1_tier2_tier3_dataset_builders():
    """Verifies dataset generation across Tier 1, Tier 2, and Tier 3."""
    target_date = date(2026, 9, 12)
    os_hourly = synthesize_climatological_hourly_series(target_date)

    # Mock hardware reading object
    class MockReading:
        def __init__(self):
            self.id = 101
            self.campus_id = 1
            self.station_id = "BIC-KHI-ROOF-01"
            self.device_id = "ESP32-KHI-01"
            self.sequence_number = 42
            self.observed_at = datetime(2026, 9, 12, 10, 0, 0, tzinfo=timezone.utc)
            self.source = "onsite_esp32"
            self.pm1 = 8.0
            self.pm2_5 = 12.5
            self.pm10 = 20.0
            self.temperature_c = 30.5
            self.humidity_pct = 62.0
            self.pressure_hpa = 1011.5
            self.rain_flag = False
            self.aqi = 52
            self.payload_json = {
                "battery_voltage_v": 4.15,
                "wifi_rssi_dbm": -62,
                "free_heap_bytes": 190000,
                "precipitation_analog_val": 4095
            }

    readings = [MockReading()]

    # 1. Tier 1: Hardware physicals + Open-source chemicals
    t1 = build_tier1_dataset(readings, os_hourly)
    assert len(t1) == 1
    r1 = t1[0]
    assert r1["temperature_c"] == 30.5
    assert r1["pm2_5_raw"] == 12.5
    assert r1["co2_ppm"] >= 400.0
    assert r1["no2_ug_m3"] is not None
    assert r1["battery_voltage_v"] == 4.15
    assert r1["qc_flags"].startswith("TIER1_HARDWARE_CHEMICAL")
    for col in TARGETED_VARIABLES:
        assert col in r1

    # 2. Tier 2: Pure Open-Source physical and chemical
    t2 = build_tier2_dataset(os_hourly)
    assert len(t2) == 24
    r2 = t2[0]
    assert r2["station_id"] == "EXT-OPEN-METEO-KHI"
    assert r2["device_uid"] == "OPENSOURCE_API_GRID"
    assert r2["battery_voltage_v"] == ""  # Virtual node has no battery
    assert r2["qc_flags"].startswith("TIER2_OPENSOURCE_PURE")
    for col in TARGETED_VARIABLES:
        assert col in r2

    # 3. Tier 3: ML Cumulative Validated (Cross-validated)
    t3 = build_tier3_dataset(readings, os_hourly)
    assert len(t3) == 1
    r3 = t3[0]
    assert r3["temperature_c"] == 30.5
    assert r3["pm2_5_raw"] == 12.5
    assert r3["co2_ppm"] >= 400.0
    assert r3["quality_score"] >= 0.70
    assert r3["is_valid"] is True
    assert "CROSS_VALIDATED" in r3["qc_flags"]
    assert len(r3["content_hash"]) == 64  # SHA-256 hex string
    for col in TARGETED_VARIABLES:
        assert col in r3


def test_export_dataset_to_csv_and_sanitization(tmp_path):
    """Verifies that export_dataset_to_csv creates valid CSV with headers and blocks CSV formula injection."""
    out_file = tmp_path / "test_tier3.csv"
    test_rows = [
        {
            "pm1_raw": 10.0,
            "pm2_5_raw": 15.0,
            "pm10_raw": 25.0,
            "co2_ppm": 415.0,
            "temperature_c": -2.5,  # Valid negative number should NOT have quote prepended
            "station_id": "=cmd|' /C calc'!A0",  # Injection attempt should have single quote prepended
            "observed_at_utc": "2026-09-12T10:00:00Z",
            "observed_at_pk": "2026-09-12 15:00:00",
            "quality_score": 0.95,
            "is_valid": True,
            "is_interpolated": False,
            "qc_flags": "CLEAN",
            "content_hash": "a" * 64
        }
    ]

    export_dataset_to_csv(test_rows, out_file)
    assert out_file.exists()

    with open(out_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        row = next(reader)

        assert header == FULL_SCHEMA_COLUMNS
        stn_idx = header.index("station_id")
        temp_idx = header.index("temperature_c")

        # Formula injection is escaped
        assert row[stn_idx].startswith("'=")
        # Valid negative number is preserved as numeric text
        assert row[temp_idx] == "-2.5"


@pytest.mark.asyncio
async def test_api_tiered_csv_endpoints():
    """Verifies GET /api/v1/hardware/daily-csv?tier=X and GET /api/v1/hardware/tiered-csv/{tier}."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Tier 1
        res1 = await client.get("/api/v1/hardware/daily-csv?tier=1&date_str=2026-09-12")
        assert res1.status_code == 200
        assert res1.headers["content-type"].startswith("text/csv")
        assert "tier1_hardware_chemical_2026-09-12.csv" in res1.headers["content-disposition"]
        lines1 = res1.text.strip().split("\n")
        assert lines1[0].split(",") == FULL_SCHEMA_COLUMNS

        # Tier 2
        res2 = await client.get("/api/v1/hardware/daily-csv?tier=2&date_str=2026-09-12")
        assert res2.status_code == 200
        assert "tier2_opensource_pure_2026-09-12.csv" in res2.headers["content-disposition"]
        lines2 = res2.text.strip().split("\n")
        assert len(lines2) == 25  # Header + 24 hourly records

        # Tier 3
        res3 = await client.get("/api/v1/hardware/daily-csv?tier=3&date_str=2026-09-12")
        assert res3.status_code == 200
        assert "tier3_ml_cumulative_validated_2026-09-12.csv" in res3.headers["content-disposition"]
        lines3 = res3.text.strip().split("\n")
        assert lines3[0].split(",") == FULL_SCHEMA_COLUMNS

        # Direct tiered route /api/v1/hardware/tiered-csv/3
        res_direct = await client.get("/api/v1/hardware/tiered-csv/3?date_str=2026-09-12")
        assert res_direct.status_code == 200
        assert "tier3_ml_cumulative_validated_2026-09-12.csv" in res_direct.headers["content-disposition"]

        # Invalid tier route returns 400 or 422
        res_inv = await client.get("/api/v1/hardware/tiered-csv/4")
        assert res_inv.status_code == 400


def test_automated_backup_multi_tier_generation_and_zip(tmp_path):
    """Verifies that generate_daily_backup generates Tier 1, Tier 2, Tier 3, legacy CSV, and zip archive."""
    import zipfile
    target_date = date(2026, 9, 12)
    res = generate_daily_backup(target_date=target_date, output_dir=tmp_path, send_telegram=False, tier="all")

    assert res["status"] == "success"
    assert "tier1_csv_path" in res and Path(res["tier1_csv_path"]).exists()
    assert "tier2_csv_path" in res and Path(res["tier2_csv_path"]).exists()
    assert "tier3_csv_path" in res and Path(res["tier3_csv_path"]).exists()
    assert "zip_path" in res and Path(res["zip_path"]).exists()

    # Inspect zip file contents
    zip_p = Path(res["zip_path"])
    with zipfile.ZipFile(zip_p, "r") as zf:
        names = zf.namelist()
        assert any("tier1_hardware_chemical" in n for n in names)
        assert any("tier2_opensource_pure" in n for n in names)
        assert any("tier3_ml_cumulative_validated" in n for n in names)
        assert any("airsense_daily" in n for n in names)


def test_tier2_24_7_continuous_minute_series_1440_records():
    """Verifies that Tier 2 open-source dataset generates exactly 1,440 continuous minute readings per 24-hour day."""
    target_date = date(2026, 9, 14)
    os_hourly = synthesize_climatological_hourly_series(target_date)

    # 1. Hourly baseline (24 rows)
    t2_hourly = build_tier2_dataset(os_hourly, expand_to_minute=False)
    assert len(t2_hourly) == 24

    # 2. 24/7-365 Continuous Minute Stream (1,440 rows)
    t2_minute = build_tier2_dataset(os_hourly, expand_to_minute=True)
    assert len(t2_minute) == 1440

    # Verify sequential minute continuity without any skips
    for idx, r in enumerate(t2_minute):
        assert r["sequence_number"] == idx + 1
        assert "observed_at_utc" in r
        assert "observed_at_pk" in r
        assert r["station_id"] == "EXT-OPEN-METEO-KHI"
        assert r["device_uid"] == "OPENSOURCE_API_GRID"
        assert "TIER2_OPENSOURCE_PURE" in r["qc_flags"]
        assert len(r["content_hash"]) == 64
        for col in TARGETED_VARIABLES:
            assert col in r

        # Check consecutive 1-minute delta
        if idx < len(t2_minute) - 1:
            curr_dt = datetime.fromisoformat(r["observed_at_utc"].replace("Z", "+00:00"))
            next_dt = datetime.fromisoformat(t2_minute[idx + 1]["observed_at_utc"].replace("Z", "+00:00"))
            assert (next_dt - curr_dt).total_seconds() == 60


@pytest.mark.asyncio
async def test_weather_telemetry_feed_endpoint_up_to_1440_limit():
    """Verifies that /api/v1/providers/weather/telemetry-feed supports full 24-hour query limits up to 1440."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/providers/weather/telemetry-feed?limit=1440")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["records"]) == 1440
        assert data["records"][0]["minute_slot"] > data["records"][-1]["minute_slot"]
