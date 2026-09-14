# BRIEFING — 2026-09-01T16:11:50Z

## Mission
Discover and document exhaustive MQTT WebSockets protocol requirements, browser client integration, dual-mode fallback, reactive heartbeat logic, packet JSON schemas, state machines, edge cases, and reconnection strategies for AirSense-v2 standalone cloud deployment.

## 🔒 My Identity
- Archetype: Specification Miner (Teamwork Specialist)
- Roles: MQTT & Protocol Specialist
- Working directory: c:\Users\HP\AirSense-v2\.agents\spec_miner_survey_1
- Original parent: 5cb1eac6-68de-47cb-bf01-3b1ce85430c8
- Milestone: Survey / Protocol Specification Mining

## 🔒 Key Constraints
- Authoritative specification discovery only — do NOT implement code changes in the main application.
- Exhaustive documentation of MQTT WebSockets protocol, HiveMQ Cloud broker endpoints, topic patterns, JSON schemas, edge cases, connection state machine, error handling, dual-mode fallback, and reactive heartbeat (8s silence window).
- Maintain file workspace convention: write only in `.agents/spec_miner_survey_1/`.
- Provide hard handoff with complete 5 sections: Observation, Logic Chain, Caveats, Conclusion, Verification Method.

## Current Parent
- Conversation ID: 5cb1eac6-68de-47cb-bf01-3b1ce85430c8
- Updated: 2026-09-01T16:11:50Z

## Task Summary
- **What to build**: Specification report for MQTT WebSockets browser client, dual-mode fallback, and heartbeat protocol.
- **Success criteria**: Comprehensive `analysis.md` and `handoff.md` covering all protocol endpoints, message schemas, connection lifecycle, fallback states, failure modes, and edge cases.
- **Interface contracts**: `.agents/ORIGINAL_REQUEST.md`, `PROJECT.md`, codebase schemas.

## Key Decisions Made
- Fully documented HiveMQ Cloud endpoints (`wss://broker.hivemq.com:8884/mqtt` over TLS for HTTPS/Vercel/GitHub Pages, `ws://broker.hivemq.com:8000/mqtt` for local HTTP, `1883` for ESP32 raw TCP).
- Formulated canonical JSON schema normalization rules covering all hardware and API variants.
- Specified 8-second reactive silence timer state machine with automatic degradation to `🔴 ESP32 DISCONNECTED` and instant self-healing recovery.
- Defined dual-mode fallback arbitration prioritizing MQTT WebSockets while preserving local REST polling capabilities.
- Analyzed browser library choices (Paho MQTT vs MQTT.js).

## Artifact Index
- `c:\Users\HP\AirSense-v2\.agents\spec_miner_survey_1\analysis.md` — Detailed protocol specification analysis
- `c:\Users\HP\AirSense-v2\.agents\spec_miner_survey_1\handoff.md` — 5-component handoff report
- `c:\Users\HP\AirSense-v2\.agents\spec_miner_survey_1\progress.md` — Heartbeat and activity log
- `c:\Users\HP\AirSense-v2\.agents\spec_miner_survey_1\DISPATCH.md` — Dispatch log
