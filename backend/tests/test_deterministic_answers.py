import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from groq import RateLimitError

from backend.agent import agent
from backend.agent.failures import FailureCategory, RequestFailure
from backend.weather.location_models import ConfirmedLocation, Resolved, ResolutionProvenance


def hourlies(**updates):
    start = datetime(2026, 11, 21)
    values = {
        "time": [(start + timedelta(hours=hour)).isoformat(timespec="minutes") for hour in range(48)],
        "temperature_2m": [22] * 48, "precipitation_probability": [12] * 48,
        "precipitation": [0] * 48, "wind_speed_10m": [8] * 48,
        "wind_gusts_10m": [13] * 48, "weather_code": [0] * 48,
        "relative_humidity_2m": [62] * 48,
    }
    values.update({key: value if isinstance(value, list) else [value] * 48 for key, value in updates.items()})
    return {"timezone": "Asia/Kolkata", "current": {"time": "2026-11-21T15:00"}, "hourly": values}


@pytest.fixture
def weather(monkeypatch):
    async def resolve(location, **_):
        return Resolved(query=location, location=ConfirmedLocation(
            name=location, latitude=20 if location == "Pune" else 30, longitude=75, timezone="Asia/Kolkata",
            provenance=ResolutionProvenance(method="standalone"),
        ))

    current = AsyncMock(return_value={"current": {
        "temperature_2m": 23, "weather_code": 2, "relative_humidity_2m": 62, "wind_speed_10m": 9,
    }})
    hourly = AsyncMock(return_value=hourlies())
    client_factory = Mock(side_effect=AssertionError("Unexpected Groq client"))
    monkeypatch.setattr(agent, "resolve_location", AsyncMock(side_effect=resolve))
    monkeypatch.setattr(agent, "get_current_weather", current)
    monkeypatch.setattr(agent, "get_hourly_forecast", hourly)
    monkeypatch.setattr(agent, "get_groq_client", client_factory)
    return hourly, current, client_factory


@pytest.mark.parametrize(("message", "expected"), [
    ("Temperature in Pune right now?", ("23 °C", "Current weather")),
    ("ok check Pune", ("Partly cloudy", "23 °C")),
    ("Could you give me the rain odds in Pune tonight?", ("12%", "tonight")),
    ("How strong is the wind in Pune tomorrow?", ("8 km/h", "tomorrow")),
    ("Humidity in Pune tonight?", ("62%", "tonight")),
    ("Tomorrow's weather in Pune?", ("22 °C", "12%", "8 km/h")),
    ("What should I wear in Pune tonight?", ("Light layers", "22 °C", "12%", "8 km/h")),
    ("Compare Pune and Nasik tomorrow.", ("Pune", "Nasik")),
])
def test_deterministic_eligible_requests_use_audited_evidence(weather, message, expected):
    output = asyncio.run(agent.run_agent(message))
    assert all(fragment in output["response"] for fragment in expected)
    assert output["validation_report"]["is_trustworthy"]
    summary = output["token_usage"]
    assert summary["deterministic_selected"] and summary["answer_complete"]
    assert summary["llm_calls_attempted"] == 0
    weather[2].assert_not_called()


@pytest.mark.parametrize(("message", "updates", "hazard"), [
    ("Can I go for a walk in Pune tonight?", {"weather_code": 95}, "Thunderstorm"),
    ("Should I drive in Pune tonight?", {"precipitation": 25}, "Heavy Rainfall"),
    ("Can I go for a walk in Pune tonight?", {"wind_gusts_10m": 100}, "Strong Wind"),
    ("Can I exercise in Pune tomorrow?", {"temperature_2m": 45}, "Extreme Heat"),
    ("Should I travel in Pune tonight?", {"weather_code": 45}, "reduced visibility"),
])
def test_activity_and_visibility_hazards_are_reported(weather, message, updates, hazard):
    weather[0].return_value = hourlies(**updates)
    output = asyncio.run(agent.run_agent(message))
    assert hazard in output["response"]
    assert output["validation_report"]["is_trustworthy"]
    assert output["token_usage"]["answer_complete"]
    weather[2].assert_not_called()
    if hazard != "reduced visibility":
        assert output["risk_assessment"]["overall_risk_level"] in {"HIGH", "SEVERE"}
        assert "postponing" in output["response"]


def test_partial_risk_evidence_never_turns_known_storm_into_positive_advice(weather):
    weather[0].return_value = hourlies(precipitation=None, temperature_2m=None, weather_code=95)
    output = asyncio.run(agent.run_agent("What should I wear in Pune tonight?"))
    assert "Thunderstorm" in output["response"]
    assert "postponing" in output["response"]
    assert not output["token_usage"]["answer_complete"]
    assert "Light layers" not in output["response"]


def test_supported_temperature_does_not_make_a_wind_answer_complete(weather):
    weather[0].return_value = hourlies(wind_speed_10m=[None] + [8] * 42 + [None] * 5)
    output = asyncio.run(agent.run_agent("How windy will it be tomorrow in Pune?"))
    assert "wind speed evidence" in output["response"]
    assert "8 km/h" not in output["response"]
    assert not output["token_usage"]["answer_complete"]


def completion(content):
    return SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=content, tool_calls=None), finish_reason="stop",
    )])


def test_complex_path_receives_prepared_evidence_and_checks_completeness(weather):
    create = AsyncMock(return_value=completion("Tomorrow in Pune, the temperature will be 22 °C."))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    output = asyncio.run(agent.run_agent("Explain the wind speed in Pune tomorrow in detail.", client=client))
    create.assert_awaited_once()
    messages = create.await_args.kwargs["messages"]
    assert any("Verified planned weather data" in message.get("content", "") and "8" in message["content"]
               for message in messages if isinstance(message, dict))
    assert not output["token_usage"]["answer_complete"]
    assert "complete answer" in output["response"]


def test_complex_quota_failure_without_complete_fallback_remains_typed(weather):
    request = httpx.Request("POST", "https://example.invalid")
    create = AsyncMock(side_effect=RateLimitError(
        "Daily quota exhausted", response=httpx.Response(429, request=request), body=None,
    ))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    with pytest.raises(RequestFailure) as caught:
        asyncio.run(agent.run_agent("Explain the wind speed in Pune tomorrow in detail.", client=client))
    assert caught.value.category == FailureCategory.GROQ_QUOTA_EXHAUSTED
    assert caught.value.metrics["llm_calls_attempted"] == 1


def test_same_day_relative_windows_have_separate_provenance(weather):
    output = asyncio.run(agent.run_agent("Is it colder in Pune tomorrow morning than tomorrow evening?"))
    assert "same forecast temperature range" in output["response"]
    assert output["token_usage"]["answer_complete"]
    assert output["token_usage"]["llm_calls_attempted"] == 0
    ids = {item for row in output["validation_report"]["validation_results"] for item in row["supporting_evidence_ids"]}
    assert any(item.startswith("tomorrow_morning:") for item in ids)
    assert any(item.startswith("tomorrow_evening:") for item in ids)


def test_multiple_requested_measurements_are_all_checked(weather):
    answer = asyncio.run(agent.run_agent("Temperature and humidity in Pune right now?"))
    assert "23 °C" in answer["response"] and "62%" in answer["response"]
    assert answer["token_usage"]["answer_complete"]
    weather[1].return_value["current"].pop("relative_humidity_2m")
    partial = asyncio.run(agent.run_agent("Temperature and humidity in Pune right now?"))
    assert "humidity evidence" in partial["response"]
    assert not partial["token_usage"]["answer_complete"]


def test_complex_comparison_can_fall_back_to_complete_audited_comparison(weather):
    request = httpx.Request("POST", "https://example.invalid")
    create = AsyncMock(side_effect=RateLimitError(
        "Daily quota exhausted", response=httpx.Response(429, request=request), body=None,
    ))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    output = asyncio.run(agent.run_agent("Compare Pune and Nasik tomorrow in detail.", client=client))
    assert output["validation_report"]["is_trustworthy"]
    assert output["token_usage"]["deterministic_fallback"]
    assert output["token_usage"]["answer_complete"]
    assert output["token_usage"]["failure_category"] == "groq_quota_exhausted"
