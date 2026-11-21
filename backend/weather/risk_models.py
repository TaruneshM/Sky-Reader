from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    SEVERE = "SEVERE"


class RiskType(str, Enum):
    HEAVY_RAINFALL = "heavy_rainfall"
    HIGH_PRECIPITATION_PROBABILITY = "high_precipitation_probability"
    THUNDERSTORM = "thunderstorm"
    STRONG_WIND = "strong_wind"
    EXTREME_HEAT = "extreme_heat"
    EXTREME_COLD = "extreme_cold"


class RiskThresholds(BaseModel):
    """
    Configurable meteorological thresholds for risk classification.
    Can be adjusted or overridden based on local climate norms.
    """
    # Rainfall accumulation (mm per 24h period or event)
    rain_moderate_mm: float = 15.0
    rain_high_mm: float = 30.0
    rain_severe_mm: float = 60.0

    # Hourly rain rate (mm/h)
    rain_rate_moderate_mmh: float = 5.0
    rain_rate_high_mmh: float = 10.0
    rain_rate_severe_mmh: float = 20.0

    # Precipitation probability (%)
    precip_prob_moderate: float = 60.0
    precip_prob_high: float = 80.0
    precip_prob_severe: float = 95.0

    # Wind speed (km/h) - Beaufort scale aligned
    wind_moderate_kmh: float = 30.0  # Moderate breeze / near strong breeze
    wind_high_kmh: float = 45.0      # Strong breeze / near gale
    wind_severe_kmh: float = 62.0    # Gale / storm force (Beaufort 8+)

    # Extreme heat (°C)
    heat_moderate_c: float = 35.0    # Hot
    heat_high_c: float = 40.0        # Very hot / heat advisory
    heat_severe_c: float = 45.0      # Extreme heat warning

    # Extreme cold (°C)
    cold_moderate_c: float = 0.0     # Freezing point
    cold_high_c: float = -10.0       # Severe freeze
    cold_severe_c: float = -20.0     # Extreme cold hazard


class RiskItem(BaseModel):
    risk_type: RiskType
    severity: RiskLevel
    condition: str = Field(..., description="Human-readable condition title, e.g. 'Heavy Rainfall Risk'")
    reason: str = Field(..., description="Specific explanation of why this condition triggered a risk warning")
    measurements: Dict[str, Any] = Field(default_factory=dict, description="Key numerical metrics backing this assessment")
    forecast_window: str = Field(..., description="Time window or date range relevant to this risk")
    recommendations: List[str] = Field(default_factory=list, description="Actionable safety recommendations")


class WeatherRiskAssessment(BaseModel):
    overall_risk_level: RiskLevel = RiskLevel.LOW
    overall_summary: str
    detected_risks: List[RiskItem] = Field(default_factory=list)
    safety_recommendations: List[str] = Field(default_factory=list)
    forecast_period: str
    is_official_alert: bool = False
    official_alert_source: Optional[str] = None
    official_alerts_available: bool = False
    assessment_source: str = (
        "AI-generated risk assessment calculated by Sky Reader using numerical weather "
        "model forecasts and deterministic thresholds. This is NOT an official government weather alert."
    )
    uncertainty_notes: List[str] = Field(default_factory=list)
    data_limitations: List[str] = Field(default_factory=list)
    evaluated_at: str
