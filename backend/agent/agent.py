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
except ImportError:
    from agent.tools import tools
    from agent.executor import execute_tool

logger = logging.getLogger(__name__)

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_MAX_ITERATIONS = 10

SYSTEM_PROMPT = (
    "You are Sky Reader, an intelligent agentic AI weather assistant. "
    "Your goal is to answer users' weather-related questions accurately using real-time data from Open-Meteo via your tools.\n\n"
    "Guidelines:\n"
    "1. To get weather data for any named place, first invoke 'geocode_location' with the place name to obtain its latitude and longitude.\n"
    "2. Once coordinates are available, call 'get_current_weather' for current conditions, and/or 'get_hourly_forecast' for upcoming forecasts (e.g. tomorrow, upcoming hours, precipitation chances).\n"
    "3. Synthesize the returned data into a clear, concise, and helpful natural-language response. Present figures like temperature, feels-like, humidity, precipitation chances, and wind speed when helpful.\n"
    "4. If a user asks a general question unrelated to weather (e.g., greetings, general knowledge, math), answer directly without calling any tools.\n"
    "5. If a tool reports that a location was not found or an error occurred, explain the situation clearly and politely to the user."
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
                logger.warning("Rate limit hit, sleeping 5s before retry %d/3...", attempts)
                await asyncio.sleep(5)
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
            return {
                "response": assistant_message.content or "",
                "tool_calls": executed_tools,
                "iterations": iteration + 1,
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
