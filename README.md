# 🌦️ Sky Reader (WeatherGPT)
### Agentic AI Weather Intelligence, Reasoning & Verification Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57.svg)](https://www.sqlite.org/)
[![Groq](https://img.shields.io/badge/Groq-Cloud%20LLM-f55036.svg)](https://groq.com/)
[![Open-Meteo](https://img.shields.io/badge/Data-Open--Meteo-orange.svg)](https://open-meteo.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Sky Reader** is an agentic AI meteorological intelligence and deterministic claim verification platform. Beyond traditional weather forecasting apps, Sky Reader unifies **real-time Open-Meteo observations**, a **deterministic Python meteorological analysis engine**, **Groq LLM tool-calling**, a **formal Evidence Generation & Claim Validation System**, and a **visionOS/macOS-inspired glassmorphism frontend** featuring live particle simulation canvases, SQLite user authentication, and multi-model AI dispatching.

The platform is engineered with zero-tolerance for hallucinations: every AI-generated claim is parsed, audited against verified ground-truth meteorological records, and paired with an audited **Explanation Proof** before being served to the user.

---

## 🌟 Key Features & Capabilities

### 🎨 1. Visionary Glassmorphism UI & Ambient Atmospheric Canvas
- **Floating Glass Application Frame**: VisionOS/macOS-inspired frosted window (`backdrop-filter: blur(28px)`), rounded pill architecture, and realistic drifting sky clouds.
- **HTML5 Canvas Atmospheric Particle Engine**: Dynamic real-time weather simulations that automatically react to real weather or user preference:
  - ☀️ **Sunshine & Warm Radiance**: Golden sun rays and luminous particles.
  - 🌧️ **Rain & Precipitation**: Slanted raindrops with impact ripples.
  - ✨ **Midnight Stars**: Twinkling stardust and calm night sky.
  - 🍃 **Wind & Drifting Foliage**: Swaying leaves following fluid aerodynamic turbulence.
  - ❄️ **Snow & Blizzard**: Softly drifting snowflakes.
  - ⚡ **Thunderstorm**: Atmospheric lightning flashes and deep rain bursts.
  - ☁️ **Overcast**: Soft drifting ambient cloud layers.
  - 🔄 **Auto Mode**: Detects atmospheric conditions dynamically from Open-Meteo telemetry and agent claim extractions.
- **Eye-Friendly Warm Light & Dark Themes**: High-contrast dark mode for evening focus, paired with a soft warm parchment/linen light theme (`#ede8df` → `#c8bfb2`) specifically designed to eliminate screen glare and eye strain.

---

### 🧠 2. AI Model Engine Selector (`ModelSelector`)
Integrated centered dropdown pill allowing instant switching between specialized meteorological reasoning engines:
- ✦ **Sky Reader 4 (Default / Precision)**: Flagship reasoning engine with strict factual claim audits and zero-hallucination verification.
- ⚡ **Sky Reader 4 Turbo (High Velocity)**: Optimized for rapid multi-point hourly telemetry, swift radar analytics, and dynamic route planning.
- ⏱️ **Sky Reader 3.5 Flash (Ultra-Low Latency)**: Instant responses for quick temperature queries and daily summaries.
- 🌐 **Sky Reader Ensemble (Consensus Audit)**: Cross-validates atmospheric observations against deterministic physical models and consensus checks.

---

### 🔖 3. Saved Places Watchlist (`SavedPlacesView`)
- **Watchlist Dashboard**: Manage saved global locations with live temperature, condition label, humidity, wind velocity, and day/night badges.
- **Search & Auto-Validate**: Add new global locations with instant geocoding verification.
- **1-Click Quick Add Chips**: Pre-curated chips for world capitals (Tokyo, Zurich, Paris, New York, Reykjavik, Sydney, Dehradun).
- **Deep Integration**:
  - Jump directly into **Dashboard & Trips** for full 48-hour hourly forecasting.
  - 1-click **Ask AI** to consult the meteorological agent about that city.
  - **Save Place Bookmark Button** in the main city lookup header to bookmark any searched location.
  - Real-time counter badge on the left sidebar navigation pill.
  - Synced across `localStorage` and the SQLite database backend.

---

### 🔐 4. Accounts, guest access, and conversation storage

- Email/password authentication uses SQLite with salted PBKDF2 password hashes and 14-day bearer sessions. The browser validates saved tokens through `GET /api/auth/me` before displaying account content. A temporarily unavailable server leaves the account locked and provides a retry.
- **Stay signed in** stores the token for later browser visits. Turning it off keeps the token in tab session storage, which survives reloads in that tab. Logout immediately removes browser credentials and asks `POST /api/auth/logout` to revoke the token. If revocation fails, the UI reports it while remaining signed out locally.
- **Continue as guest** grants access to public features without an account. Guest and each authenticated account have separate browser-local conversation histories. History survives refresh and logout and is available again in the same scope. Clearing history removes only the active scope. The old unscoped history is left unused because its owner cannot be identified.
- Browser history is not server-enforced account storage, encrypted storage, or cross-device sync. People or scripts with access to the same browser profile can read its local data. The frontend exposes Google sign-in and password reset as unavailable.
- The built-in demo account is disabled by default. Set `SKYREADER_ENABLE_DEMO=1` explicitly for local development to permit it. With the flag off, existing demo rows are preserved and their sessions cannot be used.

---

### 🤖 5. Agentic AI Tool-Calling & Verification Loop
- **Autonomous Tool Dispatch**: Groq LLM dynamically determines whether a query requires geocoding, current weather, hourly forecasting, deep analysis, or direct conversational answers.
- **Complete Reasoning Cycle**: *User Query → Tool Invocation → Python Execution → Data Return → Model Synthesis → Grounded Answer*.
- **Structured Evidence Engine**: Extracts and tags all weather data into provenance-tracked records: `OBSERVED`, `FORECAST`, and `DERIVED`.
- **Deterministic Claim Extractor & Validator**:
  - Regex-based factual claim parsing (temperature, rain chance, wind speed, pressure, trends, umbrella advisories).
  - Domain-calibrated tolerances ($\pm 1.0^\circ\text{C}$ temperature, $\pm 5.0\%$ rain probability, $\pm 2.5\text{ km/h}$ wind).
  - Real-time status classifications: `SUPPORTED`, `PARTIALLY_SUPPORTED`, `CONTRADICTED`, `INSUFFICIENT_EVIDENCE`.
- **Hallucination Controller & Self-Correction**: Automatically detects contradictions and triggers targeted corrective regeneration with ground-truth evidence before returning to user.

### 🛡️ Phase 6: Safety, Risk Assessment & Uncertainty Awareness
- **Deterministic Weather Risk Engine**: Analyzes forecast records across configurable thresholds to identify severe hazards:
  - **Heavy Rainfall**: Detects flash flood and waterlogging risks based on 24h accumulation ($\ge 15$, $\ge 30$, $\ge 60\text{ mm}$) and peak hourly rates ($\ge 5$, $\ge 10$, $\ge 20\text{ mm/h}$).
  - **High Rain Probability**: Categorizes precipitation probabilities ($\ge 60\%$, $\ge 80\%$, $\ge 95\%$) while separating likelihood from volume.
  - **Severe Thunderstorms & Hail**: Flags WMO storm codes (95, 96, 99) and lightning hazards.
  - **Strong Wind & Gales**: Beaufort-aligned hazard classification ($\ge 30$, $\ge 45$, $\ge 62\text{ km/h}$).
  - **Extreme Heat & Cold**: Detects heatstroke thresholds ($\ge 35^\circ\text{C}$, $\ge 40^\circ\text{C}$, $\ge 45^\circ\text{C}$) and hypothermia/freezing conditions ($\le 0^\circ\text{C}$, $\le -10^\circ\text{C}$, $\le -20^\circ\text{C}$).
- **Severity Classification**: Maps conditions into standardized risk levels: `LOW`, `MODERATE`, `HIGH`, and `SEVERE`.
- **Actionable Safety Recommendations**: Generates non-alarmist, practical guidance (shelter indoors during lightning, avoid flood-prone routes, hydration, loose attire).
- **Official Alerts vs. AI Risk Assessments**: Strict architectural distinction: all assessments are explicitly watermarked as AI-calculated from numerical forecasts and deterministic thresholds, never masquerading as official government emergency alerts.
- **Uncertainty Communication**: Discloses probability interpretation (e.g. 75% probability = likely, not guaranteed), identifies missing or incomplete sensor channels, and notes forecast uncertainty.
- **Visual Safety Cards (`RiskCard.jsx`)**: Displays severity badges, condition summaries, key measurements, precautions, and collapsible uncertainty notes directly in chat bubbles when hazards are assessed.

---

### 🧭 6. City Lookup, Telemetry & Preferences
- **48-Hour Hourly Forecast Slider**: Hourly temperature cards, precipitation probability markers, and current hour highlight.
- **Telemetry Grid**: Beaufort wind scale, cardinal compass directions, barometric pressure trend, and humidity comfort indexing.
- **Decision Support Engine**:
  - ☔ **Umbrella Advisory**: Threshold-based recommendations with associated confidence levels.
  - 🏃 **Outdoor Activity Windows**: Ranks 6-hour blocks (Night, Morning, Afternoon, Evening) for ideal outdoor conditions.
  - 🚗 **Travel Suitability**: Evaluates hazards (heavy rain, severe winds, fog, thunderstorms).
- **Preferences & Settings Panel (`PreferencesView`)**:
  - Units toggle (Celsius °C / Fahrenheit °F).
  - Atmospheric scene override.
  - AI reasoning depth & hallucination verification toggles.
  - Chat history management and cache reset.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    User([User]) <--> Frontend["React 19 + Vite Frontend<br/>localhost:5173"]
    Frontend <--> API["FastAPI Backend<br/>localhost:8000"]
    API <--> SQLite[("SQLite Database<br/>skyreader.db")]
    API <--> Agent["Agent Reasoning Loop<br/>backend/agent/agent.py"]
    Agent <--> GroqLLM["Groq Cloud LLM<br/>openai/gpt-oss-120b"]
    Agent <--> Executor["Python Tool Executor<br/>backend/agent/executor.py"]
    Executor <--> Analysis["Meteorological Engine<br/>backend/weather/analysis.py"]
    Executor <--> Service["Open-Meteo Service<br/>backend/weather/service.py"]
    Service <--> OpenMeteo[("Open-Meteo APIs<br/>Geocoding & Forecast")]

    %% Evidence Generation & Verification
    Agent <--> EvEngine["Evidence Generation Engine<br/>backend/evidence/evidence_engine.py"]
    Agent <--> ClaimExt["Claim Extractor<br/>backend/evidence/claim_extractor.py"]
    Agent <--> ClaimVal["Claim Validator<br/>backend/evidence/claim_validator.py"]
    Agent <--> HallucCtrl["Hallucination Controller<br/>backend/evidence/hallucination_controller.py"]
    Agent <--> ExplEngine["Explanation Proof Engine<br/>backend/evidence/explanation_engine.py"]
```

---

## 🧰 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend Framework** | React 19, Vite | Fast modular component hierarchy & reactive state |
| **Styling & Effects** | Pure CSS3 & HTML5 Canvas | Glassmorphism, particle physics, custom scrollbars, dual themes |
| **Icons** | Lucide React | Clean, scalable iconography for weather, navigation, and telemetry |
| **Backend Framework** | Python 3.10+, FastAPI, Pydantic v2 | High-throughput async REST API, strict schemas, CORS |
| **Database** | SQLite3, PBKDF2-HMAC-SHA256 | Local, zero-configuration user storage and session management |
| **AI Inference** | Groq Cloud SDK (`AsyncGroq`) | Ultra-fast LLM inference using `openai/gpt-oss-120b` with tool calling |
| **Verification Engine** | Deterministic Python | Provenance tagging, regex claim parsing, domain tolerance validation |
| **Weather Telemetry** | Open-Meteo API | Free, high-accuracy global geocoding, current data, and hourly forecasts |

---

## 📁 Project Directory Structure

```text
Sky-Reader/
├── README.md                          # Comprehensive project documentation
├── .gitignore
├── backend/
│   ├── .env                           # Environment variables (GROQ_API_KEY, GROQ_MODEL)
│   ├── skyreader.db                   # SQLite database (auto-generated on startup)
│   ├── database.py                    # SQLite schema, password hashing, session tokens
│   ├── requirements.txt               # fastapi, httpx, pydantic, groq, python-dotenv
│   ├── main.py                        # FastAPI routes (Auth, Weather, Analysis, Chat, Evidence, Risks)
│   ├── test_executor.py               # Phase 1 tool executor test
│   ├── test_phase2.py                 # Phase 2 agentic tool-calling integration suite
│   ├── test_phase3.py                 # Phase 3 meteorological intelligence integration suite
│   ├── test_phase4.py                 # Phase 4 end-to-end verification & explainability suite
│   ├── test_phase6.py                 # Phase 6 weather safety & risk assessment integration suite
│   ├── test_analysis.py               # Phase 3 meteorological engine unit tests
│   ├── test_multiturn_chat.py         # Multi-turn conversational flow & reset verification test
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── agent.py                   # Groq tool-calling agent with validation loop
│   │   ├── executor.py                # Tool dispatcher executing weather & analysis functions
│   │   └── tools.py                   # OpenAPI schemas for weather tools
│   ├── weather/
│   │   ├── __init__.py
│   │   ├── analysis.py                # Meteorological trends, comfort, Beaufort, decision support
│   │   ├── risk_engine.py             # Phase 6 deterministic weather risk assessment engine
│   │   ├── risk_models.py             # Pydantic schemas: RiskLevel, RiskItem, WeatherRiskAssessment
│   │   ├── service.py                 # Open-Meteo HTTP client with retry logic & formatters
│   │   ├── models.py                  # Pydantic response models
│   │   └── weather_codes.py           # WMO weather code to description & emoji mappings
│   ├── evidence/                      # Evidence & Claim Verification Subsystem
│   │   ├── __init__.py
│   │   ├── evidence_models.py         # EvidenceItem, FactualClaim, ExplanationProof schemas
│   │   ├── evidence_engine.py         # Extracts structured records with provenance tagging
│   │   ├── claim_extractor.py         # Deterministic regex-based factual claim extractor
│   │   ├── claim_validator.py         # Deterministic validator with domain tolerances
│   │   ├── hallucination_controller.py# Metrics calculation, feedback loop & safe fallback
│   │   └── explanation_engine.py      # Generates ExplanationProof & Markdown audit chains
│   ├── evaluation/                    # Phase 7 Benchmark Dataset & Evaluation Suite
│   │   ├── __init__.py                # Package exports (models, loaders)
│   │   ├── models.py                  # Pydantic benchmark validation schemas (TestCase, Dataset, Fixtures)
│   │   ├── dataset_loader.py          # Loader & cross-reference validator functions
│   │   ├── generate_benchmark_data.py # Deterministic dataset & synthetic fixture generator
│   │   ├── datasets/                  # 50 validated benchmark test cases across 10 categories
│   │   │   └── weather_benchmark.json
│   │   ├── fixtures/                  # 12 high-fidelity synthetic weather fixtures
│   │   │   └── weather_fixtures.json
│   │   ├── metrics.py                 # Formulas for Grounding, Hallucination, F1, Overhead
│   │   ├── benchmark.py               # Comparative benchmark script
│   │   ├── ablation.py                # Architectural ablation study runner
│   │   └── README.md                  # Comprehensive evaluation dataset documentation
│   └── tests/                         # Modular unit & integration test suites
│       ├── test_evidence_engine.py
│       ├── test_claim_extractor.py
│       ├── test_claim_validator.py
│       ├── test_hallucination_controller.py
│       ├── test_explanation_engine.py
│       ├── test_risk_engine.py        # Phase 6 hazard & uncertainty unit tests
│       ├── test_temporal_context.py   # Phase 8.1 timezone & forecast window tests
│       ├── test_rate_limit_and_routing.py # Phase 8.1 rate limit & routing tests
│       └── test_evaluation_dataset.py # Phase 7.1 dataset validation & fixture unit tests
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── main.jsx
        ├── App.jsx                    # Root state manager (auth, atmospheric canvas, view tabs)
        ├── App.css                    # Complete CSS tokens, glassmorphism, animations, dual themes
        └── components/                # Modular UI component hierarchy
            ├── ChatHeader.jsx         # Header bar with model selector, atmosphere, theme, New Chat
            ├── ModelSelector.jsx      # Interactive dropdown selector for AI reasoning engines
            ├── WeatherAtmosphere.jsx  # HTML5 Canvas particle simulation engine
            ├── AtmosphereSelector.jsx # Ambient weather animation selector pill
            ├── Sidebar.jsx            # Responsive left navigation with unconstrained scrolling & badges
            ├── SavedPlacesView.jsx    # Dedicated watchlist view with live city cards & quick add
            ├── LoginPage.jsx          # Twilight aurora canvas login card with authentication
            ├── PreferencesView.jsx    # Settings panel: units, themes, atmosphere overrides
            ├── WelcomeHero.jsx        # Conversational starter cards and capsule input
            ├── ChatMessage.jsx        # Left/Right message bubbles with copy, timestamp & formatted text
            ├── WeatherSnapshot.jsx    # Visual telemetry cards (temp, humidity, wind, rain, umbrella)
            ├── RiskCard.jsx           # Phase 6 safety cards, severity badges & uncertainty notes
            ├── AuditDrawer.jsx        # Collapsible Phase 4 verification & explainability drawer
            ├── ThinkingIndicator.jsx  # Animated 3-dot typing status indicator
            ├── ChatInput.jsx          # Modern floating textarea, footnote & send button
            └── CityLookup.jsx         # Preserved Phase 1 city weather search & hourly forecast
        │   ├── ChatMessage.jsx        # Left/right chat bubbles with timestamp & telemetry embeds
        │   ├── WeatherSnapshot.jsx    # Visual telemetry cards (temp, humidity, rain %, umbrella)
        │   ├── AuditDrawer.jsx        # Collapsible verification & explainability drawer
        │   ├── ThinkingIndicator.jsx  # Animated typing status indicator
        │   ├── ChatInput.jsx          # Bottom fixed textarea, quick suggestions & send button
        │   ├── CityLookup.jsx         # 48h forecast, hourly slider, telemetry & bookmark toggle
        │   └── PreferencesView.jsx    # Settings panel for units, theme, and AI reasoning depth
        └── utils/
            ├── weatherAtmosphere.js   # Atmosphere detection logic & scene presets
            └── weatherIcons.jsx       # WMO code to Lucide weather icon mapper
>>>>>>> b88b7eb200530ec549a267ca87b8814a6f56cc38
```

---

## 🚀 Quickstart Guide

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** and **npm**
- **Groq API Key** (available free at [console.groq.com](https://console.groq.com/))

### 1. Clone the Repository
```bash
git clone https://github.com/TaruneshM/Sky-Reader.git
cd Sky-Reader
```

### 2. Configure Backend Environment
Create or edit `backend/.env`:
```bash
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

### 3. Install & Start Backend Server
```bash
# Windows
python -m venv backend\venv
backend\venv\Scripts\activate
pip install -r backend\requirements.txt

# Run FastAPI server
cd backend
uvicorn main:app --reload --port 8000
```
- API live at: **http://127.0.0.1:8000**
- Interactive Swagger docs: **http://127.0.0.1:8000/docs**

### 4. Install & Start Frontend Server
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
- Frontend live at: **http://localhost:5173**

---

## 🔌 API Reference Summary

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Service status welcome message |
| `POST` | `/api/auth/register` | Register a new user profile in SQLite |
| `POST` | `/api/auth/login` | Authenticate user and issue session token |
| `GET` | `/api/auth/me` | Retrieve profile of authenticated user |
| `POST` | `/api/auth/logout` | Terminate and invalidate session token |
| `GET` | `/weather?location={city}` | Phase 1 current weather and 24h/48h hourly forecast |
| `GET` | `/api/weather/analysis?location={city}&focus={focus}&day_offset={0\|1}` | Phase 3 meteorological intelligence & decision support |
| `GET` | `/api/weather/risks?location={city}&day_offset={0\|1}` | Phase 6 deterministic weather hazard detection & safety assessment |
| `POST` | `/api/agent/chat` | Phase 2, 3, 4, 6 & 8 verified conversational agent reasoning endpoint |
| `POST` | `/api/evidence/validate` | Phase 4 deterministic claim extraction & validation for any text |
| `GET` | `/api/evidence/summary?location={city}` | Phase 4 complete evidence collection & provenance records |

### Public and authenticated routes

Weather lookup, deterministic weather and evidence routes, and chat are public, including their legacy aliases. Login and registration are public entry points. Profile access and logout require the bearer token from login or registration. The backend stores no account conversation history and exposes no route to retrieve it.

Both chat aliases share rolling process-local limits. Set `SKYREADER_CHAT_REQUESTS_PER_IP_PER_MINUTE` (default `12`) and `SKYREADER_CHAT_REQUESTS_PER_MINUTE` (default `60`) to positive integers. Excess requests receive HTTP 429 with a retry hint before agent execution. Chat messages are limited to 4,000 characters, and only the last six history entries are used, with at most 4,000 characters per entry. These limits apply to guest and signed-in traffic and are independent across processes. Behind a proxy, client addresses depend on the server’s trusted-proxy configuration.

### Example 1: Multi-Turn Verified Agent Chat Response
```bash
curl -X POST "http://127.0.0.1:8000/api/agent/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "Should I carry an umbrella?",
       "conversation_history": [
         {"role": "user", "content": "What is the weather in Dehradun tomorrow?"},
         {"role": "assistant", "content": "Tomorrow in Dehradun will be mostly clear with a high of 26°C and 0% rain chance."}
       ]
     }'
```
```json
{
  "response": "The current temperature in Paris is 8.8 °C with 86% humidity and wind at 6.7 km/h...",
  "tool_calls": [
    {"tool": "geocode_location", "arguments": {"location": "Paris"}},
    {"tool": "get_current_weather", "arguments": {"latitude": 48.85, "longitude": 2.35}}
  ],
  "iterations": 2,
  "claims": [
    {
      "claim_id": "claim_1",
      "statement": "The current temperature in Paris is 8.8 °C",
      "variable": "temperature",
      "claimed_value": 8.8,
      "unit": "°C",
      "claim_type": "numerical_value"
    }
  ],
  "validation_report": {
    "total_claims": 3,
    "supported_claims": 3,
    "contradicted_claims": 0,
    "unsupported_claims": 0,
    "hallucination_rate": 0.0,
    "contradiction_rate": 0.0,
    "is_trustworthy": true
  },
  "explanation": {
    "query": "What is the current weather in Paris?",
    "conclusion": "The current temperature in Paris is 8.8 °C...",
    "claim_validation_status": "100% Grounded (3/3 claims verified)",
    "hallucination_risk": "Low",
    "data_sources": ["Open-Meteo Current Weather API"],
    "limitations_and_uncertainty": "Numerical weather prediction accuracy naturally degrades beyond 24-48 hours..."
  }
}
```

### Example 2: On-Demand Claim Validation
```bash
curl -X POST "http://127.0.0.1:8000/api/evidence/validate" \
     -H "Content-Type: application/json" \
     -d '{
       "location": "Dehradun",
       "text": "The temperature is 22.0 °C and humidity is 60%."
     }'
```

### Example 3: Evidence Collection Summary
```bash
curl "http://127.0.0.1:8000/api/evidence/summary?location=Dehradun"
```

---

## 🧪 Testing & Verification Suites

Sky Reader includes modular unit tests, integration test suites, and empirical benchmarking tools:

### Offline authentication and conversation checks

```bash
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
python -m pytest backend/tests backend/test_analysis.py backend/test_phase4.py
```

The frontend checks cover request ownership, session transitions, browser storage isolation, and rendered login controls. Backend checks use temporary SQLite databases and mocked weather/provider requests.

### 1. Phase 6 & Phase 4 Unit Tests (Offline / Zero Network)
```bash
# Phase 7.1 benchmark evaluation dataset & fixture unit tests (8 test suites)
backend/venv/bin/python backend/tests/test_evaluation_dataset.py

# Phase 6 weather safety, risk levels, and uncertainty unit tests (10 test cases)
backend/venv/bin/python backend/tests/test_risk_engine.py

# Phase 4 verification & explainability unit tests
backend/venv/bin/python backend/tests/test_evidence_engine.py
backend/venv/bin/python backend/tests/test_claim_extractor.py
backend/venv/bin/python backend/tests/test_claim_validator.py
backend/venv/bin/python backend/tests/test_hallucination_controller.py
backend/venv/bin/python backend/tests/test_explanation_engine.py
```
*(All test suites pass deterministically without network dependencies).*

### 2. Complete Phase 6 Weather Safety & Risk Integration Suite
Tests deterministic hazard evaluation, tool executor mappings, FastAPI `/api/weather/risks` endpoints, and Groq agent hazard routing:
```bash
PYTHONPATH=. backend/venv/bin/python backend/test_phase6.py
```
*(Result: 3/3 test suites pass).*

### 3. Complete Phase 4 Integration Suite
Tests evidence extraction, claim extraction, validation with tolerances, hallucination feedback, explanation proofs, FastAPI endpoints, and end-to-end agent reasoning:
```bash
backend/venv/bin/python backend/test_phase4.py
```
*(Result: 7/7 test suites pass).*

### 3. Empirical Benchmarking & Ablation Studies
```bash
# Run comparative benchmark across architectures
backend/venv/bin/python backend/evaluation/benchmark.py

# Run ablation study on tolerances, feedback, and derived evidence
backend/venv/bin/python backend/evaluation/ablation.py
```

### 4. Multi-Turn Contextual Conversation Flow Test
Tests conversational memory across follow-up queries (*"Dehradun tomorrow"* → *"Should I carry an umbrella?"* → *"What about travelling?"*) and validates context clearing on "New Chat":
```bash
PYTHONPATH=. backend/venv/bin/python backend/test_multiturn_chat.py
```
*(Result: 4/4 conversational turns pass cleanly).*

### 5. Phase 3 & Phase 2 Integration Tests
```bash
# Phase 3 meteorological intelligence
PYTHONPATH=. backend/venv/bin/python backend/test_phase3.py

# Phase 2 Groq tool-calling agent loop
PYTHONPATH=. backend/venv/bin/python backend/test_phase2.py
```

### 6. Phase 1 Executor & Analysis Unit Tests
```bash
# Phase 1 executor
PYTHONPATH=. backend/venv/bin/python backend/test_executor.py

# Phase 3 offline analysis math
backend/venv/bin/python backend/test_analysis.py
```

---

## 💡 Example Queries Supported

- *"What is the current temperature in Dehradun?"*
- *"Will it rain tomorrow in Paris? Should I carry an umbrella?"*
- *"Is the temperature increasing or decreasing over the next 24 hours in Delhi?"*
- *"What is the best time for outdoor activities tomorrow in Tokyo?"*
- *"Is tomorrow suitable for travelling in Chennai?"*
- *"How will tomorrow's weather compare with today's in London?"*
- *"Are there any weather risks, storms, or severe safety hazards in Dehradun tomorrow?"*
- *"Is it safe to go hiking in Tokyo tomorrow given the wind and rain forecast?"*
- *"Can you explain the meteorological evidence behind your recommendation?"*
- *"What causes lightning and thunder?"* (answered directly as general knowledge without tool calls)


---

## 📜 License & Acknowledgements

- **License**: MIT License
- **Weather Data**: Real-time telemetry provided by [Open-Meteo](https://open-meteo.com/).
- **AI Inference**: High-speed LLM inference powered by [Groq](https://groq.com/).
