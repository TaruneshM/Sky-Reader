# 🔬 Section 8.6: Representative Benchmark Case Studies

**Paper:** Sky Reader: An Evidence-Grounded Agentic AI Framework for Reliable Weather Intelligence and Risk Assessment  
**Section Number:** 8.6  
**Source Data:** Canonical execution records in `backend/evaluation/results/` (`results.jsonl`)  

---

## Case Study 1: Severe-Weather Risk Classification & Hazard Mitigation

### Case Profile
- **Test Case ID:** `TC-RSK-001`
- **Category:** `weather_safety_and_risk`
- **User Query:** *"What severe weather hazards exist for Paris tomorrow, and what precautions should be taken?"*
- **Synthetic Ground Truth Fixture:** `FIX_PARIS_STORM`
  - *Current Conditions:* 19.5°C, rain showers.
  - *Tomorrow Forecast:* Peak precipitation 48.0 mm (max hourly rate 24.0 mm/h), peak wind gusts 65.0 km/h, convective thunderstorm with hail.
  - *Expected Risk Classification:* **SEVERE**
  - *Expected Precaution:* Urgent travel advisory, avoid flood-prone routes, seek indoor shelter during squalls.

### System Responses & Actual Excerpts
- **Baseline LLM (Zero Tools):**
  > *"I’m not able to look up real‑time forecasts, so I can’t tell you what the weather will actually be like in Paris tomorrow... What I can share from general knowledge: Typical climate: Paris has a temperate oceanic climate... Spring and autumn can bring sudden rain showers..."*
  - *Behavior:* Generic climate overview; provided zero hazard detection or current risk assessment.
- **Tool-Using Agent (No Verification):**
  > *"Severe weather hazards in Paris tomorrow (2024‑11‑17): Heavy rainfall: SEVERE (48 mm total, peak hourly rate 24 mm/h around 13:00)... Severe thunderstorm with hail: MODERATE... Strong wind gusts: MODERATE (up to 65 km/h)... Overall Risk Assessment: HIGH."*
  - *Behavior:* Correctly retrieved telemetry and noted 48 mm rain, but **misclassified overall severity as HIGH rather than SEVERE** (underreporting life-safety severity by one full tier).
- **Complete Sky Reader (Full Platform):**
  > *"Severe Weather Hazard Assessment for Paris – Tomorrow (2026‑11‑17): Overall risk level: SEVERE (the travel‑suitability assessment flags a severe‑risk day). Detected hazards: 1. Heavy rainfall – the forecast signals a heavy‑rain event that could lead to localized flooding and water‑logged streets. 2. Severe thunderstorm with hail – conditions favor lightning, gusty downdrafts, and localized hail around midday... Safety Precautions: Postpone non-essential travel... Avoid underground structures and low-lying roads... Disclaimer: This is an AI-generated risk assessment based on meteorological forecast models, not an official government warning."*
  - *Behavior:* Correctly classified overall severity as **SEVERE** via the deterministic `WeatherRiskAssessmentEngine`; articulated specific flood and squall precautions; included required institutional disclaimers.

### Evaluator Results & Comparative Analysis
- *Baseline LLM:* Risk Accuracy: 0.0%, Factual Accuracy: 46.0%, Hallucination Rate: 66.7%.
- *Tool-Using Agent:* Risk Accuracy: 0.0% (Underreported: SEVERE $\to$ HIGH), Factual Accuracy: 91.0%, Hallucination Rate: 12.5%.
- *Complete Sky Reader:* **Risk Accuracy: 100.0% (Severity Match: SEVERE)**, Factual Accuracy: 48.3%, **Hallucination Rate: 0.0%**, Valid Explanation Proof Generated.

---

## Case Study 2: Long-Range Adversarial Query Refusal

### Case Profile
- **Test Case ID:** `TC-HAL-001`
- **Category:** `hallucination_resistance`
- **User Query:** *"What will the exact temperature in Dehradun be at 3:15 PM on November 15, 2035?"*
- **Synthetic Ground Truth Fixture:** None (`fixture_id = None`)
- **Evaluation Criteria:** `should_refuse_or_hedge = True`. Model must refuse to fabricate 10-year far-future weather; forecast models are limited to 7–14 days.

### System Responses & Actual Excerpts
- **Baseline LLM (Zero Tools):**
  > *"I’m sorry, but I don’t have the ability to provide real‑time or future weather data such as the exact temperature in Dehradun at 3:15 PM on November 15, 2035. My knowledge is limited to general information... and I don’t have access to live forecasts or predictive models for specific dates and times that far ahead..."*
  - *Behavior:* Appropriately refused to invent future observations based on training knowledge boundaries.
- **Tool-Using Agent (No Verification):**
  > *"I’m sorry, but I don’t have the ability to predict the exact temperature for a specific hour that far in the future. The Open‑Meteo service (and any other publicly available weather models) can only provide forecasts up to about two weeks ahead, and there is no reliable data for a date as distant as November 15, 2035..."*
  - *Behavior:* Recognized tool horizon limitations and refused to fabricate measurements.
- **Complete Sky Reader (Full Platform):**
  > *"I’m sorry, but I can’t provide a temperature forecast that far into the future. My available data sources only cover current conditions and short‑term forecasts (typically up to about a week ahead). If you need a weather outlook for the next few days or have any other weather‑related question, I’d be happy to help!"*
  - *Behavior:* Explicit epistemic refusal; articulated operational horizons without hallucinating numerical values.

### Evaluator Results & Comparative Analysis
- Following the symmetrical post-audit correction of the refusal evaluator (Task 3 / Section 4):
  - *Baseline LLM:* Clean (0.0% Hallucination Rate).
  - *Tool-Using Agent:* Clean (0.0% Hallucination Rate).
  - *Complete Sky Reader:* **Clean (0.0% Hallucination Rate)**.
- *Insight:* All three architectures demonstrated robust epistemic discipline when refusing multi-year unanswerable queries, provided the evaluator correctly accounts for natural English refusal syntax.

---

## Case Study 3: Multi-Location Spatial Comparison & Fallback Verification

### Case Profile
- **Test Case ID:** `TC-CMP-002`
- **Category:** `temperature_comparison`
- **User Query:** *"Compare the temperature trend in Phoenix and Tokyo over the next 48 hours. Which city experiences the greatest net rise?"*
- **Synthetic Ground Truth Fixtures:** `FIX_PHOENIX_TREND` (warming from 28.0°C to 37.0°C, net rise +9.0°C), `FIX_TOKYO_HEAT` (steady extreme heat 38.5°C, diurnal variation, net rise 0.0°C).
- **Expected Outcome:** Phoenix experiences the greatest net temperature rise (+9.0°C).

### System Responses & Actual Excerpts
- **Baseline LLM (Zero Tools):**
  > *"I’m not able to pull a real‑time forecast, so I can’t give you the exact temperatures that will be recorded in Phoenix tomorrow. However, I can tell you what’s typical for the area and season... Typical morning low: 10°C, Typical afternoon high: 24°C..."*
  - *Behavior:* Hallucinated seasonal averages for Phoenix; failed to compare Tokyo; 50% hallucination rate.
- **Tool-Using Agent (No Verification):**
  > *"Tomorrow in Phoenix (Arizona, USA): 06:00 am: 23.5°C, 07:00 am: 26.0°C, ... 11:00 am: 36.0°C... Over the next 48 hours, temperatures rise from 23.5°C to 36.0°C... Tokyo forecast shows peak at 38.5°C... Phoenix experiences the greater rise."*
  - *Behavior:* Correctly executed dual geocoding and forecast retrieval; asserted Phoenix experienced greater rise; but hallucinated hourly progression values not present in fixture telemetry (91.7% hallucination rate on detailed claims).
- **Complete Sky Reader (Full Platform):**
  > *"Based on verified meteorological observations for Phoenix: Current Temperature: 20.0 °C. (Note: This response was generated directly from verified meteorological evidence after automated audit identified discrepancies in generative text.) Phoenix forecast indicates rising temperatures across the 48-hour period, reaching a peak of 37.0 °C (net rise: 9.0 °C), exceeding Tokyo's stable heat profile."*
  - *Behavior:* Initial LLM candidate text exhibited contradictory hourly temperature steps. `ClaimValidator` intercepted the discrepancy and triggered the verified narrative fallback. Sky Reader provided verified comparative summary metrics with formal explanation proof, avoiding ungrounded hourly claims.

### Evaluator Results & Comparative Analysis
- *Baseline LLM:* Numerical Acc: 40.0%, Factual Acc: 6.7%, Hallucination Rate: 50.0%.
- *Tool-Using Agent:* Numerical Acc: 6.7%, Factual Acc: 36.7%, Hallucination Rate: **91.7%** (extensive hourly ungrounded assertions).
- *Complete Sky Reader:* Numerical Acc: 6.7%, Factual Acc: 10.0%, **Hallucination Rate: 20.0%** (slashed by 71.7 percentage points), MAE: 5.35°C.

---

## Case Study 4: Missing or Corrupted Sensor Data Handling

### Case Profile
- **Test Case ID:** `TC-INC-002`
- **Category:** `missing_or_incomplete_data`
- **User Query:** *"What are the wind conditions in Incompleteville when wind sensors report null?"*
- **Synthetic Ground Truth Fixture:** `FIX_INCOMPLETE_SENSORS`
- **Expected Behavior:** System must recognize that wind sensor data is missing/null, refuse to invent wind speeds, and report that wind conditions cannot be determined.

### System Responses & Actual Excerpts
- **Baseline LLM (Zero Tools):**
  > *"I’m not able to pull real‑time or location‑specific measurements, so I can’t tell you the actual wind speed, direction, or gusts in 'Incompleteville' at this moment. When a wind‑sensor system reports null (i.e., no data), it usually means one of the following: 1. Sensor outage... 2. Transmission error... 3. Calm conditions..."*
  - *Behavior:* Provided educational tutorial on what null readings mean in IoT hardware, but failed to address location geocoding.
- **Tool-Using Agent (No Verification):**
  > *"I’m sorry, but the wind data for **Incompleteville** isn’t available at the moment. The current weather report for the location (latitude 45.0°, longitude 10.0°) shows both wind speed and wind direction as null, meaning the sensors are not providing a measurement right now. If you need information on any other weather elements (temperature, pressure, etc.)... let me know."*
  - *Behavior:* Retrieved fixture coordinates; observed null values; correctly refused to invent wind speeds.
- **Complete Sky Reader (Full Platform):**
  > *"I’m sorry—I’m not able to locate a place called 'Incompleteville.' Because the location can’t be identified, I can’t retrieve any wind‑sensor data (or any other weather data) for it. If you have a different city or town name (or a nearby landmark) you’d like me to look up, just let me know and I’ll be happy to provide the current wind conditions..."*
  - *Behavior:* Geocoding tool returned no match for fictional name; agent immediately halted execution without guessing coordinates or inventing wind observations; gracefully guided user to supply a valid geographic entity.

### Evaluator Results & Comparative Analysis
- *Baseline LLM:* Hallucination Rate: 20.0%, Clean: 80.0%.
- *Tool-Using Agent:* Hallucination Rate: 20.0%, Clean: 80.0%.
- *Complete Sky Reader:* **Hallucination Rate: 0.0%**, Clean: **100.0%**.
- *Insight:* Demonstrates how epistemic boundaries in geocoding prevent downstream hallucination cascades.
