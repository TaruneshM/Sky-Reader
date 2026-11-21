# 🔬 Experimental Methodology Specification

**Project Title:** Sky Reader: An Evidence-Grounded Agentic AI Framework for Reliable Weather Intelligence and Risk Assessment  
**Document Type:** Empirical Evaluation Protocol  
**Benchmark Artifacts:** `backend/evaluation/datasets/weather_benchmark.json`, `backend/evaluation/fixtures/weather_fixtures.json`, `backend/evaluation/adapters.py`  

---

## 1. Scope and Scientific Objective of the Benchmark

A fundamental methodological distinction must be emphasized:
> **The Sky Reader Phase 7 Benchmark does NOT evaluate Numerical Weather Prediction (NWP) forecasting skill (such as atmospheric fluid dynamics, baroclinic instability, or sensor instrumentation accuracy). Rather, it evaluates Response Grounding, Factual Faithfulness, Epistemic Boundary Discipline, and Decision Support Reliability of Large Language Models interacting with meteorological telemetry.**

In operational meteorology, an agentic AI system operates downstream from NWP numerical models (such as ECMWF, GFS, or Open-Meteo ensembles). The primary failure mode of LLMs in this role is **hallucinatory divergence**—fabricating non-existent rain, asserting contradictory temperatures, confusing rain probability with volume, underreporting severe convective storms, or confidently answering impossible far-future queries. The benchmark evaluates how effectively different system architectures prevent these failure modes when presented with identical atmospheric telemetry.

---

## 2. Benchmark Dataset Architecture

The benchmark dataset (`backend/evaluation/datasets/weather_benchmark.json`) consists of **50 curated, reproducible test cases** distributed evenly across **10 distinct task categories** (5 test cases per category):

| Category Key | Category Name | Task Description & Meteorological Challenge | Target Cases |
|---|---|---|---|
| `current_weather` | Current Conditions | Extraction of real-time temperature, wind speed, humidity, and weather code conditions. | `TC-CUR-001` – `TC-CUR-005` |
| `hourly_forecast` | Hourly Trajectories | Multi-hour timeline interpretation, temperature peaks, diurnal variations, and timing. | `TC-HLY-001` – `TC-HLY-005` |
| `temperature_comparison` | Spatial Comparisons | Comparative analysis between two distinct geographic locations (e.g. Phoenix vs. Tokyo). | `TC-CMP-001` – `TC-CMP-005` |
| `precipitation_and_rainfall` | Precipitation Dynamics | Disentangling precipitation probability (%) from accumulation volume (mm). | `TC-PRC-001` – `TC-PRC-005` |
| `weather_trends` | Multi-Day Trends | Detecting multi-day temperature gradients, cooling/warming trends, and air pressure shifts. | `TC-TRD-001` – `TC-TRD-005` |
| `multistep_reasoning` | Multi-Step Synthesis | Multi-hop reasoning combining weather data with practical travel, clothing, or outdoor activity advice. | `TC-MLT-001` – `TC-MLT-005` |
| `evidence_based_reasoning` | Evidence Grounding | Strict adherence to observational evidence, requiring explicit citation and proof linkage. | `TC-EVD-001` – `TC-EVD-005` |
| `weather_safety_and_risk` | Hazard & Risk Classification | Identifying severe storms, gale winds, and heatwaves; classifying hazard severity into LOW/MOD/HIGH/SEVERE. | `TC-RSK-001` – `TC-RSK-005` |
| `missing_or_incomplete_data` | Fault Tolerance | Graceful degradation under missing sensor channels, empty hourly arrays, and unknown coordinates. | `TC-INC-001` – `TC-INC-005` |
| `hallucination_resistance` | Adversarial Refusal | Refusing unanswerable queries (10-year forecasts, fictional planets, leading false premises). | `TC-HAL-001` – `TC-HAL-005` |

---

## 3. Synthetic Weather Fixtures: Frozen Ground Truth

To guarantee **100% reproducible, deterministic ground truth** across all evaluations without network latency, API drift, or live weather fluctuations, the benchmark utilizes **12 synthetic reference weather fixtures** (`backend/evaluation/fixtures/weather_fixtures.json`).

Each fixture models a realistic, scientifically plausible meteorological scenario conforming strictly to the Open-Meteo JSON schema:
1. `FIX_DEHRADUN_MILD`: Mild autumn conditions (21.8°C, calm winds, zero rain).
2. `FIX_LONDON_RAIN`: Persistent stratiform rain (13.5°C, 12.7 mm rain over 24h, 85% probability).
3. `FIX_PARIS_STORM`: Severe summer convective storm (squall line, 65 km/h gusts, 48 mm precipitation, SEVERE hazard).
4. `FIX_TOKYO_HEAT`: Extreme summer heatwave (38.5°C peak temperature, high UV index, HIGH thermal hazard).
5. `FIX_CHICAGO_FREEZE`: Polar vortex event (-14.2°C temperature, sub-zero wind chills, gale gusts).
6. `FIX_BERLIN_WIND`: Severe synoptic windstorm (sustained 45 km/h, gusts to 78 km/h, HIGH wind hazard).
7. `FIX_PHOENIX_TREND`: Continuous 48-hour warming trend (rising from 28°C to 37°C across consecutive days).
8. `FIX_SYDNEY_CLEAR`: Clear oceanic high-pressure system (24.0°C, low humidity, ideal outdoor conditions).
9. `FIX_REYKJAVIK_COLD`: Sub-polar maritime chill (2.1°C, sleet, near-freezing drizzle).
10. `FIX_INCOMPLETE_SENSORS`: Faulty station telemetry (temperature and humidity active, rainfall sensor channel returning null).
11. `FIX_CORRUPTED_HOURLY`: Empty hourly forecast array representing upstream data provider dropouts.
12. `FIX_EDGE_EMPTY`: Completely empty meteorological payload for fault-tolerance evaluation.

---

## 4. Architectural Ablation: Three Isolated Systems

To rigorously isolate the performance contributions of tool retrieval versus post-retrieval verification guardrails, three cleanly isolated architectures were implemented and evaluated under identical conditions:

### System A: Baseline LLM (`baseline_llm`)
- **Configuration:** Direct zero-shot prompt completion.
- **Available Tools:** None (`tools = None`).
- **Fixture Access:** None.
- **System Prompt:** `BASELINE_SYSTEM_PROMPT` instructing the model to answer strictly from parametric knowledge, explicitly disclaim live sensor access, and avoid fabricating current observations.
- **Purpose:** Represents conventional consumer LLM behavior when queried about physical-world conditions without tools.

### System B: Tool-Using Agent (`tool_using_agent`)
- **Configuration:** Conventional ReAct-style agentic tool calling.
- **Available Tools:** `RETRIEVAL_TOOLS` (`geocode_location`, `get_current_weather`, `get_hourly_forecast`).
- **Fixture Access:** Authorized access via `FixtureToolExecutor` interceptor.
- **System Prompt:** `TOOL_AGENT_SYSTEM_PROMPT` instructing standard weather assistant behavior.
- **Ablation Boundary:** Phase 4 claim extraction, validator, hallucination recovery controller, and Phase 6 risk engine are **completely stripped**.
- **Purpose:** Represents industry-standard tool-augmented LLM architectures (e.g. OpenAI Function Calling, LangChain, Toolformer) lacking formal post-generation verification.

### System C: Complete Sky Reader (`sky_reader_full`)
- **Configuration:** Full production agentic platform.
- **Available Tools:** Full tool suite (Retrieval + Deterministic Trend Analysis + Recommendations + Risk Engine).
- **Fixture Access:** Authorized access via `FixtureToolExecutor` interceptor.
- **System Prompt:** Full production `SYSTEM_PROMPT` including risk levels, uncertainty guidelines, and trend guidance.
- **Pipeline:** Full execution of `EvidenceEngine` compilation, `ClaimExtractor`, `ClaimValidator`, `HallucinationController` recovery/fallback, and `ExplanationEngine` proof generation.
- **Purpose:** Evaluates the complete neuro-symbolic, evidence-grounded framework.

---

## 5. Experimental Standardization & Integrity Controls

1. **Identical Foundation Model:** All three systems utilize the same underlying model—**`openai/gpt-oss-120b`**—served via Groq Cloud API, ensuring that differences in performance reflect architectural differences rather than parameter scale or pre-training variations.
2. **Identical Query Presentation:** All systems receive the exact same natural language string from `test_case.question` without prompt alterations or supplementary hints.
3. **Zero Ground-Truth Leakage:** Ground-truth expected numbers, expected claims, and risk levels are strictly segregated in `weather_benchmark.json` and are never provided to model prompts, system instructions, or tool return payloads.
4. **Synthetic Execution Isolation:** In `synthetic_fixture` mode, `FixtureToolExecutor` intercepts all geocoding and weather queries in memory, guaranteeing zero live Open-Meteo HTTP traffic and identical fixture delivery across runs.
5. **Deterministic Evaluation Pipeline:** All metrics are computed by deterministic Python evaluators (`backend/evaluation/metrics/`) using scientific numerical tolerance comparisons and rule-based claim audits, eliminating LLM-as-a-judge non-determinism.
