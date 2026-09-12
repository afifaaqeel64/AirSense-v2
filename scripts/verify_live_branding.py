import httpx

base = 'https://airsense-team.vercel.app'
client = httpx.Client(base_url=base, follow_redirects=True, timeout=15.0)

urls = [
    '/favicon.ico',
    '/favicon-32x32.png',
    '/favicon-16x16.png',
    '/apple-touch-icon.png',
    '/android-chrome-192x192.png',
    '/android-chrome-512x512.png',
    '/site.webmanifest',
    '/assets/logo-files/android-chrome-192x192.png',
    '/hardware',
    '/'
]

print(f"Probing {base}...")
for u in urls:
    r = client.get(u)
    ctype = r.headers.get("content-type", "")
    print(f"{u:45} -> HTTP {r.status_code} ({ctype[:30]}, {len(r.content)} bytes)")
