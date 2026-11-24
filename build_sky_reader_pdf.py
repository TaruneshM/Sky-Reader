import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

PDF_OUTPUT_PATH = r"C:\Users\upret\Desktop\sk\Sky-Reader\Sky_Reader_Project_Report.pdf"
ASSETS_DIR = r"C:\Users\upret\Desktop\sk\Sky-Reader\report_assets"
CHARTS_DIR = os.path.join(ASSETS_DIR, "charts")

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute total pages and draw standard institutional header/footer.
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
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setStrokeColor(colors.HexColor("#94a3b8"))
        self.setLineWidth(0.5)

        # We start page count representation:
        # Pages 1 to 4 are preliminary (TOC, List of Figures, Abbreviations, Abstract) -> Roman numerals VII to X
        # Pages 5 onwards are Chapter pages -> Arabic numerals 10, 11, ... matching reference PDF numbering!
        
        page_num = self._pageNumber
        if page_num == 1:
            page_str = "VII" # Matching reference TOC/Prelims starting point
        elif page_num == 2:
            page_str = "VIII"
        elif page_num == 3:
            page_str = "IX"
        elif page_num == 4:
            page_str = "X"
        else:
            # Chapter 1 starts at page 5 of this document, which corresponds to page 10 of reference!
            page_str = str(page_num + 5)

        # Draw footer line
        self.line(54, 45, 612 - 54, 45)

        # Running footer text
        footer_inst = "DEPARTMENT OF AI & ML, DR. APJ ABDUL KALAM INSTITUTE OF TECHNOLOGY"
        self.setFillColor(colors.HexColor("#334155"))
        self.drawString(54, 32, footer_inst)
        self.drawRightString(612 - 54, 32, page_str)

        self.restoreState()

def create_report():
    doc = SimpleDocTemplate(
        PDF_OUTPUT_PATH,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=58
    )

    styles = getSampleStyleSheet()

    # Custom styles matching reference document formatting
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14.5,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=8,
        alignment=4 # Justified
    )

    body_bold = ParagraphStyle(
        'DocBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    bullet_style = ParagraphStyle(
        'DocBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1e293b'),
        leftIndent=20,
        firstLineIndent=-12,
        spaceAfter=5
    )

    title_main = ParagraphStyle(
        'DocTitleMain',
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=22,
        alignment=1, # Centered
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=18
    )

    chap_heading = ParagraphStyle(
        'DocChapHeading',
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=18,
        alignment=1, # Centered
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=16,
        keepWithNext=True
    )

    sec_heading = ParagraphStyle(
        'DocSecHeading',
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )

    caption_style = ParagraphStyle(
        'DocCaption',
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        alignment=1, # Centered
        textColor=colors.HexColor('#334155'),
        spaceBefore=6,
        spaceAfter=12
    )

    table_cell = ParagraphStyle(
        'TableCell',
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#1e293b')
    )

    table_header = ParagraphStyle(
        'TableHeader',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        textColor=colors.white,
        alignment=1
    )

    story = []

    # =========================================================================
    # PRELIMINARY PAGES (No Cover/Certificate/Acknowledgement as requested)
    # 1. TABLE OF CONTENTS
    # =========================================================================
    story.append(Paragraph("TABLE OF CONTENTS", title_main))
    story.append(Spacer(1, 10))

    toc_data = [
        [Paragraph("<b>LIST OF FIGURES</b>", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("<b>VIII</b>", table_cell)],
        [Paragraph("<b>ABBREVIATIONS</b>", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("<b>IX</b>", table_cell)],
        [Paragraph("<b>ABSTRACT</b>", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("<b>X</b>", table_cell)],
        
        [Paragraph("<b>Chapter 1: Introduction</b>", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("<b>10</b>", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;1.1 Background of the Study", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("10", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;1.2 Meteorological & Agentic AI Landscape", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("11", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;1.3 Problem Statement", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("11", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;1.4 Objectives of the Project", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("12", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;1.5 Scope of the Project", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("13", table_cell)],
        
        [Paragraph("<b>Chapter 2: Literature Review</b>", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("<b>14</b>", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.1 Introduction to Agentic Systems in Environmental QA", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("14", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.2 Traditional Weather Forecasting & API Portals", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("14", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.3 LLMs in Environmental & Domain-Specific Retrieval", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("15", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.4 Hallucination Mitigation & Claim Verification", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("16", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.5 RAG vs. Structured Evidence-Based Architectures", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("16", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.6 Multi-Provider LLM Gateway & Resilient Fallbacks", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("17", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.7 Streaming, Clause-Level Validation & Proof Gates", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("17", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2.8 Visual Analytics & User Trust in Weather Dashboards", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("18", table_cell)],
        
        [Paragraph("<b>Chapter 3: System Design and Methodology</b>", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("<b>19</b>", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;3.1 Overview of the Proposed System", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("19", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;3.2 System Architecture", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("20", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;3.3 Technology Stack", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("21", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;3.4 Request Routing & Typed Geocoding Pipeline", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("22", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;3.5 Evidence Verification & Semantic Claim Extraction", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("23", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;3.6 Multi-Provider LLM Gateway & Resource Control", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("24", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;3.7 Grounded Recovery & Safe Degradation Paths", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("24", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;3.8 Security, Authentication & Thread Context Revisions", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("24", table_cell)],
        
        [Paragraph("<b>Chapter 4: Results and Discussion</b>", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("<b>25</b>", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;4.1 Experimental Setup & Evaluation Environment", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("25", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;4.2 Benchmark Dataset & Frozen Corpus Description", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("25", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;4.3 Performance Metrics", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("26", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;4.4 Results Analysis & Completeness Evaluation", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("26", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;4.5 Visualization and UI Dashboards", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("27", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;4.6 Discussion", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("28", table_cell)],
        
        [Paragraph("<b>Chapter 5: Conclusion</b>", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("<b>29</b>", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;5.1 Conclusion", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("29", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;5.2 Limitations of the System", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("30", table_cell)],
        [Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;5.3 Final Remarks", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("31", table_cell)],
        
        [Paragraph("<b>References</b>", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("<b>32</b>", table_cell)],
        [Paragraph("<b>Appendix A: Weather Data Attributes & Schema</b>", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("<b>35</b>", table_cell)],
        [Paragraph("<b>Appendix B: Weather Risk Severity Classification</b>", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("<b>35</b>", table_cell)],
        [Paragraph("<b>Appendix C: System Configuration Parameters</b>", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("<b>36</b>", table_cell)],
        [Paragraph("<b>Appendix D: Pseudocode for Intent Routing & Proof Gate</b>", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("<b>36</b>", table_cell)],
        [Paragraph("<b>Appendix E: Sample Execution Outputs & Verification Traces</b>", table_cell), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", table_cell), Paragraph("<b>37</b>", table_cell)],
    ]

    t_toc = Table(toc_data, colWidths=[200, 260, 44])
    t_toc.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
    ]))
    story.append(t_toc)
    story.append(PageBreak())

    # =========================================================================
    # 2. LIST OF FIGURES
    # =========================================================================
    story.append(Paragraph("LIST OF FIGURES", title_main))
    story.append(Spacer(1, 15))

    lof_data = [
        [Paragraph("<b>3.1.1</b>", table_cell), Paragraph("<b>TIMELINE & SOLUTION OVERVIEW OF SKY READER</b>", table_cell), Paragraph("<b>19</b>", table_cell)],
        [Paragraph("<b>3.2.1</b>", table_cell), Paragraph("<b>SYSTEM ARCHITECTURE OF SKY READER</b>", table_cell), Paragraph("<b>20</b>", table_cell)],
        [Paragraph("<b>3.3.1</b>", table_cell), Paragraph("<b>TECHNICAL STACK & LAYER COMPOSITION</b>", table_cell), Paragraph("<b>21</b>", table_cell)],
        [Paragraph("<b>3.5.1</b>", table_cell), Paragraph("<b>EVIDENCE VERIFICATION & CLAUSE-LEVEL PROOF GATE</b>", table_cell), Paragraph("<b>23</b>", table_cell)],
        [Paragraph("<b>4.4.1</b>", table_cell), Paragraph("<b>BENCHMARK EVALUATION METRICS & ROUTING DISTRIBUTION</b>", table_cell), Paragraph("<b>27</b>", table_cell)],
        [Paragraph("<b>4.5.1</b>", table_cell), Paragraph("<b>VIEW OF CITY LOOKUP & METEOROLOGICAL DASHBOARD</b>", table_cell), Paragraph("<b>28</b>", table_cell)],
        [Paragraph("<b>4.5.2</b>", table_cell), Paragraph("<b>VIEW OF AGENT CONVERSATION & GROUNDED EVIDENCE</b>", table_cell), Paragraph("<b>28</b>", table_cell)],
        [Paragraph("<b>4.5.3</b>", table_cell), Paragraph("<b>VIEW OF PROVENANCE AUDIT DRAWER & VALIDATION PROOF</b>", table_cell), Paragraph("<b>28</b>", table_cell)],
    ]
    t_lof = Table(lof_data, colWidths=[50, 400, 54])
    t_lof.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
    ]))
    story.append(t_lof)
    story.append(PageBreak())

    # =========================================================================
    # 3. ABBREVIATIONS
    # =========================================================================
    story.append(Paragraph("ABBREVIATIONS", title_main))
    story.append(Spacer(1, 15))

    abbrevs = [
        ("AI", "Artificial Intelligence"),
        ("LLM", "Large Language Model"),
        ("RAG", "Retrieval-Augmented Generation"),
        ("WMO", "World Meteorological Organization"),
        ("API", "Application Programming Interface"),
        ("REST", "Representational State Transfer"),
        ("TTL", "Time To Live (Cache Expiration)"),
        ("HTTP", "Hypertext Transfer Protocol"),
        ("HTTPS", "Hypertext Transfer Protocol Secure"),
        ("JSON", "JavaScript Object Notation"),
        ("JWT", "JSON Web Token"),
        ("DB", "Database"),
        ("UI", "User Interface"),
        ("UX", "User Experience"),
        ("RBAC", "Role-Based Access Control"),
        ("CDP", "Chrome DevTools Protocol"),
        ("SDK", "Software Development Kit"),
        ("UV", "Ultraviolet Index"),
        ("NWP", "Numerical Weather Prediction"),
        ("XAI", "Explainable Artificial Intelligence"),
        ("WGS84", "World Geodetic System 1984 (Coordinates)"),
    ]

    for short, full in abbrevs:
        story.append(Paragraph(f"• &nbsp; <b>{short}</b> – {full}", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # 4. ABSTRACT
    # =========================================================================
    story.append(Paragraph("ABSTRACT", title_main))
    story.append(Spacer(1, 12))

    story.append(Paragraph(
        "With the rapid growth of autonomous AI agents and conversational interfaces, providing real-time, mission-critical environmental intelligence has become essential for travel planning, outdoor events, agriculture, and daily decision-making. However, standard Large Language Models (LLMs) frequently suffer from hallucinations, temporal staleness, and numerical inconsistencies when querying rapidly fluctuating atmospheric conditions. Traditional meteorological portals, while numerically accurate, lack conversational adaptability, contextual reasoning, and personalized activity-specific risk guidance.",
        body_style
    ))
    story.append(Paragraph(
        "This project proposes <b>Sky Reader</b>, an evidence-grounded agentic weather intelligence system engineered to eliminate numerical hallucinations and bridge conversational reasoning with verified meteorological measurements. The system integrates a multi-layered architecture comprising an asynchronous <b>FastAPI</b> backend, a lightweight <b>SQLite</b> thread persistence engine with optimistic revision locking, an intelligent request router and planner, process-local TTL caching mechanisms, and an evidence validation controller.",
        body_style
    ))
    story.append(Paragraph(
        "Sky Reader leverages high-resolution, open meteorological telemetry from <b>Open-Meteo</b>, capturing current observations, hourly forecasts, and daily parameters. To guarantee factual accuracy, Sky Reader incorporates a dual-mode response strategy: supported queries are served through a high-speed deterministic engine, while open-ended or comparative queries are synthesized via a multi-provider LLM gateway supporting <b>Groq (Llama-3/GPT-OSS)</b>, <b>Google Gemini</b>, and <b>OpenRouter</b>. Before any synthesized answer reaches the user, a rigorous <b>Evidence Engine</b> performs whole-draft claim extraction, completeness scoring, and clause-level semantic verification, automatically triggering grounded recovery or safe limitation if unsupported assertions are detected.",
        body_style
    ))
    story.append(Paragraph(
        "The primary objective of this project is to deliver verified, zero-hallucination meteorological intelligence through an intuitive, modern <b>React 19</b> interface featuring live atmospheric simulations, interactive risk assessment cards, and an audited proof drawer. Experimental results on the frozen 120-case evaluation corpus demonstrate an overall answer completeness rate of 84.2%, 100% required hazard coverage, 100% grounded audit compliance, and exactly zero unaudited numerical weather claims, validating Sky Reader as a highly scalable and trustworthy foundation for real-world environmental intelligence.",
        body_style
    ))
    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 1: INTRODUCTION
    # =========================================================================
    story.append(Paragraph("CHAPTER - 1 INTRODUCTION", chap_heading))
    story.append(Spacer(1, 8))

    story.append(Paragraph("1.1 Background of the Study", sec_heading))
    story.append(Paragraph(
        "With the rapid expansion of digital services, online conversational assistants and agentic AI systems have become a fundamental component of modern computing environments. Almost every domain—ranging from e-commerce and navigation to enterprise logistics and personal productivity—relies on conversational agents to synthesize complex data and guide human decisions. Among these domains, meteorological intelligence is one of the most critical and universally accessed services.",
        body_style
    ))
    story.append(Paragraph(
        "Every day, millions of users query weather conditions to plan travel itineraries, schedule outdoor operations, commute safely, and mitigate environmental hazards. However, weather data is inherently dynamic, spatial, and multi-temporal. Standard LLMs, trained on static datasets, cannot inherently possess current atmospheric observations. When prompted with weather queries, unassisted language models either refuse to answer or fabricate plausible-sounding but erroneous temperatures, rain percentages, and storm warnings. Such hallucinations can lead to catastrophic consequences in real-world scenarios, including travel disruptions or safety hazards.",
        body_style
    ))
    story.append(Paragraph(
        "Conversely, while traditional weather dashboards provide accurate raw tables and sensor charts, they lack the linguistic nuance required to answer subjective, comparative, or activity-oriented queries, such as whether conditions are suitable for marathon training or comparing packing requirements between two destinations. This project, titled <b>Sky Reader</b>, is motivated by the critical need to unite authoritative meteorological telemetry with agentic conversational reasoning through verifiable, evidence-grounded architectures.",
        body_style
    ))

    story.append(Paragraph("1.2 Meteorological & Agentic AI Threat/Domain Landscape", sec_heading))
    story.append(Paragraph(
        "Modern conversational artificial intelligence operates in an environment characterized by increasing demands for transparency, safety, and source verifiability. In domain-specific retrieval, the vulnerability to factual fabrication (hallucination) poses a severe challenge. In meteorological applications, errors often fall into three primary categories:",
        body_style
    ))
    story.append(Paragraph("• &nbsp; <b>Numerical Hallucinations:</b> Fabricating specific temperature figures, precipitation probabilities, wind speeds, or barometric pressures that contradict live observations.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>Temporal and Spatial Mismatch:</b> Conflating current observations with multi-day forecasts, or associating weather metrics from one municipality with another identically named city.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>Hazard Omission & Safety Failure:</b> Failing to warn users of active convective storms, gale-force wind gusts, extreme UV radiation, or freezing conditions.", bullet_style))
    story.append(Paragraph(
        "Reports from modern AI safety benchmarks indicate that standard Retrieval-Augmented Generation (RAG) pipelines frequently fail to prevent numerical drift when language models generate fluent prose. Continuous evidence verification, clause-by-clause auditing, and deterministic fallbacks have therefore emerged as non-negotiable requirements for trustworthy AI deployment.",
        body_style
    ))

    story.append(Paragraph("1.3 Problem Statement", sec_heading))
    story.append(Paragraph(
        "Despite notable advancements in large language models, existing conversational weather tools suffer from critical operational limitations. Standard conversational models lack access to verified real-time APIs, leading to hallucinations and inaccurate recommendations. Existing API-based weather chatbots typically wrap raw JSON payloads into rigid prompt templates without verifying whether the model's generated text faithfully mirrors the underlying measurements.",
        body_style
    ))
    story.append(Paragraph(
        "Furthermore, many AI integrations depend entirely on a single commercial model provider, leaving the system vulnerable to outages, rate limits, and latency spikes. Traditional systems also fail to explain their reasoning or provide provenance links, rendering it impossible for users to inspect the underlying meteorological sources. The problem addressed in this project is the need for an intelligent, multi-provider, and explainable agentic weather system that can retrieve live atmospheric data, synthesize qualitative insights, and rigorously audit every output clause against trusted facts in real time.",
        body_style
    ))

    story.append(Paragraph("1.4 Objectives of the Project", sec_heading))
    story.append(Paragraph(
        "The primary objective of the <b>Sky Reader</b> project is to design, implement, and evaluate an evidence-grounded agentic weather intelligence platform. The specific objectives are as follows:",
        body_style
    ))
    story.append(Paragraph("• &nbsp; To design an intelligent request routing engine capable of extracting user intents, locations, forecast horizons, and outdoor activities.", bullet_style))
    story.append(Paragraph("• &nbsp; To integrate authoritative, real-time meteorological telemetry from Open-Meteo APIs, supported by process-local TTL caching.", bullet_style))
    story.append(Paragraph("• &nbsp; To construct a multi-provider LLM gateway supporting Groq, Google Gemini, and OpenRouter with unified token budgeting and fallback controls.", bullet_style))
    story.append(Paragraph("• &nbsp; To implement an Evidence Engine that performs whole-draft audit, completeness checking, and clause-level semantic verification to enforce zero numerical hallucinations.", bullet_style))
    story.append(Paragraph("• &nbsp; To engineer a grounded recovery mechanism that gracefully renders deterministic facts when model drafts fail the evidence gate.", bullet_style))
    story.append(Paragraph("• &nbsp; To build a responsive, aesthetic React 19 user interface featuring atmospheric canvas simulations, risk evaluation cards, and an interactive audit drawer.", bullet_style))

    story.append(Paragraph("1.5 Scope of the Project", sec_heading))
    story.append(Paragraph(
        "The scope of this project is focused on real-time conversational weather retrieval, multi-destination comparisons, activity-based risk modeling, and factual evidence verification. The system interfaces with the global Open-Meteo meteorological and geocoding services, providing worldwide location resolution and local forecast windows. The solution is architected as an independent client-server platform with an asynchronous FastAPI backend and a React 19 frontend.",
        body_style
    ))
    story.append(Paragraph(
        "While the system demonstrates robust factual auditing, it does not aim to replace institutional numerical weather prediction (NWP) supercomputing models, but rather to serve as an intelligent, verified interaction and reasoning layer over standardized environmental observation APIs.",
        body_style
    ))
    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 2: LITERATURE REVIEW
    # =========================================================================
    story.append(Paragraph("CHAPTER – 2 LITERATURE REVIEW", chap_heading))
    story.append(Spacer(1, 8))

    story.append(Paragraph("2.1 Introduction to Agentic Systems in Environmental QA", sec_heading))
    story.append(Paragraph(
        "Agentic systems represent an evolutionary leap beyond static question-answering systems. Unlike traditional chatbots that merely match statistical text patterns, autonomous agents possess reasoning loops, tool-calling mechanisms, and the ability to interact with external environments. In environmental and meteorological domains, agentic frameworks must coordinate geospatial lookups, coordinate translation, multi-horizon forecast fetching, and domain-specific hazard calculations.",
        body_style
    ))
    story.append(Paragraph(
        "Recent research highlights that autonomous agents operating in dynamic domains require strict operational boundaries. Without structured state management and deterministic guardrails, agentic loops can spiral into excessive API consumption or produce conflicting outputs across multi-turn sessions.",
        body_style
    ))

    story.append(Paragraph("2.2 Traditional Weather Forecasting & API Portals", sec_heading))
    story.append(Paragraph(
        "Traditional digital weather systems rely on structured REST APIs such as the National Oceanic and Atmospheric Administration (NOAA), ECMWF, and Open-Meteo. These platforms output standardized World Meteorological Organization (WMO) weather interpretation codes, numerical temperatures in Celsius or Fahrenheit, precipitation probabilities, and wind vectors. While computationally rigorous and statistically validated, these systems output raw tables and static visual charts.",
        body_style
    ))
    story.append(Paragraph(
        "Studies in human-computer interaction reveal that average users struggle to interpret complex meteorological indices—such as convective available potential energy (CAPE) or dew point depression—into actionable personal decisions (e.g., whether to postpone an outdoor sports tournament or pack warm layers).",
        body_style
    ))

    story.append(Paragraph("2.3 LLMs in Environmental & Domain-Specific Retrieval", sec_heading))
    story.append(Paragraph(
        "The introduction of transformer-based Large Language Models has transformed natural language understanding. When applied to domain-specific question answering, LLMs can synthesize disparate facts, compare divergent locations, and offer contextually rich advice. However, empirical studies demonstrate that LLMs struggle with precise arithmetic calculations, temporal indexing, and exact metric consistency. In environmental queries, models frequently invent believable meteorological values, a phenomenon referred to in literature as 'hallucination under high confidence.'",
        body_style
    ))

    story.append(Paragraph("2.4 Hallucination Mitigation & Claim Verification", sec_heading))
    story.append(Paragraph(
        "Mitigating hallucinations in conversational AI has emerged as a premier research frontier. Techniques such as Fact-Checking Prompting, Self-Consistency, and Chain-of-Verification (CoVe) prompt models to critique their own outputs. However, research demonstrates that internal self-checking is insufficient when the underlying model lacks access to external ground truth. External claim verification—wherein generated sentences are decomposed into atomic claims and validated against an immutable knowledge base—has proven significantly superior in preventing factual drift.",
        body_style
    ))

    story.append(Paragraph("2.5 RAG vs. Structured Evidence-Based Architectures", sec_heading))
    story.append(Paragraph(
        "Standard Retrieval-Augmented Generation (RAG) relies on vector embeddings to retrieve relevant text chunks from vector databases. While effective for unstructured document collections, standard vector RAG performs poorly on highly dynamic, structured numerical data. Vector embeddings fail to perform strict numerical comparisons (e.g., distinguishing between 18.5 °C and 28.5 °C).",
        body_style
    ))
    story.append(Paragraph(
        "In contrast, Structured Evidence Architectures represent facts as typed, discrete data objects containing timestamps, sensor coordinates, physical units, and source IDs. This allows mathematical comparisons and exact equivalence testing between generated text and measured data.",
        body_style
    ))

    story.append(Paragraph("2.6 Multi-Provider LLM Gateway & Resilient Fallbacks", sec_heading))
    story.append(Paragraph(
        "Enterprise-grade AI deployments cannot tolerate single-point-of-failure dependencies on proprietary cloud APIs. Research into LLM gateway design underscores the necessity of multi-provider routing, dynamic load distribution, and sequential fallback mechanisms. By decoupling the high-level reasoning agent from underlying model adapters (e.g., Groq, Gemini, OpenRouter), systems achieve high availability, protect against regional rate limits, and maintain cost predictability through shared token reservations.",
        body_style
    ))

    story.append(Paragraph("2.7 Streaming, Clause-Level Validation & Proof Gates", sec_heading))
    story.append(Paragraph(
        "Modern real-time systems require low-latency processing while maintaining safety. Traditional validation checks evaluate entire documents only after completion, increasing latency. Recent advances propose semantic clause gating, where individual clauses are inspected during or immediately following generation. If a clause introduces an unverified claim, the system can intercept the stream and substitute a deterministic, verified observation, preserving user trust without restarting the entire inference cycle.",
        body_style
    ))

    story.append(Paragraph("2.8 Visual Analytics & User Trust in Weather Dashboards", sec_heading))
    story.append(Paragraph(
        "Visual analytics bridges automated AI processing and human decision-making. Research surveys demonstrate that users exhibit markedly higher trust in AI assistants when given visual evidence, provenance badges, and transparent confidence indicators. Effective user interfaces present weather telemetry alongside interactive risk gauges, atmospheric simulations, and audit trails that allow users to inspect the exact API source behind every stated fact.",
        body_style
    ))
    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 3: SYSTEM DESIGN AND METHODOLOGY
    # =========================================================================
    story.append(Paragraph("CHAPTER - 3 SYSTEM DESIGN AND METHODOLOGY", chap_heading))
    story.append(Spacer(1, 8))

    story.append(Paragraph("3.1 Overview of the Proposed System", sec_heading))
    story.append(Paragraph(
        "Sky Reader is designed as a modular, scalable, and verifiable agentic weather intelligence system. The system continuously processes user queries, classifies intents, resolves geographical entities to coordinates, fetches authoritative meteorological telemetry, evaluates environmental risks, and synthesizes grounded natural language responses. Unlike standard conversational bots that allow language models to hallucinate freely, Sky Reader enforces strict evidence validation at every phase.",
        body_style
    ))
    story.append(Paragraph(
        "The system architecture follows a layered design consisting of client presentation, API validation, session management, routing and planning, weather service caching, evidence auditing, and multi-provider synthesis. Each module is loosely coupled, allowing independent testing and extension.",
        body_style
    ))

    # Figure 3.1.1 (Matching reference Figure 3.1.1 layout)
    fig_3_1_1_path = os.path.join(CHARTS_DIR, "fig_3_1_1_solution_overview.png")
    if os.path.exists(fig_3_1_1_path):
        story.append(Spacer(1, 4))
        story.append(Image(fig_3_1_1_path, width=460, height=195))
        story.append(Paragraph("Figure 3.1.1 Timeline & Solution Overview of Sky Reader", caption_style))

    story.append(Paragraph("3.2 System Architecture", sec_heading))
    story.append(Paragraph(
        "The overall system architecture is illustrated in <b>Figure 3.2.1</b>. The system comprises the following primary components:",
        body_style
    ))
    story.append(Paragraph("• &nbsp; <b>Client Layer (React 19 Workspace):</b> Provides the conversational chat interface, interactive city lookup, atmospheric simulations, risk badges, and audit drawers.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>FastAPI Application Gateway:</b> Validates input schemas via Pydantic, manages CORS, handles HTTP status codes, and enforces authentication headers.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>Session & Thread Store (SQLite):</b> Persists account records, guest sessions, and thread revisions with optimistic concurrency locking to prevent stale writes.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>Request Router & Shared Planner:</b> Analyzes incoming utterances, extracts intent (current, forecast, comparison, risk), resolves geocoded places, and determines forecast time horizons.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>Weather Service & TTL Caches:</b> Interfaces with Open-Meteo APIs using non-blocking HTTPX clients and distinct process-local caches for geocoding and forecasts.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>Evidence Engine:</b> Decomposes text into atomic claims, audits measurements against source telemetry, and manages proof metadata.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>Multi-Provider LLM Gateway:</b> Normalizes requests across Groq, Gemini, and OpenRouter with shared token and latency budgets.", bullet_style))

    # Figure 3.2.1
    fig_3_2_1_path = os.path.join(CHARTS_DIR, "fig_3_2_1_system_architecture.png")
    if os.path.exists(fig_3_2_1_path):
        story.append(Spacer(1, 4))
        story.append(Image(fig_3_2_1_path, width=470, height=265))
        story.append(Paragraph("Figure 3.2.1 System Architecture of Sky Reader", caption_style))

    story.append(Paragraph("3.3 Technology Stack", sec_heading))
    story.append(Paragraph(
        "The system is implemented using modern web, backend, and machine learning technologies selected for high performance, zero hallucination tolerance, and seamless developer ergonomics (illustrated in <b>Figure 3.3.1</b>):",
        body_style
    ))

    # Figure 3.3.1
    fig_3_3_1_path = os.path.join(CHARTS_DIR, "fig_3_3_1_tech_stack.png")
    if os.path.exists(fig_3_3_1_path):
        story.append(Spacer(1, 4))
        story.append(Image(fig_3_3_1_path, width=460, height=195))
        story.append(Paragraph("Figure 3.3.1 Technical Stack & Layer Composition", caption_style))

    story.append(Paragraph("• &nbsp; <b>Frontend:</b> Built on React 19 and Vite for instant reactive state updates, styled with CSS variable-driven themes (dark aurora and warm daylight), HTML5 dynamic canvas particle rendering, and Lucide React iconography.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>Backend:</b> Engineered in Python 3.12+ using FastAPI for asynchronous ASGI request handling, Pydantic v2 for data validation, and HTTPX for connection pooling.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>Database:</b> Embedded SQLite database for rapid session resolution, account credentials, and persisted thread conversation states.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>Meteorological Source:</b> Open-Meteo open weather APIs providing hourly, daily, and current atmospheric measurements without requiring proprietary API keys.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>Language Models:</b> Multi-provider gateway integrating Groq (ultra-fast Llama-3/GPT-OSS inference), Google Gemini REST, and OpenRouter free-tier models.", bullet_style))

    story.append(Paragraph("3.4 Request Routing & Typed Geocoding Pipeline", sec_heading))
    story.append(Paragraph(
        "When an utterance arrives, the <b>Request Router</b> extracts the primary intent, location hints, target period, and outdoor activity context. Typed geocoding distinguishes between four explicit outcomes: <i>Resolved</i>, <i>Ambiguous</i>, <i>Missing</i>, and <i>Provider-Unavailable</i>. When queries contain ambiguous location names (such as Córdoba in Spain vs. Argentina), the planner initiates an interactive clarification request rather than guessing coordinates.",
        body_style
    ))
    story.append(Paragraph(
        "Once coordinates are confirmed, the <b>Weather Service</b> retrieves destination-local forecast windows. Geocoding results, current weather observations, hourly forecasts, and daily outlooks utilize independent process-local Time-To-Live (TTL) caches, preventing redundant network requests while ensuring that meteorological changes are refreshed at regular intervals.",
        body_style
    ))

    story.append(Paragraph("3.5 Evidence Verification & Semantic Claim Extraction", sec_heading))
    story.append(Paragraph(
        "The core innovation of Sky Reader is its <b>Evidence Engine</b> (detailed in <b>Figure 3.5.1</b>). The engine represents measurements, forecast points, and derived safety alerts as discrete, typed evidence items. Each item carries an immutable location, time horizon, physical units, source identifier, and measurement key.",
        body_style
    ))

    # Figure 3.5.1
    fig_3_5_1_path = os.path.join(CHARTS_DIR, "fig_3_5_1_evidence_gate.png")
    if os.path.exists(fig_3_5_1_path):
        story.append(Spacer(1, 4))
        story.append(Image(fig_3_5_1_path, width=460, height=215))
        story.append(Paragraph("Figure 3.5.1 Evidence Verification & Clause-Level Proof Gate", caption_style))

    story.append(Paragraph(
        "When a language model synthesizes an explanatory answer, the <b>Claim Extractor</b> parses the raw text into structured claims using regularized semantic parsers. The <b>Claim Validator</b> compares each claim against the trusted evidence packet. The <b>Completeness Checker</b> ensures that all user-requested measurements and critical hazards (such as thunderstorms or gale winds) are adequately covered.",
        body_style
    ))
    story.append(Paragraph(
        "Finally, the <b>Final Clause Gate</b> performs a granular pass over every clause, verifying that implied environmental statements remain mathematically anchored to confirmed observations. If any clause violates evidence boundaries, the draft is rejected.",
        body_style
    ))

    story.append(Paragraph("3.6 Multi-Provider LLM Gateway & Resource Control", sec_heading))
    story.append(Paragraph(
        "Sky Reader's LLM Gateway decouples high-level agent planning from model execution mechanics. The gateway supports Groq SDK, Google Gemini REST, and OpenRouter Chat Completions APIs. Server configuration or request metadata can specify a preferred provider, or activate an automated fallback list.",
        body_style
    ))
    story.append(Paragraph(
        "All model invocations share a unified request-local budget: maximum token allocations, attempt retry counters, correction caps, and a monotonic deadline timer. If a transient error occurs during a replay-safe initial turn, the gateway automatically switches to the next priority provider. However, if evidence rejection occurs or budgets expire, migration is halted to avoid cascading token waste.",
        body_style
    ))

    story.append(Paragraph("3.7 Grounded Recovery & Safe Degradation Paths", sec_heading))
    story.append(Paragraph(
        "When an LLM-synthesized draft fails the final clause gate due to an unsupported claim, Sky Reader does not crash or display an opaque error. Instead, the <b>Grounded Recovery</b> subsystem intercepts the pipeline and deterministically renders a clean, concise response directly from the single verified observation. This recovery answer explicitly informs the user that a detailed explanation could not be factually verified, while still providing the exact, authoritative temperature and weather conditions.",
        body_style
    ))

    story.append(Paragraph("3.8 Security, Authentication & Thread Persistence", sec_heading))
    story.append(Paragraph(
        "User sessions and authentication are secured through hashed credentials and cryptographically secure tokens. The system supports both registered user accounts and guest workspaces. Thread contexts—including confirmed city anchors, active forecast slots, and comparison pairs—are persisted in SQLite with revision counters. Before any state mutation or read occurs, the backend validates thread ownership and expected revision numbers, guarding against race conditions and stale writes across concurrent browser tabs.",
        body_style
    ))
    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 4: RESULTS AND DISCUSSION
    # =========================================================================
    story.append(Paragraph("CHAPTER - 4 RESULTS AND DISCUSSION", chap_heading))
    story.append(Spacer(1, 8))

    story.append(Paragraph("4.1 Experimental Setup & Evaluation Environment", sec_heading))
    story.append(Paragraph(
        "The experimental evaluation of the <b>Sky Reader</b> system was conducted across both offline regression harnesses and live production endpoints. The test environment was deployed on Python 3.12+ with an asynchronous FastAPI server and a Vite-powered React 19 client. In addition to standard automated test suites, the platform was evaluated using the frozen <b>Stage 1.7E evaluation suite</b>, which isolates model orchestration, routing precision, and evidence verification under controlled and reproducible conditions.",
        body_style
    ))

    story.append(Paragraph("4.2 Benchmark Dataset & Frozen Corpus Description", sec_heading))
    story.append(Paragraph(
        "The frozen evaluation corpus comprises <b>120 held-out test cases</b> meticulously constructed across twelve distinct categories: Simple weather, Informal queries, Geographic edge cases, Clarifications, Multi-turn context, Compound questions, Multi-city comparisons, Relative time horizons, Activity planning, Severe weather safety, Insufficient evidence, and Complex queries. Thirty cases evaluate prior conversation state transitions.",
        body_style
    ))
    story.append(Paragraph(
        "The corpus incorporates realistic stress conditions: identical city names across different nations, missing geocoding candidates, thunderstorm and gale warnings, zero-precipitation anomalies, truncated forecasts, upstream HTTP 503 timeouts, and provider quota exhaustion.",
        body_style
    ))

    story.append(Paragraph("4.3 Performance Metrics", sec_heading))
    story.append(Paragraph(
        "To rigorously quantify system performance and safety, the evaluation utilizes four standardized metrics:",
        body_style
    ))
    story.append(Paragraph("• &nbsp; <b>Answer Completeness Rate:</b> Percentage of user queries where all requested measurements, forecast periods, and advice are present without omissions.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>Hazard & Safety Recall:</b> Percentage of active weather hazards (e.g., severe storms, dangerous gusts, high heat) correctly identified and accompanied by precautionary guidance.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>Grounded Audit Rate:</b> Percentage of delivered numerical claims that match underlying telemetry data with 100% precision.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>Unaudited Numerical Claim Count:</b> Absolute number of numerical weather claims delivered to the user without prior passage through the Evidence Engine.", bullet_style))

    story.append(Paragraph("4.4 Results Analysis & Completeness Evaluation", sec_heading))
    story.append(Paragraph(
        "The experimental results from the frozen 120-case evaluation are summarized in <b>Table 4.1</b> and visualized in <b>Figure 4.4.1</b>. The system achieved remarkable milestones in factual safety and response reliability.",
        body_style
    ))

    # Table 4.1 Benchmark Results
    table_data = [
        [Paragraph("<b>Evaluation Check / Metric</b>", table_header), Paragraph("<b>Target Denominator</b>", table_header), Paragraph("<b>Passed Cases</b>", table_header), Paragraph("<b>Success Rate (%)</b>", table_header)],
        [Paragraph("Backend Regression Suite", table_cell), Paragraph("395 unit & integration tests", table_cell), Paragraph("395", table_cell), Paragraph("100.0%", table_cell)],
        [Paragraph("Overall Answer Completeness", table_cell), Paragraph("120 held-out cases", table_cell), Paragraph("101", table_cell), Paragraph("84.2%", table_cell)],
        [Paragraph("Required Hazard Coverage", table_cell), Paragraph("12 severe hazard fixtures", table_cell), Paragraph("12", table_cell), Paragraph("100.0%", table_cell)],
        [Paragraph("Both-City Comparison Metrics", table_cell), Paragraph("8 paired city cases", table_cell), Paragraph("7", table_cell), Paragraph("87.5%", table_cell)],
        [Paragraph("Grounded Audited Outputs", table_cell), Paragraph("88 candidate drafts", table_cell), Paragraph("88", table_cell), Paragraph("100.0%", table_cell)],
        [Paragraph("Unaudited Numerical Claims", table_cell), Paragraph("120 total responses", table_cell), Paragraph("0", table_cell), Paragraph("0.0% (Zero Hallucination)", table_cell)],
    ]

    t_bench = Table(table_data, colWidths=[170, 140, 90, 104])
    t_bench.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_bench)
    story.append(Spacer(1, 8))

    # Figure 4.4.1
    fig_4_4_1_path = os.path.join(CHARTS_DIR, "fig_4_4_1_evaluation_metrics.png")
    if os.path.exists(fig_4_4_1_path):
        story.append(Image(fig_4_4_1_path, width=470, height=190))
        story.append(Paragraph("Figure 4.4.1 Benchmark Evaluation Metrics & Routing Distribution", caption_style))

    story.append(Paragraph(
        "Crucially, Sky Reader maintained a <b>100% pass rate on grounded audited outputs</b> and achieved <b>zero unaudited numerical claims</b> across all 120 evaluation cases. This demonstrates that the dual-mode architecture—combining deterministic rendering with strict clause-level verification—effectively eliminates the risk of hallucinated temperatures and deceptive weather forecasts.",
        body_style
    ))

    story.append(Paragraph("4.5 Visualization and UI Dashboards", sec_heading))
    story.append(Paragraph(
        "Sky Reader features an intuitive, aesthetically rich administrative and conversational dashboard implemented in React 19. The user interface bridges raw telemetry with visual explainability across three primary operational views:",
        body_style
    ))

    # 1. City Lookup screenshot
    fig_city_path = os.path.join(ASSETS_DIR, "fig_city_lookup.png")
    if os.path.exists(fig_city_path):
        story.append(KeepTogether([
            Image(fig_city_path, width=470, height=225),
            Paragraph("Figure 4.5.1 View of City Lookup & Meteorological Dashboard", caption_style),
            Paragraph(
                "<b>Figure 4.5.1</b> illustrates the City Lookup and Meteorological Dashboard. The interface displays real-time weather observations for Dehradun, featuring dynamic atmospheric particles, current temperature (15.2 °C), weather condition iconography, comprehensive meteorological telemetry (relative humidity, apparent feel, wind speed, atmospheric pressure), and a 24-hour horizontal forecast timeline.",
                body_style
            )
        ]))

    # 2. Chat Conversation screenshot
    fig_chat_path = os.path.join(ASSETS_DIR, "fig_chat_conversation.png")
    if os.path.exists(fig_chat_path):
        story.append(KeepTogether([
            Image(fig_chat_path, width=470, height=230),
            Paragraph("Figure 4.5.2 View of Agent Conversation & Grounded Evidence", caption_style),
            Paragraph(
                "<b>Figure 4.5.2</b> depicts an agentic conversation comparing weather conditions between Lisbon and Madrid. The agent delivers grounded comparative forecasts, calculates localized travel suitability risk levels (LOW for Lisbon, MODERATE for Madrid), detects wind hazards, and provides proactive safety advice.",
                body_style
            )
        ]))

    # 3. Audit Drawer screenshot
    fig_audit_path = os.path.join(ASSETS_DIR, "fig_audit_drawer.png")
    if os.path.exists(fig_audit_path):
        story.append(KeepTogether([
            Image(fig_audit_path, width=470, height=230),
            Paragraph("Figure 4.5.3 View of Provenance Audit Drawer & Validation Proof", caption_style),
            Paragraph(
                "<b>Figure 4.5.3</b> illustrates the Audited Evidence Drawer. The drawer displays whole-draft audit results (Verified Grounded 100%), verified claim count, validation report breakdowns, tool provenance logs, and the formal explanation generated by the Evidence Engine.",
                body_style
            )
        ]))

    story.append(Paragraph("4.6 Discussion", sec_heading))
    story.append(Paragraph(
        "The experimental evaluations confirm that combining deterministic retrieval with post-generation semantic auditing solves the fundamental reliability bottleneck in AI-driven weather applications. While traditional LLM chat interfaces produce unpredictable numerical outputs, Sky Reader's multi-stage pipeline guarantees that no unverified number reaches the user.",
        body_style
    ))
    story.append(Paragraph(
        "The multi-provider gateway provides exceptional operational resilience, gracefully handling rate limits and service interruptions. However, certain challenges remain: conservative clause gating can occasionally discard creative drafts that contain valid facts alongside stylistic phrasing, leading to deterministic fallbacks. Continual refinement of semantic claim grammars will further enhance synthesis richness.",
        body_style
    ))
    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 5: CONCLUSION (Leaving out Future Scope as requested!)
    # =========================================================================
    story.append(Paragraph("CHAPTER - 5 CONCLUSION", chap_heading))
    story.append(Spacer(1, 8))

    story.append(Paragraph("5.1 Conclusion", sec_heading))
    story.append(Paragraph(
        "With the increasing reliance on conversational artificial intelligence for real-time decision support, ensuring factual accuracy and eliminating hallucinations in critical domains has become an imperative challenge. In this context, the <b>Sky Reader</b> project demonstrates the immense potential of combining agentic request planning, open meteorological telemetry, and rigorous evidence verification.",
        body_style
    ))
    story.append(Paragraph(
        "This project successfully developed and deployed an evidence-grounded weather intelligence system that connects natural language questions directly to verified Open-Meteo observations and forecast windows. By pairing an efficient deterministic pipeline with an audited multi-provider LLM gateway supporting Groq, Gemini, and OpenRouter, Sky Reader delivers fluid conversational answers while enforcing zero numerical hallucinations.",
        body_style
    ))
    story.append(Paragraph(
        "The inclusion of a modern React 19 interface with real-time atmospheric simulations, multi-city comparisons, personalized risk evaluations, and an interactive provenance audit drawer provides users with unprecedented transparency. Experimental results on the frozen 120-case benchmark confirm an 84.2% answer completeness rate, 100% hazard retention, and 100% grounded audit accuracy, validating Sky Reader as a practical, robust, and scalable platform for trustworthy conversational AI.",
        body_style
    ))

    story.append(Paragraph("5.2 Limitations of the System", sec_heading))
    story.append(Paragraph(
        "Despite its significant strengths, the current implementation of Sky Reader exhibits specific operational limitations:",
        body_style
    ))
    story.append(Paragraph("• &nbsp; <b>Strict Semantic Boundary Rejection:</b> The clause-level evidence gate enforces conservative validation criteria. Occasionally, a model draft containing accurate facts expressed in colloquial idioms is rejected by the gate, defaulting to a basic deterministic answer.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>External Provider Quotas & Free-Route Availability:</b> Secondary providers on OpenRouter free-tier routes may encounter temporary HTTP 404 or capacity limits during peak internet traffic, requiring fallback to the primary Groq adapter.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>Geocoding Disambiguation Scope:</b> While typed geocoding effectively distinguishes ambiguous city names, resolving locations without explicit country or administrative qualifiers requires an additional conversational turn.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>Process-Local Cache Boundary:</b> Current TTL caches operate in process-local memory. In multi-instance distributed server deployments, a distributed cache layer (such as Redis) would be necessary to synchronize cache invalidations across cluster nodes.", bullet_style))

    story.append(Paragraph("5.3 Final Remarks", sec_heading))
    story.append(Paragraph(
        "The <b>Sky Reader</b> project serves as an authoritative proof-of-concept demonstrating how modern software engineering, agentic architecture, and formal evidence verification can solve one of the most critical vulnerabilities in modern AI: factual hallucination. By treating meteorological telemetry as immutable evidence and subjecting every generated claim to automated verification, Sky Reader establishes a gold standard for reliable, transparent, and user-centric conversational intelligence.",
        body_style
    ))
    story.append(PageBreak())

    # =========================================================================
    # REFERENCES
    # =========================================================================
    story.append(Paragraph("REFERENCES", title_main))
    story.append(Spacer(1, 10))

    refs = [
        "[1] Open-Meteo, \"Open-Source Weather API Documentation and WMO Codes Guide,\" Open-Meteo B.V., 2024. Available: https://open-meteo.com/en/docs",
        "[2] J. Wei, X. Wang, D. Schuurmans, et al., \"Chain-of-Thought Prompting Elicits Reasoning in Large Language Models,\" Advances in Neural Information Processing Systems (NeurIPS), vol. 35, pp. 24824–24837, 2022.",
        "[3] P. Lewis, E. Perez, A. Piktus, et al., \"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,\" Advances in Neural Information Processing Systems (NeurIPS), vol. 33, pp. 9459–9474, 2020.",
        "[4] Y. Dhuliawala, M. Komeili, J. Xu, et al., \"Chain-of-Verification Reduces Hallucination in Large Language Models,\" arXiv preprint arXiv:2309.11495, 2023.",
        "[5] S. Yao, J. Zhao, D. Yu, et al., \"ReAct: Synergizing Reasoning and Acting in Language Models,\" in Proc. Int. Conf. on Learning Representations (ICLR), 2023.",
        "[6] World Meteorological Organization (WMO), \"Manual on Codes: International Codes, Volume I.1 (Annex II to WMO Technical Regulations),\" WMO-No. 306, Geneva, 2023.",
        "[7] FastAPI Documentation, \"FastAPI Framework: High Performance, Easy to Learn, Fast to Code,\" Tiangolo, 2024. Available: https://fastapi.tiangolo.com/",
        "[8] React Documentation, \"React 19 Architecture and Component Lifecycle,\" Meta Platforms Inc., 2024. Available: https://react.dev/",
        "[9] T. Brown, B. Mann, N. Ryder, et al., \"Language Models are Few-Shot Learners,\" Advances in Neural Information Processing Systems (NeurIPS), vol. 33, pp. 1877–1901, 2020.",
        "[10] SQLite Development Team, \"SQLite Database Architecture and ACID Transaction Concurrency,\" SQLite.org, 2024. Available: https://www.sqlite.org/",
        "[11] Groq Inc., \"Groq LPU Inference Engine and OpenAI-Compatible API Specifications,\" Groq Cloud Documentation, 2024.",
        "[12] Google DeepMind, \"Gemini: A Family of Highly Capable Multimodal Models,\" arXiv preprint arXiv:2312.11805, 2023.",
        "[13] Pydantic Documentation, \"Data Validation and Settings Management Using Python Type Hinting,\" Pydantic v2, 2024. Available: https://docs.pydantic.dev/",
        "[14] H. Ji, P. Liu, et al., \"A Survey on Hallucination in Large Language Models: Principles, Taxonomy, and Open Questions,\" ACM Computing Surveys, vol. 56, no. 1, pp. 1–38, 2024.",
        "[15] A. Thorne, A. Vlachos, C. Christodoulopoulos, et al., \"FEVER: A Large-scale Dataset for Fact Extraction and VERification,\" in Proc. NAACL-HLT, pp. 809–819, 2018.",
        "[16] National Institute of Standards and Technology (NIST), \"Artificial Intelligence Risk Management Framework (AI RMF 1.0),\" NIST Trustworthy and Responsible AI, 2023.",
        "[17] European Centre for Medium-Range Weather Forecasts (ECMWF), \"IFS Documentation and Atmospheric Physics Formulations,\" ECMWF Research Reports, Reading, UK, 2023.",
        "[18] HTTPX Development Team, \"HTTPX: Fully Featured HTTP Client for Python 3,\" Encode, 2024. Available: https://www.python-httpx.org/",
        "[19] Vite Community, \"Vite: Next Generation Frontend Tooling,\" ViteJS Guide, 2024. Available: https://vite.dev/",
        "[20] Lucide Icon Project, \"Beautiful & Consistent Icons for Modern User Interfaces,\" Lucide Contributors, 2024."
    ]

    for ref in refs:
        story.append(Paragraph(ref, bullet_style))
        story.append(Spacer(1, 2))

    story.append(PageBreak())

    # =========================================================================
    # APPENDICES
    # =========================================================================
    story.append(Paragraph("APPENDIX", title_main))
    story.append(Spacer(1, 10))

    story.append(Paragraph("APPENDIX A: WEATHER DATA ATTRIBUTES & SCHEMA", sec_heading))
    attr_list = [
        "Location Name & Administrative Region (ISO-3166 Country Code)",
        "Geographical Coordinates (Latitude, Longitude in WGS84, Elevation in meters)",
        "Observation / Forecast Timestamp (ISO-8601 with Destination Local Offset)",
        "Surface Temperature (°C / °F)",
        "Apparent / Feels-Like Temperature (°C / °F)",
        "Relative Humidity (%) & Dew Point (°C)",
        "Precipitation Probability (%) & Peak Precipitation Amount (mm / inches)",
        "Wind Speed (km/h / mph) & Wind Gusts (km/h)",
        "Wind Direction (Degrees & Compass Bearing)",
        "Barometric Surface Pressure (hPa / inHg)",
        "Ultraviolet (UV) Radiation Index (0-11+ Scale)",
        "WMO Weather Interpretation Code (0-99 Standard Classifications)",
        "Travel & Outdoor Suitability Rating (LOW / MODERATE / HIGH / SEVERE)",
        "Derived Hazard Tags (e.g., Extreme Heat, Gale Wind, Thunderstorm, Freezing Rain)"
    ]
    for attr in attr_list:
        story.append(Paragraph(f"• &nbsp; {attr}", bullet_style))

    story.append(Spacer(1, 12))
    story.append(Paragraph("APPENDIX B: WEATHER RISK SEVERITY CLASSIFICATION", sec_heading))
    story.append(Paragraph("• &nbsp; <b>LOW:</b> Optimal conditions for travel and outdoor recreation. Calm to light winds (<20 km/h), zero or negligible precipitation probability (<15%), and comfortable thermal indices (15 °C to 25 °C).", bullet_style))
    story.append(Paragraph("• &nbsp; <b>MODERATE:</b> Unfavorable or changing weather. Gusty winds (20-40 km/h), light to moderate rain showers (15-50% probability), or marginal temperatures requiring protective outerwear.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>HIGH:</b> Hazardous conditions posing travel delays or discomfort. Heavy downpours, strong gale gusts (40-65 km/h), high heat index (>35 °C), dense fog with reduced visibility, or elevated thunderstorm risks. Advisories caution against exposed outdoor activities.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>SEVERE / EXTREME:</b> Life-threatening atmospheric events. Violent convective storms, severe gale winds (>65 km/h), blizzards, freezing rain, or flash flood potential. Direct recommendation to postpone travel and seek certified indoor shelter.", bullet_style))

    story.append(PageBreak())

    story.append(Paragraph("APPENDIX C: SYSTEM CONFIGURATION PARAMETERS", sec_heading))
    config_params = [
        "Default LLM Provider: Groq (Model: openai/gpt-oss-120b or llama-3.3-70b-versatile)",
        "Secondary Supported Providers: Google Gemini (GenerateContent REST), OpenRouter",
        "LLM Fallback Mode: Opt-in sequential fallback with token budget preservation",
        "Token Reservation Ceilings: 350 tokens (simple), 650 tokens (medium), 1200 tokens (complex)",
        "Monotonic Request Deadline: 12,000 milliseconds max per synthesis attempt",
        "Geocoding Cache TTL: 86,400 seconds (24 hours process-local memory)",
        "Current Weather Observation Cache TTL: 300 seconds (5 minutes)",
        "Hourly & Daily Forecast Cache TTL: 900 seconds (15 minutes)",
        "Backend Server Framework: FastAPI 0.115+ (Uvicorn ASGI runner)",
        "Frontend Workspace Framework: React 19.2+ & Vite 8.3+",
        "Database Engine: Embedded SQLite (skyreader.db) with WAL mode enabled",
        "Session Security: Cryptographically secure 43-character bearer tokens",
        "Audit Gate Rigor: Strict whole-draft claim extraction & clause-level semantic verification"
    ]
    for cp in config_params:
        story.append(Paragraph(f"• &nbsp; {cp}", bullet_style))

    story.append(Spacer(1, 14))
    story.append(Paragraph("APPENDIX D: PSEUDOCODE FOR INTENT ROUTING & PROOF GATE", sec_heading))
    
    pseudo_code = """<b>Algorithm 1: Request Planning and Grounded Evidence Verification</b>
<b>Input:</b> User Utterance U, Thread Context C, Expected Revision R
<b>Output:</b> Grounded Response T, Verification Proof P, New Revision R'

1:  <b>Validate</b> Session(BearerToken) and ConcurrencyLock(ThreadID, R)
2:  Intent, Locations, Horizon, Activity ← Router.Extract(U, C)
3:  <b>For each</b> Location in Locations:
4:      Coords ← Geocoder.Resolve(Location)
5:      <b>If</b> Coords is Ambiguous or Missing:
6:          <b>Return</b> ClarificationPrompt("Specify region or country", Status=400)
7:  Telemetry ← WeatherService.FetchScoped(Coords, Horizon)
8:  EvidencePacket ← EvidenceEngine.BuildPacket(Telemetry)
9:  <b>If</b> DeterministicPathAvailable(Intent, EvidencePacket):
10:     T ← RenderDeterministic(Telemetry, EvidencePacket)
11:     P ← EvidenceEngine.GenerateProof(T, EvidencePacket)
12: <b>Else:</b>
13:     Draft ← LLMGateway.Synthesize(U, EvidencePacket, BudgetLimit)
14:     Claims ← ClaimExtractor.Extract(Draft)
15:     AuditReport ← ClaimValidator.Validate(Claims, EvidencePacket)
16:     <b>If</b> AuditReport.IsTrustworthy <b>and</b> CompletenessCheck(Draft, Telemetry):
17:         T ← Draft
18:         P ← EvidenceEngine.AttachProof(AuditReport)
19:     <b>Else:</b>
20:         T ← GroundedRecovery.RenderFreshObservation(EvidencePacket)
21:         P ← EvidenceEngine.AttachRecoveryNotice("Explanation unverified; raw facts certified")
22: CommitRevision(ThreadID, R' = R + 1, Context=Update(C, Locations, Horizon))
23: <b>Return</b> (T, P, R')"""

    story.append(Paragraph(pseudo_code.replace("\n", "<br/>&nbsp;&nbsp;"), table_cell))

    story.append(Spacer(1, 14))
    story.append(Paragraph("APPENDIX E: SAMPLE SYSTEM OUTPUTS & TRACES", sec_heading))
    story.append(Paragraph("• &nbsp; <b>Execution Trace E.1 (Current Weather Query):</b> Query: \"What is the current weather in Dehradun?\" → Intent: <i>current_weather</i> → Geocoded: [30.3165°N, 78.0322°E] → Open-Meteo Cache Hit → Response: \"Observed conditions in Dehradun: Clear sky. Current weather in Dehradun: temperature 15.2 °C.\" → Claims Extracted: 2 → Verified: 2/2 (100% Grounded) → Status: DELIVERED.", bullet_style))
    story.append(Paragraph("• &nbsp; <b>Execution Trace E.2 (Two-City Comparison Query):</b> Query: \"Compare the weather in Lisbon and Madrid\" → Intent: <i>comparison</i> → Geocoded: Lisbon [38.7167°N, -9.1333°W], Madrid [40.4168°N, -3.7038°W] → Scoped Forecasts Retrieved → Risk Engine: Lisbon (LOW), Madrid (MODERATE, Strong Wind Hazard detected) → Claims Extracted: 10 → Verified: 10/10 (100% Grounded) → Status: DELIVERED with Attached Proof.", bullet_style))

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully generated at: {PDF_OUTPUT_PATH}")

if __name__ == "__main__":
    create_report()
