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
                is_trustworthy=False,
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
        is_trustworthy = (supported == total)

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

    def audit(self, text: str, evidence: EvidenceCollection):
        claims = self.extractor.extract_claims(text, default_location=evidence.location_name)
        return claims, self.evaluate_claims(self.validator.validate_all(claims, evidence))

    def generate_safe_fallback(
        self,
        original_query: str,
        evidence: EvidenceCollection,
        report: Optional[HallucinationReport] = None,
    ) -> str:
        """Summarize measurements only when their city and requested window are established."""
        try:
            from backend.agent.router import parse_weather_request, synthesize_deterministic_weather_buddy_response
        except ImportError:
            from agent.router import parse_weather_request, synthesize_deterministic_weather_buddy_response

        if not evidence.location_name:
            return "I couldn’t verify the requested weather for each location and forecast period."
        request = parse_weather_request(original_query)
        period = request.period
        fields = {
            WeatherVariable.TEMPERATURE: ("temperature_2m", "temperatures"),
            WeatherVariable.APPARENT_TEMPERATURE: ("apparent_temperature", "apparent_temperatures"),
            WeatherVariable.HUMIDITY: ("relative_humidity_2m", "humidities"),
            WeatherVariable.WIND_GUST: ("wind_gusts_10m", "gusts"),
            WeatherVariable.WIND_SPEED: ("wind_speed_10m", "wind_speeds"),
            WeatherVariable.PRECIPITATION_PROBABILITY: ("precipitation_probability", "rain_probabilities"),
            WeatherVariable.PRECIPITATION_AMOUNT: ("precipitation", "rain_amounts"),
        }
        current = {}
        forecast = {}
        risk = None
        for item in evidence.items:
            if item.location and item.location.casefold() != evidence.location_name.casefold():
                continue
            bound = item.metadata.get("requested_period")
            if item.variable == WeatherVariable.TRAVEL_SUITABILITY and bound == period and item.unit == "risk_level":
                risk = {"overall_risk_level": item.value, "detected_risks": [
                    {"condition": condition} for condition in item.metadata.get("detected_risks", [])
                ]}
            if item.variable not in fields:
                continue
            observed_key, forecast_key = fields[item.variable]
            if item.source_type.value == "observed" and period == "current":
                current[observed_key] = item.value
            elif bound == period and item.source_type.value == "forecast":
                forecast.setdefault(forecast_key, []).append(item.value)
        answer = synthesize_deterministic_weather_buddy_response(
            ("temperature" if request.intent == "current_weather" and "temperature" in original_query.casefold()
             else request.intent or "current_weather"), evidence.location_name,
            {"current": current}, forecast if forecast else None, risk,
            period=period, activity=request.activity,
        )
        return answer + " The automated audit identified discrepancies in the earlier draft."

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
            _, report = self.audit(current_text, evidence)

            if report.is_trustworthy or attempts >= max_retries or regenerate_fn is None:
                # If trustworthy, return text
                if report.is_trustworthy:
                    return current_text, report, attempts

                # If reached max retries and still not trustworthy, use safe fallback
                if attempts >= max_retries:
                    fallback = self.generate_safe_fallback(query, evidence, report)
                    # Re-audit fallback to ensure 100% clean report
                    _, fb_report = self.audit(fallback, evidence)
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
                _, fb_report = self.audit(fallback, evidence)
                return fallback, fb_report, attempts
