import argparse
import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from backend.evaluation.models import (
        ApplicableSystem,
        BenchmarkCategory,
        EvaluationDataset,
        FixtureCollection,
        TestCase,
        WeatherFixture,
    )
    from backend.evaluation.dataset_loader import load_benchmark_suite
    from backend.evaluation.config import EvaluationConfig, DEFAULT_RESULTS_DIR, DEFAULT_MODEL
    from backend.evaluation.result_models import (
        EvaluationResult,
        ExecutionStatus,
        FixtureMode,
        RunSummary,
    )
    from backend.evaluation.result_store import ResultStore
    from backend.evaluation.adapters import (
        BaselineLLMAdapter,
        ToolUsingAgentAdapter,
        SkyReaderAdapter,
    )
except ImportError:
    from evaluation.models import (
        ApplicableSystem,
        BenchmarkCategory,
        EvaluationDataset,
        FixtureCollection,
        TestCase,
        WeatherFixture,
    )
    from evaluation.dataset_loader import load_benchmark_suite
    from evaluation.config import EvaluationConfig, DEFAULT_RESULTS_DIR, DEFAULT_MODEL
    from evaluation.result_models import (
        EvaluationResult,
        ExecutionStatus,
        FixtureMode,
        RunSummary,
    )
    from evaluation.result_store import ResultStore
    from evaluation.adapters import (
        BaselineLLMAdapter,
        ToolUsingAgentAdapter,
        SkyReaderAdapter,
    )

logger = logging.getLogger(__name__)


def generate_run_id() -> str:
    """Generates a timestamped, collision-free run ID."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    short_uuid = uuid.uuid4().hex[:6]
    return f"run_{ts}_{short_uuid}"


class EvaluationRunner:
    """
    Orchestrates benchmark evaluation runs across baseline LLMs, tool-using agents,
    and the full Sky Reader platform with synthetic fixture injection and isolated result storage.
    """

    def __init__(
        self,
        config: Optional[EvaluationConfig] = None,
        client: Optional[Any] = None,
        store: Optional[ResultStore] = None,
    ):
        self.config = config or EvaluationConfig()
        self.client = client
        self.store = store or ResultStore(Path(self.config.results_dir))

        # Initialize system adapters
        self.adapters = {
            ApplicableSystem.BASELINE_LLM.value: BaselineLLMAdapter(self.config, client=self.client),
            ApplicableSystem.TOOL_USING_AGENT.value: ToolUsingAgentAdapter(self.config, client=self.client),
            ApplicableSystem.SKY_READER_FULL.value: SkyReaderAdapter(self.config, client=self.client),
        }

    def plan_executions(
        self,
        dataset: EvaluationDataset,
        fixtures: FixtureCollection,
    ) -> List[Tuple[TestCase, str, Optional[WeatherFixture]]]:
        """
        Builds the ordered list of (test_case, system_name, fixture) execution tuples
        based on configuration filters.
        """
        cases = dataset.test_cases

        # 1. Filter by specific test IDs
        if self.config.selected_ids:
            target_ids = {i.strip() for i in self.config.selected_ids}
            cases = [tc for tc in cases if tc.id in target_ids]

        # 2. Filter by category
        if self.config.selected_categories:
            target_cats = {c.strip().lower() for c in self.config.selected_categories}
            cases = [tc for tc in cases if tc.category.value.lower() in target_cats]

        # 3. Limit case count if specified
        if self.config.max_cases and self.config.max_cases > 0:
            cases = cases[:self.config.max_cases]

        planned: List[Tuple[TestCase, str, Optional[WeatherFixture]]] = []

        for tc in cases:
            # Determine which systems to evaluate
            if self.config.selected_systems:
                target_systems = [s.strip().lower() for s in self.config.selected_systems]
            else:
                target_systems = [s.value for s in tc.applicable_systems]

            fixture = fixtures.get(tc.fixture_id) if tc.fixture_id else None

            for sys_name in target_systems:
                if sys_name in self.adapters:
                    planned.append((tc, sys_name, fixture))

        return planned

    async def run(
        self,
        run_id: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, EvaluationResult], None]] = None,
    ) -> RunSummary:
        """
        Executes the planned evaluation session and persists results.
        """
        active_run_id = run_id or generate_run_id()
        started_at = datetime.now(timezone.utc).isoformat()

        dataset, fixtures = load_benchmark_suite(
            dataset_path=self.config.dataset_path,
            fixtures_path=self.config.fixtures_path,
        )

        plan = self.plan_executions(dataset, fixtures)
        total_tasks = len(plan)
        distinct_cases = len(set(tc.id for tc, _, _ in plan))

        completed_count = 0
        failed_count = 0
        timeout_count = 0
        skipped_count = 0
        executed_systems = sorted(list(set(sys_name for _, sys_name, _ in plan)))
        executed_categories = sorted(list(set(tc.category.value for tc, _, _ in plan)))

        # Handle Dry-Run mode
        if self.config.dry_run:
            print(f"\n[DRY RUN] Evaluation Plan for {active_run_id}:")
            print(f"  Selected Test Cases: {distinct_cases}")
            print(f"  Total System Executions Planned: {total_tasks}")
            print(f"  Systems: {executed_systems}")
            print(f"  Categories: {executed_categories}")
            for idx, (tc, sys_name, fix) in enumerate(plan, start=1):
                fix_desc = fix.fixture_id if fix else "None"
                print(f"  [{idx}/{total_tasks}] {tc.id} ({tc.category.value}) -> System: {sys_name} [Fixture: {fix_desc}]")

            return RunSummary(
                run_id=active_run_id,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
                total_cases_selected=distinct_cases,
                total_executions=total_tasks,
                completed_count=0,
                failed_count=0,
                timeout_count=0,
                skipped_count=total_tasks,
                systems_evaluated=executed_systems,
                categories_evaluated=executed_categories,
                config=self.config.model_dump(),
            )

        print(f"\nStarting Evaluation Run: {active_run_id}")
        print(f"Total tasks: {total_tasks} ({distinct_cases} cases x systems)\n")

        for idx, (tc, sys_name, fixture) in enumerate(plan, start=1):
            adapter = self.adapters[sys_name]
            print(f"[{idx}/{total_tasks}] Running {tc.id} on system '{sys_name}'...", end=" ", flush=True)

            try:
                res = await adapter.execute(test_case=tc, run_id=active_run_id, fixture=fixture)
            except Exception as e:
                # Top-level safety: record unexpected adapter crashes as failed results
                res = EvaluationResult(
                    run_id=active_run_id,
                    test_case_id=tc.id,
                    system=sys_name,
                    category=tc.category.value,
                    question=tc.question,
                    response="",
                    execution_status=ExecutionStatus.FAILED,
                    error_type=type(e).__name__,
                    error_message=f"Fatal runner exception: {e}",
                    model_identifier=self.config.model,
                    provider="groq",
                    started_at=datetime.now(timezone.utc).isoformat(),
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    latency_ms=0.0,
                    retry_count=0,
                    tool_calls=[],
                    fixture_id=tc.fixture_id,
                    fixture_mode=self.config.fixture_mode,
                )

            # Persist immediately to prevent loss on interruption
            self.store.save_result(res)

            if res.execution_status == ExecutionStatus.COMPLETED:
                completed_count += 1
                print(f"DONE ({res.latency_ms:.0f}ms)")
            elif res.execution_status == ExecutionStatus.TIMEOUT:
                timeout_count += 1
                print("TIMEOUT")
            else:
                failed_count += 1
                print(f"FAILED ({res.error_type}: {res.error_message})")

            if progress_callback:
                progress_callback(idx, total_tasks, res)

        completed_at = datetime.now(timezone.utc).isoformat()

        summary = RunSummary(
            run_id=active_run_id,
            started_at=started_at,
            completed_at=completed_at,
            total_cases_selected=distinct_cases,
            total_executions=total_tasks,
            completed_count=completed_count,
            failed_count=failed_count,
            timeout_count=timeout_count,
            skipped_count=skipped_count,
            systems_evaluated=executed_systems,
            categories_evaluated=executed_categories,
            config=self.config.model_dump(),
        )

        self.store.save_summary(summary)
        print(f"\nRun Completed! Summary saved to {self.store._get_run_dir(active_run_id) / 'summary.json'}")
        print(f"Results: {completed_count} completed, {failed_count} failed, {timeout_count} timed out.")
        return summary


def parse_cli_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sky Reader Phase 7.2 Benchmark Evaluation Runner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all benchmark test cases across applicable systems.",
    )
    parser.add_argument(
        "--system",
        choices=["baseline_llm", "tool_using_agent", "sky_reader_full"],
        help="Run only the specified evaluation system.",
    )
    parser.add_argument(
        "--ids",
        type=str,
        help="Comma-separated test case IDs to execute (e.g. TC-CUR-001,TC-RSK-001).",
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Filter execution to a specific category (e.g. weather_safety_and_risk).",
    )
    parser.add_argument(
        "--all-systems",
        action="store_true",
        help="Run all three systems for selected test cases, overriding system filter.",
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        help="Limit execution to the first N test cases.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Per-test timeout in seconds.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Max retries on transient errors.",
    )
    parser.add_argument(
        "--fixture-mode",
        choices=["synthetic", "live"],
        default="synthetic",
        help="Whether to inject synthetic fixtures or call live APIs.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help="LLM model identifier to evaluate.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate selection and print execution plan without calling APIs.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_RESULTS_DIR),
        help="Directory to persist evaluation results.",
    )
    return parser.parse_args(args)


def main():
    parsed = parse_cli_args()

    # Build evaluation config
    selected_systems = None
    if parsed.system and not parsed.all_systems:
        selected_systems = [parsed.system]
    elif parsed.all_systems:
        selected_systems = ["baseline_llm", "tool_using_agent", "sky_reader_full"]

    selected_ids = [x.strip() for x in parsed.ids.split(",")] if parsed.ids else None
    selected_categories = [parsed.category.strip()] if parsed.category else None

    fix_mode = FixtureMode.SYNTHETIC_FIXTURE if parsed.fixture_mode == "synthetic" else FixtureMode.LIVE_DATA

    config = EvaluationConfig(
        results_dir=parsed.output_dir,
        model=parsed.model,
        timeout_seconds=parsed.timeout,
        max_retries=parsed.retries,
        fixture_mode=fix_mode,
        dry_run=parsed.dry_run,
        selected_systems=selected_systems,
        selected_categories=selected_categories,
        selected_ids=selected_ids,
        max_cases=parsed.max_cases,
    )

    runner = EvaluationRunner(config)
    asyncio.run(runner.run())


if __name__ == "__main__":
    main()
