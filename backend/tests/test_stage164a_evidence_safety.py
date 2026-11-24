"""Safety gates for regressions discovered by the frozen Stage 1.6.3 evaluation."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.agent import agent
from backend.agent.conversation_state import ConversationScope
from backend.tests.test_deterministic_answers import completion, hourlies, weather


def client_for(draft):
    create = AsyncMock(return_value=completion(draft))
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


@pytest.mark.parametrize("draft", [
    "Tomorrow in Lyon it will be 24 °C with a 15% chance of rain.",
    "It will be sunny tomorrow.",
    "Tomorrow it will be 72.",
    "Tomorrow visibility will be 3 km.",
    "The weather assessment is HIGH risk.",
])
def test_unprepared_model_weather_claims_are_withheld_even_on_unclassified_turn(draft, weather):
    output = asyncio.run(agent.run_agent("What do you think of the plans?", client=client_for(draft)))
    assert draft not in output["response"]
    assert output["response"] == "I can help with weather. Which place and time would you like?"
    assert not output["validation_report"]["is_trustworthy"]
    assert output["token_usage"]["answer_complete"] is False
    weather[0].assert_not_called()
    weather[1].assert_not_called()


@pytest.mark.parametrize("draft", [
    "Tomorrow in Lyon the temperature will be 24 °C. Visibility in Lyon will be 3 km.",
    "Tomorrow in Lyon the temperature will be 24 °C. Tomorrow in Lyon it will be sunny.",
    "Tomorrow in Lyon the temperature will be 24 °C. Tomorrow in Rome the wind speed will be 14 km/h.",
])
def test_weather_claims_outside_prepared_evidence_are_withheld(draft, weather):
    output = asyncio.run(agent.run_agent("Explain the temperature in Lyon tomorrow in detail.", client=client_for(draft)))
    assert all(fragment not in output["response"] for fragment in ("3 km", "sunny", "Rome"))
    assert output["response"] != draft


def test_final_gate_keeps_the_existing_message_for_a_weather_request(weather):
    draft = "Tomorrow in Lyon the temperature will be 22 °C. The sky is clear."
    output = asyncio.run(agent.run_agent("Explain the temperature in Lyon tomorrow in detail.", client=client_for(draft)))
    assert output["response"] == "I couldn’t verify the weather for the requested location and period."


def test_ordinary_conversation_remains_available_without_weather_calls(weather):
    draft = "The answer to 2 + 2 is 4."
    output = asyncio.run(agent.run_agent("What is two plus two?", client=client_for(draft)))
    assert output["response"] == draft
    weather[0].assert_not_called()
    weather[1].assert_not_called()


def test_safety_comparison_and_nested_activity_location_keep_hazards(weather):
    weather[0].return_value = hourlies(weather_code=99, wind_gusts_10m=100)
    single = asyncio.run(agent.run_agent("What are the hazards for hiking in Suva tomorrow?"))
    pair = asyncio.run(agent.run_agent("Compare safety in Pune and Suva tonight."))
    assert "Suva" in single["response"] and "Thunderstorm" in single["response"]
    assert single["risk_assessment"]["overall_risk_level"] == "SEVERE"
    for city in ("Pune", "Suva"):
        assert f"Detected hazards in {city}:" in pair["response"]
        assert f"Modeled weather risk in {city} for tonight is SEVERE" in pair["response"]
    assert pair["validation_report"]["is_trustworthy"]
    weather[2].assert_not_called()


@pytest.mark.parametrize(("question", "expected"), [
    ("Will it rain and be windy in Pune tomorrow?", ("12%", "8 km/h")),
    ("What's the temperature and humidity in Pune tonight?", ("22 °C", "62%")),
    ("Is it safe to walk outside in Pune tonight, and will I need an umbrella?", ("risk", "umbrella", "12%")),
    ("Will it be colder in Pune tomorrow than tonight, and should I carry a jacket?",
     ("same forecast temperature range", "layers", "12%", "8 km/h")),
])
def test_compound_components_are_fulfilled_without_groq(question, expected, weather):
    output = asyncio.run(agent.run_agent(question))
    assert all(value in output["response"] for value in expected), output["response"]
    assert output["token_usage"]["deterministic_selected"]
    assert output["validation_report"]["is_trustworthy"]
    weather[2].assert_not_called()


def test_pair_followup_covers_requested_metrics_for_each_city(weather):
    async def ask():
        scope = ConversationScope(owner_kind="guest", owner_id="owner", thread_id="pair")
        first = await agent.run_agent("Compare Pune and Suva tomorrow.", request_scope=scope)
        return await agent.run_agent("Compare humidity and wind in both cities.", request_scope=scope,
                                     trusted_state=first["conversation_state"])

    output = asyncio.run(ask())
    for city in ("Pune", "Suva"):
        assert any(city in line and "62%" in line and "8 km/h" in line for line in output["response"].splitlines())
    assert output["token_usage"]["answer_complete"]
    assert output["validation_report"]["is_trustworthy"]
    weather[2].assert_not_called()


def test_destination_choice_keeps_verified_city_measurements_separate(weather):
    async def forecast(latitude, longitude):
        return (hourlies(temperature_2m=25, precipitation_probability=5, wind_speed_10m=10)
                if latitude == 20 else hourlies(temperature_2m=16, precipitation_probability=50, wind_speed_10m=20))

    weather[0].side_effect = forecast

    async def ask():
        scope = ConversationScope(owner_kind="guest", owner_id="owner", thread_id="choice")
        prior = await agent.run_agent("Would Pune or Suva be better tomorrow?", request_scope=scope)
        return await agent.run_agent("Which city is warmer and less rainy tomorrow?", request_scope=scope,
                                     trusted_state=prior["conversation_state"])

    output = asyncio.run(ask())
    assert "Pune has the warmer forecast range." in output["response"]
    assert "Pune has the lower peak chance of rain." in output["response"]
    assert any("Pune" in line and "25 °C" in line and "10 km/h" in line for line in output["response"].splitlines())
    assert any("Suva" in line and "16 °C" in line and "20 km/h" in line for line in output["response"].splitlines())
    assert output["validation_report"]["is_trustworthy"]
    weather[2].assert_not_called()


def test_unverified_sunset_does_not_become_fixed_clock_window(weather):
    output = asyncio.run(agent.run_agent("Will it rain and get windy in Pune after sunset?"))
    assert "local sunset time" in output["response"]
    assert "next 24 hours" not in output["response"]
    weather[0].assert_not_called()
    weather[2].assert_not_called()
