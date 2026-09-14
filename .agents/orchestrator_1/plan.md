# Orchestration Plan - AirSense-v2 Cloud Dashboard

## Objective
Implement and deploy a 24/7 standalone public AirSense hardware dashboard to Vercel / GitHub Pages connecting directly to Cloud MQTT WebSockets (`wss://broker.hivemq.com:8884/mqtt` or `ws://broker.hivemq.com:8000/mqtt`) on `airsense/karachi/bic_roof/telemetry` (or `airsense/#`), parsing PMS7003, BME280, Rain sensor, and timestamps, with dual-mode fallback, reactive heartbeat (8s timeout), and zero-dependency cloud hosting.

## Phases
1. **Phase 0: Survey & Scoping**
   - Dispatch 3 parallel Explorers (codebase explorer, MQTT & telemetry spec investigator, deployment & frontend packaging investigator).
   - Aggregate findings and formulate `PROJECT.md` with complete Feature Inventory, Milestones, Architecture, Interface Contracts, and Code Layout.
2. **Phase 1: Test Infrastructure & Implementation Parallel Tracks**
   - **Track A (E2E Testing Track)**: Dispatch Test Writer / Sub-orchestrator to define test runner, Tier 1-4 test suites, and publish `TEST_READY.md`.
   - **Track B (Implementation Track)**:
     - Milestone 1: Direct Cloud MQTT WebSocket client + packet parser (PMS7003, BME280, Rain sensor, timestamps).
     - Milestone 2: Dual-mode fallback & reactive heartbeat indicator (ESP32 Live Connected vs Disconnected after 8s).
     - Milestone 3: Real-time UI widgets/gauges, smooth updates without flash, responsive design.
     - Milestone 4: Packaging and static web build setup for Vercel & GitHub Pages with zero-config hosting.
3. **Phase 2: Final Verification & Adversarial Hardening**
   - Execute 100% E2E test suites (Tiers 1-4).
   - Adversarial coverage hardening (Tier 5) with Challengers.
   - Comprehensive Forensic Audit verification.
4. **Phase 3: Completion & Reporting**
   - Synthesize final reports, verify zero-config deployment assets.
   - Report final completion to Sentinel parent.
