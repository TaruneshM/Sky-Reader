import asyncio
import json
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.agent import agent
from backend.agent.router import parse_weather_request, synthesize_deterministic_weather_buddy_response
from backend.evidence.hallucination_controller import HallucinationController
from backend.evidence.evidence_models import EvidenceCollection
from backend.weather import service


def forecast(observed="2026-11-21T16:15", temperature=20):
    midnight = datetime(2026, 11, 21)
    return {
        "timezone": "Asia/Tokyo",
        "current": {"time": observed},
        "hourly": {
            "time": [(midnight + timedelta(hours=h)).isoformat(timespec="minutes") for h in range(48)],
            "temperature_2m": [temperature] * 48,
            "apparent_temperature": [temperature - 1] * 48,
            "precipitation_probability": [4] * 24 + [29] * 24,
            "precipitation": [0] * 48,
            "wind_speed_10m": [15] * 24 + [50] * 24,
            "wind_gusts_10m": [20] * 24 + [70] * 24,
            "weather_code": [0] * 24 + [95] * 24,
            "relative_humidity_2m": [60] * 48,
        },
    }


def completion(content="", calls=()):
    return SimpleNamespace(usage=None, choices=[
        SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=list(calls)))
    ])


def client_with(*completions):
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=AsyncMock(side_effect=completions)
    )))


@pytest.mark.parametrize("question,intent,period", [
    ("Will it rain tomorrow in Tokyo?", "rain_check", "tomorrow"),
    ("How windy will it be tomorrow in Tokyo?", "wind_humidity", "tomorrow"),
    ("Will I need a jacket tonight?", "coat_clothing", "tonight"),
    ("Is it safe to drive today?", "weather_risks", "today"),
    ("Is it safe to drive in Tokyo with severe wind and humidity?", "weather_risks", "current"),
    ("Is it safe to travel during a storm?", "weather_risks", "current"),
    ("Can I go hiking tomorrow if thunderstorms are expected?", "weather_risks", "tomorrow"),
    ("Is it safe to go outside right now?", "weather_risks", "current"),
    ("Weather in Tokyo tomorrow at 5 pm?", "current_weather", "tomorrow@17:00"),
    ("Weather in Tokyo on 2026-11-22?", "current_weather", "2026-11-22"),
])
def test_intent_and_period_are_independent(question, intent, period):
    request = parse_weather_request(question)
    assert (request.intent, request.period, request.safety) == (intent, period, intent == "weather_risks")


@pytest.mark.parametrize("question,place", [
    ("Weather in São Paulo?", "São Paulo"),
    ("Weather in Paris, Texas?", "Paris, Texas"),
    ("Weather in New York City?", "New York City"),
    ("Weather in Dehradun?", "Dehradun"),
    ("Weather in Tokyo?", "Tokyo"),
])
def test_location_preserves_explicit_names(question, place):
    assert parse_weather_request(question, [{"role": "user", "content": "Weather in London?"}]).location == place
    assert parse_weather_request("Will it rain tomorrow?", [
        {"role": "assistant", "content": "The temperature in London was 22 °C."}
    ]).location is None


def test_geocoder_requires_unique_qualified_result(monkeypatch):
    texas = {"name": "Paris", "latitude": 33, "longitude": -95, "admin1": "Texas", "country": "United States"}
    france = {"name": "Paris", "latitude": 48, "longitude": 2, "admin1": "Île-de-France", "country": "France"}
    fetch = AsyncMock(return_value={"results": [france, texas]})
    monkeypatch.setattr(service, "_fetch_with_retry", fetch)
    service.clear_weather_cache()
    assert asyncio.run(service.geocode_location("Paris")) is None
    assert asyncio.run(service.geocode_location("Paris, Texas, United States"))["latitude"] == 33
    assert fetch.call_args.args[1]["name"] == "Paris"
    service.clear_weather_cache()


@pytest.mark.parametrize("observed,period,first,last", [
    ("2026-11-21T00:01", "today", "2026-11-21T00:00", "2026-11-21T23:00"),
    ("2026-11-21T16:15", "today", "2026-11-21T16:00", "2026-11-21T23:00"),
    ("2026-11-21T20:30", "tonight", "2026-11-21T20:00", "2026-11-21T23:00"),
    ("2026-11-21T23:55", "tomorrow", "2026-11-22T00:00", "2026-11-22T23:00"),
    ("2026-11-21T15:10+00:00", "today", "2026-11-22T00:00", "2026-11-22T23:00"),
])
def test_forecast_windows(observed, period, first, last):
    result = service.get_temporal_forecast_slice(forecast(observed), period)
    assert result["available"]
    assert (result["times"][0], result["times"][-1]) == (first, last)


def test_gap_missing_timestamp_and_out_of_horizon(monkeypatch):
    data = forecast()
    del data["hourly"]["time"][25]
    assert not service.get_temporal_forecast_slice(data, "tomorrow")["available"]
    assert not service.get_temporal_forecast_slice(data, "2026-11-23")["available"]
    del data["current"]
    del data["timezone"]
    assert not service.get_temporal_forecast_slice(data, "today")["available"]

    class FrozenClock(datetime):
        @classmethod
        def now(cls, tz=None):
            assert tz.key == "Asia/Tokyo"
            return cls(2026, 11, 21, 16, 15, tzinfo=tz)

    monkeypatch.setattr(service, "datetime", FrozenClock)
    data["timezone"] = "Asia/Tokyo"
    assert service.get_temporal_forecast_slice(data, "today")["times"][0] == "2026-11-21T16:00"


def test_fallback_preserves_actual_weather_and_risk():
    render = synthesize_deterministic_weather_buddy_response
    rain = render("rain_check", "Tokyo", hourly_slice={"rain_probabilities": [29]}, period="tomorrow")
    assert "29%" in rain and "tomorrow" in rain and "virtually" not in rain
    walk = render("morning_walk", "Tokyo", hourly_slice={
        "rain_probabilities": [19], "wind_speeds": [50], "temperatures": [20]
    })
    assert "19%" in walk and "50 km/h" in walk and "calm" not in walk
    assert "don't" in render("coat_clothing", "Tokyo").replace("’", "'").lower()
    for level in ("MODERATE", "SEVERE"):
        risk = render("weather_risks", "Tokyo", risk_data={
            "overall_risk_level": level, "detected_risks": [{"condition": "Thunderstorm"}],
            "data_limitations": ["Missing wind"]
        })
        assert level in risk and "Thunderstorm" in risk and "cannot establish safety" in risk


@pytest.fixture
def weather_tools(monkeypatch):
    from backend.weather.location_models import ConfirmedLocation, Resolved, ResolutionProvenance

    async def resolve(location, **kwargs):
        return Resolved(query=location, location=ConfirmedLocation(
            name="Tokyo", latitude=35, longitude=139, timezone="Asia/Tokyo",
            provenance=ResolutionProvenance(method="standalone"),
        ))

    geo = AsyncMock(side_effect=resolve)
    hourly = AsyncMock(return_value=forecast())
    current = AsyncMock(return_value={"current": {"time": "2026-11-21T16:15", "temperature_2m": 20}})
    monkeypatch.setattr(agent, "resolve_location", geo)
    monkeypatch.setattr(agent, "get_hourly_forecast", hourly)
    monkeypatch.setattr(agent, "get_current_weather", current)
    return geo, hourly, current


def test_unresolved_new_city_does_not_use_old_city(weather_tools):
    geocode, _, current = weather_tools
    from backend.weather.location_models import NotFound

    geocode.side_effect = None
    geocode.return_value = NotFound(query="São Paulo", reason="no_candidates")
    output = asyncio.run(agent.run_agent(
        "Weather in São Paulo?", [{"role": "user", "content": "Weather in Tokyo?"}], api_key=""
    ))
    geocode.assert_awaited_once_with(location="São Paulo")
    current.assert_not_called()
    assert "unique place" in output["response"]


def test_safety_uses_tomorrow_and_keeps_warnings(weather_tools):
    _, _, current = weather_tools
    output = asyncio.run(agent.run_agent("Can I go hiking tomorrow in Tokyo if thunderstorms are expected?", api_key=""))
    assert "tomorrow" in output["risk_assessment"]["forecast_period"]
    assert output["risk_assessment"]["overall_risk_level"] in {"HIGH", "SEVERE"}
    assert "Thunderstorm" in output["response"]
    assert "cannot establish safety" in output["response"]
    current.assert_not_called()


def test_future_weather_never_uses_observation_when_forecast_unavailable(weather_tools):
    _, hourly, current = weather_tools
    hourly.return_value = {}
    output = asyncio.run(agent.run_agent("How windy will it be tomorrow in Tokyo?", api_key=""))
    current.assert_not_called()
    assert "unavailable" in output["response"]


def test_deterministic_wind_and_evidence_are_in_sync(weather_tools):
    _, _, current = weather_tools
    client = client_with(completion("Tomorrow in Tokyo the wind speed will be 999 km/h."))
    output = asyncio.run(agent.run_agent("How windy will it be tomorrow in Tokyo?", client=client))
    client.chat.completions.create.assert_not_called()
    assert "50 km/h" in output["response"]
    assert "temperature" not in output["response"]
    assert "999" not in output["response"]
    assert output["claims"]
    assert output["claims"] == [row["claim"] for row in output["validation_report"]["validation_results"]]
    assert output["response"].startswith(output["explanation"]["conclusion"].removesuffix("..."))
    current.assert_not_called()


def test_current_fast_path_works_without_provider_key(weather_tools):
    _, hourly, current = weather_tools
    output = asyncio.run(agent.run_agent("Weather in Tokyo right now?", api_key=""))
    assert "20 °C" in output["response"]
    assert output["validation_report"]["is_trustworthy"]
    current.assert_awaited_once()
    hourly.assert_not_called()


def test_zero_claims_are_unverified():
    _, report = HallucinationController().audit("No data available.", EvidenceCollection())
    assert report.total_claims == 0 and not report.is_trustworthy


@pytest.mark.parametrize("question,period,names", [
    ("Compare Delhi and Dehradun.", "current", ("Delhi", "Dehradun")),
    ("Compare today's temperature in Tokyo and Paris.", "today", ("Tokyo", "Paris")),
    ("Which city has a higher rain probability tomorrow?", "tomorrow", ("Tokyo", "Paris")),
])
def test_agent_tool_evidence_isolated_by_city_and_period(question, period, names):
    def call(tool, number, **arguments):
        return SimpleNamespace(id=f"{tool}_{number}", function=SimpleNamespace(
            name=tool, arguments=json.dumps(arguments)
        ))

    calls = []
    for index, city in enumerate(names):
        calls.extend([call("geocode_location", index, location=city),
                      call("get_hourly_forecast", index, latitude=index, longitude=1)])

    async def execute(tool, arguments):
        if tool == "geocode_location":
            return {"name": arguments["location"], "latitude": names.index(arguments["location"]), "longitude": 1}
        index = arguments["latitude"]
        data = forecast(temperature=[12, 30][index])
        data["hourly"]["precipitation_probability"] = [[21, 74][index]] * 48
        return data

    if period == "tomorrow":
        good = f"Tomorrow in {names[0]} there is a 21% chance of rain. Tomorrow in {names[1]} there is a 74% chance of rain."
        bad = good.replace("21%", "74%")
    else:
        time_label = "Today " if period == "today" else ""
        good = f"{time_label}In {names[0]} it will be 12 °C. {time_label}In {names[1]} it will be 30 °C."
        bad = good.replace("12 °C", "30 °C")
    client = client_with(completion(calls=calls), completion(bad), completion(good))
    output = asyncio.run(agent.run_agent(question, executor_fn=execute, client=client))
    assert client.chat.completions.create.await_count == 3
    assert output["response"] == good
    audit = output["validation_report"]
    assert audit["is_trustworthy"]
    citations = [row["supporting_evidence_ids"][0] for row in audit["validation_results"]]
    assert citations[0].startswith("0,1:") and citations[1].startswith("1,1:")


def test_local_clock_range_excludes_hours_outside_request():
    request = parse_weather_request("Weather in Tokyo tomorrow between 3 and 6 pm?")
    assert request.period == "tomorrow@15:00-18:00"
    window = service.get_temporal_forecast_slice(forecast(), request.period)
    assert window["times"] == ["2026-11-22T15:00", "2026-11-22T16:00", "2026-11-22T17:00"]


def test_partial_series_is_not_reported_as_zero(weather_tools):
    _, hourly, _ = weather_tools
    data = forecast()
    data["hourly"]["precipitation_probability"][34] = None
    hourly.return_value = data
    output = asyncio.run(agent.run_agent("Will it rain tomorrow in Tokyo?", api_key=""))
    assert "0%" not in output["response"]
    assert "dry" not in output["response"]


def test_api_chat_contract_includes_final_risk_and_audit(weather_tools, monkeypatch):
    import httpx
    from backend.main import app

    endpoint = next(route.endpoint for route in app.routes if route.path == "/api/agent/chat")
    monkeypatch.setitem(endpoint.__globals__, "run_agent", agent.run_agent)
    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.post("/api/agent/chat", json={"message": "Is it safe to hike tomorrow in Tokyo?"})

    response = asyncio.run(send())
    assert response.status_code == 200
    payload = response.json()
    level = payload["risk_assessment"]["overall_risk_level"]
    assert level in payload["response"]
    assert payload["claims"][0]["claimed_value"] == level
    assert payload["validation_report"]["is_trustworthy"]


def test_explicit_now_rain_does_not_use_later_hours(weather_tools):
    output = asyncio.run(agent.run_agent("Will it rain right now in Tokyo?", api_key=""))
    assert "4%" in output["response"] and "29%" not in output["response"]


def test_city_followup_does_not_reuse_unrelated_location():
    history = [{"role": "user", "content": "Weather in Tokyo?"}]
    assert parse_weather_request("What about Lyon tomorrow?", history).location == "Lyon"
    history.append({"role": "user", "content": "Compare Delhi and Dehradun."})
    assert parse_weather_request("Will it rain tomorrow?", history).location is None


def test_location_after_period_and_qualifiers():
    request = parse_weather_request("What is the forecast for tomorrow in Paris, Texas?")
    assert request.location == "Paris, Texas"
    assert request.period == "tomorrow"


def test_duplicate_values_in_two_cities_are_audited_independently():
    from backend.evidence.claim_extractor import ClaimExtractor

    claims = ClaimExtractor().extract_claims(
        "Tokyo has a 30% chance of rain. Paris has a 30% chance of rain."
    )
    assert len(claims) == 2
    assert claims[0].statement != claims[1].statement


def test_wrong_peak_does_not_pass_by_matching_a_single_hour(weather_tools):
    _, hourly, _ = weather_tools
    data = forecast()
    data["hourly"]["precipitation_probability"][30] = 77
    hourly.return_value = data
    client = client_with(completion("Tomorrow in Tokyo the peak rain probability is 29%."))
    output = asyncio.run(agent.run_agent("Will it rain tomorrow in Tokyo?", client=client))
    assert "77%" in output["response"]
    assert output["validation_report"]["is_trustworthy"]


def test_weather_draft_without_tool_evidence_does_not_look_verified(weather_tools):
    weather_tools[2].return_value = {}
    client = client_with(completion("It will be 25 °C in Tokyo."))
    output = asyncio.run(agent.run_agent("Give a comprehensive weather briefing for Tokyo.", client=client))
    assert "25 °C" not in output["response"]
    assert not output["validation_report"]["is_trustworthy"]
