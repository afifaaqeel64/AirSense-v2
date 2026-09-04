"""
Generate Dedicated High-Resolution Visual Diagram: ESP32 to PMS7003 Laser PM Sensor Connection.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path
import shutil

from pathlib import Path

AIRSENSE_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PNG = str(AIRSENSE_ROOT / "docs" / "pms7003_esp32_wiring_visual.png")

fig, ax = plt.subplots(figsize=(18, 10), dpi=200)
fig.patch.set_facecolor('#0B132B')
ax.set_facecolor('#0B132B')
ax.set_xlim(-1, 19)
ax.set_ylim(-1, 11)
ax.axis('off')

# Title
ax.text(9, 10.4, "AirSense Pakistan | ESP32 to PMS7003 Visual Wiring Guide", 
        fontsize=22, fontweight='bold', color='#60A5FA', ha='center', va='center')
ax.text(9, 9.9, "Step-by-Step Color-Coded Physical Connection Guide | COIL AI Initiative", 
        fontsize=12, color='#94A3B8', ha='center', va='center')

# -----------------------------------------------------------------------------
# 1. PLANTOWER PMS7003 SENSOR (LEFT SIDE)
# -----------------------------------------------------------------------------
pms_x, pms_y, pms_w, pms_h = 1.0, 2.0, 6.0, 7.0
pms_box = patches.FancyBboxPatch((pms_x, pms_y), pms_w, pms_h, boxstyle="round,pad=0.1,rounding_size=0.2",
                                 facecolor='#1E293B', edgecolor='#0EA5E9', linewidth=2.5, zorder=2)
ax.add_patch(pms_box)

# Metal body
metal = patches.Rectangle((pms_x + 0.5, pms_y + 2.8), 5.0, 3.8, facecolor='#475569', edgecolor='#94A3B8', linewidth=2, zorder=3)
ax.add_patch(metal)
ax.text(pms_x + 3.0, pms_y + 5.2, "PLANTOWER PMS7003", fontsize=12, fontweight='bold', color='#F8FAFC', ha='center', zorder=4)
ax.text(pms_x + 3.0, pms_y + 4.5, "Laser Scattering Dust Sensor\n(Measures PM1.0, PM2.5, PM10)", fontsize=9, color='#CBD5E1', ha='center', zorder=4)

# Fan circle
fan = patches.Circle((pms_x + 1.4, pms_y + 3.6), 0.5, facecolor='#0F172A', edgecolor='#38BDF8', linewidth=2, zorder=4)
ax.add_patch(fan)
ax.text(pms_x + 1.4, pms_y + 3.6, "FAN", fontsize=7, fontweight='bold', color='#38BDF8', ha='center', va='center', zorder=5)

# Adapter Board (Bottom of PMS7003)
ad_x, ad_y, ad_w, ad_h = pms_x + 0.5, pms_y + 0.4, 5.0, 2.0
adapter = patches.FancyBboxPatch((ad_x, ad_y), ad_w, ad_h, boxstyle="round,pad=0.05,rounding_size=0.1",
                                 facecolor='#065F46', edgecolor='#10B981', linewidth=1.5, zorder=3)
ax.add_patch(adapter)
ax.text(ad_x + 2.5, ad_y + 1.6, "PMS7003 Breakout / Adapter Board", fontsize=9, fontweight='bold', color='#D1FAE5', ha='center', zorder=4)

# Pins on Adapter Board
pins_pms = [
    ("Pin 1/2: VCC (5V)", ad_y + 1.2, '#EF4444', "VCC"),
    ("Pin 3: GND", ad_y + 0.8, '#64748B', "GND"),
    ("Pin 4: TXD (Data)", ad_y + 0.4, '#3B82F6', "TXD"),
    ("Pin 5: RXD (Data)", ad_y + 0.0, '#10B981', "RXD"),
]

pms_pin_coords = {}
for label, py, col, key in pins_pms:
    ax.add_patch(patches.Rectangle((ad_x + ad_w - 0.4, py - 0.1), 0.5, 0.2, facecolor='#E2E8F0', edgecolor='#0F172A', zorder=4))
    ax.text(ad_x + ad_w - 0.6, py, label, fontsize=8.5, fontweight='bold', color='#F8FAFC', ha='right', va='center', zorder=5)
    pms_pin_coords[key] = (ad_x + ad_w + 0.1, py)

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
    ("VIN (5.0V Power)", 7.8, '#EF4444', "VIN"),
    ("GND (Ground)", 7.2, '#64748B', "GND"),
    ("GPIO 16 (RX2)", 4.0, '#3B82F6', "GPIO16"),
    ("GPIO 17 (TX2)", 3.2, '#10B981', "GPIO17"),
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
    
    # End dots
    ax.scatter([x1, x2], [y1, y2], color='#0B132B', s=80, zorder=7, edgecolors='white', linewidths=2)
    
    # Step badge on wire center
    mid_x = (x1 + x2) / 2
    mid_y = (cy1 + cy2) / 2
    badge = patches.FancyBboxPatch((mid_x - 1.2, mid_y - 0.22), 2.4, 0.44, boxstyle="round,pad=0.03,rounding_size=0.08",
                                   facecolor='#1E293B', edgecolor=color, linewidth=1.5, zorder=8)
    ax.add_patch(badge)
    ax.text(mid_x, mid_y, f"Step {step_num}: {step_text}", fontsize=8, fontweight='bold', color=color, ha='center', va='center', zorder=9)

# Wire 1: VCC -> VIN (5V)
draw_wire(ax, pms_pin_coords["VCC"], esp_pin_coords["VIN"], '#EF4444', 1, "VCC -> VIN (5V)")

# Wire 2: GND -> GND
draw_wire(ax, pms_pin_coords["GND"], esp_pin_coords["GND"], '#94A3B8', 2, "GND -> GND")

# Wire 3: TXD -> GPIO16
draw_wire(ax, pms_pin_coords["TXD"], esp_pin_coords["GPIO16"], '#38BDF8', 3, "TXD -> GPIO 16 (RX2)")

# Wire 4: RXD -> GPIO17
draw_wire(ax, pms_pin_coords["RXD"], esp_pin_coords["GPIO17"], '#34D399', 4, "RXD -> GPIO 17 (TX2)")

# -----------------------------------------------------------------------------
# 4. BOTTOM INSTRUCTION SUMMARY BOX
# -----------------------------------------------------------------------------
info_x, info_y, info_w, info_h = 1.0, 0.2, 16.5, 1.4
info_box = patches.FancyBboxPatch((info_x, info_y), info_w, info_h, boxstyle="round,pad=0.08,rounding_size=0.15",
                                  facecolor='#1E293B', edgecolor='#334155', linewidth=1.5, zorder=2)
ax.add_patch(info_box)

ax.text(info_x + 0.3, info_y + 1.0, "CRITICAL CONNECTION RULES:", fontsize=9.5, fontweight='bold', color='#FBBF24', zorder=4)
ax.text(info_x + 0.3, info_y + 0.65, "1. Always connect VCC to VIN (5V) on ESP32 so the laser diode and internal fan receive adequate spinning power.", fontsize=8.5, color='#F8FAFC', zorder=4)
ax.text(info_x + 0.3, info_y + 0.35, "2. TXD connects to GPIO 16 (UART2 RX) and RXD connects to GPIO 17 (UART2 TX). Leave SET and RESET pins empty.", fontsize=8.5, color='#F8FAFC', zorder=4)

plt.tight_layout()
plt.savefig(OUTPUT_PNG, dpi=200, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
plt.close()

print(f"Successfully generated PMS7003 Diagram: {OUTPUT_PNG}")
