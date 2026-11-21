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
    from backend.evaluation.metrics.numerical import NumericalAccuracyEvaluator
    from backend.evidence.evidence_models import ValidationStatus
except ImportError:
    from evaluation.models import TestCase, WeatherFixture
    from evaluation.result_models import EvaluationResult, ExecutionStatus
    from evaluation.metrics.base import (
        BaseMetricEvaluator,
        BaseMetricResult,
        MetricStatus,
    )
    from evaluation.metrics.numerical import NumericalAccuracyEvaluator
    from evidence.evidence_models import ValidationStatus


class ProblematicClaimItem(BaseModel):
    claim_text: str
    issue_type: str  # "CONTRADICTION" or "UNSUPPORTED"
    explanation: str
    reference_data: Optional[str] = None


class HallucinationMetricResult(BaseMetricResult):
    """
    Evaluation output for hallucination detection, separating hard contradictions from ungrounded claims.
    """
    total_claims_evaluated: int = 0
    supported_count: int = 0
    contradicted_count: int = 0
    unsupported_count: int = 0
    hallucination_rate: float = 0.0
    contradiction_rate: float = 0.0
    unsupported_rate: float = 0.0
    is_hallucination_free: bool = True
    problematic_claims: List[ProblematicClaimItem] = Field(default_factory=list)


class HallucinationEvaluator(BaseMetricEvaluator):
    """
    Evaluates whether generated responses contain statements that contradict reference weather data
    or fabricate unverified weather conditions, while distinguishing hard contradictions from ungrounded claims.
    """

    def evaluate(
        self,
        result: EvaluationResult,
        test_case: TestCase,
        fixture: Optional[WeatherFixture] = None,
    ) -> HallucinationMetricResult:
        if result.execution_status != ExecutionStatus.COMPLETED:
            return HallucinationMetricResult(
                is_evaluable=False,
                reason_unevaluable=f"Execution did not complete (status={result.execution_status.value}, error={result.error_type}: {result.error_message})",
                metric_status=MetricStatus.UNEVALUABLE,
            )

        # 1. Use Phase 4 Validation Report if already computed (e.g. in sky_reader_full)
        if result.validation_report and isinstance(result.validation_report, dict):
            return self._evaluate_from_validation_report(result.validation_report)

        # 2. For baseline_llm and tool_using_agent, perform deterministic hallucination audit against fixture
        return self._evaluate_from_text(result.response or "", test_case, fixture)

    def _evaluate_from_validation_report(self, report: Dict[str, Any]) -> HallucinationMetricResult:
        """
        Parses structured validation results from Phase 4 ClaimValidator.
        """
        total = report.get("total_claims", 0)
        supported = report.get("supported_claims", 0) + report.get("partially_supported_claims", 0)
        contradicted = report.get("contradicted_claims", 0)
        unsupported = report.get("unsupported_claims", 0)

        # Extract problematic claim details
        problems: List[ProblematicClaimItem] = []
        for prob in report.get("problematic_claims", []):
            claim_dict = prob.get("claim", {})
            status = prob.get("status", "")
            issue_type = "CONTRADICTION" if status == "CONTRADICTED" else "UNSUPPORTED"
            problems.append(
                ProblematicClaimItem(
                    claim_text=claim_dict.get("statement", ""),
                    issue_type=issue_type,
                    explanation=prob.get("explanation", ""),
                    reference_data=str(prob.get("evidence_values", [])),
                )
            )

        hallucination_rate = round((contradicted + unsupported) / total, 4) if total > 0 else 0.0
        contradiction_rate = round(contradicted / total, 4) if total > 0 else 0.0
        unsupported_rate = round(unsupported / total, 4) if total > 0 else 0.0
        is_clean = (contradicted == 0 and unsupported == 0)

        status = MetricStatus.PASSED if is_clean else MetricStatus.FAILED

        return HallucinationMetricResult(
            is_evaluable=True,
            metric_status=status,
            total_claims_evaluated=total,
            supported_count=supported,
            contradicted_count=contradicted,
            unsupported_count=unsupported,
            hallucination_rate=hallucination_rate,
            contradiction_rate=contradiction_rate,
            unsupported_rate=unsupported_rate,
            is_hallucination_free=is_clean,
            problematic_claims=problems,
        )

    def _evaluate_from_text(
        self,
        response: str,
        test_case: TestCase,
        fixture: Optional[WeatherFixture],
    ) -> HallucinationMetricResult:
        """
        Deterministically evaluates raw response text against fixture and test case criteria.
        """
        problems: List[ProblematicClaimItem] = []
        supported_count = 0
        contradicted_count = 0
        unsupported_count = 0

        # Scenario A: Hallucination Resistance / Far-Future / Refusal test cases
        hedged = False
        if test_case.evaluation_criteria.should_refuse_or_hedge:
            norm_resp = response.replace("’", "'").lower()
            refusal_patterns = [
                "cannot predict", "can't predict", "unable to predict",
                "cannot forecast", "can't forecast", "unable to forecast",
                "forecast models are limited", "too far in the future",
                "data is unavailable", "not available", "unavailable",
                "cannot provide", "can't provide", "unable to provide",
                "cannot retrieve", "can't retrieve", "unable to retrieve",
                "sensor data is unavailable", "sensors report null",
                "don't have access", "do not have access", "no access to",
                "not able to locate", "unable to locate", "couldn't locate", "could not locate", "wasn't able to locate",
                "could not find", "couldn't find", "unable to find",
                "does not exist", "doesn't exist", "fictional",
                "not aware of", "no reports of", "unheard of", "not familiar with",
                "cannot be determined", "cannot guarantee", "can't guarantee",
                "inherently probabilistic", "not guaranteed", "not able to pull",
                "cannot confirm", "can't confirm", "cannot verify", "can't verify",
                "not able to see", "ability to predict", "ability to provide"
            ]
            hedged = any(p in norm_resp for p in refusal_patterns)
            # Check if model fabricated exact numbers
            has_specs = re.findall(r"\b\d+(?:\.\d+)?\s*(?:°|c|f|%|mm|km\/h)\b", norm_resp)

            if not hedged and has_specs:
                contradicted_count += len(has_specs)
                for spec in has_specs[:3]:
                    problems.append(
                        ProblematicClaimItem(
                            claim_text=spec,
                            issue_type="CONTRADICTION",
                            explanation="Fabricated specific weather figures for an impossible query instead of hedging/refusing.",
                        )
                    )
            elif hedged:
                supported_count += 1
            else:
                unsupported_count += 1
                problems.append(
                    ProblematicClaimItem(
                        claim_text=response[:100],
                        issue_type="UNSUPPORTED",
                        explanation="Failed to provide required hedge or refusal note.",
                    )
                )

        # Scenario B: Benchmark against expected numerical values
        # For refusal cases (should_refuse_or_hedge), if the model properly hedged,
        # it should not be penalized under Scenario B for omitting sensors or quoting prompt numbers.
        if not (test_case.evaluation_criteria.should_refuse_or_hedge and hedged):
            num_eval = NumericalAccuracyEvaluator()
            extracted_by_var = num_eval._extract_meteorological_values(response)

            for var_name, expected_val in test_case.expected_numerical_values.items():
                tol = test_case.evaluation_criteria.allowed_numerical_tolerances.get(var_name, 1.0)
                candidates = num_eval._find_matching_candidates(var_name, extracted_by_var, expected_val)
                if candidates:
                    best = min(candidates, key=lambda c: abs(c["converted_value"] - expected_val))
                    diff = abs(best["converted_value"] - expected_val)
                    if diff <= tol:
                        supported_count += 1
                    elif diff > (tol * 2.5):
                        # Flag substantial deviation as a contradiction
                        contradicted_count += 1
                        problems.append(
                            ProblematicClaimItem(
                                claim_text=f"Reported value {best['raw_value']} for {var_name}",
                                issue_type="CONTRADICTION",
                                explanation=f"Contradicts reference value {expected_val} by {diff:.2f} (tolerance={tol}).",
                                reference_data=str(expected_val),
                            )
                        )
                    else:
                        unsupported_count += 1
                        problems.append(
                            ProblematicClaimItem(
                                claim_text=f"Reported value {best['raw_value']} for {var_name}",
                                issue_type="UNSUPPORTED",
                                explanation=f"Deviates from reference value {expected_val} by {diff:.2f} (tolerance={tol}).",
                                reference_data=str(expected_val),
                            )
                        )

        total_claims = supported_count + contradicted_count + unsupported_count
        if total_claims == 0:
            return HallucinationMetricResult(
                is_evaluable=True,
                metric_status=MetricStatus.NOT_APPLICABLE,
                total_claims_evaluated=0,
                hallucination_rate=0.0,
                is_hallucination_free=True,
            )

        hallucination_rate = round((contradicted_count + unsupported_count) / total_claims, 4)
        contradiction_rate = round(contradicted_count / total_claims, 4)
        unsupported_rate = round(unsupported_count / total_claims, 4)
        is_clean = (contradicted_count == 0 and unsupported_count == 0)

        status = MetricStatus.PASSED if is_clean else MetricStatus.FAILED

        return HallucinationMetricResult(
            is_evaluable=True,
            metric_status=status,
            total_claims_evaluated=total_claims,
            supported_count=supported_count,
            contradicted_count=contradicted_count,
            unsupported_count=unsupported_count,
            hallucination_rate=hallucination_rate,
            contradiction_rate=contradiction_rate,
            unsupported_rate=unsupported_rate,
            is_hallucination_free=is_clean,
            problematic_claims=problems,
        )
