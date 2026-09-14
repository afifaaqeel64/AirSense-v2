# Task Assignment: Serial Bridge & E2E Verification Survey

## Identity
- Role: Hardware Bridge & E2E Verification Explorer
- Working Directory: c:\Users\HP\AirSense-v2\.agents\explorer_survey_bridge_tests_1\
- Parent: orchestrator_3 (Conversation ID: d855ea29-0400-4419-801f-9d26248c059f)

## Objective
Survey the hardware serial bridge (`scripts/airsense_serial_live_bridge.py` and related scripts) and existing E2E verification test suites.

## Context & Authoritative References
- Original User Request: c:\Users\HP\AirSense-v2\ORIGINAL_REQUEST.md
- Bridge scripts: `scripts/airsense_serial_live_bridge.py`, `scripts/airsense_serial_forwarder.py`, `scripts/airsense_mqtt_live_forwarder.py`
- Tests directory: `c:\Users\HP\AirSense-v2\tests\`

## Tasks to Investigate
1. Inspect `scripts/airsense_serial_live_bridge.py`:
   - How does it read serial data?
   - How does it publish to MQTT / HTTP?
   - How can it be updated or verified to route physical sensor packets to both local (`http://127.0.0.1:8000/api/v1/ingest/reading`) and live cloud endpoints (`https://<cloud-url>/api/v1/ingest/reading`)?
2. Inspect `tests/` directory:
   - What test files exist?
   - How are endpoints currently verified?
   - What test harness or script is needed to systematically verify:
     - `/api/v1/health/liveness`
     - `/api/v1/health/readiness`
     - `/api/v1/ingest/reading` (HTTP POST)
     - `/api/v1/ingest/sensors/diagnostic` (HTTP GET)
     - `/api/v1/providers/weather/telemetry-feed` (HTTP GET)
     over the public HTTPS URL?
3. What is needed for hardware serial packet routing simulation / verification?

## Output Deliverable
Write a comprehensive report to `c:\Users\HP\AirSense-v2\.agents\explorer_survey_bridge_tests_1\handoff.md`. Include architecture diagrams, code references, and verification scripts.
When done, message orchestrator_3 with a brief notification referencing `handoff.md`.
