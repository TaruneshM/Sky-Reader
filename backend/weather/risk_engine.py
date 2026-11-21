import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from backend.weather.risk_models import (
        RiskLevel,
        RiskType,
        RiskThresholds,
        RiskItem,
        WeatherRiskAssessment,
    )
    from backend.weather.weather_codes import get_weather_description
except ImportError:
    from weather.risk_models import (
        RiskLevel,
        RiskType,
        RiskThresholds,
        RiskItem,
        WeatherRiskAssessment,
    )
    from weather.weather_codes import get_weather_description


SEVERITY_ORDER = {
    RiskLevel.LOW: 0,
    RiskLevel.MODERATE: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.SEVERE: 3,
}


def _safe_extract_series(data: dict, key: str, start: int = 0, count: int = 24) -> tuple:
    """
    Safely extracts a slice of numerical/string series from Open-Meteo hourly dict.
    Returns (sliced_list, is_available, missing_count).
    """
    if not isinstance(data, dict):
        return ([], False, count)

    hourly = data.get("hourly", data)
    if not isinstance(hourly, dict):
        return ([], False, count)

    raw_list = hourly.get(key)
    if raw_list is None or not isinstance(raw_list, list) or len(raw_list) == 0:
        return ([], False, count)

    sliced = raw_list[start:start + count]
    missing_count = count - len(sliced) + sum(1 for x in sliced if x is None)
    is_available = len(sliced) > 0 and missing_count < len(sliced)

    return (sliced, is_available, missing_count)


class WeatherRiskEngine:
    """
    Deterministic Python Weather Risk Assessment Engine.
    Identifies dangerous meteorological conditions, assigns structured risk levels,
    generates practical safety recommendations, and explicitly communicates forecast uncertainty.
    """

    def __init__(self, thresholds: Optional[RiskThresholds] = None):
        self.thresholds = thresholds or RiskThresholds()

    def assess_risks(
        self,
        hourly_data: dict,
        day_offset: int = 1,
        location_name: Optional[str] = None,
        forecast_period: Optional[str] = None,
    ) -> WeatherRiskAssessment:
        """
        Runs comprehensive deterministic risk assessment on 24-hour window.
        day_offset=0 evaluates today (hours 0-23); day_offset=1 evaluates tomorrow (hours 24-47).
        """
        start_idx = 0 if forecast_period else day_offset * 24
        count = len(hourly_data.get("hourly", {}).get("time", [])) if forecast_period else 24

        # Extract series
        times, has_times, _ = _safe_extract_series(hourly_data, "time", start_idx, count)
        temps, has_temps, missing_temps = _safe_extract_series(hourly_data, "temperature_2m", start_idx, count)
        precip_prob, has_prob, missing_prob = _safe_extract_series(hourly_data, "precipitation_probability", start_idx, count)
        precip_amount, has_amount, missing_amount = _safe_extract_series(hourly_data, "precipitation", start_idx, count)
        winds, has_winds, missing_winds = _safe_extract_series(hourly_data, "wind_speed_10m", start_idx, count)
        codes, has_codes, missing_codes = _safe_extract_series(hourly_data, "weather_code", start_idx, count)

        detected_risks: List[RiskItem] = []
        data_limitations: List[str] = []
        uncertainty_notes: List[str] = []

        # Determine forecast time window
        start_time_str = times[0] if (has_times and len(times) > 0 and times[0]) else "start of period"
        end_time_str = times[-1] if (has_times and len(times) > 0 and times[-1]) else "end of period"
        period_label = f"tomorrow ({start_time_str} to {end_time_str})" if day_offset == 1 else f"today ({start_time_str} to {end_time_str})"

        if forecast_period:
            period_label = f"{forecast_period} ({start_time_str} to {end_time_str})"

        # Check data completeness & limitations
        if not has_temps:
            data_limitations.append("Temperature data unavailable in forecast; thermal risk evaluation skipped.")
        elif missing_temps > 0:
            data_limitations.append(f"Temperature data is incomplete ({missing_temps}/{count} hours missing).")

        if not has_prob and not has_amount:
            data_limitations.append("Precipitation data unavailable in forecast; rainfall risk evaluation skipped.")
        elif missing_amount > 0:
            data_limitations.append(f"Precipitation accumulation data is incomplete ({missing_amount}/{count} hours missing).")

        if not has_winds:
            data_limitations.append("Wind speed data unavailable in forecast; wind hazard evaluation skipped.")
        elif missing_winds > 0:
            data_limitations.append(f"Wind speed data is incomplete ({missing_winds}/{count} hours missing).")

        if not has_codes or missing_codes:
            data_limitations.append("WMO weather condition codes unavailable; severe thunderstorm detection limited.")

        # -------------------------------------------------------------
        # 1. Heavy Rainfall Assessment (Volume and Hourly Rate)
        # -------------------------------------------------------------
        valid_amounts = [float(x) for x in precip_amount if isinstance(x, (int, float))]
        if valid_amounts:
            total_rain = sum(valid_amounts)
            max_hourly_rain = max(valid_amounts)

            rain_risk = None
            if total_rain >= self.thresholds.rain_severe_mm or max_hourly_rain >= self.thresholds.rain_rate_severe_mmh:
                rain_risk = RiskLevel.SEVERE
                reason = (
                    f"Severe heavy rainfall predicted: total accumulation of {round(total_rain, 1)} mm with peak "
                    f"hourly rate of {round(max_hourly_rain, 1)} mm/h. High potential for flash flooding and waterlogging."
                )
                recommendations = [
                    "Avoid traveling through low-lying or flood-prone areas.",
                    "Exercise extreme caution around storm drains and saturated ground.",
                    "Keep emergency electronics charged and monitor local authorities.",
                ]
            elif total_rain >= self.thresholds.rain_high_mm or max_hourly_rain >= self.thresholds.rain_rate_high_mmh:
                rain_risk = RiskLevel.HIGH
                reason = (
                    f"Substantial rainfall expected: total accumulation of {round(total_rain, 1)} mm with peak "
                    f"intensity of {round(max_hourly_rain, 1)} mm/h. May cause localized standing water and road spray."
                )
                recommendations = [
                    "Carry sturdy rain gear or waterproof clothing.",
                    "Allow extra travel time due to slick road surfaces and reduced braking distance.",
                    "Be cautious around underpasses and poorly drained roadways.",
                ]
            elif total_rain >= self.thresholds.rain_moderate_mm or max_hourly_rain >= self.thresholds.rain_rate_moderate_mmh:
                rain_risk = RiskLevel.MODERATE
                reason = (
                    f"Moderate rainfall expected: total accumulation of {round(total_rain, 1)} mm (peak rate "
                    f"{round(max_hourly_rain, 1)} mm/h)."
                )
                recommendations = [
                    "Carry an umbrella or rain jacket.",
                    "Exercise normal caution on wet roads and pedestrian walkways.",
                ]

            if rain_risk:
                # Find peak rain time
                peak_rain_time = ""
                if has_times and max_hourly_rain in valid_amounts:
                    idx = precip_amount.index(max_hourly_rain)
                    peak_rain_time = times[idx] if idx < len(times) else ""

                detected_risks.append(
                    RiskItem(
                        risk_type=RiskType.HEAVY_RAINFALL,
                        severity=rain_risk,
                        condition="Heavy Rainfall",
                        reason=reason,
                        measurements={
                            "total_expected_rain_mm": round(total_rain, 1),
                            "max_hourly_rate_mmh": round(max_hourly_rain, 1),
                            "peak_rain_time": peak_rain_time,
                        },
                        forecast_window=period_label,
                        recommendations=recommendations,
                    )
                )

        # -------------------------------------------------------------
        # 2. High Precipitation Probability Assessment
        # -------------------------------------------------------------
        valid_probs = [float(x) for x in precip_prob if isinstance(x, (int, float))]
        if valid_probs:
            max_prob = max(valid_probs)
            # Only trigger an independent probability warning if prob is elevated and not already overshadowed by severe rain
            if max_prob >= self.thresholds.precip_prob_moderate:
                if max_prob >= self.thresholds.precip_prob_severe:
                    prob_risk = RiskLevel.HIGH
                    prob_desc = f"Very high probability of precipitation ({round(max_prob)}%). Rain is almost certain during this period."
                elif max_prob >= self.thresholds.precip_prob_high:
                    prob_risk = RiskLevel.MODERATE
                    prob_desc = f"High probability of precipitation ({round(max_prob)}%). Rain is likely to occur."
                else:
                    prob_risk = RiskLevel.LOW  # Informational moderate risk
                    prob_desc = f"Moderate chance of precipitation ({round(max_prob)}%)."

                if prob_risk != RiskLevel.LOW:
                    peak_prob_time = ""
                    if has_times:
                        idx = precip_prob.index(max_prob)
                        peak_prob_time = times[idx] if idx < len(times) else ""

                    detected_risks.append(
                        RiskItem(
                            risk_type=RiskType.HIGH_PRECIPITATION_PROBABILITY,
                            severity=prob_risk,
                            condition="High Precipitation Probability",
                            reason=prob_desc,
                            measurements={
                                "peak_precipitation_probability": round(max_prob, 1),
                                "peak_probability_time": peak_prob_time,
                            },
                            forecast_window=period_label,
                            recommendations=[
                                "Keep an umbrella on hand when heading out.",
                                "Plan outdoor activities around peak precipitation windows.",
                            ],
                        )
                    )

        # -------------------------------------------------------------
        # 3. Thunderstorm Hazard Assessment
        # -------------------------------------------------------------
        valid_codes = [int(x) for x in codes if isinstance(x, (int, float))]
        thunderstorm_codes = [c for c in valid_codes if c in (95, 96, 99)]
        if thunderstorm_codes:
            has_hail = any(c in (96, 99) for c in thunderstorm_codes)
            ts_severity = RiskLevel.SEVERE if has_hail else RiskLevel.HIGH
            ts_label = "Severe Thunderstorm with Hail" if has_hail else "Thunderstorm Activity"
            ts_reason = (
                "Thunderstorm conditions detected in numerical forecast (WMO codes 96/99: thunderstorm with hail). "
                "Danger from cloud-to-ground lightning, rapid wind gusts, and damaging hail."
                if has_hail
                else "Thunderstorm conditions detected in forecast (WMO code 95). Potential for cloud-to-ground lightning and sudden gusts."
            )
            detected_risks.append(
                RiskItem(
                    risk_type=RiskType.THUNDERSTORM,
                    severity=ts_severity,
                    condition=ts_label,
                    reason=ts_reason,
                    measurements={
                        "detected_wmo_codes": list(set(thunderstorm_codes)),
                        "hail_detected": has_hail,
                    },
                    forecast_window=period_label,
                    recommendations=[
                        "Seek shelter indoors inside a sturdy building when thunder roars.",
                        "Avoid open fields, bodies of water, isolated tall trees, and exposed metal structures.",
                        "Stay away from windows and avoid using corded electrical equipment during the storm.",
                    ],
                )
            )

        # -------------------------------------------------------------
        # 4. Strong Wind Hazard Assessment
        # -------------------------------------------------------------
        gusts, _, _ = _safe_extract_series(hourly_data, "wind_gusts_10m", start_idx, count)
        peaks = [(float(value), index, kind) for kind, series in (("wind speed", winds), ("wind gust", gusts))
                 for index, value in enumerate(series) if isinstance(value, (int, float))]
        if peaks:
            max_wind, peak_index, peak_kind = max(peaks)
            wind_risk = None
            if max_wind >= self.thresholds.wind_severe_kmh:
                wind_risk = RiskLevel.SEVERE
                wind_reason = (
                    f"Gale or storm-force winds predicted: peak speeds reaching {round(max_wind, 1)} km/h. "
                    f"Structural damage, flying debris, fallen branches, and power outages possible."
                )
                wind_recs = [
                    "Secure loose outdoor furniture, signs, and trash cans.",
                    "Avoid walking or parking under tall trees or near temporary scaffolding.",
                    "High-profile vehicles should avoid exposed highway bridges.",
                ]
            elif max_wind >= self.thresholds.wind_high_kmh:
                wind_risk = RiskLevel.HIGH
                wind_reason = (
                    f"Strong wind expected: peak {peak_kind} reaching {round(max_wind, 1)} km/h. "
                    f"May cause difficulty walking, sway high vehicles, and dislodge tree limbs."
                )
                wind_recs = [
                    "Exercise caution when driving high-profile vehicles in crosswinds.",
                    "Secure lightweight outdoor items.",
                ]
            elif max_wind >= self.thresholds.wind_moderate_kmh:
                wind_risk = RiskLevel.MODERATE
                wind_reason = f"Breezy to moderately strong winds: peak speeds reaching {round(max_wind, 1)} km/h."
                wind_recs = ["Be mindful of sudden gusts when opening vehicle doors or cycling."]

            if wind_risk:
                peak_wind_time = ""
                if has_times:
                    peak_wind_time = times[peak_index] if peak_index < len(times) else ""

                detected_risks.append(
                    RiskItem(
                        risk_type=RiskType.STRONG_WIND,
                        severity=wind_risk,
                        condition="Strong Wind",
                        reason=wind_reason,
                        measurements={
                            "max_wind_speed_kmh": round(max_wind, 1),
                            "peak_wind_time": peak_wind_time,
                            "peak_measurement": peak_kind,
                        },
                        forecast_window=period_label,
                        recommendations=wind_recs,
                    )
                )

        # -------------------------------------------------------------
        # 5. Extreme Heat Assessment
        # -------------------------------------------------------------
        valid_temps = [float(x) for x in temps if isinstance(x, (int, float))]
        if valid_temps:
            max_temp = max(valid_temps)
            min_temp = min(valid_temps)

            if max_temp >= self.thresholds.heat_moderate_c:
                if max_temp >= self.thresholds.heat_severe_c:
                    heat_risk = RiskLevel.SEVERE
                    heat_reason = (
                        f"Severe extreme heat hazard: peak temperature of {round(max_temp, 1)}°C. "
                        f"Dangerous risk of heat exhaustion and heatstroke with continued outdoor exposure."
                    )
                    heat_recs = [
                        "Stay hydrated: drink plenty of water and electrolytes even if you do not feel thirsty.",
                        "Avoid strenuous outdoor activities, especially between 11:00 and 16:00.",
                        "Never leave children or pets inside parked vehicles.",
                        "Seek air-conditioned or well-ventilated spaces.",
                    ]
                elif max_temp >= self.thresholds.heat_high_c:
                    heat_risk = RiskLevel.HIGH
                    heat_reason = (
                        f"Extreme heat conditions: peak temperature reaching {round(max_temp, 1)}°C. "
                        f"Elevated risk of heat-related illness."
                    )
                    heat_recs = [
                        "Stay well hydrated throughout the day.",
                        "Wear lightweight, loose-fitting, light-colored clothing.",
                        "Limit prolonged exposure to direct midday sunlight.",
                    ]
                else:
                    heat_risk = RiskLevel.MODERATE
                    heat_reason = f"High temperatures expected: peak temperature reaching {round(max_temp, 1)}°C."
                    heat_recs = [
                        "Carry water when traveling outdoors.",
                        "Seek shade during the hottest afternoon hours.",
                    ]

                peak_heat_time = ""
                if has_times:
                    idx = temps.index(max_temp)
                    peak_heat_time = times[idx] if idx < len(times) else ""

                detected_risks.append(
                    RiskItem(
                        risk_type=RiskType.EXTREME_HEAT,
                        severity=heat_risk,
                        condition="Extreme Heat",
                        reason=heat_reason,
                        measurements={
                            "max_temperature_c": round(max_temp, 1),
                            "peak_temperature_time": peak_heat_time,
                        },
                        forecast_window=period_label,
                        recommendations=heat_recs,
                    )
                )

            # -------------------------------------------------------------
            # 6. Extreme Cold Assessment
            # -------------------------------------------------------------
            if min_temp <= self.thresholds.cold_moderate_c:
                if min_temp <= self.thresholds.cold_severe_c:
                    cold_risk = RiskLevel.SEVERE
                    cold_reason = (
                        f"Severe extreme cold hazard: minimum temperature plummeting to {round(min_temp, 1)}°C. "
                        f"Dangerous frostbite and hypothermia hazard within minutes of exposed skin contact."
                    )
                    cold_recs = [
                        "Wear layered insulated clothing with wind-resistant outer shell.",
                        "Cover all exposed skin (hat, scarf, insulated gloves, thermal socks).",
                        "Limit outdoor exposure time and watch for numbness or white patches on skin.",
                    ]
                elif min_temp <= self.thresholds.cold_high_c:
                    cold_risk = RiskLevel.HIGH
                    cold_reason = (
                        f"Extreme cold conditions: temperatures dropping to {round(min_temp, 1)}°C. "
                        f"High risk of frostbite and severe hypothermia."
                    )
                    cold_recs = [
                        "Dress in warm thermal layers with insulated outerwear.",
                        "Protect hands, ears, and feet from cold exposure.",
                        "Check on vulnerable neighbors and protect outdoor pipes and pets.",
                    ]
                else:
                    cold_risk = RiskLevel.MODERATE
                    cold_reason = f"Freezing temperatures expected: minimum temperature dropping to {round(min_temp, 1)}°C."
                    cold_recs = [
                        "Wear a warm coat, gloves, and a hat.",
                        "Watch for black ice on roadways, bridges, and pedestrian walkways.",
                    ]

                peak_cold_time = ""
                if has_times:
                    idx = temps.index(min_temp)
                    peak_cold_time = times[idx] if idx < len(times) else ""

                detected_risks.append(
                    RiskItem(
                        risk_type=RiskType.EXTREME_COLD,
                        severity=cold_risk,
                        condition="Extreme Cold",
                        reason=cold_reason,
                        measurements={
                            "min_temperature_c": round(min_temp, 1),
                            "coldest_time": peak_cold_time,
                        },
                        forecast_window=period_label,
                        recommendations=cold_recs,
                    )
                )

        # -------------------------------------------------------------
        # Determine Overall Risk Level
        # -------------------------------------------------------------
        if not detected_risks:
            overall_level = RiskLevel.LOW
            overall_summary = "No significant weather hazards or elevated risks detected for this period."
            all_recs = ["Standard weather conditions expected. No specialized safety precautions required."]
        else:
            # Sort detected risks by severity descending
            detected_risks.sort(key=lambda r: SEVERITY_ORDER[r.severity], reverse=True)
            overall_level = detected_risks[0].severity

            # Build aggregated summary
            risk_titles = [f"{r.condition} ({r.severity})" for r in detected_risks]
            overall_summary = f"{overall_level} risk level detected: " + ", ".join(risk_titles) + "."

            # Aggregate unique recommendations preserving order
            all_recs = []
            seen = set()
            for r in detected_risks:
                for rec in r.recommendations:
                    if rec not in seen:
                        seen.add(rec)
                        all_recs.append(rec)

        # -------------------------------------------------------------
        # Uncertainty Notes & Responsible Communication
        # -------------------------------------------------------------
        if valid_probs and valid_amounts:
            max_p = max(valid_probs)
            tot_r = sum(valid_amounts)
            uncertainty_notes.append(
                f"Precipitation probability ({round(max_p)}%) indicates the statistical likelihood of rain occurring "
                f"within the forecast area, not the fraction of the day it will rain. The total expected volume is "
                f"{round(tot_r, 1)} mm."
            )
        elif valid_probs:
            max_p = max(valid_probs)
            uncertainty_notes.append(
                f"Precipitation probability is {round(max_p)}%. Rain is {'likely' if max_p >= 60 else 'possible' if max_p >= 30 else 'unlikely'}, but not guaranteed."
            )

        uncertainty_notes.append(
            "Numerical weather forecasts represent model-based probabilistic estimates. Actual conditions may vary locally or shift over time."
        )

        return WeatherRiskAssessment(
            overall_risk_level=overall_level,
            overall_summary=overall_summary,
            detected_risks=detected_risks,
            safety_recommendations=all_recs,
            forecast_period=period_label,
            is_official_alert=False,
            official_alert_source=None,
            official_alerts_available=False,
            assessment_source=(
                "AI-generated risk assessment calculated by Sky Reader using Open-Meteo numerical "
                "forecast data and deterministic meteorological thresholds. This is NOT an official "
                "government weather alert."
            ),
            uncertainty_notes=uncertainty_notes,
            data_limitations=data_limitations,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
        )
