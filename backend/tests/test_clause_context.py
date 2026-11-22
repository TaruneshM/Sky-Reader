from types import SimpleNamespace

import pytest

from backend.agent.weather_evidence_gate import model_weather_answer_is_grounded
from backend.evaluation.stage17c.diagnostics import draft_diagnostic
from backend.evidence.evidence_engine import EvidenceEngine
from backend.evidence.hallucination_controller import HallucinationController
from backend.llm_gateway.models import Usage


OBSERVATION = {"current": {"temperature_2m": 21, "relative_humidity_2m": 64, "weather_code": 0}}
PLACE = {"name": "Lisbon"}
ANCHOR = "Currently in Lisbon the temperature is 21 °C"


@pytest.mark.parametrize(("draft", "expected"), [
    (ANCHOR + ".", True),
    (ANCHOR + ". The humidity there is 64%.", True),
    (ANCHOR + " and the humidity is 64%.", True),
    (ANCHOR + ". In Paris the humidity is 64%.", False),
    (ANCHOR + ". The humidity in the other city is 64%.", False),
    (ANCHOR + ". It will be sunny tomorrow.", False),
    (ANCHOR + ". The humidity there is 5%.", False),
    (ANCHOR + ". The humidity there will be 64% tomorrow.", False),
    (ANCHOR + ". The humidity there is 64%. No risk.", False),
    ("The humidity there is 64%.", False),
    (ANCHOR + ". What about Paris? The humidity there is 64%.", False),
    ("In Lisbon or Paris the temperature is 21 °C. The humidity there is 64%.", False),
])
def test_clause_validation_preserves_scope_and_evidence(draft, expected):
    evidence = EvidenceEngine().generate_evidence(current_data=OBSERVATION, location_meta=PLACE)
    assert model_weather_answer_is_grounded(
        draft, evidence, HallucinationController(), weather_request=True,
    ) is expected


def test_no_location_inheritance_in_multi_city_evidence():
    engine = EvidenceEngine()
    evidence = engine.generate_evidence(current_data=OBSERVATION, location_meta=PLACE)
    for item in engine.generate_evidence(current_data=OBSERVATION, location_meta={"name": "Paris"}).items:
        evidence.add(item.model_copy(update={"id": "paris-" + item.id}))
    assert model_weather_answer_is_grounded(
        ANCHOR + ". Currently in Paris the temperature is 21 °C.",
        evidence, HallucinationController(), weather_request=True,
    )
    assert not model_weather_answer_is_grounded(
        ANCHOR + ". The humidity there is 64%.",
        evidence, HallucinationController(), weather_request=True,
    )


def test_truncation_is_distinct_from_evidence_rejection():
    response = SimpleNamespace(message={"content": ANCHOR + "."}, usage=Usage(224, 350), finish_reason="length")
    diagnostics = draft_diagnostic(response, "Explain the temperature in Lisbon.", OBSERVATION, PLACE, 350)
    assert diagnostics["truncated"] and diagnostics["reported_usage_reached_cap"]
    assert diagnostics["final_gate_rejection"] is None
    assert diagnostics["draft_passed_model_evidence_gate"]


def test_normal_audit_reports_inherited_contradiction():
    from backend.agent.weather_evidence_gate import first_weather_gate_rejection

    evidence = EvidenceEngine().generate_evidence(current_data=OBSERVATION, location_meta=PLACE)
    rejection = first_weather_gate_rejection(
        ANCHOR + ". The humidity there is 5%.", evidence, HallucinationController(), weather_request=True,
    )
    assert rejection["reason"] == "clause_claim_audit_failed"
    assert rejection["claim_checks"] == [{"variable": "humidity", "status": "CONTRADICTED"}]


def test_truncated_unsupported_draft_still_fails_evidence_gate():
    response = SimpleNamespace(message={"content": ANCHOR + ". It will be sunny tomorrow."},
                               usage=Usage(224, 350), finish_reason="length")
    diagnostics = draft_diagnostic(response, "Explain the temperature in Lisbon.", OBSERVATION, PLACE, 350)
    assert diagnostics["truncated"]
    assert diagnostics["final_gate_rejection"]["clause_index"] == 2
    assert not diagnostics["draft_passed_model_evidence_gate"]


@pytest.mark.parametrize(("tail", "prerequisite", "numeric", "forecast"), [
    ("The humidity there is 5%.", "grounded_claims_required", True, False),
    ("It will be sunny tomorrow.", "numeric_continuation_required", False, True),
    ("The humidity in the other city is 64%.", "numeric_continuation_required", False, False),
    ("In Paris the humidity is 64%.", "numeric_continuation_required", False, False),
    ("It is 64% there.", "extractable_claim_required", True, False),
])
def test_location_rejection_explains_the_failed_prerequisite(tail, prerequisite, numeric, forecast):
    from backend.agent.weather_evidence_gate import first_weather_gate_rejection

    evidence = EvidenceEngine().generate_evidence(current_data=OBSERVATION, location_meta=PLACE)
    result = first_weather_gate_rejection(
        ANCHOR + ". " + tail, evidence, HallucinationController(), weather_request=True,
    )
    decision = result["location_decision"]
    assert result["clause_index"] == 2
    assert decision == {
        "explicit_evidence_location_detected": False,
        "explicit_location_match_count": 0,
        "candidate_location_count": 1,
        "previous_clause_validated": True,
        "previous_clause_location_established": True,
        "previous_anchor_status": "explicit_observation_anchor",
        "evidence_scope": "observation",
        "forecast_wording_detected": forecast,
        "numeric_continuation_eligible": numeric,
        "location_inheritance_attempted": True,
        "location_inherited": numeric,
        "failed_prerequisite": prerequisite,
    }
    assert tail not in str(result)


def test_validated_clause_can_fail_to_establish_an_inheritance_anchor():
    from backend.agent.weather_evidence_gate import first_weather_gate_rejection

    evidence = EvidenceEngine().generate_evidence(current_data=OBSERVATION, location_meta=PLACE)
    result = first_weather_gate_rejection(
        "Lisbon currently has a temperature of 21 °C. The humidity there is 64%.",
        evidence, HallucinationController(), weather_request=True,
    )
    decision = result["location_decision"]
    assert decision["previous_clause_validated"] and not decision["previous_clause_location_established"]
    assert decision["previous_anchor_status"] == "anchor_grammar_mismatch"
    assert decision["failed_prerequisite"] == "previous_location_anchor_required"


@pytest.mark.parametrize("scope", ["mixed", "multi_city"])
def test_candidate_scope_failure_is_distinct_from_grammar(scope):
    from backend.agent.weather_evidence_gate import first_weather_gate_rejection
    from backend.evidence.evidence_models import EvidenceSourceType

    engine = EvidenceEngine()
    evidence = engine.generate_evidence(current_data=OBSERVATION, location_meta=PLACE)
    update = {"id": "second-item"}
    if scope == "mixed":
        update["source_type"] = EvidenceSourceType.FORECAST
    else:
        update["location"] = "Paris"
    evidence.add(evidence.items[0].model_copy(update=update))
    result = first_weather_gate_rejection(
        ANCHOR + " and the humidity is 64%.", evidence, HallucinationController(), weather_request=True,
    )
    decision = result["location_decision"]
    assert result["clause_index"] == 2 and decision["numeric_continuation_eligible"]
    if scope == "mixed":
        assert decision["failed_prerequisite"] == "observation_only_evidence_required"
        assert decision["evidence_scope"] == "mixed_or_derived"
    else:
        assert decision["failed_prerequisite"] == "multiple_evidence_locations"
        assert decision["candidate_location_count"] == 2
