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

    async with httpx.AsyncClient() as client:
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
            "weather_code",
        ]),
        "timezone": "auto",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)

    response.raise_for_status()

    return response.json()

async def get_hourly_forecast(latitude: float, longitude: float):
    url= "https://api.open-meteo.com/v1/forecast"

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
        ]),
        "forcast_day":2,
        "timezone":"auto",
    }
    async with httpx.AsyncClient() as client:
        response=await client.get(url,params=params)

    response.raise_for_status()
    return response.json()

def format_hourly_forecast(weather_data: dict, current_time:str, hours:int=24):
    hourly= weather_data["hourly"]
    try:
        start_index = hourly["time"].index(current_time)
    except ValueError:
        start_index = 0

    end_index = start_index + hours

    forecast = []

    for i in range(
        start_index,
        min(end_index, len(hourly["time"]))
    ):
        weather_info = get_weather_description(hourly["weather_code"][i])
        forecast.append({
            "time": hourly["time"][i],
            "temperature": hourly["temperature_2m"][i],
            "humidity": hourly["relative_humidity_2m"][i],
            "precipitation_probability": hourly["precipitation_probability"][i],
            "precipitation": hourly["precipitation"][i],
            "wind_speed": hourly["wind_speed_10m"][i],
            "weather_code": hourly["weather_code"][i],
            "condition": weather_info["condition"],
            "icon": weather_info["icon"],})

    return forecast    
def format_current_weather(location: dict, weather_data: dict):

    current = weather_data["current"]

    weather_info = get_weather_description(current["weather_code"])

    return {
        "location": {
            "name": location["name"],
            "country": location["country"],
            "region": location["admin1"],
            "latitude": location["latitude"],
            "longitude": location["longitude"],
        },

        "current": {
            "time": current["time"],
            "temperature": current["temperature_2m"],
            "feels_like": current["apparent_temperature"],
            "humidity": current["relative_humidity_2m"],
            "wind_speed": current["wind_speed_10m"],
            "weather_code": current["weather_code"],
            "condition": weather_info["condition"],
            "icon": weather_info["icon"],}
    }