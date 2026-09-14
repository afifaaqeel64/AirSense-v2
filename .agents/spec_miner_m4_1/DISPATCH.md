# Dispatch: spec_miner_m4_1

Target: Investigate ingestion API specification and schemas in the AirSense-v2 repository.
Objectives:
- Find the FastAPI router and Pydantic schema for `/api/v1/ingest/reading` (e.g., in `apps/api/routers/` or similar).
- Determine exact field names, expected data types, required vs optional fields, and response status codes.
- Check headers expected (e.g. `Content-Type: application/json`, API key if any).
- Compare this with the JSON payload constructed in `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino` to ensure 100% field compliance.

## 2026-09-05T17:58:49Z
You are spec_miner_m4_1 (teamwork_preview_spec_miner).
Your working directory is: c:\Users\HP\AirSense-v2\.agents\spec_miner_m4_1\
You MUST read the authoritative request at: c:\Users\HP\AirSense-v2\ORIGINAL_REQUEST.md
Also read the scope at: c:\Users\HP\AirSense-v2\.agents\orchestrator_4\SCOPE.md and the dispatch notes at: c:\Users\HP\AirSense-v2\.agents\spec_miner_m4_1\DISPATCH.md.

Task:
Mine the backend API specification and schemas in the AirSense-v2 repository.
1. Inspect `apps/api/routers/ingest_router.py` (and any related Pydantic models in `apps/api/schemas/` or `apps/api/models/`).
2. Extract the exact schema for `POST /api/v1/ingest/reading`:
   - All expected JSON field names and data types (e.g. `device_uid`, `station_code`, `campus_code`, `pm1`, `pm2_5`, `pm10`, `temperature`, `humidity`, `pressure`, `gas_resistance_kohm`, `rain_flag`, `sensor_health`, `transmission_mode`, `schema_version`).
   - Which fields are required vs optional, default values.
   - Expected headers (`Content-Type`, `X-Device-Token`, `Authorization`).
   - HTTP response status codes and body structure on success (200/201) and failure (400, 401, 422).
3. Compare this specification with the JSON serialization in `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino` and identify any missing or mismatched fields.
4. Document all findings in `c:\Users\HP\AirSense-v2\.agents\spec_miner_m4_1\spec.md` and write `handoff.md`.
Communicate back using send_message to your caller.
