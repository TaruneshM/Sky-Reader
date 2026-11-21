import asyncio
import json
import logging
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv
from groq import AsyncGroq, GroqError, RateLimitError

# Load environment variables securely from backend/.env or root .env
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    load_dotenv(dotenv_path=_env_file)
else:
    load_dotenv()

try:
    from backend.agent.tools import tools
    from backend.agent.executor import execute_tool
    from backend.agent.tracer import LifecycleTracer
    from backend.agent.router import (
        describe_period,
        parse_weather_request,
        weather_facts,
        synthesize_deterministic_weather_buddy_response,
    )
    from backend.weather.service import (
        geocode_location,
        get_current_weather,
        get_hourly_forecast,
        get_temporal_forecast_slice,
        scope_hourly_forecast,
    )
    from backend.weather.analysis import get_weather_decision_support
    from backend.weather.risk_engine import WeatherRiskEngine
    from backend.evidence.evidence_engine import EvidenceEngine
    from backend.evidence.hallucination_controller import HallucinationController
    from backend.evidence.explanation_engine import ExplanationEngine
except ImportError:
    from agent.tools import tools
    from agent.executor import execute_tool
    from agent.tracer import LifecycleTracer
    from agent.router import (
        describe_period,
        parse_weather_request,
        weather_facts,
        synthesize_deterministic_weather_buddy_response,
    )
    from weather.service import (
        geocode_location,
        get_current_weather,
        get_hourly_forecast,
        get_temporal_forecast_slice,
        scope_hourly_forecast,
    )
    from weather.analysis import get_weather_decision_support
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


def drops_comparison_qualifiers(question: str, lookup: str) -> bool:
    def normalize(value):
        value = unicodedata.normalize("NFC", value.casefold())
        return re.sub(r"\s*,\s*", ", ", " ".join(value.split()))

    question, lookup = normalize(question), normalize(lookup)
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


async def run_agent(
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    executor_fn: Optional[Any] = None,
    client: Optional[Any] = None,
    tracer: Optional[LifecycleTracer] = None,
) -> Dict[str, Any]:
    """
    Runs the agentic reasoning and deterministic fast-path routing pipeline.
    Optimized for sub-second latency, bounded token usage, and robust rate-limit handling.
    """
    active_tracer = tracer or LifecycleTracer()
    active_model = model or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)
    active_client = client
    active_executor = executor_fn or execute_tool
    evidence_engine = EvidenceEngine()
    hallucination_controller = HallucinationController()
    explanation_engine = ExplanationEngine()

    def result(text, executed=(), iterations=1, evidence=None, risk=None):
        claims, report, proof = [], None, None
        if evidence is None and executed:
            evidence = evidence_engine.generate_evidence()
        if evidence is not None:
            claims, report = hallucination_controller.audit(text, evidence)
            proof = explanation_engine.generate_proof(user_message, text, evidence, report, report.validation_results)
        return {
            "response": text, "tool_calls": list(executed), "iterations": iterations,
            "claims": [claim.model_dump() for claim in claims],
            "validation_report": report.model_dump() if report is not None else None,
            "explanation": proof.model_dump() if proof is not None else None,
            "risk_assessment": risk, "token_usage": active_tracer.get_summary(),
        }

    t_parse_start = time.time()
    request = parse_weather_request(user_message, conversation_history)
    intent = request.intent
    comparison = bool(re.search(r"\b(compare|versus|vs|which city|difference between)\b", user_message, re.I))
    weather_query = intent or comparison or re.search(
        r"\b(weather|forecast|temperature|rain|wind|humidity)\b", user_message, re.I
    )
    complexity = classify_query_complexity(user_message)
    active_tracer.record_span("parsing_and_routing", (time.time() - t_parse_start) * 1000)

    if request.safety and comparison:
        return result("Which city should I assess first? Weather hazards and activity advice depend on the location.")

    # Historical evaluation injects an executor and exercises the tool loop.
    fast_path = intent and not comparison and (executor_fn is None or request.safety)
    executed_tools: List[Dict[str, Any]] = []

    async def fetch(name, function, **arguments):
        started = time.time()
        output = await (function(**arguments) if executor_fn is None else active_executor(name, arguments))
        executed_tools.append({"tool": name, "arguments": arguments, "result": output})
        active_tracer.record_tool_execution(name, arguments, (time.time() - started) * 1000)
        return output

    def clarify(location):
        return f"I couldn’t resolve {location} to a unique place. Could you specify the city, region, and country?"

    place = None
    if fast_path or (executor_fn is None and weather_query and request.location and not comparison):
        if not request.location:
            return result("Which city and region should I check?")
        place = await fetch("geocode_location", geocode_location, location=request.location)
        if not isinstance(place, dict) or not {"latitude", "longitude", "name"} <= place.keys():
            return result(clarify(request.location), executed_tools)

    if fast_path:
        coordinates = {"latitude": place["latitude"], "longitude": place["longitude"]}
        location = place["name"]
        period = request.period
        use_forecast = period != "current" or intent in {"rain_check", "umbrella", "morning_walk"}
        if period == "current" and use_forecast:
            explicit_now = re.search(r"\b(right now|now|currently|current conditions)\b", user_message, re.I)
            period = "next_1h" if explicit_now else "next_24h"
        current = None
        scoped = None
        window = None
        risk = None
        recommendations = None
        if use_forecast or request.safety:
            hourly = await fetch("get_hourly_forecast", get_hourly_forecast, **coordinates)
            hourly = {**(hourly or {}), "timezone": (hourly or {}).get("timezone") or place.get("timezone")}
            selection = "next_1h" if period == "current" else period
            window = get_temporal_forecast_slice(hourly, selection)
            if not window["available"]:
                return result(f"The requested forecast window ({describe_period(request.period)}) is unavailable in {location}.", executed_tools)
            scoped = scope_hourly_forecast(hourly, selection)
            if request.safety:
                risk_fields = ("temperature_2m", "precipitation", "wind_speed_10m", "wind_gusts_10m", "weather_code")
                if not any(isinstance(value, (int, float)) for key in risk_fields
                           for value in scoped["hourly"].get(key, [])):
                    return result(f"I don’t have enough forecast evidence to assess hazards in {location}.", executed_tools)
                assessment = WeatherRiskEngine().assess_risks(scoped, location_name=location, forecast_period=period)
                risk = assessment.model_dump(mode="json")
            elif intent in {"umbrella", "morning_walk"} and len(window["times"]) == 24 and all(
                values and all(isinstance(value, (int, float)) for value in values)
                for key in ("temperature_2m", "precipitation_probability", "precipitation", "wind_speed_10m", "weather_code")
                for values in [scoped["hourly"].get(key)]
            ):
                recommendations = get_weather_decision_support(scoped, day_offset=0)
        else:
            current = await fetch("get_current_weather", get_current_weather, **coordinates)

        evidence = evidence_engine.generate_evidence(
            current_data=current, hourly_data=scoped, location_meta=place,
            analysis_results={"day_analyzed": period, **(recommendations or {}),
                              **({"risk_assessment": risk} if risk else {})},
        )
        if scoped:
            bind_period(evidence, period, len(window["times"]))

        label = describe_period(period)
        facts = weather_facts(intent, current, window, risk)
        fallback = synthesize_deterministic_weather_buddy_response(
            intent, location, current, window, risk, recommendations, label, request.activity,
        )
        if request.safety or not facts:
            return result(fallback, executed_tools, evidence=evidence, risk=risk)

        prompt = [
            {"role": "system", "content": WEATHER_BUDDY_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({
                "question": user_message, "intent": intent, "activity": request.activity,
                "location": location, "region": place.get("admin1"),
                "country": place.get("country"), "period": label,
                "timezone": (scoped or current or {}).get("timezone") or place.get("timezone"),
                "forecast_hours": window["times"][::max(1, len(window["times"]) - 1)] if window else None,
                "verified_facts": facts,
                "activity_recommendations": recommendations,
                "instruction": "Answer the question in one or two sentences using only these facts. State when the requested measurement is missing.",
            }, ensure_ascii=False)},
        ]
        started = time.time()
        try:
            active_client = active_client or get_groq_client(api_key=api_key)
            response = await active_client.chat.completions.create(
                model=active_model, messages=prompt, max_tokens=250, temperature=0.3,
            )
            active_tracer.record_llm_call(
                model=active_model, latency_ms=(time.time() - started) * 1000,
                prompt_tokens=getattr(response.usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(response.usage, "completion_tokens", 0) or 0,
                total_tokens=getattr(response.usage, "total_tokens", 0) or 0,
                call_purpose="fast_path_synthesis",
            )
            candidate = response.choices[0].message.content or ""
            _, report = hallucination_controller.audit(candidate, evidence)
            if report.is_trustworthy:
                return result(candidate, executed_tools, evidence=evidence)
        except (ValueError, GroqError) as error:
            logger.warning("Fast-path synthesis unavailable: %s", error)
        return result(fallback, executed_tools, evidence=evidence)

    active_client = active_client or get_groq_client(api_key=api_key)
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": WEATHER_BUDDY_SYSTEM_PROMPT}
    ]

    # Bounded conversation history (last 4 turns = 2 exchanges)
    if conversation_history:
        recent_history = conversation_history[-4:]
        for msg in recent_history:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                if msg["role"] in ("user", "assistant") and msg.get("content"):
                    messages.append({"role": msg["role"], "content": msg["content"]})

    if request.period != "current":
        messages.append({"role": "system", "content": (
            f"Requested forecast period: {request.period}. Use that window for every location. "
            "If the tool reports the window unavailable, state that limitation."
        )})
    confirmed_place = place
    places = {}
    if confirmed_place:
        coordinates = (confirmed_place["latitude"], confirmed_place["longitude"])
        places[coordinates] = confirmed_place
        messages.append({"role": "system", "content": (
            "Use this resolved location and its coordinates for all weather tools in this request: "
            + json.dumps(confirmed_place, ensure_ascii=False)
        )})
    elif executor_fn is None and weather_query:
        messages.append({"role": "system", "content": (
            "Geocode each requested place before fetching weather. Submit the full place name with "
            "any qualifiers the user gave. If a place is unresolved, ask the user to clarify."
        )})
    messages.append({"role": "user", "content": user_message})
    sources = {}
    risk_results = None

    for iteration in range(max_iterations):
        is_severe = False
        if risk_results and isinstance(risk_results, dict):
            lvl = risk_results.get("overall_risk_level") or risk_results.get("risk_level")
            if lvl in ("HIGH", "SEVERE"):
                is_severe = True
        current_token_limit = get_token_limit_for_complexity(complexity, is_severe_risk=is_severe)

        # Execute completion with explicit rate-limit handling (Task 4)
        t_call = time.time()
        try:
            response = await active_client.chat.completions.create(
                model=active_model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=current_token_limit,
            )
            call_ms = (time.time() - t_call) * 1000
            usage_obj = getattr(response, "usage", None)
            prompt_toks = getattr(usage_obj, "prompt_tokens", 0) or 0 if usage_obj else 0
            comp_toks = getattr(usage_obj, "completion_tokens", 0) or 0 if usage_obj else 0
            tot_toks = getattr(usage_obj, "total_tokens", 0) or 0 if usage_obj else 0
            active_tracer.record_llm_call(
                model=active_model,
                latency_ms=call_ms,
                prompt_tokens=prompt_toks,
                completion_tokens=comp_toks,
                total_tokens=tot_toks,
                call_purpose=f"agent_turn_{iteration + 1}"
            )
        except RateLimitError as rle:
            err_text = str(rle).lower()
            logger.warning("Groq RateLimitError hit: %s", rle)
            # Check for daily token exhaustion
            is_daily = any(w in err_text for w in ["daily", "tokens per day", "tpd", "200000", "quota"])
            if is_daily:
                active_tracer.record_llm_call(
                    model=active_model, latency_ms=(time.time() - t_call) * 1000,
                    prompt_tokens=0, completion_tokens=0, total_tokens=0,
                    finish_reason="tpd_quota_exhausted", call_purpose="rate_limit"
                )
                return {
                    "response": "Sky Reader has reached its AI usage limit for now 🌤️ Please try again later.",
                    "tool_calls": executed_tools,
                    "iterations": iteration + 1,
                    "claims": [],
                    "validation_report": None,
                    "explanation": None,
                    "risk_assessment": None,
                    "token_usage": active_tracer.get_summary(),
                }

            # For minute limits, short retry if retry-after is small (<= 2s)
            retry_after = getattr(rle, "retry_after", None)
            if retry_after is not None and retry_after <= 2.0:
                await asyncio.sleep(retry_after)
                continue

            # Fall back safely without hanging
            return {
                "response": "Sky Reader has reached its AI usage limit for now 🌤️ Please try again later.",
                "tool_calls": executed_tools,
                "iterations": iteration + 1,
                "claims": [],
                "validation_report": None,
                "explanation": None,
                "risk_assessment": None,
                "token_usage": active_tracer.get_summary(),
            }
        except GroqError as ge:
            logger.error("Groq API error: %s", ge)
            raise

        choice = response.choices[0]
        assistant_message = choice.message
        messages.append(assistant_message)

        # If model did not request any tools, we have reached the final answer
        if not assistant_message.tool_calls:
            candidate_response = assistant_message.content or ""

            if executed_tools:
                evidence = evidence_engine.generate_evidence()
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
                                source, "next_24h" if request.period == "current" else request.period,
                                len(record["hourly_data"]["hourly"]["time"]),
                            )
                        for item in source.items:
                            item.id = f"{latitude},{longitude}:{item.id}"
                            if item.id not in evidence_ids:
                                evidence_ids.add(item.id)
                                evidence.add(item)
                if len(sources) == 1 and not comparison:
                    evidence.location_name = next(iter(places.values()))["name"] if len(places) == 1 else None

                async def regenerate_fn(prompt: str) -> str:
                    retry_messages = list(messages) + [
                        {"role": "user", "content": prompt}
                    ]
                    t_reg = time.time()
                    try:
                        reg_resp = await active_client.chat.completions.create(
                            model=active_model,
                            messages=retry_messages,
                            max_tokens=max(current_token_limit, 500),
                        )
                        reg_ms = (time.time() - t_reg) * 1000
                        reg_usage = getattr(reg_resp, "usage", None)
                        prompt_t = getattr(reg_usage, "prompt_tokens", 0) or 0 if reg_usage else 0
                        comp_t = getattr(reg_usage, "completion_tokens", 0) or 0 if reg_usage else 0
                        tot_t = getattr(reg_usage, "total_tokens", 0) or 0 if reg_usage else 0
                        active_tracer.record_llm_call(
                            model=active_model,
                            latency_ms=reg_ms,
                            prompt_tokens=prompt_t,
                            completion_tokens=comp_t,
                            total_tokens=tot_t,
                            call_purpose="hallucination_correction"
                        )
                        return reg_resp.choices[0].message.content or ""
                    except Exception:
                        return ""

                t_audit = time.time()
                final_text, report, _ = await hallucination_controller.verify_and_correct(
                    query=user_message,
                    response_text=candidate_response,
                    evidence=evidence,
                    regenerate_fn=regenerate_fn,
                    max_retries=1,
                )
                active_tracer.record_span("hallucination_correction", (time.time() - t_audit) * 1000)

                return result(final_text, executed_tools, iteration + 1, evidence,
                              risk_results if len(sources) == 1 else None)

            if weather_query:
                return result("I couldn’t verify weather data for the requested location and period.",
                              iterations=iteration + 1, evidence=evidence_engine.generate_evidence())
            return result(candidate_response, iterations=iteration + 1)

        # Model requested one or more tool calls
        for tool_call in assistant_message.tool_calls:
            fn_name = tool_call.function.name
            raw_args = tool_call.function.arguments

            # 1. Parse arguments safely
            try:
                if isinstance(raw_args, str):
                    parsed_args = json.loads(raw_args)
                elif isinstance(raw_args, dict):
                    parsed_args = raw_args
                else:
                    parsed_args = {}
            except Exception as parse_err:
                logger.warning("Failed to parse tool arguments: %s", raw_args)
                tool_result = {"error": f"Invalid JSON arguments: {raw_args} ({str(parse_err)})"}
                executed_tools.append({
                    "tool": fn_name,
                    "arguments": raw_args,
                    "error": str(parse_err),
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": fn_name,
                    "content": json.dumps(tool_result),
                })
                continue

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
                    execution_result = await active_executor(fn_name, parsed_args)
                elif (executor_fn is None and isinstance(parsed_args, dict)
                      and {"latitude", "longitude"} <= parsed_args.keys()
                      and (parsed_args["latitude"], parsed_args["longitude"]) not in places):
                    raise ValueError("Use coordinates returned by geocoding the requested location first.")
                else:
                    execution_result = await active_executor(fn_name, parsed_args)
                if execution_result is None:
                    tool_result = {
                        "status": "not_found",
                        "message": f"No data found for tool '{fn_name}' with arguments {parsed_args}",
                    }
                else:
                    tool_result = execution_result
            except ValueError as ve:
                logger.warning("ValueError executing %s: %s", fn_name, ve)
                tool_result = {"error": str(ve)}
            except TypeError as te:
                logger.warning("TypeError executing %s: %s", fn_name, te)
                tool_result = {"error": f"Invalid arguments for {fn_name}: {str(te)}"}
            except httpx.HTTPError as he:
                logger.warning("Network error calling %s: %s", fn_name, he)
                tool_result = {"error": f"Weather service network error: {str(he)}"}
            except Exception as e:
                logger.exception("Unexpected error executing %s", fn_name)
                tool_result = {"error": f"Tool execution failed: {str(e)}"}

            exec_ms = (time.time() - t_exec) * 1000
            active_tracer.record_tool_execution(fn_name, parsed_args, exec_ms)

            executed_tools.append({
                "tool": fn_name,
                "arguments": parsed_args,
                "result": tool_result,
            })

            if (executor_fn is None and fn_name == "geocode_location"
                    and tool_result.get("status") == "not_found"):
                return result(clarify(parsed_args["location"]), executed_tools, iteration + 1)

            # Associate each tool result with its own coordinates and window.
            compact_payload = create_compact_tool_payload(fn_name, tool_result) if fn_name == "get_current_weather" else tool_result
            if isinstance(parsed_args, dict) and isinstance(tool_result, dict) and not tool_result.get("error"):
                if fn_name == "geocode_location" and {"latitude", "longitude", "name"} <= tool_result.keys():
                    places[(tool_result["latitude"], tool_result["longitude"])] = tool_result
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

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": fn_name,
                "content": json.dumps(compact_payload, default=str),
            })

    summary = active_tracer.get_summary()
    return {
        "response": (
            "I could not finalize the weather response within the allowed tool execution steps. "
            "Please try refining your question."
        ),
        "tool_calls": executed_tools,
        "iterations": max_iterations,
        "claims": [],
        "validation_report": None,
        "explanation": None,
        "risk_assessment": None,
        "token_usage": summary,
    }


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
