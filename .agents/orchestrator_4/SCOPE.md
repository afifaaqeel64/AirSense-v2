# Scope: Milestone 5 — ESP32 Autonomous Firmware Upgrade (WiFiManager & Direct HTTPS Cloud Ingestion)

## Architecture
Transition the ESP32 hardware node from depending on a tethered laptop running `airsense_serial_live_bridge.py` to being a completely autonomous standalone IoT appliance:
1. Dynamic Wi-Fi provisioning via `tzapu/WiFiManager` AP (`AirSense-Setup`), eliminating hardcoded Wi-Fi credentials.
2. Direct Secure Cloud Ingestion via `WiFiClientSecure` using `client.setInsecure()` posting JSON directly to `https://airsense-team.vercel.app/api/v1/ingest/reading`.
3. Standalone dual transmission: Direct HiveMQ Cloud MQTT broker publishing + direct Vercel HTTPS ingestion.
4. Comprehensive user documentation in `scripts/airsense_esp32_firmware/README_FIRMWARE.md` and automated validation tests.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Dynamic Wi-Fi Configuration | Integrate `tzapu/WiFiManager`, broadcast `AirSense-Setup` AP on boot, auto-reconnect, remove hardcoded `WIFI_SSID` / `WIFI_PASS` | M5 | ORIGINAL_REQUEST §2026-09-05T17:56:46Z |
| 2 | Direct Secure Cloud Ingestion | Replace HTTP with `WiFiClientSecure` (`client.setInsecure()`), target `https://airsense-team.vercel.app/api/v1/ingest/reading` | M5 | ORIGINAL_REQUEST §2026-09-05T17:56:46Z |
| 3 | Laptop Dependency Removal | Wall-adapter standalone operation: simultaneous MQTT + HTTPS without serial bridge | M5 | ORIGINAL_REQUEST §2026-09-05T17:56:46Z |
| 4 | Firmware User Documentation | Create `README_FIRMWARE.md` with Arduino IDE setup, WiFiManager library install, flashing guide, and AP connection flow | M5 | ORIGINAL_REQUEST §2026-09-05T17:56:46Z |
| 5 | Firmware Verification & Test Suite | Develop syntax validation and JSON schema conformance tests for the firmware | M5 | ORIGINAL_REQUEST §2026-09-05T17:56:46Z |

## Code Layout
- Target firmware: `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`
- Target documentation: `scripts/airsense_esp32_firmware/README_FIRMWARE.md`
- Tests / validation: `tests/test_firmware_payload.py` or similar
