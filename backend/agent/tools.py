weather_tool = {
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": (
            "Get the current weather for a location "
            "using its latitude and longitude."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number",
                    "description": "Latitude of the location."
                },
                "longitude": {
                    "type": "number",
                    "description": "Longitude of the location."
                }
            },
            "required": ["latitude", "longitude"],
            "additionalProperties": False
        }
    }
}

location_tool = {
    "type": "function",
    "function": {
        "name": "geocode_location",
        "description": (
            "Converts a place name into geographic coordinates "
            "by finding its latitude and longitude."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The name of the place to look up, such as Dehradun."
                }
            },
            "required": ["location"],
            "additionalProperties": False
        }
    }
}

forecast_tool = {
    "type": "function",
    "function": {
        "name": "get_hourly_forecast",
        "description": (
            "Retrieves hourly weather forecast data "
            "using the latitude and longitude of a location."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number",
                    "description": "The latitude of the location."
                },
                "longitude": {
                    "type": "number",
                    "description": "The longitude of the location."
                }
            },
            "required": ["latitude", "longitude"],
            "additionalProperties": False
        }
    }
}


tools = [
    location_tool,
    weather_tool,
    forecast_tool
]