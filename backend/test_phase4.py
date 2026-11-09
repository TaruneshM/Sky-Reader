import asyncio
import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.evidence.evidence_models import (
    ClaimType,
    EvidenceCollection,
    EvidenceItem,
    EvidenceSourceType,
    FactualClaim,
    ValidationStatus,
    WeatherVariable,
)
from backend.evidence.evidence_engine import EvidenceEngine
from backend.evidence.claim_extractor import ClaimExtractor
from backend.evidence.claim_validator import ClaimValidator
from backend.evidence.hallucination_controller import HallucinationController
from backend.evidence.explanation_engine import ExplanationEngine
from backend.agent.agent import run_agent
from backend.main import app


def test_evidence_engine():
    print("\n" + "=" * 60)
    print("PHASE 4 TEST 1: Evidence Generation & Provenance Tracking")
    print("=" * 60)
    engine = EvidenceEngine()

    mock_current = {
        "time": "2026-11-09T16:00",
        "temperature_2m": 22.5,
        "apparent_temperature": 24.0,
        "relative_humidity_2m": 65.0,
        "wind_speed_10m": 12.0,
        "wind_direction_10m": 90.0,
        "surface_pressure": 945.0,
        "cloud_cover": 20.0,
        "weather_code": 0,
    }

    mock_hourly = {
        "time": [f"2026-11-09T{h:02d}:00" for h in range(12)],
        "temperature_2m": [15.0 + h for h in range(12)],
        "relative_humidity_2m": [60.0 for _ in range(12)],
        "precipitation_probability": [0.0 if h < 6 else 40.0 for h in range(12)],
        "precipitation": [0.0 for _ in range(12)],
        "wind_speed_10m": [10.0 for _ in range(12)],
        "weather_code": [0 for _ in range(12)],
    }

    mock_location = {"name": "Dehradun", "latitude": 30.32, "longitude": 78.03}

    collection = engine.generate_evidence(
        current_data={"current": mock_current},
        hourly_data={"hourly": mock_hourly},
        location_meta=mock_location,
    )

    assert collection.location_name == "Dehradun"
    assert len(collection.items) > 0

    # Verify Provenance Types
    obs_items = [it for it in collection.items if it.source_type == EvidenceSourceType.OBSERVED]
    fc_items = [it for it in collection.items if it.source_type == EvidenceSourceType.FORECAST]
    der_items = [it for it in collection.items if it.source_type == EvidenceSourceType.DERIVED]

    assert len(obs_items) >= 5, "Must have observed current items"
    assert len(fc_items) >= 12, "Must have forecast hourly items"
    assert len(der_items) >= 1, "Must have derived analytical items"

    print(f"  -> Generated {len(collection.items)} structured evidence items:")
    print(f"     Observed: {len(obs_items)} | Forecast: {len(fc_items)} | Derived: {len(der_items)}")
    print(">>> PHASE 4 TEST 1 PASSED: Evidence engine generated valid provenance-tracked records.")
    return True


def test_claim_extraction():
    print("\n" + "=" * 60)
    print("PHASE 4 TEST 2: Deterministic Claim Extraction")
    print("=" * 60)
    extractor = ClaimExtractor()

    text = (
        "The current temperature in Dehradun is 22.5 °C with a feels-like temperature of 24.0°C. "
        "There is a 40% chance of rain in the afternoon with 2.5 mm expected precipitation. "
        "Wind speed is 12 km/h and relative humidity is 65%. "
        "Temperatures are increasing throughout the day. "
        "You do not need an umbrella today. "
        "Have a great day ahead!"
    )

    claims = extractor.extract_claims(text, default_location="Dehradun")
    print(f"  -> Extracted {len(claims)} verifiable factual claims from response text.")
    for c in claims:
        print(f"     [{c.variable.value}]: claimed '{c.claimed_value}' ({c.unit or ''}) type={c.claim_type.value}")

    variables_found = {c.variable for c in claims}
    assert WeatherVariable.TEMPERATURE in variables_found
    assert WeatherVariable.APPARENT_TEMPERATURE in variables_found
    assert WeatherVariable.PRECIPITATION_PROBABILITY in variables_found
    assert WeatherVariable.PRECIPITATION_AMOUNT in variables_found
    assert WeatherVariable.WIND_SPEED in variables_found
    assert WeatherVariable.HUMIDITY in variables_found
    assert WeatherVariable.TEMPERATURE_TREND in variables_found
    assert WeatherVariable.UMBRELLA_NEED in variables_found

    # Pleasantry check: 'Have a great day ahead!' should not produce any false claims
    assert not any("great day" in c.statement.lower() for c in claims)

    print(">>> PHASE 4 TEST 2 PASSED: Claim extractor accurately parsed all weather claims.")
    return True


def test_claim_validation():
    print("\n" + "=" * 60)
    print("PHASE 4 TEST 3: Deterministic Claim Validation with Domain Tolerances")
    print("=" * 60)
    validator = ClaimValidator()

    evidence = EvidenceCollection(
        location_name="Dehradun",
        items=[
            EvidenceItem(
                id="ev_temp",
                variable=WeatherVariable.TEMPERATURE,
                value=22.5,
                unit="°C",
                time_period="current",
                source_type=EvidenceSourceType.OBSERVED,
                source_name="Open-Meteo Current Weather",
            ),
            EvidenceItem(
                id="ev_rain_prob",
                variable=WeatherVariable.PRECIPITATION_PROBABILITY,
                value=40.0,
                unit="%",
                time_period="afternoon",
                source_type=EvidenceSourceType.FORECAST,
                source_name="Open-Meteo Hourly Forecast",
            ),
            EvidenceItem(
                id="ev_trend",
                variable=WeatherVariable.TEMPERATURE_TREND,
                value="increasing",
                unit="trend",
                time_period="afternoon",
                source_type=EvidenceSourceType.DERIVED,
                source_name="Phase 3 Temperature Analysis",
            ),
        ]
    )

    # 1. Supported (Exact)
    c1 = FactualClaim(claim_id="c1", statement="Temp is 22.5°C", variable=WeatherVariable.TEMPERATURE, claimed_value=22.5, unit="°C", time_period="current")
    # 2. Supported (Within tolerance ±1.0°C)
    c2 = FactualClaim(claim_id="c2", statement="Temp is 23.0°C", variable=WeatherVariable.TEMPERATURE, claimed_value=23.0, unit="°C", time_period="current")
    # 3. Contradicted (Numerical)
    c3 = FactualClaim(claim_id="c3", statement="Temp is 35.0°C", variable=WeatherVariable.TEMPERATURE, claimed_value=35.0, unit="°C", time_period="current")
    # 4. Contradicted (Trend reversal)
    c4 = FactualClaim(claim_id="c4", statement="Temp is decreasing", variable=WeatherVariable.TEMPERATURE_TREND, claimed_value="decreasing", unit="trend", time_period="afternoon")
    # 5. Insufficient Evidence
    c5 = FactualClaim(claim_id="c5", statement="Pressure is 1013 hPa", variable=WeatherVariable.PRESSURE, claimed_value=1013.0, unit="hPa", time_period="current")

    results = validator.validate_all([c1, c2, c3, c4, c5], evidence)
    assert results[0].status == ValidationStatus.SUPPORTED
    assert results[1].status == ValidationStatus.SUPPORTED
    assert results[2].status == ValidationStatus.CONTRADICTED
    assert results[3].status == ValidationStatus.CONTRADICTED
    assert results[4].status == ValidationStatus.INSUFFICIENT_EVIDENCE

    print("  -> Claim 1 (22.5°C vs 22.5°C):", results[0].status.value)
    print("  -> Claim 2 (23.0°C vs 22.5°C within ±1.0):", results[1].status.value)
    print("  -> Claim 3 (35.0°C vs 22.5°C):", results[2].status.value)
    print("  -> Claim 4 (decreasing vs increasing):", results[3].status.value)
    print("  -> Claim 5 (Pressure missing):", results[4].status.value)

    print(">>> PHASE 4 TEST 3 PASSED: Claim validator correctly assigned verification statuses.")
    return True


async def test_hallucination_controller():
    print("\n" + "=" * 60)
    print("PHASE 4 TEST 4: Hallucination Controller & Regeneration Loop")
    print("=" * 60)
    controller = HallucinationController()

    evidence = EvidenceCollection(
        location_name="Dehradun",
        items=[
            EvidenceItem(
                id="ev_temp",
                variable=WeatherVariable.TEMPERATURE,
                value=22.5,
                unit="°C",
                time_period="current",
                source_type=EvidenceSourceType.OBSERVED,
                source_name="Open-Meteo Current Weather",
            ),
        ]
    )

    # Simulate an agent response that hallucinates
    hallucinated = "The current temperature in Dehradun is 36.0 °C."

    # Mock regeneration function that corrects on retry
    async def mock_correction_fn(prompt: str):
        assert "36.0" in prompt
        assert "22.5" in prompt
        return "Apologies. The current temperature in Dehradun is 22.5 °C."

    final_text, report, retries = await controller.verify_and_correct(
        query="What is the temperature in Dehradun?",
        response_text=hallucinated,
        evidence=evidence,
        regenerate_fn=mock_correction_fn,
        max_retries=1,
    )

    assert retries == 1
    assert "22.5 °C" in final_text
    assert report.is_trustworthy is True
    assert report.contradicted_claims == 0
    print(f"  -> Successfully caught hallucination and corrected response on retry {retries}.")
    print(f"  -> Final Text: {final_text}")
    print(f"  -> Hallucination Rate: {report.hallucination_rate} | Is Trustworthy: {report.is_trustworthy}")

    print(">>> PHASE 4 TEST 4 PASSED: Hallucination feedback loop detected and corrected errors.")
    return True


def test_explanation_engine():
    print("\n" + "=" * 60)
    print("PHASE 4 TEST 5: Weather Reasoning & Explanation Proof Generation")
    print("=" * 60)
    engine = ExplanationEngine()

    evidence = EvidenceCollection(
        location_name="Dehradun",
        items=[
            EvidenceItem(
                id="ev_temp",
                variable=WeatherVariable.TEMPERATURE,
                value=22.5,
                unit="°C",
                time_period="current",
                source_type=EvidenceSourceType.OBSERVED,
                source_name="Open-Meteo Current Weather",
            ),
            EvidenceItem(
                id="ev_umb",
                variable=WeatherVariable.UMBRELLA_NEED,
                value=False,
                unit="recommendation",
                time_period="current",
                source_type=EvidenceSourceType.DERIVED,
                source_name="Phase 3 Decision Support",
                analysis_method="Precipitation threshold evaluation",
            ),
        ]
    )

    proof = engine.generate_proof(
        query="Do I need an umbrella in Dehradun?",
        response_text="Current temperature is 22.5 °C. You do not need an umbrella today.",
        evidence=evidence,
    )

    assert proof.query == "Do I need an umbrella in Dehradun?"
    assert proof.hallucination_risk in ("Low", "None / Low")
    assert len(proof.supporting_evidence) > 0
    assert "Open-Meteo Current Weather" in proof.data_sources

    md = engine.format_markdown_proof(proof)
    assert "Evidence & Meteorological Reasoning Proof" in md
    assert "Key Supporting Measurements" in md

    print("  -> Generated ExplanationProof:")
    print(f"     Risk: {proof.hallucination_risk}")
    print(f"     Status: {proof.claim_validation_status}")
    print(f"     Sources: {proof.data_sources}")

    print(">>> PHASE 4 TEST 5 PASSED: Explanation engine produced structured provenance proofs.")
    return True


def test_fastapi_evidence_endpoints():
    print("\n" + "=" * 60)
    print("PHASE 4 TEST 6: FastAPI Evidence & Validation Endpoints")
    print("=" * 60)
    from unittest.mock import patch

    client = TestClient(app)

    mock_place = {"name": "Dehradun", "latitude": 30.32, "longitude": 78.03, "country": "India", "region": "Uttarakhand"}
    mock_current = {
        "current": {
            "time": "2026-11-09T16:00",
            "temperature_2m": 22.0,
            "apparent_temperature": 23.0,
            "relative_humidity_2m": 60.0,
            "wind_speed_10m": 10.0,
            "wind_direction_10m": 90.0,
            "surface_pressure": 950.0,
            "cloud_cover": 20.0,
            "weather_code": 0,
        }
    }
    mock_hourly = {
        "hourly": {
            "time": [f"2026-11-09T{h:02d}:00" for h in range(24)],
            "temperature_2m": [18.0 + (h * 0.5) for h in range(24)],
            "relative_humidity_2m": [60.0 for _ in range(24)],
            "precipitation_probability": [0.0 for _ in range(24)],
            "precipitation": [0.0 for _ in range(24)],
            "wind_speed_10m": [10.0 for _ in range(24)],
            "weather_code": [0 for _ in range(24)],
        }
    }

    # Patch weather service for offline/sandboxed verification
    with patch("backend.main.geocode_location", return_value=mock_place), \
         patch("backend.main.get_current_weather", return_value=mock_current), \
         patch("backend.main.get_hourly_forecast", return_value=mock_hourly):

        # 1. Test /api/evidence/summary
        res_summary = client.get("/api/evidence/summary?location=Dehradun")
        assert res_summary.status_code == 200, f"Expected 200, got {res_summary.status_code}"
        data_summary = res_summary.json()
        assert "evidence_summary" in data_summary
        assert "items" in data_summary
        assert data_summary["evidence_count"] > 0
        print(f"  -> /api/evidence/summary returned {data_summary['evidence_count']} evidence records.")

        # 2. Test /api/evidence/validate
        validate_payload = {
            "location": "Dehradun",
            "text": "The temperature is 22.0 °C and humidity is 60%.",
        }
        res_val = client.post("/api/evidence/validate", json=validate_payload)
        assert res_val.status_code == 200, f"Expected 200, got {res_val.status_code}"
        data_val = res_val.json()
        assert "claims" in data_val
        assert "validation_results" in data_val
        assert "hallucination_report" in data_val
        assert "explanation_proof" in data_val
        print(f"  -> /api/evidence/validate extracted {len(data_val['claims'])} claims.")
        print(f"  -> Hallucination report trustworthy: {data_val['hallucination_report']['is_trustworthy']}")

    print(">>> PHASE 4 TEST 6 PASSED: FastAPI evidence endpoints operational.")
    return True


async def test_agent_phase4_end_to_end():
    print("\n" + "=" * 60)
    print("PHASE 4 TEST 7: End-to-End Agent with Evidence, Validation & Explanation")
    print("=" * 60)
    query = "What is the current temperature in Dehradun?"

    try:
        result = await run_agent(query)
    except Exception as net_err:
        print(f"  (Live network unavailable in environment: {net_err}. Testing end-to-end pipeline with mock tools)")
        from unittest.mock import patch, AsyncMock

        mock_place = {"name": "Dehradun", "latitude": 30.32, "longitude": 78.03, "country": "India", "region": "Uttarakhand"}
        mock_current = {
            "current": {
                "time": "2026-11-09T16:00",
                "temperature_2m": 22.5,
                "apparent_temperature": 24.0,
                "relative_humidity_2m": 65.0,
                "wind_speed_10m": 12.0,
                "weather_code": 0,
            }
        }

        # Mock Groq tool call loop
        mock_tool_call_1 = AsyncMock()
        mock_tool_call_1.id = "call_1"
        mock_tool_call_1.function.name = "geocode_location"
        mock_tool_call_1.function.arguments = '{"location": "Dehradun"}'

        mock_tool_call_2 = AsyncMock()
        mock_tool_call_2.id = "call_2"
        mock_tool_call_2.function.name = "get_current_weather"
        mock_tool_call_2.function.arguments = '{"latitude": 30.32, "longitude": 78.03}'

        msg_tool_1 = AsyncMock()
        msg_tool_1.content = None
        msg_tool_1.tool_calls = [mock_tool_call_1, mock_tool_call_2]

        msg_final = AsyncMock()
        msg_final.content = "The current temperature in Dehradun is 22.5 °C with 65% humidity."
        msg_final.tool_calls = None

        mock_choice_1 = AsyncMock()
        mock_choice_1.message = msg_tool_1
        mock_resp_1 = AsyncMock()
        mock_resp_1.choices = [mock_choice_1]

        mock_choice_2 = AsyncMock()
        mock_choice_2.message = msg_final
        mock_resp_2 = AsyncMock()
        mock_resp_2.choices = [mock_choice_2]

        with patch("backend.agent.agent.execute_tool", side_effect=[mock_place, mock_current]), \
             patch("backend.agent.agent.get_groq_client") as mock_client_factory:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(side_effect=[mock_resp_1, mock_resp_2])
            mock_client_factory.return_value = mock_client
            result = await run_agent(query)

    print(f"Query: {query}")
    print(f"Response:\n{result['response']}\n")
    print(f"Tools Executed: {[tc['tool'] for tc in result.get('tool_calls', [])]}")
    print(f"Claims Extracted: {len(result.get('claims', []))}")

    assert "response" in result
    assert "tool_calls" in result
    assert "claims" in result
    assert "validation_report" in result
    assert "explanation" in result

    report = result["validation_report"]
    if report:
        print(f"Validation Report:")
        print(f"  Total Claims: {report.get('total_claims')}")
        print(f"  Supported: {report.get('supported_claims')}")
        print(f"  Contradicted: {report.get('contradicted_claims')}")
        print(f"  Is Trustworthy: {report.get('is_trustworthy')}")
        assert report.get("is_trustworthy") is True, "Response should be verified as trustworthy"

    explanation = result["explanation"]
    if explanation:
        print(f"Explanation Proof:")
        print(f"  Status: {explanation.get('claim_validation_status')}")
        print(f"  Risk: {explanation.get('hallucination_risk')}")
        print(f"  Sources: {explanation.get('data_sources')}")

    print(">>> PHASE 4 TEST 7 PASSED: Agent produced evidence-backed, validated answer.")
    return True


async def run_all_phase4_tests():
    print("\n" + "#" * 60)
    print("STARTING SKY READER PHASE 4 INTEGRATION TEST SUITE")
    print("#" * 60)

    results = {}

    try:
        results["Evidence Engine"] = test_evidence_engine()
    except Exception as e:
        print(f"TEST 1 FAILED: {e}")
        results["Evidence Engine"] = False

    try:
        results["Claim Extraction"] = test_claim_extraction()
    except Exception as e:
        print(f"TEST 2 FAILED: {e}")
        results["Claim Extraction"] = False

    try:
        results["Claim Validation"] = test_claim_validation()
    except Exception as e:
        print(f"TEST 3 FAILED: {e}")
        results["Claim Validation"] = False

    try:
        results["Hallucination Controller"] = await test_hallucination_controller()
    except Exception as e:
        print(f"TEST 4 FAILED: {e}")
        results["Hallucination Controller"] = False

    try:
        results["Explanation Engine"] = test_explanation_engine()
    except Exception as e:
        print(f"TEST 5 FAILED: {e}")
        results["Explanation Engine"] = False

    try:
        results["FastAPI Endpoints"] = test_fastapi_evidence_endpoints()
    except Exception as e:
        print(f"TEST 6 FAILED: {e}")
        results["FastAPI Endpoints"] = False

    try:
        results["Agent End-to-End"] = await test_agent_phase4_end_to_end()
    except Exception as e:
        print(f"TEST 7 FAILED: {e}")
        results["Agent End-to-End"] = False

    print("\n" + "=" * 60)
    print("PHASE 4 TEST SUMMARY:")
    all_passed = True
    for name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"  [{status}] {name}")
        if not passed:
            all_passed = False
    print("=" * 60)

    if all_passed:
        print("\nALL PHASE 4 TESTS COMPLETED SUCCESSFULLY!\n")
    else:
        print("\nSOME PHASE 4 TESTS FAILED!\n")
    return all_passed


if __name__ == "__main__":
    asyncio.run(run_all_phase4_tests())
