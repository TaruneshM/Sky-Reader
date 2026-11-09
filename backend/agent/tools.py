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

analysis_tool = {
    "type": "function",
    "function": {
        "name": "analyze_weather",
        "description": (
            "Performs in-depth meteorological analysis on temperature trends (rising/falling/min/max), "
            "precipitation accumulation vs probability, wind patterns, atmospheric stability, 6-hour "
            "aggregated time periods, and today-vs-tomorrow comparisons using forecast data."
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
                },
                "focus": {
                    "type": "string",
                    "enum": ["all", "temperature", "precipitation", "wind", "humidity", "patterns", "comparison"],
                    "description": "Specific analytical focus area: 'temperature', 'precipitation', 'wind', 'humidity', 'patterns', 'comparison', or 'all' (default)."
                },
                "day_offset": {
                    "type": "integer",
                    "description": "0 for today (current 24h), 1 for tomorrow (next 24h). Defaults to 1."
                }
            },
            "required": ["latitude", "longitude"],
            "additionalProperties": False
        }
    }
}

recommendations_tool = {
    "type": "function",
    "function": {
        "name": "get_weather_recommendations",
        "description": (
            "Generates evidence-based weather recommendations and decision support for a location: "
            "whether to carry an umbrella, best and worst time windows for outdoor activities, "
            "and travel suitability/hazards (fog, storms, high wind)."
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
                },
                "day_offset": {
                    "type": "integer",
                    "description": "0 for today, 1 for tomorrow. Defaults to 1."
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
    forecast_tool,
    analysis_tool,
    recommendations_tool,
]
