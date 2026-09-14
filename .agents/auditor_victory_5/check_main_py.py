with open("apps/api/main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if any(k in line for k in ["favicon", "apple-touch-icon", "site.webmanifest", "logo-files", "StaticFiles"]):
        start = max(0, i - 2)
        end = min(len(lines), i + 15)
        print(f"--- Around line {i+1} ---")
        for j in range(start, end):
            print(f"{j+1:4d}: {lines[j]}", end="")
        print("\n" + "="*40 + "\n")
