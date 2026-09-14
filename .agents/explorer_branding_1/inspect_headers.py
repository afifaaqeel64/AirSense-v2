import re

paths = [
    r"c:\Users\HP\AirSense-v2\public\index.html",
    r"c:\Users\HP\AirSense-v2\public\hardware.html",
    r"c:\Users\HP\AirSense-v2\public\diagnostics.html",
    r"c:\Users\HP\AirSense-v2\public\sensor-health.html",
    r"c:\Users\HP\AirSense-v2\public\command.html",
    r"c:\Users\HP\AirSense-v2\public\opensource.html",
    r"c:\Users\HP\AirSense-v2\public\enterprise.html",
]

for p in paths:
    print(f"\n==========================================")
    print(f"File: {p}")
    print(f"==========================================")
    with open(p, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    # 1. Look at <head> top
    head_match = re.search(r"<head>(.*?)</head>", content, re.DOTALL | re.IGNORECASE)
    if head_match:
        head_lines = [line.strip() for line in head_match.group(1).split("\n") if line.strip()]
        print("Head tags (first 10):")
        for line in head_lines[:10]:
            print(f"  {line}")

    # 2. Look for brand / logo / nav header
    brand_match = re.search(r'(<div\s+class="[^"]*brand[^"]*"[^>]*>.*?</div>\s*</div>)', content, re.DOTALL | re.IGNORECASE)
    if not brand_match:
        brand_match = re.search(r'class="[^"]*brand-mark[^"]*"', content)
        if brand_match:
            start = max(0, brand_match.start() - 100)
            end = min(len(content), brand_match.end() + 250)
            print("\nBrand mark snippet:")
            print(content[start:end])
        else:
            # Look for nav / header
            h_match = re.search(r'<header[^>]*>.*?</header>', content, re.DOTALL | re.IGNORECASE)
            if h_match:
                print("\nHeader tag snippet:")
                print(h_match.group(0)[:300])
            else:
                print("No brand-mark found")
    else:
        print("\nBrand snippet:")
        print(brand_match.group(0))
