# 📑 Statistical Methodology & Integrity Notes

**Project Title:** Sky Reader: An Evidence-Grounded Agentic AI Framework for Reliable Weather Intelligence and Risk Assessment  
**Document Type:** Statistical Protocol & Methodological Audit  
**Implementation Source:** `backend/evaluation/analysis/comparator.py`, `backend/evaluation/analysis/final_benchmark_audit.md`  

---

## 1. Experimental Design: Paired Case-Level Resampling

All comparative evaluations between systems (e.g., Sky Reader vs. Tool Agent, Sky Reader vs. Baseline LLM) are structured under a **strictly paired, matched-case design**:
1. Every test case in the benchmark ($N=50$) is presented to all three architectures under identical prompt text and identical fixture state.
2. Pairwise statistical tests compute differences $d_i = y_{A,i} - y_{B,i}$ for each individual test case $i \in \{1, \dots, N\}$.
3. The resampling unit is always the `test_case_id`. Responses from different systems are never shuffled across disparate test cases, preserving the within-case correlation structure.

---

## 2. Reconciling Evaluation Denominators: $N=43$ vs. $N=50$

A critical methodological integrity finding concerns the evaluation denominator:

### Why Do Numerical Comparisons Use $N=43$ while Global Metrics Use $N=50$?
- **The Benchmark Suite:** Contains exactly $N=50$ distinct test cases across 10 categories.
- **Global Metrics ($N=50$):** Factual Accuracy, Hallucination Rate, Completeness Score, and Clean Case Ratio evaluate all 50 cases ($N=50$).
- **Numerical Accuracy & Numerical Comparisons ($N=43$):** Exactly 43 cases in the dataset define reference numerical values in `expected_numerical_values`.
- **The 7 Non-Numerical Cases:**
  1. `TC-HAL-001` (10-year far-future query: November 15, 2035).
  2. `TC-HAL-004` (Fictional planet query: capital city of Mars).
  3. `TC-INC-001` (Forecast with missing precipitation sensor channels).
  4. `TC-INC-002` (Null wind sensors in Incompleteville).
  5. `TC-INC-003` (Empty hourly forecast payload).
  6. `TC-INC-005` (Fictional realm: AtlantisFantasyRealm999).
  7. `TC-RSK-005` (Mild conditions hazard inquiry in Dehradun).

In these 7 cases, expecting a numerical value would be a **category error**: the scientific objective of these test cases is to evaluate whether the model *appropriately refuses to fabricate numbers* when data is non-existent, far-future, or corrupted. Expecting a numerical measurement on Mars or in the year 2035 would penalize models for correctly asserting epistemic limitations.

Therefore:
- **Numerical Accuracy Denominator:** Exactly $N=43$ test cases ($\sum |V_i| = 72$ variables).
- **Paired Numerical Permutation Test:** Evaluated across the 43 matched numerical cases ($N=43$).
- **Global Evaluation Denominator:** Exactly $N=50$ test cases.

---

## 3. Statistical Testing Framework

### Non-Parametric Bootstrap Confidence Intervals
To avoid assuming Gaussian normality on bounded proportional metrics (accuracy $\in [0, 1]$, hallucination rate $\in [0, 1]$), 95% confidence intervals are computed using the **percentile bootstrap**:
- **Resamples:** $B = 2,000$ bootstrap iterations with replacement.
- **Random Seed:** Fixed seed `42` to ensure 100% numerical reproducibility.
- **Interval Formulation:** $[q_{0.025}, q_{0.975}]$, where $q_\alpha$ is the empirical $\alpha$-quantile of the bootstrap mean distribution.

### Two-Sided Paired Permutation Test (Sign-Flip Test)
For hypothesis testing of differences between architectures ($H_0: \mu_{A-B} = 0$):
1. Compute observed sample mean difference: $\bar{d} = \frac{1}{n} \sum_{i=1}^n (A_i - B_i)$.
2. Under the null hypothesis that systems $A$ and $B$ are interchangeable, the paired difference $d_i$ is symmetric around zero.
3. For $b = 1$ to $B=2,000$ resamples (seed 42), generate a pseudo-difference vector by multiplying each $d_i$ by a random sign $s_i \in \{-1, +1\}$ with equal probability ($p=0.5$).
4. Compute the permutation test statistic: $\bar{d}^{*(b)} = \frac{1}{n} \sum_{i=1}^n s_i \cdot d_i$.
5. The empirical two-sided $p$-value is calculated as:
   $$p = \frac{1}{B} \sum_{b=1}^B \mathbb{I}\left( |\bar{d}^{*(b)}| \ge |\bar{d}| \right)$$
6. Statistical significance is declared if and only if $p < 0.05$ and the 95% bootstrap confidence interval does not cover zero.

---

## 4. Reproducible Statistical Power Analysis

A rigorous scientific paper must not assert statistical power without reproducible mathematical derivation. Below is the exact statistical power calculation for this paired benchmark design:

### Statistical Power Formulation
For a two-sided paired comparison at significance level $\alpha = 0.05$ ($z_{\alpha/2} \approx 1.960$) and sample size $n$:
$$\text{Power} = \Phi\left( \sqrt{n} \cdot d - z_{\alpha/2} \right)$$
where $d = \frac{\mu_{\text{diff}}}{\sigma_{\text{diff}}}$ is Cohen's effect size index, and $\Phi(\cdot)$ is the standard normal cumulative distribution function.

### Minimum Detectable Effect Size (MDES) for 80% Power ($\beta = 0.20$, $z_\beta = 0.842$)
$$d_{\text{MDES}} = \frac{z_{\alpha/2} + z_\beta}{\sqrt{n}} = \frac{1.95996 + 0.84162}{\sqrt{n}} = \frac{2.80158}{\sqrt{n}}$$

- **For Full Cohort ($N=50$):** $d_{\text{MDES}} = \frac{2.8016}{\sqrt{50}} = \mathbf{0.396}$ (Medium effect size).
- **For Numerical Cohort ($N=43$):** $d_{\text{MDES}} = \frac{2.8016}{\sqrt{43}} = \mathbf{0.427}$ (Medium effect size).

### Empirical Power Curve across Cohen's $d$ ($N=50, \alpha=0.05$)

| Effect Size ($d$) | Magnitude Classification | Statistical Power ($\%$) | Interpretation |
|---|---|---|---|
| $d = 0.20$ | Small effect | **29.3%** | Substantially underpowered; high risk of Type II error ($\beta = 70.7\%$). |
| $d = 0.30$ | Small-to-medium effect | **56.4%** | Moderate power. |
| $d = 0.35$ | Moderate effect | **69.7%** | Approaching acceptable threshold. |
| **$d = 0.40$** | **Medium effect** | **80.7%** | **Adequately powered ($\ge 80\%$). Benchmark threshold.** |
| $d = 0.45$ | Medium-to-large effect | **88.9%** | Well powered. |
| $d = 0.50$ | Large effect | **94.2%** | High power. |
| $d = 0.60$ | Very large effect | **98.9%** | Extremely high power. |
| $d \ge 0.70$ | Dominant architectural effect | **$\ge 99.9\%$** | Near-certain detection. |

### Crucial Methodological Interpretations:
1. **Large Effect Detection:** The benchmark is well-powered to detect large architectural effect sizes ($d \ge 0.40$, or raw accuracy differences $\Delta \ge 0.15$). Sky Reader's reduction in hallucination rate ($d = 0.82$, raw $\Delta = -0.2543$, $p < 0.001$) represents a very large effect size that the benchmark detects with $>99\%$ power.
2. **Absence of Difference $\ne$ Equivalence:** For metrics where no statistically significant difference was detected between Sky Reader and Tool Agent—namely Factual Accuracy ($p=0.5250, \Delta = -0.0293$) and Completeness ($p=0.5750, \Delta = +0.0167$)—the paper **must NOT claim statistical equivalence**. With $N=50$, small effect sizes ($\Delta < 0.08$) cannot be distinguished from LLM sampling variance. These results must be reported as *no statistically significant difference detected*, acknowledging sample-size sensitivity constraints.

---

## 5. Multiple Hypothesis Testing Considerations

When evaluating 12 pairwise hypothesis tests simultaneously across multiple metrics, the cumulative Family-Wise Error Rate (FWER) inflates according to $1 - (1 - \alpha)^k \approx 1 - (0.95)^{12} \approx 46.0\%$.

- **Bonferroni Conservative Threshold:** $\alpha_{\text{adjusted}} = \frac{0.05}{12} \approx \mathbf{0.00417}$.
- **Audit Finding:**
  - Sky Reader vs. Tool Agent Hallucination Reduction: $p < 0.001 \le 0.00417$ (**Remains significant under strict Bonferroni correction**).
  - Sky Reader vs. Baseline Hallucination Reduction: $p < 0.001 \le 0.00417$ (**Remains significant under strict Bonferroni correction**).
  - Sky Reader vs. Baseline Factual Accuracy Gain: $p < 0.001 \le 0.00417$ (**Remains significant under strict Bonferroni correction**).
  - Sky Reader vs. Baseline Numerical Accuracy Gain: $p = 0.0070 > 0.00417$ (**Marginal; significant under unadjusted $\alpha=0.05$, not under conservative Bonferroni**).

The paper must transparently report both unadjusted empirical $p$-values and Bonferroni-adjusted thresholds.
