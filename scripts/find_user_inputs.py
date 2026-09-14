import json
from pathlib import Path

p = Path(r"C:\Users\HP\.gemini\antigravity\brain\e303e424-1532-4a94-a73b-0d3dd4070224\.system_generated\logs\transcript.jsonl")

for idx, line in enumerate(open(p, encoding='utf-8', errors='replace')):
    try:
        data = json.loads(line)
        if data.get('type') == 'USER_INPUT':
            print(f"\n--- USER INPUT at line {idx}, step {data.get('step_index')} ---")
            print(data.get('content'))
    except Exception:
        pass
