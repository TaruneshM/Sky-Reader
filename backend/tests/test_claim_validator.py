import sys
from pathlib import Path

# Ensure backend directory is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.evidence.evidence_models import (
    ClaimType,
    EvidenceCollection,
    EvidenceItem,
    EvidenceSourceType,
    FactualClaim,
    ValidationStatus,
    WeatherVariable,
)
from backend.evidence.claim_validator import ClaimValidator


def test_claim_validator():
    print("Testing ClaimValidator...")
    validator = ClaimValidator()

    # Build a mock EvidenceCollection
    evidence = EvidenceCollection(
        location_name="Dehradun",
        items=[
            EvidenceItem(
                id="ev_obs_temp_current",
                variable=WeatherVariable.TEMPERATURE,
                value=22.5,
                unit="°C",
                location="Dehradun",
                time_period="current",
                source_type=EvidenceSourceType.OBSERVED,
                source_name="Open-Meteo Current Weather API",
            ),
            EvidenceItem(
                id="ev_obs_humidity_current",
                variable=WeatherVariable.HUMIDITY,
                value=65.0,
                unit="%",
                location="Dehradun",
                time_period="current",
                source_type=EvidenceSourceType.OBSERVED,
                source_name="Open-Meteo Current Weather API",
            ),
            EvidenceItem(
                id="ev_derived_temp_trend",
                variable=WeatherVariable.TEMPERATURE_TREND,
                value="decreasing",
                unit="trend",
                location="Dehradun",
                time_period="next_24h",
                source_type=EvidenceSourceType.DERIVED,
                source_name="Phase 3 Temperature Analysis",
            ),
            EvidenceItem(
                id="ev_derived_umbrella",
                variable=WeatherVariable.UMBRELLA_NEED,
                value=False,
                unit="recommendation",
                location="Dehradun",
                time_period="forecast_period",
                source_type=EvidenceSourceType.DERIVED,
                source_name="Phase 3 Decision Support",
            ),
        ]
    )

    # 1. Exact / within tolerance -> SUPPORTED
    claim_supported = FactualClaim(
        claim_id="c1",
        statement="Current temperature is 22.5°C",
        variable=WeatherVariable.TEMPERATURE,
        claimed_value=22.5,
        unit="°C",
        time_period="current",
        location="Dehradun",
        claim_type=ClaimType.NUMERICAL_VALUE,
    )
    res_1 = validator.validate_claim(claim_supported, evidence)
    assert res_1.status == ValidationStatus.SUPPORTED
    assert "ev_obs_temp_current" in res_1.supporting_evidence_ids
    assert res_1.confidence_score >= 0.95

    # 2. Within tolerance rounding (e.g. 23.0 vs 22.5, diff 0.5 <= 1.0) -> SUPPORTED
    claim_rounded = FactualClaim(
        claim_id="c2",
        statement="Current temperature is around 23°C",
        variable=WeatherVariable.TEMPERATURE,
        claimed_value=23.0,
        unit="°C",
        time_period="current",
        location="Dehradun",
        claim_type=ClaimType.NUMERICAL_VALUE,
    )
    res_2 = validator.validate_claim(claim_rounded, evidence)
    assert res_2.status == ValidationStatus.SUPPORTED

    # 3. Partially supported (e.g. 24.0 vs 22.5, diff 1.5 > 1.0 and <= 2.0) -> PARTIALLY_SUPPORTED
    claim_partial = FactualClaim(
        claim_id="c3",
        statement="Current temperature is 24°C",
        variable=WeatherVariable.TEMPERATURE,
        claimed_value=24.0,
        unit="°C",
        time_period="current",
        location="Dehradun",
        claim_type=ClaimType.NUMERICAL_VALUE,
    )
    res_3 = validator.validate_claim(claim_partial, evidence)
    assert res_3.status == ValidationStatus.PARTIALLY_SUPPORTED

    # 4. Out-of-bounds numerical -> CONTRADICTED
    claim_contradicted = FactualClaim(
        claim_id="c4",
        statement="Current temperature is 35°C",
        variable=WeatherVariable.TEMPERATURE,
        claimed_value=35.0,
        unit="°C",
        time_period="current",
        location="Dehradun",
        claim_type=ClaimType.NUMERICAL_VALUE,
    )
    res_4 = validator.validate_claim(claim_contradicted, evidence)
    assert res_4.status == ValidationStatus.CONTRADICTED

    # 5. Trend contradiction -> CONTRADICTED
    claim_trend_contra = FactualClaim(
        claim_id="c5",
        statement="Temperature is increasing over the next 24 hours",
        variable=WeatherVariable.TEMPERATURE_TREND,
        claimed_value="increasing",
        unit="trend",
        time_period="next_24h",
        location="Dehradun",
        claim_type=ClaimType.TREND,
    )
    res_5 = validator.validate_claim(claim_trend_contra, evidence)
    assert res_5.status == ValidationStatus.CONTRADICTED

    # 6. Recommendation contradiction -> CONTRADICTED (claims True when evidence is False)
    claim_umb_contra = FactualClaim(
        claim_id="c6",
        statement="Carry an umbrella",
        variable=WeatherVariable.UMBRELLA_NEED,
        claimed_value=True,
        unit="recommendation",
        time_period="forecast_period",
        location="Dehradun",
        claim_type=ClaimType.RECOMMENDATION_SUPPORT,
    )
    res_6 = validator.validate_claim(claim_umb_contra, evidence)
    assert res_6.status == ValidationStatus.CONTRADICTED

    # 7. Insufficient evidence -> INSUFFICIENT_EVIDENCE
    claim_no_ev = FactualClaim(
        claim_id="c7",
        statement="Surface pressure is 1013 hPa",
        variable=WeatherVariable.PRESSURE,
        claimed_value=1013.0,
        unit="hPa",
        time_period="current",
        location="Dehradun",
        claim_type=ClaimType.NUMERICAL_VALUE,
    )
    res_7 = validator.validate_claim(claim_no_ev, evidence)
    assert res_7.status == ValidationStatus.INSUFFICIENT_EVIDENCE

    # 8. Batch validation
    batch_res = validator.validate_all([claim_supported, claim_contradicted, claim_no_ev], evidence)
    assert len(batch_res) == 3
    assert batch_res[0].status == ValidationStatus.SUPPORTED
    assert batch_res[1].status == ValidationStatus.CONTRADICTED
    assert batch_res[2].status == ValidationStatus.INSUFFICIENT_EVIDENCE

    print("  -> Passed all ClaimValidator unit tests.")


if __name__ == "__main__":
    test_claim_validator()
