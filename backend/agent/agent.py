import json
import logging
import os
import re
import time
import unicodedata
from pathlib import Path
from uuid import uuid4
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv
from groq import AsyncGroq

# Load environment variables securely from backend/.env or root .env
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    load_dotenv(dotenv_path=_env_file)
else:
    load_dotenv()

try:
    from backend.agent.weather_evidence_gate import model_weather_answer_is_grounded
    from backend.agent.answer_completeness import ADVICE_INTENTS, COMPLEX_REQUEST, requirements
    from backend.agent.llm_budget import (LLMBudget, LLMLimits, MAX_TOOL_REPLY_BYTES, UnsafePayload,
                                          assistant_fields, encode_wire, wire_size)
    from backend.agent.prepared_prompt import synthesis_message
    from backend.agent.tools import tools
    from backend.agent.executor import execute_tool
    from backend.agent.tracer import LifecycleTracer
    from backend.agent.failures import FailureCategory, RequestFailure, classify_groq_failure
    from backend.agent.conversation_state import ConversationScope, ConversationWeatherContext
    from backend.agent.request_planner import plan_weather_request
    from backend.agent.router import (
        describe_period,
        parse_weather_request,
        weather_facts,
        synthesize_deterministic_weather_buddy_response,
    )
    from backend.weather.service import (
        geocode_location,
        resolve_location,
        summarize_scoped_forecast,
        get_current_weather,
        get_hourly_forecast,
        get_temporal_forecast_slice,
        scope_hourly_forecast,
        weather_http_observer,
    )
    from backend.weather.risk_engine import WeatherRiskEngine
    from backend.evidence.evidence_engine import EvidenceEngine
    from backend.evidence.hallucination_controller import HallucinationController
    from backend.evidence.explanation_engine import ExplanationEngine
except ImportError:
    from agent.weather_evidence_gate import model_weather_answer_is_grounded
    from agent.answer_completeness import ADVICE_INTENTS, COMPLEX_REQUEST, requirements
    from agent.llm_budget import (LLMBudget, LLMLimits, MAX_TOOL_REPLY_BYTES, UnsafePayload,
                                          assistant_fields, encode_wire, wire_size)
    from agent.prepared_prompt import synthesis_message
    from agent.tools import tools
    from agent.executor import execute_tool
    from agent.tracer import LifecycleTracer
    from agent.failures import FailureCategory, RequestFailure, classify_groq_failure
    from agent.conversation_state import ConversationScope, ConversationWeatherContext
    from agent.request_planner import plan_weather_request
    from agent.router import (
        describe_period,
        parse_weather_request,
        weather_facts,
        synthesize_deterministic_weather_buddy_response,
    )
    from weather.service import (
        geocode_location,
        resolve_location,
        summarize_scoped_forecast,
        get_current_weather,
        get_hourly_forecast,
        get_temporal_forecast_slice,
        scope_hourly_forecast,
        weather_http_observer,
    )
    from weather.risk_engine import WeatherRiskEngine
    from evidence.evidence_engine import EvidenceEngine
    from evidence.hallucination_controller import HallucinationController
    from evidence.explanation_engine import ExplanationEngine

logger = logging.getLogger(__name__)

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
FAST_GROQ_MODEL = os.getenv("GROQ_FAST_MODEL", "openai/gpt-oss-120b")
DEFAULT_MAX_ITERATIONS = 10

WEATHER_BUDDY_SYSTEM_PROMPT = (
    "You are Sky Reader, a friendly, warm, and helpful Weather Buddy! 🌦️\n"
    "Your goal is to give users clear, practical, and conversational weather advice grounded in verified real-time data.\n\n"
    "Tone & Style Guidelines:\n"
    "1. Warm, conversational, and direct: Answer the user's question immediately in the first sentence.\n"
    "2. Be concise: Keep everyday answers punchy (25–50 words) and easy to read. Don't ramble.\n"
    "3. Understand casual English, Hinglish (e.g., 'thand hai kya', 'barish hogi kya'), slang, and typos naturally.\n"
    "4. Use friendly emojis occasionally (☀️, 🌧️, 🧥, 🧣, 💨) — don't overdo them.\n"
    "5. Avoid unnecessary technical meteorological jargon (e.g., barometric pressure or dew points) unless specifically requested.\n"
    "6. NEVER produce markdown tables unless the user explicitly asks for a table or comparison.\n"
    "7. NEVER repeat the user's question back to them.\n\n"
    "Grounding & Safety Rules:\n"
    "- Always ground factual numbers (temperature, rain probability, wind) strictly in the data returned by tools.\n"
    "- Umbrella & rain advice: Only recommend an umbrella if rain probability is at least 30% or rainfall is expected. If rain chance is low (under 20%), reassure the user that rain is unlikely.\n"
    "- Cold & attire advice: If cold (<15°C), suggest warm layers, a jacket or coat. If warm/hot (>30°C), suggest light clothing and hydration.\n"
    "- Risk communication: If risks are detected, clearly state the risk level and safety precautions. Never claim to be an official government alert system.\n"
    "- Uncertainty awareness: Express rain probabilistically without guaranteeing certainty."
)

SYSTEM_PROMPT = WEATHER_BUDDY_SYSTEM_PROMPT


def classify_query_complexity(query: str) -> str:
    """
    Deterministically classifies query complexity into 'simple', 'moderate', or 'complex'
    without making any additional LLM calls.
    """
    clean_q = query.strip().lower()
    words = clean_q.split()
    word_count = len(words)

    # Complex triggers: comparisons, multi-day forecasts, deep trend analyses, detailed explanations
    complex_keywords = [
        "compare", "vs", "versus", "difference", "trend", "trends",
        "next 3 days", "next 5 days", "next 7 days", "weekly",
        "hourly breakdown", "explain in detail", "in detail", "detailed",
        "breakdown", "deep dive", "meteorological", "comprehensive"
    ]
    if any(kw in clean_q for kw in complex_keywords) or word_count > 25:
        return "complex"

    # Multi-location check: e.g. "Delhi and Mumbai", "Paris or London"
    if re.search(r"\b(and|or|vs|to)\b", clean_q) and ("weather in" in clean_q or "compare" in clean_q):
        return "complex"

    # Simple triggers: quick binary/single-metric questions or short casual queries
    simple_patterns = [
        r"^(should i carry|do i need|will i need|need an?) (umbrella|coat|jacket|sweater|raincoat)",
        r"^(will it|is it going to) rain",
        r"^(is it|it's) (hot|cold|warm|chilly|freezing|raining|sunny)",
        r"^(how's|how is|what's|what is) the weather (today|now|outside)?",
        r"^(thand|garmi|barish) hai kya",
        r"^(can i|should i) (go for a walk|run|exercise|go out)",
        r"^temperature in ",
        r"^what about tomorrow\??$",
        r"^how about tomorrow\??$",
        r"^and tomorrow\??$",
    ]
    for pat in simple_patterns:
        if re.search(pat, clean_q):
            return "simple"

    if word_count <= 8:
        return "simple"

    return "moderate"


def get_token_limit_for_complexity(complexity: str, is_severe_risk: bool = False) -> int:
    """Returns max_tokens limit according to classified query complexity and risk state."""
    if is_severe_risk:
        base = 600
    elif complexity == "simple":
        base = 350
    elif complexity == "moderate":
        base = 650
    else:
        base = 1200
    return max(base, 600) if is_severe_risk else base


def create_compact_tool_payload(fn_name: str, raw_result: Any, scoped_period=None) -> Any:
    """
    Formats a compact payload of the tool output for inclusion in the LLM's context.
    The full raw result is preserved in agent memory for deterministic evidence engines.
    """
    if not isinstance(raw_result, dict):
        return raw_result

    if fn_name == "get_hourly_forecast":
        hourly = raw_result.get("hourly", {})
        times = hourly.get("time", [])
        if not times:
            return raw_result

        if scoped_period:
            slice_data = {
                "times": times,
                "temperatures": hourly.get("temperature_2m", []),
                "rain_probabilities": hourly.get("precipitation_probability", []),
                "rain_amounts": hourly.get("precipitation", []),
                "wind_speeds": hourly.get("wind_speed_10m", []),
            }
        else:
            slice_data = get_temporal_forecast_slice(raw_result)
        temps, rain_probs, rain_amounts, winds = (
            [value for value in slice_data[key] if isinstance(value, (int, float))]
            for key in ("temperatures", "rain_probabilities", "rain_amounts", "wind_speeds")
        )
        slice_times = slice_data["times"]

        # A summary across missing hours can understate a peak or total.
        count = len(slice_times)
        summary = {
            "min_temp_c": round(min(temps), 1) if count and len(temps) == count else None,
            "max_temp_c": round(max(temps), 1) if count and len(temps) == count else None,
            "peak_rain_chance_pct": max(rain_probs) if count and len(rain_probs) == count else None,
            "total_precipitation_mm": round(sum(rain_amounts), 2) if count and len(rain_amounts) == count else None,
            "max_wind_kmh": round(max(winds), 1) if count and len(winds) == count else None,
        }

        # Sample every 3 hours for the next 24 hours
        sampled_checkpoints = []
        for i in range(0, min(24, len(slice_times)), 3):
            sampled_checkpoints.append({
                "time": slice_times[i],
                "temp_c": slice_data["temperatures"][i] if i < len(slice_data["temperatures"]) else None,
                "rain_pct": slice_data["rain_probabilities"][i] if i < len(slice_data["rain_probabilities"]) else None,
                "rain_mm": slice_data["rain_amounts"][i] if i < len(slice_data["rain_amounts"]) else None,
                "wind_kmh": slice_data["wind_speeds"][i] if i < len(slice_data["wind_speeds"]) else None,
            })

        return {
            "period": scoped_period or "next_24h",
            "summary": summary,
            "timezone": raw_result.get("timezone"),
            "checkpoints_sampled_3h": sampled_checkpoints,
        }

    if fn_name == "get_current_weather":
        current = raw_result.get("current", {})
        if current:
            return {
                "temperature": current.get("temperature_2m"),
                "feels_like": current.get("apparent_temperature"),
                "humidity": current.get("relative_humidity_2m"),
                "wind_speed": current.get("wind_speed_10m"),
                "weather_code": current.get("weather_code"),
                "time": current.get("time"),
            }

    return raw_result


def bind_period(evidence, period, window_hours):
    for item in evidence.items:
        item.metadata.update(requested_period=period, window_hours=window_hours)


def comparison_location_key(value: str) -> str:
    value = unicodedata.normalize("NFC", value.casefold())
    return re.sub(r"\s*,\s*", ", ", " ".join(value.split()))


def matches_resolved_destination(lookup: str, requested: str, place: dict) -> bool:
    key = comparison_location_key(lookup)
    requested_key = comparison_location_key(requested)
    if key == requested_key:
        return True
    if "," in requested_key:
        return False
    city, *qualifiers = key.split(", ")
    labels = {comparison_location_key(place.get(field) or "") for field in ("admin1", "country", "country_code")}
    return city in {requested_key, comparison_location_key(place["name"])} and bool(qualifiers) and all(
        qualifier and qualifier in labels for qualifier in qualifiers
    )


def drops_comparison_qualifiers(question: str, lookup: str) -> bool:
    question, lookup = map(comparison_location_key, (question, lookup))
    city, separator, _ = lookup.partition(", ")
    if not city or not re.search(r"(?<!\w)" + re.escape(city) + r", ", question):
        return False
    # A trailing comma followed by another label means the lookup omitted a qualifier.
    suffix = r"(?!\w)(?!, (?!and\b|versus\b|vs\b)\w)"
    return not separator or not re.search(r"(?<!\w)" + re.escape(lookup) + suffix, question)


def get_groq_client(api_key: Optional[str] = None) -> AsyncGroq:
    """
    Initializes and returns an AsyncGroq client with max_retries=0
    to allow Sky Reader explicit, non-blocking rate limit control.
    """
    key = os.getenv("GROQ_API_KEY") if api_key is None else api_key
    if not key or not key.strip():
        raise ValueError(
            "Groq API key is missing. Please set GROQ_API_KEY in backend/.env"
        )
    return AsyncGroq(api_key=key.strip(), max_retries=0)


def weather_advice(topic, components, facts, material):
    advice_parts = []
    if "temperature" in facts and (topic == "coat_clothing" or "clothing" in components):
        layers = facts.get("feels like", facts["temperature"])[0] < 15
        advice = "Bring a jacket or warm layers." if layers else "Light layers should be enough for the temperature."
        if (facts.get("rain probability", (0, 0))[1] >= 30 or facts.get("rainfall", (0, 0))[1] > 0
                or facts.get("wind speed", (0, 0))[1] >= 30):
            advice += " Choose a wind-resistant or waterproof outer layer."
        advice_parts.append(advice)
    if topic == "morning_walk":
        advice_parts.append("Keep the outing flexible and recheck conditions before leaving.")
    if topic == "umbrella" or "umbrella" in components:
        wet = facts.get("rain probability", (0, 0))[1] >= 30 or facts.get("rainfall", (0, 0))[1] > 0
        advice_parts.append("Pack rain protection." if wet else "An umbrella is optional based on this forecast.")
    if material and (topic in ADVICE_INTENTS or {"clothing", "umbrella", "safety"} & set(components)):
        advice_parts = ["Consider postponing or moving the activity indoors."]
        if "umbrella" in components:
            advice_parts.append("An umbrella does not protect against the reported hazards.")
        if "clothing" in components:
            advice_parts.append("Clothing alone will not address these hazards.")
    elif topic == "weather_risks":
        advice_parts.append("Check local alerts and conditions before leaving.")
    return " ".join(advice_parts) or None


async def run_agent(
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    executor_fn: Optional[Any] = None,
    client: Optional[Any] = None,
    tracer: Optional[LifecycleTracer] = None,
    *,
    request_scope: ConversationScope | None = None,
    trusted_state: ConversationWeatherContext | None = None,
    llm_limits: LLMLimits | None = None,
) -> Dict[str, Any]:
    """
    Runs the agentic reasoning and deterministic fast-path routing pipeline.
    Optimized for sub-second latency, bounded token usage, and robust rate-limit handling.
    """
    active_tracer = tracer or LifecycleTracer()
    active_model = model or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)
    active_client = client
    budget = LLMBudget(llm_limits or LLMLimits())
    active_executor = executor_fn or execute_tool
    evidence_engine = EvidenceEngine()
    hallucination_controller = HallucinationController()
    explanation_engine = ExplanationEngine()
    plan = None
    if trusted_state is not None and request_scope != trusted_state.scope:
        raise ValueError("Trusted state requires a matching request scope.")

    def failure(error):
        active_tracer.failure_category = error.category.value
        error.metrics = active_tracer.get_summary()
        return error

    def require_client():
        try:
            return get_groq_client(api_key=api_key)
        except ValueError:
            raise failure(RequestFailure(FailureCategory.GROQ_AUTHENTICATION)) from None

    async def complete(purpose, **kwargs):
        nonlocal active_client
        try:
            dimensions = {
                "prompt_bytes": wire_size({"model": active_model, **kwargs}),
                "schema_bytes": wire_size(kwargs["tools"]) if kwargs.get("tools") else 0,
            }
        except UnsafePayload:
            active_tracer.budget_exhausted = True
            raise failure(RequestFailure(FailureCategory.LLM_BUDGET_EXHAUSTED)) from None
        reservation = budget.reserve(purpose, dimensions["prompt_bytes"], kwargs["max_tokens"])
        if reservation is None:
            active_tracer.budget_exhausted = True
            raise failure(RequestFailure(FailureCategory.LLM_BUDGET_EXHAUSTED))
        active_client = active_client or require_client()
        estimated_input, allowed_output = reservation
        kwargs["max_tokens"] = allowed_output
        dimensions["estimated_prompt_tokens"] = estimated_input
        started = time.perf_counter()
        try:
            response = await active_client.chat.completions.create(model=active_model, **kwargs)
            choices = getattr(response, "choices", None)
            if type(choices) not in (list, tuple) or not choices:
                raise RequestFailure(FailureCategory.GROQ_SERVICE)
            message = assistant_fields(getattr(choices[0], "message", None))
        except Exception as error:
            classified = (RequestFailure(FailureCategory.GROQ_SERVICE) if isinstance(error, UnsafePayload)
                          else error if isinstance(error, RequestFailure) else classify_groq_failure(error))
            active_tracer.record_llm_call(
                active_model, (time.perf_counter() - started) * 1000, None, None, None,
                call_purpose=purpose, failure_category=classified.category.value, **dimensions,
            )
            raise failure(classified) from None
        usage = getattr(response, "usage", None)
        def usage_count(name):
            value = getattr(usage, name, None)
            return value if type(value) is int and value >= 0 else None

        budget.observe(estimated_input, allowed_output, usage)
        active_tracer.record_llm_call(
            active_model, (time.perf_counter() - started) * 1000, usage_count("prompt_tokens"),
            usage_count("completion_tokens"), usage_count("total_tokens"),
            finish_reason=getattr(choices[0], "finish_reason", None)
            if type(getattr(choices[0], "finish_reason", None)) is str else None,
            call_purpose=purpose, **dimensions,
        )
        return message

    def result(text, executed=(), iterations=1, evidence=None, risk=None, *, fallback=False, outcome=None, audit=None, model_draft=False):
        if model_draft and not model_weather_answer_is_grounded(
            text, evidence, hallucination_controller, weather_request=bool(weather_query),
        ):
            text = "I couldn’t verify the weather for the requested location and period."
            audit = None
            active_tracer.answer_complete = False
            outcome = FailureCategory.FORECAST_WINDOW_UNAVAILABLE
            evidence = evidence or evidence_engine.generate_evidence()
        active_tracer.deterministic_fallback |= fallback
        if active_tracer.deterministic_selected:
            active_tracer.answer_complete = True
        if outcome:
            active_tracer.failure_category = outcome.value
        claims, report, proof = [], None, None
        if evidence is None and executed:
            evidence = evidence_engine.generate_evidence()
        if evidence is not None:
            claims, report = audit or hallucination_controller.audit(text, evidence)
            if claims and not report.is_trustworthy and executor_fn is None:
                verified_hazards = [line for line in text.splitlines() if line.startswith("Detected hazards")
                                    and not re.search(r"\d", line)]
                text = " ".join((*verified_hazards, "I couldn’t verify the requested weather details."))
                claims, report = hallucination_controller.audit(text, evidence)
                active_tracer.answer_complete = False
                active_tracer.deterministic_selected = False
                active_tracer.failure_category = FailureCategory.FORECAST_WINDOW_UNAVAILABLE.value
            proof = explanation_engine.generate_proof(user_message, text, evidence, report, report.validation_results)
        return {
            "response": text, "tool_calls": list(executed), "iterations": iterations,
            "claims": [claim.model_dump() for claim in claims],
            "validation_report": report.model_dump() if report is not None else None,
            "explanation": proof.model_dump() if proof is not None else None,
            "risk_assessment": risk, "token_usage": active_tracer.get_summary(),
            **({"conversation_state": plan.state} if plan and request_scope is not None else {}),
        }

    t_parse_start = time.time()
    complexity = classify_query_complexity(user_message)
    detailed = bool(COMPLEX_REQUEST.search(user_message))
    executed_tools: List[Dict[str, Any]] = []

    async def fetch(name, function, **arguments):
        started = time.perf_counter()
        observer_token = weather_http_observer.set(active_tracer.record_weather_http)
        try:
            output = await (function(**arguments) if executor_fn is None else active_executor(name, arguments))
        except Exception:
            active_tracer.record_tool_execution(name, arguments, (time.perf_counter() - started) * 1000,
                                                error="tool_failed")
            raise
        finally:
            weather_http_observer.reset(observer_token)
        trace_result = output
        if name == "geocode_location" and hasattr(output, "status"):
            trace_result = output.location.as_legacy_place() if output.status == "RESOLVED" else {
                "status": output.status.lower(),
            }
        trace_args = {key: value for key, value in arguments.items() if key != "reference"}
        executed_tools.append({"tool": name, "arguments": trace_args, "result": trace_result})
        active_tracer.record_tool_execution(name, trace_args, (time.perf_counter() - started) * 1000)
        return output

    def clarify(location):
        return f"I couldn’t resolve {location} to a unique place. Could you specify the city, region, and country?"

    place = None
    planned_single = None
    if executor_fn is None:
        async def resolve(**arguments):
            return await fetch("geocode_location", resolve_location, **arguments)

        async def current_weather(**coordinates):
            return await fetch("get_current_weather", get_current_weather, **coordinates)

        async def hourly_forecast(**coordinates):
            return await fetch("get_hourly_forecast", get_hourly_forecast, **coordinates)

        planner_start = time.perf_counter()
        try:
            plan = await plan_weather_request(
                user_message, conversation_history,
                scope=request_scope or ConversationScope(owner_kind="guest", owner_id=uuid4().hex, thread_id=uuid4().hex),
                state=trusted_state, resolver=resolve, current_weather=current_weather, hourly_forecast=hourly_forecast,
            )
        except RequestFailure as error:
            active_tracer.record_span("planner", (time.perf_counter() - planner_start) * 1000)
            raise failure(error) from None
        active_tracer.record_span("planner", (time.perf_counter() - planner_start) * 1000)
        request = plan.task
        intent, comparison = request.intent, request.comparison
        fast_path = False
        if plan.decision:
            decision = plan.decision
            logger.debug("Weather planning decision=%s", decision.kind)
            if decision.kind == "PROVIDER_UNAVAILABLE":
                raise failure(RequestFailure(FailureCategory.WEATHER_PROVIDER_UNAVAILABLE))
            messages_by_kind = {
                "location_required": "Which city and region should I check?",
                "comparison_required": "Which two destinations should I compare?",
                "relative_place_required": "Which earlier place should I compare with the current destination?",
                "sunset_required": "I can’t verify the local sunset time. What local time should the forecast start at?",
                "same_location": "Both names resolve to the same place. Which other destination should I compare?",
                "relative_time_required": "Which time should I compare with that forecast window?",
            }
            if decision.kind == "NOT_FOUND":
                return result(f"I couldn’t find a unique place for {decision.query}. Check the spelling or specify the city, region, and country.",
                              executed_tools, outcome=FailureCategory.LOCATION_NOT_FOUND)
            return result(messages_by_kind.get(decision.kind) or clarify(decision.query), executed_tools,
                          outcome=FailureCategory.AMBIGUOUS if decision.kind == "AMBIGUOUS" else None)
        if plan.destinations and not comparison:
            planned_single = plan.destinations[0]
            place = planned_single.place.as_legacy_place()
            if planned_single.status == "unavailable":
                active_tracer.answer_complete = False
                label = describe_period(planned_single.period)
                return result(f"Weather for {place['name']} is unavailable for {label}.", executed_tools,
                              outcome=FailureCategory.FORECAST_WINDOW_UNAVAILABLE)
    else:
        # Historical callers with injected executors retain their evaluation flow.
        request = parse_weather_request(user_message, conversation_history)
        intent, comparison = request.intent, request.comparison
        fast_path = bool(request.safety and not comparison)
        if request.needs_destinations:
            return result("Which two destinations should I compare?")
        if request.safety and comparison:
            return result("Which city should I assess first? Weather hazards and activity advice depend on the location.")

    active_tracer.record_span("parsing_and_routing", (time.time() - t_parse_start) * 1000)
    weather_query = intent or comparison or re.search(
        r"\b(weather|forecast|temperature|rain|wind|humidity)\b", user_message, re.I
    )
    logger.debug("Weather routing intent=%s comparison=%s fast_path=%s", intent, comparison, fast_path)
    if executor_fn is not None and fast_path:
        if not request.location:
            return result("Which city and region should I check?")
        place = await fetch("geocode_location", geocode_location, location=request.location)
        if not isinstance(place, dict) or not {"latitude", "longitude", "name"} <= place.keys():
            return result(clarify(request.location), executed_tools)

    if plan and plan.baseline and planned_single:
        evidence = evidence_engine.generate_evidence()
        ranges = []
        lines = []
        contracts = []
        missing_components = []
        for destination in (planned_single, plan.baseline):
            scoped = destination.data()
            window = summarize_scoped_forecast(scoped, destination.period)
            facts = weather_facts("all", hourly_slice=window)
            values = facts.get("temperature")
            if not values:
                active_tracer.answer_complete = False
                return result("I don’t have temperature data for both forecast windows.", executed_tools,
                              outcome=FailureCategory.FORECAST_WINDOW_UNAVAILABLE)
            ranges.append(values)
            label = describe_period(destination.period)
            relative_risk = WeatherRiskEngine().assess_risks(
                scoped, location_name=place["name"], forecast_period=destination.period,
            ).model_dump(mode="json")
            hazards = [item["condition"] for item in relative_risk["detected_risks"]
                       if item["severity"] in {"HIGH", "SEVERE"}]
            components = request.components if destination is planned_single else ()
            topic = intent if destination is planned_single and intent in ADVICE_INTENTS else "temperature"
            advice = weather_advice(topic, components, facts, hazards)
            contract = requirements(topic, user_message, forecast=True, risk=relative_risk,
                                    advice=advice, components=components)
            required = {metric for group in contract.measurements for metric in group}
            risk_complete = not relative_risk["data_limitations"]
            available = set(facts) | ({"risk"} if risk_complete else set())
            missing = contract.missing_data(available)
            show_risk = ("risk" in required and risk_complete) or bool(hazards)
            lines.append(synthesize_deterministic_weather_buddy_response(
                "all", place["name"], hourly_slice=window, period=label, metrics=required & facts.keys(),
            ))
            if show_risk:
                lines.append(f"Modeled weather risk in {place['name']} for {label} is {relative_risk['overall_risk_level']}.")
            if hazards:
                lines.append(f"Detected hazards for {label}: " + ", ".join(hazards) + ".")
            if advice and (not missing or hazards):
                lines.append(advice)
            if missing:
                missing_components.extend(missing)
                lines.append(f"I don’t have complete evidence for {', '.join(missing)} for {label}.")
            contracts.append(contract)
            source = evidence_engine.generate_evidence(
                hourly_data=scoped, location_meta=place,
                analysis_results={"day_analyzed": destination.period, "risk_assessment": relative_risk} if show_risk else None,
            )
            bind_period(source, destination.period, len(window["times"]))
            for item in source.items:
                item.id = f"{destination.period}:{item.id}"
                evidence.add(item)
        target, baseline = ranges
        target_label, baseline_label = map(describe_period, (planned_single.period, plan.baseline.period))
        if target[1] < baseline[0]:
            comparison_text = f"The forecast is colder for {target_label} than for {baseline_label}."
        elif target[0] > baseline[1]:
            comparison_text = f"The forecast is warmer for {target_label} than for {baseline_label}."
        elif target == baseline:
            comparison_text = "The two windows have the same forecast temperature range."
        else:
            comparison_text = "The temperature ranges overlap across the two windows."
        text = "\n".join((comparison_text, *lines))
        _, report = hallucination_controller.audit(text, evidence)
        active_tracer.deterministic_selected = report.is_trustworthy and not missing_components and not any(
            contract.omissions(text, report, evidence, location=place["name"], period=destination.period)
            for contract, destination in zip(contracts, (planned_single, plan.baseline))
        )
        active_tracer.answer_complete = active_tracer.deterministic_selected
        if not active_tracer.answer_complete and not (missing_components and report.is_trustworthy):
            return result("I couldn’t verify temperatures for both forecast windows.", executed_tools,
                          outcome=FailureCategory.FORECAST_WINDOW_UNAVAILABLE)
        return result(text, executed_tools, evidence=evidence,
                      outcome=FailureCategory.FORECAST_WINDOW_UNAVAILABLE if missing_components else None)

    prepared_risk = None
    if planned_single and planned_single.requirement == "hourly":
        prepared_risk = WeatherRiskEngine().assess_risks(
            planned_single.data(), location_name=place["name"], forecast_period=planned_single.period,
        ).model_dump(mode="json")
    material_risk = bool(prepared_risk and prepared_risk["overall_risk_level"] in {"HIGH", "SEVERE"})

    if planned_single and (not detailed or intent in ADVICE_INTENTS or material_risk):
        raw = planned_single.data()
        hourly = planned_single.requirement == "hourly"
        period = planned_single.period
        label = describe_period(period)
        location = place["name"]
        window = summarize_scoped_forecast(raw, period) if hourly else None
        topic = intent or "current_weather"
        risk = prepared_risk
        material = [item for item in (risk or {}).get("detected_risks", [])
                    if item["severity"] in {"HIGH", "SEVERE"}]
        visible_hazards = [item for item in (risk or {}).get("detected_risks", [])
                           if topic in ADVICE_INTENTS or item in material]
        risk_complete = bool(risk and not risk["data_limitations"])
        hazard_lines = []
        if visible_hazards:
            hazard_lines.append("Detected hazards: " + ", ".join(item["condition"] for item in visible_hazards) + ".")
            hazard_lines.extend(dict.fromkeys(item["recommendations"][0] for item in visible_hazards
                                              if item["recommendations"]
                                              and "carry an umbrella" not in item["recommendations"][0].casefold()))
        facts = weather_facts("all", raw if not hourly else None, window)
        advice = weather_advice(topic, request.components, facts, material)
        contract = requirements(topic, user_message, forecast=hourly, risk=risk, advice=advice, components=request.components)
        required_metrics = {metric for group in contract.measurements for metric in group}
        evidence = evidence_engine.generate_evidence(
            current_data=raw if not hourly else None, hourly_data=raw if hourly else None, location_meta=place,
            analysis_results={"day_analyzed": period, "risk_assessment": risk} if risk_complete or material else None,
        )
        if hourly:
            bind_period(evidence, period, len(window["times"]))
        lines = []
        available = set(facts)
        if not hourly:
            condition = next((item.value for item in evidence.items
                              if item.variable.value == "weather_condition" and item.value != "Unknown"), None)
            if condition:
                available.add("conditions")
                if "conditions" in required_metrics:
                    lines.append(f"Observed conditions in {location}: {condition}.")
        metrics = required_metrics & set(facts)
        if metrics:
            render_topic = "rain_check" if topic in {"rain_check", "umbrella"} and metrics <= {
                "rain probability", "rainfall",
            } else "all"
            lines.append(synthesize_deterministic_weather_buddy_response(
                render_topic, location, raw if not hourly else None, window,
                period=label if hourly else None, metrics=metrics,
            ))
        if material or (risk_complete and "risk" in required_metrics):
            lines.append(f"Modeled weather risk in {location} for {label} is {risk['overall_risk_level']}.")
        if risk_complete:
            available.add("risk")
        lines.extend(hazard_lines)
        missing = contract.missing_data(available)
        if missing:
            lines.append(f"I don’t have complete {'; '.join(missing)} evidence in {location}"
                         + (f" for {label}." if hourly else " right now."))
        if advice and (not missing or material or topic == "weather_risks"):
            lines.append(advice)
        if topic == "weather_risks":
            lines.append(f"This assessment cannot establish safety{f' for {request.activity}' if request.activity else ''}.")
        if detailed and material_risk and topic not in ADVICE_INTENTS:
            lines.append("This is a forecast summary. The requested detailed analysis is unavailable.")
        text = " ".join(lines)
        claims, report = hallucination_controller.audit(text, evidence)
        omissions = contract.omissions(text, report, evidence, location=location, period=period if hourly else None)
        if not missing and not omissions and report.is_trustworthy and (not detailed or topic in ADVICE_INTENTS):
            active_tracer.deterministic_selected = True
            return result(text, executed_tools, evidence=evidence, risk=risk if topic in ADVICE_INTENTS or material else None,
                          audit=(claims, report))
        if not report.is_trustworthy and report.total_claims:
            text = " ".join(hazard_lines + [f"I can’t verify a complete answer in {location} for {label}."])
        active_tracer.answer_complete = False
        return result(text, executed_tools, evidence=evidence, risk=risk if risk_complete or material else None,
                      outcome=FailureCategory.FORECAST_WINDOW_UNAVAILABLE if hourly else None)

    if fast_path:
        # Historical injected executors use the original safety contract.
        coordinates = {"latitude": place["latitude"], "longitude": place["longitude"]}
        period = "next_1h" if request.period == "current" else request.period
        hourly = await fetch("get_hourly_forecast", get_hourly_forecast, **coordinates)
        hourly = {**(hourly or {}), "timezone": (hourly or {}).get("timezone") or place.get("timezone")}
        scoped = scope_hourly_forecast(hourly, period)
        window = summarize_scoped_forecast(scoped, period)
        label = describe_period(period)
        if not window["available"]:
            return result(f"The requested forecast window ({label}) is unavailable in {place['name']}.", executed_tools)
        risk = WeatherRiskEngine().assess_risks(
            scoped, location_name=place["name"], forecast_period=period,
        ).model_dump(mode="json")
        if risk["data_limitations"] and not risk["detected_risks"]:
            return result(f"I don’t have enough forecast evidence to assess hazards in {place['name']}.", executed_tools)
        evidence = evidence_engine.generate_evidence(
            hourly_data=scoped, location_meta=place,
            analysis_results={"day_analyzed": period, "risk_assessment": risk},
        )
        bind_period(evidence, period, len(window["times"]))
        text = synthesize_deterministic_weather_buddy_response(
            intent, place["name"], hourly_slice=window, risk_data=risk,
            period=label, activity=request.activity,
        )
        return result(text, executed_tools, evidence=evidence, risk=risk)

    comparison_data = {}
    comparison_places = {}
    comparison_evidence = None
    comparison_text = None
    comparison_high_risk = False
    comparison_hazards = []
    comparison_incomplete = False
    if plan and comparison and plan.destinations:
        resolved = []
        for destination in plan.destinations:
            resolved_place = destination.place.as_legacy_place()
            coordinates = (destination.place.latitude, destination.place.longitude)
            comparison_places[coordinates] = resolved_place
            resolved.append((destination.query, coordinates, resolved_place))

        comparison_evidence = evidence_engine.generate_evidence()
        lines = []
        names_repeat = len({place["name"].casefold() for _, _, place in resolved}) < len(resolved)
        for destination, (name, coordinates, resolved_place) in zip(plan.destinations, resolved):
            location = name if names_repeat else resolved_place["name"]
            latitude, longitude = coordinates
            scope = destination.period
            label = describe_period(scope)
            scoped = destination.data()
            window = summarize_scoped_forecast(scoped, scope)
            facts = weather_facts("all", hourly_slice=window)
            if not window["available"]:
                comparison_incomplete = True
                lines.append(f"Weather for {location} is unavailable for {label}.")
                comparison_data[coordinates] = {"location": location, "status": "unavailable"}
                continue

            risk = WeatherRiskEngine().assess_risks(
                scoped, location_name=location, forecast_period=scope
            ).model_dump(mode="json")
            risk_level = risk["overall_risk_level"]
            contract = requirements("comparison", user_message, forecast=True, components=request.components)
            available = set(facts)
            if not risk["data_limitations"]:
                available.add("risk")
            missing = contract.missing_data(available)
            incomplete = bool(missing)
            comparison_incomplete |= incomplete
            comparison_high_risk |= risk_level in {"HIGH", "SEVERE"}
            show_risk = not incomplete or bool(risk["detected_risks"])
            analysis = {"day_analyzed": scope, "risk_assessment": risk} if show_risk else None
            source = evidence_engine.generate_evidence(
                hourly_data=scoped, location_meta={**resolved_place, "name": location}, analysis_results=analysis
            )
            bind_period(source, scope, len(window["times"]))
            for item in source.items:
                item.id = f"{latitude},{longitude}:{item.id}"
                comparison_evidence.add(item)

            metrics = {metric for group in contract.measurements for metric in group} & facts.keys()
            if metrics:
                lines.append(synthesize_deterministic_weather_buddy_response(
                    "all", location, hourly_slice=window, period=label, metrics=metrics,
                ))
            if missing:
                lines.append(f"Incomplete forecast evidence in {location} for {label}: " + ", ".join(missing) + ".")
            if show_risk:
                lines.append(f"Modeled weather risk in {location} for {label} is {risk_level}.")
                if risk["detected_risks"]:
                    hazards = ", ".join(item["condition"] for item in risk["detected_risks"])
                    hazard_line = f"Detected hazards in {location}: {hazards}."
                    comparison_hazards.append(hazard_line)
                    lines.append(hazard_line)
                    if risk["safety_recommendations"]:
                        guidance = risk["safety_recommendations"][0]
                        if "carry an umbrella" in guidance.casefold():
                            guidance = "Pack rain protection."
                        lines.append(f"For {location}: {guidance}")
            comparison_data[coordinates] = {
                "location": location, "timezone": scoped.get("timezone"), "period": label,
                "hours": [window["times"][0], window["times"][-1]],
                "measurements": facts, "risk": risk if show_risk else None,
            }

        if comparison_incomplete:
            lines.append("Forecast coverage is incomplete. I can’t recommend one destination over the other.")
        elif request.safety:
            lines.append("Check local alerts and conditions for each destination before leaving.")
        if not comparison_incomplete and re.search(r"\b(?:choose|pick|better|prefer)\b", user_message, re.I):
            first, second = comparison_data.values()
            order = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "SEVERE": 3}
            levels = [order[entry["risk"]["overall_risk_level"]] for entry in (first, second)]
            if min(levels) >= order["HIGH"]:
                lines.append("Both destinations have elevated hazards. Consider postponing outdoor plans.")
            elif levels[0] != levels[1]:
                preferred = first if levels[0] < levels[1] else second
                lines.append(f"I’d favor {preferred['location']} on weather risk alone.")
            else:
                lines.append("Neither destination has a lower modeled risk rating. Use the temperature, rain and wind forecasts to decide.")
        if not comparison_incomplete and re.search(r"\b(?:warmer|colder|less rain(?:y)?|drier)\b", user_message, re.I):
            first, second = comparison_data.values()
            left, right = (entry["measurements"]["temperature"] for entry in (first, second))
            if re.search(r"\b(?:warmer|colder)\b", user_message, re.I):
                warmer = first if left[0] > right[1] else second if right[0] > left[1] else None
                colder_requested = bool(re.search(r"\bcolder\b", user_message, re.I))
                chosen = (second if warmer is first else first) if warmer and colder_requested else warmer
                adjective = "colder" if colder_requested else "warmer"
                lines.append(f"{chosen['location']} has the {adjective} forecast range." if chosen else
                             "The forecast temperature ranges overlap.")
            if re.search(r"\b(?:less rain(?:y)?|drier)\b", user_message, re.I):
                odds = [entry["measurements"].get("rain probability") for entry in (first, second)]
                if all(odds) and odds[0][1] != odds[1][1]:
                    lower = first if odds[0][1] < odds[1][1] else second
                    lines.append(f"{lower['location']} has the lower peak chance of rain.")
                elif all(odds):
                    lines.append("Both destinations have the same peak chance of rain.")
                else:
                    lines.append("The available evidence does not establish which destination is less likely to get rain.")
        comparison_text = "\n".join(lines)
        comparison_claims, comparison_report = hallucination_controller.audit(comparison_text, comparison_evidence)
        comparison_complete = not comparison_incomplete and comparison_report.is_trustworthy and all(
            not requirements("comparison", user_message, forecast=True, risk=data["risk"],
                             components=request.components).omissions(
                comparison_text, comparison_report, comparison_evidence, location=data["location"],
                period=destination.period,
            ) for data, destination in zip(comparison_data.values(), plan.destinations)
        )
        if not detailed or comparison_incomplete or comparison_high_risk:
            active_tracer.deterministic_selected = comparison_complete
            active_tracer.answer_complete = comparison_complete
            if comparison_report.total_claims and not comparison_report.is_trustworthy:
                comparison_text = " ".join((*comparison_hazards,
                                           "I couldn’t verify the requested comparison for both destinations."))
            return result(comparison_text, executed_tools, evidence=comparison_evidence,
                          outcome=None if comparison_complete else FailureCategory.FORECAST_WINDOW_UNAVAILABLE,
                          audit=(comparison_claims, comparison_report) if comparison_report.is_trustworthy else None)
    prepared = bool(plan and plan.destinations)
    messages = [{"role": "system", "content": (
        "You are Sky Reader. Give clear, concise weather explanations grounded in the supplied evidence."
        if prepared else WEATHER_BUDDY_SYSTEM_PROMPT
    )}]
    confirmed_place = place
    places = dict(comparison_places)
    sources = {}
    if prepared:
        risks = [entry.get("risk") for entry in comparison_data.values()] if comparison else [prepared_risk]
        messages.append(synthesis_message(
            plan.destinations, risks, request.components, request.activity,
            hourly_detail=bool(re.search(r"\b(?:hourly|hour by hour|at \d)\b", user_message, re.I)),
        ))
        if planned_single:
            coordinates = (place["latitude"], place["longitude"])
            places[coordinates] = place
            record_key = "hourly_data" if planned_single.requirement == "hourly" else "current_data"
            sources[coordinates] = [{record_key: planned_single.data()}]
    else:
        for msg in (conversation_history or [])[-4:]:
            if isinstance(msg, dict) and msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})
        if request.period != "current":
            messages.append({"role": "system", "content": f"Requested forecast period: {request.period}."})
        if weather_query and executor_fn is None:
            messages.append({"role": "system", "content": (
                "No destination was verified. Ask for the destination and withhold weather claims."
            )})
    messages.append({"role": "user", "content": user_message})
    # The production planner owns weather retrieval. The injected executor still supports legacy tool clients.
    eligible_tools = tools if executor_fn is not None else []
    if eligible_tools and not detailed and intent in {"temperature", "wind_humidity", "rain_check", "current_weather"}:
        retrieval = "get_hourly_forecast" if request.period != "current" or intent == "rain_check" else "get_current_weather"
        eligible_tools = [tool for tool in tools if tool["function"]["name"] in {"geocode_location", retrieval}]
    allowed_tools = {tool["function"]["name"] for tool in eligible_tools}
    tool_options = {"tools": eligible_tools, "tool_choice": "auto"} if eligible_tools else {}
    seen_tool_calls = set()
    declined_tools = False
    rounds = min(max_iterations, budget.limits.tool_rounds)
    risk_results = None

    for iteration in range(rounds):
        is_severe = False
        if risk_results and isinstance(risk_results, dict):
            lvl = risk_results.get("overall_risk_level") or risk_results.get("risk_level")
            if lvl in ("HIGH", "SEVERE"):
                is_severe = True
        current_token_limit = get_token_limit_for_complexity(complexity, is_severe_risk=is_severe)

        try:
            response = await complete(
                f"agent_turn_{iteration + 1}", messages=list(messages),
                max_tokens=current_token_limit, **tool_options,
            )
        except RequestFailure as error:
            logger.warning("AI completion unavailable category=%s", error.category.value)
            if comparison_text is not None and comparison_complete:
                active_tracer.answer_complete = True
                return result(comparison_text, executed_tools, iteration + 1, comparison_evidence, fallback=True)
            raise

        assistant_message = response
        tool_calls = assistant_message.get("tool_calls", [])
        if tool_calls and not allowed_tools:
            active_tracer.suppressed_tools += len(tool_calls)
            if not declined_tools:
                messages.insert(-1, {"role": "system", "content": "Answer directly. Tools are unavailable."})
                declined_tools = True
            continue
        messages.append(assistant_message)

        # If model did not request any tools, we have reached the final answer
        if not tool_calls:
            candidate_response = assistant_message["content"] or ""

            if executed_tools:
                evidence = comparison_evidence or evidence_engine.generate_evidence()
                evidence_ids = set()
                for (latitude, longitude), records in sources.items():
                    place = places.get((latitude, longitude))
                    if place and sum(candidate["name"].casefold() == place["name"].casefold()
                                     for candidate in places.values()) > 1:
                        # The claim has no reliable way to distinguish two places with the same name.
                        continue
                    if place is None:
                        continue
                    for record in records:
                        source = evidence_engine.generate_evidence(location_meta=place, **record)
                        if record.get("hourly_data"):
                            bind_period(
                                source, planned_single.period if planned_single else (
                                    "next_24h" if request.period == "current" else request.period
                                ),
                                len(record["hourly_data"]["hourly"]["time"]),
                            )
                        for item in source.items:
                            item.id = f"{latitude},{longitude}:{item.id}"
                            if item.id not in evidence_ids:
                                evidence_ids.add(item.id)
                                evidence.add(item)
                if len(sources) == 1 and not comparison:
                    evidence.location_name = next(iter(places.values()))["name"] if len(places) == 1 else None

                correction_failure = None

                async def regenerate_fn(prompt: str) -> str:
                    nonlocal correction_failure
                    retry_messages = [message for message in messages if isinstance(message, dict) and
                                      message.get("role") in {"system", "user"}] + [
                        {"role": "user", "content": prompt}
                    ]
                    try:
                        reply = await complete("hallucination_correction", messages=retry_messages,
                                               max_tokens=max(current_token_limit, 500))
                        return reply["content"] or ""
                    except RequestFailure as error:
                        correction_failure = error
                        raise

                t_audit = time.time()
                final_text, report, _ = await hallucination_controller.verify_and_correct(
                    query=user_message,
                    response_text=candidate_response,
                    evidence=evidence,
                    regenerate_fn=regenerate_fn,
                    max_retries=budget.limits.corrections,
                )
                active_tracer.record_span("hallucination_correction", (time.time() - t_audit) * 1000)

                if comparison_text is not None:
                    active_tracer.answer_complete = report.is_trustworthy and all(
                        not requirements("comparison", user_message, forecast=True, risk=data["risk"],
                             components=request.components).omissions(
                            final_text, report, evidence, location=data["location"], period=destination.period,
                        ) for data, destination in zip(comparison_data.values(), plan.destinations)
                    )
                    if not active_tracer.answer_complete:
                        final_text = comparison_text
                        active_tracer.deterministic_fallback = True
                        active_tracer.answer_complete = comparison_complete
                elif planned_single:
                    contract = requirements(intent or "temperature", user_message,
                                            forecast=planned_single.requirement == "hourly", components=request.components)
                    active_tracer.answer_complete = report.is_trustworthy and not contract.omissions(
                        final_text, report, evidence, location=places[coordinates]["name"],
                        period=planned_single.period if planned_single.requirement == "hourly" else None,
                    )
                    if not active_tracer.answer_complete:
                        if correction_failure is not None:
                            raise correction_failure
                        return result("I couldn’t verify a complete answer for the requested weather question.",
                                      executed_tools, iteration + 1, evidence,
                                      outcome=FailureCategory.FORECAST_WINDOW_UNAVAILABLE)
                return result(final_text, executed_tools, iteration + 1, evidence,
                              risk_results if len(sources) == 1 else None,
                              model_draft=not (comparison_text is not None and final_text == comparison_text))

            if weather_query:
                return result("I couldn’t verify weather data for the requested location and period.",
                              iterations=iteration + 1, evidence=evidence_engine.generate_evidence())
            return result(candidate_response, iterations=iteration + 1, model_draft=True)

        # Model requested one or more tool calls
        for tool_call in tool_calls:
            fn_name = tool_call["function"]["name"]
            raw_args = tool_call["function"]["arguments"]

            # 1. Parse arguments safely
            try:
                if isinstance(raw_args, str):
                    parsed_args = json.loads(raw_args)
                elif isinstance(raw_args, dict):
                    parsed_args = raw_args
                else:
                    raise UnsafePayload("Malformed tool arguments.")
                if type(parsed_args) is not dict:
                    raise UnsafePayload("Malformed tool arguments.")
                encode_wire(parsed_args)
            except (ValueError, TypeError, RecursionError):
                logger.warning("Weather tool rejected category=invalid_arguments")
                tool_result = {"error": "Invalid JSON tool arguments."}
                executed_tools.append({
                    "tool": fn_name,
                    "arguments": {},
                    "error": "Invalid JSON tool arguments.",
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": fn_name,
                    "content": json.dumps(tool_result),
                })
                continue

            signature = (fn_name, json.dumps(parsed_args, sort_keys=True, ensure_ascii=False))
            if fn_name not in allowed_tools or signature in seen_tool_calls:
                active_tracer.suppressed_tools += 1
                messages.append({"role": "tool", "tool_call_id": tool_call["id"], "name": fn_name,
                                 "content": '{"status":"unavailable_or_already_supplied"}'})
                continue
            seen_tool_calls.add(signature)

            # 2. Execute tool using existing executor
            t_exec = time.time()
            try:
                if confirmed_place and fn_name == "geocode_location":
                    parsed_args = {"location": request.location}
                    execution_result = confirmed_place
                elif executor_fn is None and comparison and fn_name == "geocode_location":
                    lookup = parsed_args.get("location", "") if isinstance(parsed_args, dict) else ""
                    if isinstance(lookup, str) and drops_comparison_qualifiers(user_message, lookup):
                        raise ValueError("Geocode the place with the comma-separated qualifiers supplied by the user.")
                    raise ValueError("Use one of the destinations resolved by the request planner.")
                elif (executor_fn is None and isinstance(parsed_args, dict)
                      and {"latitude", "longitude"} <= parsed_args.keys()
                      and (parsed_args["latitude"], parsed_args["longitude"]) not in places):
                    raise ValueError("Use coordinates returned by geocoding the requested location first.")
                else:
                    observer_token = weather_http_observer.set(active_tracer.record_weather_http)
                    try:
                        execution_result = await active_executor(fn_name, parsed_args)
                    finally:
                        weather_http_observer.reset(observer_token)
                try:
                    encode_wire(execution_result, MAX_TOOL_REPLY_BYTES)
                except UnsafePayload:
                    active_tracer.suppressed_tools += 1
                    execution_result = {"error": "Tool reply exceeded safe payload limits or was malformed."}
                if execution_result is None:
                    tool_result = {
                        "status": "not_found",
                        "message": "No data found for the requested tool.",
                    }
                else:
                    tool_result = execution_result
            except (TypeError, ValueError) as error:
                logger.warning("Weather tool rejected category=invalid_arguments")
                # Errors raised by the planner use fixed text. Do not expose arbitrary executor errors.
                safe_errors = {
                    "Geocode the place with the comma-separated qualifiers supplied by the user.",
                    "Use one of the destinations resolved by the request planner.",
                    "Use coordinates returned by geocoding the requested location first.",
                }
                tool_result = {"error": str(error) if str(error) in safe_errors else "Invalid weather tool arguments."}
            except httpx.HTTPError:
                active_tracer.record_tool_execution(fn_name, parsed_args, (time.time() - t_exec) * 1000,
                                                    error="tool_failed")
                raise failure(RequestFailure(FailureCategory.WEATHER_PROVIDER_UNAVAILABLE)) from None
            except Exception:
                logger.error("Weather tool failed category=internal_application_error")
                tool_result = {"error": "Weather tool execution failed."}

            exec_ms = (time.time() - t_exec) * 1000
            active_tracer.record_tool_execution(fn_name, parsed_args, exec_ms)

            executed_tools.append({
                "tool": fn_name,
                "arguments": parsed_args,
                "result": tool_result,
            })

            # Associate each tool result with its own coordinates and window.
            compact_payload = create_compact_tool_payload(fn_name, tool_result) if fn_name == "get_current_weather" else tool_result
            if isinstance(parsed_args, dict) and isinstance(tool_result, dict) and not tool_result.get("error"):
                if fn_name == "geocode_location" and {"latitude", "longitude", "name"} <= tool_result.keys():
                    coords = (tool_result["latitude"], tool_result["longitude"])
                    places[coords] = tool_result
                elif {"latitude", "longitude"} <= parsed_args.keys():
                    coords = (parsed_args["latitude"], parsed_args["longitude"])
                    records = sources.setdefault(coords, [])
                    if fn_name == "get_current_weather" and tool_result.get("current"):
                        if request.period == "current":
                            records.append({"current_data": tool_result})
                        else:
                            compact_payload = {"status": "unavailable", "period": request.period}
                    elif fn_name == "get_hourly_forecast" and tool_result.get("hourly"):
                        observed = next((record["current_data"]["current"].get("time")
                                         for record in reversed(records) if "current_data" in record), None)
                        place = places.get(coords, {})
                        forecast = {**tool_result, "timezone": tool_result.get("timezone") or place.get("timezone")}
                        scoped = scope_hourly_forecast(forecast, request.period, observed)
                        if scoped["hourly"].get("time"):
                            records.append({"hourly_data": scoped})
                            compact_payload = create_compact_tool_payload(fn_name, scoped, request.period)
                        else:
                            compact_payload = {"status": "unavailable", "period": request.period}
                    elif fn_name in ("analyze_weather", "get_weather_recommendations", "assess_weather_risks"):
                        offset = parsed_args.get("day_offset", 1)
                        period = {0: "today", 1: "tomorrow"}.get(offset)
                        if period and request.period in {"current", period}:
                            analysis = {"day_analyzed": period, **tool_result}
                            if fn_name == "assess_weather_risks" and "overall_risk_level" in tool_result:
                                risk_results = tool_result
                            records.append({"analysis_results": analysis})
                        else:
                            compact_payload = {"status": "unavailable", "period": request.period}

            try:
                tool_content = encode_wire(compact_payload, MAX_TOOL_REPLY_BYTES)[0]
            except UnsafePayload:
                active_tracer.suppressed_tools += 1
                tool_content = '{"status":"tool_reply_unavailable"}'
            messages.append({
                "role": "tool", "tool_call_id": tool_call["id"], "name": fn_name, "content": tool_content,
            })

    if comparison_text is not None and comparison_complete:
        active_tracer.answer_complete = True
        return result(comparison_text, executed_tools, rounds, comparison_evidence, fallback=True)
    active_tracer.budget_exhausted = True
    raise failure(RequestFailure(FailureCategory.LLM_BUDGET_EXHAUSTED))


class WeatherAgent:
    """Object-oriented wrapper around the Sky Reader agent."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        executor_fn: Optional[Any] = None,
        client: Optional[Any] = None,
    ):
        self.api_key = api_key
        self.model = model
        self.max_iterations = max_iterations
        self.executor_fn = executor_fn
        self.client = client

    async def ask(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        return await run_agent(
            user_message=question,
            conversation_history=conversation_history,
            api_key=self.api_key,
            model=self.model,
            max_iterations=self.max_iterations,
            executor_fn=self.executor_fn,
            client=self.client,
        )
