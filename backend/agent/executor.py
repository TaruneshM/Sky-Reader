try:
    from backend.weather.service import (
        geocode_location,
        get_current_weather,
        get_hourly_forecast,
        get_daily_forecast,
    )
    from backend.weather.analysis import (
        analyze_weather_data,
        get_weather_decision_support,
    )
except ImportError:
    from weather.service import (
        geocode_location,
        get_current_weather,
        get_hourly_forecast,
        get_daily_forecast,
    )
    from weather.analysis import (
        analyze_weather_data,
        get_weather_decision_support,
    )


async def analyze_weather(latitude: float, longitude: float, focus: str = "all", day_offset: int = 1):
    """Fetches hourly forecast and runs Python meteorological analysis engine."""
    forecast_data = await get_hourly_forecast(latitude, longitude)
    return analyze_weather_data(forecast_data, focus=focus, day_offset=day_offset)


async def get_weather_recommendations(latitude: float, longitude: float, day_offset: int = 1):
    """Fetches hourly forecast and generates decision support (umbrella, outdoor, travel)."""
    forecast_data = await get_hourly_forecast(latitude, longitude)
    return get_weather_decision_support(forecast_data, day_offset=day_offset)


available_func = {
    "geocode_location": geocode_location,
    "get_current_weather": get_current_weather,
    "get_hourly_forecast": get_hourly_forecast,
    "get_daily_forecast": get_daily_forecast,
    "analyze_weather": analyze_weather,
    "get_weather_recommendations": get_weather_recommendations,
}


async def execute_tool(tool_name: str, arguments: dict):
    function = available_func.get(tool_name)

    if function is None:
        raise ValueError(f"Unknown tool: {tool_name}")

    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be a dictionary")

    result = await function(**arguments)
    return result
