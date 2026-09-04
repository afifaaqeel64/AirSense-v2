import os
import sys
import fitz
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

BASE_DIR = r"d:\MUNIM - UOE @BIC\AirSense\Campus Deployment - LATEST"
OUTPUT_PDF = os.path.join(BASE_DIR, r"PROPOSAL - ISBD - HEADOFFICE\AirSense_Campus_Proposal_Revised.pdf")
IMAGE_DIR = os.path.join(BASE_DIR, "extracted_images")

# Color Palette
NAVY = colors.HexColor("#1A365D")
BLUE = colors.HexColor("#2B6CB0")
LIGHT_BLUE = colors.HexColor("#EBF8FF")
BORDER_BLUE = colors.HexColor("#BEE3F8")
LIGHT_GREEN = colors.HexColor("#F0FFF4")
BORDER_GREEN = colors.HexColor("#C6F6D5")
GRAY_BG = colors.HexColor("#F7FAFC")
BORDER_GRAY = colors.HexColor("#E2E8F0")
TEXT_DARK = colors.HexColor("#2D3748")
TEXT_MUTED = colors.HexColor("#4A5568")
CALLOUT_BG = colors.HexColor("#F0F4F8")
ACCENT_LINE = colors.HexColor("#2B6CB0")

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas for header and footer with total page count.
    No em-dashes used anywhere.
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
        if self._pageNumber == 1:
            # Top accent bar on cover
            self.setFillColor(NAVY)
            self.rect(0, 841.89 - 14, 595.27, 14, fill=1, stroke=0)
            return

        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(TEXT_MUTED)

        # Header
        self.drawString(40, 812, "AirSense | Campus Pilot Proposal")
        self.drawRightString(595.27 - 40, 812, "Beaconhouse International College, Islamabad")
        self.setStrokeColor(BORDER_GRAY)
        self.setLineWidth(0.75)
        self.line(40, 804, 595.27 - 40, 804)

        # Footer
        self.line(40, 42, 595.27 - 40, 42)
        self.drawString(40, 28, "July 2026 | Executive Review")
        self.drawRightString(595.27 - 40, 28, f"Page {self._pageNumber}")
        self.restoreState()


def build_proposal_pdf():
    os.makedirs(os.path.dirname(OUTPUT_PDF), exist_ok=True)
    
    doc = SimpleDocTemplate(
        OUTPUT_PDF,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=45,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=40,
        leading=44,
        textColor=NAVY,
        alignment=1,
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=20,
        leading=24,
        textColor=BLUE,
        alignment=1,
        spaceAfter=20
    )
    cover_desc_style = ParagraphStyle(
        'CoverDesc',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=NAVY,
        alignment=1,
        spaceAfter=6
    )
    cover_tag_style = ParagraphStyle(
        'CoverTagline',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=11,
        leading=15,
        textColor=TEXT_MUTED,
        alignment=1,
        spaceAfter=25
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=NAVY,
        spaceBefore=14,
        spaceAfter=4,
        keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=BLUE,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )
    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=TEXT_DARK,
        spaceAfter=8
    )
    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )
    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9.2,
        leading=13.5,
        textColor=NAVY
    )
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.white
    )
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=TEXT_DARK
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=table_cell_style,
        fontName='Helvetica-Bold'
    )

    story = []

    # -------------------------------------------------------------------------
    # PAGE 1: COVER PAGE
    # -------------------------------------------------------------------------
    story.append(Spacer(1, 1.2 * inch))
    story.append(Paragraph("AirSense", title_style))
    story.append(Paragraph("Campus Pilot Initiative", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=20, spaceBefore=5))
    
    story.append(Paragraph("Rooftop Air Quality Monitoring, Intelligent Forecasting and Campus Decision Support", cover_desc_style))
    story.append(Paragraph("A Business Proposal for Budget Approval, Hardware Deployment and Strategic Pilot Validation", cover_tag_style))
    story.append(Spacer(1, 0.4 * inch))

    # Box 1: Submitted To
    sub_to_html = """
    <b>SUBMITTED TO</b><br/><br/>
    <b>Ms. Saba Ahson</b><br/>
    Head of Institute &nbsp;|&nbsp; Beaconhouse International College, Islamabad<br/><br/>
    <b>Ms. Sahifa Alam</b><br/>
    Head of CSSE / AI Department &nbsp;|&nbsp; Beaconhouse International College, Islamabad
    """
    p_sub_to = Paragraph(sub_to_html, ParagraphStyle('SubTo', parent=body_style, alignment=1, leading=14))
    t_sub_to = Table([[p_sub_to]], colWidths=[480])
    t_sub_to.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BLUE),
        ('BOX', (0,0), (-1,-1), 1, BLUE),
        ('PADDING', (0,0), (-1,-1), 14),
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))
    story.append(t_sub_to)
    story.append(Spacer(1, 0.3 * inch))

    # Box 2: Submitted By
    sub_by_html = """
    <b>SUBMITTED BY</b><br/><br/>
    <b>Munim Qureshi</b><br/>
    AirSense Project Team &nbsp;|&nbsp; Beaconhouse International College, Islamabad
    """
    p_sub_by = Paragraph(sub_by_html, ParagraphStyle('SubBy', parent=body_style, alignment=1, leading=14))
    t_sub_by = Table([[p_sub_by]], colWidths=[480])
    t_sub_by.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), GRAY_BG),
        ('BOX', (0,0), (-1,-1), 0.75, BORDER_GRAY),
        ('PADDING', (0,0), (-1,-1), 12),
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))
    story.append(t_sub_by)
    story.append(Spacer(1, 0.6 * inch))

    cover_footer_html = "<font color='#718096'>July 2026<br/>CONFIDENTIAL &nbsp;|&nbsp; FOR INSTITUTIONAL REVIEW ONLY</font>"
    story.append(Paragraph(cover_footer_html, ParagraphStyle('CoverFoot', parent=body_style, alignment=1, fontSize=9)))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 2: METRIC BANNER & EXECUTIVE SUMMARY
    # -------------------------------------------------------------------------
    m1 = Paragraph("<font size=13 color='white'><b>PKR 20,000</b></font><br/><font size=8 color='white'>Budget Requested</font>", ParagraphStyle('m1', alignment=1, leading=14))
    m2 = Paragraph("<font size=13 color='#1A365D'><b>3 Months</b></font><br/><font size=8 color='#2B6CB0'>Pilot Duration</font>", ParagraphStyle('m2', alignment=1, leading=14))
    m3 = Paragraph("<font size=13 color='#1A365D'><b>2 Sites</b></font><br/><font size=8 color='#276749'>Islamabad + Karachi</font>", ParagraphStyle('m3', alignment=1, leading=14))
    m4 = Paragraph("<font size=13 color='#1A365D'><b>4 Horizons</b></font><br/><font size=8 color='#2B6CB0'>1h / 3h / 6h / 24h Forecasts</font>", ParagraphStyle('m4', alignment=1, leading=14))

    metric_table = Table([[m1, m2, m3, m4]], colWidths=[125, 125, 125, 125])
    metric_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), NAVY),
        ('BACKGROUND', (1,0), (1,0), LIGHT_BLUE),
        ('BACKGROUND', (2,0), (2,0), LIGHT_GREEN),
        ('BACKGROUND', (3,0), (3,0), LIGHT_BLUE),
        ('BOX', (0,0), (0,0), 1, NAVY),
        ('BOX', (1,0), (1,0), 1, BORDER_BLUE),
        ('BOX', (2,0), (2,0), 1, BORDER_GREEN),
        ('BOX', (3,0), (3,0), 1, BORDER_BLUE),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(metric_table)
    story.append(Spacer(1, 12))

    # 1. Executive Summary
    story.append(Paragraph("1. Executive Summary", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8, spaceBefore=2))
    
    story.append(Paragraph(
        "<b>AirSense</b> is an intelligent campus environmental decision platform developed by students at <b>Beaconhouse International College (BIC), Islamabad</b>. Recognized in international innovation competitions, AirSense transforms environmental data into direct, actionable business and administrative guidance for campus leadership.",
        body_style
    ))
    story.append(Paragraph(
        "This proposal requests formal approval for a one-time hardware investment of <b>PKR 20,000</b> to execute Phase 1 of the AirSense Campus Pilot at BIC Islamabad. The pilot includes installing a low-cost rooftop sensor unit, collecting three months of continuous air quality data, and calibrating predictive forecasting models. Operating in parallel with a sister pilot at BIC Karachi, this initiative creates Pakistan's first multi-campus smart environmental network.",
        body_style
    ))

    # Callout Box 1
    callout_1 = Paragraph(
        "<b>Strategic Financial Assurance:</b> The PKR 20,000 budget covers 100% of hardware procurement, installation, weatherproofing, and contingency reserves. <b>Zero cloud, subscription, or recurring costs</b> are incurred during the pilot. The institute's exposure is strictly limited to a single capital expenditure yielding lasting institutional assets.",
        callout_style
    )
    t_callout_1 = Table([[callout_1]], colWidths=[500])
    t_callout_1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BLUE),
        ('BOX', (0,0), (-1,-1), 1, BORDER_BLUE),
        ('LINELEFT', (0,0), (-1,-1), 4, BLUE),
        ('PADDING', (0,0), (-1,-1), 10)
    ]))
    story.append(t_callout_1)
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        "At the conclusion of the pilot, BIC will possess a validated environmental dataset, calibrated forecasting engines, an operational decision playbook, and a published pilot report. These assets deliver clear brand leadership, student health protection, and proprietary intellectual property for Beaconhouse.",
        body_style
    ))

    # 2. Strategic Background and Origin
    story.append(Paragraph("2. Strategic Background and Origin", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8, spaceBefore=2))

    story.append(Paragraph("2.1 The Origin of AirSense: Market-Validated Innovation", h2_style))
    story.append(Paragraph(
        "AirSense was conceived during an international academic innovation challenge, earning top recognition for its unique business focus. While traditional air quality systems output raw, complex graphs, AirSense operates at the <b>executive decision layer</b>: converting complex predictions into clear administrative actions such as adjusting building ventilation, rescheduling outdoor sports, or issuing student health advisories.",
        body_style
    ))
    story.append(Paragraph(
        "Early prototypes proved the core concept using public data. Moving to a live campus pilot provides the hyper-local microclimate data required to achieve commercial predictive accuracy.",
        body_style
    ))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 3: WHY CAMPUS PILOT & THE PROBLEM ADDRESSED
    # -------------------------------------------------------------------------
    story.append(Paragraph("2.2 Why BIC Islamabad is the Ideal Flagship Hub", h2_style))
    story.append(Paragraph(
        "Every successful commercial technology requires a controlled environment to validate operational utility. BIC Islamabad offers the ideal flagship location: clear physical boundaries, established power and network infrastructure, an active student community, and progressive institutional leadership.",
        body_style
    ))
    story.append(Paragraph(
        "By hosting this pilot, BIC Islamabad becomes the founding innovation hub for smart campus environmental management across the Beaconhouse network, generating the institution's first continuous local air quality dataset.",
        body_style
    ))

    story.append(Paragraph("2.3 The Business, Health, and Operational Problem Addressed", h2_style))
    story.append(Paragraph(
        "Seasonal smog and fine particulate pollution (PM2.5) in the Islamabad region create significant operational challenges for educational institutions. Poor air quality directly affects student health, classroom focus, and attendance. Currently, campus administrators make operational decisions without predictive intelligence, often reacting too late to pollution spikes.",
        body_style
    ))
    story.append(Paragraph(
        "AirSense fills this gap by delivering 24-hour predictive risk forecasts, enabling BIC management to fulfill its duty of care for student health while optimizing campus facility operations.",
        body_style
    ))

    # 3. The AirSense System
    story.append(Paragraph("3. The AirSense System", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8, spaceBefore=2))

    story.append(Paragraph("3.1 System Architecture: Transforming Data into Business Value", h2_style))
    story.append(Paragraph(
        "AirSense connects physical hardware to administrative decision-making through four simple layers:",
        body_style
    ))

    # Architecture Table
    arch_data = [
        [Paragraph("System Layer", table_header_style), Paragraph("Hardware & Software Stack", table_header_style), Paragraph("Business & Institutional Value", table_header_style)],
        [
            Paragraph("<b>Sensing Layer</b>", table_cell_bold),
            Paragraph("PMS7003 + BME280 + Rain Sensors", table_cell_style),
            Paragraph("Captures continuous rooftop particulate, temperature, humidity, and rain metrics.", table_cell_style)
        ],
        [
            Paragraph("<b>Control & Logging</b>", table_cell_bold),
            Paragraph("ESP32 Controller + Onboard MicroSD", table_cell_style),
            Paragraph("Ensures 100% data security and continuous logging with zero external cloud dependencies.", table_cell_style)
        ],
        [
            Paragraph("<b>Forecasting Engine</b>", table_cell_bold),
            Paragraph("Machine Learning Algorithms", table_cell_style),
            Paragraph("Generates 1-hour, 3-hour, 6-hour, and 24-hour ahead pollution risk predictions.", table_cell_style)
        ],
        [
            Paragraph("<b>Decision Layer</b>", table_cell_bold),
            Paragraph("Operational Playbook + AI Advisor", table_cell_style),
            Paragraph("Translates predictions into plain-language administrative instructions for campus managers.", table_cell_style)
        ]
    ]

    t_arch = Table(arch_data, colWidths=[100, 130, 270])
    t_arch.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, GRAY_BG]),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_arch)
    story.append(Spacer(1, 10))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 4: WHAT MAKES AIRSENSE DIFFERENT & FEATURES
    # -------------------------------------------------------------------------
    story.append(Paragraph("3.2 What Makes AirSense Different: The Decision Advantage", h2_style))
    story.append(Paragraph(
        "Conventional environmental monitors only show past pollution data. AirSense provides <b>predictive operational recommendations</b>. Rather than asking campus staff to interpret technical data, the platform provides direct advice: <i>'High smog expected in 4 hours. Switch HVAC intake to internal recirculation and move physical education classes indoors.'</i>",
        body_style
    ))
    story.append(Paragraph(
        "Furthermore, the platform is designed for rapid expansion across additional Beaconhouse campuses, offering a standardized blueprint for group-wide adoption.",
        body_style
    ))

    story.append(Paragraph("3.3 Operational Capabilities and Input Drivers", h2_style))
    story.append(Paragraph(
        "The system combines multiple inputs to deliver accurate forecasts tailored to campus needs:",
        body_style
    ))

    feat_data = [
        [Paragraph("Category", table_header_style), Paragraph("Input Variable", table_header_style), Paragraph("Primary Source", table_header_style), Paragraph("Operational Benefit", table_header_style)],
        [Paragraph("Target Metric", table_cell_bold), Paragraph("PM2.5 Concentration", table_cell_style), Paragraph("Rooftop Sensor", table_cell_style), Paragraph("Core indicator used to trigger health warnings.", table_cell_style)],
        [Paragraph("Historical Trends", table_cell_bold), Paragraph("Hourly Lag Records", table_cell_style), Paragraph("Onboard Storage", table_cell_style), Paragraph("Captures daily microclimate and traffic patterns.", table_cell_style)],
        [Paragraph("Meteorology", table_cell_bold), Paragraph("Temperature & Humidity", table_cell_style), Paragraph("BME280 Sensor", table_cell_style), Paragraph("Models atmospheric conditions driving smog formation.", table_cell_style)],
        [Paragraph("Rain Events", table_cell_bold), Paragraph("Rainfall Indicator", table_cell_style), Paragraph("Rain Sensor", table_cell_style), Paragraph("Identifies natural air cleansing events.", table_cell_style)],
        [Paragraph("Wind Patterns", table_cell_bold), Paragraph("Wind Speed & Direction", table_cell_style), Paragraph("Weather API", table_cell_style), Paragraph("Forecasts regional pollution movement toward campus.", table_cell_style)],
        [Paragraph("Campus Schedule", table_cell_bold), Paragraph("Academic Calendar Flags", table_cell_style), Paragraph("System Calendar", table_cell_style), Paragraph("Adjusts predictions based on term times and breaks.", table_cell_style)]
    ]

    t_feat = Table(feat_data, colWidths=[80, 120, 100, 200])
    t_feat.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, GRAY_BG]),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_feat)
    story.append(Spacer(1, 10))

    # 4. Campus Pilot Plan
    story.append(Paragraph("4. Campus Pilot Implementation Plan", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8, spaceBefore=2))

    story.append(Paragraph("4.1 Strategic Pilot Objectives", h2_style))
    story.append(Paragraph("<b>1. Hardware Commissioning:</b> Deploy a weatherproofed rooftop sensor unit at BIC Islamabad to verify continuous operation.", bullet_style))
    story.append(Paragraph("<b>2. Proprietary Data Asset:</b> Build a clean three-month environmental dataset owned entirely by BIC.", bullet_style))
    story.append(Paragraph("<b>3. Model Accuracy Validation:</b> Calibrate machine learning models for 24-hour ahead air quality forecasting.", bullet_style))
    story.append(Paragraph("<b>4. Administrative Utility Testing:</b> Evaluate automated administrative alerts against real campus events.", bullet_style))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 5: SETUP AND DEPLOYMENT PHASES (0-4)
    # -------------------------------------------------------------------------
    story.append(Paragraph("4.2 Phased Deployment Roadmap", h2_style))
    story.append(Paragraph(
        "The project follows a structured, risk-managed 6-phase roadmap designed for smooth execution without administrative burden:",
        body_style
    ))

    phase_data = [
        [Paragraph("Phase & Timeline", table_header_style), Paragraph("Activity Focus", table_header_style), Paragraph("Executive & Operational Deliverables", table_header_style)],
        [
            Paragraph("<b>Phase 0</b><br/>Days 1 to 7", table_cell_bold),
            Paragraph("Hardware Procurement", table_cell_style),
            Paragraph("• Procure verified sensor components from local vendors.<br/>• Secure weatherproofing enclosure and power leads.<br/>• Perform initial quality checks before bench assembly.", table_cell_style)
        ],
        [
            Paragraph("<b>Phase 1</b><br/>Days 6 to 9", table_cell_bold),
            Paragraph("Bench Assembly & Benchmarking", table_cell_style),
            Paragraph("• Assemble controller, sensors, and storage modules.<br/>• Upload system firmware and test data logging.<br/>• Confirm Wi-Fi data transmission to campus workstation.", table_cell_style)
        ],
        [
            Paragraph("<b>Phase 2</b><br/>Days 9 to 10", table_cell_bold),
            Paragraph("Rooftop Installation", table_cell_style),
            Paragraph("• Mount weatherproof enclosure on BIC rooftop.<br/>• Connect power and verify Wi-Fi signal strength.<br/>• Initiate live data logging. Pilot clock starts.", table_cell_style)
        ],
        [
            Paragraph("<b>Phase 3</b><br/>Months 1 to 3", table_cell_bold),
            Paragraph("Autonomous Data Collection", table_cell_style),
            Paragraph("• Sensor operates continuously with zero daily maintenance.<br/>• Data collection runs through weekends and academic breaks.<br/>• Weekly quality checks ensure uninterrupted telemetry.", table_cell_style)
        ],
        [
            Paragraph("<b>Phase 4</b><br/>Months 2 to 3", table_cell_bold),
            Paragraph("Model Training & Calibration", table_cell_style),
            Paragraph("• Clean environmental dataset and remove anomalies.<br/>• Train time-series machine learning models.<br/>• Evaluate forecast accuracy across prediction horizons.", table_cell_style)
        ]
    ]

    t_phase = Table(phase_data, colWidths=[90, 140, 270])
    t_phase.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, GRAY_BG]),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_phase)
    story.append(Spacer(1, 10))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 6: REPORTING, CLOSEOUT & KARACHI COLLABORATION
    # -------------------------------------------------------------------------
    phase5_data = [
        [Paragraph("Phase & Timeline", table_header_style), Paragraph("Activity Focus", table_header_style), Paragraph("Executive & Operational Deliverables", table_header_style)],
        [
            Paragraph("<b>Phase 5</b><br/>End Month 3", table_cell_bold),
            Paragraph("Executive Reporting & Handover", table_cell_style),
            Paragraph("• Evaluate operational decision accuracy against campus conditions.<br/>• Deliver comprehensive Pilot Completion Report to BIC Management.<br/>• Archive dataset and trained models; present expansion options.", table_cell_style)
        ]
    ]
    t_phase5 = Table(phase5_data, colWidths=[90, 140, 270])
    t_phase5.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_phase5)
    story.append(Spacer(1, 10))

    callout_2 = Paragraph(
        "<b>Autonomous, Maintenance-Free Operation:</b> Once installed, the rooftop unit runs autonomously without requiring daily staff attention. Data collection continues smoothly across academic breaks, building a robust asset for the college.",
        callout_style
    )
    t_callout_2 = Table([[callout_2]], colWidths=[500])
    t_callout_2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BLUE),
        ('BOX', (0,0), (-1,-1), 1, BORDER_BLUE),
        ('LINELEFT', (0,0), (-1,-1), 4, BLUE),
        ('PADDING', (0,0), (-1,-1), 8)
    ]))
    story.append(t_callout_2)
    story.append(Spacer(1, 12))

    # 5. Karachi Campus Collaboration
    story.append(Paragraph("5. Multi-Campus Network Synergy: Karachi Collaboration", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8, spaceBefore=2))

    story.append(Paragraph("5.1 Two-City Pilot Network Strategy", h2_style))
    story.append(Paragraph(
        "Alongside the Islamabad deployment, a parallel pilot is coordinated at a Beaconhouse campus in Karachi led by a dedicated student lead. Utilizing the exact same hardware configuration and software pipeline, this joint effort creates Pakistan's first multi-campus student air quality network.",
        body_style
    ))

    city_data = [
        [Paragraph("BIC Islamabad (Flagship Hub)", table_header_style), Paragraph("BIC Karachi (Coastal Sister Site)", table_header_style)],
        [
            Paragraph("• Primary development hub and baseline training site.<br/>• Inland climate: cold winter smog, temperature inversions, urban traffic.<br/>• Overseen directly by BIC Islamabad management.", table_cell_style),
            Paragraph("• Parallel deployment validating cross-city compatibility.<br/>• Coastal climate: high humidity, sea breeze dispersion, industrial dust.<br/>• Demonstrates scalability across different regional environments.", table_cell_style)
        ]
    ]
    t_city = Table(city_data, colWidths=[245, 255])
    t_city.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white]),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_city)
    story.append(Spacer(1, 10))

    story.append(Paragraph("5.2 Strategic Value to Beaconhouse", h2_style))
    story.append(Paragraph(
        "Testing across two distinct climate zones proves that AirSense can scale across the entire Beaconhouse Group. This multi-city dataset enhances predictive precision and positions BIC as a pioneer in campus technology.",
        body_style
    ))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 7: BENEFITS TO BEACONHOUSE INTERNATIONAL COLLEGE
    # -------------------------------------------------------------------------
    story.append(Paragraph("6. Core Business Benefits to Beaconhouse International College", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8, spaceBefore=2))
    story.append(Paragraph(
        "The AirSense pilot offers strong strategic, marketing, academic, and financial returns for BIC management:",
        body_style
    ))

    ben_data = [
        [Paragraph("Strategic ROI Pillar", table_header_style), Paragraph("Direct Institutional Value and Persuasive Business Impact", table_header_style)],
        [
            Paragraph("<b>Duty of Care & Student Safety</b>", table_cell_bold),
            Paragraph("Protects student and staff health with 24-hour predictive smog alerts. Minimizes health risks, reduces absenteeism, and demonstrates institutional responsibility.", table_cell_style)
        ],
        [
            Paragraph("<b>Marketing & Admissions PR</b>", table_cell_bold),
            Paragraph("Establishes BIC as <i>'Pakistan's First AI-Powered Smart & Healthy Campus'</i>. Provides a unique, premium story for student recruitment, open days, and social media campaigns.", table_cell_style)
        ],
        [
            Paragraph("<b>Academic Distinction & Partners</b>", table_cell_bold),
            Paragraph("Offers clear evidence of applied engineering leadership to UK degree awarding partners, proving BIC students build deployed, real-world solutions.", table_cell_style)
        ],
        [
            Paragraph("<b>Facility & HVAC Cost Savings</b>", table_cell_bold),
            Paragraph("Enables smart management of building ventilation and outdoor activities, avoiding energy waste and extending air filter life during high-pollution periods.", table_cell_style)
        ],
        [
            Paragraph("<b>Departmental Prestige</b>", table_cell_bold),
            Paragraph("Elevates the standing of the CSSE and AI Department across the Beaconhouse Group, proving practical innovation leadership.", table_cell_style)
        ],
        [
            Paragraph("<b>100% Asset & IP Ownership</b>", table_cell_bold),
            Paragraph("BIC retains full ownership of all hardware, datasets, calibrated models, and research outputs for future academic use or commercial scaling.", table_cell_style)
        ]
    ]

    t_ben = Table(ben_data, colWidths=[150, 350])
    t_ben.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, GRAY_BG]),
        ('PADDING', (0,0), (-1,-1), 7),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_ben)
    story.append(Spacer(1, 10))

    # 7. Dashboard Overview Intro
    story.append(Paragraph("7. Executive Control Dashboard Overview", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8, spaceBefore=2))
    story.append(Paragraph(
        "The AirSense dashboard provides campus leadership with an intuitive interface showing live air metrics, forecast trends, regulatory notices, and conversational AI guidance.",
        body_style
    ))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 8: DASHBOARD VIEWS (MAIN & POLICY TRACKER)
    # -------------------------------------------------------------------------
    story.append(Paragraph("7.1 Main Executive Dashboard and Policy Tracker", h2_style))
    story.append(Paragraph(
        "The primary dashboard displays real-time air quality metrics, 10-day risk trends, and regulatory alerts to support quick administrative decision-making.",
        body_style
    ))

    img_8_1_path = os.path.join(IMAGE_DIR, "page_8_img_1.jpeg")
    img_8_2_path = os.path.join(IMAGE_DIR, "page_8_img_2.jpeg")

    if os.path.exists(img_8_1_path):
        story.append(RLImage(img_8_1_path, width=6.8*inch, height=3.1*inch))
        story.append(Paragraph("<font size=8 color='#4A5568'><i>Figure 7.1a: AirSense Main Overview displaying live air metrics and predictive risk horizons.</i></font>", ParagraphStyle('cap1', alignment=1)))
        story.append(Spacer(1, 10))

    if os.path.exists(img_8_2_path):
        story.append(RLImage(img_8_2_path, width=6.8*inch, height=3.1*inch))
        story.append(Paragraph("<font size=8 color='#4A5568'><i>Figure 7.1b: Regulatory Tracker monitoring environmental directives and campus compliance.</i></font>", ParagraphStyle('cap2', alignment=1)))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 9: AI DECISION ADVISOR & HEALTH RISK PANEL
    # -------------------------------------------------------------------------
    story.append(Paragraph("7.2 AI Decision Advisor and Health Risk Calculator", h2_style))
    story.append(Paragraph(
        "Natural language AI interfaces allow administrators to ask operational questions, while the health calculator recommends safe activity windows for campus groups.",
        body_style
    ))

    img_9_1_path = os.path.join(IMAGE_DIR, "page_9_img_1.jpeg")
    img_9_2_path = os.path.join(IMAGE_DIR, "page_9_img_2.jpeg")

    if os.path.exists(img_9_1_path):
        story.append(RLImage(img_9_1_path, width=6.8*inch, height=2.6*inch))
        story.append(Paragraph("<font size=8 color='#4A5568'><i>Figure 7.2a: AI Advisor providing plain-language operational guidance to campus leadership.</i></font>", ParagraphStyle('cap3', alignment=1)))
        story.append(Spacer(1, 10))

    if os.path.exists(img_9_2_path):
        story.append(RLImage(img_9_2_path, width=6.8*inch, height=3.2*inch))
        story.append(Paragraph("<font size=8 color='#4A5568'><i>Figure 7.2b: Health Risk Panel calculating safe dispatch windows for outdoor activities.</i></font>", ParagraphStyle('cap4', alignment=1)))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 10: POLICY COMMAND CENTRE & EXPANSION PATH
    # -------------------------------------------------------------------------
    story.append(Paragraph("7.3 Policy Command Centre", h2_style))
    story.append(Paragraph(
        "The Policy Command Centre coordinates campus emergency responses during high pollution episodes, issuing automated notices to facility managers.",
        body_style
    ))

    img_10_1_path = os.path.join(IMAGE_DIR, "page_10_img_1.jpeg")
    if os.path.exists(img_10_1_path):
        story.append(RLImage(img_10_1_path, width=6.8*inch, height=3.2*inch))
        story.append(Paragraph("<font size=8 color='#4A5568'><i>Figure 7.3: Policy Command Centre mapping automated advisory triggers to facility actions.</i></font>", ParagraphStyle('cap5', alignment=1)))
        story.append(Spacer(1, 12))

    # 8. Future Vision & Commercial Expansion Scope
    story.append(Paragraph("8. Commercial Vision and Expansion Scope", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8, spaceBefore=2))

    story.append(Paragraph("8.1 From Campus Pilot to Commercial SaaS Platform", h2_style))
    story.append(Paragraph(
        "Phase 1 at BIC Islamabad establishes the foundational data and operational blueprint for a scalable commercial SaaS business targeting enterprise clients.",
        body_style
    ))

    road_data = [
        [Paragraph("Phase", table_header_style), Paragraph("Growth Stage", table_header_style), Paragraph("Strategic Scope and Objectives", table_header_style), Paragraph("Key Institutional Deliverable", table_header_style)],
        [
            Paragraph("<b>1</b>", table_cell_bold),
            Paragraph("Campus Pilot", table_cell_bold),
            Paragraph("Deploy rooftop units at BIC Islamabad and Karachi. Collect 3 months data to train baseline prediction engines.", table_cell_style),
            Paragraph("Validated local dataset, calibrated models, pilot completion report.", table_cell_style)
        ],
        [
            Paragraph("<b>2</b>", table_cell_bold),
            Paragraph("Network Expansion", table_cell_bold),
            Paragraph("Refine algorithms and expand deployment across additional Beaconhouse Group campuses nationwide.", table_cell_style),
            Paragraph("High-accuracy multi-campus model suite, standardized blueprint.", table_cell_style)
        ],
        [
            Paragraph("<b>3</b>", table_cell_bold),
            Paragraph("Commercial Launch", table_cell_bold),
            Paragraph("Launch enterprise SaaS product targeting logistics, construction, healthcare, and educational sectors.", table_cell_style),
            Paragraph("Revenue-generating commercial platform with BIC as founding IP partner.", table_cell_style)
        ]
    ]
    t_road = Table(road_data, colWidths=[40, 90, 220, 150])
    t_road.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, GRAY_BG]),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_road)

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 11: COMMERCIAL USE CASES & BUDGET BREAKDOWN
    # -------------------------------------------------------------------------
    story.append(Paragraph("8.2 B2B Enterprise Market Opportunities", h2_style))
    story.append(Paragraph(
        "AirSense addresses clear operational needs across multiple high-value commercial markets:",
        body_style
    ))

    sec_data = [
        [Paragraph("Enterprise Sector", table_header_style), Paragraph("Environmental Trigger", table_header_style), Paragraph("Commercial Value Proposition", table_header_style)],
        [
            Paragraph("<b>Logistics & Transport</b>", table_cell_bold),
            Paragraph("High morning smog forecast", table_cell_style),
            Paragraph("Adjust shift departure times and optimize routes to reduce driver exposure and delivery delays.", table_cell_style)
        ],
        [
            Paragraph("<b>Schools & Campuses</b>", table_cell_bold),
            Paragraph("PM2.5 spike in next 3 to 6 hours", table_cell_style),
            Paragraph("Move sports activities indoors and adjust building ventilation to protect student health.", table_cell_style)
        ],
        [
            Paragraph("<b>Construction & Mining</b>", table_cell_bold),
            Paragraph("High pollution + low wind dispersion", table_cell_style),
            Paragraph("Activate dust suppression misting and issue safety gear to outdoor work crews.", table_cell_style)
        ],
        [
            Paragraph("<b>Retail & Hospitality</b>", table_cell_bold),
            Paragraph("Severe smog episode alert", table_cell_style),
            Paragraph("Optimize indoor air purification and highlight clean air environments to guests.", table_cell_style)
        ],
        [
            Paragraph("<b>Corporate ESG Reporting</b>", table_cell_bold),
            Paragraph("Repeated threshold exceedance", table_cell_style),
            Paragraph("Generate automated compliance reports for corporate sustainability audits.", table_cell_style)
        ]
    ]
    t_sec = Table(sec_data, colWidths=[130, 150, 220])
    t_sec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, GRAY_BG]),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_sec)
    story.append(Spacer(1, 8))

    callout_3 = Paragraph(
        "<b>BIC as Founding Technology Partner:</b> Approving this pilot establishes BIC Islamabad as the founding institutional partner of AirSense, creating lasting academic recognition and commercial licensing potential.",
        callout_style
    )
    t_callout_3 = Table([[callout_3]], colWidths=[500])
    t_callout_3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BLUE),
        ('BOX', (0,0), (-1,-1), 1, BORDER_BLUE),
        ('LINELEFT', (0,0), (-1,-1), 4, BLUE),
        ('PADDING', (0,0), (-1,-1), 8)
    ]))
    story.append(t_callout_3)
    story.append(Spacer(1, 10))

    # 9. Budget Request
    story.append(Paragraph("9. Executive Budget Request", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8, spaceBefore=2))

    story.append(Paragraph("9.1 Itemized Hardware Budget (PKR 20,000)", h2_style))
    story.append(Paragraph(
        "The requested <b>PKR 20,000</b> represents a single, one-time capital investment covering all physical components, enclosures, weatherproofing, and power leads. Zero recurring costs are required.",
        body_style
    ))

    # Budget Table Items (1-3)
    bud1_data = [
        [Paragraph("#", table_header_style), Paragraph("Component Description", table_header_style), Paragraph("Vendor Source", table_header_style), Paragraph("Qty", table_header_style), Paragraph("Cost (PKR)", table_header_style)],
        [Paragraph("1", table_cell_bold), Paragraph("PMS7003 Laser Dust PM1/PM2.5/PM10 Sensor", table_cell_style), Paragraph("Embeded Studio", table_cell_style), Paragraph("1", table_cell_style), Paragraph("4,200", table_cell_bold)],
        [Paragraph("2", table_cell_bold), Paragraph("ESP32 WROOM-32D Development Board", table_cell_style), Paragraph("Digilog.pk", table_cell_style), Paragraph("1", table_cell_style), Paragraph("1,160", table_cell_bold)],
        [Paragraph("3", table_cell_bold), Paragraph("BME280 Temp / Humidity / Pressure Sensor", table_cell_style), Paragraph("Electrobes", table_cell_style), Paragraph("1", table_cell_style), Paragraph("850", table_cell_bold)]
    ]
    t_bud1 = Table(bud1_data, colWidths=[25, 235, 120, 35, 85])
    t_bud1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (3,0), (4,-1), 'CENTER')
    ]))
    story.append(t_bud1)

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 12: BUDGET TABLE CONTINUED & FUTURE PHASE COSTS
    # -------------------------------------------------------------------------
    bud2_data = [
        [Paragraph("#", table_header_style), Paragraph("Component Description", table_header_style), Paragraph("Vendor Source", table_header_style), Paragraph("Qty", table_header_style), Paragraph("Cost (PKR)", table_header_style)],
        [Paragraph("4", table_cell_bold), Paragraph("Arduino MicroSD Card Reader Module", table_cell_style), Paragraph("Electrobes", table_cell_style), Paragraph("1", table_cell_style), Paragraph("150", table_cell_style)],
        [Paragraph("5", table_cell_bold), Paragraph("Samsung EVO Plus 16 GB MicroSD Card", table_cell_style), Paragraph("Daraz.pk", table_cell_style), Paragraph("1", table_cell_style), Paragraph("1,450", table_cell_style)],
        [Paragraph("6", table_cell_bold), Paragraph("Waterproof IP65 Electrical Enclosure Box", table_cell_style), Paragraph("A.E Solution", table_cell_style), Paragraph("1", table_cell_style), Paragraph("750", table_cell_style)],
        [Paragraph("7", table_cell_bold), Paragraph("Jumper Wire Kit, 120 pcs", table_cell_style), Paragraph("Daraz.pk", table_cell_style), Paragraph("1", table_cell_style), Paragraph("440", table_cell_style)],
        [Paragraph("8", table_cell_bold), Paragraph("5V 2A AC/DC Power Adapter Unit", table_cell_style), Paragraph("Electronics Hub", table_cell_style), Paragraph("1", table_cell_style), Paragraph("170", table_cell_style)],
        [Paragraph("9", table_cell_bold), Paragraph("Cable Ties, 100-pack", table_cell_style), Paragraph("Daraz.pk", table_cell_style), Paragraph("1", table_cell_style), Paragraph("120", table_cell_style)],
        [Paragraph("10", table_cell_bold), Paragraph("2-inch Stainless Hose Clamps (2 pcs)", table_cell_style), Paragraph("DreamsMart.pk", table_cell_style), Paragraph("1", table_cell_style), Paragraph("60", table_cell_style)],
        [Paragraph("11", table_cell_bold), Paragraph("Raindrop Detection Sensor Module A", table_cell_style), Paragraph("Digilog.pk", table_cell_style), Paragraph("1", table_cell_style), Paragraph("160", table_cell_style)],
        [Paragraph("12", table_cell_bold), Paragraph("Rain Drop Moisture Sensor Module B", table_cell_style), Paragraph("Electrobes", table_cell_style), Paragraph("1", table_cell_style), Paragraph("150", table_cell_style)],
        [Paragraph("13", table_cell_bold), Paragraph("UNI-T UT363 Digital Anemometer", table_cell_style), Paragraph("Electrobes", table_cell_style), Paragraph("1", table_cell_style), Paragraph("4,250", table_cell_style)],
        [Paragraph("14", table_cell_bold), Paragraph("Clopal 10m Heavy-Duty Extension Lead", table_cell_style), Paragraph("Clopal Online", table_cell_style), Paragraph("1", table_cell_style), Paragraph("3,295", table_cell_style)],
        [Paragraph("15", table_cell_bold), Paragraph("GMSA RTV Silicone Weatherproof Sealant", table_cell_style), Paragraph("Expert Tools", table_cell_style), Paragraph("1", table_cell_style), Paragraph("390", table_cell_style)],
        [Paragraph("16", table_cell_bold), Paragraph("Mounting Nuts & Bolts M3-M6 (8 pcs)", table_cell_style), Paragraph("Multan Elec.", table_cell_style), Paragraph("8", table_cell_style), Paragraph("192", table_cell_style)],
        [Paragraph("17", table_cell_bold), Paragraph("Radiation Shield (Local Islamabad Sourcing)", table_cell_style), Paragraph("Local Supplier", table_cell_style), Paragraph("1", table_cell_style), Paragraph("TBD", table_cell_style)],
        [Paragraph("", table_cell_bold), Paragraph("<b>Hardware Subtotal (Items 1 to 16)</b>", table_cell_bold), Paragraph("", table_cell_style), Paragraph("", table_cell_style), Paragraph("<b>PKR 17,787</b>", table_cell_bold)],
        [Paragraph("", table_cell_bold), Paragraph("<b>Radiation Shield + Contingency Reserve Buffer</b>", table_cell_bold), Paragraph("", table_cell_style), Paragraph("", table_cell_style), Paragraph("<b>PKR 2,213</b>", table_cell_bold)],
        [Paragraph("", table_cell_bold), Paragraph("<font size=10 color='#1A365D'><b>TOTAL BUDGET REQUESTED</b></font>", table_cell_bold), Paragraph("", table_cell_style), Paragraph("", table_cell_style), Paragraph("<font size=10 color='#1A365D'><b>PKR 20,000</b></font>", table_cell_bold)]
    ]

    t_bud2 = Table(bud2_data, colWidths=[25, 235, 120, 35, 85])
    t_bud2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('PADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (3,0), (4,-1), 'CENTER'),
        ('BACKGROUND', (0,-3), (-1,-1), LIGHT_BLUE),
        ('BOX', (0,-1), (-1,-1), 1.5, NAVY)
    ]))
    story.append(t_bud2)
    story.append(Spacer(1, 8))

    callout_4 = Paragraph(
        "<b>Financial Governance:</b> The radiation shield price is pending final local quotation. The PKR 2,213 contingency buffer is reserved to cover this component and minor price fluctuations. Any unspent funds will be returned to the institute.",
        callout_style
    )
    t_callout_4 = Table([[callout_4]], colWidths=[500])
    t_callout_4.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), GRAY_BG),
        ('BOX', (0,0), (-1,-1), 0.75, BORDER_GRAY),
        ('LINELEFT', (0,0), (-1,-1), 3, NAVY),
        ('PADDING', (0,0), (-1,-1), 7)
    ]))
    story.append(t_callout_4)
    story.append(Spacer(1, 10))

    story.append(Paragraph("9.2 Financial Sustainability", h2_style))
    story.append(Paragraph(
        "Phase 2 operates with zero additional budget by utilizing the Phase 1 hardware stack. Commercial SaaS costs in Phase 3 will be self-funded through client revenue.",
        body_style
    ))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 13: DELIVERABLES & CONCLUSION
    # -------------------------------------------------------------------------
    story.append(Paragraph("10. Deliverables at Pilot Completion", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8, spaceBefore=2))
    story.append(Paragraph(
        "At the end of the 3-month pilot, the project team will formally submit five core deliverables to BIC management:",
        body_style
    ))

    deliv_data = [
        [Paragraph("No.", table_header_style), Paragraph("Deliverable Asset", table_header_style), Paragraph("Institutional Description and Strategic Value", table_header_style)],
        [
            Paragraph("<b>1</b>", table_cell_bold),
            Paragraph("<b>Validated PM2.5 Dataset</b>", table_cell_bold),
            Paragraph("3 months of continuous, timestamped hourly air quality records collected directly from the BIC Islamabad campus.", table_cell_style)
        ],
        [
            Paragraph("<b>2</b>", table_cell_bold),
            Paragraph("<b>Trained Forecasting Models</b>", table_cell_bold),
            Paragraph("Calibrated machine learning models for 1h, 3h, 6h, and 24h prediction horizons with performance metrics.", table_cell_style)
        ],
        [
            Paragraph("<b>3</b>", table_cell_bold),
            Paragraph("<b>Decision Framework Report</b>", table_cell_bold),
            Paragraph("An evaluation of the AI decision layer: testing advice accuracy and real-world administrative utility on campus.", table_cell_style)
        ],
        [
            Paragraph("<b>4</b>", table_cell_bold),
            Paragraph("<b>Environmental Drivers Analysis</b>", table_cell_bold),
            Paragraph("An analytical report identifying the primary atmospheric drivers of local Islamabad pollution.", table_cell_style)
        ],
        [
            Paragraph("<b>5</b>", table_cell_bold),
            Paragraph("<b>Pilot Completion Report</b>", table_cell_bold),
            Paragraph("A comprehensive executive report detailing system performance, multi-campus findings, and expansion options.", table_cell_style)
        ]
    ]

    t_deliv = Table(deliv_data, colWidths=[30, 150, 320])
    t_deliv.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, GRAY_BG]),
        ('PADDING', (0,0), (-1,-1), 7),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_deliv)
    story.append(Spacer(1, 12))

    # 11. Conclusion and Request for Approval
    story.append(Paragraph("11. Conclusion and Formal Request for Approval", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8, spaceBefore=2))
    story.append(Paragraph(
        "AirSense represents an exceptional, low-risk opportunity for Beaconhouse International College. For a modest one-time investment of <b>PKR 20,000</b>, BIC gains a functional smart environmental station, proprietary data assets, calibrated AI decision engines, and a unique marketing asset that reinforces BIC's reputation as a leader in educational innovation.",
        body_style
    ))
    story.append(Paragraph(
        "The project team is ready to commence deployment immediately upon approval.",
        body_style
    ))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 14: FORMAL SIGN-OFF & APPROVAL REQUEST
    # -------------------------------------------------------------------------
    story.append(Paragraph("Formal Request for Management Approval", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=10, spaceBefore=2))

    story.append(Paragraph(
        "The AirSense team respectfully requests approval of the following items from <b>Ms. Saba Ahson</b> and <b>Ms. Sahifa Alam</b>:",
        body_style
    ))

    req_data = [
        [Paragraph("<b>1</b>", table_cell_bold), Paragraph("Approval of a one-time hardware budget of <b>PKR 20,000</b> for procurement of sensor components itemized in Section 9.", table_cell_style)],
        [Paragraph("<b>2</b>", table_cell_bold), Paragraph("Permission to install the weatherproofed sensor unit at an agreed rooftop location on the BIC Islamabad campus for three months.", table_cell_style)],
        [Paragraph("<b>3</b>", table_cell_bold), Paragraph("Facilitation of access to a rooftop power outlet and setup of a campus Wi-Fi extender for live telemetry.", table_cell_style)],
        [Paragraph("<b>4</b>", table_cell_bold), Paragraph("Official recognition as a supported BIC student project, enabling access to campus computing resources for model training.", table_cell_style)]
    ]
    t_req = Table(req_data, colWidths=[30, 470])
    t_req.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BLUE),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story.append(t_req)
    story.append(Spacer(1, 15))

    banner_p = Paragraph(
        "<font size=12 color='white'><b>The sensor goes on the roof. The data comes in. The models learn.<br/>We ask for PKR 20,000 and three months to prove that it works.<br/>Everything else follows from that.</b></font>",
        ParagraphStyle('banner', alignment=1, leading=16)
    )
    t_banner = Table([[banner_p]], colWidths=[500])
    t_banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NAVY),
        ('PADDING', (0,0), (-1,-1), 14),
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))
    story.append(t_banner)
    story.append(Spacer(1, 20))

    story.append(Paragraph("Respectfully submitted,", body_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Munim Qureshi</b><br/>AirSense Project Lead<br/>Beaconhouse International College, Islamabad<br/>July 2026", body_style))
    story.append(Spacer(1, 25))

    # Formal Approval Sign-off Box
    story.append(Paragraph("Approval Sign-Off", h2_style))
    sign_data = [
        [Paragraph("Role", table_header_style), Paragraph("Name", table_header_style), Paragraph("Signature", table_header_style), Paragraph("Date", table_header_style)],
        [Paragraph("<b>Head of Institute</b>", table_cell_bold), Paragraph("Ms. Saba Ahson", table_cell_style), Paragraph("", table_cell_style), Paragraph("", table_cell_style)],
        [Paragraph("<b>Head of CSSE / AI</b>", table_cell_bold), Paragraph("Ms. Sahifa Alam", table_cell_style), Paragraph("", table_cell_style), Paragraph("", table_cell_style)],
        [Paragraph("<b>Project Team Lead</b>", table_cell_bold), Paragraph("Munim Qureshi", table_cell_style), Paragraph("<i>Munim</i>", table_cell_bold), Paragraph("29/07/2026", table_cell_style)]
    ]
    t_sign = Table(sign_data, colWidths=[130, 140, 130, 100])
    t_sign.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, GRAY_BG]),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story.append(t_sign)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated revised proposal PDF without em-dashes: {OUTPUT_PDF}")


if __name__ == "__main__":
    build_proposal_pdf()
