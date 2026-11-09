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
    HallucinationReport,
    ValidationStatus,
    WeatherVariable,
)
from backend.evidence.explanation_engine import ExplanationEngine


def test_explanation_engine():
    print("Testing ExplanationEngine...")
    engine = ExplanationEngine()

    ev_temp = EvidenceItem(
        id="ev_obs_temp_current",
        variable=WeatherVariable.TEMPERATURE,
        value=22.5,
        unit="°C",
        location="Dehradun",
        time_period="current",
        source_type=EvidenceSourceType.OBSERVED,
        source_name="Open-Meteo Current Weather API",
    )
    ev_umb = EvidenceItem(
        id="ev_derived_umbrella",
        variable=WeatherVariable.UMBRELLA_NEED,
        value=False,
        unit="recommendation",
        location="Dehradun",
        time_period="forecast_period",
        source_type=EvidenceSourceType.DERIVED,
        source_name="Phase 3 Decision Support",
        analysis_method="Precipitation threshold evaluation",
    )

    evidence = EvidenceCollection(
        location_name="Dehradun",
        items=[ev_temp, ev_umb],
    )

    claim = FactualClaim(
        claim_id="c1",
        statement="Current temperature is 22.5 °C in Dehradun.",
        variable=WeatherVariable.TEMPERATURE,
        claimed_value=22.5,
        unit="°C",
        time_period="current",
        location="Dehradun",
        claim_type=ClaimType.NUMERICAL_VALUE,
    )

    val_result = ClaimValidationResult(
        claim=claim,
        status=ValidationStatus.SUPPORTED,
        confidence_score=1.0,
        supporting_evidence_ids=["ev_obs_temp_current"],
        evidence_values=[22.5],
        explanation="Exact match",
    )

    proof = engine.generate_proof(
        query="What is the temperature in Dehradun?",
        response_text="Current temperature is 22.5 °C in Dehradun. No umbrella is required today.",
        evidence=evidence,
        validation_results=[val_result],
    )

    assert proof.query == "What is the temperature in Dehradun?"
    assert "22.5" in proof.conclusion
    assert proof.hallucination_risk == "Low"
    assert "100% Grounded" in proof.claim_validation_status
    assert len(proof.supporting_evidence) > 0
    assert any(m["id"] == "ev_obs_temp_current" for m in proof.measurements_used)
    assert "Open-Meteo Current Weather API" in proof.data_sources

    # Check Markdown rendering
    md = engine.format_markdown_proof(proof)
    assert "Evidence & Meteorological Reasoning Proof" in md
    assert "Validation Status" in md
    assert "22.5 °C" in md

    print("  -> Passed ExplanationEngine unit tests.")


if __name__ == "__main__":
    test_explanation_engine()
