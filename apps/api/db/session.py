"""AirSense Pakistan Database Engine & Session Factory."""

import os
import socket
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, quote_plus, unquote_plus
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from apps.api.core.config import settings


def normalize_database_url(raw_url: str | None) -> str:
    """Normalize database URL for asyncpg / aiosqlite compatibility, handling
    scheme prefixes, password escaping, and Supabase IPv4 fallback.
    """
    if not raw_url or not raw_url.strip():
        return "sqlite+aiosqlite:///./data/airsense.db"

    url = raw_url.strip()

    # Normalize driver scheme
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # SQLite handling
    if "sqlite" in url:
        return url

    # Parse PostgreSQL URL to ensure password encoding and handle IPv4/IPv6 compatibility
    try:
        parsed = urlsplit(url)
        username = parsed.username or ""
        password = parsed.password or ""
        hostname = parsed.hostname or ""
        port = parsed.port or 5432
        path = parsed.path or "/postgres"
        query = parsed.query

        # URL-encode password properly (idempotent if already %-encoded)
        if password:
            encoded_password = quote_plus(unquote_plus(password))
        else:
            encoded_password = ""

        # Supabase hostname handling:
        # Supabase direct host (db.<project-ref>.supabase.co) only provides IPv6 records.
        # On IPv4-only networks or environments without IPv6 egress (such as Vercel Serverless
        # and AWS Lambda), direct connection fails. In those cases, automatically route through
        # the Supabase connection pooler on port 5432.
        if hostname and hostname.startswith("db.") and hostname.endswith(".supabase.co"):
            use_pooler = False
            if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or os.environ.get("FORCE_SUPABASE_POOLER"):
                use_pooler = True
            else:
                try:
                    # Test whether direct connection is actually reachable
                    with socket.create_connection((hostname, port), timeout=0.8):
                        pass
                except (socket.error, OSError):
                    use_pooler = True

            if use_pooler:
                parts = hostname.split(".")
                project_ref = parts[1] if len(parts) > 1 else "vppczkvawiaptiygrqhx"
                # Route through regional Supavisor transaction pooler (port 6543) to prevent session exhaustion (EMAXCONNSESSION)
                pooler_host = os.environ.get("SUPABASE_POOLER_HOST") or "aws-0-ap-northeast-2.pooler.supabase.com"
                pooler_port = int(os.environ.get("SUPABASE_POOLER_PORT") or 6543)
                hostname = pooler_host
                port = pooler_port
                if not username.endswith(f".{project_ref}"):
                    username = f"{username}.{project_ref}" if username else f"postgres.{project_ref}"

        # Reconstruct netloc
        netloc = ""
        if username:
            netloc += quote_plus(unquote_plus(username))
            if encoded_password:
                netloc += f":{encoded_password}"
            netloc += "@"
        netloc += hostname
        if port:
            netloc += f":{port}"

        return urlunsplit((parsed.scheme, netloc, path, query, parsed.fragment))
    except Exception:
        return url


# Normalize database URL for PostgreSQL asyncpg compatibility
normalized_db_url = normalize_database_url(settings.DATABASE_URL)

# Ensure sqlite data directory exists if using SQLite
if "sqlite" in normalized_db_url:
    db_path = normalized_db_url.replace("sqlite+aiosqlite:///", "")
    if db_path.startswith("./"):
        db_path = db_path[2:]
    parent_dir = Path(db_path).parent
    if not parent_dir.exists():
        parent_dir.mkdir(parents=True, exist_ok=True)

# Connection arguments for asyncpg
connect_args = {}
if "pooler.supabase.com" in normalized_db_url or ":6543" in normalized_db_url:
    # Transaction pooler mode requires disabling prepared statement cache in asyncpg
    connect_args["statement_cache_size"] = 0
    connect_args["prepared_statement_cache_size"] = 0

engine = create_async_engine(
    normalized_db_url,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    connect_args=connect_args
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Alias for background scheduler and service tasks
async_session_maker = AsyncSessionLocal


class Base(DeclarativeBase):
    pass


async def get_db_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
