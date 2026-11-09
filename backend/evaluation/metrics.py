import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure backend directory is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from backend.evidence.evidence_models import (
        ClaimValidationResult,
        EvidenceCollection,
        ValidationStatus,
        WeatherVariable,
    )
    from backend.evidence.claim_extractor import ClaimExtractor
    from backend.evidence.claim_validator import ClaimValidator
except ImportError:
    from evidence.evidence_models import (
        ClaimValidationResult,
        EvidenceCollection,
        ValidationStatus,
        WeatherVariable,
    )
    from evidence.claim_extractor import ClaimExtractor
    from evidence.claim_validator import ClaimValidator


def calculate_claim_grounding(validation_results: List[ClaimValidationResult]) -> float:
    """
    Computes the Claim Grounding Ratio (0.0 to 1.0).
    The proportion of extracted factual claims that are supported or partially supported.
    """
    if not validation_results:
        return 1.0
    grounded = sum(
        1 for r in validation_results
        if r.status in (ValidationStatus.SUPPORTED, ValidationStatus.PARTIALLY_SUPPORTED)
    )
    return round(grounded / len(validation_results), 4)


def calculate_hallucination_rate(validation_results: List[ClaimValidationResult]) -> float:
    """
    Computes the Hallucination Rate (0.0 to 1.0).
    The proportion of extracted factual claims that are contradicted or ungrounded.
    """
    if not validation_results:
        return 0.0
    ungrounded = sum(
        1 for r in validation_results
        if r.status in (ValidationStatus.CONTRADICTED, ValidationStatus.INSUFFICIENT_EVIDENCE)
    )
    return round(ungrounded / len(validation_results), 4)


def calculate_contradiction_rate(validation_results: List[ClaimValidationResult]) -> float:
    """
    Computes the Hard Contradiction Rate (0.0 to 1.0).
    The proportion of claims that directly contradict meteorological evidence.
    """
    if not validation_results:
        return 0.0
    contradicted = sum(1 for r in validation_results if r.status == ValidationStatus.CONTRADICTED)
    return round(contradicted / len(validation_results), 4)


def calculate_evidence_coverage(
    evidence: EvidenceCollection,
    target_variables: Optional[List[WeatherVariable]] = None,
) -> float:
    """
    Measures the breadth of meteorological variables represented in the evidence collection.
    """
    if target_variables is None:
        target_variables = [
            WeatherVariable.TEMPERATURE,
            WeatherVariable.HUMIDITY,
            WeatherVariable.PRECIPITATION_PROBABILITY,
            WeatherVariable.PRECIPITATION_AMOUNT,
            WeatherVariable.WIND_SPEED,
            WeatherVariable.PRESSURE,
            WeatherVariable.CLOUD_COVER,
            WeatherVariable.TEMPERATURE_TREND,
            WeatherVariable.UMBRELLA_NEED,
        ]
    if not target_variables:
        return 1.0

    present_vars = {it.variable for it in evidence.items}
    covered = sum(1 for v in target_variables if v in present_vars)
    return round(covered / len(target_variables), 4)


def calculate_validation_accuracy(
    predicted_statuses: List[ValidationStatus],
    true_statuses: List[ValidationStatus],
) -> Dict[str, float]:
    """
    Calculates evaluation metrics (accuracy, precision, recall, F1) comparing predicted
    validation statuses against ground-truth human annotations.
    """
    if len(predicted_statuses) != len(true_statuses) or not predicted_statuses:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}

    total = len(predicted_statuses)
    correct = sum(1 for p, t in zip(predicted_statuses, true_statuses) if p == t)
    accuracy = round(correct / total, 4)

    # Binary classification: Grounded (SUPPORTED/PARTIALLY) vs Hallucinated (CONTRADICTED/INSUFFICIENT)
    tp = sum(1 for p, t in zip(predicted_statuses, true_statuses)
             if p in (ValidationStatus.SUPPORTED, ValidationStatus.PARTIALLY_SUPPORTED)
             and t in (ValidationStatus.SUPPORTED, ValidationStatus.PARTIALLY_SUPPORTED))
    fp = sum(1 for p, t in zip(predicted_statuses, true_statuses)
             if p in (ValidationStatus.SUPPORTED, ValidationStatus.PARTIALLY_SUPPORTED)
             and t in (ValidationStatus.CONTRADICTED, ValidationStatus.INSUFFICIENT_EVIDENCE))
    fn = sum(1 for p, t in zip(predicted_statuses, true_statuses)
             if p in (ValidationStatus.CONTRADICTED, ValidationStatus.INSUFFICIENT_EVIDENCE)
             and t in (ValidationStatus.SUPPORTED, ValidationStatus.PARTIALLY_SUPPORTED))

    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    f1 = round(2 * (precision * recall) / (precision + recall), 4) if (precision + recall) > 0 else 0.0

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def calculate_correction_success_rate(total_hallucinated: int, successfully_corrected: int) -> float:
    """Computes the success rate of the hallucination feedback and correction loop."""
    if total_hallucinated <= 0:
        return 1.0
    return round(successfully_corrected / total_hallucinated, 4)


def measure_validation_overhead(text: str, evidence: EvidenceCollection) -> Dict[str, Any]:
    """
    Measures the computational execution time (in milliseconds) for deterministic
    claim extraction and validation.
    """
    extractor = ClaimExtractor()
    validator = ClaimValidator()

    t0 = time.perf_counter()
    claims = extractor.extract_claims(text, default_location=evidence.location_name)
    t1 = time.perf_counter()
    val_results = validator.validate_all(claims, evidence)
    t2 = time.perf_counter()

    extraction_ms = round((t1 - t0) * 1000, 3)
    validation_ms = round((t2 - t1) * 1000, 3)
    total_ms = round((t2 - t0) * 1000, 3)

    return {
        "claim_count": len(claims),
        "extraction_ms": extraction_ms,
        "validation_ms": validation_ms,
        "total_overhead_ms": total_ms,
    }
