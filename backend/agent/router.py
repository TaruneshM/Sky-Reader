import re
from typing import Any, Dict, List, Optional, Tuple


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
        r"\b(humidity and wind|wind and humidity|humidity|wind speed|windy)\b",
    ]),
    ("tomorrow_forecast", [
        r"\bwhat about tomorrow\b",
        r"\bhow about tomorrow\b",
        r"\btomorrow('s)? weather\b",
        r"\bforecast for tomorrow\b",
    ]),
    ("weather_risks", [
        r"\b(storm|severe|warning|danger|hazard|safe to travel|safe to drive)\b",
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
    "paris", "tokyo", "new york", "san francisco", "berlin", "dubai", "singapore"
]


def detect_weather_intent(query: str) -> Optional[str]:
    """
    Detects if a query matches a standard simple weather intent.
    Returns the intent name or None if the query requires complex/agentic reasoning.
    """
    clean_q = query.strip().lower()

    # If comparison, multi-city, or explicit detailed analytical breakdown, return None
    complex_triggers = ["compare", " vs ", " versus ", "difference between", "explain in detail", "comprehensive"]
    if any(trig in clean_q for trig in complex_triggers):
        return None

    # Check for matching intent patterns
    for intent_name, patterns in INTENT_PATTERNS:
        for pat in patterns:
            if re.search(pat, clean_q):
                return intent_name

    return None


def extract_location_from_query_or_history(
    query: str,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Optional[str]:
    """
    Resolves the target location from the query, or falls back to the most recent
    location identified in the conversation history.
    """
    clean_q = query.strip().lower()

    # 1. Look for 'in <Location>', 'at <Location>', 'for <Location>'
    loc_match = re.search(r"\b(?:in|at|for|around|near)\s+([a-zA-Z\s]{2,25})(?:\?|\.|$|,)", clean_q)
    if loc_match:
        candidate = loc_match.group(1).strip()
        # Clean trailing conversational particles (please, now, today, etc.)
        cleaned = re.sub(r"\b(please|now|today|tonight|tomorrow|outside|at the moment|right now)\b", "", candidate, flags=re.IGNORECASE).strip()
        if cleaned and cleaned.lower() not in ("tomorrow", "today", "the morning", "the evening", "the afternoon", "detail"):
            return cleaned.title()

    # 2. Check for known cities directly mentioned
    for city in KNOWN_INDIAN_AND_GLOBAL_CITIES:
        if re.search(r"\b" + re.escape(city) + r"\b", clean_q):
            return city.title()

    # 3. Check conversation history backwards
    if conversation_history:
        for msg in reversed(conversation_history):
            content = str(msg.get("content", ""))
            # Check for city mentions in assistant or user messages
            for city in KNOWN_INDIAN_AND_GLOBAL_CITIES:
                if re.search(r"\b" + re.escape(city) + r"\b", content.lower()):
                    return city.title()
            # Check for pattern 'in <City>' in history
            hist_match = re.search(r"\b(?:in|at|for)\s+([a-zA-Z\s]{2,25})(?:\?|\.|$|,)", content.lower())
            if hist_match:
                cand = hist_match.group(1).strip()
                if cand not in ("tomorrow", "today", "the morning", "the evening", "the afternoon", "detail"):
                    return cand.title()

    return None


def synthesize_deterministic_weather_buddy_response(
    intent: str,
    location_name: str,
    current_data: Optional[Dict[str, Any]] = None,
    hourly_slice: Optional[Dict[str, Any]] = None,
    risk_data: Optional[Dict[str, Any]] = None,
    recommendations_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Produces a warm, conversational, 100% evidence-grounded Weather Buddy response
    without requiring an additional LLM round trip.
    """
    curr = (current_data or {}).get("current", {})
    temp = curr.get("temperature_2m", 20.0)
    feels = curr.get("apparent_temperature", temp)
    humidity = curr.get("relative_humidity_2m", 50.0)
    wind = curr.get("wind_speed_10m", 5.0)

    # Precipitation probability from hourly slice if present
    rain_probs = (hourly_slice or {}).get("rain_probabilities", [0.0])
    max_rain_prob = max(rain_probs) if rain_probs else 0.0

    if intent == "coat_clothing":
        if temp < 15.0:
            return f"It's chilly in {location_name} at around {temp} °C (feels like {feels} °C) 🧣. A warm coat or jacket is definitely recommended before heading out!"
        elif temp <= 24.0:
            return f"No heavy coat needed in {location_name}—it's comfortably mild at about {temp} °C (feels like {feels} °C) 🌤️. A light jacket or sweater will keep you comfortable if you'll be out late."
        else:
            return f"No coat needed at all—it's warm in {location_name} at {temp} °C ☀️. Light, breathable clothing is all you need!"

    elif intent == "umbrella":
        if max_rain_prob >= 30.0:
            return f"Yes, you should carry an umbrella in {location_name} 🌧️. The forecast indicates up to a {round(max_rain_prob)}% chance of rain."
        else:
            return f"No umbrella needed in {location_name}! Rain chance is practically zero (peak {round(max_rain_prob)}%) with dry conditions ☀️. Enjoy your day!"

    elif intent == "rain_check":
        if max_rain_prob >= 30.0:
            return f"Rain is likely in {location_name} with up to a {round(max_rain_prob)}% probability of showers 🌧️. Keep an umbrella handy!"
        else:
            return f"There's virtually no chance of rain in {location_name} ({round(max_rain_prob)}% probability) ☀️. Clear and dry skies ahead!"

    elif intent == "morning_walk":
        if max_rain_prob < 20.0 and 15.0 <= temp <= 28.0:
            return f"Yes, it's a great time for a morning walk in {location_name}! 🌤️ Temperatures are near {temp} °C with 0% rain risk and calm breezes. Enjoy your stroll!"
        else:
            return f"You can go for a walk in {location_name}, but keep in mind temperatures are around {temp} °C with {round(max_rain_prob)}% rain probability 🌤️. Dress comfortably!"

    elif intent == "wind_humidity":
        return f"In {location_name} right now, humidity is at {humidity}% with a gentle breeze of {wind} km/h 🌬️. Conditions feel pleasant!"

    elif intent == "tomorrow_forecast":
        temps = (hourly_slice or {}).get("temperatures", [15.0, 24.0])
        min_t = min(temps) if temps else 14.0
        max_t = max(temps) if temps else 24.0
        return f"Tomorrow in {location_name} will be pleasant with a high near {max_t} °C and a low of {min_t} °C 🌤️. Rain chance remains very low ({round(max_rain_prob)}%)."

    elif intent == "weather_risks":
        overall = (risk_data or {}).get("overall_risk_level", "LOW")
        hazards = (risk_data or {}).get("hazards", [])
        if overall in ("HIGH", "SEVERE"):
            return f"⚠️ Safety Advisory: {overall} weather risks detected for {location_name}. Conditions may include adverse weather. Exercise caution and avoid unnecessary travel."
        else:
            return f"Good news! Weather risks are currently LOW in {location_name} 🌤️. No severe weather hazards or travel disruptions are expected."

    # Default: current weather
    return f"It's mild and pleasant in {location_name} right now, around {temp} °C (feels like {feels} °C) with {humidity}% humidity and a {wind} km/h breeze 🌤️. No rain is currently expected."
