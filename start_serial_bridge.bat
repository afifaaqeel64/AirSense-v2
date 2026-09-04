@echo off
title AirSense Serial Bridge (COM7)
echo ===================================================
echo   AirSense Pakistan - Live USB Serial Bridge
echo   Connecting ESP32 (COM7) to Live Dashboard...
echo ===================================================
echo.
echo Press Ctrl + C at any time, or run stop_serial_bridge.bat to stop.
echo.
py -u scripts\airsense_serial_live_bridge.py COM7
pause
