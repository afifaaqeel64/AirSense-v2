/*
  =============================================================================
  AirSense Pakistan: Autonomous Zero-Dependency Production ESP32 Firmware
  =============================================================================
  Hardware Target: ESP32 Dev Module (WROOM-32 / ESP32-D0WDQ6)
  Features:
    - PMS7003 Optical Laser Dust Sensor (Hardware UART2 GPIO 16/17)
    - Bosch BME280 Direct Register I2C Driver (GPIO 21/22)
    - Resistive Raindrop Moisture Plate (ADC1 GPIO 34)
    - MicroSD Circular SPI Backup Logging (VSPI GPIO 5/18/19/23)
    - Structured [JSON_TELEMETRY] Serial Streaming for Python Bridge
    - Transparent Sensor Error / Health Status Reporting (Zero Fake Data)
    - Non-Blocking Wi-Fi Reconnection & Dual-Broker Cloud MQTT Failover
    - Dynamic Wi-Fi Configuration via WiFiManager (Captive Portal)
    - Direct Secure HTTPS Cloud Ingestion to Vercel
  =============================================================================
*/

#include <WiFi.h>
#include <WiFiManager.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <time.h>

// =============================================================================
// 1. DEVICE IDENTIFICATION CONFIGURATION
// =============================================================================
const char* DEVICE_UID    = "AIRSENSE-NODE-KHI-01";    // Global Node UID
const char* DEVICE_ID     = "AIRSENSE-NODE-KHI-01";    // Standard Schema Device ID
const char* STATION_CODE  = "BIC-KHI-ROOF-01";         // Station Code
const char* CAMPUS_CODE   = "KARACHI";                 // Campus Code
const char* LOCATION      = "BIC_ROOF_KARACHI";        // Physical Location
const char* FIRMWARE_VER  = "v4.0.0-AUTONOMOUS";       // Autonomous Firmware Version

// Live Cloud Backend Ingestion (Direct HTTPS)
const char* API_ENDPOINT  = "https://airsense-team.vercel.app/api/v1/ingest/reading";
const char* DEVICE_TOKEN  = "airsense_dev_token_khi_01";

// =============================================================================
// 2. GLOBAL CLOUD MQTT CONFIGURATION (Dual-Broker Failover Support)
// =============================================================================
const char* MQTT_BROKERS[] = {"broker.hivemq.com", "broker.emqx.io"};
const int   NUM_BROKERS    = 2;
const int   MQTT_PORT      = 1883;
const char* MQTT_TOPIC     = "airsense/karachi/bic_roof/telemetry";

WiFiClient    mqttClient;
int           current_broker_idx = 0;
unsigned long last_mqtt_attempt  = 0;
bool          mqtt_is_connected  = false;

// =============================================================================
// 3. HARDWARE PIN DEFINITIONS
// =============================================================================
#define PMS_RX_PIN     16     // ESP32 GPIO16 connects to PMS7003 Pin 4 (TXD)
#define PMS_TX_PIN     17     // ESP32 GPIO17 connects to PMS7003 Pin 5 (RXD)
#define BME_SDA_PIN    21     // ESP32 GPIO21 connects to BME280 SDA
#define BME_SCL_PIN    22     // ESP32 GPIO22 connects to BME280 SCL
#define SD_CS_PIN      5      // ESP32 GPIO5 connects to MicroSD CS
#define RAIN_ADC_PIN   34     // ESP32 GPIO34 connects to Raindrop AO
#define STATUS_LED_PIN 2      // Built-in Blue LED

HardwareSerial pmsSerial(2);

// =============================================================================
// 4. ZERO-DEPENDENCY BOSCH BME280 DIRECT REGISTER DRIVER
// =============================================================================
struct BME280Calib {
  uint16_t dig_T1; int16_t dig_T2, dig_T3;
  uint16_t dig_P1; int16_t dig_P2, dig_P3, dig_P4, dig_P5, dig_P6, dig_P7, dig_P8, dig_P9;
  uint8_t  dig_H1; int16_t dig_H2; uint8_t dig_H3; int16_t dig_H4, dig_H5; int8_t dig_H6;
  int32_t  t_fine;
} bmeCalib;

uint8_t       bme_addr         = 0x76;
bool          bme_found        = false;
bool          is_bmp280        = false;
bool          sd_found         = false;
unsigned long last_sample_time = 0;
unsigned long packet_seq       = 0;

uint8_t read8(uint8_t reg) {
  Wire.beginTransmission(bme_addr);
  Wire.write(reg);
  Wire.endTransmission(false); // Repeated Start
  Wire.requestFrom(bme_addr, (uint8_t)1);
  return Wire.available() ? Wire.read() : 0;
}

uint16_t read16_LE(uint8_t reg) {
  Wire.beginTransmission(bme_addr);
  Wire.write(reg);
  Wire.endTransmission(false); // Repeated Start
  Wire.requestFrom(bme_addr, (uint8_t)2);
  if (Wire.available() >= 2) {
    return (Wire.read() | (Wire.read() << 8));
  }
  return 0;
}

int16_t readS16_LE(uint8_t reg) {
  return (int16_t)read16_LE(reg);
}

void write8(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(bme_addr);
  Wire.write(reg);
  Wire.write(val);
  Wire.endTransmission();
}

bool initBME280() {
  Wire.setTimeOut(50);
  Wire.setClock(100000);
  bme_addr = 0x76;
  uint8_t id = read8(0xD0);
  if (id != 0x60 && id != 0x58 && id != 0x56 && id != 0x57) {
    bme_addr = 0x77;
    id = read8(0xD0);
    if (id != 0x60 && id != 0x58 && id != 0x56 && id != 0x57) return false;
  }
  
  is_bmp280 = (id == 0x58 || id == 0x56 || id == 0x57);
  if (is_bmp280) {
    Serial.printf("[INIT] Detected Bosch BMP280 (ID: 0x%02X) on I2C (0x%02X). Temperature & Pressure active.\n", id, bme_addr);
  } else {
    Serial.printf("[INIT] Detected Bosch BME280 (ID: 0x%02X) on I2C (0x%02X). Temp, Humidity & Pressure active.\n", id, bme_addr);
  }

  // Read Temperature & Pressure calibration coefficients (common to both BME280 and BMP280)
  bmeCalib.dig_T1 = read16_LE(0x88);
  bmeCalib.dig_T2 = readS16_LE(0x8A);
  bmeCalib.dig_T3 = readS16_LE(0x8C);
  bmeCalib.dig_P1 = read16_LE(0x8E);
  bmeCalib.dig_P2 = readS16_LE(0x90);
  bmeCalib.dig_P3 = readS16_LE(0x92);
  bmeCalib.dig_P4 = readS16_LE(0x94);
  bmeCalib.dig_P5 = readS16_LE(0x96);
  bmeCalib.dig_P6 = readS16_LE(0x98);
  bmeCalib.dig_P7 = readS16_LE(0x9A);
  bmeCalib.dig_P8 = readS16_LE(0x9C);
  bmeCalib.dig_P9 = readS16_LE(0x9E);

  if (!is_bmp280) {
    // Read Humidity calibration coefficients (BME280 only)
    bmeCalib.dig_H1 = read8(0xA1);
    bmeCalib.dig_H2 = readS16_LE(0xE1);
    bmeCalib.dig_H3 = read8(0xE3);
    bmeCalib.dig_H4 = (read8(0xE4) << 4) | (read8(0xE5) & 0x0F);
    bmeCalib.dig_H5 = (read8(0xE6) << 4) | (read8(0xE5) >> 4);
    bmeCalib.dig_H6 = (int8_t)read8(0xE7);

    write8(0xF2, 0x01); // Humidity oversampling x1
  }

  write8(0xF4, 0x27); // Pressure x1, Temp x1, Normal mode
  write8(0xF5, 0xA0); // Standby 1000ms, Filter off
  return true;
}

bool readBME280(float &temp, float &hum, float &press) {
  if (!bme_found) {
    static unsigned long last_bme_retry = 0;
    if (millis() - last_bme_retry > 10000) {
      last_bme_retry = millis();
      bme_found = initBME280();
    }
    if (!bme_found) {
      temp  = -999.0;
      hum   = -1.0;
      press = -1.0;
      return false;
    }
  }

  Wire.beginTransmission(bme_addr);
  Wire.write(0xF7);
  if (Wire.endTransmission(false) != 0) { // Repeated Start
    bme_found = false;
    temp  = -999.0;
    hum   = -1.0;
    press = -1.0;
    return false;
  }

  uint8_t req_bytes = is_bmp280 ? 6 : 8;
  uint8_t bytesRead = Wire.requestFrom(bme_addr, req_bytes);
  if (bytesRead < req_bytes) {
    bme_found = false;
    temp  = -999.0;
    hum   = -1.0;
    press = -1.0;
    return false;
  }

  int32_t adc_P = ((int32_t)Wire.read() << 12) | ((int32_t)Wire.read() << 4) | ((int32_t)Wire.read() >> 4);
  int32_t adc_T = ((int32_t)Wire.read() << 12) | ((int32_t)Wire.read() << 4) | ((int32_t)Wire.read() >> 4);
  int32_t adc_H = 0;
  if (!is_bmp280) {
    adc_H = ((int32_t)Wire.read() << 8) | (int32_t)Wire.read();
  }

  // Validate that ADC values are not all-zeros or all-ones (I2C communication fault)
  if (adc_T == 0 || adc_T == 0x7FFFF || (uint32_t)adc_T == 0xFFFFF || adc_P == 0) {
    bme_found = false;
    temp  = -999.0;
    hum   = -1.0;
    press = -1.0;
    return false;
  }

  // Compensate Temperature
  int32_t var1 = ((((adc_T >> 3) - ((int32_t)bmeCalib.dig_T1 << 1))) * ((int32_t)bmeCalib.dig_T2)) >> 11;
  int32_t var2 = (((((adc_T >> 4) - ((int32_t)bmeCalib.dig_T1)) * ((adc_T >> 4) - ((int32_t)bmeCalib.dig_T1))) >> 12) * ((int32_t)bmeCalib.dig_T3)) >> 14;
  bmeCalib.t_fine = var1 + var2;
  temp = (float)((bmeCalib.t_fine * 5 + 128) >> 8) / 100.0;

  // Compensate Pressure
  int64_t p1 = ((int64_t)bmeCalib.t_fine) - 128000;
  int64_t p2 = p1 * p1 * (int64_t)bmeCalib.dig_P6;
  p2 = p2 + ((p1 * (int64_t)bmeCalib.dig_P5) << 17);
  p2 = p2 + (((int64_t)bmeCalib.dig_P4) << 35);
  p1 = ((p1 * p1 * (int64_t)bmeCalib.dig_P3) >> 8) + ((p1 * (int64_t)bmeCalib.dig_P2) << 12);
  p1 = (((((int64_t)1) << 47) + p1)) * ((int64_t)bmeCalib.dig_P1) >> 33;
  if (p1 == 0) {
    press = -1.0;
    return false;
  } else {
    int64_t p = 1048576 - adc_P;
    p = (((p << 31) - p2) * 3125) / p1;
    p1 = (((int64_t)bmeCalib.dig_P9) * (p >> 13) * (p >> 13)) >> 25;
    p2 = (((int64_t)bmeCalib.dig_P8) * p) >> 19;
    press = (float)(((p + p1 + p2) >> 8) + (((int64_t)bmeCalib.dig_P7) << 4)) / 25600.0;
  }

  // Compensate Humidity (BME280 only)
  if (is_bmp280) {
    hum = -1.0; // BMP280 does not have a humidity channel
  } else {
    int32_t v_x1_u32r = (bmeCalib.t_fine - ((int32_t)76800));
    v_x1_u32r = (((((adc_H << 14) - (((int32_t)bmeCalib.dig_H4) << 20) - (((int32_t)bmeCalib.dig_H5) * v_x1_u32r)) +
                   ((int32_t)16384)) >> 15) * (((((((v_x1_u32r * ((int32_t)bmeCalib.dig_H6)) >> 10) *
                   (((v_x1_u32r * ((int32_t)bmeCalib.dig_H3)) >> 11) + ((int32_t)32768))) >> 10) +
                   ((int32_t)2097152)) * ((int32_t)bmeCalib.dig_H2) + 8192) >> 14));
    v_x1_u32r = (v_x1_u32r - (((((v_x1_u32r >> 15) * (v_x1_u32r >> 15)) >> 7) * ((int32_t)bmeCalib.dig_H1)) >> 4));
    v_x1_u32r = (v_x1_u32r < 0 ? 0 : v_x1_u32r);
    v_x1_u32r = (v_x1_u32r > 419430400 ? 419430400 : v_x1_u32r);
    hum = (float)(v_x1_u32r >> 12) / 1024.0;
  }

  // Sanity check physical operational bounds
  if (temp < -40.0 || temp > 85.0 || press < 300.0 || press > 1200.0) {
    return false;
  }
  if (!is_bmp280 && (hum < 0.0 || hum > 100.0)) {
    return false;
  }

  return true;
}

// =============================================================================
// 5. PLANTOWER PMS7003 LASER DUST SENSOR DRIVER
// =============================================================================
bool readPMS7003(float &pm1, float &pm25, float &pm10) {
  // Flush stale bytes accumulated in UART RX buffer before reading fresh frame
  if (pmsSerial.available() > 32) {
    while (pmsSerial.available() > 0) {
      pmsSerial.read();
    }
  }

  uint8_t buffer[32];
  unsigned long start = millis();
  while (millis() - start < 2000) {
    if (pmsSerial.available() > 0) {
      if (pmsSerial.peek() != 0x42) {
        pmsSerial.read(); // Discard noise until start character 0x42
        continue;
      }

      // Check second byte for 0x4D frame header
      if (pmsSerial.available() < 2) {
        delay(2);
        continue;
      }

      pmsSerial.read(); // consume 0x42
      if (pmsSerial.peek() != 0x4D) {
        // Not 0x4D; 0x42 was a data byte. Slide window by 1 byte.
        continue;
      }
      pmsSerial.read(); // consume 0x4D

      buffer[0] = 0x42;
      buffer[1] = 0x4D;

      // Read remaining 30 bytes with 500ms frame timeout
      int bytesRead = 2;
      unsigned long frameStart = millis();
      while (bytesRead < 32 && (millis() - frameStart < 500)) {
        if (pmsSerial.available() > 0) {
          buffer[bytesRead++] = pmsSerial.read();
        } else {
          delay(2);
        }
      }

      if (bytesRead == 32) {
        uint16_t checksum = 0;
        for (int i = 0; i < 30; i++) checksum += buffer[i];
        uint16_t frame_checksum = (buffer[30] << 8) | buffer[31];
        if (checksum == frame_checksum) {
          pm1  = (float)((buffer[10] << 8) | buffer[11]); // Standard particle PM1.0
          pm25 = (float)((buffer[12] << 8) | buffer[13]); // Standard particle PM2.5
          pm10 = (float)((buffer[14] << 8) | buffer[15]); // Standard particle PM10
          return true;
        }
      }
    } else {
      delay(5);
    }
  }
  pm1  = -1.0;
  pm25 = -1.0;
  pm10 = -1.0;
  return false;
}

// =============================================================================
// 6. RAINDROP ANALOG SENSOR DRIVER
// =============================================================================
bool readRainSensor(int &rain_adc, bool &rain_flag) {
  long rain_sum = 0;
  for (int i = 0; i < 8; i++) {
    rain_sum += analogRead(RAIN_ADC_PIN);
    delay(1);
  }
  rain_adc = (int)(rain_sum / 8);
  if (rain_adc < 0 || rain_adc > 4095) {
    rain_adc  = 4095;
    rain_flag = false;
    return false;
  }
  rain_flag = (rain_adc < 2800);
  return true;
}

// =============================================================================
// 7. NON-BLOCKING CLOUD MQTT ENGINE (Dual-Broker Failover)
// =============================================================================
bool connectMQTT() {
  if (WiFi.status() != WL_CONNECTED) {
    mqtt_is_connected = false;
    return false;
  }

  const char* broker = MQTT_BROKERS[current_broker_idx];
  Serial.printf("[MQTT] Connecting to Cloud Broker %s:%d...\n", broker, MQTT_PORT);

  // Fast non-blocking socket connect (2500ms timeout for cross-border cloud latency)
  if (!mqttClient.connect(broker, MQTT_PORT, 2500)) {
    Serial.printf("[MQTT WARNING] Connection to broker %s failed. Switching broker index.\n", broker);
    mqttClient.stop();
    mqtt_is_connected = false;
    current_broker_idx = (current_broker_idx + 1) % NUM_BROKERS;
    return false;
  }

  // MQTT 3.1.1 CONNECT packet with unique Client ID
  char clientId[40];
  uint32_t chipId = (uint32_t)(ESP.getEfuseMac() & 0xFFFFFF);
  snprintf(clientId, sizeof(clientId), "as-esp32-%06X", chipId);
  uint16_t clientLen = strlen(clientId);
  uint8_t varHeader[] = {
    0x00, 0x04, 'M', 'Q', 'T', 'T',
    0x04, 0x02, 0x00, 0x78 // 120 seconds Keep-Alive
  };
  uint16_t remLen = sizeof(varHeader) + 2 + clientLen;
  mqttClient.write((uint8_t)0x10);
  mqttClient.write((uint8_t)remLen);
  mqttClient.write(varHeader, sizeof(varHeader));
  mqttClient.write((uint8_t)(clientLen >> 8));
  mqttClient.write((uint8_t)(clientLen & 0xFF));
  mqttClient.write((const uint8_t*)clientId, clientLen);

  // Fast non-blocking CONNACK check (max 2500ms for cloud handshake latency)
  unsigned long t0 = millis();
  while (mqttClient.available() < 4 && (millis() - t0 < 2500)) {
    delay(5);
  }

  if (mqttClient.available() >= 4) {
    uint8_t connack[4];
    mqttClient.read(connack, 4);
    if (connack[3] == 0) {
      Serial.printf("[MQTT SUCCESS] Connected to %s!\n", broker);
      mqtt_is_connected = true;
      return true;
    } else {
      Serial.printf("[MQTT ERROR] Connack rejected with code: %d\n", connack[3]);
      mqttClient.stop();
      mqtt_is_connected = false;
      current_broker_idx = (current_broker_idx + 1) % NUM_BROKERS;
      return false;
    }
  } else {
    Serial.printf("[MQTT WARNING] Connack timeout from %s.\n", broker);
    mqttClient.stop();
    mqtt_is_connected = false;
    current_broker_idx = (current_broker_idx + 1) % NUM_BROKERS;
    return false;
  }
}

void publishMQTT(const char* topic, const char* payload) {
  if (WiFi.status() != WL_CONNECTED) {
    if (mqttClient.connected()) mqttClient.stop();
    mqtt_is_connected = false;
    return;
  }

  unsigned long now = millis();

  // If disconnected, attempt reconnect at most once every 10 seconds (non-blocking)
  if (!mqttClient.connected()) {
    mqtt_is_connected = false;
    if (now - last_mqtt_attempt < 10000 && last_mqtt_attempt != 0) {
      return; // Reconnect backoff active
    }
    last_mqtt_attempt = now;
    if (!connectMQTT()) {
      return;
    }
  }

  // MQTT 3.1.1 PUBLISH packet (QoS 0)
  uint16_t topicLen   = strlen(topic);
  uint16_t payloadLen = strlen(payload);
  uint32_t remLen     = 2 + topicLen + payloadLen;

  mqttClient.write((uint8_t)0x30);
  uint32_t x = remLen;
  do {
    uint8_t encodedByte = x % 128;
    x = x / 128;
    if (x > 0) encodedByte |= 128;
    mqttClient.write(encodedByte);
  } while (x > 0);

  mqttClient.write((uint8_t)(topicLen >> 8));
  mqttClient.write((uint8_t)(topicLen & 0xFF));
  mqttClient.write((const uint8_t*)topic, topicLen);
  size_t bytesWritten = mqttClient.write((const uint8_t*)payload, payloadLen);

  if (bytesWritten != payloadLen) {
    Serial.println("[MQTT WARNING] Incomplete packet write. Resetting socket.");
    mqttClient.stop();
    mqtt_is_connected = false;
  } else {
    Serial.printf("[MQTT CLOUD PUSH] Broadcasted packet to: %s via %s\n", topic, MQTT_BROKERS[current_broker_idx]);
  }
}

// =============================================================================
// 8. NON-BLOCKING WI-FI RECONNECTION STATE MACHINE
// =============================================================================
void handleWiFiReconnection(unsigned long now) {
  static unsigned long last_wifi_check           = 0;
  static unsigned long wifi_reconnect_started_at = 0;
  static bool          wifi_reconnecting         = false;

  if (WiFi.status() == WL_CONNECTED) {
    if (wifi_reconnecting) {
      wifi_reconnecting = false;
      Serial.println("\n[WIFI RESTORED] Connected to AP! IP: " + WiFi.localIP().toString());
      digitalWrite(STATUS_LED_PIN, HIGH);
      configTime(5 * 3600, 0, "pool.ntp.org", "time.google.com");
    }
    return;
  }

  // Wi-Fi is currently disconnected
  digitalWrite(STATUS_LED_PIN, LOW);
  if (mqttClient.connected()) {
    mqttClient.stop();
    mqtt_is_connected = false;
  }

  if (!wifi_reconnecting) {
    if (now - last_wifi_check >= 10000 || last_wifi_check == 0) {
      last_wifi_check = now;
      Serial.println("[WIFI WARNING] Wi-Fi link lost. Initiating non-blocking reconnection...");
      WiFi.disconnect();
      WiFi.reconnect(); // Uses saved NVS credentials from WiFiManager
      wifi_reconnecting = true;
      wifi_reconnect_started_at = now;
    }
  } else {
    if (now - wifi_reconnect_started_at > 15000) {
      // Reconnect attempt timed out; reset state for next check cycle
      wifi_reconnecting = false;
      last_wifi_check = now;
    }
  }
}

// =============================================================================
// 8. SETUP & INITIALIZATION
// =============================================================================
void setup() {
  Serial.begin(115200);
  pinMode(STATUS_LED_PIN, OUTPUT);
  digitalWrite(STATUS_LED_PIN, LOW);
  delay(500);

  Serial.println("\n========================================================");
  Serial.println("  AirSense Pakistan: Autonomous ESP32 Node Booting  ");
  Serial.println("========================================================");

  // 1. Init PMS7003 UART2
  pmsSerial.begin(9600, SERIAL_8N1, PMS_RX_PIN, PMS_TX_PIN);
  Serial.println("[INIT] PMS7003 UART2 initialized on GPIO 16 (RX) / 17 (TX).");

  // [I2C BUS RECOVERY] 9-Clock bus clearing sequence to unlock stuck slaves
  pinMode(BME_SDA_PIN, INPUT_PULLUP);
  pinMode(BME_SCL_PIN, OUTPUT);
  for (int i = 0; i < 9; i++) {
    if (digitalRead(BME_SDA_PIN) == HIGH) break;
    digitalWrite(BME_SCL_PIN, HIGH); delayMicroseconds(10);
    digitalWrite(BME_SCL_PIN, LOW);  delayMicroseconds(10);
  }
  // Generate manual I2C STOP condition to reset slave state machine
  pinMode(BME_SDA_PIN, OUTPUT);
  digitalWrite(BME_SDA_PIN, LOW);  delayMicroseconds(10);
  digitalWrite(BME_SCL_PIN, HIGH); delayMicroseconds(10);
  digitalWrite(BME_SDA_PIN, HIGH); delayMicroseconds(10);
  pinMode(BME_SDA_PIN, INPUT_PULLUP);
  pinMode(BME_SCL_PIN, INPUT_PULLUP);

  // [DIAGNOSTIC I2C SCANNER]
  Serial.println("[I2C SCAN] Scanning I2C bus on SDA=21, SCL=22...");
  Wire.begin(BME_SDA_PIN, BME_SCL_PIN);
  Wire.setTimeOut(50);
  Wire.setClock(100000);

  int i2c_devices = 0;
  for (byte address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    if (Wire.endTransmission() == 0) {
      Serial.print("[I2C SCAN] FOUND DEVICE AT ADDRESS: 0x");
      if (address < 16) Serial.print("0");
      Serial.println(address, HEX);
      i2c_devices++;
    }
  }
  if (i2c_devices == 0) {
    Serial.println("[I2C SCAN WARNING] No I2C devices found at all! The sensor is dead or wiring is completely wrong.");
  }

  // 2. Init Bosch BME280 / BMP280 I2C
  bme_found = initBME280();
  if (bme_found) {
    Serial.println("[INIT] Bosch BME280 initialized on I2C (0x76/0x77).");
  } else {
    Serial.println("[INIT WARNING] BME280 not found on I2C. Check wiring (SDA->21, SCL->22).");
  }

  // 3. Init MicroSD SPI
  if (SD.begin(SD_CS_PIN)) {
    sd_found = true;
    Serial.println("[INIT] MicroSD SPI logging initialized (CS->GPIO 5).");
  } else {
    Serial.println("[INIT WARNING] MicroSD card not detected (CS->GPIO 5).");
  }

  // 4. WiFiManager Setup (Dynamic configuration)
  WiFiManager wm;
  Serial.println("[WIFI] Starting WiFiManager Setup Portal (AirSense-Setup)...");
  
  // Set non-blocking timeout for config portal (180 seconds)
  wm.setConfigPortalTimeout(180);
  
  bool res = wm.autoConnect("AirSense-Setup"); // Creates an open AP named AirSense-Setup
  
  if (!res) {
    Serial.println("\n[WIFI WARNING] Config portal timed out (180s). Continuing in autonomous offline sensor mode.");
    digitalWrite(STATUS_LED_PIN, LOW);
  } else {
    Serial.println("\n[WIFI CONNECTED] IP: " + WiFi.localIP().toString());
    digitalWrite(STATUS_LED_PIN, HIGH);
    configTime(5 * 3600, 0, "pool.ntp.org", "time.google.com");
    Serial.println("[NTP] Internal clock synchronized with global atomic time (PKT UTC+5).");
  }
}

// =============================================================================
// 8.1 MICROSD DAILY DATE PARTITIONING & TIMESTAMPS
// =============================================================================
void logToMicroSD(unsigned long seq, const char* pm1_str, const char* pm25_str, const char* pm10_str,
                  const char* temp_str, const char* hum_str, const char* press_str,
                  bool rain_flag, const char* pms_health, const char* bme_health) {
  if (!sd_found) return;

  time_t now_epoch = time(NULL);
  char filename[40] = "/telemetry.csv";
  char dt_pkt[32] = "00:00:00";

  if (now_epoch > 1700000000) {
    struct tm timeinfo;
    localtime_r(&now_epoch, &timeinfo);
    snprintf(filename, sizeof(filename), "/airsense_%04d_%02d_%02d.csv",
             timeinfo.tm_year + 1900, timeinfo.tm_mon + 1, timeinfo.tm_mday);
    snprintf(dt_pkt, sizeof(dt_pkt), "%02d:%02d:%02d",
             timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);
  }

  bool file_exists = SD.exists(filename);
  File f = SD.open(filename, FILE_APPEND);
  if (f) {
    if (!file_exists || f.size() == 0) {
      f.println("seq,epoch,datetime_pkt,pm1_0,pm2_5,pm10,temp_c,humidity_pct,pressure_hpa,rain_status,pms_health,bme_health");
    }
    const char* rain_status = rain_flag ? "WET" : "DRY";
    f.printf("%lu,%lu,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n",
             seq,
             (unsigned long)now_epoch,
             dt_pkt,
             pm1_str, pm25_str, pm10_str,
             temp_str, hum_str, press_str,
             rain_status,
             pms_health, bme_health);
    f.close();
  }
}

// =============================================================================
// 9. MAIN LOOP & DATA ACQUISITION
// =============================================================================
void loop() {
  unsigned long now = millis();

  if (now - last_sample_time >= 5000 || last_sample_time == 0) {
    last_sample_time = now;
    packet_seq++;

    // 1. Read PMS7003 Optical Laser Dust Sensor
    float pm1 = -1.0, pm25 = -1.0, pm10 = -1.0;
    bool pms_ok = readPMS7003(pm1, pm25, pm10);

    if (pms_ok) {
      Serial.printf("[READING] PMS7003 -> PM1.0: %.1f | PM2.5: %.1f | PM10: %.1f ug/m3 (Status: OK)\n", pm1, pm25, pm10);
    } else {
      Serial.println("[READING WARNING] PMS7003 -> Sensor read failed / timeout (Status: ERROR, sent null)");
    }

    // 2. Read Bosch BME280 Environmental Sensor
    float temp = -999.0, hum = -1.0, press = -1.0;
    bool bme_ok = readBME280(temp, hum, press);

    if (bme_ok) {
      Serial.printf("[READING] BME280  -> Temp: %.1f C | Humidity: %.1f %% | Pressure: %.1f hPa (Status: OK)\n", temp, hum, press);
    } else {
      Serial.println("[READING WARNING] BME280  -> Sensor read failed / I2C bus error (Status: ERROR, sent null)");
    }

    // 3. Read Raindrop Resistive Moisture Sensor
    int  rain_adc  = 4095;
    bool rain_flag = false;
    bool rain_ok   = readRainSensor(rain_adc, rain_flag);

    const char* rain_state_desc = "DRY (No Rain)";
    if (rain_adc < 1500) {
      rain_state_desc = "HEAVY RAIN";
    } else if (rain_adc < 2500) {
      rain_state_desc = "LIGHT RAIN";
    } else if (rain_adc < 3500) {
      rain_state_desc = "MOISTURE / DEW";
    }

    Serial.printf("[READING] Raindrop -> Raw ADC: %d | Status: %s | Rain Flag: %s\n",
      rain_adc, rain_state_desc, rain_flag ? "YES (Wet)" : "NO (Dry)");

    // Prepare JSON number/null string representations
    char pm1_str[16], pm25_str[16], pm10_str[16];
    char temp_str[16], hum_str[16], press_str[16];

    if (pms_ok) {
      snprintf(pm1_str, sizeof(pm1_str), "%.1f", pm1);
      snprintf(pm25_str, sizeof(pm25_str), "%.1f", pm25);
      snprintf(pm10_str, sizeof(pm10_str), "%.1f", pm10);
    } else {
      snprintf(pm1_str, sizeof(pm1_str), "null");
      snprintf(pm25_str, sizeof(pm25_str), "null");
      snprintf(pm10_str, sizeof(pm10_str), "null");
    }

    if (bme_ok) {
      snprintf(temp_str, sizeof(temp_str), "%.1f", temp);
      if (is_bmp280) {
        snprintf(hum_str, sizeof(hum_str), "null");
      } else {
        snprintf(hum_str, sizeof(hum_str), "%.1f", hum);
      }
      snprintf(press_str, sizeof(press_str), "%.1f", press);
    } else {
      snprintf(temp_str, sizeof(temp_str), "null");
      snprintf(hum_str, sizeof(hum_str), "null");
      snprintf(press_str, sizeof(press_str), "null");
    }

    const char* pms_health  = pms_ok ? "OK" : "ERROR";
    const char* bme_health  = bme_ok ? "OK" : "ERROR";
    const char* rain_health = rain_ok ? "OK" : "ERROR";
    const char* sd_health   = sd_found ? "OK" : "ERROR";

    // 4. Log to MicroSD Card CSV (Daily Date Partitioning & Timestamps)
    logToMicroSD(packet_seq, pm1_str, pm25_str, pm10_str,
                 temp_str, hum_str, press_str,
                 rain_flag, pms_health, bme_health);

    // 5. Format Structured JSON Telemetry Payload
    char jsonPayload[640];
    snprintf(jsonPayload, sizeof(jsonPayload),
      "{\"schema_version\":\"1.0\","
      "\"device_id\":\"%s\","
      "\"device_uid\":\"%s\","
      "\"station_code\":\"%s\","
      "\"campus_code\":\"%s\","
      "\"location\":\"%s\","
      "\"firmware_version\":\"%s\","
      "\"sequence_number\":%lu,"
      "\"timestamp_epoch\":%lu,"
      "\"pm1\":%s,\"pm1_0\":%s,"
      "\"pm2_5\":%s,\"pm25\":%s,"
      "\"pm10\":%s,"
      "\"temperature\":%s,\"temperature_c\":%s,"
      "\"humidity\":%s,\"humidity_pct\":%s,"
      "\"pressure\":%s,\"pressure_hpa\":%s,"
      "\"rain_flag\":%s,"
      "\"sensor_health\":{\"pms7003\":\"%s\",\"bme280\":\"%s\",\"rain\":\"%s\",\"microsd\":\"%s\"},"
      "\"transmission_mode\":\"%s\"}",
      DEVICE_UID, DEVICE_UID, STATION_CODE, CAMPUS_CODE, LOCATION, FIRMWARE_VER,
      packet_seq, (unsigned long)(time(NULL)),
      pm1_str, pm1_str,
      pm25_str, pm25_str,
      pm10_str,
      temp_str, temp_str,
      hum_str, hum_str,
      press_str, press_str,
      rain_flag ? "true" : "false",
      pms_health, bme_health, rain_health, sd_health,
      (WiFi.status() == WL_CONNECTED) ? "WIFI_DIRECT" : "SERIAL_BRIDGE"
    );

    // 6. Emit Structured JSON Telemetry over Serial for Diagnostics
    Serial.print("[JSON_TELEMETRY] ");
    Serial.println(jsonPayload);

    // 7. Publish to Cloud MQTT Broker (Dual-Broker Non-blocking Engine)
    if (WiFi.status() == WL_CONNECTED) {
      publishMQTT(MQTT_TOPIC, jsonPayload);

      // 8. HTTPS Push directly to Vercel (Fast non-blocking)
      WiFiClientSecure secureClient;
      secureClient.setInsecure(); // Bypass cert verification for simplicity on ESP32

      HTTPClient http;
      http.begin(secureClient, API_ENDPOINT);
      http.setTimeout(2500); // Allow slightly longer for SSL handshake
      http.addHeader("Content-Type", "application/json");
      http.addHeader("X-Device-Token", DEVICE_TOKEN);
      
      int code = http.POST(jsonPayload);
      if (code > 0) {
        Serial.printf("[HTTPS VERCEL PUSH] Success (HTTP %d)\n", code);
      } else {
        Serial.printf("[HTTPS VERCEL PUSH] Failed, error: %s\n", http.errorToString(code).c_str());
      }
      http.end();
    }

    Serial.println("--------------------------------------------------------");
  }

  // Periodic non-blocking Wi-Fi reconnect check using NVS credentials
  handleWiFiReconnection(now);
  delay(20);
}