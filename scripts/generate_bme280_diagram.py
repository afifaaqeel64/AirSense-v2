"""
Generate Dedicated High-Resolution Visual Diagram: ESP32 to Bosch BME280 Sensor Connection.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path
import shutil

from pathlib import Path

AIRSENSE_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PNG = str(AIRSENSE_ROOT / "docs" / "bme280_esp32_wiring_visual.png")

fig, ax = plt.subplots(figsize=(18, 10), dpi=200)
fig.patch.set_facecolor('#0B132B')
ax.set_facecolor('#0B132B')
ax.set_xlim(-1, 19)
ax.set_ylim(-1, 11)
ax.axis('off')

# Title
ax.text(9, 10.4, "AirSense Pakistan | ESP32 to Bosch BME280 Visual Wiring Guide", 
        fontsize=22, fontweight='bold', color='#A855F7', ha='center', va='center')
ax.text(9, 9.9, "I2C Bus Wiring (Temperature, Relative Humidity, Barometric Pressure) | COIL AI Initiative", 
        fontsize=12, color='#94A3B8', ha='center', va='center')

# -----------------------------------------------------------------------------
# 1. BOSCH BME280 SENSOR (LEFT SIDE)
# -----------------------------------------------------------------------------
bme_x, bme_y, bme_w, bme_h = 1.5, 2.5, 5.5, 6.0
bme_box = patches.FancyBboxPatch((bme_x, bme_y), bme_w, bme_h, boxstyle="round,pad=0.1,rounding_size=0.2",
                                 facecolor='#4C1D95', edgecolor='#A855F7', linewidth=2.5, zorder=2)
ax.add_patch(bme_box)

# Sensor Metal Chip
chip = patches.Rectangle((bme_x + 1.8, bme_y + 3.2), 1.9, 1.6, facecolor='#CBD5E1', edgecolor='#E2E8F0', linewidth=1.5, zorder=3)
ax.add_patch(chip)
ax.text(bme_x + 2.75, bme_y + 4.0, "BOSCH\nBME280", fontsize=9, fontweight='bold', color='#0F172A', ha='center', va='center', zorder=4)

ax.text(bme_x + 2.75, bme_y + 5.2, "BOSCH BME280 MODULE", fontsize=11, fontweight='bold', color='#F5D0FE', ha='center', zorder=4)
ax.text(bme_x + 2.75, bme_y + 2.2, "Digital Environmental Sensor\nTemp / Humidity / Pressure\nI2C Bus (Address 0x76 / 0x77)", fontsize=8.5, color='#E9D5FF', ha='center', zorder=4)

# Pins on BME280 (Right Edge)
pins_bme = [
    ("VCC (3.3V Power)", bme_y + 1.5, '#EF4444', "VCC"),
    ("GND (Ground)", bme_y + 1.0, '#64748B', "GND"),
    ("SCL (I2C Clock)", bme_y + 0.5, '#F59E0B', "SCL"),
    ("SDA (I2C Data)", bme_y + 0.0, '#06B6D4', "SDA"),
]

bme_pin_coords = {}
for label, py, col, key in pins_bme:
    ax.add_patch(patches.Rectangle((bme_x + bme_w - 0.4, py - 0.1), 0.5, 0.2, facecolor='#E2E8F0', edgecolor='#0F172A', zorder=4))
    ax.text(bme_x + bme_w - 0.6, py, label, fontsize=8.5, fontweight='bold', color='#F8FAFC', ha='right', va='center', zorder=5)
    bme_pin_coords[key] = (bme_x + bme_w + 0.1, py)

# -----------------------------------------------------------------------------
# 2. ESP32 WROOM-32D (RIGHT SIDE)
# -----------------------------------------------------------------------------
esp_x, esp_y, esp_w, esp_h = 12.0, 2.0, 5.5, 7.0
esp_box = patches.FancyBboxPatch((esp_x, esp_y), esp_w, esp_h, boxstyle="round,pad=0.1,rounding_size=0.2",
                                 facecolor='#1E293B', edgecolor='#3B82F6', linewidth=2.5, zorder=2)
ax.add_patch(esp_box)

# Wi-Fi Shield
rf_shield = patches.Rectangle((esp_x + 1.0, esp_y + 3.8), 3.5, 2.8, facecolor='#94A3B8', edgecolor='#CBD5E1', linewidth=1.5, zorder=3)
ax.add_patch(rf_shield)
ax.text(esp_x + 2.75, esp_y + 5.2, "ESP-WROOM-32D\nMicrocontroller", fontsize=11, fontweight='bold', color='#0F172A', ha='center', zorder=4)

# USB Port
usb = patches.Rectangle((esp_x + 2.0, esp_y - 0.3), 1.5, 0.5, facecolor='#64748B', edgecolor='#CBD5E1', linewidth=1.5, zorder=3)
ax.add_patch(usb)
ax.text(esp_x + 2.75, esp_y - 0.05, "Micro-USB", fontsize=8, color='#F8FAFC', ha='center', zorder=4)

# ESP32 Pins on Left Header
esp_pin_coords = {}
esp_pins_list = [
    ("3V3 (3.3V Power)", 7.8, '#EF4444', "3V3"),
    ("GND (Ground)", 7.2, '#64748B', "GND"),
    ("GPIO 22 (SCL)", 4.0, '#F59E0B', "GPIO22"),
    ("GPIO 21 (SDA)", 3.2, '#06B6D4', "GPIO21"),
]

for label, py, col, key in esp_pins_list:
    ax.add_patch(patches.Rectangle((esp_x - 0.3, py - 0.12), 0.5, 0.24, facecolor='#E2E8F0', edgecolor='#0F172A', zorder=4))
    ax.text(esp_x + 0.4, py, label, fontsize=9, fontweight='bold', color='#F8FAFC', ha='left', va='center', zorder=5)
    esp_pin_coords[key] = (esp_x - 0.3, py)

# -----------------------------------------------------------------------------
# 3. DRAW CONNECTING JUMPER WIRES (BEZIER SPLINES)
# -----------------------------------------------------------------------------
def draw_wire(ax, start, end, color, step_num, step_text):
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
    
    cx1 = x1 + dx * 0.45
    cy1 = y1 + dy * 0.1 + (0.4 if step_num % 2 == 0 else -0.4)
    cx2 = x1 + dx * 0.55
    cy2 = y2 - dy * 0.1 - (0.4 if step_num % 2 == 0 else -0.4)
    
    path = Path([(x1, y1), (cx1, cy1), (cx2, cy2), (x2, y2)],
                [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4])
    ax.add_patch(patches.PathPatch(path, facecolor='none', edgecolor=color, lw=4, zorder=6, alpha=0.95))
    
    ax.scatter([x1, x2], [y1, y2], color='#0B132B', s=80, zorder=7, edgecolors='white', linewidths=2)
    
    mid_x = (x1 + x2) / 2
    mid_y = (cy1 + cy2) / 2
    badge = patches.FancyBboxPatch((mid_x - 1.2, mid_y - 0.22), 2.4, 0.44, boxstyle="round,pad=0.03,rounding_size=0.08",
                                   facecolor='#1E293B', edgecolor=color, linewidth=1.5, zorder=8)
    ax.add_patch(badge)
    ax.text(mid_x, mid_y, f"Step {step_num}: {step_text}", fontsize=8, fontweight='bold', color=color, ha='center', va='center', zorder=9)

# Wire 1: VCC -> 3V3
draw_wire(ax, bme_pin_coords["VCC"], esp_pin_coords["3V3"], '#EF4444', 1, "VCC -> 3V3 (3.3V)")

# Wire 2: GND -> GND
draw_wire(ax, bme_pin_coords["GND"], esp_pin_coords["GND"], '#94A3B8', 2, "GND -> GND")

# Wire 3: SCL -> GPIO22
draw_wire(ax, bme_pin_coords["SCL"], esp_pin_coords["GPIO22"], '#F59E0B', 3, "SCL -> GPIO 22")

# Wire 4: SDA -> GPIO21
draw_wire(ax, bme_pin_coords["SDA"], esp_pin_coords["GPIO21"], '#06B6D4', 4, "SDA -> GPIO 21")

# -----------------------------------------------------------------------------
# 4. BOTTOM INSTRUCTION SUMMARY BOX
# -----------------------------------------------------------------------------
info_x, info_y, info_w, info_h = 1.0, 0.2, 16.5, 1.4
info_box = patches.FancyBboxPatch((info_x, info_y), info_w, info_h, boxstyle="round,pad=0.08,rounding_size=0.15",
                                  facecolor='#1E293B', edgecolor='#334155', linewidth=1.5, zorder=2)
ax.add_patch(info_box)

ax.text(info_x + 0.3, info_y + 1.0, "CRITICAL BME280 CONNECTION RULES:", fontsize=9.5, fontweight='bold', color='#FBBF24', zorder=4)
ax.text(info_x + 0.3, info_y + 0.65, "1. Always connect VCC to the 3V3 (3.3V) pin on ESP32. Never connect the BME280 to the 5V VIN rail.", fontsize=8.5, color='#F8FAFC', zorder=4)
ax.text(info_x + 0.3, info_y + 0.35, "2. SCL goes to GPIO 22 (I2C Clock) and SDA goes to GPIO 21 (I2C Data). The firmware auto-detects address 0x76 or 0x77.", fontsize=8.5, color='#F8FAFC', zorder=4)

plt.tight_layout()
plt.savefig(OUTPUT_PNG, dpi=200, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
plt.close()
print(f"BME280 diagram generated at {OUTPUT_PNG}")
print(f"Successfully generated BME280 Diagram: {OUTPUT_PNG}")
