import asyncio
import time
import logging
from collections.abc import Callable
from contextvars import ContextVar
from json import JSONDecodeError
from math import asin, cos, radians, sin, sqrt
from typing import Dict, Any, Optional, Tuple
import httpx
from pydantic import ValidationError
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import re
import unicodedata
from .weather_codes import get_weather_description


from .location_models import (
    Ambiguous, CandidateSummary, ConfirmedLocation, LocationResolution,
    NotFound, ProviderUnavailable, Resolved, ResolutionProvenance,
)


logger = logging.getLogger(__name__)
weather_http_observer: ContextVar[Callable[[float], None] | None] = ContextVar(
    "weather_http_observer", default=None
)


# In-memory TTL Cache store
_GEOCODE_CACHE: Dict[str, Tuple[float, ConfirmedLocation]] = {}
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
                started = time.perf_counter()
                try:
                    response = await client.get(url, params=params)
                finally:
                    if observer := weather_http_observer.get():
                        observer((time.perf_counter() - started) * 1000)
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


def geocoding_log_label(location):
    """Log only short place-like strings, with credential-shaped spans redacted."""
    if not location or len(location) > 80 or re.search(r"[^\s,.'’\w-]|\S{28,}|[0-9]", location):
        return None
    return " ".join(location.split())


def _distance_km(anchor, destination):
    latitude, other_latitude = map(radians, (anchor["latitude"], destination["latitude"]))
    longitude_delta = radians(destination["longitude"] - anchor["longitude"])
    distance = sin((other_latitude - latitude) / 2) ** 2 + cos(latitude) * cos(other_latitude) * sin(longitude_delta / 2) ** 2
    return 12742 * asin(sqrt(min(1, distance)))


def _nearby_candidate(candidates, reference):
    country = reference.get("country_code")
    nearby = sorted(
        ((_distance_km(reference, candidate), candidate) for candidate in candidates
         if country and candidate.get("country_code") == country),
        key=lambda entry: entry[0],
    )
    if not nearby:
        return None
    distance, candidate = nearby[0]
    runner_up = nearby[1][0] if len(nearby) > 1 else float("inf")
    if distance <= 150 and runner_up >= max(2 * distance, distance + 50):
        logger.debug("Geocoding decision=nearby_same_country candidate_id=%s distance_km=%.0f "
                     "same_country_runner_up_km=%.0f", candidate.get("id") if isinstance(candidate.get("id"), int) else None, distance, runner_up)
        return candidate
    logger.debug("Geocoding decision=ambiguous_proximity nearest_km=%.0f same_country_runner_up_km=%.0f",
                 distance, runner_up)
    return None


def _rank_geocoding_candidates(name, qualifiers, results, reference=None, *, tied=None):
    candidates = {}
    for item in results:
        metadata = item.get("id") if isinstance(item.get("id"), int) else None
        latitude, longitude = item.get("latitude"), item.get("longitude")
        if not (isinstance(latitude, (int, float)) and -90 <= latitude <= 90
                and isinstance(longitude, (int, float)) and -180 <= longitude <= 180):
            logger.debug("Geocoding candidate=%r rejected=invalid_coordinates", metadata)
            continue
        name_match = _place_match(name, item.get("name"))
        if not name_match:
            logger.debug("Geocoding candidate=%r rejected=name_mismatch", metadata)
            continue

        labels = [item.get(key) for key in
                  ("admin1", "admin2", "admin3", "admin4", "country", "country_code")]
        if (_normalized_place_name(item.get("country_code")) == "us"
                or _normalized_place_name(item.get("country")) == "united states"):
            labels.extend(("USA", "U.S.A", "U.S.A.", "United States of America"))
        matches = [max(_place_match(qualifier, label) for label in labels) for qualifier in qualifiers]
        if not all(matches):
            logger.debug("Geocoding candidate=%r rejected=qualifier_mismatch", metadata)
            continue

        # Retain exact accents and qualifiers as stronger evidence than folded matches.
        rank = (sum(matches), name_match, bool((item.get("feature_code") or "").startswith("PPL")))
        logger.debug("Geocoding candidate=%r eligible_rank=%r", metadata, rank)
        coordinates = (latitude, longitude)
        existing = candidates.get(coordinates)
        entry = (rank, item)
        if existing is None or _candidate_sort_key(entry) > _candidate_sort_key(existing):
            candidates[coordinates] = entry

    ranked = sorted(candidates.values(), key=_candidate_sort_key, reverse=True)
    if not ranked:
        logger.debug("Geocoding decision=%s", "no_eligible_candidates" if results else "no_candidates")
        return None

    best_rank, best = ranked[0]
    peers = [item for rank, item in ranked[1:] if rank == best_rank]
    if not peers:
        logger.debug("Geocoding decision=unique_top_rank candidate_id=%s", best.get("id") if isinstance(best.get("id"), int) else None)
        return best

    population = _population(best)
    runner_up = max(map(_population, peers))
    # Comparable municipalities require clarification. An unknown population is not zero
    # evidence of a rival's size, so beating such a candidate requires a major admin seat.
    missing_population = any(not _population(item) for item in peers)
    if missing_population and not (_is_administrative_seat(best) and population >= 100_000):
        reason = "missing_population"
    elif population >= 3 * runner_up and population - runner_up >= 50_000:
        logger.debug("Geocoding decision=population_lead candidate_id=%s", best.get("id") if isinstance(best.get("id"), int) else None)
        return best
    else:
        reason = "insufficient_population_lead"
    logger.debug("Geocoding decision=ambiguous reason=%s top_population=%s runner_up_population=%s",
                 reason, population, runner_up)
    if reference and not qualifiers:
        nearby = _nearby_candidate([best, *peers], reference)
        if nearby:
            return nearby
    if tied is not None:
        tied.extend([best, *peers])
    return None



def _candidate_sort_key(entry):
    rank, item = entry
    # The metadata tie-breakers only pick a representation of the same coordinates.
    # Distinct, equally plausible locations still have to pass the confidence check.
    return (rank, _population(item), _is_administrative_seat(item),
            bool(item.get("timezone")),
            tuple(str(item.get(key) or "") for key in ("name", "country", "country_code", "admin1", "timezone")))


class InvalidGeocodingResponse(ValueError):
    pass


def _one_edit(left: str, right: str) -> bool:
    if min(len(left), len(right)) < 5 or left[:1] != right[:1] or abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right)) == 1
    short, long = sorted((left, right), key=len)
    return any(long[:index] + long[index + 1:] == short
               for index in range(1, len(long)))


def _validated_spelling(name, qualifiers, results):
    """Use one nearby spelling only among already-returned, explicitly qualified provider candidates."""
    if not qualifiers:
        return None
    possible = set()
    for item in results:
        candidate = _normalized_place_name(item.get("name"))
        if _one_edit(_accent_insensitive(name), _accent_insensitive(candidate)):
            possible.add((candidate, tuple(qualifiers)))
        elif _place_match(name, candidate):
            for index, qualifier in enumerate(qualifiers):
                for field in ("admin1", "admin2", "admin3", "admin4", "country"):
                    label = _normalized_place_name(item.get(field))
                    if _one_edit(_accent_insensitive(qualifier), _accent_insensitive(label)):
                        corrected = (*qualifiers[:index], label, *qualifiers[index + 1:])
                        possible.add((candidate, corrected))
    if len(possible) != 1:
        return None
    corrected_name, corrected_qualifiers = next(iter(possible))
    # The confirmed candidate must be unique after verifying the corrected spelling and qualifiers.
    candidates = {}
    for item in results:
        labels = tuple(item.get(field) for field in ("admin1", "admin2", "admin3", "admin4", "country", "country_code"))
        if _place_match(corrected_name, item.get("name")) and all(
            any(_place_match(qualifier, label) for label in labels) for qualifier in corrected_qualifiers
        ):
            lat, lon = item.get("latitude"), item.get("longitude")
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and -90 <= lat <= 90 and -180 <= lon <= 180:
                candidates[(lat, lon)] = item
    return next(iter(candidates.values())) if len(candidates) == 1 else None


async def _lookup_location(
    location: str, *, reference_location: Optional[str] = None, reference_place: Optional[dict] = None,
    allow_spelling_match: bool = False,
) -> LocationResolution:
    name, *qualifiers = [" ".join(part.split()) for part in location.split(",")]
    if not name or any(not qualifier for qualifier in qualifiers):
        return NotFound(query=location, reason="invalid_query")
    name = unicodedata.normalize("NFC", name)
    norm_key = ", ".join(map(_normalized_place_name, (name, *qualifiers)))
    now = time.time()
    cached = _GEOCODE_CACHE.get(norm_key)
    if cached and now - cached[0] < GEOCODE_TTL:
        logger.debug("Geocoding decision=cache_hit")
        return Resolved(query=location, location=cached[1].model_copy(update={"qualifiers": tuple(qualifiers)}))

    if _normalized_place_name(name) == "new york city":
        name = "New York"
    logger.debug("Geocoding has_reference=%s", bool(reference_place or reference_location))
    data = await _fetch_with_retry(
        "https://geocoding-api.open-meteo.com/v1/search",
        {"name": name, "count": 20, "language": "en", "format": "json"},
    )
    if not isinstance(data, dict) or (data.get("results") is not None and not isinstance(data["results"], list)):
        raise InvalidGeocodingResponse("Invalid geocoding provider response.")
    results = data.get("results") or []
    if any(not isinstance(item, dict) for item in results):
        raise InvalidGeocodingResponse("Invalid geocoding candidate response.")
    normalized = _normalized_place_name(name)
    normalized_qualifiers = list(map(_normalized_place_name, qualifiers))
    tied = []
    result = _rank_geocoding_candidates(normalized, normalized_qualifiers, results, tied=tied)
    spelling_match = False
    if result is None and not tied and allow_spelling_match:
        result = _validated_spelling(normalized, normalized_qualifiers, results)
        spelling_match = result is not None
    use_context = result is None and not qualifiers and (reference_place or reference_location) and any(
        _place_match(normalized, item.get("name")) for item in results
    ) and _normalized_place_name(reference_location) != normalized
    reference = None
    if use_context:
        reference = reference_place or await geocode_location(reference_location)
        if reference:
            result = _rank_geocoding_candidates(normalized, normalized_qualifiers, results, reference=reference)
        else:
            logger.debug("Geocoding decision=reference_unresolved")
    if result is None:
        if tied:
            return Ambiguous(query=location, candidates=tuple(
                CandidateSummary(provider_id=item.get("id"), name=item["name"],
                                 country=item.get("country"), region=item.get("admin1"), district=item.get("admin2"))
                for item in tied
            ), missing_qualifiers=("district or more specific locality",) if qualifiers else ("region", "country"))
        return NotFound(query=location, reason="no_matching_candidates" if results else "no_candidates")

    place = ConfirmedLocation(
        name=result["name"], latitude=result["latitude"], longitude=result["longitude"],
        country=result.get("country"), country_code=result.get("country_code"), region=result.get("admin1"),
        timezone=result.get("timezone"), provider_id=result.get("id"), qualifiers=tuple(qualifiers),
        provenance=ResolutionProvenance(
            method="geographic_hint" if use_context else "provider_spelling_match" if spelling_match else "standalone",
            reference_name=(reference.get("name") or reference_location or location) if use_context else None,
        ),
    )
    if not use_context and not spelling_match:
        _GEOCODE_CACHE[norm_key] = (now, place)
    return Resolved(query=location, location=place)


async def resolve_location(
    location: str, *, reference: ConfirmedLocation | None = None, reference_location: str | None = None,
) -> LocationResolution:
    """Typed resolver for trusted backend callers. Provider errors carry safe categories."""
    try:
        return await _lookup_location(location, reference_location=reference_location,
                                      reference_place=reference.as_legacy_place() if reference else None,
                                      allow_spelling_match=True)
    except httpx.TimeoutException:
        return ProviderUnavailable(query=location, reason="timeout", retriable=True)
    except httpx.HTTPStatusError as error:
        status = error.response.status_code
        return ProviderUnavailable(query=location, reason="provider_http_error", retriable=status == 429 or status >= 500)
    except httpx.RequestError:
        return ProviderUnavailable(query=location, reason="network_error", retriable=True)
    except (JSONDecodeError, InvalidGeocodingResponse, ValidationError):
        return ProviderUnavailable(query=location, reason="invalid_response", retriable=True)


async def geocode_location(
    location: str, *, reference_location: Optional[str] = None, reference_place: Optional[dict] = None
):
    """Legacy dictionary/None adapter. Provider exceptions still propagate to existing callers."""
    outcome = await _lookup_location(location, reference_location=reference_location, reference_place=reference_place)
    return outcome.location.as_legacy_place() if isinstance(outcome, Resolved) else None


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
    return summarize_scoped_forecast(scope_hourly_forecast(weather_data, period, current_time), period)


def summarize_scoped_forecast(scoped, period):
    hourly = scoped["hourly"]
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
