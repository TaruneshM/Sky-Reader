import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os

os.makedirs('C:/Users/upret/Desktop/sk/Sky-Reader/report_assets/charts', exist_ok=True)
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']

# --- CHART 1: Solution Overview / 3 Pillars (Matching Figure 3.1.1 of reference) ---
def make_fig_3_1_1():
    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.5)
    ax.axis('off')

    # Title
    ax.text(5, 4.1, "Our Solution: Sky Reader Weather Intelligence", 
            ha='center', va='center', fontsize=16, fontweight='bold', color='#1e3a8a')

    cards = [
        ("1. RETRIEVE & PLAN", 
         "Deterministic & agentic routing.\nExtracts intent, location & period.\nQueries Open-Meteo with TTL caches\nfor raw meteorological telemetry.", 
         "#3b82f6", 1.8),
        ("2. AUDIT & VERIFY", 
         "Structured Evidence Engine.\nExtracts claims from model drafts.\nRuns whole-draft & clause-level gates\nto guarantee zero hallucinations.", 
         "#8b5cf6", 5.0),
        ("3. SYNTHESIZE & SECURE", 
         "Multi-provider LLM gateway.\nShared token & latency budgets.\nSQLite session & thread revisions.\nReact 19 dynamic UI & atmosphere.", 
         "#06b6d4", 8.2),
    ]

    for title, desc, color, cx in cards:
        # Card background
        rect = patches.FancyBboxPatch((cx - 1.4, 0.4), 2.8, 3.2,
                                      boxstyle="round,pad=0.15,rounding_size=0.2",
                                      ec=color, fc="#f8fafc", lw=2, zorder=2)
        ax.add_patch(rect)
        # Header banner
        header_rect = patches.FancyBboxPatch((cx - 1.4, 3.0), 2.8, 0.6,
                                             boxstyle="round,pad=0.1,rounding_size=0.15",
                                             ec="none", fc=color, zorder=3)
        ax.add_patch(header_rect)
        ax.text(cx, 3.3, title, ha='center', va='center', color='white', fontsize=11, fontweight='bold', zorder=4)
        ax.text(cx, 1.7, desc, ha='center', va='center', color='#334155', fontsize=9.5, linespacing=1.5, zorder=4)

    plt.tight_layout()
    plt.savefig('C:/Users/upret/Desktop/sk/Sky-Reader/report_assets/charts/fig_3_1_1_solution_overview.png')
    plt.close()

# --- CHART 2: System Architecture (Matching Figure 3.2.1) ---
def make_fig_3_2_1():
    fig, ax = plt.subplots(figsize=(11, 6.2), dpi=300)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis('off')

    boxes = [
        ("User Query / Client\n(React 19 Frontend)", 1.5, 6.5, 2.2, 1.0, "#38bdf8", "#0369a1"),
        ("FastAPI Gateway\n(Routes, CORS & Auth)", 4.8, 6.5, 2.4, 1.0, "#34d399", "#065f46"),
        ("SQLite & Threads\n(Revision Control)", 8.5, 6.5, 2.3, 1.0, "#fbbf24", "#92400e"),
        
        ("Request Router & Planner\n(Scope, Slots, Intent)", 4.8, 4.6, 2.4, 1.1, "#818cf8", "#3730a3"),
        ("Weather Service & Cache\n(Open-Meteo APIs)", 1.5, 4.6, 2.2, 1.1, "#60a5fa", "#1d4ed8"),
        
        ("Evidence Engine\n(Claim Extraction & Audit)", 4.8, 2.6, 2.4, 1.1, "#f472b6", "#9d174d"),
        ("Multi-Provider Gateway\n(Groq, Gemini, OpenRouter)", 8.5, 2.6, 2.5, 1.1, "#a78bfa", "#5b21b6"),
        
        ("Grounded Response &\nProof Verification Packet", 4.8, 0.7, 2.6, 1.0, "#4ade80", "#166534"),
    ]

    for label, x, y, w, h, bg, border in boxes:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1,rounding_size=0.15",
                                      ec=border, fc=bg, lw=2, alpha=0.9, zorder=3)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, label, ha='center', va='center', fontsize=9.5, fontweight='bold', color='#0f172a', zorder=4)

    # Connections
    arrows = [
        ((3.7, 7.0), (4.8, 7.0), "HTTP/JSON"),
        ((7.2, 7.0), (8.5, 7.0), "Verify Session"),
        ((6.0, 6.5), (6.0, 5.7), "Dispatch"),
        ((4.8, 5.15), (3.7, 5.15), "Fetch Weather"),
        ((6.0, 4.6), (6.0, 3.7), "Scoped Telemetry"),
        ((7.2, 3.15), (8.5, 3.15), "LLM Synthesis"),
        ((8.5, 2.8), (7.2, 2.8), "Draft Output"),
        ((6.0, 2.6), (6.0, 1.7), "Verified Claims"),
        ((4.8, 1.2), (2.6, 6.5), "Deliver Verified UI"),
    ]

    for (x1, y1), (x2, y2), txt in arrows:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color="#334155", lw=1.8, shrinkA=3, shrinkB=3), zorder=2)
        mid_x, mid_y = (x1 + x2)/2, (y1 + y2)/2
        if txt == "Deliver Verified UI":
            mid_x, mid_y = 3.2, 3.8
        ax.text(mid_x, mid_y + 0.18, txt, fontsize=8, color="#475569", ha='center',
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8), zorder=5)

    plt.tight_layout()
    plt.savefig('C:/Users/upret/Desktop/sk/Sky-Reader/report_assets/charts/fig_3_2_1_system_architecture.png')
    plt.close()

# --- CHART 3: Tech Stack (Matching Figure 3.3.1) ---
def make_fig_3_3_1():
    fig, ax = plt.subplots(figsize=(10.5, 4.5), dpi=300)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 5)
    ax.axis('off')

    ax.text(5.5, 4.6, "System Technology Stack", ha='center', va='center',
            fontsize=16, fontweight='bold', color='#1e3a8a')

    columns = [
        ("1. FRONTEND\nUI LAYER", [
            "React 19 & Vite",
            "Atmospheric Simulation",
            "Lucide React Icons",
            "Audit & Risk Drawers",
            "Browser Storage Cache"
        ], "#38bdf8", 1.8),
        ("2. BACKEND API\n& ENGINE", [
            "Python 3.12+ & FastAPI",
            "Pydantic Validation",
            "HTTPX Async Client",
            "Deterministic Engine",
            "SQLite + Session Auth"
        ], "#34d399", 5.5),
        ("3. INTELLIGENCE\n& GROUNDING", [
            "Open-Meteo Free APIs",
            "Evidence Engine Audit",
            "Multi-Provider Gateway",
            "Groq / Gemini / OpenRouter",
            "Clause-Level Proof Gate"
        ], "#a78bfa", 9.2),
    ]

    for title, items, color, cx in columns:
        card = patches.FancyBboxPatch((cx - 1.5, 0.4), 3.0, 3.8,
                                      boxstyle="round,pad=0.15,rounding_size=0.2",
                                      ec=color, fc="#f8fafc", lw=2)
        ax.add_patch(card)
        top = patches.FancyBboxPatch((cx - 1.5, 3.5), 3.0, 0.7,
                                     boxstyle="round,pad=0.1,rounding_size=0.15",
                                     ec="none", fc=color)
        ax.add_patch(top)
        ax.text(cx, 3.85, title, ha='center', va='center', color='white', fontsize=10.5, fontweight='bold')
        
        y_pos = 2.9
        for item in items:
            ax.text(cx, y_pos, f"• {item}", ha='center', va='center', color='#1e293b', fontsize=9.5)
            y_pos -= 0.55

    plt.tight_layout()
    plt.savefig('C:/Users/upret/Desktop/sk/Sky-Reader/report_assets/charts/fig_3_3_1_tech_stack.png')
    plt.close()

# --- CHART 4: Evidence Gate Flow (Figure 3.5.1) ---
def make_fig_3_5_1():
    fig, ax = plt.subplots(figsize=(10.5, 5.0), dpi=300)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 5.5)
    ax.axis('off')

    ax.text(5.5, 5.1, "Evidence Gate & Clause-Level Semantic Auditing", 
            ha='center', va='center', fontsize=15, fontweight='bold', color='#1e3a8a')

    nodes = [
        ("Model Draft &\nWeather Evidence", 1.2, 3.2, 1.8, 1.0, "#93c5fd", "#1e40af"),
        ("Whole-Draft Audit\n(Claim Extraction)", 3.7, 3.2, 1.9, 1.0, "#c4b5fd", "#5b21b6"),
        ("Completeness\nCheck", 6.3, 3.2, 1.6, 1.0, "#fde047", "#854d0e"),
        ("Final Clause Gate\n(Semantic Match)", 8.6, 3.2, 1.8, 1.0, "#f9a8d4", "#9d174d"),
        
        ("Grounded Response\n+ Attached Proof", 8.6, 1.0, 1.8, 1.0, "#86efac", "#166534"),
        ("Safe Recovery /\nDeterministic Limitation", 5.0, 1.0, 2.4, 1.0, "#fca5a5", "#991b1b"),
    ]

    for label, x, y, w, h, bg, border in nodes:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1,rounding_size=0.15",
                                      ec=border, fc=bg, lw=1.8, zorder=3)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, label, ha='center', va='center', fontsize=9, fontweight='bold', color='#0f172a', zorder=4)

    # Connections
    ax.annotate("", xy=(3.7, 3.7), xytext=(3.0, 3.7),
                arrowprops=dict(arrowstyle="->", color="#334155", lw=1.8))
    ax.annotate("", xy=(6.3, 3.7), xytext=(5.6, 3.7),
                arrowprops=dict(arrowstyle="->", color="#334155", lw=1.8))
    ax.annotate("", xy=(8.6, 3.7), xytext=(7.9, 3.7),
                arrowprops=dict(arrowstyle="->", color="#334155", lw=1.8))
    
    # Gate pass
    ax.annotate("", xy=(9.5, 2.0), xytext=(9.5, 3.2),
                arrowprops=dict(arrowstyle="->", color="#166534", lw=2))
    ax.text(9.9, 2.6, "Pass", color="#166534", fontsize=10, fontweight='bold')

    # Gate reject
    ax.annotate("", xy=(7.4, 1.5), xytext=(8.6, 3.2),
                arrowprops=dict(arrowstyle="->", color="#991b1b", lw=2, linestyle="--"))
    ax.text(7.6, 2.3, "Reject", color="#991b1b", fontsize=10, fontweight='bold')

    # Completeness fail
    ax.annotate("", xy=(6.2, 2.0), xytext=(7.1, 3.2),
                arrowprops=dict(arrowstyle="->", color="#991b1b", lw=1.5, linestyle="--"))

    plt.tight_layout()
    plt.savefig('C:/Users/upret/Desktop/sk/Sky-Reader/report_assets/charts/fig_3_5_1_evidence_gate.png')
    plt.close()

# --- CHART 5: Benchmark Evaluation Metrics (Matching Figure 4.4.1) ---
def make_fig_4_4_1():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5), dpi=300)

    # Left: Evaluation Metrics Bar Chart
    categories = ['Completeness\n(101/120)', 'Hazard\nCoverage (12/12)', 'Both-City\nMetrics (7/8)', 'Grounded\nAudit (88/88)', 'Unaudited\nErrors (0/120)']
    percentages = [84.17, 100.0, 87.5, 100.0, 0.0]
    colors = ['#3b82f6', '#10b981', '#6366f1', '#06b6d4', '#ef4444']

    bars = ax1.bar(categories, percentages, color=colors, width=0.55, edgecolor='#1e293b', lw=1.2)
    ax1.set_ylim(0, 115)
    ax1.set_ylabel("Verification Rate (%)", fontsize=11, fontweight='bold', color='#1e293b')
    ax1.set_title("Stage 1.7E Frozen Suite Benchmark (120 Cases)", fontsize=12, fontweight='bold', color='#1e3a8a')
    ax1.grid(axis='y', linestyle='--', alpha=0.5)

    for bar in bars:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., h + 2.5, f"{h:.1f}%",
                 ha='center', va='bottom', fontsize=9.5, fontweight='bold')

    # Right: Response Execution Path Distribution
    routes = ['Deterministic\nSelected (70)', 'Groq Model\nAttempted (20)', 'Clarification\nNeeded (19)', 'Evidence\nLimitation (11)']
    counts = [70, 20, 19, 11]
    donut_colors = ['#38bdf8', '#818cf8', '#fbbf24', '#f87171']

    wedges, texts, autotexts = ax2.pie(counts, labels=routes, autopct='%1.1f%%',
                                       startangle=140, colors=donut_colors,
                                       wedgeprops=dict(width=0.45, edgecolor='white', lw=2),
                                       textprops=dict(fontsize=9, color='#1e293b'))
    for at in autotexts:
        at.set_fontsize(9.5)
        at.set_fontweight('bold')
    ax2.set_title("Request Execution Path Distribution", fontsize=12, fontweight='bold', color='#1e3a8a')

    plt.tight_layout()
    plt.savefig('C:/Users/upret/Desktop/sk/Sky-Reader/report_assets/charts/fig_4_4_1_evaluation_metrics.png')
    plt.close()

make_fig_3_1_1()
make_fig_3_2_1()
make_fig_3_3_1()
make_fig_3_5_1()
make_fig_4_4_1()
print("All charts generated successfully!")
