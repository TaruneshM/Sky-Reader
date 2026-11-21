# 🧪 Research Hypotheses Specification

**Project Title:** Sky Reader: An Evidence-Grounded Agentic AI Framework for Reliable Weather Intelligence and Risk Assessment  
**Author:** Sky Reader Research Team  
**Status:** Methodological Formulation (Pre-Experiment Formalization)  

---

## Overview

The following formal hypotheses are formulated to investigate the architectural efficacy and operational trade-offs of the **Sky Reader** framework. In accordance with scientific methodology, these hypotheses represent testable propositions subject to empirical falsification, rather than assumed facts.

---

## Hypothesis 1 (H1): Hallucination Mitigation
> **Hypothesis 1:** An agentic weather architecture integrating evidence compilation, deterministic claim validation, and automated hallucination correction (Complete Sky Reader) achieves a statistically significant reduction in hallucination rate compared to a conventional tool-augmented agent lacking verification guardrails (Tool-Using Agent).

- **Null Hypothesis ($H_{0,1}$):** There is no significant difference in the mean paired hallucination rate between Complete Sky Reader and the Tool-Using Agent ($\mu_{\text{hallucination, SkyReader}} - \mu_{\text{hallucination, ToolAgent}} \ge 0$).
- **Alternative Hypothesis ($H_{1,1}$):** Complete Sky Reader produces a lower mean paired hallucination rate than the Tool-Using Agent ($\mu_{\text{hallucination, SkyReader}} - \mu_{\text{hallucination, ToolAgent}} < 0$).
- **Operational Definition of Hallucination Rate:** Proportion of asserted model statements classified as either a *contradiction* (conflicting with reference telemetry) or *unsupported* (fabricating non-existent conditions) relative to total asserted claims across matched benchmark cases.
- **Test Metric & Statistical Threshold:** Two-sided paired permutation sign-flip test across $N=50$ matched test cases with $B=2,000$ resamples at $\alpha = 0.05$.
- **Falsification Criteria:** Falsified if $p \ge 0.05$ or if the 95% bootstrap confidence interval of the difference covers zero or indicates increased hallucinations in Sky Reader.

---

## Hypothesis 2 (H2): Weather Risk Classification Precision
> **Hypothesis 2:** Augmenting an agentic LLM with a deterministic meteorological risk assessment engine significantly improves weather hazard severity classification accuracy and reduces dangerous severity underreporting compared to unverified tool-using agents and baseline LLMs.

- **Null Hypothesis ($H_{0,2}$):** Complete Sky Reader exhibits risk classification accuracy less than or equal to that of the Tool-Using Agent ($\text{Acc}_{\text{risk, SkyReader}} \le \text{Acc}_{\text{risk, ToolAgent}}$).
- **Alternative Hypothesis ($H_{1,2}$):** Complete Sky Reader exhibits superior risk classification accuracy compared to the Tool-Using Agent ($\text{Acc}_{\text{risk, SkyReader}} > \text{Acc}_{\text{risk, ToolAgent}}$).
- **Operational Definition of Risk Accuracy:** The proportion of risk-applicable benchmark cases ($N=11$) where the system's predicted hazard severity level (LOW, MODERATE, HIGH, SEVERE) matches the meteorological ground-truth severity classification.
- **Operational Definition of Dangerous Underreporting:** Cases where the system classifies a HIGH or SEVERE meteorological event as safe or lower severity (e.g., SEVERE storm classified as HIGH or LOW).
- **Test Metric & Statistical Threshold:** Exact binomial difference of proportions across the $N=11$ risk-applicable benchmark cohort.
- **Falsification Criteria:** Falsified if Complete Sky Reader achieves equal or lower classification accuracy than the Tool-Using Agent, or if it produces more dangerous severity underreports.

---

## Hypothesis 3 (H3): Verification Latency Penalty
> **Hypothesis 3:** Multi-stage verification guardrails (evidence extraction, secondary claim audit, potential LLM regeneration, and explanation proof generation) introduce a statistically and operationally significant latency penalty compared to unverified tool-using generation and zero-tool generation.

- **Null Hypothesis ($H_{0,3}$):** Mean end-to-end execution latency for Complete Sky Reader is equal to or less than that of the Tool-Using Agent ($\mu_{\text{latency, SkyReader}} \le \mu_{\text{latency, ToolAgent}}$).
- **Alternative Hypothesis ($H_{1,3}$):** Mean end-to-end execution latency for Complete Sky Reader is greater than that of the Tool-Using Agent ($\mu_{\text{latency, SkyReader}} > \mu_{\text{latency, ToolAgent}}$).
- **Operational Definition of Latency:** Wall-clock response generation time in milliseconds from initial query ingestion to final validated payload return.
- **Test Metric & Statistical Threshold:** Paired difference test and 95% bootstrap confidence intervals for mean and P95 latency across $N=50$ cases.
- **Falsification Criteria:** Falsified if Complete Sky Reader exhibits comparable or lower latency than the Tool-Using Agent.

---

## Hypothesis 4 (H4): Verification Coverage / Recall Trade-Off
> **Hypothesis 4:** The enforcement of strict evidence-grounding guardrails and safe narrative fallbacks induces a trade-off that reduces raw numerical variable coverage (recall) in exchange for eliminating ungrounded numerical errors and reducing Mean Absolute Error (MAE).

- **Null Hypothesis ($H_{0,4}$):** Complete Sky Reader achieves numerical variable accuracy/recall equal to or greater than the Tool-Using Agent ($\text{Acc}_{\text{numerical, SkyReader}} \ge \text{Acc}_{\text{numerical, ToolAgent}}$).
- **Alternative Hypothesis ($H_{1,4}$):** Complete Sky Reader achieves lower raw numerical variable accuracy/recall than the Tool-Using Agent ($\text{Acc}_{\text{numerical, SkyReader}} < \text{Acc}_{\text{numerical, ToolAgent}}$), while simultaneously achieving lower Mean Absolute Error ($\text{MAE}_{\text{SkyReader}} < \text{MAE}_{\text{ToolAgent}}$).
- **Operational Definition of Numerical Accuracy:** The proportion of expected reference numerical variables correctly extracted within allowed meteorological tolerances across the $N=43$ cases with numerical ground truth.
- **Operational Definition of MAE:** The mean absolute deviation between reported numerical values and reference fixture values across matched variables.
- **Falsification Criteria:** Falsified if Complete Sky Reader exhibits higher numerical recall than the Tool Agent, or if its numerical MAE is equal to or worse than that of the Tool Agent.
