"""Offline evaluation. Run python -m backend.evaluation.stage163.run --output /tmp/stage163.json."""
import argparse
import asyncio
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timedelta
import json
from math import ceil
from pathlib import Path
import re
from statistics import median
from time import perf_counter
from types import SimpleNamespace
from unittest.mock import patch
import unicodedata

import httpx
from groq import RateLimitError

from backend.agent import agent
from backend.agent.conversation_state import ConversationScope
from backend.agent.failures import RequestFailure
from backend.agent.router import parse_weather_request
from backend.evidence.hallucination_controller import HallucinationController
from backend.weather import service

from .cases import CASES


CATALOG = {
    "Lisbon": ("Portugal", "PT", "Europe/Lisbon"), "Zürich": ("Switzerland", "CH", "Europe/Zurich"),
    "Osaka": ("Japan", "JP", "Asia/Tokyo"), "Recife": ("Brazil", "BR", "America/Recife"),
    "Kigali": ("Rwanda", "RW", "Africa/Kigali"), "Reykjavík": ("Iceland", "IS", "Atlantic/Reykjavik"),
    "Accra": ("Ghana", "GH", "Africa/Accra"), "Lyon": ("France", "FR", "Europe/Paris"),
    "Muscat": ("Oman", "OM", "Asia/Muscat"), "Cebu": ("Philippines", "PH", "Asia/Manila"),
    "Suva": ("Fiji", "FJ", "Pacific/Fiji"), "Doha": ("Qatar", "QA", "Asia/Qatar"),
    "Qaşr-e Shirin": ("Iran", "IR", "Asia/Tehran"),
    "São José dos Campos": ("Brazil", "BR", "America/Sao_Paulo"),
}


def key(value):
    return "".join(char for char in unicodedata.normalize("NFD", value.casefold())
                   if unicodedata.category(char) != "Mn")


def candidate(name, country, code, tz, number):
    return dict(id=number, name=name, country=country, country_code=code, timezone=tz,
                latitude=10 + number, longitude=20 + number, feature_code="PPL", population=500_000)


CATALOG_ROWS = [candidate(name, *metadata, index) for index, (name, metadata) in enumerate(CATALOG.items(), 1)]
CATALOG_ROWS += [
    candidate("Córdoba", "Argentina", "AR", "America/Argentina/Cordoba", 30),
    candidate("Córdoba", "Spain", "ES", "Europe/Madrid", 31),
]
START = datetime(2026, 7, 14)
HOURS = [(START + timedelta(hours=index)).isoformat(timespec="minutes") for index in range(48)]
HAZARDS = {"storm", "flood", "gust", "heat", "fog", "multi", "partial_storm", "contradiction"}
SAFE = re.compile(r"postpon|avoid|shelter|slow down|indoors|check local alerts|caution", re.I)
POSITIVE = re.compile(r"\b(?:safe to (?:go|walk|drive|travel)|no precautions required|go ahead)\b", re.I)


def forecast(fixture, second, timezone):
    hourly = dict(time=HOURS, temperature_2m=[28 if second else 24] * 48,
                  precipitation_probability=[35 if second else 15] * 48,
                  precipitation=[0] * 48, wind_speed_10m=[19 if second else 14] * 48,
                  wind_gusts_10m=[25] * 48, weather_code=[2] * 48, relative_humidity_2m=[64] * 48)
    override = {
        "storm": {"weather_code": 95}, "flood": {"precipitation": 25}, "gust": {"wind_gusts_10m": 100},
        "heat": {"temperature_2m": 45}, "fog": {"weather_code": 45},
        "multi": {"weather_code": 99, "wind_gusts_10m": 100},
        "partial_storm": {"weather_code": 95, "temperature_2m": None, "precipitation": None},
        "contradiction": {"weather_code": 95, "precipitation_probability": 0, "precipitation": 0},
        "no_temperature": {"temperature_2m": None}, "no_rain": {"precipitation_probability": None, "precipitation": None},
        "cold": {"temperature_2m": 10},
    }.get(fixture, {})
    hourly.update({field: [value] * 48 for field, value in override.items()})
    if fixture == "cooler":
        hourly["temperature_2m"] = [24] * 24 + [15] * 24
    if fixture == "partial_wind":
        hourly["wind_speed_10m"] = [14] * 20 + [None] * 28
    if fixture == "short":
        hourly = {field: array[:24] for field, array in hourly.items()}
    current = dict(time=HOURS[14], temperature_2m=21, weather_code=2, relative_humidity_2m=64, wind_speed_10m=11)
    return dict(current=current, hourly=hourly, timezone=timezone)


def check_requirement(requirement, answer):
    if requirement == "caution":
        return bool(SAFE.search(answer)) and not POSITIVE.search(answer)
    if requirement == "incomplete":
        return "incomplete" in answer or "don’t have complete" in answer
    return requirement.removeprefix("hazard:").casefold() in answer.casefold()


NUMBER = re.compile(r"(-?\d+(?:\.\d+)?)\s*(°C|%|km/h|mm)(?![\w/])", re.I)


def fixture_measurements(case, text):
    """Independently check numeric literals against fixture values and the labeled window."""
    if not NUMBER.search(text):
        return None
    if not case.places:
        return False
    fields = {
        "°c": ("temperature_2m",), "%": ("precipitation_probability", "relative_humidity_2m"),
        "km/h": ("wind_speed_10m", "wind_gusts_10m"), "mm": ("precipitation",),
    }
    answers = []
    for line in text.splitlines():
        numbers = NUMBER.findall(line)
        if not numbers:
            continue
        matching = [place for place in case.places if key(place) in key(line)] or list(case.places)
        for numeric, unit in numbers:
            candidates = set()
            for place in matching:
                raw = forecast(case.fixture, len(case.places) == 2 and place == case.places[1], None)
                window = case.window
                if "than" in case.message.casefold():
                    if "tonight" in line.casefold():
                        window = "tonight"
                    elif "tomorrow" in line.casefold():
                        window = "tomorrow"
                for field in fields[unit.casefold()]:
                    if window == "current":
                        candidates.add(raw["current"].get(field))
                    else:
                        start = 24 if window.startswith("tomorrow") else 18 if window == "tonight" else 0
                        stop = 48 if window.startswith("tomorrow") else 24
                        candidates.update(raw["hourly"].get(field, [])[start:stop])
            answers.append(float(numeric) in candidates)
    return all(answers)


class Fixture:
    def __init__(self, case):
        self.case = case
        self.warming = False
        self.forecasts = []
        self.lookups = []
        self.prompts = []
        self.plan = None
        self.audit_ms = 0
        self.audit_count = 0

    async def http(self, request):
        params = request.url.params
        await asyncio.sleep(0.002)
        if "name" in params:
            name = params["name"]
            self.lookups.append(name)
            query = "lisbon" if self.case.fixture == "spelling" and key(name) == "lisbn" else key(name)
            return httpx.Response(200, json={"results": [row for row in CATALOG_ROWS if key(row["name"]) == query]})
        row = next(row for row in CATALOG_ROWS if row["latitude"] == float(params["latitude"]))
        self.forecasts.append((row["name"], "hourly" if "hourly" in params else "current"))
        fixture = self.case.fixture if not self.warming else "normal"
        if fixture == "timeout":
            raise httpx.ReadTimeout("fixture timeout", request=request)
        if fixture == "provider_error":
            return httpx.Response(503, json={"error": True})
        second = not self.warming and len(self.case.places) == 2 and row["name"] == self.case.places[1]
        return httpx.Response(200, json=forecast(fixture, second, row["timezone"]))

    async def completion(self, **kwargs):
        payload = json.dumps(kwargs, ensure_ascii=False, default=str)
        schema_chars = len(json.dumps(kwargs.get("tools", []), ensure_ascii=False)) if kwargs.get("tools") else 0
        self.prompts.append({"chars": len(payload), "schema_chars": schema_chars})
        await asyncio.sleep(0.008)
        case = self.case
        count = len(self.prompts)
        if case.fixture == "quota" and not self.warming:
            response = httpx.Response(429, request=httpx.Request("POST", "https://fixture.invalid"))
            raise RateLimitError("daily fixture quota", response=response, body=None)
        content = self.draft()
        calls = None
        if case.fixture == "correction" and count == 1 and not self.warming:
            content = "Tomorrow in Osaka temperature is 99 °C."
        if case.fixture == "tool" and count in {1, 2} and not self.warming and self.plan and self.plan.destinations:
            target = self.plan.destinations[0]
            arguments = {"latitude": target.place.latitude, "longitude": target.place.longitude}
            calls = [SimpleNamespace(id=f"fixture-{count}", function=SimpleNamespace(
                name="get_hourly_forecast", arguments=json.dumps(arguments),
            ))]
            content = ""
        self.prompts[-1]["completion_chars"] = len(content) + (len(json.dumps(arguments)) if calls else 0)
        output = SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=content, tool_calls=calls), finish_reason="tool_calls" if calls else "stop",
        )])
        if case.fixture != "no_usage":
            output.usage = SimpleNamespace(prompt_tokens=412, completion_tokens=37, total_tokens=449)
        return output

    def draft(self):
        # Scripted drafts evaluate orchestration and rejection, never model quality.
        if self.warming or not self.case.groq_permitted or self.case.intent is None and not self.case.places:
            return "Hello. What weather would you like to check?"
        message = self.case.message.casefold()
        if "uncertainty" in self.case.required:
            return "Forecast uncertainty means plans should allow for changes. Recheck the forecast this afternoon."
        if self.case.fixture == "no_usage":
            return "Current temperature in Cebu is 21 °C."
        if "humidity" in message:
            return "Tomorrow in Accra humidity will be 64%. For cycling, leave room for breaks."
        if "wind forecast" in message:
            return "Tomorrow in Lisbon wind speed will be 14 km/h."
        if "temperature" in message:
            return "Tonight in Suva temperature will be 24 °C."
        if "breakdown" in message:
            city = self.case.places[0]
            return f"Tomorrow in {city} temperature is 24 °C, rain probability is 15%, and wind speed is 14 km/h."
        return "I need more weather information before advising on travel."


async def evaluate(case, index):
    fixture = Fixture(case)
    http_client = httpx.AsyncClient
    scope = ConversationScope(owner_kind="guest", owner_id="evaluation", thread_id=f"stage163-{index}")
    state = None
    history = []
    create = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fixture.completion)))
    real_plan = agent.plan_weather_request
    real_sleep = asyncio.sleep
    real_audit = HallucinationController.audit

    async def plan(*args, **kwargs):
        record = await real_plan(*args, **kwargs)
        fixture.plan = record
        return record

    def audit(controller, *args, **kwargs):
        start = perf_counter()
        try:
            return real_audit(controller, *args, **kwargs)
        finally:
            fixture.audit_ms += (perf_counter() - start) * 1000
            fixture.audit_count += 1

    def local_client(**kwargs):
        return http_client(transport=httpx.MockTransport(fixture.http), **kwargs)

    service.clear_weather_cache()
    with patch.object(service.httpx, "AsyncClient", local_client), patch.object(agent, "plan_weather_request", plan), \
            patch.object(HallucinationController, "audit", audit), patch.object(agent, "get_groq_client", return_value=create) as client_factory, \
            patch.object(service.asyncio, "sleep") as sleep:
        # Production retries still execute. Compress the one-second retry backoff in the fixture.
        async def fixture_sleep(delay):
            await real_sleep(min(delay, 0.008))
        sleep.side_effect = fixture_sleep
        fixture.warming = True
        for prompt in case.prior:
            try:
                prior = await agent.run_agent(prompt, history, request_scope=scope, trusted_state=state)
                state = prior.get("conversation_state", state)
                history += [{"role": "user", "content": prompt}, {"role": "assistant", "content": prior["response"]}]
            except RequestFailure:
                history.append({"role": "user", "content": prompt})
        fixture.warming = False
        fixture.plan = None
        fixture.prompts.clear()
        fixture.lookups.clear()
        fixture.forecasts.clear()
        fixture.audit_ms = fixture.audit_count = 0
        client_factory.reset_mock()
        started = perf_counter()
        failure = None
        try:
            answer = await agent.run_agent(case.message, history, request_scope=scope, trusted_state=state)
        except RequestFailure as error:
            failure = error.category.value
            answer = {"response": failure, "token_usage": error.metrics}
        except Exception as error:  # Capture reproducible production failures without stopping the dataset.
            failure = type(error).__name__
            answer = {"response": failure, "token_usage": {}}
        elapsed = (perf_counter() - started) * 1000

    metrics = answer.get("token_usage") or {}
    plan = fixture.plan
    task = plan.task if plan else parse_weather_request(case.message, history)
    confirmed = tuple(destination.place.name for destination in plan.destinations) if plan else ()
    actual_window = plan.destinations[0].period if plan and plan.destinations else task.period
    actual_state = answer.get("conversation_state") or state
    prior_anchor = state.last_confirmed_location if state else None
    anchor = actual_state.last_confirmed_location if actual_state else None
    if failure:
        state_ok = actual_state == state
    elif case.transition == "retain_anchor":
        state_ok = anchor == prior_anchor
    elif case.transition == "allow_first_confirmed_destination":
        state_ok = bool(anchor and fixture.lookups and key(anchor.name) == key(fixture.lookups[0]))
    elif case.transition == "resolve":
        state_ok = tuple(map(key, confirmed)) == tuple(map(key, case.places)) and (
            len(case.places) > 1 or (anchor and key(anchor.name) == key(case.places[0]))
        )
    else:
        state_ok = anchor == prior_anchor
    if case.category == "clarification" and case.prior and state and state.pending_clarification and case.message != "Thanks!":
        if case.message.startswith("Actually"):
            state_ok = state_ok and not actual_state.pending_clarification and actual_state.task_id != state.task_id
        else:
            state_ok = state_ok and not actual_state.pending_clarification and actual_state.task_id == state.task_id
    if case.message == "Thanks!" and state:
        state_ok = actual_state == state
    text = answer["response"]
    checks = {requirement: check_requirement(requirement, text) for requirement in case.required}
    report = answer.get("validation_report") or {}
    claimed = report.get("total_claims", 0) > 0
    grounding = report.get("is_trustworthy") if claimed else None
    fixture_numbers_ok = fixture_measurements(case, text)
    decision = plan.decision.kind if plan and plan.decision else None
    selected = metrics.get("deterministic_selected", False)
    calls = metrics.get("llm_calls_attempted", 0)
    route = "G" if calls else "D" if selected else "C" if decision not in {None, "PROVIDER_UNAVAILABLE"} else "L"
    location_ok = tuple(map(key, confirmed)) == tuple(map(key, case.places))
    if case.qualifier and location_ok:
        location_ok = bool(plan.destinations and plan.destinations[0].place.country == case.qualifier)
    parsed = task.destinations if task.comparison else ((task.location,) if task.location else ())
    parsed_location_ok = None if not case.places else tuple(
        key(place.split(",")[0].strip()) for place in parsed
    ) == tuple(map(key, case.places))
    if case.fixture in {"accent", "spelling"} and location_ok:
        parsed_location_ok = True  # Intended destination expressed using the fixture alias.
    # Unavailable provider data does not negate a successfully selected destination.
    if failure == "weather_provider_unavailable" and fixture.forecasts:
        location_ok = key(fixture.forecasts[-1][0]) == key(case.places[0])
    evaluated_answer = case.route in {"D", "G"} and bool(case.places)
    answer_location = all(key(place) in key(text) for place in case.places) if evaluated_answer else None
    answer_window = (case.window == "current" or case.window.replace("_", " ") in text.casefold()
                     ) if evaluated_answer else None
    hazard_checks = [passed for name, passed in checks.items() if name.startswith("hazard:") or name == "caution"]
    complete = all(checks.values()) and bool(state_ok) and (
        case.route not in {"D", "G"} or (not failure and answer_location is not False and answer_window is not False and grounding is not False and fixture_numbers_ok is not False)
    )
    behavior_ok = {
        "audited_fallback_or_typed_groq_quota": failure == "groq_quota_exhausted" or bool(
            metrics.get("deterministic_fallback") and grounding),
        "typed_weather_provider_unavailable": failure == "weather_provider_unavailable",
        "clarify": route == "C" and all(checks.values()),
        "state_evidence_limit": route == "L" and all(checks.values()),
        "audited_answer": route == "D" and complete,
        "prepared_synthesis": route == "G" and complete and (not case.places or bool(confirmed)),
    }[case.expected_behavior]
    pair_scoped = None
    if case.category == "comparison" and len(case.places) == 2:
        destination_values = [
            (case.places[0], ("24 °C", "15%", "14 km/h")),
            (case.places[1], ("28 °C", "35%", "19 km/h")),
        ]
        pair_scoped = all(any(key(city) in key(line) and all(value in line for value in measurements)
                              for line in text.splitlines()) for city, measurements in destination_values)
    return {
        "case": {**asdict(case), "expected_behavior": case.expected_behavior, "transition": case.transition,
                 "groq_permitted": case.groq_permitted, "country_qualifier": case.qualifier}, "response": text, "decision": decision, "failure": failure, "outcome": metrics.get("failure_category"),
        "actual": {"intent": task.intent, "places": confirmed, "window": actual_window, "route": route},
        "checks": checks, "complete": complete, "grounding": grounding, "state_ok": bool(state_ok),
        "behavior_ok": behavior_ok, "pair_scoped": pair_scoped, "fixture_numbers_ok": fixture_numbers_ok,
        "intent_ok": task.intent == case.intent, "location_ok": location_ok, "parsed_location_ok": parsed_location_ok,
        "window_ok": actual_window == case.window,
        "answer_location": answer_location, "answer_window": answer_window,
        "hazards_ok": all(hazard_checks) if hazard_checks else None,
        "metrics": {key: metrics.get(key) for key in (
            "llm_calls_attempted", "llm_calls_completed", "llm_calls", "deterministic_fallback",
            "weather_http_attempts", "planner_latency_ms", "weather_provider_latency_ms", "llm_latency_ms",
        )},
        "elapsed_ms": elapsed, "audit_ms": fixture.audit_ms, "audits": fixture.audit_count,
        "iterations": answer.get("iterations"), "client_constructions": client_factory.call_count,
        "lookups": fixture.lookups, "forecasts": fixture.forecasts, "prompts": fixture.prompts,
    }


def summarize(rows):
    def rate(field):
        values = [row[field] for row in rows if row[field] is not None]
        return [sum(values), len(values)]

    def timings(values):
        ordered = sorted(values)
        return [round(median(ordered), 2), round(ordered[ceil(len(ordered) * 0.95) - 1], 2)] if ordered else None

    turns = [call for row in rows for call in row["metrics"]["llm_calls"] or []]
    successful = [row for row in rows if row["complete"] and row["case"]["route"] in {"D", "G"} and row["case"]["places"]]
    return {
        "cases": len(rows),
        "expected": dict(Counter(row["case"]["route"] for row in rows)),
        "routing": dict(Counter(f"{row['case']['route']}->{row['actual']['route']}" for row in rows)),
        "quality": {field: rate(field) for field in ("intent_ok", "location_ok", "parsed_location_ok", "window_ok", "state_ok", "complete",
                                                         "grounding", "hazards_ok", "answer_location", "answer_window", "behavior_ok", "pair_scoped", "fixture_numbers_ok")},
        "calls": {"attempted": len(turns), "completed": sum(call["failure_category"] is None for call in turns),
                  "failed": sum(call["failure_category"] is not None for call in turns),
                  "corrections": sum(call["purpose"] == "hallucination_correction" for call in turns)},
        "fixture_tokens": {field: [sum(values), len(values)] for field in ("prompt_tokens", "completion_tokens")
                           if (values := [call[field] for call in turns if call[field] is not None])},
        "estimated_missing_tokens": sum(ceil(prompt["chars"] / 4) + ceil(prompt.get("completion_chars", 0) / 4)
                                        for row in rows for prompt, call in zip(row["prompts"], row["metrics"]["llm_calls"] or [])
                                        if call["prompt_tokens"] is None),
        "outcomes": dict(Counter(row["outcome"] for row in rows if row["outcome"])),
        "weather_http": sum(len(row["lookups"]) + len(row["forecasts"]) for row in rows),
        "unprepared_answer_attempts": sum(
            row["case"]["intent"] is not None and not row["actual"]["places"] and bool(row["prompts"])
            for row in rows
        ),
        "client_constructions": sum(row["client_constructions"] for row in rows),
        "iterations": dict(Counter(str(row["iterations"]) for row in rows)),
        "fallbacks": sum(row["metrics"]["deterministic_fallback"] is True for row in rows),
        "failures": dict(Counter(row["failure"] for row in rows if row["failure"])),
        "successful_weather_answers": len(successful),
        "successful_answers_with_groq": sum(bool(row["prompts"]) for row in successful),
        "success_timings_ms": {
            name: timings([value for row in successful if (value := getter(row)) is not None])
            for name, getter in {
                "total": lambda row: row["elapsed_ms"], "audit": lambda row: row["audit_ms"],
                "planner": lambda row: row["metrics"]["planner_latency_ms"],
                "weather": lambda row: row["metrics"]["weather_provider_latency_ms"],
                "groq_positive_only": lambda row: row["metrics"]["llm_latency_ms"] or None,
            }.items()
        },
    }


async def main(output):
    assert len(CASES) >= 120 and len({case.message.casefold() for case in CASES}) == len(CASES)
    rows = [await evaluate(case, index) for index, case in enumerate(CASES, 1)]
    results = {"summary": summarize(rows),
               "categories": {category: summarize([row for row in rows if row["case"]["category"] == category])
                              for category in dict.fromkeys(case.category for case in CASES)},
               "rows": rows}
    output.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(json.dumps(results["summary"], indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(main(parser.parse_args().output))
