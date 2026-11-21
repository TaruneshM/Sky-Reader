# 📐 Evaluation Metrics & Mathematical Formulation Specification

**Project Title:** Sky Reader: An Evidence-Grounded Agentic AI Framework for Reliable Weather Intelligence and Risk Assessment  
**Document Type:** Metric Formulation & Mathematical Reference  
**Implementation Modules:** `backend/evaluation/metrics/numerical.py`, `factual.py`, `hallucination.py`, `evidence.py`, `risk.py`, `completeness.py`, `performance.py`, `aggregator.py`  

---

## 1. Metric Design Principles

In accordance with rigorous scientific benchmarking standards:
1. **Zero Arbitrary Composite Scores:** Individual metrics are **never** combined into an arbitrary weighted composite score (e.g., $0.4 \times \text{Acc} + 0.3 \times \text{Hallucination}$). Each metric measures an isolated, orthogonal capability of the system.
2. **Explicit Denominators:** Every reported metric defines an exact mathematical numerator and denominator. Denominators distinguish *total attempted cases* ($N=50$), *evaluable cases* ($N=50$), and *subsets with applicable ground truth* (e.g., $N=43$ for numerical variables, $N=11$ for risk classifications).
3. **Multi-Label Error Accountability:** Failure modes are classified under a multi-label taxonomy; a single response can exhibit an omitted number and an unsupported factual claim simultaneously.

---

## 2. Mathematical Formulations

### 1. Numerical Variable Accuracy ($\text{Acc}_{\text{num}}$)
Evaluates whether quantitative meteorological quantities asserted in the response fall within configured scientific tolerances of the reference fixture.

$$\text{Acc}_{\text{num}} = \frac{\sum_{i=1}^{M_{\text{eval}}} \sum_{v \in V_i} \mathbb{I}\left( |x_{i,v} - y_{i,v}^*| \le \tau_v \right)}{\sum_{i=1}^{M_{\text{eval}}} |V_i|}$$

- **Numerator:** Total count of extracted numerical variables matching reference values within allowed tolerance $\tau_v$ (e.g., $\pm 1.0^\circ\text{C}$ for temperature, $\pm 5.0\text{ km/h}$ for wind speed, $\pm 1.0\text{ mm}$ for rainfall).
- **Denominator:** Total expected numerical variables across evaluable numerical cases ($M_{\text{num}} = 43$ cases, $\sum |V_i| = 72$ expected variables).
- **Sub-cohort Note:** 7 of 50 benchmark cases have no expected numerical values ($V_i = \emptyset$) because they evaluate refusal on adversarial/unanswerable queries (`TC-HAL-001`, `TC-HAL-004`, `TC-INC-001`, `TC-INC-002`, `TC-INC-003`, `TC-INC-005`, `TC-RSK-005`).

### 2. Mean Absolute Error (MAE)
Measures the average magnitude of numerical deviation on extracted meteorological variables.

$$\text{MAE} = \frac{1}{K} \sum_{k=1}^K |x_k - y_k^*|$$

- **Numerator:** Sum of absolute differences between candidate extracted values and reference fixture values across all matched variable pairs.
- **Denominator:** $K$, the total count of matched variable pairs where the model reported a value for an expected variable.
- **Unit Note:** MAE aggregates deviations across mixed meteorological dimensions (°C, km/h, mm); it is reported as a scale-aggregated index of quantitative drift.

### 3. Factual Claim Accuracy ($\text{Acc}_{\text{fact}}$)
Measures the semantic recall of expected ground-truth meteorological facts and trends.

$$\text{Acc}_{\text{fact}} = \frac{\sum_{i=1}^N \sum_{c \in C_i^*} \mathbb{I}(c \text{ is semantically supported})}{\sum_{i=1}^N |C_i^*|}$$

- **Numerator:** Total expected factual propositions successfully addressed and supported in candidate responses.
- **Denominator:** Total expected factual propositions across all benchmark cases ($N=50$ cases, $\sum |C_i^*| = 149$ expected claims).

### 4. Hallucination Rate ($H_{\text{rate}}$)
Measures the proportion of asserted model statements that conflict with or lack grounding in retrieved telemetry.

$$H_{\text{rate}} = \frac{N_{\text{contradicted}} + N_{\text{unsupported}}}{N_{\text{total claims evaluated}}}$$

- **Numerator:** Count of contradicted claims (directly conflicting with telemetry) plus unsupported claims (asserting unverified weather phenomena).
- **Denominator:** Total atomic claims evaluated across candidate responses.

### 5. Contradiction Rate ($C_{\text{rate}}$) and Unsupported Rate ($U_{\text{rate}}$)
Decomposes the hallucination rate into hard scientific contradictions versus ungrounded speculations:

$$C_{\text{rate}} = \frac{N_{\text{contradicted}}}{N_{\text{total claims evaluated}}}, \quad U_{\text{rate}} = \frac{N_{\text{unsupported}}}{N_{\text{total claims evaluated}}}$$

### 6. Clean Case Ratio ($R_{\text{clean}}$)
Proportion of test cases answered completely free of ungrounded or contradictory assertions:

$$R_{\text{clean}} = \frac{\sum_{i=1}^N \mathbb{I}(N_{\text{contradicted}, i} = 0 \land N_{\text{unsupported}, i} = 0)}{N}$$

- **Numerator:** Count of evaluable test cases where the model made zero contradicted and zero unsupported claims.
- **Denominator:** Total evaluable benchmark cases ($N=50$).

### 7. Meteorological Risk Classification Accuracy ($\text{Acc}_{\text{risk}}$)
Measures the accuracy of classifying hazard severity into standardized meteorological tiers (LOW, MODERATE, HIGH, SEVERE):

$$\text{Acc}_{\text{risk}} = \frac{\sum_{i \in \mathcal{R}} \mathbb{I}(\hat{r}_i = r_i^*)}{|\mathcal{R}|}$$

- **Numerator:** Count of cases where the predicted risk level $\hat{r}_i$ matches the ground-truth severity tier $r_i^*$.
- **Denominator:** $|\mathcal{R}| = 11$, the subset of 11 benchmark cases carrying ground-truth risk classifications.
- **Strict Grading Rule:** If a system provides no risk classification ($\hat{r}_i = \text{None}$), it is graded as non-matching ($\mathbb{I} = 0$). Missing risk is never assumed safe.

### 8. Dangerous Severity Underreporting Count ($N_{\text{underreport}}$)
Counts life-safety failure modes where a high or severe meteorological hazard is classified as low or moderate:

$$N_{\text{underreport}} = \sum_{i \in \mathcal{R}} \mathbb{I}(\text{Severity}(\hat{r}_i) < \text{Severity}(r_i^*))$$

### 9. Response Completeness Score ($\text{Comp}$)
Measures how comprehensively the model addresses all facets of the user's natural language request (location, observation, forecast, advisory):

$$\text{Comp} = \frac{1}{N} \sum_{i=1}^N \frac{\text{Elements Addressed}_i}{\text{Total Required Elements}_i}$$

- **Fully Complete Cases Ratio:** Proportion of cases achieving $\text{Comp}_i = 1.0$.

### 10. First-Attempt Reliability ($\text{Rel}_{\text{1st}}$) vs. Eventual Completion ($\text{Rel}_{\text{eventual}}$)
Distinguishes initial single-pass execution reliability from eventual completion post-retry:

$$\text{Rel}_{\text{1st}} = \frac{N_{\text{completed on first attempt}}}{N_{\text{total attempted cases}}}, \quad \text{Rel}_{\text{eventual}} = \frac{N_{\text{completed eventually}}}{N_{\text{total attempted cases}}}$$

- **Denominator:** $N=50$ attempted cases per system.

### 11. Latency Profiles ($\text{Lat}_{\text{mean}}, \text{Lat}_{\text{P95}}$)
Measures the total wall-clock runtime in milliseconds from request receipt to final validated response delivery. Evaluated across completed cases using sample mean and empirical 95th percentile.
