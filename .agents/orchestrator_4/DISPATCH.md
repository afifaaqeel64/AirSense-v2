# Dispatch Log

## 2026-09-05T17:57:31Z

You are the Project Orchestrator (orchestrator_4).
Your working directory is: c:\Users\HP\AirSense-v2\.agents\orchestrator_4\
The authoritative user request is in: c:\Users\HP\AirSense-v2\ORIGINAL_REQUEST.md (under header ## 2026-09-05T17:56:46Z).

Your objective:
Update the ESP32 C++ firmware (`scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`) to be a fully autonomous IoT device connecting directly to the Vercel cloud and MQTT broker without relying on the laptop serial bridge script.

Requirements:
1. Dynamic Wi-Fi Configuration (WiFiManager):
   Remove hardcoded WIFI_SSID and WIFI_PASS credentials. Implement the tzapu/WiFiManager library in the ESP32 firmware so that on first boot, it broadcasts a Setup AP (e.g. AirSense-Setup). Users can connect via phone to enter local Wi-Fi credentials dynamically.
2. Direct Secure Cloud API Ingestion (HTTPS):
   Update API_ENDPOINT to point directly to live Vercel production API: https://airsense-team.vercel.app/api/v1/ingest/reading.
   Refactor HTTP push logic in the firmware to use WiFiClientSecure with client.setInsecure() to handle HTTPS requests properly and push JSON telemetry payload directly to the cloud backend.
3. Remove Laptop Dependency:
   Ensure that when powered via wall adapter, it connects to Wi-Fi, publishes to HiveMQ Cloud Broker, and executes HTTPS POST to Vercel independently.
4. Documentation & Verification:
   Create README_FIRMWARE.md or similar instructions for the user on how to install the WiFiManager library in Arduino IDE and flash the updated code.
   Verify the firmware syntax/structure and run tests/validation.

Maintain plan.md, progress.md, and BRIEFING.md in your working directory.
When all tasks are complete and verified, send a message back with your completion report and handoff details so the Sentinel can trigger the mandatory Victory Audit.
