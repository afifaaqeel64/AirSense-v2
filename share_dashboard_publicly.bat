@echo off
title AirSense Permanent Public Dashboard Tunnel
echo =========================================================
echo   AirSense Pakistan - PERMANENT Public Link
echo   Fixed URL: https://airsense-karachi-live.loca.lt/hardware
echo =========================================================
echo.
echo Fetching your public IP passcode...
for /f "delims=" %%a in ('powershell -Command "(Invoke-WebRequest -Uri 'https://api.ipify.org' -UseBasicParsing).Content"') do set PUB_IP=%%a
echo.
echo =========================================================
echo   YOUR PASSCODE / IP: %PUB_IP%
echo   (Send this to your friend if asked on first visit)
echo =========================================================
echo.
echo Starting permanent public tunnel for port 8000...
echo Fixed Link: https://airsense-karachi-live.loca.lt/hardware
echo.
cmd /c npx localtunnel --port 8000 --subdomain airsense-karachi-live
pause
