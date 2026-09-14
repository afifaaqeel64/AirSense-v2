"""
Unit Tests for AirSense Pakistan Milestone M1: Multi-Decadal Data Lake & Ingestion Engine (1995-2025).

Verifies:
  - Exact volume: 1,630,512 cumulative continuous station-hours (>1,000,000 threshold).
  - 6 mandated core urban centers: Karachi, Lahore, Islamabad, Faisalabad, Peshawar, Quetta.
  - Complete temporal continuity: 1995-01-01 00:00:00 UTC to 2025-12-31 23:00:00 UTC (31 calendar years).
  - Monotonic hourly steps, 0 missing timestamps, 0 duplicate timestamps.
  - Zero future lookahead leakage.
  - Physical atmospheric bounds & aerodynamic size hierarchy (PM1 <= PM2.5 <= PM10).
  - Elevational barometric pressure adjustment for Quetta (~1,680m, ~830 hPa).
  - Cryptographic integrity: 100% SHA-256 verification against checksums.sha256.
  - Parquet Snappy compression and metadata manifest validation.
"""

import json
import hashlib
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

AIRSENSE_ROOT = Path(r"d:\MUNIM - UOE @BIC\AirSense")
DECADAL_DIR = AIRSENSE_ROOT / "data" / "datasets" / "decadal"
PARQUET_DIR = DECADAL_DIR / "parquet"
CSV_DIR = DECADAL_DIR / "csv"
CHECKSUMS_FILE = DECADAL_DIR / "checksums.sha256"
METADATA_FILE = DECADAL_DIR / "metadata.json"

EXPECTED_CITIES = ["karachi", "lahore", "islamabad", "faisalabad", "peshawar", "quetta"]
EXPECTED_HOURS_PER_STATION = 271752
EXPECTED_TOTAL_HOURS = 6 * EXPECTED_HOURS_PER_STATION  # 1,630,512
EXPECTED_START_UTC = "1995-01-01T00:00:00Z"
EXPECTED_END_UTC = "2025-12-31T23:00:00Z"

CANONICAL_COLUMNS = [
    "timestamp",
    "city",
    "pm1",
    "pm2_5",
    "pm10",
    "temperature_c",
    "relative_humidity_pct",
    "wind_speed_kmh",
    "wind_direction_deg",
    "pressure_hpa",
    "precipitation_mm",
    "blh_m",
    "qa_flag"
]


def test_decadal_lake_directory_structure_exists():
    """Confirms the physical directory layout, Parquet partitions, CSVs, and manifests exist."""
    assert DECADAL_DIR.exists(), f"Decadal directory missing at {DECADAL_DIR}"
    assert PARQUET_DIR.exists(), f"Parquet root missing at {PARQUET_DIR}"
    assert CSV_DIR.exists(), f"CSV root missing at {CSV_DIR}"
    assert CHECKSUMS_FILE.exists(), f"Checksums manifest missing at {CHECKSUMS_FILE}"
    assert METADATA_FILE.exists(), f"Metadata JSON missing at {METADATA_FILE}"

    # Verify all 6 cities have parquet partition subdirectories
    for ckey in EXPECTED_CITIES:
        city_pq_dir = PARQUET_DIR / f"city={ckey}"
        assert city_pq_dir.exists(), f"Missing parquet partition dir for {ckey}"

        # Verify all 31 years (1995 to 2025)
        for yr in range(1995, 2026):
            yr_dir = city_pq_dir / f"year={yr}"
            assert yr_dir.exists(), f"Missing year partition {yr} for {ckey}"
            pq_files = list(yr_dir.glob("*.parquet"))
            assert len(pq_files) >= 1, f"No parquet file in {yr_dir}"

        # Verify master CSV exists
        master_csv = CSV_DIR / f"airsense_decadal_{ckey}_1995_2025.csv"
        assert master_csv.exists(), f"Master CSV missing for {ckey} at {master_csv}"


def test_decadal_total_station_hours_count():
    """Verifies that each city has exactly 271,752 records, totaling 1,630,512 (>1M hours)."""
    total_records = 0
    for ckey in EXPECTED_CITIES:
        master_csv = CSV_DIR / f"airsense_decadal_{ckey}_1995_2025.csv"
        df = pd.read_csv(master_csv, usecols=["timestamp"])
        assert len(df) == EXPECTED_HOURS_PER_STATION, (
            f"City {ckey} expected {EXPECTED_HOURS_PER_STATION} rows, got {len(df)}"
        )
        total_records += len(df)

    assert total_records == EXPECTED_TOTAL_HOURS, (
        f"Expected cumulative {EXPECTED_TOTAL_HOURS} hours, got {total_records}"
    )
    assert total_records > 1_000_000, "Cumulative volume fails 1,000,000 station-hours mandate"


def test_decadal_temporal_continuity_and_zero_missing_hours():
    """Verifies strict monotonic hourly progression, zero missing timestamps, and leap year accounting."""
    for ckey in EXPECTED_CITIES:
        master_csv = CSV_DIR / f"airsense_decadal_{ckey}_1995_2025.csv"
        df = pd.read_csv(master_csv, usecols=["timestamp"])

        # Check start and end timestamp bounds
        assert df["timestamp"].iloc[0] == EXPECTED_START_UTC, (
            f"{ckey} start mismatch: {df['timestamp'].iloc[0]} != {EXPECTED_START_UTC}"
        )
        assert df["timestamp"].iloc[-1] == EXPECTED_END_UTC, (
            f"{ckey} end mismatch: {df['timestamp'].iloc[-1]} != {EXPECTED_END_UTC}"
        )

        # Monotonicity & exact 1-hour delta
        ts = pd.to_datetime(df["timestamp"], format="%Y-%m-%dT%H:%M:%SZ")
        assert ts.is_monotonic_increasing, f"{ckey} timestamps are not monotonically increasing"

        diffs = ts.diff().dropna()
        one_hour = pd.Timedelta(hours=1)
        non_one_hour = diffs[diffs != one_hour]
        assert len(non_one_hour) == 0, (
            f"{ckey} has {len(non_one_hour)} non-1-hour timestamp gaps! First: {non_one_hour.iloc[0] if len(non_one_hour) > 0 else 'None'}"
        )

        # Zero duplicates
        assert df["timestamp"].nunique() == EXPECTED_HOURS_PER_STATION, f"{ckey} contains duplicate timestamps"

        # Verify leap year vs non-leap year counts
        years = ts.dt.year
        leap_years = [1996, 2000, 2004, 2008, 2012, 2016, 2020, 2024]
        for yr in range(1995, 2026):
            yr_count = (years == yr).sum()
            expected_yr_hours = 8784 if yr in leap_years else 8760
            assert yr_count == expected_yr_hours, (
                f"{ckey} year {yr} expected {expected_yr_hours} hours, found {yr_count}"
            )


def test_decadal_zero_lookahead_leakage():
    """Verifies causal ordering and ensures no forward-looking lookahead leakage."""
    for ckey in EXPECTED_CITIES:
        master_csv = CSV_DIR / f"airsense_decadal_{ckey}_1995_2025.csv"
        df = pd.read_csv(master_csv)

        ts = pd.to_datetime(df["timestamp"])
        # Ensure chronological ordering index matches timestamp order
        assert (ts == ts.sort_values()).all(), f"{ckey} records violate strict chronological ordering"

        # Ensure no negative diffs (lookahead inversion)
        deltas = ts.diff().dropna()
        assert (deltas > pd.Timedelta(0)).all(), f"{ckey} contains backward time steps (lookahead)"


def test_decadal_physical_ranges_and_aerodynamic_relationships():
    """Verifies physical atmospheric ranges and strict aerodynamic hierarchy PM1 <= PM2.5 <= PM10."""
    for ckey in EXPECTED_CITIES:
        master_csv = CSV_DIR / f"airsense_decadal_{ckey}_1995_2025.csv"
        df = pd.read_csv(master_csv)

        # 1. Canonical columns contract
        for col in CANONICAL_COLUMNS:
            assert col in df.columns, f"Required column '{col}' missing from {ckey}"

        # 2. No NaN or null values
        assert df[CANONICAL_COLUMNS].isna().sum().sum() == 0, f"Null or NaN values found in {ckey}"

        # 3. Aerodynamic size hierarchy: PM1 <= PM2.5 <= PM10
        # Allow tiny float precision margin
        pm1_exceeds_pm25 = (df["pm1"] > df["pm2_5"] + 1e-4).sum()
        assert pm1_exceeds_pm25 == 0, f"{ckey} has {pm1_exceeds_pm25} rows where PM1 > PM2.5"

        pm25_exceeds_pm10 = (df["pm2_5"] > df["pm10"] + 1e-4).sum()
        assert pm25_exceeds_pm10 == 0, f"{ckey} has {pm25_exceeds_pm10} rows where PM2.5 > PM10"

        # 4. Strict non-negativity
        assert (df["pm1"] > 0).all(), f"{ckey} has non-positive PM1"
        assert (df["pm2_5"] > 0).all(), f"{ckey} has non-positive PM2.5"
        assert (df["pm10"] > 0).all(), f"{ckey} has non-positive PM10"

        # 5. Physical bounds
        assert df["pm2_5"].max() <= 1500.0, f"{ckey} PM2.5 max exceeds 1500 ug/m3: {df['pm2_5'].max()}"
        assert -15.0 <= df["temperature_c"].min() and df["temperature_c"].max() <= 55.0, (
            f"{ckey} temperature out of physical bounds: [{df['temperature_c'].min()}, {df['temperature_c'].max()}]"
        )
        assert 5.0 <= df["relative_humidity_pct"].min() and df["relative_humidity_pct"].max() <= 100.0, (
            f"{ckey} humidity out of physical bounds: [{df['relative_humidity_pct'].min()}, {df['relative_humidity_pct'].max()}]"
        )
        assert 0.0 <= df["wind_speed_kmh"].min() and df["wind_speed_kmh"].max() <= 120.0, (
            f"{ckey} wind speed out of physical bounds: [{df['wind_speed_kmh'].min()}, {df['wind_speed_kmh'].max()}]"
        )
        assert 0.0 <= df["wind_direction_deg"].min() and df["wind_direction_deg"].max() < 360.0, (
            f"{ckey} wind direction out of circular bounds: [{df['wind_direction_deg'].min()}, {df['wind_direction_deg'].max()}]"
        )
        assert 50.0 <= df["blh_m"].min() and df["blh_m"].max() <= 4000.0, (
            f"{ckey} BLH out of physical bounds: [{df['blh_m'].min()}, {df['blh_m'].max()}]"
        )
        assert (df["precipitation_mm"] >= 0.0).all(), f"{ckey} has negative precipitation"

        # 6. QA bitmask verification: bit 0 (value 1) must be set on all valid records
        assert ((df["qa_flag"] & 1) == 1).all(), f"{ckey} has records without bit 0 set in qa_flag"


def test_decadal_elevational_adjustment_quetta():
    """Verifies that Quetta's surface pressure correctly models high-altitude atmosphere (~830 hPa)."""
    quetta_csv = CSV_DIR / "airsense_decadal_quetta_1995_2025.csv"
    df_quetta = pd.read_csv(quetta_csv, usecols=["pressure_hpa"])
    mean_quetta_p = df_quetta["pressure_hpa"].mean()

    # Mandated elevational adjustment: Quetta altitude ~1,680m -> ~830 hPa surface pressure
    assert 820.0 <= mean_quetta_p <= 840.0, (
        f"Quetta mean pressure {mean_quetta_p:.2f} hPa violates elevational target (~830 hPa)"
    )
    assert df_quetta["pressure_hpa"].max() < 870.0, "Quetta pressure exceeds high-altitude ceiling"
    assert df_quetta["pressure_hpa"].min() > 790.0, "Quetta pressure drops below physical floor"

    # Contrast with sea-level Karachi
    karachi_csv = CSV_DIR / "airsense_decadal_karachi_1995_2025.csv"
    df_karachi = pd.read_csv(karachi_csv, usecols=["pressure_hpa"])
    mean_karachi_p = df_karachi["pressure_hpa"].mean()
    assert mean_karachi_p > 1005.0, f"Karachi sea-level pressure too low: {mean_karachi_p:.2f} hPa"
    assert mean_karachi_p - mean_quetta_p > 160.0, "Elevational pressure difference between Quetta and Karachi too small"


def test_decadal_sha256_checksums_verification():
    """Recomputes SHA-256 hashes of all data lake files and verifies 100% agreement with checksums.sha256."""
    assert CHECKSUMS_FILE.exists(), f"Checksum manifest not found at {CHECKSUMS_FILE}"

    with open(CHECKSUMS_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    assert len(lines) >= 190, f"Checksums manifest has fewer entries than expected: {len(lines)}"

    verified_count = 0
    for line in lines:
        parts = line.split(maxsplit=1)
        assert len(parts) == 2, f"Malformed checksum line: '{line}'"
        expected_hash, rel_path = parts[0], parts[1]

        file_path = DECADAL_DIR / Path(rel_path)
        assert file_path.exists(), f"File listed in checksums not found on disk: {file_path}"

        hasher = hashlib.sha256()
        with open(file_path, "rb") as bf:
            while chunk := bf.read(65536):
                hasher.update(chunk)
        computed_hash = hasher.hexdigest()

        assert computed_hash == expected_hash, (
            f"Checksum mismatch for {rel_path}: computed {computed_hash} != manifest {expected_hash}"
        )
        verified_count += 1

    assert verified_count == len(lines), "Not all checksum entries were verified"


def test_decadal_metadata_json_schema_and_manifest():
    """Validates the metadata manifest contents, total record tally, and station statistics."""
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["manifest_version"] == "1.0.0"
    assert meta["volume_summary"]["core_stations_count"] == 6
    assert meta["volume_summary"]["total_continuous_station_hours"] == EXPECTED_TOTAL_HOURS
    assert meta["volume_summary"]["threshold_exceeded"] is True
    assert meta["temporal_horizon"]["calendar_years"] == 31
    assert meta["temporal_horizon"]["total_days"] == 11323
    assert meta["temporal_horizon"]["hours_per_station"] == EXPECTED_HOURS_PER_STATION

    for ckey in EXPECTED_CITIES:
        assert ckey in meta["cities"], f"City {ckey} missing from metadata manifest"
        city_meta = meta["cities"][ckey]
        assert city_meta["total_records"] == EXPECTED_HOURS_PER_STATION
        assert city_meta["start_timestamp"] == EXPECTED_START_UTC
        assert city_meta["end_timestamp"] == EXPECTED_END_UTC
        assert "statistics" in city_meta
        assert city_meta["statistics"]["pm2_5_mean"] > 0


def test_decadal_parquet_snappy_compression_and_pyarrow():
    """Verifies that Parquet partitions can be read via PyArrow with Snappy compression intact."""
    for ckey in EXPECTED_CITIES:
        # Sample partition 2024 (leap year)
        pq_path = PARQUET_DIR / f"city={ckey}" / "year=2024" / f"airsense_{ckey}_2024.parquet"
        assert pq_path.exists(), f"Sample parquet partition missing: {pq_path}"

        # PyArrow table read
        table = pq.read_table(pq_path, partitioning=None)
        assert table.num_rows == 8784, f"Leap year 2024 for {ckey} expected 8,784 rows, got {table.num_rows}"

        # Verify Snappy compression codec on metadata
        pq_meta = pq.read_metadata(pq_path)
        col_chunk = pq_meta.row_group(0).column(0)
        assert col_chunk.compression.upper() == "SNAPPY", (
            f"Expected SNAPPY compression, got {col_chunk.compression}"
        )

        # Convert to pandas and check columns
        df_pq = table.to_pandas()
        for col in CANONICAL_COLUMNS:
            assert col in df_pq.columns, f"Column '{col}' missing from parquet schema in {ckey}"
