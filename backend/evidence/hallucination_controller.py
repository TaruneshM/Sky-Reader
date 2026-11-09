from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from backend.evidence.claim_extractor import ClaimExtractor
    from backend.evidence.claim_validator import ClaimValidator
    from backend.evidence.evidence_models import (
        ClaimValidationResult,
        EvidenceCollection,
        EvidenceSourceType,
        HallucinationReport,
        ValidationStatus,
        WeatherVariable,
    )
except ImportError:
    from evidence.claim_extractor import ClaimExtractor
    from evidence.claim_validator import ClaimValidator
    from evidence.evidence_models import (
        ClaimValidationResult,
        EvidenceCollection,
        EvidenceSourceType,
        HallucinationReport,
        ValidationStatus,
        WeatherVariable,
    )


class HallucinationController:
    """
    Hallucination Detection, Auditing, and Correction Controller.
    Evaluates claim validation results, computes hallucination metrics,
    and coordinates deterministic correction loops with transparent fallback mechanisms.
    """

    def __init__(
        self,
        claim_extractor: Optional[ClaimExtractor] = None,
        claim_validator: Optional[ClaimValidator] = None,
        contradiction_threshold: float = 0.0,
        hallucination_threshold: float = 0.25,
    ):
        self.extractor = claim_extractor or ClaimExtractor()
        self.validator = claim_validator or ClaimValidator()
        self.contradiction_threshold = contradiction_threshold
        self.hallucination_threshold = hallucination_threshold

    def evaluate_claims(self, validation_results: List[ClaimValidationResult]) -> HallucinationReport:
        """
        Computes structured hallucination metrics and determines whether
        the AI-generated response is trustworthy.
        """
        total = len(validation_results)
        if total == 0:
            return HallucinationReport(
                total_claims=0,
                supported_claims=0,
                contradicted_claims=0,
                unsupported_claims=0,
                partially_supported_claims=0,
                hallucination_rate=0.0,
                contradiction_rate=0.0,
                unsupported_rate=0.0,
                is_trustworthy=True,
                validation_results=[],
                problematic_claims=[],
            )

        supported = sum(1 for r in validation_results if r.status == ValidationStatus.SUPPORTED)
        partially = sum(1 for r in validation_results if r.status == ValidationStatus.PARTIALLY_SUPPORTED)
        contradicted = sum(1 for r in validation_results if r.status == ValidationStatus.CONTRADICTED)
        unsupported = sum(1 for r in validation_results if r.status == ValidationStatus.INSUFFICIENT_EVIDENCE)

        contradiction_rate = round(contradicted / total, 4)
        unsupported_rate = round(unsupported / total, 4)
        # Hallucination includes both hard contradictions and unverifiable unsupported claims
        hallucination_rate = round((contradicted + unsupported) / total, 4)

        # Zero tolerance for direct contradictions; low tolerance for unverifiable claims
        is_trustworthy = (contradicted == 0) and (hallucination_rate <= self.hallucination_threshold)

        problematic = [
            r for r in validation_results
            if r.status in (ValidationStatus.CONTRADICTED, ValidationStatus.INSUFFICIENT_EVIDENCE)
        ]

        return HallucinationReport(
            total_claims=total,
            supported_claims=supported,
            contradicted_claims=contradicted,
            unsupported_claims=unsupported,
            partially_supported_claims=partially,
            hallucination_rate=hallucination_rate,
            contradiction_rate=contradiction_rate,
            unsupported_rate=unsupported_rate,
            is_trustworthy=is_trustworthy,
            validation_results=validation_results,
            problematic_claims=problematic,
        )

    def generate_correction_prompt(
        self,
        report: HallucinationReport,
        original_query: str,
        evidence: EvidenceCollection,
    ) -> str:
        """
        Builds a targeted correction prompt listing contradictory claims
        and referencing ground-truth evidence values.
        """
        issues: List[str] = []
        for prob in report.problematic_claims:
            claim = prob.claim
            status = prob.status.value
            expl = prob.explanation
            issues.append(f"- Claim: '{claim.statement}' (Variable: {claim.variable.value}, Claimed: {claim.claimed_value})\n  Issue ({status}): {expl}")

        issues_str = "\n".join(issues)

        # Summarize actual evidence ground truth
        summary_lines = []
        for it in evidence.items[:15]:  # include prominent evidence
            summary_lines.append(f"- {it.variable.value} ({it.time_period}): {it.value} {it.unit or ''} [{it.source_type.value}]")
        evidence_str = "\n".join(summary_lines)

        return (
            f"Your previous response to the user query '{original_query}' failed meteorological verification.\n\n"
            f"The following factual errors or unsupported claims were detected:\n"
            f"{issues_str}\n\n"
            f"VERIFIED GROUND-TRUTH METEOROLOGICAL EVIDENCE:\n"
            f"{evidence_str}\n\n"
            f"INSTRUCTIONS FOR CORRECTION:\n"
            f"1. Rewrite the answer to resolve the user's question accurately.\n"
            f"2. Use ONLY the verified measurements and analysis values provided above.\n"
            f"3. Do NOT invent or extrapolate unverified weather numbers.\n"
            f"4. Directly correct any previously contradictory numbers or trends."
        )

    def generate_safe_fallback(
        self,
        original_query: str,
        evidence: EvidenceCollection,
        report: Optional[HallucinationReport] = None,
    ) -> str:
        """
        Generates a deterministic, trustworthy fallback response directly
        derived from verified evidence when LLM regeneration fails or is exhausted.
        """
        loc = evidence.location_name or "the requested location"

        temp_items = evidence.find_by_variable(WeatherVariable.TEMPERATURE)
        hum_items = evidence.find_by_variable(WeatherVariable.HUMIDITY)
        wind_items = evidence.find_by_variable(WeatherVariable.WIND_SPEED)
        rain_prob_items = evidence.find_by_variable(WeatherVariable.PRECIPITATION_PROBABILITY)
        umbrella_items = evidence.find_by_variable(WeatherVariable.UMBRELLA_NEED)

        lines = [f"Based on verified meteorological observations for {loc}:"]
        if temp_items:
            lines.append(f"- Current Temperature: {temp_items[0].value} {temp_items[0].unit or '°C'}")
        if hum_items:
            lines.append(f"- Relative Humidity: {hum_items[0].value}%")
        if wind_items:
            lines.append(f"- Wind Speed: {wind_items[0].value} km/h")
        if rain_prob_items:
            max_rain_prob = max([float(it.value) for it in rain_prob_items if isinstance(it.value, (int, float))], default=0.0)
            lines.append(f"- Peak Precipitation Probability: {max_rain_prob}%")
        if umbrella_items:
            if umbrella_items[0].value is True:
                lines.append("- Recommendation: Carry an umbrella due to expected rain and precipitation.")
            else:
                lines.append("- Recommendation: You do not need an umbrella as rain or precipitation probability is low.")

        lines.append(
            "\n*(Note: This response was generated directly from verified meteorological evidence "
            "after automated audit identified discrepancies in generative text.)*"
        )
        return "\n".join(lines)

    async def verify_and_correct(
        self,
        query: str,
        response_text: str,
        evidence: EvidenceCollection,
        regenerate_fn: Optional[Callable[[str], Any]] = None,
        max_retries: int = 2,
    ) -> Tuple[str, HallucinationReport, int]:
        """
        Audits the response, executes up to max_retries corrections if hallucinations
        are detected, and returns a verified trustworthy response or safe fallback.
        """
        current_text = response_text
        attempts = 0

        while True:
            claims = self.extractor.extract_claims(current_text, default_location=evidence.location_name)
            validation_results = self.validator.validate_all(claims, evidence)
            report = self.evaluate_claims(validation_results)

            if report.is_trustworthy or attempts >= max_retries or regenerate_fn is None:
                # If trustworthy, return text
                if report.is_trustworthy:
                    return current_text, report, attempts

                # If reached max retries and still not trustworthy, use safe fallback
                if attempts >= max_retries:
                    fallback = self.generate_safe_fallback(query, evidence, report)
                    # Re-audit fallback to ensure 100% clean report
                    fb_claims = self.extractor.extract_claims(fallback, default_location=evidence.location_name)
                    fb_results = self.validator.validate_all(fb_claims, evidence)
                    fb_report = self.evaluate_claims(fb_results)
                    return fallback, fb_report, attempts

                return current_text, report, attempts

            # Trigger regeneration attempt
            attempts += 1
            correction_prompt = self.generate_correction_prompt(report, query, evidence)

            try:
                # Call regeneration function (can be async or sync)
                new_text = regenerate_fn(correction_prompt)
                if hasattr(new_text, "__await__"):
                    new_text = await new_text
                current_text = str(new_text)
            except Exception as e:
                # If regeneration call fails, break and fall back immediately
                fallback = self.generate_safe_fallback(query, evidence, report)
                fb_claims = self.extractor.extract_claims(fallback, default_location=evidence.location_name)
                fb_results = self.validator.validate_all(fb_claims, evidence)
                fb_report = self.evaluate_claims(fb_results)
                return fallback, fb_report, attempts
