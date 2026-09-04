/*
 * ============================================================================
 * AirSense - ESP32 Complete Weather & Air Quality IoT Node
 * Campus / Environmental Monitoring Station
 * ============================================================================
 * Pin Mapping:
 * - OLED SSD1306 (I2C) : SDA -> GPIO 21, SCL -> GPIO 22
 * - DHT22 Temp/Humidity: Data -> GPIO 15
 * - PM2.5 Simulator    : Analog -> GPIO 34 (ADC1)
 * - MQ-135 Gas Sensor  : Analog -> GPIO 35 (ADC1)
 * - Rain Sensor        : Analog -> GPIO 32 (ADC1), Digital -> GPIO 13
 * - MicroSD Card (SPI) : CS -> GPIO 5, SCK -> GPIO 18, MISO -> GPIO 19, MOSI -> GPIO 23
 * - Green LED          : GPIO 25
 * - Red LED            : GPIO 26
 * - Buzzer             : GPIO 27
 * ============================================================================
 */

#include <Wire.h>
#include <WiFi.h>
#include <SPI.h>
#include <SD.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>

// --- PIN DEFINITIONS ---
#define DHTPIN        15
#define DHTTYPE       DHT22
#define PIN_PM25      34
#define PIN_MQ135     35
#define PIN_RAIN_AO   32
#define PIN_RAIN_DO   13
#define SD_CS_PIN     5
#define LED_GREEN     25
#define LED_RED       26
#define BUZZER_PIN    27

// --- OLED CONFIGURATION ---
#define SCREEN_WIDTH  128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// --- DHT SENSOR ---
DHT dht(DHTPIN, DHTTYPE);

// --- WIFI CONFIG (Wokwi Virtual Network) ---
const char* ssid = "Wokwi-GUEST";
const char* password = "";

// --- LOGGING & TIMING ---
unsigned long lastReadTime = 0;
const unsigned long readInterval = 2000; // Read sensors every 2 seconds
bool sdCardAvailable = false;
int displayPage = 0;
unsigned long lastPageSwitch = 0;

// --- AQI CATEGORIES ---
struct AQIResult {
  int aqi;
  String category;
  bool isHazardous;
};

// Calculate US EPA AQI for PM2.5 (ug/m3)
AQIResult calculatePM25AQI(float pm25) {
  AQIResult res;
  if (pm25 < 0) pm25 = 0;

  if (pm25 <= 12.0) {
    res.aqi = map((int)(pm25 * 10), 0, 120, 0, 50);
    res.category = "Good";
    res.isHazardous = false;
  } else if (pm25 <= 35.4) {
    res.aqi = map((int)(pm25 * 10), 121, 354, 51, 100);
    res.category = "Moderate";
    res.isHazardous = false;
  } else if (pm25 <= 55.4) {
    res.aqi = map((int)(pm25 * 10), 355, 554, 101, 150);
    res.category = "Unhealthy (SG)";
    res.isHazardous = false;
  } else if (pm25 <= 150.4) {
    res.aqi = map((int)(pm25 * 10), 555, 1504, 151, 200);
    res.category = "Unhealthy";
    res.isHazardous = true;
  } else if (pm25 <= 250.4) {
    res.aqi = map((int)(pm25 * 10), 1505, 2504, 201, 300);
    res.category = "Very Unhealthy";
    res.isHazardous = true;
  } else {
    res.aqi = map((int)(pm25 * 10), 2505, 5000, 301, 500);
    res.category = "HAZARDOUS";
    res.isHazardous = true;
  }
  return res;
}

void logToSD(float temp, float hum, float pm25, int gasRaw, int rainRaw, int aqi, String cat) {
  if (!sdCardAvailable) return;

  File logFile = SD.open("/airsense_log.csv", FILE_APPEND);
  if (logFile) {
    logFile.print(millis() / 1000);
    logFile.print(",");
    logFile.print(temp, 1);
    logFile.print(",");
    logFile.print(hum, 1);
    logFile.print(",");
    logFile.print(pm25, 1);
    logFile.print(",");
    logFile.print(gasRaw);
    logFile.print(",");
    logFile.print(rainRaw);
    logFile.print(",");
    logFile.print(aqi);
    logFile.print(",");
    logFile.println(cat);
    logFile.close();
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n=================================");
  Serial.println("  AirSense Station Initializing  ");
  Serial.println("=================================");

  // Pin Modes
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_RED, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(PIN_RAIN_DO, INPUT);
  digitalWrite(LED_GREEN, LOW);
  digitalWrite(LED_RED, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  // Initialize OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("❌ SSD1306 OLED initialization failed!");
  } else {
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setTextSize(1);
    display.setCursor(18, 15);
    display.println("AirSense Node");
    display.setCursor(10, 35);
    display.println("System Booting...");
    display.display();
  }

  // Initialize DHT22
  dht.begin();

  // Initialize SD Card
  Serial.print("Checking MicroSD Card...");
  if (!SD.begin(SD_CS_PIN)) {
    Serial.println(" (SD Not Detected / Optional)");
    sdCardAvailable = false;
  } else {
    Serial.println(" (SD Card OK!)");
    sdCardAvailable = true;
    // Write CSV Header if new file
    if (!SD.exists("/airsense_log.csv")) {
      File logFile = SD.open("/airsense_log.csv", FILE_WRITE);
      if (logFile) {
        logFile.println("Uptime_s,Temp_C,Humidity_pct,PM25_ugm3,Gas_Raw,Rain_Raw,AQI,Category");
        logFile.close();
      }
    }
  }

  // Connect to Wi-Fi
  Serial.print("Connecting to Wi-Fi");
  WiFi.begin(ssid, password);
  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry < 15) {
    delay(300);
    Serial.print(".");
    retry++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n Connected! IP: " + WiFi.localIP().toString());
  } else {
    Serial.println("\n⚠️ Wi-Fi Offline (Running local standalone)");
  }

  delay(1000);
}

void loop() {
  unsigned long now = millis();

  // Read sensors at fixed interval
  if (now - lastReadTime >= readInterval) {
    lastReadTime = now;

    // 1. Read DHT22
    float humidity = dht.readHumidity();
    float temperature = dht.readTemperature();
    if (isnan(humidity) || isnan(temperature)) {
      temperature = 25.0; // fallback if sensor warm-up
      humidity = 50.0;
    }

    // 2. Read PM2.5 Simulated Potentiometer (ADC: 0 - 4095 mapped to 0 - 500 ug/m3)
    int rawPM = analogRead(PIN_PM25);
    float pm25 = (rawPM / 4095.0) * 500.0;

    // 3. Read MQ-135 Gas Sensor Potentiometer (ADC: 0 - 4095)
    int rawGas = analogRead(PIN_MQ135);

    // 4. Read Rain Sensor (0 = heavy wet, 4095 = completely dry)
    int rawRain = analogRead(PIN_RAIN_AO);
    bool isRaining = (rawRain < 2500) || (digitalRead(PIN_RAIN_DO) == LOW);

    // 5. Calculate AQI
    AQIResult aqiData = calculatePM25AQI(pm25);

    // 6. Actuators (LEDs & Buzzer)
    if (aqiData.isHazardous) {
      digitalWrite(LED_GREEN, LOW);
      digitalWrite(LED_RED, HIGH);
      // Chirp buzzer briefly for hazardous alert
      tone(BUZZER_PIN, 1000, 100);
    } else {
      digitalWrite(LED_GREEN, HIGH);
      digitalWrite(LED_RED, LOW);
      noTone(BUZZER_PIN);
    }

    // 7. Log to MicroSD
    logToSD(temperature, humidity, pm25, rawGas, rawRain, aqiData.aqi, aqiData.category);

    // 8. Serial Monitor Telemetry Output
    Serial.println("---------------------------------------------");
    Serial.printf("Temp: %.1f C | Hum: %.1f %% | Rain: %s (%d)\n", 
                  temperature, humidity, isRaining ? "YES 🌧️" : "NO ☀️", rawRain);
    Serial.printf("PM2.5: %.1f ug/m3 | Gas Raw: %d\n", pm25, rawGas);
    Serial.printf("AQI: %d [%s]\n", aqiData.aqi, aqiData.category.c_str());
    Serial.printf("SD Log: %s | WiFi: %s\n", 
                  sdCardAvailable ? "Active" : "Disabled",
                  WiFi.status() == WL_CONNECTED ? "Online" : "Offline");

    // 9. Update OLED Display (Dual Page Rotation)
    display.clearDisplay();
    
    // Switch between Page 0 (AQI & PM2.5) and Page 1 (Weather & Rain) every 4 seconds
    if (now - lastPageSwitch > 4000) {
      displayPage = (displayPage + 1) % 2;
      lastPageSwitch = now;
    }

    if (displayPage == 0) {
      // PAGE 1: AIR QUALITY FOCUS
      display.setTextSize(1);
      display.setCursor(0, 0);
      display.print("AirSense | AQI INFO");
      display.drawLine(0, 10, 128, 10, SSD1306_WHITE);

      display.setTextSize(2);
      display.setCursor(0, 16);
      display.printf("AQI:%d", aqiData.aqi);

      display.setTextSize(1);
      display.setCursor(0, 36);
      display.printf("Status: %s", aqiData.category.c_str());

      display.setCursor(0, 52);
      display.printf("PM2.5: %.1f ug/m3", pm25);
    } else {
      // PAGE 2: WEATHER & ENVIRONMENT FOCUS
      display.setTextSize(1);
      display.setCursor(0, 0);
      display.print("AirSense | WEATHER");
      display.drawLine(0, 10, 128, 10, SSD1306_WHITE);

      display.setCursor(0, 16);
      display.printf("Temp : %.1f C", temperature);
      
      display.setCursor(0, 28);
      display.printf("Hum  : %.1f %%", humidity);

      display.setCursor(0, 40);
      display.printf("Rain : %s", isRaining ? "RAIN DETECTED!" : "Clear / Dry");

      display.setCursor(0, 54);
      display.printf("Gas Raw: %d", rawGas);
    }

    display.display();
  }
}
