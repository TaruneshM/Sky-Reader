"""Versioned, backend-owned weather state and deterministic transitions.

Browser histories are untrusted text. A valid serialized state or provider ID is
not proof of authenticity. Only validated server resolver results may confirm a
place. Scope and task checks reject accidental cross-thread or stale updates;
a future persistence layer must authenticate ownership before loading state. Provider responses are also
inputs to validate and rank before constructing a confirmed location.
"""

import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Literal

from pydantic import Field, model_validator

if __package__ == "backend.agent":
    from backend.weather.location_models import (
        Ambiguous, CandidateSummary, ConfirmedLocation, FrozenModel, LocationResolution, Name, NotFound, Resolved,
    )
else:
    from weather.location_models import (
        Ambiguous, CandidateSummary, ConfirmedLocation, FrozenModel, LocationResolution, Name, NotFound, Resolved,
    )
from .router import WeatherRequest


def _location_key(query: str) -> str:
    return ",".join(
        unicodedata.normalize("NFC", " ".join(part.split()).casefold())
        for part in query.split(",")
    )


class ConversationScope(FrozenModel):
    owner_kind: Literal["account", "guest"]
    owner_id: Name
    thread_id: Name


class LocationMention(FrozenModel):
    original_text: Name
    normalized_name: Name
    qualifiers: tuple[Name, ...] = ()
    status: Literal["UNRESOLVED", "RESOLVED", "AMBIGUOUS", "NOT_FOUND", "PROVIDER_UNAVAILABLE", "SUPERSEDED"] = "UNRESOLVED"
    confirmed: ConfirmedLocation | None = None

    @model_validator(mode="after")
    def check_confirmation(self):
        if self.status != "SUPERSEDED" and (self.status == "RESOLVED") != (self.confirmed is not None):
            raise ValueError("Only a resolved or superseded mention can refer to a confirmed location.")
        return self

    @property
    def query(self) -> str:
        return ", ".join((self.original_text.split(",", 1)[0].strip(), *self.qualifiers))


class TimeIntent(FrozenModel):
    period: Name
    explicit: bool = False


class ForecastWindow(FrozenModel):
    starts_at: Name
    ends_at: Name
    timezone: Name
    location: ConfirmedLocation

    @model_validator(mode="after")
    def check_window(self):
        try:
            zone = ZoneInfo(self.timezone)
            start, end = map(datetime.fromisoformat, (self.starts_at, self.ends_at))
            start = start if start.tzinfo else start.replace(tzinfo=zone)
            end = end if end.tzinfo else end.replace(tzinfo=zone)
            if start > end:
                raise ValueError("Forecast window ends before it starts.")
        except ZoneInfoNotFoundError as error:
            raise ValueError("Unknown forecast timezone.") from error
        return self


Slot = Literal["location", "first", "second"]


class PendingClarification(FrozenModel):
    kind: Literal["location_qualifier", "location_not_found"] = "location_qualifier"
    task_id: Name
    intent: str | None
    comparison: bool
    safety: bool
    slot: Slot
    missing: tuple[Name, ...] = Field(min_length=1)
    base_qualifiers: tuple[Name, ...] = ()
    confirmed_locations: tuple[ConfirmedLocation, ...] = ()
    time: TimeIntent | None
    relative_baseline: str | None = None
    components: tuple[str, ...] = ()
    activity: str | None
    candidates: tuple[CandidateSummary, ...] = ()

    @model_validator(mode="after")
    def check_candidates(self):
        if self.kind == "location_qualifier" and len(self.candidates) < 2:
            raise ValueError("An ambiguous clarification requires candidate choices.")
        if self.kind == "location_not_found" and self.candidates:
            raise ValueError("A not-found clarification has no candidate choices.")
        return self


class ConversationWeatherContext(FrozenModel):
    schema_version: Literal[1] = 1
    scope: ConversationScope
    task_id: Name | None = None
    intent: str | None = None
    comparison: bool = False
    safety: bool = False
    last_confirmed_location: ConfirmedLocation | None = None
    requested_location: LocationMention | None = None
    comparison_destinations: tuple[LocationMention, ...] = Field(default=(), max_length=2)
    time: TimeIntent | None = None
    relative_baseline: str | None = None
    components: tuple[str, ...] = ()
    activity: str | None = None
    last_evaluated_windows: tuple[ForecastWindow, ...] = Field(default=(), max_length=2)
    pending_clarification: PendingClarification | None = None
    task_status: Literal["IDLE", "RESOLVING", "AWAITING_CLARIFICATION", "LOCATION_UNAVAILABLE", "READY"] = "IDLE"
    superseded_locations: tuple[LocationMention, ...] = Field(default=(), max_length=3)
    last_turn_answered_weather: bool = False


def _update(model, **fields):
    # model_copy(update=...) skips Pydantic validators.
    return type(model).model_validate({**dict(model), **fields})


def mention_from_query(query: str) -> LocationMention:
    name, *qualifiers = (" ".join(part.split()) for part in query.split(","))
    return LocationMention(original_text=query, normalized_name=_location_key(name), qualifiers=tuple(qualifiers))


def _check_scope(state: ConversationWeatherContext, scope: ConversationScope, task_id: str | None = None):
    if state.scope != scope or (task_id is not None and task_id != state.task_id):
        raise ValueError("Context scope or task does not match.")


def begin_task(
    state: ConversationWeatherContext, scope: ConversationScope, task_id: str, request: WeatherRequest,
    *, inherit_context: bool = False, explicit_time: bool | None = None,
) -> ConversationWeatherContext:
    """Adapt the legacy router request. Supply explicit_time for an explicit 'now'."""
    _check_scope(state, scope)
    if state.task_id == task_id:
        raise ValueError("A new task requires a new ID.")
    if len(request.destinations) > 2 or (request.destinations and not request.comparison):
        raise ValueError("Invalid comparison destinations.")
    requested = mention_from_query(request.location) if request.location and not request.comparison else None
    if requested is None and not request.comparison and inherit_context and state.last_confirmed_location:
        place = state.last_confirmed_location
        requested = LocationMention(original_text=place.name, normalized_name=_location_key(place.name),
                                    qualifiers=place.qualifiers, status="RESOLVED", confirmed=place)
    destinations = tuple(mention_from_query(name) for name in request.destinations)
    explicit_time = request.period != "current" if explicit_time is None else explicit_time
    time = state.time if inherit_context and not explicit_time and state.time else TimeIntent(
        period=request.period, explicit=explicit_time
    )
    previous = (state.requested_location, *state.comparison_destinations)
    return _update(
        state, task_id=task_id, intent=request.intent, comparison=request.comparison, safety=request.safety,
        requested_location=requested, comparison_destinations=destinations, time=time,
        relative_baseline=request.relative_baseline, components=request.components,
        activity=request.activity or (state.activity if inherit_context else None),
        pending_clarification=None,
        task_status="READY" if requested and requested.confirmed else "RESOLVING",
        superseded_locations=tuple(_update(item, status="SUPERSEDED") for item in previous if item),
        last_turn_answered_weather=False,
    )


def _slot_mention(state: ConversationWeatherContext, slot: Slot) -> LocationMention:
    if slot == "location" and state.requested_location:
        return state.requested_location
    index = {"first": 0, "second": 1}.get(slot)
    if index is not None and index < len(state.comparison_destinations):
        return state.comparison_destinations[index]
    raise ValueError("There is no mention for that destination slot.")


def _replace_slot(state, slot, mention, **changes):
    if slot == "location":
        return _update(state, requested_location=mention, **changes)
    index = 0 if slot == "first" else 1
    destinations = list(state.comparison_destinations)
    destinations[index] = mention
    return _update(state, comparison_destinations=tuple(destinations), **changes)


def apply_resolution(
    state: ConversationWeatherContext, scope: ConversationScope, task_id: str, slot: Slot,
    outcome: LocationResolution,
) -> ConversationWeatherContext:
    """Apply a result from the trusted resolver for the current task and query."""
    _check_scope(state, scope, task_id)
    mention = _slot_mention(state, slot)
    if _location_key(mention.query) != _location_key(outcome.query):
        raise ValueError("Resolution does not match the destination query.")
    pending = state.pending_clarification
    anchor = state.last_confirmed_location
    confirmed = outcome.location if isinstance(outcome, Resolved) else None
    if confirmed:
        anchor = confirmed
        if pending and pending.slot == slot:
            pending = None
        elif pending and confirmed not in pending.confirmed_locations:
            pending = _update(pending, confirmed_locations=(*pending.confirmed_locations, confirmed))
    elif isinstance(outcome, Ambiguous) or (isinstance(outcome, NotFound) and pending is None):
        known = tuple(
            item.confirmed for item in (state.requested_location, *state.comparison_destinations)
            if item and item.confirmed
        )
        if anchor and anchor not in known:
            known = (*known, anchor)
        pending = PendingClarification(
            task_id=task_id, intent=state.intent, comparison=state.comparison, safety=state.safety,
            kind="location_qualifier" if isinstance(outcome, Ambiguous) else "location_not_found",
            slot=slot, missing=outcome.missing_qualifiers if isinstance(outcome, Ambiguous) else ("region", "country"),
            base_qualifiers=mention.qualifiers, confirmed_locations=known,
            time=state.time, activity=state.activity, relative_baseline=state.relative_baseline, components=state.components,
            candidates=outcome.candidates if isinstance(outcome, Ambiguous) else (),
        )
    updated = _replace_slot(
        state, slot, _update(mention, status=outcome.status, confirmed=confirmed),
        last_confirmed_location=anchor, pending_clarification=pending,
    )
    if pending and pending.kind == "location_qualifier":
        status = "AWAITING_CLARIFICATION"
    else:
        locations = updated.comparison_destinations if state.comparison else (updated.requested_location,)
        if any(item and item.status in {"NOT_FOUND", "PROVIDER_UNAVAILABLE"} for item in locations):
            status = "LOCATION_UNAVAILABLE"
        elif all(item and item.confirmed for item in locations) and len(locations) == (2 if state.comparison else 1):
            status = "READY"
        else:
            status = "RESOLVING"
    return _update(updated, task_status=status)


def fill_destination(
    state: ConversationWeatherContext, scope: ConversationScope, task_id: str, query: str,
) -> ConversationWeatherContext:
    """Fill a missing single destination or replace the candidate in a pending slot."""
    _check_scope(state, scope, task_id)
    mention = mention_from_query(query)
    if state.pending_clarification:
        return _replace_slot(state, state.pending_clarification.slot, mention, task_status="RESOLVING")
    if state.comparison or state.requested_location or state.task_status != "RESOLVING":
        raise ValueError("No destination slot is waiting for a reply.")
    return _update(state, requested_location=mention)


def apply_qualifiers(
    state: ConversationWeatherContext, scope: ConversationScope, task_id: str, qualifiers: tuple[str, ...],
) -> ConversationWeatherContext:
    """Apply already parsed qualifier tokens. Keep the task pending until lookup succeeds."""
    _check_scope(state, scope, task_id)
    pending = state.pending_clarification
    if not pending or not qualifiers or any(not part.strip() or "," in part for part in qualifiers):
        raise ValueError("A pending clarification and non-empty qualifier tokens are required.")
    mention = _slot_mention(state, pending.slot)
    combined = {_location_key(part): part.strip() for part in (*pending.base_qualifiers, *qualifiers)}
    return _replace_slot(
        state, pending.slot, _update(mention, qualifiers=tuple(combined.values()), status="UNRESOLVED", confirmed=None),
        task_status="RESOLVING",
    )


def record_forecast_window(
    state: ConversationWeatherContext, scope: ConversationScope, task_id: str, slot: Slot,
    window: ForecastWindow,
) -> ConversationWeatherContext:
    """Record a window only for the confirmed place associated with this task slot."""
    _check_scope(state, scope, task_id)
    confirmed = _slot_mention(state, slot).confirmed
    if confirmed != window.location:
        raise ValueError("Forecast window does not match the confirmed destination.")
    other_windows = tuple(item for item in state.last_evaluated_windows if item.location != window.location)
    return _update(state, last_evaluated_windows=(*other_windows[-1:], window))
