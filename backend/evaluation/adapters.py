import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

try:
    from backend.agent.agent import SYSTEM_PROMPT, DEFAULT_GROQ_MODEL, get_groq_client, run_agent
    from backend.agent.tools import (
        tools,
        location_tool,
        weather_tool,
        forecast_tool,
    )
    from backend.agent.executor import execute_tool
    from backend.weather.analysis import analyze_weather_data, get_weather_decision_support
    from backend.weather.risk_engine import WeatherRiskEngine
    from backend.evaluation.models import TestCase, WeatherFixture, ApplicableSystem
    from backend.evaluation.result_models import EvaluationResult, ExecutionStatus, FixtureMode
    from backend.evaluation.config import EvaluationConfig
except ImportError:
    from agent.agent import SYSTEM_PROMPT, DEFAULT_GROQ_MODEL, get_groq_client, run_agent
    from agent.tools import (
        tools,
        location_tool,
        weather_tool,
        forecast_tool,
    )
    from agent.executor import execute_tool
    from weather.analysis import analyze_weather_data, get_weather_decision_support
    from weather.risk_engine import WeatherRiskEngine
    from evaluation.models import TestCase, WeatherFixture, ApplicableSystem
    from evaluation.result_models import EvaluationResult, ExecutionStatus, FixtureMode
    from evaluation.config import EvaluationConfig

logger = logging.getLogger(__name__)

BASELINE_SYSTEM_PROMPT = (
    "You are an AI assistant. Answer the user's weather question based strictly on your general knowledge. "
    "You do NOT have access to live weather tools, weather databases, or current sensor observations. "
    "If a question requires real-time, current, or specific local forecast observations that you do not know, "
    "state your limitations clearly and do not invent specific current measurements."
)

RETRIEVAL_TOOLS = [
    location_tool,
    weather_tool,
    forecast_tool,
]

TOOL_AGENT_SYSTEM_PROMPT = (
    "You are an AI weather assistant equipped with weather retrieval tools. "
    "Your goal is to answer users' weather questions using meteorological observations retrieved via your tools.\n\n"
    "Guidelines:\n"
    "1. Always geocode a place name first using 'geocode_location' to obtain its latitude and longitude.\n"
    "2. For basic current conditions, use 'get_current_weather'.\n"
    "3. For raw hourly forecasts, use 'get_hourly_forecast'.\n"
    "4. Answer clearly based on the retrieved weather data.\n"
    "5. For general queries unrelated to weather, answer directly without invoking tools.\n"
    "6. If a location cannot be found or tool execution fails, explain the issue politely to the user."
)


class FixtureToolExecutor:
    """
    Dependency-injected tool executor backed deterministically by a synthetic WeatherFixture.
    Ensures benchmark evaluations never leak to live APIs and never fabricate missing fixture data.
    """

    def __init__(self, fixture: Optional[WeatherFixture] = None):
        self.fixture = fixture
        self.invoked_calls: List[Dict[str, Any]] = []
        self.risk_engine = WeatherRiskEngine()

    async def __call__(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        self.invoked_calls.append({"tool": tool_name, "arguments": arguments})

        if tool_name == "geocode_location":
            req_loc = str(arguments.get("location", "")).lower()
            if self.fixture and self.fixture.location:
                fix_loc_name = str(self.fixture.location.get("name", "")).lower()
                # Match location if fixture name matches or if fixture is assigned to this test
                if fix_loc_name in req_loc or req_loc in fix_loc_name or not req_loc:
                    return self.fixture.location
                # If specific location does not match fixture (e.g. fictional place), return None
                return None
            return None

        if not self.fixture:
            return {"status": "not_found", "message": f"No weather fixture available for tool '{tool_name}'"}

        if tool_name == "get_current_weather":
            if not self.fixture.current:
                return {"status": "not_found", "message": "No current weather in fixture."}
            loc = self.fixture.location or {}
            return {
                "latitude": loc.get("latitude", 0.0),
                "longitude": loc.get("longitude", 0.0),
                "current": self.fixture.current,
            }

        if tool_name == "get_hourly_forecast":
            if not self.fixture.hourly:
                return {"status": "not_found", "message": "No hourly forecast in fixture."}
            loc = self.fixture.location or {}
            return {
                "latitude": loc.get("latitude", 0.0),
                "longitude": loc.get("longitude", 0.0),
                "hourly": self.fixture.hourly,
            }

        if tool_name == "get_daily_forecast":
            loc = self.fixture.location or {}
            return {
                "latitude": loc.get("latitude", 0.0),
                "longitude": loc.get("longitude", 0.0),
                "daily": {},
            }

        if tool_name == "analyze_weather":
            if not self.fixture.hourly:
                return {"status": "error", "message": "No hourly forecast data in fixture for analysis."}
            loc = self.fixture.location or {}
            hourly_wrapped = {"latitude": loc.get("latitude", 0.0), "longitude": loc.get("longitude", 0.0), "hourly": self.fixture.hourly}
            focus = arguments.get("focus", "all")
            day_offset = int(arguments.get("day_offset", 1))
            return analyze_weather_data(hourly_wrapped, focus=focus, day_offset=day_offset)

        if tool_name == "get_weather_recommendations":
            if not self.fixture.hourly:
                return {"status": "error", "message": "No hourly forecast data in fixture for recommendations."}
            loc = self.fixture.location or {}
            hourly_wrapped = {"latitude": loc.get("latitude", 0.0), "longitude": loc.get("longitude", 0.0), "hourly": self.fixture.hourly}
            day_offset = int(arguments.get("day_offset", 1))
            return get_weather_decision_support(hourly_wrapped, day_offset=day_offset)

        if tool_name == "assess_weather_risks":
            if not self.fixture.hourly:
                return {"status": "error", "message": "No hourly forecast data in fixture for risk assessment."}
            loc = self.fixture.location or {}
            hourly_wrapped = {"latitude": loc.get("latitude", 0.0), "longitude": loc.get("longitude", 0.0), "hourly": self.fixture.hourly}
            day_offset = int(arguments.get("day_offset", 1))
            assessment = self.risk_engine.assess_risks(
                hourly_wrapped, day_offset=day_offset, location_name=loc.get("name")
            )
            return assessment.dict()

        raise ValueError(f"Unknown tool requested from FixtureToolExecutor: {tool_name}")


class BaseSystemAdapter:
    """Base evaluation adapter interface for benchmark systems."""
    system_name: str = "base"

    def __init__(self, config: EvaluationConfig, client: Optional[Any] = None):
        self.config = config
        self.client = client

    def get_client(self) -> Any:
        if self.client is not None:
            return self.client
        return get_groq_client(api_key=self.config.api_key)

    async def execute(
        self,
        test_case: TestCase,
        run_id: str,
        fixture: Optional[WeatherFixture] = None,
    ) -> EvaluationResult:
        raise NotImplementedError


class BaselineLLMAdapter(BaseSystemAdapter):
    """
    System A: Baseline LLM without weather tools or external data access.
    Evaluates un-grounded, zero-tool LLM capabilities and hallucination tendencies.
    """
    system_name = ApplicableSystem.BASELINE_LLM.value

    async def execute(
        self,
        test_case: TestCase,
        run_id: str,
        fixture: Optional[WeatherFixture] = None,
    ) -> EvaluationResult:
        started_at = datetime.now(timezone.utc).isoformat()
        t0 = time.perf_counter()
        client = self.get_client()

        messages = [
            {"role": "system", "content": BASELINE_SYSTEM_PROMPT},
            {"role": "user", "content": test_case.question},
        ]

        retries = 0
        error_type = None
        error_msg = None
        response_text = ""
        status = ExecutionStatus.COMPLETED

        while retries <= self.config.max_retries:
            try:
                task = client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    # STRICT ISOLATION: No tools passed
                )
                resp = await asyncio.wait_for(task, timeout=self.config.timeout_seconds)
                response_text = resp.choices[0].message.content or ""
                break
            except asyncio.TimeoutError:
                status = ExecutionStatus.TIMEOUT
                error_type = "TimeoutError"
                error_msg = f"Baseline execution timed out after {self.config.timeout_seconds}s."
                break
            except Exception as e:
                retries += 1
                error_type = type(e).__name__
                error_msg = str(e)
                if retries > self.config.max_retries:
                    status = ExecutionStatus.FAILED
                    break
                await asyncio.sleep(self.config.retry_backoff_seconds * retries)

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        completed_at = datetime.now(timezone.utc).isoformat()

        return EvaluationResult(
            run_id=run_id,
            test_case_id=test_case.id,
            system=self.system_name,
            category=test_case.category.value,
            question=test_case.question,
            response=response_text,
            execution_status=status,
            error_type=error_type,
            error_message=error_msg,
            model_identifier=self.config.model,
            provider="groq",
            started_at=started_at,
            completed_at=completed_at,
            latency_ms=latency_ms,
            retry_count=retries,
            tool_calls=[],
            fixture_id=None,  # Baseline never accesses fixtures
            fixture_mode=FixtureMode.NONE,
            claims=None,
            validation_report=None,
            explanation=None,
            risk_assessment=None,
            execution_metadata={"tools_enabled": False},
        )


class ToolUsingAgentAdapter(BaseSystemAdapter):
    """
    System B: Tool-Using Agent with weather retrieval tools but WITHOUT Sky Reader's Phase 4
    evidence validation, claim audit, hallucination correction, or explanation proof guardrails.
    """
    system_name = ApplicableSystem.TOOL_USING_AGENT.value

    def __init__(
        self,
        config: EvaluationConfig,
        client: Optional[Any] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ):
        super().__init__(config, client=client)
        self.tools = tools if tools is not None else RETRIEVAL_TOOLS
        self.system_prompt = system_prompt or TOOL_AGENT_SYSTEM_PROMPT

    async def execute(
        self,
        test_case: TestCase,
        run_id: str,
        fixture: Optional[WeatherFixture] = None,
    ) -> EvaluationResult:
        started_at = datetime.now(timezone.utc).isoformat()
        t0 = time.perf_counter()
        client = self.get_client()

        # Build isolated tool executor
        if self.config.fixture_mode == FixtureMode.SYNTHETIC_FIXTURE:
            executor_fn = FixtureToolExecutor(fixture)
            fixture_mode = FixtureMode.SYNTHETIC_FIXTURE
            fixture_id = test_case.fixture_id
        else:
            executor_fn = execute_tool
            fixture_mode = FixtureMode.LIVE_DATA
            fixture_id = None

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": test_case.question},
        ]

        retries = 0
        error_type = None
        error_msg = None
        response_text = ""
        status = ExecutionStatus.COMPLETED
        executed_tools: List[Dict[str, Any]] = []

        try:
            for _ in range(self.config.max_iterations):
                resp = None
                for attempt in range(self.config.max_retries + 1):
                    try:
                        task = client.chat.completions.create(
                            model=self.config.model,
                            messages=messages,
                            tools=self.tools,
                            tool_choice="auto",
                        )
                        resp = await asyncio.wait_for(task, timeout=self.config.timeout_seconds)
                        break
                    except asyncio.TimeoutError:
                        raise
                    except Exception as call_err:
                        if attempt >= self.config.max_retries:
                            raise
                        retries += 1
                        await asyncio.sleep(self.config.retry_backoff_seconds * (attempt + 1))

                if resp is None:
                    break

                msg = resp.choices[0].message
                messages.append(msg)

                if not msg.tool_calls:
                    # Model provided its final answer directly without Phase 4 audit
                    response_text = msg.content or ""
                    break

                for tc_call in msg.tool_calls:
                    fn_name = tc_call.function.name
                    raw_args = tc_call.function.arguments
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except Exception as parse_err:
                        args = {}
                        t_res = {"error": f"JSON parse error: {parse_err}"}
                    else:
                        try:
                            t_res = await executor_fn(fn_name, args)
                        except Exception as exec_err:
                            t_res = {"error": str(exec_err)}

                    executed_tools.append({"tool": fn_name, "arguments": args, "result": t_res})
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc_call.id,
                        "name": fn_name,
                        "content": json.dumps(t_res, default=str),
                    })
            else:
                response_text = "Tool iterations exceeded without final answer."

        except asyncio.TimeoutError:
            status = ExecutionStatus.TIMEOUT
            error_type = "TimeoutError"
            error_msg = f"Tool agent execution timed out after {self.config.timeout_seconds}s."
        except Exception as e:
            status = ExecutionStatus.FAILED
            error_type = type(e).__name__
            error_msg = str(e)

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        completed_at = datetime.now(timezone.utc).isoformat()

        return EvaluationResult(
            run_id=run_id,
            test_case_id=test_case.id,
            system=self.system_name,
            category=test_case.category.value,
            question=test_case.question,
            response=response_text,
            execution_status=status,
            error_type=error_type,
            error_message=error_msg,
            model_identifier=self.config.model,
            provider="groq",
            started_at=started_at,
            completed_at=completed_at,
            latency_ms=latency_ms,
            retry_count=retries,
            tool_calls=executed_tools,
            fixture_id=fixture_id,
            fixture_mode=fixture_mode,
            claims=None,  # STRICT ISOLATION: No claim extraction
            validation_report=None,  # STRICT ISOLATION: No validation report
            explanation=None,  # STRICT ISOLATION: No explanation proof
            risk_assessment=None,
            execution_metadata={"tools_enabled": True, "guardrails_enabled": False},
        )


class SkyReaderAdapter(BaseSystemAdapter):
    """
    System C: Complete Sky Reader Platform with tools, meteorological analysis,
    Phase 4 claim extraction & validation, hallucination feedback, explanation proofs,
    and Phase 6 risk assessment.
    """
    system_name = ApplicableSystem.SKY_READER_FULL.value

    async def execute(
        self,
        test_case: TestCase,
        run_id: str,
        fixture: Optional[WeatherFixture] = None,
    ) -> EvaluationResult:
        started_at = datetime.now(timezone.utc).isoformat()
        t0 = time.perf_counter()
        client = self.get_client()

        # Build isolated tool executor
        if self.config.fixture_mode == FixtureMode.SYNTHETIC_FIXTURE:
            executor_fn = FixtureToolExecutor(fixture)
            fixture_mode = FixtureMode.SYNTHETIC_FIXTURE
            fixture_id = test_case.fixture_id
        else:
            executor_fn = execute_tool
            fixture_mode = FixtureMode.LIVE_DATA
            fixture_id = None

        retries = 0
        error_type = None
        error_msg = None
        response_text = ""
        status = ExecutionStatus.COMPLETED
        tool_calls: List[Dict[str, Any]] = []
        claims = None
        val_report = None
        explanation = None
        risk_assessment = None

        try:
            task = run_agent(
                user_message=test_case.question,
                model=self.config.model,
                max_iterations=self.config.max_iterations,
                executor_fn=executor_fn,
                client=client,
            )
            agent_result = await asyncio.wait_for(task, timeout=self.config.timeout_seconds)

            response_text = agent_result.get("response", "")
            tool_calls = agent_result.get("tool_calls", [])
            claims = agent_result.get("claims")
            val_report = agent_result.get("validation_report")
            explanation = agent_result.get("explanation")
            risk_assessment = agent_result.get("risk_assessment")

        except asyncio.TimeoutError:
            status = ExecutionStatus.TIMEOUT
            error_type = "TimeoutError"
            error_msg = f"Sky Reader execution timed out after {self.config.timeout_seconds}s."
        except Exception as e:
            status = ExecutionStatus.FAILED
            error_type = type(e).__name__
            error_msg = str(e)

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        completed_at = datetime.now(timezone.utc).isoformat()

        return EvaluationResult(
            run_id=run_id,
            test_case_id=test_case.id,
            system=self.system_name,
            category=test_case.category.value,
            question=test_case.question,
            response=response_text,
            execution_status=status,
            error_type=error_type,
            error_message=error_msg,
            model_identifier=self.config.model,
            provider="groq",
            started_at=started_at,
            completed_at=completed_at,
            latency_ms=latency_ms,
            retry_count=retries,
            tool_calls=tool_calls,
            fixture_id=fixture_id,
            fixture_mode=fixture_mode,
            claims=claims,
            validation_report=val_report,
            explanation=explanation,
            risk_assessment=risk_assessment,
            execution_metadata={"tools_enabled": True, "guardrails_enabled": True},
        )
