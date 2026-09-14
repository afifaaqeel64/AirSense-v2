import os, glob, re

css_files = sorted(glob.glob("public/**/*.css", recursive=True) + glob.glob("apps/web/**/*.css", recursive=True))
print("Found CSS files:", css_files)

for cf in css_files:
    with open(cf, "r", encoding="utf-8") as f:
        content = f.read()
    if "brand-logo" in content:
        print("\n--- Brand logo rules in", cf, "---")
        # Extract rule block
        matches = re.findall(r'(\.brand-logo[^{]*\{[^}]*\})', content, re.DOTALL)
        for m in matches:
            print(m.strip())
            print()
