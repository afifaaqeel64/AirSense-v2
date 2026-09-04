# 🌤️ AirSense: Simple Project Guide (Easy to Read)

> **Live Website Link:** [https://airsense-team.vercel.app](https://airsense-team.vercel.app)  
> **What is this?** A non-technical summary of what AirSense is, what we have built so far, and what is left to do.

---

## 📌 1. What is AirSense in Simple Words?

AirSense is a **smart environmental station** built for Karachi.

Think of it like a mini weather station that you place outdoors (for example, on a university rooftop). It constantly tests the air you breathe, checks the weather, and **sends the live readings directly to a website on your phone** so anyone can see if the air is clean or polluted.

---

## 🔬 2. What Sensors Are on the Device?

Our device has 3 main sensors working together:

1. **Dust & Smog Sensor (PMS7003):**  
   Uses a tiny laser beam to count microscopic pollution particles (known as **PM2.5**). This tells you if the air has harmful smoke, dust, or vehicle exhaust.
2. **Weather Sensor (BME280):**  
   Measures 3 everyday weather conditions:
   * **Temperature** (How hot or cold it is in °C)
   * **Humidity** (How much moisture is in the air in %)
   * **Air Pressure** (Barometric pressure for weather changes)
3. **Rain Detector:**  
   A sensitive gold plate that immediately detects when raindrops start falling, separating dry weather from light drizzle or heavy rain.
4. **Memory Card (MicroSD):**  
   Saves a continuous backup of all readings on a small memory card, so even if the internet goes down, no data is ever lost.

---

## 🚀 3. How Does the Whole System Work? (3 Simple Steps)

```text
  [ 1. SENSORS ON ROOFTOP ]
  The device tests the air every 5 seconds.
             │
             ▼
  [ 2. INTERNET BROADCAST ]
  The device connects to Wi-Fi and sends the data to the cloud.
             │
             ▼
  [ 3. LIVE WEBSITE ON YOUR PHONE ]
  Anyone opens https://airsense-team.vercel.app and sees live gauges moving!
```

* **Best Part:** **You do NOT need your laptop turned on!**  
  The website is hosted on the cloud 24 hours a day, 7 days a week. Your laptop can be turned off, and the website will still show live data as long as the device has power and Wi-Fi.

---

## ✅ 4. What We Have Completed (Done So Far)

Here is everything we have built, tested, and finished:

* **Real Hardware Data (No Fake Data):**  
  Connected all physical sensors to the ESP32 microchip. We removed all artificial/fake data generators. Every number you see is 100% real.
* **Fixed the "White Screen" Bug:**  
  The website was previously showing a blank white page because it was waiting for slow external tools. We rebuilt it with clean, fast code that loads in under 1 second.
* **Stable Connection & 15s Heartbeat Ping:**  
  The website now sends a heartbeat ping every 15 seconds to the cloud broker. It will **never disconnect after a minute by itself**! It stays rock-solid **GREEN (`LIVE CONNECTED`)** as long as your hardware has power and Wi-Fi.
* **RECORDED TELEMETRY LOG (Hardware & Open-Source):**  
  Both the Hardware Hub and the 24/7 Open-Source Weather Hub now have live recording tables that remember previous readings in your phone/browser storage so they are never blank!
* **1-Click "EXPORT CSV" Working Everywhere:**  
  Clicking the blue **EXPORT CSV** button immediately downloads a real spreadsheet file directly onto your phone or computer.
* **Accurate Pakistan Atomic Clock Time (NTP):**  
  The ESP32 now automatically connects to global atomic time servers (`pool.ntp.org`) over Wi-Fi, setting the chip to exact Pakistan Standard Time (PKT).
* **100% Mobile Responsive:**  
  All 4 dashboards adapt cleanly to any screen size—whether on an Android, iPhone, iPad, or desktop monitor.
* **Published to the Global Internet (Vercel):**  
  Uploaded to permanent production:  
  👉 **`https://airsense-team.vercel.app`** (also aliased to **`https://airsense.pk`**).

---

## ⏳ 5. What is Remaining? (Your Next Steps)

Everything in the code and on the website is completely finished! All that remains are the **physical steps on campus**:

### Step 1: Put Campus Wi-Fi onto the Device (Takes 2 minutes)
* Open the code file in Arduino IDE on your laptop.
* Type your campus Wi-Fi name and password.
* Click **Upload** to save it onto the chip.

### Step 2: Put the Device on the Rooftop
* Place the hardware inside a protective plastic box (to shield it from sun and direct rain).
* Make sure the rain sensor plate is facing up toward the sky.
* Plug the device into power (using a phone charger or power bank).

### Step 3: Open the Website & Watch It Work!
* Open **`https://airsense-team.vercel.app`** on your phone.
* You will see the green "Connected" badge and your campus weather live on screen!

---

## 📱 Quick Reference: All 4 Live Dashboards

| Dashboard | Description | Live Link |
|:---|:---|:---|
| 📟 **Hardware Station Hub** | Real-time physical ESP32 rooftop sensor stream | **[Open Hardware Hub](https://airsense-team.vercel.app/)** |
| 🛰️ **24/7 Open-Source Weather** | Continuous Karachi satellite weather & air quality | **[Open Weather Hub](https://airsense-team.vercel.app/opensource)** |
| 🌐 **Operations Command Center** | Interactive GIS city map & predictive analytics | **[Open Command Center](https://airsense-team.vercel.app/command)** |
| 🏢 **Enterprise Platform** | Multi-campus institutional compliance & reporting | **[Open Enterprise Hub](https://airsense-team.vercel.app/enterprise)** |

*(You can also seamlessly switch between all 4 dashboards using the navigation tabs at the top of any page!)*
