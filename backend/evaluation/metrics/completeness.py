import re
from typing import Any, Dict, List, Optional
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


class CompletenessMetricResult(BaseMetricResult):
    """
    Evaluation output for response completeness across benchmark query requirements.
    """
    completeness_score: float = 0.0
    is_complete: bool = False
    missing_elements: List[str] = Field(default_factory=list)
    criteria_checked: Dict[str, bool] = Field(default_factory=dict)


class ResponseCompletenessEvaluator(BaseMetricEvaluator):
    """
    Deterministically evaluates whether the system addressed all mandatory components
    of the benchmark question according to dataset evaluation criteria.
    """

    UNCERTAINTY_TOKENS = {
        "uncertainty", "probability", "confidence", "approximate", "approximately",
        "subject to change", "data limitation", "data limitations", "forecast horizon",
        "potential error", "confidence interval", "estimated", "margin of error",
    }

    REFUSAL_TOKENS = {
        "cannot predict", "unable to predict", "cannot forecast", "unable to forecast",
        "cannot provide", "impossible to predict", "models are limited", "too far in the future",
        "beyond the forecasting horizon", "data is unavailable", "sensor data is unavailable",
        "data limitation", "missing data", "not available", "unreliable beyond",
    }

    def evaluate(
        self,
        result: EvaluationResult,
        test_case: TestCase,
        fixture: Optional[WeatherFixture] = None,
    ) -> CompletenessMetricResult:
        if result.execution_status != ExecutionStatus.COMPLETED:
            return CompletenessMetricResult(
                is_evaluable=False,
                reason_unevaluable=f"Execution did not complete (status={result.execution_status.value}, error={result.error_type}: {result.error_message})",
                metric_status=MetricStatus.UNEVALUABLE,
            )

        response = result.response or ""
        response_lower = response.lower()
        criteria = test_case.evaluation_criteria

        checked: Dict[str, bool] = {}
        missing: List[str] = []

        # 1. Location Mentioned
        loc_name = test_case.location.lower().strip()
        # For general knowledge / abstract hallucination tests, location might be fictional or generic
        if loc_name and loc_name not in ("unspecified", "global", "none"):
            addressed_loc = loc_name in response_lower
            checked["addressed_location"] = addressed_loc
            if not addressed_loc:
                missing.append(f"Target location '{test_case.location}' was not addressed in response.")

        # 2. Target Variable / Metric Mentioned
        if test_case.expected_numerical_values:
            has_any_num = bool(re.search(r"[-+]?\d+(?:\.\d+)?", response))
            checked["addressed_numerical_variables"] = has_any_num
            if not has_any_num:
                missing.append(f"Expected numerical variables {list(test_case.expected_numerical_values.keys())} were not provided.")

        # 3. Risk Assessment Required
        if criteria.requires_risk_assessment:
            has_risk = bool(result.risk_assessment) or bool(re.search(r"\b(risk|hazard|safety)\b", response_lower))
            checked["satisfied_risk_requirement"] = has_risk
            if not has_risk:
                missing.append("Query required weather risk assessment, but none was provided.")

        # 4. Evidence Proof Required
        if criteria.requires_evidence_proof:
            has_proof = bool(result.explanation) or bool(re.search(r"\b(ev_[a-zA-Z0-9_\-]+|provenance|source)\b", response_lower))
            checked["satisfied_evidence_requirement"] = has_proof
            if not has_proof:
                missing.append("Query required formal evidence proof, but none was provided.")

        # 5. Uncertainty Note Required
        if criteria.requires_uncertainty_note:
            has_uncertainty = any(u in response_lower for u in self.UNCERTAINTY_TOKENS)
            # Also check if risk assessment uncertainty notes exist
            if not has_uncertainty and result.risk_assessment and isinstance(result.risk_assessment, dict):
                has_uncertainty = bool(result.risk_assessment.get("uncertainty_notes"))
            checked["satisfied_uncertainty_requirement"] = has_uncertainty
            if not has_uncertainty:
                missing.append("Query required explicit uncertainty or probabilistic communication, but none was found.")

        # 6. Refusal / Hedging Required
        if criteria.should_refuse_or_hedge:
            has_refusal = any(r in response_lower for r in self.REFUSAL_TOKENS)
            checked["satisfied_refusal_requirement"] = has_refusal
            if not has_refusal:
                missing.append("Query required refusal or hedging on impossible/missing data, but system failed to refuse.")

        if not checked:
            return CompletenessMetricResult(
                is_evaluable=True,
                completeness_score=1.0,
                is_complete=True,
                metric_status=MetricStatus.NOT_APPLICABLE,
            )

        satisfied_count = sum(1 for v in checked.values() if v is True)
        total_criteria = len(checked)
        completeness_score = round(satisfied_count / total_criteria, 4)
        is_complete = (satisfied_count == total_criteria)

        if is_complete:
            status = MetricStatus.PASSED
        elif satisfied_count > 0:
            status = MetricStatus.PARTIAL
        else:
            status = MetricStatus.FAILED

        return CompletenessMetricResult(
            is_evaluable=True,
            metric_status=status,
            completeness_score=completeness_score,
            is_complete=is_complete,
            missing_elements=missing,
            criteria_checked=checked,
        )
