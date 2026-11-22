import asyncio
import json
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.agent import agent
from backend.agent.conversation_state import ConversationScope
from backend.agent.request_planner import plan_weather_request
from backend.weather.location_models import (
    Ambiguous, CandidateSummary, ConfirmedLocation, NotFound, ProviderUnavailable, Resolved, ResolutionProvenance,
)

SCOPE = ConversationScope(owner_kind="account", owner_id="42", thread_id="outing")


def place(name, coordinates, zone="Asia/Kolkata", region=None):
    return ConfirmedLocation(
        name=name, latitude=coordinates[0], longitude=coordinates[1], timezone=zone, region=region,
        provenance=ResolutionProvenance(method="standalone"),
    )


PLACES = {
    "jharsuguda": place("Jharsuguda", (21.86, 84.02), region="Odisha"),
    "sambalpur": place("Sambalpur", (21.46, 83.98), region="Odisha"),
    "bhimtal": place("Bhimtal", (29.35, 79.56)),
    "tanakpur": place("Tanakpur", (29.07, 80.11), region="Uttarakhand"),
    "paris, france": place("Paris", (48.85, 2.35), "Europe/Paris", "Île-de-France"),
    "paris, texas": place("Paris", (33.66, -95.55), "America/Chicago", "Texas"),
    "tokyo": place("Tokyo", (35.68, 139.69), "Asia/Tokyo"),
}
CANDIDATES = (
    CandidateSummary(name="Sambalpur", region="Odisha"),
    CandidateSummary(name="Sambalpur", region="Chhattisgarh"),
)


@pytest.fixture
def providers():
    async def resolve(location, reference=None, **_kwargs):
        key = location.casefold()
        if key == "sambalpur, odisha":
            return Resolved(query=location, location=PLACES["sambalpur"])
        if key == "sambalpur" and reference != PLACES["jharsuguda"]:
            return Ambiguous(query=location, candidates=CANDIDATES)
        if key == "offline":
            return ProviderUnavailable(query=location, reason="timeout", retriable=True)
        if key not in PLACES:
            return NotFound(query=location, reason="no_candidates")
        return Resolved(query=location, location=PLACES[key])

    async def hourly(latitude, longitude):
        start = datetime(2026, 11, 21)
        return {"current": {"time": "2026-11-21T20:00+00:00"}, "hourly": {
            "time": [(start + timedelta(hours=offset)).isoformat(timespec="minutes") for offset in range(48)],
            "temperature_2m": [round(latitude)] * 48,
            "wind_speed_10m": [5] * 48, "precipitation_probability": [0] * 48,
            "precipitation": [0] * 48, "weather_code": [0] * 48,
        }}

    return {
        "resolver": AsyncMock(side_effect=resolve),
        "hourly_forecast": AsyncMock(side_effect=hourly),
        "current_weather": AsyncMock(return_value={"current": {"temperature_2m": 20}}),
    }


def plan(message, providers, **kwargs):
    return asyncio.run(plan_weather_request(message, scope=SCOPE, **providers, **kwargs))


@pytest.mark.parametrize("query,history,names", [
    ("Jharsuguda vs Sambalpur tonight", [], ("Jharsuguda", "Sambalpur")),
    ("Bhimtal or Tanakpur tonight", [], ("Bhimtal", "Tanakpur")),
    ("I was thinking about Tanakpur. Which place would be better tonight?", [
        {"role": "user", "content": "I'm going out in Bhimtal tonight. What should I wear?"},
    ], ("Bhimtal", "Tanakpur")),
])
def test_comparison_uses_one_weather_fetch_per_destination(query, history, names, providers):
    result = plan(query, providers, history=history)
    assert result.decision is None
    assert tuple(item.place.name for item in result.destinations) == names
    assert all(item.window.starts_at == "2026-11-22T18:00" for item in result.destinations)
    assert result.task.period == "tonight"
    assert providers["hourly_forecast"].await_count == providers["resolver"].await_count == 2
    providers["current_weather"].assert_not_called()
    assert providers["resolver"].await_args_list[1].kwargs["reference"] == result.destinations[0].place
    result.destinations[0].data()["hourly"]["time"].clear()
    assert len(result.destinations[0].data()["hourly"]["time"]) == 6


def test_qualifier_only_reply_reuses_confirmed_comparison_slot(providers):
    # A full leading comparison also works without any transcript.
    waiting = plan("Compare Bhimtal and Sambalpur tonight", providers)
    assert waiting.decision.kind == "AMBIGUOUS"
    assert waiting.state.pending_clarification.slot == "second"
    assert waiting.state.comparison_destinations[0].confirmed == PLACES["bhimtal"]
    assert waiting.state.task_status == "AWAITING_CLARIFICATION"
    resolved = plan("odisha", providers, state=waiting.state)
    assert resolved.state.task_id == waiting.state.task_id
    assert resolved.state.pending_clarification is None
    assert resolved.task.period == "tonight"
    assert [item.query for item in resolved.destinations] == ["Bhimtal", "Sambalpur, odisha"]
    assert providers["resolver"].await_args.kwargs == {"location": "Sambalpur, odisha"}
    assert providers["hourly_forecast"].await_count == 2


def test_stateless_qualifier_rechecks_prior_user_task_only(providers):
    history = [None, {"role": "user"}, {"role": "user", "content": "Weather in Sambalpur tonight?"},
               {"role": "assistant", "content": "Assistant prose does not confirm any place."}]
    result = plan("Sambalpur, Odisha", providers, history=history)
    assert result.decision is None and result.destinations[0].place.region == "Odisha"
    assert result.task.period == "tonight"
    assert [entry.kwargs["location"] for entry in providers["resolver"].await_args_list] == [
        "Sambalpur", "Sambalpur, Odisha",
    ]


def test_trusted_anchor_survives_failed_lookup_and_long_history(providers):
    first = plan("Weather in Bhimtal tonight?", providers)
    failed = plan("Weather in Missingville?", providers, state=first.state)
    assert failed.decision.kind == "NOT_FOUND"
    assert failed.state.last_confirmed_location == PLACES["bhimtal"]
    result = plan("Is it colder there tomorrow?", providers, state=failed.state, history=[
        {"role": "user", "content": "Thanks"} for _ in range(40)
    ])
    assert result.destinations[0].place == PLACES["bhimtal"]
    assert result.task.period == "tomorrow"
    assert providers["resolver"].await_count == 2


def test_absent_history_and_provider_failure_have_distinct_decisions(providers):
    missing = plan("What about tomorrow?", providers)
    assert missing.decision.kind == "location_required"
    unavailable = plan("Weather in Offline?", providers)
    assert unavailable.decision.kind == "PROVIDER_UNAVAILABLE" and unavailable.decision.retriable
    assert unavailable.state.pending_clarification is None
    providers["hourly_forecast"].assert_not_called()


def test_explicit_qualified_same_name_places_are_separate_and_use_local_clocks(providers):
    result = plan("Paris, France vs Paris, Texas tonight", providers)
    france, texas = result.destinations
    assert france.window.starts_at == "2026-11-21T21:00"
    assert texas.window.starts_at == "2026-11-21T18:00"
    assert france.window.timezone != texas.window.timezone
    assert france.data()["hourly"]["temperature_2m"][0] != texas.data()["hourly"]["temperature_2m"][0]
    assert all("reference" not in args.kwargs for args in providers["resolver"].await_args_list)


@pytest.mark.parametrize("kind,owner,thread", [("account", "99", "outing"), ("account", "42", "other"), ("guest", "42", "outing")])
def test_foreign_state_rejected_before_provider_access(kind, owner, thread, providers):
    first = plan("Weather in Bhimtal?", providers)
    with pytest.raises(ValueError, match="scope"):
        asyncio.run(plan_weather_request(
            "What about tomorrow?", scope=ConversationScope(owner_kind=kind, owner_id=owner, thread_id=thread),
            state=first.state, **providers,
        ))
    assert providers["resolver"].await_count == 1


def test_groq_and_deterministic_share_forecast_evidence_and_block_tool_drift(monkeypatch, providers):
    monkeypatch.setattr(agent, "resolve_location", providers["resolver"])
    monkeypatch.setattr(agent, "get_hourly_forecast", providers["hourly_forecast"])
    query = "Compare Bhimtal and Tanakpur tonight."
    baseline = asyncio.run(agent.run_agent(query, api_key="", request_scope=SCOPE))
    tool = SimpleNamespace(id="wrong", function=SimpleNamespace(
        name="get_hourly_forecast", arguments=json.dumps({"latitude": 0, "longitude": 0}),
    ))
    def reply(text=None, calls=None):
        return SimpleNamespace(usage=None, choices=[SimpleNamespace(
            message=SimpleNamespace(content=text, tool_calls=calls),
        )])

    model = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(side_effect=[
        reply(calls=[tool]), reply("Bhimtal tonight will be 99 °C."), reply("Bhimtal tonight will be 99 °C."),
    ]))))
    generated = asyncio.run(agent.run_agent(query, client=model, request_scope=SCOPE))
    assert baseline["response"] == generated["response"]
    assert baseline["validation_report"]["is_trustworthy"]
    assert generated["conversation_state"].last_evaluated_windows == baseline["conversation_state"].last_evaluated_windows
    assert baseline["explanation"]["supporting_evidence"] == generated["explanation"]["supporting_evidence"]
    assert providers["hourly_forecast"].await_count == 4


def test_explicit_new_task_supersedes_pending_qualifier(providers):
    previous = plan("Weather in Sambalpur tonight?", providers)
    assert previous.state.pending_clarification
    new = plan("Weather in Tokyo tomorrow?", providers, state=previous.state)
    assert new.state.pending_clarification is None
    assert new.state.task_id != previous.state.task_id
    assert new.state.superseded_locations[0].normalized_name == "sambalpur"
    assert new.destinations[0].place == PLACES["tokyo"]
    assert new.destinations[0].period == "tomorrow"
