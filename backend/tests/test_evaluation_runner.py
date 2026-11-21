import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from backend.evaluation.config import EvaluationConfig
from backend.evaluation.dataset_loader import load_benchmark_suite
from backend.evaluation.models import ApplicableSystem, BenchmarkCategory
from backend.evaluation.result_models import ExecutionStatus, FixtureMode
from backend.evaluation.result_store import ResultStore
from backend.evaluation.runner import EvaluationRunner, generate_run_id
from backend.evaluation.adapters import (
    BaselineLLMAdapter,
    ToolUsingAgentAdapter,
    SkyReaderAdapter,
    FixtureToolExecutor,
)


class MockMessage:
    def __init__(self, content="", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class MockChoice:
    def __init__(self, message):
        self.message = message


class MockResponse:
    def __init__(self, content="", tool_calls=None):
        self.choices = [MockChoice(MockMessage(content, tool_calls))]


def make_mock_client(responses):
    """
    Creates a mocked AsyncGroq client returning an iterable of mock responses.
    """
    client = MagicMock()
    call_index = 0

    async def mock_create(**kwargs):
        nonlocal call_index
        if call_index >= len(responses):
            return MockResponse(content="Default fallback response")
        resp = responses[call_index]
        call_index += 1
        if isinstance(resp, Exception):
            raise resp
        return resp

    client.chat.completions.create = AsyncMock(side_effect=mock_create)
    return client


class TestEvaluationRunner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.results_dir = Path(self.temp_dir.name)
        self.config = EvaluationConfig(
            results_dir=str(self.results_dir),
            model="mock/test-model",
            timeout_seconds=2.0,
            max_retries=1,
            retry_backoff_seconds=0.01,
            fixture_mode=FixtureMode.SYNTHETIC_FIXTURE,
        )
        self.dataset, self.fixtures = load_benchmark_suite()

    def tearDown(self):
        self.temp_dir.cleanup()

    # -----------------------------------------------------------------
    # 1. Dataset Loading & Selection Filters
    # -----------------------------------------------------------------
    def test_runner_planning_and_filtering(self):
        """Verifies runner plans executions and applies ID, category, and system filters."""
        # A. Filter by single ID
        cfg_id = self.config.model_copy(update={"selected_ids": ["TC-CUR-001"]})
        runner_id = EvaluationRunner(cfg_id)
        plan_id = runner_id.plan_executions(self.dataset, self.fixtures)
        self.assertEqual(len(set(tc.id for tc, _, _ in plan_id)), 1)
        self.assertEqual(plan_id[0][0].id, "TC-CUR-001")
        # By default runs all applicable systems for TC-CUR-001
        self.assertEqual(len(plan_id), 3)

        # B. Filter by Category
        cfg_cat = self.config.model_copy(update={"selected_categories": ["weather_safety_and_risk"]})
        runner_cat = EvaluationRunner(cfg_cat)
        plan_cat = runner_cat.plan_executions(self.dataset, self.fixtures)
        self.assertTrue(all(tc.category == BenchmarkCategory.WEATHER_SAFETY_AND_RISK for tc, _, _ in plan_cat))

        # C. Filter by System
        cfg_sys = self.config.model_copy(update={"selected_systems": ["baseline_llm"]})
        runner_sys = EvaluationRunner(cfg_sys)
        plan_sys = runner_sys.plan_executions(self.dataset, self.fixtures)
        self.assertTrue(all(sys_name == "baseline_llm" for _, sys_name, _ in plan_sys))

        # D. Max cases limit
        cfg_limit = self.config.model_copy(update={"max_cases": 2, "selected_systems": ["sky_reader_full"]})
        runner_limit = EvaluationRunner(cfg_limit)
        plan_limit = runner_limit.plan_executions(self.dataset, self.fixtures)
        self.assertEqual(len(plan_limit), 2)

    # -----------------------------------------------------------------
    # 2. Fixture Injection & Isolation
    # -----------------------------------------------------------------
    def test_fixture_injection_and_isolation(self):
        """Verifies FixtureToolExecutor injects fixture values and never leaks to baseline."""
        fixture = self.fixtures.get("FIX_DEHRADUN_MILD")
        self.assertIsNotNone(fixture)

        executor = FixtureToolExecutor(fixture)

        # Geocode returns fixture location
        geo = asyncio.run(executor("geocode_location", {"location": "Dehradun"}))
        self.assertEqual(geo["name"], "Dehradun")
        self.assertEqual(geo["latitude"], 30.3165)

        # Current weather returns fixture current observations
        cur = asyncio.run(executor("get_current_weather", {"latitude": 30.31, "longitude": 78.03}))
        self.assertEqual(cur["current"]["temperature_2m"], 21.8)

        # Hourly forecast returns fixture hourly
        hly = asyncio.run(executor("get_hourly_forecast", {"latitude": 30.31, "longitude": 78.03}))
        self.assertIn("hourly", hly)
        self.assertEqual(len(hly["hourly"]["time"]), 48)

        # Ungeocodeable location returns None
        geo_unknown = asyncio.run(executor("geocode_location", {"location": "AtlantisFantasy999"}))
        self.assertIsNone(geo_unknown)

    # -----------------------------------------------------------------
    # 3. System Isolation Guarantees
    # -----------------------------------------------------------------
    def test_baseline_system_isolation(self):
        """Verifies BaselineLLMAdapter strictly omits tools, sets fixture_id=None, and does not call executor."""
        mock_client = make_mock_client([MockResponse(content="Baseline estimate of 25°C.")])
        adapter = BaselineLLMAdapter(self.config, client=mock_client)

        tc = self.dataset.get_by_id("TC-CUR-001")
        fixture = self.fixtures.get("FIX_DEHRADUN_MILD")

        res = asyncio.run(adapter.execute(test_case=tc, run_id="test_run", fixture=fixture))

        self.assertEqual(res.execution_status, ExecutionStatus.COMPLETED)
        self.assertEqual(res.system, "baseline_llm")
        self.assertEqual(res.response, "Baseline estimate of 25°C.")
        self.assertEqual(res.tool_calls, [])
        self.assertIsNone(res.fixture_id)  # Never accesses fixture
        self.assertEqual(res.fixture_mode, FixtureMode.NONE)
        self.assertIsNone(res.claims)
        self.assertIsNone(res.validation_report)

        # Verify mock_client was called with NO tools
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        self.assertNotIn("tools", call_kwargs)

    def test_tool_using_agent_isolation(self):
        """Verifies ToolUsingAgentAdapter calls tools but strictly excludes Phase 4 verification guardrails."""
        class MockToolCall:
            def __init__(self):
                self.id = "call_123"
                self.function = MagicMock()
                self.function.name = "get_current_weather"
                self.function.arguments = '{"latitude": 30.3165, "longitude": 78.0322}'

        mock_client = make_mock_client([
            MockResponse(tool_calls=[MockToolCall()]),
            MockResponse(content="Current temperature in Dehradun is 21.8°C."),
        ])
        adapter = ToolUsingAgentAdapter(self.config, client=mock_client)

        tc = self.dataset.get_by_id("TC-CUR-001")
        fixture = self.fixtures.get("FIX_DEHRADUN_MILD")

        res = asyncio.run(adapter.execute(test_case=tc, run_id="test_run", fixture=fixture))

        self.assertEqual(res.execution_status, ExecutionStatus.COMPLETED)
        self.assertEqual(res.system, "tool_using_agent")
        self.assertEqual(len(res.tool_calls), 1)
        self.assertEqual(res.tool_calls[0]["tool"], "get_current_weather")
        self.assertEqual(res.fixture_id, "FIX_DEHRADUN_MILD")
        # STRICT ISOLATION: No claims, validation report, or explanation
        self.assertIsNone(res.claims)
        self.assertIsNone(res.validation_report)
        self.assertIsNone(res.explanation)
        self.assertFalse(res.execution_metadata.get("guardrails_enabled"))

    def test_sky_reader_system_execution(self):
        """Verifies SkyReaderAdapter executes production agent path, calls injected fixture tools, and generates claims/reports."""
        class MockToolCall:
            def __init__(self):
                self.id = "call_sky_1"
                self.function = MagicMock()
                self.function.name = "get_current_weather"
                self.function.arguments = '{"latitude": 30.3165, "longitude": 78.0322}'

        mock_client = make_mock_client([
            MockResponse(tool_calls=[MockToolCall()]),
            MockResponse(content="The current temperature in Dehradun is 21.8 °C."),
        ])
        adapter = SkyReaderAdapter(self.config, client=mock_client)

        tc = self.dataset.get_by_id("TC-CUR-001")
        fixture = self.fixtures.get("FIX_DEHRADUN_MILD")

        res = asyncio.run(adapter.execute(test_case=tc, run_id="test_run", fixture=fixture))

        self.assertEqual(res.execution_status, ExecutionStatus.COMPLETED)
        self.assertEqual(res.system, "sky_reader_full")
        self.assertEqual(len(res.tool_calls), 1)
        self.assertEqual(res.fixture_id, "FIX_DEHRADUN_MILD")
        self.assertTrue(res.execution_metadata.get("guardrails_enabled"))
        # Phase 4 outputs present
        self.assertIsNotNone(res.validation_report)
        self.assertIsNotNone(res.explanation)

    # -----------------------------------------------------------------
    # 4. Error, Timeout, and Retry Handling
    # -----------------------------------------------------------------
    def test_timeout_handling(self):
        """Verifies runner records a TIMEOUT status when execution exceeds timeout."""
        mock_client = MagicMock()

        async def slow_create(**kwargs):
            await asyncio.sleep(5.0)  # Exceeds config.timeout_seconds of 0.2s
            return MockResponse(content="Too late")

        mock_client.chat.completions.create = AsyncMock(side_effect=slow_create)
        cfg_fast = self.config.model_copy(update={"timeout_seconds": 0.1})

        adapter = BaselineLLMAdapter(cfg_fast, client=mock_client)
        tc = self.dataset.get_by_id("TC-CUR-001")

        res = asyncio.run(adapter.execute(test_case=tc, run_id="test_run"))
        self.assertEqual(res.execution_status, ExecutionStatus.TIMEOUT)
        self.assertEqual(res.error_type, "TimeoutError")

    def test_retry_on_transient_failure(self):
        """Verifies adapter retries on transient errors and succeeds if next attempt works."""
        mock_client = make_mock_client([
            RuntimeError("Transient network drop"),
            MockResponse(content="Recovered answer."),
        ])
        adapter = BaselineLLMAdapter(self.config, client=mock_client)
        tc = self.dataset.get_by_id("TC-CUR-001")

        res = asyncio.run(adapter.execute(test_case=tc, run_id="test_run"))
        self.assertEqual(res.execution_status, ExecutionStatus.COMPLETED)
        self.assertEqual(res.response, "Recovered answer.")
        self.assertEqual(res.retry_count, 1)

    # -----------------------------------------------------------------
    # 5. Result Serialization & Store Persistence
    # -----------------------------------------------------------------
    def test_result_persistence_and_interrupted_run(self):
        """Verifies records are persisted incrementally in JSONL and summary in JSON."""
        store = ResultStore(self.results_dir)
        mock_client = make_mock_client([MockResponse(content="Mocked answer")])

        cfg_run = self.config.model_copy(update={
            "selected_ids": ["TC-CUR-001", "TC-CUR-002"],
            "selected_systems": ["baseline_llm"],
        })
        runner = EvaluationRunner(cfg_run, client=mock_client, store=store)

        summary = asyncio.run(runner.run(run_id="run_test_persistence"))

        self.assertEqual(summary.completed_count, 2)
        self.assertEqual(summary.failed_count, 0)

        # Check results.jsonl on disk
        results_file = self.results_dir / "run_test_persistence" / "results.jsonl"
        self.assertTrue(results_file.exists())
        with open(results_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["test_case_id"], "TC-CUR-001")
        self.assertEqual(lines[1]["test_case_id"], "TC-CUR-002")

        # Check summary.json on disk
        summary_file = self.results_dir / "run_test_persistence" / "summary.json"
        self.assertTrue(summary_file.exists())
        loaded_summary = store.load_summary("run_test_persistence")
        self.assertIsNotNone(loaded_summary)
        self.assertEqual(loaded_summary.run_id, "run_test_persistence")

        # Check store list_runs
        runs = store.list_runs()
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["record_count"], 2)


if __name__ == "__main__":
    unittest.main()
