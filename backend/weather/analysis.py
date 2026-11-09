import math
from typing import Any, Dict, List, Optional, Tuple

try:
    from backend.weather.weather_codes import get_weather_description
except ImportError:
    from weather.weather_codes import get_weather_description


CARDINAL_DIRECTIONS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
]


def degrees_to_cardinal(degrees: Optional[float]) -> str:
    """Converts wind direction in degrees (0-360) to a cardinal direction string."""
    if degrees is None:
        return "Unknown"
    deg = float(degrees) % 360
    idx = int((deg + 11.25) / 22.5) % 16
    return CARDINAL_DIRECTIONS[idx]


def safe_series(data: dict, key: str, start: int = 0, count: int = 24, default_val: float = 0.0) -> List[Any]:
    """Safely extracts a slice of a series from Open-Meteo hourly dictionary."""
    if not isinstance(data, dict):
        return [default_val] * count
    hourly = data.get("hourly", data)
    if not isinstance(hourly, dict):
        return [default_val] * count
    arr = hourly.get(key)
    if not isinstance(arr, list) or len(arr) == 0:
        return [default_val] * count

    sliced = arr[start:start + count]
    # Clean any None or invalid values
    cleaned = []
    for item in sliced:
        if item is None:
            cleaned.append(default_val)
        else:
            cleaned.append(item)

    if len(cleaned) < count:
        cleaned.extend([default_val] * (count - len(cleaned)))
    return cleaned


# =====================================================================
# A. Temperature Analysis
# =====================================================================

def analyze_temperature(hourly_data: dict, start_index: int = 0, count: int = 24) -> Dict[str, Any]:
    """
    Analyzes temperature patterns over a given hourly window.
    Identifies min/max, trend direction, rate of change, and steepest shifts.
    """
    times = safe_series(hourly_data, "time", start_index, count, default_val="")
    temps = safe_series(hourly_data, "temperature_2m", start_index, count, default_val=0.0)

    # Filter out empty entries if data is completely empty
    valid_temps = [float(t) for t in temps if isinstance(t, (int, float))]
    if not valid_temps:
        return {
            "status": "error",
            "message": "No valid temperature data available for analysis.",
        }

    min_t = min(valid_temps)
    max_t = max(valid_temps)
    min_idx = valid_temps.index(min_t)
    max_idx = valid_temps.index(max_t)
    avg_t = sum(valid_temps) / len(valid_temps)

    start_t = valid_temps[0]
    end_t = valid_temps[-1]
    net_diff = end_t - start_t

    # Hour to hour deltas
    deltas = [valid_temps[i + 1] - valid_temps[i] for i in range(len(valid_temps) - 1)]

    steepest_rise = {"delta": 0.0, "time": ""}
    steepest_drop = {"delta": 0.0, "time": ""}

    if deltas:
        max_rise = max(deltas)
        max_drop = min(deltas)
        if max_rise > 0:
            rise_idx = deltas.index(max_rise)
            steepest_rise = {
                "delta": round(max_rise, 2),
                "from_time": times[rise_idx] if rise_idx < len(times) else "",
                "to_time": times[rise_idx + 1] if rise_idx + 1 < len(times) else "",
            }
        if max_drop < 0:
            drop_idx = deltas.index(max_drop)
            steepest_drop = {
                "delta": round(max_drop, 2),
                "from_time": times[drop_idx] if drop_idx < len(times) else "",
                "to_time": times[drop_idx + 1] if drop_idx + 1 < len(times) else "",
            }

    # Trend categorization
    if net_diff >= 1.5:
        trend = "increasing"
        trend_desc = f"Temperatures follow an upward trend, rising by {round(net_diff, 1)}°C over the period."
    elif net_diff <= -1.5:
        trend = "decreasing"
        trend_desc = f"Temperatures follow a downward trend, dropping by {round(abs(net_diff), 1)}°C over the period."
    else:
        trend = "steady"
        trend_desc = f"Temperatures remain relatively stable (net change of {round(net_diff, 1)}°C)."

    return {
        "status": "ok",
        "min_temperature": round(min_t, 1),
        "min_temperature_time": times[min_idx] if min_idx < len(times) else "",
        "max_temperature": round(max_t, 1),
        "max_temperature_time": times[max_idx] if max_idx < len(times) else "",
        "average_temperature": round(avg_t, 1),
        "temperature_range": round(max_t - min_t, 1),
        "start_temperature": round(start_t, 1),
        "end_temperature": round(end_t, 1),
        "net_temperature_difference": round(net_diff, 1),
        "trend": trend,
        "trend_description": trend_desc,
        "steepest_rise": steepest_rise,
        "steepest_drop": steepest_drop,
    }


# =====================================================================
# B. Humidity Analysis
# =====================================================================

def analyze_humidity(hourly_data: dict, start_index: int = 0, count: int = 24) -> Dict[str, Any]:
    """
    Analyzes humidity levels, significant changes, and perceived comfort impact.
    """
    times = safe_series(hourly_data, "time", start_index, count, default_val="")
    humidities = safe_series(hourly_data, "relative_humidity_2m", start_index, count, default_val=50.0)

    valid_h = [float(h) for h in humidities if isinstance(h, (int, float))]
    if not valid_h:
        return {"status": "error", "message": "No valid humidity data available."}

    min_h = min(valid_h)
    max_h = max(valid_h)
    avg_h = sum(valid_h) / len(valid_h)

    # Detect significant shifts (>= 15% change in 2 hours)
    significant_shifts = []
    for i in range(len(valid_h) - 2):
        delta = valid_h[i + 2] - valid_h[i]
        if abs(delta) >= 15.0:
            significant_shifts.append({
                "from_time": times[i],
                "to_time": times[i + 2],
                "change": round(delta, 1),
                "type": "surge" if delta > 0 else "drop",
            })

    # Comfort level classification
    if avg_h < 30.0:
        comfort = "dry"
        impact = "Air is dry; may cause dry skin and throat irritation. Hydration recommended."
    elif avg_h <= 60.0:
        comfort = "comfortable"
        impact = "Optimal humidity levels. Pleasant and comfortable for indoor and outdoor activities."
    elif avg_h <= 75.0:
        comfort = "moderately_humid"
        impact = "Noticeable moisture in the air. Warm temperatures will feel slightly warmer."
    else:
        comfort = "oppressive"
        impact = "High humidity creates a muggy/heavy atmosphere. Sweat evaporation is hindered."

    return {
        "status": "ok",
        "min_humidity": round(min_h, 1),
        "max_humidity": round(max_h, 1),
        "average_humidity": round(avg_h, 1),
        "comfort_level": comfort,
        "perceived_impact": impact,
        "significant_shifts_count": len(significant_shifts),
        "significant_shifts": significant_shifts[:3],  # top 3 shifts
    }


# =====================================================================
# C. Precipitation Analysis
# =====================================================================

def analyze_precipitation(hourly_data: dict, start_index: int = 0, count: int = 24) -> Dict[str, Any]:
    """
    Analyzes precipitation probability vs expected volume, identifying peak rain periods
    and distinguishing probability from actual accumulation.
    """
    times = safe_series(hourly_data, "time", start_index, count, default_val="")
    probs = safe_series(hourly_data, "precipitation_probability", start_index, count, default_val=0.0)
    amounts = safe_series(hourly_data, "precipitation", start_index, count, default_val=0.0)

    valid_probs = [float(p) for p in probs]
    valid_amounts = [float(a) for a in amounts]

    if not valid_probs:
        return {"status": "error", "message": "No valid precipitation data available."}

    max_prob = max(valid_probs)
    max_prob_idx = valid_probs.index(max_prob)
    avg_prob = sum(valid_probs) / len(valid_probs)
    total_rain = sum(valid_amounts)
    max_hourly_rain = max(valid_amounts) if valid_amounts else 0.0

    # Periods with elevated rain risk (prob >= 35% or amount >= 0.2 mm)
    elevated_periods = []
    for i in range(len(valid_probs)):
        if valid_probs[i] >= 35.0 or valid_amounts[i] >= 0.2:
            elevated_periods.append({
                "time": times[i] if i < len(times) else "",
                "probability": round(valid_probs[i], 1),
                "expected_mm": round(valid_amounts[i], 2),
            })

    # Risk level determination
    if max_prob >= 70.0 or total_rain >= 5.0:
        risk_level = "high"
    elif max_prob >= 35.0 or total_rain >= 1.0:
        risk_level = "moderate"
    elif max_prob >= 15.0 or total_rain >= 0.1:
        risk_level = "low"
    else:
        risk_level = "none"

    # Explicit distinction note between probability and accumulation
    if total_rain < 0.2 and max_prob > 40.0:
        distinction = (
            f"Note: Elevated rain probability ({round(max_prob)}%), but minimal accumulation is expected "
            f"({round(total_rain, 1)} mm). Light, fleeting showers or sprinkles are possible."
        )
    elif total_rain >= 5.0 and max_prob < 50.0:
        distinction = (
            f"Note: Moderate probability ({round(max_prob)}%), but significant rainfall volume ({round(total_rain, 1)} mm) "
            f"could occur if a storm system hits."
        )
    elif max_prob <= 15.0 and total_rain < 0.1:
        distinction = "Dry conditions expected. Rain probability and accumulation are both near zero."
    else:
        distinction = (
            f"Precipitation chance peaks at {round(max_prob)}% with an estimated cumulative total of {round(total_rain, 1)} mm."
        )

    return {
        "status": "ok",
        "max_probability": round(max_prob, 1),
        "max_probability_time": times[max_prob_idx] if max_prob_idx < len(times) else "",
        "average_probability": round(avg_prob, 1),
        "total_expected_rain_mm": round(total_rain, 2),
        "max_hourly_rain_mm": round(max_hourly_rain, 2),
        "risk_level": risk_level,
        "elevated_periods_count": len(elevated_periods),
        "elevated_periods": elevated_periods[:5],
        "distinction_note": distinction,
    }


# =====================================================================
# D. Wind Analysis
# =====================================================================

def analyze_wind(hourly_data: dict, start_index: int = 0, count: int = 24) -> Dict[str, Any]:
    """
    Analyzes wind speed, directions, gusts, and potentially hazardous or strong wind periods.
    """
    times = safe_series(hourly_data, "time", start_index, count, default_val="")
    speeds = safe_series(hourly_data, "wind_speed_10m", start_index, count, default_val=0.0)
    directions = safe_series(hourly_data, "wind_direction_10m", start_index, count, default_val=None)

    valid_speeds = [float(s) for s in speeds]
    if not valid_speeds:
        return {"status": "error", "message": "No valid wind data available."}

    min_speed = min(valid_speeds)
    max_speed = max(valid_speeds)
    max_speed_idx = valid_speeds.index(max_speed)
    avg_speed = sum(valid_speeds) / len(valid_speeds)

    # Prevailing direction
    valid_dirs = [d for d in directions if d is not None and isinstance(d, (int, float))]
    if valid_dirs:
        cardinals = [degrees_to_cardinal(d) for d in valid_dirs]
        prevailing_dir = max(set(cardinals), key=cardinals.count)
    else:
        prevailing_dir = "Variable"

    # Strong wind periods (speeds >= 20.0 km/h)
    strong_periods = []
    for i in range(len(valid_speeds)):
        if valid_speeds[i] >= 20.0:
            strong_periods.append({
                "time": times[i] if i < len(times) else "",
                "speed_kmh": round(valid_speeds[i], 1),
                "direction": degrees_to_cardinal(directions[i]) if i < len(directions) else "Unknown",
            })

    # Classification
    if max_speed < 12.0:
        category = "light_calm"
        desc = "Calm to light breeze. Ideal for all outdoor activities."
    elif max_speed < 25.0:
        category = "moderate_breeze"
        desc = "Moderate breeze. Noticeable and refreshing, generally comfortable."
    elif max_speed < 40.0:
        category = "fresh_strong"
        desc = "Fresh to strong breeze. Dust and paper may blow; umbrellas may turn inside out."
    else:
        category = "near_gale"
        desc = "High wind / near gale warning. Walking against wind is difficult; secure loose objects."

    return {
        "status": "ok",
        "min_wind_speed": round(min_speed, 1),
        "max_wind_speed": round(max_speed, 1),
        "max_wind_time": times[max_speed_idx] if max_speed_idx < len(times) else "",
        "average_wind_speed": round(avg_speed, 1),
        "prevailing_direction": prevailing_dir,
        "wind_category": category,
        "description": desc,
        "strong_periods_count": len(strong_periods),
        "strong_periods": strong_periods[:4],
    }


# =====================================================================
# E. Weather Pattern & Trend Detection
# =====================================================================

def detect_weather_patterns(hourly_data: dict, start_index: int = 0, count: int = 24) -> Dict[str, Any]:
    """
    Detects dynamic meteorological patterns, condition changes, pressure trends,
    and multi-variable stability indicators.
    """
    times = safe_series(hourly_data, "time", start_index, count, default_val="")
    codes = safe_series(hourly_data, "weather_code", start_index, count, default_val=0)
    pressures = safe_series(hourly_data, "surface_pressure", start_index, count, default_val=None)
    cloud_covers = safe_series(hourly_data, "cloud_cover", start_index, count, default_val=0.0)

    # Condition sequence
    conditions_sequence = []
    last_condition = None
    for i, code in enumerate(codes):
        info = get_weather_description(code)
        cond = info.get("condition", "Clear sky")
        if cond != last_condition:
            conditions_sequence.append({
                "time": times[i] if i < len(times) else "",
                "condition": cond,
                "icon": info.get("icon", "☀️"),
            })
            last_condition = cond

    # Pressure trend analysis (if pressure data exists)
    valid_pressures = [p for p in pressures if p is not None and isinstance(p, (int, float))]
    pressure_trend = "stable"
    pressure_desc = "Atmospheric pressure is steady."

    if len(valid_pressures) >= 2:
        start_p = valid_pressures[0]
        end_p = valid_pressures[-1]
        p_diff = end_p - start_p
        min_p = min(valid_pressures)
        max_p = max(valid_pressures)

        # Check net diff and any sharp drops within the window
        max_drop = min_p - start_p
        if p_diff <= -3.0 or max_drop <= -3.0:
            pressure_trend = "falling_rapidly"
            pressure_desc = f"Significant pressure drop detected (down to {round(min_p, 1)} hPa, drop of {round(abs(max_drop), 1)} hPa), often indicating storm systems or frontal activity."
        elif p_diff <= -1.0 or max_drop <= -1.5:
            pressure_trend = "falling"
            pressure_desc = f"Pressure is trending downward (down to {round(min_p, 1)} hPa), indicating unsettled weather."
        elif p_diff >= 3.0:
            pressure_trend = "rising_rapidly"
            pressure_desc = f"Pressure is rising rapidly (+{round(p_diff, 1)} hPa), indicating clearing and stabilizing skies."
        elif p_diff >= 1.0:
            pressure_trend = "rising"
            pressure_desc = f"Pressure is rising slightly (+{round(p_diff, 1)} hPa), indicating improving conditions."

    # Cloud cover trend
    valid_clouds = [float(c) for c in cloud_covers if isinstance(c, (int, float))]
    avg_cloud = sum(valid_clouds) / len(valid_clouds) if valid_clouds else 0.0

    return {
        "status": "ok",
        "condition_changes_count": len(conditions_sequence),
        "conditions_sequence": conditions_sequence,
        "pressure_trend": pressure_trend,
        "pressure_description": pressure_desc,
        "average_cloud_cover_percent": round(avg_cloud, 1),
    }


# =====================================================================
# F. Time-Based Aggregations (6-Hour Blocks & Daily Comparisons)
# =====================================================================

def aggregate_6hour_blocks(hourly_data: dict, day_offset: int = 0) -> Dict[str, Any]:
    """
    Aggregates a 24-hour day into 4 standard 6-hour meteorological periods:
    Night (00-06), Morning (06-12), Afternoon (12-18), Evening (18-24).
    """
    start_index = day_offset * 24
    period_definitions = [
        {"name": "Night", "hours": "00:00 - 06:00", "start": 0, "end": 6},
        {"name": "Morning", "hours": "06:00 - 12:00", "start": 6, "end": 12},
        {"name": "Afternoon", "hours": "12:00 - 18:00", "start": 12, "end": 18},
        {"name": "Evening", "hours": "18:00 - 24:00", "start": 18, "end": 24},
    ]

    blocks = []
    for p in period_definitions:
        sub_start = start_index + p["start"]
        t_sub = safe_series(hourly_data, "temperature_2m", sub_start, 6, 0.0)
        p_sub = safe_series(hourly_data, "precipitation_probability", sub_start, 6, 0.0)
        r_sub = safe_series(hourly_data, "precipitation", sub_start, 6, 0.0)
        w_sub = safe_series(hourly_data, "wind_speed_10m", sub_start, 6, 0.0)
        c_sub = safe_series(hourly_data, "weather_code", sub_start, 6, 0)

        # Most common weather condition in block
        dominant_code = max(set(c_sub), key=c_sub.count) if c_sub else 0
        desc = get_weather_description(dominant_code)

        blocks.append({
            "period": p["name"],
            "time_range": p["hours"],
            "min_temperature": round(min(t_sub), 1),
            "max_temperature": round(max(t_sub), 1),
            "avg_temperature": round(sum(t_sub) / len(t_sub), 1),
            "max_rain_probability": round(max(p_sub), 1),
            "total_rainfall_mm": round(sum(r_sub), 2),
            "avg_wind_speed": round(sum(w_sub) / len(w_sub), 1),
            "condition": desc["condition"],
            "icon": desc["icon"],
        })

    return {
        "status": "ok",
        "day_offset": day_offset,
        "blocks": blocks,
    }


def compare_days(hourly_data: dict) -> Dict[str, Any]:
    """
    Compares Today (Day 1, hours 0-23) with Tomorrow (Day 2, hours 24-47).
    Highlights temperature change, rainfall variance, and wind trends.
    """
    day1_temp = analyze_temperature(hourly_data, 0, 24)
    day2_temp = analyze_temperature(hourly_data, 24, 24)

    day1_rain = analyze_precipitation(hourly_data, 0, 24)
    day2_rain = analyze_precipitation(hourly_data, 24, 24)

    day1_wind = analyze_wind(hourly_data, 0, 24)
    day2_wind = analyze_wind(hourly_data, 24, 24)

    if day1_temp.get("status") != "ok" or day2_temp.get("status") != "ok":
        return {
            "status": "error",
            "message": "Insufficient hourly forecast data to perform daily comparison.",
        }

    temp_delta = round(day2_temp["average_temperature"] - day1_temp["average_temperature"], 1)
    max_temp_delta = round(day2_temp["max_temperature"] - day1_temp["max_temperature"], 1)
    rain_delta = round(day2_rain["total_expected_rain_mm"] - day1_rain["total_expected_rain_mm"], 2)
    wind_delta = round(day2_wind["average_wind_speed"] - day1_wind["average_wind_speed"], 1)

    # Narrative summary
    temp_comp = "warmer" if temp_delta > 0.5 else ("cooler" if temp_delta < -0.5 else "about the same temperature")
    rain_comp = "wetter" if rain_delta > 0.5 else ("drier" if rain_delta < -0.5 else "similar precipitation levels")

    summary = (
        f"Tomorrow is expected to be {temp_comp} (average temp {temp_delta:+}°C, peak {max_temp_delta:+}°C) "
        f"and {rain_comp} compared to today."
    )

    return {
        "status": "ok",
        "day1": {
            "avg_temperature": day1_temp["average_temperature"],
            "max_temperature": day1_temp["max_temperature"],
            "total_rain_mm": day1_rain["total_expected_rain_mm"],
            "avg_wind_kmh": day1_wind["average_wind_speed"],
        },
        "day2": {
            "avg_temperature": day2_temp["average_temperature"],
            "max_temperature": day2_temp["max_temperature"],
            "total_rain_mm": day2_rain["total_expected_rain_mm"],
            "avg_wind_kmh": day2_wind["average_wind_speed"],
        },
        "deltas": {
            "average_temp_diff": temp_delta,
            "max_temp_diff": max_temp_delta,
            "rain_diff_mm": rain_delta,
            "wind_diff_kmh": wind_delta,
        },
        "comparison_summary": summary,
    }


# =====================================================================
# G. Weather Decision Support (Umbrella, Outdoor, Travel)
# =====================================================================

def evaluate_umbrella_recommendation(precipitation_analysis: dict) -> Dict[str, Any]:
    """Evaluates whether carrying an umbrella is recommended based on forecast data."""
    max_prob = precipitation_analysis.get("max_probability", 0.0)
    total_rain = precipitation_analysis.get("total_expected_rain_mm", 0.0)
    peak_time = precipitation_analysis.get("max_probability_time", "")

    if max_prob >= 50.0 or total_rain >= 1.0:
        recommended = True
        confidence = "high"
        reason = (
            f"Yes, carrying an umbrella is strongly advised. Rain probability reaches {round(max_prob)}% "
            f"with {round(total_rain, 1)} mm rainfall expected."
        )
    elif max_prob >= 25.0 or total_rain >= 0.2:
        recommended = True
        confidence = "moderate"
        reason = (
            f"Carrying a compact umbrella is recommended as a precaution. There is a {round(max_prob)}% chance of rain "
            f"with light showers possible."
        )
    else:
        recommended = False
        confidence = "high"
        reason = (
            f"No umbrella needed. Rain probability remains very low (peak {round(max_prob)}%) with "
            f"{round(total_rain, 1)} mm rain expected."
        )

    return {
        "recommended": recommended,
        "confidence": confidence,
        "reason": reason,
        "peak_time": peak_time,
    }


def evaluate_outdoor_suitability(blocks: list) -> Dict[str, Any]:
    """
    Evaluates 6-hour blocks to find the best and least favorable times for outdoor activities.
    Scored based on temperature comfort (18-25°C), low precipitation, and gentle wind (< 20 km/h).
    """
    if not blocks:
        return {"status": "error", "message": "No block data available."}

    scored_periods = []
    for b in blocks:
        score = 100.0
        # Penalize rain probability heavily
        score -= b["max_rain_probability"] * 0.7
        # Penalize rainfall volume
        score -= min(b["total_rainfall_mm"] * 10, 30.0)
        # Penalize extreme wind
        if b["avg_wind_speed"] > 20.0:
            score -= (b["avg_wind_speed"] - 20.0) * 2.0
        # Penalize temperature deviation from ideal 21°C
        temp_penalty = abs(b["avg_temperature"] - 21.0) * 1.5
        score -= min(temp_penalty, 30.0)

        scored_periods.append((score, b))

    scored_periods.sort(key=lambda x: x[0], reverse=True)
    best_period = scored_periods[0][1]
    worst_period = scored_periods[-1][1]

    best_score = scored_periods[0][0]
    if best_score >= 80:
        rating = "Excellent"
    elif best_score >= 60:
        rating = "Good"
    elif best_score >= 40:
        rating = "Fair"
    else:
        rating = "Challenging"

    recommendation = (
        f"The best window for outdoor activities is {best_period['period']} ({best_period['time_range']}) "
        f"with pleasant temperatures ({best_period['avg_temperature']}°C) and minimal rain risk ({best_period['max_rain_probability']}%). "
        f"The least favorable window is {worst_period['period']} ({worst_period['time_range']})."
    )

    return {
        "overall_rating": rating,
        "best_period": best_period["period"],
        "best_time_range": best_period["time_range"],
        "worst_period": worst_period["period"],
        "worst_time_range": worst_period["time_range"],
        "recommendation": recommendation,
    }


def evaluate_travel_suitability(precip_analysis: dict, wind_analysis: dict, pattern_analysis: dict) -> Dict[str, Any]:
    """
    Evaluates weather suitability for local/regional road and air travel.
    Considers adverse factors: severe rain, gale winds, fog/freezing conditions, thunderstorms.
    """
    max_prob = precip_analysis.get("max_probability", 0.0)
    total_rain = precip_analysis.get("total_expected_rain_mm", 0.0)
    max_wind = wind_analysis.get("max_wind_speed", 0.0)

    advisories = []
    caution_level = "low"

    if total_rain >= 15.0 or max_prob >= 80.0:
        advisories.append("Heavy rain may cause reduced visibility, waterlogging, and slick road surfaces.")
        caution_level = "high"
    elif total_rain >= 3.0:
        advisories.append("Wet road conditions expected; allow extra travel time.")
        if caution_level == "low":
            caution_level = "moderate"

    if max_wind >= 40.0:
        advisories.append("High wind warnings in effect; caution advised for high-profile vehicles.")
        caution_level = "high"
    elif max_wind >= 25.0:
        advisories.append("Breezy conditions; hold the steering wheel firmly on exposed highways.")

    # Check for fog or storm codes
    for item in pattern_analysis.get("conditions_sequence", []):
        cond_lower = item.get("condition", "").lower()
        if "fog" in cond_lower:
            advisories.append("Foggy conditions may impair highway visibility during early morning hours.")
            if caution_level == "low":
                caution_level = "moderate"
        elif "thunderstorm" in cond_lower:
            advisories.append("Thunderstorms detected; travel delays possible.")
            caution_level = "high"

    if caution_level == "low":
        status = "Suitable"
        summary = "Travel conditions are favorable with no significant weather impediments detected."
    elif caution_level == "moderate":
        status = "Fair (Exercise Normal Caution)"
        summary = "Travel is generally suitable, but remain aware of minor rain, wind, or visibility factors."
    else:
        status = "Caution Advised"
        summary = "Adverse weather conditions detected. Plan ahead, exercise caution, or postpone non-essential transit."

    return {
        "suitability_status": status,
        "caution_level": caution_level,
        "summary": summary,
        "advisories": advisories if advisories else ["No severe weather hazards anticipated."],
    }


def get_weather_decision_support(hourly_data: dict, day_offset: int = 1) -> Dict[str, Any]:
    """
    Comprehensive decision support function for user queries (e.g. umbrella, travel, outdoor activities).
    Default day_offset=1 analyzes tomorrow (hours 24-47), while day_offset=0 analyzes today (hours 0-23).
    """
    start_idx = day_offset * 24
    temp_analysis = analyze_temperature(hourly_data, start_idx, 24)
    precip_analysis = analyze_precipitation(hourly_data, start_idx, 24)
    wind_analysis = analyze_wind(hourly_data, start_idx, 24)
    pattern_analysis = detect_weather_patterns(hourly_data, start_idx, 24)
    blocks_analysis = aggregate_6hour_blocks(hourly_data, day_offset=day_offset)

    umbrella = evaluate_umbrella_recommendation(precip_analysis)
    outdoor = evaluate_outdoor_suitability(blocks_analysis.get("blocks", []))
    travel = evaluate_travel_suitability(precip_analysis, wind_analysis, pattern_analysis)

    return {
        "status": "ok",
        "day_analyzed": "tomorrow" if day_offset == 1 else "today",
        "umbrella": umbrella,
        "outdoor_activities": outdoor,
        "travel": travel,
        "temperature_trend": temp_analysis.get("trend", "steady"),
        "temperature_summary": temp_analysis.get("trend_description", ""),
    }


# =====================================================================
# Comprehensive Weather Analysis Coordinator
# =====================================================================

def analyze_weather_data(hourly_data: dict, focus: str = "all", day_offset: int = 1) -> Dict[str, Any]:
    """
    Main entry point for Python weather analysis engine.
    Focus options: 'all', 'temperature', 'precipitation', 'wind', 'humidity', 'patterns', 'recommendations', 'comparison'.
    """
    start_idx = day_offset * 24

    if focus == "temperature":
        return {
            "status": "ok",
            "focus": "temperature",
            "temperature": analyze_temperature(hourly_data, start_idx, 24),
            "6hour_blocks": aggregate_6hour_blocks(hourly_data, day_offset=day_offset).get("blocks", []),
        }

    if focus == "precipitation":
        p_res = analyze_precipitation(hourly_data, start_idx, 24)
        return {
            "status": "ok",
            "focus": "precipitation",
            "precipitation": p_res,
            "umbrella_advice": evaluate_umbrella_recommendation(p_res),
        }

    if focus == "wind":
        return {
            "status": "ok",
            "focus": "wind",
            "wind": analyze_wind(hourly_data, start_idx, 24),
        }

    if focus == "humidity":
        return {
            "status": "ok",
            "focus": "humidity",
            "humidity": analyze_humidity(hourly_data, start_idx, 24),
        }

    if focus == "recommendations":
        return get_weather_decision_support(hourly_data, day_offset=day_offset)

    if focus == "comparison":
        return compare_days(hourly_data)

    # focus == "all": return balanced, high-signal structured intelligence
    temp_res = analyze_temperature(hourly_data, start_idx, 24)
    precip_res = analyze_precipitation(hourly_data, start_idx, 24)
    wind_res = analyze_wind(hourly_data, start_idx, 24)
    humidity_res = analyze_humidity(hourly_data, start_idx, 24)
    pattern_res = detect_weather_patterns(hourly_data, start_idx, 24)
    blocks_res = aggregate_6hour_blocks(hourly_data, day_offset=day_offset)
    day_comp = compare_days(hourly_data)

    umbrella = evaluate_umbrella_recommendation(precip_res)
    outdoor = evaluate_outdoor_suitability(blocks_res.get("blocks", []))
    travel = evaluate_travel_suitability(precip_res, wind_res, pattern_res)

    return {
        "status": "ok",
        "day_analyzed": "tomorrow" if day_offset == 1 else "today",
        "temperature": temp_res,
        "precipitation": precip_res,
        "wind": wind_res,
        "humidity": humidity_res,
        "patterns": pattern_res,
        "6hour_blocks": blocks_res.get("blocks", []),
        "day_comparison": day_comp,
        "decision_support": {
            "umbrella": umbrella,
            "outdoor_activities": outdoor,
            "travel": travel,
        },
    }
