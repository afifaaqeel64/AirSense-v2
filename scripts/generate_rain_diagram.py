"""
Generate Dedicated High-Resolution Visual Diagram: ESP32 to Raindrop / Moisture Sensor Connection.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path
import shutil

from pathlib import Path

AIRSENSE_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PNG = str(AIRSENSE_ROOT / "docs" / "rain_sensor_esp32_wiring_visual.png")

fig, ax = plt.subplots(figsize=(19, 10), dpi=200)
fig.patch.set_facecolor('#0B132B')
ax.set_facecolor('#0B132B')
ax.set_xlim(-1, 20)
ax.set_ylim(-1, 11)
ax.axis('off')

# Title
ax.text(9.5, 10.4, "AirSense Pakistan | Raindrop / Moisture Sensor Visual Wiring Guide", 
        fontsize=22, fontweight='bold', color='#38BDF8', ha='center', va='center')
ax.text(9.5, 9.9, "Rain Plate to Comparator Module & ESP32 Analog Ingestion (GPIO 34) | COIL AI Initiative", 
        fontsize=12, color='#94A3B8', ha='center', va='center')

# -----------------------------------------------------------------------------
# 1. RAIN COLLECTOR PLATE (FAR LEFT)
# -----------------------------------------------------------------------------
pl_x, pl_y, pl_w, pl_h = 0.5, 3.0, 4.2, 5.2
pl_box = patches.FancyBboxPatch((pl_x, pl_y), pl_w, pl_h, boxstyle="round,pad=0.1,rounding_size=0.15",
                                facecolor='#1E293B', edgecolor='#64748B', linewidth=2, zorder=2)
ax.add_patch(pl_box)

# Metallic Zigzag Tracks on Plate
for ty in [3.8, 4.4, 5.0, 5.6, 6.2, 6.8, 7.4]:
    ax.plot([pl_x + 0.5, pl_x + pl_w - 0.5], [ty, ty], color='#FCD34D', lw=2.5, zorder=3)
for tx in [1.2, 2.0, 2.8, 3.6]:
    ax.plot([tx, tx], [3.8, 7.4], color='#FCD34D', lw=1.5, zorder=3)

ax.text(pl_x + pl_w/2, pl_y + pl_h - 0.4, "Rain Collector Plate", fontsize=10, fontweight='bold', color='#F8FAFC', ha='center', zorder=4)
ax.text(pl_x + pl_w/2, pl_y + 0.4, "2 Header Pins on Edge", fontsize=8.5, color='#94A3B8', ha='center', zorder=4)

# 2 Pins on Plate
p1_coord = (pl_x + pl_w, pl_y + 2.2)
p2_coord = (pl_x + pl_w, pl_y + 1.6)
ax.add_patch(patches.Rectangle((pl_x + pl_w - 0.2, pl_y + 2.05), 0.4, 0.3, facecolor='#E2E8F0', edgecolor='#0F172A', zorder=4))
ax.add_patch(patches.Rectangle((pl_x + pl_w - 0.2, pl_y + 1.45), 0.4, 0.3, facecolor='#E2E8F0', edgecolor='#0F172A', zorder=4))

# -----------------------------------------------------------------------------
# 2. COMPARATOR / CONTROL BOARD (MIDDLE)
# -----------------------------------------------------------------------------
cb_x, cb_y, cb_w, cb_h = 6.2, 2.5, 5.0, 6.2
cb_box = patches.FancyBboxPatch((cb_x, cb_y), cb_w, cb_h, boxstyle="round,pad=0.1,rounding_size=0.15",
                                facecolor='#1E3A8A', edgecolor='#3B82F6', linewidth=2.5, zorder=2)
ax.add_patch(cb_box)

# LM393 Chip
chip = patches.Rectangle((cb_x + 1.6, cb_y + 2.8), 1.8, 1.4, facecolor='#0F172A', edgecolor='#64748B', linewidth=1.5, zorder=3)
ax.add_patch(chip)
ax.text(cb_x + 2.5, cb_y + 3.5, "LM393\nComparator", fontsize=8, fontweight='bold', color='#E0F2FE', ha='center', va='center', zorder=4)

# Potentiometer Dial
pot = patches.Circle((cb_x + 2.5, cb_y + 4.9), 0.5, facecolor='#0284C7', edgecolor='#BAE6FD', linewidth=1.5, zorder=3)
ax.add_patch(pot)
ax.text(cb_x + 2.5, cb_y + 4.9, "ADJ", fontsize=7, color='white', ha='center', va='center', zorder=4)

ax.text(cb_x + cb_w/2, cb_y + cb_h - 0.4, "Control Module Board", fontsize=10, fontweight='bold', color='#BAE6FD', ha='center', zorder=4)

# 2-Pin Input on Left of Control Board
cb_in1 = (cb_x, cb_y + 2.2)
cb_in2 = (cb_x, cb_y + 1.6)
ax.add_patch(patches.Rectangle((cb_x - 0.2, cb_y + 2.05), 0.4, 0.3, facecolor='#E2E8F0', edgecolor='#0F172A', zorder=4))
ax.add_patch(patches.Rectangle((cb_x - 0.2, cb_y + 1.45), 0.4, 0.3, facecolor='#E2E8F0', edgecolor='#0F172A', zorder=4))

# 4-Pin Output on Right of Control Board
cb_pins = [
    ("VCC (3.3V Power)", cb_y + 2.2, '#EF4444', "VCC"),
    ("GND (Ground)", cb_y + 1.6, '#64748B', "GND"),
    ("DO (Digital - EMPTY)", cb_y + 1.0, '#94A3B8', "DO"),
    ("AO (Analog Out)", cb_y + 0.4, '#06B6D4', "AO"),
]

cb_pin_coords = {}
for label, py, col, key in cb_pins:
    ax.add_patch(patches.Rectangle((cb_x + cb_w - 0.3, py - 0.1), 0.5, 0.2, facecolor='#E2E8F0', edgecolor='#0F172A', zorder=4))
    ax.text(cb_x + cb_w - 0.5, py, label, fontsize=8, fontweight='bold', color='#F8FAFC', ha='right', va='center', zorder=5)
    cb_pin_coords[key] = (cb_x + cb_w + 0.1, py)

# -----------------------------------------------------------------------------
# 3. ESP32 WROOM-32D (RIGHT SIDE)
# -----------------------------------------------------------------------------
esp_x, esp_y, esp_w, esp_h = 13.5, 2.0, 5.5, 7.0
esp_box = patches.FancyBboxPatch((esp_x, esp_y), esp_w, esp_h, boxstyle="round,pad=0.1,rounding_size=0.2",
                                 facecolor='#1E293B', edgecolor='#3B82F6', linewidth=2.5, zorder=2)
ax.add_patch(esp_box)

# Wi-Fi Shield
rf_shield = patches.Rectangle((esp_x + 1.0, esp_y + 3.8), 3.5, 2.8, facecolor='#94A3B8', edgecolor='#CBD5E1', linewidth=1.5, zorder=3)
ax.add_patch(rf_shield)
ax.text(esp_x + 2.75, esp_y + 5.2, "ESP-WROOM-32D\nMicrocontroller", fontsize=11, fontweight='bold', color='#0F172A', ha='center', zorder=4)

# ESP32 Pins
esp_pin_coords = {}
esp_pins_list = [
    ("3V3 (3.3V Power)", 7.8, '#EF4444', "3V3"),
    ("GND (Ground)", 7.2, '#64748B', "GND"),
    ("GPIO 34 (ADC1_CH6)", 4.2, '#06B6D4', "GPIO34"),
]

for label, py, col, key in esp_pins_list:
    ax.add_patch(patches.Rectangle((esp_x - 0.3, py - 0.12), 0.5, 0.24, facecolor='#E2E8F0', edgecolor='#0F172A', zorder=4))
    ax.text(esp_x + 0.4, py, label, fontsize=9, fontweight='bold', color='#F8FAFC', ha='left', va='center', zorder=5)
    esp_pin_coords[key] = (esp_x - 0.3, py)

# -----------------------------------------------------------------------------
# 4. DRAW CONNECTING WIRES
# -----------------------------------------------------------------------------
# Plate to Control Board (2 wires)
ax.plot([p1_coord[0], cb_in1[0]], [p1_coord[1], cb_in1[1]], color='#94A3B8', lw=3, zorder=6)
ax.plot([p2_coord[0], cb_in2[0]], [p2_coord[1], cb_in2[1]], color='#94A3B8', lw=3, zorder=6)
ax.text((p1_coord[0] + cb_in1[0])/2, p1_coord[1] + 0.4, "2-Wire Link Cable\n(Any Polarity)", fontsize=8, color='#BAE6FD', ha='center', zorder=7)

def draw_wire(ax, start, end, color, step_num, step_text):
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
    cx1 = x1 + dx * 0.45
    cy1 = y1 + dy * 0.1 + (0.3 if step_num % 2 == 0 else -0.3)
    cx2 = x1 + dx * 0.55
    cy2 = y2 - dy * 0.1 - (0.3 if step_num % 2 == 0 else -0.3)
    path = Path([(x1, y1), (cx1, cy1), (cx2, cy2), (x2, y2)],
                [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4])
    ax.add_patch(patches.PathPatch(path, facecolor='none', edgecolor=color, lw=4, zorder=6, alpha=0.95))
    ax.scatter([x1, x2], [y1, y2], color='#0B132B', s=70, zorder=7, edgecolors='white', linewidths=2)
    
    mid_x = (x1 + x2) / 2
    mid_y = (cy1 + cy2) / 2
    badge = patches.FancyBboxPatch((mid_x - 1.1, mid_y - 0.2), 2.2, 0.4, boxstyle="round,pad=0.03,rounding_size=0.08",
                                   facecolor='#1E293B', edgecolor=color, linewidth=1.5, zorder=8)
    ax.add_patch(badge)
    ax.text(mid_x, mid_y, f"Step {step_num}: {step_text}", fontsize=7.5, fontweight='bold', color=color, ha='center', va='center', zorder=9)

# Control Board -> ESP32
draw_wire(ax, cb_pin_coords["VCC"], esp_pin_coords["3V3"], '#EF4444', 1, "VCC -> 3V3 (3.3V)")
draw_wire(ax, cb_pin_coords["GND"], esp_pin_coords["GND"], '#94A3B8', 2, "GND -> GND")
draw_wire(ax, cb_pin_coords["AO"], esp_pin_coords["GPIO34"], '#06B6D4', 3, "AO -> GPIO 34 (ADC1)")

# DO pin note
ax.text(cb_pin_coords["DO"][0] + 0.3, cb_pin_coords["DO"][1], "[ LEAVE UNCONNECTED / EMPTY ]", fontsize=8, color='#F87171', va='center', zorder=6)

# -----------------------------------------------------------------------------
# 5. BOTTOM INSTRUCTION SUMMARY BOX
# -----------------------------------------------------------------------------
info_x, info_y, info_w, info_h = 0.5, 0.2, 18.5, 1.4
info_box = patches.FancyBboxPatch((info_x, info_y), info_w, info_h, boxstyle="round,pad=0.08,rounding_size=0.15",
                                  facecolor='#1E293B', edgecolor='#334155', linewidth=1.5, zorder=2)
ax.add_patch(info_box)

ax.text(info_x + 0.3, info_y + 1.0, "CRITICAL RAIN SENSOR RULES:", fontsize=9.5, fontweight='bold', color='#FBBF24', zorder=4)
ax.text(info_x + 0.3, info_y + 0.65, "1. Connect the Rain Plate to the 2-pin header on the small control board using the 2-wire cable (polarity does not matter).", fontsize=8.5, color='#F8FAFC', zorder=4)
ax.text(info_x + 0.3, info_y + 0.35, "2. Connect VCC to 3V3, GND to GND, and AO to GPIO 34 on the ESP32. Leave DO empty because our firmware reads analog ADC gradient.", fontsize=8.5, color='#F8FAFC', zorder=4)

plt.tight_layout()
plt.savefig(OUTPUT_PNG, dpi=200, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
plt.close()

print(f"Successfully generated Rain Sensor Diagram: {OUTPUT_PNG}")
