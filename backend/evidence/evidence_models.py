from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceSourceType(str, Enum):
    OBSERVED = "observed"   # Current real-time weather observations
    FORECAST = "forecast"   # Numerical weather prediction model forecast
    DERIVED = "derived"     # Computed by Phase 3 analytical engine


class WeatherVariable(str, Enum):
    TEMPERATURE = "temperature"
    APPARENT_TEMPERATURE = "apparent_temperature"
    HUMIDITY = "humidity"
    PRECIPITATION_PROBABILITY = "precipitation_probability"
    PRECIPITATION_AMOUNT = "precipitation_amount"
    WIND_SPEED = "wind_speed"
    WIND_DIRECTION = "wind_direction"
    PRESSURE = "pressure"
    CLOUD_COVER = "cloud_cover"
    WEATHER_CONDITION = "weather_condition"
    TEMPERATURE_TREND = "temperature_trend"
    UMBRELLA_NEED = "umbrella_need"
    OUTDOOR_SUITABILITY = "outdoor_suitability"
    TRAVEL_SUITABILITY = "travel_suitability"
    DAILY_COMPARISON = "daily_comparison"


class ValidationStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"


class ClaimType(str, Enum):
    NUMERICAL_VALUE = "numerical_value"
    TREND = "trend"
    CONDITION = "condition"
    COMPARISON = "comparison"
    RECOMMENDATION_SUPPORT = "recommendation_support"


class EvidenceItem(BaseModel):
    id: str = Field(..., description="Unique evidence identifier, e.g. ev_temp_current")
    variable: WeatherVariable = Field(..., description="The meteorological variable")
    value: Any = Field(..., description="The measured, forecast, or derived analytical value")
    unit: Optional[str] = Field(None, description="Physical unit, e.g. °C, %, mm, km/h, hPa")
    location: Optional[str] = Field(None, description="Location name or identifier")
    latitude: Optional[float] = Field(None, description="Latitude")
    longitude: Optional[float] = Field(None, description="Longitude")
    time_period: str = Field(..., description="Specific timestamp or time period, e.g. 2026-11-09T16:00, tomorrow, morning")
    source_type: EvidenceSourceType = Field(..., description="Observed, forecast, or derived")
    source_name: str = Field(..., description="Originating service or analytical module")
    analysis_method: Optional[str] = Field(None, description="Method used if derived")
    confidence: Optional[float] = Field(1.0, description="Confidence score 0.0 to 1.0")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context or raw parameters")


class EvidenceCollection(BaseModel):
    items: List[EvidenceItem] = Field(default_factory=list)
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    generated_at: Optional[str] = None

    def add(self, item: EvidenceItem) -> None:
        self.items.append(item)

    def find_by_variable(self, variable: WeatherVariable) -> List[EvidenceItem]:
        return [it for it in self.items if it.variable == variable]

    def find_by_variable_and_period(self, variable: WeatherVariable, time_prefix: str) -> List[EvidenceItem]:
        return [
            it for it in self.items
            if it.variable == variable and time_prefix.lower() in it.time_period.lower()
        ]

    def get_by_id(self, evidence_id: str) -> Optional[EvidenceItem]:
        for it in self.items:
            if it.id == evidence_id:
                return it
        return None

    def to_summary_dict(self) -> Dict[str, Any]:
        """Provides a lightweight summary grouped by variable for agent reasoning."""
        summary: Dict[str, List[Dict[str, Any]]] = {}
        for it in self.items:
            key = it.variable.value
            if key not in summary:
                summary[key] = []
            summary[key].append({
                "id": it.id,
                "value": it.value,
                "unit": it.unit,
                "time_period": it.time_period,
                "source_type": it.source_type.value,
            })
        return summary


class FactualClaim(BaseModel):
    claim_id: str = Field(..., description="Unique claim identifier, e.g. claim_1")
    statement: str = Field(..., description="The original textual statement extracted from the response")
    variable: WeatherVariable = Field(..., description="The weather variable referenced")
    claimed_value: Any = Field(..., description="Extracted numerical or qualitative claim")
    unit: Optional[str] = Field(None, description="Extracted unit if present")
    time_period: Optional[str] = Field(None, description="Referenced time period, e.g. tomorrow, 5 PM, today")
    location: Optional[str] = Field(None, description="Location mentioned")
    claim_type: ClaimType = Field(default=ClaimType.NUMERICAL_VALUE)


class ClaimValidationResult(BaseModel):
    claim: FactualClaim
    status: ValidationStatus
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    evidence_values: List[Any] = Field(default_factory=list)
    explanation: str = Field(..., description="Audit explanation detailing why the status was assigned")
    tolerance_used: Optional[float] = Field(None, description="Tolerance margin applied during comparison")


class HallucinationReport(BaseModel):
    total_claims: int
    supported_claims: int
    contradicted_claims: int
    unsupported_claims: int
    partially_supported_claims: int
    hallucination_rate: float = Field(..., description="Proportion of contradicted or unsupported claims (0.0 to 1.0)")
    contradiction_rate: float = Field(..., description="Proportion of contradicted claims (0.0 to 1.0)")
    unsupported_rate: float = Field(..., description="Proportion of unverifiable claims (0.0 to 1.0)")
    is_trustworthy: bool
    validation_results: List[ClaimValidationResult] = Field(default_factory=list)
    problematic_claims: List[ClaimValidationResult] = Field(default_factory=list)


class ExplanationProof(BaseModel):
    query: str
    conclusion: str
    supporting_evidence: List[Dict[str, Any]]
    measurements_used: List[Dict[str, Any]]
    analysis_performed: List[str]
    data_sources: List[str]
    time_periods: List[str]
    claim_validation_status: str
    hallucination_risk: str
    limitations_and_uncertainty: str
