import httpx
from datetime import datetime
from .weather_codes import get_weather_description


async def geocode_location(location: str):
    url = "https://geocoding-api.open-meteo.com/v1/search"

    params = {
        "name": location,
        "count": 1,
        "language": "en",
        "format": "json",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, params=params)

    response.raise_for_status()
    data = response.json()

    if "results" not in data or not data["results"]:
        return None

    result = data["results"][0]

    return {
        "name": result["name"],
        "latitude": result["latitude"],
        "longitude": result["longitude"],
        "country": result.get("country"),
        "admin1": result.get("admin1"),
    }


async def get_current_weather(latitude: float, longitude: float):
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

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, params=params)

    response.raise_for_status()
    return response.json()


async def get_hourly_forecast(latitude: float, longitude: float):
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
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, params=params)

    response.raise_for_status()
    return response.json()


async def get_daily_forecast(latitude: float, longitude: float, days: int = 3):
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
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, params=params)

    response.raise_for_status()
    return response.json()


def format_hourly_forecast(weather_data: dict, current_time: str, hours: int = 24):
    hourly = weather_data.get("hourly", {})
    times = hourly.get("time", [])

    try:
        start_index = times.index(current_time)
    except (ValueError, AttributeError):
        start_index = 0

    end_index = start_index + hours
    forecast = []

    wind_directions = hourly.get("wind_direction_10m") or [None] * len(times)
    pressures = hourly.get("surface_pressure") or [None] * len(times)
    cloud_covers = hourly.get("cloud_cover") or [None] * len(times)

    for i in range(start_index, min(end_index, len(times))):
        w_code = hourly.get("weather_code", [0])[i] if i < len(hourly.get("weather_code", [])) else 0
        weather_info = get_weather_description(w_code)

        forecast.append({
            "time": times[i],
            "temperature": hourly.get("temperature_2m", [0])[i],
            "humidity": hourly.get("relative_humidity_2m", [0])[i],
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
