"""Integration and Unit Tests for Supabase Live PostgreSQL Connection & URL Normalization."""

import os
import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from apps.api.db.session import normalize_database_url


def get_test_supabase_url() -> str:
    return (
        os.environ.get("SAVED_DATABASE_URL")
        or os.environ.get("SUPABASE_DATABASE_URL")
        or "postgresql://postgres:7EZgyMcqYi%269qUE@db.vppczkvawiaptiygrqhx.supabase.co:5432/postgres"
    )


def test_normalize_database_url_handling():
    """Verifies that normalize_database_url correctly handles all variants."""
    # 1. Raw ampersand in password
    raw_url = "postgresql://postgres:7EZgyMcqYi&9qUE@db.vppczkvawiaptiygrqhx.supabase.co:5432/postgres"
    norm = normalize_database_url(raw_url)
    assert norm.startswith("postgresql+asyncpg://")
    assert "7EZgyMcqYi%269qUE" in norm

    # 2. Already percent-encoded ampersand
    encoded_url = "postgresql://postgres:7EZgyMcqYi%269qUE@db.vppczkvawiaptiygrqhx.supabase.co:5432/postgres"
    norm_enc = normalize_database_url(encoded_url)
    assert norm_enc.startswith("postgresql+asyncpg://")
    assert "7EZgyMcqYi%269qUE" in norm_enc
    assert "7EZgyMcqYi%25269qUE" not in norm_enc  # No double encoding

    # 3. postgres:// scheme conversion
    pg_url = "postgres://user:pass@localhost:5432/db"
    assert normalize_database_url(pg_url).startswith("postgresql+asyncpg://")

    # 4. SQLite preservation
    sqlite_url = "sqlite+aiosqlite:///./data/airsense.db"
    assert normalize_database_url(sqlite_url) == sqlite_url

    # 5. Empty / None fallback
    assert "sqlite+aiosqlite:///" in normalize_database_url("")
    assert "sqlite+aiosqlite:///" in normalize_database_url(None)

    # 6. Vercel environment detection
    os.environ["VERCEL"] = "1"
    try:
        norm_vercel = normalize_database_url(raw_url)
        assert "pooler.supabase.com" in norm_vercel
    finally:
        del os.environ["VERCEL"]

    # 7. Custom SUPABASE_POOLER_HOST
    os.environ["SUPABASE_POOLER_HOST"] = "aws-0-ap-south-1.pooler.supabase.com"
    try:
        norm_custom = normalize_database_url(raw_url)
        assert "aws-0-ap-south-1.pooler.supabase.com" in norm_custom
    finally:
        del os.environ["SUPABASE_POOLER_HOST"]


@pytest.mark.asyncio
async def test_live_supabase_connectivity():
    """Tests live connection to the Supabase PostgreSQL database."""
    supabase_url = get_test_supabase_url()
    norm_url = normalize_database_url(supabase_url)
    
    test_engine = create_async_engine(norm_url, pool_pre_ping=True)
    async with test_engine.connect() as conn:
        res = await conn.execute(text("SELECT version();"))
        ver = res.scalar()
        assert "PostgreSQL" in ver
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_live_supabase_schema_tables():
    """Tests that all required AirSense schema tables exist in the live Supabase database."""
    supabase_url = get_test_supabase_url()
    norm_url = normalize_database_url(supabase_url)
    
    expected_tables = {
        "campuses",
        "stations",
        "devices",
        "raw_readings",
        "quality_assessments",
        "observations",
        "hourly_observations",
        "maintenance_events",
        "import_batches",
        "external_provider_runs",
        "model_runs",
        "model_validation_folds",
        "predictions",
        "model_explanations",
        "model_promotion_events",
        "external_comparisons",
        "evaluation_events",
    }
    
    test_engine = create_async_engine(norm_url, pool_pre_ping=True)
    async with test_engine.connect() as conn:
        res = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
        ))
        existing_tables = set(r[0] for r in res.fetchall())
        missing = expected_tables - existing_tables
        assert not missing, f"Missing tables in Supabase: {missing}"
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_live_supabase_pilot_metadata():
    """Tests that seeded pilot station metadata exists and is active on Supabase."""
    supabase_url = get_test_supabase_url()
    norm_url = normalize_database_url(supabase_url)
    
    test_engine = create_async_engine(norm_url, pool_pre_ping=True)
    async with test_engine.connect() as conn:
        # Check campus
        res_camp = await conn.execute(text("SELECT name, status FROM campuses WHERE code = 'KHI_CAMPUS';"))
        camp = res_camp.fetchone()
        assert camp is not None
        assert camp[1] == "active"

        # Check station BIC-KHI-ROOF-01
        res_stn = await conn.execute(text("SELECT station_name, status FROM stations WHERE station_code = 'BIC-KHI-ROOF-01';"))
        stn = res_stn.fetchone()
        assert stn is not None
        assert stn[1] == "active"

        # Check device AIRSENSE-NODE-KHI-01
        res_dev = await conn.execute(text("SELECT device_uid, status FROM devices WHERE device_uid = 'AIRSENSE-NODE-KHI-01';"))
        dev = res_dev.fetchone()
        assert dev is not None
        assert dev[1] == "active"
    await test_engine.dispose()
