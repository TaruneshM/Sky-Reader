# 📊 Sky Reader Evaluation & Benchmarking Subsystem (Phases 7.1, 7.2, 7.3 & 7.4)

This module provides the reproducible evaluation foundation, execution runner, multi-dimensional metrics engine, and comparative statistical analysis pipeline for **Sky Reader (WeatherGPT)**, enabling systematic benchmarking and empirical comparison between three isolated evaluation systems:

1. **`baseline_llm`**: Vanilla language model without tool access (generates ungrounded estimates from prior training weights).
2. **`tool_using_agent`**: Standard LLM with tool calling enabled (fetches weather data via tool calls but lacks Phase 4 claim validation and Phase 6 risk guardrails).
3. **`sky_reader_full`**: Complete Sky Reader platform (agentic reasoning + deterministic meteorological analysis + Phase 4 claim extraction, validation & hallucination control + Phase 6 risk assessment and uncertainty communication).

---

## 📁 Directory Structure

```text
backend/evaluation/
├── __init__.py                 # Package exports (models, adapters, runner, store, metrics, analyzer)
├── models.py                   # Pydantic validation schemas (TestCase, EvaluationDataset, WeatherFixture)
├── dataset_loader.py           # Loader & cross-validator functions
├── generate_benchmark_data.py  # Deterministic dataset and fixture generator
├── result_models.py            # Result schemas (EvaluationResult, ExecutionStatus, RunSummary)
├── config.py                   # Runner configuration (EvaluationConfig)
├── adapters.py                 # System execution adapters & FixtureToolExecutor
├── result_store.py             # Incremental JSONL storage & crash-resilient persistence
├── runner.py                   # Execution orchestrator & CLI interface
├── metrics/                    # Phase 7.3 Multi-dimensional Metrics Engine
│   ├── __init__.py             # Exports all evaluators, result schemas, and legacy metrics
│   ├── base.py                 # Base metric classes & shared status Enums
│   ├── numerical.py            # Numerical accuracy, tolerance validation & unit conversions
│   ├── factual.py              # Polarity-aware factual claim & refusal evaluation
│   ├── hallucination.py        # Contradiction vs ungrounded claim detection
│   ├── evidence.py             # Evidence availability vs usage & citation auditing
│   ├── risk.py                 # Risk severity classification & confusion matrix entries
│   ├── performance.py          # Latency, retry counts, and execution failure isolation
│   ├── completeness.py         # Mandatory question component & criteria completeness
│   ├── aggregator.py           # Multi-dimensional scorecards & sliced aggregation
│   └── legacy.py               # Backward-compatible Phase 4 helper functions
├── analysis/                   # Phase 7.4 Comparative Analysis & Statistical Reliability
│   ├── __init__.py             # Lazy exports for ComparativeAnalyzer
│   ├── comparator.py           # Multi-system comparison, paired bootstrap & artifact generation
│   ├── benchmark_integrity_report.md # Dataset and fixture isolation audit
│   ├── comparative_report.md   # Final comparative evaluation report & discussion
│   ├── comparative_summary.json/csv # Global comparative matrix
│   ├── category_comparison.csv # System-by-category breakdown table
│   ├── error_analysis.json     # 8-class failure taxonomy & case studies
│   ├── statistical_analysis.json # 95% bootstrap CIs & paired hypothesis tests
│   ├── metric_comparison.svg   # Visual accuracy & completeness comparison chart
│   ├── latency_comparison.svg  # Mean vs P95 execution latency comparison chart
│   └── error_distribution.svg  # Error taxonomy frequency bar chart
├── datasets/
│   └── weather_benchmark.json  # 50 validated benchmark test cases across 10 categories
├── fixtures/
│   └── weather_fixtures.json   # 12 high-fidelity synthetic weather fixtures
├── results/                    # Execution artifacts grouped by run_id
│   └── <run_id>/
│       ├── results.jsonl       # Incremental line-delimited execution results
│       └── summary.json        # Final run summary and aggregate metrics
├── benchmark.py                # Comparative benchmark script (Phase 4 legacy)
├── ablation.py                 # Ablation study runner (Phase 4 legacy)
└── README.md                   # This documentation
```

---

## 🏷️ Test Categories & Distribution (Phase 7.1)

The benchmark dataset consists of **50 test cases**, evenly distributed across 10 meteorological and agentic categories (5 test cases each):

| Category Key | Category Title | Primary Evaluation Objective | Case IDs |
|---|---|---|---|
| `current_weather` | Current Weather | Accuracy of real-time observed variables (temperature, humidity, pressure, wind). | `TC-CUR-001` – `005` |
| `hourly_forecast` | Hourly Forecast | Accuracy of diurnal curves, peak rain hours, and overnight lows. | `TC-HLY-001` – `005` |
| `temperature_comparison` | Temperature Comparison | Today vs tomorrow comparison, day-vs-night delta, cross-city contrasts. | `TC-CMP-001` – `005` |
| `precipitation_and_rainfall` | Precipitation & Rainfall | Separation of precipitation probability (%) from total accumulation (mm). | `TC-PRC-001` – `005` |
| `weather_trends` | Weather Trends | Identification of upward, downward, or steady trajectories and pressure drops. | `TC-TRD-001` – `005` |
| `multistep_reasoning` | Multi-Step Reasoning | Decision support requiring multiple variables (umbrella, outdoor windows, travel). | `TC-MLT-001` – `005` |
| `evidence_based_reasoning` | Evidence-Based Reasoning | Queries requiring explicit citations to measurement IDs, values, and provenance. | `TC-EVD-001` – `005` |
| `weather_safety_and_risk` | Weather Safety & Risk | Severity classification (`LOW`, `MODERATE`, `HIGH`, `SEVERE`) and precautions. | `TC-RSK-001` – `005` |
| `missing_or_incomplete_data` | Missing & Incomplete Data | Graceful degradation without false alarms when sensor channels are null or empty. | `TC-INC-001` – `005` |
| `hallucination_resistance` | Hallucination Resistance | Refusal to fabricate far-future weather, refuting false claims, and probabilistic hedging. | `TC-HAL-001` – `005` |

---

## 🔬 Synthetic Reference Fixtures

Benchmark test cases link to controlled synthetic fixtures in `fixtures/weather_fixtures.json`. Each fixture is strictly validated by Pydantic:
- **`is_synthetic: true`**: Explicitly marked so synthetic test data is never confused with live observations.
- **Open-Meteo Compatibility**: Formatted with standard `current` and 48-hour `hourly` structures.
- **Coverage**:
  - `FIX_DEHRADUN_MILD`: Clear skies, zero rain, pleasant diurnal curve.
  - `FIX_LONDON_RAIN`: Overcast with 18.5 mm moderate rainfall.
  - `FIX_TOKYO_HEAT`: Dangerous heatwave peaking at 41.5°C.
  - `FIX_CHICAGO_FREEZE`: Arctic cold wave with -15.0°C lows.
  - `FIX_PARIS_STORM`: Convective thunderstorm with WMO 99 hail and 68 km/h gales.
  - `FIX_MUMBAI_MONSOON`: Torrential monsoon with 75.0 mm accumulation.
  - `FIX_BERLIN_WIND`: Frontal high-wind event with 52.0 km/h gusts.
  - `FIX_PHOENIX_TREND`: Steep desert warming (+16°C rise).
  - `FIX_REYKJAVIK_COLD`: Subpolar coastal freeze oscillating around 0°C.
  - `FIX_SYDNEY_CLEAR`: Ideal outdoor activity conditions.
  - `FIX_INCOMPLETE_SENSORS`: Null precipitation and corrupted wind sensors.
  - `FIX_CORRUPTED_HOURLY`: Empty forecast payloads for error-handling tests.

---

## ⚙️ Evaluation Systems & Isolation Architecture (Phase 7.2)

1. **`BaselineLLMAdapter`**: Receives `tools=None` and zero fixture access. Instructed that it has no real-time meteorological sensors.
2. **`ToolUsingAgentAdapter`**: Standard tool-calling agent using `FixtureToolExecutor`. Strictly bypasses Phase 4 claim verification and Phase 6 risk guardrails.
3. **`SkyReaderAdapter`**: Executes complete production `run_agent()` pipeline with injected `FixtureToolExecutor`, full claim verification, hallucination control, explanations, and risk assessments.

---

## 📐 Multi-Dimensional Metrics Engine (Phase 7.3)

The metrics subsystem under `backend/evaluation/metrics/` evaluates raw execution outputs across 7 independent dimensions without arbitrary single-score blending:

### 1. Numerical Accuracy (`numerical.py`)
- **Tolerances**: Applies per-variable allowed margins from `evaluation_criteria.allowed_numerical_tolerances`.
- **Unit Conversions**: Standardizes units to canonical meteorological units (°F $\to$ °C, mph/m/s/knots $\to$ km/h, inches/cm $\to$ mm, inHg $\to$ hPa).
- **Measurement Isolation**: Extracts numbers based on meteorological variable keywords and units, preventing timestamps (`14:00`), years (`2026`), or day counts from corrupting weather values.
- **Missing vs. Incorrect**: Distinguishes values not found (`MISSING`) from values found outside tolerance (`INCORRECT`).

### 2. Factual Accuracy (`factual.py`)
- **Polarity-Aware Matching**: Evaluates negative polarity constraints (e.g. "umbrella not needed" vs "bring an umbrella").
- **Refusal & Hedging**: Evaluates whether the system appropriately hedged or refused to predict far-future or missing data.
- **Status Classification**: Each expected claim is graded as `CORRECT`, `INCORRECT` (contradicted), `UNADDRESSED`, or `UNSUPPORTED`.

### 3. Hallucination Detection (`hallucination.py`)
- **Hard Contradictions vs. Ungrounded Claims**: Distinguishes claims that directly contradict fixture reference data from ungrounded claims.
- **Absence of Citations $\neq$ Hallucination**: A factually correct statement without an evidence tag is recognized as grounded even if uncited.
- **Metrics**: Computes `hallucination_rate`, `contradiction_rate`, `unsupported_rate`, and `clean_case_ratio`.

### 4. Evidence Grounding (`evidence.py`)
- **Availability vs. Usage**: Distinguishes whether evidence was accessible (via tools/fixtures) from whether the response actively cited or leveraged it.
- **Citation Validation**: Verifies evidence IDs (`ev_...`) against generated evidence collections, flagging fabricated citation IDs.
- **Proof Structure**: Audits Phase 4 `ExplanationProof` for supporting evidence and measurement citations.

### 5. Risk Assessment Accuracy (`risk.py`)
- **Classification Matching**: Evaluates overall risk level (`LOW`, `MODERATE`, `HIGH`, `SEVERE`) against expected risk.
- **Severity Errors**: Measures underreported vs overreported severity.
- **Confusion Matrix**: Emits `{actual: "...", predicted: "..."}` records suitable for confusion matrix analysis.
- **Hazard Recall & Precision**: Tracks matched, missed, and false-positive hazard types.

### 6. Performance & Execution Health (`performance.py`)
- **Runtime Metrics**: Wall-clock latency (`latency_ms`), retry counts, and status (`COMPLETED`, `FAILED`, `TIMEOUT`).
- **Failure Isolation**: Execution failures and timeouts are flagged with `is_evaluable=False` and tracked under health metrics — **never scored as incorrect meteorological answers**.

### 7. Response Completeness (`completeness.py`)
- **Criteria Auditing**: Evaluates presence of queried location, expected variables, risk notes, uncertainty notes, and refusals.
- **Completeness Score**: Computes the exact ratio of satisfied applicable criteria (0.0 to 1.0).

---

## 📊 Aggregation & Structured Reporting

```python
from backend.evaluation.dataset_loader import load_benchmark_suite
from backend.evaluation.result_store import ResultStore
from backend.evaluation.metrics import MetricsEngine

dataset, fixtures = load_benchmark_suite()
store = ResultStore("backend/evaluation/results")
results = store.load_results("run_20261117_example")

engine = MetricsEngine()
report = engine.evaluate_run(results, dataset, fixtures)

# Multi-dimensional summary by system slice
for sys_name, summary in report.by_system.items():
    print(f"System: {sys_name}")
    print(f"  Evaluable Cases: {summary.evaluable_cases}/{summary.total_cases}")
    print(f"  Numerical Accuracy: {summary.mean_numerical_accuracy}")
    print(f"  Factual Accuracy: {summary.mean_factual_accuracy}")
    print(f"  Hallucination Rate: {summary.mean_hallucination_rate}")
    print(f"  Clean Case Ratio: {summary.clean_case_ratio}")
    print(f"  Evidence Usage Rate: {summary.evidence_usage_rate}")
    print(f"  Risk Accuracy: {summary.risk_classification_accuracy}")
    print(f"  Mean Latency: {summary.mean_latency_ms} ms")
```

---

## 🧪 Testing & Verification

Comprehensive offline tests for all evaluation subsystems run without requiring external API keys or live network access:

```bash
# Run Phase 7.3 metrics engine tests (all 7 dimensions, unit conversions, edge cases)
PYTHONPATH=. backend/venv/bin/python backend/tests/test_evaluation_metrics.py

# Run Phase 7.2 runner tests (isolation, injection, persistence, retries, timeouts)
PYTHONPATH=. backend/venv/bin/python backend/tests/test_evaluation_runner.py

# Run Phase 7.1 dataset validation tests (schema integrity, fixture cross-referencing)
PYTHONPATH=. backend/venv/bin/python backend/tests/test_evaluation_dataset.py

# Run the current offline backend regression suite from the repository root
GROQ_API_KEY= GEMINI_API_KEY= OPENROUTER_API_KEY= backend/venv/bin/python -m pytest \
  backend/tests backend/test_analysis.py backend/test_phase4.py
```

---

For the current frozen-suite command, verified Stage 1.7E metrics and live-validation scope, see the [root README](../../README.md#testing-and-evaluation).

## ⚠️ Known Limitations & Scope Boundaries

1. **Metrics Engine Only (Phase 7.3)**: This module evaluates results and generates structured multi-dimensional reports. It **does not generate comparative research papers, cross-system statistical significance tests, or visual UI dashboards** (Phase 7.4 scope).
2. **Deterministic Evaluation**: Semantic matching uses deterministic keyword, polarity, entity, and concept token checking. It does not invoke secondary LLM-as-a-judge calls, maintaining reproducibility, zero cost, and zero non-deterministic drift.
