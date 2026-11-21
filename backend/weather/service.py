import asyncio
import time
from typing import Dict, Any, Optional, Tuple
import httpx
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import re
import unicodedata
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


def _normalized_place_name(value):
    return unicodedata.normalize("NFC", " ".join(str(value or "").split()).casefold())


def _accent_insensitive(value):
    return "".join(char for char in unicodedata.normalize("NFD", value)
                   if unicodedata.category(char) != "Mn")


def _place_match(requested, actual):
    actual = _normalized_place_name(actual)
    if requested == actual:
        return 2
    return int(_accent_insensitive(requested) == _accent_insensitive(actual))


def _population(candidate):
    population = candidate.get("population")
    return population if isinstance(population, int) and population > 0 else 0


def _is_administrative_seat(candidate):
    return candidate.get("feature_code") in {"PPLC", "PPLA", "PPLA2", "PPLA3", "PPLA4"}


def _rank_geocoding_candidates(name, qualifiers, results):
    candidates = {}
    for item in results:
        latitude, longitude = item.get("latitude"), item.get("longitude")
        if not (isinstance(latitude, (int, float)) and -90 <= latitude <= 90
                and isinstance(longitude, (int, float)) and -180 <= longitude <= 180):
            continue
        name_match = _place_match(name, item.get("name"))
        if not name_match:
            continue

        labels = [item.get(key) for key in
                  ("admin1", "admin2", "admin3", "admin4", "country", "country_code")]
        if (_normalized_place_name(item.get("country_code")) == "us"
                or _normalized_place_name(item.get("country")) == "united states"):
            labels.extend(("USA", "U.S.A", "U.S.A.", "United States of America"))
        matches = [max(_place_match(qualifier, label) for label in labels) for qualifier in qualifiers]
        if not all(matches):
            continue

        # Retain exact accents and qualifiers as stronger evidence than folded matches.
        rank = (sum(matches), name_match, bool((item.get("feature_code") or "").startswith("PPL")))
        coordinates = (latitude, longitude)
        existing = candidates.get(coordinates)
        entry = (rank, item)
        if existing is None or _candidate_sort_key(entry) > _candidate_sort_key(existing):
            candidates[coordinates] = entry

    ranked = sorted(candidates.values(), key=_candidate_sort_key, reverse=True)
    if not ranked:
        return None

    best_rank, best = ranked[0]
    peers = [item for rank, item in ranked[1:] if rank == best_rank]
    if not peers:
        return best

    population = _population(best)
    runner_up = max(map(_population, peers))
    # Comparable municipalities require clarification. An unknown population is not zero
    # evidence of a rival's size, so beating such a candidate requires a major admin seat.
    if any(not _population(item) for item in peers) and not (
        _is_administrative_seat(best) and population >= 100_000
    ):
        return None
    if population >= 3 * runner_up and population - runner_up >= 50_000:
        return best
    return None


def _candidate_sort_key(entry):
    rank, item = entry
    # The metadata tie-breakers only pick a representation of the same coordinates.
    # Distinct, equally plausible locations still have to pass the confidence check.
    return (rank, _population(item), _is_administrative_seat(item),
            bool(item.get("timezone")),
            tuple(str(item.get(key) or "") for key in ("name", "country", "country_code", "admin1", "timezone")))


async def geocode_location(location: str):
    name, *qualifiers = [" ".join(part.split()) for part in location.split(",")]
    if not name or any(not qualifier for qualifier in qualifiers):
        return None
    name = unicodedata.normalize("NFC", name)
    norm_key = ", ".join(map(_normalized_place_name, (name, *qualifiers)))
    now = time.time()
    cached = _GEOCODE_CACHE.get(norm_key)
    if cached and now - cached[0] < GEOCODE_TTL:
        return cached[1]

    if _normalized_place_name(name) == "new york city":
        name = "New York"
    data = await _fetch_with_retry(
        "https://geocoding-api.open-meteo.com/v1/search",
        {"name": name, "count": 20, "language": "en", "format": "json"},
    )
    result = _rank_geocoding_candidates(
        _normalized_place_name(name), list(map(_normalized_place_name, qualifiers)), data.get("results") or []
    )
    if result is None:
        return None

    geo_data = {key: result.get(key) for key in
                ("name", "latitude", "longitude", "country", "country_code", "admin1", "timezone")}
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
            "wind_gusts_10m",
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
            "apparent_temperature",
            "relative_humidity_2m",
            "precipitation_probability",
            "precipitation",
            "weather_code",
            "wind_speed_10m",
            "wind_gusts_10m",
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

    indices = forecast_indices(weather_data, f"next_{hours}h", current_time, allow_partial=True)
    forecast = []

    rel_hums = hourly.get("relative_humidity_2m") or [0] * len(times)
    wind_directions = hourly.get("wind_direction_10m") or [None] * len(times)
    pressures = hourly.get("surface_pressure") or [None] * len(times)
    cloud_covers = hourly.get("cloud_cover") or [None] * len(times)

    for i in indices:
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


def forecast_indices(weather_data, period, current_time=None, *, allow_partial=False):
    """Select a continuous window using the forecast location's local clock."""
    times = weather_data.get("hourly", {}).get("time", [])
    if not times:
        return []
    try:
        timezone_name = weather_data.get("timezone")
        zone = ZoneInfo(timezone_name) if timezone_name else None
        timestamp = current_time or weather_data.get("current", {}).get("time")
        if timestamp:
            local = datetime.fromisoformat(timestamp)
            if local.tzinfo:
                if zone is None:
                    return []
                local = local.astimezone(zone).replace(tzinfo=None)
        elif zone:
            local = datetime.now(zone).replace(tzinfo=None)
        else:
            return []
        hour = local.replace(minute=0, second=0, microsecond=0)
        midnight = hour.replace(hour=0)
        if period == "current" or re.fullmatch(r"next_\d+h", period):
            count = 24 if period == "current" else int(period[5:-1])
            if not 0 < count <= 48:
                return []
            start, end = hour, hour + timedelta(hours=count)
        else:
            base, separator, specific = period.partition("@")
            base, _, span = base.partition("_")
            if base in {"today", "tonight"}:
                day = midnight
            elif base == "tomorrow":
                day = midnight + timedelta(days=1)
            else:
                day = datetime.strptime(base, "%Y-%m-%d")
            start, end = day, day + timedelta(days=1)
            ranges = {"morning": (6, 12), "afternoon": (12, 18), "evening": (18, 24)}
            if span in ranges:
                first, last = ranges[span]
                start, end = day + timedelta(hours=first), day + timedelta(hours=last)
            elif separator:
                start_clock, _, end_clock = specific.partition("-")
                clock = datetime.strptime(start_clock, "%H:%M")
                start = day.replace(hour=clock.hour)
                if end_clock:
                    clock = datetime.strptime(end_clock, "%H:%M")
                    end = day.replace(hour=clock.hour) + timedelta(hours=bool(clock.minute))
                    if end <= start:
                        return []
                else:
                    end = start + timedelta(hours=1)
            if base == "tonight":
                start = max(start, day + timedelta(hours=18))
            start = max(start, hour)
        if start >= end:
            return []
        lookup = {value: index for index, value in enumerate(times)}
        indices = []
        while start < end:
            index = lookup.get(start.isoformat(timespec="minutes"))
            if index is None:
                return indices if allow_partial else []
            indices.append(index)
            start += timedelta(hours=1)
        return indices
    except (ValueError, TypeError, ZoneInfoNotFoundError):
        return []


def scope_hourly_forecast(weather_data, period, current_time=None):
    hourly = weather_data.get("hourly", {})
    indices = forecast_indices(weather_data, period, current_time)
    return {**weather_data, "hourly": {
        key: [values[index] if index < len(values) else None for index in indices]
        for key, values in hourly.items() if isinstance(values, list)
    }}


def get_temporal_forecast_slice(weather_data, period="current", current_time=None):
    hourly = scope_hourly_forecast(weather_data, period, current_time)["hourly"]
    fields = {
        "times": "time", "temperatures": "temperature_2m", "apparent_temperatures": "apparent_temperature",
        "rain_probabilities": "precipitation_probability", "rain_amounts": "precipitation",
        "wind_speeds": "wind_speed_10m", "gusts": "wind_gusts_10m", "humidities": "relative_humidity_2m",
    }
    return {"period": period, "available": bool(hourly.get("time")),
            **{name: hourly.get(key, []) for name, key in fields.items()}}


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
