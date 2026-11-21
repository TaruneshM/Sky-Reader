from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

try:
    from backend.evaluation.models import TestCase, WeatherFixture
    from backend.evaluation.result_models import EvaluationResult, ExecutionStatus
except ImportError:
    from evaluation.models import TestCase, WeatherFixture
    from evaluation.result_models import EvaluationResult, ExecutionStatus


class MetricStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNEVALUABLE = "UNEVALUABLE"


class NumericalMatchStatus(str, Enum):
    CORRECT = "CORRECT"
    INCORRECT = "INCORRECT"
    MISSING = "MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class FactualClaimStatus(str, Enum):
    CORRECT = "CORRECT"
    INCORRECT = "INCORRECT"
    UNADDRESSED = "UNADDRESSED"
    UNSUPPORTED = "UNSUPPORTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class BaseMetricResult(BaseModel):
    """
    Base model for all metric evaluation outputs.
    Ensures explicit tracking of evaluability and failure rationale.
    """
    is_evaluable: bool = Field(
        default=True,
        description="Whether this result could be evaluated (False if execution failed or timed out)."
    )
    reason_unevaluable: Optional[str] = Field(
        default=None,
        description="Diagnostic explanation if the metric could not be evaluated."
    )
    metric_status: MetricStatus = Field(
        default=MetricStatus.NOT_APPLICABLE,
        description="High-level categorical evaluation status."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional diagnostic metadata or intermediate steps."
    )


class BaseMetricEvaluator(ABC):
    """
    Abstract base class for all Phase 7.3 metric evaluators.
    Evaluators must be deterministic, pure functions operating on frozen
    EvaluationResult, TestCase, and optional WeatherFixture instances.
    """

    @abstractmethod
    def evaluate(
        self,
        result: EvaluationResult,
        test_case: TestCase,
        fixture: Optional[WeatherFixture] = None,
    ) -> BaseMetricResult:
        """
        Evaluates a single execution result against the benchmark test case.
        """
        pass
