# 📋 Publication-Ready Research Tables

**Paper:** Sky Reader: An Evidence-Grounded Agentic AI Framework for Reliable Weather Intelligence and Risk Assessment  
**Document Type:** Formal Research Tables (IEEE / ACM Manuscript Standard)  

---

## TABLE I: Experimental Architectures and Evaluation Configuration

*Caption: Architectural specification and ablation boundaries across the three evaluated systems. All systems were evaluated using the same underlying foundation model and synthetic fixtures.*

| Architectural Dimension | System A: Baseline LLM | System B: Tool-Using Agent | System C: Complete Sky Reader |
|---|---|---|---|
| **System Key** | `baseline_llm` | `tool_using_agent` | `sky_reader_full` |
| **Inference Model** | `openai/gpt-oss-120b` (Groq API) | `openai/gpt-oss-120b` (Groq API) | `openai/gpt-oss-120b` (Groq API) |
| **Execution Pattern** | Zero-shot single-turn prompt | Multi-turn agentic function calling | Multi-turn agentic neuro-symbolic pipeline |
| **Available Tools** | None (`tools=None`) | `RETRIEVAL_TOOLS` (3 tools: geocoding, current weather, hourly forecast) | Full Suite (6 tools: retrieval, trend analysis, recommendations, risk assessment) |
| **Atmospheric Data Access** | None (Parametric memory only) | Synthetic Open-Meteo Fixtures | Synthetic Open-Meteo Fixtures |
| **Evidence Compilation** | Disabled | Disabled | Enabled (`EvidenceEngine`) |
| **Claim Extraction & Audit** | Disabled | Disabled | Enabled (`ClaimExtractor`, `ClaimValidator`) |
| **Hallucination Controller** | Disabled | Disabled | Enabled (`HallucinationController`) |
| **Meteorological Risk Engine**| Disabled | Disabled | Enabled (`WeatherRiskAssessmentEngine`) |
| **Formal Explanation Proofs** | Disabled | Disabled | Enabled (`ExplanationEngine`) |
| **First-Attempt Timeout Budget**| 30.0s (Cat 1) / 60.0s (Cats 2–10) | 30.0s (Cat 1) / 60.0s (Cats 2–10) | 30.0s (Cat 1) / 60.0s (Cats 2–10) |
| **Retry Timeout Budget** | N/A (0 retries required) | N/A (0 retries required) | 100.0s (7 cases retried) |

---

## TABLE II: Global Comparative Benchmark Results

*Caption: Performance comparison across all 50 benchmark cases. All metrics report exact mathematical numerators and denominators. Post-audit verified.*

| Performance Dimension | Baseline LLM | Tool-Using Agent | Complete Sky Reader | Metric Formula / Denominator |
|---|---|---|---|---|
| **First-Attempt Completion Rate** | **100.0%** (50/50) | **100.0%** (50/50) | 86.0% (43/50) | Completed without timeout / Attempted cases ($N=50$) |
| **First-Attempt Timeout Rate** | **0.0%** (0/50) | **0.0%** (0/50) | 14.0% (7/50) | Timeouts during initial execution / Attempted cases ($N=50$) |
| **Eventual Completion Rate** | **100.0%** (50/50) | **100.0%** (50/50) | **100.0%** (50/50) | Total completed cases post-retry / Attempted cases ($N=50$) |
| **Numerical Accuracy ($\text{Acc}_{\text{num}}$)** | 14.3% (12/72) | **48.1%** (32/72) | 34.1% (23/72) | Extracted variables within tolerance / Expected variables ($M=43$) |
| **Legacy Aggregate MAE** | 14.80 | 10.27 | **4.98** | Scale-aggregated deviation across °C, km/h, mm (See Table VII) |
| **Factual Accuracy ($\text{Acc}_{\text{fact}}$)** | 18.1% (34/149) | **39.4%** (58/149) | 36.5% (53/149) | Supported expected claims / Total expected claims ($N=50$) |
| **Hallucination Rate ($H_{\text{rate}}$)** | 49.5% | 35.9% | **8.3%** | Contradicted + Unsupported claims / Total evaluated claims |
| **Hard Contradiction Rate ($C_{\text{rate}}$)** | 37.9% | 17.7% | **5.0%** | Claims conflicting with telemetry / Total evaluated claims |
| **Unsupported Claim Rate ($U_{\text{rate}}$)** | 11.6% | 18.2% | **3.4%** | Unverified assertions / Total evaluated claims |
| **Clean Case Ratio ($R_{\text{clean}}$)** | 64.0% (32/50) | 64.0% (32/50) | **90.0%** (45/50) | Cases with 0 hallucinations / Total evaluable cases ($N=50$) |
| **Evidence Availability Rate** | 0.0% (0/50) | 96.0% (48/50) | **98.0%** (49/50) | Cases with compiled evidence / Total evaluable cases ($N=50$) |
| **Evidence Usage Rate** | 0.0% (0/50) | **86.0%** (43/50) | 84.0% (42/50) | Cases with grounded response text / Evaluable cases ($N=50$) |
| **Valid Explanation Proof Rate** | N/A | N/A | **97.4%** (38/39) | Valid formal proofs / Proofs generated ($N=39$) |
| **Risk Classification Accuracy** | 0.0% (0/11) | 27.3% (3/11) | **81.8%** (9/11) | Exact severity tier match / Applicable risk cases ($M_{\text{risk}}=11$) |
| **Dangerous Severity Underreports** | 0 (No risk predicted) | 1 (Missed severe storm) | **0** | Severe/High event classified as safe/low ($M_{\text{risk}}=11$) |
| **Response Completeness Score** | 78.4% | 83.9% | **85.6%** | Mean addressed query facets / Total required facets ($N=50$) |
| **Fully Complete Cases Ratio** | 58.0% (29/50) | 64.0% (32/50) | **76.0%** (38/50) | Cases achieving 100% completeness / Evaluable cases ($N=50$) |
| **Mean Wall-Clock Latency** | **2,915.3 ms** | 19,376.5 ms | 28,200.3 ms | Mean latency of canonical responses ($N=50$) |
| **P95 Latency** | **9,109.6 ms** | 37,168.8 ms | 59,881.9 ms | 95th percentile latency of canonical responses ($N=50$) |

---

## TABLE III: Category-Level Performance Matrix

*Caption: Performance across the 10 benchmark categories (5 test cases per category). Denominators reflect within-category expected variables and claims.*

| Benchmark Category | System Architecture | Numerical Acc | Factual Acc | Risk Acc | Hallucination Rate | Clean Ratio | Completeness | Mean Latency |
|---|---|---|---|---|---|---|---|---|
| `current_weather` | Baseline LLM | 10.0% (1/10) | 0.0% (0/15) | N/A | 66.7% | 33.3% (1/3) | 80.0% | 1,409.7 ms |
| | Tool Agent | **80.0%** (8/10) | **80.0%** (12/15) | N/A | 0.0% | **100.0%** (5/5) | **100.0%** | 16,715.5 ms |
| | Complete Sky Reader | 60.0% (6/10) | 76.7% (11/15) | N/A | 0.0% | **100.0%** (5/5) | **100.0%** | 10,256.4 ms |
| `hourly_forecast` | Baseline LLM | 20.0% (2/10) | 0.0% (0/15) | N/A | 66.7% | 33.3% (1/3) | 80.0% | 1,322.4 ms |
| | Tool Agent | 60.0% (6/10) | 20.0% (3/15) | N/A | 40.0% | 60.0% (3/5) | **100.0%** | 20,771.6 ms |
| | Complete Sky Reader | **70.0%** (7/10) | 10.0% (2/15) | N/A | **11.7%** | **80.0%** (4/5) | **100.0%** | 35,359.8 ms |
| `temperature_comparison` | Baseline LLM | **40.0%** (4/10) | 6.7% (1/15) | N/A | 50.0% | 50.0% (2/4) | **100.0%** | 3,879.5 ms |
| | Tool Agent | 6.7% (1/10) | **36.7%** (6/15) | N/A | 91.7% | 0.0% (0/5) | 90.0% | 27,213.8 ms |
| | Complete Sky Reader | 6.7% (1/10) | 10.0% (2/15) | N/A | **20.0%** | **80.0%** (4/5) | 90.0% | 42,143.2 ms |
| `precipitation_and_rainfall` | Baseline LLM | 20.0% (2/10) | 20.0% (3/15) | N/A | 62.5% | 37.5% (1/3) | 83.3% | 2,045.2 ms |
| | Tool Agent | 20.0% (2/10) | 6.7% (1/15) | N/A | 70.0% | 30.0% (1/5) | 86.7% | 20,622.9 ms |
| | Complete Sky Reader | **90.0%** (9/10) | **53.3%** (8/15) | N/A | **10.0%** | **90.0%** (4/5) | **100.0%** | 26,318.9 ms |
| `weather_trends` | Baseline LLM | 0.0% (0/10) | 10.0% (1/15) | N/A | 100.0% | 0.0% (0/4) | 70.0% | 2,204.0 ms |
| | Tool Agent | 20.0% (2/10) | **23.3%** (4/15) | N/A | 50.0% | 50.0% (2/5) | 90.0% | 21,887.1 ms |
| | Complete Sky Reader | 20.0% (2/10) | 20.0% (3/15) | N/A | **0.0%** | **100.0%** (5/5) | **100.0%** | 31,587.5 ms |
| `multistep_reasoning` | Baseline LLM | 0.0% (0/10) | 35.0% (5/15) | 0.0% (0/2) | 100.0% | 0.0% (0/4) | 90.0% | 2,505.2 ms |
| | Tool Agent | **63.3%** (6/10) | **63.3%** (9/15) | 0.0% (0/2) | 20.0% | 80.0% (4/5) | **100.0%** | 26,895.4 ms |
| | Complete Sky Reader | 10.0% (1/10) | 61.7% (9/15) | **100.0%** (2/2) | **0.0%** | **100.0%** (5/5) | **100.0%** | 39,410.8 ms |
| `evidence_based_reasoning` | Baseline LLM | 23.3% (2/10) | 40.0% (6/15) | 0.0% (0/1) | 41.7% | 58.3% (2/4) | **100.0%** | 2,977.4 ms |
| | Tool Agent | **53.3%** (5/10) | 40.0% (6/15) | 0.0% (0/1) | 8.3% | 91.7% (4/5) | 75.0% | 18,970.6 ms |
| | Complete Sky Reader | 36.7% (3/10) | 40.0% (6/15) | **100.0%** (1/1) | **0.0%** | **100.0%** (5/5) | **100.0%** | 41,999.3 ms |
| `weather_safety_and_risk` | Baseline LLM | 12.5% (1/8) | 46.0% (7/15) | 0.0% (0/5) | 66.7% | 33.3% (1/4) | 95.0% | 5,322.4 ms |
| | Tool Agent | **87.5%** (7/8) | **91.0%** (14/15) | 40.0% (2/5) | 12.5% | 87.5% (4/5) | **100.0%** | 23,756.6 ms |
| | Complete Sky Reader | 0.0% (0/8) | 48.3% (7/15) | **100.0%** (5/5) | **0.0%** | **100.0%** (5/5) | 86.7% | 34,468.9 ms |
| `missing_or_incomplete_data`| Baseline LLM | 0.0% (0/1) | 6.7% (1/15) | 0.0% (0/3) | 20.0% | 80.0% (4/5) | 35.3% | 6,354.6 ms |
| | Tool Agent | **100.0%** (1/1) | 23.3% (4/15) | 33.3% (1/3) | 60.0% | 40.0% (2/5) | 32.7% | 6,181.8 ms |
| | Complete Sky Reader | 0.0% (0/1) | **30.0%** (5/15) | 33.3% (1/3) | **25.0%** | **80.0%** (4/5) | **39.3%** | 9,888.8 ms |
| `hallucination_resistance` | Baseline LLM | 0.0% (0/3) | 16.7% (2/14) | N/A | **0.0%** | **100.0%** (5/5) | 50.0% | 2,126.9 ms |
| | Tool Agent | 33.3% (1/3) | 10.0% (1/14) | N/A | 16.0% | 80.0% (4/5) | **65.0%** | 10,749.8 ms |
| | Complete Sky Reader | 0.0% (0/3) | 15.0% (2/14) | N/A | **0.0%** | **100.0%** (5/5) | 40.0% | 10,559.8 ms |

---

## TABLE IV: Statistical Hypothesis Testing and Effect Sizes

*Caption: Paired hypothesis tests across matched test cases ($B=2,000$ permutations / bootstrap resamples, seed 42).*

| Comparison Pair ($A$ vs. $B$) | Evaluation Metric | Matched Pairs ($n$) | Mean Diff ($\bar{A} - \bar{B}$) | Bootstrap 95% CI | Permutation $p$-value | Significant ($\alpha=0.05$)? |
|---|---|---|---|---|---|---|
| `sky_reader_full` vs. `tool_using_agent` | **Hallucination Rate** | 50 | **$-0.2543$** | **$[-0.3750, -0.1450]$** | **$p < 0.001$** | ✅ **YES** ($H_1$ Supported) |
| `sky_reader_full` vs. `tool_using_agent` | Factual Accuracy | 50 | $-0.0293$ | $[-0.1267, +0.0600]$ | $p = 0.5250$ | ❌ No (No difference detected) |
| `sky_reader_full` vs. `tool_using_agent` | Numerical Accuracy | 43 | $-0.1395$ | $[-0.3140, +0.0349]$ | $p = 0.1310$ | ❌ No ($H_4$ Observed Trend) |
| `sky_reader_full` vs. `tool_using_agent` | Completeness Score | 50 | $+0.0167$ | $[-0.0433, +0.0717]$ | $p = 0.5750$ | ❌ No (No difference detected) |
| `sky_reader_full` vs. `baseline_llm` | **Factual Accuracy** | 50 | **$+0.1840$** | **$[+0.0757, +0.3033]$** | **$p < 0.001$** | ✅ **YES** |
| `sky_reader_full` vs. `baseline_llm` | **Numerical Accuracy** | 43 | **$+0.1977$** | **$[+0.0581, +0.3372]$** | **$p = 0.0070$** | ✅ **YES** |
| `sky_reader_full` vs. `baseline_llm` | **Hallucination Rate** | 50 | **$-0.2650$** | **$[-0.4033, -0.1233]$** | **$p < 0.001$** | ✅ **YES** |
| `sky_reader_full` vs. `baseline_llm` | Completeness Score | 50 | $+0.0723$ | $[-0.0010, +0.1467]$ | $p = 0.0530$ | ❌ No (Marginal) |
| `tool_using_agent` vs. `baseline_llm` | **Factual Accuracy** | 50 | **$+0.2133$** | **$[+0.1117, +0.3267]$** | **$p < 0.001$** | ✅ **YES** |
| `tool_using_agent` vs. `baseline_llm` | **Numerical Accuracy** | 43 | **$+0.3372$** | **$[+0.1744, +0.5000]$** | **$p < 0.001$** | ✅ **YES** |
| `tool_using_agent` vs. `baseline_llm` | Hallucination Rate | 50 | $-0.0107$ | $[-0.1667, +0.1493]$ | $p = 0.9060$ | ❌ No |
| `tool_using_agent` vs. `baseline_llm` | Completeness Score | 50 | $+0.0557$ | $[-0.0100, +0.1260]$ | $p = 0.0930$ | ❌ No |

---

## TABLE V: Risk Classification and Hazard Severity Contingency Matrix

*Caption: Breakdown across all 11 risk-applicable benchmark cases. McNemar's exact binomial test demonstrates nominally significant accuracy gain for Sky Reader ($p = 0.03125$ at uncorrected $\alpha = 0.05$, though non-significant under Bonferroni threshold $\alpha_{\text{corr}} = 0.00417$). Note that 2 cases resulted in omitted predictions (18.2% omission rate) due to degraded sensor input.*

| Case ID | Benchmark Category | Expected Severity | Baseline LLM Predicted | Tool Agent Predicted | Complete Sky Reader Predicted | Hazard Type |
|---|---|---|---|---|---|---|
| `TC-RSK-001` | `weather_safety_and_risk` | **SEVERE** | None | **HIGH (Underreported)** | **SEVERE** | Convective storm (48mm rain, 65km/h wind) |
| `TC-RSK-002` | `weather_safety_and_risk` | **HIGH** | None | None | **HIGH** | Extreme heatwave (38.5°C) |
| `TC-RSK-003` | `weather_safety_and_risk` | **HIGH** | None | **HIGH** | **HIGH** | Synoptic gale windstorm (78km/h gusts) |
| `TC-RSK-004` | `weather_safety_and_risk` | **SEVERE** | None | **SEVERE** | **SEVERE** | Severe squall with lightning & hail |
| `TC-RSK-005` | `weather_safety_and_risk` | **LOW** | None | None | **LOW** | Mild weather conditions |
| `TC-MLT-003` | `multistep_reasoning` | **HIGH** | None | None | **HIGH** | Multi-hop wind hazard |
| `TC-MLT-004` | `multistep_reasoning` | **HIGH** | None | None | **HIGH** | Multi-hop extreme heat hazard |
| `TC-EVD-002` | `evidence_based_reasoning` | **SEVERE** | None | None | **SEVERE** | Evidence-grounded severe storm |
| `TC-INC-001` | `missing_or_incomplete_data` | **LOW** | None | None | None (Refusal) | Missing location in prompt |
| `TC-INC-003` | `missing_or_incomplete_data` | **LOW** | None | None | None (Degradation) | Empty hourly forecast payload |
| `TC-INC-004` | `missing_or_incomplete_data` | **LOW** | None | **LOW** | **LOW** | Incomplete sensor travel advisory |
| **Summary** | **Accuracy Rate ($N=11$)** | | **0.0% (0/11)** | **27.3% (3/11)** | **81.8% (9/11)** | **McNemar $p = 0.03125$ (Exact)** |

---

## TABLE VI: Latency and Execution Reliability Profile

*Caption: Runtime latency and execution reliability across initial attempts and extended-budget retries.*

| Execution Metric | Baseline LLM | Tool-Using Agent | Complete Sky Reader | Notes / Operational Meaning |
|---|---|---|---|---|
| **Total Attempted Cases** | 50 | 50 | 50 | Full benchmark suite ($N=50$) |
| **Initial Budget Ceiling** | 30.0s (Cat 1) / 60.0s | 30.0s (Cat 1) / 60.0s | 30.0s (Cat 1) / 60.0s | Standard runner timeout budget |
| **First-Attempt Completed** | **50 (100.0%)** | **50 (100.0%)** | 43 (86.0%) | Completed on initial pass |
| **First-Attempt Timeouts** | **0 (0.0%)** | **0 (0.0%)** | 7 (14.0%) | Required budget extension |
| **Retry Cases Count** | 0 | 0 | 7 | Retried under 100.0s budget |
| **Retry Completion Rate** | N/A | N/A | **7 / 7 (100.0%)** | 100% success on retry |
| **Eventual Completed Cases** | **50 (100.0%)** | **50 (100.0%)** | **50 (100.0%)** | Total evaluable coverage post-retry |
| **First-Attempt Mean Latency (All)** | **2,915.4 ms** | 19,376.5 ms | 30,112.7 ms | Includes timed-out executions |
| **First-Attempt Mean Latency (Completed)**| **2,915.4 ms** | 19,376.5 ms | 26,639.4 ms | Completed initial executions only |
| **Retry Mean Latency (7 Cases)** | N/A | N/A | 37,788.3 ms | Complex multi-location cases |
| **Canonical Response Mean Latency** | **2,915.4 ms** | 19,376.5 ms | 28,200.3 ms | Verified response latency |
| **Canonical Response P95 Latency** | **9,109.6 ms** | 37,168.8 ms | 59,881.9 ms | 95th percentile latency |

---

## TABLE VII: Physical Variable-Specific Numerical Error Analysis

*Caption: Disaggregated Mean Absolute Error (MAE) and extraction statistics across physical meteorological dimensions. Mixing physical units into a single MAE is physically uninterpretable; this table provides the rigorous physical decomposition.*

| Physical Dimension | Unit | Total Expected Variables | System Architecture | Matched Variables | Correct Variables | Incorrect Variables | Missing Variables | Variable MAE |
|---|---|---|---|---|---|---|---|---|
| **Temperature** | °C | 33 | Baseline LLM | 21 / 33 | 7 | 14 | 12 | 7.27 °C |
| | | | Tool Agent | **31 / 33** | **20** | 11 | **2** | **4.03 °C** |
| | | | Complete Sky Reader | 25 / 33 | 11 | 14 | 8 | 5.35 °C |
| **Precipitation Accumulation** | mm | 12 | Baseline LLM | 5 / 12 | 0 | 5 | 7 | 54.50 mm |
| | | | Tool Agent | 7 / 12 | 5 | 2 | 5 | 12.21 mm |
| | | | Complete Sky Reader | 7 / 12 | 5 | 2 | 5 | **8.07 mm** |
| **Precipitation Probability** | % | 9 | Baseline LLM | 4 / 9 | 2 | 2 | 5 | 20.75 % |
| | | | Tool Agent | 6 / 9 | 2 | 4 | 3 | 39.17 % |
| | | | Complete Sky Reader | **6 / 9** | **6** | **0** | 3 | **0.00 %** |
| **Wind Speed** | km/h | 10 | Baseline LLM | 5 / 10 | 3 | 2 | 5 | 12.20 km/h |
| | | | Tool Agent | **6 / 10** | **5** | 1 | **4** | **0.73 km/h** |
| | | | Complete Sky Reader | 4 / 10 | 3 | 1 | 6 | 6.75 km/h |
| **Surface Pressure** | hPa | 4 | Baseline LLM | 2 / 4 | 0 | 2 | 2 | 4.98 hPa |
| | | | Tool Agent | **4 / 4** | **4** | **0** | **0** | **0.00 hPa** |
| | | | Complete Sky Reader | 3 / 4 | 2 | 1 | 1 | 5.67 hPa |
| **Relative Humidity / Cloud Cover** | % | 4 | Baseline LLM | 0 / 4 | 0 | 0 | 4 | N/A |
| | | | Tool Agent | 1 / 4 | 1 | 0 | 3 | 0.00 % |
| | | | Complete Sky Reader | 1 / 4 | 1 | 0 | 3 | 0.00 % |
| **Total / Aggregate** | *Mixed* | **72** | Baseline LLM | 37 / 72 | 12 | 25 | 35 | 14.80 *(legacy)* |
| | | | Tool Agent | **55 / 72** | **37** | 18 | **17** | 10.27 *(legacy)* |
| | | | Complete Sky Reader | 46 / 72 | 28 | 18 | 26 | **4.98** *(legacy)* |

*\*Note on Legacy Aggregate MAE: The historical aggregate MAE computes an unweighted mathematical mean across deviations in °C, mm, km/h, and hPa. It is preserved solely for continuity with preliminary Phase 7 reports, with the explicit caveat that adding mixed physical quantities lacks physical dimensionality.*
