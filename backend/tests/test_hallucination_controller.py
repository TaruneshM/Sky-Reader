import asyncio
import sys
from pathlib import Path

# Ensure backend directory is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.evidence.evidence_models import (
    ClaimType,
    ClaimValidationResult,
    EvidenceCollection,
    EvidenceItem,
    EvidenceSourceType,
    FactualClaim,
    ValidationStatus,
    WeatherVariable,
)
from backend.evidence.hallucination_controller import HallucinationController


def test_hallucination_metrics():
    print("Testing HallucinationController metrics calculation...")
    controller = HallucinationController()

    c1 = FactualClaim(
        claim_id="c1",
        statement="Temp is 20°C",
        variable=WeatherVariable.TEMPERATURE,
        claimed_value=20.0,
    )
    c2 = FactualClaim(
        claim_id="c2",
        statement="Humidity is 50%",
        variable=WeatherVariable.HUMIDITY,
        claimed_value=50.0,
    )
    c3 = FactualClaim(
        claim_id="c3",
        statement="Wind is 100 km/h",
        variable=WeatherVariable.WIND_SPEED,
        claimed_value=100.0,
    )

    # 1. Clean results: 2 supported, 0 contradicted
    res_clean = [
        ClaimValidationResult(claim=c1, status=ValidationStatus.SUPPORTED, explanation="ok"),
        ClaimValidationResult(claim=c2, status=ValidationStatus.SUPPORTED, explanation="ok"),
    ]
    rep_clean = controller.evaluate_claims(res_clean)
    assert rep_clean.total_claims == 2
    assert rep_clean.supported_claims == 2
    assert rep_clean.contradicted_claims == 0
    assert rep_clean.hallucination_rate == 0.0
    assert rep_clean.is_trustworthy is True

    # 2. Results with a contradiction
    res_contra = [
        ClaimValidationResult(claim=c1, status=ValidationStatus.SUPPORTED, explanation="ok"),
        ClaimValidationResult(claim=c3, status=ValidationStatus.CONTRADICTED, explanation="too high"),
    ]
    rep_contra = controller.evaluate_claims(res_contra)
    assert rep_contra.total_claims == 2
    assert rep_contra.contradicted_claims == 1
    assert rep_contra.contradiction_rate == 0.5
    assert rep_contra.hallucination_rate == 0.5
    assert rep_contra.is_trustworthy is False
    assert len(rep_contra.problematic_claims) == 1

    print("  -> Passed metrics calculation tests.")


def test_correction_prompt_and_fallback():
    print("Testing HallucinationController correction prompt & fallback...")
    controller = HallucinationController()

    evidence = EvidenceCollection(
        location_name="Dehradun",
        items=[
            EvidenceItem(
                id="ev_obs_temp_current",
                variable=WeatherVariable.TEMPERATURE,
                value=22.5,
                unit="°C",
                time_period="current",
                source_type=EvidenceSourceType.OBSERVED,
                source_name="Open-Meteo Current Weather API",
            ),
            EvidenceItem(
                id="ev_obs_hum_current",
                variable=WeatherVariable.HUMIDITY,
                value=60.0,
                unit="%",
                time_period="current",
                source_type=EvidenceSourceType.OBSERVED,
                source_name="Open-Meteo Current Weather API",
            ),
        ]
    )

    c_bad = FactualClaim(
        claim_id="c_bad",
        statement="It is scorching hot at 42°C in Dehradun",
        variable=WeatherVariable.TEMPERATURE,
        claimed_value=42.0,
        unit="°C",
    )
    val_res = [
        ClaimValidationResult(
            claim=c_bad,
            status=ValidationStatus.CONTRADICTED,
            explanation="Claimed 42°C contradicts 22.5°C",
        )
    ]
    report = controller.evaluate_claims(val_res)

    prompt = controller.generate_correction_prompt(report, "What is the temperature in Dehradun?", evidence)
    assert "failed meteorological verification" in prompt
    assert "42.0" in prompt
    assert "22.5" in prompt

    fallback = controller.generate_safe_fallback("What is the temperature in Dehradun?", evidence, report)
    assert "22.5 °C" in fallback
    assert "Dehradun" in fallback
    assert "automated audit identified discrepancies" in fallback

    print("  -> Passed correction prompt & fallback tests.")


def test_verify_and_correct_loop():
    print("Testing HallucinationController verify_and_correct feedback loop...")
    controller = HallucinationController()

    evidence = EvidenceCollection(
        location_name="Dehradun",
        items=[
            EvidenceItem(
                id="ev_obs_temp_current",
                variable=WeatherVariable.TEMPERATURE,
                value=22.5,
                unit="°C",
                time_period="current",
                source_type=EvidenceSourceType.OBSERVED,
                source_name="Open-Meteo Current Weather API",
            ),
        ]
    )

    # Scenario A: Hallucinates at first, corrects on 1st retry
    hallucinated_text = "The current temperature in Dehradun is 35.0 °C."
    corrected_text = "Apologies, the current temperature in Dehradun is actually 22.5 °C."

    async def mock_agent_success(prompt: str):
        return corrected_text

    final_text, final_report, attempts = asyncio.run(
        controller.verify_and_correct(
            query="What is the temperature?",
            response_text=hallucinated_text,
            evidence=evidence,
            regenerate_fn=mock_agent_success,
            max_retries=2,
        )
    )

    assert attempts == 1
    assert "22.5 °C" in final_text
    assert final_report.is_trustworthy is True
    assert final_report.contradicted_claims == 0

    # Scenario B: Stubbornly hallucinates through all retries -> triggers fallback
    async def mock_agent_failure(prompt: str):
        return "It is definitely 50.0 °C in Dehradun."

    fallback_text, fallback_report, attempts_f = asyncio.run(
        controller.verify_and_correct(
            query="What is the temperature?",
            response_text=hallucinated_text,
            evidence=evidence,
            regenerate_fn=mock_agent_failure,
            max_retries=2,
        )
    )

    assert attempts_f == 2
    assert "automated audit identified discrepancies" in fallback_text
    assert "22.5 °C" in fallback_text
    assert fallback_report.is_trustworthy is True

    print("  -> Passed verify_and_correct loop tests.")


if __name__ == "__main__":
    test_hallucination_metrics()
    test_correction_prompt_and_fallback()
    test_verify_and_correct_loop()
