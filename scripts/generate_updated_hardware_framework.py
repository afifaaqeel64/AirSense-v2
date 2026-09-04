"""
AirSense Pakistan: Hardware Requirements & Technical Prediction Framework PDF Generator
Generates a comprehensive, publication-grade technical blueprint PDF and markdown artifact
for the dual-campus COIL AI deployment at Beaconhouse International College.

Strict Constraints:
- No em-dashes used anywhere.
- Strictly isolated to D: drive.
"""

import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

from pathlib import Path

AIRSENSE_ROOT = Path(__file__).resolve().parent.parent
BASE_DIR = str(AIRSENSE_ROOT / "Campus Deployment - LATEST")
DOCS_DIR = str(AIRSENSE_ROOT / "docs")
os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)

OUTPUT_PDF_PRIMARY = os.path.join(BASE_DIR, "AirSense_Hardware_Framework.pdf")
OUTPUT_PDF_NAMED = os.path.join(BASE_DIR, "AirSense_Hardware_and_Technical_Framework.pdf")
OUTPUT_PDF_DOCS = os.path.join(DOCS_DIR, "AirSense_Hardware_and_Technical_Framework.pdf")

# Sophisticated Color Palette
NAVY = colors.HexColor("#0F294A")
SLATE = colors.HexColor("#1E3A8A")
TEAL = colors.HexColor("#0D9488")
DARK_TEAL = colors.HexColor("#0F766E")
LIGHT_TEAL = colors.HexColor("#F0FDFA")
BORDER_TEAL = colors.HexColor("#CCFBF1")
LIGHT_BLUE = colors.HexColor("#EFF6FF")
BORDER_BLUE = colors.HexColor("#DBEAFE")
LIGHT_GRAY = colors.HexColor("#F8FAFC")
BORDER_GRAY = colors.HexColor("#E2E8F0")
DARK_TEXT = colors.HexColor("#1E293B")
MUTED_TEXT = colors.HexColor("#475569")
ACCENT_AMBER = colors.HexColor("#D97706")
LIGHT_AMBER = colors.HexColor("#FFFBEB")
BORDER_AMBER = colors.HexColor("#FEF3C7")
WHITE = colors.HexColor("#FFFFFF")

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and draw total page count.
    Strictly avoids em-dashes.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        # Top banner on first page
        if self._pageNumber == 1:
            self.setFillColor(NAVY)
            self.rect(0, 841.89 - 12, 595.27, 12, fill=1, stroke=0)
            self.setFillColor(TEAL)
            self.rect(0, 841.89 - 16, 595.27, 4, fill=1, stroke=0)
            return

        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(SLATE)

        # Header
        self.drawString(36, 810, "AirSense Pakistan | Hardware & Technical Prediction Framework")
        self.setFont("Helvetica", 8)
        self.setFillColor(MUTED_TEXT)
        self.drawRightString(595.27 - 36, 810, "COIL AI | Beaconhouse International College")
        self.setStrokeColor(BORDER_GRAY)
        self.setLineWidth(0.75)
        self.line(36, 802, 595.27 - 36, 802)

        # Footer
        self.line(36, 42, 595.27 - 36, 42)
        self.drawString(36, 28, "Confidential | Engineering Specification & Multi-Campus Deployment Blueprint")
        self.drawRightString(595.27 - 36, 28, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def create_styled_table(data, col_widths, is_header=True, custom_style=None):
    """Utility to build clean, professional tables with alternating rows."""
    base_style = [
        ('BACKGROUND', (0, 0), (-1, 0), NAVY if is_header else LIGHT_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE if is_header else DARK_TEXT),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
    ]
    if is_header and len(data) > 1:
        for i in range(1, len(data)):
            bg = LIGHT_GRAY if i % 2 == 1 else WHITE
            base_style.append(('BACKGROUND', (0, i), (-1, i), bg))
            base_style.append(('TEXTCOLOR', (0, i), (-1, i), DARK_TEXT))
            base_style.append(('FONTNAME', (0, i), (-1, i), 'Helvetica'))
            base_style.append(('FONTSIZE', (0, i), (-1, i), 8))
            
    if custom_style:
        base_style.extend(custom_style)
        
    return Table(data, colWidths=col_widths, style=TableStyle(base_style))


def generate_framework_pdf(output_path):
    print(f"Generating publication-grade Hardware & Technical Framework PDF at: {output_path}")
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=48,
        bottomMargin=48
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    cover_title = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=NAVY,
        alignment=0,
        spaceAfter=4
    )
    cover_subtitle = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=DARK_TEAL,
        alignment=0,
        spaceAfter=12
    )
    h1_style = ParagraphStyle(
        'Header1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=17,
        textColor=NAVY,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'Header2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=13.5,
        textColor=SLATE,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=DARK_TEXT,
        spaceAfter=5
    )
    body_bold = ParagraphStyle(
        'BodyBoldCustom',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    callout_text = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=DARK_TEXT
    )
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=DARK_TEXT
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=table_cell,
        fontName='Helvetica-Bold'
    )
    table_cell_right = ParagraphStyle(
        'TableCellRight',
        parent=table_cell,
        alignment=2
    )
    table_cell_right_bold = ParagraphStyle(
        'TableCellRightBold',
        parent=table_cell_bold,
        alignment=2
    )

    story = []

    # =========================================================================
    # COVER / HEADER SECTION
    # =========================================================================
    story.append(Paragraph("AirSense Pakistan", cover_title))
    story.append(Paragraph("Hardware Architecture and Technical Prediction Framework", cover_subtitle))
    
    meta_box = [
        [
            Paragraph("<b>Document Type:</b> Engineering Specification & Deployment Blueprint", callout_text),
            Paragraph("<b>Initiative:</b> COIL AI Collaborative Research", callout_text)
        ],
        [
            Paragraph("<b>Islamabad Campus Lead:</b> Munim Qureshi<br/><b>Supervisor:</b> Ms. Sahifa Alam (Head of CSSE/AI)", callout_text),
            Paragraph("<b>Karachi Campus Lead:</b> Areesha Aqeel<br/><b>Supervisor:</b> Mr. Sajid (Head of CSSE/AI)", callout_text)
        ],
        [
            Paragraph("<b>Institution:</b> Beaconhouse International College (BIC)", callout_text),
            Paragraph("<b>Release Version:</b> v3.0 Enterprise Operational Edition (August 2026)", callout_text)
        ]
    ]
    t_meta = Table(meta_box, colWidths=[260, 263], style=TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_TEAL),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_TEAL),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_TEAL),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # =========================================================================
    # SECTION 1: EXECUTIVE SUMMARY & MULTI-CAMPUS DEPLOYMENT SCOPE
    # =========================================================================
    story.append(Paragraph("1. Executive Overview and Multi-Campus Objectives", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DARK_TEAL, spaceAfter=8))
    
    story.append(Paragraph(
        "AirSense Pakistan is an enterprise-grade IoT sensing and predictive machine learning platform engineered during the <b>COIL AI</b> program. The framework establishes a unified environmental intelligence infrastructure spanning Beaconhouse International College (BIC) campuses in Islamabad and Karachi, with complete architectural readiness for nationwide scaling across Lahore, Rawalpindi, Faisalabad, and Peshawar.",
        body_style
    ))
    story.append(Paragraph(
        "This specification serves as the definitive reference for physical hardware assembly, local Pakistan vendor procurement, edge firmware telemetry, 10-year ground-truth data integration, 5-model machine learning forecasting, and the automated campus operational decision matrix.",
        body_style
    ))

    # Strategic Pillars Box
    pillars = [
        [
            Paragraph("<b>Pillar 1: 100% Domestic Sourcing</b><br/>Zero international import delays, custom tariffs, or currency risk. All 16 components sourced directly from Daraz.pk, Hallroad Lahore, and local hardware distributors.", callout_text),
            Paragraph("<b>Pillar 2: 10-Year Verified Training</b><br/>Trained across 578,592 continuous hours (2015 to 2025) integrating US Embassy BAM-1020 regulatory monitors, ECMWF ERA5 weather reanalysis, and CAMS atmospheric physics.", callout_text),
            Paragraph("<b>Pillar 3: Dual Edge & Cloud Resilience</b><br/>Microcontroller ring-buffering on 16GB SD storage protects against network drops, coupled with real-time Isolation Forest anomaly detection for sensor fault screening.", callout_text)
        ]
    ]
    t_pillars = Table(pillars, colWidths=[174, 174, 175], style=TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BLUE),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_BLUE),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_BLUE),
    ]))
    story.append(t_pillars)
    story.append(Spacer(1, 10))

    # =========================================================================
    # SECTION 2: HARDWARE ARCHITECTURE & EDGE SENSING TOPOLOGY
    # =========================================================================
    story.append(Paragraph("2. Edge Sensing Hardware Architecture", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    
    story.append(Paragraph(
        "The edge sensing station is engineered for continuous rooftop operation under rigorous Pakistani meteorological conditions, including intense solar radiation in Islamabad and corrosive high-humidity marine air in Karachi. The station comprises three dedicated functional subsystems:",
        body_style
    ))

    hw_arch_table = [
        [
            Paragraph("Subsystem", table_cell_bold),
            Paragraph("Component & Model", table_cell_bold),
            Paragraph("Interface / Protocol", table_cell_bold),
            Paragraph("Key Operational Role & Engineering Specification", table_cell_bold)
        ],
        [
            Paragraph("<b>Core Compute & Telemetry</b>", table_cell),
            Paragraph("Espressif ESP32 WROOM-32D", table_cell),
            Paragraph("Wi-Fi 802.11 b/g/n<br/>BLE 4.2 / Dual Core", table_cell),
            Paragraph("Dual-core 240 MHz Xtensa LX6 processor. Core 0 executes non-blocking HTTP/MQTT cloud telemetry and ring-buffer synchronization. Core 1 manages deterministic sensor polling and SD logging.", table_cell)
        ],
        [
            Paragraph("<b>Particulate Matter Sensing</b>", table_cell),
            Paragraph("Plantower PMS7003 Laser Counter", table_cell),
            Paragraph("UART Serial<br/>(9600 baud, 3.3V)", table_cell),
            Paragraph("Laser scattering chamber with integrated constant-flow fan. Simultaneously measures PM1.0, PM2.5, and PM10 mass concentrations (0.3 to 10 um range). Rated for 3-year continuous diode life.", table_cell)
        ],
        [
            Paragraph("<b>Meteorological Drivers</b>", table_cell),
            Paragraph("Bosch BME280 Environmental Sensor", table_cell),
            Paragraph("I2C Bus<br/>(Address 0x76, 3.3V)", table_cell),
            Paragraph("High-accuracy ambient temperature (+-0.5 C), relative humidity (+-3%), and barometric pressure (+-1 hPa). Essential for calculating atmospheric boundary layer stagnation and inversion indices.", table_cell)
        ],
        [
            Paragraph("<b>Local Offline Buffer</b>", table_cell),
            Paragraph("SPI MicroSD Module + 16GB EVO+", table_cell),
            Paragraph("SPI Bus<br/>(CS Pin GPIO5, 3.3V)", table_cell),
            Paragraph("Non-volatile circular logging buffer. Preserves raw 1-minute and canonical 1-hour readings locally for 180+ days, preventing data loss during campus Wi-Fi outages.", table_cell)
        ],
        [
            Paragraph("<b>Wet Deposition Flag</b>", table_cell),
            Paragraph("Resistive Raindrop Sensor Board", table_cell),
            Paragraph("Analog ADC / GPIO34<br/>(3.3V Logic)", table_cell),
            Paragraph("Detects surface wet deposition and active precipitation to trigger atmospheric particulate wash-out compensation algorithms.", table_cell)
        ],
        [
            Paragraph("<b>Field Validation Tool</b>", table_cell),
            Paragraph("Digital Handheld Anemometer", table_cell),
            Paragraph("Physical Field Gauge<br/>(0.1 m/s accuracy)", table_cell),
            Paragraph("Provides on-site wind vector cross-validation against ERA5 meteorological reanalysis during monthly operational maintenance visits.", table_cell)
        ]
    ]
    story.append(create_styled_table(hw_arch_table, [90, 115, 85, 233]))
    story.append(Spacer(1, 10))

    # =========================================================================
    # SECTION 3: PINOUT WIRING & ELECTRICAL SPECIFICATIONS
    # =========================================================================
    story.append(Paragraph("3. Electrical Interface and Pin Wiring Reference", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    
    pin_table = [
        [
            Paragraph("Sensor / Subsystem", table_cell_bold),
            Paragraph("Module Pin", table_cell_bold),
            Paragraph("ESP32 Pin", table_cell_bold),
            Paragraph("Voltage / Bus", table_cell_bold),
            Paragraph("Functional Description & Wiring Instructions", table_cell_bold)
        ],
        [
            Paragraph("Plantower PMS7003", table_cell),
            Paragraph("Pin 4 (TXD)<br/>Pin 5 (RXD)<br/>Pin 1,2 (VCC)<br/>Pin 3 (GND)", table_cell),
            Paragraph("GPIO16 (RX2)<br/>GPIO17 (TX2)<br/>VIN (5V Rail)<br/>GND Rail", table_cell),
            Paragraph("5.0V Power<br/>3.3V UART Logic", table_cell),
            Paragraph("Hardware Serial UART2 channel. Laser diode and fan draw from 5V rail; UART data lines operate natively at 3.3V logic without level shifting.", table_cell)
        ],
        [
            Paragraph("Bosch BME280", table_cell),
            Paragraph("SDA<br/>SCL<br/>VCC<br/>GND", table_cell),
            Paragraph("GPIO21 (SDA)<br/>GPIO22 (SCL)<br/>3V3 Rail<br/>GND Rail", table_cell),
            Paragraph("3.3V Power<br/>I2C Bus (0x76)", table_cell),
            Paragraph("Standard I2C communications. Requires external pull-up resistors (4.7k ohm) if not integrated on the breakout board.", table_cell)
        ],
        [
            Paragraph("MicroSD SPI Logger", table_cell),
            Paragraph("MOSI<br/>MISO<br/>SCK<br/>CS / VCC / GND", table_cell),
            Paragraph("GPIO23<br/>GPIO19<br/>GPIO18<br/>GPIO5 / 3V3 / GND", table_cell),
            Paragraph("3.3V Power<br/>SPI Bus", table_cell),
            Paragraph("Hardware SPI bus configuration. Dedicated Chip Select (CS) on GPIO5. Supports FAT32 file system for direct CSV parsing on PC.", table_cell)
        ],
        [
            Paragraph("Raindrop Board", table_cell),
            Paragraph("AO (Analog Out)<br/>VCC / GND", table_cell),
            Paragraph("GPIO34 (ADC1_CH6)<br/>3V3 Rail / GND", table_cell),
            Paragraph("3.3V Power<br/>ADC Input", table_cell),
            Paragraph("Analog precipitation reading. Uses ADC1 channel to avoid Wi-Fi radio conflicts associated with ADC2 channels.", table_cell)
        ]
    ]
    story.append(create_styled_table(pin_table, [90, 85, 95, 75, 178]))
    story.append(Spacer(1, 10))

    # =========================================================================
    # SECTION 4: LOCAL PAKISTAN VENDOR PRICING & PROCUREMENT BOM
    # =========================================================================
    story.append(Paragraph("4. Pakistan-Local Vendor Pricing & Bill of Materials", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    
    story.append(Paragraph(
        "All components are 100% sourced within Pakistan across Daraz.pk, Hallroad Electronics Wholesale Market (Lahore), and local hardware stores. Procurement lead time is 3 to 5 business days per campus.",
        body_style
    ))

    bom_table = [
        [
            Paragraph("#", table_cell_bold),
            Paragraph("Component / Specification", table_cell_bold),
            Paragraph("Vendor / Sourcing Channel", table_cell_bold),
            Paragraph("Qty", table_cell_right_bold),
            Paragraph("Unit (PKR)", table_cell_right_bold),
            Paragraph("Total (PKR)", table_cell_right_bold)
        ],
        # Core items
        [Paragraph("1", table_cell), Paragraph("PMS7003 Laser Dust Sensor", table_cell), Paragraph("Daraz.pk Verified Store", table_cell), Paragraph("1", table_cell_right), Paragraph("4,589", table_cell_right), Paragraph("4,589", table_cell_right)],
        [Paragraph("2", table_cell), Paragraph("ESP32 WROOM-32D Microcontroller", table_cell), Paragraph("Hallroad Lahore / Epro.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("1,150", table_cell_right), Paragraph("1,150", table_cell_right)],
        [Paragraph("3", table_cell), Paragraph("Bosch BME280 Temp/Humidity/Pressure", table_cell), Paragraph("Hallroad Lahore", table_cell), Paragraph("1", table_cell_right), Paragraph("650", table_cell_right), Paragraph("650", table_cell_right)],
        [Paragraph("4", table_cell), Paragraph("Arduino MicroSD SPI Logger Module", table_cell), Paragraph("Hallroad Lahore", table_cell), Paragraph("1", table_cell_right), Paragraph("147", table_cell_right), Paragraph("147", table_cell_right)],
        [Paragraph("5", table_cell), Paragraph("Samsung EVO Plus 16GB MicroSD Card", table_cell), Paragraph("Daraz.pk Official", table_cell), Paragraph("1", table_cell_right), Paragraph("989", table_cell_right), Paragraph("989", table_cell_right)],
        [Paragraph("6", table_cell), Paragraph("IP65 Weatherproof Junction Enclosure", table_cell), Paragraph("Hallroad Lahore", table_cell), Paragraph("1", table_cell_right), Paragraph("343", table_cell_right), Paragraph("343", table_cell_right)],
        [Paragraph("7", table_cell), Paragraph("Jumper Wires 20cm Kit (40 pcs)", table_cell), Paragraph("Daraz.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("199", table_cell_right), Paragraph("199", table_cell_right)],
        [Paragraph("8", table_cell), Paragraph("5V 2A Regulated DC Power Supply", table_cell), Paragraph("Hallroad Lahore", table_cell), Paragraph("1", table_cell_right), Paragraph("294", table_cell_right), Paragraph("294", table_cell_right)],
        [Paragraph("9", table_cell), Paragraph("UV-Resistant Cable Ties (100 pcs)", table_cell), Paragraph("Daraz.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("100", table_cell_right), Paragraph("100", table_cell_right)],
        [Paragraph("10", table_cell), Paragraph("Stainless Steel 2-inch Hose Clamps (2 pcs)", table_cell), Paragraph("Daraz.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("139", table_cell_right), Paragraph("139", table_cell_right)],
        [Paragraph("11", table_cell), Paragraph("Multi-Plate Solar Radiation Shield", table_cell), Paragraph("Daraz.pk 3D / Plastic", table_cell), Paragraph("1", table_cell_right), Paragraph("299", table_cell_right), Paragraph("299", table_cell_right)],
        [Paragraph("12", table_cell), Paragraph("Raindrop Detection Module Board", table_cell), Paragraph("Hallroad Lahore", table_cell), Paragraph("1", table_cell_right), Paragraph("147", table_cell_right), Paragraph("147", table_cell_right)],
        # Core Subtotal
        [Paragraph("", table_cell_bold), Paragraph("<b>CORE BUILD SUB-TOTAL (Items 1 to 12)</b>", table_cell_bold), Paragraph("", table_cell), Paragraph("12", table_cell_right_bold), Paragraph("", table_cell), Paragraph("<b>PKR 9,046</b>", table_cell_right_bold)],
        # Recommended additions
        [Paragraph("13", table_cell), Paragraph("Handheld Digital Field Anemometer", table_cell), Paragraph("Hallroad Lahore / Online", table_cell), Paragraph("1", table_cell_right), Paragraph("2,090", table_cell_right), Paragraph("2,090", table_cell_right)],
        [Paragraph("14", table_cell), Paragraph("Heavy-Duty 10m Outdoor Extension Cable", table_cell), Paragraph("Local Hardware Store", table_cell), Paragraph("1", table_cell_right), Paragraph("800", table_cell_right), Paragraph("800", table_cell_right)],
        [Paragraph("15", table_cell), Paragraph("Neutral-Cure Silicone Sealant (300ml)", table_cell), Paragraph("Local Hardware Store", table_cell), Paragraph("1", table_cell_right), Paragraph("350", table_cell_right), Paragraph("350", table_cell_right)],
        [Paragraph("16", table_cell), Paragraph("Stainless M4/M6 Mounting Fastener Kit", table_cell), Paragraph("Local Hardware Store", table_cell), Paragraph("1", table_cell_right), Paragraph("250", table_cell_right), Paragraph("250", table_cell_right)],
        # Additions Subtotal
        [Paragraph("", table_cell_bold), Paragraph("<b>RECOMMENDED ADDITIONS SUB-TOTAL (Items 13 to 16)</b>", table_cell_bold), Paragraph("", table_cell), Paragraph("4", table_cell_right_bold), Paragraph("", table_cell), Paragraph("<b>PKR 3,490</b>", table_cell_right_bold)],
        # Hardware Subtotal
        [Paragraph("", table_cell_bold), Paragraph("<b>TOTAL HARDWARE DIRECT COST (Items 1 to 16)</b>", table_cell_bold), Paragraph("", table_cell), Paragraph("16", table_cell_right_bold), Paragraph("", table_cell), Paragraph("<b>PKR 12,536</b>", table_cell_right_bold)],
        # Contingency
        [Paragraph("17", table_cell), Paragraph("Contingency Reserve (5% for consumables)", table_cell), Paragraph("Budget Reserve", table_cell), Paragraph("1", table_cell_right), Paragraph("627", table_cell_right), Paragraph("627", table_cell_right)],
        # Final Total
        [Paragraph("", table_cell_bold), Paragraph("<b>TOTAL PILOT BUDGET REQUEST PER CAMPUS</b>", table_cell_bold), Paragraph("<b>Islamabad / Karachi</b>", table_cell_bold), Paragraph("<b>17</b>", table_cell_right_bold), Paragraph("", table_cell), Paragraph("<b>PKR 13,163</b>", table_cell_right_bold)]
    ]
    
    custom_bom_style = [
        ('BACKGROUND', (0, 13), (-1, 13), LIGHT_TEAL),
        ('BACKGROUND', (0, 18), (-1, 18), LIGHT_TEAL),
        ('BACKGROUND', (0, 19), (-1, 19), LIGHT_BLUE),
        ('BACKGROUND', (0, 21), (-1, 21), NAVY),
        ('TEXTCOLOR', (0, 21), (-1, 21), WHITE),
    ]
    story.append(create_styled_table(bom_table, [22, 195, 120, 28, 65, 93], custom_style=custom_bom_style))
    story.append(Spacer(1, 10))

    # =========================================================================
    # SECTION 5: 10-YEAR GROUND TRUTH & MULTI-CITY TRAINING ARCHITECTURE
    # =========================================================================
    story.append(Paragraph("5. 10-Year Continuous Ground-Truth & Multi-City Training", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    
    story.append(Paragraph(
        "To establish regulatory-grade forecasting accuracy, AirSense models are trained on a unified <b>10-Year Continuous Hourly Dataset (2015 to 2025)</b> comprising <b>578,592 continuous hours</b> across Pakistan. The dataset synthesizes ECMWF ERA5 hourly meteorological reanalysis, official US Embassy Met One BAM-1020 regulatory stations (2019 to 2025), and Copernicus CAMS atmospheric modeling.",
        body_style
    ))

    city_data_table = [
        [
            Paragraph("City / Monitoring Node", table_cell_bold),
            Paragraph("Total Hours (2015-2025)", table_cell_bold),
            Paragraph("Mean PM2.5", table_cell_bold),
            Paragraph("Peak PM2.5", table_cell_bold),
            Paragraph("Primary Role in Machine Learning Pipeline", table_cell_bold)
        ],
        [
            Paragraph("<b>Islamabad Campus</b>", table_cell),
            Paragraph("96,432 continuous", table_cell),
            Paragraph("51.78 ug/m3", table_cell),
            Paragraph("508.0 ug/m3", table_cell),
            Paragraph("Primary deployment hub. Characterized by temperate foothill microclimates and diurnal valley stagnation.", table_cell)
        ],
        [
            Paragraph("<b>Karachi Campus</b>", table_cell),
            Paragraph("96,432 continuous", table_cell),
            Paragraph("46.83 ug/m3", table_cell),
            Paragraph("985.0 ug/m3", table_cell),
            Paragraph("Primary coastal deployment hub. High relative humidity and dynamic marine wind dispersion.", table_cell)
        ],
        [
            Paragraph("<b>Lahore Station</b>", table_cell),
            Paragraph("96,432 continuous", table_cell),
            Paragraph("126.67 ug/m3", table_cell),
            Paragraph("943.0 ug/m3", table_cell),
            Paragraph("Extreme winter smog training ground. Teaches non-linear models severe temperature inversion dynamics.", table_cell)
        ],
        [
            Paragraph("<b>Rawalpindi Station</b>", table_cell),
            Paragraph("96,432 continuous", table_cell),
            Paragraph("52.20 ug/m3", table_cell),
            Paragraph("175.3 ug/m3", table_cell),
            Paragraph("Urban traffic corridor reference node. Calibrates vehicle emission surge parameters.", table_cell)
        ],
        [
            Paragraph("<b>Faisalabad & Peshawar</b>", table_cell),
            Paragraph("192,864 continuous", table_cell),
            Paragraph("80.94 ug/m3", table_cell),
            Paragraph("461.9 ug/m3", table_cell),
            Paragraph("Industrial and basin topography nodes. Validates nationwide cross-regional model generalization.", table_cell)
        ],
        [
            Paragraph("<b>Combined Master Dataset</b>", table_cell_bold),
            Paragraph("<b>578,592 continuous</b>", table_cell_bold),
            Paragraph("<b>73.22 ug/m3</b>", table_cell_bold),
            Paragraph("<b>985.0 ug/m3</b>", table_cell_bold),
            Paragraph("<b>11 full calendar years of complete hourly atmospheric forcing.</b>", table_cell_bold)
        ]
    ]
    story.append(create_styled_table(city_data_table, [110, 85, 65, 65, 198]))
    story.append(Spacer(1, 10))

    # =========================================================================
    # SECTION 6: 5-MODEL MACHINE LEARNING ENGINE & BENCHMARK RESULTS
    # =========================================================================
    story.append(Paragraph("6. Machine Learning Pipeline & Out-of-Sample Benchmarks", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    
    story.append(Paragraph(
        "The predictive pipeline incorporates five distinct model families. Models were trained on historical records (2015 to early 2023, 72,323 continuous hours) and evaluated strictly on out-of-sample unseen data (2023 to 2025, 24,108 continuous hours).",
        body_style
    ))

    ml_table = [
        [
            Paragraph("City", table_cell_bold),
            Paragraph("Model Family", table_cell_bold),
            Paragraph("Test R2", table_cell_bold),
            Paragraph("Test RMSE", table_cell_bold),
            Paragraph("Test MAE", table_cell_bold),
            Paragraph("Test MAPE", table_cell_bold),
            Paragraph("Operational Status & Role", table_cell_bold)
        ],
        # Islamabad
        [Paragraph("<b>Islamabad</b>", table_cell), Paragraph("<b>Gradient Boosting</b>", table_cell_bold), Paragraph("<b>0.7973</b>", table_cell_bold), Paragraph("20.37 ug/m3", table_cell), Paragraph("12.48 ug/m3", table_cell), Paragraph("34.63%", table_cell), Paragraph("<b>Production Champion</b>", table_cell_bold)],
        [Paragraph("Islamabad", table_cell), Paragraph("XGBoost", table_cell), Paragraph("0.7964", table_cell), Paragraph("20.42 ug/m3", table_cell), Paragraph("12.49 ug/m3", table_cell), Paragraph("34.70%", table_cell), Paragraph("High-Speed Challenger", table_cell)],
        [Paragraph("Islamabad", table_cell), Paragraph("Random Forest", table_cell), Paragraph("0.7886", table_cell), Paragraph("20.80 ug/m3", table_cell), Paragraph("12.70 ug/m3", table_cell), Paragraph("34.47%", table_cell), Paragraph("Bagged Robust Ensemble", table_cell)],
        [Paragraph("Islamabad", table_cell), Paragraph("Regression", table_cell), Paragraph("0.7308", table_cell), Paragraph("23.47 ug/m3", table_cell), Paragraph("14.85 ug/m3", table_cell), Paragraph("42.09%", table_cell), Paragraph("Linear Baseline Anchor", table_cell)],
        [Paragraph("Islamabad", table_cell), Paragraph("Isolation Forest", table_cell), Paragraph("N/A", table_cell), Paragraph("1,834 Outliers", table_cell), Paragraph("Contam: 0.05", table_cell), Paragraph("7.6% Flags", table_cell), Paragraph("Hardware Screener", table_cell)],
        # Karachi
        [Paragraph("<b>Karachi</b>", table_cell), Paragraph("<b>XGBoost</b>", table_cell_bold), Paragraph("<b>0.7729</b>", table_cell_bold), Paragraph("14.89 ug/m3", table_cell), Paragraph("7.89 ug/m3", table_cell), Paragraph("<b>22.96%</b>", table_cell_bold), Paragraph("<b>Production Champion</b>", table_cell_bold)],
        [Paragraph("Karachi", table_cell), Paragraph("Gradient Boosting", table_cell), Paragraph("0.7667", table_cell), Paragraph("15.10 ug/m3", table_cell), Paragraph("8.04 ug/m3", table_cell), Paragraph("23.70%", table_cell), Paragraph("High-Precision Challenger", table_cell)],
        [Paragraph("Karachi", table_cell), Paragraph("Random Forest", table_cell), Paragraph("0.7566", table_cell), Paragraph("15.42 ug/m3", table_cell), Paragraph("8.02 ug/m3", table_cell), Paragraph("23.13%", table_cell), Paragraph("Bagged Robust Ensemble", table_cell)],
        [Paragraph("Karachi", table_cell), Paragraph("Regression", table_cell), Paragraph("0.7155", table_cell), Paragraph("16.67 ug/m3", table_cell), Paragraph("9.69 ug/m3", table_cell), Paragraph("30.87%", table_cell), Paragraph("Linear Baseline Anchor", table_cell)],
        [Paragraph("Karachi", table_cell), Paragraph("Isolation Forest", table_cell), Paragraph("N/A", table_cell), Paragraph("913 Outliers", table_cell), Paragraph("Contam: 0.05", table_cell), Paragraph("3.8% Flags", table_cell), Paragraph("Hardware Screener", table_cell)],
        # Lahore
        [Paragraph("<b>Lahore</b>", table_cell), Paragraph("<b>Gradient Boosting</b>", table_cell_bold), Paragraph("<b>0.8338</b>", table_cell_bold), Paragraph("42.40 ug/m3", table_cell), Paragraph("24.15 ug/m3", table_cell), Paragraph("41.85%", table_cell), Paragraph("<b>Extreme Inversion Model</b>", table_cell_bold)],
        [Paragraph("Lahore", table_cell), Paragraph("XGBoost", table_cell), Paragraph("0.8332", table_cell), Paragraph("42.48 ug/m3", table_cell), Paragraph("24.00 ug/m3", table_cell), Paragraph("41.23%", table_cell), Paragraph("High-Speed Challenger", table_cell)]
    ]
    
    custom_ml_style = [
        ('BACKGROUND', (0, 1), (-1, 1), LIGHT_TEAL),
        ('BACKGROUND', (0, 6), (-1, 6), LIGHT_TEAL),
        ('BACKGROUND', (0, 11), (-1, 11), LIGHT_TEAL),
    ]
    story.append(create_styled_table(ml_table, [65, 95, 50, 65, 65, 55, 128], custom_style=custom_ml_style))
    story.append(Spacer(1, 10))

    # =========================================================================
    # SECTION 7: OPERATIONAL DECISION LAYER & CAMPUS ACTION TIERS
    # =========================================================================
    story.append(Paragraph("7. Operational Decision Layer & Campus Action Tiers", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    
    action_table = [
        [
            Paragraph("PM2.5 Forecast Band", table_cell_bold),
            Paragraph("Air Quality Category", table_cell_bold),
            Paragraph("Automated Campus HVAC Action", table_cell_bold),
            Paragraph("Student & Athletic Advisory Protocol", table_cell_bold)
        ],
        [
            Paragraph("Below 35 ug/m3", table_cell),
            Paragraph("Good / Acceptable", table_cell),
            Paragraph("100% fresh air dampers open. Normal filtration.", table_cell),
            Paragraph("Unrestricted outdoor sports and campus activities.", table_cell)
        ],
        [
            Paragraph("35 to 75 ug/m3", table_cell),
            Paragraph("Moderate", table_cell),
            Paragraph("Modulate fresh air dampers to 70%. Activate secondary stage filters.", table_cell),
            Paragraph("Issue advisory for students with diagnosed respiratory conditions.", table_cell)
        ],
        [
            Paragraph("75 to 150 ug/m3", table_cell),
            Paragraph("Unhealthy for Sensitive Groups", table_cell),
            Paragraph("Recirculation mode enabled (80% recirc / 20% fresh). HEPA filtration active.", table_cell),
            Paragraph("Relocate strenuous outdoor sports indoors. Broadcast campus alert banner.", table_cell)
        ],
        [
            Paragraph("Above 150 ug/m3", table_cell),
            Paragraph("Hazardous / Severe Smog", table_cell),
            Paragraph("100% recirculation mode with positive pressure ionization active.", table_cell),
            Paragraph("Mandate indoor operations. Distribute N95 protective masks at entrances.", table_cell)
        ],
        [
            Paragraph("High PM + Stagnant Wind", table_cell),
            Paragraph("Atmospheric Inversion Surge", table_cell),
            Paragraph("Pre-cool building envelope 2 hours prior to forecast morning peak.", table_cell),
            Paragraph("Pre-emptive early advisory to campus administration.", table_cell)
        ]
    ]
    story.append(create_styled_table(action_table, [85, 95, 160, 183]))
    story.append(Spacer(1, 10))

    # =========================================================================
    # SECTION 8: STEP-BY-STEP DEPLOYMENT PROTOCOL & MAINTENANCE CHECKLIST
    # =========================================================================
    story.append(Paragraph("8. Deployment Checklist and Monthly Maintenance Protocol", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    
    deploy_table = [
        [
            Paragraph("Phase", table_cell_bold),
            Paragraph("Task & Operational Procedure", table_cell_bold),
            Paragraph("Success / Completion Criteria", table_cell_bold)
        ],
        [
            Paragraph("<b>Phase 1: Lab Bench Test</b>", table_cell),
            Paragraph("Assemble ESP32, PMS7003, BME280, and SD logger on test breadboard. Flash firmware and verify serial output.", table_cell),
            Paragraph("Continuous 24-hour error-free data stream verified on UART serial monitor.", table_cell)
        ],
        [
            Paragraph("<b>Phase 2: Enclosure Assembly</b>", table_cell),
            Paragraph("Mount components in IP65 enclosure. Fit solar radiation shield over BME280. Apply neutral-cure silicone sealant.", table_cell),
            Paragraph("Enclosure passed splash test; zero moisture ingress detected.", table_cell)
        ],
        [
            Paragraph("<b>Phase 3: Rooftop Installation</b>", table_cell),
            Paragraph("Secure unit to rooftop parapet rail using 2-inch stainless hose clamps. Connect 10m outdoor extension cable.", table_cell),
            Paragraph("Unit securely mounted vertically; live telemetry packets verified in database within 5 minutes.", table_cell)
        ],
        [
            Paragraph("<b>Monthly Maintenance</b>", table_cell),
            Paragraph("Clean PMS7003 optical inlet with dry compressed air. Perform 3 spot wind checks with handheld anemometer. Inspect silicone seals.", table_cell),
            Paragraph("Maintenance log signed off; data completeness verified >98.5% for preceding 30 days.", table_cell)
        ]
    ]
    story.append(create_styled_table(deploy_table, [95, 240, 188]))
    story.append(Spacer(1, 14))

    # Sign-off block
    sign_box = [
        [
            Paragraph("<b>Islamabad Campus Authorization:</b><br/><br/>___________________________<br/><b>Munim Qureshi</b><br/>Project Lead, AirSense ISB<br/>Beaconhouse International College", callout_text),
            Paragraph("<b>Faculty Supervision Authorization:</b><br/><br/>___________________________<br/><b>Ms. Sahifa Alam</b><br/>Head of CSSE & AI<br/>Beaconhouse International College", callout_text),
            Paragraph("<b>Karachi Campus Authorization:</b><br/><br/>___________________________<br/><b>Areesha Aqeel</b><br/>Project Lead, AirSense KHI<br/>Beaconhouse International College", callout_text)
        ]
    ]
    t_sign = Table(sign_box, colWidths=[174, 174, 175], style=TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_GRAY),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(KeepTogether(t_sign))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated PDF ({doc.page} pages): {output_path}")


def generate_framework_markdown():
    """Generates the companion comprehensive Markdown reference document."""
    md_content = """# AirSense Pakistan: Hardware Architecture & Technical Prediction Framework

**Document Type:** Engineering Specification & Multi-Campus Deployment Blueprint  
**Initiative:** COIL AI Collaborative Research Project  
**Institution:** Beaconhouse International College (BIC)  
**Leadership Team:**  
- **Islamabad Campus:** Munim Qureshi (Project Lead), Ms. Sahifa Alam (Head of CSSE/AI)  
- **Karachi Campus:** Areesha Aqeel (Project Lead), Mr. Sajid (Head of CSSE/AI)  
**Version:** v3.0 Enterprise Operational Edition (August 2026)  

---

## 1. Executive Summary & Multi-Campus Deployment Scope
AirSense Pakistan is an enterprise-grade IoT sensing and predictive machine learning platform developed during the **COIL AI** program. The system establishes an intelligent environmental monitoring infrastructure spanning Beaconhouse International College campuses in Islamabad and Karachi, with full architectural readiness for nationwide scaling across Lahore, Rawalpindi, Faisalabad, and Peshawar.

### Key Strategic Pillars
1. **100% Domestic Sourcing:** Zero international import delays, custom tariffs, or currency risk. All 16 components sourced directly from Daraz.pk, Hallroad Lahore, and local hardware distributors.
2. **10-Year Verified Training:** Trained across 578,592 continuous hours (2015 to 2025) integrating US Embassy BAM-1020 regulatory monitors, ECMWF ERA5 weather reanalysis, and CAMS atmospheric physics.
3. **Dual Edge & Cloud Resilience:** Microcontroller ring-buffering on 16GB SD storage protects against network drops, coupled with real-time Isolation Forest anomaly detection for sensor fault screening.

---

## 2. Hardware Architecture & Edge Sensing Topology

| Subsystem | Component & Model | Interface / Protocol | Key Operational Role & Engineering Specification |
| :--- | :--- | :--- | :--- |
| **Core Compute & Telemetry** | Espressif ESP32 WROOM-32D | Wi-Fi 802.11 b/g/n, Dual Core 240 MHz | Dual-core processor. Core 0 executes non-blocking HTTP/MQTT telemetry. Core 1 manages deterministic sensor polling and SD logging. |
| **Particulate Matter Sensing** | Plantower PMS7003 Laser Counter | UART Serial (9600 baud, 3.3V) | Laser scattering chamber with constant-flow fan. Simultaneously measures PM1.0, PM2.5, and PM10 mass concentrations. |
| **Meteorological Drivers** | Bosch BME280 Environmental Sensor | I2C Bus (Address 0x76, 3.3V) | High-accuracy ambient temperature, relative humidity, and barometric pressure for calculating atmospheric stagnation indices. |
| **Local Offline Buffer** | SPI MicroSD Module + 16GB EVO+ | SPI Bus (CS Pin GPIO5, 3.3V) | Circular logging buffer preserving raw 1-minute and canonical 1-hour readings locally for 180+ days during Wi-Fi outages. |
| **Wet Deposition Flag** | Resistive Raindrop Sensor Board | Analog ADC / GPIO34 (3.3V) | Detects active precipitation to trigger atmospheric particulate wash-out compensation algorithms. |
| **Field Validation Tool** | Digital Handheld Anemometer | Physical Field Gauge (0.1 m/s accuracy) | Provides on-site wind vector cross-validation against ERA5 meteorological reanalysis during monthly maintenance visits. |

---

## 3. Electrical Pinout & Wiring Reference

| Sensor / Module | Module Pin | ESP32 Pin | Voltage / Bus | Wiring Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Plantower PMS7003** | Pin 4 (TXD), Pin 5 (RXD), Pin 1,2 (VCC), Pin 3 (GND) | GPIO16 (RX2), GPIO17 (TX2), VIN (5V Rail), GND Rail | 5.0V Power, 3.3V UART | Laser diode and fan draw from 5V rail; UART data lines operate natively at 3.3V logic. |
| **Bosch BME280** | SDA, SCL, VCC, GND | GPIO21 (SDA), GPIO22 (SCL), 3V3 Rail, GND Rail | 3.3V Power, I2C (0x76) | Standard I2C communications with 4.7k ohm pull-up resistors. |
| **MicroSD SPI Logger** | MOSI, MISO, SCK, CS, VCC, GND | GPIO23, GPIO19, GPIO18, GPIO5, 3V3, GND | 3.3V Power, SPI Bus | Hardware SPI bus configuration with dedicated Chip Select on GPIO5. |
| **Raindrop Board** | AO (Analog Out), VCC, GND | GPIO34 (ADC1_CH6), 3V3 Rail, GND | 3.3V Power, ADC Input | Uses ADC1 channel to avoid Wi-Fi radio conflicts associated with ADC2. |

---

## 4. Local Pakistan Vendor Pricing & Bill of Materials

| # | Component / Item Description | Model / Specification | Sourcing Channel | Qty | Unit (PKR) | Total (PKR) |
| :-: | :--- | :--- | :--- | :-: | -: | -: |
| 1 | Laser Dust Sensor | Plantower PMS7003 | Daraz.pk Verified Store | 1 | 4,589 | 4,589 |
| 2 | Microcontroller Board | ESP32 WROOM-32D | Hallroad Lahore / Epro.pk | 1 | 1,150 | 1,150 |
| 3 | Environmental Sensor | Bosch BME280 | Hallroad Lahore | 1 | 650 | 650 |
| 4 | MicroSD Data Logger | Arduino SPI Reader Module | Hallroad Lahore | 1 | 147 | 147 |
| 5 | Storage Media | Samsung EVO Plus 16GB MicroSD | Daraz.pk Official | 1 | 989 | 989 |
| 6 | Weather Enclosure | IP65 Waterproof Junction Box | Hallroad Lahore | 1 | 343 | 343 |
| 7 | Jumper Wires | 20cm 40-piece Kit | Daraz.pk | 1 | 199 | 199 |
| 8 | Regulated Power Supply | 5V 2A with Micro-USB Cable | Hallroad Lahore | 1 | 294 | 294 |
| 9 | UV Cable Ties | 100-piece Assorted Pack | Daraz.pk | 1 | 100 | 100 |
| 10 | Stainless Hose Clamps | 2-inch Stainless (Pack of 2) | Daraz.pk | 1 | 139 | 139 |
| 11 | Solar Radiation Shield | Multi-Plate Louvered Shield | Daraz.pk Plastic | 1 | 299 | 299 |
| 12 | Rain Proxy Sensor | Raindrop Detection Board | Hallroad Lahore | 1 | 147 | 147 |
| **-** | **CORE BUILD SUB-TOTAL** | **Items 1 to 12** | **Core Hardware** | **12** | **-** | **PKR 9,046** |
| 13 | Validation Anemometer | Handheld Digital Field Unit | Hallroad Lahore / Online | 1 | 2,090 | 2,090 |
| 14 | Outdoor Extension Cable | Heavy-Duty 10m 3-Pin Cable | Local Hardware Store | 1 | 800 | 800 |
| 15 | Weatherproof Sealant | Neutral-Cure Silicone (300ml) | Local Hardware Store | 1 | 350 | 350 |
| 16 | Mounting Fasteners | Stainless M4/M6 Bolt Set | Local Hardware Store | 1 | 250 | 250 |
| **-** | **ADDITIONS SUB-TOTAL** | **Items 13 to 16** | **Rooftop Deployment** | **4** | **-** | **PKR 3,490** |
| **-** | **HARDWARE DIRECT COST** | **Items 1 to 16** | **Complete Build** | **16** | **-** | **PKR 12,536** |
| 17 | Contingency Reserve | 5% for spares & consumables | Budget Reserve | 1 | 627 | 627 |
| **-** | **TOTAL PILOT REQUEST** | **Per Campus Budget** | **Islamabad / Karachi** | **17** | **-** | **PKR 13,163** |

*Combined Dual-Campus Pilot Budget (Islamabad + Karachi): **PKR 26,326**.*

---

## 5. 10-Year Continuous Ground-Truth & Multi-City Training Architecture

| City / Monitoring Node | Coordinates | Continuous Hours (2015-2025) | Mean PM2.5 | Peak PM2.5 | Operational Role |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Islamabad Campus** | 33.68 N, 73.05 E | 96,432 | 51.78 ug/m3 | 508.0 ug/m3 | Primary deployment hub. Temperate foothill microclimates and diurnal valley stagnation. |
| **Karachi Campus** | 24.86 N, 67.00 E | 96,432 | 46.83 ug/m3 | 985.0 ug/m3 | Primary coastal deployment hub. Marine wind dispersion and high humidity dynamics. |
| **Lahore Station** | 31.52 N, 74.36 E | 96,432 | 126.67 ug/m3 | 943.0 ug/m3 | Extreme winter smog training ground. Teaches non-linear models severe temperature inversion physics. |
| **Rawalpindi Station** | 33.60 N, 73.04 E | 96,432 | 52.20 ug/m3 | 175.3 ug/m3 | Urban traffic corridor reference node calibrating vehicular surge parameters. |
| **Faisalabad & Peshawar** | Central & KPK | 192,864 | 80.94 ug/m3 | 461.9 ug/m3 | Industrial and basin topography nodes validating nationwide cross-regional generalization. |
| **Combined Master Dataset** | **Pakistan-Wide** | **578,592** | **73.22 ug/m3** | **985.0 ug/m3** | **11 full calendar years of complete hourly atmospheric forcing.** |

---

## 6. Machine Learning Pipeline & Benchmark Highlights

Models trained on **72,323 continuous hours (2015 to 2022)** and evaluated on out-of-sample **24,108 continuous hours (2023 to 2025)**:

### Islamabad Campus Node (24,108 Test Hours)
- **Gradient Boosting (Champion):** Test $R^2 = 0.7973$, Test RMSE $= 20.37\ \mu\text{g/m}^3$, Test MAE $= 12.48\ \mu\text{g/m}^3$, Test MAPE $= 34.63\%$
- **XGBoost (High-Speed):** Test $R^2 = 0.7964$, Test RMSE $= 20.42\ \mu\text{g/m}^3$, Test MAE $= 12.49\ \mu\text{g/m}^3$, Test MAPE $= 34.70\%$
- **Random Forest (Ensemble):** Test $R^2 = 0.7886$, Test RMSE $= 20.80\ \mu\text{g/m}^3$, Test MAE $= 12.70\ \mu\text{g/m}^3$, Test MAPE $= 34.47\%$
- **Regression (Baseline):** Test $R^2 = 0.7308$, Test RMSE $= 23.47\ \mu\text{g/m}^3$, Test MAE $= 14.85\ \mu\text{g/m}^3$, Test MAPE $= 42.09\%$
- **Isolation Forest (Hardware Screener):** 1,834 Anomalies flagged (7.6% contamination filter)

### Karachi Campus Node (24,108 Test Hours)
- **XGBoost (Champion):** Test $R^2 = 0.7729$, Test RMSE $= 14.89\ \mu\text{g/m}^3$, Test MAE $= 7.89\ \mu\text{g/m}^3$, Test MAPE $= 22.96\%$
- **Gradient Boosting (High-Precision):** Test $R^2 = 0.7667$, Test RMSE $= 15.10\ \mu\text{g/m}^3$, Test MAE $= 8.04\ \mu\text{g/m}^3$, Test MAPE $= 23.70\%$
- **Random Forest (Ensemble):** Test $R^2 = 0.7566$, Test RMSE $= 15.42\ \mu\text{g/m}^3$, Test MAE $= 8.02\ \mu\text{g/m}^3$, Test MAPE $= 23.13\%$
- **Regression (Baseline):** Test $R^2 = 0.7155$, Test RMSE $= 16.67\ \mu\text{g/m}^3$, Test MAE $= 9.69\ \mu\text{g/m}^3$, Test MAPE $= 30.87\%$
- **Isolation Forest (Hardware Screener):** 913 Anomalies flagged (3.8% contamination filter)

---

## 7. Operational Decision Layer & Campus Action Tiers

| PM2.5 Forecast Band | Air Quality Category | Automated Campus HVAC Action | Student & Athletic Advisory Protocol |
| :--- | :--- | :--- | :--- |
| **Below 35 ug/m3** | Good / Acceptable | 100% fresh air dampers open. Standard filtration. | Unrestricted outdoor athletic and academic activities. |
| **35 to 75 ug/m3** | Moderate | Modulate fresh air dampers to 70%. Activate stage 2 filters. | Issue advisory for students with diagnosed respiratory sensitivities. |
| **75 to 150 ug/m3** | Unhealthy for Sensitive | Recirculation mode enabled (80% recirc / 20% fresh). HEPA on. | Move strenuous outdoor sports indoors. Broadcast campus alert banner. |
| **Above 150 ug/m3** | Hazardous / Severe Smog | 100% recirculation mode with positive pressure ionization. | Mandate indoor operations. Distribute N95 protective masks at gates. |
| **High PM + Stagnant Wind** | Atmospheric Inversion | Pre-cool building envelope 2 hours prior to forecast morning peak. | Pre-emptive early advisory to campus administration. |

---

## 8. Deployment Protocol & Maintenance Protocol

1. **Phase 1 (Lab Bench Assembly):** Assemble circuit on breadboard, flash ESP32 firmware, and verify 24-hour continuous stream via UART serial monitor.
2. **Phase 2 (Enclosure Assembly):** Install in IP65 junction box, mount radiation shield over BME280, and seal entry glands with neutral-cure silicone.
3. **Phase 3 (Rooftop Installation):** Clamp enclosure to parapet railing, connect 10m outdoor power cable, and verify cloud telemetry packets within 5 minutes of boot.
4. **Monthly Maintenance Protocol:** Gently clear PMS7003 inlet with dry compressed air, take 3 handheld anemometer spot-readings, check silicone seals, and verify >98.5% data completeness.
"""
    md_path = os.path.join(DOCS_DIR, "AirSense_Hardware_and_Technical_Framework.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Saved Markdown Framework to: {md_path}")
    return md_content


def main():
    generate_framework_pdf(OUTPUT_PDF_PRIMARY)
    generate_framework_pdf(OUTPUT_PDF_NAMED)
    generate_framework_pdf(OUTPUT_PDF_DOCS)
    generate_framework_markdown()
    print("\n========================================================")
    print("ALL HARDWARE & TECHNICAL FRAMEWORK DOCUMENTS GENERATED SUCCESSFULLY!")
    print("========================================================")

if __name__ == "__main__":
    main()
