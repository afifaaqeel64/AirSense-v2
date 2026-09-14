import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.api.core.config import settings
from apps.api.db.session import normalize_database_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from apps.api.db.models import RawReading

async def main():
    u = normalize_database_url(settings.DATABASE_URL)
    u6543 = u.replace(':5432', ':6543')
    
    eng = create_async_engine(
        u6543,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0},
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5
    )
    
    session_factory = async_sessionmaker(bind=eng, class_=AsyncSession, expire_on_commit=False)
    
    async with session_factory() as session:
        stmt = select(RawReading).order_by(RawReading.observed_at.desc()).limit(3)
        res = await session.execute(stmt)
        readings = res.scalars().all()
        print(f"Retrieved {len(readings)} latest readings:")
        for r in readings:
            print(f"  ID={r.id}, observed_at={r.observed_at}, pm25={r.pm2_5}, temp={r.temperature_c}")

    await eng.dispose()
    print("All ORM queries completed successfully on port 6543!")

if __name__ == "__main__":
    asyncio.run(main())
