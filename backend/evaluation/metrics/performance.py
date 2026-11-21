from typing import Optional
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


class PerformanceMetricResult(BaseMetricResult):
    """
    Evaluation output capturing operational performance, latency, retry counts, and execution health.
    """
    latency_ms: float = 0.0
    retry_count: int = 0
    execution_status: ExecutionStatus = ExecutionStatus.COMPLETED
    is_successful: bool = True
    is_timeout: bool = False
    is_failure: bool = False
    tool_call_count: int = 0
    error_type: Optional[str] = None
    error_message: Optional[str] = None


class PerformanceEvaluator(BaseMetricEvaluator):
    """
    Extracts runtime performance and diagnostic metrics directly from EvaluationResult records.
    Explicitly distinguishes execution failures and timeouts from meteorological inaccuracies.
    """

    def evaluate(
        self,
        result: EvaluationResult,
        test_case: TestCase,
        fixture: Optional[WeatherFixture] = None,
    ) -> PerformanceMetricResult:
        is_completed = (result.execution_status == ExecutionStatus.COMPLETED)
        is_timeout = (result.execution_status == ExecutionStatus.TIMEOUT)
        is_failure = (result.execution_status in (ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT))

        if is_completed:
            status = MetricStatus.PASSED
        elif is_timeout or result.execution_status == ExecutionStatus.FAILED:
            status = MetricStatus.FAILED
        else:
            status = MetricStatus.NOT_APPLICABLE

        return PerformanceMetricResult(
            is_evaluable=True,
            metric_status=status,
            latency_ms=result.latency_ms,
            retry_count=result.retry_count,
            execution_status=result.execution_status,
            is_successful=is_completed,
            is_timeout=is_timeout,
            is_failure=is_failure,
            tool_call_count=len(result.tool_calls),
            error_type=result.error_type,
            error_message=result.error_message,
        )
