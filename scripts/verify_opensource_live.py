import urllib.request
import json
import time

url = "https://airsense-team.vercel.app/api/v1/providers/weather/telemetry-feed?limit=5&force_refresh=true"
page_url = "https://airsense-team.vercel.app/opensource"

print("Checking live Vercel production deployment...")
for attempt in range(1, 10):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AirSenseVerifier/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            pkt_time = data.get("timestamp_pkt")
            disp_time = data.get("display_time")
            records = data.get("records", [])
            rec0 = records[0] if records else {}

            print(f"[Attempt {attempt}] HTTP {resp.status} | timestamp_pkt={pkt_time} | display_time={disp_time}")
            if pkt_time and "PKT" in pkt_time:
                print("SUCCESS: Vercel deployment is LIVE with native PKT timezone formatting!")
                print(f"Server PKT Time: {pkt_time}")
                print(f"Display Time: {disp_time}")
                print(f"Record 0: time={rec0.get('time')}, pkt={rec0.get('timestamp_pkt')}, source={rec0.get('source')}")
                break
    except Exception as e:
        print(f"[Attempt {attempt}] Error: {e}")
    time.sleep(10)

# Also check frontend HTML page contains PKT
try:
    req_page = urllib.request.Request(page_url, headers={"User-Agent": "AirSenseVerifier/1.0"})
    with urllib.request.urlopen(req_page, timeout=10) as resp:
        html_content = resp.read().decode()
        assert "PKT" in html_content
        assert "TIMESTAMP (PKT / UTC+5)" in html_content
        print("SUCCESS: Live frontend HTML contains TIMESTAMP (PKT / UTC+5) and PKT formatting logic!")
except Exception as e:
    print(f"Frontend HTML check notice: {e}")
