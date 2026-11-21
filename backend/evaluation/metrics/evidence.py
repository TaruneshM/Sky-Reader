import re
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

try:
    from backend.evaluation.models import TestCase, WeatherFixture
    from backend.evaluation.result_models import EvaluationResult, ExecutionStatus
    from backend.evaluation.metrics.base import (
        BaseMetricEvaluator,
        BaseMetricResult,
        MetricStatus,
    )
except ImportError:
    from evaluation.models import TestCase, WeatherFixture
    from evaluation.result_models import EvaluationResult, ExecutionStatus
    from evaluation.metrics.base import (
        BaseMetricEvaluator,
        BaseMetricResult,
        MetricStatus,
    )


class EvidenceMetricResult(BaseMetricResult):
    """
    Evaluation output for evidence grounding, citations, and provenance validation.
    """
    evidence_available: bool = False
    evidence_used: bool = False
    evidence_citation_count: int = 0
    valid_citation_ids: List[str] = Field(default_factory=list)
    invalid_citation_ids: List[str] = Field(default_factory=list)
    has_explanation_proof: bool = False
    proof_valid: Optional[bool] = None
    provenance_sources: List[str] = Field(default_factory=list)
    grounding_ratio: Optional[float] = None


class EvidenceGroundingEvaluator(BaseMetricEvaluator):
    """
    Evaluates evidence availability versus evidence usage, citations of evidence IDs,
    and formal explanation proof structures.
    """

    # Regex for evidence identifiers, e.g. "ev_temp_current", "ev_hourly_rain_14"
    EVIDENCE_ID_PATTERN = re.compile(r"\b(ev_[a-zA-Z0-9_\-]+)\b")

    def evaluate(
        self,
        result: EvaluationResult,
        test_case: TestCase,
        fixture: Optional[WeatherFixture] = None,
    ) -> EvidenceMetricResult:
        if result.execution_status != ExecutionStatus.COMPLETED:
            return EvidenceMetricResult(
                is_evaluable=False,
                reason_unevaluable=f"Execution did not complete (status={result.execution_status.value}, error={result.error_type}: {result.error_message})",
                metric_status=MetricStatus.UNEVALUABLE,
            )

        # 1. Determine Evidence Availability
        # Available if tools were called with outputs, fixture was injected, or validation report exists
        evidence_available = (
            len(result.tool_calls) > 0 or
            (result.fixture_id is not None and fixture is not None) or
            result.validation_report is not None
        )

        # 2. Extract Evidence IDs Cited in Response Text or Explanation
        response_text = result.response or ""
        cited_ids_in_text = set(self.EVIDENCE_ID_PATTERN.findall(response_text))

        # Check Explanation Proof
        explanation = result.explanation if isinstance(result.explanation, dict) else None
        has_proof = explanation is not None

        proof_valid: Optional[bool] = None
        cited_in_proof: Set[str] = set()
        provenance_sources: Set[str] = set()

        if has_proof:
            supporting_ev = explanation.get("supporting_evidence", [])
            measurements = explanation.get("measurements_used", [])
            sources = explanation.get("data_sources", [])
            for s in sources:
                if isinstance(s, str):
                    provenance_sources.add(s)

            for item in supporting_ev:
                if isinstance(item, dict) and "id" in item:
                    cited_in_proof.add(str(item["id"]))
            for item in measurements:
                if isinstance(item, dict) and "id" in item:
                    cited_in_proof.add(str(item["id"]))

            # Validate proof structure
            proof_valid = bool(supporting_ev or measurements)

        # Also extract provenance from tool calls
        for tc in result.tool_calls:
            t_name = tc.get("tool", "")
            if t_name:
                provenance_sources.add(f"tool:{t_name}")

        all_cited_ids = cited_ids_in_text.union(cited_in_proof)

        # Check if citations are valid against actual evidence items in validation report
        valid_ids: List[str] = []
        invalid_ids: List[str] = []

        known_evidence_ids: Set[str] = set()
        if result.validation_report and isinstance(result.validation_report, dict):
            for vr in result.validation_report.get("validation_results", []):
                for eid in vr.get("supporting_evidence_ids", []):
                    known_evidence_ids.add(str(eid))

        for cid in sorted(all_cited_ids):
            if known_evidence_ids and cid in known_evidence_ids:
                valid_ids.append(cid)
            elif known_evidence_ids:
                invalid_ids.append(cid)
            else:
                # If no formal validation report available to cross-check, treat formatted ev_ ID as valid citation
                valid_ids.append(cid)

        # 3. Determine Evidence Usage
        evidence_used = bool(all_cited_ids or (has_proof and proof_valid) or len(result.tool_calls) > 0)

        # 4. Compute Grounding Ratio
        grounding_ratio: Optional[float] = None
        if result.validation_report and isinstance(result.validation_report, dict):
            total_claims = result.validation_report.get("total_claims", 0)
            supported = (
                result.validation_report.get("supported_claims", 0) +
                result.validation_report.get("partially_supported_claims", 0)
            )
            grounding_ratio = round(supported / total_claims, 4) if total_claims > 0 else 1.0
        elif evidence_available and evidence_used:
            grounding_ratio = 1.0 if not invalid_ids else 0.5
        elif evidence_available and not evidence_used:
            grounding_ratio = 0.0

        # Check against test case requirements
        requires_proof = test_case.evaluation_criteria.requires_evidence_proof
        if requires_proof:
            status = MetricStatus.PASSED if (has_proof and proof_valid is True) else MetricStatus.FAILED
        elif evidence_available and evidence_used:
            status = MetricStatus.PASSED
        elif not evidence_available and not test_case.evaluation_criteria.requires_tools:
            status = MetricStatus.NOT_APPLICABLE
        else:
            status = MetricStatus.FAILED if test_case.evaluation_criteria.requires_tools else MetricStatus.NOT_APPLICABLE

        return EvidenceMetricResult(
            is_evaluable=True,
            metric_status=status,
            evidence_available=evidence_available,
            evidence_used=evidence_used,
            evidence_citation_count=len(all_cited_ids),
            valid_citation_ids=valid_ids,
            invalid_citation_ids=invalid_ids,
            has_explanation_proof=has_proof,
            proof_valid=proof_valid,
            provenance_sources=sorted(list(provenance_sources)),
            grounding_ratio=grounding_ratio,
        )
