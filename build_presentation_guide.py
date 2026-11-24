import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.pdfgen import canvas

PDF_OUTPUT_PATH = r"C:\Users\upret\Desktop\sk\Sky-Reader\Sky_Reader_Evaluator_Presentation_Guide.pdf"
ASSETS_DIR = r"C:\Users\upret\Desktop\sk\Sky-Reader\report_assets"
CHARTS_DIR = os.path.join(ASSETS_DIR, "charts")

class PresentationCanvas(canvas.Canvas):
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

    def draw_page_decorations(self, total_pages):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#0369a1"))
        
        # Header (Pages 2+)
        if self._pageNumber > 1:
            self.drawString(48, 752, "SKY READER: PROJECT PRESENTATION & EVALUATOR VIVA MANUAL")
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748b"))
            self.drawRightString(612 - 48, 752, "B.Tech AI & ML Minor Project Defense")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(48, 745, 612 - 48, 745)

        # Footer on all pages
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(48, 42, 612 - 48, 42)
        
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#1e3a8a"))
        self.drawString(48, 30, "DEPARTMENT OF ARTIFICIAL INTELLIGENCE & MACHINE LEARNING")
        
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#475569"))
        self.drawRightString(612 - 48, 30, f"Page {self._pageNumber} of {total_pages}")
        
        self.restoreState()

def build_presentation_guide():
    doc = SimpleDocTemplate(
        PDF_OUTPUT_PATH,
        pagesize=letter,
        leftMargin=48,
        rightMargin=48,
        topMargin=46,
        bottomMargin=48
    )

    styles = getSampleStyleSheet()

    title_main = ParagraphStyle(
        'GuideTitle',
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=2
    )

    subtitle = ParagraphStyle(
        'GuideSubtitle',
        fontName='Helvetica',
        fontSize=10,
        leading=13.5,
        textColor=colors.HexColor('#0284c7'),
        spaceAfter=6
    )

    sec_title = ParagraphStyle(
        'SecTitle',
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=14.5,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=5,
        spaceAfter=3,
        keepWithNext=True
    )

    sub_title = ParagraphStyle(
        'SubTitle',
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12.5,
        textColor=colors.HexColor('#1e40af'),
        spaceBefore=3,
        spaceAfter=2,
        keepWithNext=True
    )

    body = ParagraphStyle(
        'GuideBody',
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=3
    )

    bullet = ParagraphStyle(
        'GuideBullet',
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#1e293b'),
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2
    )

    talking_point = ParagraphStyle(
        'TalkingPoint',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#065f46')
    )

    qa_question = ParagraphStyle(
        'QAQuestion',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#991b1b')
    )

    qa_answer = ParagraphStyle(
        'QAAnswer',
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#1e293b')
    )

    caption = ParagraphStyle(
        'GuideCaption',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        alignment=1,
        textColor=colors.HexColor('#475569'),
        spaceBefore=2,
        spaceAfter=5
    )

    def make_box(content, bg_hex="#f8fafc", border_hex="#cbd5e1", pad=4):
        t = Table([[content]], colWidths=[516])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(bg_hex)),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor(border_hex)),
            ('TOPPADDING', (0,0), (-1,-1), pad),
            ('BOTTOMPADDING', (0,0), (-1,-1), pad),
            ('LEFTPADDING', (0,0), (-1,-1), pad + 3),
            ('RIGHTPADDING', (0,0), (-1,-1), pad + 3),
        ]))
        return t

    story = []

    # =========================================================================
    # PAGE 1: OVERVIEW, PITCH & PROBLEM COMPARISON
    # =========================================================================
    banner = [
        Paragraph("SKY READER: PROJECT PRESENTATION GUIDE", title_main),
        Paragraph("<b>Evidence-Grounded Agentic Weather Intelligence System | Defense & Evaluation Manual</b>", subtitle),
        Paragraph("Structured for student project teams to present <b>Sky Reader</b> with clarity and authority to evaluators and examiners.", body)
    ]
    story.append(make_box(banner, bg_hex="#eff6ff", border_hex="#3b82f6", pad=4))
    story.append(Spacer(1, 3))

    story.append(Paragraph("1. The 30-Second Elevator Pitch (What to Say When You Begin)", sec_title))
    pitch_text = Paragraph(
        "\"<b>Sky Reader</b> is an evidence-grounded agentic weather intelligence system. Unlike standard AI chatbots that hallucinate numbers and fabricate forecasts, and unlike static dashboards that only show raw tables, Sky Reader bridges both worlds. It connects natural language queries to live <b>Open-Meteo</b> telemetry, provides contextual activity guidance (attire, travel safety), and subjects every generated response to an automated <b>Evidence Engine</b> that validates individual clauses. If any claim cannot be proven from real telemetry, our system catches it and replaces it with certified observations—delivering <b>100% grounded facts with zero numerical hallucinations</b>.\"",
        talking_point
    )
    story.append(make_box(pitch_text, bg_hex="#ecfdf5", border_hex="#10b981", pad=4))
    story.append(Spacer(1, 3))

    story.append(Paragraph("2. Problem Statement: Why Existing Systems Fail", sec_title))
    prob_data = [
        [Paragraph("<b>Approach</b>", caption), Paragraph("<b>How It Works</b>", caption), Paragraph("<b>Critical Flaw / Failure Mode</b>", caption)],
        [
            Paragraph("<b>General LLMs (ChatGPT)</b>", body),
            Paragraph("Statistical next-token prediction based on static pretraining.", body),
            Paragraph("<b>Hallucination:</b> Confidently invents temperatures, rain percentages, and storm warnings with zero live grounding.", body)
        ],
        [
            Paragraph("<b>Standard Weather Sites</b>", body),
            Paragraph("Static UI displaying raw tables, radar maps, and dials.", body),
            Paragraph("<b>No Reasoning:</b> Cannot answer comparative questions, relative time windows, or activity suitability.", body)
        ],
        [
            Paragraph("<b>Basic Vector RAG</b>", body),
            Paragraph("Embeds text chunks and performs cosine semantic lookup.", body),
            Paragraph("<b>Numerical Failure:</b> Embeddings cannot perform arithmetic, coordinate distance, or strict metric validation.", body)
        ],
        [
            Paragraph("<b>Sky Reader (Our Solution)</b>", talking_point),
            Paragraph("<b>Agentic routing + Typed Evidence + Multi-Provider LLM Gateway + Clause Proof Gate.</b>", talking_point),
            Paragraph("<b>Zero Hallucinations:</b> Combines deterministic speeds with mathematical evidence auditing & proof trails.", talking_point)
        ]
    ]
    t_prob = Table(prob_data, colWidths=[120, 186, 210])
    t_prob.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e3a8a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor("#f8fafc")]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#dcfce7")),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_prob)
    story.append(Spacer(1, 3))

    fig_3_1 = os.path.join(CHARTS_DIR, "fig_3_1_1_solution_overview.png")
    if os.path.exists(fig_3_1):
        story.append(Image(fig_3_1, width=470, height=110))
        story.append(Paragraph("Figure 1: Sky Reader's Three Architectural Pillars", caption))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: SYSTEM ARCHITECTURE & REQUEST FLOW
    # =========================================================================
    story.append(Paragraph("3. End-to-End System Architecture (How the System Operates)", sec_title))
    story.append(Paragraph("Explain how a user query moves through each architectural layer:", body))

    fig_3_2 = os.path.join(CHARTS_DIR, "fig_3_2_1_system_architecture.png")
    if os.path.exists(fig_3_2):
        story.append(Image(fig_3_2, width=470, height=170))
        story.append(Paragraph("Figure 2: End-to-End System Architecture Flow", caption))

    story.append(Paragraph("<b>Step-by-Step Execution Lifecycle:</b>", sub_title))
    steps = [
        ("1. Request & Session Auth", "React dispatches user query to FastAPI with bearer token. Backend resolves session in SQLite and checks thread revision counters to guard against concurrent write collisions."),
        ("2. Routing & Disambiguation", "The Router extracts intent, places, and time window. Typed geocoding disambiguates coordinates (e.g., distinguishing Córdoba, Spain from Córdoba, Argentina)."),
        ("3. Telemetry Retrieval & TTL Cache", "Weather Service queries Open-Meteo REST APIs through process-local TTL caches (24h geocoding, 5m current, 15m hourly forecasts) for near-zero latency."),
        ("4. Decision Branch (Fast vs. Synthesis)", "Simple queries render instantly via high-speed deterministic engine (6.65 ms). Complex/comparative queries route to the Multi-Provider LLM Gateway."),
        ("5. Evidence Engine & Proof Gate", "Claim Extractor parses model text into structured claims. Validator checks claims against raw telemetry. If verified, proof is attached; if not, Grounded Recovery steps in."),
        ("6. Reactive UI with Atmosphere", "Response is returned with attached audit metadata and rendered in React with live canvas atmospheric simulation (aurora, rain, sun, clouds).")
    ]
    for s_title, s_desc in steps:
        story.append(Paragraph(f"• &nbsp; <b>{s_title}:</b> {s_desc}", bullet))

    tip_box = Paragraph(
        "<b>Presenter Tip for Evaluators:</b> Highlight Steps 4 and 5! Explain that the LLM is never allowed to communicate unverified numbers directly to the user. The <b>Evidence Engine</b> acts as an impartial mathematical judge.",
        talking_point
    )
    story.append(Spacer(1, 3))
    story.append(make_box(tip_box, bg_hex="#fffbeb", border_hex="#f59e0b", pad=4))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: EVIDENCE ENGINE & SEMANTIC GATE
    # =========================================================================
    story.append(Paragraph("4. The Core Innovation: The Evidence Engine & Semantic Gate", sec_title))
    story.append(Paragraph("This is the central technical innovation of Sky Reader: eliminating hallucinations without labeled training data.", body))

    fig_3_5 = os.path.join(CHARTS_DIR, "fig_3_5_1_evidence_gate.png")
    if os.path.exists(fig_3_5):
        story.append(Image(fig_3_5, width=470, height=155))
        story.append(Paragraph("Figure 3: Evidence Engine & Clause-Level Proof Gate Architecture", caption))

    story.append(Paragraph("<b>The Four Verification Stages:</b>", sub_title))
    stages = [
        ("1. Structured Evidence Packaging", "Prior to prompting, backend builds an immutable evidence packet from Open-Meteo containing exact variables: temperature, apparent feel, precipitation, wind speed, gusts, UV index, and WMO codes."),
        ("2. Semantic Claim Extraction", "The draft response is passed through a deterministic claim extractor, decomposing prose into typed claim objects: <code>{variable: 'temperature', claimed_value: 15.2, location: 'Dehradun'}</code>."),
        ("3. Completeness & Hazard Verification", "Verifies that the draft answers all requested variables and includes all critical environmental hazards (e.g., thunderstorms or gale gusts detected in telemetry)."),
        ("4. Clause-Level Proof Gating & Grounded Recovery", "Inspects individual sentences. If a draft claims '28 °C' when telemetry says '15 °C', the gate rejects the draft and activates <b>Grounded Recovery</b>: rendering a clean, verified answer from certified telemetry without crashing.")
    ]
    for st_title, st_desc in stages:
        story.append(Paragraph(f"• &nbsp; <b>{st_title}:</b> {st_desc}", bullet))

    story.append(Spacer(1, 3))
    code_box = Paragraph(
        "<b>Evaluator Oral Defense Tip:</b> If asked: <i>'What happens when the model hallucinates?'</i><br/>"
        "<b>Answer:</b> <i>'The Evidence Gate intercepts the mismatch, blocks the ungrounded text, and renders Grounded Recovery: raw certified telemetry with an honest disclaimer that extended prose could not be verified. The system never lies.'</i>",
        talking_point
    )
    story.append(make_box(code_box, bg_hex="#ecfdf5", border_hex="#10b981", pad=4))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: MULTI-PROVIDER GATEWAY & TECH STACK
    # =========================================================================
    story.append(Paragraph("5. Multi-Provider LLM Gateway Architecture", sec_title))
    story.append(Paragraph("Decouples high-level reasoning from model providers to eliminate single-vendor lock-in:", body))

    gw_data = [
        [Paragraph("<b>Provider</b>", caption), Paragraph("<b>Model / Adapter</b>", caption), Paragraph("<b>Role & Failover Strategy</b>", caption)],
        [
            Paragraph("<b>Groq</b>", body),
            Paragraph("openai/gpt-oss-120b & Llama-3.3-70b (LPU inference)", body),
            Paragraph("<b>Primary Engine:</b> Sub-second response generation, highly reliable structured reasoning.", body)
        ],
        [
            Paragraph("<b>Google Gemini</b>", body),
            Paragraph("GenerateContent REST Adapter (Request-local state)", body),
            Paragraph("<b>Secondary Provider:</b> High-capacity reasoning; tool schemas remain request-scoped.", body)
        ],
        [
            Paragraph("<b>OpenRouter</b>", body),
            Paragraph("Chat Completions REST (Free-model allowlist)", body),
            Paragraph("<b>Cost-Free Alternative:</b> Strict zero-cost ceiling, provider-side fallback disabled.", body)
        ]
    ]
    t_gw = Table(gw_data, colWidths=[90, 196, 230])
    t_gw.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_gw)

    story.append(Paragraph("<b>Resource Controls:</b> Monotonic 12s deadline per request; token caps (350 simple, 650 medium, 1200 complex); transient errors trigger sequential fallback; malformed/rejected claims halt migration.", bullet))
    story.append(Spacer(1, 3))

    story.append(Paragraph("6. Technology Stack & Component Justification", sec_title))
    fig_3_3 = os.path.join(CHARTS_DIR, "fig_3_3_1_tech_stack.png")
    if os.path.exists(fig_3_3):
        story.append(Image(fig_3_3, width=470, height=115))
        story.append(Paragraph("Figure 4: Full Technology Stack Overview", caption))

    tech_points = [
        ("React 19 & Vite", "Instantaneous reactive UI updates, client-side session caching, and HTML5 canvas particle atmospheric rendering."),
        ("FastAPI (Python 3.12+)", "Asynchronous ASGI performance, automatic OpenAPI schema docs, and Pydantic validation."),
        ("SQLite with Optimistic Locking", "Lightweight, zero-maintenance storage with thread revision checks guarding against write collisions."),
        ("Open-Meteo Global APIs", "Authoritative open meteorological data (NOAA, ECMWF, DWD) without API key restrictions.")
    ]
    for tp_name, tp_desc in tech_points:
        story.append(Paragraph(f"• &nbsp; <b>{tp_name}:</b> {tp_desc}", bullet))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 5: LIVE DEMONSTRATION SCRIPT
    # =========================================================================
    story.append(Paragraph("7. Live Demonstration Script: Step-by-Step for Presentation", sec_title))
    story.append(Paragraph("Follow this demonstration sequence to impress evaluators in under 3 minutes:", body))

    # Demo 1: City Lookup
    story.append(Paragraph("<b>Demo Step 1: Real-Time Meteorological Dashboard (City Lookup)</b>", sub_title))
    fig_city = os.path.join(ASSETS_DIR, "fig_city_lookup.png")
    if os.path.exists(fig_city):
        story.append(Image(fig_city, width=410, height=160))
        story.append(Paragraph("Figure 5: Live City Lookup & Atmospheric Simulation (Dehradun)", caption))

    d1_script = Paragraph(
        "<b>What to Say:</b> <i>\"Here on the Dashboard, we search for <b>Dehradun</b>. The system instantly resolves coordinates (30.32°N, 78.03°E), queries Open-Meteo, and displays live temperature (15 °C), apparent feel, 83% relative humidity, light wind dynamics, and a 24-hour hourly forecast timeline. Notice the atmospheric canvas in the background: it dynamically renders a midnight starfield matching current night conditions.\"</i>",
        body
    )
    story.append(make_box(d1_script, bg_hex="#f8fafc", border_hex="#cbd5e1", pad=3.5))
    story.append(Spacer(1, 3))

    # Demo 2: Agent Chat Comparison
    story.append(Paragraph("<b>Demo Step 2: Multi-City Comparative Chat & Risk Analysis</b>", sub_title))
    fig_chat = os.path.join(ASSETS_DIR, "fig_chat_conversation.png")
    if os.path.exists(fig_chat):
        story.append(Image(fig_chat, width=410, height=140))
        story.append(Paragraph("Figure 6: Conversational Comparison with Modeled Travel Risk (Lisbon vs. Madrid)", caption))

    d2_script = Paragraph(
        "<b>What to Say:</b> <i>\"Next, in the AI Chat tab, we ask: <b>'Compare the weather in Lisbon and Madrid'</b>. Notice how the agent analyzes both cities simultaneously. It models risk levels: <b>LOW in Lisbon</b>, but <b>MODERATE in Madrid</b> due to strong wind gusts. It provides actionable safety advice: 'Be mindful of sudden gusts when opening vehicle doors or cycling.'\"</i>",
        body
    )
    story.append(make_box(d2_script, bg_hex="#f8fafc", border_hex="#cbd5e1", pad=3.5))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 6: LIVE DEMO (AUDIT DRAWER) & BENCHMARK RESULTS
    # =========================================================================
    story.append(Paragraph("<b>Demo Step 3: Proving Zero Hallucinations (The Audit Drawer)</b>", sub_title))
    fig_audit = os.path.join(ASSETS_DIR, "fig_audit_drawer.png")
    if os.path.exists(fig_audit):
        story.append(Image(fig_audit, width=430, height=140))
        story.append(Paragraph("Figure 7: Expandable Audit Drawer with 100% Grounded Verification Proof", caption))

    d3_script = Paragraph(
        "<b>What to Say:</b> <i>\"Finally, we click the <b>'Verified Grounded (100%)'</b> audit badge. This opens the Audit Drawer. Evaluators can see every extracted claim, matched against underlying API sources, complete with tool provenance logs. This guarantees total transparency and eliminates black-box AI doubt.\"</i>",
        talking_point
    )
    story.append(make_box(d3_script, bg_hex="#ecfdf5", border_hex="#10b981", pad=3.5))
    story.append(Spacer(1, 4))

    story.append(Paragraph("8. Quantitative Evaluation & Benchmark Results", sec_title))
    fig_4_4 = os.path.join(CHARTS_DIR, "fig_4_4_1_evaluation_metrics.png")
    if os.path.exists(fig_4_4):
        story.append(Image(fig_4_4, width=450, height=115))
        story.append(Paragraph("Figure 8: Benchmark Evaluation Metrics & Request Routing Distribution", caption))

    eval_data = [
        [Paragraph("<b>Evaluation Metric</b>", caption), Paragraph("<b>Tested Cases</b>", caption), Paragraph("<b>Score / Result</b>", caption), Paragraph("<b>Significance for Evaluators</b>", caption)],
        [
            Paragraph("<b>Answer Completeness</b>", body),
            Paragraph("120 held-out cases", body),
            Paragraph("<b>101 / 120 (84.2%)</b>", body),
            Paragraph("Answers contain all required variables and guidance without omission.", body)
        ],
        [
            Paragraph("<b>Hazard & Safety Recall</b>", body),
            Paragraph("12 extreme fixtures", body),
            Paragraph("<b>12 / 12 (100.0%)</b>", talking_point),
            Paragraph("Zero safety omissions: thunderstorms and gale winds always flagged.", talking_point)
        ],
        [
            Paragraph("<b>Grounded Audit Rate</b>", body),
            Paragraph("88 candidate drafts", body),
            Paragraph("<b>88 / 88 (100.0%)</b>", talking_point),
            Paragraph("100% of delivered claims mathematically match underlying telemetry.", talking_point)
        ],
        [
            Paragraph("<b>Unaudited Numerical Claims</b>", body),
            Paragraph("120 total runs", body),
            Paragraph("<b>0 (Zero Hallucination)</b>", talking_point),
            Paragraph("No numerical claim ever reaches the user without proof gate certification.", talking_point)
        ],
        [
            Paragraph("<b>Deterministic Latency</b>", body),
            Paragraph("70 weather queries", body),
            Paragraph("<b>6.65 ms (Median)</b>", body),
            Paragraph("Near-instantaneous response speed for standard weather lookups.", body)
        ]
    ]
    t_eval = Table(eval_data, colWidths=[120, 95, 115, 186])
    t_eval.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e3a8a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_eval)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 7: VIVA DEFENSE QUESTIONS (PART 1)
    # =========================================================================
    story.append(Paragraph("9. Viva Defense: Top Evaluator Questions & Winning Answers (Part 1)", sec_title))
    story.append(Paragraph("Be prepared for these exact questions from professors and technical examiners:", body))

    viva_q1 = [
        Paragraph("<b>Q1: Why didn't you just use standard Retrieval-Augmented Generation (RAG) with a Vector DB?</b>", qa_question),
        Paragraph("<b>Winning Answer:</b> Standard RAG uses vector embeddings to retrieve text chunks based on semantic similarity. However, vector embeddings cannot do math or compare physical quantities. An embedding cannot tell that 28 °C and 18 °C are contradictory temperatures. Furthermore, weather telemetry is structured time-series data, not static documents. We use a <b>Structured Evidence Engine</b> where facts are discrete, typed contracts with coordinates, timestamps, and units, enabling exact mathematical verification.", qa_answer)
    ]
    story.append(make_box(viva_q1, bg_hex="#fef2f2", border_hex="#f87171", pad=3.5))
    story.append(Spacer(1, 3))

    viva_q2 = [
        Paragraph("<b>Q2: How does the system guarantee zero hallucinations in numerical weather data?</b>", qa_question),
        Paragraph("<b>Winning Answer:</b> Through a multi-stage proof gate. When an LLM generates a response, our <b>Claim Extractor</b> parses every numerical statement into structured claims. The <b>Claim Validator</b> compares each claim against the raw Open-Meteo telemetry. If any number deviates or lacks empirical support, the draft is rejected. Our <b>Grounded Recovery</b> module then renders a clean, concise response directly from certified telemetry. No unverified number ever reaches the user.", qa_answer)
    ]
    story.append(make_box(viva_q2, bg_hex="#fef2f2", border_hex="#f87171", pad=3.5))
    story.append(Spacer(1, 3))

    viva_q3 = [
        Paragraph("<b>Q3: What is the benefit of having both a Deterministic Engine and an LLM Gateway?</b>", qa_question),
        Paragraph("<b>Winning Answer:</b> Efficiency and cost! Simple queries like 'What is the temperature in Tokyo?' do not need a 70-billion parameter LLM. Serving them deterministically takes only <b>6.65 milliseconds</b> and consumes zero tokens. We reserve the LLM for complex queries requiring natural language synthesis, such as multi-city packing comparisons or activity safety planning.", qa_answer)
    ]
    story.append(make_box(viva_q3, bg_hex="#fef2f2", border_hex="#f87171", pad=3.5))
    story.append(Spacer(1, 3))

    viva_q4 = [
        Paragraph("<b>Q4: How do you handle ambiguous city names (e.g., London, UK vs. London, Canada)?</b>", qa_question),
        Paragraph("<b>Winning Answer:</b> Our Request Planner uses <b>Typed Geocoding</b>. It categorizes outcomes as <i>Resolved</i>, <i>Ambiguous</i>, <i>Missing</i>, or <i>Unavailable</i>. If a city name matches multiple significant population centers without explicit country qualifiers, the system halts execution and issues an interactive clarification prompt asking the user to specify their country or region, rather than guessing coordinates.", qa_answer)
    ]
    story.append(make_box(viva_q4, bg_hex="#fef2f2", border_hex="#f87171", pad=3.5))
    story.append(Spacer(1, 3))

    viva_q5 = [
        Paragraph("<b>Q5: Why did you choose Open-Meteo instead of OpenWeatherMap or WeatherAPI?</b>", qa_question),
        Paragraph("<b>Winning Answer:</b> Open-Meteo is open-source, provides global hourly and daily forecasts based on authoritative national weather models (NOAA GFS, ECMWF IFS, DWD ICON), requires no proprietary API keys, imposes no arbitrary query tier paywalls, and outputs standardized WMO weather interpretation codes.", qa_answer)
    ]
    story.append(make_box(viva_q5, bg_hex="#fef2f2", border_hex="#f87171", pad=3.5))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 8: VIVA DEFENSE (PART 2) & FINAL CHECKLIST
    # =========================================================================
    story.append(Paragraph("9. Viva Defense: Top Evaluator Questions & Winning Answers (Part 2)", sec_title))

    viva_q6 = [
        Paragraph("<b>Q6: What happens if the Groq LLM API goes down or hits rate limits?</b>", qa_question),
        Paragraph("<b>Winning Answer:</b> Our Multi-Provider LLM Gateway features automated sequential fallback. If the primary Groq provider encounters a transient timeout or rate limit, the request is cleanly rebuilt and migrated to Google Gemini REST or OpenRouter under a shared request deadline (12,000 ms) and token budget. If all providers fail, the system falls back to certified deterministic answers.", qa_answer)
    ]
    story.append(make_box(viva_q6, bg_hex="#fef2f2", border_hex="#f87171", pad=3.5))
    story.append(Spacer(1, 3))

    viva_q7 = [
        Paragraph("<b>Q7: Why use SQLite for chat persistence instead of MongoDB or PostgreSQL?</b>", qa_question),
        Paragraph("<b>Winning Answer:</b> SQLite is an embedded, zero-configuration database that runs in-process with zero network overhead. For session and thread persistence with optimistic revision locks, SQLite provides full ACID compliance with microsecond query times. It is ideal for local development, reproducible academic evaluation, and lightweight edge deployments.", qa_answer)
    ]
    story.append(make_box(viva_q7, bg_hex="#fef2f2", border_hex="#f87171", pad=3.5))
    story.append(Spacer(1, 3))

    viva_q8 = [
        Paragraph("<b>Q8: How did you evaluate the system quantitatively without human bias?</b>", qa_question),
        Paragraph("<b>Winning Answer:</b> We constructed a frozen evaluation corpus of 120 held-out cases across 12 distinct categories. The test harness isolates the production agent with mocked transports and scripted replies, measuring answer completeness, hazard coverage, and exact numerical match against ground-truth fixtures with an automated rubric.", qa_answer)
    ]
    story.append(make_box(viva_q8, bg_hex="#fef2f2", border_hex="#f87171", pad=3.5))
    story.append(Spacer(1, 5))

    story.append(Paragraph("10. Team Presentation Checklist & Key Takeaways", sec_title))
    checklist_items = [
        ("Introduce the problem first", "Do not jump straight into code. First explain why ChatGPT hallucinates weather and why weather websites are hard to interpret."),
        ("Emphasize the Evidence Engine", "This is your main scientific contribution. Highlight that you built a verification gate that acts as a guardrail over the AI."),
        ("Show, don't just tell", "Demonstrate both the City Lookup (visual appeal) and the Chat Comparison (intelligence and risk analysis)."),
        ("Click the Audit Drawer", "Show the evaluators the 100% Grounded badge and the provenance proof. Evaluators love seeing verifiable proof!"),
        ("Know your metrics", "Remember the key numbers: <b>120 benchmark cases</b>, <b>84.2% completeness</b>, <b>100% hazard recall</b>, and <b>0 unaudited numerical claims</b>.")
    ]
    for c_title, c_desc in checklist_items:
        story.append(Paragraph(f"✓ &nbsp; <b>{c_title}:</b> {c_desc}", bullet))

    story.append(Spacer(1, 5))
    final_banner = Paragraph(
        "<b>Summary for the Presentation:</b> Sky Reader represents the transition from probabilistic, ungrounded chatbots to deterministic, verifiable agentic AI. It provides speed, accuracy, and total transparency.",
        talking_point
    )
    story.append(make_box(final_banner, bg_hex="#dcfce7", border_hex="#16a34a", pad=4))

    doc.build(story, canvasmaker=PresentationCanvas)
    print(f"Presentation Guide PDF generated at: {PDF_OUTPUT_PATH}")

if __name__ == "__main__":
    build_presentation_guide()
