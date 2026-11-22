import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unicodedata import normalize

import pytest

from backend.agent import agent, executor
from backend.weather import service


def place(name, latitude, longitude, country, code, region, timezone, population=None, feature="PPL"):
    return {
        "name": name, "latitude": latitude, "longitude": longitude, "country": country,
        "country_code": code, "admin1": region, "timezone": timezone, "population": population,
        "feature_code": feature,
    }


TOKYO = place("Tokyo", 35.68, 139.69, "Japan", "JP", "Tokyo", "Asia/Tokyo", 8_300_000, "PPLC")
SAO_PAULO = place("São Paulo", -23.55, -46.64, "Brazil", "BR", "São Paulo", "America/Sao_Paulo", 12_000_000, "PPLA")
PARIS_TX = place("Paris", 33.66, -95.56, "United States", "US", "Texas", "America/Chicago", 25_000, "PPLA2")
PARIS_FR = place("Paris", 48.85, 2.35, "France", "FR", "Île-de-France", "Europe/Paris", 2_100_000, "PPLC")
SPRINGFIELD_IL = place("Springfield", 39.8, -89.64, "United States", "US", "Illinois", "America/Chicago", 114_000, "PPLA")
SPRINGFIELD_MO = place("Springfield", 37.2, -93.29, "United States", "US", "Missouri", "America/Chicago", 170_000)


@pytest.fixture
def open_meteo(monkeypatch):
    results = {
        "Tokyo": [
            place("Tokyo", 36, 140, "Japan", "JP", "Ibaraki", "Asia/Tokyo", 1900),
            place("Tokyo", 35.67, 139.70, "Japan", "JP", "Tokyo", "Asia/Tokyo", 14_000_000, "ADM1"),
            TOKYO,
        ],
        "São Paulo": [
            place("São Paulo", -8, -36, "Brazil", "BR", "Pernambuco", "America/Recife"),
            SAO_PAULO,
        ],
        "Paris": [PARIS_TX, PARIS_FR],
        "Springfield": [SPRINGFIELD_IL, SPRINGFIELD_MO],
        "Newport": [
            place("Newport", 51.59, -3, "United Kingdom", "GB", "Wales", "Europe/London"),
            place("Newport", 41.49, -71.3, "United States", "US", "Rhode Island", "America/New_York"),
        ],
    }

    async def search(url, params):
        assert params["count"] > 1
        return {"results": results.get(params["name"], [])}

    fetch = AsyncMock(side_effect=search)
    monkeypatch.setattr(service, "_fetch_with_retry", fetch)
    service.clear_weather_cache()
    yield results, fetch
    service.clear_weather_cache()


@pytest.mark.parametrize("query,expected", [
    ("Tokyo", TOKYO),
    (normalize("NFD", "São Paulo"), SAO_PAULO),
    ("Paris, Texas, USA", PARIS_TX),
    ("Paris, Texas", PARIS_TX),
    ("Paris, France", PARIS_FR),
    ("Springfield", None),
    ("Newport", None),
    ("Paris, Japan", None),
])
def test_ranking_is_independent_of_provider_order(query, expected, open_meteo):
    results, fetch = open_meteo
    for _ in range(2):
        result = asyncio.run(service.geocode_location(query))
        if expected is None:
            assert result is None
        else:
            assert result == {key: expected[key] for key in result}
        provider_query = fetch.call_args.args[1]["name"]
        if provider_query in results:
            results[provider_query].reverse()
        service.clear_weather_cache()


def test_normalized_name_preserves_meaningful_accents(open_meteo):
    results, fetch = open_meteo
    results["São Paulo"].insert(0, {**SAO_PAULO, "name": "Sao Paulo", "latitude": -24, "population": 25_000_000})
    result = asyncio.run(service.geocode_location(normalize("NFD", "São Paulo")))
    assert result["name"] == "São Paulo"
    assert result["latitude"] == SAO_PAULO["latitude"]
    assert fetch.call_args.args[1]["name"] == "São Paulo"


def observation():
    return {"current": {"time": "2026-11-21T16:00", "temperature_2m": 20}}


def test_fast_path_reuses_confirmed_location_for_followup(open_meteo, monkeypatch):
    current = AsyncMock(return_value=observation())
    monkeypatch.setattr(agent, "get_current_weather", current)
    user_turn = "What's the weather in São Paulo?"
    first = asyncio.run(agent.run_agent(user_turn, api_key=""))
    followup = asyncio.run(agent.run_agent("How windy is it now?", [
        {"role": "user", "content": user_turn},
        {"role": "assistant", "content": first["response"]},
    ], api_key=""))
    resolved = followup["tool_calls"][0]["result"]
    assert (resolved["name"], resolved["admin1"], resolved["country"], resolved["timezone"]) == (
        "São Paulo", "São Paulo", "Brazil", "America/Sao_Paulo",
    )
    assert current.await_count == 2
    current.assert_awaited_with(latitude=SAO_PAULO["latitude"], longitude=SAO_PAULO["longitude"])
    open_meteo[1].assert_awaited_once()


@pytest.mark.parametrize("query", [
    "What is the weather in Unknownville?",
    "Give a comprehensive weather briefing for Unknownville.",
    "What is the weather in Springfield?",
])
def test_unresolved_explicit_location_stops_both_paths(query, open_meteo, monkeypatch):
    current = AsyncMock(return_value=observation())
    monkeypatch.setattr(agent, "get_current_weather", current)
    output = asyncio.run(agent.run_agent(query, [
        {"role": "user", "content": "Weather in Tokyo?"},
        {"role": "assistant", "content": "It's 20 °C in Tokyo."},
    ], api_key=""))
    assert "specify the city, region, and country" in output["response"]
    assert len(output["tool_calls"]) == 1
    assert output["tool_calls"][0]["arguments"]["location"] in {"Unknownville", "Springfield"}
    current.assert_not_called()


def tool_call(tool, number, **args):
    return SimpleNamespace(id=f"call_{number}", function=SimpleNamespace(name=tool, arguments=json.dumps(args)))


def completion(text="", calls=()):
    return SimpleNamespace(usage=None, choices=[
        SimpleNamespace(message=SimpleNamespace(content=text, tool_calls=list(calls)))
    ])


def test_agentic_single_location_preserves_qualifiers_and_coordinates(open_meteo, monkeypatch):
    current = AsyncMock(return_value=observation())
    monkeypatch.setattr(agent, "get_current_weather", current)
    complete = AsyncMock(side_effect=[
        completion(calls=[
            tool_call("geocode_location", 1, location="Paris"),
            tool_call("get_current_weather", 2, latitude=PARIS_FR["latitude"], longitude=PARIS_FR["longitude"]),
            tool_call("get_current_weather", 3, latitude=PARIS_TX["latitude"], longitude=PARIS_TX["longitude"]),
        ]),
        completion("The current temperature in Paris is 20 °C."),
    ])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=complete)))
    output = asyncio.run(agent.run_agent("Give a comprehensive weather briefing for Paris, Texas.", client=client))
    current.assert_awaited_once_with(latitude=PARIS_TX["latitude"], longitude=PARIS_TX["longitude"])
    open_meteo[1].assert_awaited_once()
    lookup = output["tool_calls"][0]
    assert lookup["arguments"]["location"] == "Paris, Texas"
    assert lookup["result"]["admin1"] == "Texas"
    assert lookup["result"]["timezone"] == "America/Chicago"
    assert output["token_usage"]["suppressed_tool_requests"] == 3
    assert output["validation_report"]["is_trustworthy"]


def test_agentic_comparison_uses_shared_ranking_and_stops_on_ambiguity(open_meteo):
    complete = AsyncMock(return_value=completion(calls=[
        tool_call("geocode_location", 1, location="Tokyo"),
        tool_call("geocode_location", 2, location="Springfield"),
        tool_call("geocode_location", 3, location="Paris"),
    ]))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=complete)))
    output = asyncio.run(agent.run_agent("Compare Tokyo and Springfield.", client=client))
    assert output["tool_calls"][0]["result"]["country"] == "Japan"
    assert "Springfield" in output["response"] and "specify" in output["response"]
    assert open_meteo[1].await_count == 2


@pytest.mark.parametrize("incomplete", ["Paris", "Paris, Texas"])
def test_agentic_comparison_cannot_silently_drop_user_qualifier(open_meteo, incomplete, monkeypatch):
    forecast = {"current": {"time": "2026-11-21T16:00"},
                "hourly": {"time": ["2026-11-21T16:00"], "temperature_2m": [20],
                           "precipitation_probability": [10], "precipitation": [0],
                           "wind_speed_10m": [8], "weather_code": [0]}}
    monkeypatch.setattr(agent, "get_hourly_forecast", AsyncMock(return_value=forecast))
    complete = AsyncMock(side_effect=[
        completion(calls=[tool_call("geocode_location", 1, location=incomplete)]),
        completion(calls=[
            tool_call("geocode_location", 2, location="Paris, Texas, USA"),
            tool_call("geocode_location", 3, location="Tokyo"),
        ]),
        completion("I need more weather data."),
    ])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=complete)))
    output = asyncio.run(agent.run_agent("Compare Paris, Texas, USA and Tokyo in detail.", client=client))
    assert output["token_usage"]["suppressed_tool_requests"] == 3
    assert all("tools" not in invocation.kwargs for invocation in complete.call_args_list)
    assert output["tool_calls"][0]["result"]["admin1"] == "Texas"
    assert output["tool_calls"][1]["result"]["country"] == "Japan"
    assert open_meteo[1].await_count == 2


def test_tomorrow_fast_path_uses_ranked_tokyo_and_local_timezone(open_meteo, monkeypatch):
    from datetime import datetime, timedelta

    midnight = datetime(2026, 11, 21)
    hourly = AsyncMock(return_value={
        "current": {"time": "2026-11-21T16:00"},
        "hourly": {
            "time": [(midnight + timedelta(hours=hour)).isoformat(timespec="minutes") for hour in range(48)],
            "wind_speed_10m": [5] * 24 + [30] * 24,
        },
    })
    monkeypatch.setattr(agent, "get_hourly_forecast", hourly)
    complete = AsyncMock(return_value=completion("In Tokyo tomorrow, wind speed will be 30 km/h."))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=complete)))
    output = asyncio.run(agent.run_agent("How windy will it be tomorrow in Tokyo?", client=client))
    hourly.assert_awaited_once_with(latitude=TOKYO["latitude"], longitude=TOKYO["longitude"])
    complete.assert_not_called()
    assert output["tool_calls"][0]["result"]["timezone"] == "Asia/Tokyo"
    assert "30 km/h" in output["response"] and "tomorrow" in output["response"]
    assert output["validation_report"]["is_trustworthy"]


def scoped_comparison_fixture(temperature, risk=False):
    from datetime import datetime, timedelta

    start = datetime(2026, 11, 21)
    return {
        "current": {"time": "2026-11-21T20:00+00:00"},
        "hourly": {
            "time": [(start + timedelta(hours=hour)).isoformat(timespec="minutes") for hour in range(48)],
            "temperature_2m": [temperature] * 24 + [temperature + 3] * 24,
            "precipitation_probability": [60 if risk else 5] * 48,
            "precipitation": [1 if risk else 0] * 48,
            "wind_speed_10m": [65 if risk else 10] * 48,
            "weather_code": [95 if risk else 0] * 48,
        },
    }


def test_different_countries_compare_each_local_night_and_preserve_hazards(open_meteo, monkeypatch):
    async def forecast(latitude, longitude):
        if (latitude, longitude) == (TOKYO["latitude"], TOKYO["longitude"]):
            return scoped_comparison_fixture(9, risk=True)
        assert (latitude, longitude) == (PARIS_FR["latitude"], PARIS_FR["longitude"])
        return scoped_comparison_fixture(18)

    monkeypatch.setattr(agent, "get_hourly_forecast", AsyncMock(side_effect=forecast))
    output = asyncio.run(agent.run_agent("Compare Tokyo and Paris, France tonight.", api_key=""))
    assert "Tokyo for tonight: temperature 12 °C" in output["response"]
    assert "Paris for tonight: temperature 18 °C" in output["response"]
    assert "Thunderstorm" in output["response"]
    assert "peak rain probability 60%" in output["response"] and "wind speed 65 km/h" in output["response"]
    assert output["validation_report"]["is_trustworthy"]
    forecast_citations = output["explanation"]["supporting_evidence"]
    assert any(row["location"] == "Tokyo" and row["time_period"].startswith("2026-11-22T18") for row in forecast_citations)
    assert any(row["location"] == "Paris" and row["time_period"].startswith("2026-11-21T21") for row in forecast_citations)


def test_qualified_same_name_destinations_have_distinct_evidence(open_meteo, monkeypatch):
    results = iter((scoped_comparison_fixture(8), scoped_comparison_fixture(22)))
    monkeypatch.setattr(agent, "get_hourly_forecast", AsyncMock(side_effect=lambda **_: next(results)))
    output = asyncio.run(agent.run_agent("Compare Paris, France and Paris, Texas tonight.", api_key=""))
    assert "Paris, France for tonight: temperature 8 °C" in output["response"]
    assert "Paris, Texas for tonight: temperature 22 °C" in output["response"]
    assert output["validation_report"]["is_trustworthy"]
    locations = {row["location"] for row in output["explanation"]["supporting_evidence"]}
    assert locations == {"Paris, France", "Paris, Texas"}
