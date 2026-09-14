import os
import filecmp

pairs = [
    (r"c:\Users\HP\AirSense-v2\public\index.html", r"c:\Users\HP\AirSense-v2\apps\web\index.html"),
    (r"c:\Users\HP\AirSense-v2\public\hardware.html", r"c:\Users\HP\AirSense-v2\apps\web\hardware_dashboard.html"),
    (r"c:\Users\HP\AirSense-v2\public\diagnostics.html", r"c:\Users\HP\AirSense-v2\apps\web\diagnostics_dashboard.html"),
    (r"c:\Users\HP\AirSense-v2\public\command.html", r"c:\Users\HP\AirSense-v2\apps\web\command_center.html"),
    (r"c:\Users\HP\AirSense-v2\public\command_center.html", r"c:\Users\HP\AirSense-v2\apps\web\command_center.html"),
    (r"c:\Users\HP\AirSense-v2\public\opensource.html", r"c:\Users\HP\AirSense-v2\apps\web\opensource_dashboard.html"),
    (r"c:\Users\HP\AirSense-v2\public\enterprise.html", r"c:\Users\HP\AirSense-v2\apps\web_enterprise\index.html"),
    (r"c:\Users\HP\AirSense-v2\public\paho-mqtt.js", r"c:\Users\HP\AirSense-v2\apps\web\paho-mqtt.js")
]

for p1, p2 in pairs:
    if os.path.exists(p1) and os.path.exists(p2):
        s1 = os.path.getsize(p1)
        s2 = os.path.getsize(p2)
        match = filecmp.cmp(p1, p2, shallow=False)
        print(f"{os.path.basename(p1)} ({s1}b) vs {os.path.basename(p2)} ({s2}b): match={match}")
    else:
        print(f"Missing: {p1} or {p2}")
