import os
import sys
import asyncio
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from httpx import AsyncClient, ASGITransport
from apps.api.main import app as main_app
from scripts.serve_enterprise import app as enterprise_app



async def test_main_api():
    print("--- Testing Main FastAPI Application (Port 8000 Interface) ---")
    transport = ASGITransport(app=main_app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
        # 1. Root / Control Center HTML
        r_root = await client.get("/")
        print(f"GET / : status={r_root.status_code}, length={len(r_root.text)}, title in html={'AirSense' in r_root.text}")
        assert r_root.status_code == 200
        assert "AirSense" in r_root.text

        # 2. Ops Dashboard
        r_ops = await client.get("/ops")
        print(f"GET /ops : status={r_ops.status_code}")
        assert r_ops.status_code == 200

        # 3. Enterprise Route
        r_ent = await client.get("/enterprise")
        print(f"GET /enterprise : status={r_ent.status_code}")
        assert r_ent.status_code == 200

        # 4. Swagger UI /docs
        r_docs = await client.get("/docs")
        print(f"GET /docs : status={r_docs.status_code}")
        assert r_docs.status_code == 200

        # 5. OpenAPI JSON schema
        r_openapi = await client.get("/openapi.json")
        print(f"GET /openapi.json : status={r_openapi.status_code}, paths_count={len(r_openapi.json().get('paths', {}))}")
        assert r_openapi.status_code == 200
        assert len(r_openapi.json().get("paths", {})) >= 10

        # 6. Health & Readiness
        r_health = await client.get("/api/v1/health")
        print(f"GET /api/v1/health : status={r_health.status_code}, data={r_health.json()}")
        assert r_health.status_code == 200
        assert r_health.json()["status"] == "healthy"

        r_ready = await client.get("/api/v1/ready")
        print(f"GET /api/v1/ready : status={r_ready.status_code}, status_val={r_ready.json()['status']}")
        assert r_ready.status_code == 200

        r_version = await client.get("/api/v1/version")
        print(f"GET /api/v1/version : status={r_version.status_code}, version={r_version.json()['version']}")
        assert r_version.status_code == 200

        # 7. Ingest latest
        r_latest = await client.get("/api/v1/ingest/latest?limit=5")
        print(f"GET /api/v1/ingest/latest : status={r_latest.status_code}, items_count={len(r_latest.json())}")
        assert r_latest.status_code == 200

        # 8. Campuses
        r_campuses = await client.get("/api/v1/campuses")
        print(f"GET /api/v1/campuses : status={r_campuses.status_code}, campuses_count={len(r_campuses.json())}")
        assert r_campuses.status_code == 200


async def test_enterprise_service():
    print("\n--- Testing Dedicated Enterprise Service (Port 8080 Interface) ---")
    transport = ASGITransport(app=enterprise_app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1:8080") as client:
        # 1. Root / Enterprise HTML
        r_root = await client.get("/")
        print(f"GET / : status={r_root.status_code}, cache_header={r_root.headers.get('cache-control')}")
        assert r_root.status_code == 200
        assert "no-cache" in r_root.headers.get("cache-control", "")
        assert "AirSense" in r_root.text

        # 2. Enterprise Route
        r_ent = await client.get("/enterprise")
        print(f"GET /enterprise : status={r_ent.status_code}")
        assert r_ent.status_code == 200


async def main():
    await test_main_api()
    await test_enterprise_service()
    print("\n=======================================================")
    print("ALL OPERATIONAL SERVER STARTUP & ROUTE CHECKS PASSED!")
    print("=======================================================")


if __name__ == "__main__":
    asyncio.run(main())
