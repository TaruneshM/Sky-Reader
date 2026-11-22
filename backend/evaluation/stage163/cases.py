"""Held-out labels. D = deterministic, G = Groq-capable synthesis, C = clarification, L = limitation."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Case:
    category: str
    message: str
    intent: str | None
    places: tuple[str, ...]
    window: str
    route: str
    required: tuple[str, ...]
    fixture: str = "normal"
    prior: tuple[str, ...] = ()

    @property
    def groq_permitted(self):
        return self.route == "G"

    @property
    def expected_behavior(self):
        if self.fixture == "quota":
            return "audited_fallback_or_typed_groq_quota"
        if self.fixture in {"provider_error", "timeout"}:
            return "typed_weather_provider_unavailable"
        return {"D": "audited_answer", "G": "prepared_synthesis",
                "C": "clarify", "L": "state_evidence_limit"}[self.route]

    @property
    def qualifier(self):
        for country in ("Argentina", "Spain", "Portugal", "Fiji"):
            if country in self.message and self.places:
                return country
        return None

    @property
    def transition(self):
        if self.category == "comparison" and self.route == "C":
            return "allow_first_confirmed_destination"
        return "retain_anchor" if self.route == "C" and self.prior else "resolve" if self.places else "no_anchor"


def group(category, rows):
    for message, intent, places, window, route, required, *options in rows:
        fixture = options[0] if options else "normal"
        prior = options[1] if len(options) > 1 else ()
        yield Case(category, message, intent, tuple(places.split("|")) if places else (), window,
                   route, tuple(required.split("|")) if required else (), fixture, prior)


CASES = [
    *group("simple", [
        ("What temperature is Lisbon at right now?", "temperature", "Lisbon", "current", "D", "21 °C"),
        ("Humidity in Zürich currently?", "wind_humidity", "Zürich", "current", "D", "64%"),
        ("What’s the weather in Osaka?", "current_weather", "Osaka", "current", "D", "21 °C|partly cloudy"),
        ("How windy will it be in Recife tomorrow?", "wind_humidity", "Recife", "tomorrow", "D", "14 km/h"),
        ("Any rain expected in Kigali tonight?", "rain_check", "Kigali", "tonight", "D", "15%"),
        ("Temperature in Reykjavík tonight?", "temperature", "Reykjavík", "tonight", "D", "24 °C"),
        ("Tomorrow’s weather in Accra?", "tomorrow_forecast", "Accra", "tomorrow", "D", "24 °C|15%|14 km/h"),
        ("Wind gusts in Lyon tomorrow?", "wind_humidity", "Lyon", "tomorrow", "D", "25 km/h"),
        ("Could you give the precipitation probability in Muscat tonight?", "rain_check", "Muscat", "tonight", "D", "15%"),
        ("Is it humid in Cebu right now?", "wind_humidity", "Cebu", "current", "D", "64%"),
    ]),
    *group("informal", [
        ("ok please check Lisbon", "current_weather", "Lisbon", "current", "D", "21 °C|partly cloudy"),
        ("hey can you check how the weather's looking around there tomorrow?", "tomorrow_forecast", "Osaka", "tomorrow", "D", "24 °C|15%|14 km/h", "normal", ("Weather in Osaka?",)),
        ("soo weather about Zürich pls?", "current_weather", "Zürich", "current", "D", "21 °C"),
        ("could you look up Recife real quick?", "current_weather", "Recife", "current", "D", "21 °C"),
        ("what's it like in Kigali tonight?", "current_weather", "Kigali", "tonight", "D", "24 °C|15%"),
        ("umm rain odds in Accra tonight?", "rain_check", "Accra", "tonight", "D", "15%"),
        ("say how windy it'll get in Lyon tonight", "wind_humidity", "Lyon", "tonight", "D", "14 km/h"),
        ("weather in Muscat, thx", "current_weather", "Muscat", "current", "D", "21 °C"),
        ("how about tomorrow then?", "tomorrow_forecast", "Cebu", "tomorrow", "D", "24 °C|15%", "normal", ("Weather in Cebu?",)),
        ("what about the weather in Reykjavík?", "current_weather", "Reykjavík", "current", "D", "21 °C"),
    ]),
    *group("geography", [
        ("Temperature in Zurich right now?", "temperature", "Zürich", "current", "D", "21 °C", "accent"),
        ("Weather in Córdoba, Argentina?", "current_weather", "Córdoba", "current", "D", "21 °C", "ambiguous"),
        ("Temperature in Córdoba, Spain?", "temperature", "Córdoba", "current", "D", "21 °C", "ambiguous"),
        ("What's the weather in Córdoba?", "current_weather", "", "current", "C", "specify", "ambiguous"),
        ("Weather in Qaşr-e Shirin?", "current_weather", "Qaşr-e Shirin", "current", "D", "21 °C"),
        ("Temperature in São José dos Campos?", "temperature", "São José dos Campos", "current", "D", "21 °C"),
        ("Weather in Lisbn, Portugal?", "current_weather", "Lisbon", "current", "D", "21 °C", "spelling"),
        ("Weather in Lisbn?", "current_weather", "", "current", "C", "spelling", "empty_geocode"),
        ("Would you check Suva, Fiji?", "current_weather", "Suva", "current", "D", "21 °C"),
        ("Weather in Doha, Norway?", "current_weather", "", "current", "C", "specify"),
    ]),
    *group("clarification", [
        ("Argentina", "current_weather", "Córdoba", "current", "D", "21 °C", "ambiguous", ("Weather in Córdoba?",)),
        ("Spain", "temperature", "Córdoba", "tonight", "D", "24 °C", "ambiguous", ("Temperature in Córdoba tonight?",)),
        ("Córdoba in Spain", "wind_humidity", "Córdoba", "tomorrow", "D", "14 km/h", "ambiguous", ("How windy in Córdoba tomorrow?",)),
        ("Córdoba, Argentina", "rain_check", "Córdoba", "tonight", "D", "15%", "ambiguous", ("Any rain in Córdoba tonight?",)),
        ("Zürich", "current_weather", "Zürich", "current", "D", "21 °C", "normal", ("Could you check another city?",)),
        ("Lisbon, Portugal", "current_weather", "Lisbon", "current", "D", "21 °C", "empty_geocode", ("Weather in Lisbn?",)),
        ("Osaka", "temperature", "Osaka", "tomorrow", "D", "24 °C", "normal", ("What temperature tomorrow?",)),
        ("Accra", "rain_check", "Accra", "tonight", "D", "15%", "normal", ("Will it rain tonight?",)),
        ("Actually, humidity in Muscat tonight?", "wind_humidity", "Muscat", "tonight", "D", "64%", "ambiguous", ("Weather in Córdoba?",)),
        ("Thanks!", None, "", "current", "G", "hello", "ambiguous", ("Weather in Córdoba?",)),
    ]),
    *group("context", [
        ("How humid is it there now?", "wind_humidity", "Lisbon", "current", "D", "64%", "normal", ("Weather in Lisbon?", "Thanks", "Got it", "Okay", "Hello", "Nice", "Cheers")),
        ("What about Recife instead?", "temperature", "Recife", "tonight", "D", "24 °C", "normal", ("Temperature in Osaka tonight?",)),
        ("Will it rain there tomorrow?", "rain_check", "Cebu", "tomorrow", "D", "15%", "normal", ("Weather in Lyon?", "Weather in Cebu?")),
        ("Actually what’s it like in Suva?", "current_weather", "Suva", "current", "D", "21 °C", "normal", ("Temperature in Lisbon tonight?",)),
        ("Could you check another city?", "current_weather", "", "current", "C", "which city", "normal", ("Weather in Lisbon?",)),
        ("Please check weather in Lisbn?", "current_weather", "", "current", "C", "spelling", "empty_geocode", ("Weather in Recife?",)),
        ("How windy there tonight?", "wind_humidity", "Lyon", "tonight", "D", "14 km/h", "normal", ("Weather in Lyon?", "Weather in Lisbn?")),
        ("what if the forecast changes by the afternoon?", "uncertainty", "Osaka", "today_afternoon", "G", "forecast|uncertainty", "normal", ("Weather in Osaka?",)),
        ("Could we switch to the weather in Kigali tomorrow?", "current_weather", "Kigali", "tomorrow", "D", "24 °C", "normal", ("Weather in Recife?",)),
        ("What about this evening instead?", "tomorrow_forecast", "Muscat", "today_evening", "D", "24 °C|15%", "normal", ("Tomorrow's weather in Muscat?",)),
    ]),
    *group("compound", [
        ("Temperature and humidity in Lisbon now?", "temperature", "Lisbon", "current", "D", "21 °C|64%"),
        ("Rain probability and wind speed in Osaka tomorrow?", "rain_check", "Osaka", "tomorrow", "D", "15%|14 km/h"),
        ("Humidity and wind gusts in Zürich tonight?", "wind_humidity", "Zürich", "tonight", "D", "64%|25 km/h"),
        ("Give the temperature and risk of rain in Recife tonight.", "temperature", "Recife", "tonight", "D", "24 °C|15%"),
        ("Will it rain and get windy after sunset?", "rain_check", "Kigali", "tonight", "D", "15%|14 km/h", "normal", ("Weather in Kigali?",)),
        ("Will it rain in Accra and how humid will it be tomorrow?", "rain_check", "Accra", "tomorrow", "D", "15%|64%"),
        ("How windy is Lyon now, and what is the temperature?", "wind_humidity", "Lyon", "current", "D", "11 km/h|21 °C"),
        ("Give me both the humidity and temperature in Cebu tonight.", "temperature", "Cebu", "tonight", "D", "64%|24 °C"),
        ("Weather and wind speed in Muscat tomorrow evening?", "current_weather", "Muscat", "tomorrow_evening", "D", "24 °C|15%|14 km/h"),
        ("Is Reykjavík warm and dry tomorrow?", "temperature", "Reykjavík", "tomorrow", "D", "24 °C|15%"),
    ]),
    *group("comparison", [
        ("Compare Lisbon and Osaka tomorrow.", None, "Lisbon|Osaka", "tomorrow", "D", "24 °C|28 °C|15%|35%|14 km/h|19 km/h"),
        ("Compare Kigali with Recife tonight.", None, "Kigali|Recife", "tonight", "D", "24 °C|28 °C"),
        ("Would Accra or Lyon be better tomorrow?", None, "Accra|Lyon", "tomorrow", "D", "24 °C|28 °C|risk"),
        ("Compare Muscat and Cebu for cycling tomorrow.", None, "Muscat|Cebu", "tomorrow", "G", "14 km/h|19 km/h|risk"),
        ("Compare Zürich and Reykjavík tomorrow evening.", None, "Zürich|Reykjavík", "tomorrow_evening", "D", "24 °C|28 °C"),
        ("Compare the conditions in these two cities for cycling.", None, "Lisbon|Osaka", "tomorrow", "G", "risk|wind", "normal", ("Compare Lisbon and Osaka tomorrow.",)),
        ("Which place would be better tonight if I switch to Suva?", None, "Osaka|Suva", "tonight", "D", "24 °C", "normal", ("Weather in Osaka?",)),
        ("Compare Lisbon and Lisbn tonight.", None, "", "tonight", "C", "spelling", "empty_geocode"),
        ("Compare Osaka and Osaka tonight.", None, "", "tonight", "C", "same place"),
        ("Compare Accra with Recife tonight in detail.", None, "Accra|Recife", "tonight", "G", "24 °C|28 °C", "quota"),
    ]),
    *group("relative", [
        ("Is it colder in Lisbon tomorrow morning than tomorrow evening?", "temperature", "Lisbon", "tomorrow_morning", "D", "same forecast temperature range"),
        ("Will it be warmer in Osaka tomorrow than tonight?", "temperature", "Osaka", "tomorrow", "D", "same forecast temperature range"),
        ("Is it colder in Zürich tonight than tomorrow?", "temperature", "Zürich", "tonight", "D", "same forecast temperature range"),
        ("Is Recife cooler tomorrow afternoon than tomorrow morning?", "temperature", "Recife", "tomorrow_afternoon", "D", "same forecast temperature range"),
        ("Is it colder than the place we checked earlier?", "temperature", "", "current", "C", "which", "normal", ("Weather in Kigali?", "Weather in Cebu?")),
        ("Is it warmer than tonight?", "temperature", "Lyon", "current", "C", "which time", "normal", ("Weather in Lyon?",)),
        ("Tomorrow", "temperature", "Muscat", "tomorrow", "D", "same forecast temperature range", "normal", ("Weather in Muscat?", "Is it cooler than tonight?")),
        ("Will it be cooler in Accra tomorrow than tonight?", "temperature", "Accra", "tomorrow", "D", "colder", "cooler"),
        ("Will Cebu be warmer tomorrow morning than tonight?", "temperature", "Cebu", "tomorrow_morning", "L", "unavailable", "short"),
        ("Is it colder in Suva tomorrow than tonight?", "temperature", "Suva", "tomorrow", "L", "temperature data", "no_temperature"),
    ]),
    *group("activity", [
        ("What should I wear in Lisbon tomorrow evening?", "coat_clothing", "Lisbon", "tomorrow_evening", "D", "layers|24 °C|15%|14 km/h"),
        ("Should I bring a jacket in Osaka tonight?", "coat_clothing", "Osaka", "tonight", "D", "jacket|10 °C", "cold"),
        ("Would a jacket help in Zürich tomorrow?", "coat_clothing", "Zürich", "tomorrow", "D", "jacket|10 °C", "cold"),
        ("Should I go for a walk in Recife tonight?", "morning_walk", "Recife", "tonight", "D", "24 °C|15%|flexible"),
        ("Should I drive in Kigali tomorrow?", "morning_walk", "Kigali", "tomorrow", "D", "24 °C|14 km/h"),
        ("Can I cycle in Accra tonight?", "morning_walk", "Accra", "tonight", "D", "14 km/h|flexible"),
        ("Do I need an umbrella in Lyon tonight?", "umbrella", "Lyon", "tonight", "D", "umbrella|15%"),
        ("Can I go hiking in Cebu tomorrow morning?", "morning_walk", "Cebu", "tomorrow_morning", "D", "24 °C|15%"),
        ("Should I wear a hoodie in Muscat tonight?", "coat_clothing", "Muscat", "tonight", "D", "jacket|10 °C", "cold"),
        ("Can I exercise outside in Suva tomorrow evening?", "morning_walk", "Suva", "tomorrow_evening", "D", "flexible|24 °C"),
    ]),
    *group("safety", [
        ("Is it safe to walk in Lisbon tonight?", "weather_risks", "Lisbon", "tonight", "D", "hazard:thunderstorm|caution", "storm"),
        ("Should I drive in Osaka tonight?", "morning_walk", "Osaka", "tonight", "D", "hazard:heavy rainfall|caution", "flood"),
        ("Can I go for a walk in Zürich tomorrow?", "morning_walk", "Zürich", "tomorrow", "D", "hazard:strong wind|caution", "gust"),
        ("Can I exercise outside in Recife tomorrow?", "morning_walk", "Recife", "tomorrow", "D", "hazard:extreme heat|caution", "heat"),
        ("Should I travel in Kigali tonight?", "morning_walk", "Kigali", "tonight", "D", "hazard:reduced visibility|caution", "fog"),
        ("Is it safe to travel in Accra tomorrow morning?", "weather_risks", "Accra", "tomorrow_morning", "D", "hazard:thunderstorm|hazard:strong wind|caution", "multi"),
        ("i have an outdoor event tomorrow evening, should i postpone it?", "morning_walk", "Lyon", "tomorrow_evening", "D", "hazard:thunderstorm|caution", "storm", ("Weather in Lyon?",)),
        ("Are there any warnings in Cebu tonight?", "weather_risks", "Cebu", "tonight", "D", "hazard:heavy rainfall|caution", "flood"),
        ("Compare safety in Muscat and Suva tonight.", None, "Muscat|Suva", "tonight", "D", "hazard:thunderstorm|caution", "storm"),
        ("What are the hazards for hiking in Suva tomorrow?", "weather_risks", "Suva", "tomorrow", "D", "hazard:strong wind|caution", "gust"),
    ]),
    *group("insufficient", [
        ("What’s the temperature in Lisbon tomorrow?", "temperature", "Lisbon", "tomorrow", "L", "temperature evidence", "no_temperature"),
        ("How windy will Osaka get tomorrow?", "wind_humidity", "Osaka", "tomorrow", "L", "unavailable", "short"),
        ("Can I go for a walk in Zürich tonight?", "morning_walk", "Zürich", "tonight", "L", "hazard:thunderstorm|caution|incomplete", "partial_storm"),
        ("Will it rain in Recife tonight?", "rain_check", "Recife", "tonight", "L", "rain probability|evidence", "no_rain"),
        ("How windy will Kigali be tonight?", "wind_humidity", "Kigali", "tonight", "L", "wind speed evidence", "partial_wind"),
        ("Compare Accra and Lyon tomorrow.", None, "Accra|Lyon", "tomorrow", "L", "can’t recommend", "short"),
        ("Is it safe to go outside in Cebu tonight?", "weather_risks", "Cebu", "tonight", "D", "hazard:thunderstorm|caution", "contradiction"),
        ("Humidity in Muscat now?", "wind_humidity", "Muscat", "current", "L", "weather_provider_unavailable", "timeout"),
        ("Weather in Suva tomorrow?", "current_weather", "Suva", "tomorrow", "L", "weather_provider_unavailable", "provider_error"),
        ("Do I need a jacket in Reykjavík tomorrow?", "coat_clothing", "Reykjavík", "tomorrow", "L", "evidence", "no_temperature"),
    ]),
    *group("complex", [
        ("Explain the wind forecast in Lisbon tomorrow in detail.", "wind_humidity", "Lisbon", "tomorrow", "G", "14 km/h", "tool"),
        ("Give a detailed breakdown of Osaka’s weather tomorrow.", "current_weather", "Osaka", "tomorrow", "G", "24 °C|15%|14 km/h", "correction"),
        ("I might go hiking this weekend, which day seems safer?", "morning_walk", "Zürich", "weekend", "L", "unavailable", "normal", ("Weather in Zürich?",)),
        ("Explain trade-offs for a drive through Recife tomorrow evening.", "morning_walk", "Recife", "tomorrow_evening", "G", "wind|rain|driv"),
        ("What should I plan for a three-day road trip from Kigali?", "trip", "Kigali", "multi_day", "L", "coverage"),
        ("Explain the humidity in Accra tomorrow and how it affects cycling.", "wind_humidity", "Accra", "tomorrow", "G", "64%|cycling"),
        ("Could you give an hourly breakdown for Lyon tomorrow?", "current_weather", "Lyon", "tomorrow", "G", "hour"),
        ("Explain the weather in Muscat tomorrow in detail.", "current_weather", "Muscat", "tomorrow", "G", "24 °C|15%|14 km/h", "quota"),
        ("Give a comprehensive weather briefing for Cebu.", "current_weather", "Cebu", "current", "G", "21 °C", "no_usage"),
        ("Explain the temperature in Suva tonight in detail.", "temperature", "Suva", "tonight", "G", "24 °C", "tool"),
    ]),
]
