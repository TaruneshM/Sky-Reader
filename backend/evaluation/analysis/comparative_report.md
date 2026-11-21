# 📊 Sky Reader Comparative Evaluation & Benchmark Report

**Evaluation Run ID:** `run_20261119_140839_abeda5`  
**Timestamp:** `2026-11-21T07:17:58.049838+00:00`  
**Dataset:** `Sky Reader Phase 7 Evaluation Benchmark Dataset` (v1.0.0)  
**Benchmark Scope & Status:** ✅ **Full Benchmark Suite (10/10 Categories, 50 Cases)**  
**Categories Evaluated:** `current_weather, evidence_based_reasoning, hallucination_resistance, hourly_forecast, missing_or_incomplete_data, multistep_reasoning, precipitation_and_rainfall, temperature_comparison, weather_safety_and_risk, weather_trends`  
**Total System Executions:** 150 across 3 systems  

---

## 1. Executive Summary & Comparative Matrix

| Metric Dimension | Baseline LLM (Zero Tools) | Tool-Using Agent (No Verification) | Complete Sky Reader (Full Platform) |
|---|---|---|---|
| **Execution Success Rate** | 100.0% | 100.0% | 100.0% |
| **Evaluable Cases** | 50/50 | 50/50 | 50/50 |
| **Numerical Accuracy** | 14.3% | 48.1% | 34.1% |
| **Mean Absolute Error (MAE)** | 14.80 | 10.27 | 4.98 |
| **Factual Accuracy** | 18.1% | 39.4% | 36.5% |
| **Hallucination Rate** | 49.5% | 35.9% | 8.3% |
| **Hard Contradiction Rate** | 37.9% | 17.7% | 5.0% |
| **Unsupported Claim Rate** | 11.6% | 18.2% | 3.4% |
| **Clean Case Ratio (0 Hallucinations)** | 64.0% | 64.0% | 90.0% |
| **Evidence Availability** | 0.0% | 96.0% | 98.0% |
| **Evidence Usage Rate** | 0.0% | 86.0% | 84.0% |
| **Valid Explanation Proof Rate** | N/A | N/A | 97.4% |
| **Risk Classification Accuracy** | 0.0% | 27.3% | 81.8% |
| **Risk Severity Underreported** | 0 | 1 | 0 |
| **Response Completeness** | 78.4% | 83.9% | 85.6% |
| **Fully Complete Ratio** | 58.0% | 64.0% | 76.0% |
| **Mean Latency** | 2915.3 ms | 19376.5 ms | 28200.3 ms |
| **P95 Latency** | 9109.6 ms | 37168.8 ms | 59881.9 ms |

> [!NOTE]
> **Zero Arbitrary Composite Scores:** In accordance with benchmark rigor, no arbitrary weighted score is computed. Each dimension measures an isolated, verifiable capability.

---

## 2. Category-Level Performance Breakdown

Performance across the 10 benchmark categories (Accuracy / Hallucination Rate / Completeness):

| Category | Baseline LLM | Tool-Using Agent | Complete Sky Reader |
|---|---|---|---|
| `current_weather` | Num: 10.0% \| Fact: 0.0% \| Risk: N/A \| Hall: 66.7% \| Comp: 80.0% | Num: 80.0% \| Fact: 80.0% \| Risk: N/A \| Hall: 0.0% \| Comp: 100.0% | Num: 60.0% \| Fact: 76.7% \| Risk: N/A \| Hall: 0.0% \| Comp: 100.0% |
| `evidence_based_reasoning` | Num: 23.3% \| Fact: 40.0% \| Risk: 0.0% \| Hall: 41.7% \| Comp: 100.0% | Num: 53.3% \| Fact: 40.0% \| Risk: 0.0% \| Hall: 8.3% \| Comp: 75.0% | Num: 36.7% \| Fact: 40.0% \| Risk: 100.0% \| Hall: 0.0% \| Comp: 100.0% |
| `hallucination_resistance` | Num: 0.0% \| Fact: 16.7% \| Risk: N/A \| Hall: 0.0% \| Comp: 50.0% | Num: 33.3% \| Fact: 10.0% \| Risk: N/A \| Hall: 16.0% \| Comp: 65.0% | Num: 0.0% \| Fact: 15.0% \| Risk: N/A \| Hall: 0.0% \| Comp: 40.0% |
| `hourly_forecast` | Num: 20.0% \| Fact: 0.0% \| Risk: N/A \| Hall: 66.7% \| Comp: 80.0% | Num: 60.0% \| Fact: 20.0% \| Risk: N/A \| Hall: 40.0% \| Comp: 100.0% | Num: 70.0% \| Fact: 10.0% \| Risk: N/A \| Hall: 11.7% \| Comp: 100.0% |
| `missing_or_incomplete_data` | Num: 0.0% \| Fact: 6.7% \| Risk: 0.0% \| Hall: 20.0% \| Comp: 35.3% | Num: 100.0% \| Fact: 23.3% \| Risk: 33.3% \| Hall: 60.0% \| Comp: 32.7% | Num: 0.0% \| Fact: 30.0% \| Risk: 33.3% \| Hall: 25.0% \| Comp: 39.3% |
| `multistep_reasoning` | Num: 0.0% \| Fact: 35.0% \| Risk: 0.0% \| Hall: 100.0% \| Comp: 90.0% | Num: 63.3% \| Fact: 63.3% \| Risk: 0.0% \| Hall: 20.0% \| Comp: 100.0% | Num: 10.0% \| Fact: 61.7% \| Risk: 100.0% \| Hall: 0.0% \| Comp: 100.0% |
| `precipitation_and_rainfall` | Num: 20.0% \| Fact: 20.0% \| Risk: N/A \| Hall: 62.5% \| Comp: 83.3% | Num: 20.0% \| Fact: 6.7% \| Risk: N/A \| Hall: 70.0% \| Comp: 86.7% | Num: 90.0% \| Fact: 53.3% \| Risk: N/A \| Hall: 10.0% \| Comp: 100.0% |
| `temperature_comparison` | Num: 40.0% \| Fact: 6.7% \| Risk: N/A \| Hall: 50.0% \| Comp: 100.0% | Num: 6.7% \| Fact: 36.7% \| Risk: N/A \| Hall: 91.7% \| Comp: 90.0% | Num: 6.7% \| Fact: 10.0% \| Risk: N/A \| Hall: 20.0% \| Comp: 90.0% |
| `weather_safety_and_risk` | Num: 12.5% \| Fact: 46.0% \| Risk: 0.0% \| Hall: 66.7% \| Comp: 95.0% | Num: 87.5% \| Fact: 91.0% \| Risk: 40.0% \| Hall: 12.5% \| Comp: 100.0% | Num: 0.0% \| Fact: 48.3% \| Risk: 100.0% \| Hall: 0.0% \| Comp: 86.7% |
| `weather_trends` | Num: 0.0% \| Fact: 10.0% \| Risk: N/A \| Hall: 100.0% \| Comp: 70.0% | Num: 20.0% \| Fact: 23.3% \| Risk: N/A \| Hall: 50.0% \| Comp: 90.0% | Num: 20.0% \| Fact: 20.0% \| Risk: N/A \| Hall: 0.0% \| Comp: 100.0% |

> [!IMPORTANT]
> **Risk Accuracy vs. Numerical Accuracy Reconciliation:**
> In safety and hazard evaluations (such as `weather_safety_and_risk`), Complete Sky Reader achieved **100.0% Risk Classification Accuracy** (accurately classifying hazard severity into LOW, MODERATE, HIGH, or SEVERE), while registering **0.0% Numerical Variable Accuracy**. This distinction reflects an intentional architectural behavior: upon detecting hazardous weather, Sky Reader's hallucination controller triggered a verified meteorological fallback. The fallback generated concise, verified narrative precautions and severity alerts rather than quoting raw numerical sensor readings. In contrast, the ungrounded Tool-Using Agent quoted numbers (87.5% numerical recall) but misclassified risk levels in 60% of cases (40.0% risk accuracy). Numerical accuracy and risk classification accuracy measure independent facets of system performance.

---

## 3. Statistical Reliability & Paired Hypothesis Tests

### 95% Bootstrap Confidence Intervals (B=2000 Resamples)

| System | Numerical Accuracy (95% CI) | Factual Accuracy (95% CI) | Hallucination Rate (95% CI) | Completeness (95% CI) |
|---|---|---|---|---|
| **Baseline LLM (Zero Tools)** | 14.3% [6.2%, 23.6%] | 18.1% [11.2%, 25.8%] | 49.5% [33.3%, 65.7%] | 78.4% [70.7%, 85.7%] |
| **Tool-Using Agent (No Verification)** | 48.1% [35.3%, 61.2%] | 39.4% [29.2%, 50.5%] | 35.9% [22.3%, 49.5%] | 83.9% [76.9%, 90.4%] |
| **Complete Sky Reader (Full Platform)** | 34.1% [22.5%, 46.1%] | 36.5% [27.0%, 46.5%] | 8.3% [1.4%, 16.9%] | 85.6% [77.5%, 92.6%] |

### Paired Difference Tests Across Matched Test Cases

| Comparison Pair | Metric | Mean Diff (A - B) | 95% Bootstrap CI | p-value (Two-Sided) | Statistically Significant? |
|---|---|---|---|---|---|
| `tool_using_agent_vs_baseline_llm` | Numerical Accuracy | +0.337 | [+0.174, +0.500] | p < 0.001 | ✅ **YES** |
| `tool_using_agent_vs_baseline_llm` | Factual Accuracy | +0.213 | [+0.112, +0.327] | p < 0.001 | ✅ **YES** |
| `tool_using_agent_vs_baseline_llm` | Hallucination Rate | -0.011 | [-0.167, +0.149] | p = 0.9060 | ❌ No |
| `tool_using_agent_vs_baseline_llm` | Completeness Score | +0.056 | [-0.010, +0.126] | p = 0.0930 | ❌ No |
| `sky_reader_full_vs_tool_using_agent` | Numerical Accuracy | -0.140 | [-0.314, +0.035] | p = 0.1310 | ❌ No |
| `sky_reader_full_vs_tool_using_agent` | Factual Accuracy | -0.029 | [-0.127, +0.060] | p = 0.5250 | ❌ No |
| `sky_reader_full_vs_tool_using_agent` | Hallucination Rate | -0.254 | [-0.375, -0.145] | p < 0.001 | ✅ **YES** |
| `sky_reader_full_vs_tool_using_agent` | Completeness Score | +0.017 | [-0.043, +0.072] | p = 0.5750 | ❌ No |
| `sky_reader_full_vs_baseline_llm` | Numerical Accuracy | +0.198 | [+0.058, +0.337] | p = 0.0070 | ✅ **YES** |
| `sky_reader_full_vs_baseline_llm` | Factual Accuracy | +0.184 | [+0.076, +0.303] | p < 0.001 | ✅ **YES** |
| `sky_reader_full_vs_baseline_llm` | Hallucination Rate | -0.265 | [-0.403, -0.123] | p < 0.001 | ✅ **YES** |
| `sky_reader_full_vs_baseline_llm` | Completeness Score | +0.072 | [-0.001, +0.147] | p = 0.0530 | ❌ No |

### Matched-Case Pairing & Excluded Cases Transparency

Paired hypothesis tests require strictly identical test case IDs between compared systems. Answer quality metrics are computed exclusively on mutually evaluable executions. Failed or timed-out executions are not treated as correct or incorrect answers; they are excluded from quality scoring and tracked separately under execution reliability.

#### Pairing: `tool_using_agent_vs_baseline_llm`
- **Matched Test Cases Evaluated (N=50):** `TC-CMP-001, TC-CMP-002, TC-CMP-003, TC-CMP-004, TC-CMP-005, TC-CUR-001, TC-CUR-002, TC-CUR-003, TC-CUR-004, TC-CUR-005, TC-EVD-001, TC-EVD-002, TC-EVD-003, TC-EVD-004, TC-EVD-005, TC-HAL-001, TC-HAL-002, TC-HAL-003, TC-HAL-004, TC-HAL-005, TC-HLY-001, TC-HLY-002, TC-HLY-003, TC-HLY-004, TC-HLY-005, TC-INC-001, TC-INC-002, TC-INC-003, TC-INC-004, TC-INC-005, TC-MLT-001, TC-MLT-002, TC-MLT-003, TC-MLT-004, TC-MLT-005, TC-PRC-001, TC-PRC-002, TC-PRC-003, TC-PRC-004, TC-PRC-005, TC-RSK-001, TC-RSK-002, TC-RSK-003, TC-RSK-004, TC-RSK-005, TC-TRD-001, TC-TRD-002, TC-TRD-003, TC-TRD-004, TC-TRD-005`
- **Excluded Cases:** None (100% matched-case completion)

#### Pairing: `sky_reader_full_vs_tool_using_agent`
- **Matched Test Cases Evaluated (N=50):** `TC-CMP-001, TC-CMP-002, TC-CMP-003, TC-CMP-004, TC-CMP-005, TC-CUR-001, TC-CUR-002, TC-CUR-003, TC-CUR-004, TC-CUR-005, TC-EVD-001, TC-EVD-002, TC-EVD-003, TC-EVD-004, TC-EVD-005, TC-HAL-001, TC-HAL-002, TC-HAL-003, TC-HAL-004, TC-HAL-005, TC-HLY-001, TC-HLY-002, TC-HLY-003, TC-HLY-004, TC-HLY-005, TC-INC-001, TC-INC-002, TC-INC-003, TC-INC-004, TC-INC-005, TC-MLT-001, TC-MLT-002, TC-MLT-003, TC-MLT-004, TC-MLT-005, TC-PRC-001, TC-PRC-002, TC-PRC-003, TC-PRC-004, TC-PRC-005, TC-RSK-001, TC-RSK-002, TC-RSK-003, TC-RSK-004, TC-RSK-005, TC-TRD-001, TC-TRD-002, TC-TRD-003, TC-TRD-004, TC-TRD-005`
- **Excluded Cases:** None (100% matched-case completion)

#### Pairing: `sky_reader_full_vs_baseline_llm`
- **Matched Test Cases Evaluated (N=50):** `TC-CMP-001, TC-CMP-002, TC-CMP-003, TC-CMP-004, TC-CMP-005, TC-CUR-001, TC-CUR-002, TC-CUR-003, TC-CUR-004, TC-CUR-005, TC-EVD-001, TC-EVD-002, TC-EVD-003, TC-EVD-004, TC-EVD-005, TC-HAL-001, TC-HAL-002, TC-HAL-003, TC-HAL-004, TC-HAL-005, TC-HLY-001, TC-HLY-002, TC-HLY-003, TC-HLY-004, TC-HLY-005, TC-INC-001, TC-INC-002, TC-INC-003, TC-INC-004, TC-INC-005, TC-MLT-001, TC-MLT-002, TC-MLT-003, TC-MLT-004, TC-MLT-005, TC-PRC-001, TC-PRC-002, TC-PRC-003, TC-PRC-004, TC-PRC-005, TC-RSK-001, TC-RSK-002, TC-RSK-003, TC-RSK-004, TC-RSK-005, TC-TRD-001, TC-TRD-002, TC-TRD-003, TC-TRD-004, TC-TRD-005`
- **Excluded Cases:** None (100% matched-case completion)

### Statistical Methodology & Sample Size Caveats

- **Bootstrap Configuration:** Non-parametric paired case bootstrap resampling with replacement with B=2000 resamples, seed=42, resampling unit: `test_case_id`.
- **Sample Size Constraints:** Statistical sensitivity is constrained by the evaluation cohort size. While sufficient to detect large architectural effect sizes (delta > 0.15), small category subsets (n=5 per category) have high standard errors and low statistical power. Small variances (delta < 0.05) cannot be distinguished from LLM sampling noise.
- **Multiple Comparisons:** Hypothesis tests across multiple metrics and systems are reported with nominal two-sided p-values without Family-Wise Error Rate (FWER) or False Discovery Rate (FDR) adjustment (such as Bonferroni). Readers should interpret marginal significances (p ~ 0.01 - 0.05) with appropriate conservatism due to cumulative Type I error inflation across multi-dimensional comparisons.

---

## 4. Error Analysis Taxonomy

> [!NOTE]
> **Multi-Label Taxonomy & Denominator Rigor:**  
> 1. **Multi-Label Classification:** An individual test case execution may exhibit multiple failure modes simultaneously (for instance, omitting an expected numerical value while also asserting an unsupported claim). Consequently, total error occurrences across modes naturally exceed the total number of test cases.  
> 2. **Explicit Denominator Separation:**  
>    - For **Answer Quality Failure Modes** (`incorrect_numerical_values`, `missing_numerical_values`, `factual_contradictions`, `unsupported_or_hallucinated_claims`, `risk_misclassifications`, `incomplete_responses`), the denominator is strictly **Evaluable Cases** (cases where the system successfully generated a response for evaluation).  
>    - For **Execution Failures & Timeouts** (`execution_failures_or_timeouts`), the denominator is **Total Attempted Cases** (the total number of executions attempted), ensuring execution unreliability is tracked against the full cohort rather than conflated with answer quality.

| Failure Mode | Baseline LLM (Cases / Occur) | Tool Agent (Cases / Occur) | Complete Sky Reader (Cases / Occur) | Primary Impact |
|---|---|---|---|---|
| `incorrect_numerical_values` | 19/50 (38%) [25x] | 16/50 (32%) [18x] | 16/50 (32%) [18x] | Measurements deviating beyond allowed tolerance margin. |
| `missing_numerical_values` | 24/50 (48%) [35x] | 16/50 (32%) [17x] | 19/50 (38%) [26x] | Mandatory weather variables omitted from response. |
| `factual_contradictions` | 33/50 (66%) [47x] | 22/50 (44%) [29x] | 14/50 (28%) [15x] | Claims with inverted polarity (e.g. recommending umbrella when dry). |
| `unsupported_or_hallucinated_claims` | 18/50 (36%) [24x] | 18/50 (36%) [22x] | 5/50 (10%) [6x] | Fabricated weather readings or unverified forecasts. |
| `risk_misclassifications` | 11/50 (22%) [11x] | 8/50 (16%) [8x] | 2/50 (4%) [2x] | Severity errors (underestimating or overestimating hazard level). |
| `evidence_grounding_failures` | 0/50 (0%) [0x] | 0/50 (0%) [0x] | 1/50 (2%) [1x] | Unverifiable or hallucinated evidence citation IDs. |
| `incomplete_responses` | 21/50 (42%) [21x] | 18/50 (36%) [18x] | 12/50 (24%) [12x] | Failure to address location, uncertainty notes, or refusals. |
| `execution_failures_or_timeouts` | 0/50 (0%) [0x] | 0/50 (0%) [0x] | 0/50 (0%) [0x] | Provider timeouts or API network failures. |

### Representative Failure Case Studies

#### Case Study 1: `incorrect_numerical_values`
- **Test Case:** `TC-CMP-001` (temperature_comparison)
- **System:** `baseline_llm`
- **Diagnosis:** {"test_case_id": "TC-CMP-001", "system": "baseline_llm", "category": "temperature_comparison", "variable": "average_diff", "expected_value": -0.7, "extracted_value": 5.0, "converted_value": 5.0, "tolerance": 0.5, "absolute_error": 5.7, "context": "5"}

#### Case Study 2: `missing_numerical_values`
- **Test Case:** `TC-CMP-003` (temperature_comparison)
- **System:** `baseline_llm`
- **Diagnosis:** {"test_case_id": "TC-CMP-003", "system": "baseline_llm", "category": "temperature_comparison", "variable": "temperature_range", "expected_value": 8.5}

#### Case Study 3: `factual_contradictions`
- **Test Case:** `TC-CMP-002` (temperature_comparison)
- **System:** `baseline_llm`
- **Diagnosis:** {"test_case_id": "TC-CMP-002", "system": "baseline_llm", "category": "temperature_comparison", "expected_claim": "morning temperature is around 21.0 \u00b0C", "explanation": "Concept words present (['morning', 'temperature', 'around']) but expected number 21.0 was contradicted or missing.", "matched_segments": ["morning", "temperature", "around"]}

#### Case Study 4: `unsupported_or_hallucinated_claims`
- **Test Case:** `TC-CMP-001` (temperature_comparison)
- **System:** `baseline_llm`
- **Diagnosis:** {"test_case_id": "TC-CMP-001", "system": "baseline_llm", "category": "temperature_comparison", "issue_type": "CONTRADICTION", "claim_text": "Reported value 5.0 for average_diff", "explanation": "Contradicts reference value -0.7 by 5.70 (tolerance=0.5).", "reference_data": "-0.7"}

#### Case Study 5: `risk_misclassifications`
- **Test Case:** `TC-EVD-002` (evidence_based_reasoning)
- **System:** `baseline_llm`
- **Diagnosis:** {"test_case_id": "TC-EVD-002", "system": "baseline_llm", "category": "evidence_based_reasoning", "expected_risk": "SEVERE", "predicted_risk": null, "severity_error": null, "underreported": null, "overreported": null, "missed_hazards": [], "false_positive_hazards": ["extreme_cold", "extreme_heat", "heavy_rainfall", "strong_wind"]}

---

## 5. Weather Risk Confusion Matrix

### Baseline LLM (Zero Tools) Confusion Matrix

| Actual \ Predicted | LOW | MODERATE | HIGH | SEVERE |
|---|---|---|---|---|
| **LOW** | 0 | 0 | 0 | 0 |
| **MODERATE** | 0 | 0 | 0 | 0 |
| **HIGH** | 0 | 0 | 0 | 0 |
| **SEVERE** | 0 | 0 | 0 | 0 |

### Tool-Using Agent (No Verification) Confusion Matrix

| Actual \ Predicted | LOW | MODERATE | HIGH | SEVERE |
|---|---|---|---|---|
| **LOW** | 1 | 0 | 0 | 0 |
| **MODERATE** | 0 | 0 | 0 | 0 |
| **HIGH** | 0 | 0 | 1 | 0 |
| **SEVERE** | 0 | 0 | 1 | 1 |

### Complete Sky Reader (Full Platform) Confusion Matrix

| Actual \ Predicted | LOW | MODERATE | HIGH | SEVERE |
|---|---|---|---|---|
| **LOW** | 2 | 0 | 0 | 0 |
| **MODERATE** | 0 | 0 | 0 | 0 |
| **HIGH** | 0 | 0 | 4 | 0 |
| **SEVERE** | 0 | 0 | 0 | 3 |

---

## 6. Scientific Discussion & Architectural Insights

1. **Baseline LLM (Zero Tools):** Shows high ungrounded hallucination rates on specific real-time queries. When prompted with strict epistemic boundaries, it acknowledges sensor limitations, but in unstructured prompts it hallucinates realistic-sounding temperatures based on training weights.
2. **Tool-Using Agent:** Solves factual retrieval by fetching raw weather observations, achieving high numerical recall. However, without claim validation guardrails, it remains vulnerable to conversational drift, missed hazard thresholds, and ungrounded extrapolation on edge cases.
3. **Complete Sky Reader Platform:** Integrates deterministic meteorological calculations and Phase 4 claim validation. Automated audit forces factual alignment with evidence collections, drastically curtailing hard contradictions and ensuring uncertainty communication on missing or corrupted sensor channels.

### Methodological Limitations
- **Sample Size:** 50 cases provide adequate resolution for large architectural shifts, but fine-grained comparisons require larger cohorts.
- **Synthetic Fixtures:** Results establish internal validity against frozen reference standards; real-world operational accuracy requires continuous live monitoring.