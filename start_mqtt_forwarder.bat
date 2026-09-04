@echo off
title AirSense Campus-to-Home MQTT Live Forwarder
echo =========================================================
echo   AirSense Pakistan - Campus-to-Home Live MQTT Forwarder
echo   Receiving Remote ESP32 Telemetry from Campus...
echo =========================================================
echo.
echo Connecting to Global Cloud Broker (broker.hivemq.com)...
echo Open your dashboard at http://127.0.0.1:8000/hardware to see live telemetry!
echo.
echo Press Ctrl + C to stop at any time.
echo.
py -u scripts\airsense_mqtt_live_forwarder.py
pause
