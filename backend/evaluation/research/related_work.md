# 📖 Section 2: Related Work

**Paper:** Sky Reader: An Evidence-Grounded Agentic AI Framework for Reliable Weather Intelligence and Risk Assessment  
**Section Number:** 2  

---

## 2.1 Tool-Augmented Language Models

The integration of external tools into Large Language Models (LLMs) represents a central paradigm shift to overcome the limitations of static, closed-world parametric memory. Standard foundation models frequently struggle with arithmetic precision, dynamic temporal contexts, and domain-specific computation. 

To bridge this gap, Yao et al. (2023) proposed **ReAct**, a prompting framework that interleaves reasoning traces ("thoughts") with domain-specific API calls ("actions") and environment feedback ("observations"). By alternating between reasoning and action, ReAct demonstrated substantial improvements over pure Chain-of-Thought (CoT) prompting in multi-hop question answering (HotpotQA, FEVER) and interactive web navigation (WebShop). Similarly, Schick et al. (2023) introduced **Toolformer**, demonstrating that language models can self-teach tool use in a self-supervised manner. By inserting potential API calls (calculators, QA lookups, calendars) into plain text and retaining only those that reduced token perplexity, Toolformer demonstrated that a 6.7B parameter model could outperform much larger models without task-specific fine-tuning.

**Relationship and Distinction to Sky Reader:**  
Sky Reader builds on the principles of tool augmentation by equipping an agent with structured meteorological retrieval and analysis tools. However, conventional tool-augmented agents (including our audited `tool_using_agent` baseline) suffer from a critical failure mode: they treat raw API responses as contextual tokens but remain vulnerable to post-retrieval fabrication, interpretation drift, and reasoning hallucination. Unlike ReAct or Toolformer, which rely on the model itself to interpret tool outputs and self-correct, Sky Reader implements an external deterministic neuro-symbolic validation pipeline (`EvidenceEngine` and `ClaimValidator`). The foundation model generates candidate hypotheses, but cannot output unverified numerical or risk claims without deterministic symbolic verification against telemetry.

---

## 2.2 Evidence-Grounded Response Generation

Retrieval-Augmented Generation (RAG) grounds language generation in non-parametric external knowledge. Lewis et al. (2020) formalized the RAG architecture by combining a pre-trained sequence-to-sequence model with a dense neural retriever over Wikipedia passages, training the generator and retriever end-to-end to excel at knowledge-intensive NLP benchmarks (Natural Questions, TriviaQA). Concurrently, Guu et al. (2020) developed **REALM**, which integrated a neural knowledge retriever directly into the pre-training objective of masked language models.

**Relationship and Distinction to Sky Reader:**  
While standard RAG architectures retrieve unstructured text chunks from dense vector databases based on semantic similarity, weather intelligence presents a structurally distinct challenge:
1. **Dynamic Time-Series Telemetry:** Weather observations are not narrative passages; they are multi-dimensional, time-indexed numerical arrays (hourly temperature profiles, precipitation accumulations, barometric gradients).
2. **Deterministic Computations:** Weather queries often require mathematical operations (e.g., computing a 24-hour diurnal temperature delta, identifying maximum gust velocity, or evaluating convective available potential energy) rather than semantic text synthesis.

Sky Reader extends evidence-grounded generation from narrative text retrieval to structured telemetry compilation. Its `EvidenceEngine` transforms raw Open-Meteo REST payloads into strongly typed, immutable evidence items (`WeatherEvidenceItem`), ensuring that downstream assertions are grounded in verified observations rather than approximated passage semantics.

---

## 2.3 Hallucination Detection and Claim Verification

Hallucination—defined by Ji et al. (2023) as generated content that is nonsensical or unfaithful to the source text or real-world facts—remains a fundamental obstacle to deploying generative models in high-consequence domains. Hallucinations are broadly bifurcated into:
- *Intrinsic hallucinations:* Assertions that directly contradict the provided source evidence.
- *Extrinsic hallucinations:* Assertions that introduce external facts that cannot be substantiated or refuted by the source.

To detect hallucinations in black-box models without access to internal token probabilities or external databases, Manakul et al. (2023) proposed **SelfCheckGPT**. Operating on the principle that an LLM will produce divergent, mutually inconsistent completions when hallucinating, SelfCheckGPT evaluates sentence-level factuality by measuring consistency across stochastically sampled generations using n-gram overlap, BERTScore, and Natural Language Inference (NLI). In the domain of fine-grained evaluation, Min et al. (2023) introduced **FActScore**, which decomposes long-form text into individual atomic factual propositions and evaluates what percentage are supported by a knowledge corpus (such as Wikipedia), uncovering widespread hallucination even in commercial state-of-the-art models. To mitigate hallucinations during generation, Dhuliawala et al. (2024) developed **Chain-of-Verification (CoVe)**, where the model drafts a response, generates verification questions, answers them independently, and revises the draft to eliminate unverified claims.

**Relationship and Distinction to Sky Reader:**  
Sky Reader operationalizes fine-grained atomic claim evaluation directly within an interactive operational pipeline. Rather than relying on stochastic multi-sample variance (as in SelfCheckGPT) or self-prompted verification questions (as in CoVe)—both of which incur high latency and remain susceptible to model confirmation bias—Sky Reader's `ClaimExtractor` isolates numerical and categorical meteorological assertions, and passes them to a deterministic code-based auditor (`ClaimValidator`). As demonstrated in our benchmark, this deterministic separation reduces the hallucination rate from 35.9% in standard tool agents to 8.3% in Sky Reader ($p < 0.001$).

---

## 2.4 Explainable AI and Structured Evidence

The field of automated fact verification was largely standardized by the **FEVER** benchmark (Thorne et al., 2018), which framed verification as a three-way classification task (`SUPPORTS`, `REFUTES`, `NOT ENOUGH INFO`) requiring models to extract sentence-level evidence from Wikipedia. In high-stakes decision support, end users require more than a binary label; they require transparent, audit-ready explanations that explicitly link conclusions to observational premises.

**Relationship and Distinction to Sky Reader:**  
Sky Reader adapts the FEVER verification paradigm to real-time meteorological reasoning. Through its `ExplanationEngine`, Sky Reader constructs formal proof graphs that pair every factual conclusion with its supporting sensor observation, timestamp, measurement units, and physical tolerance window. By producing structured explanation proofs (which achieved a 97.4% structural validity rate in our benchmark), Sky Reader provides an audit trail suitable for operational decision makers.

---

## 2.5 AI-Assisted Weather Intelligence and Risk Assessment

Recent advances in artificial intelligence for meteorology have centered primarily on global numerical weather simulation. Deep learning models such as **GraphCast** (Lam et al., 2023) and **ClimaX** (Nguyen et al., 2023) have demonstrated remarkable skill in generating medium-range global forecasts, outperforming conventional operational Numerical Weather Prediction (NWP) systems (such as ECMWF's HRES) on standardized benchmarks like **WeatherBench 2** (Rasp et al., 2024).

However, raw forecasting models address the *simulation* problem—producing grid-scale physical state vectors—not the *communication and decision-support* problem. As documented by meteorological decision scientists (e.g., Morss et al., 2017), catastrophic outcomes during severe weather frequently arise not from numerical forecast errors, but from ambiguous, misleading, or poorly communicated risk assessments. When conventional LLMs are queried about severe weather, their tendency to underreport hazards or confuse probabilistic risk tiers poses direct public safety hazards.

**Relationship and Distinction to Sky Reader:**  
Sky Reader does not seek to replace NWP or AI-based atmospheric simulators like GraphCast. Instead, it occupies the complementary layer: an evidence-grounded agentic interface that ingests numerical weather forecasts, executes deterministic meteorological hazard checks (e.g., heat index thresholds, Beaufort scale wind categorizations, convective precipitation rates), and generates clear, un-hallucinated natural language intelligence and safety advisories.

---

## 2.6 Research Gap and Sky Reader's Contribution

While prior work has advanced tool use, retrieval augmentation, hallucination detection, and AI weather modeling independently, significant gaps persist at their intersection:
1. **The Tool-Agent Vulnerability Gap:** Tool augmentation provides LLMs with access to external weather data, but does not prevent the model from misreading numerical values, confusing units (such as treating precipitation millimeters as percentage probabilities), or inventing imaginary forecasts.
2. **The Decision Safety Gap:** In safety-critical weather scenarios, false negatives (underreporting severe risks) can be catastrophic. Conventional LLMs exhibit an unacceptably high rate of risk omission (100% in our zero-tool baseline) or dangerous severity underreporting (e.g., rating severe storms as "Low" hazard in unverified tool agents).
3. **The Multi-Unit Evaluation Gap:** Previous LLM benchmarks have evaluated numerical extraction using aggregate metrics (such as mixing Celsius degrees, millimeters, and kilometers per hour into a single MAE), obscuring variable-specific physical error dynamics.

**Sky Reader's Contribution:**  
This research presents the design, formalization, and audited empirical evaluation of an evidence-grounded agentic weather intelligence framework. By coupling frozen foundation models with deterministic claim extraction, symbolic constraint validation, and a meteorological risk assessment engine, Sky Reader demonstrates:
- A statistically significant reduction in hallucination rate ($35.9\% 	o 8.3\%$, $p < 0.001$).
- A significant improvement in risk classification accuracy ($27.3\% 	o 81.8\%$, nominal $p = 0.03125$).
- Zero false-negative underreports on high-impact weather hazards across the benchmark suite.
- A transparent documentation of the operational latency tax (28.2s vs. 19.4s) and reliability trade-offs required to enforce deterministic safety in agentic systems.
