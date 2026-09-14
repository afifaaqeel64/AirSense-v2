import sqlite3
conn = sqlite3.connect("data/airsense.db")
cur = conn.cursor()
for tbl in ["campuses", "stations", "devices"]:
    print(f"\n--- {tbl} ---")
    cur.execute(f"SELECT * FROM {tbl}")
    rows = cur.fetchall()
    print(f"Total: {len(rows)}")
    for r in rows:
        print(" ", r)
conn.close()
