@echo off
title Stop AirSense Serial Bridge
echo ===================================================
echo   Stopping AirSense Serial Bridge (COM7)...
echo ===================================================
echo.
py scripts\stop_serial_bridge.py
echo.
echo You can now upload firmware in Arduino IDE!
echo.
pause
