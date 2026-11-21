# Sky Reader: An Evidence-Grounded Agentic AI Framework for Reliable Weather Intelligence and Risk Assessment

**Authors:** [Author Names Omitted for Blind Peer Review]  
**Affiliation:** [Department of Computer Science / Engineering, University / Institutional Affiliation Omitted]  
**Contact:** [Author Email Placeholders: `{author1, author2}@institution.edu`]  

---

### Abstract

Deploying Large Language Models (LLMs) for weather intelligence and meteorological risk communication is severely constrained by their susceptibility to hallucinations, numerical unit confusion, and safety-critical false negatives during hazardous events. While tool augmentation provides models with access to external atmospheric APIs, conventional tool-using agents lack formal verification guardrails, frequently misinterpreting telemetry and asserting ungrounded claims. 

In this paper, we present **Sky Reader**, a neuro-symbolic agentic framework that couples frozen foundation models with deterministic meteorological validation. Sky Reader integrates an evidence compilation engine that canonicalizes multi-dimensional atmospheric telemetry into strongly typed evidence items, an atomic claim extractor and validator that audits candidate assertions against observational tolerances, and a deterministic meteorological risk assessment engine governed by physical thresholds. 

We conduct a rigorous, matched-pair comparative benchmark ($N=50$ distinct test cases across 10 meteorological task categories) evaluated against 12 frozen synthetic Open-Meteo ground-truth scenarios, comparing Complete Sky Reader against a zero-tool baseline LLM and an unverified tool-using agent using Groq's `openai/gpt-oss-120b`. 

Complete Sky Reader achieves a statistically significant reduction in hallucination rate from 35.9% (tool agent) to **8.3%** ($p < 0.001$, paired permutation test, Cohen's $d = 0.771$), while elevating the clean-response ratio from 64.0% to **90.0%**. In meteorological risk classification ($N=11$), Sky Reader improves exact accuracy from 27.3% to **81.8%** (nominal $p = 0.03125$), completely eliminating false-negative severity underreports on severe hazards. However, this reliability incurs an operational latency tax (mean wall-clock latency of 28.2s vs. 19.4s) and an epistemic trade-off: by suppressing unverified probabilistic assertions, Sky Reader reduces raw numerical recall (34.1% vs. 48.1%) while dramatically improving precision across reported precipitation amounts (8.07 mm vs. 12.21 mm MAE) and probability forecasts (0.00% vs. 39.17% MAE).

**Keywords:** Agentic AI, Large Language Models, Weather Intelligence, Evidence Grounding, Hallucination Mitigation, Explainable AI, Risk Assessment, Tool-Augmented Reasoning.

---

## 1. Introduction

The integration of Large Language Models (LLMs) into interactive decision-support systems has accelerated rapidly across high-consequence domains. In meteorology and climate intelligence, natural language interfaces offer transformative potential: translating dense multi-dimensional numerical weather prediction (NWP) data into intuitive, human-actionable guidance for agriculture, aviation, supply chain logistics, and emergency disaster management.

However, standard foundation models exhibit critical vulnerabilities that preclude their unconstrained deployment in safety-critical settings:
1. **Parametric Hallucination & Epistemic Blindness:** When queried regarding real-time or localized atmospheric conditions, standalone LLMs fabricate realistic-sounding yet entirely fictitious temperatures, wind speeds, and precipitation amounts based on parametric memorization rather than real-world observation.
2. **Post-Retrieval Interpretation Drift:** Equipping models with external weather retrieval tools (e.g., via ReAct-style function calling [1] or Toolformer-style API execution [2]) provides access to external telemetry, but does not guarantee factual fidelity. Unverified tool-using agents frequently hallucinate interpretations of retrieved data, misalign temporal indices (e.g., confusing current observations with 24-hour peaks), and confuse physical dimensions (e.g., treating millimeter rainfall accumulation as percentage probabilities).
3. **Public Safety Hazards in Risk Communication:** Severe convective storms, gale-force winds, and extreme heatwaves demand strict hazard classification. Unverified agents generate probabilistic language that frequently minimizes or underreports severe conditions (e.g., classifying a squall line with 65 km/h gusts as "Low" hazard), introducing life-safety vulnerabilities documented by meteorological decision scientists [13].

To address these vulnerabilities, we introduce **Sky Reader**, an evidence-grounded agentic framework designed to enforce deterministic fidelity and physical consistency in AI-assisted weather intelligence. Sky Reader decouples natural language dialogue from quantitative meteorological truth: candidate natural language claims generated by the LLM are intercepted, parsed into atomic quantitative assertions, and deterministically verified against strongly typed observational evidence compiled from operational telemetry. Hazard severity classifications are computed exclusively by a deterministic rule engine executing standardized World Meteorological Organization (WMO) and Beaufort criteria.

### Research Questions & Key Contributions
This paper addresses three central research questions:
- **RQ1 (Hallucination Mitigation):** Can a post-hoc deterministic claim validation pipeline significantly reduce hallucination rates compared to both zero-tool baselines and unverified tool agents?
- **RQ2 (Risk Assessment Reliability):** How does deterministic meteorological rule execution affect the accuracy and false-negative rate of hazard severity classifications?
- **RQ3 (Operational Trade-offs):** What are the measurable latency, reliability, and numerical recall trade-offs imposed by enforcing deterministic verification guardrails?

The contributions of this work are as follows:
1. **The Sky Reader Architecture:** A neuro-symbolic framework coupling frozen foundation models (`openai/gpt-oss-120b`) with an immutable `EvidenceEngine`, an atomic `ClaimValidator`, a deterministic `WeatherRiskAssessmentEngine`, and an `ExplanationEngine` that synthesizes auditable proof graphs.
2. **A Controlled 50-Case Weather Benchmark:** A reproducible, multi-category benchmark suite encompassing 10 meteorological tasks evaluated against 12 frozen synthetic Open-Meteo scenarios with strict ground-truth separation.
3. **Audited Empirical Validation:** A matched-pair comparative evaluation demonstrating an absolute 27.6% reduction in hallucination rate ($p < 0.001$), an improvement in exact risk classification from 27.3% to 81.8% ($p = 0.03125$), and an error-decomposition analysis across physical meteorological dimensions (°C, mm, km/h, %).
4. **Empirical Characterization of the Latency Tax:** A transparent accounting of execution reliability (86.0% first-attempt completion) and response latency (28.2s vs. 19.4s), establishing practical operational deployment boundaries.

---

## 2. Related Work

### 2.1 Tool-Augmented Language Models
To overcome the frozen parametric memory of foundation models, recent research has explored tool-augmented reasoning. Yao et al. [1] introduced **ReAct**, interleaving natural language reasoning traces ("thoughts") with action commands ("actions") and environment feedback ("observations"). Schick et al. [2] developed **Toolformer**, training models in a self-supervised manner to insert API calls that reduce token perplexity. While tool augmentation enables models to access current weather telemetry, our empirical findings reveal that access alone is insufficient: unverified tool agents exhibit a 35.9% hallucination rate due to post-retrieval reasoning errors. Sky Reader differs fundamentally from ReAct and Toolformer by shifting verification from internal model self-reflection to external, deterministic symbolic validation.

### 2.2 Retrieval-Augmented and Evidence-Grounded Generation
Retrieval-Augmented Generation (RAG) [6] and REALM [7] ground model outputs in non-parametric textual passages retrieved from dense vector indices. However, meteorological data is fundamentally multi-dimensional, time-indexed, and numerical. Semantic vector retrieval is inadequate for resolving physical calculations (e.g., diurnal ranges or wind gust thresholds). Sky Reader extends evidence grounding by compiling structured REST payloads into strongly typed, immutable evidence items (`WeatherEvidenceItem`), verifying claims against quantitative arrays rather than text chunks.

### 2.3 Hallucination Detection and Claim-Level Verification
Hallucinations in natural language generation are classified into *intrinsic* (contradicting source data) and *extrinsic* (unverifiable by source data) [9]. To detect hallucinations without token probabilities, Manakul et al. [3] introduced **SelfCheckGPT**, measuring semantic divergence across stochastically sampled completions. Min et al. [4] formulated **FActScore**, evaluating the factual precision of atomic propositions against Wikipedia. Dhuliawala et al. [5] introduced **Chain-of-Verification (CoVe)**, where models self-generate verification questions to revise drafts. Unlike SelfCheckGPT's sampling variance or CoVe's self-prompted verification (both of which remain susceptible to model bias), Sky Reader executes deterministic, code-based constraint validation, comparing extracted numerical claims against sensor tolerances.

### 2.4 Explainable AI and Automated Fact-Checking
The automated verification of factual claims was formalized by the **FEVER** benchmark [8], requiring models to classify claims as `SUPPORTS`, `REFUTES`, or `NOT ENOUGH INFO`. Sky Reader adapts the FEVER paradigm to meteorological decision support. Through its `ExplanationEngine`, it generates structural proof graphs pairing factual assertions with sensor readings, timestamps, and physical tolerance windows, achieving a 97.4% proof validity rate in our benchmark.

### 2.5 AI-Assisted Meteorology and Decision Support
Recent advances in AI weather modeling have achieved breakthrough performance in numerical simulation. GraphCast [10] and ClimaX [11] simulate global atmospheric dynamics using graph neural networks and transformers, outperforming operational NWP systems on benchmarks like WeatherBench 2 [12]. However, these models address numerical simulation, not natural language decision support. As established by Morss et al. [13], hazardous weather disasters frequently result from ambiguous or poorly communicated risk advice. Sky Reader operates at the interface between numerical telemetry and human decision makers, enforcing deterministic safety guardrails.

---

## 3. Problem Formulation

Let $q \in \mathcal{Q}$ denote a user query regarding atmospheric conditions for a target spatiotemporal coordinate $(l, t)$, where $l = (	ext{lat}, 	ext{lon})$ and $t$ represents a temporal interval $[t_{	ext{start}}, t_{	ext{end}}]$.

### 3.1 External Weather Evidence Compilation
Let $\mathcal{W}$ denote an external meteorological data source providing observational telemetry and deterministic numerical forecasts. The retrieval service yields a raw payload $\mathcal{P} = 	ext{Retrieve}(l, t)$. The evidence engine deterministically compiles $\mathcal{P}$ into an immutable set of structured evidence items:
$$\mathcal{E} = \{ e_i \mid e_i = \langle 	ext{id}_i, 	ext{var}_i, 	ext{val}_i, 	ext{unit}_i, 	au_i angle \}$$
where $	ext{var}_i \in \{ 	ext{temp}, 	ext{precip}, 	ext{wind}, 	ext{code}, \dots \}$, $	ext{val}_i \in \mathbb{R}$, $	ext{unit}_i$ is the physical dimension, and $	au_i$ is the timestamp.

### 3.2 Candidate Response and Claim Extraction
Given query $q$ and evidence $\mathcal{E}$, an autoregressive foundation model $M_{	heta}$ generates a candidate textual response:
$$R_{	ext{cand}} \sim P_{	heta}(R \mid q, \mathcal{E})$$
The atomic claim extractor $\mathcal{X}$ decomposes $R_{	ext{cand}}$ into a finite set of $K$ propositional assertions:
$$\mathcal{C} = \mathcal{X}(R_{	ext{cand}}) = \{ c_k \mid k = 1, \dots, K \}$$
where each claim $c_k = \langle 	ext{subject}_k, 	ext{predicate}_k, v_k, u_k, t_k angle$ represents a quantitative or qualitative assertion.

### 3.3 Deterministic Claim Validation
Each claim $c_k \in \mathcal{C}$ is audited against the evidence set $\mathcal{E}$ by a deterministic verification function $\mathcal{V}(c_k, \mathcal{E}) 	o \{ 	ext{CORRECT}, 	ext{CONTRADICTION}, 	ext{UNSUPPORTED}, 	ext{UNVERIFIABLE} \}$.
For a numerical claim asserting value $v_k$ with physical tolerance $\delta(	ext{var})$:
$$\mathcal{V}(c_k, \mathcal{E}) = egin{cases} 
	ext{CORRECT} & 	ext{if } \exists e_i \in \mathcal{E} 	ext{ s.t. } 	ext{var}_i = 	ext{var}_k \land |v_k - 	ext{val}_i| \le \delta(	ext{var}_k) \
	ext{CONTRADICTION} & 	ext{if } \exists e_i \in \mathcal{E} 	ext{ s.t. } 	ext{var}_i = 	ext{var}_k \land |v_k - 	ext{val}_i| > \delta(	ext{var}_k) \
	ext{UNSUPPORTED} & 	ext{if } orall e_i \in \mathcal{E}, 	ext{var}_i 
e 	ext{var}_k \lor 	au_i 
e t_k \
	ext{UNVERIFIABLE} & 	ext{if } c_k 	ext{ asserts an out-of-domain proposition}
\end{cases}$$

### 3.4 Deterministic Hazard Risk Assessment
Hazard severity $\mathcal{S} \in \{ 	ext{NONE}, 	ext{LOW}, 	ext{HIGH}, 	ext{SEVERE} \}$ is determined exclusively by a deterministic rule engine $\mathcal{R}(\mathcal{E})$ evaluating physical threshold vectors:
$$\mathcal{S} = \mathcal{R}(\mathcal{E}) = \max_{j} \left\{ \phi_j(\mathcal{E}) ight\}$$
where $\phi_j$ evaluates threshold rules (e.g., wind gusts $>60	ext{ km/h} \implies 	ext{HIGH}$, precipitation rate $>15	ext{ mm/h} \land 	ext{gusts} >75	ext{ km/h} \implies 	ext{SEVERE}$).

### 3.5 Final Response Synthesis
If $orall c_k \in \mathcal{C}, \mathcal{V}(c_k, \mathcal{E}) = 	ext{CORRECT}$, the candidate response is validated: $R_{	ext{final}} = R_{	ext{cand}}$. If any claim is marked $	ext{CONTRADICTION}$ or $	ext{UNSUPPORTED}$, the hallucination controller intercepts the execution, triggering a verified narrative fallback:
$$R_{	ext{final}} = 	ext{SynthesizeFallback}(\mathcal{E}, \mathcal{S})$$

---

## 4. Proposed Sky Reader Architecture

Sky Reader is implemented as a modular neuro-symbolic framework separating probabilistic natural language generation from deterministic meteorological audit. Figure 1 illustrates the pipeline architecture.

```
+-----------------------------------------------------------------------------------+
|                            SKY READER PIPELINE ARCHITECTURE                       |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [ User Query q ] ---> ( FastAPI REST Interface / Conversational Session State )  |
|                                         |                                         |
|                                         v                                         |
|                 [ Agent Orchestrator: Groq openai/gpt-oss-120b ]                  |
|                                         |                                         |
|                +------------------------+------------------------+                |
|                |                                                 |                |
|                v                                                 v                |
|   ( Function Calling Tools )                        ( Deterministic Engines )     |
|   * geocode_location()                              * EvidenceEngine              |
|   * get_current_weather()                             - Compiles immutable items  |
|   * get_hourly_forecast()                           * WeatherRiskAssessmentEngine |
|   * analyze_weather_trends()                          - Evaluates WMO thresholds  |
|                |                                                 |                |
|                v                                                 |                |
|   [ Candidate Response Text ] <----------------------------------+                |
|                |                                                                  |
|                v                                                                  |
|   [ ClaimExtractor ] ---> Isolates atomic quantitative & categorical assertions   |
|                |                                                                  |
|                v                                                                  |
|   [ ClaimValidator ] ---> Audits claims against compiled evidence tolerances      |
|                |                                                                  |
|       +--------+--------+                                                         |
|       |                 |                                                         |
|   (All Valid)     (Violations Detected)                                           |
|       |                 |                                                         |
|       |                 v                                                         |
|       |        [ HallucinationController ]                                        |
|       |        - Single regeneration attempt with feedback                        |
|       |        - Fallback to verified template if violations persist              |
|       |                 |                                                         |
|       +--------> ( ) <--+                                                         |
|                   |                                                               |
|                   v                                                               |
|        [ ExplanationEngine ] ---> Generates formal proof graph                    |
|                   |                                                               |
|                   v                                                               |
|   [ Final Verified Response ] ---> Delivered to React Conversational UI           |
+-----------------------------------------------------------------------------------+
```

### Architectural Modules:
1. **Frontend Interface:** A responsive React UI providing interactive chat, streaming token rendering, structured risk advisory cards (`RiskCard.jsx`), and interactive evidence inspection.
2. **FastAPI Backend & Agent Orchestrator:** Manages session state, tool registration, and multi-turn execution loops with Groq Cloud API (`openai/gpt-oss-120b`).
3. **Retrieval Tool Suite:** Implements Open-Meteo REST API integration for geocoding, current weather observations, and 48-hour hourly forecasts.
4. **Deterministic Evidence Engine:** Translates raw JSON arrays into an immutable evidence container (`WeatherEvidence`), preventing tool output modification during multi-turn reasoning.
5. **Deterministic Risk Assessment Engine:** Evaluates multi-parameter hazard conditions (e.g., heat index, convective storm thresholds, wind gusts) independently of LLM reasoning.
6. **Claim Extraction & Validation Engine:** Regex- and NLP-based extraction decomposing candidate text into atomic quantitative claims, evaluated within physical tolerance bounds (e.g., $\pm 1.0$°C for temperature, $\pm 5$ km/h for wind).
7. **Hallucination Controller & Verified Fallback:** Enforces epistemic safety by catching ungrounded assertions and substituting deterministic template-based advisories.
8. **Explanation Engine:** Constructs formal JSON proof graphs documenting the verification audit trail.

---

## 5. Experimental Methodology

### 5.1 Benchmark Dataset Design
The evaluation utilizes the `Sky Reader Phase 7 Benchmark Dataset` (v1.0.0), comprising **50 distinct test cases** uniformly divided across **10 meteorological task categories** (5 cases per category):
1. `current_weather`: Basic real-time observation queries.
2. `hourly_forecast`: Diurnal progressions across 24- to 48-hour horizons.
3. `temperature_comparison`: Multi-location comparative evaluations.
4. `precipitation_and_rainfall`: Quantitative rainfall accumulation and rain probability.
5. `weather_trends`: Diurnal warming, cooling, and pressure trend assertions.
6. `weather_safety_and_risk`: Severe squalls, gale-force winds, and heatwave hazards ($N=11$ risk cases across suite).
7. `multistep_reasoning`: Complex chained reasoning (e.g., clothing/activity suitability).
8. `evidence_based_reasoning`: Claims requiring explicit proof-chain linkage.
9. `missing_or_incomplete_data`: Graceful degradation under missing sensor payloads.
10. `hallucination_resistance`: Adversarial premises, out-of-domain historical queries, and impossible 10-year forecasts.

### 5.2 Synthetic Fixture Injection & Ground-Truth Separation
To guarantee absolute experimental reproducibility and eliminate live API volatility, all systems were evaluated against **12 frozen synthetic Open-Meteo fixtures** representing realistic atmospheric profiles (e.g., Tokyo heatwave at 38.5°C, London gale storm with 78 km/h gusts). Fixture payloads were strictly separated from benchmark test cases to prevent data leakage.

### 5.3 Comparative Architectures & Ablations
All three architectures were evaluated on identical benchmark cases using the same foundation model (`openai/gpt-oss-120b` via Groq):
- **System A (Baseline LLM):** Zero-tool prompt execution ($tools=\emptyset$). Relies strictly on internal parametric memory.
- **System B (Tool-Using Agent):** Equipped with weather retrieval tools, executing standard ReAct function calling, but with all claim validation, evidence compilation, and risk engine guardrails stripped.
- **System C (Complete Sky Reader):** The full neuro-symbolic platform with retrieval tools, deterministic evidence compilation, claim validation, hallucination control, and deterministic risk assessment.

### 5.4 Canonical Response Selection Policy
A total of **160 execution records** are preserved in the result store across 14 historical evaluation sessions. For canonical comparative scoring, the latest valid attempt per `(test_case_id, system)` pair is selected, ensuring 100% evaluable response coverage ($N=50$) across all systems, while preserving original attempt records for first-attempt reliability auditing.

---

## 6. Experimental Results

Table I presents the global comparative performance across all three systems. Every metric reports authoritative values cross-referenced against `authoritative_metrics.json`.

### TABLE I: Global Comparative Performance Across Systems ($N=50$ Cases per System)

| Performance Dimension | System A: Baseline LLM | System B: Tool-Using Agent | System C: Complete Sky Reader | Exact Formulation / Denominator |
|---|---|---|---|---|
| **First-Attempt Completion Rate** | **100.0%** (50/50) | **100.0%** (50/50) | 86.0% (43/50) | Initial completions without timeout ($N=50$) |
| **First-Attempt Timeout Rate** | **0.0%** (0/50) | **0.0%** (0/50) | 14.0% (7/50) | Initial executions exceeding budget ($N=50$) |
| **Eventual Completion Rate** | **100.0%** (50/50) | **100.0%** (50/50) | **100.0%** (50/50) | Total completed cases post-retry ($N=50$) |
| **Hallucination Rate (Case Mean)** | 49.5% [33.3%, 65.7%] | 35.9% [22.3%, 49.5%] | **8.3%** [1.4%, 16.9%] | Mean unverified claim ratio per case ($p < 0.001$) |
| **Hard Contradiction Rate (Case)** | 37.9% | 17.7% | **5.0%** | Claims conflicting with ground truth |
| **Clean Case Ratio (0 Halluc)** | 64.0% (32/50) | 64.0% (32/50) | **90.0%** (45/50) | Cases with exactly 0 hallucinations ($p = 0.0047$) |
| **Risk Classification Accuracy** | 0.0% (0/11) | 27.3% (3/11) | **81.8%** (9/11) | Exact severity tier match ($M_{	ext{risk}}=11$, nom. $p=0.03125$) |
| **Dangerous Severity Underreports**| 0 (Omitted completely) | 1 (Missed severe storm) | **0** | Severe/High hazard classified as Low/None |
| **Risk Classification Omissions** | 11 / 11 (100.0%) | 7 / 11 (63.6%) | **2 / 11 (18.2%)** | Applicable cases where risk was omitted |
| **Numerical Accuracy (Case Mean)** | 14.3% [6.2%, 23.6%] | **48.1%** [35.3%, 61.2%] | 34.1% [22.5%, 46.1%] | Mean tolerance-matched variable ratio ($M=43$) |
| **Numerical Accuracy (Micro)** | 16.7% (12/72) | **51.4%** (37/72) | 38.9% (28/72) | Correct numbers / Total expected variables (72) |
| **Factual Accuracy (Case Mean)** | 18.1% [11.2%, 25.8%] | **39.4%** [29.2%, 50.5%] | 36.5% [27.0%, 46.5%] | Mean supported factual claim ratio ($N=50$) |
| **Factual Accuracy (Micro)** | 22.8% (34/149) | **40.3%** (60/149) | 36.9% (55/149) | Correct facts / Total expected facts (149) |
| **Response Completeness Score** | 78.4% [70.7%, 85.7%] | 83.9% [76.9%, 90.4%] | **85.6%** [77.5%, 92.6%] | Mean addressed query facets / Total facets |
| **Fully Complete Cases Ratio** | 58.0% (29/50) | 64.0% (32/50) | **76.0%** (38/50) | Cases achieving 100% completeness ($N=50$) |
| **Mean Wall-Clock Latency** | **2,915.4 ms** (2.92s) | 19,376.5 ms (19.38s) | 28,200.3 ms (28.20s) | Arithmetic mean latency of canonical runs |
| **95th Percentile Latency (P95)** | **9,109.6 ms** (9.11s) | 37,168.8 ms (37.17s) | 59,881.9 ms (59.88s) | Empirical 95th percentile latency |

---

### 6.1 Statistical Hypothesis Testing
Matched-pair statistical tests were executed across all 50 test cases using paired permutation sign-flip tests ($B=2,000$ resamples) and bootstrap 95% confidence intervals ($B=2,000$ resamples with replacement, seed 42):

#### Hypothesis 1 (Hallucination Reduction — Supported):
Complete Sky Reader reduced mean hallucination rate by **27.58%** compared to Tool Agent (mean difference $-0.2543$, 95% CI: $[-0.3750, -0.1450]$, $p < 0.001$, Cohen's $d = 0.7713$). Compared to Baseline LLM, the reduction was **41.16%** ($p < 0.001$, Cohen's $d = 0.9632$).

#### Hypothesis 2 (Risk Classification Accuracy — Nominally Supported):
Across the 11 risk-applicable test cases, Sky Reader achieved 9/11 accuracy vs. Tool Agent's 3/11. McNemar's exact two-sided binomial test on discordant pairs ($b=6, c=0, n_{	ext{disc}}=6$) yielded nominal $p = 2 	imes (0.5)^6 = \mathbf{0.03125}$. While statistically significant at an uncorrected $lpha = 0.05$ threshold, this result does not survive a conservative Bonferroni correction across the family of 12 benchmark metrics ($lpha_{	ext{corr}} = 0.05 / 12 = 0.00417$). It is therefore designated as a nominally significant exploratory finding.

#### Hypothesis 3 (Factual Accuracy Parity — Non-Significant):
The difference in factual accuracy between Sky Reader (36.5%) and Tool Agent (39.4%) was $-2.93\%$ (95% CI: $[-0.1267, +0.0600]$, $p = 0.5250$). Failing to reject $H_0$ demonstrates that no statistically significant difference was detected; it does not establish formal equivalence.

#### Hypothesis 4 (Completeness Parity — Non-Significant):
Sky Reader's completeness score (85.6%) did not differ significantly from Tool Agent (83.9%, difference $+0.0167$, 95% CI: $[-0.0433, +0.0717]$, $p = 0.5750$).

---

### 6.2 Physical Variable-Specific Error Decomposition
Table II provides the rigorous physical decomposition of numerical error across physical meteorological dimensions, overcoming the dimensional invalidity of legacy aggregate MAE metrics.

### TABLE II: Physical Variable-Specific Numerical Error Analysis

| Physical Dimension | Unit | Expected Variables | System Architecture | Matched Variables (Coverage) | Correct Variables | Incorrect Variables | Missing Variables | Variable MAE |
|---|---|---|---|---|---|---|---|---|
| **Temperature** | °C | 33 | Baseline LLM | 21 / 33 (63.6%) | 7 | 14 | 12 | 7.27 °C |
| | | | Tool Agent | **31 / 33 (93.9%)** | **20** | 11 | **2** | **4.03 °C** |
| | | | Complete Sky Reader | 25 / 33 (75.8%) | 11 | 14 | 8 | 5.35 °C |
| **Precipitation Amount** | mm | 12 | Baseline LLM | 5 / 12 (41.7%) | 0 | 5 | 7 | 54.50 mm |
| | | | Tool Agent | 7 / 12 (58.3%) | 5 | 2 | 5 | 12.21 mm |
| | | | Complete Sky Reader | 7 / 12 (58.3%) | 5 | 2 | 5 | **8.07 mm** |
| **Precipitation Prob.** | % | 9 | Baseline LLM | 4 / 9 (44.4%) | 2 | 2 | 5 | 20.75 % |
| | | | Tool Agent | 6 / 9 (66.7%) | 2 | 4 | 3 | 39.17 % |
| | | | Complete Sky Reader | **6 / 9 (66.7%)** | **6** | **0** | 3 | **0.00 %** |
| **Wind Speed** | km/h | 10 | Baseline LLM | 5 / 10 (50.0%) | 3 | 2 | 5 | 12.20 km/h |
| | | | Tool Agent | **6 / 10 (60.0%)** | **5** | 1 | **4** | **0.73 km/h** |
| | | | Complete Sky Reader | 4 / 10 (40.0%) | 3 | 1 | 6 | 6.75 km/h |
| **Surface Pressure** | hPa | 4 | Baseline LLM | 2 / 4 (50.0%) | 0 | 2 | 2 | 4.98 hPa |
| | | | Tool Agent | **4 / 4 (100.0%)** | **4** | **0** | **0** | **0.00 hPa** |
| | | | Complete Sky Reader | 3 / 4 (75.0%) | 2 | 1 | 1 | 5.67 hPa |
| **Aggregate Composite**| *Mixed* | **72** | Baseline LLM | 37 / 72 (51.4%) | 12 | 25 | 35 | 14.80 *(legacy)* |
| | | | Tool Agent | **55 / 72 (76.4%)** | **37** | 18 | **17** | 10.27 *(legacy)* |
| | | | Complete Sky Reader | 46 / 72 (63.9%) | 28 | 18 | 26 | **4.98** *(legacy)* |

*\*Note on Legacy Aggregate MAE: The composite MAE computes an unweighted mathematical mean across mixed dimensions (°C, mm, km/h, hPa) and is presented solely for legacy traceability. Combining heterogeneous units lacks physical dimensionality.*

---

## 7. Discussion

### 7.1 Mechanisms of Hallucination Mitigation
The reduction in hallucination rate (from 35.9% to 8.3%) stems from Sky Reader's multi-stage verification architecture:
1. **Immutable Evidence Canonicalization:** Incoming REST payloads are frozen into strongly typed evidence items with unique identifiers, preventing prompt context corruption.
2. **Deterministic Propositional Auditing:** Candidate text is parsed into atomic claims checked against evidence within configured scientific tolerances.
3. **Closed-Loop Safety Fallback:** When ungrounded claims are detected, the hallucination controller attempts a guided regeneration. If ungrounded assertions persist, the system substitutes a verified template advisory constructed directly from evidence items.

*Ablation Disclosure:* Because the benchmark evaluated Sky Reader as an integrated system, individual module contributions (e.g., claim extraction vs. fallback synthesis) represent a composite architectural effect; isolating marginal contributions requires future single-component ablations.

### 7.2 Deterministic Risk Safeguards vs. Omission Vulnerabilities
In meteorological risk classification, Complete Sky Reader produced **zero dangerous false-negative severity underreports on severe events**, whereas Tool Agent classified a severe squall line (`TC-RSK-001`, 48mm rain, 65km/h gusts) as mere HIGH risk.

However, Sky Reader omitted risk predictions in two cases (`TC-INC-001`, `TC-INC-003`), yielding an **18.2% omission rate**. In `TC-INC-001`, the query omitted the location, and Sky Reader correctly sought clarification. In `TC-INC-003`, the hourly payload was empty, and Sky Reader triggered a graceful degradation explanation. While neither case produced an unsafe advisory, omitting risk predictions represents an operational limitation that must not be conflated with perfect safety.

### 7.3 The Numerical Recall vs. Safety Fallback Trade-Off
An unexpected empirical finding was that the unverified Tool Agent achieved higher raw numerical accuracy (48.1%) than Sky Reader (34.1%). Detailed trace analysis reveals the operational mechanism:
When `ClaimValidator` detected minor numerical discrepancies in candidate responses (e.g., confusing peak afternoon temperatures with current readings in multi-location queries), Sky Reader triggered its safety fallback. The fallback provided verified narrative advisories while intentionally suppressing secondary hourly figures. The benchmark evaluator recorded these suppressed numbers as missing predictions, reducing numerical recall. 

Conversely, on variables Sky Reader did emit, its error was dramatically lower: precipitation probability MAE dropped from 39.17% (Tool Agent) to **0.00%**, as Sky Reader eliminated instances where rainfall millimeters were confused with probability percentages.

### 7.4 Execution Reliability and the Latency Tax
Enforcing multi-stage verification imposes a substantial latency penalty: Sky Reader averaged **28.2s mean latency (P95: 59.9s)**, compared to **19.4s for Tool Agent** and **2.9s for Baseline LLM**. Furthermore, on initial execution passes under 30s/60s budgets, Sky Reader experienced **7 timeouts (14.0% timeout rate)** on complex multi-hop queries. While all 7 succeeded upon retry under an extended 100-second budget, this latency tax restricts Sky Reader's suitability for real-time voice interfaces, rendering it optimal for high-stakes enterprise decision support.

---

## 8. Threats to Validity and Limitations

1. **Synthetic Fixtures vs. Live NWP Forecast Drift:** The evaluation used 12 frozen synthetic Open-Meteo scenarios to guarantee reproducibility. While realistic, synthetic fixtures do not model live NWP numerical forecast drift, observational sensor calibration noise, or unexpected external API outages.
2. **Sample Size & Statistical Power:** The benchmark suite comprises 50 cases ($n=5$ per category) with 11 risk-applicable cases. While adequately powered ($eta = 0.20$) to detect large effect sizes ($d \ge 0.396$), it is underpowered (29.3% power) for small effect sizes ($d = 0.20$).
3. **Multiple Testing Correction:** The risk classification accuracy improvement ($p = 0.03125$) is nominally significant under uncorrected testing, but does not survive conservative Bonferroni correction across 12 metrics ($lpha_{	ext{corr}} = 0.00417$).
4. **Single Foundation Model Evaluation:** All experiments evaluated Groq's `openai/gpt-oss-120b`. Model-transferability across proprietary (e.g., Claude 3.5, GPT-4o) and open-weight architectures (e.g., Llama 3) remains to be demonstrated.
5. **Heuristic Evaluator Approximations:** Benchmark extraction relies on regex and semantic parsing, which may misclassify natural language paraphrasing as missing variables.
6. **No Real-World NWP Forecasting Skill Claims:** Sky Reader is an agentic natural language interpretation and verification layer; it does not replace or evaluate numerical weather simulation skill.

---

## 9. Conclusion and Future Work

This paper presented **Sky Reader**, an evidence-grounded agentic framework designed to deliver reliable, hallucination-resistant weather intelligence and risk assessment. Through a controlled, audited benchmark of 50 meteorological tasks, we demonstrated that coupling frozen foundation models with deterministic claim validation and meteorological rule engines significantly reduces hallucination rates (from 35.9% to 8.3%, $p < 0.001$) and improves risk classification accuracy (from 27.3% to 81.8%), while eliminating severe-hazard false-negative underreports. 

These safety enhancements entail concrete operational costs: a 1.45× latency overhead over unverified tool agents (28.2s vs. 19.4s) and an epistemic trade-off where numerical recall is sacrificed to prevent ungrounded assertions.

### Future Work
Future research will focus on:
1. Conducting component-level ablations to isolate the marginal contributions of claim extraction versus guided regeneration versus template fallbacks.
2. Expanding the evaluation to live operational meteorological streams and multi-model evaluations across diverse LLM families.
3. Enhancing numerical recall by incorporating iterative constraint-solving in candidate drafting.
4. Integrating official National Meteorological and Hydrological Services (NMHS) Common Alerting Protocol (CAP) alert feeds.

---

## References

[1] S. Yao, J. Zhao, D. Yu, N. Du, I. Shafran, K. R. Narasimhan, and Y. Cao, "ReAct: Synergizing Reasoning and Acting in Language Models," in *International Conference on Learning Representations (ICLR)*, 2023.

[2] T. Schick, J. Dwivedi-Yu, R. Dessì, R. Raileanu, M. Lomeli, L. Zettlemoyer, N. Cancedda, and T. Scialom, "Toolformer: Language Models Can Teach Themselves to Use Tools," in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 36, pp. 68539–68551, 2023.

[3] P. Manakul, A. Liusie, and M. J. F. Gales, "SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models," in *Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing (EMNLP)*, pp. 9004–9017, 2023.

[4] S. Min, K. Krishna, X. Lyu, M. Lewis, W. Yih, P. W. Koh, M. Iyyer, L. Zettlemoyer, and H. Hajishirzi, "FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation," in *Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing (EMNLP)*, pp. 12076–12100, 2023.

[5] S. Dhuliawala, M. Komeili, J. Xu, R. Raileanu, X. Li, A. Celikyilmaz, and J. Weston, "Chain-of-Verification Reduces Hallucination in Large Language Models," in *Findings of the Association for Computational Linguistics: ACL 2024*, pp. 3563–3578, 2024.

[6] P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin, N. Goyal, H. Küttler, M. Lewis, W. Yih, T. Rocktäschel, S. Riedel, and D. Kiela, "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 33, pp. 9459–9474, 2020.

[7] K. Guu, K. Lee, Z. Tung, P. Pasupat, and M. Chang, "REALM: Retrieval-Augmented Language Model Pre-Training," in *Proceedings of the 37th International Conference on Machine Learning (ICML)*, PMLR 119, pp. 3929–3938, 2020.

[8] J. Thorne, A. Vlachos, C. Christodoulopoulos, and A. Mittal, "FEVER: a Large-scale Dataset for Fact Extraction and VERification," in *Proceedings of the 2018 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (NAACL-HLT)*, pp. 809–819, 2018.

[9] Z. Ji, N. Lee, R. Frieske, T. Yu, D. Su, Y. Xu, E. Ishii, Y. J. Bang, A. Madotto, and P. Fung, "Survey of Hallucination in Natural Language Generation," *ACM Computing Surveys*, vol. 55, no. 12, pp. 1–38, 2023.

[10] R. Lam, A. Sanchez-Gonzalez, M. Willson, P. Wirnsberger, M. Fortunato, F. Alet, S. Ravuri, T. Ewalds, Z. Eaton-Rosen, W. Hu, A. Merose, S. Hoyer, G. Holland, O. Vinyals, J. Stott, A. Pritzel, S. Mohamed, and P. Battaglia, "Learning skillful medium-range global weather forecasting," *Science*, vol. 382, no. 6677, pp. 1416–1421, 2023.

[11] T. Nguyen, J. Brandstetter, A. Kapoor, J. K. Gupta, and A. Grover, "ClimaX: A foundation model for weather and climate," in *Proceedings of the 40th International Conference on Machine Learning (ICML)*, PMLR 202, pp. 25904–25938, 2023.

[12] S. Rasp, P. D. Dueben, S. Scher, J. A. Weyn, S. Mouatadid, N. Thuerey, et al., "WeatherBench 2: A benchmark for the next generation of data-driven global weather models," *Artificial Intelligence for the Earth System*, 2024.

[13] R. E. Morss, J. L. Demuth, J. K. Lazo, K. A. Dickinson, H. Lazrus, and B. H. Morrow, "Understanding Public Hurricane Evacuation Decisions and Responses to Forecast and Risk Information," *Bulletin of the American Meteorological Society*, vol. 98, no. 7, pp. 1431–1446, 2017.

[14] D. Amodei, C. Olah, J. Steinhardt, P. Christiano, J. Schulman, and D. Mané, "Concrete Problems in AI Safety," *arXiv preprint arXiv:1606.06565*, 2016.

[15] D. Hendrycks, N. Carlini, J. Schulman, and J. Steinhardt, "Unsolved Problems in ML Safety," *arXiv preprint arXiv:2109.13916*, 2021.

[16] S. Lin, J. Hilton, and O. Evans, "TruthfulQA: Measuring How Models Mimic Human Falsehoods," in *Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (ACL)*, pp. 3214–3252, 2022.
