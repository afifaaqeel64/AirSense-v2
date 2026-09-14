import sqlite3

conn = sqlite3.connect("data/airsense.db")
cursor = conn.cursor()
tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print(f"Total tables: {len(tables)}")
print(f"Tables: {tables}")
for t in tables:
    count = cursor.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t}: {count} rows")
conn.close()
