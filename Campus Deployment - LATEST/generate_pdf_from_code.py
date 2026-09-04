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
OUTPUT_PDF = os.path.join(BASE_DIR, r"AirSense_Campus_Proposal_v4.pdf")
IMAGE_DIR = os.path.join(BASE_DIR, "extracted_images")

# Palette matching docx code exactly
NAVY   = colors.HexColor("#1B3A6B")
BLUE   = colors.HexColor("#2E6099")
LBLUE  = colors.HexColor("#EEF4FB")
MBLUE  = colors.HexColor("#D0E4F5")
WHITE  = colors.HexColor("#FFFFFF")
GREY   = colors.HexColor("#6B7280")
BLACK  = colors.HexColor("#111111")
LGREY  = colors.HexColor("#F5F7FA")
GREEN  = colors.HexColor("#1B5E20")
LGREEN = colors.HexColor("#E8F5E9")
TEAL   = colors.HexColor("#0D7B6A")
LTEAL  = colors.HexColor("#E0F2F1")
AMBER  = colors.HexColor("#E65100")
LAMBER = colors.HexColor("#FFF3E0")

BORDER_BLUE = colors.HexColor("#9AB8D4")
BORDER_GRAY = colors.HexColor("#D0D9E8")

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to add headers and footers with total page count.
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
            # Top accent bar on cover page
            self.setFillColor(NAVY)
            self.rect(0, 841.89 - 16, 595.27, 16, fill=1, stroke=0)
            return

        self.saveState()
        self.setFont("Helvetica-Bold", 8.5)
        self.setFillColor(NAVY)

        # Header (y = 812)
        self.drawString(40, 812, "AirSense | Campus Pilot Proposal | COIL AI Initiative")
        self.setFont("Helvetica", 8.5)
        self.setFillColor(GREY)
        self.drawRightString(595.27 - 40, 812, "BIC Islamabad x BIC Karachi | July 2026")
        self.setStrokeColor(BLUE)
        self.setLineWidth(0.75)
        self.line(40, 804, 595.27 - 40, 804)

        # Footer (y = 30)
        self.setStrokeColor(BLUE)
        self.line(40, 42, 595.27 - 40, 42)
        self.drawString(40, 28, "Confidential | For Management Review Only")
        self.drawRightString(595.27 - 40, 28, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def build_proposal_v4_pdf():
    os.makedirs(os.path.dirname(OUTPUT_PDF), exist_ok=True)

    doc = SimpleDocTemplate(
        OUTPUT_PDF,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=48,
        bottomMargin=48
    )

    styles = getSampleStyleSheet()

    # Custom styles corresponding to docx script
    cover_title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=42,
        leading=46,
        textColor=NAVY,
        alignment=1,
        spaceAfter=4
    )
    cover_sub_style = ParagraphStyle(
        'CoverSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=18,
        leading=22,
        textColor=BLUE,
        alignment=1,
        spaceAfter=15
    )
    cover_h2_style = ParagraphStyle(
        'CoverH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=NAVY,
        alignment=1,
        spaceAfter=4
    )
    cover_tag_style = ParagraphStyle(
        'CoverTagline',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=10.5,
        leading=14,
        textColor=GREY,
        alignment=1,
        spaceAfter=20
    )

    h1_style = ParagraphStyle(
        'H1_Docx',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=NAVY,
        spaceBefore=16,
        spaceAfter=6,
        keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'H2_Docx',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=BLUE,
        spaceBefore=12,
        spaceAfter=4,
        keepWithNext=True
    )
    h3_style = ParagraphStyle(
        'H3_Docx',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=TEAL,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Docx',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=BLACK,
        alignment=4, # Justified
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet_Docx',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9.5,
        leading=13.5,
        textColor=NAVY
    )
    convince_style = ParagraphStyle(
        'ConvinceText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13.5,
        textColor=GREEN
    )

    table_h_style = ParagraphStyle(
        'TableH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=WHITE,
        alignment=1
    )
    table_c_style = ParagraphStyle(
        'TableC',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=BLACK
    )
    table_c_bold = ParagraphStyle(
        'TableCBold',
        parent=table_c_style,
        fontName='Helvetica-Bold'
    )
    table_sh_style = ParagraphStyle(
        'TableSH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        textColor=NAVY,
        alignment=1
    )

    story = []

    # -------------------------------------------------------------------------
    # COVER PAGE
    # -------------------------------------------------------------------------
    story.append(Spacer(1, 0.8 * inch))
    story.append(Paragraph("AirSense", cover_title_style))
    story.append(Paragraph("BIC Islamabad  x  BIC Karachi", cover_sub_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLUE, spaceAfter=20, spaceBefore=4))
    
    story.append(Paragraph("An IoT and Artificial Intelligence Initiative for Real-Time Air Quality Monitoring,", cover_h2_style))
    story.append(Paragraph("Intelligent Forecasting and Operational Decision Support", cover_h2_style))
    story.append(Paragraph("Developed during COIL AI  |  A Strategic Investment for BIC Campuses", cover_tag_style))
    story.append(Spacer(1, 0.25 * inch))

    # Submitted To Table
    sub_to_p = Paragraph(
        "<b><font size=8.5 color='#6B7280'>SUBMITTED TO</font></b><br/><br/>"
        "<b><font size=11 color='#1B3A6B'>Ms. Saba Ahson</font></b><br/>"
        "<font size=9.5 color='#6B7280'>Head of Institute  |  Beaconhouse International College</font><br/><br/>"
        "<b><font size=11 color='#1B3A6B'>Ms. Sahifa Alam</font></b><br/>"
        "<font size=9.5 color='#6B7280'>Head of CSSE / AI Department  |  Beaconhouse International College, Islamabad</font><br/><br/>"
        "<b><font size=11 color='#1B3A6B'>Mr. Sajid</font></b><br/>"
        "<font size=9.5 color='#6B7280'>Head of CSSE / AI Department  |  Beaconhouse International College, Karachi</font>",
        ParagraphStyle('SubToText', parent=body_style, alignment=1, leading=14)
    )
    t_sub_to = Table([[sub_to_p]], colWidths=[480])
    t_sub_to.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LBLUE),
        ('LINEABOVE', (0,0), (-1,-1), 1.5, NAVY),
        ('LINEBELOW', (0,0), (-1,-1), 1.5, NAVY),
        ('PADDING', (0,0), (-1,-1), 12),
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))
    story.append(t_sub_to)
    story.append(Spacer(1, 0.2 * inch))

    # Submitted By Table
    sub_by_p = Paragraph(
        "<b><font size=8.5 color='#6B7280'>SUBMITTED BY</font></b><br/><br/>"
        "<b><font size=11 color='#1B3A6B'>Munim Qureshi</font></b><br/>"
        "<font size=9.5 color='#6B7280'>Project Lead  |  BIC Islamabad Campus</font><br/><br/>"
        "<b><font size=11 color='#1B3A6B'>Areesha Aqeel</font></b><br/>"
        "<font size=9.5 color='#6B7280'>Project Lead  |  BIC Karachi Campus</font><br/><br/>"
        "<b><font size=10 color='#1B3A6B'>Hiba Safdar  |  M. Abbas  |  M. Bilal Ahmed  |  Komal Alishba</font></b><br/>"
        "<i><font size=9 color='#6B7280'>AirSense Development Team  |  Beaconhouse International College</font></i>",
        ParagraphStyle('SubByText', parent=body_style, alignment=1, leading=14)
    )
    t_sub_by = Table([[sub_by_p]], colWidths=[480])
    t_sub_by.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LGREY),
        ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor("#CCCCCC")),
        ('PADDING', (0,0), (-1,-1), 10),
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))
    story.append(t_sub_by)
    story.append(Spacer(1, 0.4 * inch))

    story.append(Paragraph("<font color='#6B7280'>July 2026<br/><i>CONFIDENTIAL  |  FOR INSTITUTIONAL REVIEW ONLY</i></font>", ParagraphStyle('CoverFootText', parent=body_style, alignment=1, fontSize=9)))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # MAIN BODY: STATS BAR & EXECUTIVE SUMMARY
    # -------------------------------------------------------------------------
    # Stats Bar Table
    sb1 = Paragraph("<font size=16 color='white'><b>PKR 20,000</b></font><br/><font size=8 color='white'>One-Time Investment</font>", ParagraphStyle('sb1', alignment=1, leading=16))
    sb2 = Paragraph("<font size=16 color='#1B3A6B'><b>2 BIC Campuses</b></font><br/><font size=8 color='#1B3A6B'>Islamabad + Karachi</font>", ParagraphStyle('sb2', alignment=1, leading=16))
    sb3 = Paragraph("<font size=16 color='#1B5E20'><b>Live Public Dashboard</b></font><br/><font size=8 color='#1B5E20'>BIC-Branded Online</font>", ParagraphStyle('sb3', alignment=1, leading=16))
    sb4 = Paragraph("<font size=16 color='#1B3A6B'><b>COIL AI</b></font><br/><font size=8 color='#1B3A6B'>Internationally Recognised Origin</font>", ParagraphStyle('sb4', alignment=1, leading=16))

    stats_table = Table([[sb1, sb2, sb3, sb4]], colWidths=[125, 125, 125, 125])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), NAVY),
        ('BACKGROUND', (1,0), (1,0), MBLUE),
        ('BACKGROUND', (2,0), (2,0), LGREEN),
        ('BACKGROUND', (3,0), (3,0), LBLUE),
        ('BOX', (0,0), (0,0), 1, NAVY),
        ('BOX', (1,0), (1,0), 1, MBLUE),
        ('BOX', (2,0), (2,0), 1, LGREEN),
        ('BOX', (3,0), (3,0), 1, LBLUE),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 10))

    # Section 1: Executive Summary
    story.append(Paragraph("1.  Executive Summary", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=8, spaceBefore=2))

    story.append(Paragraph("We are presenting a highly scalable business and technological asset for Beaconhouse International College. AirSense is a fully developed, AI-powered air quality intelligence platform, designed and built by BIC students during the prestigious COIL AI international academic programme. The foundational architecture, machine learning pipeline, and digital dashboards are already complete. We are now seeking a minimal seed investment to execute the physical IoT deployment on campus.", body_style))
    story.append(Paragraph("This proposal requests a one-time capital allocation of PKR 20,000 to fund the physical deployment of a rooftop IoT sensor unit at BIC Islamabad, matched by a parallel deployment at BIC Karachi. These interconnected nodes will form a dual-campus data network, providing live environmental intelligence that directly informs campus operational decisions. The data captured will continuously train our existing in-house machine learning models, customising them for BIC's specific microclimates.", body_style))
    story.append(Paragraph("By deploying AirSense, BIC achieves immediate ROI through operational efficiency, student health protection, and powerful public relations. The resulting live dashboard will be publicly accessible, permanently associating the Beaconhouse International College brand with applied AI innovation.", body_style))

    # Convince callout
    conv_1 = Paragraph("An investment of PKR 20,000 delivers a live, dual-campus AI network and a public dashboard showcasing BIC's technological leadership. The institute does not just fund a student project; it acquires a scalable institutional asset.", convince_style)
    t_conv_1 = Table([[conv_1]], colWidths=[500])
    t_conv_1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LGREEN),
        ('LINELEFT', (0,0), (-1,-1), 4, GREEN),
        ('PADDING', (0,0), (-1,-1), 8)
    ]))
    story.append(t_conv_1)
    story.append(Spacer(1, 8))


    # Section 2: Strategic Origins
    story.append(Paragraph("2.  Strategic Origins & Institutional Value", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=8, spaceBefore=2))

    story.append(Paragraph("2.1  Developed During COIL AI: A Global Standard", h2_style))
    story.append(Paragraph("AirSense is not a standard classroom assignment. It was conceived and rigorously developed under the COIL AI framework, a structured international academic collaboration. In this highly competitive environment, student teams were evaluated against stringent international standards for commercial and technological viability. AirSense emerged with a validated product identity and a clear market-ready architecture. For BIC, supporting a COIL AI-originated project provides a powerful marketing narrative: our students do not just study AI, they deploy internationally recognised platforms on our own campuses.", body_style))

    story.append(Paragraph("2.2  The Business Case for Real-World IoT Implementation", h2_style))
    story.append(Paragraph("Software simulations hold limited institutional value. The true value of AirSense lies in its physical IoT implementation. By connecting hardware sensors to cloud infrastructure and AI models in a live environment, we transition from theory to a tangible product. A physical deployment proves to future students, parents, and industry partners that BIC provides hands-on, enterprise-grade engineering experience. This IoT infrastructure becomes a living laboratory, driving recruitment and elevating the institution's technological prestige.", body_style))

    story.append(Paragraph("2.3  Solving a Core Operational Problem", h2_style))
    story.append(Paragraph("Air quality is a critical factor in student well-being, particularly in Islamabad and Karachi where PM2.5 levels fluctuate dramatically. Currently, campus administrations make decisions regarding outdoor activities, physical education, and HVAC operations based on delayed or generalised weather apps. AirSense solves this by providing hyper-local, real-time, and predictive data directly to campus management, enabling proactive health and safety decisions that protect students and reassure parents.", body_style))
    
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 3: IOT & PROBLEM WE ARE SOLVING
    # -------------------------------------------------------------------------
    # Section 3: The AirSense Platform
    story.append(Paragraph("3.  The AirSense Platform", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=8, spaceBefore=2))

    story.append(Paragraph("3.1  Operational Decision Making at Scale", h2_style))
    story.append(Paragraph("AirSense is designed for management, not just engineers. It moves beyond raw data display to provide actionable operational intelligence. Through four integrated layers, it translates environmental metrics into plain-language directives, allowing campus leadership to optimise daily operations effortlessly.", body_style))

    # 4-Layer Table
    lay_data = [
        [Paragraph("Layer", table_h_style), Paragraph("Technology", table_h_style), Paragraph("Business & Operational Value", table_h_style)],
        [Paragraph("<b>1. IoT Sensing</b>", table_c_bold), Paragraph("PMS7003 Laser Sensor + BME280 + Rain Sensor + ESP32", table_c_style), Paragraph("Deploys low-cost, high-reliability physical hardware on BIC rooftops, establishing a proprietary institutional data source.", table_c_style)],
        [Paragraph("<b>2. Data Pipeline</b>", table_c_bold), Paragraph("MicroSD Logging + Campus Wi-Fi + Public Weather API", table_c_style), Paragraph("Ensures continuous, redundant data collection. The data itself becomes a valuable institutional asset for future research and PR.", table_c_style)],
        [Paragraph("<b>3. AI Forecasting</b>", table_c_bold), Paragraph("In-House ML Models (XGBoost, Random Forest, LightGBM)", table_c_style), Paragraph("Predicts air quality conditions up to 24 hours in advance, allowing administration to proactively manage schedules rather than reacting to conditions.", table_c_style)],
        [Paragraph("<b>4. Decision Layer</b>", table_c_bold), Paragraph("Operational Playbook + AI Language Model Advisor", table_c_style), Paragraph("Converts complex forecasts into simple, actionable administrative advice (e.g., 'Reschedule outdoor PE to 2:00 PM due to predicted PM2.5 spikes').", table_c_style)]
    ]
    t_lay = Table(lay_data, colWidths=[90, 130, 280])
    t_lay.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LBLUE]),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_lay)
    story.append(Spacer(1, 10))

    story.append(Paragraph("3.2  Training In-House Machine Learning Models", h2_style))
    story.append(Paragraph("A major strategic advantage of this project is that we are not purchasing a third-party software license. We are using existing, in-house ML models developed by our students. The pilot deployment is critical because it allows us to feed live, local BIC data into these existing models, training and fine-tuning them specifically for the Islamabad and Karachi microclimates. The intellectual property, the algorithms, and the resulting insights remain entirely owned by Beaconhouse International College.", body_style))

    conv_2 = Paragraph("By training our existing in-house models on live campus data, BIC builds a proprietary technological asset. We rely on no external vendors; the innovation is 100% homegrown.", convince_style)
    t_conv_2 = Table([[conv_2]], colWidths=[500])
    t_conv_2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LGREEN),
        ('LINELEFT', (0,0), (-1,-1), 4, GREEN),
        ('PADDING', (0,0), (-1,-1), 8)
    ]))
    story.append(t_conv_2)
    story.append(Spacer(1, 10))


    # Section 4: Campus Deployment Plan
    story.append(Paragraph("4.  Campus Deployment Plan", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=8, spaceBefore=2))

    story.append(Paragraph("4.1  Rapid, Low-Risk Implementation", h2_style))
    story.append(Paragraph("The physical deployment is designed for minimal disruption and rapid time-to-value. The hardware is a single weatherproof unit powered by a standard outlet, requiring zero daily maintenance from BIC facilities staff.", body_style))

    # Deployment Table
    dep_data = [
        [Paragraph("Phase", table_h_style), Paragraph("Timeframe", table_h_style), Paragraph("Execution Details", table_h_style)],
        [
            Paragraph("<b>0</b>", table_c_bold),
            Paragraph("Days 1-7", table_c_style),
            Paragraph("<b>Hardware Procurement</b><br/>• Source high-quality, cost-effective components from verified local vendors.<br/>• Total controlled budget constraint: PKR 20,000.", table_c_style)
        ],
        [
            Paragraph("<b>1</b>", table_c_bold),
            Paragraph("Days 6-9", table_c_style),
            Paragraph("<b>Bench Assembly and QA Validation</b><br/>• Complete in-house wiring, SD logging configuration, and firmware flashing.<br/>• Rigorous quality assurance testing before rooftop deployment.", table_c_style)
        ],
        [
            Paragraph("<b>2</b>", table_c_bold),
            Paragraph("Day 9-10", table_c_style),
            Paragraph("<b>Rooftop Installation</b><br/>• Non-invasive mounting on BIC rooftops in Islamabad and Karachi.<br/>• End-to-end telemetry verification. System goes live instantly.", table_c_style)
        ],
        [
            Paragraph("<b>3</b>", table_c_bold),
            Paragraph("Months 1-3", table_c_style),
            Paragraph("<b>Data Collection & Model Training</b><br/>• Autonomous 24/7 dual-channel data logging.<br/>• In-house ML models ingest local campus data for precise calibration.", table_c_style)
        ],
        [
            Paragraph("<b>4</b>", table_c_bold),
            Paragraph("End Month 3", table_c_style),
            Paragraph("<b>Dashboard Launch & Management Handover</b><br/>• Public launch of the live BIC-branded AirSense dashboard.<br/>• Final project report and operational playbook delivered to management.", table_c_style)
        ]
    ]

    t_dep = Table(dep_data, colWidths=[45, 65, 390])
    t_dep.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LBLUE]),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_dep)

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 5: BIC INTER-CAMPUS COLLABORATION & BENEFITS
    # -------------------------------------------------------------------------
    story.append(Paragraph("5.  A Strategic Multi-Campus Collaboration", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=8, spaceBefore=2))

    story.append(Paragraph("5.1  Unified Development Across BIC Islamabad and Karachi", h2_style))
    story.append(Paragraph("AirSense is intrinsically designed as a scalable, multi-campus network. The project is led jointly by Munim Qureshi (Islamabad) and Areesha Aqeel (Karachi). Under the supervision of Ms. Sahifa Alam and Mr. Sajid, both campuses will collaboratively deploy identical hardware stacks, feed into a unified cloud architecture, and co-develop the AI models. This cross-city integration transforms a local initiative into a robust institutional framework.", body_style))
    
    # Side by side table
    collab_data = [
        [Paragraph("BIC Islamabad", table_sh_style), Paragraph("BIC Karachi", table_sh_style)],
        [
            Paragraph("<b>Supervisor: Ms. Sahifa Alam</b><br/>Head of CSSE / AI Department<br/><br/><b>Project Lead: Munim Qureshi</b><br/><br/>• Focus on inland microclimate analytics.<br/>• Joint hardware and firmware development.<br/>• Centralised model training coordination.", table_c_style),
            Paragraph("<b>Supervisor: Mr. Sajid</b><br/>Head of CSSE / AI Department<br/><br/><b>Project Lead: Areesha Aqeel</b><br/><br/>• Focus on coastal climate and high-humidity dispersion.<br/>• Parallel hardware deployment and data validation.<br/>• Cross-campus knowledge transfer.", table_c_style)
        ]
    ]
    t_collab = Table(collab_data, colWidths=[245, 255])
    t_collab.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), MBLUE),
        ('BACKGROUND', (1,0), (1,0), LGREEN),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_BLUE),
        ('BACKGROUND', (0,1), (0,1), LBLUE),
        ('BACKGROUND', (1,1), (1,1), LGREEN),
        ('PADDING', (0,0), (-1,-1), 7),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_collab)
    story.append(Spacer(1, 10))

    story.append(Paragraph("5.2  Expanding Together", h2_style))
    story.append(Paragraph("This collaboration establishes a blueprint for institutional expansion. As we prove the model in Islamabad and Karachi, we have the infrastructure in place to seamlessly integrate future campuses into the network, creating a unified Beaconhouse environmental intelligence grid.", body_style))

    conv_3 = Paragraph("This dual-campus approach signifies institutional unity and technological ambition. We are building a scalable framework where multiple campuses innovate together, share data, and collectively elevate the BIC brand.", convince_style)
    t_conv_3 = Table([[conv_3]], colWidths=[500])
    t_conv_3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LGREEN),
        ('LINELEFT', (0,0), (-1,-1), 4, GREEN),
        ('PADDING', (0,0), (-1,-1), 8)
    ]))
    story.append(t_conv_3)
    story.append(Spacer(1, 10))

    # Section 6: Benefits to BIC
    story.append(Paragraph("6.  The Direct Business Benefits to BIC", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=8, spaceBefore=2))

    story.append(Paragraph("6.1  A Publicly Available, Branded Dashboard", h2_style))
    story.append(Paragraph("A cornerstone of this proposal is the deployment of a publicly accessible, beautifully designed digital dashboard. Live environmental data and AI forecasts will be broadcast globally under the BIC banner. This acts as a perpetual marketing asset, demonstrating to parents, prospective students, and industry observers that BIC operates at the cutting edge of applied technology.", body_style))

    story.append(Paragraph("6.2  Institutional Value Summary", h2_style))
    ben_data = [
        [Paragraph("Value Proposition", table_h_style), Paragraph("Strategic Benefit to BIC", table_h_style)],
        [Paragraph("<b>Duty of Care & Health</b>", table_c_bold), Paragraph("Enables data-driven, proactive decisions for student outdoor activities, mitigating health risks and liability.", table_c_style)],
        [Paragraph("<b>Public Relations & Brand</b>", table_c_bold), Paragraph("The public dashboard serves as a continuous, high-visibility showcase of BIC's commitment to student innovation and community welfare.", table_c_style)],
        [Paragraph("<b>Proprietary AI Ownership</b>", table_c_bold), Paragraph("In-house ML models, calibrated exclusively with BIC campus data, remain the intellectual property of the institution. Zero licensing fees.", table_c_style)],
        [Paragraph("<b>COIL AI Validation</b>", table_c_bold), Paragraph("Leverages the prestige of a global academic programme to validate the quality and rigor of BIC's technology curriculum.", table_c_style)],
        [Paragraph("<b>Cross-Campus Unity</b>", table_c_bold), Paragraph("Fosters high-level, inter-city collaboration between Islamabad and Karachi, strengthening the national institutional network.", table_c_style)]
    ]
    t_ben = Table(ben_data, colWidths=[130, 370])
    t_ben.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LBLUE]),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_ben)

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 6: DASHBOARD OVERVIEW & SCREENSHOTS
    # -------------------------------------------------------------------------
    story.append(Paragraph("7.  Public Dashboard Preview", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=8, spaceBefore=2))
    story.append(Paragraph("The publicly available dashboard is the commercial and marketing face of the platform. It provides a sleek, enterprise-grade interface that reflects positively on the institution while delivering critical operational intelligence.", body_style))

    story.append(Paragraph("7.1  Executive Overview & Dual-Campus Monitoring", h3_style))
    story.append(Paragraph("Displays synchronised, real-time AQI and predictive trends for both BIC Islamabad and BIC Karachi simultaneously.", body_style))

    img_8_1_path = os.path.join(IMAGE_DIR, "page_8_img_1.jpeg")
    img_8_2_path = os.path.join(IMAGE_DIR, "page_8_img_2.jpeg")

    if os.path.exists(img_8_1_path):
        story.append(RLImage(img_8_1_path, width=6.8*inch, height=3.0*inch))
        story.append(Paragraph("<font size=8 color='#6B7280'><i>Figure 7.1a: The live, public-facing interface displaying real-time metrics and predictive risk.</i></font>", ParagraphStyle('cap1', alignment=1)))
        story.append(Spacer(1, 8))

    story.append(Paragraph("7.2  Predictive Policy Tracker", h3_style))
    if os.path.exists(img_8_2_path):
        story.append(RLImage(img_8_2_path, width=6.8*inch, height=3.0*inch))
        story.append(Paragraph("<font size=8 color='#6B7280'><i>Figure 7.1b: Predictive tracker translating data into actionable campus policy directives.</i></font>", ParagraphStyle('cap2', alignment=1)))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 7: AI DECISION ADVISOR & HEALTH RISK PANEL
    # -------------------------------------------------------------------------
    story.append(Paragraph("7.3  AI Administrative Advisor", h3_style))
    story.append(Paragraph("A direct interface for campus management to query the AI in plain language and receive immediate operational recommendations.", body_style))

    img_9_1_path = os.path.join(IMAGE_DIR, "page_9_img_1.jpeg")
    img_9_2_path = os.path.join(IMAGE_DIR, "page_9_img_2.jpeg")

    if os.path.exists(img_9_1_path):
        story.append(RLImage(img_9_1_path, width=6.8*inch, height=2.6*inch))
        story.append(Paragraph("<font size=8 color='#6B7280'><i>Figure 7.3: Natural-language Decision Advisor streamlining administrative workflows.</i></font>", ParagraphStyle('cap3', alignment=1)))
        story.append(Spacer(1, 8))

    story.append(Paragraph("7.4  Health Risk & Dispatch Calculator", h3_style))
    if os.path.exists(img_9_2_path):
        story.append(RLImage(img_9_2_path, width=6.8*inch, height=3.0*inch))
        story.append(Paragraph("<font size=8 color='#6B7280'><i>Figure 7.4: Automated calculator identifying optimal time windows for outdoor campus activities.</i></font>", ParagraphStyle('cap4', alignment=1)))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 8: OPERATIONAL DECISIONS & EXPANSION
    # -------------------------------------------------------------------------
    story.append(Paragraph("8.  Commercial Scope and Market Offerings", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=8, spaceBefore=2))

    story.append(Paragraph("8.1  B2B Operational Decision Making", h2_style))
    story.append(Paragraph("While currently tailored for BIC, AirSense is fundamentally an enterprise decision-support tool. It is architected to scale into a lucrative B2B offering, providing risk-mitigation data across multiple high-exposure industries.", body_style))

    sec_data = [
        [Paragraph("Target Market", table_h_style), Paragraph("The Business Problem", table_h_style), Paragraph("The AirSense SaaS Solution", table_h_style)],
        [Paragraph("<b>Education Sector</b>", table_c_bold), Paragraph("Liability surrounding student health during smog seasons.", table_c_style), Paragraph("Automated PE scheduling, HVAC optimization, and parental reassurance dashboards.", table_c_style)],
        [Paragraph("<b>Logistics & Fleet</b>", table_c_bold), Paragraph("Driver health risks and delayed morning dispatches due to visibility.", table_c_style), Paragraph("Predictive route scheduling and shift allocation based on exposure forecasts.", table_c_style)],
        [Paragraph("<b>Construction</b>", table_c_bold), Paragraph("Regulatory fines for dust generation; worker safety compliance.", table_c_style), Paragraph("Targeted wet suppression alerts and automated ESG compliance reporting.", table_c_style)],
        [Paragraph("<b>Corporate ESG</b>", table_c_bold), Paragraph("Mandates to demonstrate environmental responsibility and employee welfare.", table_c_style), Paragraph("Automated environmental audit trails and branded sustainability metrics.", table_c_style)]
    ]
    t_sec = Table(sec_data, colWidths=[110, 140, 250])
    t_sec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LBLUE]),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_sec)
    story.append(Spacer(1, 10))

    story.append(Paragraph("8.2  Future Commercialization Strategy", h2_style))
    story.append(Paragraph("The successful execution of the BIC pilot serves as a powerful proof-of-concept for external commercialization. By owning the underlying intellectual property and the initial deployment case study, BIC positions itself at the forefront of a potential SaaS spin-off. We can subsequently offer this platform to external corporate campuses and industrial partners via a subscription model.", body_style))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 9: PHASE ROADMAP & BUDGET
    # -------------------------------------------------------------------------
    story.append(Paragraph("9.  Strategic Growth Roadmap", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=8, spaceBefore=2))

    road_data = [
        [Paragraph("Phase", table_h_style), Paragraph("Strategic Stage", table_h_style), Paragraph("Execution Focus", table_h_style), Paragraph("Business Outcome for BIC", table_h_style)],
        [
            Paragraph("<b>1</b>", table_c_bold),
            Paragraph("Dual-Campus Pilot (Current Request)", table_c_bold),
            Paragraph("Deploy hardware at BIC Islamabad & Karachi. Train existing models on live, local data.", table_c_style),
            Paragraph("Proprietary dataset, publicly available dashboard, validated operational use-case.", table_c_style)
        ],
        [
            Paragraph("<b>2</b>", table_c_bold),
            Paragraph("Model Refinement & Institutional Integration", table_c_bold),
            Paragraph("Fine-tune AI accuracy. Integrate insights directly into campus administration workflows.", table_c_style),
            Paragraph("Demonstrable ROI through health risk mitigation and operational efficiency.", table_c_style)
        ],
        [
            Paragraph("<b>3</b>", table_c_bold),
            Paragraph("Commercial SaaS Spin-off", table_c_bold),
            Paragraph("Package the platform as a subscription service targeting logistics, construction, and corporate sectors.", table_c_style),
            Paragraph("Potential revenue generation; elevated brand prestige as a tech incubator.", table_c_style)
        ]
    ]
    t_road = Table(road_data, colWidths=[35, 105, 200, 160])
    t_road.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LBLUE]),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_road)
    story.append(Spacer(1, 10))

    # Section 10: Budget Request
    story.append(Paragraph("10.  Budget Request: PKR 20,000", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=8, spaceBefore=2))

    story.append(Paragraph("10.1  A Low-Risk, High-Return Investment", h2_style))
    story.append(Paragraph("This is a highly structured, one-time capital request. Software development costs have already been absorbed by the student teams. This budget covers strictly the physical IoT hardware components necessary to bring the platform into the real world.", body_style))

    # Budget Table
    bud_data = [
        [Paragraph("#", table_h_style), Paragraph("Component", table_h_style), Paragraph("Vendor", table_h_style), Paragraph("Qty", table_h_style), Paragraph("Cost (PKR)", table_h_style)],
        [Paragraph("1", table_c_bold), Paragraph("PMS7003 Laser Dust Sensor", table_c_style), Paragraph("Embeded Studio", table_c_style), Paragraph("1", table_c_style), Paragraph("4,200", table_c_bold)],
        [Paragraph("2", table_c_bold), Paragraph("ESP32 WROOM-32D Board", table_c_style), Paragraph("Digilog.pk", table_c_style), Paragraph("1", table_c_style), Paragraph("1,160", table_c_bold)],
        [Paragraph("3", table_c_bold), Paragraph("BME280 Temp/Humidity/Pressure Sensor", table_c_style), Paragraph("Electrobes", table_c_style), Paragraph("1", table_c_style), Paragraph("850", table_c_bold)],
        [Paragraph("4", table_c_bold), Paragraph("Arduino MicroSD Module", table_c_style), Paragraph("Electrobes", table_c_style), Paragraph("1", table_c_style), Paragraph("150", table_c_style)],
        [Paragraph("5", table_c_bold), Paragraph("Samsung 16GB MicroSD Card", table_c_style), Paragraph("Daraz.pk", table_c_style), Paragraph("1", table_c_style), Paragraph("1,450", table_c_style)],
        [Paragraph("6", table_c_bold), Paragraph("IP65 Waterproof Enclosure", table_c_style), Paragraph("A.E Solution", table_c_style), Paragraph("1", table_c_style), Paragraph("750", table_c_style)],
        [Paragraph("7", table_c_bold), Paragraph("Jumper Wire Kit, 120 pcs", table_c_style), Paragraph("Daraz.pk", table_c_style), Paragraph("1", table_c_style), Paragraph("440", table_c_style)],
        [Paragraph("8", table_c_bold), Paragraph("5V 2A AC/DC Power Adapter", table_c_style), Paragraph("Electronics Hub", table_c_style), Paragraph("1", table_c_style), Paragraph("170", table_c_style)],
        [Paragraph("9", table_c_bold), Paragraph("Cable Ties, 100-pack", table_c_style), Paragraph("Daraz.pk", table_c_style), Paragraph("1", table_c_style), Paragraph("120", table_c_style)],
        [Paragraph("10", table_c_bold), Paragraph("Stainless Hose Clamps (2 pcs)", table_c_style), Paragraph("DreamsMart.pk", table_c_style), Paragraph("1", table_c_style), Paragraph("60", table_c_style)],
        [Paragraph("11", table_c_bold), Paragraph("Raindrop Sensor Module A", table_c_style), Paragraph("Digilog.pk", table_c_style), Paragraph("1", table_c_style), Paragraph("160", table_c_style)],
        [Paragraph("12", table_c_bold), Paragraph("Rain Drop Moisture Sensor Module B", table_c_style), Paragraph("Electrobes", table_c_style), Paragraph("1", table_c_style), Paragraph("150", table_c_style)],
        [Paragraph("13", table_c_bold), Paragraph("UNI-T UT363 Digital Anemometer", table_c_style), Paragraph("Electrobes", table_c_style), Paragraph("1", table_c_style), Paragraph("4,250", table_c_style)],
        [Paragraph("14", table_c_bold), Paragraph("Clopal 10m Heavy-Duty Lead", table_c_style), Paragraph("Clopal Online", table_c_style), Paragraph("1", table_c_style), Paragraph("3,295", table_c_style)],
        [Paragraph("15", table_c_bold), Paragraph("GMSA RTV Weatherproof Sealant", table_c_style), Paragraph("Expert Tools", table_c_style), Paragraph("1", table_c_style), Paragraph("390", table_c_style)],
        [Paragraph("16", table_c_bold), Paragraph("Mounting Nuts & Bolts (8 pcs)", table_c_style), Paragraph("Multan Elec.", table_c_style), Paragraph("8", table_c_style), Paragraph("192", table_c_style)],
        [Paragraph("17", table_c_bold), Paragraph("Radiation Shield (Local Sourcing)", table_c_style), Paragraph("Local Supplier", table_c_style), Paragraph("1", table_c_style), Paragraph("TBD", table_c_style)],
        [Paragraph("", table_c_bold), Paragraph("<b>Hardware Subtotal (Items 1-16)</b>", table_c_bold), Paragraph("", table_c_style), Paragraph("", table_c_style), Paragraph("<b>PKR 17,787</b>", table_c_bold)],
        [Paragraph("", table_c_bold), Paragraph("<b>Radiation Shield + Contingency Buffer</b>", table_c_bold), Paragraph("", table_c_style), Paragraph("", table_c_style), Paragraph("<b>PKR 2,213</b>", table_c_bold)],
        [Paragraph("", table_c_bold), Paragraph("<font size=9 color='white'><b>TOTAL REQUESTED BUDGET</b></font>", table_c_bold), Paragraph("", table_c_style), Paragraph("", table_c_style), Paragraph("<font size=9 color='white'><b>PKR 20,000</b></font>", table_c_bold)]
    ]
    t_bud = Table(bud_data, colWidths=[25, 235, 120, 35, 85])
    t_bud.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('PADDING', (0,0), (-1,-1), 3.5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (3,0), (4,-1), 'CENTER'),
        ('BACKGROUND', (0,-3), (-1,-3), MBLUE),
        ('BACKGROUND', (0,-2), (-1,-2), LGREEN),
        ('BACKGROUND', (0,-1), (-1,-1), NAVY)
    ]))
    story.append(t_bud)

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 10: DELIVERABLES & CONCLUSION & SIGN-OFF
    # -------------------------------------------------------------------------
    story.append(Paragraph("11.  Guaranteed Deliverables", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=8, spaceBefore=2))

    del_data = [
        [Paragraph("No.", table_h_style), Paragraph("Asset Delivered", table_h_style), Paragraph("Strategic Impact", table_h_style)],
        [Paragraph("<b>1</b>", table_c_bold), Paragraph("<b>Live Public Dashboard</b>", table_c_bold), Paragraph("A permanently available, highly visible online asset enhancing the BIC brand.", table_c_style)],
        [Paragraph("<b>2</b>", table_c_bold), Paragraph("<b>Retrained In-House AI Models</b>", table_c_bold), Paragraph("Proprietary intellectual property, tuned specifically to BIC environments.", table_c_style)],
        [Paragraph("<b>3</b>", table_c_bold), Paragraph("<b>Actionable Data Feeds</b>", table_c_bold), Paragraph("Continuous real-time insights empowering safer campus management.", table_c_style)],
        [Paragraph("<b>4</b>", table_c_bold), Paragraph("<b>Commercial Proof of Concept</b>", table_c_bold), Paragraph("A validated case study paving the way for B2B SaaS offerings.", table_c_style)]
    ]
    t_del = Table(del_data, colWidths=[30, 160, 310])
    t_del.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LBLUE]),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_del)
    story.append(Spacer(1, 10))

    # Section 12: Why BIC Should Say Yes
    story.append(Paragraph("12.  Approval Request", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=8, spaceBefore=2))

    story.append(Paragraph("A PKR 20,000 investment transforms a theoretical academic exercise into a live, scalable technology asset. We are offering BIC the opportunity to claim ownership of an internationally recognised, multi-campus AI platform.", body_style))

    # Conviction Banner
    conv_p = Paragraph(
        "<font size=11 color='white'><b>This is an asymmetric opportunity for BIC.<br/>"
        "The software is built. The team is aligned. The global COIL AI recognition is secured.<br/>"
        "We simply need the seed capital to bring the hardware online.<br/>"
        "Approve this PKR 20,000 budget, and we will deliver a platform that redefines student innovation.</b></font>",
        ParagraphStyle('conv_p', alignment=1, leading=15)
    )
    t_conv_banner = Table([[conv_p]], colWidths=[500])
    t_conv_banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NAVY),
        ('PADDING', (0,0), (-1,-1), 12),
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))
    story.append(t_conv_banner)
    story.append(Spacer(1, 10))

    story.append(Paragraph("The project leadership respectfully requests approval for:", body_style))
    req_data = [
        [Paragraph("<b>1</b>", table_c_bold), Paragraph("Allocation of a one-time hardware budget of <b>PKR 20,000</b>.", table_c_style)],
        [Paragraph("<b>2</b>", table_c_bold), Paragraph("Authorization to deploy the weatherproofed sensor nodes on BIC Islamabad and BIC Karachi rooftops.", table_c_style)],
        [Paragraph("<b>3</b>", table_c_bold), Paragraph("Official institutional backing to proceed with the dual-campus pilot.", table_c_style)]
    ]
    t_req = Table(req_data, colWidths=[30, 470])
    t_req.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('BACKGROUND', (0,0), (-1,-1), LBLUE),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story.append(t_req)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Respectfully submitted,", body_style))
    story.append(Paragraph("<b>Munim Qureshi</b> (Project Lead | BIC Islamabad Campus)", body_style))
    story.append(Paragraph("<b>Areesha Aqeel</b> (Project Lead | BIC Karachi Campus)", body_style))
    story.append(Paragraph("<b>Hiba Safdar | M. Abbas | M. Bilal Ahmed | Komal Alishba</b> (Development Team)", body_style))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Executive Sign-Off", h2_style))
    sign_data = [
        [Paragraph("Role", table_h_style), Paragraph("Name", table_h_style), Paragraph("Signature", table_h_style), Paragraph("Date", table_h_style)],
        [Paragraph("<b>Head of Institute, BIC</b>", table_c_bold), Paragraph("Ms. Saba Ahson", table_c_style), Paragraph("", table_c_style), Paragraph("", table_c_style)],
        [Paragraph("<b>Head of CSSE/AI, BIC Islamabad</b>", table_c_bold), Paragraph("Ms. Sahifa Alam", table_c_style), Paragraph("", table_c_style), Paragraph("", table_c_style)],
        [Paragraph("<b>Head of CSSE/AI, BIC Karachi</b>", table_c_bold), Paragraph("Mr. Sajid", table_c_style), Paragraph("", table_c_style), Paragraph("", table_c_style)],
        [Paragraph("<b>Project Lead, Islamabad</b>", table_c_bold), Paragraph("Munim Qureshi", table_c_style), Paragraph("<i>Munim</i>", table_c_bold), Paragraph("29/07/2026", table_c_style)],
        [Paragraph("<b>Project Lead, Karachi</b>", table_c_bold), Paragraph("Areesha Aqeel", table_c_style), Paragraph("<i>Areesha</i>", table_c_bold), Paragraph("29/07/2026", table_c_style)]
    ]
    t_sign = Table(sign_data, colWidths=[130, 140, 130, 100])
    t_sign.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LBLUE]),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story.append(t_sign)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated proposal v4 PDF: {OUTPUT_PDF}")


if __name__ == "__main__":
    build_proposal_v4_pdf()
