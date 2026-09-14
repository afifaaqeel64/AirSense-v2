## 2026-09-02T09:49:06Z
Investigate all ESP32 firmware files, Arduino/C/C++ sketches, sensor drivers, pinouts, and serial/Wi-Fi communication code in c:/Users/HP/AirSense-v2.
Analyze:
1. What sensors and hardware pins are configured (e.g. DHT11/22, MQ135, PMS5003, etc.)?
2. How is data formatted (JSON, CSV, raw strings)?
3. What are the transmission modes currently implemented (Serial UART baud rate, Wi-Fi, MQTT client on ESP32 if any)?
4. What happens when Wi-Fi drops (blocking vs non-blocking reconnect)?
5. What happens when sensors fail or read NaN?
6. Identify all broken code, missing header files, hardcoded credentials, buffer overflows, or blocking loops.
7. Recommend exact fixes for resilient, 24/7 standalone or bridge-assisted telemetry.
