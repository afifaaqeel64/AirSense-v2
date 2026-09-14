import os
import re

directories = [
    r"c:\Users\HP\AirSense-v2\public",
    r"c:\Users\HP\AirSense-v2\apps\web",
    r"c:\Users\HP\AirSense-v2\apps\web_enterprise"
]

for base in directories:
    if not os.path.exists(base):
        continue
    print(f"\n==========================================")
    print(f"Directory: {base}")
    print(f"==========================================")
    for f in sorted(os.listdir(base)):
        if f.endswith(".html"):
            p = os.path.join(base, f)
            with open(p, "r", encoding="utf-8", errors="ignore") as fp:
                content = fp.read()
            
            # Find all <link> tags in <head>
            links = re.findall(r'<link\s+[^>]+>', content, re.IGNORECASE)
            icon_links = [l for l in links if "icon" in l.lower() or "manifest" in l.lower()]
            
            # Find logo or AS placeholders
            as_badges = re.findall(r'<div[^>]*class="[^"]*logo[^"]*"[^>]*>.*?</div>', content, re.DOTALL | re.IGNORECASE)
            if not as_badges:
                as_badges = re.findall(r'<span[^>]*class="[^"]*logo[^"]*"[^>]*>.*?</span>', content, re.DOTALL | re.IGNORECASE)
            if not as_badges:
                # look for brand or header logo
                as_badges = re.findall(r'<div[^>]*class="[^"]*brand[^"]*"[^>]*>.*?</div>', content, re.DOTALL | re.IGNORECASE)

            print(f"\nFile: {f} ({len(content)} bytes)")
            print(f"  Icon/Manifest links found ({len(icon_links)}):")
            for il in icon_links:
                print(f"    {il}")
            if not icon_links:
                print("    [NONE FOUND]")
            
            # Look for "AS" text in header/navbar
            print(f"  Brand / Logo elements snippet:")
            # search for snippets with 'AS' surrounded by tags
            as_text_matches = re.findall(r'(<[^>]+>\s*AS\s*</[^>]+>)', content)
            if as_text_matches:
                print(f"    AS text matches: {as_text_matches[:3]}")
            else:
                print("    No standalone 'AS' element found")
