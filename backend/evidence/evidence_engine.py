import re
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from backend.evidence.evidence_models import (
        EvidenceCollection,
        EvidenceItem,
        EvidenceSourceType,
        WeatherVariable,
    )
    from backend.weather.analysis import (
        analyze_weather_data,
        get_weather_decision_support,
        degrees_to_cardinal,
    )
    from backend.weather.weather_codes import get_weather_description
except ImportError:
    from evidence.evidence_models import (
        EvidenceCollection,
        EvidenceItem,
        EvidenceSourceType,
        WeatherVariable,
    )
    from weather.analysis import (
        analyze_weather_data,
        get_weather_decision_support,
        degrees_to_cardinal,
    )
    from weather.weather_codes import get_weather_description


class EvidenceEngine:
    """
    Modular Evidence Generation Engine.
    Extracts structured, provenance-tagged evidence records from raw Open-Meteo
    weather data and Phase 3 meteorological analysis results.
    """

    def __init__(self):
        pass

    def generate_evidence(
        self,
        current_data: Optional[Dict[str, Any]] = None,
        hourly_data: Optional[Dict[str, Any]] = None,
        analysis_data: Optional[Dict[str, Any]] = None,
        location_meta: Optional[Dict[str, Any]] = None,
        analysis_results: Optional[Dict[str, Any]] = None,
    ) -> EvidenceCollection:
        """
        Builds a comprehensive EvidenceCollection.
        Accepts raw current data, hourly forecast, precomputed or freshly computed
        Phase 3 analysis, and location metadata.
        """
        resolved_analysis = analysis_data if analysis_data is not None else analysis_results

        location_name = None
        lat = None
        lon = None
        if location_meta:
            location_name = location_meta.get("name")
            lat = location_meta.get("latitude")
            lon = location_meta.get("longitude")

        collection = EvidenceCollection(
            location_name=location_name,
            latitude=lat,
            longitude=lon,
            generated_at=datetime.utcnow().isoformat(),
        )

        # 1. Observed Current Weather Evidence
        if current_data:
            self._extract_current_evidence(collection, current_data, location_name, lat, lon)

        # 2. Hourly Forecast Evidence
        if hourly_data:
            self._extract_hourly_evidence(collection, hourly_data, location_name, lat, lon)

            # If analysis_data was not supplied, compute it from hourly_data
            if not resolved_analysis:
                try:
                    resolved_analysis = analyze_weather_data(hourly_data, focus="all", day_offset=1)
                except Exception:
                    resolved_analysis = None

        # 3. Derived Analytical Evidence (Phase 3 Engine)
        if resolved_analysis:
            self._extract_analysis_evidence(collection, resolved_analysis, location_name, lat, lon)

        return collection

    def _extract_current_evidence(
        self,
        collection: EvidenceCollection,
        data: Dict[str, Any],
        location: Optional[str],
        lat: Optional[float],
        lon: Optional[float],
    ) -> None:
        current = data.get("current", data)
        if not isinstance(current, dict):
            return

        time_str = current.get("time", "current")

        # Current temperature
        if "temperature_2m" in current and current["temperature_2m"] is not None:
            collection.add(EvidenceItem(
                id="ev_obs_temp_current",
                variable=WeatherVariable.TEMPERATURE,
                value=float(current["temperature_2m"]),
                unit="°C",
                location=location,
                latitude=lat,
                longitude=lon,
                time_period=time_str,
                source_type=EvidenceSourceType.OBSERVED,
                source_name="Open-Meteo Current Weather API",
            ))

        # Feels like
        if "apparent_temperature" in current and current["apparent_temperature"] is not None:
            collection.add(EvidenceItem(
                id="ev_obs_feels_like_current",
                variable=WeatherVariable.APPARENT_TEMPERATURE,
                value=float(current["apparent_temperature"]),
                unit="°C",
                location=location,
                latitude=lat,
                longitude=lon,
                time_period=time_str,
                source_type=EvidenceSourceType.OBSERVED,
                source_name="Open-Meteo Current Weather API",
            ))

        # Relative humidity
        if "relative_humidity_2m" in current and current["relative_humidity_2m"] is not None:
            collection.add(EvidenceItem(
                id="ev_obs_humidity_current",
                variable=WeatherVariable.HUMIDITY,
                value=float(current["relative_humidity_2m"]),
                unit="%",
                location=location,
                latitude=lat,
                longitude=lon,
                time_period=time_str,
                source_type=EvidenceSourceType.OBSERVED,
                source_name="Open-Meteo Current Weather API",
            ))

        # Wind speed
        if "wind_speed_10m" in current and current["wind_speed_10m"] is not None:
            collection.add(EvidenceItem(
                id="ev_obs_wind_speed_current",
                variable=WeatherVariable.WIND_SPEED,
                value=float(current["wind_speed_10m"]),
                unit="km/h",
                location=location,
                latitude=lat,
                longitude=lon,
                time_period=time_str,
                source_type=EvidenceSourceType.OBSERVED,
                source_name="Open-Meteo Current Weather API",
            ))

        # Wind direction
        if "wind_direction_10m" in current and current["wind_direction_10m"] is not None:
            deg = float(current["wind_direction_10m"])
            cardinal = degrees_to_cardinal(deg)
            collection.add(EvidenceItem(
                id="ev_obs_wind_dir_current",
                variable=WeatherVariable.WIND_DIRECTION,
                value=cardinal,
                unit="cardinal",
                location=location,
                latitude=lat,
                longitude=lon,
                time_period=time_str,
                source_type=EvidenceSourceType.OBSERVED,
                source_name="Open-Meteo Current Weather API",
                metadata={"degrees": deg},
            ))

        # Pressure
        if "surface_pressure" in current and current["surface_pressure"] is not None:
            collection.add(EvidenceItem(
                id="ev_obs_pressure_current",
                variable=WeatherVariable.PRESSURE,
                value=float(current["surface_pressure"]),
                unit="hPa",
                location=location,
                latitude=lat,
                longitude=lon,
                time_period=time_str,
                source_type=EvidenceSourceType.OBSERVED,
                source_name="Open-Meteo Current Weather API",
            ))

        # Cloud cover
        if "cloud_cover" in current and current["cloud_cover"] is not None:
            collection.add(EvidenceItem(
                id="ev_obs_cloud_current",
                variable=WeatherVariable.CLOUD_COVER,
                value=float(current["cloud_cover"]),
                unit="%",
                location=location,
                latitude=lat,
                longitude=lon,
                time_period=time_str,
                source_type=EvidenceSourceType.OBSERVED,
                source_name="Open-Meteo Current Weather API",
            ))

        # Weather condition
        if "weather_code" in current and current["weather_code"] is not None:
            code = int(current["weather_code"])
            desc = get_weather_description(code)
            collection.add(EvidenceItem(
                id="ev_obs_condition_current",
                variable=WeatherVariable.WEATHER_CONDITION,
                value=desc["condition"],
                unit="condition",
                location=location,
                latitude=lat,
                longitude=lon,
                time_period=time_str,
                source_type=EvidenceSourceType.OBSERVED,
                source_name="Open-Meteo Current Weather API",
                metadata={"weather_code": code, "icon": desc.get("icon")},
            ))

    def _extract_hourly_evidence(
        self,
        collection: EvidenceCollection,
        data: Dict[str, Any],
        location: Optional[str],
        lat: Optional[float],
        lon: Optional[float],
    ) -> None:
        hourly = data.get("hourly", data)
        if not isinstance(hourly, dict):
            return

        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        probs = hourly.get("precipitation_probability", [])
        rains = hourly.get("precipitation", [])
        winds = hourly.get("wind_speed_10m", [])
        humidities = hourly.get("relative_humidity_2m", [])
        codes = hourly.get("weather_code", [])

        # Store forecast for each available hour
        for i, t in enumerate(times):
            hour_str = t

            if i < len(temps) and temps[i] is not None:
                collection.add(EvidenceItem(
                    id=f"ev_fc_temp_{hour_str}",
                    variable=WeatherVariable.TEMPERATURE,
                    value=float(temps[i]),
                    unit="°C",
                    location=location,
                    latitude=lat,
                    longitude=lon,
                    time_period=hour_str,
                    source_type=EvidenceSourceType.FORECAST,
                    source_name="Open-Meteo Hourly Forecast",
                ))

            if i < len(probs) and probs[i] is not None:
                collection.add(EvidenceItem(
                    id=f"ev_fc_precip_prob_{hour_str}",
                    variable=WeatherVariable.PRECIPITATION_PROBABILITY,
                    value=float(probs[i]),
                    unit="%",
                    location=location,
                    latitude=lat,
                    longitude=lon,
                    time_period=hour_str,
                    source_type=EvidenceSourceType.FORECAST,
                    source_name="Open-Meteo Hourly Forecast",
                ))

            if i < len(rains) and rains[i] is not None:
                collection.add(EvidenceItem(
                    id=f"ev_fc_precip_amt_{hour_str}",
                    variable=WeatherVariable.PRECIPITATION_AMOUNT,
                    value=float(rains[i]),
                    unit="mm",
                    location=location,
                    latitude=lat,
                    longitude=lon,
                    time_period=hour_str,
                    source_type=EvidenceSourceType.FORECAST,
                    source_name="Open-Meteo Hourly Forecast",
                ))

            if i < len(winds) and winds[i] is not None:
                collection.add(EvidenceItem(
                    id=f"ev_fc_wind_{hour_str}",
                    variable=WeatherVariable.WIND_SPEED,
                    value=float(winds[i]),
                    unit="km/h",
                    location=location,
                    latitude=lat,
                    longitude=lon,
                    time_period=hour_str,
                    source_type=EvidenceSourceType.FORECAST,
                    source_name="Open-Meteo Hourly Forecast",
                ))

            if i < len(humidities) and humidities[i] is not None:
                collection.add(EvidenceItem(
                    id=f"ev_fc_humidity_{hour_str}",
                    variable=WeatherVariable.HUMIDITY,
                    value=float(humidities[i]),
                    unit="%",
                    location=location,
                    latitude=lat,
                    longitude=lon,
                    time_period=hour_str,
                    source_type=EvidenceSourceType.FORECAST,
                    source_name="Open-Meteo Hourly Forecast",
                ))

            if i < len(codes) and codes[i] is not None:
                c_desc = get_weather_description(int(codes[i]))
                collection.add(EvidenceItem(
                    id=f"ev_fc_condition_{hour_str}",
                    variable=WeatherVariable.WEATHER_CONDITION,
                    value=c_desc["condition"],
                    unit="condition",
                    location=location,
                    latitude=lat,
                    longitude=lon,
                    time_period=hour_str,
                    source_type=EvidenceSourceType.FORECAST,
                    source_name="Open-Meteo Hourly Forecast",
                ))

    def _extract_analysis_evidence(
        self,
        collection: EvidenceCollection,
        analysis: Dict[str, Any],
        location: Optional[str],
        lat: Optional[float],
        lon: Optional[float],
    ) -> None:
        period_label = analysis.get("day_analyzed", "forecast_period")

        # Temperature Analysis
        temp = analysis.get("temperature", {})
        if isinstance(temp, dict) and temp.get("status") == "ok":
            for metric, var in [
                ("min_temperature", WeatherVariable.TEMPERATURE),
                ("max_temperature", WeatherVariable.TEMPERATURE),
                ("average_temperature", WeatherVariable.TEMPERATURE),
            ]:
                if metric in temp:
                    collection.add(EvidenceItem(
                        id=f"ev_derived_{metric}_{period_label}",
                        variable=var,
                        value=float(temp[metric]),
                        unit="°C",
                        location=location,
                        latitude=lat,
                        longitude=lon,
                        time_period=period_label,
                        source_type=EvidenceSourceType.DERIVED,
                        source_name="Phase 3 Temperature Analysis",
                        analysis_method="extremes_and_mean",
                        metadata={"metric_type": metric},
                    ))

            if "trend" in temp:
                collection.add(EvidenceItem(
                    id=f"ev_derived_temp_trend_{period_label}",
                    variable=WeatherVariable.TEMPERATURE_TREND,
                    value=temp["trend"],
                    unit="trend",
                    location=location,
                    latitude=lat,
                    longitude=lon,
                    time_period=period_label,
                    source_type=EvidenceSourceType.DERIVED,
                    source_name="Phase 3 Temperature Analysis",
                    analysis_method="linear_trend_detection",
                    metadata={"description": temp.get("trend_description", "")},
                ))

        # Precipitation Analysis
        precip = analysis.get("precipitation", {})
        if isinstance(precip, dict) and precip.get("status") == "ok":
            if "max_probability" in precip:
                collection.add(EvidenceItem(
                    id=f"ev_derived_max_precip_prob_{period_label}",
                    variable=WeatherVariable.PRECIPITATION_PROBABILITY,
                    value=float(precip["max_probability"]),
                    unit="%",
                    location=location,
                    latitude=lat,
                    longitude=lon,
                    time_period=period_label,
                    source_type=EvidenceSourceType.DERIVED,
                    source_name="Phase 3 Precipitation Analysis",
                    analysis_method="peak_probability",
                ))

            if "total_expected_rain_mm" in precip:
                collection.add(EvidenceItem(
                    id=f"ev_derived_total_rain_{period_label}",
                    variable=WeatherVariable.PRECIPITATION_AMOUNT,
                    value=float(precip["total_expected_rain_mm"]),
                    unit="mm",
                    location=location,
                    latitude=lat,
                    longitude=lon,
                    time_period=period_label,
                    source_type=EvidenceSourceType.DERIVED,
                    source_name="Phase 3 Precipitation Analysis",
                    analysis_method="cumulative_sum",
                ))

        # Wind Analysis
        wind = analysis.get("wind", {})
        if isinstance(wind, dict) and wind.get("status") == "ok":
            if "max_wind_speed" in wind:
                collection.add(EvidenceItem(
                    id=f"ev_derived_max_wind_{period_label}",
                    variable=WeatherVariable.WIND_SPEED,
                    value=float(wind["max_wind_speed"]),
                    unit="km/h",
                    location=location,
                    latitude=lat,
                    longitude=lon,
                    time_period=period_label,
                    source_type=EvidenceSourceType.DERIVED,
                    source_name="Phase 3 Wind Analysis",
                    analysis_method="peak_wind_detection",
                ))

            if "prevailing_direction" in wind:
                collection.add(EvidenceItem(
                    id=f"ev_derived_prevailing_wind_dir_{period_label}",
                    variable=WeatherVariable.WIND_DIRECTION,
                    value=wind["prevailing_direction"],
                    unit="cardinal",
                    location=location,
                    latitude=lat,
                    longitude=lon,
                    time_period=period_label,
                    source_type=EvidenceSourceType.DERIVED,
                    source_name="Phase 3 Wind Analysis",
                    analysis_method="modal_direction",
                ))

        # Decision Support Evidence
        dec = analysis.get("decision_support", {})
        if not dec and "umbrella" in analysis:
            dec = analysis  # In case get_weather_decision_support was passed directly

        if isinstance(dec, dict):
            # Umbrella recommendation
            umb = dec.get("umbrella", {})
            if isinstance(umb, dict) and "recommended" in umb:
                collection.add(EvidenceItem(
                    id=f"ev_derived_umbrella_{period_label}",
                    variable=WeatherVariable.UMBRELLA_NEED,
                    value=bool(umb["recommended"]),
                    unit="recommendation",
                    location=location,
                    latitude=lat,
                    longitude=lon,
                    time_period=period_label,
                    source_type=EvidenceSourceType.DERIVED,
                    source_name="Phase 3 Decision Support",
                    analysis_method="rain_threshold_evaluation",
                    metadata={"reason": umb.get("reason", ""), "confidence": umb.get("confidence", "high")},
                ))

                reason_str = str(umb.get("reason", ""))
                prob_match = re.search(r"(\d+(?:\.\d+)?)\s*%", reason_str)
                if prob_match and not collection.find_by_variable(WeatherVariable.PRECIPITATION_PROBABILITY):
                    collection.add(EvidenceItem(
                        id=f"ev_derived_max_precip_prob_{period_label}",
                        variable=WeatherVariable.PRECIPITATION_PROBABILITY,
                        value=float(prob_match.group(1)),
                        unit="%",
                        location=location,
                        latitude=lat,
                        longitude=lon,
                        time_period=period_label,
                        source_type=EvidenceSourceType.DERIVED,
                        source_name="Phase 3 Decision Support",
                        analysis_method="recommendation_rain_reason",
                    ))

            # Outdoor activities suitability
            out = dec.get("outdoor_activities", {})
            if isinstance(out, dict) and "best_period" in out:
                collection.add(EvidenceItem(
                    id=f"ev_derived_outdoor_best_{period_label}",
                    variable=WeatherVariable.OUTDOOR_SUITABILITY,
                    value=out["best_period"],
                    unit="time_block",
                    location=location,
                    latitude=lat,
                    longitude=lon,
                    time_period=period_label,
                    source_type=EvidenceSourceType.DERIVED,
                    source_name="Phase 3 Decision Support",
                    analysis_method="multivariate_comfort_scoring",
                    metadata={
                        "best_range": out.get("best_time_range", ""),
                        "rating": out.get("overall_rating", ""),
                        "recommendation": out.get("recommendation", "")
                    },
                ))

            # Travel suitability
            trav = dec.get("travel", {})
            if isinstance(trav, dict) and "suitability_status" in trav:
                collection.add(EvidenceItem(
                    id=f"ev_derived_travel_{period_label}",
                    variable=WeatherVariable.TRAVEL_SUITABILITY,
                    value=trav["suitability_status"],
                    unit="status",
                    location=location,
                    latitude=lat,
                    longitude=lon,
                    time_period=period_label,
                    source_type=EvidenceSourceType.DERIVED,
                    source_name="Phase 3 Decision Support",
                    analysis_method="hazard_criteria_scoring",
                    metadata={"summary": trav.get("summary", ""), "advisories": trav.get("advisories", [])},
                ))
