"""
Unit & Integration Tests for AirSense Pakistan Daily Readings Backup Automation.
Verifies:
1. 3-Tier dataset generation (Hardware, Fused Composite, Open-Source).
2. Complete canonical target variable coverage.
3. Cryptographic manifest integrity & SHA-256 calculation.
4. Storage sovereignty: zero C: drive writes & hard D: drive constraint.
"""

import os
import sys
import json
import pytest
import pandas as pd
from datetime import datetime, timezone
from fastapi.testclient import TestClient

# Ensure project root in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from services.backup.daily_readings_backup_service import DailyReadingsBackupService, ALL_TARGET_VARIABLES
from pipelines.daily_backup_pipeline import DailyBackupPipeline
from apps.api.main import app


@pytest.fixture
def backup_service():
    return DailyReadingsBackupService()


@pytest.fixture
def api_client():
    return TestClient(app)


def test_target_variables_catalog(backup_service):
    """Verify target variable dictionary completeness."""
    assert len(ALL_TARGET_VARIABLES) >= 35
    
    # Must include micro-horizons and 10-day multi-horizon
    assert "target_pm2_5_1h" in ALL_TARGET_VARIABLES
    assert "target_pm2_5_6h" in ALL_TARGET_VARIABLES
    assert "target_pm2_5_24h" in ALL_TARGET_VARIABLES
    assert "target_pm2_5_day1" in ALL_TARGET_VARIABLES
    assert "target_pm2_5_day10" in ALL_TARGET_VARIABLES

    # Must include quantiles
    assert "target_pm2_5_q10_24h" in ALL_TARGET_VARIABLES
    assert "target_pm2_5_q50_24h" in ALL_TARGET_VARIABLES
    assert "target_pm2_5_q90_24h" in ALL_TARGET_VARIABLES

    # Must include regulatory exceedance
    assert "target_exceedance_who_24h" in ALL_TARGET_VARIABLES
    assert "target_exceedance_pak_neqs_24h" in ALL_TARGET_VARIABLES
    assert "target_exceedance_hazardous_24h" in ALL_TARGET_VARIABLES

    # Must include policy and enterprise financial loss
    assert "target_policy_sec144_prob" in ALL_TARGET_VARIABLES
    assert "target_motorway_closure_prob" in ALL_TARGET_VARIABLES
    assert "target_unmitigated_financial_loss_pkr" in ALL_TARGET_VARIABLES
    assert "target_mitigated_savings_pkr" in ALL_TARGET_VARIABLES


def test_hardware_readings_generation(backup_service):
    """Verify on-site physical hardware readings generation (File 1)."""
    df = backup_service.generate_daily_hardware_readings("2026-09-11", campus_code="KAR_CAMPUS")
    assert len(df) == 24
    
    # Essential physical columns
    expected_cols = [
        "station_id", "campus_id", "sequence_number", "observed_at_utc",
        "pm1_raw", "pm2_5_raw", "pm10_raw", "temperature_c", "humidity_pct",
        "pressure_hpa", "dew_point_c", "rain_flag", "battery_voltage_v", "wifi_rssi_dbm"
    ]
    for c in expected_cols:
        assert c in df.columns, f"Missing column: {c}"

    # Plausible physical bounds
    assert (df["pm2_5_raw"] > 0).all()
    assert (df["temperature_c"] > -10.0).all()
    assert (df["temperature_c"] < 55.0).all()
    assert (df["humidity_pct"] >= 0.0).all()
    assert (df["humidity_pct"] <= 100.0).all()


def test_opensource_readings_generation(backup_service):
    """Verify open-source multi-provider reference stream (File 3)."""
    df = backup_service.generate_daily_opensource_readings("2026-09-11")
    assert not df.empty
    assert "Karachi" in df["city"].values
    assert "Lahore" in df["city"].values

    # Verify key open-source atmospheric and chemical fields
    assert "pm2_5_cams" in df.columns
    assert "no2_ug_m3" in df.columns
    assert "so2_ug_m3" in df.columns
    assert "co_ug_m3" in df.columns
    assert "boundary_layer_height_m" in df.columns
    assert "nasa_firms_fire_count" in df.columns


def test_fused_readings_generation_and_target_alignment(backup_service):
    """Verify fused composite dataset has features and all canonical targets (File 2)."""
    df_hw = backup_service.generate_daily_hardware_readings("2026-09-11")
    df_os = backup_service.generate_daily_opensource_readings("2026-09-11")
    df_fused = backup_service.generate_daily_fused_readings("2026-09-11", df_hw, df_os)

    assert len(df_fused) == len(df_hw)
    
    # Check physics features
    assert "ventilation_coeff" in df_fused.columns
    assert "wind_u10" in df_fused.columns
    assert "wind_v10" in df_fused.columns
    assert "barometric_stagnation_index" in df_fused.columns
    assert "hygroscopic_ratio" in df_fused.columns

    # Check ALL target variables attached
    for target in ALL_TARGET_VARIABLES:
        assert target in df_fused.columns, f"Target variable missing from fused dataset: {target}"
        assert df_fused[target].isna().sum() == 0, f"Target column contains NaN: {target}"


def test_execute_daily_backup_d_drive_and_manifest(backup_service):
    """Verify complete daily backup execution, D: drive isolation, and manifest creation."""
    test_date = "2026-09-11"
    manifest = backup_service.execute_daily_backup(test_date)

    assert manifest["date"] == test_date
    assert manifest["storage_sovereignty"]["d_drive_enforced"] is True
    assert manifest["storage_sovereignty"]["root_path"].lower().startswith("d:")

    # Verify partition directory on D: drive
    partition_dir = manifest["partition_directory"]
    assert os.path.exists(partition_dir)

    # Verify each dataset has corresponding file and valid SHA-256
    for ds in manifest["datasets"]:
        fpath = os.path.join(partition_dir, ds["filename"])
        assert os.path.exists(fpath), f"File was not created: {fpath}"
        assert os.path.getsize(fpath) == ds["size_bytes"]
        computed_chk = backup_service._compute_sha256(fpath)
        assert computed_chk == ds["sha256_checksum"]


def test_storage_sovereignty_rejection():
    """Verify hard PermissionError if an invalid C: drive path is attempted."""
    with pytest.raises(PermissionError):
        DailyReadingsBackupService(base_dir="C:/Users/Source Machinery/AirSense/data")


def test_backup_api_endpoints(api_client):
    """Verify FastAPI endpoints for targets catalog and daily backup listing."""
    # 1. Target variables catalog endpoint
    res_targets = api_client.get("/api/v1/backups/daily/targets")
    assert res_targets.status_code == 200
    data = res_targets.json()
    assert data["total_targets_count"] >= 35
    assert "target_pm2_5_24h" in data["target_variables"]

    # 2. List backups endpoint
    res_list = api_client.get("/api/v1/backups/daily/list")
    assert res_list.status_code == 200
    assert isinstance(res_list.json(), list)

    # 3. Trigger backup generation via API
    res_gen = api_client.post("/api/v1/backups/daily/generate", json={"date": "2026-09-10", "campus_code": "KAR_CAMPUS"})
    assert res_gen.status_code == 200
    gen_data = res_gen.json()
    assert gen_data["status"] == "success"
    assert gen_data["manifest"]["date"] == "2026-09-10"
