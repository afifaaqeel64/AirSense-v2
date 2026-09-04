"""AirSense Pakistan Database Engine & Session Factory."""

import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from apps.api.core.config import settings

# Normalize database URL for PostgreSQL asyncpg compatibility
normalized_db_url = settings.DATABASE_URL
if normalized_db_url.startswith("postgres://"):
    normalized_db_url = normalized_db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif normalized_db_url.startswith("postgresql://") and not normalized_db_url.startswith("postgresql+"):
    normalized_db_url = normalized_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Ensure sqlite data directory exists if using SQLite
if "sqlite" in normalized_db_url:
    db_path = normalized_db_url.replace("sqlite+aiosqlite:///", "")
    if db_path.startswith("./"):
        db_path = db_path[2:]
    parent_dir = Path(db_path).parent
    if not parent_dir.exists():
        parent_dir.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(
    normalized_db_url,
    echo=settings.DEBUG,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
