from backend.evaluation.metrics.base import (
    BaseMetricEvaluator,
    BaseMetricResult,
    FactualClaimStatus,
    MetricStatus,
    NumericalMatchStatus,
)
from backend.evaluation.metrics.numerical import (
    NumericalAccuracyEvaluator,
    NumericalMetricResult,
    VariableNumericalResult,
)
from backend.evaluation.metrics.factual import (
    ClaimEvaluationItem,
    FactualAccuracyEvaluator,
    FactualMetricResult,
)
from backend.evaluation.metrics.hallucination import (
    HallucinationEvaluator,
    HallucinationMetricResult,
    ProblematicClaimItem,
)
from backend.evaluation.metrics.evidence import (
    EvidenceGroundingEvaluator,
    EvidenceMetricResult,
)
from backend.evaluation.metrics.risk import (
    RiskAssessmentEvaluator,
    RiskMetricResult,
)
from backend.evaluation.metrics.performance import (
    PerformanceEvaluator,
    PerformanceMetricResult,
)
from backend.evaluation.metrics.completeness import (
    CompletenessMetricResult,
    ResponseCompletenessEvaluator,
)
from backend.evaluation.metrics.aggregator import (
    AggregatedMetricSummary,
    CaseMetricScores,
    MetricsEngine,
    RunEvaluationReport,
)
from backend.evaluation.metrics.legacy import (
    calculate_claim_grounding,
    calculate_contradiction_rate,
    calculate_correction_success_rate,
    calculate_evidence_coverage,
    calculate_hallucination_rate,
    calculate_validation_accuracy,
    measure_validation_overhead,
)

__all__ = [
    # Base
    "BaseMetricEvaluator",
    "BaseMetricResult",
    "MetricStatus",
    "NumericalMatchStatus",
    "FactualClaimStatus",
    # Numerical
    "NumericalAccuracyEvaluator",
    "NumericalMetricResult",
    "VariableNumericalResult",
    # Factual
    "FactualAccuracyEvaluator",
    "FactualMetricResult",
    "ClaimEvaluationItem",
    # Hallucination
    "HallucinationEvaluator",
    "HallucinationMetricResult",
    "ProblematicClaimItem",
    # Evidence
    "EvidenceGroundingEvaluator",
    "EvidenceMetricResult",
    # Risk
    "RiskAssessmentEvaluator",
    "RiskMetricResult",
    # Performance
    "PerformanceEvaluator",
    "PerformanceMetricResult",
    # Completeness
    "ResponseCompletenessEvaluator",
    "CompletenessMetricResult",
    # Aggregator
    "MetricsEngine",
    "CaseMetricScores",
    "AggregatedMetricSummary",
    "RunEvaluationReport",
    # Legacy Phase 4 compatibility
    "calculate_claim_grounding",
    "calculate_hallucination_rate",
    "calculate_contradiction_rate",
    "calculate_evidence_coverage",
    "calculate_validation_accuracy",
    "calculate_correction_success_rate",
    "measure_validation_overhead",
]
