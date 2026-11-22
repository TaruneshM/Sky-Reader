import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from groq import APITimeoutError, AuthenticationError, RateLimitError

from backend.agent import agent
from backend.agent.conversation_state import ConversationScope
from backend.agent.failures import FailureCategory, RequestFailure
from backend.agent.request_planner import plan_weather_request
from backend.agent.router import parse_weather_request
from backend.weather.location_models import ConfirmedLocation, NotFound, Resolved, ResolutionProvenance
from backend.weather import service


SCOPE = ConversationScope(owner_kind="guest", owner_id="owner", thread_id="thread")


def resolve(place):
    return Resolved(query=place, location=ConfirmedLocation(
        name=place.split(",")[0], latitude=29, longitude=79, timezone="Asia/Kolkata",
        provenance=ResolutionProvenance(method="standalone"),
    ))


@pytest.mark.parametrize(("message", "location"), [
    ("soo i want to know abt the weather about nanital", "nanital"),
    ("ok check bhimtal", "bhimtal"),
    ("check the weather in bhimtal", "bhimtal"),
    ("what's it like in bhimtal?", "bhimtal"),
    ("weather about nainital", "nainital"),
    ("Hey, could you look up São José dos Campos?", "São José dos Campos"),
])
def test_informal_requests(message, location):
    task = parse_weather_request(message)
    assert task.intent == "current_weather"
    assert task.location == location


def test_informal_clarifications_keep_task_and_do_not_reuse_old_city():
    lookup = AsyncMock(side_effect=lambda location, **_: (
        NotFound(query=location, reason="no_candidates") if location.casefold().startswith("nanital") else resolve(location)
    ))
    current = AsyncMock(return_value={"current": {"temperature_2m": 20}})

    async def workflow():
        async def plan(message, state=None):
            return await plan_weather_request(
                message, scope=SCOPE, state=state, resolver=lookup, current_weather=current,
            )

        initial = await plan("ok check bhimtal")
        assert initial.state.last_confirmed_location.name == "bhimtal"
        missing = await plan("soo i want to know abt the weather about nanital", initial.state)
        assert missing.decision.kind == "NOT_FOUND"
        assert missing.state.last_confirmed_location == initial.state.last_confirmed_location
        qualified = await plan("nanital in uttrakhand", missing.state)
        assert qualified.decision.kind == "NOT_FOUND"
        assert qualified.state.task_id == missing.state.task_id
        assert lookup.await_args.kwargs["location"] == "nanital, uttrakhand"
        corrected = await plan("Nainital, Uttarakhand, India", qualified.state)
        assert corrected.state.task_id == qualified.state.task_id
        assert corrected.destinations[0].place.name == "Nainital"

        new_city = await plan("can you check another city?", corrected.state)
        assert new_city.decision.kind == "location_required"
        continued = await plan("São Paulo", new_city.state)
        assert continued.state.task_id == new_city.state.task_id
        assert continued.destinations[0].place.name == "São Paulo"
        unrelated = await plan("check my grammar", continued.state)
        assert unrelated.state == continued.state
        assert not unrelated.destinations

    asyncio.run(workflow())
    assert current.await_count == 3


def groq_error(status, message, headers=None):
    request = httpx.Request("POST", "https://example.invalid")
    response = httpx.Response(status, request=request, headers=headers)
    cls = AuthenticationError if status == 401 else RateLimitError
    return cls(message, response=response, body=None)


@pytest.mark.parametrize(("error", "category", "status"), [
    (groq_error(429, "Daily usage limit"), FailureCategory.GROQ_QUOTA_EXHAUSTED, 429),
    (groq_error(429, "Too many requests", {"Retry-After": "5"}), FailureCategory.GROQ_THROTTLED, 429),
    (groq_error(401, "synthetic-private-value"), FailureCategory.GROQ_AUTHENTICATION, 503),
    (APITimeoutError(request=httpx.Request("POST", "https://example.invalid")), FailureCategory.GROQ_TIMEOUT, 504),
])
def test_failed_provider_attempt_has_safe_metrics(error, category, status, caplog):
    create = AsyncMock(side_effect=error)
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    with pytest.raises(RequestFailure) as info:
        asyncio.run(agent.run_agent("Hello!", client=client))
    assert info.value.category is category
    assert info.value.status_code == status
    assert info.value.metrics["llm_calls_attempted"] == 1
    assert info.value.metrics["llm_calls_completed"] == 0
    assert info.value.metrics["prompt_tokens"] is None
    assert "synthetic-private-value" not in str(info.value) + caplog.text
    create.assert_awaited_once()


def test_missing_usage_stays_unknown():
    create = AsyncMock(return_value=SimpleNamespace(choices=[
        SimpleNamespace(message=SimpleNamespace(content="Hello!", tool_calls=None), finish_reason="stop"),
    ]))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    output = asyncio.run(agent.run_agent("Hello!", client=client))
    assert output["token_usage"]["llm_calls_completed"] == 1
    assert output["token_usage"]["llm_calls_with_usage"] == 0
    assert output["token_usage"]["total_tokens"] is None


def test_prepared_temperature_bypasses_groq_quota(monkeypatch):
    lookup = AsyncMock(return_value=resolve("bhimtal"))
    current = AsyncMock(return_value={"current": {"temperature_2m": 20}})
    create = AsyncMock(side_effect=groq_error(429, "Daily usage limit"))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(agent, "resolve_location", lookup)
    monkeypatch.setattr(agent, "get_current_weather", current)
    output = asyncio.run(agent.run_agent("Temperature in Bhimtal?", client=client))
    assert "20" in output["response"]
    assert output["validation_report"]["is_trustworthy"]
    create.assert_not_called()
    assert output["token_usage"]["deterministic_selected"] is True
    lookup.assert_awaited_once_with(location="Bhimtal")


def test_conservative_provider_spelling_match(monkeypatch):
    candidate = dict(id=1, name="Nainital", latitude=29.38, longitude=79.46, admin1="Uttarakhand",
                     country="India", country_code="IN", timezone="Asia/Kolkata")
    monkeypatch.setattr(service, "_fetch_with_retry", AsyncMock(side_effect=[
        {"results": [candidate]}, {"results": []},
    ]))
    result = asyncio.run(service.resolve_location("Nanital, Uttarakhand"))
    assert isinstance(result, Resolved)
    assert result.location.name == "Nainital"
    assert isinstance(asyncio.run(service.resolve_location("Nanital")), NotFound)


def test_relative_followup_retains_baseline_and_audits_both_windows(monkeypatch):
    lookup = AsyncMock(return_value=resolve("Bhimtal"))
    current = AsyncMock(return_value={"current": {"temperature_2m": 20}})
    hourly = AsyncMock(return_value={
        "timezone": "Asia/Kolkata",
        "current": {"time": "2026-11-22T12:00"},
        "hourly": {
            "time": ([f"2026-11-22T{hour:02d}:00" for hour in range(18, 24)]
                     + [f"2026-11-23T{hour:02d}:00" for hour in range(24)]),
            "temperature_2m": [20, 21] * 3 + [10, 11] * 12,
        },
    })
    monkeypatch.setattr(agent, "resolve_location", lookup)
    monkeypatch.setattr(agent, "get_current_weather", current)
    monkeypatch.setattr(agent, "get_hourly_forecast", hourly)

    async def workflow():
        async def run(message, state=None):
            return await agent.run_agent(message, api_key="", request_scope=SCOPE, trusted_state=state)

        initial = await run("Weather in Bhimtal?")
        clarify = await run("Is it colder than tonight?", initial["conversation_state"])
        assert "Which time" in clarify["response"]
        hourly.assert_not_called()
        comparison = await run("Tomorrow", clarify["conversation_state"])
        assert "colder for tomorrow than for tonight" in comparison["response"]
        assert comparison["validation_report"]["is_trustworthy"]
        assert comparison["token_usage"]["llm_calls_attempted"] == 0

    asyncio.run(workflow())
    lookup.assert_awaited_once()
    hourly.assert_awaited_once()


def test_weather_http_attempt_timing_is_separate_from_tool_tracing(monkeypatch):
    payload = dict(id=1, name="Nainital", latitude=29.39, longitude=79.45, admin1="Uttarakhand",
                   country="India", country_code="IN", timezone="Asia/Kolkata")
    service.clear_weather_cache()
    make_client = httpx.AsyncClient

    def response(request):
        if request.url.host == "geocoding-api.open-meteo.com":
            return httpx.Response(200, json={"results": [payload]})
        return httpx.Response(503, text="synthetic-private-weather-provider-body")

    monkeypatch.setattr(service.httpx, "AsyncClient", lambda **kwargs: make_client(
        transport=httpx.MockTransport(response), **kwargs,
    ))
    try:
        with pytest.raises(RequestFailure) as info:
            asyncio.run(agent.run_agent("Weather in Nainital, Uttarakhand?", api_key=""))
        assert info.value.category is FailureCategory.WEATHER_PROVIDER_UNAVAILABLE
        metrics = info.value.metrics
        assert metrics["weather_http_attempts"] == 2
        assert metrics["tool_calls_count"] == 2
        assert metrics["llm_calls_attempted"] == 0
        assert metrics["weather_provider_latency_ms"] >= 0
        assert "Nainital" not in str(metrics)
        assert "29.39" not in str(metrics)
        assert "synthetic-private-weather-provider-body" not in str(info.value)
    finally:
        service.clear_weather_cache()
