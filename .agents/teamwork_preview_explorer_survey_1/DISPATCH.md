## 2026-08-25T00:34:58Z

You are Survey Explorer 1 (Backend & Sensor Diagnostic Focus).
Your working directory is: c:\Users\HP\AirSense-v2\.agents\teamwork_preview_explorer_survey_1

Please read the user requirements at:
c:\Users\HP\AirSense-v2\.agents\ORIGINAL_REQUEST.md

Your mission:
1. Thoroughly inspect the existing AirSense-v2 codebase in c:\Users\HP\AirSense-v2 (backend services, FastAPI/Flask/Node or whatever stack is used, existing ingest routes, mock or real sensor handlers, database/storage, test harnesses).
2. Investigate how sensor connectivity and diagnostics are currently implemented or structured:
   - Packet recency (120s heartbeat window)
   - UART binary frame health (Plantower PMS7003)
   - I2C bus response (Bosch BME280)
   - ADC moisture levels (Raindrop plate)
   - SPI storage (MicroSD)
   - State machine: LIVE_ACTIVE, OFFLINE, PARTIAL_DEGRADED with actionable pin troubleshooting guidance
   - Diagnostic endpoint specification (/api/v1/ingest/sensors/diagnostic)
3. Identify existing files, dependencies, build/run commands, test setups, and any missing backend components.
4. Write your comprehensive findings to c:\Users\HP\AirSense-v2\.agents\teamwork_preview_explorer_survey_1\analysis.md and write a handoff report to handoff.md. Send a completion message back when done.
