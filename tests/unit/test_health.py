"""Unit tests for FastAPI foundation health, readiness, version, and campus endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from apps.api.main import app
from apps.api.db.session import engine
from apps.api.db.models import Base, Campus
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from apps.api.core.config import settings


@pytest.fixture(autouse=True)
async def init_test_db():
    """Ensure database tables and campus records exist for test runs."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        res_isb = await session.execute(select(Campus).where(Campus.code == settings.ISLAMABAD_CAMPUS_CODE))
        if not res_isb.scalar_one_or_none():
            session.add(Campus(
                code=settings.ISLAMABAD_CAMPUS_CODE,
                name=settings.ISLAMABAD_CAMPUS_NAME,
                city="Islamabad",
                contact_name=settings.ISLAMABAD_CONTACT_NAME,
                status="configuration_required"
            ))

        res_khi = await session.execute(select(Campus).where(Campus.code == settings.KARACHI_CAMPUS_CODE))
        if not res_khi.scalar_one_or_none():
            session.add(Campus(
                code=settings.KARACHI_CAMPUS_CODE,
                name=settings.KARACHI_CAMPUS_NAME,
                city="Karachi",
                contact_name=settings.KARACHI_CONTACT_NAME,
                status="configuration_required"
            ))
        await session.commit()


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["process"] == "running"
        assert data["display_timezone"] == "Asia/Karachi"


@pytest.mark.asyncio
async def test_readiness_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"
        assert data["pilots"]["islamabad"]["contact"] == "Muhammad M. Qureshi"
        assert data["pilots"]["karachi"]["contact"] == "Areesha"


@pytest.mark.asyncio
async def test_version_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/version")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "AirSense Pakistan"
        assert "Islamabad" in data["pilots"]
        assert "Karachi" in data["pilots"]


@pytest.mark.asyncio
async def test_campuses_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/campuses")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        codes = [c["code"] for c in data]
        assert "ISB_CAMPUS" in codes
        assert "KHI_CAMPUS" in codes
