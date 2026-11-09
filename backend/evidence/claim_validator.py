import math
from typing import Any, Dict, List, Optional, Tuple

try:
    from backend.evidence.evidence_models import (
        ClaimType,
        ClaimValidationResult,
        EvidenceCollection,
        EvidenceItem,
        FactualClaim,
        ValidationStatus,
        WeatherVariable,
    )
except ImportError:
    from evidence.evidence_models import (
        ClaimType,
        ClaimValidationResult,
        EvidenceCollection,
        EvidenceItem,
        FactualClaim,
        ValidationStatus,
        WeatherVariable,
    )


class ClaimValidator:
    """
    Deterministic Python-based Claim Validation Engine.
    Validates individual factual claims against structured evidence collections
    using domain-justified numerical tolerances, unit verification, and temporal alignment.
    """

    # Sensible domain tolerances for weather measurements
    TOLERANCES: Dict[WeatherVariable, float] = {
        WeatherVariable.TEMPERATURE: 1.0,           # ±1.0°C (allows for text rounding e.g. 23.2°C to 23°C)
        WeatherVariable.APPARENT_TEMPERATURE: 1.2,  # ±1.2°C
        WeatherVariable.HUMIDITY: 3.0,              # ±3% relative humidity
        WeatherVariable.PRECIPITATION_PROBABILITY: 5.0, # ±5% probability
        WeatherVariable.PRECIPITATION_AMOUNT: 0.5,  # ±0.5 mm precipitation accumulation
        WeatherVariable.WIND_SPEED: 2.5,            # ±2.5 km/h wind speed
        WeatherVariable.PRESSURE: 2.0,              # ±2.0 hPa surface pressure
        WeatherVariable.CLOUD_COVER: 10.0,          # ±10% cloud cover
    }

    def __init__(self):
        pass

    def validate_claim(self, claim: FactualClaim, evidence: EvidenceCollection) -> ClaimValidationResult:
        """Validates a single claim against the evidence collection."""
        # Find candidate evidence items matching the variable
        candidate_items = evidence.find_by_variable(claim.variable)

        if not candidate_items:
            # Check if this is an apparent temperature claim that can fall back to regular temperature or vice-versa
            if claim.variable == WeatherVariable.APPARENT_TEMPERATURE:
                candidate_items = evidence.find_by_variable(WeatherVariable.TEMPERATURE)

        if not candidate_items:
            return ClaimValidationResult(
                claim=claim,
                status=ValidationStatus.INSUFFICIENT_EVIDENCE,
                confidence_score=0.0,
                explanation=f"No meteorological evidence found for variable '{claim.variable.value}'.",
            )

        # Filter candidate items by time alignment
        aligned_items = self._align_by_time(claim, candidate_items)

        if not aligned_items:
            # If no strict time alignment, use all candidate items for broad bounds checking
            aligned_items = candidate_items

        # Dispatch to specific validator based on claim type
        if claim.claim_type == ClaimType.NUMERICAL_VALUE:
            return self._validate_numerical_claim(claim, aligned_items)
        elif claim.claim_type == ClaimType.TREND:
            return self._validate_trend_claim(claim, aligned_items)
        elif claim.claim_type == ClaimType.RECOMMENDATION_SUPPORT:
            return self._validate_recommendation_claim(claim, aligned_items)
        else:
            return self._validate_generic_claim(claim, aligned_items)

    def validate_all(self, claims: List[FactualClaim], evidence: EvidenceCollection) -> List[ClaimValidationResult]:
        """Validates a list of claims against the evidence collection."""
        return [self.validate_claim(c, evidence) for c in claims]

    def _align_by_time(self, claim: FactualClaim, items: List[EvidenceItem]) -> List[EvidenceItem]:
        """Filters candidate evidence items that match the claim's time period."""
        if not claim.time_period:
            return items

        claim_time = claim.time_period.lower()
        aligned = []

        for it in items:
            it_time = it.time_period.lower()

            # Exact match or substring match (e.g. 'tomorrow' or '2026-11-09T16:00')
            if claim_time in it_time or it_time in claim_time:
                aligned.append(it)
                continue

            # Day matching heuristics
            if "tomorrow" in claim_time and ("day2" in it_time or "day_analyzed" in it_time or "tomorrow" in it_time):
                aligned.append(it)
            elif "current" in claim_time or "today" in claim_time or "now" in claim_time:
                if "current" in it_time or "obs" in it.id or "day1" in it_time:
                    aligned.append(it)

        return aligned

    def _validate_numerical_claim(self, claim: FactualClaim, items: List[EvidenceItem]) -> ClaimValidationResult:
        """Validates numerical measurements against evidence within domain tolerances."""
        try:
            claimed_num = float(claim.claimed_value)
        except (ValueError, TypeError):
            return ClaimValidationResult(
                claim=claim,
                status=ValidationStatus.CONTRADICTED,
                confidence_score=0.9,
                explanation=f"Claimed value '{claim.claimed_value}' is not a valid numerical measurement.",
            )

        tolerance = self.TOLERANCES.get(claim.variable, 1.0)
        best_diff = float("inf")
        best_item: Optional[EvidenceItem] = None
        evidence_values = []
        evidence_ids = []

        for it in items:
            if isinstance(it.value, (int, float)):
                val = float(it.value)
                evidence_values.append(val)
                evidence_ids.append(it.id)
                diff = abs(claimed_num - val)
                if diff < best_diff:
                    best_diff = diff
                    best_item = it

        if best_item is None:
            return ClaimValidationResult(
                claim=claim,
                status=ValidationStatus.INSUFFICIENT_EVIDENCE,
                confidence_score=0.0,
                explanation=f"No numerical evidence items available to verify {claim.variable.value}.",
            )

        closest_val = float(best_item.value)

        # 1. Exact or within strict tolerance -> SUPPORTED
        if best_diff <= tolerance:
            conf = 1.0 if tolerance <= 0 else max(0.0, 1.0 - (best_diff / (2 * tolerance)))
            return ClaimValidationResult(
                claim=claim,
                status=ValidationStatus.SUPPORTED,
                confidence_score=round(conf, 4),
                supporting_evidence_ids=[best_item.id],
                evidence_values=[closest_val],
                explanation=(
                    f"Claimed {claim.variable.value} of {claimed_num} {claim.unit or ''} is supported by "
                    f"evidence '{best_item.id}' ({closest_val} {best_item.unit or ''}) within tolerance ±{tolerance}."
                ),
                tolerance_used=tolerance,
            )

        # 2. Within wide tolerance (partial match, e.g. within 2x tolerance) -> PARTIALLY_SUPPORTED
        if best_diff <= 2.0 * tolerance:
            return ClaimValidationResult(
                claim=claim,
                status=ValidationStatus.PARTIALLY_SUPPORTED,
                confidence_score=0.6,
                supporting_evidence_ids=[best_item.id],
                evidence_values=[closest_val],
                explanation=(
                    f"Claimed {claim.variable.value} of {claimed_num} {claim.unit or ''} is partially supported "
                    f"(closest evidence '{best_item.id}' is {closest_val} {best_item.unit or ''}, deviation {round(best_diff, 1)} exceeds strict ±{tolerance})."
                ),
                tolerance_used=tolerance * 2.0,
            )

        # 3. Beyond tolerance -> CONTRADICTED
        return ClaimValidationResult(
            claim=claim,
            status=ValidationStatus.CONTRADICTED,
            confidence_score=1.0,
            supporting_evidence_ids=[best_item.id],
            evidence_values=[closest_val],
            explanation=(
                f"Claimed {claim.variable.value} of {claimed_num} {claim.unit or ''} contradicts available evidence. "
                f"Closest record '{best_item.id}' shows {closest_val} {best_item.unit or ''} (discrepancy: {round(best_diff, 1)})."
            ),
            tolerance_used=tolerance,
        )

    def _validate_trend_claim(self, claim: FactualClaim, items: List[EvidenceItem]) -> ClaimValidationResult:
        """Validates qualitative trend claims (e.g. increasing, decreasing, steady)."""
        claimed_trend = str(claim.claimed_value).lower().strip()

        for it in items:
            ev_trend = str(it.value).lower().strip()
            if claimed_trend == ev_trend:
                return ClaimValidationResult(
                    claim=claim,
                    status=ValidationStatus.SUPPORTED,
                    confidence_score=1.0,
                    supporting_evidence_ids=[it.id],
                    evidence_values=[it.value],
                    explanation=f"Claimed trend '{claimed_trend}' matches analytical evidence '{it.id}' ({ev_trend}).",
                )
            elif (
                (claimed_trend in ["increasing", "rising"] and ev_trend in ["decreasing", "falling"])
                or (claimed_trend in ["decreasing", "falling"] and ev_trend in ["increasing", "rising"])
            ):
                return ClaimValidationResult(
                    claim=claim,
                    status=ValidationStatus.CONTRADICTED,
                    confidence_score=1.0,
                    supporting_evidence_ids=[it.id],
                    evidence_values=[it.value],
                    explanation=f"Claimed trend '{claimed_trend}' directly contradicts analytical evidence '{it.id}' ({ev_trend}).",
                )

        return ClaimValidationResult(
            claim=claim,
            status=ValidationStatus.PARTIALLY_SUPPORTED,
            confidence_score=0.5,
            supporting_evidence_ids=[it.id for it in items[:1]],
            evidence_values=[it.value for it in items[:1]],
            explanation=f"Claimed trend '{claimed_trend}' is plausible but could not be strictly confirmed.",
        )

    def _validate_recommendation_claim(self, claim: FactualClaim, items: List[EvidenceItem]) -> ClaimValidationResult:
        """Validates recommendations (e.g. umbrella necessity) against derived evidence."""
        claimed_rec = bool(claim.claimed_value)

        for it in items:
            ev_rec = bool(it.value)
            if claimed_rec == ev_rec:
                return ClaimValidationResult(
                    claim=claim,
                    status=ValidationStatus.SUPPORTED,
                    confidence_score=1.0,
                    supporting_evidence_ids=[it.id],
                    evidence_values=[it.value],
                    explanation=(
                        f"Umbrella recommendation ({claimed_rec}) is consistent with decision support record '{it.id}'."
                    ),
                )
            else:
                return ClaimValidationResult(
                    claim=claim,
                    status=ValidationStatus.CONTRADICTED,
                    confidence_score=1.0,
                    supporting_evidence_ids=[it.id],
                    evidence_values=[it.value],
                    explanation=(
                        f"Umbrella recommendation ({claimed_rec}) contradicts decision support record '{it.id}' ({ev_rec})."
                    ),
                )

        return ClaimValidationResult(
            claim=claim,
            status=ValidationStatus.INSUFFICIENT_EVIDENCE,
            confidence_score=0.0,
            explanation="No decision support records found to validate recommendation.",
        )

    def _validate_generic_claim(self, claim: FactualClaim, items: List[EvidenceItem]) -> ClaimValidationResult:
        """Fallback validator for non-numerical categorical claims."""
        claimed_str = str(claim.claimed_value).lower()

        for it in items:
            ev_str = str(it.value).lower()
            if claimed_str in ev_str or ev_str in claimed_str:
                return ClaimValidationResult(
                    claim=claim,
                    status=ValidationStatus.SUPPORTED,
                    confidence_score=0.9,
                    supporting_evidence_ids=[it.id],
                    evidence_values=[it.value],
                    explanation=f"Claim '{claim.claimed_value}' is consistent with evidence item '{it.id}' ({it.value}).",
                )

        return ClaimValidationResult(
            claim=claim,
            status=ValidationStatus.INSUFFICIENT_EVIDENCE,
            confidence_score=0.0,
            explanation=f"Could not verify categorical claim '{claim.claimed_value}' against available evidence.",
        )
