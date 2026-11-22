import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.agent import agent
from backend.tests.test_thread_persistence import app_client, guest_session, open_thread, stored, turn
from backend.weather.location_models import ConfirmedLocation, Resolved, ResolutionProvenance

QUERY = "Explain the current temperature in Lisbon, Portugal."
TEMPERATURE = "Currently in Lisbon, the temperature is 21 °C."


@pytest.fixture
def observation(monkeypatch):
    place = ConfirmedLocation(name="Lisbon", country="Portugal", latitude=38.72, longitude=-9.14,
                              provenance=ResolutionProvenance(method="standalone"))
    monkeypatch.setattr(agent, "resolve_location", AsyncMock(side_effect=lambda location, **_: Resolved(query=location, location=place)))
    monkeypatch.setattr(agent, "get_current_weather", AsyncMock(return_value={"current": {"temperature_2m": 21}}))
    monkeypatch.setattr(agent, "get_hourly_forecast", AsyncMock(side_effect=AssertionError("Unexpected forecast")))


def mock_client(text):
    create = AsyncMock(return_value=SimpleNamespace(choices=[
        SimpleNamespace(message=SimpleNamespace(content=text, tool_calls=None), finish_reason="stop"),
    ]))
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


@pytest.mark.parametrize("extra", [
    "For context, this is a snapshot. The temperature there is 21 °C.",
    "In Lisbon it will be sunny tomorrow.",
    "It is safe to walk in Lisbon.",
])
def test_delivery_recovers_only_trusted_observation(observation, extra):
    client = mock_client(f"{TEMPERATURE} {extra}")
    response = asyncio.run(agent.run_agent(QUERY, client=client))
    assert "Lisbon" in response["response"] and "21 °C" in response["response"]
    assert extra not in response["response"]
    assert "detailed explanation" in response["response"]
    assert response["validation_report"]["is_trustworthy"]
    assert response["token_usage"]["answer_complete"] is False
    assert response["token_usage"]["grounded_delivery_recovery"]
    assert response["claims"][0]["location"] == "Lisbon"
    client.chat.completions.create.assert_awaited_once()


def test_supported_draft_is_delivered_without_recovery(observation):
    client = mock_client(TEMPERATURE)
    response = asyncio.run(agent.run_agent(QUERY, client=client))
    assert response["response"] == TEMPERATURE
    assert response["token_usage"]["answer_complete"]
    assert not response["token_usage"].get("grounded_delivery_recovery")


@pytest.mark.parametrize("extra", ["In Paris the temperature is 21 °C.", "In Lisbon the temperature is 99 °C."])
def test_wrong_or_contradicted_draft_never_delivered(observation, extra):
    client = mock_client(f"{TEMPERATURE} {extra}")
    response = asyncio.run(agent.run_agent(QUERY, client=client, llm_limits=agent.LLMLimits(corrections=0)))
    assert extra not in response["response"]
    assert "99" not in response["response"]
    client.chat.completions.create.assert_awaited_once()


def test_recovered_answer_preserves_server_revision(observation, app_client, monkeypatch):
    model = mock_client(TEMPERATURE + " It is safe to walk in Lisbon.")
    monkeypatch.setattr(agent, "get_groq_client", lambda **_: model)

    async def exercise():
        async with app_client as client:
            headers = await guest_session(client)
            thread = await open_thread(client, headers)
            reply = await client.post("/api/agent/chat", headers=headers, json=turn(thread, QUERY))
            assert reply.status_code == 200
            assert reply.headers["X-Thread-Revision"] == "1"
            assert reply.json()["token_usage"]["grounded_delivery_recovery"]
            assert "safe to walk" not in reply.json()["response"]
            assert stored(thread)["revision"] == 1

    asyncio.run(exercise())
    model.chat.completions.create.assert_awaited_once()


def test_recovery_does_not_drop_required_humidity(observation, monkeypatch):
    weather = {"current": {"temperature_2m": 21, "relative_humidity_2m": 64}}
    monkeypatch.setattr(agent, "get_current_weather", AsyncMock(return_value=weather))
    client = mock_client(TEMPERATURE + " Currently in Lisbon, humidity is 64%. It is safe to walk in Lisbon.")
    response = asyncio.run(agent.run_agent(
        "Explain the current temperature and humidity in Lisbon, Portugal.", client=client,
    ))
    assert not response["token_usage"]["grounded_delivery_recovery"]
    assert not response["token_usage"]["answer_complete"]
    assert "safe to walk" not in response["response"]
    assert "21 °C" not in response["response"]
    client.chat.completions.create.assert_awaited_once()


def test_current_request_does_not_deliver_mislabeled_forecast(observation):
    client = mock_client(TEMPERATURE + " In Lisbon the temperature will be 21 °C tomorrow.")
    response = asyncio.run(agent.run_agent(QUERY, client=client, llm_limits=agent.LLMLimits(corrections=0)))
    assert "tomorrow" not in response["response"]
    client.chat.completions.create.assert_awaited_once()


def test_prepared_observation_prompt_aligns_with_clause_gate(observation):
    client = mock_client(TEMPERATURE)
    asyncio.run(agent.run_agent(QUERY, client=client))
    call = client.chat.completions.create.await_args.kwargs
    instructions = call["messages"][1]["content"]
    assert "Name the city in every factual sentence." in instructions
    assert "one weather fact each" in instructions
    assert "Report current observations separately from forecasts" in instructions
    assert call["max_tokens"] == 350
    assert "tools" not in call
