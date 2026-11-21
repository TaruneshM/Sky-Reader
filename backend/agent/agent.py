import asyncio
import json
import logging
import os
import re
import time
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
        detect_weather_intent,
        extract_location_from_query_or_history,
        synthesize_deterministic_weather_buddy_response,
    )
    from backend.weather.service import (
        geocode_location,
        get_current_weather,
        get_hourly_forecast,
        get_temporal_forecast_slice,
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
        detect_weather_intent,
        extract_location_from_query_or_history,
        synthesize_deterministic_weather_buddy_response,
    )
    from weather.service import (
        geocode_location,
        get_current_weather,
        get_hourly_forecast,
        get_temporal_forecast_slice,
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


def create_compact_tool_payload(fn_name: str, raw_result: Any) -> Any:
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

        # Use temporal forecast slice starting from current hour instead of index 0
        curr_time = raw_result.get("current", {}).get("time", "")
        slice_data = get_temporal_forecast_slice(raw_result, period="current", current_time=curr_time)
        temps = slice_data["temperatures"]
        rain_probs = slice_data["rain_probabilities"]
        rain_amounts = slice_data["rain_amounts"]
        winds = slice_data["wind_speeds"]
        slice_times = slice_data["times"]

        # 24-hour summary metrics
        summary = {
            "min_temp_c": round(min(temps), 1) if temps else None,
            "max_temp_c": round(max(temps), 1) if temps else None,
            "peak_rain_chance_pct": max(rain_probs) if rain_probs else 0,
            "total_precipitation_mm": round(sum(rain_amounts), 2) if rain_amounts else 0.0,
            "max_wind_kmh": round(max(winds), 1) if winds else 0.0,
        }

        # Sample every 3 hours for the next 24 hours
        sampled_checkpoints = []
        for i in range(0, min(24, len(slice_times)), 3):
            sampled_checkpoints.append({
                "time": slice_times[i][-5:],  # HH:MM
                "temp_c": temps[i] if i < len(temps) else None,
                "rain_pct": rain_probs[i] if i < len(rain_probs) else None,
                "rain_mm": rain_amounts[i] if i < len(rain_amounts) else None,
                "wind_kmh": winds[i] if i < len(winds) else None,
            })

        return {
            "summary_next_24h": summary,
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
    t_start = time.time()
    active_model = model or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)
    active_client = client or get_groq_client(api_key=api_key)
    active_executor = executor_fn or execute_tool

    # Evidence and verification engines (Phases 3–7)
    evidence_engine = EvidenceEngine()
    hallucination_controller = HallucinationController()
    explanation_engine = ExplanationEngine()

    # -------------------------------------------------------------
    # 1. Deterministic Intent Routing & Context Extraction (Task 2)
    # -------------------------------------------------------------
    t_parse_start = time.time()
    intent = detect_weather_intent(user_message)
    resolved_location = extract_location_from_query_or_history(user_message, conversation_history)
    complexity = classify_query_complexity(user_message)
    active_tracer.record_span("parsing_and_routing", (time.time() - t_parse_start) * 1000)

    # -------------------------------------------------------------
    # 2. Fast Path: Deterministic Query Resolution (Single Turn)
    # -------------------------------------------------------------
    # Only activate fast path if executor_fn is None (production runtime).
    # When executor_fn is provided (e.g. benchmark synthetic fixtures), preserve full agentic loop.
    if intent and resolved_location and executor_fn is None:
        logger.info("Fast path triggered: intent='%s', location='%s'", intent, resolved_location)
        t_tools_start = time.time()
        place = await geocode_location(resolved_location)
        active_tracer.record_tool_execution(
            "geocode_location", {"location": resolved_location},
            (time.time() - t_tools_start) * 1000, cached=True
        )

        if place:
            lat = place["latitude"]
            lon = place["longitude"]
            loc_name = place["name"]

            # Fetch necessary weather data according to intent
            t_curr = time.time()
            current_data = await get_current_weather(lat, lon)
            active_tracer.record_tool_execution(
                "get_current_weather", {"latitude": lat, "longitude": lon},
                (time.time() - t_curr) * 1000, cached=True
            )

            hourly_data = None
            hourly_slice = None
            analysis_results = None
            risk_results = None

            if intent in ("rain_check", "umbrella", "tomorrow_forecast", "morning_walk", "weather_risks"):
                t_hour = time.time()
                hourly_data = await get_hourly_forecast(lat, lon)
                active_tracer.record_tool_execution(
                    "get_hourly_forecast", {"latitude": lat, "longitude": lon},
                    (time.time() - t_hour) * 1000, cached=True
                )
                period_name = "tomorrow" if intent == "tomorrow_forecast" else "current"
                hourly_slice = get_temporal_forecast_slice(hourly_data, period=period_name)

                if intent in ("umbrella", "morning_walk", "rain_check", "tomorrow_forecast"):
                    day_off = 1 if intent == "tomorrow_forecast" else 0
                    analysis_results = get_weather_decision_support(hourly_data, day_offset=day_off)

            if intent == "weather_risks" and hourly_data:
                risk_results = WeatherRiskEngine().assess_risks(hourly_data, location_name=loc_name).dict()

            # Compile evidence collection deterministically
            evidence = evidence_engine.generate_evidence(
                current_data=current_data,
                hourly_data=hourly_data,
                location_meta=place,
                analysis_results=analysis_results,
            )

            # Try single fast LLM synthesis call
            candidate_response = None
            curr_c = (current_data or {}).get("current", {})
            rain_prob_val = 0
            if hourly_slice and hourly_slice.get("rain_probabilities"):
                rain_prob_val = max(hourly_slice["rain_probabilities"])

            facts_summary = (
                f"Location: {loc_name}. Current Temp: {curr_c.get('temperature_2m')}°C "
                f"(feels like {curr_c.get('apparent_temperature')}°C). "
                f"Humidity: {curr_c.get('relative_humidity_2m')}%. Wind: {curr_c.get('wind_speed_10m')} km/h. "
                f"Precipitation probability: {rain_prob_val}%."
            )

            synthesis_prompt = [
                {"role": "system", "content": WEATHER_BUDDY_SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"User question: '{user_message}'\n"
                    f"Verified meteorological facts for {loc_name}:\n{facts_summary}\n"
                    f"Answer directly in 1–2 friendly conversational sentences with an emoji. Ground facts strictly. No tables."
                )}
            ]

            t_llm = time.time()
            try:
                llm_resp = await active_client.chat.completions.create(
                    model=active_model,
                    messages=synthesis_prompt,
                    max_tokens=250,
                    temperature=0.3,
                )
                llm_time = (time.time() - t_llm) * 1000
                prompt_toks = getattr(llm_resp.usage, "prompt_tokens", 0) or 0
                comp_toks = getattr(llm_resp.usage, "completion_tokens", 0) or 0
                tot_toks = getattr(llm_resp.usage, "total_tokens", 0) or 0
                active_tracer.record_llm_call(
                    model=active_model,
                    latency_ms=llm_time,
                    prompt_tokens=prompt_toks,
                    completion_tokens=comp_toks,
                    total_tokens=tot_toks,
                    call_purpose="fast_path_synthesis"
                )
                candidate_response = llm_resp.choices[0].message.content or ""
            except (RateLimitError, GroqError) as ge:
                logger.warning("Groq unavailable on fast path (%s), generating deterministic Weather Buddy output", ge)
                active_tracer.record_llm_call(
                    model=active_model,
                    latency_ms=(time.time() - t_llm) * 1000,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    finish_reason="rate_limited_fallback",
                    call_purpose="fallback"
                )
                candidate_response = synthesize_deterministic_weather_buddy_response(
                    intent=intent,
                    location_name=loc_name,
                    current_data=current_data,
                    hourly_slice=hourly_slice,
                    risk_data=risk_results,
                    recommendations_data=analysis_results,
                )

            # Audit and validate candidate response through Phase 4/5 engines
            t_eval = time.time()
            claims = hallucination_controller.extractor.extract_claims(candidate_response, default_location=loc_name)
            val_results = hallucination_controller.validator.validate_all(claims, evidence)
            report = hallucination_controller.evaluate_claims(val_results)
            active_tracer.record_span("claim_validation", (time.time() - t_eval) * 1000)

            # If ungrounded, use safe fallback directly from verified evidence
            final_text = candidate_response
            if not report.is_trustworthy:
                final_text = hallucination_controller.generate_safe_fallback(user_message, evidence, report)
                fb_claims = hallucination_controller.extractor.extract_claims(final_text, default_location=loc_name)
                fb_results = hallucination_controller.validator.validate_all(fb_claims, evidence)
                report = hallucination_controller.evaluate_claims(fb_results)

            proof = explanation_engine.generate_proof(
                query=user_message,
                response_text=final_text,
                evidence=evidence,
                report=report,
                validation_results=val_results,
            )

            executed_tools = [
                {"tool": "geocode_location", "arguments": {"location": resolved_location}, "result": place},
                {"tool": "get_current_weather", "arguments": {"latitude": lat, "longitude": lon}, "result": current_data},
            ]
            if hourly_data:
                executed_tools.append({"tool": "get_hourly_forecast", "arguments": {"latitude": lat, "longitude": lon}, "result": hourly_data})

            summary = active_tracer.get_summary()
            return {
                "response": final_text,
                "tool_calls": executed_tools,
                "iterations": 1,
                "claims": [c.dict() for c in claims],
                "validation_report": report.dict(),
                "explanation": proof.dict(),
                "risk_assessment": risk_results,
                "token_usage": summary,
            }

    # -------------------------------------------------------------
    # 3. Agentic Workflow (For Complex, Multi-City, or Open Queries)
    # -------------------------------------------------------------
    dynamic_max_tokens = get_token_limit_for_complexity(complexity)

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

    messages.append({"role": "user", "content": user_message})

    executed_tools: List[Dict[str, Any]] = []
    location_meta: Optional[Dict[str, Any]] = None
    current_data: Optional[Dict[str, Any]] = None
    hourly_data: Optional[Dict[str, Any]] = None
    analysis_results: Optional[Dict[str, Any]] = None
    risk_results: Optional[Dict[str, Any]] = None

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

            # If weather tools were executed, run evidence generation & validation
            if current_data or hourly_data or analysis_results:
                loc_meta = location_meta
                if not loc_meta and executed_tools:
                    for ex in executed_tools:
                        args = ex.get("arguments", {})
                        if isinstance(args, dict) and "location" in args:
                            loc_meta = {"name": args["location"]}
                            break

                evidence = evidence_engine.generate_evidence(
                    current_data=current_data,
                    hourly_data=hourly_data,
                    location_meta=loc_meta,
                    analysis_results=analysis_results,
                )

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

                claims = hallucination_controller.extractor.extract_claims(
                    final_text, default_location=evidence.location_name
                )
                val_results = hallucination_controller.validator.validate_all(claims, evidence)
                proof = explanation_engine.generate_proof(
                    query=user_message,
                    response_text=final_text,
                    evidence=evidence,
                    report=report,
                    validation_results=val_results,
                )

                summary = active_tracer.get_summary()
                return {
                    "response": final_text,
                    "tool_calls": executed_tools,
                    "iterations": iteration + 1,
                    "claims": [c.dict() for c in claims],
                    "validation_report": report.dict(),
                    "explanation": proof.dict(),
                    "risk_assessment": risk_results,
                    "token_usage": summary,
                }

            summary = active_tracer.get_summary()
            return {
                "response": candidate_response,
                "tool_calls": executed_tools,
                "iterations": iteration + 1,
                "claims": [],
                "validation_report": None,
                "explanation": None,
                "risk_assessment": risk_results,
                "token_usage": summary,
            }

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

            # Record full evidence sources for deterministic verification engines
            if fn_name == "geocode_location" and isinstance(tool_result, dict) and "latitude" in tool_result:
                location_meta = tool_result
            elif fn_name == "get_current_weather" and isinstance(tool_result, dict):
                current_data = tool_result
            elif fn_name == "get_hourly_forecast" and isinstance(tool_result, dict):
                hourly_data = tool_result
            elif fn_name in ("analyze_weather", "get_weather_recommendations") and isinstance(tool_result, dict):
                if analysis_results is None:
                    analysis_results = {}
                analysis_results.update(tool_result)
            elif fn_name == "assess_weather_risks" and isinstance(tool_result, dict):
                risk_results = tool_result
                if analysis_results is None:
                    analysis_results = {}
                analysis_results["risk_assessment"] = tool_result

            # Compact representation sent back to Groq to conserve tokens
            compact_payload = create_compact_tool_payload(fn_name, tool_result)

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
