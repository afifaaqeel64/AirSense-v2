@echo off
echo ========================================================
echo AirSense Live Verification and E2E Test Runner
echo Target URL: https://forums-surfaces-reef-stands.trycloudflare.com
echo ========================================================

echo.
echo [1/4] Checking / Starting FastAPI Backend on port 8000...
netstat -ano | findstr :8000 > nul
if %errorlevel% neq 0 (
    echo Starting uvicorn in background...
    start /min "AirSense Backend" cmd /c "py -u -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000"
    timeout /t 5 /nobreak > nul
) else (
    echo Port 8000 is already active!
)

echo.
echo [2/4] Executing Git and GitHub Sync...
call scripts\git_sync_helper.bat

echo.
echo [3/4] Testing Live Public HTTPS Endpoints...
py scripts\verify_live_endpoints.py https://forums-surfaces-reef-stands.trycloudflare.com
set VERIFY_EC=%errorlevel%

echo.
echo [4/4] Testing Hardware Serial Bridge Cloud Simulation Forwarding...
py scripts\airsense_serial_live_bridge.py --simulate --cloud-url https://forums-surfaces-reef-stands.trycloudflare.com/api/v1/ingest/reading
set BRIDGE_EC=%errorlevel%

echo.
echo ========================================================
echo FINAL STATUS:
echo Live Endpoint Verification: Code %VERIFY_EC%
echo Serial Bridge Simulation:   Code %BRIDGE_EC%
echo ========================================================
