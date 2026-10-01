from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware

from weather.service import (
    geocode_location,
    get_current_weather,
    format_current_weather,
    get_hourly_forecast,
    format_hourly_forecast,
)
from weather.models import WeatherResponse


app = FastAPI(
    title="WeatherGPT API",
    description="Backend API for the WeatherGPT weather intelligence system.",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "WeatherGPT backend is alive 🌦️"
    }


@app.get("/weather", response_model=WeatherResponse)
async def weather(location: str):

    place = await geocode_location(location)

    if place is None:
        raise HTTPException(
            status_code=404,
            detail=f"Could not find location: {location}"
        )

    current_data = await get_current_weather(
        place["latitude"],
        place["longitude"],
    )

    forecast_data = await get_hourly_forecast(
        place["latitude"],
        place["longitude"],
    )

    formatted_current = format_current_weather(
        place,
        current_data,
    )

    formatted_forecast = format_hourly_forecast(
        forecast_data,
        current_data["current"]["time"],
    )

    return {
        "location": formatted_current["location"],
        "current": formatted_current["current"],
        "forecast": formatted_forecast,
    }

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "WeatherGPT backend"
    }