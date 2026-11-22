import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, Optional


INTENT_PATTERNS = [
    ("coat_clothing", [
        r"\b(carry|wear|need|take)\b.*\b(coat|jacket|sweater|hoodie|clothing|clothes|cloths|layers)\b",
        r"\b(should i|do i need to)\b.*\b(coat|jacket|sweater)\b",
        r"\b(?:clothing|clothes|cloths|layers)\b.*\bwear\b",
        r"\bwhat (?:should|can) i wear\b",
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
    reference_location: Optional[str] = None
    comparison: bool = False
    destinations: tuple[str, ...] = ()
    needs_destinations: bool = False


COMPARISON_MARKER = re.compile(r"\b(compare|versus|vs|which city|difference between)\b", re.I)
COMPARE_PLACES = re.compile(r"^compare\s+(.+?)\s+(?:and|with|versus|vs\.?)\s+(.+)", re.I)
CHOICE = re.compile(r"\b(?:choose|pick|decide between)\s+(.+?)\s+(?:or|and|versus|vs\.?)\s+(.+)", re.I)
IMPLICIT_CHOICE = re.compile(
    r"\bwhich (?:one |destination |place |city )?(?:should i (?:choose|pick)|(?:is|would be) better)\b",
    re.I,
)
ALTERNATIVE = re.compile(
    r"\b(?:(?:what|how) about|think(?:ing)? (?:about|abt)|maybe|consider(?:ing)?)\s+([^?!;]+)", re.I
)
DESTINATION_PREFIX = re.compile(r"^(?:(?:going|go|travel(?:l?ing)?|head(?:ing)?) (?:out )?to|visiting)\s+", re.I)
PLACE_END = re.compile(
    r"\s+\b(?:for (?:today|tonight|tomorrow)|please|any thoughts|what do you think|in detail|"
    r"comprehensively|instead|right now|now|currently|today|tonight|"
    r"tomorrow|yesterday|this|next|at|from|between|during|with|if|on|after|before|will|would|be)\b",
    re.I,
)
NON_PLACE = re.compile(
    r"^(?:today|tomorrow|tonight|now|right now|the next|going out|there|here|that|it|"
    r"(?:the )?(?:morning|afternoon|evening|night|weather|forecast)|"
    r"(?:an? )?(?:walk|hike|jacket|coat|sweater|umbrella)|"
    r"detail|outside|this weekend|my area|next week)(?:\s|$)", re.I,
)


def _place_phrase(value: str, conversational: bool = False) -> Optional[str]:
    value = re.split(r"\.\s+(?=(?:which|what|should|could|is|would)\b)", value, maxsplit=1, flags=re.I)[0]
    place = value.strip(" .,!?:;\"'“”")
    if conversational:
        place = DESTINATION_PREFIX.sub("", place)
        if place[:4].casefold() == "the " and (place.startswith("the ") or place[4:5].islower()):
            place = place[4:]
    place = PLACE_END.split(place, maxsplit=1)[0].strip(" .,\"'“”")
    if NON_PLACE.match(place) or not re.fullmatch(r"[^\W\d_][^?!;:]*", place):
        return None
    return place


def comparison_destinations(query: str) -> tuple[str, ...]:
    match = CHOICE.search(query) or COMPARE_PLACES.match(query.strip())
    if not match:
        return ()
    first, second = match.groups()
    if re.search(r"\b(weather|temperature|rain|wind)\b", first, re.I):
        first = explicit_location(first)
    else:
        first = _place_phrase(first, conversational=True)
    second = _place_phrase(second, conversational=True)
    return (first, second) if first and second else ()


def detect_weather_intent(query: str) -> Optional[str]:
    clean = query.casefold()
    if re.search(r"\b(safe|safety|severe|warnings?|danger(?:ous)?|hazards?|hazardous|storms?|thunderstorms?)\b", clean):
        return "weather_risks"
    if COMPARISON_MARKER.search(clean) or comparison_destinations(clean) or re.search(r"\b(comprehensive|in detail)\b", clean):
        return None
    for intent, patterns in INTENT_PATTERNS:
        if any(re.search(pattern, clean) for pattern in patterns):
            return intent
    if re.search(r"\b(colder|warmer|hotter|cooler)\b", clean):
        return "temperature"
    if re.search(r"\b(weather|forecast|temperature)\b", clean):
        return "current_weather"
    return None


def explicit_location(query: str) -> Optional[str]:
    query = unicodedata.normalize("NFC", query)
    if alternative := ALTERNATIVE.search(query):
        if place := _place_phrase(alternative[1], conversational=True):
            return place
    # A qualifier belongs to the candidate, including region and country after commas.
    for match in re.finditer(r"(?=\b(?:in|at|near|around|for)\s+([^?!;]+))", query, re.I):
        if place := _place_phrase(match[1]):
            return place
    direct = re.fullmatch(r"(?:weather|forecast|temperature)\s+([^?!;]+)", query.strip(" .?!"), re.I)
    if direct and (place := _place_phrase(direct[1])):
        return place
    for city in sorted(KNOWN_INDIAN_AND_GLOBAL_CITIES + ["new york city"], key=len, reverse=True):
        match = re.search(r"\b" + re.escape(city) + r"\b(?:,\s*[^?!;]+)?", query, re.I)
        if match:
            return match[0].rstrip(".")
    return None


def extract_location_from_query_or_history(query, conversation_history=None) -> Optional[str]:
    return parse_weather_request(query, conversation_history).location


def _requested_period(clean: str) -> Optional[str]:
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
        period = next((word for word in ("tomorrow", "tonight", "today") if re.search(rf"\b{word}\b", clean)), None)
        if period is None and re.search(r"\b(now|currently|current conditions|current weather)\b", clean):
            period = "current"
    if period in {None, "current", "today", "tomorrow", "tonight"} or date_match:
        base = "today" if period in {None, "current"} else period
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
    return period


def _parse_turn(query: str, prior: Optional[WeatherRequest]) -> WeatherRequest:
    query = unicodedata.normalize("NFC", query)
    clean = query.casefold()
    destinations = comparison_destinations(query)
    implicit_choice = bool(IMPLICIT_CHOICE.search(query))
    comparison = bool(destinations or COMPARISON_MARKER.search(query) or implicit_choice)
    introduced = explicit_location(query) if implicit_choice else None
    if implicit_choice and not destinations and prior:
        if introduced and prior.location and introduced.casefold() != prior.location.casefold():
            destinations = (prior.location, introduced)
        elif not introduced:
            destinations = prior.destinations or (
                (prior.reference_location, prior.location) if prior.reference_location and prior.location else ()
            )
    if not comparison and prior and prior.destinations and "," in query:
        qualified = _place_phrase(query)
        if qualified:
            city = qualified.split(",", 1)[0].strip().casefold()
            matches = [name for name in prior.destinations if name.split(",", 1)[0].strip().casefold() == city]
            if len(matches) == 1:
                destinations = tuple(qualified if name == matches[0] else name for name in prior.destinations)
                comparison = True
    location = None if comparison else explicit_location(query)
    intent = detect_weather_intent(query)
    activity_match = re.search(
        r"\b(driv\w*|travel\w*|hik\w*|walk\w*|jog\w*|cycling|outside|outdoor\w*|go(?:ing)? out)\b", clean
    )
    activity = activity_match[0] if activity_match else None
    alternative = bool(location and (ALTERNATIVE.search(query) or re.search(r"\binstead\b", clean)))
    reference = destinations[0] if destinations else None
    if prior and prior.location and alternative:
        reference = prior.reference_location if location.casefold() == prior.location.casefold() else prior.location
    if not location and not comparison and prior:
        location = prior.location
        reference = prior.reference_location
    prior_cities = (
        {name.split(",", 1)[0].strip().casefold()
         for name in (*prior.destinations, prior.location or "", prior.reference_location or "")}
        if prior else set()
    )
    pair_related = any(name.split(",", 1)[0].strip().casefold() in prior_cities for name in destinations)
    follow_up = alternative or pair_related or bool(
        prior and re.search(r"\b(there|same (?:trip|outing)|any thoughts on that)\b", clean)
    )
    if not intent and not comparison and follow_up:
        intent = (prior.intent if prior else None) or "current_weather"
    period = _requested_period(clean)
    if follow_up and prior:
        period = period or prior.period
        activity = activity or prior.activity
    safety = intent == "weather_risks" or bool(comparison and follow_up and prior and prior.safety)
    return WeatherRequest(
        intent=intent, period=period or "current", location=location, safety=safety,
        activity=activity, reference_location=reference, comparison=comparison,
        destinations=destinations, needs_destinations=implicit_choice and not destinations,
    )


def parse_weather_request(query: str, history=None) -> WeatherRequest:
    context = None
    for message in (history or [])[-6:]:
        if message.get("role") != "user" or not isinstance(message.get("content"), str):
            continue
        turn = _parse_turn(message["content"], context)
        if turn.comparison:
            if turn.destinations:
                context = turn
            elif not turn.needs_destinations:
                context = None
        elif turn.location and (turn.intent or explicit_location(message["content"])):
            context = turn
    return _parse_turn(query, context)


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
        "comparison": ("temperature_2m", "apparent_temperature", "precipitation_probability",
                       "precipitation", "wind_speed_10m", "wind_gusts_10m"),
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
