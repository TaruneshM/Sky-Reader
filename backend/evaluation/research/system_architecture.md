# 🏗️ System Architecture & Implementation Specification

**Project Title:** Sky Reader: An Evidence-Grounded Agentic AI Framework for Reliable Weather Intelligence and Risk Assessment  
**Document Type:** Technical & Architectural Specification  
**Implementation Source Code:** `backend/agent/agent.py`, `backend/weather/`, `backend/evidence/`, `frontend/src/`  

---

## 1. Architectural Philosophy: Neuro-Symbolic Agentic Design

Sky Reader is structured as a **neuro-symbolic agentic framework**. It couples the natural-language comprehension, contextual reasoning, and multi-turn conversational capabilities of modern Large Language Models (LLMs) with **deterministic, rule-based scientific computations and formal verification gates**.

A central design principle is that **probabilistic LLMs must never perform arithmetic, meteorological threshold classifications, or unverified factual assertions in high-stakes domains**. Instead:
1. LLMs are constrained to intent parsing, query formulation, tool calling, and conversational synthesis.
2. Atmospheric analysis, metric computations, risk classifications, and claim verifications are executed exclusively by deterministic Python algorithms.

---

## 2. End-to-End System Workflow

The following execution flow represents the **precise chronological order** implemented in the repository code (`backend/main.py`, `backend/agent/agent.py`, `backend/evidence/`, `backend/weather/`):

```
User Query (Natural Language)
    │
    ▼
[1] React Conversational Client (Vite, React 19, Tailwind)
    │  (Manages multi-turn state, renders EvidenceDrawer & RiskCard)
    │  HTTP POST /api/chat (JSON: message, conversation_history)
    ▼
[2] FastAPI Gateway (`backend/main.py`)
    │  (Validates payload schemas, invokes asynchronous orchestrator)
    ▼
[3] Agentic Orchestrator (`backend/agent/agent.py::run_agent`)
    │  Initializes conversation buffer with `SYSTEM_PROMPT`
    │  Loops up to `max_iterations` (default: 10)
    ▼
[4] Groq LLM Completion Engine (`openai/gpt-oss-120b`)
    │  Evaluates messages against registered OpenAPI Tool Schemas (`tools.py`)
    │  Returns either:
    │    A) Tool Call Requests (function name + JSON arguments)
    │    B) Candidate Natural Language Response (Termination)
    ▼
[5] Tool Dispatcher & Execution (`backend/agent/executor.py`)
    │  Executes requested tools asynchronously:
    │  ├─ `geocode_location`         --> Open-Meteo Geocoding API
    │  ├─ `get_current_weather`      --> Open-Meteo Current Weather API
    │  ├─ `get_hourly_forecast`      --> Open-Meteo Forecast API (48h series)
    │  ├─ `analyze_weather`          --> Deterministic Trend Analysis (`analysis.py`)
    │  ├─ `get_weather_recommendations` --> Rule-based Activity & Umbrella Advisor
    │  └─ `assess_weather_risks`     --> Deterministic Risk Assessment Engine (`risk_engine.py`)
    │  Tool outputs appended as `role: tool` messages back to conversation buffer
    │  [Loops back to Step 4 until model terminates tool calls]
    ▼
[6] Post-Execution Verification Pipeline (Triggered upon candidate response)
    │  If weather telemetry was retrieved during iterations:
    │
    ├─ [6.1] Evidence Compilation (`backend/evidence/evidence_engine.py`)
    │        Compiles observations, hourly series, and trends into immutable
    │        `WeatherEvidence` with deterministic identifiers (`ev_current_temp`, etc.)
    │
    ├─ [6.2] Automated Claim Extraction (`backend/evidence/claim_validator.py::ClaimExtractor`)
    │        Extracts atomic propositions (numerical measurements & factual statements)
    │
    ├─ [6.3] Deterministic Claim Validation (`backend/evidence/claim_validator.py::ClaimValidator`)
    │        Audits extracted claims against compiled `WeatherEvidence`
    │        Labels each: SUPPORTED, PARTIALLY_SUPPORTED, CONTRADICTED, UNSUPPORTED
    │
    ├─ [6.4] Closed-Loop Hallucination Control (`backend/evidence/hallucination_controller.py`)
    │        Computes hallucination rate. If ungrounded assertions exceed threshold:
    │        - Attempt 1: Targeted regeneration prompt passing invalid claims
    │        - Attempt 2: Deterministic safe narrative fallback generated from verified evidence
    │
    ├─ [6.5] Formal Explanation Proof Construction (`backend/evidence/explanation_engine.py`)
    │        Builds an `ExplanationProof` linking verified claims to citation IDs and ground-truth values
    │
    └─ [6.6] Risk Assessment Payload Alignment (`backend/weather/risk_engine.py`)
             Binds deterministic `WeatherRiskAssessment` to response payload
    ▼
[7] Verified Response Delivery to User
    FastAPI returns unified JSON payload:
    {
      "response": "Final validated text",
      "tool_calls": [...],
      "claims": [...],
      "validation_report": {...},
      "explanation": { "proof_id": "...", "grounded_claims": [...] },
      "risk_assessment": { "risk_level": "...", "hazards": [...] }
    }
    React Client renders response text, expandable Evidence Drawer, and Risk Alert Badge.
```

---

## 3. Component Decomposition: LLM vs. Deterministic Computation

A critical requirement of scientific documentation is distinguishing components driven by stochastic Large Language Models from those executed via deterministic Python code.

| Architectural Component | Execution Subsystem | Underlying Technology | Operational Role |
|---|---|---|---|
| **Natural Language Understanding & Planning** | LLM | Groq API (`openai/gpt-oss-120b`) | Parses user intent, resolves conversational follow-ups, determines which tools are needed. |
| **Conversational Synthesis** | LLM | Groq API (`openai/gpt-oss-120b`) | Synthesizes complex telemetry and advisories into user-friendly natural prose. |
| **Tool Calling Decision** | LLM | Groq Function Calling Schema | Emits structured JSON tool invocation payloads with coordinates and parameters. |
| **Tool Execution Dispatcher** | Deterministic | Python (`asyncio`, `httpx`) | Dispatches HTTP requests to Open-Meteo or internal Python engines. |
| **Geocoding & Data Retrieval** | Deterministic | Open-Meteo API / Synthetic Fixture Store | Translates place names to coordinates; retrieves atmospheric telemetry arrays. |
| **Meteorological Trend Analysis** | Deterministic | Python (`backend/weather/analysis.py`) | Calculates temperature gradients, rain onset timing, daily extremes, wind vectors. |
| **Evidence Compilation** | Deterministic | Python (`backend/evidence/evidence_engine.py`) | Compiles telemetry arrays into immutable `WeatherEvidence` with canonical hash IDs. |
| **Propositional Claim Extraction** | Deterministic | Python Regex & Semantic Parsers (`claim_validator.py`) | Extracts numerical measurements, units, variables, and factual clauses from response text. |
| **Claim Verification & Auditing** | Deterministic | Python Numerical & Fact Auditing (`claim_validator.py`) | Compares claims against evidence within configured scientific tolerances (e.g., $\pm 1.0^\circ\text{C}$). |
| **Hallucination Recovery Decision** | Deterministic | Python Rule Logic (`hallucination_controller.py`) | Evaluates validation metrics; triggers regeneration or safe narrative fallback. |
| **Weather Risk & Hazard Engine** | Deterministic | Python Threshold Engine (`risk_engine.py`) | Evaluates convective, wind, thermal, and winter hazard rules to assign risk tiers. |
| **Formal Proof Generation** | Deterministic | Python Structuring (`explanation_engine.py`) | Constructs tamper-evident `ExplanationProof` linking claims directly to evidence IDs. |

---

## 4. Key Implementation Modules and Source Files

### 1. Gateway & State Management
- `backend/main.py`: FastAPI application exposing `/api/chat`, `/api/health`, and session management endpoints.
- `frontend/src/App.jsx`: Conversational state management, handling history, new chat resets, and asynchronous streaming/loading states.

### 2. Agent Core & Tools
- `backend/agent/agent.py`: Asynchronous tool-calling loop (`run_agent`), Groq rate-limit backoff handler, and evidence-pipeline orchestration.
- `backend/agent/tools.py`: OpenAPI tool schemas defining `geocode_location`, `get_current_weather`, `get_hourly_forecast`, `analyze_weather`, `get_weather_recommendations`, and `assess_weather_risks`.
- `backend/agent/executor.py`: Asynchronous dispatching mechanism executing tools against live Open-Meteo endpoints or injected fixture handlers.

### 3. Meteorological Services
- `backend/weather/service.py`: High-performance asynchronous Open-Meteo API client with coordinate geocoding, current weather, and 48-hour hourly forecast ingestion.
- `backend/weather/analysis.py`: Deterministic weather analysis engine computing temperature trends, wind severity, rain probability vs. accumulation, and practical lifestyle recommendations.
- `backend/weather/risk_engine.py`: Deterministic Phase 6 Weather Risk Assessment Engine evaluating multi-hazard meteorological criteria to classify risk severity into LOW, MODERATE, HIGH, or SEVERE.
- `backend/weather/risk_models.py`: Validated Pydantic models for hazards, severity tiers, precautionary recommendations, and risk assessment payloads.

### 4. Evidence Grounding & Verification Subsystem
- `backend/evidence/evidence_engine.py`: Compiles raw observation payloads into structured, traceable `WeatherEvidence` entities with immutable citation identifiers.
- `backend/evidence/claim_validator.py`: Contains `ClaimExtractor` (atomic proposition extraction) and `ClaimValidator` (scientific tolerance checking against evidence).
- `backend/evidence/hallucination_controller.py`: Closed-loop recovery controller auditing candidate responses, orchestrating targeted regeneration, and executing verified narrative fallbacks.
- `backend/evidence/explanation_engine.py`: Constructs formal, transparent `ExplanationProof` artifacts for user-facing auditability and verification transparency.
- `backend/evidence/evidence_models.py`: Pydantic data schemas defining evidence items, atomic claims, validation reports, and explanation proofs.
