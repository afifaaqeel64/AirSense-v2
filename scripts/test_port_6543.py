import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.api.core.config import settings
from apps.api.db.session import normalize_database_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    u = normalize_database_url(settings.DATABASE_URL)
    u6543 = u.replace(':5432', ':6543')
    print("Testing connection on port 6543 (Transaction Pooler)...")
    
    eng = create_async_engine(
        u6543,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0},
        pool_size=1,
        max_overflow=0
    )
    
    try:
        async with eng.connect() as conn:
            res = await conn.execute(text("SELECT count(*) FROM raw_readings"))
            print("SUCCESS ON PORT 6543! Raw readings count:", res.scalar())
    except Exception as e:
        print("Failed on 6543:", e)
    finally:
        await eng.dispose()

if __name__ == "__main__":
    asyncio.run(main())
