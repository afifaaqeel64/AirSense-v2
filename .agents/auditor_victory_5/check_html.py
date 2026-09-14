import os, glob, re

html_files = sorted(glob.glob('public/*.html') + glob.glob('apps/web/*.html'))
print("Total HTML files to inspect:", len(html_files))

all_passed = True
for file_path in html_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    issues = []
    if not re.search(r'<link[^>]*rel=["\x27]icon["\x27][^>]*href=["\x27][^"\x27]*favicon\.ico["\x27]', content, re.I):
        issues.append('Missing favicon.ico')
    if not re.search(r'<link[^>]*href=["\x27][^"\x27]*favicon-32x32\.png["\x27]', content, re.I):
        issues.append('Missing favicon-32x32.png')
    if not re.search(r'<link[^>]*href=["\x27][^"\x27]*favicon-16x16\.png["\x27]', content, re.I):
        issues.append('Missing favicon-16x16.png')
    if not re.search(r'<link[^>]*rel=["\x27]apple-touch-icon["\x27][^>]*href=["\x27][^"\x27]*apple-touch-icon\.png["\x27]', content, re.I):
        issues.append('Missing apple-touch-icon')
    if not re.search(r'<link[^>]*rel=["\x27]manifest["\x27][^>]*href=["\x27][^"\x27]*site\.webmanifest["\x27]', content, re.I):
        issues.append('Missing site.webmanifest')
    if not re.search(r'<img[^>]*class=["\x27][^"\x27]*brand-logo[^"\x27]*["\x27]', content):
        issues.append('Missing brand-logo img')
    if not re.search(r'<img[^>]*src=["\x27]/apple-touch-icon\.png["\x27]', content):
        issues.append('Brand logo src not /apple-touch-icon.png')
    if re.search(r'<div[^>]*class=["\x27][^"\x27]*brand-mark[^"\x27]*["\x27][^>]*>\s*AS\s*</div>', content, re.I):
        issues.append('Contains AS placeholder in brand-mark')

    if issues:
        all_passed = False
        print("[FAIL]", file_path, issues)
    else:
        print("[PASS]", file_path)

if all_passed:
    print("\nOverall HTML Header and Tag Check: ALL PASS")
else:
    print("\nOverall HTML Header and Tag Check: FAILURES DETECTED")
