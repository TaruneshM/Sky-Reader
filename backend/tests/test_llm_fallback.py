import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from groq import APIStatusError, APITimeoutError, AuthenticationError, RateLimitError

from backend.agent import agent
from backend.agent.failures import FailureCategory, RequestFailure
from backend.agent.llm_budget import LLMLimits
from backend.llm_gateway.gateway import Gateway
from backend.tests.test_thread_persistence import app_client, guest_session, open_thread, stored, turn


def completion(text="Hello.", calls=None):
    return SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=text, tool_calls=calls),
    )])


def sdk_error(status):
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    cls = {429: RateLimitError, 401: AuthenticationError}.get(status, APIStatusError)
    return cls("Mock error", response=httpx.Response(status, request=request, headers={"Retry-After": "9"}), body=None)


@pytest.fixture
def providers(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED_PROVIDERS", "groq,gemini,openrouter")
    monkeypatch.setenv("LLM_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("GROQ_API_KEY", "mock")
    monkeypatch.setenv("GEMINI_API_KEY", "mock")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-fixture")
    monkeypatch.setenv("OPENROUTER_API_KEY", "mock")
    monkeypatch.setenv("OPENROUTER_MODEL", "qwen/qwen3-coder:free")
    calls = []
    groq = AsyncMock(return_value=completion())
    monkeypatch.setattr(agent, "get_groq_client", lambda **_: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=groq)),
    ))
    statuses = {"gemini": 200, "openrouter": 200}

    def fake(req):
        import json

        name = "gemini" if req.url.host == "generativelanguage.googleapis.com" else "openrouter"
        calls.append((name, json.loads(req.content)))
        if statuses[name] != 200:
            return httpx.Response(statuses[name])
        if name == "gemini":
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "Hello."}]}}]})
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": "Hello."}}]})

    monkeypatch.setattr(agent, "Gateway", lambda name, **kwargs: Gateway(name, transport=httpx.MockTransport(fake), **kwargs))
    return groq, calls, statuses


def test_primary_success_does_not_contact_secondaries(providers):
    groq, calls, _ = providers
    result = asyncio.run(agent.run_agent("Tell me a joke."))
    assert result["token_usage"]["attempted_providers"] == ["groq"]
    assert groq.await_count == 1 and calls == []


@pytest.mark.parametrize("status", [429, 503])
def test_transient_failures_follow_priority_and_preserve_unknown_usage(providers, status):
    groq, calls, statuses = providers
    groq.side_effect = sdk_error(status)
    if status == 503:
        statuses["gemini"] = 502
    result = asyncio.run(agent.run_agent("Tell me a joke."))
    trace = result["token_usage"]
    assert trace["attempted_providers"] == (["groq", "gemini"] if status == 429 else ["groq", "gemini", "openrouter"])
    assert trace["successful_provider"] == trace["attempted_providers"][-1]
    assert trace["prompt_tokens"] is None
    assert trace["llm_calls"][0]["provider_status"] == status
    assert groq.await_count == 1
    assert "tool_calls" not in str(calls)


@pytest.mark.parametrize(("status", "explicit"), [(401, False), (400, False), (503, True)])
def test_terminal_and_explicit_errors_do_not_fall_back(providers, status, explicit):
    groq, calls, _ = providers
    groq.side_effect = sdk_error(status)
    with pytest.raises(RequestFailure):
        asyncio.run(agent.run_agent("Tell me a joke.", provider="groq" if explicit else None))
    assert calls == []


def test_disabled_and_paid_models_are_skipped(providers, monkeypatch):
    groq, calls, _ = providers
    monkeypatch.setenv("LLM_ENABLED_PROVIDERS", "gemini,openrouter")
    monkeypatch.setenv("OPENROUTER_MODEL", "paid/model")
    result = asyncio.run(agent.run_agent("Tell me a joke.", provider_priority=("openrouter", "groq", "gemini")))
    assert result["token_usage"]["attempted_providers"] == ["gemini"]
    assert groq.await_count == 0 and len(calls) == 1


@pytest.mark.parametrize("limits", [LLMLimits(attempts=1), LLMLimits(output_tokens=1)])
def test_budget_shared_across_providers(providers, limits):
    groq, calls, _ = providers
    groq.side_effect = sdk_error(503)
    with pytest.raises(RequestFailure) as caught:
        asyncio.run(agent.run_agent("Tell me a joke.", llm_limits=limits))
    assert caught.value.category is FailureCategory.LLM_BUDGET_EXHAUSTED
    assert calls == []


def test_timeout_can_replay_initial_prompt(providers):
    groq, calls, _ = providers
    groq.side_effect = APITimeoutError(request=httpx.Request("POST", "https://api.groq.com"))
    assert asyncio.run(agent.run_agent("Tell me a joke."))["token_usage"]["successful_provider"] == "gemini"
    assert len(calls) == 1


def test_deadline_and_cancellation_stop_chain(providers):
    groq, calls, _ = providers

    async def stall(**_):
        await asyncio.Event().wait()

    groq.side_effect = stall

    async def run():
        with pytest.raises(RequestFailure) as caught:
            await agent.run_agent("Tell me a joke.", llm_limits=LLMLimits(deadline_seconds=0.02))
        assert caught.value.category is FailureCategory.LLM_BUDGET_EXHAUSTED
        task = asyncio.create_task(agent.run_agent("Tell me a joke."))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run())
    assert calls == []


def test_after_tool_turn_no_replay_or_duplicate_execution(providers):
    groq, calls, _ = providers
    tool = SimpleNamespace(id="one", function=SimpleNamespace(name="geocode_location", arguments='{"location":"Tokyo"}'))
    groq.side_effect = [completion(None, [tool]), sdk_error(503)]
    executor = AsyncMock(return_value={"name": "Tokyo", "latitude": 1.0, "longitude": 2.0})
    with pytest.raises(RequestFailure) as caught:
        asyncio.run(agent.run_agent("Weather in Tokyo?", executor_fn=executor))
    assert not caught.value.replay_safe
    executor.assert_awaited_once()
    assert calls == []


def test_unsupported_weather_draft_cannot_trigger_fallback(providers):
    groq, calls, _ = providers
    groq.return_value = completion("Tomorrow in Lyon it will be 24 °C with a 15% chance of rain.")
    result = asyncio.run(agent.run_agent("What do you think of the plans?"))
    assert "24" not in result["response"]
    assert calls == []


def test_malformed_provider_reply_does_not_fall_back(providers):
    groq, calls, _ = providers
    groq.return_value = SimpleNamespace(choices=[])
    with pytest.raises(RequestFailure):
        asyncio.run(agent.run_agent("Tell me a joke."))
    assert calls == []


def test_evidence_gate_still_rejects_secondary_draft(providers, monkeypatch):
    groq, _, _ = providers
    groq.side_effect = sdk_error(429)

    def mock(request):
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [
            {"text": "Tomorrow in Lyon it will be 24 °C with a 15% chance of rain."},
        ]}}]})

    monkeypatch.setattr(agent, "Gateway", lambda name, **kwargs: Gateway(
        name, transport=httpx.MockTransport(mock), **kwargs,
    ))
    result = asyncio.run(agent.run_agent("What do you think of the plans?"))
    assert "24" not in result["response"]
    assert result["token_usage"]["attempted_providers"] == ["groq", "gemini"]


def test_deterministic_answer_does_not_consult_provider_configuration(providers, monkeypatch):
    from backend.weather.location_models import ConfirmedLocation, Resolved, ResolutionProvenance

    groq, calls, _ = providers
    location = ConfirmedLocation(name="Tokyo", latitude=35.0, longitude=139.0,
                                 provenance=ResolutionProvenance(method="standalone"))
    monkeypatch.setattr(agent, "resolve_location", AsyncMock(return_value=Resolved(query="Tokyo", location=location)))
    monkeypatch.setattr(agent, "get_current_weather", AsyncMock(return_value={"current": {
        "temperature_2m": 22, "weather_code": 0,
    }}))
    result = asyncio.run(agent.run_agent("What's the weather in Tokyo right now?"))
    assert result["token_usage"]["deterministic_selected"]
    assert groq.await_count == 0 and calls == []


def test_tertiary_terminal_failure_is_returned_without_repeating_any_provider(providers):
    groq, calls, statuses = providers
    groq.side_effect = sdk_error(503)
    statuses.update(gemini=503, openrouter=401)
    with pytest.raises(RequestFailure) as caught:
        asyncio.run(agent.run_agent("Tell me a joke."))
    assert caught.value.provider == "openrouter"
    assert caught.value.category is FailureCategory.LLM_AUTHENTICATION
    assert caught.value.metrics["attempted_providers"] == ["groq", "gemini", "openrouter"]
    assert len(calls) == 2 and groq.await_count == 1


def test_input_reservation_is_not_refunded_on_switch(providers):
    groq, calls, _ = providers
    groq.side_effect = sdk_error(503)
    with pytest.raises(RequestFailure) as first:
        asyncio.run(agent.run_agent("Tell me a joke.", llm_limits=LLMLimits(attempts=1)))
    estimate = first.value.metrics["llm_calls"][0]["estimated_prompt_tokens"]
    with pytest.raises(RequestFailure) as second:
        asyncio.run(agent.run_agent("Tell me a joke.", llm_limits=LLMLimits(input_tokens=estimate + 16)))
    assert second.value.category is FailureCategory.LLM_BUDGET_EXHAUSTED
    assert second.value.metrics["attempted_providers"] == ["groq"]
    assert calls == []




def test_total_provider_failure_leaves_thread_revision_unchanged(providers, app_client):
    groq, _, statuses = providers
    groq.side_effect = sdk_error(503)
    statuses.update(gemini=503, openrouter=503)

    async def run():
        async with app_client as client:
            headers = await guest_session(client)
            thread = await open_thread(client, headers)
            before = dict(stored(thread))
            response = await client.post("/api/agent/chat", headers=headers, json=turn(thread, "Tell me a joke."))
            assert response.status_code == 502
            assert response.json()["token_usage"]["attempted_providers"] == ["groq", "gemini", "openrouter"]
            assert "X-Thread-Revision" not in response.headers
            assert dict(stored(thread)) == before

    asyncio.run(run())
