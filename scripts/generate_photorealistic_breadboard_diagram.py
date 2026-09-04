import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path
import numpy as np

def draw_breadboard_wiring():
    fig, ax = plt.subplots(figsize=(22, 14), dpi=300)
    fig.patch.set_facecolor('#0B0F19')
    ax.set_facecolor('#0B0F19')
    ax.set_xlim(-1, 23)
    ax.set_ylim(-1, 15)
    ax.axis('off')

    # Title
    ax.text(11, 14.3, "AirSense Pakistan | Physical Breadboard Wiring Blueprint", 
            fontsize=22, fontweight='bold', color='#38BDF8', ha='center', va='center')
    ax.text(11, 13.8, "ESP32 WROOM-32D Dual-Rail (3.3V & 5.0V) Complete Multi-Sensor Breadboard Assembly", 
            fontsize=12, color='#94A3B8', ha='center', va='center')

    # --- 1. SOLDERLESS BREADBOARD (830-Point) ---
    bb_x, bb_y, bb_w, bb_h = 4.0, 1.0, 14.0, 12.0
    bb_bg = patches.FancyBboxPatch((bb_x, bb_y), bb_w, bb_h, boxstyle="round,pad=0.2,rounding_size=0.3",
                                   facecolor='#F8FAFC', edgecolor='#94A3B8', linewidth=3, zorder=1)
    ax.add_patch(bb_bg)

    # Breadboard Center Notch / Trench
    ax.axvspan(bb_x + 6.8, bb_x + 7.2, ymin=0.15, ymax=0.85, color='#CBD5E1', zorder=2)
    ax.text(bb_x + 7.0, bb_y + 0.4, "CENTER DIVIDER TROUGH", fontsize=8, color='#64748B', ha='center', va='center', rotation=90, zorder=3)

    # Power Rails Visuals
    # Left 3.3V Rail (Red + / Blue -)
    l_rail_x = bb_x + 0.8
    ax.plot([l_rail_x, l_rail_x], [bb_y + 1, bb_y + bb_h - 1], color='#EF4444', lw=3, zorder=2)
    ax.plot([l_rail_x + 0.6, l_rail_x + 0.6], [bb_y + 1, bb_y + bb_h - 1], color='#3B82F6', lw=3, zorder=2)
    ax.text(l_rail_x, bb_y + bb_h - 0.5, "+ 3.3V RAIL", fontsize=9, fontweight='bold', color='#EF4444', ha='center', zorder=3)
    ax.text(l_rail_x + 0.6, bb_y + bb_h - 0.5, "- GND", fontsize=9, fontweight='bold', color='#3B82F6', ha='center', zorder=3)

    # Right 5.0V Rail (Red + / Blue -)
    r_rail_x = bb_x + bb_w - 1.4
    ax.plot([r_rail_x, r_rail_x], [bb_y + 1, bb_y + bb_h - 1], color='#EF4444', lw=3, zorder=2)
    ax.plot([r_rail_x + 0.6, r_rail_x + 0.6], [bb_y + 1, bb_y + bb_h - 1], color='#3B82F6', lw=3, zorder=2)
    ax.text(r_rail_x, bb_y + bb_h - 0.5, "+ 5.0V (VIN)", fontsize=9, fontweight='bold', color='#EF4444', ha='center', zorder=3)
    ax.text(r_rail_x + 0.6, bb_y + bb_h - 0.5, "- GND", fontsize=9, fontweight='bold', color='#3B82F6', ha='center', zorder=3)

    # Draw Breadboard Pin Hole Grid Matrix
    for x in np.linspace(bb_x + 2.0, bb_x + 6.3, 5):
        for y in np.linspace(bb_y + 1.2, bb_y + bb_h - 1.5, 30):
            ax.scatter(x, y, s=12, color='#64748B', zorder=2)
    for x in np.linspace(bb_x + 7.7, bb_x + 12.0, 5):
        for y in np.linspace(bb_y + 1.2, bb_y + bb_h - 1.5, 30):
            ax.scatter(x, y, s=12, color='#64748B', zorder=2)

    # --- 2. ESP32 WROOM-32D PLACED ACROSS CENTER DIVIDER ---
    esp_x, esp_y, esp_w, esp_h = bb_x + 4.8, bb_y + 4.5, 4.4, 6.0
    esp_chip = patches.FancyBboxPatch((esp_x, esp_y), esp_w, esp_h, boxstyle="round,pad=0.1,rounding_size=0.2",
                                      facecolor='#0F172A', edgecolor='#38BDF8', linewidth=2.5, zorder=4)
    ax.add_patch(esp_chip)

    # ESP32 Antenna Shield
    shield = patches.Rectangle((esp_x + 0.6, esp_y + 3.6), 3.2, 2.0, facecolor='#475569', edgecolor='#94A3B8', zorder=5)
    ax.add_patch(shield)
    ax.text(esp_x + 2.2, esp_y + 4.6, "ESP32 WROOM-32D\n(Wi-Fi + BLE)", fontsize=9, fontweight='bold', color='#F8FAFC', ha='center', va='center', zorder=6)

    # Micro USB Port
    usb = patches.Rectangle((esp_x + 1.5, esp_y - 0.2), 1.4, 0.4, facecolor='#94A3B8', edgecolor='#CBD5E1', zorder=5)
    ax.add_patch(usb)
    ax.text(esp_x + 2.2, esp_y + 0.4, "ESP32 DEV MODULE", fontsize=8, fontweight='bold', color='#38BDF8', ha='center', zorder=6)

    # --- 3. SENSORS (Off-board with clear connection blocks) ---
    # SENSOR 1: BME280 (Top-Left)
    bme_x, bme_y = 0.5, 8.5
    bme_box = patches.FancyBboxPatch((bme_x, bme_y), 2.8, 3.5, boxstyle="round,pad=0.1", facecolor='#1E1B4B', edgecolor='#818CF8', linewidth=2, zorder=4)
    ax.add_patch(bme_box)
    ax.text(bme_x + 1.4, bme_y + 3.0, "Bosch BME280\n(Temp/Hum/Press)", fontsize=9, fontweight='bold', color='#A5B4FC', ha='center', zorder=5)
    pins_bme = ["1: VCC (3.3V)", "2: GND", "3: SCL", "4: SDA"]
    for i, p in enumerate(pins_bme):
        ax.text(bme_x + 0.3, bme_y + 2.2 - i*0.5, p, fontsize=8, color='#E0E7FF', zorder=5)

    # SENSOR 2: MicroSD Module (Bottom-Left)
    sd_x, sd_y = 0.5, 2.0
    sd_box = patches.FancyBboxPatch((sd_x, sd_y), 2.8, 4.5, boxstyle="round,pad=0.1", facecolor='#064E3B', edgecolor='#34D399', linewidth=2, zorder=4)
    ax.add_patch(sd_box)
    ax.text(sd_x + 1.4, sd_y + 4.0, "MicroSD SPI Module\n(Backup Logger)", fontsize=9, fontweight='bold', color='#6EE7B7', ha='center', zorder=5)
    pins_sd = ["1: CS (GPIO 5)", "2: SCK (GPIO 18)", "3: MOSI (GPIO 23)", "4: MISO (GPIO 19)", "5: VCC (3.3V)", "6: GND"]
    for i, p in enumerate(pins_sd):
        ax.text(sd_x + 0.3, sd_y + 3.2 - i*0.48, p, fontsize=7.5, color='#ECFDF5', zorder=5)

    # SENSOR 3: Rain Sensor Board (Top-Right)
    rain_x, rain_y = 18.5, 8.5
    rain_box = patches.FancyBboxPatch((rain_x, rain_y), 3.0, 3.5, boxstyle="round,pad=0.1", facecolor='#1E293B', edgecolor='#38BDF8', linewidth=2, zorder=4)
    ax.add_patch(rain_box)
    ax.text(rain_x + 1.5, rain_y + 3.0, "Raindrop Comparator\n(Analog Moisture)", fontsize=9, fontweight='bold', color='#7DD3FC', ha='center', zorder=5)
    pins_rain = ["1: VCC (3.3V)", "2: GND", "3: DO (N/C)", "4: AO (GPIO 34)"]
    for i, p in enumerate(pins_rain):
        ax.text(rain_x + 0.3, rain_y + 2.2 - i*0.5, p, fontsize=8, color='#F0F9FF', zorder=5)

    # SENSOR 4: Plantower PMS7003 (Bottom-Right)
    pms_x, pms_y = 18.5, 2.0
    pms_box = patches.FancyBboxPatch((pms_x, pms_y), 3.0, 4.5, boxstyle="round,pad=0.1", facecolor='#701A75', edgecolor='#F472B6', linewidth=2, zorder=4)
    ax.add_patch(pms_box)
    ax.text(pms_x + 1.5, pms_y + 4.0, "Plantower PMS7003\n(Laser Particle Sensor)", fontsize=9, fontweight='bold', color='#FBCFE8', ha='center', zorder=5)
    pins_pms = ["Pin 1: VCC (5.0V VIN)", "Pin 2: VCC (5.0V VIN)", "Pin 3: GND", "Pin 4: TXD (GPIO 16)", "Pin 5: RXD (GPIO 17)"]
    for i, p in enumerate(pins_pms):
        ax.text(pms_x + 0.3, pms_y + 3.2 - i*0.55, p, fontsize=7.5, color='#FDF2F8', zorder=5)

    # --- 4. BEZIER JUMPER WIRES ---
    def wire(x1, y1, x2, y2, color, lw=3, style='-'):
        dx, dy = x2 - x1, y2 - y1
        cx1, cy1 = x1 + dx * 0.3, y1 + dy * 0.1 + (0.5 if dx > 0 else -0.5)
        cx2, cy2 = x1 + dx * 0.7, y2 - dy * 0.1 - (0.5 if dx > 0 else -0.5)
        verts = [(x1, y1), (cx1, cy1), (cx2, cy2), (x2, y2)]
        codes = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4]
        patch = patches.PathPatch(Path(verts, codes), facecolor='none', edgecolor=color, lw=lw, linestyle=style, zorder=7, alpha=0.95)
        ax.add_patch(patch)
        ax.scatter([x1, x2], [y1, y2], color='#111827', s=45, zorder=8, edgecolors='white', linewidths=1.5)

    # 1. ESP32 to Power Rails
    wire(esp_x, esp_y + 5.2, l_rail_x, bb_y + 10.0, '#EF4444', 3.5) # ESP32 3V3 -> Left Red Rail
    wire(esp_x, esp_y + 4.7, l_rail_x + 0.6, bb_y + 9.5, '#3B82F6', 3.5) # ESP32 GND -> Left Blue Rail
    wire(esp_x + esp_w, esp_y + 5.2, r_rail_x, bb_y + 10.0, '#EF4444', 3.5) # ESP32 VIN -> Right Red Rail
    wire(esp_x + esp_w, esp_y + 4.7, r_rail_x + 0.6, bb_y + 9.5, '#3B82F6', 3.5) # ESP32 GND -> Right Blue Rail

    # Common Ground Bridge Wire (Left Blue Rail to Right Blue Rail)
    wire(l_rail_x + 0.6, bb_y + 1.5, r_rail_x + 0.6, bb_y + 1.5, '#1E293B', 4.0, style='--')
    ax.text(bb_x + 7.0, bb_y + 1.8, "=== COMMON GROUND BRIDGE WIRE ===", fontsize=8, fontweight='bold', color='#38BDF8', ha='center', zorder=9)

    # 2. BME280 Wires
    wire(bme_x + 2.8, bme_y + 2.2, l_rail_x, bb_y + 9.0, '#EF4444', 2.5) # VCC -> 3.3V
    wire(bme_x + 2.8, bme_y + 1.7, l_rail_x + 0.6, bb_y + 8.5, '#3B82F6', 2.5) # GND -> GND
    wire(bme_x + 2.8, bme_y + 1.2, esp_x, esp_y + 2.5, '#FBBF24', 2.5) # SCL -> GPIO 22
    wire(bme_x + 2.8, bme_y + 0.7, esp_x, esp_y + 2.0, '#60A5FA', 2.5) # SDA -> GPIO 21

    # 3. MicroSD Wires
    wire(sd_x + 2.8, sd_y + 1.28, l_rail_x, bb_y + 3.5, '#EF4444', 2.5) # VCC -> 3.3V
    wire(sd_x + 2.8, sd_y + 0.8, l_rail_x + 0.6, bb_y + 3.0, '#3B82F6', 2.5) # GND -> GND
    wire(sd_x + 2.8, sd_y + 3.2, esp_x, esp_y + 3.8, '#A855F7', 2.5) # CS -> GPIO 5
    wire(sd_x + 2.8, sd_y + 2.72, esp_x + esp_w, esp_y + 2.2, '#EC4899', 2.5) # SCK -> GPIO 18
    wire(sd_x + 2.8, sd_y + 2.24, esp_x + esp_w, esp_y + 3.2, '#14B8A6', 2.5) # MOSI -> GPIO 23
    wire(sd_x + 2.8, sd_y + 1.76, esp_x + esp_w, esp_y + 2.7, '#10B981', 2.5) # MISO -> GPIO 19

    # 4. Rain Sensor Wires
    wire(rain_x, rain_y + 2.2, l_rail_x, bb_y + 10.5, '#EF4444', 2.5) # VCC -> 3.3V
    wire(rain_x, rain_y + 1.7, l_rail_x + 0.6, bb_y + 10.2, '#3B82F6', 2.5) # GND -> GND
    wire(rain_x, rain_y + 0.7, esp_x + esp_w, esp_y + 4.2, '#F8FAFC', 2.5) # AO -> GPIO 34

    # 5. PMS7003 Wires
    wire(pms_x, pms_y + 3.2, r_rail_x, bb_y + 4.5, '#DC2626', 3.0) # VCC -> 5V VIN
    wire(pms_x, pms_y + 2.1, r_rail_x + 0.6, bb_y + 4.0, '#3B82F6', 2.5) # GND -> GND
    wire(pms_x, pms_y + 1.55, esp_x + esp_w, esp_y + 3.7, '#22C55E', 2.5) # TXD -> GPIO 16 (RX2)
    wire(pms_x, pms_y + 1.0, esp_x + esp_w, esp_y + 3.5, '#F97316', 2.5) # RXD -> GPIO 17 (TX2)

    # Save diagram
    out_path = 'docs/breadboard_complete_wiring_visual.png'
    plt.savefig(out_path, bbox_inches='tight', dpi=300)
    plt.close()
    print(f'Successfully generated {out_path}!')

if __name__ == '__main__':
    draw_breadboard_wiring()
