import os
import fitz
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable, ListFlowable, ListItem
)
from reportlab.pdfgen import canvas

BASE_DIR = r"d:\MUNIM - UOE @BIC\AirSense\Campus Deployment - LATEST"
OUTPUT_PDF = os.path.join(BASE_DIR, r"AirSense_Campus_Proposal_v5.pdf")

# Palette
NAVY = colors.HexColor("#1F3864")
TEAL = colors.HexColor("#0F6B72")
GREY = colors.HexColor("#595959")
LIGHT = colors.HexColor("#EAF0F8")
SHADE_ALT = colors.HexColor("#F5F7FA")
WHITE = colors.HexColor("#FFFFFF")
BUDGET_TOTAL = colors.HexColor("#D9E2F3")
BORDER_GREY = colors.HexColor("#BFBFBF")

class NumberedCanvas(canvas.Canvas):
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
        # The cover page in the JS code has its own section with no header/footer.
        if self._pageNumber == 1:
            return

        self.saveState()
        
        # Header
        self.setFont("Helvetica-Oblique", 8)  # italics, size 16 in twips -> 8pt
        self.setFillColor(GREY)
        self.drawRightString(595.27 - 40, 812, "AirSense  |  Campus Pilot Proposal")
        self.setStrokeColor(BORDER_GREY)
        self.setLineWidth(0.5)
        self.line(40, 804, 595.27 - 40, 804)

        # Footer
        self.setFont("Helvetica", 8)
        self.setFillColor(GREY)
        self.drawCentredString(595.27 / 2, 30, f"Page {self._pageNumber} of {page_count}")
        
        self.restoreState()

def build_pdf():
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
    
    # Text sizes in JS are in half-points. So size 26 -> 13pt. size 21 -> 10.5pt. size 64 -> 32pt. size 28 -> 14pt. size 20 -> 10pt. size 18 -> 9pt. size 16 -> 8pt. size 22 -> 11pt.
    
    cover_title = ParagraphStyle('CoverTitle', fontName='Helvetica-Bold', fontSize=32, leading=38, textColor=NAVY, alignment=1)
    cover_subtitle = ParagraphStyle('CoverSub', fontName='Helvetica-Bold', fontSize=14, leading=18, textColor=TEAL, alignment=1)
    cover_tagline = ParagraphStyle('CoverTag', fontName='Helvetica-Oblique', fontSize=10, leading=14, textColor=GREY, alignment=1)
    cover_heading = ParagraphStyle('CoverHeading', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=GREY, alignment=1)
    cover_line_name = ParagraphStyle('CoverLineName', fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=NAVY, alignment=1)
    cover_date = ParagraphStyle('CoverDate', fontName='Helvetica', fontSize=10, leading=14, textColor=GREY, alignment=1)
    cover_conf = ParagraphStyle('CoverConf', fontName='Helvetica', fontSize=8, leading=10, textColor=GREY, alignment=1)

    h1_style = ParagraphStyle('H1', fontName='Helvetica-Bold', fontSize=13, leading=16, textColor=NAVY, spaceBefore=18, spaceAfter=8)
    body_style = ParagraphStyle('Body', fontName='Helvetica', fontSize=10.5, leading=14, textColor=colors.black, alignment=4, spaceAfter=8)
    bullet_style = ParagraphStyle('Bullet', fontName='Helvetica', fontSize=10.5, leading=14, textColor=colors.black, spaceAfter=4, leftIndent=15, firstLineIndent=-10)
    
    table_header = ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=10, leading=12, textColor=WHITE)
    table_body = ParagraphStyle('TB', fontName='Helvetica', fontSize=10, leading=12, textColor=colors.black)
    
    def coverLine(name, role):
        # em-dash is avoided. We use ' - '
        return Paragraph(f"<b><font size=11 color='#1F3864'>{name}</font></b>  -  <font size=10 color='#595959'>{role}</font>", ParagraphStyle('cl', alignment=1))

    story = []
    
    # Cover Page
    story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY, spaceBefore=0, spaceAfter=20))
    story.append(Spacer(1, 30))
    story.append(Paragraph("AirSense", cover_title))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Campus Air Quality Intelligence Pilot", cover_subtitle))
    story.append(Spacer(1, 20))
    story.append(Paragraph("A joint initiative of BIC Islamabad and BIC Karachi, developed through the BIC x University of Essex COIL AI Hackathon", cover_tagline))
    story.append(Spacer(1, 10))
    
    # Light shaded block
    story.append(Table([[Paragraph(" ", cover_heading)]], colWidths=[515], style=TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT),
        ('LINEABOVE', (0,0), (-1,-1), 1, NAVY),
        ('LINEBELOW', (0,0), (-1,-1), 1, NAVY),
        ('PADDING', (0,0), (-1,-1), 5),
    ])))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("SUBMITTED TO", cover_heading))
    story.append(Spacer(1, 5))
    story.append(coverLine("Ms. Saba Ahson", "Head of Institute, BIC Islamabad"))
    story.append(Spacer(1, 5))
    story.append(coverLine("Ms. Sahifa Alam", "Head of CSSE / AI, BIC Islamabad"))
    story.append(Spacer(1, 5))
    story.append(coverLine("Mr. Sajid", "Head of CSSE / AI, BIC Karachi"))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("SUBMITTED BY", cover_heading))
    story.append(Spacer(1, 5))
    story.append(coverLine("Munim Qureshi", "Project Lead, BIC Islamabad"))
    story.append(Spacer(1, 5))
    story.append(coverLine("Areesha Aqeel", "Project Lead, BIC Karachi"))
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("August 2026", cover_date))
    story.append(Spacer(1, 5))
    story.append(Paragraph("CONFIDENTIAL  |  FOR INSTITUTIONAL REVIEW ONLY", cover_conf))
    
    story.append(PageBreak())
    
    # Main Body
    def add_h1(text):
        story.append(Paragraph(text, h1_style))
        story.append(HRFlowable(width="100%", thickness=1, color=TEAL, spaceBefore=2, spaceAfter=8))
        
    def add_body(text):
        story.append(Paragraph(text, body_style))
        
    def add_bullet(text):
        story.append(Paragraph(f"• {text}", bullet_style))
        
    def add_numbered(index, text):
        story.append(Paragraph(f"{index}. {text}", bullet_style))

    add_h1("Executive Summary")
    add_body("AirSense is an AI-powered air quality prediction and decision support platform, developed jointly by student teams at BIC Islamabad and BIC Karachi through the BIC x University of Essex COIL AI Hackathon. What began as a hackathon submission has grown into a working system with a validated forecasting model and a clear path to real institutional and commercial use.")
    add_body("We are requesting approval for a three month campus pilot at BIC Islamabad, together with a one-time budget of Rs 20,000, to install a rooftop air quality sensor and collect the real-world data our models need. An identical pilot is running in parallel at BIC Karachi under the same leadership structure, so this is a joint, two-campus effort from day one, not a single-campus project.")
    add_body("For a modest, one-time investment, BIC gains a live applied research project, a public-facing air quality dashboard, and ownership of a system with genuine potential to grow into a commercial product carrying the BIC name.")
    
    add_h1("Where This Began")
    add_body("AirSense began at the BIC x University of Essex COIL AI Hackathon, a Collaborative Online International Learning programme connecting BIC students with University of Essex students on a shared applied AI challenge. Our entry stood out for treating air quality as a decision problem rather than another monitoring dashboard. Using historical Islamabad weather data, we built and validated a forecasting model that explains 41 percent of PM2.5 variance with an average error of 49 micrograms per cubic metre, a strong result for a model trained entirely on downloaded, historical data. The project has since grown, under joint leadership at both campuses, Munim Qureshi at Islamabad and Areesha Aqeel at Karachi, into a full initiative with real institutional and commercial potential.")
    
    add_h1("Why It Matters")
    add_body("Pakistan is ranked the most polluted country in the world by IQAir's 2025 World Air Quality Report, and the World Bank estimates air pollution costs the national economy close to 47 billion US dollars a year. Despite this, institutions and businesses routinely make decisions about outdoor activity, operations, and health without access to real-time, local air quality information. AirSense exists to close that gap, starting with the campuses that built it.")
    
    add_h1("What We Are Proposing")
    add_body("We are requesting approval to install one IoT air quality sensor on the BIC Islamabad rooftop for three months, continuously logging PM2.5 and key weather variables. This is a real, physically deployed IoT system, not a simulation, and it lets us retrain our existing in-house models on genuine local data instead of historical downloads alone. BIC Karachi is running an identical deployment in parallel under Areesha Aqeel's leadership, using the same hardware and software, so both campuses build one shared system together.")
    
    add_h1("Why Both Campuses Benefit")
    
    def make_table(headers, rows, col_widths, right_align_last=False):
        table_data = []
        h_row = []
        for i, h in enumerate(headers):
            style = ParagraphStyle('th', parent=table_header, alignment=2 if right_align_last and i == len(headers)-1 else 0)
            h_row.append(Paragraph(h, style))
        table_data.append(h_row)
        
        for r in rows:
            row_data = []
            for i, cell in enumerate(r):
                style = ParagraphStyle('tb', parent=table_body, alignment=2 if right_align_last and i == len(r)-1 else 0)
                row_data.append(Paragraph(cell, style))
            table_data.append(row_data)
            
        t = Table(table_data, colWidths=col_widths)
        style = [
            ('BACKGROUND', (0,0), (-1,0), NAVY),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]
        for i in range(1, len(table_data)):
            if i % 2 != 0:
                style.append(('BACKGROUND', (0,i), (-1,i), SHADE_ALT))
            else:
                style.append(('BACKGROUND', (0,i), (-1,i), WHITE))
        t.setStyle(TableStyle(style))
        return t

    b_headers = ["Benefit Area", "What BIC Gains"]
    b_rows = [
        ["Applied Research Asset", "Three months of real, campus generated environmental data, usable across AI, Computer Science, and Environmental Science coursework at both campuses."],
        ["Cross Campus Collaboration", "A single system co-built by Islamabad and Karachi together, demonstrating institute-wide capability rather than one campus acting alone."],
        ["Public Dashboard", "A free, publicly accessible live air quality dashboard for the whole BIC community, and eventually the public, at no cost to either campus."],
        ["Institutional Positioning", "BIC becomes one of the first Pakistani institutes with a deployed, student-built, AI-driven environmental monitoring system, at two campuses at once."],
        ["Zero Ongoing Cost", "All software, modelling, and dashboard infrastructure is already built and maintained by the team. The one-time hardware cost is the full financial commitment."]
    ]
    # DXA widths: 2600, 6900. Total = 9500. Proportions: 26/95, 69/95. Total width available ~ 515 pts.
    b_col_widths = [515 * (26/95), 515 * (69/95)]
    story.append(make_table(b_headers, b_rows, b_col_widths))
    story.append(Spacer(1, 10))
    
    add_h1("Budget Request")
    add_body("We are requesting a one-time release of Rs 20,000 to procure and install pilot hardware for the BIC Islamabad deployment. This is a one-time cost with no software licensing fees, subscriptions, or recurring charges, since our full software stack is already built and maintained by the team.")
    
    bud_rows = [
        ["Sensor unit and microcontroller", "12,500"],
        ["Weatherproof enclosure and rooftop mounting", "2,500"],
        ["Power supply and wiring", "2,000"],
        ["Data connectivity for the pilot period", "2,000"],
        ["Contingency (approximately 5 percent)", "1,000"],
    ]
    bud_widths = [515 * (72/95), 515 * (23/95)]
    
    bud_table_data = []
    h_row = [
        Paragraph("Item", ParagraphStyle('th', parent=table_header)), 
        Paragraph("Cost (Rs)", ParagraphStyle('th', parent=table_header, alignment=2))
    ]
    bud_table_data.append(h_row)
    for i, r in enumerate(bud_rows):
        bud_table_data.append([
            Paragraph(r[0], ParagraphStyle('tb', parent=table_body)),
            Paragraph(r[1], ParagraphStyle('tb', parent=table_body, alignment=2))
        ])
    
    # Add Total row
    bud_table_data.append([
        Paragraph("Total", ParagraphStyle('tbb', fontName='Helvetica-Bold', fontSize=10, leading=12)),
        Paragraph("20,000", ParagraphStyle('tbb', fontName='Helvetica-Bold', fontSize=10, leading=12, alignment=2))
    ])
    
    t_bud = Table(bud_table_data, colWidths=bud_widths)
    t_bud_style = [
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 6),
    ]
    for i in range(1, len(bud_table_data)-1):
        if i % 2 != 0:
            t_bud_style.append(('BACKGROUND', (0,i), (-1,i), SHADE_ALT))
        else:
            t_bud_style.append(('BACKGROUND', (0,i), (-1,i), WHITE))
    t_bud_style.append(('BACKGROUND', (0, len(bud_table_data)-1), (-1, len(bud_table_data)-1), BUDGET_TOTAL))
    t_bud.setStyle(TableStyle(t_bud_style))
    story.append(t_bud)
    story.append(Spacer(1, 10))
    
    add_h1("Where This Goes Next")
    add_body("The campus pilot is Phase 1 of a three-phase roadmap that ends in a genuine commercial product.")
    
    rm_headers = ["Phase", "Description", "Key Output"]
    rm_rows = [
        ["Phase 1\nCampus Pilot", "Deploy sensors at both campuses, collect three months of data, retrain existing in-house models.", "Validated two-city dataset and forecasting models."],
        ["Phase 2\nMulti-Campus Refinement", "Improve models using combined Islamabad and Karachi data; expand the decision framework.", "Higher-accuracy models and a reusable blueprint for new cities."],
        ["Phase 3\nOperational Platform", "Launch as a subscription service turning forecasts into direct operational guidance for business and institutional clients.", "Revenue-generating platform with BIC as its founding institution."]
    ]
    rm_widths = [515 * (20/95), 515 * (47/95), 515 * (28/95)]
    
    # Convert newlines to <br/> for Paragraph
    rm_rows_formatted = []
    for r in rm_rows:
        rm_rows_formatted.append([c.replace('\n', '<br/>') for c in r])
        
    story.append(make_table(rm_headers, rm_rows_formatted, rm_widths))
    story.append(Spacer(1, 10))
    
    add_body("The commercial opportunity is significant. In Lahore alone, over 8,000 logistics companies are potential clients, and our projections show the platform breaking even at just 10 subscribers, with an average return of roughly 45 times subscription cost for a typical client through avoided losses. Every part of that opportunity traces back to data collected on BIC's own rooftops, which positions BIC as the founding institution behind this platform, regardless of how large it eventually grows.")
    
    add_h1("Timeline")
    tl_headers = ["Stage", "Activity"]
    tl_rows = [
        ["Week 1", "Budget release and vendor procurement"],
        ["Week 2", "Sensor installation and calibration at both campuses"],
        ["Weeks 3-14", "Continuous data collection, approximately three months"],
        ["Final 2 weeks", "Model retraining, validation, and completion report to management"]
    ]
    tl_widths = [515 * (22/95), 515 * (73/95)]
    story.append(make_table(tl_headers, tl_rows, tl_widths))
    story.append(Spacer(1, 10))
    
    add_h1("Our Request")
    add_body("We respectfully request:")
    add_numbered(1, "Approval of a one-time Rs 20,000 hardware budget for the BIC Islamabad sensor deployment")
    add_numbered(2, "Permission to install the sensor at an agreed rooftop location for a three-month pilot period")
    add_numbered(3, "Facilitation of rooftop access and connectivity support from campus facilities")
    add_numbered(4, "Recognition and support for the parallel BIC Karachi deployment led by Areesha Aqeel")
    add_body("We are happy to present this proposal in person and answer any questions. Thank you for your continued support of student-led innovation at Beaconhouse International College.")
    
    story.append(Spacer(1, 10))
    story.append(Paragraph("Respectfully submitted,", body_style))
    story.append(Spacer(1, 10))
    
    sign_headers = ["Role", "Name", "Signature", "Date"]
    sign_rows = [
        ["Head of Institute, BIC Islamabad", "Ms. Saba Ahson", "", ""],
        ["Head of CSSE/AI, BIC Islamabad", "Ms. Sahifa Alam", "", ""],
        ["Head of CSSE/AI, BIC Karachi", "Mr. Sajid", "", ""],
        ["Project Lead, BIC Islamabad", "Munim Qureshi", "", ""],
        ["Project Lead, BIC Karachi", "Areesha Aqeel", "", ""]
    ]
    # DXA: [3000, 2600, 2200, 1700] -> Total 9500
    sign_widths = [515 * (30/95), 515 * (26/95), 515 * (22/95), 515 * (17/95)]
    story.append(make_table(sign_headers, sign_rows, sign_widths))
    
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated proposal v5 PDF: {OUTPUT_PDF}")

if __name__ == "__main__":
    build_pdf()
