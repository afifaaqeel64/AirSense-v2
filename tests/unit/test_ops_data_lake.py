import os
import json
import tempfile
import pytest
from datetime import datetime, timezone

from pipelines.ops_data_lake_manager import OpsDataLakeManager

def test_d_drive_enforcement_raises_on_c_drive():
    """Verify D: drive path validation raises PermissionError when given a C: drive path."""
    with pytest.raises(PermissionError) as excinfo:
        OpsDataLakeManager(base_path="C:/Users/Source Machinery/AirSense/data/ops")
    assert "violates D: drive isolation constraint" in str(excinfo.value)

    with pytest.raises(PermissionError) as excinfo2:
        OpsDataLakeManager(base_path="C:/tmp/lake")
    assert "violates D: drive isolation constraint" in str(excinfo2.value)

def test_d_drive_target_path_assertion():
    """Verify target file path assertion raises PermissionError on non-D drive paths."""
    mgr = OpsDataLakeManager()
    with pytest.raises(PermissionError) as excinfo:
        mgr._assert_d_drive("C:/Windows/Temp/payload.json")
    assert "violates D: drive isolation constraint" in str(excinfo.value)

    # Valid D: drive path must succeed without error
    mgr._assert_d_drive("D:/MUNIM - UOE @BIC/AirSense/data/ops/test.json")

def test_tempfile_isolation_to_d_drive():
    """Verify tempfile.gettempdir() and TEMP/TMP/TMPDIR environment variables point to D: drive."""
    mgr = OpsDataLakeManager()
    
    temp_dir = tempfile.gettempdir()
    assert temp_dir.lower().startswith("d:"), f"tempfile.tempdir '{temp_dir}' must point to D: drive"
    assert os.environ.get("TEMP", "").lower().startswith("d:"), "TEMP environment variable must point to D: drive"
    assert os.environ.get("TMP", "").lower().startswith("d:"), "TMP environment variable must point to D: drive"
    assert os.environ.get("TMPDIR", "").lower().startswith("d:"), "TMPDIR environment variable must point to D: drive"
    assert os.path.exists(mgr.tmp_dir), f"Temporary directory '{mgr.tmp_dir}' must exist on D: drive"
    assert os.path.exists(mgr.cache_dir), f"Cache directory '{mgr.cache_dir}' must exist on D: drive"

def test_store_raw_scrape_date_partitioning():
    """Verify store_raw_scrape partitions files into YYYY-MM-DD subdirectories."""
    mgr = OpsDataLakeManager()
    today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    unique_text = f"EPA_ORDER_UNIT_TEST_{datetime.now(timezone.utc).timestamp()}"
    raw_payload = {
        "raw_text": unique_text,
        "target_url": "https://epd.punjab.gov.pk/test",
        "scraped_at": datetime.now(timezone.utc).isoformat()
    }
    
    saved_path = mgr.store_raw_scrape("epa_gazettes", raw_payload)
    assert saved_path.lower().startswith("d:"), f"Saved path '{saved_path}' must be on D: drive"
    assert f"/{today_utc}/" in saved_path.replace("\\", "/"), f"Expected date partition '/{today_utc}/' in path '{saved_path}'"
    assert os.path.exists(saved_path), f"Saved raw file '{saved_path}' does not exist on disk"
    
    with open(saved_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert data["domain"] == "epa_gazettes"
    assert "checksum" in data
    assert data["payload"]["raw_text"] == unique_text
    assert "scraped_at_utc" in data

def test_sha256_deduplication_suppresses_duplicate_writes():
    """Verify SHA-256 deduplication suppresses duplicate file creation for identical payloads."""
    mgr = OpsDataLakeManager()
    fixed_text = "FIXED_DEDUPLICATION_TEST_PAYLOAD_SECTION_144"
    raw_payload = {
        "raw_text": fixed_text,
        "target_url": "https://nhmp.gov.pk/test",
        "scraped_at": datetime.now(timezone.utc).isoformat()
    }
    
    path1 = mgr.store_raw_scrape("motorway_traffic", raw_payload)
    path2 = mgr.store_raw_scrape("motorway_traffic", raw_payload)
    
    assert path1 == path2, f"Expected duplicate payload to return identical file path, got '{path1}' vs '{path2}'"

def test_store_normalized_notice_and_legacy_mirror():
    """Verify store_normalized_notice writes to normalized_lake and mirrors to policy_lake on D: drive."""
    mgr = OpsDataLakeManager()
    event_id = f"TEST_NORM_{int(datetime.now(timezone.utc).timestamp())}"
    notice_data = {
        "event_id": event_id,
        "domain": "education_circulars",
        "raw_text": "School winter closure notification",
        "event_type": "Closure",
        "affected_sectors": ["Education"],
        "extracted_lead_time_hours": 48
    }
    
    saved_path = mgr.store_normalized_notice("education_circulars", notice_data)
    assert saved_path.lower().startswith("d:")
    assert os.path.exists(saved_path)
    
    legacy_path = os.path.join(mgr.policy_lake, f"{event_id}.json").replace("\\", "/")
    assert legacy_path.lower().startswith("d:")
    assert os.path.exists(legacy_path)

def test_get_storage_stats_recursive_count():
    """Verify get_storage_stats audits all 8 domains recursively across date partition folders."""
    mgr = OpsDataLakeManager()
    stats = mgr.get_storage_stats()
    
    assert "d_drive_root" in stats
    assert "domains" in stats
    assert len(stats["domains"]) == 8
    
    for domain in mgr.DOMAINS:
        assert domain in stats["domains"], f"Missing domain '{domain}' in storage statistics"
        assert stats["domains"][domain]["raw_scrapes"] >= 0
        assert stats["domains"][domain]["normalized_notices"] >= 0
