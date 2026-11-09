import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

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
    from backend.evidence.evidence_engine import EvidenceEngine
    from backend.evidence.hallucination_controller import HallucinationController
    from backend.evidence.explanation_engine import ExplanationEngine
except ImportError:
    from agent.tools import tools
    from agent.executor import execute_tool
    from evidence.evidence_engine import EvidenceEngine
    from evidence.hallucination_controller import HallucinationController
    from evidence.explanation_engine import ExplanationEngine

logger = logging.getLogger(__name__)

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_MAX_ITERATIONS = 10

SYSTEM_PROMPT = (
    "You are Sky Reader, an intelligent agentic AI weather intelligence and reasoning system. "
    "Your goal is to answer users' weather questions, analyze trends, interpret meteorological patterns, "
    "and provide evidence-based decision support using real-time data from Open-Meteo via your tools.\n\n"
    "Guidelines:\n"
    "1. Always geocode a place name first using 'geocode_location' to obtain its latitude and longitude.\n"
    "2. For basic current conditions, use 'get_current_weather'.\n"
    "3. For raw hourly forecasts, use 'get_hourly_forecast'.\n"
    "4. For analytical or trend questions (e.g. temperature trends, increasing/decreasing temperatures, precipitation breakdown, wind analysis, today vs tomorrow comparisons), call 'analyze_weather'.\n"
    "5. For practical advice and decision support (e.g. should I carry an umbrella, is it good for travelling, best time for outdoor activities, rain timing), call 'get_weather_recommendations'.\n"
    "6. Ground all analytical statements and recommendations in the actual data returned by the tools. Clearly communicate uncertainty (forecasts are probabilities, not guarantees) and never invent measurements.\n"
    "7. For general queries unrelated to weather, answer directly without invoking tools.\n"
    "8. If a location cannot be found or tool execution fails, explain the issue politely to the user."
)


def get_groq_client(api_key: Optional[str] = None) -> AsyncGroq:
    """
    Initializes and returns an AsyncGroq client with the provided API key
    or from the GROQ_API_KEY environment variable.
    """
    key = os.getenv("GROQ_API_KEY") if api_key is None else api_key
    if not key or not key.strip():
        raise ValueError(
            "Groq API key is missing. Please set GROQ_API_KEY in backend/.env"
        )
    return AsyncGroq(api_key=key.strip())


async def run_agent(
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> Dict[str, Any]:
    """
    Runs the agentic tool-calling loop using Groq and Open-Meteo weather tools.

    Args:
        user_message: The natural-language query from the user.
        conversation_history: Optional list of previous chat messages.
        api_key: Optional Groq API key override.
        model: Optional model name override (defaults to GROQ_MODEL or DEFAULT_GROQ_MODEL).
        max_iterations: Maximum tool-call cycles before terminating.

    Returns:
        Dict with keys 'response', 'tool_calls', and 'iterations'.
    """
    active_model = model or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)
    client = get_groq_client(api_key=api_key)

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    if conversation_history:
        for msg in conversation_history:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    executed_tools: List[Dict[str, Any]] = []
    location_meta: Optional[Dict[str, Any]] = None
    current_data: Optional[Dict[str, Any]] = None
    hourly_data: Optional[Dict[str, Any]] = None
    analysis_results: Optional[Dict[str, Any]] = None

    evidence_engine = EvidenceEngine()
    hallucination_controller = HallucinationController()
    explanation_engine = ExplanationEngine()

    for iteration in range(max_iterations):
        attempts = 0
        response = None
        while attempts < 3:
            try:
                response = await client.chat.completions.create(
                    model=active_model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )
                break
            except RateLimitError as rle:
                attempts += 1
                if attempts >= 3:
                    logger.error("Rate limit exceeded 3 times: %s", rle)
                    raise
                logger.warning("Rate limit hit, sleeping 10s before retry %d/3...", attempts)
                await asyncio.sleep(10)
            except GroqError as ge:
                logger.error("Groq API error during completion: %s", ge)
                raise

        if response is None:
            raise RuntimeError("Failed to obtain response from Groq.")

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
                    reg_resp = await client.chat.completions.create(
                        model=active_model,
                        messages=retry_messages,
                    )
                    return reg_resp.choices[0].message.content or ""

                final_text, report, _ = await hallucination_controller.verify_and_correct(
                    query=user_message,
                    response_text=candidate_response,
                    evidence=evidence,
                    regenerate_fn=regenerate_fn,
                    max_retries=1,
                )

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

                return {
                    "response": final_text,
                    "tool_calls": executed_tools,
                    "iterations": iteration + 1,
                    "claims": [c.dict() for c in claims],
                    "validation_report": report.dict(),
                    "explanation": proof.dict(),
                }

            return {
                "response": candidate_response,
                "tool_calls": executed_tools,
                "iterations": iteration + 1,
                "claims": [],
                "validation_report": None,
                "explanation": None,
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
            try:
                execution_result = await execute_tool(fn_name, parsed_args)
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

            executed_tools.append({
                "tool": fn_name,
                "arguments": parsed_args,
                "result": tool_result,
            })

            # Record evidence sources
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

            # Send tool response back to Groq
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": fn_name,
                "content": json.dumps(tool_result, default=str),
            })

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
    }


class WeatherAgent:
    """Object-oriented wrapper around the Sky Reader agent."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
    ):
        self.api_key = api_key
        self.model = model
        self.max_iterations = max_iterations

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
        )
