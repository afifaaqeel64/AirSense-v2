import asyncio
import asyncpg

async def main():
    db_url = "postgresql://postgres.vppczkvawiaptiygrqhx:7EZgyMcqYi%269qUE@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres"
    conn = await asyncpg.connect(db_url)
    rows = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
    print("Tables in public schema:")
    for r in rows:
        print(" -", r["table_name"])
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
