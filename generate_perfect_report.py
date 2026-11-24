import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.pdfgen import canvas

PDF_OUTPUT_PATH = r"C:\Users\upret\Desktop\sk\Sky-Reader\Sky_Reader_Project_Report.pdf"
ASSETS_DIR = r"C:\Users\upret\Desktop\sk\Sky-Reader\report_assets"
CHARTS_DIR = os.path.join(ASSETS_DIR, "charts")

# Custom page numbers dictionary to match reference PDF numbering exactly
PAGE_NUMBER_MAP = {
    1: "III",   # TOC 1
    2: "IV",   # TOC 2
    3: "V",    # TOC 3
    4: "VII",  # List of Figures
    5: "VIII", # Abbreviations
    6: "IX",   # Abstract
    7: "10",   # Chap 1: 1.1
    8: "11",   # 1.2, 1.3
    9: "12",   # 1.3 cont, 1.4
    10: "13",  # 1.5
    11: "14",  # Chap 2: 2.1, 2.2
    12: "15",  # 2.2 cont, 2.3
    13: "16",  # 2.4, 2.5
    14: "17",  # 2.6, 2.7
    15: "18",  # 2.8
    16: "19",  # Chap 3: 3.1 & Fig 3.1.1
    17: "20",  # 3.2 & Fig 3.2.1
    18: "21",  # 3.3 & Fig 3.3.1
    19: "22",  # 3.4, 3.5
    20: "23",  # 3.6 & Fig 3.6.1
    21: "24",  # 3.7, 3.8
    22: "25",  # Chap 4: 4.1, 4.2
    23: "26",  # 4.3, 4.4
    24: "27",  # Fig 4.4.1 & 4.5
    25: "28",  # Fig 4.5.1 & 4.6
    26: "29",  # Chap 5: 5.1
    27: "30",  # 5.2
    28: "31",  # 5.4 Final Remarks (Future scope omitted!)
    29: "32",  # References [1]-[7]
    30: "33",  # References [8]-[16]
    31: "34",  # References [17]-[20]
    32: "35",  # Appendix A, B
    33: "36",  # Appendix C, D
    34: "37",  # Appendix E
}

class ReferenceNumberedCanvas(canvas.Canvas):
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
            self.draw_page_decorations()
            super().showPage()
        super().save()

    def draw_page_decorations(self):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setStrokeColor(colors.HexColor("#94a3b8"))
        self.setLineWidth(0.5)

        # Footer line
        self.line(54, 45, 612 - 54, 45)

        # Footer text
        inst_text = "DEPARTMENT OF AI & ML, DR. APJ ABDUL KALAM INSTITUTE OF TECHNOLOGY"
        page_num_str = PAGE_NUMBER_MAP.get(self._pageNumber, str(self._pageNumber))

        self.setFillColor(colors.HexColor("#334155"))
        self.drawString(54, 32, inst_text)
        self.drawRightString(612 - 54, 32, page_num_str)
        self.restoreState()

def build_pdf():
    # Margins: 54 pt (0.75 in), bottom: 60 pt to clear footer cleanly
    doc = SimpleDocTemplate(
        PDF_OUTPUT_PATH,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=62
    )

    styles = getSampleStyleSheet()

    body = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14.5,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=7,
        alignment=4
    )

    bullet = ParagraphStyle(
        'DocBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1e293b'),
        leftIndent=18,
        firstLineIndent=-12,
        spaceAfter=5
    )

    title_main = ParagraphStyle(
        'DocTitleMain',
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=20,
        alignment=1,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=14
    )

    chap_heading = ParagraphStyle(
        'DocChapHeading',
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=18,
        alignment=1,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=14
    )

    sec_heading = ParagraphStyle(
        'DocSecHeading',
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=8,
        spaceAfter=5
    )

    caption_style = ParagraphStyle(
        'DocCaption',
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        alignment=1,
        textColor=colors.HexColor('#334155'),
        spaceBefore=6,
        spaceAfter=10
    )

    cell = ParagraphStyle(
        'TableCell',
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#1e293b')
    )

    cell_bold = ParagraphStyle(
        'TableCellBold',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#0f172a')
    )

    cell_dots = ParagraphStyle(
        'TableCellDots',
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#64748b')
    )

    story = []

    # Helper function for TOC rows
    def make_toc_row(label, dots, page, bold=False):
        c_style = cell_bold if bold else cell
        return [Paragraph(label, c_style), Paragraph(dots, cell_dots), Paragraph(page, c_style)]

    DOTS = ". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . ."

    # -------------------------------------------------------------------------
    # PAGE 1 (Reference Page 3): TABLE OF CONTENTS (Part 1)
    # -------------------------------------------------------------------------
    story.append(Paragraph("TABLE OF CONTENTS", title_main))
    story.append(Spacer(1, 10))

    toc_p1 = [
        make_toc_row("<b>ACKNOWLEDGEMENT</b>", DOTS, "<b>VI</b>", bold=True),
        make_toc_row("<b>LIST OF FIGURES</b>", DOTS, "<b>VII</b>", bold=True),
        make_toc_row("<b>ABBREVIATIONS</b>", DOTS, "<b>VIII</b>", bold=True),
        make_toc_row("<b>ABSTRACT</b>", DOTS, "<b>IX</b>", bold=True),
        make_toc_row("<b>Chapter 1: Introduction</b>", DOTS, "<b>10</b>", bold=True),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;1.1 Background of the Study", DOTS, "10"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;1.2 Meteorological & AI Domain Landscape", DOTS, "11"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;1.3 Problem Statement", DOTS, "11"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;1.4 Objectives of the Project", DOTS, "12"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;1.5 Scope of the Project", DOTS, "13"),
        make_toc_row("<b>Chapter 2: Literature Review</b>", DOTS, "<b>14</b>", bold=True),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;2.1 Introduction to Agentic Systems in Environmental QA", DOTS, "14"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;2.2 Traditional Weather Forecasting & API Portals", DOTS, "14"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;2.3 LLMs in Environmental & Domain-Specific Retrieval", DOTS, "15"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;2.4 Hallucination Mitigation & Claim Verification", DOTS, "16"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;2.5 RAG vs. Structured Evidence-Based Architectures", DOTS, "16"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;2.6 Multi-Provider LLM Gateway & Resilient Fallbacks", DOTS, "17"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;2.7 Streaming, Clause-Level Validation & Proof Gates", DOTS, "17"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;2.8 Visual Analytics & User Trust in Weather Dashboards", DOTS, "18"),
    ]
    t1 = Table(toc_p1, colWidths=[205, 255, 44])
    t1.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('ALIGN', (2,0), (2,-1), 'RIGHT'),
    ]))
    story.append(t1)
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 2 (Reference Page 4): TABLE OF CONTENTS (Part 2)
    # -------------------------------------------------------------------------
    story.append(Spacer(1, 10))
    toc_p2 = [
        make_toc_row("<b>Chapter 3: System Design and Methodology</b>", DOTS, "<b>19</b>", bold=True),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;3.1 Overview of the Proposed System", DOTS, "19"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;3.2 System Architecture", DOTS, "20"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;3.3 Technology Stack", DOTS, "21"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;3.4 Request Routing & Typed Geocoding Pipeline", DOTS, "22"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;3.5 Feature Engineering & Contextual Slots", DOTS, "22"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;3.6 Evidence Engine & Clause-Level Proof Gate", DOTS, "23"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;3.7 Grounded Recovery & Thresholding", DOTS, "24"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;3.8 Security & Concurrency Considerations", DOTS, "24"),
        make_toc_row("<b>Chapter 4: Results and Discussion</b>", DOTS, "<b>25</b>", bold=True),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;4.1 Experimental Setup", DOTS, "25"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;4.2 Benchmark Dataset Description", DOTS, "25"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;4.3 Performance Metrics", DOTS, "26"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;4.4 Results Analysis & Completeness Evaluation", DOTS, "26"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;4.5 Visualization and Dashboard Output", DOTS, "27"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;4.6 Discussion", DOTS, "28"),
        make_toc_row("<b>Chapter 5: Conclusion</b>", DOTS, "<b>29</b>", bold=True),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;5.1 Conclusion", DOTS, "29"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;5.2 Limitations of the System", DOTS, "30"),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;5.3 Final Remarks", DOTS, "31"),
    ]
    t2 = Table(toc_p2, colWidths=[205, 255, 44])
    t2.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('ALIGN', (2,0), (2,-1), 'RIGHT'),
    ]))
    story.append(t2)
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 3 (Reference Page 5): TABLE OF CONTENTS (Part 3)
    # -------------------------------------------------------------------------
    story.append(Spacer(1, 10))
    toc_p3 = [
        make_toc_row("<b>References</b>", DOTS, "<b>32</b>", bold=True),
        make_toc_row("<b>Appendix A</b>", DOTS, "<b>35</b>", bold=True),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;Weather Data Attributes & Schema", DOTS, "35"),
        make_toc_row("<b>Appendix B</b>", DOTS, "<b>35</b>", bold=True),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;Weather Risk Severity Classification", DOTS, "35"),
        make_toc_row("<b>Appendix C</b>", DOTS, "<b>36</b>", bold=True),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;System Configuration Parameters", DOTS, "36"),
        make_toc_row("<b>Appendix D</b>", DOTS, "<b>36</b>", bold=True),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;Pseudocode for Routing & Proof Gate", DOTS, "36"),
        make_toc_row("<b>Appendix E</b>", DOTS, "<b>37</b>", bold=True),
        make_toc_row("&nbsp;&nbsp;&nbsp;&nbsp;Sample Outputs & Execution Traces", DOTS, "37"),
    ]
    t3 = Table(toc_p3, colWidths=[205, 255, 44])
    t3.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('ALIGN', (2,0), (2,-1), 'RIGHT'),
    ]))
    story.append(t3)
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 4 (Reference Page 7): LIST OF FIGURES
    # -------------------------------------------------------------------------
    story.append(Paragraph("LIST OF FIGURES", title_main))
    story.append(Spacer(1, 14))

    lof = [
        make_toc_row("<b>3.1.1</b>", "<b>TIMELINE & SOLUTION OVERVIEW OF SKY READER</b>", "<b>19</b>", bold=True),
        make_toc_row("<b>3.2.1</b>", "<b>SYSTEM ARCHITECTURE OF SKY READER</b>", "<b>20</b>", bold=True),
        make_toc_row("<b>3.3.1</b>", "<b>TECHNICAL STACK & LAYER COMPOSITION</b>", "<b>21</b>", bold=True),
        make_toc_row("<b>3.6.1</b>", "<b>EVIDENCE VERIFICATION & CLAUSE-LEVEL PROOF GATE</b>", "<b>23</b>", bold=True),
        make_toc_row("<b>4.4.1</b>", "<b>BENCHMARK EVALUATION METRICS & ROUTING DISTRIBUTION</b>", "<b>27</b>", bold=True),
        make_toc_row("<b>4.5.1</b>", "<b>VIEW OF CITY LOOKUP & METEOROLOGICAL DASHBOARD</b>", "<b>28</b>", bold=True),
    ]
    t_lof = Table(lof, colWidths=[55, 395, 54])
    t_lof.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('ALIGN', (2,0), (2,-1), 'RIGHT'),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    story.append(t_lof)
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 5 (Reference Page 8): ABBREVIATIONS
    # -------------------------------------------------------------------------
    story.append(Paragraph("ABBREVIATIONS", title_main))
    story.append(Spacer(1, 14))

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
    for k, v in abbrevs:
        story.append(Paragraph(f"• &nbsp; <b>{k}</b> – {v}", bullet))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 6 (Reference Page 9): ABSTRACT
    # -------------------------------------------------------------------------
    story.append(Paragraph("ABSTRACT", title_main))
    story.append(Spacer(1, 12))

    story.append(Paragraph(
        "With the rapid growth of autonomous digital assistants and conversational interfaces, providing real-time, mission-critical environmental intelligence has become essential for personal planning, outdoor recreation, agriculture, and daily decision-making. However, standard Large Language Models (LLMs) frequently suffer from factual hallucinations, temporal staleness, and numerical inconsistencies when querying rapidly fluctuating atmospheric conditions. Traditional meteorological platforms, while numerically accurate, lack conversational adaptability, contextual reasoning, and personalized activity-specific risk guidance.",
        body
    ))
    story.append(Paragraph(
        "This project proposes <b>Sky Reader</b>, an evidence-grounded agentic weather intelligence system engineered to eliminate numerical hallucinations and bridge conversational reasoning with verified meteorological measurements. The system leverages behavioral features such as conversational intent, geographical coordinates, target forecast windows, and specific outdoor activity context to construct tailored atmospheric analyses.",
        body
    ))
    story.append(Paragraph(
        "An unsupervised evidence verification architecture using a structured <b>Evidence Engine</b> and clause-level semantic proof gates is employed to audit synthesized claims without requiring labeled hallucination training data. The proposed system integrates an asynchronous FastAPI backend for data processing, an embedded SQLite database with optimistic revision locks for conversation persistence, an intelligent request planner, process-local TTL caches, a multi-provider LLM gateway supporting Groq, Gemini, and OpenRouter, and a user-friendly React 19 dashboard for visualization, risk assessment, and provenance auditing.",
        body
    ))
    story.append(Paragraph(
        "The primary objective of this project is to enhance weather information reliability by enabling early detection of unsupported claims while eliminating false or unverified numerical statements. The system also provides explainable insights into detected weather hazards, allowing users to make informed, safe decisions. This approach demonstrates the practical application of agentic AI and formal evidence verification in strengthening domain-specific conversational systems, offering a scalable solution for real-world environmental intelligence.",
        body
    ))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 7 (Reference Page 10): CHAPTER 1 - INTRODUCTION / 1.1
    # -------------------------------------------------------------------------
    story.append(Paragraph("CHAPTER - 1 INTRODUCTION", chap_heading))
    story.append(Spacer(1, 8))

    story.append(Paragraph("1.1 Background of the Study", sec_heading))
    story.append(Paragraph(
        "With the rapid expansion of digital services, online conversational systems have become a fundamental component of modern computing environments. Almost every application—ranging from virtual assistants and search engines to enterprise travel management and agricultural logistics—relies on automated information retrieval mechanisms to deliver timely data to users. As the number of connected users and digital services increases, the volume of environmental and contextual queries processed daily has grown significantly. This growth has highlighted critical vulnerabilities in existing AI systems when dealing with time-sensitive and physically grounded real-world data.",
        body
    ))
    story.append(Paragraph(
        "Traditional information systems such as static weather tables, rule-based dashboards, and keyword-based weather widgets are no longer sufficient to satisfy the nuanced needs of modern users. Users do not merely require raw numerical measurements; they require contextual interpretation—such as whether current conditions permit safe travel between two distant cities, what outerwear is appropriate for changing conditions, or how impending rain will impact outdoor operations. While modern Large Language Models (LLMs) excel at natural language synthesis, their probabilistic architecture causes them to hallucinate plausible-sounding but erroneous temperatures, rain percentages, and storm alerts when queried on live conditions. As a result, conversational systems must evolve to combine fluent conversational capabilities with rigorous, evidence-grounded verification.",
        body
    ))
    story.append(Paragraph(
        "Agentic AI frameworks enable systems to combine natural language understanding with deterministic tool usage, querying external authoritative APIs in real time and verifying outputs before presentation. In the context of meteorological intelligence, attributes such as location coordinates, observation timestamps, temperature trends, wind gusts, and precipitation probabilities can be systematically captured, modeled, and verified. This project, titled <b>Sky Reader</b>, is motivated by the critical need to enhance environmental intelligence and conversational reliability through intelligent, evidence-grounded approaches.",
        body
    ))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 8 (Reference Page 11): 1.2 Threat/Domain Landscape & 1.3 Problem Statement
    # -------------------------------------------------------------------------
    story.append(Paragraph("1.2 Meteorological & AI Domain Landscape", sec_heading))
    story.append(Paragraph(
        "The application of conversational artificial intelligence to dynamic domain-specific tasks has increased dramatically in recent years. In environmental monitoring, severe risks arise when conversational models fabricate meteorological data. Common failure modes include numerical hallucinations, spatial conflation (attributing weather from one region to an identically named town elsewhere), temporal misalignment (conflating current conditions with multi-day forecasts), and hazard omissions (failing to alert travelers to gale gusts or lightning risks).",
        body
    ))
    story.append(Paragraph(
        "In critical outdoor scenarios, ungrounded advice can lead to severe real-world hazards, including travel strandings, heat exposure, or accidents during extreme convective storms. Furthermore, proprietary model providers suffer from intermittent outages, rate limitations, and unpredictable latency spikes. Relying entirely on a single closed provider introduces unacceptable single-point-of-failure vulnerabilities.",
        body
    ))
    story.append(Paragraph(
        "Reports from AI reliability and benchmarking consortia indicate that standard Retrieval-Augmented Generation (RAG) pipelines fail to eliminate numerical fabrication in tabular and quantitative domains. This highlights the vital importance of continuous, clause-level evidence verification rather than relying solely on prompting guardrails. Structured evidence verification has therefore emerged as an indispensable component of trustworthy AI strategies, ensuring that every delivered claim is strictly backed by authoritative sensor observations.",
        body
    ))

    story.append(Paragraph("1.3 Problem Statement", sec_heading))
    story.append(Paragraph(
        "Despite advancements in conversational AI and open environmental APIs, existing weather intelligence solutions face severe limitations. Conventional weather websites provide accurate tabular metrics but lack conversational adaptability, multi-turn reasoning, and cross-city comparative planning. Conversely, modern generative AI chatbots produce fluid responses but frequently hallucinate exact numerical readings, presenting fabricated forecasts with unwarranted confidence.",
        body
    ))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 9 (Reference Page 12): 1.3 cont. & 1.4 Objectives
    # -------------------------------------------------------------------------
    story.append(Paragraph(
        "Another major challenge is the lack of adaptability and resilience in traditional systems. Existing API integrations depend on rigid prompt wrappers around a single proprietary model provider, offering no automatic fallback when rate limits or transient network errors occur. Furthermore, when language models generate verbose explanations, existing systems fail to inspect individual generated clauses for factual accuracy, making it impossible for users to discern verified observations from speculative prose.",
        body
    ))
    story.append(Paragraph(
        "The problem addressed in this project is the urgent need for an intelligent, adaptive, and explainable conversational weather intelligence system that can automatically retrieve live meteorological telemetry, synthesize qualitative insights across multiple providers, and rigorously audit every output clause in real time while guaranteeing zero numerical hallucinations.",
        body
    ))

    story.append(Paragraph("1.4 Objectives of the Project", sec_heading))
    story.append(Paragraph(
        "The primary objective of the <b>Sky Reader</b> project is to design, implement, and evaluate an evidence-grounded agentic weather intelligence platform. The specific objectives are as follows:",
        body
    ))
    story.append(Paragraph("• &nbsp; To analyze natural language weather queries and extract relevant conversational features, intents, locations, and time horizons.", bullet))
    story.append(Paragraph("• &nbsp; To interface with authoritative Open-Meteo APIs using non-blocking asynchronous clients and multi-tier process-local TTL caches.", bullet))
    story.append(Paragraph("• &nbsp; To design a resilient multi-provider LLM gateway supporting Groq, Google Gemini, and OpenRouter with unified token and latency budgets.", bullet))
    story.append(Paragraph("• &nbsp; To develop a structured Evidence Engine that performs whole-draft auditing, completeness evaluation, and clause-level proof gating.", bullet))
    story.append(Paragraph("• &nbsp; To engineer a deterministic grounded recovery mechanism that seamlessly replaces unverified model drafts with factual observations.", bullet))
    story.append(Paragraph("• &nbsp; To design a user-friendly, responsive React 19 interface featuring live atmospheric simulations, risk assessment cards, and provenance audit drawers.", bullet))
    story.append(Paragraph("• &nbsp; To ensure the architecture is scalable, modular, and verified against frozen offline regression suites.", bullet))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 10 (Reference Page 13): 1.5 Scope of the Project
    # -------------------------------------------------------------------------
    story.append(Paragraph("1.5 Scope of the Project", sec_heading))
    story.append(Paragraph(
        "The scope of this project is focused on real-time conversational weather retrieval, multi-destination comparisons, activity-based risk modeling, and factual evidence verification using modern web and agentic AI architectures. The system focuses on atmospheric telemetry—including surface temperature, apparent feel, precipitation probability, rainfall accumulation, wind velocity, wind gusts, relative humidity, UV index, and WMO weather codes—and does not perform long-range climate reanalysis or custom numerical weather prediction modeling.",
        body
    ))
    story.append(Paragraph(
        "The proposed solution is designed as a modular, full-stack application comprising an asynchronous FastAPI backend, an embedded SQLite database with optimistic revision locks for conversation persistence, and a reactive React 19 client workspace. The project uses unsupervised evidence verification techniques, making it suitable for production environments where pre-labeled hallucination training data is completely unavailable.",
        body
    ))
    story.append(Paragraph(
        "While the system demonstrates exceptionally effective anomaly interception and zero-hallucination guarantees, it does not aim to replace official governmental meteorological emergency warning feeds, but rather to complement them by adding an intelligent, interactive, and transparent conversational interaction layer for everyday users, travelers, and decision-makers.",
        body
    ))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 11 (Reference Page 14): CHAPTER 2 - LITERATURE REVIEW / 2.1, 2.2
    # -------------------------------------------------------------------------
    story.append(Paragraph("CHAPTER – 2 LITERATURE REVIEW", chap_heading))
    story.append(Spacer(1, 8))

    story.append(Paragraph("2.1 Introduction to Agentic Systems in Environmental QA", sec_heading))
    story.append(Paragraph(
        "Environmental question answering is a critical area of research at the intersection of natural language processing and meteorological sciences. Unlike traditional information retrieval systems that rely on static keyword indices, modern conversational systems aim to interpret complex, multi-faceted user intents and synthesize contextual answers. In meteorological domains, queries often include relative timeframes ('this weekend', 'in 3 hours'), multi-destination comparisons ('is Lisbon warmer than Madrid?'), or subjective activity suitability ('is it safe to cycle this afternoon?').",
        body
    ))
    story.append(Paragraph(
        "Early conversational systems were primarily rule-based or statistical pattern matchers, relying on static intent classifiers and slot-filling templates. However, these methods struggled with complex linguistic variations, spatial ambiguity, and conversational follow-ups. With the emergence of Large Language Models (LLMs) and agentic workflows, researchers began applying reasoning-and-acting (ReAct) frameworks that automatically orchestrate API calls, interpret responses, and communicate answers in natural language.",
        body
    ))

    story.append(Paragraph("2.2 Traditional Weather Forecasting & API Portals", sec_heading))
    story.append(Paragraph(
        "Traditional digital weather forecasting platforms rely on numerical weather prediction (NWP) models operated by global meteorological agencies such as NOAA, ECMWF, and national weather services. Modern open APIs, such as Open-Meteo, democratize access to these supercomputer models by providing high-resolution hourly and daily forecasts via RESTful endpoints without proprietary licensing hurdles.",
        body
    ))
    story.append(Paragraph(
        "While computationally rigorous, traditional web portals present data through static tables, line graphs, and radar maps. Users are forced to manually parse dozens of metrics—such as dew point, barometric pressure, and precipitation probability—and perform mental arithmetic to deduce whether conditions meet their personal criteria. Furthermore, these platforms lack conversational memory, making iterative travel planning cumbersome.",
        body
    ))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 12 (Reference Page 15): 2.2 cont. & 2.3 LLMs in Environmental QA
    # -------------------------------------------------------------------------
    story.append(Paragraph(
        "Rule-based alerting systems deployed in traditional portals rely on rigid, expert-defined thresholds, such as flagging high wind only when velocities exceed a static cutoff. Although effective for standardized meteorological advisories, these systems fail to adapt to user-specific contexts, such as distinguishing the wind sensitivity of cycling versus driving an automobile. Moreover, maintaining complex rule hierarchies across diverse geographical zones becomes increasingly intractable as applications scale.",
        body
    ))
    story.append(Paragraph(
        "These limitations motivated the transition toward intelligent, data-driven conversational architectures that can dynamically contextualize meteorological data while preserving absolute factual rigor.",
        body
    ))

    story.append(Paragraph("2.3 LLMs in Environmental & Domain-Specific Retrieval", sec_heading))
    story.append(Paragraph(
        "Large Language Models have demonstrated unprecedented capabilities in contextual comprehension, multi-step reasoning, and qualitative synthesis. When applied to domain-specific question answering, LLMs can bridge the gap between technical metrics and human decision-making, explaining atmospheric phenomena in accessible terms.",
        body
    ))
    story.append(Paragraph(
        "However, extensive research has documented the vulnerability of LLMs to factual hallucination—generating convincing statements that have no basis in reality. In quantitative and physical domains, this vulnerability is acute. LLMs lack internal grounding in real-time physical states; when prompted for current weather without external tools, they generate fictitious numbers that align statistically with historical training text but bear no correlation with live atmospheric conditions.",
        body
    ))
    story.append(Paragraph(
        "To mitigate this, researchers have developed tool-augmented architectures where models generate structured function calls to retrieve live data before generating answers. Nevertheless, empirical studies reveal that even when provided with accurate tool outputs, LLMs frequently misread, round incorrectly, or invent extraneous details during text synthesis, highlighting the critical need for independent, post-generation verification.",
        body
    ))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 13 (Reference Page 16): 2.4 Hallucination Mitigation & 2.5 RAG vs Evidence
    # -------------------------------------------------------------------------
    story.append(Paragraph("2.4 Hallucination Mitigation & Claim Verification", sec_heading))
    story.append(Paragraph(
        "Mitigating hallucinations in conversational AI has become a premier research priority. Automated claim verification frameworks decompose model responses into atomic, self-contained claims and validate them against authoritative ground truth. Unlike classification models that output a generic probability score, atomic claim verification produces interpretable, fine-grained judgments for every statement.",
        body
    ))
    story.append(Paragraph(
        "Recent advances include Chain-of-Verification (CoVe) and automated fact-checking pipelines such as FEVER. However, when applied to dynamic real-time streams, prompt-based self-verification increases token consumption, doubles inference latency, and remains susceptible to the model's own biases. External, deterministic claim validators that compare extracted variables (e.g., temperature, wind speed) directly against structured API payloads provide vastly superior guarantees, operating in sub-millisecond execution times without additional LLM overhead.",
        body
    ))

    story.append(Paragraph("2.5 RAG vs. Structured Evidence-Based Architectures", sec_heading))
    story.append(Paragraph(
        "Retrieval-Augmented Generation (RAG) is widely adopted for document-grounded question answering. Standard RAG indexes unstructured text chunks into vector embeddings and retrieves semantically similar passages using cosine distance metrics. While effective for knowledge bases and policy documents, vector-based RAG suffers severe deficiencies when applied to numerical meteorological telemetry.",
        body
    ))
    story.append(Paragraph(
        "Vector embeddings cannot perform mathematical comparisons, temporal filtering, or coordinate distance calculations. Retrieving a text snippet stating that 'Madrid was 28 °C last Tuesday' provides no guarantee that the model will not cite that figure when asked about today's forecast. In contrast, Structured Evidence Architectures represent facts as discrete, typed data contracts containing exact timestamps, geographic coordinates, measurement keys, physical units, and source IDs. This guarantees mathematical precision and enables deterministic, zero-tolerance verification.",
        body
    ))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 14 (Reference Page 17): 2.6 Multi-Provider LLM & 2.7 Streaming Validation
    # -------------------------------------------------------------------------
    story.append(Paragraph("2.6 Multi-Provider LLM Gateway & Resilient Fallbacks", sec_heading))
    story.append(Paragraph(
        "Commercial deployments of conversational agents cannot afford single-point dependencies on individual AI infrastructure providers. Model providers frequently experience localized rate limits, quota exhaustion, maintenance windows, and transient network timeouts. Multi-provider gateway architectures address this vulnerability by decoupling application logic from underlying model APIs.",
        body
    ))
    story.append(Paragraph(
        "Research in gateway engineering emphasizes the importance of unified request budgets, standardized message schemas, and replay-safe fallback policies. By routing requests across diverse providers—such as Groq's high-speed inference engine, Google Gemini's multimodal REST API, and OpenRouter's distributed network—systems achieve high availability and consistent latency profiles while enforcing strict per-request token caps.",
        body
    ))

    story.append(Paragraph("2.7 Streaming, Clause-Level Validation & Proof Gates", sec_heading))
    story.append(Paragraph(
        "Modern conversational systems operate in real time, requiring minimal latency between user input and token generation. Whole-document auditing methods introduce unacceptable delays, as the entire response must be generated before verification can begin. Clause-level semantic gating inspects text at fine-grained syntactic boundaries.",
        body
    ))
    story.append(Paragraph(
        "By evaluating individual weather-shaped clauses against structured evidence, the system can detect factual divergence immediately. If an unsupported assertion is identified, the proof gate can halt the stream and substitute a verified deterministic observation, preventing erroneous information from reaching the user while maintaining a smooth conversational experience.",
        body
    ))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 15 (Reference Page 18): 2.8 Visual Analytics
    # -------------------------------------------------------------------------
    story.append(Paragraph("2.8 Visual Analytics for Weather Intelligence", sec_heading))
    story.append(Paragraph(
        "Visual analytics plays a crucial role in helping users interpret meteorological data and understand AI decisions. Research surveys emphasize the importance of interactive dashboards, weather timelines, risk gauges, and provenance indicators in establishing user trust. Visualization bridges the gap between raw automated telemetry and human decision-making.",
        body
    ))
    story.append(Paragraph(
        "Effective visual analytics platforms present live atmospheric observations, 24-hour forecast trends, color-coded hazard indicators, and detailed audit trails in an intuitive layout. Visual elements such as animated atmospheric simulations, expandable proof drawers, and quantitative confidence scores significantly reduce cognitive load, allowing users to make rapid, safety-critical decisions. However, many existing systems focus solely on raw text outputs and completely neglect visualization and transparency.",
        body
    ))
    story.append(Paragraph(
        "In summary, the literature clearly establishes the necessity for an integrated system that combines structured meteorological retrieval, multi-provider resiliency, clause-level factual verification, and rich visual analytics. These foundational principles directly guide the architectural design and implementation of <b>Sky Reader</b>.",
        body
    ))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 16 (Reference Page 19): CHAPTER 3 - SYSTEM DESIGN / 3.1 & Fig 3.1.1
    # -------------------------------------------------------------------------
    story.append(Paragraph("CHAPTER - 3 SYSTEM DESIGN AND METHODOLOGY", chap_heading))
    story.append(Spacer(1, 8))

    story.append(Paragraph("3.1 Overview of the Proposed System", sec_heading))
    story.append(Paragraph(
        "The <b>Sky Reader</b> system is designed as a modular, scalable, and verifiable agentic platform for conversational weather intelligence. The system continuously processes natural language utterances, extracts conversational intents and spatiotemporal constraints, fetches authoritative atmospheric telemetry from Open-Meteo APIs, computes localized hazard risks, and generates factually verified answers. The proposed approach does not rely on static prompt templates or ungrounded generative models, ensuring that every delivered statement is backed by immutable physical observations.",
        body
    ))
    story.append(Paragraph(
        "The system architecture follows a layered design consisting of client presentation, API validation, session management, routing and planning, weather service caching, evidence auditing, and multi-provider synthesis. Each module is loosely coupled, allowing independent testing, maintenance, and future expansion. The system supports both registered user accounts and guest workspaces through cryptographically secure session tokens.",
        body
    ))

    # Figure 3.1.1
    fig_3_1_1_path = os.path.join(CHARTS_DIR, "fig_3_1_1_solution_overview.png")
    if os.path.exists(fig_3_1_1_path):
        story.append(Spacer(1, 4))
        story.append(Image(fig_3_1_1_path, width=460, height=190))
        story.append(Paragraph("Figure 3.1.1 Timeline & Solution Overview of Sky Reader", caption_style))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 17 (Reference Page 20): 3.2 System Architecture & Fig 3.2.1
    # -------------------------------------------------------------------------
    story.append(Paragraph("3.2 System Architecture", sec_heading))
    story.append(Paragraph(
        "The overall system architecture is illustrated in <b>Figure 3.2.1</b>. It consists of the following major components:",
        body
    ))
    story.append(Paragraph("• &nbsp; <b>User Interface Layer:</b> Built in React 19, handling user chat, interactive city lookups, atmospheric animations, and provenance inspection.", bullet))
    story.append(Paragraph("• &nbsp; <b>Backend API Gateway:</b> FastAPI application managing request validation, CORS, authentication headers, and routing.", bullet))
    story.append(Paragraph("• &nbsp; <b>Database & Session Layer:</b> SQLite database persisting user accounts, authentication tokens, and conversation threads with revision counters.", bullet))
    story.append(Paragraph("• &nbsp; <b>Request Router & Shared Planner:</b> Parses intent, resolves geographical coordinates, and establishes local forecast horizons.", bullet))
    story.append(Paragraph("• &nbsp; <b>Weather Service & TTL Caches:</b> Asynchronously communicates with Open-Meteo, caching geocoding and forecast payloads.", bullet))
    story.append(Paragraph("• &nbsp; <b>Evidence & Audit Engine:</b> Extracts claims from model drafts, validates them against evidence packets, and attaches verification proof.", bullet))

    # Figure 3.2.1
    fig_3_2_1_path = os.path.join(CHARTS_DIR, "fig_3_2_1_system_architecture.png")
    if os.path.exists(fig_3_2_1_path):
        story.append(Spacer(1, 4))
        story.append(Image(fig_3_2_1_path, width=465, height=260))
        story.append(Paragraph("Figure 3.2.1 System Architecture of Sky Reader", caption_style))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 18 (Reference Page 21): 3.3 Technology Stack & Fig 3.3.1
    # -------------------------------------------------------------------------
    story.append(Paragraph("3.3 Technology Stack", sec_heading))
    story.append(Paragraph(
        "The system is implemented using modern web, backend, and machine learning technologies selected for performance, scalability, and ease of integration.",
        body
    ))

    # Figure 3.3.1
    fig_3_3_1_path = os.path.join(CHARTS_DIR, "fig_3_3_1_tech_stack.png")
    if os.path.exists(fig_3_3_1_path):
        story.append(Spacer(1, 4))
        story.append(Image(fig_3_3_1_path, width=460, height=190))
        story.append(Paragraph("Figure 3.3.1 Technical Stack", caption_style))

    story.append(Paragraph("• &nbsp; <b>Frontend:</b> React 19 is used to build a responsive and interactive user interface. Vite serves as the modern build tool, and Lucide React provides meteorological and system iconography.", bullet))
    story.append(Paragraph("• &nbsp; <b>Backend:</b> FastAPI is used to develop RESTful APIs that handle authentication, request validation, weather analysis, and coordination with the Evidence Engine.", bullet))
    story.append(Paragraph("• &nbsp; <b>Database:</b> SQLite is used to store user profiles, session tokens, and thread context metadata due to its zero-configuration simplicity and ACID compliance.", bullet))
    story.append(Paragraph("• &nbsp; <b>Authentication:</b> Cryptographically secure bearer tokens (43-character tokens) are used to implement session management and thread ownership control.", bullet))
    story.append(Paragraph("• &nbsp; <b>Machine Learning & LLM:</b> Multi-provider gateway integrating Groq, Google Gemini, and OpenRouter, paired with a custom Evidence Engine for factual verification.", bullet))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 19 (Reference Page 22): 3.4 Data & 3.5 Feature Engineering
    # -------------------------------------------------------------------------
    story.append(Paragraph("3.4 Data Collection and Preprocessing", sec_heading))
    story.append(Paragraph(
        "Meteorological events processed by the system are sourced from Open-Meteo global weather APIs. Raw telemetry includes surface temperature, apparent feel, precipitation probability, precipitation amount, wind speed, wind gusts, wind direction, surface pressure, UV index, and standard WMO weather codes. Raw API responses contain dense time-series arrays and floating-point values that must be processed before conversational consumption.",
        body
    ))
    story.append(Paragraph("Preprocessing steps include:", body))
    story.append(Paragraph("• &nbsp; Coordinate validation and boundary bounding.", bullet))
    story.append(Paragraph("• &nbsp; Conversion of UTC timestamps into destination-local time offsets.", bullet))
    story.append(Paragraph("• &nbsp; Handling missing or null sensor values with graceful interpolations.", bullet))
    story.append(Paragraph("• &nbsp; Mapping WMO numerical codes into human-readable meteorological descriptions.", bullet))
    story.append(Paragraph("• &nbsp; Normalization of physical units according to user preferences (°C / °F, km/h / mph).", bullet))
    story.append(Paragraph(
        "These steps ensure that the telemetry fed into the Evidence Engine and agent planner is consistent and reliable.",
        body
    ))

    story.append(Paragraph("3.5 Feature Engineering", sec_heading))
    story.append(Paragraph(
        "Feature engineering plays a crucial role in understanding user queries and evaluating environmental safety. The following behavioral features are extracted from incoming requests and weather logs:",
        body
    ))
    story.append(Paragraph("• &nbsp; Conversational intent (current weather, hourly forecast, multi-city comparison, outdoor risk).", bullet))
    story.append(Paragraph("• &nbsp; Spatiotemporal horizon (instantaneous observation, relative 1-hour window, multi-day span).", bullet))
    story.append(Paragraph("• &nbsp; Thermal stress index (temperature deviation from seasonal baselines, apparent feel).", bullet))
    story.append(Paragraph("• &nbsp; Convective and precipitation severity index (rainfall rate, thunderstorm codes).", bullet))
    story.append(Paragraph("• &nbsp; Outdoor activity context (cycling, running, open-air dining, long-distance road transit).", bullet))
    story.append(Paragraph(
        "These features capture both physical atmospheric conditions and user-centric contextual requirements, enabling the system to evaluate travel suitability effectively.",
        body
    ))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 20 (Reference Page 23): 3.6 Evidence Engine / Proof Gate & Fig 3.6.1
    # -------------------------------------------------------------------------
    story.append(Paragraph("3.6 Clause-Level Evidence Gate Algorithm", sec_heading))
    story.append(Paragraph(
        "The core innovation of Sky Reader is its <b>Evidence Engine</b>. Rather than assuming that language model outputs are inherently truthful, the system treats model drafts as unverified candidate hypotheses. The engine constructs a multiple-layer verification pipeline that isolates factual claims and tests them against the immutable Open-Meteo evidence packet.",
        body
    ))
    story.append(Paragraph(
        "The verification score is computed based on claim accuracy, temporal alignment, and required hazard coverage. Statements with complete empirical backing are certified, while drafts containing unverified or contradicted figures are rejected by the proof gate.",
        body
    ))

    # Figure 3.6.1 (Evidence gate)
    fig_3_5_1_path = os.path.join(CHARTS_DIR, "fig_3_5_1_evidence_gate.png")
    if os.path.exists(fig_3_5_1_path):
        story.append(Spacer(1, 4))
        story.append(Image(fig_3_5_1_path, width=460, height=210))
        story.append(Paragraph("Figure 3.6.1 Evidence Verification & Clause-Level Proof Gate", caption_style))

    story.append(Paragraph(
        "The Evidence Engine is chosen due to its mathematical rigor, sub-millisecond execution efficiency, and ability to enforce zero-tolerance numerical hallucination policies without requiring labeled training datasets.",
        body
    ))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 21 (Reference Page 24): 3.7 Grounded Recovery & 3.8 Security
    # -------------------------------------------------------------------------
    story.append(Paragraph("3.7 Anomaly Scoring and Grounded Recovery", sec_heading))
    story.append(Paragraph(
        "Each conversational draft processed by the Evidence Engine is assigned a factual trust score. The system uses deterministic validation rules to classify candidate statements into verified and ungrounded categories. Severity risk levels—such as low, moderate, high, and severe—are computed by the Risk Engine based on wind speeds, precipitation peaks, and thermal stress.",
        body
    ))
    story.append(Paragraph(
        "When an LLM-synthesized draft fails the final clause gate due to an unsupported assertion, Sky Reader triggers its <b>Grounded Recovery</b> pathway. Instead of returning an error, the system automatically renders a fresh, concise response directly from the single verified observation. This recovery mechanism guarantees that users always receive factual weather telemetry while being transparently notified that extended prose could not be verified.",
        body
    ))

    story.append(Paragraph("3.8 Security Considerations", sec_heading))
    story.append(Paragraph(
        "Security is a critical aspect of the system design. Passwords are stored using strong cryptographic one-way hashing algorithms, and all client-server communications are conducted over secure HTTP/HTTPS channels. Bearer token-based session management ensures that only authenticated users can access private conversation histories.",
        body
    ))
    story.append(Paragraph(
        "Role-based access separation distinguishes registered user accounts from guest sessions. Furthermore, thread context writes are governed by optimistic concurrency revision locks: each thread maintains an incremental revision counter, preventing race conditions and stale writes when multiple browser tabs interact simultaneously.",
        body
    ))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 22 (Reference Page 25): CHAPTER 4 - RESULTS / 4.1, 4.2
    # -------------------------------------------------------------------------
    story.append(Paragraph("CHAPTER - 4 RESULTS AND DISCUSSION", chap_heading))
    story.append(Spacer(1, 8))

    story.append(Paragraph("4.1 Experimental Setup", sec_heading))
    story.append(Paragraph(
        "The experimental evaluation of the <b>Sky Reader</b> system was conducted using both live deployment environments and controlled offline regression harnesses. The system was deployed in a local development environment utilizing the FastAPI backend, an embedded SQLite database, and the Vite-powered React 19 frontend.",
        body
    ))
    story.append(Paragraph(
        "Meteorological events and natural language queries were processed in real time and evaluated by the Evidence Engine. The evaluation examined routing precision, geocoding resolution, answer completeness, hazard recall, and factual grounding across diverse question categories.",
        body
    ))

    story.append(Paragraph("4.2 Dataset Description", sec_heading))
    story.append(Paragraph(
        "The dataset used for systematic evaluation consists of the <b>frozen Stage 1.7E evaluation corpus</b> comprising <b>120 distinct held-out test cases</b> collected and curated across twelve balanced operational categories. Each test record represents a realistic user scenario, containing conversational utterances, expected destination coordinates, target forecast windows, required measurements, and ground truth weather conditions.",
        body
    ))
    story.append(Paragraph(
        "The corpus primarily contains standard weather queries, complemented by challenging edge cases such as identically named cities in different countries (e.g., Córdoba in Spain vs. Argentina), misspelled city names, convective thunderstorm alerts, severe wind gusts, truncated forecast horizons, and upstream provider rate-limit simulations. This realistic distribution reflects real-world conditions where ambiguous phrasing and volatile weather must be handled without failure.",
        body
    ))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 23 (Reference Page 26): 4.3 Metrics & 4.4 Results Analysis
    # -------------------------------------------------------------------------
    story.append(Paragraph("4.3 Performance Metrics", sec_heading))
    story.append(Paragraph(
        "To rigorously quantify the effectiveness and reliability of Sky Reader, system performance was evaluated using the following metrics:",
        body
    ))
    story.append(Paragraph("• &nbsp; <b>Answer Completeness Rate:</b> Percentage of user requests where all requested variables, target locations, and time windows are fully answered.", bullet))
    story.append(Paragraph("• &nbsp; <b>Hazard & Safety Recall:</b> Percentage of active meteorological hazards (e.g., severe storms, gale winds) correctly identified and communicated.", bullet))
    story.append(Paragraph("• &nbsp; <b>Grounded Audit Rate:</b> Percentage of delivered numerical claims verified against underlying Open-Meteo telemetry with 100% precision.", bullet))
    story.append(Paragraph("• &nbsp; <b>Unaudited Numerical Claim Count:</b> Absolute number of numerical claims delivered without passing through the Evidence Engine.", bullet))
    story.append(Paragraph("• &nbsp; <b>Average Processing Latency:</b> Time taken to route, retrieve telemetry, audit, and render responses.", bullet))

    story.append(Paragraph("4.4 Results Analysis", sec_heading))
    story.append(Paragraph(
        "The experimental results demonstrated that Sky Reader effectively resolved user intents, retrieved authoritative telemetry, and eliminated numerical hallucinations. Queries regarding current weather and forecast windows achieved exceptional accuracy. The system achieved an <b>overall answer completeness rate of 84.2% (101/120 cases)</b> and a <b>100% hazard recall rate (12/12 severe cases)</b>.",
        body
    ))
    story.append(Paragraph(
        "Crucially, the Evidence Engine achieved a <b>100% pass rate on grounded audited outputs (88/88 candidate drafts)</b>, resulting in <b>exactly zero unaudited numerical weather claims delivered</b>. The average processing latency for complete weather answers without external LLM overhead was approximately 6.65 ms, proving that the system is exceptionally well-suited for real-time deployment.",
        body
    ))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 24 (Reference Page 27): Fig 4.4.1 & 4.5 Visualization
    # -------------------------------------------------------------------------
    # Figure 4.4.1
    fig_4_4_1_path = os.path.join(CHARTS_DIR, "fig_4_4_1_evaluation_metrics.png")
    if os.path.exists(fig_4_4_1_path):
        story.append(Image(fig_4_4_1_path, width=470, height=190))
        story.append(Paragraph("Figure 4.4.1 Anomaly Score & Benchmark Metrics Distribution", caption_style))

    story.append(Paragraph("4.5 Visualization and Dashboard Output", sec_heading))
    story.append(Paragraph(
        "The system includes an intuitive administrative and conversational dashboard that presents real-time weather telemetry and evidence verification results in an intuitive manner. The dashboard displays current observations, 24-hour forecast timelines, calculated risk levels, and detailed provenance logs.",
        body
    ))
    story.append(Paragraph(
        "Visual indicators such as color-coded risk tags (LOW in green, MODERATE in amber, HIGH in red) help users instantly recognize adverse atmospheric conditions. Expandable proof drawers allow users to inspect the exact API source and timestamp behind every statement, enhancing system transparency and establishing deep user trust.",
        body
    ))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 25 (Reference Page 28): Fig 4.5.1 & 4.6 Discussion
    # -------------------------------------------------------------------------
    # Figure 4.5.1
    fig_city_path = os.path.join(ASSETS_DIR, "fig_city_lookup.png")
    if os.path.exists(fig_city_path):
        story.append(Image(fig_city_path, width=410, height=274))
        story.append(Paragraph("Figure 4.5.1 View of City Lookup & Meteorological Dashboard", caption_style))

    story.append(Paragraph("4.6 Discussion", sec_heading))
    story.append(Paragraph(
        "The experimental results demonstrate that combining deterministic routing with post-generation semantic auditing is highly effective in eliminating conversational hallucinations without sacrificing linguistic fluency. Open-Meteo proved to be an ideal data provider due to its open access, global coverage, and sub-second response times.",
        body
    ))
    story.append(Paragraph(
        "However, some operational challenges were observed. Highly colloquial phrasing or complex multi-clause sentences occasionally triggered conservative rejections in the final clause gate, causing the system to fall back to deterministic answers. This highlights the value of continuing to expand semantic grammar definitions. Overall, the results validate the feasibility and robustness of the proposed system as a practical, production-ready weather intelligence solution.",
        body
    ))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 26 (Reference Page 29): CHAPTER 5 - CONCLUSION / 5.1
    # -------------------------------------------------------------------------
    story.append(Paragraph("CHAPTER - 5 CONCLUSION", chap_heading))
    story.append(Spacer(1, 8))

    story.append(Paragraph("5.1 Conclusion", sec_heading))
    story.append(Paragraph(
        "With the increasing reliance on digital platforms and conversational AI services, securing the factual accuracy of environmental and weather information systems has become a critical challenge. Traditional generative AI models frequently fail to provide reliable numerical data due to their propensity for factual hallucination and temporal disconnect. In this context, the <b>Sky Reader</b> project demonstrates the immense effectiveness of combining agentic request planning with formal evidence verification.",
        body
    ))
    story.append(Paragraph(
        "This project proposed an evidence-grounded weather intelligence system that analyzes conversational user queries, extracts spatiotemporal requirements, and retrieves verified meteorological telemetry from Open-Meteo. By leveraging a structured Evidence Engine and clause-level semantic proof gates, the system is capable of verifying generated answers without requiring expensive labeled attack or hallucination datasets. This makes the proposed solution highly practical for real-world production environments where dynamic atmospheric conditions evolve continuously.",
        body
    ))
    story.append(Paragraph(
        "The experimental results confirm that the system achieves an 84.2% answer completeness rate, 100% hazard recall, and exactly zero unaudited numerical claims while maintaining minimal processing latency. The inclusion of an interactive React 19 dashboard further enhances usability by enabling users to explore hourly timelines, inspect risk ratings, and review provenance verification proof.",
        body
    ))
    story.append(Paragraph(
        "Overall, Sky Reader successfully demonstrates how software engineering rigor and formal verification can be applied to strengthen conversational AI security. The project highlights the paramount importance of structured evidence analysis in modern conversational systems.",
        body
    ))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 27 (Reference Page 30): 5.2 Limitations (Future Scope OMITTED!)
    # -------------------------------------------------------------------------
    story.append(Paragraph("5.2 Limitations of the System", sec_heading))
    story.append(Paragraph(
        "Despite its high effectiveness, the proposed system has certain limitations. The clause-level evidence gate may occasionally reject legitimate model drafts that express verified facts in non-standard colloquial idioms, falling back to basic deterministic summaries. While this conservative approach guarantees zero numerical hallucinations, it can occasionally reduce conversational variety.",
        body
    ))
    story.append(Paragraph(
        "Additionally, external multi-provider routing on free-tier endpoints (such as OpenRouter free-tier models) can occasionally experience upstream HTTP 404 or capacity limits during peak internet usage, necessitating fallback to primary Groq adapters. Furthermore, the system currently caches telemetry in process-local memory; deploying across distributed multi-server clusters would require external distributed caching infrastructure to synchronize cache states.",
        body
    ))
    story.append(Paragraph(
        "Finally, geographical disambiguation currently relies on explicit country qualifiers when identically named municipalities exist. Without an explicit qualifier, the system requires an additional conversational clarification turn from the user before proceeding.",
        body
    ))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 28 (Reference Page 31): 5.3 Final Remarks (Future Scope OMITTED!)
    # -------------------------------------------------------------------------
    story.append(Paragraph("5.3 Final Remarks", sec_heading))
    story.append(Paragraph(
        "The <b>Sky Reader</b> project serves as a compelling and practical example of applying agentic AI, robust API engineering, and formal evidence verification to solve real-world reliability challenges in conversational computing. By focusing on immutable meteorological telemetry, deterministic fallback pathways, and transparent provenance auditing, the system adds an essential layer of trustworthiness to conversational digital assistants.",
        body
    ))
    story.append(Paragraph(
        "As conversational artificial intelligence continues to permeate every facet of human activity—from travel planning and commuting to logistics and hazard management—architectures that guarantee mathematical grounding and source transparency will become foundational. Sky Reader demonstrates that fluid natural language interaction and absolute factual precision can coexist harmoniously, establishing an inspiring benchmark for the next generation of trustworthy, user-centric AI applications.",
        body
    ))
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 29 (Reference Page 32): REFERENCES [1]-[7]
    # -------------------------------------------------------------------------
    story.append(Paragraph("REFERENCES", title_main))
    story.append(Spacer(1, 10))

    refs_p1 = [
        "[1] Open-Meteo, \"Open-Source Weather API Documentation and WMO Codes Guide,\" Open-Meteo B.V., 2024. Available: https://open-meteo.com/en/docs",
        "[2] J. Wei, X. Wang, D. Schuurmans, et al., \"Chain-of-Thought Prompting Elicits Reasoning in Large Language Models,\" Advances in Neural Information Processing Systems (NeurIPS), vol. 35, pp. 24824–24837, 2022.",
        "[3] P. Lewis, E. Perez, A. Piktus, et al., \"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,\" Advances in Neural Information Processing Systems (NeurIPS), vol. 33, pp. 9459–9474, 2020.",
        "[4] Y. Dhuliawala, M. Komeili, J. Xu, et al., \"Chain-of-Verification Reduces Hallucination in Large Language Models,\" arXiv preprint arXiv:2309.11495, 2023.",
        "[5] S. Yao, J. Zhao, D. Yu, et al., \"ReAct: Synergizing Reasoning and Acting in Language Models,\" in Proc. Int. Conf. on Learning Representations (ICLR), 2023.",
        "[6] World Meteorological Organization (WMO), \"Manual on Codes: International Codes, Volume I.1 (Annex II to WMO Technical Regulations),\" WMO-No. 306, Geneva, 2023.",
        "[7] FastAPI Documentation, \"FastAPI Framework: High Performance, Easy to Learn, Fast to Code,\" Tiangolo, 2024. Available: https://fastapi.tiangolo.com/"
    ]
    for r in refs_p1:
        story.append(Paragraph(r, bullet))
        story.append(Spacer(1, 4))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 30 (Reference Page 33): REFERENCES [8]-[16]
    # -------------------------------------------------------------------------
    story.append(Spacer(1, 10))
    refs_p2 = [
        "[8] React Documentation, \"React 19 Architecture and Component Lifecycle,\" Meta Platforms Inc., 2024. Available: https://react.dev/",
        "[9] T. Brown, B. Mann, N. Ryder, et al., \"Language Models are Few-Shot Learners,\" Advances in Neural Information Processing Systems (NeurIPS), vol. 33, pp. 1877–1901, 2020.",
        "[10] SQLite Development Team, \"SQLite Database Architecture and ACID Transaction Concurrency,\" SQLite.org, 2024. Available: https://www.sqlite.org/",
        "[11] Groq Inc., \"Groq LPU Inference Engine and OpenAI-Compatible API Specifications,\" Groq Cloud Documentation, 2024.",
        "[12] Google DeepMind, \"Gemini: A Family of Highly Capable Multimodal Models,\" arXiv preprint arXiv:2312.11805, 2023.",
        "[13] Pydantic Documentation, \"Data Validation and Settings Management Using Python Type Hinting,\" Pydantic v2, 2024. Available: https://docs.pydantic.dev/",
        "[14] H. Ji, P. Liu, et al., \"A Survey on Hallucination in Large Language Models: Principles, Taxonomy, and Open Questions,\" ACM Computing Surveys, vol. 56, no. 1, pp. 1–38, 2024.",
        "[15] A. Thorne, A. Vlachos, C. Christodoulopoulos, et al., \"FEVER: A Large-scale Dataset for Fact Extraction and VERification,\" in Proc. NAACL-HLT, pp. 809–819, 2018.",
        "[16] National Institute of Standards and Technology (NIST), \"Artificial Intelligence Risk Management Framework (AI RMF 1.0),\" NIST Trustworthy and Responsible AI, 2023."
    ]
    for r in refs_p2:
        story.append(Paragraph(r, bullet))
        story.append(Spacer(1, 4))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 31 (Reference Page 34): REFERENCES [17]-[20]
    # -------------------------------------------------------------------------
    story.append(Spacer(1, 10))
    refs_p3 = [
        "[17] European Centre for Medium-Range Weather Forecasts (ECMWF), \"IFS Documentation and Atmospheric Physics Formulations,\" ECMWF Research Reports, Reading, UK, 2023.",
        "[18] HTTPX Development Team, \"HTTPX: Fully Featured HTTP Client for Python 3,\" Encode, 2024. Available: https://www.python-httpx.org/",
        "[19] Vite Community, \"Vite: Next Generation Frontend Tooling,\" ViteJS Guide, 2024. Available: https://vite.dev/",
        "[20] Lucide Icon Project, \"Beautiful & Consistent Icons for Modern User Interfaces,\" Lucide Contributors, 2024."
    ]
    for r in refs_p3:
        story.append(Paragraph(r, bullet))
        story.append(Spacer(1, 4))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 32 (Reference Page 35): APPENDIX A & APPENDIX B
    # -------------------------------------------------------------------------
    story.append(Paragraph("APPENDIX", title_main))
    story.append(Spacer(1, 8))

    story.append(Paragraph("APPENDIX A", sec_heading))
    story.append(Paragraph("<b>WEATHER DATA ATTRIBUTES</b>", sec_heading))
    app_a = [
        "User Query Utterance",
        "Geocoded Latitude & Longitude (WGS84)",
        "Destination Local Offset Timestamp",
        "Surface Temperature (°C / °F)",
        "Apparent / Feels-Like Temperature (°C / °F)",
        "Relative Humidity (%)",
        "Precipitation Probability (%)",
        "Precipitation Amount (mm / inches)",
        "Wind Speed & Wind Gusts (km/h)",
        "Wind Compass Direction",
        "Barometric Surface Pressure (hPa)",
        "UV Radiation Index (0-11+)",
        "WMO Weather Interpretation Code",
        "Account / Session Bearer Token"
    ]
    for a in app_a:
        story.append(Paragraph(a, bullet))

    story.append(Spacer(1, 10))
    story.append(Paragraph("APPENDIX B", sec_heading))
    story.append(Paragraph("<b>WEATHER RISK SEVERITY CLASSIFICATION</b>", sec_heading))
    app_b = [
        "Low – Optimal atmospheric conditions for travel and outdoor recreation",
        "Moderate – Minor deviations requiring attention (gusts, scattered light showers)",
        "High – Critical environmental hazard (convective storm, gale gusts, extreme UV)",
        "Severe – Life-threatening atmospheric event requiring immediate shelter"
    ]
    for b in app_b:
        story.append(Paragraph(b, bullet))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 33 (Reference Page 36): APPENDIX C & APPENDIX D
    # -------------------------------------------------------------------------
    story.append(Paragraph("APPENDIX C", sec_heading))
    story.append(Paragraph("<b>SYSTEM CONFIGURATION PARAMETERS</b>", sec_heading))
    app_c = [
        "Default LLM Provider: Groq (openai/gpt-oss-120b)",
        "Secondary Providers: Google Gemini, OpenRouter",
        "Token Ceilings: 350 (simple), 650 (medium), 1200 (complex)",
        "Monotonic Request Deadline: 12,000 ms",
        "Geocoding Cache TTL: 86,400 seconds (24 hours)",
        "Current Weather Cache TTL: 300 seconds (5 minutes)",
        "Forecast Cache TTL: 900 seconds (15 minutes)",
        "Backend Framework: FastAPI",
        "Frontend Framework: React 19",
        "Database: SQLite (WAL mode)",
        "Authentication: 43-character Bearer Token"
    ]
    for c in app_c:
        story.append(Paragraph(c, bullet))

    story.append(Spacer(1, 10))
    story.append(Paragraph("APPENDIX D", sec_heading))
    story.append(Paragraph("<b>PSEUDOCODE FOR REQUEST ROUTING & PROOF GATE</b>", sec_heading))
    app_d = [
        "Input: User Utterance U, Thread Context C, Expected Revision R",
        "Validate Session(Token) and ConcurrencyLock(ThreadID, R)",
        "Intent, Locations, Horizon ← Router.Extract(U, C)",
        "Coords ← Geocoder.Resolve(Locations)",
        "If Coords Ambiguous: Return ClarificationPrompt()",
        "Telemetry ← WeatherService.FetchScoped(Coords, Horizon)",
        "If DeterministicAvailable(Intent):",
        "    Answer ← RenderDeterministic(Telemetry)",
        "Else:",
        "    Draft ← LLMGateway.Synthesize(U, Telemetry)",
        "    Claims ← ClaimExtractor.Extract(Draft)",
        "    If ClaimValidator.Validate(Claims, Telemetry) == PASS:",
        "        Answer ← Draft",
        "    Else:",
        "        Answer ← GroundedRecovery.RenderFreshObservation(Telemetry)",
        "CommitRevision(ThreadID, R + 1)",
        "Return Answer with Attached Provenance Proof"
    ]
    for d in app_d:
        story.append(Paragraph(d, bullet))

    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 34 (Reference Page 37): APPENDIX E (Future Scope OMITTED!)
    # -------------------------------------------------------------------------
    story.append(Paragraph("APPENDIX E", sec_heading))
    story.append(Paragraph("<b>SAMPLE OUTPUTS</b>", sec_heading))
    app_e = [
        "Figure A.1 View of City Lookup & Meteorological Dashboard",
        "Figure A.2 View of Grounded Agent Conversation & Risk Analysis",
        "Figure A.3 View of Provenance Audit Drawer & Validation Proof"
    ]
    for e in app_e:
        story.append(Paragraph(e, bullet))

    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>SAMPLE EXECUTION LOGS</b>", sec_heading))
    story.append(Paragraph("• &nbsp; <b>Sample Log 1:</b> [INFO] Query: 'Weather in Dehradun' | Geocode: (30.3165, 78.0322) | Cache: HIT | Telemetry: 15.2°C, Clear sky | Claims: 2 | Grounded: 100% | Status: 200 OK", bullet))
    story.append(Paragraph("• &nbsp; <b>Sample Log 2:</b> [INFO] Query: 'Compare Lisbon and Madrid' | Geocode: Lisbon (38.7167, -9.1333), Madrid (40.4168, -3.7038) | Hazards: Madrid Strong Wind | Risk: Lisbon LOW, Madrid MODERATE | Claims: 10 | Grounded: 100% | Status: 200 OK", bullet))
    story.append(Paragraph("• &nbsp; <b>Sample Log 3:</b> [INFO] Session: token_iQ2LQeRTCigSB2PS83ejqmX2srgB6x1asqj3a9ZxRgk | User: upretiankit100@gmail.com | Revision: 4 committed | Concurrency: Verified", bullet))

    # Build PDF
    doc.build(story, canvasmaker=ReferenceNumberedCanvas)
    print(f"Generated 34-page report at {PDF_OUTPUT_PATH}")

if __name__ == "__main__":
    build_pdf()
