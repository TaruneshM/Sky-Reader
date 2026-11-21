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
    from backend.weather.risk_models import RiskLevel, RiskType
except ImportError:
    from evaluation.models import TestCase, WeatherFixture
    from evaluation.result_models import EvaluationResult, ExecutionStatus
    from evaluation.metrics.base import (
        BaseMetricEvaluator,
        BaseMetricResult,
        MetricStatus,
    )
    from weather.risk_models import RiskLevel, RiskType

RISK_SEVERITY_ORDER = {
    "LOW": 0,
    "MODERATE": 1,
    "HIGH": 2,
    "SEVERE": 3,
}

KNOWN_HAZARDS = {
    "heavy_rainfall": ["heavy rain", "torrential", "high rainfall", "heavy rainfall", "monsoon", "downpour"],
    "thunderstorm": ["thunderstorm", "lightning", "hail", "severe storm"],
    "strong_wind": ["strong wind", "gale", "high wind", "damaging wind", "wind gusts"],
    "extreme_heat": ["extreme heat", "heatwave", "heat wave", "scorching", "excessive heat"],
    "extreme_cold": ["extreme cold", "freeze", "freezing", "frost", "arctic cold", "sub-zero"],
}


class RiskMetricResult(BaseMetricResult):
    """
    Evaluation output for weather safety risk assessment and hazard classification.
    """
    is_applicable: bool = False
    expected_risk_level: Optional[str] = None
    predicted_risk_level: Optional[str] = None
    classification_match: Optional[bool] = None
    severity_error: Optional[int] = None
    underreported: Optional[bool] = None
    overreported: Optional[bool] = None
    expected_hazards: List[str] = Field(default_factory=list)
    detected_hazards: List[str] = Field(default_factory=list)
    matched_hazards: List[str] = Field(default_factory=list)
    missed_hazards: List[str] = Field(default_factory=list)
    false_positive_hazards: List[str] = Field(default_factory=list)
    confusion_matrix_entry: Optional[Dict[str, Any]] = None


class RiskAssessmentEvaluator(BaseMetricEvaluator):
    """
    Deterministically evaluates risk level accuracy, hazard detection, and severity errors
    producing confusion-matrix compatible outputs.
    """

    def evaluate(
        self,
        result: EvaluationResult,
        test_case: TestCase,
        fixture: Optional[WeatherFixture] = None,
    ) -> RiskMetricResult:
        if result.execution_status != ExecutionStatus.COMPLETED:
            return RiskMetricResult(
                is_evaluable=False,
                reason_unevaluable=f"Execution did not complete (status={result.execution_status.value}, error={result.error_type}: {result.error_message})",
                metric_status=MetricStatus.UNEVALUABLE,
                is_applicable=bool(test_case.expected_risk_classification or test_case.evaluation_criteria.requires_risk_assessment),
            )

        expected_risk = test_case.expected_risk_classification
        requires_risk = test_case.evaluation_criteria.requires_risk_assessment

        if not expected_risk and not requires_risk:
            return RiskMetricResult(
                is_evaluable=True,
                is_applicable=False,
                metric_status=MetricStatus.NOT_APPLICABLE,
            )

        # 1. Extract Predicted Risk Level
        predicted_risk = self._extract_predicted_risk(result)

        # 2. Extract Hazards
        expected_hazards = self._extract_expected_hazards(test_case)
        detected_hazards = self._extract_detected_hazards(result)

        matched_hazards = [h for h in expected_hazards if h in detected_hazards]
        missed_hazards = [h for h in expected_hazards if h not in detected_hazards]
        fp_hazards = [h for h in detected_hazards if h not in expected_hazards]

        # 3. Calculate Severity Error & Classification Match
        classification_match: Optional[bool] = None
        severity_error: Optional[int] = None
        underreported: Optional[bool] = None
        overreported: Optional[bool] = None
        cm_entry: Optional[Dict[str, Any]] = None

        if expected_risk:
            exp_upper = expected_risk.upper()
            pred_upper = predicted_risk.upper() if predicted_risk else "NONE"

            classification_match = (exp_upper == pred_upper)
            cm_entry = {
                "actual": exp_upper,
                "predicted": pred_upper,
            }

            if exp_upper in RISK_SEVERITY_ORDER and pred_upper in RISK_SEVERITY_ORDER:
                severity_error = RISK_SEVERITY_ORDER[pred_upper] - RISK_SEVERITY_ORDER[exp_upper]
                underreported = (severity_error < 0)
                overreported = (severity_error > 0)

        # Determine metric status
        if classification_match is True:
            status = MetricStatus.PASSED
        elif classification_match is False:
            status = MetricStatus.FAILED
        elif requires_risk and predicted_risk is not None:
            status = MetricStatus.PASSED
        elif requires_risk and predicted_risk is None:
            status = MetricStatus.FAILED
        else:
            status = MetricStatus.NOT_APPLICABLE

        return RiskMetricResult(
            is_evaluable=True,
            is_applicable=True,
            metric_status=status,
            expected_risk_level=expected_risk,
            predicted_risk_level=predicted_risk,
            classification_match=classification_match,
            severity_error=severity_error,
            underreported=underreported,
            overreported=overreported,
            expected_hazards=expected_hazards,
            detected_hazards=detected_hazards,
            matched_hazards=matched_hazards,
            missed_hazards=missed_hazards,
            false_positive_hazards=fp_hazards,
            confusion_matrix_entry=cm_entry,
        )

    def _extract_predicted_risk(self, result: EvaluationResult) -> Optional[str]:
        # Priority 1: Structured risk assessment output
        if result.risk_assessment and isinstance(result.risk_assessment, dict):
            lvl = result.risk_assessment.get("overall_risk_level")
            if lvl and str(lvl).upper() in RISK_SEVERITY_ORDER:
                return str(lvl).upper()

        # Priority 2: Text search for explicit risk statements
        response = result.response or ""
        match = re.search(
            r"\b(?:risk level|overall risk|weather risk|risk is|risk:\s*)\s*:?\s*(LOW|MODERATE|HIGH|SEVERE)\b",
            response,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).upper()

        # Standalone mentions like "severe risk" or "moderate risk"
        adj_match = re.search(
            r"\b(LOW|MODERATE|HIGH|SEVERE)\s+(?:weather\s+)?risk\b",
            response,
            re.IGNORECASE,
        )
        if adj_match:
            return adj_match.group(1).upper()

        return None

    def _extract_expected_hazards(self, test_case: TestCase) -> List[str]:
        expected: List[str] = []
        combined_text = (test_case.question + " " + " ".join(test_case.expected_facts_or_claims)).lower()

        for hazard_key, synonyms in KNOWN_HAZARDS.items():
            if any(syn in combined_text for syn in synonyms):
                expected.append(hazard_key)

        return sorted(list(set(expected)))

    def _extract_detected_hazards(self, result: EvaluationResult) -> List[str]:
        detected: List[str] = []

        # From structured risk assessment
        if result.risk_assessment and isinstance(result.risk_assessment, dict):
            for item in result.risk_assessment.get("detected_risks", []):
                if isinstance(item, dict) and "risk_type" in item:
                    detected.append(str(item["risk_type"]).lower())

        # From text
        response_lower = (result.response or "").lower()
        for hazard_key, synonyms in KNOWN_HAZARDS.items():
            if any(syn in response_lower for syn in synonyms):
                detected.append(hazard_key)

        return sorted(list(set(detected)))
