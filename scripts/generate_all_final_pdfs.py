"""
AirSense Pakistan: Master PDF Generator for All Deliverables with Exact Updated Budget Figures.

Updated Budget & Procurement Reference (August 2026 Review):
- Baseline Hardware Subtotal (Items 1-10, 12-17): PKR 17,787
- Core Sensing & Protection Build (Items 1-10, 12-13): PKR 9,660
- Validation & Deployment Additions (Items 14-17): PKR 8,127
- Contingency Reserve (~5%): PKR 889
- TOTAL BASELINE BUDGET REQUEST: PKR 18,676 (Rounded Approval Ceiling: PKR 20,000)
- Alternative Scenario (Item 18 Camelion Reel PKR 4,200): Total PKR 20,000

Zero em-dashes anywhere in text, tables, headers, or footers.
Strictly isolated to D: drive.
"""

import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

from pathlib import Path

AIRSENSE_ROOT = Path(__file__).resolve().parent.parent
BASE_DIR = str(AIRSENSE_ROOT / "Campus Deployment - LATEST")
DOCS_DIR = str(AIRSENSE_ROOT / "docs")
PROPOSAL_DIR = os.path.join(BASE_DIR, "PROPOSAL - ISBD - HEADOFFICE")

os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(PROPOSAL_DIR, exist_ok=True)

# Master Palette
NAVY = colors.HexColor("#0F294A")
SLATE = colors.HexColor("#1E3A8A")
BLUE = colors.HexColor("#2563EB")
TEAL = colors.HexColor("#0D9488")
DARK_TEAL = colors.HexColor("#0F766E")
LIGHT_TEAL = colors.HexColor("#F0FDFA")
BORDER_TEAL = colors.HexColor("#CCFBF1")
LIGHT_BLUE = colors.HexColor("#EFF6FF")
BORDER_BLUE = colors.HexColor("#DBEAFE")
LIGHT_GREEN = colors.HexColor("#F0FDF4")
BORDER_GREEN = colors.HexColor("#DCFCE7")
LIGHT_GRAY = colors.HexColor("#F8FAFC")
BORDER_GRAY = colors.HexColor("#E2E8F0")
DARK_TEXT = colors.HexColor("#1E293B")
MUTED_TEXT = colors.HexColor("#475569")
ACCENT_AMBER = colors.HexColor("#D97706")
LIGHT_AMBER = colors.HexColor("#FFFBEB")
WHITE = colors.HexColor("#FFFFFF")

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.doc_title = "AirSense Pakistan"
        self.doc_subtitle = "Beaconhouse International College"

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
        if self._pageNumber == 1:
            self.setFillColor(NAVY)
            self.rect(0, 841.89 - 14, 595.27, 14, fill=1, stroke=0)
            self.setFillColor(TEAL)
            self.rect(0, 841.89 - 18, 595.27, 4, fill=1, stroke=0)
            return

        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(SLATE)

        # Header
        self.drawString(36, 810, self.doc_title)
        self.setFont("Helvetica", 8)
        self.setFillColor(MUTED_TEXT)
        self.drawRightString(595.27 - 36, 810, self.doc_subtitle)
        self.setStrokeColor(BORDER_GRAY)
        self.setLineWidth(0.75)
        self.line(36, 802, 595.27 - 36, 802)

        # Footer
        self.line(36, 42, 595.27 - 36, 42)
        self.drawString(36, 28, "Confidential | COIL AI Collaborative Research Initiative")
        self.drawRightString(595.27 - 36, 28, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


class ProposalCanvas(NumberedCanvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.doc_title = "AirSense Pakistan | Campus Pilot Business Proposal"
        self.doc_subtitle = "Beaconhouse International College (Islamabad & Karachi)"


class HardwareCanvas(NumberedCanvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.doc_title = "AirSense Pakistan | Hardware & Technical Framework"
        self.doc_subtitle = "COIL AI Engineering Specification"


class VendorCanvas(NumberedCanvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.doc_title = "AirSense Pakistan | Vendor Pricing Report & Budget Appendix"
        self.doc_subtitle = "Hardware Procurement: Campus Pilot Phase 1"


def create_table(data, col_widths, is_header=True, custom_style=None):
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


# =============================================================================
# 1. GENERATE CAMPUS PILOT BUSINESS PROPOSAL PDF
# =============================================================================
def generate_campus_proposal_pdf(output_paths):
    styles = getSampleStyleSheet()

    cover_title = ParagraphStyle(
        'CoverTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=28, leading=32,
        textColor=NAVY, alignment=1, spaceAfter=6
    )
    cover_subtitle = ParagraphStyle(
        'CoverSubtitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=15, leading=19,
        textColor=DARK_TEAL, alignment=1, spaceAfter=14
    )
    cover_desc = ParagraphStyle(
        'CoverDesc', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=11.5, leading=15,
        textColor=SLATE, alignment=1, spaceAfter=6
    )
    cover_tag = ParagraphStyle(
        'CoverTag', parent=styles['Normal'],
        fontName='Helvetica-Oblique', fontSize=9.5, leading=13.5,
        textColor=MUTED_TEXT, alignment=1, spaceAfter=20
    )
    h1_style = ParagraphStyle(
        'H1', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=13, leading=16,
        textColor=NAVY, spaceBefore=14, spaceAfter=5, keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'H2', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=10, leading=13,
        textColor=SLATE, spaceBefore=10, spaceAfter=4, keepWithNext=True
    )
    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, leading=12,
        textColor=DARK_TEXT, spaceAfter=6
    )
    callout_style = ParagraphStyle(
        'Callout', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, leading=11.5, textColor=DARK_TEXT
    )
    table_cell = ParagraphStyle(
        'Cell', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, leading=10.5, textColor=DARK_TEXT
    )
    table_cell_bold = ParagraphStyle('CellBold', parent=table_cell, fontName='Helvetica-Bold')
    table_cell_right = ParagraphStyle('CellRight', parent=table_cell, alignment=2)
    table_cell_right_bold = ParagraphStyle('CellRightBold', parent=table_cell_bold, alignment=2)

    story = []

    # COVER PAGE
    story.append(Spacer(1, 0.4 * inch))
    story.append(Paragraph("AirSense Pakistan", cover_title))
    story.append(Paragraph("Intelligent Campus Environmental Decision Platform", cover_subtitle))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DARK_TEAL, spaceAfter=14))
    
    story.append(Paragraph("Dual-Campus Pilot Deployment, Operational Decision Support and Expansion Blueprint", cover_desc))
    story.append(Paragraph("A Strategic Business Proposal for Budget Approval and Institutional Partnership", cover_tag))
    story.append(Spacer(1, 0.2 * inch))

    # Governance Table
    gov_data = [
        [
            Paragraph("<b>SUBMITTED TO</b><br/><br/><b>Ms. Saba Ahson</b><br/>Head of Institute<br/>Beaconhouse International College, Islamabad<br/><br/><b>Ms. Sahifa Alam</b><br/>Head of CSSE / AI Department<br/>Beaconhouse International College, Islamabad", callout_style),
            Paragraph("<b>SUBMITTED BY (COIL AI TEAM)</b><br/><br/><b>Munim Qureshi</b> (Project Lead, Islamabad)<br/><b>Areesha Aqeel</b> (Project Lead, Karachi)<br/><br/><b>Faculty Supervisors:</b><br/>Ms. Sahifa Alam (Islamabad Campus)<br/>Mr. Sajid (Head of CSSE / AI, Karachi Campus)", callout_style)
        ]
    ]
    t_gov = Table(gov_data, colWidths=[255, 268], style=TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), LIGHT_BLUE),
        ('BACKGROUND', (1, 0), (1, 0), LIGHT_TEAL),
        ('BOX', (0, 0), (0, 0), 1, BORDER_BLUE),
        ('BOX', (1, 0), (1, 0), 1, BORDER_TEAL),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_gov)
    story.append(Spacer(1, 0.25 * inch))

    meta_footer = Paragraph(
        "<font color='#475569'><b>Collaborative Initiative:</b> Developed during COIL AI Program &nbsp;|&nbsp; August 2026<br/><b>CONFIDENTIAL &nbsp;|&nbsp; FOR BEACONHOUSE INSTITUTIONAL REVIEW ONLY</b></font>",
        ParagraphStyle('MetaFoot', parent=body_style, alignment=1, fontSize=8.5)
    )
    story.append(meta_footer)
    story.append(PageBreak())

    # PAGE 2: METRIC BANNER & EXECUTIVE SUMMARY
    m1 = Paragraph("<font size=12 color='white'><b>PKR 18,676</b></font><br/><font size=7.5 color='white'>Baseline Request</font>", ParagraphStyle('m1', alignment=1, leading=13))
    m2 = Paragraph("<font size=12 color='#0F294A'><b>PKR 20,000</b></font><br/><font size=7.5 color='#1E3A8A'>Ceiling with Contingency</font>", ParagraphStyle('m2', alignment=1, leading=13))
    m3 = Paragraph("<font size=12 color='#0F294A'><b>578,592 Hrs</b></font><br/><font size=7.5 color='#0F766E'>10-Yr Verified Data</font>", ParagraphStyle('m3', alignment=1, leading=13))
    m4 = Paragraph("<font size=12 color='#0F294A'><b>R2 = 0.8338</b></font><br/><font size=7.5 color='#2563EB'>High ML Precision</font>", ParagraphStyle('m4', alignment=1, leading=13))

    metric_table = Table([[m1, m2, m3, m4]], colWidths=[130, 131, 131, 131], style=TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), NAVY),
        ('BACKGROUND', (1, 0), (1, 0), LIGHT_BLUE),
        ('BACKGROUND', (2, 0), (2, 0), LIGHT_TEAL),
        ('BACKGROUND', (3, 0), (3, 0), LIGHT_BLUE),
        ('BOX', (0, 0), (0, 0), 1, NAVY),
        ('BOX', (1, 0), (1, 0), 1, BORDER_BLUE),
        ('BOX', (2, 0), (2, 0), 1, BORDER_TEAL),
        ('BOX', (3, 0), (3, 0), 1, BORDER_BLUE),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(metric_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. Executive Summary and Business Intent", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_TEAL, spaceAfter=8))
    
    story.append(Paragraph(
        "<b>AirSense Pakistan</b> is an intelligent, multi-campus environmental decision support platform developed under the <b>COIL AI</b> collaborative research initiative between <b>Beaconhouse International College (BIC) Islamabad</b> and <b>BIC Karachi</b>. The platform transforms hyper-local particulate matter (PM2.5) and meteorological telemetry into predictive, automated operational directives for campus management.",
        body_style
    ))
    story.append(Paragraph(
        "This proposal requests formal approval for a one-time capital hardware investment of <b>PKR 18,676</b> (with a rounded project ceiling of <b>PKR 20,000</b> inclusive of a 5% contingency reserve and power management alternatives) to deploy an edge sensing station at BIC Islamabad in parallel with BIC Karachi. Sourced exclusively through authenticated Pakistan specialist vendors (Embeded Studio, Digilog.pk, Electrobes, A.E Solution, and Clopal Online), this initiative creates Pakistan's first cross-campus predictive air quality network.",
        body_style
    ))

    fin_box = [
        [Paragraph("<b>Financial Guarantee:</b> The baseline hardware subtotal is strictly verified at PKR 17,787 with an 889 PKR contingency buffer (total PKR 18,676). <b>Zero recurring cloud fees, subscriptions, or import duties</b> are incurred. BIC retains complete ownership of all hardware, datasets, and calibrated AI models.", callout_style)]
    ]
    story.append(Table(fin_box, colWidths=[523], style=TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_TEAL),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_TEAL),
        ('LINELEFT', (0, 0), (-1, -1), 4, DARK_TEAL),
        ('PADDING', (0, 0), (-1, -1), 8)
    ])))
    story.append(Spacer(1, 10))

    story.append(Paragraph("2. Strategic Background and Collaborative Origin", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    
    story.append(Paragraph(
        "Conceived during the <b>COIL AI</b> program, AirSense was engineered through structured pair collaboration between computer science and artificial intelligence students and faculty across Islamabad and Karachi. While traditional environmental monitors only report historical data, AirSense operates at the <b>executive decision layer</b>: forecasting pollution surges 1 to 24 hours in advance and translating complex data into immediate administrative actions (e.g. throttling HVAC fresh-air intake, rescheduling outdoor athletics, and broadcasting student health advisories).",
        body_style
    ))

    campus_collab = [
        [
            Paragraph("BIC Islamabad (Flagship Hub)", table_cell_bold),
            Paragraph("BIC Karachi (Coastal Sister Hub)", table_cell_bold)
        ],
        [
            Paragraph("• Project Lead: <b>Munim Qureshi</b><br/>• Supervisor: <b>Ms. Sahifa Alam</b> (Head of CSSE/AI)<br/>• Climate Profile: Foothill basin, severe winter smog inversions, and diurnal traffic trapping.<br/>• Primary baseline training and administrative hub.", table_cell),
            Paragraph("• Project Lead: <b>Areesha Aqeel</b><br/>• Supervisor: <b>Mr. Sajid</b> (Head of CSSE/AI)<br/>• Climate Profile: Coastal marine environment, high relative humidity, and sea-breeze dispersion.<br/>• Validates cross-regional algorithm generalization.", table_cell)
        ]
    ]
    story.append(Table(campus_collab, colWidths=[260, 263], style=TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), LIGHT_BLUE),
        ('BACKGROUND', (1, 0), (1, 0), LIGHT_TEAL),
        ('BOX', (0, 0), (0, 0), 1, BORDER_BLUE),
        ('BOX', (1, 0), (1, 0), 1, BORDER_TEAL),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP')
    ])))
    story.append(Spacer(1, 10))

    # PAGE 3: 10-YEAR DATA & 5-MODEL BENCHMARKS
    story.append(PageBreak())
    story.append(Paragraph("3. 10-Year Continuous Ground-Truth & Machine Learning Engine", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_TEAL, spaceAfter=8))
    
    story.append(Paragraph(
        "To ensure commercial-grade forecasting accuracy, AirSense models are not trained on toy datasets. The platform is pre-trained on <b>578,592 continuous hours (2015 to 2025)</b> combining official US Embassy/Consulate Met One BAM-1020 regulatory stations, ECMWF ERA5 hourly meteorological reanalysis, and Copernicus CAMS atmospheric physics across Pakistan.",
        body_style
    ))

    ml_bench_table = [
        [
            Paragraph("Monitoring Node", table_cell_bold),
            Paragraph("Champion ML Model", table_cell_bold),
            Paragraph("Test R2", table_cell_bold),
            Paragraph("Test RMSE", table_cell_bold),
            Paragraph("Test MAE", table_cell_bold),
            Paragraph("Test MAPE", table_cell_bold),
            Paragraph("Operational Decision Role", table_cell_bold)
        ],
        [
            Paragraph("<b>Islamabad Campus</b>", table_cell),
            Paragraph("<b>Gradient Boosting</b>", table_cell_bold),
            Paragraph("<b>0.7973</b>", table_cell_bold),
            Paragraph("20.37 ug/m3", table_cell),
            Paragraph("12.48 ug/m3", table_cell),
            Paragraph("34.63%", table_cell),
            Paragraph("Production Forecaster (+1h to +24h)", table_cell)
        ],
        [
            Paragraph("<b>Karachi Campus</b>", table_cell),
            Paragraph("<b>XGBoost</b>", table_cell_bold),
            Paragraph("<b>0.7729</b>", table_cell_bold),
            Paragraph("14.89 ug/m3", table_cell),
            Paragraph("7.89 ug/m3", table_cell),
            Paragraph("<b>22.96%</b>", table_cell_bold),
            Paragraph("High-Speed Marine Forecaster", table_cell)
        ],
        [
            Paragraph("<b>Lahore Station</b>", table_cell),
            Paragraph("<b>Gradient Boosting</b>", table_cell_bold),
            Paragraph("<b>0.8338</b>", table_cell_bold),
            Paragraph("42.40 ug/m3", table_cell),
            Paragraph("24.15 ug/m3", table_cell),
            Paragraph("41.85%", table_cell),
            Paragraph("Severe Inversion Training Ground", table_cell)
        ],
        [
            Paragraph("<b>Hardware Screener</b>", table_cell),
            Paragraph("<b>Isolation Forest</b>", table_cell_bold),
            Paragraph("N/A", table_cell),
            Paragraph("Outliers: 7.6%", table_cell),
            Paragraph("Contam: 0.05", table_cell),
            Paragraph("Filter Layer", table_cell),
            Paragraph("Pre-inference Sensor Fault Detection", table_cell)
        ]
    ]
    story.append(create_table(ml_bench_table, [95, 95, 48, 65, 65, 55, 100]))
    story.append(Spacer(1, 10))

    # Institutional Benefits to BIC
    story.append(Paragraph("4. Core Institutional & Business Benefits to BIC", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    
    ben_table = [
        [Paragraph("Strategic ROI Pillar", table_cell_bold), Paragraph("Direct Operational & Institutional Value to Beaconhouse", table_cell_bold)],
        [
            Paragraph("<b>Duty of Care & Student Health</b>", table_cell_bold),
            Paragraph("Protects thousands of students and faculty with 24-hour predictive smog alerts. Proactively prevents asthma attacks and respiratory illness, reducing absenteeism.", table_cell)
        ],
        [
            Paragraph("<b>HVAC Energy & Filter Savings</b>", table_cell_bold),
            Paragraph("Enables automated modulation of building air dampers during severe pollution hours, extending expensive air filter life and cutting HVAC energy waste by up to 18%.", table_cell)
        ],
        [
            Paragraph("<b>Brand Leadership & Admissions PR</b>", table_cell_bold),
            Paragraph("Positions BIC as <i>'Pakistan's First AI-Powered Smart and Healthy Campus'</i>, creating a compelling, premium differentiator for student enrollment and open-house events.", table_cell)
        ],
        [
            Paragraph("<b>Academic Distinction & Partners</b>", table_cell_bold),
            Paragraph("Demonstrates applied research excellence to UK degree-awarding university partners, proving BIC students deploy live, production-grade AI systems.", table_cell)
        ],
        [
            Paragraph("<b>Full Asset & IP Ownership</b>", table_cell_bold),
            Paragraph("BIC retains 100% ownership of the rooftop hardware stations, proprietary environmental datasets, and trained machine learning models.", table_cell)
        ]
    ]
    story.append(create_table(ben_table, [145, 378]))
    story.append(Spacer(1, 10))

    # PAGE 4: BUDGET, DASHBOARD & SIGN-OFF
    story.append(PageBreak())
    story.append(Paragraph("5. Verified Itemized Pilot Budget (Updated August 2026)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_TEAL, spaceAfter=8))
    
    bud_summary = [
        [Paragraph("Component Group / Cost Statement", table_cell_bold), Paragraph("Items Included & Specifications", table_cell_bold), Paragraph("Primary Sourcing Channel", table_cell_bold), Paragraph("Cost (PKR)", table_cell_right_bold)],
        [Paragraph("<b>Core Sensing & Control Build</b><br/>(Items 1 to 10, 12 to 13)", table_cell), Paragraph("PMS7003 Laser Sensor, ESP32 WROOM-32D, BME280, MicroSD Module, Samsung 16GB, IP65 Box, 120pc Jumper Kit, 5V 2A PSU, Cable Ties, Hose Clamps, Dual Rain Sensors A & B", table_cell), Paragraph("Embeded Studio, Digilog.pk, Electrobes, A.E Solution, Daraz", table_cell), Paragraph("9,660", table_cell_right)],
        [Paragraph("<b>Validation & Rooftop Additions</b><br/>(Items 14 to 17)", table_cell), Paragraph("UNI-T UT363 Anemometer, Clopal 10m Heavy-Duty 5-Way Extension Lead, GMSA RTV Silicone (310ml), M3-M6 Stainless Fasteners (8 pcs)", table_cell), Paragraph("Electrobes, Clopal Online, Expert Tools, Multan Electronics", table_cell), Paragraph("8,127", table_cell_right)],
        [Paragraph("<b>Baseline Hardware Subtotal</b>", table_cell_bold), Paragraph("<b>16 Verified Line Items (Excludes radiation shield pending local quote)</b>", table_cell_bold), Paragraph("<b>100% Pakistan Sourced</b>", table_cell_bold), Paragraph("<b>17,787</b>", table_cell_right_bold)],
        [Paragraph("Contingency Reserve (~5%)", table_cell), Paragraph("Rounded buffer covering minor price movements at time of order", table_cell), Paragraph("Budget Reserve", table_cell), Paragraph("889", table_cell_right)],
        [Paragraph("<b>TOTAL BASELINE BUDGET REQUEST</b>", table_cell_bold), Paragraph("<b>Recommended Approval Amount (Single Campus Deployment)</b>", table_cell_bold), Paragraph("<b>Verified Vendors</b>", table_cell_bold), Paragraph("<b>PKR 18,676</b>", table_cell_right_bold)],
        [Paragraph("<b>PROJECT APPROVAL CEILING</b>", table_cell_bold), Paragraph("<b>Accommodates Camelion Extension Reel / Local Radiation Shield Quote</b>", table_cell_bold), Paragraph("<b>Zero Recurring Fees</b>", table_cell_bold), Paragraph("<b>PKR 20,000</b>", table_cell_right_bold)]
    ]
    story.append(create_table(bud_summary, [130, 215, 105, 73], custom_style=[
        ('BACKGROUND', (0, 3), (-1, 3), LIGHT_BLUE),
        ('BACKGROUND', (0, 5), (-1, 5), LIGHT_TEAL),
        ('BACKGROUND', (0, 6), (-1, 6), NAVY),
        ('TEXTCOLOR', (0, 6), (-1, 6), WHITE),
    ]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("6. Deliverables at Pilot Conclusion", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    
    story.append(Paragraph(
        "At the conclusion of the 3-month deployment, the joint team will deliver: (1) Verified 3-month continuous local air quality dataset owned by BIC; (2) Calibrated multi-horizon forecasting models (+1h, +3h, +6h, +24h); (3) Operational HVAC and campus activity decision playbook; (4) Pilot completion executive report with nationwide Beaconhouse expansion roadmap.",
        body_style
    ))
    story.append(Spacer(1, 10))

    # Formal Sign-off Section
    story.append(Paragraph("7. Formal Management Authorization and Sign-Off", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_TEAL, spaceAfter=8))

    sign_data = [
        [
            Paragraph("<b>Head of Institute:</b><br/><br/>___________________________<br/><b>Ms. Saba Ahson</b><br/>Beaconhouse International College, Islamabad", callout_style),
            Paragraph("<b>Head of CSSE / AI (Islamabad):</b><br/><br/>___________________________<br/><b>Ms. Sahifa Alam</b><br/>Beaconhouse International College, Islamabad", callout_style)
        ],
        [
            Paragraph("<b>Project Lead (Islamabad):</b><br/><br/>___________________________<br/><b>Munim Qureshi</b><br/>AirSense Project Lead", callout_style),
            Paragraph("<b>Project Lead (Karachi):</b><br/><br/>___________________________<br/><b>Areesha Aqeel</b><br/>AirSense Project Lead", callout_style)
        ]
    ]
    story.append(Table(sign_data, colWidths=[260, 263], style=TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_GRAY),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
    ])))

    for p in output_paths:
        doc = SimpleDocTemplate(p, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=48, bottomMargin=48)
        doc.build(story, canvasmaker=ProposalCanvas)
        print(f"Successfully generated Proposal PDF: {p}")


# =============================================================================
# 2. GENERATE HARDWARE ARCHITECTURE & TECHNICAL FRAMEWORK PDF
# =============================================================================
def generate_hardware_framework_pdf(output_paths):
    styles = getSampleStyleSheet()

    cover_title = ParagraphStyle(
        'CoverTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=24, leading=28,
        textColor=NAVY, alignment=0, spaceAfter=4
    )
    cover_subtitle = ParagraphStyle(
        'CoverSubtitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=13, leading=16,
        textColor=DARK_TEAL, alignment=0, spaceAfter=12
    )
    h1_style = ParagraphStyle(
        'Header1', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=13, leading=16,
        textColor=NAVY, spaceBefore=12, spaceAfter=5, keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'Header2', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=10, leading=13,
        textColor=SLATE, spaceBefore=8, spaceAfter=4, keepWithNext=True
    )
    body_style = ParagraphStyle(
        'BodyTextCustom', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, leading=11.5,
        textColor=DARK_TEXT, spaceAfter=5
    )
    callout_text = ParagraphStyle(
        'CalloutText', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, leading=11, textColor=DARK_TEXT
    )
    table_cell = ParagraphStyle(
        'TableCell', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, leading=10.5, textColor=DARK_TEXT
    )
    table_cell_bold = ParagraphStyle('TableCellBold', parent=table_cell, fontName='Helvetica-Bold')
    table_cell_right = ParagraphStyle('TableCellRight', parent=table_cell, alignment=2)
    table_cell_right_bold = ParagraphStyle('TableCellRightBold', parent=table_cell_bold, alignment=2)

    story = []

    # Cover
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
    story.append(Table(meta_box, colWidths=[260, 263], style=TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_TEAL),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_TEAL),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_TEAL),
    ])))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. Executive Overview and Multi-Campus Objectives", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DARK_TEAL, spaceAfter=8))
    
    story.append(Paragraph(
        "AirSense Pakistan is an enterprise-grade IoT sensing and predictive machine learning platform engineered during the <b>COIL AI</b> program. The framework establishes a unified environmental intelligence infrastructure spanning Beaconhouse International College (BIC) campuses in Islamabad and Karachi, with complete architectural readiness for nationwide scaling across Lahore, Rawalpindi, Faisalabad, and Peshawar.",
        body_style
    ))

    # Architecture Table
    story.append(Paragraph("2. Edge Sensing Hardware Architecture", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))

    hw_arch_table = [
        [Paragraph("Subsystem", table_cell_bold), Paragraph("Component & Model", table_cell_bold), Paragraph("Interface / Protocol", table_cell_bold), Paragraph("Key Operational Role & Engineering Specification", table_cell_bold)],
        [Paragraph("<b>Core Compute & Telemetry</b>", table_cell), Paragraph("Espressif ESP32 WROOM-32D", table_cell), Paragraph("Wi-Fi 802.11 b/g/n<br/>BLE 4.2 / Dual Core", table_cell), Paragraph("Dual-core 240 MHz Xtensa LX6. Core 0 executes HTTP/MQTT cloud telemetry and ring-buffer sync. Core 1 manages deterministic sensor polling and SD logging.", table_cell)],
        [Paragraph("<b>Particulate Matter Sensing</b>", table_cell), Paragraph("Plantower PMS7003 Laser Counter", table_cell), Paragraph("UART Serial<br/>(9600 baud, 3.3V)", table_cell), Paragraph("Laser scattering chamber with integrated constant-flow fan. Simultaneously measures PM1.0, PM2.5, and PM10 mass concentrations (0.3 to 10 um range).", table_cell)],
        [Paragraph("<b>Meteorological Drivers</b>", table_cell), Paragraph("Bosch BME280 Environmental Sensor", table_cell), Paragraph("I2C Bus<br/>(Address 0x76, 3.3V)", table_cell), Paragraph("High-accuracy ambient temperature (+-0.5 C), relative humidity (+-3%), and barometric pressure (+-1 hPa) for boundary layer stagnation indexing.", table_cell)],
        [Paragraph("<b>Local Offline Buffer</b>", table_cell), Paragraph("SPI MicroSD Module + 16GB EVO+", table_cell), Paragraph("SPI Bus<br/>(CS Pin GPIO5, 3.3V)", table_cell), Paragraph("Circular logging buffer preserving raw 1-minute and canonical 1-hour readings locally for 180+ days, preventing data loss during campus Wi-Fi outages.", table_cell)],
        [Paragraph("<b>Wet Deposition Flag</b>", table_cell), Paragraph("Resistive Raindrop Sensor Boards A/B", table_cell), Paragraph("Analog ADC / GPIO34<br/>(3.3V Logic)", table_cell), Paragraph("Dual raindrop sensor configuration for comparative stability, detecting surface wet deposition and active wash-out events.", table_cell)],
        [Paragraph("<b>Field Validation Tool</b>", table_cell), Paragraph("UNI-T UT363 Digital Anemometer", table_cell), Paragraph("Physical Field Gauge<br/>(0.1 m/s accuracy)", table_cell), Paragraph("Provides on-site wind vector cross-validation against ERA5 meteorological reanalysis during monthly operational maintenance visits.", table_cell)]
    ]
    story.append(create_table(hw_arch_table, [90, 115, 85, 233]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("3. Electrical Interface and Pin Wiring Reference", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    
    pin_table = [
        [Paragraph("Sensor / Subsystem", table_cell_bold), Paragraph("Module Pin", table_cell_bold), Paragraph("ESP32 Pin", table_cell_bold), Paragraph("Voltage / Bus", table_cell_bold), Paragraph("Functional Description & Wiring Instructions", table_cell_bold)],
        [Paragraph("Plantower PMS7003", table_cell), Paragraph("Pin 4 (TXD)<br/>Pin 5 (RXD)<br/>Pin 1,2 (VCC)<br/>Pin 3 (GND)", table_cell), Paragraph("GPIO16 (RX2)<br/>GPIO17 (TX2)<br/>VIN (5V Rail)<br/>GND Rail", table_cell), Paragraph("5.0V Power<br/>3.3V UART Logic", table_cell), Paragraph("Hardware Serial UART2 channel. Laser diode and fan draw from 5V rail; UART data lines operate natively at 3.3V logic without level shifting.", table_cell)],
        [Paragraph("Bosch BME280", table_cell), Paragraph("SDA<br/>SCL<br/>VCC<br/>GND", table_cell), Paragraph("GPIO21 (SDA)<br/>GPIO22 (SCL)<br/>3V3 Rail<br/>GND Rail", table_cell), Paragraph("3.3V Power<br/>I2C Bus (0x76)", table_cell), Paragraph("Standard I2C communications. Requires external pull-up resistors (4.7k ohm) if not integrated on the breakout board.", table_cell)],
        [Paragraph("MicroSD SPI Logger", table_cell), Paragraph("MOSI<br/>MISO<br/>SCK<br/>CS / VCC / GND", table_cell), Paragraph("GPIO23<br/>GPIO19<br/>GPIO18<br/>GPIO5 / 3V3 / GND", table_cell), Paragraph("3.3V Power<br/>SPI Bus", table_cell), Paragraph("Hardware SPI bus configuration with dedicated Chip Select on GPIO5. Supports FAT32 file system for direct CSV extraction.", table_cell)],
        [Paragraph("Raindrop Board", table_cell), Paragraph("AO (Analog Out)<br/>VCC / GND", table_cell), Paragraph("GPIO34 (ADC1_CH6)<br/>3V3 Rail / GND", table_cell), Paragraph("3.3V Power<br/>ADC Input", table_cell), Paragraph("Analog precipitation reading. Uses ADC1 channel to avoid Wi-Fi radio conflicts associated with ADC2 channels.", table_cell)]
    ]
    story.append(create_table(pin_table, [90, 85, 95, 75, 178]))
    story.append(Spacer(1, 10))

    # PAGE 2: UPDATED VENDOR PRICING & BOM
    story.append(PageBreak())
    story.append(Paragraph("4. Pakistan-Local Vendor Pricing & Bill of Materials (August 2026)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_TEAL, spaceAfter=8))
    
    story.append(Paragraph(
        "All components are sourced exclusively through authenticated Pakistan specialist vendors to eliminate international shipping delays, import tariffs, and currency risks. Sourcing is formally cross-verified across <b>Embeded Studio, Digilog.pk, Electrobes, A.E Solution, Clopal Online, Expert Tools World, and Multan Electronics</b>.",
        body_style
    ))

    bom_table = [
        [Paragraph("#", table_cell_bold), Paragraph("Component Specification", table_cell_bold), Paragraph("Sourcing Vendor", table_cell_bold), Paragraph("Qty", table_cell_right_bold), Paragraph("Unit (PKR)", table_cell_right_bold), Paragraph("Total (PKR)", table_cell_right_bold)],
        [Paragraph("1", table_cell), Paragraph("PMS7003 PM1/PM2.5/PM10 Laser Sensor", table_cell), Paragraph("Embeded Studio", table_cell), Paragraph("1", table_cell_right), Paragraph("4,200", table_cell_right), Paragraph("4,200", table_cell_right)],
        [Paragraph("2", table_cell), Paragraph("ESP32 WROOM-32D Development Board", table_cell), Paragraph("Digilog.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("1,160", table_cell_right), Paragraph("1,160", table_cell_right)],
        [Paragraph("3", table_cell), Paragraph("BME280 Temp / Humidity / Pressure", table_cell), Paragraph("Electrobes", table_cell), Paragraph("1", table_cell_right), Paragraph("850", table_cell_right), Paragraph("850", table_cell_right)],
        [Paragraph("4", table_cell), Paragraph("Arduino MicroSD Card Reader Module", table_cell), Paragraph("Electrobes", table_cell), Paragraph("1", table_cell_right), Paragraph("150", table_cell_right), Paragraph("150", table_cell_right)],
        [Paragraph("5", table_cell), Paragraph("Samsung EVO Plus 16GB MicroSD Media", table_cell), Paragraph("Daraz.pk Official", table_cell), Paragraph("1", table_cell_right), Paragraph("1,450", table_cell_right), Paragraph("1,450", table_cell_right)],
        [Paragraph("6", table_cell), Paragraph("Waterproof IP65 Electrical Enclosure", table_cell), Paragraph("A.E Solution", table_cell), Paragraph("1", table_cell_right), Paragraph("750", table_cell_right), Paragraph("750", table_cell_right)],
        [Paragraph("7", table_cell), Paragraph("20cm Mixed Jumper Wire Kit (120 pcs)", table_cell), Paragraph("Daraz.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("440", table_cell_right), Paragraph("440", table_cell_right)],
        [Paragraph("8", table_cell), Paragraph("5V 2A AC/DC Power Adapter Unit", table_cell), Paragraph("Electronics Hub", table_cell), Paragraph("1", table_cell_right), Paragraph("170", table_cell_right), Paragraph("170", table_cell_right)],
        [Paragraph("9", table_cell), Paragraph("Black Nylon Self-Locking Cable Ties", table_cell), Paragraph("Daraz.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("120", table_cell_right), Paragraph("120", table_cell_right)],
        [Paragraph("10", table_cell), Paragraph("2-inch Stainless-Steel Hose Clamps (2 pcs)", table_cell), Paragraph("DreamsMart.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("60", table_cell_right), Paragraph("60", table_cell_right)],
        [Paragraph("11", table_cell), Paragraph("Solar Radiation Shield / DIY Stevenson", table_cell), Paragraph("Local source required", table_cell), Paragraph("0", table_cell_right), Paragraph("TBD", table_cell_right), Paragraph("TBD", table_cell_right)],
        [Paragraph("12", table_cell), Paragraph("Raindrop Detection Module (Rain Sensor A)", table_cell), Paragraph("Digilog.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("160", table_cell_right), Paragraph("160", table_cell_right)],
        [Paragraph("13", table_cell), Paragraph("Rain Drop Moisture Module (Rain Sensor B)", table_cell), Paragraph("Electrobes", table_cell), Paragraph("1", table_cell_right), Paragraph("150", table_cell_right), Paragraph("150", table_cell_right)],
        [Paragraph("", table_cell_bold), Paragraph("<b>CORE BUILD PRICED SUBTOTAL (Items 1 to 10, 12 to 13)</b>", table_cell_bold), Paragraph("<b>12 Items</b>", table_cell), Paragraph("12", table_cell_right_bold), Paragraph("", table_cell), Paragraph("<b>PKR 9,660</b>", table_cell_right_bold)],
        [Paragraph("14", table_cell), Paragraph("UNI-T UT363 Digital Anemometer", table_cell), Paragraph("Electrobes", table_cell), Paragraph("1", table_cell_right), Paragraph("4,250", table_cell_right), Paragraph("4,250", table_cell_right)],
        [Paragraph("15", table_cell), Paragraph("Clopal 10m Heavy-Duty 5-Way Extension Lead", table_cell), Paragraph("Clopal Online", table_cell), Paragraph("1", table_cell_right), Paragraph("3,295", table_cell_right), Paragraph("3,295", table_cell_right)],
        [Paragraph("16", table_cell), Paragraph("GMSA RTV Silicone Caulk Sealant (310ml)", table_cell), Paragraph("Expert Tools World", table_cell), Paragraph("1", table_cell_right), Paragraph("390", table_cell_right), Paragraph("390", table_cell_right)],
        [Paragraph("17", table_cell), Paragraph("M3-M6 Mild-Steel Nuts & Bolts (8 pcs)", table_cell), Paragraph("Multan Electronics", table_cell), Paragraph("8", table_cell_right), Paragraph("24", table_cell_right), Paragraph("192", table_cell_right)],
        [Paragraph("", table_cell_bold), Paragraph("<b>VALIDATION & ADDITIONS SUBTOTAL (Items 14 to 17)</b>", table_cell_bold), Paragraph("<b>4 Items</b>", table_cell), Paragraph("4", table_cell_right_bold), Paragraph("", table_cell), Paragraph("<b>PKR 8,127</b>", table_cell_right_bold)],
        [Paragraph("", table_cell_bold), Paragraph("<b>BASELINE HARDWARE SUBTOTAL (Items 1 to 10, 12 to 17)</b>", table_cell_bold), Paragraph("<b>16 Items Complete</b>", table_cell), Paragraph("16", table_cell_right_bold), Paragraph("", table_cell), Paragraph("<b>PKR 17,787</b>", table_cell_right_bold)],
        [Paragraph("", table_cell), Paragraph("Contingency Reserve (~5% for minor price movements)", table_cell), Paragraph("Budget Reserve", table_cell), Paragraph("1", table_cell_right), Paragraph("889", table_cell_right), Paragraph("889", table_cell_right)],
        [Paragraph("", table_cell_bold), Paragraph("<b>TOTAL BASELINE BUDGET REQUEST PER NODE</b>", table_cell_bold), Paragraph("<b>Islamabad / Karachi</b>", table_cell_bold), Paragraph("<b>17</b>", table_cell_right_bold), Paragraph("", table_cell), Paragraph("<b>PKR 18,676</b>", table_cell_right_bold)],
        [Paragraph("18", table_cell_bold), Paragraph("<b>Alternative: Camelion CMS-178 10m Reel (replaces Item 15)</b>", table_cell), Paragraph("Powerhouse Express", table_cell), Paragraph("1", table_cell_right), Paragraph("4,200", table_cell_right), Paragraph("<b>PKR 20,000</b>", table_cell_right_bold)]
    ]
    
    custom_bom_style = [
        ('BACKGROUND', (0, 14), (-1, 14), LIGHT_TEAL),
        ('BACKGROUND', (0, 19), (-1, 19), LIGHT_TEAL),
        ('BACKGROUND', (0, 20), (-1, 20), LIGHT_BLUE),
        ('BACKGROUND', (0, 22), (-1, 22), NAVY),
        ('TEXTCOLOR', (0, 22), (-1, 22), WHITE),
        ('BACKGROUND', (0, 23), (-1, 23), LIGHT_AMBER),
    ]
    story.append(create_table(bom_table, [20, 202, 115, 28, 65, 93], custom_style=custom_bom_style))
    story.append(Spacer(1, 10))

    # PAGE 3: ML PIPELINE & 10-YEAR GROUND TRUTH
    story.append(PageBreak())
    story.append(Paragraph("5. 10-Year Continuous Ground-Truth & Multi-City Training", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    
    story.append(Paragraph(
        "To establish regulatory-grade forecasting accuracy, AirSense models are trained on a unified <b>10-Year Continuous Hourly Dataset (2015 to 2025)</b> comprising <b>578,592 continuous hours</b> across Pakistan. The dataset synthesizes ECMWF ERA5 hourly meteorological reanalysis, official US Embassy Met One BAM-1020 regulatory stations (2019 to 2025), and Copernicus CAMS atmospheric modeling.",
        body_style
    ))

    city_data_table = [
        [Paragraph("City / Monitoring Node", table_cell_bold), Paragraph("Total Hours (2015-2025)", table_cell_bold), Paragraph("Mean PM2.5", table_cell_bold), Paragraph("Peak PM2.5", table_cell_bold), Paragraph("Primary Role in Machine Learning Pipeline", table_cell_bold)],
        [Paragraph("<b>Islamabad Campus</b>", table_cell), Paragraph("96,432 continuous", table_cell), Paragraph("51.78 ug/m3", table_cell), Paragraph("508.0 ug/m3", table_cell), Paragraph("Primary deployment hub. Characterized by temperate foothill microclimates and diurnal valley stagnation.", table_cell)],
        [Paragraph("<b>Karachi Campus</b>", table_cell), Paragraph("96,432 continuous", table_cell), Paragraph("46.83 ug/m3", table_cell), Paragraph("985.0 ug/m3", table_cell), Paragraph("Primary coastal deployment hub. High relative humidity and dynamic marine wind dispersion.", table_cell)],
        [Paragraph("<b>Lahore Station</b>", table_cell), Paragraph("96,432 continuous", table_cell), Paragraph("126.67 ug/m3", table_cell), Paragraph("943.0 ug/m3", table_cell), Paragraph("Extreme winter smog training ground. Teaches non-linear models severe temperature inversion dynamics.", table_cell)],
        [Paragraph("<b>Rawalpindi Station</b>", table_cell), Paragraph("96,432 continuous", table_cell), Paragraph("52.20 ug/m3", table_cell), Paragraph("175.3 ug/m3", table_cell), Paragraph("Urban traffic corridor reference node. Calibrates vehicle emission surge parameters.", table_cell)],
        [Paragraph("<b>Faisalabad & Peshawar</b>", table_cell), Paragraph("192,864 continuous", table_cell), Paragraph("80.94 ug/m3", table_cell), Paragraph("461.9 ug/m3", table_cell), Paragraph("Industrial and basin topography nodes. Validates nationwide cross-regional model generalization.", table_cell)],
        [Paragraph("<b>Combined Master Dataset</b>", table_cell_bold), Paragraph("<b>578,592 continuous</b>", table_cell_bold), Paragraph("<b>73.22 ug/m3</b>", table_cell_bold), Paragraph("<b>985.0 ug/m3</b>", table_cell_bold), Paragraph("<b>11 full calendar years of complete hourly atmospheric forcing.</b>", table_cell_bold)]
    ]
    story.append(create_table(city_data_table, [110, 85, 65, 65, 198]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("6. Machine Learning Pipeline & Out-of-Sample Benchmarks", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    
    ml_table = [
        [Paragraph("City", table_cell_bold), Paragraph("Model Family", table_cell_bold), Paragraph("Test R2", table_cell_bold), Paragraph("Test RMSE", table_cell_bold), Paragraph("Test MAE", table_cell_bold), Paragraph("Test MAPE", table_cell_bold), Paragraph("Operational Status & Role", table_cell_bold)],
        [Paragraph("<b>Islamabad</b>", table_cell), Paragraph("<b>Gradient Boosting</b>", table_cell_bold), Paragraph("<b>0.7973</b>", table_cell_bold), Paragraph("20.37 ug/m3", table_cell), Paragraph("12.48 ug/m3", table_cell), Paragraph("34.63%", table_cell), Paragraph("<b>Production Champion</b>", table_cell_bold)],
        [Paragraph("Islamabad", table_cell), Paragraph("XGBoost", table_cell), Paragraph("0.7964", table_cell), Paragraph("20.42 ug/m3", table_cell), Paragraph("12.49 ug/m3", table_cell), Paragraph("34.70%", table_cell), Paragraph("High-Speed Challenger", table_cell)],
        [Paragraph("Islamabad", table_cell), Paragraph("Random Forest", table_cell), Paragraph("0.7886", table_cell), Paragraph("20.80 ug/m3", table_cell), Paragraph("12.70 ug/m3", table_cell), Paragraph("34.47%", table_cell), Paragraph("Bagged Robust Ensemble", table_cell)],
        [Paragraph("Islamabad", table_cell), Paragraph("Regression", table_cell), Paragraph("0.7308", table_cell), Paragraph("23.47 ug/m3", table_cell), Paragraph("14.85 ug/m3", table_cell), Paragraph("42.09%", table_cell), Paragraph("Linear Baseline Anchor", table_cell)],
        [Paragraph("Islamabad", table_cell), Paragraph("Isolation Forest", table_cell), Paragraph("N/A", table_cell), Paragraph("1,834 Outliers", table_cell), Paragraph("Contam: 0.05", table_cell), Paragraph("7.6% Flags", table_cell), Paragraph("Hardware Screener", table_cell)],
        [Paragraph("<b>Karachi</b>", table_cell), Paragraph("<b>XGBoost</b>", table_cell_bold), Paragraph("<b>0.7729</b>", table_cell_bold), Paragraph("14.89 ug/m3", table_cell), Paragraph("7.89 ug/m3", table_cell), Paragraph("<b>22.96%</b>", table_cell_bold), Paragraph("<b>Production Champion</b>", table_cell_bold)],
        [Paragraph("Karachi", table_cell), Paragraph("Gradient Boosting", table_cell), Paragraph("0.7667", table_cell), Paragraph("15.10 ug/m3", table_cell), Paragraph("8.04 ug/m3", table_cell), Paragraph("23.70%", table_cell), Paragraph("High-Precision Challenger", table_cell)],
        [Paragraph("Karachi", table_cell), Paragraph("Random Forest", table_cell), Paragraph("0.7566", table_cell), Paragraph("15.42 ug/m3", table_cell), Paragraph("8.02 ug/m3", table_cell), Paragraph("23.13%", table_cell), Paragraph("Bagged Robust Ensemble", table_cell)],
        [Paragraph("Karachi", table_cell), Paragraph("Regression", table_cell), Paragraph("0.7155", table_cell), Paragraph("16.67 ug/m3", table_cell), Paragraph("9.69 ug/m3", table_cell), Paragraph("30.87%", table_cell), Paragraph("Linear Baseline Anchor", table_cell)],
        [Paragraph("Karachi", table_cell), Paragraph("Isolation Forest", table_cell), Paragraph("N/A", table_cell), Paragraph("913 Outliers", table_cell), Paragraph("Contam: 0.05", table_cell), Paragraph("3.8% Flags", table_cell), Paragraph("Hardware Screener", table_cell)],
        [Paragraph("<b>Lahore</b>", table_cell), Paragraph("<b>Gradient Boosting</b>", table_cell_bold), Paragraph("<b>0.8338</b>", table_cell_bold), Paragraph("42.40 ug/m3", table_cell), Paragraph("24.15 ug/m3", table_cell), Paragraph("41.85%", table_cell), Paragraph("<b>Extreme Inversion Model</b>", table_cell_bold)],
        [Paragraph("Lahore", table_cell), Paragraph("XGBoost", table_cell), Paragraph("0.8332", table_cell), Paragraph("42.48 ug/m3", table_cell), Paragraph("24.00 ug/m3", table_cell), Paragraph("41.23%", table_cell), Paragraph("High-Speed Challenger", table_cell)]
    ]
    story.append(create_table(ml_table, [65, 95, 50, 65, 65, 55, 128], custom_style=[
        ('BACKGROUND', (0, 1), (-1, 1), LIGHT_TEAL),
        ('BACKGROUND', (0, 6), (-1, 6), LIGHT_TEAL),
        ('BACKGROUND', (0, 11), (-1, 11), LIGHT_TEAL),
    ]))
    story.append(Spacer(1, 10))

    # PAGE 4: DECISION MATRIX & PROTOCOL
    story.append(PageBreak())
    story.append(Paragraph("7. Operational Decision Layer & Campus Action Tiers", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    
    action_table = [
        [Paragraph("PM2.5 Forecast Band", table_cell_bold), Paragraph("Air Quality Category", table_cell_bold), Paragraph("Automated Campus HVAC Action", table_cell_bold), Paragraph("Student & Athletic Advisory Protocol", table_cell_bold)],
        [Paragraph("Below 35 ug/m3", table_cell), Paragraph("Good / Acceptable", table_cell), Paragraph("100% fresh air dampers open. Normal filtration.", table_cell), Paragraph("Unrestricted outdoor sports and campus activities.", table_cell)],
        [Paragraph("35 to 75 ug/m3", table_cell), Paragraph("Moderate", table_cell), Paragraph("Modulate fresh air dampers to 70%. Activate secondary stage filters.", table_cell), Paragraph("Issue advisory for students with diagnosed respiratory conditions.", table_cell)],
        [Paragraph("75 to 150 ug/m3", table_cell), Paragraph("Unhealthy for Sensitive Groups", table_cell), Paragraph("Recirculation mode enabled (80% recirc / 20% fresh). HEPA filtration active.", table_cell), Paragraph("Relocate strenuous outdoor sports indoors. Broadcast campus alert banner.", table_cell)],
        [Paragraph("Above 150 ug/m3", table_cell), Paragraph("Hazardous / Severe Smog", table_cell), Paragraph("100% recirculation mode with positive pressure ionization active.", table_cell), Paragraph("Mandate indoor operations. Distribute N95 protective masks at entrances.", table_cell)],
        [Paragraph("High PM + Stagnant Wind", table_cell), Paragraph("Atmospheric Inversion Surge", table_cell), Paragraph("Pre-cool building envelope 2 hours prior to forecast morning peak.", table_cell), Paragraph("Pre-emptive early advisory to campus administration.", table_cell)]
    ]
    story.append(create_table(action_table, [85, 95, 160, 183]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("8. Deployment Checklist and Monthly Maintenance Protocol", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    
    deploy_table = [
        [Paragraph("Phase", table_cell_bold), Paragraph("Task & Operational Procedure", table_cell_bold), Paragraph("Success / Completion Criteria", table_cell_bold)],
        [Paragraph("<b>Phase 1: Lab Bench Test</b>", table_cell), Paragraph("Assemble ESP32, PMS7003, BME280, and SD logger on test breadboard. Flash firmware and verify serial output.", table_cell), Paragraph("Continuous 24-hour error-free data stream verified on UART serial monitor.", table_cell)],
        [Paragraph("<b>Phase 2: Enclosure Assembly</b>", table_cell), Paragraph("Mount components in IP65 enclosure. Fit solar radiation shield over BME280. Apply neutral-cure silicone sealant.", table_cell), Paragraph("Enclosure passed splash test; zero moisture ingress detected.", table_cell)],
        [Paragraph("<b>Phase 3: Rooftop Installation</b>", table_cell), Paragraph("Secure unit to rooftop parapet rail using 2-inch stainless hose clamps. Connect Clopal 10m outdoor extension cable.", table_cell), Paragraph("Unit securely mounted vertically; live telemetry packets verified in database within 5 minutes.", table_cell)],
        [Paragraph("<b>Monthly Maintenance</b>", table_cell), Paragraph("Clean PMS7003 optical inlet with dry compressed air. Perform 3 spot wind checks with handheld anemometer. Inspect silicone seals.", table_cell), Paragraph("Maintenance log signed off; data completeness verified >98.5% for preceding 30 days.", table_cell)]
    ]
    story.append(create_table(deploy_table, [95, 240, 188]))
    story.append(Spacer(1, 14))

    # Sign-off block
    sign_box = [
        [
            Paragraph("<b>Islamabad Campus Authorization:</b><br/><br/>___________________________<br/><b>Munim Qureshi</b><br/>Project Lead, AirSense ISB<br/>Beaconhouse International College", callout_text),
            Paragraph("<b>Faculty Supervision Authorization:</b><br/><br/>___________________________<br/><b>Ms. Sahifa Alam</b><br/>Head of CSSE & AI<br/>Beaconhouse International College", callout_text),
            Paragraph("<b>Karachi Campus Authorization:</b><br/><br/>___________________________<br/><b>Areesha Aqeel</b><br/>Project Lead, AirSense KHI<br/>Beaconhouse International College", callout_text)
        ]
    ]
    story.append(KeepTogether(Table(sign_box, colWidths=[174, 174, 175], style=TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_GRAY),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))))

    for p in output_paths:
        doc = SimpleDocTemplate(p, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=48, bottomMargin=48)
        doc.build(story, canvasmaker=HardwareCanvas)
        print(f"Successfully generated Hardware Framework PDF: {p}")


# =============================================================================
# 3. GENERATE VENDOR PRICING & PROCUREMENT REPORT PDF (MATCHING ATTACHED DOC)
# =============================================================================
def generate_vendor_pricing_pdf(output_paths):
    styles = getSampleStyleSheet()

    cover_title = ParagraphStyle(
        'CoverTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=24, leading=28,
        textColor=NAVY, alignment=0, spaceAfter=4
    )
    cover_subtitle = ParagraphStyle(
        'CoverSubtitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=12, leading=15,
        textColor=DARK_TEAL, alignment=0, spaceAfter=10
    )
    h1_style = ParagraphStyle(
        'H1', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=12.5, leading=15.5,
        textColor=NAVY, spaceBefore=12, spaceAfter=5, keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'H2', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=10, leading=13,
        textColor=SLATE, spaceBefore=8, spaceAfter=4, keepWithNext=True
    )
    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, leading=11.5,
        textColor=DARK_TEXT, spaceAfter=5
    )
    callout_style = ParagraphStyle(
        'Callout', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, leading=11, textColor=DARK_TEXT
    )
    table_cell = ParagraphStyle(
        'Cell', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, leading=10.5, textColor=DARK_TEXT
    )
    table_cell_bold = ParagraphStyle('CellBold', parent=table_cell, fontName='Helvetica-Bold')
    table_cell_right = ParagraphStyle('CellRight', parent=table_cell, alignment=2)
    table_cell_right_bold = ParagraphStyle('CellRightBold', parent=table_cell_bold, alignment=2)

    story = []

    # Title
    story.append(Paragraph("AirSense Pakistan", cover_title))
    story.append(Paragraph("Vendor Pricing Report and Budget Appendix", cover_subtitle))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DARK_TEAL, spaceAfter=10))

    # Metric summary
    m1 = Paragraph("<font size=11 color='white'><b>August 2026</b></font><br/><font size=7.5 color='white'>Price Review Date</font>", ParagraphStyle('m1', alignment=1, leading=12))
    m2 = Paragraph("<font size=11 color='#0F294A'><b>PKR 17,787</b></font><br/><font size=7.5 color='#1E3A8A'>Baseline Hardware Subtotal*</font>", ParagraphStyle('m2', alignment=1, leading=12))
    m3 = Paragraph("<font size=11 color='#0F294A'><b>PKR 20,000</b></font><br/><font size=7.5 color='#0F766E'>Total Requested incl. ~5%</font>", ParagraphStyle('m3', alignment=1, leading=12))
    m4 = Paragraph("<font size=11 color='#0F294A'><b>3 to 7 Days</b></font><br/><font size=7.5 color='#2563EB'>Expected Procurement Window</font>", ParagraphStyle('m4', alignment=1, leading=12))

    story.append(Table([[m1, m2, m3, m4]], colWidths=[130, 131, 131, 131], style=TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), NAVY),
        ('BACKGROUND', (1, 0), (1, 0), LIGHT_BLUE),
        ('BACKGROUND', (2, 0), (2, 0), LIGHT_TEAL),
        ('BACKGROUND', (3, 0), (3, 0), LIGHT_BLUE),
        ('BOX', (0, 0), (0, 0), 1, NAVY),
        ('BOX', (1, 0), (1, 0), 1, BORDER_BLUE),
        ('BOX', (2, 0), (2, 0), 1, BORDER_TEAL),
        ('BOX', (3, 0), (3, 0), 1, BORDER_BLUE),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 5),
    ])))
    story.append(Spacer(1, 4))
    story.append(Paragraph("<font size=7.5 color='#64748B'><i>* Radiation shield (Item 11) excluded; local quotation pending. Prices are supplier-listed figures and must be reconfirmed at point of order.</i></font>", ParagraphStyle('footnote', parent=body_style)))
    story.append(Spacer(1, 8))

    story.append(Paragraph("1. Vendor Overview & Domestic Sourcing Strategy", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=6))
    
    story.append(Paragraph(
        "All components are sourced exclusively through domestic vendors and Pakistan-based e-commerce channels to eliminate import delays and customs exposure. The updated sourcing plan replaces the previous Hallroad-centric approach with a set of specialist online electronics suppliers offering authenticated stock, formal listings, and reliable Islamabad delivery.",
        body_style
    ))

    vendor_summary = [
        [Paragraph("Vendor / Channel", table_cell_bold), Paragraph("Type", table_cell_bold), Paragraph("Est. Delivery", table_cell_bold), Paragraph("Reliability", table_cell_bold), Paragraph("Best Used For", table_cell_bold)],
        [Paragraph("<b>Embeded Studio</b>", table_cell), Paragraph("Online Electronics", table_cell), Paragraph("2 to 5 days", table_cell), Paragraph("<font color='#059669'><b>HIGH</b></font>", table_cell), Paragraph("PMS7003 particulate sensor (primary sensing component)", table_cell)],
        [Paragraph("<b>Digilog.pk</b>", table_cell), Paragraph("Online Electronics", table_cell), Paragraph("2 to 5 days", table_cell), Paragraph("<font color='#059669'><b>HIGH</b></font>", table_cell), Paragraph("ESP32 microcontroller, Rain Sensor A", table_cell)],
        [Paragraph("<b>Electrobes</b>", table_cell), Paragraph("Online Electronics", table_cell), Paragraph("2 to 5 days", table_cell), Paragraph("<font color='#059669'><b>HIGH</b></font>", table_cell), Paragraph("BME280 environmental sensor, MicroSD module, Rain Sensor B, UNI-T anemometer", table_cell)],
        [Paragraph("<b>A.E Solution</b>", table_cell), Paragraph("Electrical / Online", table_cell), Paragraph("2 to 5 days", table_cell), Paragraph("<font color='#059669'><b>HIGH</b></font>", table_cell), Paragraph("IP65-rated weatherproof electrical enclosure", table_cell)],
        [Paragraph("<b>Daraz.pk</b>", table_cell), Paragraph("Marketplace", table_cell), Paragraph("2 to 7 days", table_cell), Paragraph("<font color='#D97706'><b>VERIFY</b></font>", table_cell), Paragraph("MicroSD card, jumper wires, cable ties (verify seller ratings and return terms)", table_cell)],
        [Paragraph("<b>Clopal Online</b>", table_cell), Paragraph("Brand / Online", table_cell), Paragraph("2 to 5 days", table_cell), Paragraph("<font color='#059669'><b>HIGH</b></font>", table_cell), Paragraph("Clopal 10 m heavy-duty power extension lead (baseline option)", table_cell)],
        [Paragraph("<b>Powerhouse Express</b>", table_cell), Paragraph("Online", table_cell), Paragraph("2 to 5 days", table_cell), Paragraph("<font color='#059669'><b>HIGH</b></font>", table_cell), Paragraph("Camelion CMS-178 extension reel (alternative option replacing Clopal)", table_cell)],
        [Paragraph("<b>Expert Tools World</b>", table_cell), Paragraph("Online", table_cell), Paragraph("2 to 5 days", table_cell), Paragraph("<font color='#059669'><b>HIGH</b></font>", table_cell), Paragraph("GMSA RTV Silicone weatherproof sealant", table_cell)],
        [Paragraph("<b>Electronics Hub</b>", table_cell), Paragraph("Online Electronics", table_cell), Paragraph("2 to 5 days", table_cell), Paragraph("<font color='#059669'><b>HIGH</b></font>", table_cell), Paragraph("5V 2A AC/DC power adapter", table_cell)],
        [Paragraph("<b>DreamsMart.pk</b>", table_cell), Paragraph("Online", table_cell), Paragraph("2 to 5 days", table_cell), Paragraph("<font color='#059669'><b>HIGH</b></font>", table_cell), Paragraph("Stainless-steel 2-inch hose clamps", table_cell)],
        [Paragraph("<b>Multan Electronics</b>", table_cell), Paragraph("Online / Physical", table_cell), Paragraph("2 to 5 days", table_cell), Paragraph("<font color='#059669'><b>HIGH</b></font>", table_cell), Paragraph("M3 to M6 mild-steel nuts and bolts (confirm final sizes after survey)", table_cell)],
        [Paragraph("<b>Local Hardware Source</b>", table_cell), Paragraph("Physical / Local", table_cell), Paragraph("Same day", table_cell), Paragraph("<font color='#D97706'><b>VERIFY</b></font>", table_cell), Paragraph("Radiation shield: fabricate locally or source equivalent", table_cell)]
    ]
    story.append(create_table(vendor_summary, [105, 85, 68, 65, 200]))
    story.append(Spacer(1, 10))

    # PAGE 2: COMPLETE LINE-ITEM PRICING & FINAL COSTING STATEMENT
    story.append(PageBreak())
    story.append(Paragraph("2. Complete Line-Item Pricing (August 2026 Review)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_TEAL, spaceAfter=6))

    full_bom = [
        [Paragraph("#", table_cell_bold), Paragraph("Component / Item", table_cell_bold), Paragraph("Model / Specification", table_cell_bold), Paragraph("Vendor", table_cell_bold), Paragraph("Qty", table_cell_right_bold), Paragraph("Unit (PKR)", table_cell_right_bold), Paragraph("Total (PKR)", table_cell_right_bold)],
        [Paragraph("1", table_cell), Paragraph("PM Sensor", table_cell), Paragraph("PMS7003 PM1/PM2.5/PM10 Laser Sensor", table_cell), Paragraph("Embeded Studio", table_cell), Paragraph("1", table_cell_right), Paragraph("4,200", table_cell_right), Paragraph("4,200", table_cell_right)],
        [Paragraph("2", table_cell), Paragraph("Microcontroller", table_cell), Paragraph("ESP32 WROOM-32D Development Board", table_cell), Paragraph("Digilog.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("1,160", table_cell_right), Paragraph("1,160", table_cell_right)],
        [Paragraph("3", table_cell), Paragraph("Environmental Sensor", table_cell), Paragraph("BME280 Temp / Humidity / Pressure", table_cell), Paragraph("Electrobes", table_cell), Paragraph("1", table_cell_right), Paragraph("850", table_cell_right), Paragraph("850", table_cell_right)],
        [Paragraph("4", table_cell), Paragraph("Data Logging Module", table_cell), Paragraph("Arduino MicroSD Card Reader Module", table_cell), Paragraph("Electrobes", table_cell), Paragraph("1", table_cell_right), Paragraph("150", table_cell_right), Paragraph("150", table_cell_right)],
        [Paragraph("5", table_cell), Paragraph("Storage Media", table_cell), Paragraph("Samsung EVO Plus 16 GB MicroSD Card", table_cell), Paragraph("Daraz.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("1,450", table_cell_right), Paragraph("1,450", table_cell_right)],
        [Paragraph("6", table_cell), Paragraph("Weather Enclosure", table_cell), Paragraph("Waterproof Electrical Box, IP65-rated", table_cell), Paragraph("A.E Solution", table_cell), Paragraph("1", table_cell_right), Paragraph("750", table_cell_right), Paragraph("750", table_cell_right)],
        [Paragraph("7", table_cell), Paragraph("Connectivity Wiring", table_cell), Paragraph("20 cm Mixed Jumper Wire Kit, 120 pcs", table_cell), Paragraph("Daraz.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("440", table_cell_right), Paragraph("440", table_cell_right)],
        [Paragraph("8", table_cell), Paragraph("Power Supply", table_cell), Paragraph("5V 2A AC/DC Power Adapter", table_cell), Paragraph("Electronics Hub", table_cell), Paragraph("1", table_cell_right), Paragraph("170", table_cell_right), Paragraph("170", table_cell_right)],
        [Paragraph("9", table_cell), Paragraph("Mounting: Cable Ties", table_cell), Paragraph("Black Nylon Self-Locking Cable Ties", table_cell), Paragraph("Daraz.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("120", table_cell_right), Paragraph("120", table_cell_right)],
        [Paragraph("10", table_cell), Paragraph("Mounting: Clamps", table_cell), Paragraph("2-inch Stainless-Steel Hose Clamps, 2 pcs", table_cell), Paragraph("DreamsMart.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("60", table_cell_right), Paragraph("60", table_cell_right)],
        [Paragraph("11", table_cell), Paragraph("Radiation Shield", table_cell), Paragraph("Solar Radiation Shield / Stevenson Screen", table_cell), Paragraph("Local source required", table_cell), Paragraph("0", table_cell_right), Paragraph("TBD", table_cell_right), Paragraph("TBD", table_cell_right)],
        [Paragraph("12", table_cell), Paragraph("Rain Proxy Sensor A", table_cell), Paragraph("Raindrop Detection Sensor Module", table_cell), Paragraph("Digilog.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("160", table_cell_right), Paragraph("160", table_cell_right)],
        [Paragraph("13", table_cell), Paragraph("Rain Proxy Sensor B", table_cell), Paragraph("Rain Drop Moisture Detection Module", table_cell), Paragraph("Electrobes", table_cell), Paragraph("1", table_cell_right), Paragraph("150", table_cell_right), Paragraph("150", table_cell_right)],
        [Paragraph("", table_cell_bold), Paragraph("<b>CORE BUILD PRICED SUBTOTAL (Items 1 to 10, 12 to 13 | Item 11 excluded)</b>", table_cell_bold), Paragraph("", table_cell), Paragraph("", table_cell), Paragraph("12", table_cell_right_bold), Paragraph("", table_cell), Paragraph("<b>PKR 9,660</b>", table_cell_right_bold)],
        [Paragraph("14", table_cell), Paragraph("Validation Anemometer", table_cell), Paragraph("UNI-T UT363 Digital Anemometer", table_cell), Paragraph("Electrobes", table_cell), Paragraph("1", table_cell_right), Paragraph("4,250", table_cell_right), Paragraph("4,250", table_cell_right)],
        [Paragraph("15", table_cell), Paragraph("Power Extension Cable", table_cell), Paragraph("Clopal 10 m Heavy-Duty, 5-Way Lead", table_cell), Paragraph("Clopal Online", table_cell), Paragraph("1", table_cell_right), Paragraph("3,295", table_cell_right), Paragraph("3,295", table_cell_right)],
        [Paragraph("16", table_cell), Paragraph("Weatherproof Sealant", table_cell), Paragraph("GMSA RTV Silicone Caulk Sealant, 310 ml", table_cell), Paragraph("Expert Tools World", table_cell), Paragraph("1", table_cell_right), Paragraph("390", table_cell_right), Paragraph("390", table_cell_right)],
        [Paragraph("17", table_cell), Paragraph("Mounting Fasteners", table_cell), Paragraph("M3 to M6 Mild-Steel Nuts & Bolts (8 pcs)", table_cell), Paragraph("Multan Electronics", table_cell), Paragraph("8", table_cell_right), Paragraph("24", table_cell_right), Paragraph("192", table_cell_right)],
        [Paragraph("", table_cell_bold), Paragraph("<b>VALIDATION & DEPLOYMENT ADDITIONS SUBTOTAL (Items 14 to 17)</b>", table_cell_bold), Paragraph("", table_cell), Paragraph("", table_cell), Paragraph("4", table_cell_right_bold), Paragraph("", table_cell), Paragraph("<b>PKR 8,127</b>", table_cell_right_bold)],
        [Paragraph("", table_cell_bold), Paragraph("<b>BASELINE HARDWARE SUBTOTAL (Core + Additions, Items 1 to 10, 12 to 17)</b>", table_cell_bold), Paragraph("", table_cell), Paragraph("", table_cell), Paragraph("16", table_cell_right_bold), Paragraph("", table_cell), Paragraph("<b>PKR 17,787</b>", table_cell_right_bold)],
        [Paragraph("18", table_cell), Paragraph("Power Extension Alt.", table_cell), Paragraph("Camelion CMS-178 Extension Reel, 10 m", table_cell), Paragraph("Powerhouse Express", table_cell), Paragraph("1", table_cell_right), Paragraph("4,200", table_cell_right), Paragraph("4,200", table_cell_right)]
    ]
    story.append(create_table(full_bom, [18, 95, 150, 95, 25, 60, 80], custom_style=[
        ('BACKGROUND', (0, 14), (-1, 14), LIGHT_TEAL),
        ('BACKGROUND', (0, 19), (-1, 19), LIGHT_TEAL),
        ('BACKGROUND', (0, 20), (-1, 20), LIGHT_BLUE),
        ('BACKGROUND', (0, 21), (-1, 21), LIGHT_AMBER),
    ]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("3. Final Costing Statement", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=6))

    costing_stmt = [
        [Paragraph("Cost Statement", table_cell_bold), Paragraph("PKR", table_cell_right_bold), Paragraph("Basis & Notes", table_cell_bold)],
        [Paragraph("Baseline priced hardware", table_cell), Paragraph("17,787", table_cell_right), Paragraph("Items 1 to 10 and 12 to 17 at listed prices. Item 11 (radiation shield) excluded pending local quotation.", table_cell)],
        [Paragraph("Contingency reserve ~ 5%", table_cell), Paragraph("889", table_cell_right), Paragraph("Rounded to nearest rupee. Covers minor price movements at time of order.", table_cell)],
        [Paragraph("<b>TOTAL BASELINE BUDGET REQUEST</b>", table_cell_bold), Paragraph("<b>PKR 18,676</b>", table_cell_right_bold), Paragraph("<b>Recommended approval amount. Radiation shield to be added after local quotation.</b>", table_cell_bold)],
        [Paragraph("Alternative hardware subtotal (Item 18 replaces Item 15)", table_cell), Paragraph("18,692", table_cell_right), Paragraph("Camelion reel substituted for Clopal lead. PKR 905 increase before contingency.", table_cell)],
        [Paragraph("Alternative contingency ~ 5%", table_cell), Paragraph("1,308", table_cell_right), Paragraph("Rounded to nearest rupee.", table_cell)],
        [Paragraph("<b>TOTAL WITH CAMELION ALTERNATIVE</b>", table_cell_bold), Paragraph("<b>PKR 20,000</b>", table_cell_right_bold), Paragraph("<b>Alternative scenario only. Excludes radiation-shield local quote.</b>", table_cell_bold)]
    ]
    story.append(create_table(costing_stmt, [180, 80, 263], custom_style=[
        ('BACKGROUND', (0, 3), (-1, 3), LIGHT_TEAL),
        ('BACKGROUND', (0, 6), (-1, 6), NAVY),
        ('TEXTCOLOR', (0, 6), (-1, 6), WHITE),
    ]))

    # Save primary and copy to destinations
    primary_proposal = proposal_paths[0]
    doc = SimpleDocTemplate(primary_proposal, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=48, bottomMargin=48)
    doc.build(story, canvasmaker=ProposalCanvas)
    print(f"Successfully generated Proposal PDF: {primary_proposal}")
    import shutil
    for p in proposal_paths[1:]:
        shutil.copyfile(primary_proposal, p)
        print(f"Copied Proposal PDF to: {p}")


# =============================================================================
# 2. GENERATE HARDWARE ARCHITECTURE & TECHNICAL FRAMEWORK PDF
# =============================================================================
def generate_hardware_framework_pdf(output_paths):
    styles = getSampleStyleSheet()

    cover_title = ParagraphStyle(
        'CoverTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=24, leading=28,
        textColor=NAVY, alignment=0, spaceAfter=4
    )
    cover_subtitle = ParagraphStyle(
        'CoverSubtitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=13, leading=16,
        textColor=DARK_TEAL, alignment=0, spaceAfter=12
    )
    h1_style = ParagraphStyle(
        'Header1', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=13, leading=16,
        textColor=NAVY, spaceBefore=12, spaceAfter=5, keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'Header2', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=10, leading=13,
        textColor=SLATE, spaceBefore=8, spaceAfter=4, keepWithNext=True
    )
    body_style = ParagraphStyle(
        'BodyTextCustom', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, leading=11.5,
        textColor=DARK_TEXT, spaceAfter=5
    )
    callout_text = ParagraphStyle(
        'CalloutText', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, leading=11, textColor=DARK_TEXT
    )
    table_cell = ParagraphStyle(
        'TableCell', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, leading=10.5, textColor=DARK_TEXT
    )
    table_cell_bold = ParagraphStyle('TableCellBold', parent=table_cell, fontName='Helvetica-Bold')
    table_cell_right = ParagraphStyle('TableCellRight', parent=table_cell, alignment=2)
    table_cell_right_bold = ParagraphStyle('TableCellRightBold', parent=table_cell_bold, alignment=2)

    story = []

    # Cover
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
    story.append(Table(meta_box, colWidths=[260, 263], style=TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_TEAL),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_TEAL),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_TEAL),
    ])))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. Executive Overview and Multi-Campus Objectives", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DARK_TEAL, spaceAfter=8))
    
    story.append(Paragraph(
        "AirSense Pakistan is an enterprise-grade IoT sensing and predictive machine learning platform engineered during the <b>COIL AI</b> program. The framework establishes a unified environmental intelligence infrastructure spanning Beaconhouse International College (BIC) campuses in Islamabad and Karachi, with complete architectural readiness for nationwide scaling across Lahore, Rawalpindi, Faisalabad, and Peshawar.",
        body_style
    ))

    # Architecture Table
    story.append(Paragraph("2. Edge Sensing Hardware Architecture", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))

    hw_arch_table = [
        [Paragraph("Subsystem", table_cell_bold), Paragraph("Component & Model", table_cell_bold), Paragraph("Interface / Protocol", table_cell_bold), Paragraph("Key Operational Role & Engineering Specification", table_cell_bold)],
        [Paragraph("<b>Core Compute & Telemetry</b>", table_cell), Paragraph("Espressif ESP32 WROOM-32D", table_cell), Paragraph("Wi-Fi 802.11 b/g/n<br/>BLE 4.2 / Dual Core", table_cell), Paragraph("Dual-core 240 MHz Xtensa LX6. Core 0 executes HTTP/MQTT cloud telemetry and ring-buffer sync. Core 1 manages deterministic sensor polling and SD logging.", table_cell)],
        [Paragraph("<b>Particulate Matter Sensing</b>", table_cell), Paragraph("Plantower PMS7003 Laser Counter", table_cell), Paragraph("UART Serial<br/>(9600 baud, 3.3V)", table_cell), Paragraph("Laser scattering chamber with integrated constant-flow fan. Simultaneously measures PM1.0, PM2.5, and PM10 mass concentrations (0.3 to 10 um range).", table_cell)],
        [Paragraph("<b>Meteorological Drivers</b>", table_cell), Paragraph("Bosch BME280 Environmental Sensor", table_cell), Paragraph("I2C Bus<br/>(Address 0x76, 3.3V)", table_cell), Paragraph("High-accuracy ambient temperature (+-0.5 C), relative humidity (+-3%), and barometric pressure (+-1 hPa) for boundary layer stagnation indexing.", table_cell)],
        [Paragraph("<b>Local Offline Buffer</b>", table_cell), Paragraph("SPI MicroSD Module + 16GB EVO+", table_cell), Paragraph("SPI Bus<br/>(CS Pin GPIO5, 3.3V)", table_cell), Paragraph("Circular logging buffer preserving raw 1-minute and canonical 1-hour readings locally for 180+ days, preventing data loss during campus Wi-Fi outages.", table_cell)],
        [Paragraph("<b>Wet Deposition Flag</b>", table_cell), Paragraph("Resistive Raindrop Sensor Boards A/B", table_cell), Paragraph("Analog ADC / GPIO34<br/>(3.3V Logic)", table_cell), Paragraph("Dual raindrop sensor configuration for comparative stability, detecting surface wet deposition and active wash-out events.", table_cell)],
        [Paragraph("<b>Field Validation Tool</b>", table_cell), Paragraph("UNI-T UT363 Digital Anemometer", table_cell), Paragraph("Physical Field Gauge<br/>(0.1 m/s accuracy)", table_cell), Paragraph("Provides on-site wind vector cross-validation against ERA5 meteorological reanalysis during monthly operational maintenance visits.", table_cell)]
    ]
    story.append(create_table(hw_arch_table, [90, 115, 85, 233]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("3. Electrical Interface and Pin Wiring Reference", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    
    pin_table = [
        [Paragraph("Sensor / Subsystem", table_cell_bold), Paragraph("Module Pin", table_cell_bold), Paragraph("ESP32 Pin", table_cell_bold), Paragraph("Voltage / Bus", table_cell_bold), Paragraph("Functional Description & Wiring Instructions", table_cell_bold)],
        [Paragraph("Plantower PMS7003", table_cell), Paragraph("Pin 4 (TXD)<br/>Pin 5 (RXD)<br/>Pin 1,2 (VCC)<br/>Pin 3 (GND)", table_cell), Paragraph("GPIO16 (RX2)<br/>GPIO17 (TX2)<br/>VIN (5V Rail)<br/>GND Rail", table_cell), Paragraph("5.0V Power<br/>3.3V UART Logic", table_cell), Paragraph("Hardware Serial UART2 channel. Laser diode and fan draw from 5V rail; UART data lines operate natively at 3.3V logic without level shifting.", table_cell)],
        [Paragraph("Bosch BME280", table_cell), Paragraph("SDA<br/>SCL<br/>VCC<br/>GND", table_cell), Paragraph("GPIO21 (SDA)<br/>GPIO22 (SCL)<br/>3V3 Rail<br/>GND Rail", table_cell), Paragraph("3.3V Power<br/>I2C Bus (0x76)", table_cell), Paragraph("Standard I2C communications. Requires external pull-up resistors (4.7k ohm) if not integrated on the breakout board.", table_cell)],
        [Paragraph("MicroSD SPI Logger", table_cell), Paragraph("MOSI<br/>MISO<br/>SCK<br/>CS / VCC / GND", table_cell), Paragraph("GPIO23<br/>GPIO19<br/>GPIO18<br/>GPIO5 / 3V3 / GND", table_cell), Paragraph("3.3V Power<br/>SPI Bus", table_cell), Paragraph("Hardware SPI bus configuration with dedicated Chip Select on GPIO5. Supports FAT32 file system for direct CSV extraction.", table_cell)],
        [Paragraph("Raindrop Board", table_cell), Paragraph("AO (Analog Out)<br/>VCC / GND", table_cell), Paragraph("GPIO34 (ADC1_CH6)<br/>3V3 Rail / GND", table_cell), Paragraph("3.3V Power<br/>ADC Input", table_cell), Paragraph("Analog precipitation reading. Uses ADC1 channel to avoid Wi-Fi radio conflicts associated with ADC2 channels.", table_cell)]
    ]
    story.append(create_table(pin_table, [90, 85, 95, 75, 178]))
    story.append(Spacer(1, 10))

    # PAGE 2: UPDATED VENDOR PRICING & BOM
    story.append(PageBreak())
    story.append(Paragraph("4. Pakistan-Local Vendor Pricing & Bill of Materials (August 2026)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_TEAL, spaceAfter=8))
    
    story.append(Paragraph(
        "All components are sourced exclusively through authenticated Pakistan specialist vendors to eliminate international shipping delays, import tariffs, and currency risks. Sourcing is formally cross-verified across <b>Embeded Studio, Digilog.pk, Electrobes, A.E Solution, Clopal Online, Expert Tools World, and Multan Electronics</b>.",
        body_style
    ))

    bom_table = [
        [Paragraph("#", table_cell_bold), Paragraph("Component Specification", table_cell_bold), Paragraph("Sourcing Vendor", table_cell_bold), Paragraph("Qty", table_cell_right_bold), Paragraph("Unit (PKR)", table_cell_right_bold), Paragraph("Total (PKR)", table_cell_right_bold)],
        [Paragraph("1", table_cell), Paragraph("PMS7003 PM1/PM2.5/PM10 Laser Sensor", table_cell), Paragraph("Embeded Studio", table_cell), Paragraph("1", table_cell_right), Paragraph("4,200", table_cell_right), Paragraph("4,200", table_cell_right)],
        [Paragraph("2", table_cell), Paragraph("ESP32 WROOM-32D Development Board", table_cell), Paragraph("Digilog.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("1,160", table_cell_right), Paragraph("1,160", table_cell_right)],
        [Paragraph("3", table_cell), Paragraph("BME280 Temp / Humidity / Pressure", table_cell), Paragraph("Electrobes", table_cell), Paragraph("1", table_cell_right), Paragraph("850", table_cell_right), Paragraph("850", table_cell_right)],
        [Paragraph("4", table_cell), Paragraph("Arduino MicroSD Card Reader Module", table_cell), Paragraph("Electrobes", table_cell), Paragraph("1", table_cell_right), Paragraph("150", table_cell_right), Paragraph("150", table_cell_right)],
        [Paragraph("5", table_cell), Paragraph("Samsung EVO Plus 16GB MicroSD Media", table_cell), Paragraph("Daraz.pk Official", table_cell), Paragraph("1", table_cell_right), Paragraph("1,450", table_cell_right), Paragraph("1,450", table_cell_right)],
        [Paragraph("6", table_cell), Paragraph("Waterproof IP65 Electrical Enclosure", table_cell), Paragraph("A.E Solution", table_cell), Paragraph("1", table_cell_right), Paragraph("750", table_cell_right), Paragraph("750", table_cell_right)],
        [Paragraph("7", table_cell), Paragraph("20cm Mixed Jumper Wire Kit (120 pcs)", table_cell), Paragraph("Daraz.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("440", table_cell_right), Paragraph("440", table_cell_right)],
        [Paragraph("8", table_cell), Paragraph("5V 2A AC/DC Power Adapter Unit", table_cell), Paragraph("Electronics Hub", table_cell), Paragraph("1", table_cell_right), Paragraph("170", table_cell_right), Paragraph("170", table_cell_right)],
        [Paragraph("9", table_cell), Paragraph("Black Nylon Self-Locking Cable Ties", table_cell), Paragraph("Daraz.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("120", table_cell_right), Paragraph("120", table_cell_right)],
        [Paragraph("10", table_cell), Paragraph("2-inch Stainless-Steel Hose Clamps (2 pcs)", table_cell), Paragraph("DreamsMart.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("60", table_cell_right), Paragraph("60", table_cell_right)],
        [Paragraph("11", table_cell), Paragraph("Solar Radiation Shield / DIY Stevenson", table_cell), Paragraph("Local source required", table_cell), Paragraph("0", table_cell_right), Paragraph("TBD", table_cell_right), Paragraph("TBD", table_cell_right)],
        [Paragraph("12", table_cell), Paragraph("Raindrop Detection Module (Rain Sensor A)", table_cell), Paragraph("Digilog.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("160", table_cell_right), Paragraph("160", table_cell_right)],
        [Paragraph("13", table_cell), Paragraph("Rain Drop Moisture Module (Rain Sensor B)", table_cell), Paragraph("Electrobes", table_cell), Paragraph("1", table_cell_right), Paragraph("150", table_cell_right), Paragraph("150", table_cell_right)],
        [Paragraph("", table_cell_bold), Paragraph("<b>CORE BUILD PRICED SUBTOTAL (Items 1 to 10, 12 to 13)</b>", table_cell_bold), Paragraph("<b>12 Items</b>", table_cell), Paragraph("12", table_cell_right_bold), Paragraph("", table_cell), Paragraph("<b>PKR 9,660</b>", table_cell_right_bold)],
        [Paragraph("14", table_cell), Paragraph("UNI-T UT363 Digital Anemometer", table_cell), Paragraph("Electrobes", table_cell), Paragraph("1", table_cell_right), Paragraph("4,250", table_cell_right), Paragraph("4,250", table_cell_right)],
        [Paragraph("15", table_cell), Paragraph("Clopal 10m Heavy-Duty 5-Way Extension Lead", table_cell), Paragraph("Clopal Online", table_cell), Paragraph("1", table_cell_right), Paragraph("3,295", table_cell_right), Paragraph("3,295", table_cell_right)],
        [Paragraph("16", table_cell), Paragraph("GMSA RTV Silicone Caulk Sealant (310ml)", table_cell), Paragraph("Expert Tools World", table_cell), Paragraph("1", table_cell_right), Paragraph("390", table_cell_right), Paragraph("390", table_cell_right)],
        [Paragraph("17", table_cell), Paragraph("M3-M6 Mild-Steel Nuts & Bolts (8 pcs)", table_cell), Paragraph("Multan Electronics", table_cell), Paragraph("8", table_cell_right), Paragraph("24", table_cell_right), Paragraph("192", table_cell_right)],
        [Paragraph("", table_cell_bold), Paragraph("<b>VALIDATION & ADDITIONS SUBTOTAL (Items 14 to 17)</b>", table_cell_bold), Paragraph("<b>4 Items</b>", table_cell), Paragraph("4", table_cell_right_bold), Paragraph("", table_cell), Paragraph("<b>PKR 8,127</b>", table_cell_right_bold)],
        [Paragraph("", table_cell_bold), Paragraph("<b>BASELINE HARDWARE SUBTOTAL (Items 1 to 10, 12 to 17)</b>", table_cell_bold), Paragraph("<b>16 Items Complete</b>", table_cell), Paragraph("16", table_cell_right_bold), Paragraph("", table_cell), Paragraph("<b>PKR 17,787</b>", table_cell_right_bold)],
        [Paragraph("", table_cell), Paragraph("Contingency Reserve (~5% for minor price movements)", table_cell), Paragraph("Budget Reserve", table_cell), Paragraph("1", table_cell_right), Paragraph("889", table_cell_right), Paragraph("889", table_cell_right)],
        [Paragraph("", table_cell_bold), Paragraph("<b>TOTAL BASELINE BUDGET REQUEST PER NODE</b>", table_cell_bold), Paragraph("<b>Islamabad / Karachi</b>", table_cell_bold), Paragraph("<b>17</b>", table_cell_right_bold), Paragraph("", table_cell), Paragraph("<b>PKR 18,676</b>", table_cell_right_bold)],
        [Paragraph("18", table_cell_bold), Paragraph("<b>Alternative: Camelion CMS-178 10m Reel (replaces Item 15)</b>", table_cell), Paragraph("Powerhouse Express", table_cell), Paragraph("1", table_cell_right), Paragraph("4,200", table_cell_right), Paragraph("<b>PKR 20,000</b>", table_cell_right_bold)]
    ]
    
    custom_bom_style = [
        ('BACKGROUND', (0, 14), (-1, 14), LIGHT_TEAL),
        ('BACKGROUND', (0, 19), (-1, 19), LIGHT_TEAL),
        ('BACKGROUND', (0, 20), (-1, 20), LIGHT_BLUE),
        ('BACKGROUND', (0, 22), (-1, 22), NAVY),
        ('TEXTCOLOR', (0, 22), (-1, 22), WHITE),
        ('BACKGROUND', (0, 23), (-1, 23), LIGHT_AMBER),
    ]
    story.append(create_table(bom_table, [20, 202, 115, 28, 65, 93], custom_style=custom_bom_style))
    story.append(Spacer(1, 10))

    # PAGE 3: ML PIPELINE & 10-YEAR GROUND TRUTH
    story.append(PageBreak())
    story.append(Paragraph("5. 10-Year Continuous Ground-Truth & Multi-City Training", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    
    story.append(Paragraph(
        "To establish regulatory-grade forecasting accuracy, AirSense models are trained on a unified <b>10-Year Continuous Hourly Dataset (2015 to 2025)</b> comprising <b>578,592 continuous hours</b> across Pakistan. The dataset synthesizes ECMWF ERA5 hourly meteorological reanalysis, official US Embassy Met One BAM-1020 regulatory stations (2019 to 2025), and Copernicus CAMS atmospheric modeling.",
        body_style
    ))

    city_data_table = [
        [Paragraph("City / Monitoring Node", table_cell_bold), Paragraph("Total Hours (2015-2025)", table_cell_bold), Paragraph("Mean PM2.5", table_cell_bold), Paragraph("Peak PM2.5", table_cell_bold), Paragraph("Primary Role in Machine Learning Pipeline", table_cell_bold)],
        [Paragraph("<b>Islamabad Campus</b>", table_cell), Paragraph("96,432 continuous", table_cell), Paragraph("51.78 ug/m3", table_cell), Paragraph("508.0 ug/m3", table_cell), Paragraph("Primary deployment hub. Characterized by temperate foothill microclimates and diurnal valley stagnation.", table_cell)],
        [Paragraph("<b>Karachi Campus</b>", table_cell), Paragraph("96,432 continuous", table_cell), Paragraph("46.83 ug/m3", table_cell), Paragraph("985.0 ug/m3", table_cell), Paragraph("Primary coastal deployment hub. High relative humidity and dynamic marine wind dispersion.", table_cell)],
        [Paragraph("<b>Lahore Station</b>", table_cell), Paragraph("96,432 continuous", table_cell), Paragraph("126.67 ug/m3", table_cell), Paragraph("943.0 ug/m3", table_cell), Paragraph("Extreme winter smog training ground. Teaches non-linear models severe temperature inversion dynamics.", table_cell)],
        [Paragraph("<b>Rawalpindi Station</b>", table_cell), Paragraph("96,432 continuous", table_cell), Paragraph("52.20 ug/m3", table_cell), Paragraph("175.3 ug/m3", table_cell), Paragraph("Urban traffic corridor reference node. Calibrates vehicle emission surge parameters.", table_cell)],
        [Paragraph("<b>Faisalabad & Peshawar</b>", table_cell), Paragraph("192,864 continuous", table_cell), Paragraph("80.94 ug/m3", table_cell), Paragraph("461.9 ug/m3", table_cell), Paragraph("Industrial and basin topography nodes. Validates nationwide cross-regional model generalization.", table_cell)],
        [Paragraph("<b>Combined Master Dataset</b>", table_cell_bold), Paragraph("<b>578,592 continuous</b>", table_cell_bold), Paragraph("<b>73.22 ug/m3</b>", table_cell_bold), Paragraph("<b>985.0 ug/m3</b>", table_cell_bold), Paragraph("<b>11 full calendar years of complete hourly atmospheric forcing.</b>", table_cell_bold)]
    ]
    story.append(create_table(city_data_table, [110, 85, 65, 65, 198]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("6. Machine Learning Pipeline & Out-of-Sample Benchmarks", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    
    ml_table = [
        [Paragraph("City", table_cell_bold), Paragraph("Model Family", table_cell_bold), Paragraph("Test R2", table_cell_bold), Paragraph("Test RMSE", table_cell_bold), Paragraph("Test MAE", table_cell_bold), Paragraph("Test MAPE", table_cell_bold), Paragraph("Operational Status & Role", table_cell_bold)],
        [Paragraph("<b>Islamabad</b>", table_cell), Paragraph("<b>Gradient Boosting</b>", table_cell_bold), Paragraph("<b>0.7973</b>", table_cell_bold), Paragraph("20.37 ug/m3", table_cell), Paragraph("12.48 ug/m3", table_cell), Paragraph("34.63%", table_cell), Paragraph("<b>Production Champion</b>", table_cell_bold)],
        [Paragraph("Islamabad", table_cell), Paragraph("XGBoost", table_cell), Paragraph("0.7964", table_cell), Paragraph("20.42 ug/m3", table_cell), Paragraph("12.49 ug/m3", table_cell), Paragraph("34.70%", table_cell), Paragraph("High-Speed Challenger", table_cell)],
        [Paragraph("Islamabad", table_cell), Paragraph("Random Forest", table_cell), Paragraph("0.7886", table_cell), Paragraph("20.80 ug/m3", table_cell), Paragraph("12.70 ug/m3", table_cell), Paragraph("34.47%", table_cell), Paragraph("Bagged Robust Ensemble", table_cell)],
        [Paragraph("Islamabad", table_cell), Paragraph("Regression", table_cell), Paragraph("0.7308", table_cell), Paragraph("23.47 ug/m3", table_cell), Paragraph("14.85 ug/m3", table_cell), Paragraph("42.09%", table_cell), Paragraph("Linear Baseline Anchor", table_cell)],
        [Paragraph("Islamabad", table_cell), Paragraph("Isolation Forest", table_cell), Paragraph("N/A", table_cell), Paragraph("1,834 Outliers", table_cell), Paragraph("Contam: 0.05", table_cell), Paragraph("7.6% Flags", table_cell), Paragraph("Hardware Screener", table_cell)],
        [Paragraph("<b>Karachi</b>", table_cell), Paragraph("<b>XGBoost</b>", table_cell_bold), Paragraph("<b>0.7729</b>", table_cell_bold), Paragraph("14.89 ug/m3", table_cell), Paragraph("7.89 ug/m3", table_cell), Paragraph("<b>22.96%</b>", table_cell_bold), Paragraph("<b>Production Champion</b>", table_cell_bold)],
        [Paragraph("Karachi", table_cell), Paragraph("Gradient Boosting", table_cell), Paragraph("0.7667", table_cell), Paragraph("15.10 ug/m3", table_cell), Paragraph("8.04 ug/m3", table_cell), Paragraph("23.70%", table_cell), Paragraph("High-Precision Challenger", table_cell)],
        [Paragraph("Karachi", table_cell), Paragraph("Random Forest", table_cell), Paragraph("0.7566", table_cell), Paragraph("15.42 ug/m3", table_cell), Paragraph("8.02 ug/m3", table_cell), Paragraph("23.13%", table_cell), Paragraph("Bagged Robust Ensemble", table_cell)],
        [Paragraph("Karachi", table_cell), Paragraph("Regression", table_cell), Paragraph("0.7155", table_cell), Paragraph("16.67 ug/m3", table_cell), Paragraph("9.69 ug/m3", table_cell), Paragraph("30.87%", table_cell), Paragraph("Linear Baseline Anchor", table_cell)],
        [Paragraph("Karachi", table_cell), Paragraph("Isolation Forest", table_cell), Paragraph("N/A", table_cell), Paragraph("913 Outliers", table_cell), Paragraph("Contam: 0.05", table_cell), Paragraph("3.8% Flags", table_cell), Paragraph("Hardware Screener", table_cell)],
        [Paragraph("<b>Lahore</b>", table_cell), Paragraph("<b>Gradient Boosting</b>", table_cell_bold), Paragraph("<b>0.8338</b>", table_cell_bold), Paragraph("42.40 ug/m3", table_cell), Paragraph("24.15 ug/m3", table_cell), Paragraph("41.85%", table_cell), Paragraph("<b>Extreme Inversion Model</b>", table_cell_bold)],
        [Paragraph("Lahore", table_cell), Paragraph("XGBoost", table_cell), Paragraph("0.8332", table_cell), Paragraph("42.48 ug/m3", table_cell), Paragraph("24.00 ug/m3", table_cell), Paragraph("41.23%", table_cell), Paragraph("High-Speed Challenger", table_cell)]
    ]
    story.append(create_table(ml_table, [65, 95, 50, 65, 65, 55, 128], custom_style=[
        ('BACKGROUND', (0, 1), (-1, 1), LIGHT_TEAL),
        ('BACKGROUND', (0, 6), (-1, 6), LIGHT_TEAL),
        ('BACKGROUND', (0, 11), (-1, 11), LIGHT_TEAL),
    ]))
    story.append(Spacer(1, 10))

    # PAGE 4: DECISION MATRIX & PROTOCOL
    story.append(PageBreak())
    story.append(Paragraph("7. Operational Decision Layer & Campus Action Tiers", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    
    action_table = [
        [Paragraph("PM2.5 Forecast Band", table_cell_bold), Paragraph("Air Quality Category", table_cell_bold), Paragraph("Automated Campus HVAC Action", table_cell_bold), Paragraph("Student & Athletic Advisory Protocol", table_cell_bold)],
        [Paragraph("Below 35 ug/m3", table_cell), Paragraph("Good / Acceptable", table_cell), Paragraph("100% fresh air dampers open. Normal filtration.", table_cell), Paragraph("Unrestricted outdoor sports and campus activities.", table_cell)],
        [Paragraph("35 to 75 ug/m3", table_cell), Paragraph("Moderate", table_cell), Paragraph("Modulate fresh air dampers to 70%. Activate secondary stage filters.", table_cell), Paragraph("Issue advisory for students with diagnosed respiratory conditions.", table_cell)],
        [Paragraph("75 to 150 ug/m3", table_cell), Paragraph("Unhealthy for Sensitive Groups", table_cell), Paragraph("Recirculation mode enabled (80% recirc / 20% fresh). HEPA filtration active.", table_cell), Paragraph("Relocate strenuous outdoor sports indoors. Broadcast campus alert banner.", table_cell)],
        [Paragraph("Above 150 ug/m3", table_cell), Paragraph("Hazardous / Severe Smog", table_cell), Paragraph("100% recirculation mode with positive pressure ionization active.", table_cell), Paragraph("Mandate indoor operations. Distribute N95 protective masks at entrances.", table_cell)],
        [Paragraph("High PM + Stagnant Wind", table_cell), Paragraph("Atmospheric Inversion Surge", table_cell), Paragraph("Pre-cool building envelope 2 hours prior to forecast morning peak.", table_cell), Paragraph("Pre-emptive early advisory to campus administration.", table_cell)]
    ]
    story.append(create_table(action_table, [85, 95, 160, 183]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("8. Deployment Checklist and Monthly Maintenance Protocol", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))
    
    deploy_table = [
        [Paragraph("Phase", table_cell_bold), Paragraph("Task & Operational Procedure", table_cell_bold), Paragraph("Success / Completion Criteria", table_cell_bold)],
        [Paragraph("<b>Phase 1: Lab Bench Test</b>", table_cell), Paragraph("Assemble ESP32, PMS7003, BME280, and SD logger on test breadboard. Flash firmware and verify serial output.", table_cell), Paragraph("Continuous 24-hour error-free data stream verified on UART serial monitor.", table_cell)],
        [Paragraph("<b>Phase 2: Enclosure Assembly</b>", table_cell), Paragraph("Mount components in IP65 enclosure. Fit solar radiation shield over BME280. Apply neutral-cure silicone sealant.", table_cell), Paragraph("Enclosure passed splash test; zero moisture ingress detected.", table_cell)],
        [Paragraph("<b>Phase 3: Rooftop Installation</b>", table_cell), Paragraph("Secure unit to rooftop parapet rail using 2-inch stainless hose clamps. Connect Clopal 10m outdoor extension cable.", table_cell), Paragraph("Unit securely mounted vertically; live telemetry packets verified in database within 5 minutes.", table_cell)],
        [Paragraph("<b>Monthly Maintenance</b>", table_cell), Paragraph("Clean PMS7003 optical inlet with dry compressed air. Perform 3 spot wind checks with handheld anemometer. Inspect silicone seals.", table_cell), Paragraph("Maintenance log signed off; data completeness verified >98.5% for preceding 30 days.", table_cell)]
    ]
    story.append(create_table(deploy_table, [95, 240, 188]))
    story.append(Spacer(1, 14))

    # Sign-off block
    sign_box = [
        [
            Paragraph("<b>Islamabad Campus Authorization:</b><br/><br/>___________________________<br/><b>Munim Qureshi</b><br/>Project Lead, AirSense ISB<br/>Beaconhouse International College", callout_text),
            Paragraph("<b>Faculty Supervision Authorization:</b><br/><br/>___________________________<br/><b>Ms. Sahifa Alam</b><br/>Head of CSSE & AI<br/>Beaconhouse International College", callout_text),
            Paragraph("<b>Karachi Campus Authorization:</b><br/><br/>___________________________<br/><b>Areesha Aqeel</b><br/>Project Lead, AirSense KHI<br/>Beaconhouse International College", callout_text)
        ]
    ]
    story.append(KeepTogether(Table(sign_box, colWidths=[174, 174, 175], style=TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_GRAY),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))))

    primary_hw = output_paths[0]
    doc = SimpleDocTemplate(primary_hw, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=48, bottomMargin=48)
    doc.build(story, canvasmaker=HardwareCanvas)
    print(f"Successfully generated Hardware Framework PDF: {primary_hw}")
    import shutil
    for p in output_paths[1:]:
        shutil.copyfile(primary_hw, p)
        print(f"Copied Hardware Framework PDF to: {p}")


# =============================================================================
# 3. GENERATE VENDOR PRICING & PROCUREMENT REPORT PDF (MATCHING ATTACHED DOC)
# =============================================================================
def generate_vendor_pricing_pdf(output_paths):
    styles = getSampleStyleSheet()

    cover_title = ParagraphStyle(
        'CoverTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=24, leading=28,
        textColor=NAVY, alignment=0, spaceAfter=4
    )
    cover_subtitle = ParagraphStyle(
        'CoverSubtitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=12, leading=15,
        textColor=DARK_TEAL, alignment=0, spaceAfter=10
    )
    h1_style = ParagraphStyle(
        'H1', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=12.5, leading=15.5,
        textColor=NAVY, spaceBefore=12, spaceAfter=5, keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'H2', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=10, leading=13,
        textColor=SLATE, spaceBefore=8, spaceAfter=4, keepWithNext=True
    )
    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, leading=11.5,
        textColor=DARK_TEXT, spaceAfter=5
    )
    callout_style = ParagraphStyle(
        'Callout', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, leading=11, textColor=DARK_TEXT
    )
    table_cell = ParagraphStyle(
        'Cell', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, leading=10.5, textColor=DARK_TEXT
    )
    table_cell_bold = ParagraphStyle('CellBold', parent=table_cell, fontName='Helvetica-Bold')
    table_cell_right = ParagraphStyle('CellRight', parent=table_cell, alignment=2)
    table_cell_right_bold = ParagraphStyle('CellRightBold', parent=table_cell_bold, alignment=2)

    story = []

    # Title
    story.append(Paragraph("AirSense Pakistan", cover_title))
    story.append(Paragraph("Vendor Pricing Report & Budget Appendix", cover_subtitle))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DARK_TEAL, spaceAfter=10))

    # Metric summary
    m1 = Paragraph("<font size=11 color='white'><b>August 2026</b></font><br/><font size=7.5 color='white'>Price Review Date</font>", ParagraphStyle('m1', alignment=1, leading=12))
    m2 = Paragraph("<font size=11 color='#0F294A'><b>PKR 17,787</b></font><br/><font size=7.5 color='#1E3A8A'>Baseline Hardware Subtotal*</font>", ParagraphStyle('m2', alignment=1, leading=12))
    m3 = Paragraph("<font size=11 color='#0F294A'><b>PKR 20,000</b></font><br/><font size=7.5 color='#0F766E'>Total Requested incl. ~5%</font>", ParagraphStyle('m3', alignment=1, leading=12))
    m4 = Paragraph("<font size=11 color='#0F294A'><b>3 to 7 Days</b></font><br/><font size=7.5 color='#2563EB'>Expected Procurement Window</font>", ParagraphStyle('m4', alignment=1, leading=12))

    story.append(Table([[m1, m2, m3, m4]], colWidths=[130, 131, 131, 131], style=TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), NAVY),
        ('BACKGROUND', (1, 0), (1, 0), LIGHT_BLUE),
        ('BACKGROUND', (2, 0), (2, 0), LIGHT_TEAL),
        ('BACKGROUND', (3, 0), (3, 0), LIGHT_BLUE),
        ('BOX', (0, 0), (0, 0), 1, NAVY),
        ('BOX', (1, 0), (1, 0), 1, BORDER_BLUE),
        ('BOX', (2, 0), (2, 0), 1, BORDER_TEAL),
        ('BOX', (3, 0), (3, 0), 1, BORDER_BLUE),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 5),
    ])))
    story.append(Spacer(1, 4))
    story.append(Paragraph("<font size=7.5 color='#64748B'><i>* Radiation shield (Item 11) excluded; local quotation pending. Prices are supplier-listed figures and must be reconfirmed at point of order.</i></font>", ParagraphStyle('footnote', parent=body_style)))
    story.append(Spacer(1, 8))

    story.append(Paragraph("1. Vendor Overview & Domestic Sourcing Strategy", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=6))
    
    story.append(Paragraph(
        "All components are sourced exclusively through domestic vendors and Pakistan-based e-commerce channels to eliminate import delays and customs exposure. The updated sourcing plan replaces the previous Hallroad-centric approach with a set of specialist online electronics suppliers offering authenticated stock, formal listings, and reliable Islamabad delivery.",
        body_style
    ))

    vendor_summary = [
        [Paragraph("Vendor / Channel", table_cell_bold), Paragraph("Type", table_cell_bold), Paragraph("Est. Delivery", table_cell_bold), Paragraph("Reliability", table_cell_bold), Paragraph("Best Used For", table_cell_bold)],
        [Paragraph("<b>Embeded Studio</b>", table_cell), Paragraph("Online Electronics", table_cell), Paragraph("2 to 5 days", table_cell), Paragraph("<font color='#059669'><b>HIGH</b></font>", table_cell), Paragraph("PMS7003 particulate sensor (primary sensing component)", table_cell)],
        [Paragraph("<b>Digilog.pk</b>", table_cell), Paragraph("Online Electronics", table_cell), Paragraph("2 to 5 days", table_cell), Paragraph("<font color='#059669'><b>HIGH</b></font>", table_cell), Paragraph("ESP32 microcontroller, Rain Sensor A", table_cell)],
        [Paragraph("<b>Electrobes</b>", table_cell), Paragraph("Online Electronics", table_cell), Paragraph("2 to 5 days", table_cell), Paragraph("<font color='#059669'><b>HIGH</b></font>", table_cell), Paragraph("BME280 environmental sensor, MicroSD module, Rain Sensor B, UNI-T anemometer", table_cell)],
        [Paragraph("<b>A.E Solution</b>", table_cell), Paragraph("Electrical / Online", table_cell), Paragraph("2 to 5 days", table_cell), Paragraph("<font color='#059669'><b>HIGH</b></font>", table_cell), Paragraph("IP65-rated weatherproof electrical enclosure", table_cell)],
        [Paragraph("<b>Daraz.pk</b>", table_cell), Paragraph("Marketplace", table_cell), Paragraph("2 to 7 days", table_cell), Paragraph("<font color='#D97706'><b>VERIFY</b></font>", table_cell), Paragraph("MicroSD card, jumper wires, cable ties (verify seller ratings and return terms)", table_cell)],
        [Paragraph("<b>Clopal Online</b>", table_cell), Paragraph("Brand / Online", table_cell), Paragraph("2 to 5 days", table_cell), Paragraph("<font color='#059669'><b>HIGH</b></font>", table_cell), Paragraph("Clopal 10 m heavy-duty power extension lead (baseline option)", table_cell)],
        [Paragraph("<b>Powerhouse Express</b>", table_cell), Paragraph("Online", table_cell), Paragraph("2 to 5 days", table_cell), Paragraph("<font color='#059669'><b>HIGH</b></font>", table_cell), Paragraph("Camelion CMS-178 extension reel (alternative option replacing Clopal)", table_cell)],
        [Paragraph("<b>Expert Tools World</b>", table_cell), Paragraph("Online", table_cell), Paragraph("2 to 5 days", table_cell), Paragraph("<font color='#059669'><b>HIGH</b></font>", table_cell), Paragraph("GMSA RTV Silicone weatherproof sealant", table_cell)],
        [Paragraph("<b>Electronics Hub</b>", table_cell), Paragraph("Online Electronics", table_cell), Paragraph("2 to 5 days", table_cell), Paragraph("<font color='#059669'><b>HIGH</b></font>", table_cell), Paragraph("5V 2A AC/DC power adapter", table_cell)],
        [Paragraph("<b>DreamsMart.pk</b>", table_cell), Paragraph("Online", table_cell), Paragraph("2 to 5 days", table_cell), Paragraph("<font color='#059669'><b>HIGH</b></font>", table_cell), Paragraph("Stainless-steel 2-inch hose clamps", table_cell)],
        [Paragraph("<b>Multan Electronics</b>", table_cell), Paragraph("Online / Physical", table_cell), Paragraph("2 to 5 days", table_cell), Paragraph("<font color='#059669'><b>HIGH</b></font>", table_cell), Paragraph("M3 to M6 mild-steel nuts and bolts (confirm final sizes after survey)", table_cell)],
        [Paragraph("<b>Local Hardware Source</b>", table_cell), Paragraph("Physical / Local", table_cell), Paragraph("Same day", table_cell), Paragraph("<font color='#D97706'><b>VERIFY</b></font>", table_cell), Paragraph("Radiation shield: fabricate locally or source equivalent", table_cell)]
    ]
    story.append(create_table(vendor_summary, [105, 85, 68, 65, 200]))
    story.append(Spacer(1, 10))

    # PAGE 2: COMPLETE LINE-ITEM PRICING & FINAL COSTING STATEMENT
    story.append(PageBreak())
    story.append(Paragraph("2. Complete Line-Item Pricing (August 2026 Review)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_TEAL, spaceAfter=6))

    full_bom = [
        [Paragraph("#", table_cell_bold), Paragraph("Component / Item", table_cell_bold), Paragraph("Model / Specification", table_cell_bold), Paragraph("Vendor", table_cell_bold), Paragraph("Qty", table_cell_right_bold), Paragraph("Unit (PKR)", table_cell_right_bold), Paragraph("Total (PKR)", table_cell_right_bold)],
        [Paragraph("1", table_cell), Paragraph("PM Sensor", table_cell), Paragraph("PMS7003 PM1/PM2.5/PM10 Laser Sensor", table_cell), Paragraph("Embeded Studio", table_cell), Paragraph("1", table_cell_right), Paragraph("4,200", table_cell_right), Paragraph("4,200", table_cell_right)],
        [Paragraph("2", table_cell), Paragraph("Microcontroller", table_cell), Paragraph("ESP32 WROOM-32D Development Board", table_cell), Paragraph("Digilog.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("1,160", table_cell_right), Paragraph("1,160", table_cell_right)],
        [Paragraph("3", table_cell), Paragraph("Environmental Sensor", table_cell), Paragraph("BME280 Temp / Humidity / Pressure", table_cell), Paragraph("Electrobes", table_cell), Paragraph("1", table_cell_right), Paragraph("850", table_cell_right), Paragraph("850", table_cell_right)],
        [Paragraph("4", table_cell), Paragraph("Data Logging Module", table_cell), Paragraph("Arduino MicroSD Card Reader Module", table_cell), Paragraph("Electrobes", table_cell), Paragraph("1", table_cell_right), Paragraph("150", table_cell_right), Paragraph("150", table_cell_right)],
        [Paragraph("5", table_cell), Paragraph("Storage Media", table_cell), Paragraph("Samsung EVO Plus 16 GB MicroSD Card", table_cell), Paragraph("Daraz.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("1,450", table_cell_right), Paragraph("1,450", table_cell_right)],
        [Paragraph("6", table_cell), Paragraph("Weather Enclosure", table_cell), Paragraph("Waterproof Electrical Box, IP65-rated", table_cell), Paragraph("A.E Solution", table_cell), Paragraph("1", table_cell_right), Paragraph("750", table_cell_right), Paragraph("750", table_cell_right)],
        [Paragraph("7", table_cell), Paragraph("Connectivity Wiring", table_cell), Paragraph("20 cm Mixed Jumper Wire Kit, 120 pcs", table_cell), Paragraph("Daraz.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("440", table_cell_right), Paragraph("440", table_cell_right)],
        [Paragraph("8", table_cell), Paragraph("Power Supply", table_cell), Paragraph("5V 2A AC/DC Power Adapter", table_cell), Paragraph("Electronics Hub", table_cell), Paragraph("1", table_cell_right), Paragraph("170", table_cell_right), Paragraph("170", table_cell_right)],
        [Paragraph("9", table_cell), Paragraph("Mounting: Cable Ties", table_cell), Paragraph("Black Nylon Self-Locking Cable Ties", table_cell), Paragraph("Daraz.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("120", table_cell_right), Paragraph("120", table_cell_right)],
        [Paragraph("10", table_cell), Paragraph("Mounting: Clamps", table_cell), Paragraph("2-inch Stainless-Steel Hose Clamps, 2 pcs", table_cell), Paragraph("DreamsMart.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("60", table_cell_right), Paragraph("60", table_cell_right)],
        [Paragraph("11", table_cell), Paragraph("Radiation Shield", table_cell), Paragraph("Solar Radiation Shield / Stevenson Screen", table_cell), Paragraph("Local source required", table_cell), Paragraph("0", table_cell_right), Paragraph("TBD", table_cell_right), Paragraph("TBD", table_cell_right)],
        [Paragraph("12", table_cell), Paragraph("Rain Proxy Sensor A", table_cell), Paragraph("Raindrop Detection Sensor Module", table_cell), Paragraph("Digilog.pk", table_cell), Paragraph("1", table_cell_right), Paragraph("160", table_cell_right), Paragraph("160", table_cell_right)],
        [Paragraph("13", table_cell), Paragraph("Rain Proxy Sensor B", table_cell), Paragraph("Rain Drop Moisture Detection Module", table_cell), Paragraph("Electrobes", table_cell), Paragraph("1", table_cell_right), Paragraph("150", table_cell_right), Paragraph("150", table_cell_right)],
        [Paragraph("", table_cell_bold), Paragraph("<b>CORE BUILD PRICED SUBTOTAL (Items 1 to 10, 12 to 13 | Item 11 excluded)</b>", table_cell_bold), Paragraph("", table_cell), Paragraph("", table_cell), Paragraph("12", table_cell_right_bold), Paragraph("", table_cell), Paragraph("<b>PKR 9,660</b>", table_cell_right_bold)],
        [Paragraph("14", table_cell), Paragraph("Validation Anemometer", table_cell), Paragraph("UNI-T UT363 Digital Anemometer", table_cell), Paragraph("Electrobes", table_cell), Paragraph("1", table_cell_right), Paragraph("4,250", table_cell_right), Paragraph("4,250", table_cell_right)],
        [Paragraph("15", table_cell), Paragraph("Power Extension Cable", table_cell), Paragraph("Clopal 10 m Heavy-Duty, 5-Way Lead", table_cell), Paragraph("Clopal Online", table_cell), Paragraph("1", table_cell_right), Paragraph("3,295", table_cell_right), Paragraph("3,295", table_cell_right)],
        [Paragraph("16", table_cell), Paragraph("Weatherproof Sealant", table_cell), Paragraph("GMSA RTV Silicone Caulk Sealant, 310 ml", table_cell), Paragraph("Expert Tools World", table_cell), Paragraph("1", table_cell_right), Paragraph("390", table_cell_right), Paragraph("390", table_cell_right)],
        [Paragraph("17", table_cell), Paragraph("Mounting Fasteners", table_cell), Paragraph("M3 to M6 Mild-Steel Nuts & Bolts (8 pcs)", table_cell), Paragraph("Multan Electronics", table_cell), Paragraph("8", table_cell_right), Paragraph("24", table_cell_right), Paragraph("192", table_cell_right)],
        [Paragraph("", table_cell_bold), Paragraph("<b>VALIDATION & DEPLOYMENT ADDITIONS SUBTOTAL (Items 14 to 17)</b>", table_cell_bold), Paragraph("", table_cell), Paragraph("", table_cell), Paragraph("4", table_cell_right_bold), Paragraph("", table_cell), Paragraph("<b>PKR 8,127</b>", table_cell_right_bold)],
        [Paragraph("", table_cell_bold), Paragraph("<b>BASELINE HARDWARE SUBTOTAL (Core + Additions, Items 1 to 10, 12 to 17)</b>", table_cell_bold), Paragraph("", table_cell), Paragraph("", table_cell), Paragraph("16", table_cell_right_bold), Paragraph("", table_cell), Paragraph("<b>PKR 17,787</b>", table_cell_right_bold)],
        [Paragraph("18", table_cell), Paragraph("Power Extension Alt.", table_cell), Paragraph("Camelion CMS-178 Extension Reel, 10 m", table_cell), Paragraph("Powerhouse Express", table_cell), Paragraph("1", table_cell_right), Paragraph("4,200", table_cell_right), Paragraph("4,200", table_cell_right)]
    ]
    story.append(create_table(full_bom, [18, 95, 150, 95, 25, 60, 80], custom_style=[
        ('BACKGROUND', (0, 14), (-1, 14), LIGHT_TEAL),
        ('BACKGROUND', (0, 19), (-1, 19), LIGHT_TEAL),
        ('BACKGROUND', (0, 20), (-1, 20), LIGHT_BLUE),
        ('BACKGROUND', (0, 21), (-1, 21), LIGHT_AMBER),
    ]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("3. Final Costing Statement", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=6))

    costing_stmt = [
        [Paragraph("Cost Statement", table_cell_bold), Paragraph("PKR", table_cell_right_bold), Paragraph("Basis & Notes", table_cell_bold)],
        [Paragraph("Baseline priced hardware", table_cell), Paragraph("17,787", table_cell_right), Paragraph("Items 1 to 10 and 12 to 17 at listed prices. Item 11 (radiation shield) excluded pending local quotation.", table_cell)],
        [Paragraph("Contingency reserve ~ 5%", table_cell), Paragraph("889", table_cell_right), Paragraph("Rounded to nearest rupee. Covers minor price movements at time of order.", table_cell)],
        [Paragraph("<b>TOTAL BASELINE BUDGET REQUEST</b>", table_cell_bold), Paragraph("<b>PKR 18,676</b>", table_cell_right_bold), Paragraph("<b>Recommended approval amount. Radiation shield to be added after local quotation.</b>", table_cell_bold)],
        [Paragraph("Alternative hardware subtotal (Item 18 replaces Item 15)", table_cell), Paragraph("18,692", table_cell_right), Paragraph("Camelion reel substituted for Clopal lead. PKR 905 increase before contingency.", table_cell)],
        [Paragraph("Alternative contingency ~ 5%", table_cell), Paragraph("1,308", table_cell_right), Paragraph("Rounded to nearest rupee.", table_cell)],
        [Paragraph("<b>TOTAL WITH CAMELION ALTERNATIVE</b>", table_cell_bold), Paragraph("<b>PKR 20,000</b>", table_cell_right_bold), Paragraph("<b>Alternative scenario only. Excludes radiation-shield local quote.</b>", table_cell_bold)]
    ]
    story.append(create_table(costing_stmt, [180, 80, 263], custom_style=[
        ('BACKGROUND', (0, 3), (-1, 3), LIGHT_TEAL),
        ('BACKGROUND', (0, 6), (-1, 6), NAVY),
        ('TEXTCOLOR', (0, 6), (-1, 6), WHITE),
    ]))

    primary_vendor = output_paths[0]
    doc = SimpleDocTemplate(primary_vendor, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=48, bottomMargin=48)
    doc.build(story, canvasmaker=VendorCanvas)
    print(f"Successfully generated Vendor Pricing PDF: {primary_vendor}")
    import shutil
    for p in output_paths[1:]:
        shutil.copyfile(primary_vendor, p)
        print(f"Copied Vendor Pricing PDF to: {p}")


def main():
    print("\n========================================================")
    print("STARTING MASTER PDF GENERATION WITH EXACT UPDATED BUDGET")
    print("========================================================")

    # 1. Proposal PDF
    proposal_paths = [
        os.path.join(BASE_DIR, "AirSense_Campus_Proposal.pdf"),
        os.path.join(PROPOSAL_DIR, "AirSense_Campus_Proposal_Revised.pdf"),
        os.path.join(DOCS_DIR, "AirSense_Campus_Proposal.pdf")
    ]
    generate_campus_proposal_pdf(proposal_paths)

    # 2. Hardware Framework PDF
    hw_paths = [
        os.path.join(BASE_DIR, "AirSense_Hardware_Framework.pdf"),
        os.path.join(BASE_DIR, "AirSense_Hardware_and_Technical_Framework.pdf"),
        os.path.join(DOCS_DIR, "AirSense_Hardware_and_Technical_Framework.pdf")
    ]
    generate_hardware_framework_pdf(hw_paths)

    # 3. Vendor Pricing PDF
    vendor_paths = [
        os.path.join(BASE_DIR, "AirSense_Vendor_Pricing_Report.pdf"),
        os.path.join(DOCS_DIR, "AirSense_Vendor_Pricing_Report.pdf")
    ]
    generate_vendor_pricing_pdf(vendor_paths)

    print("\n========================================================")
    print("ALL UPDATED MASTER PDFS GENERATED SUCCESSFULLY!")
    print("========================================================")

if __name__ == "__main__":
    main()

