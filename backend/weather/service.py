import asyncio
import time
from typing import Dict, Any, Optional, Tuple
import httpx
from datetime import datetime
from .weather_codes import get_weather_description


# In-memory TTL Cache store
_GEOCODE_CACHE: Dict[str, Tuple[float, Any]] = {}
_CURRENT_WEATHER_CACHE: Dict[Tuple[float, float], Tuple[float, Any]] = {}
_HOURLY_CACHE: Dict[Tuple[float, float], Tuple[float, Any]] = {}
_DAILY_CACHE: Dict[Tuple[float, float, int], Tuple[float, Any]] = {}

GEOCODE_TTL = 3600.0        # 1 hour
CURRENT_WEATHER_TTL = 300.0  # 5 minutes
HOURLY_TTL = 600.0          # 10 minutes
DAILY_TTL = 900.0           # 15 minutes


def clear_weather_cache():
    """Clear all in-memory weather and geocoding caches (useful for testing)."""
    _GEOCODE_CACHE.clear()
    _CURRENT_WEATHER_CACHE.clear()
    _HOURLY_CACHE.clear()
    _DAILY_CACHE.clear()


async def _fetch_with_retry(url: str, params: dict, retries: int = 2) -> dict:
    """Helper to fetch from Open-Meteo with retry on transient network timeouts."""
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError):
            if attempt == retries - 1:
                raise
            await asyncio.sleep(1.0)


async def geocode_location(location: str):
    norm_key = location.strip().lower()
    now = time.time()
    if norm_key in _GEOCODE_CACHE:
        ts, cached_val = _GEOCODE_CACHE[norm_key]
        if now - ts < GEOCODE_TTL:
            return cached_val

    url = "https://geocoding-api.open-meteo.com/v1/search"

    params = {
        "name": location,
        "count": 1,
        "language": "en",
        "format": "json",
    }

    data = await _fetch_with_retry(url, params)

    if "results" not in data or not data["results"]:
        _GEOCODE_CACHE[norm_key] = (now, None)
        return None

    result = data["results"][0]

    geo_data = {
        "name": result["name"],
        "latitude": result["latitude"],
        "longitude": result["longitude"],
        "country": result.get("country"),
        "admin1": result.get("admin1"),
    }
    _GEOCODE_CACHE[norm_key] = (now, geo_data)
    return geo_data


async def get_current_weather(latitude: float, longitude: float):
    cache_key = (round(float(latitude), 3), round(float(longitude), 3))
    now = time.time()
    if cache_key in _CURRENT_WEATHER_CACHE:
        ts, cached_val = _CURRENT_WEATHER_CACHE[cache_key]
        if now - ts < CURRENT_WEATHER_TTL:
            return cached_val

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "wind_speed_10m",
            "wind_direction_10m",
            "surface_pressure",
            "cloud_cover",
            "weather_code",
        ]),
        "timezone": "auto",
    }

    res = await _fetch_with_retry(url, params)
    _CURRENT_WEATHER_CACHE[cache_key] = (now, res)
    return res


async def get_hourly_forecast(latitude: float, longitude: float):
    cache_key = (round(float(latitude), 3), round(float(longitude), 3))
    now = time.time()
    if cache_key in _HOURLY_CACHE:
        ts, cached_val = _HOURLY_CACHE[cache_key]
        if now - ts < HOURLY_TTL:
            return cached_val

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation_probability",
            "precipitation",
            "weather_code",
            "wind_speed_10m",
            "wind_direction_10m",
            "surface_pressure",
            "cloud_cover",
        ]),
        "forecast_days": 2,
        "timezone": "auto",
    }
    res = await _fetch_with_retry(url, params)
    _HOURLY_CACHE[cache_key] = (now, res)
    return res


async def get_daily_forecast(latitude: float, longitude: float, days: int = 3):
    cache_key = (round(float(latitude), 3), round(float(longitude), 3), days)
    now = time.time()
    if cache_key in _DAILY_CACHE:
        ts, cached_val = _DAILY_CACHE[cache_key]
        if now - ts < DAILY_TTL:
            return cached_val

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ",".join([
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "precipitation_probability_max",
            "wind_speed_10m_max",
            "weather_code",
        ]),
        "forecast_days": max(1, min(days, 7)),
        "timezone": "auto",
    }
    return await _fetch_with_retry(url, params)


def format_hourly_forecast(weather_data: dict, current_time: str, hours: int = 24):
    hourly = weather_data.get("hourly", {})
    times = hourly.get("time", [])

    start_index = 0
    if current_time and times:
        # Match exact ISO or prefix up to hour (e.g. '2026-11-21T16')
        prefix = current_time[:13]
        matched = False
        for idx, t in enumerate(times):
            if t.startswith(prefix):
                start_index = idx
                matched = True
                break
        if not matched:
            # Fall back to the first hour greater than or equal to current_time
            for idx, t in enumerate(times):
                if t >= current_time:
                    start_index = idx
                    matched = True
                    break

    end_index = start_index + hours
    forecast = []

    rel_hums = hourly.get("relative_humidity_2m") or [0] * len(times)
    wind_directions = hourly.get("wind_direction_10m") or [None] * len(times)
    pressures = hourly.get("surface_pressure") or [None] * len(times)
    cloud_covers = hourly.get("cloud_cover") or [None] * len(times)

    for i in range(start_index, min(end_index, len(times))):
        w_code = hourly.get("weather_code", [0])[i] if i < len(hourly.get("weather_code", [])) else 0
        weather_info = get_weather_description(w_code)

        forecast.append({
            "time": times[i],
            "temperature": hourly.get("temperature_2m", [0])[i],
            "humidity": rel_hums[i] if i < len(rel_hums) else 0,
            "precipitation_probability": hourly.get("precipitation_probability", [0])[i],
            "precipitation": hourly.get("precipitation", [0])[i],
            "wind_speed": hourly.get("wind_speed_10m", [0])[i],
            "weather_code": w_code,
            "condition": weather_info["condition"],
            "icon": weather_info["icon"],
            "wind_direction": wind_directions[i] if i < len(wind_directions) else None,
            "pressure": pressures[i] if i < len(pressures) else None,
            "cloud_cover": cloud_covers[i] if i < len(cloud_covers) else None,
        })

    return forecast


def get_temporal_forecast_slice(
    weather_data: dict,
    period: str = "current",
    current_time: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extracts a temporal slice from Open-Meteo hourly data aligned to the target period:
    - 'current' / 'today_remaining': from current hour to end of today or next 24h
    - 'tonight': 18:00 to 23:00 of the current day
    - 'tomorrow': 00:00 to 23:00 of the next calendar day (day_offset=1)
    - 'all_48h': complete 48h dataset
    """
    hourly = weather_data.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        return {"times": [], "temperatures": [], "rain_probabilities": [], "rain_amounts": [], "wind_speeds": []}

    curr_iso = current_time or weather_data.get("current", {}).get("time", "")
    curr_date = curr_iso[:10] if curr_iso else times[0][:10]

    # Find starting index of current hour
    curr_hour_idx = 0
    if curr_iso:
        prefix = curr_iso[:13]
        for idx, t in enumerate(times):
            if t.startswith(prefix) or t >= curr_iso:
                curr_hour_idx = idx
                break

    if period == "tonight":
        # Match today's 18:00 to 23:00
        indices = [
            i for i, t in enumerate(times)
            if t.startswith(curr_date) and 18 <= int(t[11:13]) <= 23
        ]
        if not indices:
            # If current hour is past 23:00, use next 4 hours
            indices = list(range(curr_hour_idx, min(curr_hour_idx + 5, len(times))))
    elif period == "tomorrow":
        # All hours where date > curr_date or hours 24-47
        indices = [i for i, t in enumerate(times) if not t.startswith(curr_date)]
        if not indices:
            indices = list(range(min(24, len(times)), min(48, len(times))))
    elif period == "today":
        # All remaining hours of today
        indices = [i for i, t in enumerate(times) if t.startswith(curr_date) and i >= curr_hour_idx]
        if not indices:
            indices = list(range(curr_hour_idx, min(curr_hour_idx + 12, len(times))))
    else:
        # Default: next 24 hours starting from current hour
        indices = list(range(curr_hour_idx, min(curr_hour_idx + 24, len(times))))

    temps = hourly.get("temperature_2m", [])
    rain_probs = hourly.get("precipitation_probability", [])
    rain_amounts = hourly.get("precipitation", [])
    winds = hourly.get("wind_speed_10m", [])

    return {
        "period": period,
        "times": [times[i] for i in indices if i < len(times)],
        "temperatures": [temps[i] for i in indices if i < len(temps)],
        "rain_probabilities": [rain_probs[i] for i in indices if i < len(rain_probs)],
        "rain_amounts": [rain_amounts[i] for i in indices if i < len(rain_amounts)],
        "wind_speeds": [winds[i] for i in indices if i < len(winds)],
    }


def format_current_weather(location: dict, weather_data: dict):
    current = weather_data.get("current", {})
    weather_info = get_weather_description(current.get("weather_code", 0))

    return {
        "location": {
            "name": location.get("name", "Unknown"),
            "country": location.get("country"),
            "region": location.get("admin1"),
            "latitude": location.get("latitude", 0.0),
            "longitude": location.get("longitude", 0.0),
        },
        "current": {
            "time": current.get("time", ""),
            "temperature": current.get("temperature_2m", 0.0),
            "feels_like": current.get("apparent_temperature", current.get("temperature_2m", 0.0)),
            "humidity": current.get("relative_humidity_2m", 0.0),
            "wind_speed": current.get("wind_speed_10m", 0.0),
            "weather_code": current.get("weather_code", 0),
            "condition": weather_info["condition"],
            "icon": weather_info["icon"],
            "wind_direction": current.get("wind_direction_10m"),
            "pressure": current.get("surface_pressure"),
            "cloud_cover": current.get("cloud_cover"),
        }
    }
