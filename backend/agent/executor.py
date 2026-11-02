try:
    from backend.weather.service import (geocode_location, get_current_weather, get_hourly_forecast)
except ImportError:
    from weather.service import (geocode_location, get_current_weather, get_hourly_forecast)

available_func={
    "geocode_location": geocode_location,
    "get_current_weather": get_current_weather,
    "get_hourly_forecast": get_hourly_forecast}


async def execute_tool(tool_name: str, arguments: dict):

    function = available_func.get(tool_name)

    if function is None:
        raise ValueError(f"Unknown tool: {tool_name}")

    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be a dictionary")

    result = await function(**arguments)

    return result