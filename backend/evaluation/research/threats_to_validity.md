# ⚠️ Section 9: Limitations & Threats to Validity

**Paper:** Sky Reader: An Evidence-Grounded Agentic AI Framework for Reliable Weather Intelligence and Risk Assessment  
**Section Number:** 9  
**Methodological Integrity Requirement:** Transparent and rigorous scientific disclosure of all empirical, architectural, and evaluation boundaries  

---

## 9.1 Synthetic Fixtures vs. Operational Meteorology

### Construct Validity Boundary
The benchmark utilizes **12 frozen synthetic weather fixtures** conforming to Open-Meteo schemas. While these fixtures were engineered to model realistic atmospheric conditions (e.g., squall lines, polar cold outbreaks, heatwaves), they possess structural limitations:
1. **Absence of Real-World Telemetry Jitter:** Real-world meteorological sensor networks experience intermittent sensor drift, transmission packet loss, and missing observations. While `FIX_INCOMPLETE_SENSORS` evaluates null rainfall channels, it does not capture the full stochastic complexity of operational weather station networks.
2. **Deterministic Atmosphere vs. NWP Ensemble Spread:** Frozen fixtures present static point observations and deterministic 48-hour forecasts. Operational forecasters rely on multi-model ensemble spreads (e.g., 50-member ECMWF ensembles) to convey probabilistic confidence.
3. **Forecasting Skill Disclaimer:** **This benchmark does NOT validate Numerical Weather Prediction (NWP) forecasting skill.** Sky Reader operates downstream from numerical prediction engines. High benchmark scores indicate adherence to retrieved telemetry and safe decision support, not superior atmospheric modeling.

---

## 9.2 Sample Size and Statistical Sensitivity Constraints

### Statistical Power Boundaries
1. **Global Cohort ($N=50$):** As demonstrated in the reproducible power analysis (Section 6), an evaluation sample of 50 paired cases provides adequate statistical power ($\ge 80\%$ at $\alpha=0.05$) only for detecting **medium-to-large effect sizes (Cohen's $d \ge 0.40$, raw difference $\Delta \ge 0.15$)**. For small effect sizes ($d=0.20$), statistical power drops to **29.3%**.
2. **Category-Level Subsets ($n=5$ per Category):** Each individual category contains only 5 test cases. Small sample sizes induce high sampling variance and wide standard errors. Consequently, category-level accuracy scores should be interpreted as qualitative indicators rather than high-precision empirical parameters.
3. **Risk-Applicable Subset ($M_{\text{risk}}=11$):** Exactly 11 cases in the suite carry ground-truth hazard risk classifications. While McNemar's exact binomial test demonstrates statistical significance ($p = 0.03125$), evaluating hazard detection across a broader catalog of extreme weather events is necessary for generalized disaster-response deployment.
4. **Non-Equivalence Assertion:** Where hypothesis tests between Sky Reader and the Tool Agent failed to reject the null hypothesis (Factual Accuracy: $p=0.5250$; Completeness: $p=0.5750$), we explicitly **do not claim statistical equivalence**. The evaluation lacks the statistical power to rule out small but meaningful differences.

---

## 9.3 Execution Reliability and Timeout Budget Asymmetry

### Internal Validity Boundary
1. **Asymmetric Timeout Budget:** Baseline LLM and Tool Agent completed 100% of tasks within initial 30s/60s budgets. Complete Sky Reader required an extended **100-second timeout budget** to complete 7 complex multi-location and time-series cases.
2. **Strict Operational Ceiling:** Under a strict, uniform 60-second operational ceiling, Sky Reader's completed execution reliability was **86.0% (43/50)**. Eventual 100% completion was achieved only post-retry. Systems operating in hard real-time environments cannot assume 100% first-attempt completion without architectural latency optimizations.

---

## 9.4 Evaluator Heuristics and Propositional Matching

### Measurement Validity Boundary
1. **Deterministic String & Tolerance Parsers:** Propositional claim validation and factual accuracy are evaluated using deterministic Python regex matching and numerical tolerance windows. While this eliminates LLM-as-a-judge non-determinism, deterministic parsers can misinterpret complex linguistic paraphrases.
2. **Evaluator Sensitivity Discovered in Audit:** The Phase 7.4.3 audit revealed that the initial evaluator falsely penalized natural English contractions (`can't provide`, `don't have access`) as hallucinations. While this bug was corrected symmetrically across all three systems, deterministic string matching remains susceptible to linguistic edge cases.

---

## 9.5 Single-Model and Provider Specificity

### External Validity Boundary
1. **Single LLM Evaluation:** All experiments were conducted using a single foundation model—**`openai/gpt-oss-120b`**—served via Groq Cloud API. While this holds model scale and pre-training constant for controlled architectural ablation, it leaves open whether smaller models (e.g., Llama-3-8B) or proprietary models (e.g., GPT-4o, Claude-3.5-Sonnet) would exhibit different baseline hallucination rates or tool execution reliability.
2. **Inference Nondeterminism:** While API temperature was set to deterministic defaults, cloud LLM inference engines may exhibit subtle non-determinism across disparate days due to speculative decoding or distributed GPU scheduling.

---

## 9.6 Lack of Module-Level Ablations

### Internal Attribution Boundary
Complete Sky Reader combines multiple sub-modules: deterministic meteorological analysis (`analysis.py`), evidence compilation (`EvidenceEngine`), claim extraction and validation (`ClaimValidator`), hallucination recovery (`HallucinationController`), and risk assessment (`WeatherRiskAssessmentEngine`).

Because the Phase 7 benchmark compared Complete Sky Reader as an integrated platform against the Tool Agent, the reported improvements reflect a **composite architectural effect**. The marginal contribution of claim validation in isolation from evidence formatting or risk assessment cannot be definitively disentangled without future factorial ablation experiments.
