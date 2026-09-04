"""Unit tests to verify synthetic sample data files and contract assertions."""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def test_json_sample_payload():
    path = BASE_DIR / "data" / "samples" / "example_sensor_payload.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "_comment" in data
    assert "SYNTHETIC EXAMPLE DATA ONLY" in data["_comment"]
    assert data["campus_code"] == "ISB_CAMPUS"
    assert "readings" in data
    assert "pm25" in data["readings"]


def test_csv_sample_readings():
    path = BASE_DIR / "data" / "samples" / "example_sensor_readings.csv"
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "SYNTHETIC EXAMPLE DATA ONLY" in content
    assert "ISB_CAMPUS" in content
    assert "KHI_CAMPUS" in content
