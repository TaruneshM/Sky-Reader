# 🔬 Sky Reader: Reproducibility Appendix and Experimental Manifest

**Paper:** Sky Reader: An Evidence-Grounded Agentic AI Framework for Reliable Weather Intelligence and Risk Assessment  
**Document Type:** Publication Reproducibility Appendix  
**Target Venue Standard:** IEEE / ACM Artifact Availability & Reproducibility Guidelines  

---

## 1. Repository Structure & Artifact Locations

The research evaluation artifacts, source implementations, and datasets are organized within the project repository as follows:

```
/home/victus/sky reader /Sky-Reader/
├── backend/
│   ├── agent/                      # Core agent implementation & tool registry
│   │   ├── agent.py                # WeatherAgent with verification loop
│   │   ├── executor.py             # Agent execution loop & memory management
│   │   └── tools.py                # Function schemas for weather tools
│   ├── weather/                    # Meteorological analysis & retrieval
│   │   ├── service.py              # Open-Meteo API client
│   │   ├── analysis.py             # Deterministic weather analytics
│   │   ├── risk_engine.py          # Deterministic WeatherRiskAssessmentEngine
│   │   └── risk_models.py          # WeatherRiskAssessment Pydantic schemas
│   ├── evidence/                   # Neuro-symbolic evidence & claim verification
│   │   ├── evidence_engine.py      # Evidence compilation & proof construction
│   │   └── models.py               # WeatherEvidenceItem & Claim schemas
│   └── evaluation/                 # Benchmark evaluation framework
│       ├── datasets/
│       │   └── weather_benchmark.json    # 50 benchmark cases across 10 categories
│       ├── fixtures/
│       │   └── weather_fixtures.json     # 12 synthetic Open-Meteo telemetry fixtures
│       ├── metrics/                      # Modular evaluation metrics engine
│       │   ├── numerical.py        # Variable-specific tolerance matching
│       │   ├── factual.py          # Factual claim verification
│       │   ├── hallucination.py    # Intrinsic/extrinsic hallucination scoring
│       │   └── risk.py             # Risk classification accuracy & underreports
│       ├── results/                # 160 preserved raw execution JSON records
│       ├── analysis/               # Comparative evaluation summaries & reports
│       │   ├── comparative_summary.json  # Canonical metric aggregation
│       │   └── statistical_analysis.json # Paired non-parametric statistical tests
│       └── research/               # Formal research manuscript artifacts
│           ├── paper.md            # Complete Markdown research manuscript
│           ├── latex/              # IEEEtran LaTeX source bundle & Makefile
│           ├── figures/            # Publication vector figures (SVG)
│           ├── authoritative_metrics.json # Single source of truth for all metrics
│           └── references.bib      # 16 verified BibTeX entries
└── frontend/                       # Interactive conversational interface
    └── src/components/
        └── RiskCard.jsx            # Structured risk visualization component
```

---

## 2. Experimental Environment & Model Specification

| Parameter | Specification |
|---|---|
| **Foundation Model** | `openai/gpt-oss-120b` |
| **Inference Provider** | Groq Cloud API |
| **Decoding Temperature** | 0.0 (deterministic greedy decoding where supported) |
| **Context Window** | 8,192 tokens |
| **Execution Hardware** | Linux x86_64, Python 3.14.0 (virtual environment `backend/venv`) |
| **Backend Framework** | FastAPI 0.162.0, Uvicorn 0.54.0, Pydantic v2.14.2 |
| **Frontend Framework** | React 18, Vite 8.3.1, Tailwind CSS |
| **API Secret Protection** | Groq API keys are read strictly from environment variable `GROQ_API_KEY`; no private keys are embedded in codebase or evaluation datasets. |

---

## 3. Dataset and Fixture Specification

- **Benchmark Dataset:** `backend/evaluation/datasets/weather_benchmark.json` (v1.0.0)
  - 50 distinct test cases uniformly distributed across 10 meteorological categories ($n=5$ per category).
  - 43 test cases require numerical variable extraction ($M_{	ext{num}}=43$) spanning 72 ground-truth expected variables.
  - 50 test cases require factual claim verification spanning 149 ground-truth expected facts.
  - 11 test cases require hazard severity classification ($M_{	ext{risk}}=11$).
- **Synthetic Telemetry Fixtures:** `backend/evaluation/fixtures/weather_fixtures.json`
  - 12 frozen synthetic Open-Meteo payloads representing diverse atmospheric states (e.g., severe convective squall, gale windstorm, extreme heatwave, sub-zero blizzard premise, null-sensor payload).
  - Fixtures are injected via `EvaluationAdapter` to guarantee 100% bit-exact reproducibility regardless of external network conditions.

---

## 4. Execution Policy, Timeouts, and Deduplication

1. **First-Attempt Timeout Budget:**
   - Category 1 (`current_weather`): 30.0 seconds per case.
   - Categories 2–10: 60.0 seconds per case.
   - All three systems were evaluated under identical initial budgets.
2. **First-Attempt Reliability:**
   - Baseline LLM: 50/50 (100.0%) completed without timeout.
   - Tool-Using Agent: 50/50 (100.0%) completed without timeout.
   - Complete Sky Reader: 43/50 (86.0%) completed without timeout; 7 timeouts (14.0%) on complex multi-hop queries.
3. **Retry Timeout Budget:**
   - The 7 timed-out Sky Reader cases were re-executed under an extended 100.0-second budget (`run_20261121_065501_3b721b`).
   - All 7 cases reached successful completion (100.0% eventual completion).
4. **Canonical Deduplication Policy:**
   - Canonical response selection selects the latest completed attempt per `(test_case_id, system)` pair.
   - All historical initial attempt records remain permanently preserved in their original session directories to support independent reliability audits.

---

## 5. Statistical Testing Procedures & Random Seeds

1. **Permutation Sign-Flip Tests:**
   - Evaluated on matched case pairs ($N=50$, $M=43$).
   - Monte Carlo resamples: $B = 2,000$.
   - Test statistic: Mean difference $ar{D} = rac{1}{n} \sum (x_{i, A} - x_{i, B})$.
   - Two-sided empirical $p$-value: Proportion of permutations where $|ar{D}_{	ext{perm}}| \ge |ar{D}_{	ext{obs}}|$.
2. **Bootstrap Confidence Intervals:**
   - Percentile bootstrap with replacement: $B = 2,000$ resamples.
   - Random seed: `42` (fixed across all statistical runs).
   - Interval: $[	heta_{0.025}, 	heta_{0.975}]$.
3. **McNemar's Exact Binomial Test:**
   - Evaluated on $N=11$ risk cases.
   - Contingency table: $b = 6$ (Sky Reader correct, Tool Agent wrong), $c = 0$ (Tool Agent correct, Sky Reader wrong).
   - Under $H_0: b \sim 	ext{Binomial}(6, 0.5)$.
   - Exact two-sided $p = 2 	imes (0.5)^6 = 0.03125$.
   - Bonferroni multiple-comparison threshold across 12 metrics: $lpha_{	ext{corr}} = 0.05 / 12 = 0.00417$. Disclosed as nominally significant under exploratory hypothesis testing.

---

## 6. Commands for Benchmark Reproduction

### 6.1 Running Unit Test Suites
```bash
# Activate environment
source backend/venv/bin/activate

# Execute all backend tests
python -m unittest discover -s backend/tests
```

### 6.2 Running the Comparative Benchmark Runner
```bash
# Execute benchmark runner across all systems
python backend/evaluation/runner.py --dataset backend/evaluation/datasets/weather_benchmark.json --mode synthetic_fixture
```

### 6.3 Aggregating and Auditing Results
```bash
# Run comparative analysis and generate statistical summary
python backend/evaluation/analysis/comparator.py
```
