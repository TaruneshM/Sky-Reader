import asyncio
import json
import logging
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.agent import agent, executor
from backend.agent.conversation_state import ConversationScope, ConversationWeatherContext
from backend.agent.router import location_reply, parse_weather_request
from backend.weather import service
from backend.weather.location_models import Ambiguous, Resolved


OUTING = "i ma going out in bhimtal tonight wht type of cloths should i wear"
ALTERNATIVE = "ok soo i was also thinking abt the tanakpur any thoughts on that"
HISTORY = [{"role": "user", "content": OUTING}]
BHIMTAL = (29.35, 79.5667)
TANAKPUR = (29.074, 80.11139)
KHATIMA = (28.92, 79.97)


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
        "khatima": [location(1266813, "Khatima", KHATIMA, "IN", "Uttarakhand")],
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
        temperature = {BHIMTAL: 12, TANAKPUR: 26, KHATIMA: 22}[(latitude, longitude)]
        start = datetime(2026, 11, 21)
        return {
            "timezone": "Asia/Kolkata",
            "current": {"time": "2026-11-21T16:30"},
            "hourly": {
                "time": [(start + timedelta(hours=hour)).isoformat(timespec="minutes") for hour in range(48)],
                "temperature_2m": [temperature] * 48,
                "precipitation_probability": [12] * 48,
                "precipitation": [0] * 48,
                "wind_speed_10m": [8] * 48,
                "weather_code": [0] * 48,
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
    assert "decision=NOT_FOUND" in caplog.text
    assert "Missingville" not in caplog.text
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
    output = asyncio.run(agent.run_agent("What about Tanakpur tonight? Give the temperature in detail.", HISTORY, client=client))
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
    client.chat.completions.create.assert_not_called()
    assert output["validation_report"]["is_trustworthy"]
    citation_ids = [row["supporting_evidence_ids"][0] for row in output["validation_report"]["validation_results"]]
    assert citation_ids[0].startswith("29.35,79.5667:")
    assert any(value.startswith("29.074,80.11139:") for value in citation_ids)


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


def test_groq_comparison_reuses_one_prepared_packet_per_city(provider):
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
    output = asyncio.run(agent.run_agent(EXACT_COMPARISON + " Explain in detail.", [{"role": "user", "content": EXACT_OUTING}], client=client))
    for call_args in client.chat.completions.create.call_args_list:
        assert "tools" not in call_args.kwargs
        messages = call_args.kwargs["messages"]
        packets = [message["content"] for message in messages
                   if message["content"].startswith("Verified planned weather data.")]
        assert len(packets) == 1
        payload = json.loads(packets[0][packets[0].index("{"):])
        assert [item["place"][0] for item in payload["weather"]] == ["Bhimtal", "Tanakpur"]
        assert payload["weather"][1]["local_window"][0] == "2026-11-21T18:00"
        assert all(message["role"] != "tool" for message in messages)
    assert output["token_usage"]["suppressed_tool_requests"] == 5
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


def test_tanakpur_requires_a_qualifier_without_context(provider):
    places, _, _ = provider
    places["tanakpur"].append(dict(places["tanakpur"][2], id=987))
    bare = asyncio.run(service.resolve_location("Tanakpur"))
    assert isinstance(bare, Ambiguous)
    assert len(bare.candidates) == 5  # Duplicate coordinates are already collapsed by the ranker.
    qualified = asyncio.run(service.resolve_location("Tanakpur, Uttarakhand, India"))
    assert isinstance(qualified, Resolved)
    assert (qualified.location.latitude, qualified.location.longitude) == TANAKPUR
    hinted = asyncio.run(service.resolve_location("Tanakpur", reference_location="Khatima"))
    assert isinstance(hinted, Resolved)
    assert hinted.location.provenance.method == "geographic_hint"
    assert (hinted.location.latitude, hinted.location.longitude) == TANAKPUR
    assert isinstance(asyncio.run(service.resolve_location("Tanakpur")), Ambiguous)


@pytest.mark.parametrize("reply", ["Uttarakhand", "Tanakpur, Uttarakhand"])
def test_tanakpur_options_and_qualifier_preserve_the_outing(provider, reply):
    scope = ConversationScope(owner_kind="guest", owner_id="test", thread_id="outing")
    question = "I'm going out in Tanakpur tonight. What should I wear?"
    waiting = asyncio.run(agent.run_agent(question, api_key="", request_scope=scope))
    state = waiting["conversation_state"]
    text = waiting["response"]
    assert "Tanakpur, Uttarakhand, India" in text
    assert "Tanakpur, Bihar, India" in text
    assert text.count("Tanakpur, Sudurpashchim Pradesh, Nepal") == 1
    assert "region" in text

    answer = asyncio.run(agent.run_agent(reply, api_key="", request_scope=scope, trusted_state=state))
    updated = answer["conversation_state"]
    assert updated.pending_clarification is None
    assert updated.task_id == state.task_id
    assert (updated.intent, updated.time.period, updated.activity, updated.components) == (
        state.intent, "tonight", "going out", state.components,
    )
    assert "26 °C" in answer["response"] and "tonight" in answer["response"]
    assert answer["validation_report"]["is_trustworthy"]


def test_far_away_tanakpur_reference_stays_ambiguous(provider):
    places, _, _ = provider
    places["faraway"] = [location(3, "Faraway", (12.97, 77.59), "IN", "Karnataka")]
    result = asyncio.run(service.resolve_location("Tanakpur", reference_location="Faraway"))
    assert isinstance(result, Ambiguous)


@pytest.mark.parametrize("acknowledgement", ["nice", "Cool!", "great", "lol", "ok", "hmm"])
def test_acknowledgement_is_not_a_place_reply(acknowledgement):
    assert location_reply(acknowledgement) is None


def test_completed_outing_does_not_hint_a_bare_or_explicit_tanakpur_request(provider):
    scope = ConversationScope(owner_kind="guest", owner_id="test", thread_id="outing")
    initial = asyncio.run(agent.run_agent(OUTING, api_key="", request_scope=scope))
    state = initial["conversation_state"]
    assert state.last_turn_answered_weather
    _, search, forecast = provider
    for question in ("Tanakpur", "What's the weather in Tanakpur?"):
        response = asyncio.run(agent.run_agent(question, api_key="", request_scope=scope, trusted_state=state))
        assert response["token_usage"]["failure_category"] == "geocoding_ambiguity"
        assert "Tanakpur, Uttarakhand, India" in response["response"]
        assert response["conversation_state"].last_confirmed_location.name == "Bhimtal"
        assert search.await_args.args[1]["name"] == "Tanakpur"
    forecast.assert_awaited_once()


def test_bare_switch_preserves_the_verified_outing_task(provider):
    scope = ConversationScope(owner_kind="guest", owner_id="test", thread_id="outing")
    initial = asyncio.run(agent.run_agent(OUTING, api_key="", request_scope=scope))
    state = initial["conversation_state"]
    client = client_for()
    response = asyncio.run(agent.run_agent("khatima", client=client, request_scope=scope, trusted_state=state))
    updated = response["conversation_state"]
    assert updated.task_id != state.task_id
    assert (updated.intent, updated.time, updated.activity, updated.components) == (
        state.intent, state.time, state.activity, state.components,
    )
    assert "Khatima" in response["response"] and "22 °C" in response["response"] and "tonight" in response["response"]
    assert response["validation_report"]["is_trustworthy"]
    provider[2].assert_awaited_with(latitude=KHATIMA[0], longitude=KHATIMA[1])
    client.chat.completions.create.assert_not_called()


def test_intervening_model_assisted_turn_does_not_leave_bare_switch_enabled(provider):
    scope = ConversationScope(owner_kind="guest", owner_id="test", thread_id="outing")
    initial = asyncio.run(agent.run_agent(OUTING, api_key="", request_scope=scope))
    client = client_for(completion("Here is a joke."), completion("What would you like to know about Khatima?"))
    acknowledgement = asyncio.run(agent.run_agent(
        "Tell me a joke.", client=client, request_scope=scope, trusted_state=initial["conversation_state"],
    ))
    assert acknowledgement["response"] == "Here is a joke."
    assert not acknowledgement["conversation_state"].last_turn_answered_weather
    reply = asyncio.run(agent.run_agent(
        "khatima", client=client, request_scope=scope, trusted_state=acknowledgement["conversation_state"],
    ))
    assert reply["response"] == "What would you like to know about Khatima?"
    _, search, forecast = provider
    search.assert_awaited_once()
    forecast.assert_awaited_once()


SMALL_TALK_REPLY = "Hello! I’m here if you have a weather question."


@pytest.mark.parametrize("prompt", [
    "nice", "coool!", "thanks", "thank yooou", "OK", "hii", "hellooo there", "Good morning!", "byeee",
])
def test_small_talk_answers_without_planning_claims_or_model(prompt, monkeypatch):
    planner = AsyncMock()
    monkeypatch.setattr(agent, "plan_weather_request", planner)
    model = client_for()
    result = asyncio.run(agent.run_agent(prompt, client=model))
    assert result["response"] == SMALL_TALK_REPLY
    assert result["claims"] == []
    assert result["validation_report"] is None
    assert result["token_usage"]["llm_calls_attempted"] == 0
    planner.assert_not_awaited()
    model.chat.completions.create.assert_not_awaited()


def test_nice_has_the_same_reply_in_fresh_and_verified_delhi_threads(monkeypatch):
    scope = ConversationScope(owner_kind="guest", owner_id="test", thread_id="delhi")
    fresh = ConversationWeatherContext(scope=scope)
    model = client_for()
    geocoder = AsyncMock(side_effect=lambda location: Resolved(query=location, location={
        "name": location.split(",")[0], "latitude": 28.61, "longitude": 77.21,
        "provenance": {"method": "standalone"},
    }))
    current = AsyncMock(return_value={"current": {"temperature_2m": 21, "weather_code": 0}})
    monkeypatch.setattr(agent, "resolve_location", geocoder)
    monkeypatch.setattr(agent, "get_current_weather", current)

    initial = asyncio.run(agent.run_agent(
        "What's the weather in Delhi?", client=model, request_scope=scope, trusted_state=fresh,
    ))
    delhi = initial["conversation_state"]
    assert delhi.last_turn_answered_weather and delhi.last_confirmed_location.name == "Delhi"
    assert initial["validation_report"]["is_trustworthy"]

    for state in (fresh, delhi):
        reply = asyncio.run(agent.run_agent("nice", client=model, request_scope=scope, trusted_state=state))
        assert reply["response"] == SMALL_TALK_REPLY
        assert reply["conversation_state"] is state
        assert reply["claims"] == []
        assert reply["token_usage"]["llm_calls_attempted"] == 0

    # The title-case destination still follows the normal switch path.
    switched = asyncio.run(agent.run_agent("Nice?", client=model, request_scope=scope, trusted_state=delhi))
    assert switched["conversation_state"].last_confirmed_location.name == "Nice"
    assert geocoder.await_count == current.await_count == 2
    model.chat.completions.create.assert_not_awaited()


@pytest.mark.parametrize("prompt", ["Nice", "Nice, France", "What's the weather in Nice?", "Hilo", "São Paulo"])
def test_small_talk_does_not_match_place_requests(prompt):
    assert not agent.is_small_talk(prompt)


def test_unverified_weather_in_chit_chat_is_withheld_with_neutral_message():
    model = client_for(completion("Here’s a joke. It is 17 °C in Delhi."))
    answer = asyncio.run(agent.run_agent("Tell me a joke.", client=model))
    assert answer["response"] == "I can help with weather. Which place and time would you like?"
    assert answer["claims"] == []
    assert answer["token_usage"]["answer_complete"] is False
    model.chat.completions.create.assert_awaited_once()
