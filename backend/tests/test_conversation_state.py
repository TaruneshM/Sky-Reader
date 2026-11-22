import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import TypeAdapter, ValidationError

from backend.agent.conversation_state import (
    ConversationScope, ConversationWeatherContext, ForecastWindow, LocationMention,
    apply_qualifiers, apply_resolution, begin_task, mention_from_query,
)
from backend.agent.router import WeatherRequest, parse_weather_request
from backend.weather import service
from backend.weather.location_models import (
    Ambiguous, CandidateSummary, ConfirmedLocation, LocationResolution, NotFound,
    ProviderUnavailable, Resolved, ResolutionProvenance,
)


SCOPE = ConversationScope(owner_kind="account", owner_id="42", thread_id="outing")
CANDIDATES = (
    CandidateSummary(name="Springfield", region="Illinois", provider_id=11),
    CandidateSummary(name="Springfield", region="Missouri", provider_id=12),
)


def location(name="Paris", **fields):
    return ConfirmedLocation(name=name, latitude=48.85, longitude=2.35,
                             provenance=ResolutionProvenance(method="standalone"), **fields)


def begin(query, *, state=None, task="first", **kwargs):
    return begin_task(state or ConversationWeatherContext(scope=SCOPE), SCOPE, task,
                      parse_weather_request(query), **kwargs)


def test_confirmed_location_and_unresolved_mention_are_distinct():
    original = begin("Weather in Paris, France?")
    mention = original.requested_location
    assert mention.original_text == "Paris, France"
    assert mention.normalized_name == "paris"
    assert mention.qualifiers == ("France",)
    assert mention.status == "UNRESOLVED" and original.last_confirmed_location is None
    place = location(country="France", region="Île-de-France", qualifiers=("France",), provider_id=2988507)
    confirmed = apply_resolution(original, SCOPE, "first", "location", Resolved(query=mention.query, location=place))
    assert confirmed.last_confirmed_location == confirmed.requested_location.confirmed == place
    assert confirmed.task_status == "READY"
    assert original.requested_location.status == "UNRESOLVED"
    repeat = begin("Weather in Paris, France?", state=confirmed, task="second")
    assert repeat.requested_location.confirmed is None
    assert repeat.superseded_locations[0].status == "SUPERSEDED"
    assert repeat.superseded_locations[0].confirmed == place


@pytest.mark.parametrize("fields", [{"latitude": 90.1}, {"longitude": -181}, {"latitude": float("nan")}])
def test_invalid_coordinates_are_rejected(fields):
    with pytest.raises(ValidationError):
        ConfirmedLocation.model_validate({**location().model_dump(), **fields})
    with pytest.raises(ValidationError):
        LocationMention(original_text="Paris", normalized_name="paris", status="RESOLVED")


def test_missing_optional_timezone_and_provider_id():
    place = location()
    assert place.timezone is None and place.provider_id is None
    assert place.status == "RESOLVED"
    assert place.as_legacy_place()["timezone"] is None
    with pytest.raises(ValidationError):
        ResolutionProvenance(method="geographic_hint")


@pytest.mark.parametrize("outcome", [
    NotFound(query="Missingville", reason="no_candidates"),
    ProviderUnavailable(query="Missingville", reason="timeout", retriable=True),
])
def test_failed_lookup_keeps_last_confirmed_location(outcome):
    initial = begin("Weather in Paris?")
    confirmed = apply_resolution(initial, SCOPE, "first", "location", Resolved(query="Paris", location=location()))
    new = begin("Weather in Missingville?", state=confirmed, task="second")
    failed = apply_resolution(new, SCOPE, "second", "location", outcome)
    assert failed.last_confirmed_location == confirmed.last_confirmed_location
    assert failed.requested_location.status == outcome.status
    assert failed.requested_location.confirmed is None
    assert failed.task_status == "LOCATION_UNAVAILABLE"


def test_comparison_clarification_qualifier_and_resume():
    comparison = WeatherRequest("coat_clothing", "tonight", None, False, "outing",
                                comparison=True, destinations=("Paris", "Springfield"))
    initial = begin_task(ConversationWeatherContext(scope=SCOPE), SCOPE, "compare", comparison)
    first = apply_resolution(initial, SCOPE, "compare", "first", Resolved(query="Paris", location=location()))
    assert [item.status for item in first.comparison_destinations] == ["RESOLVED", "UNRESOLVED"]
    assert first.task_status == "RESOLVING"
    waiting = apply_resolution(first, SCOPE, "compare", "second", Ambiguous(query="Springfield", candidates=CANDIDATES))
    pending = waiting.pending_clarification
    assert waiting.task_status == "AWAITING_CLARIFICATION"
    assert (pending.slot, pending.intent, pending.comparison, pending.time.period, pending.activity) == (
        "second", "coat_clothing", True, "tonight", "outing",
    )
    assert pending.confirmed_locations == (location(),)
    assert pending.candidates == CANDIDATES
    refined = apply_qualifiers(waiting, SCOPE, "compare", ("Illinois",))
    assert refined.pending_clarification == pending
    assert waiting.comparison_destinations[1].query == "Springfield"
    with pytest.raises(ValueError, match="query"):
        apply_resolution(refined, SCOPE, "compare", "second", Resolved(query="Springfield", location=location()))
    done = apply_resolution(refined, SCOPE, "compare", "second", Resolved(
        query="Springfield, Illinois", location=location("Springfield", region="Illinois", qualifiers=("Illinois",)),
    ))
    assert done.pending_clarification is None and done.task_status == "READY"
    assert done.comparison and done.intent == "coat_clothing" and done.time.period == "tonight"


def test_superseding_task_rejects_delayed_results_and_distinguishes_no_location():
    initial = begin("Weather in Springfield?")
    waiting = apply_resolution(initial, SCOPE, "first", "location", Ambiguous(query="Springfield", candidates=CANDIDATES))
    new = begin("What is the weather?", state=waiting, task="second")
    assert new.pending_clarification is None
    assert new.requested_location is None
    assert new.superseded_locations[0].status == "SUPERSEDED"
    with pytest.raises(ValueError, match="scope or task"):
        apply_resolution(new, SCOPE, "first", "location", NotFound(query="Springfield", reason="no_candidates"))


def test_time_and_activity_inheritance_and_override():
    outing = begin("I'm going out in Paris tonight. What should I wear?")
    confirmed = apply_resolution(outing, SCOPE, "first", "location", Resolved(query="Paris", location=location()))
    inherited = begin("Should I wear a jacket?", state=confirmed, task="followup", inherit_context=True)
    assert inherited.time.period == "tonight" and inherited.activity == "going out"
    assert inherited.requested_location.confirmed == location()
    tomorrow = begin("What about tomorrow?", state=confirmed, task="next", inherit_context=True)
    assert tomorrow.time.period == "tomorrow" and tomorrow.activity == "going out"
    now = begin("Is it cold right now?", state=confirmed, task="now", inherit_context=True, explicit_time=True)
    assert now.time.period == "current" and now.time.explicit


def test_versioned_serialization_and_discriminated_result():
    state = begin("Weather in Paris?")
    state = ConversationWeatherContext.model_validate({**dict(state), "last_evaluated_windows": (
        ForecastWindow(starts_at="2026-11-22T18:00", ends_at="2026-11-22T23:00", timezone="Europe/Paris",
                       location=location(timezone="Europe/Paris")),
    )})
    assert ConversationWeatherContext.model_validate_json(state.model_dump_json()) == state
    with pytest.raises(ValidationError):
        ConversationWeatherContext.model_validate({**state.model_dump(), "schema_version": 2})
    adapter = TypeAdapter(LocationResolution)
    sample = Resolved(query="Paris", location=location())
    assert adapter.validate_json(sample.model_dump_json()) == sample
    with pytest.raises(ValidationError):
        adapter.validate_python({"status": "NOT_FOUND", "query": "Paris", "reason": "no_candidates", "location": {}})
    with pytest.raises(ValidationError):
        adapter.validate_python({"status": "AMBIGUOUS", "query": "Paris", "candidates": []})


@pytest.mark.parametrize("scope", [
    ConversationScope(owner_kind="account", owner_id="42", thread_id="other"),
    ConversationScope(owner_kind="account", owner_id="101", thread_id="outing"),
    ConversationScope(owner_kind="guest", owner_id="42", thread_id="outing"),
])
def test_scope_isolation_and_no_shared_state(scope):
    baseline = ConversationWeatherContext(scope=SCOPE)
    other = ConversationWeatherContext(scope=scope)
    request = parse_weather_request("Weather in Paris?")
    first = begin_task(baseline, SCOPE, "first", request)
    with pytest.raises(ValueError, match="scope or task"):
        begin_task(first, scope, "second", request)
    with pytest.raises(ValueError, match="scope or task"):
        apply_resolution(first, scope, "first", "location", Resolved(query="Paris", location=location()))
    assert baseline.requested_location is other.requested_location is None
    assert baseline.comparison_destinations == other.comparison_destinations == ()


@pytest.fixture
def provider(monkeypatch):
    service.clear_weather_cache()
    fetch = AsyncMock()
    monkeypatch.setattr(service, "_fetch_with_retry", fetch)
    yield fetch
    service.clear_weather_cache()


def candidate(name="Paris", *, provider_id=100, latitude=48.85, region="Île-de-France"):
    return {"name": name, "id": provider_id, "latitude": latitude, "longitude": 2.35,
            "country": "France", "country_code": "FR", "admin1": region, "feature_code": "PPL"}


def test_typed_and_legacy_use_the_same_resolution_and_cache(provider):
    provider.return_value = {"results": [candidate()]}
    outcome = asyncio.run(service.resolve_location("Paris, France"))
    legacy = asyncio.run(service.geocode_location("Paris, France"))
    assert isinstance(outcome, Resolved)
    assert outcome.location.provider_id == 100 and outcome.location.timezone is None
    assert outcome.location.qualifiers == ("France",)
    assert legacy == outcome.location.as_legacy_place()
    assert set(legacy) == {"name", "latitude", "longitude", "country", "country_code", "admin1", "timezone"}
    provider.assert_awaited_once()
    assert mention_from_query("  Sa\u0303o   Paulo, Brazil ").normalized_name == "são paulo"


def test_ambiguous_and_not_found_preserve_legacy_none(provider):
    provider.return_value = {"results": [candidate(), candidate(provider_id=101, latitude=47, region="Other")]}
    result = asyncio.run(service.resolve_location("Paris"))
    assert isinstance(result, Ambiguous)
    assert {item.provider_id for item in result.candidates} == {100, 101}
    assert asyncio.run(service.geocode_location("Paris")) is None
    assert asyncio.run(service.resolve_location("Paris, Japan")).reason == "no_matching_candidates"
    provider.return_value = {}
    assert asyncio.run(service.resolve_location("Paris")).reason == "no_candidates"
    assert asyncio.run(service.resolve_location(" ")).reason == "invalid_query"


def test_provider_failure_is_typed_and_legacy_exception_is_preserved(provider):
    provider.side_effect = httpx.ConnectTimeout("provider detail must stay private")
    outcome = asyncio.run(service.resolve_location("Paris"))
    assert outcome == ProviderUnavailable(query="Paris", reason="timeout", retriable=True)
    assert "private" not in outcome.model_dump_json()
    with pytest.raises(httpx.ConnectTimeout):
        asyncio.run(service.geocode_location("Paris"))


def test_geographic_provenance_is_typed_and_never_cached_as_standalone(provider):
    provider.return_value = {"results": [
        candidate(latitude=48.95), candidate(provider_id=101, latitude=43, region="Other"),
    ]}
    anchor = location("Nearby anchor", country_code="FR")
    outcome = asyncio.run(service.resolve_location("Paris", reference=anchor))
    assert isinstance(outcome, Resolved)
    assert outcome.location.provenance.method == "geographic_hint"
    assert outcome.location.provenance.reference_name == "Nearby anchor"
    assert isinstance(asyncio.run(service.resolve_location("Paris")), Ambiguous)


def test_invalid_provider_payload_does_not_look_like_no_candidates(provider):
    provider.return_value = {"results": "bad response"}
    outcome = asyncio.run(service.resolve_location("Paris"))
    assert outcome == ProviderUnavailable(query="Paris", reason="invalid_response", retriable=True)


def test_forecast_window_must_belong_to_a_confirmed_slot():
    from backend.agent.conversation_state import record_forecast_window

    initial = begin("Weather in Paris tonight?")
    place = location(timezone="Europe/Paris")
    window = ForecastWindow(starts_at="2026-11-22T18:00", ends_at="2026-11-22T23:00",
                            timezone="Europe/Paris", location=place)
    with pytest.raises(ValueError, match="confirmed destination"):
        record_forecast_window(initial, SCOPE, "first", "location", window)
    confirmed = apply_resolution(initial, SCOPE, "first", "location", Resolved(query="Paris", location=place))
    updated = record_forecast_window(confirmed, SCOPE, "first", "location", window)
    assert updated.last_evaluated_windows == (window,)
    assert confirmed.last_evaluated_windows == ()
    with pytest.raises(ValidationError):
        ForecastWindow(starts_at="2026-11-22T23:00", ends_at="2026-11-22T18:00",
                       timezone="Europe/Paris", location=place)


def test_correcting_failed_qualifier_does_not_accumulate_contradictory_regions():
    state = begin("Weather in Springfield, USA?")
    waiting = apply_resolution(state, SCOPE, "first", "location", Ambiguous(
        query="Springfield, USA", candidates=CANDIDATES,
    ))
    refined = apply_qualifiers(waiting, SCOPE, "first", ("Texas",))
    failed = apply_resolution(refined, SCOPE, "first", "location", NotFound(
        query="Springfield, USA, Texas", reason="no_matching_candidates",
    ))
    corrected = apply_qualifiers(failed, SCOPE, "first", ("Illinois",))
    assert corrected.requested_location.query == "Springfield, USA, Illinois"
    assert corrected.pending_clarification == waiting.pending_clarification
