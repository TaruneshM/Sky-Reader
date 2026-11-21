import re
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

try:
    from backend.evaluation.models import TestCase, WeatherFixture
    from backend.evaluation.result_models import EvaluationResult, ExecutionStatus
    from backend.evaluation.metrics.base import (
        BaseMetricEvaluator,
        BaseMetricResult,
        FactualClaimStatus,
        MetricStatus,
    )
except ImportError:
    from evaluation.models import TestCase, WeatherFixture
    from evaluation.result_models import EvaluationResult, ExecutionStatus
    from evaluation.metrics.base import (
        BaseMetricEvaluator,
        BaseMetricResult,
        FactualClaimStatus,
        MetricStatus,
    )


class ClaimEvaluationItem(BaseModel):
    """
    Detailed evaluation of a single expected factual claim.
    """
    expected_claim: str
    status: FactualClaimStatus
    matched_segments: List[str] = Field(default_factory=list)
    explanation: str = Field(default="")


class FactualMetricResult(BaseMetricResult):
    """
    Evaluation output for factual accuracy across expected propositions and claims.
    """
    total_expected: int = 0
    correct_count: int = 0
    incorrect_count: int = 0
    unaddressed_count: int = 0
    unsupported_count: int = 0
    accuracy: Optional[float] = None
    evaluated_claims: List[ClaimEvaluationItem] = Field(default_factory=list)


class FactualAccuracyEvaluator(BaseMetricEvaluator):
    """
    Deterministically evaluates expected factual claims against system responses.
    Uses polarity-aware semantic matching, concept token extraction, and contradiction detection.
    """

    # Common negation markers
    NEGATION_TOKENS = {
        "not", "no", "never", "none", "without", "neither", "nor", "cannot",
        "cant", "can't", "don't", "dont", "unlikely", "zero", "0", "0.0",
        "no need", "not needed", "unnecessary",
    }

    # Refusal and hedging markers
    REFUSAL_TOKENS = {
        "cannot predict", "unable to predict", "cannot forecast", "unable to forecast",
        "cannot provide", "impossible to predict", "forecast models are limited",
        "beyond the forecasting horizon", "too far in the future", "unreliable beyond",
        "data is unavailable", "data unavailable", "sensor is unavailable",
        "cannot determine", "not available", "missing sensor", "missing data",
    }

    def evaluate(
        self,
        result: EvaluationResult,
        test_case: TestCase,
        fixture: Optional[WeatherFixture] = None,
    ) -> FactualMetricResult:
        if result.execution_status != ExecutionStatus.COMPLETED:
            return FactualMetricResult(
                is_evaluable=False,
                reason_unevaluable=f"Execution did not complete (status={result.execution_status.value}, error={result.error_type}: {result.error_message})",
                metric_status=MetricStatus.UNEVALUABLE,
                total_expected=len(test_case.expected_facts_or_claims),
            )

        expected_claims = test_case.expected_facts_or_claims
        if not expected_claims:
            return FactualMetricResult(
                is_evaluable=True,
                metric_status=MetricStatus.NOT_APPLICABLE,
                total_expected=0,
                accuracy=None,
            )

        response_text = result.response or ""
        evaluated_items: List[ClaimEvaluationItem] = []
        correct_count = 0
        incorrect_count = 0
        unaddressed_count = 0
        unsupported_count = 0

        for expected in expected_claims:
            status, matched, reason = self._evaluate_single_claim(expected, response_text, test_case)
            evaluated_items.append(
                ClaimEvaluationItem(
                    expected_claim=expected,
                    status=status,
                    matched_segments=matched,
                    explanation=reason,
                )
            )

            if status == FactualClaimStatus.CORRECT:
                correct_count += 1
            elif status == FactualClaimStatus.INCORRECT:
                incorrect_count += 1
            elif status == FactualClaimStatus.UNADDRESSED:
                unaddressed_count += 1
            elif status == FactualClaimStatus.UNSUPPORTED:
                unsupported_count += 1

        total_expected = len(expected_claims)
        accuracy = round(correct_count / total_expected, 4) if total_expected > 0 else None

        if correct_count == total_expected:
            overall_status = MetricStatus.PASSED
        elif correct_count > 0:
            overall_status = MetricStatus.PARTIAL
        else:
            overall_status = MetricStatus.FAILED

        return FactualMetricResult(
            is_evaluable=True,
            metric_status=overall_status,
            total_expected=total_expected,
            correct_count=correct_count,
            incorrect_count=incorrect_count,
            unaddressed_count=unaddressed_count,
            unsupported_count=unsupported_count,
            accuracy=accuracy,
            evaluated_claims=evaluated_items,
        )

    def _evaluate_single_claim(
        self,
        expected_claim: str,
        response: str,
        test_case: TestCase,
    ) -> Tuple[FactualClaimStatus, List[str], str]:
        """
        Evaluates a single expected claim against the response text.
        Returns (status, matched_segments, explanation).
        """
        claim_lower = expected_claim.lower().strip()
        response_lower = response.lower()

        # 1. Check for Refusal / Hedging expected claims
        # e.g. "cannot provide exact weather 10 years in the future", "refuses to fabricate", "precipitation data is unavailable"
        if any(h in claim_lower for h in ["cannot", "unable", "refuses", "unreliable", "unavailable", "missing"]):
            return self._evaluate_refusal_claim(claim_lower, response_lower)

        # 2. Check for Umbrella / Outdoor Decision Support Claims
        if "umbrella" in claim_lower:
            return self._evaluate_umbrella_claim(claim_lower, response_lower)

        # 3. Check for Risk Level / Hazard Claims
        # e.g. "SEVERE risk level detected", "severe thunderstorm with hail", "seek indoor shelter"
        if any(w in claim_lower for w in ["risk", "hazard", "shelter", "thunderstorm", "heatwave", "freeze", "gale"]):
            return self._evaluate_risk_hazard_claim(claim_lower, response_lower)

        # 4. Check for General Meteorological Proposition (with numbers or trends)
        return self._evaluate_general_proposition(claim_lower, response_lower)

    def _evaluate_refusal_claim(
        self,
        claim_lower: str,
        response_lower: str,
    ) -> Tuple[FactualClaimStatus, List[str], str]:
        """
        Evaluates whether the system appropriately hedged or refused to fabricate.
        """
        matches = [m for m in self.REFUSAL_TOKENS if m in response_lower]
        if matches:
            return (
                FactualClaimStatus.CORRECT,
                matches[:3],
                f"Response correctly hedged/refused as expected. Matched cues: {matches[:3]}",
            )

        # If it didn't refuse, check if it fabricated specific weather predictions
        has_weather_specs = bool(re.search(r"\b\d+(?:\.\d+)?\s*(?:°|c|f|%|mm|km\/h)\b", response_lower))
        if has_weather_specs:
            return (
                FactualClaimStatus.INCORRECT,
                [],
                "Contradicted expected refusal: response fabricated specific meteorological data instead of refusing.",
            )

        return (
            FactualClaimStatus.UNADDRESSED,
            [],
            "Response did not address the limitation or refusal.",
        )

    def _evaluate_umbrella_claim(
        self,
        claim_lower: str,
        response_lower: str,
    ) -> Tuple[FactualClaimStatus, List[str], str]:
        """
        Evaluates umbrella recommendations with strict polarity checking.
        """
        expected_neg = any(w in claim_lower for w in ["not", "no", "unnecessary", "dont", "don't"])

        response_has_neg = any(
            phrase in response_lower
            for phrase in [
                "umbrella not needed", "no umbrella", "not need an umbrella",
                "don't need an umbrella", "leave your umbrella", "no need for an umbrella",
                "umbrella is not required", "not necessary to bring an umbrella",
                "umbrella is unnecessary",
            ]
        )
        response_has_pos = any(
            phrase in response_lower
            for phrase in [
                "bring an umbrella", "take an umbrella", "carry an umbrella",
                "umbrella is recommended", "need an umbrella", "umbrella needed",
                "pack an umbrella", "umbrella is advisable",
            ]
        )

        if expected_neg:
            if response_has_neg:
                return (FactualClaimStatus.CORRECT, ["umbrella not needed"], "Correctly advised that umbrella is not needed.")
            if response_has_pos:
                return (FactualClaimStatus.INCORRECT, ["bring an umbrella"], "Contradicted: advised bringing umbrella when not needed.")
        else:
            if response_has_pos:
                return (FactualClaimStatus.CORRECT, ["bring an umbrella"], "Correctly advised bringing umbrella.")
            if response_has_neg:
                return (FactualClaimStatus.INCORRECT, ["umbrella not needed"], "Contradicted: advised no umbrella when rain expected.")

        if "umbrella" in response_lower:
            return (FactualClaimStatus.UNSUPPORTED, ["umbrella"], "Mentioned umbrella but polarity could not be confirmed.")
        return (FactualClaimStatus.UNADDRESSED, [], "Did not address umbrella recommendation.")

    def _evaluate_risk_hazard_claim(
        self,
        claim_lower: str,
        response_lower: str,
    ) -> Tuple[FactualClaimStatus, List[str], str]:
        """
        Evaluates hazard identification, risk levels, and safety actions.
        """
        tokens = [w for w in re.findall(r"\b[a-z]{3,}\b", claim_lower) if w not in {"the", "and", "with", "for"}]
        matched_tokens = [t for t in tokens if t in response_lower]

        overlap_ratio = len(matched_tokens) / len(tokens) if tokens else 0.0

        if overlap_ratio >= 0.6:
            return (
                FactualClaimStatus.CORRECT,
                matched_tokens,
                f"Matched key risk concept tokens: {matched_tokens} ({overlap_ratio:.0%})",
            )
        elif overlap_ratio > 0.2:
            return (
                FactualClaimStatus.UNSUPPORTED,
                matched_tokens,
                f"Partially mentioned hazard concepts ({matched_tokens}) but missed key specifics.",
            )
        return (
            FactualClaimStatus.UNADDRESSED,
            [],
            f"Failed to mention required hazard concepts: {tokens}",
        )

    def _evaluate_general_proposition(
        self,
        claim_lower: str,
        response_lower: str,
    ) -> Tuple[FactualClaimStatus, List[str], str]:
        """
        Evaluates general propositions using concept overlap and numerical consistency.
        """
        # Extract numerical anchor if present in claim
        num_match = re.search(r"[-+]?\d+(?:\.\d+)?", claim_lower)
        num_str = num_match.group(0) if num_match else None

        # Clean words from claim
        words = [w for w in re.findall(r"\b[a-z]{3,}\b", claim_lower) if w not in {"the", "and", "approximately", "shows", "source"}]
        matched_words = [w for w in words if w in response_lower]

        word_overlap = len(matched_words) / len(words) if words else 0.0

        if num_str:
            num_found = num_str in response_lower
            if num_found and word_overlap >= 0.4:
                return (
                    FactualClaimStatus.CORRECT,
                    [num_str] + matched_words,
                    f"Matched number {num_str} and concept words: {matched_words}",
                )
            elif not num_found and word_overlap >= 0.5:
                # Concepts present but number missing or altered
                return (
                    FactualClaimStatus.INCORRECT,
                    matched_words,
                    f"Concept words present ({matched_words}) but expected number {num_str} was contradicted or missing.",
                )

        if word_overlap >= 0.65:
            return (
                FactualClaimStatus.CORRECT,
                matched_words,
                f"Matched proposition concepts: {matched_words} ({word_overlap:.0%})",
            )
        elif word_overlap >= 0.3:
            return (
                FactualClaimStatus.UNSUPPORTED,
                matched_words,
                f"Partially mentioned proposition concepts ({matched_words}) but incomplete.",
            )

        return (
            FactualClaimStatus.UNADDRESSED,
            [],
            f"Claim proposition unaddressed: {words}",
        )
