import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, Optional


INTENT_PATTERNS = [
    ("coat_clothing", [
        r"\b(carry|wear|need|take)\b.*\b(coat|jacket|sweater|hoodie|clothing|clothes|layers)\b",
        r"\b(should i|do i need to)\b.*\b(coat|jacket|sweater)\b",
        r"\bthand hai kya\b",
        r"\bis it cold\b",
    ]),
    ("umbrella", [
        r"\b(carry|take|need|bring)\b.*\bumbrella\b",
        r"\bdo i need an? umbrella\b",
        r"\bumbrella needed\b",
    ]),
    ("rain_check", [
        r"\b(will it|is it going to|chance of|any)\b.*\brain\b",
        r"\bbarish hogi kya\b",
        r"\bexpecting rain\b",
        r"\brain today\b",
        r"\brain tomorrow\b",
    ]),
    ("morning_walk", [
        r"\b(morning walk|evening walk|go for a walk|stroll|jogging|run|outdoor)\b",
        r"\bcan i go for a walk\b",
    ]),
    ("wind_humidity", [
        r"\b(humidity|wind speed|windy|wind gusts?)\b",
    ]),
    ("tomorrow_forecast", [
        r"\bwhat about tomorrow\b",
        r"\bhow about tomorrow\b",
        r"\btomorrow('s)? weather\b",
        r"\bforecast for tomorrow\b",
    ]),
    ("current_weather", [
        r"\bhow('s| is) the weather\b",
        r"\bwhat('s| is) the weather\b",
        r"\bcurrent weather\b",
        r"\bweather in\b",
        r"\btemperature in\b",
        r"\bhow hot\b",
        r"\bhow cold\b",
    ]),
]

KNOWN_INDIAN_AND_GLOBAL_CITIES = [
    "tanakpur", "dehradun", "delhi", "new delhi", "mumbai", "bangalore", "bengaluru",
    "kolkata", "chennai", "hyderabad", "pune", "jaipur", "lucknow", "chandigarh",
    "shimla", "manali", "nainital", "rishikesh", "haridwar", "haldwani", "london",
    "paris", "tokyo", "são paulo", "new york", "san francisco", "berlin", "dubai", "singapore"
]


@dataclass(frozen=True)
class WeatherRequest:
    intent: Optional[str]
    period: str
    location: Optional[str]
    safety: bool
    activity: Optional[str]


def detect_weather_intent(query: str) -> Optional[str]:
    clean = query.casefold()
    if re.search(r"\b(safe|safety|severe|warnings?|danger(?:ous)?|hazards?|hazardous|storms?|thunderstorms?)\b", clean):
        return "weather_risks"
    if re.search(r"\b(compare|versus|vs|which city|difference between|comprehensive|in detail)\b", clean):
        return None
    for intent, patterns in INTENT_PATTERNS:
        if any(re.search(pattern, clean) for pattern in patterns):
            return intent
    if re.search(r"\b(weather|forecast|temperature)\b", clean):
        return "current_weather"
    return None


def explicit_location(query: str) -> Optional[str]:
    query = unicodedata.normalize("NFC", query)
    # A qualifier belongs to the candidate, including region and country after commas.
    matches = re.finditer(r"(?=\b(?:in|at|near|around|for)\s+([^?!;]+))", query, re.I)
    for match in matches:
        candidate = re.split(
            r"\s+\b(?:please|right now|now|currently|today|tonight|tomorrow|yesterday|"
            r"this|next|at|from|between|during|with|if|on|after|before|will|would|be)\b",
            match[1], maxsplit=1, flags=re.I,
        )[0].strip(" .,")
        if re.match(r"(?:today|tomorrow|tonight|now|right now|the next)\b", candidate, re.I):
            continue
        if re.fullmatch(r"[^\W\d_][^?!;:]*", candidate) and not re.fullmatch(
            r"(?:the\s+)?(?:a\s+)?(?:tomorrow|today|tonight|now|right now|morning|afternoon|evening|"
            r"night|detail|a walk|walk|hike|outside|this weekend|my area|next week)", candidate, re.I
        ):
            return candidate
    direct = re.fullmatch(r"(?:weather|forecast|temperature|what about|how about)\s+([^?!;]+)",
                          query.strip(" .?!"), re.I)
    if direct and not re.match(r"(?:please|now|today|tonight|tomorrow|this|next|right)\b", direct[1], re.I):
        return re.split(r"\s+\b(?:today|tonight|tomorrow|please|right now|now|at)\b",
                        direct[1], maxsplit=1, flags=re.I)[0].strip()
    for city in sorted(KNOWN_INDIAN_AND_GLOBAL_CITIES + ["new york city"], key=len, reverse=True):
        match = re.search(r"\b" + re.escape(city) + r"\b(?:,\s*[^?!;]+)?", query, re.I)
        if match:
            return match[0].rstrip(".")
    return None


def extract_location_from_query_or_history(query, conversation_history=None) -> Optional[str]:
    if location := explicit_location(query):
        return location
    for message in reversed(conversation_history or []):
        if message.get("role") != "user":
            continue
        content = message.get("content", "")
        if re.search(r"\b(compare|versus|vs|which city|difference between)\b", content, re.I):
            return None
        if (detect_weather_intent(content) or re.search(
            r"\b(weather|forecast|temperature|rain|wind|humidity|(?:what|how) about)\b", content, re.I
        )) and (location := explicit_location(content)):
            return location
    return None


def parse_weather_request(query: str, history=None) -> WeatherRequest:
    clean = query.casefold()
    intent = detect_weather_intent(query)
    activity_match = re.search(r"\b(driv\w*|travel\w*|hik\w*|walk\w*|jog\w*|cycling|outside|outdoor\w*)\b", clean)
    activity = activity_match[0] if activity_match else None
    if not intent and re.match(r"\s*(?:what|how) about\b", clean) and explicit_location(query):
        prior = next((detect_weather_intent(message.get("content", ""))
                      for message in reversed(history or []) if message.get("role") == "user"), None)
        intent = prior or "current_weather"
    date_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", clean)
    relative = re.search(r"\bnext (\d+) hours?\b", clean)
    unsupported = re.search(r"\b(yesterday|day after tomorrow|weekend|next week|next month|"
                            r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", clean)
    if date_match:
        period = date_match[0]
    elif relative:
        period = f"next_{relative[1]}h"
    elif unsupported:
        period = unsupported[0]
    else:
        period = next((word for word in ("tomorrow", "tonight", "today") if re.search(rf"\b{word}\b", clean)), "current")
    if period in {"current", "today", "tomorrow", "tonight"} or date_match:
        base = "today" if period == "current" else period
        span = re.search(r"\b(morning|afternoon|evening)\b", clean)
        clock = re.search(r"\b(?:at|from|between)\s+(\d{1,2})(?::(\d{2}))?(?:\s*(am|pm))?"
                          r"(?:\s+(?:to|and|until)\s+(\d{1,2})(?::(\d{2}))?(?:\s*(am|pm))?)?\b", clean)
        if clock:
            def clock_time(number, minutes, meridiem):
                hour = int(number)
                if meridiem and 1 <= hour <= 12:
                    hour = hour % 12 + (12 if meridiem == "pm" else 0)
                return f"{hour:02d}:{int(minutes or 0):02d}"

            start = clock_time(clock[1], clock[2], clock[3] or clock[6])
            end = clock_time(clock[4], clock[5], clock[6]) if clock[4] else None
            period = f"{base}@{start}" + (f"-{end}" if end else "")
        elif span:
            period = f"{base}_{span[0]}"
    return WeatherRequest(intent, period, extract_location_from_query_or_history(query, history),
                          intent == "weather_risks", activity)


def describe_period(period):
    if match := re.fullmatch(r"next_(\d+)h", period):
        hours = int(match[1])
        return f"the next {hours} hour{'s' if hours != 1 else ''}"
    return period.replace("_", " ").replace("@", " at ")


def weather_facts(intent, current_data=None, hourly_slice=None, risk_data=None):
    current = (current_data or {}).get("current", {})
    series = hourly_slice or {}
    facts = {}
    fields = {
        "temperature_2m": ("temperatures", "temperature"),
        "apparent_temperature": ("apparent_temperatures", "feels like"),
        "relative_humidity_2m": ("humidities", "humidity"),
        "wind_speed_10m": ("wind_speeds", "wind speed"),
        "wind_gusts_10m": ("gusts", "wind gusts"),
        "precipitation_probability": ("rain_probabilities", "rain probability"),
        "precipitation": ("rain_amounts", "rainfall"),
    }
    selected = {
        "temperature": ("temperature_2m", "apparent_temperature"),
        "coat_clothing": ("temperature_2m", "apparent_temperature"),
        "umbrella": ("precipitation_probability", "precipitation"),
        "rain_check": ("precipitation_probability", "precipitation"),
        "morning_walk": ("temperature_2m", "wind_speed_10m", "wind_gusts_10m", "precipitation_probability"),
        "wind_humidity": ("wind_speed_10m", "wind_gusts_10m", "relative_humidity_2m"),
        "tomorrow_forecast": ("temperature_2m", "precipitation_probability", "wind_speed_10m"),
    }.get(intent, tuple(fields))
    for field in selected:
        key, label = fields[field]
        if hourly_slice is not None:
            values = series.get(key, [])
            if values and all(isinstance(value, (int, float)) for value in values):
                facts[label] = (min(values), max(values))
        elif isinstance(current.get(field), (int, float)):
            facts[label] = (current[field], current[field])
    if risk_data:
        facts["risk assessment"] = risk_data
    return facts


def synthesize_deterministic_weather_buddy_response(
    intent: str,
    location_name: str,
    current_data: Optional[Dict[str, Any]] = None,
    hourly_slice: Optional[Dict[str, Any]] = None,
    risk_data: Optional[Dict[str, Any]] = None,
    recommendations_data: Optional[Dict[str, Any]] = None,
    period: Optional[str] = None,
    activity: Optional[str] = None,
) -> str:
    scope = f"in {location_name}" + (f" for {period}" if period else "")
    if intent == "weather_risks":
        level = (risk_data or {}).get("overall_risk_level")
        if not level:
            return f"I don’t have enough forecast evidence to assess weather hazards {scope}."
        risks = risk_data.get("detected_risks", [])
        hazards = "; ".join(risk["condition"] for risk in risks if risk.get("condition"))
        advice = " ".join(risk_data.get("safety_recommendations", []))
        limitation = " Forecast data is incomplete." if risk_data.get("data_limitations") else ""
        action = f" for {activity}" if activity else ""
        return (f"The modeled weather risk {scope} is {level}."
                + (f" Detected hazards: {hazards}." if hazards else "")
                + (f" {advice}" if advice else "")
                + f"{limitation} This assessment cannot establish safety{action}. Check local alerts and conditions.")

    facts = weather_facts(intent, current_data, hourly_slice)
    if not facts:
        return f"I don’t have enough weather data to answer that {scope}."
    units = {"temperature": " °C", "feels like": " °C", "humidity": "%",
             "wind speed": " km/h", "wind gusts": " km/h", "rain probability": "%", "rainfall": " mm"}
    statements = []
    for label, (low, high) in facts.items():
        unit = units[label]
        if label in {"rain probability", "rainfall", "wind gusts"} and hourly_slice is not None:
            statements.append(f"peak {label} {high:g}{unit}")
        elif low != high:
            statements.append(f"{label} {low:g}{unit} to {high:g}{unit}")
        else:
            statements.append(f"{label} {high:g}{unit}")
    summary = f"Weather {scope}: " + ", ".join(statements) + "."
    rain = facts.get("rain probability")
    if intent in {"rain_check", "umbrella"} and rain is None:
        summary += " Rain probability is unavailable for that window."
    rainfall = facts.get("rainfall")
    if intent == "umbrella" and ((rain and rain[1] >= 30) or (rainfall and rainfall[1] > 0)):
        return f"Consider carrying an umbrella {scope}. {summary}"
    if intent == "umbrella" and rain and rain[1] == 0 and (not rainfall or rainfall[1] == 0):
        return f"No umbrella needed in {location_name} based on the available rain forecast. {summary}"
    if intent == "rain_check" and rain and rain[1] == 0 and (not rainfall or rainfall[1] == 0):
        return f"The available forecast shows virtually no chance of rain {scope}. {summary}"
    temperature = facts.get("feels like") or facts.get("temperature")
    if intent == "coat_clothing" and temperature:
        if temperature[0] < 15:
            return f"Consider a jacket {scope}. {summary}"
        return f"A heavy jacket is unlikely to be needed based on the temperatures. {summary}"
    if intent == "morning_walk":
        return f"For your walk, consider the wind and rain forecast before heading out. {summary}"
    return summary
