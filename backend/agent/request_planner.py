"""Request-local preparation shared by the two production answer paths."""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
import re
from typing import Literal
from uuid import uuid4

import httpx

from .failures import FailureCategory, RequestFailure
from .conversation_state import (
    ConversationScope, ConversationWeatherContext, ForecastWindow, Slot, apply_qualifiers,
    apply_resolution, begin_task, fill_destination, mention_from_query, record_forecast_window,
)
from .router import WeatherRequest, _parse_turn, _requested_period, location_reply, parse_weather_request

if __package__ == "backend.agent":
    from backend.weather.location_models import ConfirmedLocation, ProviderUnavailable, Resolved
    from backend.weather.service import (
        get_current_weather, get_hourly_forecast, resolve_location, scope_hourly_forecast, summarize_scoped_forecast,
    )
else:
    from weather.location_models import ConfirmedLocation, ProviderUnavailable, Resolved
    from weather.service import (
        get_current_weather, get_hourly_forecast, resolve_location, scope_hourly_forecast, summarize_scoped_forecast,
    )


@dataclass(frozen=True)
class PlanningDecision:
    kind: Literal["location_required", "comparison_required", "same_location", "relative_time_required", "relative_place_required", "sunset_required",
                  "AMBIGUOUS", "NOT_FOUND", "PROVIDER_UNAVAILABLE"]
    query: str | None = None
    retriable: bool | None = None


@dataclass(frozen=True)
class PreparedDestination:
    slot: Slot
    query: str
    place: ConfirmedLocation
    requirement: Literal["current", "hourly"]
    period: str
    status: Literal["available", "unavailable"]
    window: ForecastWindow | None
    payload_json: str

    def data(self) -> dict:
        return json.loads(self.payload_json)


@dataclass(frozen=True)
class WeatherPlan:
    task: WeatherRequest
    state: ConversationWeatherContext
    destinations: tuple[PreparedDestination, ...] = ()
    decision: PlanningDecision | None = None
    baseline: PreparedDestination | None = None


def _slots(state):
    if state.comparison:
        return zip(("first", "second"), state.comparison_destinations)
    return (("location", state.requested_location),) if state.requested_location else ()


def _qualifier_tokens(message, pending_state):
    pending = pending_state.pending_clarification
    if not pending or not re.fullmatch(r"[\wÀ-ž][\w .,'’&-]{0,79}\.?", message.strip(), re.UNICODE):
        return ()
    value = message.strip().rstrip(".")
    if value.casefold() in {"thanks", "thank you", "okay", "ok", "yes", "no", "please"}:
        return ()
    pieces = tuple(part.strip() for part in value.split(","))
    query = next(item.normalized_name for slot, item in _slots(pending_state) if slot == pending.slot)
    if len(pieces) > 1 and mention_from_query(pieces[0]).normalized_name == query:
        return pieces[1:]
    return pieces if len(value.split()) <= 4 else ()


def _prior(state):
    anchor = state.last_confirmed_location
    if state.requested_location and state.requested_location.confirmed:
        anchor = state.requested_location.confirmed
    destinations = tuple(item.query for item in state.comparison_destinations)
    return WeatherRequest(state.intent, state.time.period if state.time else "current",
                          ", ".join((anchor.name, *anchor.qualifiers)) if anchor else None,
                          state.safety, state.activity, comparison=state.comparison, destinations=destinations,
                          relative_baseline=state.relative_baseline, components=state.components)


async def plan_weather_request(
    message: str, history=None, *, scope: ConversationScope, state: ConversationWeatherContext | None = None,
    resolver=resolve_location, current_weather=get_current_weather, hourly_forecast=get_hourly_forecast,
) -> WeatherPlan:
    """Accept trusted state only from backend code. Transcript-derived mentions are unresolved."""
    if state is not None and state.scope != scope:
        raise ValueError("Context scope does not match.")
    history = [entry for entry in (history or []) if isinstance(entry, dict)
               and isinstance(entry.get("content"), str) and entry.get("role") in {"user", "assistant"}]
    trusted = state is not None
    state = state or ConversationWeatherContext(scope=scope)
    request = _parse_turn(message, _prior(state)) if trusted else parse_weather_request(message, history)
    explicit = parse_weather_request(message)
    if state.relative_baseline and state.time and state.time.period == "current" and re.fullmatch(
        r"(?:today|tonight|tomorrow)[ .?!]*", message.strip(), re.I
    ):
        request = replace(_prior(state), period=_requested_period(message.casefold()))
    reply_location = None
    if not (explicit.intent or explicit.comparison or _requested_period(message.casefold())):
        candidate = location_reply(message)
        if candidate and (
            not explicit.location
            or explicit.location.casefold() in {part.strip().casefold() for part in candidate.split(",")}
            or explicit.location.casefold() == candidate.casefold()
        ):
            reply_location = candidate
    outcomes = {}

    async def resolve_slots(context, task, *, reference=None):
        first = None
        for slot, mention in _slots(context):
            if mention.confirmed:
                place = mention.confirmed
            else:
                kwargs = {}
                if slot == "second" and first and not mention.qualifiers:
                    kwargs["reference"] = first
                elif slot == "location" and not mention.qualifiers and task.reference_location:
                    if reference and mention_from_query(reference.name).normalized_name == mention_from_query(task.reference_location).normalized_name:
                        kwargs["reference"] = reference
                    else:
                        kwargs["reference_location"] = task.reference_location
                key = (mention.query, kwargs.get("reference"), kwargs.get("reference_location"))
                if key not in outcomes:
                    outcomes[key] = await resolver(location=mention.query, **kwargs)
                outcome = outcomes[key]
                context = apply_resolution(context, scope, context.task_id, slot, outcome)
                if not isinstance(outcome, Resolved):
                    return context, PlanningDecision(outcome.status, outcome.query,
                                                     outcome.retriable if isinstance(outcome, ProviderUnavailable) else None)
                place = outcome.location
            if slot == "first":
                first = place
        return context, None

    if reply_location and not trusted and history and not request.destinations:
        # Recheck the previous user task, never an assistant's account of its outcome.
        last_user = next((index for index in range(len(history) - 1, -1, -1)
                          if history[index].get("role") == "user"), None)
        if last_user is not None:
            prior = parse_weather_request(history[last_user]["content"], history[:last_user])
            if (prior.intent or prior.location or prior.destinations) and not (prior.safety and prior.comparison):
                previous = begin_task(state, scope, uuid4().hex, prior)
                rechecked, _ = await resolve_slots(previous, prior)
                if rechecked.pending_clarification or (prior.intent and not prior.comparison and not prior.location):
                    state = rechecked

    waiting_for_location = state.task_id and state.task_status == "RESOLVING" and state.intent and not (
        state.requested_location or state.comparison
    )
    qualifiers = _qualifier_tokens(message, state) if reply_location and state.pending_clarification else ()
    if reply_location and (waiting_for_location or (state.pending_clarification and (qualifiers or "," in reply_location))):
        request = _prior(state)
        if waiting_for_location or "," in reply_location:
            state = fill_destination(state, scope, state.task_id, reply_location)
        else:
            state = apply_qualifiers(state, scope, state.task_id, qualifiers)
        request = replace(request, location=state.requested_location.query if state.requested_location else None,
                          destinations=tuple(item.query for item in state.comparison_destinations))
        reference = state.last_confirmed_location
    elif reply_location and not request.comparison and "," in reply_location:
        if trusted and state.last_confirmed_location:
            request = replace(_prior(state), intent=state.intent or "current_weather", location=reply_location,
                              comparison=False, destinations=())
        else:
            request = WeatherRequest("current_weather", "current", reply_location, False, None)
        state = begin_task(state, scope, uuid4().hex, request, inherit_context=bool(state.last_confirmed_location))
        reference = state.last_confirmed_location
    else:
        named_weather = request.location and re.search(
            r"\b(weather|forecast|temperature|rain|wind|humidity)\b", message, re.I
        )
        if not (request.intent or request.comparison or named_weather or
                (request.location and "forecast" in request.components)):
            return WeatherPlan(request, state)
        reference = state.last_confirmed_location
        if not request.intent and not request.comparison and "forecast" in request.components:
            request = replace(request, intent="current_weather")
        inherit = trusted and not explicit.location and not explicit.comparison and not request.needs_location
        fresh_request = replace(request, location=None) if inherit and not request.comparison else request
        state = begin_task(state, scope, uuid4().hex, fresh_request, inherit_context=inherit,
                           explicit_time=_requested_period(message.casefold()) is not None or not trusted)
        request = replace(request, period=state.time.period, activity=state.activity,
                          location=state.requested_location.query if state.requested_location else None)

    if re.search(r"\b(?:after|before|at) (?:sunset|sunrise)\b", message, re.I):
        return WeatherPlan(request, state, decision=PlanningDecision("sunset_required"))
    if "clothing" in request.components and re.search(r"\b(?:colder|warmer|cooler|hotter)\b", message, re.I) and not request.relative_baseline:
        return WeatherPlan(request, state, decision=PlanningDecision("relative_time_required"))
    if request.relative_baseline and request.period == "current" and _requested_period(message.casefold().split(" than ")[0]) is None:
        return WeatherPlan(request, state, decision=PlanningDecision("relative_time_required"))
    if re.search(r"\bthan\b.*\b(?:place|city|destination|location)\b", message, re.I):
        return WeatherPlan(request, state, decision=PlanningDecision("relative_place_required"))
    if request.comparison and len(request.destinations) != 2:
        return WeatherPlan(request, state, decision=PlanningDecision("comparison_required"))
    if request.intent and not request.comparison and not state.requested_location:
        return WeatherPlan(request, state, decision=PlanningDecision("location_required"))

    state, decision = await resolve_slots(state, request, reference=reference)
    if decision:
        return WeatherPlan(request, state, decision=decision)

    slots = tuple(_slots(state))
    identities = {(item.confirmed.latitude, item.confirmed.longitude) for _, item in slots}
    if len(identities) != len(slots):
        return WeatherPlan(request, state, decision=PlanningDecision("same_location"))

    prepared = []
    baseline = None
    planning_time = datetime.now(timezone.utc).isoformat()
    for slot, item in slots:
        place = item.confirmed
        period = request.period
        requested_forecast = bool(re.search(r"\bforecast\b", message, re.I)) and _requested_period(message.casefold()) != "current"
        forecast = request.comparison or request.safety or request.relative_baseline or requested_forecast or bool(
            {"rain", "umbrella", "safety"} & set(request.components)
        ) or period != "current" or request.intent in {
            "rain_check", "umbrella", "morning_walk", "coat_clothing",
        }
        if forecast and period == "current":
            now = _requested_period(message.casefold()) == "current"
            period = "next_1h" if request.comparison or request.safety or now else "next_24h"
        fetch = hourly_forecast if forecast else current_weather
        try:
            raw = await fetch(latitude=place.latitude, longitude=place.longitude)
            if not isinstance(raw, dict) or raw.get("error") or any(
                key in raw and not isinstance(raw[key], dict) for key in ("current", "hourly")
            ):
                raise RequestFailure(FailureCategory.WEATHER_PROVIDER_UNAVAILABLE)
        except (httpx.HTTPError, json.JSONDecodeError):
            raise RequestFailure(FailureCategory.WEATHER_PROVIDER_UNAVAILABLE) from None
        window = None
        if forecast:
            raw = {**raw, "timezone": raw.get("timezone") or place.timezone}
            observed_time = raw.get("current", {}).get("time")
            clock = observed_time or (planning_time if raw["timezone"] else None)
            if request.relative_baseline and not request.comparison:
                baseline_scope = scope_hourly_forecast(raw, request.relative_baseline, clock)
                baseline = PreparedDestination(
                    slot, item.query, place, "hourly", request.relative_baseline,
                    "available" if baseline_scope["hourly"].get("time") else "unavailable", None,
                    json.dumps(baseline_scope, ensure_ascii=False),
                )
            raw = scope_hourly_forecast(raw, period, clock)
            times = raw["hourly"].get("time", [])
            if times and raw["timezone"]:
                window = ForecastWindow(starts_at=times[0], ends_at=times[-1], timezone=raw["timezone"], location=place)
                state = record_forecast_window(state, scope, state.task_id, slot, window)
            available = bool(times)
        else:
            available = bool(raw.get("current"))
        prepared.append(PreparedDestination(
            slot, item.query, place, "hourly" if forecast else "current", period,
            "available" if available else "unavailable", window, json.dumps(raw, ensure_ascii=False),
        ))
    return WeatherPlan(request, state, tuple(prepared), baseline=baseline)
