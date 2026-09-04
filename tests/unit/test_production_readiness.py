"""AirSense Pakistan Phase 2 Production-Readiness Automated Test Suite.

Tests:
1. Security headers & OWASP compliance middleware
2. Rate-limiting protection on sensitive endpoints
3. Liveness, readiness, and Prometheus-compatible metrics endpoints
4. Enterprise backup service, SHA-256 validation, and disaster recovery restore
5. 24/7 background scheduler lifecycle and state reporting
"""

import pytest
import sqlite3
import hashlib
from pathlib import Path
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.core.config import settings
from services.backup_service import BackupService, compute_sha256
from services.background_scheduler import BackgroundScheduler
from services.security_middleware import rate_limiter


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_production_security_headers(client):
    """Verifies that security headers are injected into HTTP responses."""
    response = client.get("/api/v1/health/liveness")
    assert response.status_code == 200
    headers = response.headers

    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert "X-Process-Time-Ms" in headers
    assert float(headers["X-Process-Time-Ms"]) >= 0.0


def test_liveness_probe(client):
    """Verifies basic process liveness probe."""
    response = client.get("/api/v1/health/liveness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["process"] == "running"
    assert "timestamp_utc" in data


def test_readiness_probe(client):
    """Verifies deep readiness probe inspecting database, disk, and scheduler."""
    response = client.get("/api/v1/health/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"]["connected"] is True
    assert data["storage"]["disk_writable"] is True
    assert "background_scheduler" in data
    assert "pilots" in data


def test_system_metrics_endpoint(client):
    """Verifies system diagnostics and monitoring metrics endpoint."""
    response = client.get("/api/v1/health/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "database" in data
    assert "total_raw_readings" in data["database"]
    assert "background_workers" in data
    assert "environment" in data


def test_rate_limiter_sliding_window():
    """Verifies sliding window rate limiter triggers on excess requests."""
    test_key = "unit_test_ip_123"
    # Allow up to 5 requests
    for _ in range(5):
        allowed, rem = rate_limiter.is_allowed(test_key, max_requests=5, window_seconds=10)
        assert allowed is True

    # 6th request should be blocked
    allowed, rem = rate_limiter.is_allowed(test_key, max_requests=5, window_seconds=10)
    assert allowed is False
    assert rem == 0


def test_backup_service_atomic_snapshot_and_restore(tmp_path):
    """Verifies end-to-end atomic database snapshot, compression, checksum, and restore."""
    # 1. Create a dummy SQLite database with a sample table
    test_db = tmp_path / "test_airsense.db"
    conn = sqlite3.connect(test_db)
    cur = conn.cursor()
    cur.execute("CREATE TABLE test_station (id INTEGER PRIMARY KEY, name TEXT);")
    cur.execute("INSERT INTO test_station (name) VALUES ('BIC_ROOF_01');")
    conn.commit()
    conn.close()

    # 2. Run backup on test_db
    backup_result = BackupService.create_sqlite_backup(source_db_path=test_db, retention_count=5)
    assert backup_result["status"] == "success"
    assert backup_result["compressed_bytes"] > 0
    assert "test_station" in backup_result["tables_snapshotted"]

    backup_file = backup_result["backup_file"]
    backup_path = Path(backup_result["backup_path"])
    assert backup_path.exists()

    # 3. Verify SHA-256 match
    computed_sha = compute_sha256(backup_path)
    assert computed_sha == backup_result["sha256"]

    # 4. Restore into a new sandbox path
    restored_db = tmp_path / "restored_airsense.db"
    restore_result = BackupService.verify_and_restore(
        backup_filename=backup_file,
        target_db_path=restored_db,
        create_safety_snapshot=False
    )
    assert restore_result["status"] == "success"
    assert restore_result["verified_ok"] is True

    # 5. Verify restored data
    r_conn = sqlite3.connect(restored_db)
    r_cur = r_conn.cursor()
    r_cur.execute("SELECT name FROM test_station WHERE id=1;")
    row = r_cur.fetchone()
    assert row[0] == "BIC_ROOF_01"
    r_conn.close()


def test_background_scheduler_status():
    """Verifies background scheduler status reporting."""
    scheduler = BackgroundScheduler.get_instance()
    status = scheduler.get_status()
    assert "is_running" in status
    assert "active_workers" in status
    assert "execution_stats" in status
