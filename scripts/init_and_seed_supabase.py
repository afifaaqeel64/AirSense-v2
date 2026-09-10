"""AirSense Pakistan - Supabase Database Initialization & Pilot Metadata Seeder."""

import asyncio
import sys
from pathlib import Path

# Ensure root directory is on Python sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from apps.api.core.config import settings
from apps.api.core.security import hash_token
from apps.api.db.session import engine, Base
from apps.api.db.models import Campus, Station, Device


async def init_schema_and_seed():
    print(f"[AirSense] Initializing tables on database: {engine.url}...")
    
    # 1. Create all tables defined in Base.metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[AirSense] Schema tables successfully created via Base.metadata.create_all.")

    # 2. Seed pilot campuses, stations, and devices
    async with engine.connect() as conn:
        async with AsyncSession(conn) as session:
            # Islamabad Campus
            res_isb = await session.execute(select(Campus).where(Campus.code == settings.ISLAMABAD_CAMPUS_CODE))
            isb = res_isb.scalar_one_or_none()
            if not isb:
                isb = Campus(
                    code=settings.ISLAMABAD_CAMPUS_CODE,
                    name=settings.ISLAMABAD_CAMPUS_NAME,
                    city="Islamabad",
                    contact_name=settings.ISLAMABAD_CONTACT_NAME,
                    latitude=33.6844,
                    longitude=73.0479,
                    status="active",
                    location_status="verified"
                )
                session.add(isb)
                await session.flush()
                print(f"[AirSense] Seeded Campus: {isb.name} ({isb.code})")
            else:
                print(f"[AirSense] Campus already exists: {isb.name} ({isb.code})")

            # Karachi Campus
            res_khi = await session.execute(select(Campus).where(Campus.code == settings.KARACHI_CAMPUS_CODE))
            khi = res_khi.scalar_one_or_none()
            if not khi:
                khi = Campus(
                    code=settings.KARACHI_CAMPUS_CODE,
                    name=settings.KARACHI_CAMPUS_NAME,
                    city="Karachi",
                    contact_name=settings.KARACHI_CONTACT_NAME,
                    latitude=24.8607,
                    longitude=67.0011,
                    status="active",
                    location_status="verified"
                )
                session.add(khi)
                await session.flush()
                print(f"[AirSense] Seeded Campus: {khi.name} ({khi.code})")
            else:
                print(f"[AirSense] Campus already exists: {khi.name} ({khi.code})")

            # Karachi BIC Station: BIC-KHI-ROOF-01
            res_st = await session.execute(select(Station).where(Station.station_code == "BIC-KHI-ROOF-01"))
            st_khi = res_st.scalar_one_or_none()
            if not st_khi and khi:
                st_khi = Station(
                    campus_id=khi.id,
                    station_code="BIC-KHI-ROOF-01",
                    station_name="Karachi BIC Rooftop Station",
                    installation_location="BIC Rooftop",
                    latitude=24.8607,
                    longitude=67.0011,
                    elevation_m=20.0,
                    status="active",
                    sampling_interval_seconds=60,
                    firmware_version="v3.5.0-PROD"
                )
                session.add(st_khi)
                await session.flush()
                print(f"[AirSense] Seeded Station: {st_khi.station_name} ({st_khi.station_code})")
            else:
                print(f"[AirSense] Station already exists: {st_khi.station_name} ({st_khi.station_code})")

            # Default Registered ESP32 Device: AIRSENSE-NODE-KHI-01
            raw_token = "airsense_dev_token_khi_01"
            dev_hash = hash_token(raw_token)
            res_dev = await session.execute(select(Device).where(Device.device_uid == "AIRSENSE-NODE-KHI-01"))
            dev = res_dev.scalar_one_or_none()
            if not dev and st_khi:
                dev = Device(
                    station_id=st_khi.id,
                    device_uid="AIRSENSE-NODE-KHI-01",
                    device_type="ESP32_WROOM_32D",
                    model="AirSense Station V1",
                    token_hash=dev_hash,
                    firmware_version="v3.5.0-PROD",
                    status="active"
                )
                session.add(dev)
                await session.flush()
                print(f"[AirSense] Seeded Device: {dev.device_uid} (Token: {raw_token})")
            else:
                if dev:
                    dev.token_hash = dev_hash
                    print(f"[AirSense] Device exists, refreshed token hash for {dev.device_uid}")

            await session.commit()

    # 3. Verify public tables in Supabase
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"))
        tables = [r[0] for r in res.fetchall()]
        print(f"\n[AirSense] Total initialized tables in Supabase ({len(tables)}):")
        for t in tables:
            print(f"  - {t}")

        # Verify seeded records count
        c_count = await conn.execute(text("SELECT count(*) FROM campuses;"))
        s_count = await conn.execute(text("SELECT count(*) FROM stations;"))
        d_count = await conn.execute(text("SELECT count(*) FROM devices;"))
        print(f"\n[AirSense] Seed Verification:")
        print(f"  Campuses count: {c_count.scalar()}")
        print(f"  Stations count: {s_count.scalar()}")
        print(f"  Devices count:  {d_count.scalar()}")
        print("\n[AirSense] Initialization & pilot seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(init_schema_and_seed())
