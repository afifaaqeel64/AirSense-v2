@echo off
title AirSense Master Station - All In One
echo ==============================================================================
echo   AirSense Pakistan - Master Autonomous Launcher
echo ==============================================================================
echo.
echo [1/3] Starting Local FastAPI Backend (Port 8000)...
start /min "AirSense Backend" cmd /c "py -u -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000"

timeout /t 2 /nobreak >nul

echo [2/3] Starting Hardware Serial and Campus MQTT Forwarder...
start /min "AirSense Serial Bridge" cmd /c "py -u scripts\airsense_serial_live_bridge.py COM7"
start /min "AirSense MQTT Forwarder" cmd /c "py -u scripts\airsense_mqtt_live_forwarder.py"

timeout /t 2 /nobreak >nul

echo [3/3] Launching Live Cloud Tunnel...
echo.
echo ==============================================================================
echo   YOUR STATION IS FULLY LIVE AND CONNECTED!
echo.
echo   Local Dashboard:      http://127.0.0.1:8000/hardware
echo   Permanent Cloud:      https://airsense-team.vercel.app/
echo   Custom Domain:        https://airsense.pk/
echo   Tunnel Fallback:      https://airsense-karachi-live.loca.lt/hardware
echo ==============================================================================
echo.
echo NOTE: If Arduino Serial Monitor is OPEN, the hardware streams via Wi-Fi!
echo Keep this window open while streaming. Press Ctrl+C or close to stop.
echo.

cmd /c npx localtunnel --port 8000 --subdomain airsense-karachi-live
pause
