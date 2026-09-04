"""Unit tests for BackupService and Backup API."""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from apps.api.main import app
from apps.api.core.config import settings
from apps.api.db.session import engine
from apps.api.db.models import Base
from services.backup.backup_service import BackupService


@pytest.fixture(autouse=True)
async def init_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.mark.asyncio
async def test_backup_service_creation_and_verification():
    async with engine.connect() as conn:
        async with AsyncSession(conn) as session:
            res = await BackupService.create_backup(session, description="Unit test backup")
            assert res["status"] == "success"
            assert "backup_id" in res
            backup_id = res["backup_id"]

            ver = BackupService.verify_backup(backup_id)
            assert ver["status"] == "valid"
            assert ver["backup_id"] == backup_id
            assert "table_counts" in ver["manifest"]


@pytest.mark.asyncio
async def test_backup_api_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = settings.ADMIN_API_TOKEN
        headers = {"X-Admin-Token": token}

        # 1. Create backup via API
        create_res = await client.post("/api/v1/admin/backups", json={"description": "API Test Backup"}, headers=headers)
        assert create_res.status_code == 200
        c_data = create_res.json()
        assert c_data["status"] == "success"
        backup_id = c_data["backup_id"]

        # 2. List backups via API
        list_res = await client.get("/api/v1/admin/backups", headers=headers)
        assert list_res.status_code == 200
        b_list = list_res.json()
        assert any(b["backup_id"] == backup_id for b in b_list)

        # 3. Verify backup via API
        verify_res = await client.get(f"/api/v1/admin/backups/{backup_id}/verify", headers=headers)
        assert verify_res.status_code == 200
        v_data = verify_res.json()
        assert v_data["status"] == "valid"
