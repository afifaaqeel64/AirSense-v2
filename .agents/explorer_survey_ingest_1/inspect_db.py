import sqlite3
import os

print("=== CHECKING SQLITE DATABASES ===")
for path in ["data/airsense.db", "airsense.db"]:
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"\nDatabase: {path} ({size:,} bytes)")
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cur.fetchall()
        for (tbl,) in tables:
            cur.execute(f"SELECT COUNT(*) FROM \"{tbl}\"")
            count = cur.fetchone()[0]
            print(f"  Table '{tbl}': {count:,} rows")
            cur.execute(f"PRAGMA table_info(\"{tbl}\")")
            cols = [f"{c[1]} ({c[2]})" for c in cur.fetchall()]
            print(f"    Columns: {', '.join(cols)}")
        conn.close()
    else:
        print(f"\nDatabase: {path} DOES NOT EXIST")
