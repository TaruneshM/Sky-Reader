import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

try:
    from backend.evaluation.models import EvaluationDataset, FixtureCollection, TestCase, WeatherFixture
    from backend.evaluation.result_models import EvaluationResult, ExecutionStatus
    from backend.evaluation.metrics.base import MetricStatus
    from backend.evaluation.metrics.numerical import NumericalAccuracyEvaluator, NumericalMetricResult
    from backend.evaluation.metrics.factual import FactualAccuracyEvaluator, FactualMetricResult
    from backend.evaluation.metrics.hallucination import HallucinationEvaluator, HallucinationMetricResult
    from backend.evaluation.metrics.evidence import EvidenceGroundingEvaluator, EvidenceMetricResult
    from backend.evaluation.metrics.risk import RiskAssessmentEvaluator, RiskMetricResult
    from backend.evaluation.metrics.performance import PerformanceEvaluator, PerformanceMetricResult
    from backend.evaluation.metrics.completeness import ResponseCompletenessEvaluator, CompletenessMetricResult
except ImportError:
    from evaluation.models import EvaluationDataset, FixtureCollection, TestCase, WeatherFixture
    from evaluation.result_models import EvaluationResult, ExecutionStatus
    from evaluation.metrics.base import MetricStatus
    from evaluation.metrics.numerical import NumericalAccuracyEvaluator, NumericalMetricResult
    from evaluation.metrics.factual import FactualAccuracyEvaluator, FactualMetricResult
    from evaluation.metrics.hallucination import HallucinationEvaluator, HallucinationMetricResult
    from evaluation.metrics.evidence import EvidenceGroundingEvaluator, EvidenceMetricResult
    from evaluation.metrics.risk import RiskAssessmentEvaluator, RiskMetricResult
    from evaluation.metrics.performance import PerformanceEvaluator, PerformanceMetricResult
    from evaluation.metrics.completeness import ResponseCompletenessEvaluator, CompletenessMetricResult


class CaseMetricScores(BaseModel):
    """
    Consolidated metric score card for a single execution result on a benchmark test case.
    Preserves raw diagnostics and explicit evaluability status.
    """
    run_id: str
    test_case_id: str
    system: str
    category: str
    is_evaluable: bool = True
    reason_unevaluable: Optional[str] = None
    performance: PerformanceMetricResult
    numerical: NumericalMetricResult
    factual: FactualMetricResult
    hallucination: HallucinationMetricResult
    evidence: EvidenceMetricResult
    risk: RiskMetricResult
    completeness: CompletenessMetricResult


class AggregatedMetricSummary(BaseModel):
    """
    Multi-dimensional metric aggregation reporting denominators, evaluable counts,
    and distinct sub-metric scorecards without arbitrary composite blending.
    """
    total_cases: int = 0
    evaluable_cases: int = 0
    unevaluable_cases: int = 0

    # Execution health
    success_rate: float = 0.0
    failure_rate: float = 0.0
    timeout_rate: float = 0.0

    # Numerical accuracy
    numerical_cases_evaluated: int = 0
    mean_numerical_accuracy: Optional[float] = None
    total_expected_numbers: int = 0
    correct_numbers_count: int = 0
    incorrect_numbers_count: int = 0
    missing_numbers_count: int = 0
    mean_mae: Optional[float] = None

    # Factual accuracy
    factual_cases_evaluated: int = 0
    mean_factual_accuracy: Optional[float] = None
    total_expected_facts: int = 0
    correct_facts_count: int = 0
    incorrect_facts_count: int = 0
    unaddressed_facts_count: int = 0
    unsupported_facts_count: int = 0

    # Hallucination
    hallucination_cases_evaluated: int = 0
    mean_hallucination_rate: float = 0.0
    mean_contradiction_rate: float = 0.0
    mean_unsupported_rate: float = 0.0
    clean_case_ratio: float = 0.0

    # Evidence grounding
    evidence_availability_rate: float = 0.0
    evidence_usage_rate: float = 0.0
    valid_proof_rate: Optional[float] = None
    mean_grounding_ratio: Optional[float] = None

    # Risk accuracy
    applicable_risk_cases: int = 0
    risk_classification_accuracy: Optional[float] = None
    severity_underreported_count: int = 0
    severity_overreported_count: int = 0
    risk_confusion_matrix: Dict[str, Dict[str, int]] = Field(default_factory=dict)

    # Runtime performance
    mean_latency_ms: float = 0.0
    median_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    total_retries: int = 0

    # Completeness
    mean_completeness_score: float = 0.0
    fully_complete_ratio: float = 0.0


class RunEvaluationReport(BaseModel):
    """
    Complete evaluation report structured by overall run, system slice, and category slice.
    """
    run_id: str
    evaluated_at: str
    overall_summary: AggregatedMetricSummary
    by_system: Dict[str, AggregatedMetricSummary] = Field(default_factory=dict)
    by_category: Dict[str, AggregatedMetricSummary] = Field(default_factory=dict)
    case_scores: List[CaseMetricScores] = Field(default_factory=list)


class MetricsEngine:
    """
    Main evaluation orchestrator that computes all Phase 7.3 metrics across test results,
    producing structured, reproducible, and verifiable metric reports.
    """

    def __init__(self):
        self.performance_evaluator = PerformanceEvaluator()
        self.numerical_evaluator = NumericalAccuracyEvaluator()
        self.factual_evaluator = FactualAccuracyEvaluator()
        self.hallucination_evaluator = HallucinationEvaluator()
        self.evidence_evaluator = EvidenceGroundingEvaluator()
        self.risk_evaluator = RiskAssessmentEvaluator()
        self.completeness_evaluator = ResponseCompletenessEvaluator()

    def evaluate_case(
        self,
        result: EvaluationResult,
        test_case: TestCase,
        fixture: Optional[WeatherFixture] = None,
    ) -> CaseMetricScores:
        """
        Evaluates a single execution result on a test case against all 7 metric dimensions.
        """
        perf = self.performance_evaluator.evaluate(result, test_case, fixture)
        num = self.numerical_evaluator.evaluate(result, test_case, fixture)
        fact = self.factual_evaluator.evaluate(result, test_case, fixture)
        hall = self.hallucination_evaluator.evaluate(result, test_case, fixture)
        evid = self.evidence_evaluator.evaluate(result, test_case, fixture)
        risk = self.risk_evaluator.evaluate(result, test_case, fixture)
        comp = self.completeness_evaluator.evaluate(result, test_case, fixture)

        is_evaluable = (result.execution_status == ExecutionStatus.COMPLETED)
        reason = None if is_evaluable else f"Execution status: {result.execution_status.value} ({result.error_type}: {result.error_message})"

        return CaseMetricScores(
            run_id=result.run_id,
            test_case_id=test_case.id,
            system=result.system,
            category=test_case.category.value,
            is_evaluable=is_evaluable,
            reason_unevaluable=reason,
            performance=perf,
            numerical=num,
            factual=fact,
            hallucination=hall,
            evidence=evid,
            risk=risk,
            completeness=comp,
        )

    def aggregate(self, scores: List[CaseMetricScores]) -> AggregatedMetricSummary:
        """
        Aggregates a slice of CaseMetricScores into an AggregatedMetricSummary with explicit denominators.
        """
        total = len(scores)
        if total == 0:
            return AggregatedMetricSummary()

        evaluable = [s for s in scores if s.is_evaluable]
        unevaluable = [s for s in scores if not s.is_evaluable]

        # Health
        completed = sum(1 for s in scores if s.performance.is_successful)
        failed = sum(1 for s in scores if s.performance.is_failure and not s.performance.is_timeout)
        timeouts = sum(1 for s in scores if s.performance.is_timeout)

        # Numerical
        num_scores = [s.numerical for s in evaluable if s.numerical.is_evaluable and s.numerical.accuracy is not None]
        mean_num_acc = (
            round(sum(s.accuracy for s in num_scores) / len(num_scores), 4)
            if num_scores else None
        )
        total_exp_nums = sum(s.numerical.total_expected for s in evaluable if s.numerical.is_evaluable)
        corr_nums = sum(s.numerical.correct_count for s in evaluable if s.numerical.is_evaluable)
        incorr_nums = sum(s.numerical.incorrect_count for s in evaluable if s.numerical.is_evaluable)
        miss_nums = sum(s.numerical.missing_count for s in evaluable if s.numerical.is_evaluable)
        mae_values = [s.numerical.mean_absolute_error for s in evaluable if s.numerical.is_evaluable and s.numerical.mean_absolute_error is not None]
        mean_mae = round(sum(mae_values) / len(mae_values), 4) if mae_values else None

        # Factual
        fact_scores = [s.factual for s in evaluable if s.factual.is_evaluable and s.factual.accuracy is not None]
        mean_fact_acc = (
            round(sum(s.accuracy for s in fact_scores) / len(fact_scores), 4)
            if fact_scores else None
        )
        total_exp_facts = sum(s.factual.total_expected for s in evaluable if s.factual.is_evaluable)
        corr_facts = sum(s.factual.correct_count for s in evaluable if s.factual.is_evaluable)
        incorr_facts = sum(s.factual.incorrect_count for s in evaluable if s.factual.is_evaluable)
        unaddr_facts = sum(s.factual.unaddressed_count for s in evaluable if s.factual.is_evaluable)
        unsupp_facts = sum(s.factual.unsupported_count for s in evaluable if s.factual.is_evaluable)

        # Hallucination
        hall_scores = [s.hallucination for s in evaluable if s.hallucination.is_evaluable and s.hallucination.total_claims_evaluated > 0]
        mean_hall_rate = (
            round(sum(s.hallucination_rate for s in hall_scores) / len(hall_scores), 4)
            if hall_scores else 0.0
        )
        mean_contra_rate = (
            round(sum(s.contradiction_rate for s in hall_scores) / len(hall_scores), 4)
            if hall_scores else 0.0
        )
        mean_unsupp_rate = (
            round(sum(s.unsupported_rate for s in hall_scores) / len(hall_scores), 4)
            if hall_scores else 0.0
        )
        clean_cases = sum(1 for s in evaluable if s.hallucination.is_evaluable and s.hallucination.is_hallucination_free)
        clean_ratio = round(clean_cases / len(evaluable), 4) if evaluable else 0.0

        # Evidence Grounding
        ev_available_count = sum(1 for s in evaluable if s.evidence.evidence_available)
        ev_used_count = sum(1 for s in evaluable if s.evidence.evidence_used)
        ev_avail_rate = round(ev_available_count / len(evaluable), 4) if evaluable else 0.0
        ev_used_rate = round(ev_used_count / len(evaluable), 4) if evaluable else 0.0

        proof_cases = [s.evidence for s in evaluable if s.evidence.proof_valid is not None]
        valid_proof_rate = (
            round(sum(1 for s in proof_cases if s.proof_valid is True) / len(proof_cases), 4)
            if proof_cases else None
        )
        grounding_scores = [s.evidence.grounding_ratio for s in evaluable if s.evidence.grounding_ratio is not None]
        mean_grounding = (
            round(sum(grounding_scores) / len(grounding_scores), 4)
            if grounding_scores else None
        )

        # Risk Assessment
        risk_cases = [s.risk for s in evaluable if s.risk.is_applicable and s.risk.classification_match is not None]
        risk_accuracy = (
            round(sum(1 for s in risk_cases if s.classification_match is True) / len(risk_cases), 4)
            if risk_cases else None
        )
        underreported_count = sum(1 for s in risk_cases if s.underreported is True)
        overreported_count = sum(1 for s in risk_cases if s.overreported is True)

        # Build confusion matrix for risk levels
        cm: Dict[str, Dict[str, int]] = {}
        for r in risk_cases:
            if r.confusion_matrix_entry:
                act = r.confusion_matrix_entry.get("actual", "UNKNOWN")
                pred = r.confusion_matrix_entry.get("predicted", "UNKNOWN")
                if act not in cm:
                    cm[act] = {}
                cm[act][pred] = cm[act].get(pred, 0) + 1

        # Runtime Performance
        latencies = [s.performance.latency_ms for s in scores if s.performance.latency_ms > 0]
        mean_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
        median_latency = round(statistics.median(latencies), 2) if latencies else 0.0
        if len(latencies) >= 2:
            sorted_lat = sorted(latencies)
            p95_idx = int(0.95 * len(sorted_lat))
            p95_latency = round(sorted_lat[min(p95_idx, len(sorted_lat) - 1)], 2)
        else:
            p95_latency = mean_latency
        total_retries = sum(s.performance.retry_count for s in scores)

        # Completeness
        comp_scores = [s.completeness.completeness_score for s in evaluable if s.completeness.is_evaluable]
        mean_comp = round(sum(comp_scores) / len(comp_scores), 4) if comp_scores else 0.0
        fully_complete = sum(1 for s in evaluable if s.completeness.is_complete)
        fully_comp_ratio = round(fully_complete / len(evaluable), 4) if evaluable else 0.0

        return AggregatedMetricSummary(
            total_cases=total,
            evaluable_cases=len(evaluable),
            unevaluable_cases=len(unevaluable),
            success_rate=round(completed / total, 4) if total > 0 else 0.0,
            failure_rate=round(failed / total, 4) if total > 0 else 0.0,
            timeout_rate=round(timeouts / total, 4) if total > 0 else 0.0,
            numerical_cases_evaluated=len(num_scores),
            mean_numerical_accuracy=mean_num_acc,
            total_expected_numbers=total_exp_nums,
            correct_numbers_count=corr_nums,
            incorrect_numbers_count=incorr_nums,
            missing_numbers_count=miss_nums,
            mean_mae=mean_mae,
            factual_cases_evaluated=len(fact_scores),
            mean_factual_accuracy=mean_fact_acc,
            total_expected_facts=total_exp_facts,
            correct_facts_count=corr_facts,
            incorrect_facts_count=incorr_facts,
            unaddressed_facts_count=unaddr_facts,
            unsupported_facts_count=unsupp_facts,
            hallucination_cases_evaluated=len(hall_scores),
            mean_hallucination_rate=mean_hall_rate,
            mean_contradiction_rate=mean_contra_rate,
            mean_unsupported_rate=mean_unsupp_rate,
            clean_case_ratio=clean_ratio,
            evidence_availability_rate=ev_avail_rate,
            evidence_usage_rate=ev_used_rate,
            valid_proof_rate=valid_proof_rate,
            mean_grounding_ratio=mean_grounding,
            applicable_risk_cases=len(risk_cases),
            risk_classification_accuracy=risk_accuracy,
            severity_underreported_count=underreported_count,
            severity_overreported_count=overreported_count,
            risk_confusion_matrix=cm,
            mean_latency_ms=mean_latency,
            median_latency_ms=median_latency,
            p95_latency_ms=p95_latency,
            total_retries=total_retries,
            mean_completeness_score=mean_comp,
            fully_complete_ratio=fully_comp_ratio,
        )

    def evaluate_run(
        self,
        results: List[EvaluationResult],
        dataset: EvaluationDataset,
        fixtures: Optional[FixtureCollection] = None,
    ) -> RunEvaluationReport:
        """
        Processes a full batch of EvaluationResult records for a run ID,
        generating per-case scores and aggregated summaries sliced by system and category.
        """
        if not results:
            now_iso = datetime.now(timezone.utc).isoformat()
            return RunEvaluationReport(
                run_id="empty_run",
                evaluated_at=now_iso,
                overall_summary=AggregatedMetricSummary(),
            )

        run_id = results[0].run_id
        now_iso = datetime.now(timezone.utc).isoformat()

        # Build lookup maps for fast matching
        tc_map = {tc.id: tc for tc in dataset.test_cases}
        fix_map = fixtures.fixtures if fixtures else {}

        case_scores: List[CaseMetricScores] = []

        for res in results:
            tc = tc_map.get(res.test_case_id)
            if not tc:
                # Handle unexpected or deleted test case ID gracefully
                continue
            fix = fix_map.get(res.fixture_id) if res.fixture_id else None
            score = self.evaluate_case(res, tc, fix)
            case_scores.append(score)

        # 1. Overall Summary
        overall_summary = self.aggregate(case_scores)

        # 2. Slice by System
        by_system: Dict[str, AggregatedMetricSummary] = {}
        distinct_systems = sorted(list(set(s.system for s in case_scores)))
        for sys_name in distinct_systems:
            sys_scores = [s for s in case_scores if s.system == sys_name]
            by_system[sys_name] = self.aggregate(sys_scores)

        # 3. Slice by Category
        by_category: Dict[str, AggregatedMetricSummary] = {}
        distinct_cats = sorted(list(set(s.category for s in case_scores)))
        for cat_name in distinct_cats:
            cat_scores = [s for s in case_scores if s.category == cat_name]
            by_category[cat_name] = self.aggregate(cat_scores)

        return RunEvaluationReport(
            run_id=run_id,
            evaluated_at=now_iso,
            overall_summary=overall_summary,
            by_system=by_system,
            by_category=by_category,
            case_scores=case_scores,
        )

    def save_report(self, report: RunEvaluationReport, output_file: Path) -> Path:
        """
        Persists a RunEvaluationReport to JSON.
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))
        return output_path
