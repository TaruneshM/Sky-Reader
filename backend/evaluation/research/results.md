# 📊 Section 7: Experimental Results

**Paper:** Sky Reader: An Evidence-Grounded Agentic AI Framework for Reliable Weather Intelligence and Risk Assessment  
**Section Number:** 7  
**Evaluation Suite:** `Sky Reader Phase 7 Benchmark Dataset` (v1.0.0, 50 Cases, 10 Categories, 12 Fixtures)  
**Foundation Model:** Groq Cloud API — `openai/gpt-oss-120b` (Synthetic Fixture Injection Mode)  
**Audit Status:** Post-Audit Verified (Symmetrically Audited per Phase 7.4.3 Specification)  

---

## 7.1 Benchmark Coverage and Execution Profile

The empirical evaluation encompasses **50 distinct benchmark test cases** uniformly distributed across **10 meteorological task categories** (5 test cases per category). All three system architectures—**Baseline LLM** (zero tools), **Tool-Using Agent** (retrieval tools only, guardrails stripped), and **Complete Sky Reader** (full evidence-grounded platform)—were evaluated against **12 frozen synthetic ground-truth fixtures**, yielding **150 canonical paired execution responses**.

Across all historical evaluation sessions, a total of **160 execution records** are preserved in the repository result store (`backend/evaluation/results/`):
- **150 initial category run executions:** 50 cases $\times$ 3 systems across 10 run folders.
- **7 isolated retry executions:** Conducted for Complete Sky Reader under an extended timeout budget (`run_20261121_065501_3b721b`).
- **3 smoke-test records:** Phase 7.2 initialization records for `TC-CUR-001`.

The canonical record-selection policy incorporates the latest completed attempt per `(test_case_id, system)` pair, ensuring that all three systems achieve 100% evaluable response coverage ($N=50$) for comparative quality scoring, while strictly preserving initial attempt records for reliability and latency analysis.

---

## 7.2 Global Performance Comparison

Table I summarizes the global comparative performance across the three architectures. Every metric reports an exact mathematical numerator and denominator.

### TABLE I: Global Comparative Performance Across Systems ($N=50$ Cases per System)

| Performance Dimension | Baseline LLM (Zero Tools) | Tool-Using Agent (No Verification) | Complete Sky Reader (Full Platform) | Metric Denominator & Formulation |
|---|---|---|---|---|
| **First-Attempt Success Rate** | **100.0% (50/50)** | **100.0% (50/50)** | 86.0% (43/50) | Initial executions completed without timeout |
| **First-Attempt Timeout Rate** | **0.0% (0/50)** | **0.0% (0/50)** | 14.0% (7/50) | Timeouts during initial runs ($\le 60\text{s}$) |
| **Eventual Completion Rate** | **100.0% (50/50)** | **100.0% (50/50)** | **100.0% (50/50)** | Completed cases post-retry ($N=50$) |
| **Numerical Accuracy ($\text{Acc}_{\text{num}}$)** | 14.3% (12/72) | **48.1% (32/72)** | 34.1% (23/72) | Matched variables within tolerance ($M=43$ cases) |
| **Factual Claim Accuracy ($\text{Acc}_{\text{fact}}$)** | 18.1% (34/149) | **39.4% (58/149)** | 36.5% (53/149) | Supported expected factual claims ($N=50$ cases) |
| **Hallucination Rate ($H_{\text{rate}}$)** | 49.5% | 35.9% | **8.3%** | (Contradicted + Unsupported) / Total claims |
| **Hard Contradiction Rate ($C_{\text{rate}}$)** | 37.9% | 17.7% | **5.0%** | Claims conflicting with telemetry / Total claims |
| **Unsupported Claim Rate ($U_{\text{rate}}$)** | 11.6% | 18.2% | **3.4%** | Unverified assertions / Total claims |
| **Clean Case Ratio ($R_{\text{clean}}$)** | 64.0% (32/50) | 64.0% (32/50) | **90.0% (45/50)** | Cases with exactly 0 hallucinations ($N=50$) |
| **Evidence Availability Rate** | 0.0% (0/50) | 96.0% (48/50) | **98.0% (49/50)** | Cases where weather evidence was compiled |
| **Evidence Usage Rate** | 0.0% (0/50) | **86.0% (43/50)** | 84.0% (42/50) | Cases where response grounded in evidence |
| **Valid Explanation Proof Rate** | N/A | N/A | **97.4% (38/39)** | Structural validity of generated proofs |
| **Risk Classification Accuracy** | 0.0% (0/11) | 27.3% (3/11) | **81.8% (9/11)** | Exact hazard severity match ($M_{\text{risk}}=11$) |
| **Dangerous Underreported Risks** | 0 (No risk predicted) | 1 (Missed severe storm) | **0** | Severe/High event classified as safe/low |
| **Response Completeness Score** | 78.4% | 83.9% | **85.6%** | Mean proportion of query facets addressed |
| **Fully Complete Cases Ratio** | 58.0% (29/50) | 64.0% (32/50) | **76.0% (38/50)** | Cases achieving 100% completeness |
| **Mean Wall-Clock Latency** | **2,915.3 ms** | 19,376.5 ms | 28,200.3 ms | Mean latency of canonical responses |
| **P95 Latency** | **9,109.6 ms** | 37,168.8 ms | 59,881.9 ms | 95th percentile latency |

---

## 7.3 Category-Level Performance Analysis

Table II provides a disaggregated breakdown of accuracy, hallucination, and completeness across all 10 benchmark task categories.

### TABLE II: Category-Level Benchmark Results (5 Cases per Category)

| Benchmark Category | System Architecture | Numerical Acc | Factual Acc | Risk Acc | Hallucination Rate | Clean Ratio | Completeness | Mean Latency |
|---|---|---|---|---|---|---|---|---|
| `current_weather` | Baseline LLM | 10.0% | 0.0% | N/A | 66.7% | 33.3% | 80.0% | 1,409.7 ms |
| | Tool Agent | **80.0%** | **80.0%** | N/A | 0.0% | **100.0%** | **100.0%** | 16,715.5 ms |
| | Complete Sky Reader | 60.0% | 76.7% | N/A | 0.0% | **100.0%** | **100.0%** | 10,256.4 ms |
| `hourly_forecast` | Baseline LLM | 20.0% | 0.0% | N/A | 66.7% | 33.3% | 80.0% | 1,322.4 ms |
| | Tool Agent | 60.0% | 20.0% | N/A | 40.0% | 60.0% | **100.0%** | 20,771.6 ms |
| | Complete Sky Reader | **70.0%** | 10.0% | N/A | **11.7%** | **80.0%** | **100.0%** | 35,359.8 ms |
| `temperature_comparison` | Baseline LLM | **40.0%** | 6.7% | N/A | 50.0% | 50.0% | **100.0%** | 3,879.5 ms |
| | Tool Agent | 6.7% | **36.7%** | N/A | 91.7% | 0.0% | 90.0% | 27,213.8 ms |
| | Complete Sky Reader | 6.7% | 10.0% | N/A | **20.0%** | **80.0%** | 90.0% | 42,143.2 ms |
| `precipitation_and_rainfall` | Baseline LLM | 20.0% | 20.0% | N/A | 62.5% | 37.5% | 83.3% | 2,045.2 ms |
| | Tool Agent | 20.0% | 6.7% | N/A | 70.0% | 30.0% | 86.7% | 20,622.9 ms |
| | Complete Sky Reader | **90.0%** | **53.3%** | N/A | **10.0%** | **90.0%** | **100.0%** | 26,318.9 ms |
| `weather_trends` | Baseline LLM | 0.0% | 10.0% | N/A | 100.0% | 0.0% | 70.0% | 2,204.0 ms |
| | Tool Agent | 20.0% | **23.3%** | N/A | 50.0% | 50.0% | 90.0% | 21,887.1 ms |
| | Complete Sky Reader | 20.0% | 20.0% | N/A | **0.0%** | **100.0%** | **100.0%** | 31,587.5 ms |
| `multistep_reasoning` | Baseline LLM | 0.0% | 35.0% | 0.0% | 100.0% | 0.0% | 90.0% | 2,505.2 ms |
| | Tool Agent | **63.3%** | **63.3%** | 0.0% | 20.0% | 80.0% | **100.0%** | 26,895.4 ms |
| | Complete Sky Reader | 10.0% | 61.7% | **100.0%** | **0.0%** | **100.0%** | **100.0%** | 39,410.8 ms |
| `evidence_based_reasoning` | Baseline LLM | 23.3% | 40.0% | 0.0% | 41.7% | 58.3% | **100.0%** | 2,977.4 ms |
| | Tool Agent | **53.3%** | 40.0% | 0.0% | 8.3% | 91.7% | 75.0% | 18,970.6 ms |
| | Complete Sky Reader | 36.7% | 40.0% | **100.0%** | **0.0%** | **100.0%** | **100.0%** | 41,999.3 ms |
| `weather_safety_and_risk` | Baseline LLM | 12.5% | 46.0% | 0.0% | 66.7% | 33.3% | 95.0% | 5,322.4 ms |
| | Tool Agent | **87.5%** | **91.0%** | 40.0% | 12.5% | 87.5% | **100.0%** | 23,756.6 ms |
| | Complete Sky Reader | 0.0% | 48.3% | **100.0%** | **0.0%** | **100.0%** | 86.7% | 34,468.9 ms |
| `missing_or_incomplete_data`| Baseline LLM | 0.0% | 6.7% | 0.0% | 20.0% | 80.0% | 35.3% | 6,354.6 ms |
| | Tool Agent | **100.0%** | 23.3% | 33.3% | 60.0% | 40.0% | 32.7% | 6,181.8 ms |
| | Complete Sky Reader | 0.0% | **30.0%** | 33.3% | **25.0%** | **80.0%** | **39.3%** | 9,888.8 ms |
| `hallucination_resistance` | Baseline LLM | 0.0% | 16.7% | N/A | **0.0%** | **100.0%** | 50.0% | 2,126.9 ms |
| | Tool Agent | 33.3% | 10.0% | N/A | 16.0% | 80.0% | **65.0%** | 10,749.8 ms |
| | Complete Sky Reader | 0.0% | 15.0% | N/A | **0.0%** | **100.0%** | 40.0% | 10,559.8 ms |

---

## 7.4 Statistical Hypothesis Testing Results

All paired statistical comparisons were computed across matched test case IDs using two-sided paired permutation sign-flip tests ($B=2,000$ resamples) and 95% percentile bootstrap confidence intervals ($B=2,000$ resamples with replacement, seed 42).

### TABLE III: Paired System Hypothesis Testing

| Comparison ($A$ vs. $B$) | Metric | Matched Pairs ($n$) | Mean Diff ($\bar{A} - \bar{B}$) | Bootstrap 95% CI | Permutation $p$-value | Statistically Significant? |
|---|---|---|---|---|---|---|
| `sky_reader_full` vs. `tool_using_agent` | **Hallucination Rate** | 50 | **$-0.2543$** | **$[-0.3750, -0.1450]$** | **$p < 0.001$** | ✅ **YES** ($H_1$ Supported) |
| `sky_reader_full` vs. `tool_using_agent` | Factual Accuracy | 50 | $-0.0293$ | $[-0.1267, +0.0600]$ | $p = 0.5250$ | ❌ No (No difference detected) |
| `sky_reader_full` vs. `tool_using_agent` | Numerical Accuracy | 43 | $-0.1395$ | $[-0.3140, +0.0349]$ | $p = 0.1310$ | ❌ No (Observed Trend) |
| `sky_reader_full` vs. `tool_using_agent` | Completeness Score | 50 | $+0.0167$ | $[-0.0433, +0.0717]$ | $p = 0.5750$ | ❌ No (No difference detected) |
| `sky_reader_full` vs. `baseline_llm` | **Factual Accuracy** | 50 | **$+0.1840$** | **$[+0.0757, +0.3033]$** | **$p < 0.001$** | ✅ **YES** |
| `sky_reader_full` vs. `baseline_llm` | **Numerical Accuracy** | 43 | **$+0.1977$** | **$[+0.0581, +0.3372]$** | **$p = 0.0070$** | ✅ **YES** |
| `sky_reader_full` vs. `baseline_llm` | **Hallucination Rate** | 50 | **$-0.2650$** | **$[-0.4033, -0.1233]$** | **$p < 0.001$** | ✅ **YES** |
| `sky_reader_full` vs. `baseline_llm` | Completeness Score | 50 | $+0.0723$ | $[-0.0010, +0.1467]$ | $p = 0.0530$ | ❌ No (Marginal) |
| `tool_using_agent` vs. `baseline_llm` | **Factual Accuracy** | 50 | **$+0.2133$** | **$[+0.1117, +0.3267]$** | **$p < 0.001$** | ✅ **YES** |
| `tool_using_agent` vs. `baseline_llm` | **Numerical Accuracy** | 43 | **$+0.3372$** | **$[+0.1744, +0.5000]$** | **$p < 0.001$** | ✅ **YES** |
| `tool_using_agent` vs. `baseline_llm` | Hallucination Rate | 50 | $-0.0107$ | $[-0.1667, +0.1493]$ | $p = 0.9060$ | ❌ No |
| `tool_using_agent` vs. `baseline_llm` | Completeness Score | 50 | $+0.0557$ | $[-0.0100, +0.1260]$ | $p = 0.0930$ | ❌ No |

### Statistical Test for Risk Classification Accuracy ($N=11$)
To evaluate Hypothesis 2, an exact paired test was conducted on the 11 risk-applicable benchmark cases:
- In the paired contingency table between Complete Sky Reader (9/11 correct) and Tool-Using Agent (3/11 correct):
  - Both systems correct: 3 cases (`TC-RSK-003`, `TC-RSK-004`, `TC-INC-004`).
  - Sky Reader correct, Tool Agent incorrect ($b$): **6 cases** (`TC-MLT-003`, `TC-MLT-004`, `TC-EVD-002`, `TC-RSK-001`, `TC-RSK-002`, `TC-RSK-005`).
  - Sky Reader incorrect, Tool Agent correct ($c$): **0 cases**.
  - Both systems incorrect: 2 cases (`TC-INC-001`, `TC-INC-003`).
- **McNemar Exact Binomial Test:** With $n_{\text{discordant}} = b + c = 6$, under $H_0$ that both systems are equally accurate, $b \sim \text{Binomial}(6, 0.5)$.
- The exact two-sided binomial $p$-value is:
  $$p = 2 \times (0.5)^6 = 2 \times \frac{1}{64} = \mathbf{0.03125}$$
- **Statistical Interpretation:** Because $p = 0.03125 < 0.05$, **Sky Reader's improvement in risk classification accuracy (81.8% vs. 27.3%) is nominally significant under uncorrected $\alpha = 0.05$** ($H_2$ Supported under exploratory analysis). However, across the family of 12 benchmark evaluation metrics, a conservative Bonferroni-corrected threshold is $\alpha_{\text{corr}} = 0.05 / 12 = 0.00417$. Under this strict criterion, $p = 0.03125 > 0.00417$, meaning that while the direction of effect is strong ($b=6, c=0$), replication on larger sample sizes ($N > 11$) is warranted to confirm significance under multiple-comparison correction. In addition, Complete Sky Reader omitted risk predictions in two cases with severe sensor data degradation (`TC-INC-001`, `TC-INC-003`), reflecting an 18.2% omission rate that must be factored into operational safety assessments.
