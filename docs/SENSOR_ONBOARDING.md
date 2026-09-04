# AirSense Pakistan Sensor Onboarding Guide

This guide details the procedure for registering and deploying onsite ESP32 sensor stations for Islamabad campus and Karachi campus.

## 1. Onboarding Prerequisites

Before installing a new ESP32 station:
1. Confirm campus assignment (Islamabad or Karachi).
2. Obtain hardware MAC address of the ESP32 WiFi/cellular board.
3. Generate a secure device authentication token.
4. Record campus rooftop latitude and longitude (if available).

## 2. Registration Command / API

Register device via API:
```http
POST /api/v1/devices/register
Content-Type: application/json
X-Admin-Token: <ADMIN_API_TOKEN>

{
  "campus_code": "ISB_CAMPUS",
  "mac_address": "AA:BB:CC:DD:EE:01",
  "device_token": "esp32_secret_token_123",
  "firmware_version": "1.0.0"
}
```

## 3. Firmware Configuration

ESP32 firmware must POST sensor telemetry to:
`http://<SERVER_IP>:8000/api/v1/ingest/sensor`

HTTP Headers:
- `Content-Type: application/json`
- `X-Device-Token: <ESP32_SECRET_TOKEN>`

Payload Schema:
```json
{
  "device_id": "ESP32-ISB-001",
  "campus_code": "ISB_CAMPUS",
  "timestamp_utc": "2026-07-27T12:00:00Z",
  "readings": {
    "pm25": 42.5,
    "pm10": 78.0,
    "temperature": 31.2,
    "humidity": 65.0
  }
}
```
