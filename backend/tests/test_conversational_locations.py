import asyncio
import json
import logging
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.agent import agent, executor
from backend.agent.router import parse_weather_request
from backend.weather import service


OUTING = "i ma going out in bhimtal tonight wht type of cloths should i wear"
ALTERNATIVE = "ok soo i was also thinking abt the tanakpur any thoughts on that"
HISTORY = [{"role": "user", "content": OUTING}]
BHIMTAL = (29.35, 79.5667)
TANAKPUR = (29.074, 80.11139)


def location(identifier, name, coordinates, country, region, feature="PPL", population=None):
    return {
        "id": identifier, "name": name, "latitude": coordinates[0], "longitude": coordinates[1],
        "feature_code": feature, "country_code": country, "country": {"IN": "India", "NP": "Nepal"}[country],
        "admin1": region, "timezone": "Asia/Kolkata" if country == "IN" else "Asia/Kathmandu",
        "population": population,
    }


@pytest.fixture
def provider(monkeypatch):
    # Based on live Open-Meteo metadata. Bhimtal's returned admin1 is used only for display.
    places = {
        "bhimtal": [location(7667772, "Bhimtal", BHIMTAL, "IN", "Uttar Pradesh")],
        "tanakpur": [
            location(10656643, "Tanakpur", (27.18893, 83.51603), "IN", "Uttar Pradesh"),
            location(7958918, "Tanakpur", (29.06346, 80.13251), "NP", "Sudurpashchim Pradesh", "PPLL"),
            location(1255027, "Tanakpur", TANAKPUR, "IN", "Uttarakhand", population=16_905),
            location(10881257, "Tanakpur", (24.73401, 85.08772), "IN", "Bihar"),
            location(7957453, "Tanakpur", (28.67294, 80.99372), "NP", "Sudurpashchim Pradesh", "PPLL"),
        ],
    }

    async def lookup(_url, params):
        return {"results": places.get(params["name"].casefold(), [])}

    async def weather(latitude, longitude):
        temperature = {BHIMTAL: 12, TANAKPUR: 26}[(latitude, longitude)]
        start = datetime(2026, 11, 21)
        return {
            "timezone": "Asia/Kolkata",
            "current": {"time": "2026-11-21T16:30"},
            "hourly": {
                "time": [(start + timedelta(hours=hour)).isoformat(timespec="minutes") for hour in range(48)],
                "temperature_2m": [temperature] * 48,
            },
        }

    search = AsyncMock(side_effect=lookup)
    forecast = AsyncMock(side_effect=weather)
    monkeypatch.setattr(service, "_fetch_with_retry", search)
    monkeypatch.setattr(agent, "get_hourly_forecast", forecast)
    monkeypatch.setitem(executor.available_func, "get_hourly_forecast", forecast)
    service.clear_weather_cache()
    yield places, search, forecast
    service.clear_weather_cache()


@pytest.mark.parametrize("prompt,expected,period", [
    ("what about tanakpur?", "tanakpur", "tonight"),
    (ALTERNATIVE, "tanakpur", "tonight"),
    ("maybe bhimtal instead?", "bhimtal", "tonight"),
    ("what about going to nainital tonight?", "nainital", "tonight"),
    ("what about going to Sa\u0303o Paulo, São Paulo, Brazil tomorrow?", "São Paulo, São Paulo, Brazil", "tomorrow"),
    ("maybe New York City, New York, USA instead?", "New York City, New York, USA", "tonight"),
    ("what about The Hague, Netherlands?", "The Hague, Netherlands", "tonight"),
    ("is it colder there tomorrow?", "bhimtal", "tomorrow"),
    ("what about tanakpur right now?", "tanakpur", "current"),
])
def test_conversational_destinations_and_time(prompt, expected, period):
    request = parse_weather_request(prompt, HISTORY)
    assert (request.location, request.period, request.activity) == (expected, period, "going out")
    assert request.intent == ("temperature" if "colder" in prompt else "coat_clothing")


@pytest.mark.parametrize("prompt", ["what about tanakpur?", ALTERNATIVE])
def test_outing_followup_resolves_new_destination_in_same_period(prompt, provider):
    _, _, forecast = provider
    first = asyncio.run(agent.run_agent(OUTING, api_key=""))
    answer = asyncio.run(agent.run_agent(prompt, [
        *HISTORY, {"role": "assistant", "content": first["response"]},
    ], api_key=""))
    assert "jacket" in first["response"] and "12 °C" in first["response"]
    assert "Tanakpur" in answer["response"] and "26 °C" in answer["response"] and "tonight" in answer["response"]
    assert "12 °C" not in answer["response"]
    assert answer["validation_report"]["is_trustworthy"]
    assert answer["tool_calls"][0]["result"]["admin1"] == "Uttarakhand"
    forecast.assert_awaited_with(latitude=TANAKPUR[0], longitude=TANAKPUR[1])


def test_context_breaks_only_a_clear_geographic_tie_and_does_not_pollute_cache(provider, caplog):
    places, _, _ = provider
    with caplog.at_level(logging.DEBUG, logger=service.__name__):
        assert asyncio.run(service.geocode_location("Tanakpur")) is None
        inferred = asyncio.run(service.geocode_location("Tanakpur", reference_location="Bhimtal"))
        assert inferred["admin1"] == "Uttarakhand"
        assert asyncio.run(service.geocode_location("Tanakpur")) is None
        assert asyncio.run(service.geocode_location("Missingville", reference_location="Bhimtal")) is None
    assert "reason=missing_population" in caplog.text
    assert "decision=nearby_same_country" in caplog.text
    assert "decision=no_candidates" in caplog.text
    assert "10656643" in caplog.text

    places["tanakpur"].append(location(1, "Tanakpur", (29.12, 80.09), "IN", "Uttarakhand"))
    assert asyncio.run(service.geocode_location("Tanakpur", reference_location="Bhimtal")) is None
    places["tanakpur"].pop()
    qualified = asyncio.run(service.geocode_location("Tanakpur, Nepal", reference_location="Bhimtal"))
    assert qualified is None  # Two Nepal records remain ambiguous, and India cannot override the qualifier.


def test_missing_place_never_reuses_previous_weather(provider, caplog):
    _, search, forecast = provider
    with caplog.at_level(logging.DEBUG, logger=agent.__name__):
        reply = asyncio.run(agent.run_agent("maybe Missingville instead?", HISTORY, api_key=""))
    assert "Missingville" in reply["response"] and "specify" in reply["response"]
    assert "location='Missingville'" in caplog.text
    assert OUTING not in caplog.text
    search.assert_awaited_once()
    forecast.assert_not_called()


def test_diagnostics_redact_credential_like_location():
    assert service.geocoding_log_label("A" * 43) is None
    assert service.geocoding_log_label("Bhimtal, India") == "Bhimtal, India"


def call(tool, number, **arguments):
    return SimpleNamespace(id=f"call_{number}", function=SimpleNamespace(
        name=tool, arguments=json.dumps(arguments),
    ))


def completion(text="", calls=()):
    return SimpleNamespace(usage=None, choices=[
        SimpleNamespace(message=SimpleNamespace(content=text, tool_calls=list(calls))),
    ])


def client_for(*completions):
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=AsyncMock(side_effect=completions),
    )))


def test_agentic_followup_uses_same_contextual_geocoder(provider):
    client = client_for(
        completion(calls=[call("get_hourly_forecast", 1, latitude=TANAKPUR[0], longitude=TANAKPUR[1])]),
        completion("Tonight in Tanakpur the temperature will be 26 °C."),
    )
    output = asyncio.run(agent.run_agent("What about Tanakpur in detail?", HISTORY, client=client))
    assert output["tool_calls"][0]["result"]["admin1"] == "Uttarakhand"
    assert output["iterations"] == 2
    assert output["validation_report"]["is_trustworthy"]


@pytest.mark.parametrize("question", [
    "should i choose bhimtal or tanakpur?",
    "Compare Bhimtal and Tanakpur for tonight.",
])
def test_explicit_choice_keeps_city_evidence_separate(question, provider):
    calls = []
    for index, (name, coordinates) in enumerate([("Bhimtal", BHIMTAL), ("Tanakpur", TANAKPUR)]):
        calls += [
            call("geocode_location", index * 2, location=name),
            call("get_hourly_forecast", index * 2 + 1, latitude=coordinates[0], longitude=coordinates[1]),
        ]
    corrected = "Tonight in Bhimtal it will be 12 °C. Tonight in Tanakpur it will be 26 °C."
    client = client_for(completion(calls=calls), completion(corrected.replace("12 °C", "26 °C")), completion(corrected))
    output = asyncio.run(agent.run_agent(question, HISTORY, client=client))
    assert "Bhimtal for tonight: temperature 12 °C" in output["response"]
    assert "Tanakpur for tonight: temperature 26 °C" in output["response"]
    assert client.chat.completions.create.await_count == 3
    assert output["validation_report"]["is_trustworthy"]
    citation_ids = [row["supporting_evidence_ids"][0] for row in output["validation_report"]["validation_results"]]
    assert citation_ids[0].startswith("29.35,79.5667:")
    assert citation_ids[1].startswith("29.074,80.11139:")


def test_implicit_comparison_uses_two_recent_destinations_or_asks(provider):
    reply = asyncio.run(agent.run_agent("Which one should I choose?", HISTORY, api_key=""))
    assert reply["response"] == "Which two destinations should I compare?"
    request = parse_weather_request("Which one should I choose?", [
        *HISTORY, {"role": "user", "content": ALTERNATIVE},
    ])
    assert request.destinations == ("bhimtal", "tanakpur")
    assert request.period == "tonight"
    assert request.reference_location == "bhimtal"


EXACT_OUTING = "I'm going out in Bhimtal tonight. What should I wear?"
EXACT_COMPARISON = "I was also thinking about Tanakpur. Which place would be better tonight?"
EXACT_RETRY = "compare bhimtal and tanakpur"


@pytest.mark.parametrize("retry", [False, True])
def test_exact_comparison_and_retry_reuse_the_outing(provider, retry):
    _, search, forecast = provider
    first = asyncio.run(agent.run_agent(EXACT_OUTING, api_key=""))
    history = [{"role": "user", "content": EXACT_OUTING}, {"role": "assistant", "content": first["response"]}]
    if retry:
        history += [
            {"role": "user", "content": EXACT_COMPARISON},
            {"role": "assistant", "content": "Which two destinations should I compare?"},
        ]
    output = asyncio.run(agent.run_agent(EXACT_RETRY if retry else EXACT_COMPARISON, history, api_key=""))
    lookups = [entry["result"] for entry in output["tool_calls"] if entry["tool"] == "geocode_location"]
    assert [place["name"] for place in lookups] == ["Bhimtal", "Tanakpur"]
    assert lookups[1]["admin1"] == "Uttarakhand"
    assert "for tonight" in output["response"]
    assert output["validation_report"]["is_trustworthy"]
    assert [entry.args[1]["name"].casefold() for entry in search.await_args_list] == ["bhimtal", "tanakpur"]
    assert forecast.await_count == 3  # Original clothing turn plus one forecast per comparison destination.


def test_standalone_explicit_pair_resolves_second_from_first(provider):
    _, search, _ = provider
    output = asyncio.run(agent.run_agent("Compare Bhimtal and Tanakpur tonight.", api_key=""))
    assert "Tanakpur" in output["response"] and "specify" not in output["response"]
    assert search.await_count == 2
    assert asyncio.run(service.geocode_location("Tanakpur")) is None


def test_groq_comparison_serves_duplicate_qualified_alias_from_prepared_scope(provider):
    _, search, forecast = provider
    tools = [
        call("geocode_location", 1, location="Tanakpur"),
        call("geocode_location", 2, location="Bhimtal, India"),
        call("geocode_location", 3, location="Bhimtal, India"),
        call("get_hourly_forecast", 4, latitude=TANAKPUR[0], longitude=TANAKPUR[1]),
        call("get_hourly_forecast", 5, latitude=TANAKPUR[0], longitude=TANAKPUR[1]),
    ]
    client = client_for(completion(calls=tools),
                        completion("Tonight in Bhimtal it will be 12 °C. Tonight in Tanakpur it will be 26 °C."))
    output = asyncio.run(agent.run_agent(EXACT_COMPARISON, [{"role": "user", "content": EXACT_OUTING}], client=client))
    messages = client.chat.completions.create.call_args.kwargs["messages"]
    tool_replies = [json.loads(message["content"]) for message in messages if isinstance(message, dict)
                    and message["role"] == "tool"]
    assert [reply["name"] for reply in tool_replies[:3]] == ["Tanakpur", "Bhimtal", "Bhimtal"]
    assert tool_replies[3]["hours"][0] == "2026-11-21T18:00"
    assert tool_replies[3] == tool_replies[4]
    assert len(output["tool_calls"]) == 4
    assert forecast.await_count == search.await_count == 2


def test_missing_forecast_only_reports_available_city_and_withholds_recommendation(provider):
    _, _, forecast = provider
    complete = forecast.side_effect

    async def incomplete(latitude, longitude):
        return {} if (latitude, longitude) == TANAKPUR else await complete(latitude, longitude)

    forecast.side_effect = incomplete
    client = client_for()
    output = asyncio.run(agent.run_agent(EXACT_COMPARISON, [{"role": "user", "content": EXACT_OUTING}], client=client))
    assert "Weather for Tanakpur is unavailable for tonight" in output["response"]
    assert "can’t recommend" in output["response"]
    assert all(row["supporting_evidence_ids"][0].startswith("29.35,79.5667:")
               for row in output["validation_report"]["validation_results"])
    client.chat.completions.create.assert_not_called()


def test_qualified_answer_to_clarification_preserves_comparison(provider):
    history = [
        {"role": "user", "content": EXACT_OUTING},
        {"role": "user", "content": EXACT_COMPARISON},
        {"role": "assistant", "content": "Which Tanakpur did you mean?"},
    ]
    output = asyncio.run(agent.run_agent("Tanakpur, Uttarakhand", history, api_key=""))
    assert [entry["arguments"]["location"] for entry in output["tool_calls"] if entry["tool"] == "geocode_location"] == [
        "Bhimtal", "Tanakpur, Uttarakhand",
    ]
    assert "for tonight" in output["response"]


def test_model_cannot_inject_untrusted_geographic_reference(provider):
    _, search, _ = provider
    with pytest.raises(ValueError, match="location name only"):
        asyncio.run(executor.execute_tool("geocode_location", {
            "location": "Tanakpur", "reference_place": {"latitude": 29.35, "longitude": 79.5667},
        }))
    search.assert_not_called()
