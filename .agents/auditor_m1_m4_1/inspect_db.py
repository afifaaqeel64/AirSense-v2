import sqlite3
import json

conn = sqlite3.connect('data/airsense.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
stats = {}
for t in tables:
    c.execute(f"SELECT count(*) FROM {t}")
    stats[t] = c.fetchone()[0]

print("AirSense SQLite DB Table Statistics:")
print(json.dumps(stats, indent=2))
conn.close()
