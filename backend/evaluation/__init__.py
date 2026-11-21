from backend.evaluation.models import (
    ApplicableSystem,
    BenchmarkCategory,
    EvaluationCriteria,
    EvaluationDataset,
    FixtureCollection,
    ForecastPeriod,
    TestCase,
    WeatherFixture,
)
from backend.evaluation.dataset_loader import (
    get_fixture,
    get_test_case,
    load_benchmark_suite,
    load_dataset,
    load_fixtures,
)
from backend.evaluation.result_models import (
    EvaluationResult,
    ExecutionStatus,
    FixtureMode,
    RunSummary,
)
from backend.evaluation.config import EvaluationConfig
from backend.evaluation.result_store import ResultStore
from backend.evaluation.adapters import (
    BaselineLLMAdapter,
    FixtureToolExecutor,
    SkyReaderAdapter,
    ToolUsingAgentAdapter,
)
from backend.evaluation.metrics import (
    AggregatedMetricSummary,
    CaseMetricScores,
    MetricsEngine,
    RunEvaluationReport,
)

def __getattr__(name: str):
    if name == "EvaluationRunner":
        from backend.evaluation.runner import EvaluationRunner
        return EvaluationRunner
    if name == "ComparativeAnalyzer":
        from backend.evaluation.analysis.comparator import ComparativeAnalyzer
        return ComparativeAnalyzer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "ApplicableSystem",
    "BenchmarkCategory",
    "EvaluationCriteria",
    "EvaluationDataset",
    "FixtureCollection",
    "ForecastPeriod",
    "TestCase",
    "WeatherFixture",
    "get_fixture",
    "get_test_case",
    "load_benchmark_suite",
    "load_dataset",
    "load_fixtures",
    "EvaluationResult",
    "ExecutionStatus",
    "FixtureMode",
    "RunSummary",
    "EvaluationConfig",
    "ResultStore",
    "BaselineLLMAdapter",
    "FixtureToolExecutor",
    "SkyReaderAdapter",
    "ToolUsingAgentAdapter",
    "EvaluationRunner",
    "MetricsEngine",
    "CaseMetricScores",
    "AggregatedMetricSummary",
    "RunEvaluationReport",
    "ComparativeAnalyzer",
]

