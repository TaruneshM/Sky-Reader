import re
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class BenchmarkCategory(str, Enum):
    CURRENT_WEATHER = "current_weather"
    HOURLY_FORECAST = "hourly_forecast"
    TEMPERATURE_COMPARISON = "temperature_comparison"
    PRECIPITATION_AND_RAINFALL = "precipitation_and_rainfall"
    WEATHER_TRENDS = "weather_trends"
    MULTISTEP_REASONING = "multistep_reasoning"
    EVIDENCE_BASED_REASONING = "evidence_based_reasoning"
    WEATHER_SAFETY_AND_RISK = "weather_safety_and_risk"
    MISSING_INCOMPLETE_DATA = "missing_or_incomplete_data"
    HALLUCINATION_RESISTANCE = "hallucination_resistance"


class ForecastPeriod(str, Enum):
    CURRENT = "current"
    HOURLY_6H = "hourly_6h"
    HOURLY_24H = "hourly_24h"
    NEXT_24H = "next_24h"
    TOMORROW = "tomorrow"
    DAY_COMPARISON = "day_comparison"
    MULTI_DAY = "multi_day"
    UNSPECIFIED = "unspecified"


class ApplicableSystem(str, Enum):
    BASELINE_LLM = "baseline_llm"
    TOOL_USING_AGENT = "tool_using_agent"
    SKY_READER_FULL = "sky_reader_full"


class EvaluationCriteria(BaseModel):
    """
    Defines measurable evaluation criteria for grading model outputs against the test case.
    """
    requires_tools: bool = Field(
        default=True,
        description="Whether a tool call is strictly required to answer accurately."
    )
    expected_claims: List[str] = Field(
        default_factory=list,
        description="Key factual concepts or propositions that must appear in the response."
    )
    allowed_numerical_tolerances: Dict[str, float] = Field(
        default_factory=dict,
        description="Tolerance margin for numerical values (e.g. {'temperature': 1.0, 'humidity': 5.0})."
    )
    requires_evidence_proof: bool = Field(
        default=False,
        description="Whether a formal Phase 4 ExplanationProof is expected."
    )
    requires_risk_assessment: bool = Field(
        default=False,
        description="Whether a Phase 6 WeatherRiskAssessment is expected."
    )
    requires_uncertainty_note: bool = Field(
        default=False,
        description="Whether uncertainty/probability must be explicitly communicated."
    )
    should_refuse_or_hedge: bool = Field(
        default=False,
        description="For hallucination resistance / missing data: model should refuse to hallucinate."
    )

    @field_validator("allowed_numerical_tolerances")
    @classmethod
    def validate_tolerances(cls, v: Dict[str, float]) -> Dict[str, float]:
        for metric, tol in v.items():
            if not isinstance(tol, (int, float)) or tol < 0:
                raise ValueError(f"Tolerance for '{metric}' must be a non-negative number, got {tol}")
        return v


class TestCase(BaseModel):
    """
    A single reproducible benchmark test case.
    """
    id: str = Field(..., description="Stable unique test case ID, e.g. 'TC-CUR-001'.")
    category: BenchmarkCategory = Field(..., description="Evaluation category.")
    question: str = Field(..., description="Natural language user query.")
    location: str = Field(..., description="Target geographic place name.")
    forecast_period: ForecastPeriod = Field(
        default=ForecastPeriod.CURRENT,
        description="Time period targeted by the query."
    )
    fixture_id: Optional[str] = Field(
        default=None,
        description="ID of the synthetic reference weather fixture, or None if pure general knowledge."
    )
    expected_numerical_values: Dict[str, float] = Field(
        default_factory=dict,
        description="Ground-truth reference numbers (e.g. {'temperature': 21.8})."
    )
    expected_facts_or_claims: List[str] = Field(
        default_factory=list,
        description="Expected semantic facts or claims."
    )
    expected_risk_classification: Optional[str] = Field(
        default=None,
        description="Expected Phase 6 risk level (LOW, MODERATE, HIGH, SEVERE) if applicable."
    )
    evaluation_criteria: EvaluationCriteria = Field(
        default_factory=EvaluationCriteria,
        description="Criteria for scoring."
    )
    applicable_systems: List[ApplicableSystem] = Field(
        default_factory=lambda: [
            ApplicableSystem.BASELINE_LLM,
            ApplicableSystem.TOOL_USING_AGENT,
            ApplicableSystem.SKY_READER_FULL,
        ],
        description="Which systems in the evaluation matrix this test case applies to."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context, notes, or tags."
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        v_clean = v.strip()
        if not v_clean:
            raise ValueError("Test case ID cannot be empty.")
        if not re.match(r"^[A-Z0-9_\-]+$", v_clean):
            raise ValueError(f"Test case ID '{v}' contains invalid characters. Use letters, numbers, hyphens, and underscores.")
        return v_clean

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Question cannot be empty.")
        return v.strip()

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Location cannot be empty.")
        return v.strip()

    @field_validator("expected_numerical_values")
    @classmethod
    def validate_numerical_values(cls, v: Dict[str, float]) -> Dict[str, float]:
        for key, val in v.items():
            if not isinstance(val, (int, float)):
                raise ValueError(f"Expected numerical value for '{key}' must be float/int, got {type(val)}")
        return v


class EvaluationDataset(BaseModel):
    """
    Complete evaluation dataset containing benchmark test cases.
    """
    name: str = Field(..., description="Dataset name, e.g. 'Sky Reader Benchmark Dataset'.")
    version: str = Field(..., description="Semantic version string, e.g. '1.0.0'.")
    description: str = Field(..., description="Overview of dataset scope and purpose.")
    total_cases: int = Field(..., description="Total count of test cases in dataset.")
    test_cases: List[TestCase] = Field(..., description="List of benchmark test cases.")

    @model_validator(mode="after")
    def validate_dataset_integrity(self) -> "EvaluationDataset":
        # 1. Validate unique IDs
        ids = [tc.id for tc in self.test_cases]
        duplicates = [x for x in ids if ids.count(x) > 1]
        if duplicates:
            unique_dups = sorted(list(set(duplicates)))
            raise ValueError(f"Duplicate test case IDs found in dataset: {unique_dups}")

        # 2. Validate total_cases matches length
        if len(self.test_cases) != self.total_cases:
            raise ValueError(
                f"total_cases mismatch: header declares {self.total_cases}, "
                f"but found {len(self.test_cases)} test cases."
            )

        return self

    def get_by_id(self, test_id: str) -> Optional[TestCase]:
        for tc in self.test_cases:
            if tc.id == test_id:
                return tc
        return None

    def filter_by_category(self, category: BenchmarkCategory) -> List[TestCase]:
        return [tc for tc in self.test_cases if tc.category == category]

    def filter_by_system(self, system: ApplicableSystem) -> List[TestCase]:
        return [tc for tc in self.test_cases if system in tc.applicable_systems]

    def category_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for tc in self.test_cases:
            cat_name = tc.category.value
            dist[cat_name] = dist.get(cat_name, 0) + 1
        return dist


class WeatherFixture(BaseModel):
    """
    Structured synthetic weather data fixture simulating Open-Meteo responses.
    """
    fixture_id: str = Field(..., description="Unique fixture identifier, e.g. 'FIX_DEHRADUN_MILD'.")
    description: str = Field(..., description="Human-readable description of simulated scenario.")
    location: Dict[str, Any] = Field(..., description="Geographic metadata: name, lat, lon, country.")
    is_synthetic: bool = Field(default=True, description="Explicit marker that this data is synthetic.")
    current: Optional[Dict[str, Any]] = Field(default=None, description="Open-Meteo format current weather dictionary.")
    hourly: Optional[Dict[str, Any]] = Field(default=None, description="Open-Meteo format hourly forecast dictionary.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional scenario tags or annotations.")

    @field_validator("fixture_id")
    @classmethod
    def validate_fixture_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("fixture_id cannot be empty.")
        return v.strip()

    @field_validator("is_synthetic")
    @classmethod
    def enforce_synthetic_flag(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Evaluation fixtures must be explicitly marked with is_synthetic=True.")
        return v


class FixtureCollection(BaseModel):
    """
    Collection of synthetic weather fixtures for deterministic evaluation.
    """
    version: str = Field(..., description="Fixture collection version.")
    description: str = Field(..., description="Overview of fixture coverage.")
    fixtures: Dict[str, WeatherFixture] = Field(..., description="Map of fixture_id to WeatherFixture.")

    def get(self, fixture_id: str) -> Optional[WeatherFixture]:
        return self.fixtures.get(fixture_id)

    def contains(self, fixture_id: str) -> bool:
        return fixture_id in self.fixtures
