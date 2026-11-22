"""Fixed synthetic requests. Expectations concern evidence and behavior, never values."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Case:
    name: str
    message: str
    places: tuple[str, ...]
    measurements: tuple[str, ...]
    period: str
    max_groq: int = 0
    follow_up: bool = False
    unsupported: bool = False


CASES = (
    Case("current", "What's the weather in Tokyo, Japan right now?", ("Tokyo",),
         ("temperature", "weather_condition"), "current"),
    Case("tomorrow", "Tomorrow's weather in Lisbon, Portugal?", ("Lisbon",),
         ("temperature", "precipitation_probability", "wind_speed"), "tomorrow"),
    Case("umbrella", "Will it rain in Singapore tonight, and should I bring an umbrella?",
         ("Singapore",), ("precipitation_probability",), "tonight"),
    Case("safety", "Is it safe to walk outdoors in Mumbai, India tomorrow?", ("Mumbai",),
         ("travel_suitability",), "tomorrow"),
    Case("comparison", "Compare Paris, France and Berlin, Germany tomorrow.", ("Paris", "Berlin"),
         ("temperature", "precipitation_probability", "wind_speed"), "tomorrow"),
    Case("follow_up", "How windy will it be there tomorrow?", ("Tokyo",),
         ("wind_speed",), "tomorrow", follow_up=True),
    Case("synthesis", "Explain the wind forecast in Lisbon, Portugal tomorrow in detail.",
         ("Lisbon",), ("wind_speed",), "tomorrow", max_groq=2),
    Case("unsupported", "What is the temperature in Tokyo, Japan next month?", ("Tokyo",),
         (), "next month", unsupported=True),
)
