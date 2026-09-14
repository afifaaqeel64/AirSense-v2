## 2026-09-02T09:49:06Z
You are Explorer 2 (Python Bridge & MQTT Specialist).
Your working directory is: c:/Users/HP/AirSense-v2/.agents/explorer_2
Read ORIGINAL_REQUEST.md at c:/Users/HP/AirSense-v2/.agents/ORIGINAL_REQUEST.md.
Also inspect c:/Users/HP/AirSense-v2/.agents/orchestrator_2/DISPATCH.md.

Task:
Investigate all Python bridge scripts, backend services, MQTT configuration, broker details, credentials, and serial port communication in c:/Users/HP/AirSense-v2.
Analyze:
1. What Python scripts exist for serial-to-MQTT or data bridging?
2. What COM port handling is present? What happens on disconnect/unplug/re-plug or port locked errors?
3. What MQTT broker, port, protocol (TCP vs WebSockets), client ID, topics, QoS, and payload format are used?
4. What error handling and retry mechanisms exist? Does it crash or exit on serial disconnect or MQTT network timeout?
5. How is the process kept alive 24/7 (Windows service, watchdog loop, endless try/except)?
6. Identify all bugs, missing dependencies (pyserial, paho-mqtt, etc.), topic mismatch with dashboard, or payload format mismatch.
7. Recommend exact fixes for a 100% resilient auto-recovering bridge daemon.

Write a detailed handoff report to: c:/Users/HP/AirSense-v2/.agents/explorer_2/analysis.md and c:/Users/HP/AirSense-v2/.agents/explorer_2/handoff.md.
When finished, send a message to parent with your summary.
