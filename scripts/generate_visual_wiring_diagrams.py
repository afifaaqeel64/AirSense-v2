"""
AirSense Pakistan: High-Resolution Circuit Wiring & Hardware Assembly Visual Diagram Generator.
Renders publication-grade 4K PNG illustrations of:
1. Complete Breadboard/Jumper Circuit Wiring Diagram
2. ESP32 Pinout and Power Routing Matrix
3. Weatherproof IP65 Enclosure & Sensor Placement Blueprint
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path

from pathlib import Path

AIRSENSE_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = str(AIRSENSE_ROOT / "docs")
EXTRACTED_IMG_DIR = str(AIRSENSE_ROOT / "Campus Deployment - LATEST" / "extracted_images")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(EXTRACTED_IMG_DIR, exist_ok=True)

def draw_curved_wire(ax, x1, y1, x2, y2, color, lw=3, label=None, style='-'):
    """Draws an elegant, smooth Bezier wire curve between two pin coordinates."""
    dx = x2 - x1
    dy = y2 - y1
    
    # Control points for natural wire droop / curve
    cx1 = x1 + dx * 0.4
    cy1 = y1 + dy * 0.1 - (0.3 if dx > 0 else -0.3)
    cx2 = x1 + dx * 0.6
    cy2 = y2 - dy * 0.1 + (0.3 if dx > 0 else -0.3)
    
    verts = [(x1, y1), (cx1, cy1), (cx2, cy2), (x2, y2)]
    codes = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4]
    path = Path(verts, codes)
    
    patch = patches.PathPatch(path, facecolor='none', edgecolor=color, lw=lw, linestyle=style, zorder=4, alpha=0.9)
    ax.add_patch(patch)
    
    # Draw metal terminal dots on both ends
    ax.scatter([x1, x2], [y1, y2], color='#111827', s=45, zorder=5, edgecolors='white', linewidths=1.5)


def generate_complete_wiring_diagram():
    print("Rendering Complete AirSense Wiring Schematic (4K High Resolution)...")
    
    fig, ax = plt.subplots(figsize=(20, 11), dpi=200)
    fig.patch.set_facecolor('#0B132B') # Deep dark tech background
    ax.set_facecolor('#0B132B')
    
    ax.set_xlim(-1, 21)
    ax.set_ylim(-1, 12)
    ax.axis('off')
    
    # Title Banner
    ax.text(10, 11.4, "AirSense Pakistan | Complete Hardware Wiring Schematic", 
            fontsize=22, fontweight='bold', color='#60A5FA', ha='center', va='center')
    ax.text(10, 10.9, "COIL AI Collaborative Deployment | ESP32 WROOM-32D Multi-Sensor Pinout & Bus Mapping", 
            fontsize=12, color='#94A3B8', ha='center', va='center')
    
    # -------------------------------------------------------------------------
    # 1. ESP32 WROOM-32D (Center Module)
    # -------------------------------------------------------------------------
    esp_x, esp_y, esp_w, esp_h = 7.5, 2.0, 5.0, 7.5
    
    # Main PCB Body
    esp_body = patches.FancyBboxPatch((esp_x, esp_y), esp_w, esp_h, boxstyle="round,pad=0.1,rounding_size=0.2",
                                      facecolor='#1E293B', edgecolor='#3B82F6', linewidth=2.5, zorder=2)
    ax.add_patch(esp_body)
    
    # Wi-Fi / Bluetooth Metal Shield
    shield = patches.Rectangle((esp_x + 0.8, esp_y + 4.2), 3.4, 2.8,
                               facecolor='#94A3B8', edgecolor='#CBD5E1', linewidth=1.5, zorder=3)
    ax.add_patch(shield)
    ax.text(esp_x + 2.5, esp_y + 5.6, "ESP-WROOM-32D\nDual-Core 240MHz\nWi-Fi + BLE", 
            fontsize=10, fontweight='bold', color='#0F172A', ha='center', va='center', zorder=4)
    
    # Micro USB Port at bottom
    usb = patches.Rectangle((esp_x + 1.8, esp_y - 0.25), 1.4, 0.45, 
                            facecolor='#64748B', edgecolor='#CBD5E1', linewidth=1.5, zorder=3)
    ax.add_patch(usb)
    ax.text(esp_x + 2.5, esp_y - 0.05, "USB / Power", fontsize=8, color='#F8FAFC', ha='center', va='center', zorder=4)
    
    # Title on ESP32 Board
    ax.text(esp_x + 2.5, esp_y + 2.8, "ESP32 DEV MODULE", fontsize=11, fontweight='bold', color='#38BDF8', ha='center', va='center', zorder=4)
    ax.text(esp_x + 2.5, esp_y + 2.3, "Node UID: AIRSENSE-NODE-KHI-01", fontsize=8, color='#94A3B8', ha='center', va='center', zorder=4)
    
    # Left & Right Pin Headers on ESP32
    left_pins = [
        ("3V3 (3.3V)", 8.5),
        ("GND", 8.0),
        ("GPIO 36", 7.5),
        ("GPIO 39", 7.0),
        ("GPIO 34 (ADC)", 6.5),
        ("GPIO 35", 6.0),
        ("GPIO 32", 5.5),
        ("GPIO 33", 5.0),
        ("GPIO 25", 4.5),
        ("GPIO 26", 4.0),
        ("GPIO 27", 3.5),
        ("GPIO 14", 3.0),
        ("GPIO 12", 2.5),
    ]
    
    right_pins = [
        ("VIN (5.0V)", 8.5),
        ("GND", 8.0),
        ("GPIO 13", 7.5),
        ("GPIO 12", 7.0),
        ("GPIO 14", 6.5),
        ("GPIO 27", 6.0),
        ("GPIO 26", 5.5),
        ("GPIO 25", 5.0),
        ("GPIO 23 (MOSI)", 4.5),
        ("GPIO 22 (SCL)", 4.0),
        ("GPIO 21 (SDA)", 3.5),
        ("GPIO 19 (MISO)", 3.0),
        ("GPIO 18 (SCK)", 2.5),
    ]
    
    # Draw Pin Rectangles & Text Labels
    for name, py in left_pins:
        ax.add_patch(patches.Rectangle((esp_x - 0.25, py - 0.15), 0.5, 0.3, facecolor='#E2E8F0', edgecolor='#475569', zorder=3))
        ax.text(esp_x + 0.35, py, name, fontsize=8, color='#F8FAFC', ha='left', va='center', zorder=4)
        
    for name, py in right_pins:
        ax.add_patch(patches.Rectangle((esp_x + esp_w - 0.25, py - 0.15), 0.5, 0.3, facecolor='#E2E8F0', edgecolor='#475569', zorder=3))
        ax.text(esp_x + esp_w - 0.35, py, name, fontsize=8, color='#F8FAFC', ha='right', va='center', zorder=4)
    
    # -------------------------------------------------------------------------
    # 2. PLANTOWER PMS7003 SENSOR (Top-Right)
    # -------------------------------------------------------------------------
    pms_x, pms_y, pms_w, pms_h = 15.0, 7.2, 4.8, 3.2
    pms_box = patches.FancyBboxPatch((pms_x, pms_y), pms_w, pms_h, boxstyle="round,pad=0.08,rounding_size=0.15",
                                     facecolor='#334155', edgecolor='#0EA5E9', linewidth=2, zorder=2)
    ax.add_patch(pms_box)
    
    # Laser Sensor Visual Details
    metal_casing = patches.Rectangle((pms_x + 0.4, pms_y + 0.9), 4.0, 2.0, facecolor='#64748B', edgecolor='#94A3B8', linewidth=1.5, zorder=3)
    ax.add_patch(metal_casing)
    ax.text(pms_x + 2.4, pms_y + 2.3, "PLANTOWER PMS7003", fontsize=10, fontweight='bold', color='#F8FAFC', ha='center', zorder=4)
    ax.text(pms_x + 2.4, pms_y + 1.8, "Laser Particulate Counter\nPM1.0 / PM2.5 / PM10", fontsize=8, color='#CBD5E1', ha='center', zorder=4)
    
    # Fan inlet circle
    fan = patches.Circle((pms_x + 1.0, pms_y + 1.4), 0.35, facecolor='#1E293B', edgecolor='#38BDF8', linewidth=1.5, zorder=4)
    ax.add_patch(fan)
    
    # PMS7003 Pins (Left side of adapter board)
    pms_vcc = (pms_x, pms_y + 0.7)
    pms_gnd = (pms_x, pms_y + 0.4)
    pms_txd = (pms_x, pms_y + 0.1)
    pms_rxd = (pms_x, pms_y - 0.2)
    
    ax.text(pms_x + 0.1, pms_y + 0.7, "VCC (5V)", fontsize=7.5, color='#F87171', ha='left', va='center', zorder=5)
    ax.text(pms_x + 0.1, pms_y + 0.4, "GND", fontsize=7.5, color='#94A3B8', ha='left', va='center', zorder=5)
    ax.text(pms_x + 0.1, pms_y + 0.1, "TXD (UART)", fontsize=7.5, color='#60A5FA', ha='left', va='center', zorder=5)
    ax.text(pms_x + 0.1, pms_y - 0.2, "RXD (UART)", fontsize=7.5, color='#34D399', ha='left', va='center', zorder=5)
    
    # -------------------------------------------------------------------------
    # 3. BOSCH BME280 SENSOR (Top-Left)
    # -------------------------------------------------------------------------
    bme_x, bme_y, bme_w, bme_h = 0.5, 7.5, 4.5, 2.8
    bme_box = patches.FancyBboxPatch((bme_x, bme_y), bme_w, bme_h, boxstyle="round,pad=0.08,rounding_size=0.15",
                                     facecolor='#4C1D95', edgecolor='#A855F7', linewidth=2, zorder=2)
    ax.add_patch(bme_box)
    
    # Metal sensor chip
    bme_chip = patches.Rectangle((bme_x + 1.6, bme_y + 1.2), 1.3, 1.1, facecolor='#CBD5E1', edgecolor='#E2E8F0', linewidth=1, zorder=3)
    ax.add_patch(bme_chip)
    ax.text(bme_x + 2.25, bme_y + 2.5, "BOSCH BME280", fontsize=10, fontweight='bold', color='#F5D0FE', ha='center', zorder=4)
    ax.text(bme_x + 2.25, bme_y + 0.7, "Temp / Humidity / Pressure\nI2C Bus (Address 0x76)", fontsize=8, color='#E9D5FF', ha='center', zorder=4)
    
    # BME Pins on right edge
    bme_vcc = (bme_x + bme_w, bme_y + 2.1)
    bme_gnd = (bme_x + bme_w, bme_y + 1.6)
    bme_scl = (bme_x + bme_w, bme_y + 1.1)
    bme_sda = (bme_x + bme_w, bme_y + 0.6)
    
    ax.text(bme_x + bme_w - 0.1, bme_y + 2.1, "VCC (3.3V)", fontsize=7.5, color='#F87171', ha='right', va='center', zorder=5)
    ax.text(bme_x + bme_w - 0.1, bme_y + 1.6, "GND", fontsize=7.5, color='#94A3B8', ha='right', va='center', zorder=5)
    ax.text(bme_x + bme_w - 0.1, bme_y + 1.1, "SCL", fontsize=7.5, color='#FBBF24', ha='right', va='center', zorder=5)
    ax.text(bme_x + bme_w - 0.1, bme_y + 0.6, "SDA", fontsize=7.5, color='#38BDF8', ha='right', va='center', zorder=5)

    # -------------------------------------------------------------------------
    # 4. MICROSD SPI LOGGING MODULE (Bottom-Right)
    # -------------------------------------------------------------------------
    sd_x, sd_y, sd_w, sd_h = 15.0, 1.5, 4.8, 4.2
    sd_box = patches.FancyBboxPatch((sd_x, sd_y), sd_w, sd_h, boxstyle="round,pad=0.08,rounding_size=0.15",
                                    facecolor='#064E3B', edgecolor='#10B981', linewidth=2, zorder=2)
    ax.add_patch(sd_box)
    
    # SD Slot & Card
    sd_slot = patches.Rectangle((sd_x + 1.0, sd_y + 1.4), 2.8, 2.2, facecolor='#1F2937', edgecolor='#4ADE80', linewidth=1.5, zorder=3)
    ax.add_patch(sd_slot)
    ax.text(sd_x + 2.4, sd_y + 3.2, "MicroSD SPI Reader", fontsize=10, fontweight='bold', color='#D1FAE5', ha='center', zorder=4)
    ax.text(sd_x + 2.4, sd_y + 2.5, "Samsung EVO+ 16GB\nFAT32 Offline Ring Buffer\n180+ Days Logging", fontsize=8, color='#A7F3D0', ha='center', zorder=4)
    
    # SD Pins on left edge
    sd_cs   = (sd_x, sd_y + 3.8)
    sd_sck  = (sd_x, sd_y + 3.3)
    sd_mosi = (sd_x, sd_y + 2.8)
    sd_miso = (sd_x, sd_y + 2.3)
    sd_vcc  = (sd_x, sd_y + 1.8)
    sd_gnd  = (sd_x, sd_y + 1.3)
    
    ax.text(sd_x + 0.1, sd_y + 3.8, "CS (GPIO 5)", fontsize=7.5, color='#F472B6', ha='left', va='center', zorder=5)
    ax.text(sd_x + 0.1, sd_y + 3.3, "SCK (GPIO 18)", fontsize=7.5, color='#FBBF24', ha='left', va='center', zorder=5)
    ax.text(sd_x + 0.1, sd_y + 2.8, "MOSI (GPIO 23)", fontsize=7.5, color='#34D399', ha='left', va='center', zorder=5)
    ax.text(sd_x + 0.1, sd_y + 2.3, "MISO (GPIO 19)", fontsize=7.5, color='#60A5FA', ha='left', va='center', zorder=5)
    ax.text(sd_x + 0.1, sd_y + 1.8, "VCC (3.3V)", fontsize=7.5, color='#F87171', ha='left', va='center', zorder=5)
    ax.text(sd_x + 0.1, sd_y + 1.3, "GND", fontsize=7.5, color='#94A3B8', ha='left', va='center', zorder=5)

    # -------------------------------------------------------------------------
    # 5. RAINDROP MOISTURE SENSOR BOARD (Bottom-Left)
    # -------------------------------------------------------------------------
    rain_x, rain_y, rain_w, rain_h = 0.5, 1.5, 4.5, 4.2
    rain_box = patches.FancyBboxPatch((rain_x, rain_y), rain_w, rain_h, boxstyle="round,pad=0.08,rounding_size=0.15",
                                      facecolor='#1E3A8A', edgecolor='#38BDF8', linewidth=2, zorder=2)
    ax.add_patch(rain_box)
    
    # Forked detection plate drawing
    plate = patches.Rectangle((rain_x + 0.6, rain_y + 1.6), 3.3, 2.0, facecolor='#334155', edgecolor='#94A3B8', linewidth=1.5, zorder=3)
    ax.add_patch(plate)
    # Gold traces on plate
    for tx in [0.9, 1.4, 1.9, 2.4, 2.9, 3.4]:
        ax.plot([rain_x + tx, rain_x + tx], [rain_y + 1.8, rain_y + 3.4], color='#FCD34D', lw=2, zorder=4)
        
    ax.text(rain_x + 2.25, rain_y + 3.9, "Raindrop Sensing Board", fontsize=10, fontweight='bold', color='#E0F2FE', ha='center', zorder=4)
    ax.text(rain_x + 2.25, rain_y + 0.8, "Wet Deposition & Washout Flag\nAnalog Moisture Level", fontsize=8, color='#BAE6FD', ha='center', zorder=4)
    
    # Rain Pins on right edge
    rain_vcc = (rain_x + rain_w, rain_y + 2.5)
    rain_gnd = (rain_x + rain_w, rain_y + 2.0)
    rain_ao  = (rain_x + rain_w, rain_y + 1.5)
    
    ax.text(rain_x + rain_w - 0.1, rain_y + 2.5, "VCC (3.3V)", fontsize=7.5, color='#F87171', ha='right', va='center', zorder=5)
    ax.text(rain_x + rain_w - 0.1, rain_y + 2.0, "GND", fontsize=7.5, color='#94A3B8', ha='right', va='center', zorder=5)
    ax.text(rain_x + rain_w - 0.1, rain_y + 1.5, "AO (Analog Out)", fontsize=7.5, color='#38BDF8', ha='right', va='center', zorder=5)

    # -------------------------------------------------------------------------
    # 6. ROUTE ALL JUMPER WIRES (ELEGANT COLORED BEZIER CURVES)
    # -------------------------------------------------------------------------
    
    # PMS7003 Wires -> ESP32
    draw_curved_wire(ax, pms_vcc[0], pms_vcc[1], esp_x + esp_w, 8.5, color='#EF4444', lw=3) # VCC to VIN 5V
    draw_curved_wire(ax, pms_gnd[0], pms_gnd[1], esp_x + esp_w, 8.0, color='#64748B', lw=3) # GND to GND
    draw_curved_wire(ax, pms_txd[0], pms_txd[1], esp_x + esp_w, 2.0, color='#3B82F6', lw=3) # TXD to GPIO 16 (RX2)
    draw_curved_wire(ax, pms_rxd[0], pms_rxd[1], esp_x + esp_w, 1.5, color='#10B981', lw=3) # RXD to GPIO 17 (TX2)

    # BME280 Wires -> ESP32
    draw_curved_wire(ax, bme_vcc[0], bme_vcc[1], esp_x, 8.5, color='#EF4444', lw=3) # VCC to 3V3
    draw_curved_wire(ax, bme_gnd[0], bme_gnd[1], esp_x, 8.0, color='#64748B', lw=3) # GND to GND
    draw_curved_wire(ax, bme_scl[0], bme_scl[1], esp_x + esp_w, 4.0, color='#F59E0B', lw=3) # SCL to GPIO 22
    draw_curved_wire(ax, bme_sda[0], bme_sda[1], esp_x + esp_w, 3.5, color='#06B6D4', lw=3) # SDA to GPIO 21

    # MicroSD Wires -> ESP32
    draw_curved_wire(ax, sd_vcc[0], sd_vcc[1], esp_x, 8.5, color='#EF4444', lw=2.5, style='--') # 3.3V
    draw_curved_wire(ax, sd_gnd[0], sd_gnd[1], esp_x, 8.0, color='#64748B', lw=2.5, style='--') # GND
    draw_curved_wire(ax, sd_cs[0], sd_cs[1], esp_x + esp_w, 1.0, color='#EC4899', lw=3) # CS to GPIO 5
    draw_curved_wire(ax, sd_sck[0], sd_sck[1], esp_x + esp_w, 2.5, color='#F59E0B', lw=3) # SCK to GPIO 18
    draw_curved_wire(ax, sd_mosi[0], sd_mosi[1], esp_x + esp_w, 4.5, color='#10B981', lw=3) # MOSI to GPIO 23
    draw_curved_wire(ax, sd_miso[0], sd_miso[1], esp_x + esp_w, 3.0, color='#3B82F6', lw=3) # MISO to GPIO 19

    # Rain Sensor Wires -> ESP32
    draw_curved_wire(ax, rain_vcc[0], rain_vcc[1], esp_x, 8.5, color='#EF4444', lw=2.5, style='--') # 3.3V
    draw_curved_wire(ax, rain_gnd[0], rain_gnd[1], esp_x, 8.0, color='#64748B', lw=2.5, style='--') # GND
    draw_curved_wire(ax, rain_ao[0], rain_ao[1], esp_x, 6.5, color='#06B6D4', lw=3) # AO to GPIO 34 (ADC1)

    # -------------------------------------------------------------------------
    # 7. COLOR LEGEND & ENGINEERING NOTES
    # -------------------------------------------------------------------------
    leg_x, leg_y, leg_w, leg_h = 0.5, 0.1, 19.3, 0.9
    leg_box = patches.FancyBboxPatch((leg_x, leg_y), leg_w, leg_h, boxstyle="round,pad=0.05,rounding_size=0.1",
                                     facecolor='#1E293B', edgecolor='#334155', linewidth=1.5, zorder=2)
    ax.add_patch(leg_box)
    
    # Legend color pills
    legend_items = [
        ("RED: Power (5V VIN / 3.3V)", '#EF4444', 1.0),
        ("GREY: Common Ground (GND)", '#64748B', 5.2),
        ("YELLOW: Clock (I2C SCL / SPI SCK)", '#F59E0B', 9.2),
        ("BLUE: Data In (UART RX / SPI MISO)", '#3B82F6', 13.5),
        ("GREEN: Data Out (UART TX / SPI MOSI)", '#10B981', 17.2),
    ]
    for text, col, lx in legend_items:
        ax.add_patch(patches.Circle((lx, 0.55), 0.15, facecolor=col, edgecolor='white', linewidth=1, zorder=4))
        ax.text(lx + 0.3, 0.55, text, fontsize=8.5, fontweight='bold', color='#F8FAFC', va='center', zorder=4)

    # Save to disk
    out_png = os.path.join(OUTPUT_DIR, "airsense_complete_wiring_diagram.png")
    plt.tight_layout()
    plt.savefig(out_png, dpi=200, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    
    # Copy to images
    import shutil
    shutil.copyfile(out_png, os.path.join(EXTRACTED_IMG_DIR, "airsense_complete_wiring_diagram.png"))
    print(f"Successfully generated 4K Wiring Diagram PNG: {out_png}")
    return out_png


def generate_enclosure_assembly_diagram():
    print("Rendering IP65 Weatherproof Enclosure 3D Assembly Diagram...")
    
    fig, ax = plt.subplots(figsize=(16, 10), dpi=200)
    fig.patch.set_facecolor('#0B132B')
    ax.set_facecolor('#0B132B')
    ax.set_xlim(-1, 17)
    ax.set_ylim(-1, 11)
    ax.axis('off')
    
    ax.text(8, 10.4, "AirSense Pakistan | IP65 Weatherproof Rooftop Assembly Blueprint", 
            fontsize=20, fontweight='bold', color='#60A5FA', ha='center', va='center')
    ax.text(8, 9.9, "Component Arrangement, Airflow Geometry, Solar Shielding & Sealing Protocol", 
            fontsize=11, color='#94A3B8', ha='center', va='center')
    
    # Main IP65 Enclosure Box
    enc_x, enc_y, enc_w, enc_h = 3.5, 1.2, 9.0, 7.8
    enc_box = patches.FancyBboxPatch((enc_x, enc_y), enc_w, enc_h, boxstyle="round,pad=0.15,rounding_size=0.3",
                                     facecolor='#1E293B', edgecolor='#38BDF8', linewidth=3, zorder=2)
    ax.add_patch(enc_box)
    ax.text(enc_x + 0.4, enc_y + enc_h - 0.4, "IP65 Weatherproof Junction Enclosure (Interior)", fontsize=10, fontweight='bold', color='#38BDF8', zorder=4)
    
    # 1. ESP32 on Main Baseplate
    esp = patches.Rectangle((enc_x + 1.0, enc_y + 1.2), 3.2, 4.0, facecolor='#0F172A', edgecolor='#3B82F6', linewidth=2, zorder=3)
    ax.add_patch(esp)
    ax.text(enc_x + 2.6, enc_y + 3.2, "ESP32 Controller\n& MicroSD Logger\n(Mounted on standoffs)", fontsize=9, fontweight='bold', color='#F8FAFC', ha='center', zorder=4)
    
    # 2. Plantower PMS7003 Air Path
    pms = patches.Rectangle((enc_x + 4.8, enc_y + 3.8), 3.4, 2.6, facecolor='#334155', edgecolor='#0EA5E9', linewidth=2, zorder=3)
    ax.add_patch(pms)
    ax.text(enc_x + 6.5, enc_y + 5.1, "Plantower PMS7003\nLaser Sensor\n(Fan Intake at Wall)", fontsize=9, fontweight='bold', color='#F8FAFC', ha='center', zorder=4)
    
    # Airflow Vents
    ax.arrow(enc_x + enc_w + 1.8, enc_y + 5.1, -1.5, 0, head_width=0.3, head_length=0.4, fc='#38BDF8', ec='#38BDF8', lw=2, zorder=5)
    ax.text(enc_x + enc_w + 2.0, enc_y + 5.1, "Continuous Ambient\nAirflow Intake", fontsize=8.5, fontweight='bold', color='#38BDF8', va='center', zorder=5)
    
    # 3. Solar Radiation Shield (External Louvered)
    shield_x, shield_y = enc_x - 3.0, enc_y + 3.5
    for i in range(5):
        plate = patches.FancyBboxPatch((shield_x, shield_y + i * 0.45), 2.2, 0.35, boxstyle="round,pad=0.02,rounding_size=0.08",
                                       facecolor='#F8FAFC', edgecolor='#CBD5E1', linewidth=1.5, zorder=4)
        ax.add_patch(plate)
        
    ax.text(shield_x + 1.1, shield_y - 0.4, "White Multi-Plate\nSolar Shield", fontsize=8.5, fontweight='bold', color='#F8FAFC', ha='center', zorder=5)
    
    # BME280 inside shield
    bme_in_shield = patches.Rectangle((shield_x + 0.6, shield_y + 0.8), 1.0, 0.8, facecolor='#A855F7', edgecolor='white', linewidth=1, zorder=5)
    ax.add_patch(bme_in_shield)
    ax.text(shield_x + 1.1, shield_y + 1.2, "BME280", fontsize=7.5, fontweight='bold', color='white', ha='center', zorder=6)
    
    # 4. Cable Gland & Power Ingress at Bottom
    gland = patches.Rectangle((enc_x + 2.0, enc_y - 0.6), 1.2, 0.6, facecolor='#64748B', edgecolor='#94A3B8', linewidth=1.5, zorder=3)
    ax.add_patch(gland)
    ax.text(enc_x + 2.6, enc_y - 0.3, "Cable Gland", fontsize=7.5, color='#F8FAFC', ha='center', va='center', zorder=4)
    
    # Extension cable
    ax.plot([enc_x + 2.6, enc_x + 2.6], [enc_y - 0.6, enc_y - 1.2], color='#F59E0B', lw=4, zorder=4)
    ax.text(enc_x + 2.6, enc_y - 1.4, "10m Clopal 3-Pin\nHeavy-Duty Power Lead\n(Sealed with GMSA Silicone)", fontsize=8, color='#FBBF24', ha='center', va='top', zorder=4)
    
    # 5. Stainless Mounting Clamps on Rear
    clamp_top = patches.Rectangle((enc_x + enc_w + 0.1, enc_y + 6.0), 0.6, 0.8, facecolor='#94A3B8', edgecolor='white', linewidth=1.5, zorder=3)
    clamp_bot = patches.Rectangle((enc_x + enc_w + 0.1, enc_y + 2.0), 0.6, 0.8, facecolor='#94A3B8', edgecolor='white', linewidth=1.5, zorder=3)
    ax.add_patch(clamp_top)
    ax.add_patch(clamp_bot)
    ax.text(enc_x + enc_w + 0.8, enc_y + 6.4, "2-inch Stainless Hose Clamp\n(Secures to Rooftop Parapet)", fontsize=8, color='#CBD5E1', va='center', zorder=4)
    ax.text(enc_x + enc_w + 0.8, enc_y + 2.4, "2-inch Stainless Hose Clamp\n(Lower Mounting Anchor)", fontsize=8, color='#CBD5E1', va='center', zorder=4)

    out_png = os.path.join(OUTPUT_DIR, "enclosure_assembly_diagram.png")
    plt.tight_layout()
    plt.savefig(out_png, dpi=200, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    
    import shutil
    shutil.copyfile(out_png, os.path.join(EXTRACTED_IMG_DIR, "enclosure_assembly_diagram.png"))
    print(f"Successfully generated Enclosure Assembly PNG: {out_png}")
    return out_png


def main():
    generate_complete_wiring_diagram()
    generate_enclosure_assembly_diagram()
    print("\n========================================================")
    print("ALL VISUAL DIAGRAMS GENERATED AND SAVED SUCCESSFULLY!")
    print("========================================================")

if __name__ == "__main__":
    main()
