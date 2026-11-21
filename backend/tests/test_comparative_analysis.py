import json
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from backend.evaluation.models import (
    ApplicableSystem,
    BenchmarkCategory,
    EvaluationCriteria,
    EvaluationDataset,
    ForecastPeriod,
    TestCase,
    WeatherFixture,
)
from backend.evaluation.result_models import (
    EvaluationResult,
    ExecutionStatus,
    FixtureMode,
)
from backend.evaluation.result_store import ResultStore
from backend.evaluation.analysis.comparator import (
    ComparativeAnalyzer,
    bootstrap_ci,
    paired_bootstrap_test,
)


class TestComparativeAnalysis(unittest.TestCase):
    """
    Offline test suite for Phase 7.4 Comparative Analysis & Benchmarking.
    Tests statistical reliability, paired tests, category grouping, error taxonomy,
    artifact generation, and missing system handling.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.results_dir = Path(self.temp_dir) / "results"
        self.output_dir = Path(self.temp_dir) / "analysis"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.store = ResultStore(self.results_dir)

        # Create two test cases
        self.tc1 = TestCase(
            id="TC-CUR-001",
            category=BenchmarkCategory.CURRENT_WEATHER,
            question="What is the current temperature in Dehradun?",
            location="Dehradun",
            expected_numerical_values={"temperature": 21.8},
            expected_facts_or_claims=["temperature is approximately 21.8 °C"],
            evaluation_criteria=EvaluationCriteria(
                allowed_numerical_tolerances={"temperature": 1.0}
            ),
        )

        self.tc2 = TestCase(
            id="TC-RSK-001",
            category=BenchmarkCategory.WEATHER_SAFETY_AND_RISK,
            question="Is there severe weather in Paris?",
            location="Paris",
            expected_numerical_values={"max_wind_speed": 68.0},
            expected_facts_or_claims=["severe thunderstorm with hail"],
            expected_risk_classification="SEVERE",
            evaluation_criteria=EvaluationCriteria(
                allowed_numerical_tolerances={"max_wind_speed": 4.0},
                requires_risk_assessment=True,
            ),
        )

        self.dataset = EvaluationDataset(
            name="Mock Dataset",
            version="1.0.0",
            description="Testing comparative analysis",
            total_cases=2,
            test_cases=[self.tc1, self.tc2],
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # --------------------------------------------------------------------------
    # 1. Statistical Calculation Tests
    # --------------------------------------------------------------------------

    def test_bootstrap_ci_computation(self):
        data = [0.8, 0.85, 0.9, 0.95, 1.0]
        mean, lower, upper = bootstrap_ci(data, n_resamples=1000, seed=42)
        self.assertAlmostEqual(mean, 0.9, places=2)
        self.assertLessEqual(lower, mean)
        self.assertGreaterEqual(upper, mean)
        self.assertGreater(lower, 0.75)
        self.assertLess(upper, 1.05)

    def test_paired_bootstrap_test(self):
        # System A clearly superior to System B
        scores_a = [1.0, 1.0, 0.9, 1.0, 0.95]
        scores_b = [0.2, 0.1, 0.3, 0.0, 0.2]

        test_res = paired_bootstrap_test(scores_a, scores_b, n_resamples=1000, seed=42)
        self.assertEqual(test_res["n_pairs"], 5)
        self.assertAlmostEqual(test_res["mean_diff"], 0.81, places=2)
        self.assertTrue(test_res["statistically_significant"])
        self.assertLess(test_res["p_value_two_sided"], 0.05)
        self.assertEqual(test_res["p_value_display"], "p < 0.001")
        self.assertGreater(test_res["ci_95"][0], 0.5)

    def test_paired_bootstrap_test_null_case(self):
        # Systems identical
        scores_a = [0.8, 0.8, 0.8, 0.8]
        scores_b = [0.8, 0.8, 0.8, 0.8]
        test_res = paired_bootstrap_test(scores_a, scores_b, n_resamples=500, seed=42)
        self.assertEqual(test_res["mean_diff"], 0.0)
        self.assertFalse(test_res["statistically_significant"])
        self.assertEqual(test_res["p_value_display"], "p = 1.0000")

    def test_p_value_display_scientific_formatting(self):
        # Explicitly verify p-values are never displayed as 0.0000
        res = paired_bootstrap_test([1.0]*10, [0.0]*10, n_resamples=500, seed=42)
        self.assertEqual(res["p_value_two_sided"], 0.0)
        self.assertEqual(res["p_value_display"], "p < 0.001")
        self.assertNotEqual(res["p_value_display"], "p = 0.0000")

    # --------------------------------------------------------------------------
    # 2. Comparative Aggregation & Denominators
    # --------------------------------------------------------------------------

    def test_comparative_aggregation_and_denominators(self):
        # Create execution results for all 3 systems
        results = [
            # Baseline
            EvaluationResult(
                run_id="run_comp_test",
                test_case_id="TC-CUR-001",
                system="baseline_llm",
                category="current_weather",
                question="...",
                response="I do not have real time weather tools. Check IMD.",
                execution_status=ExecutionStatus.COMPLETED,
                model_identifier="test-model",
                started_at=datetime.now(timezone.utc).isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
            ),
            EvaluationResult(
                run_id="run_comp_test",
                test_case_id="TC-RSK-001",
                system="baseline_llm",
                category="weather_safety_and_risk",
                question="...",
                response="",
                execution_status=ExecutionStatus.FAILED,
                error_type="APIConnectionError",
                error_message="Network unreachable",
                model_identifier="test-model",
                started_at=datetime.now(timezone.utc).isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
            ),
            # Tool Agent
            EvaluationResult(
                run_id="run_comp_test",
                test_case_id="TC-CUR-001",
                system="tool_using_agent",
                category="current_weather",
                question="...",
                response="The temperature in Dehradun is 21.8°C.",
                execution_status=ExecutionStatus.COMPLETED,
                model_identifier="test-model",
                started_at=datetime.now(timezone.utc).isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
                tool_calls=[{"tool": "get_current_weather"}],
            ),
            EvaluationResult(
                run_id="run_comp_test",
                test_case_id="TC-RSK-001",
                system="tool_using_agent",
                category="weather_safety_and_risk",
                question="...",
                response="Winds are reaching 68 km/h in Paris.",
                execution_status=ExecutionStatus.COMPLETED,
                model_identifier="test-model",
                started_at=datetime.now(timezone.utc).isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
                tool_calls=[{"tool": "get_hourly_forecast"}],
            ),
            # Sky Reader Full
            EvaluationResult(
                run_id="run_comp_test",
                test_case_id="TC-CUR-001",
                system="sky_reader_full",
                category="current_weather",
                question="...",
                response="Dehradun temperature is 21.8 °C.",
                execution_status=ExecutionStatus.COMPLETED,
                model_identifier="test-model",
                started_at=datetime.now(timezone.utc).isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
                tool_calls=[{"tool": "get_current_weather"}],
                validation_report={"total_claims": 1, "supported_claims": 1, "contradicted_claims": 0, "unsupported_claims": 0},
            ),
            EvaluationResult(
                run_id="run_comp_test",
                test_case_id="TC-RSK-001",
                system="sky_reader_full",
                category="weather_safety_and_risk",
                question="...",
                response="Risk Level: SEVERE. Severe thunderstorm with hail and winds reaching 68 km/h.",
                execution_status=ExecutionStatus.COMPLETED,
                model_identifier="test-model",
                started_at=datetime.now(timezone.utc).isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
                tool_calls=[{"tool": "assess_weather_risks"}],
                risk_assessment={"overall_risk_level": "SEVERE"},
                validation_report={"total_claims": 2, "supported_claims": 2, "contradicted_claims": 0, "unsupported_claims": 0},
            ),
        ]

        analyzer = ComparativeAnalyzer(
            dataset=self.dataset,
            fixtures=None,
            output_dir=self.output_dir,
        )

        analysis = analyzer.analyze(results)

        # Verify system summaries
        sys_sums = analysis["system_summaries"]
        self.assertIn("baseline_llm", sys_sums)
        self.assertIn("tool_using_agent", sys_sums)
        self.assertIn("sky_reader_full", sys_sums)

        # Baseline had 1 completed, 1 failed
        self.assertEqual(sys_sums["baseline_llm"]["total_cases"], 2)
        self.assertEqual(sys_sums["baseline_llm"]["evaluable_cases"], 1)
        self.assertEqual(sys_sums["baseline_llm"]["unevaluable_cases"], 1)
        self.assertEqual(sys_sums["baseline_llm"]["failure_rate"], 0.5)

        # Tool Agent had 2 completed
        self.assertEqual(sys_sums["tool_using_agent"]["evaluable_cases"], 2)
        self.assertEqual(sys_sums["tool_using_agent"]["mean_numerical_accuracy"], 1.0)

        # Sky Reader had 2 completed with full risk accuracy
        self.assertEqual(sys_sums["sky_reader_full"]["evaluable_cases"], 2)
        self.assertEqual(sys_sums["sky_reader_full"]["risk_classification_accuracy"], 1.0)

    # --------------------------------------------------------------------------
    # 3. Category Grouping & Missing Systems
    # --------------------------------------------------------------------------

    def test_category_grouping_and_missing_systems(self):
        # Run with only tool_using_agent (baseline and sky_reader missing)
        results = [
            EvaluationResult(
                run_id="run_missing_sys",
                test_case_id="TC-CUR-001",
                system="tool_using_agent",
                category="current_weather",
                question="...",
                response="Temperature is 21.8°C.",
                execution_status=ExecutionStatus.COMPLETED,
                model_identifier="test-model",
                started_at=datetime.now(timezone.utc).isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
        ]

        analyzer = ComparativeAnalyzer(
            dataset=self.dataset,
            fixtures=None,
            output_dir=self.output_dir,
        )

        analysis = analyzer.analyze(results)
        sys_sums = analysis["system_summaries"]

        self.assertIsNotNone(sys_sums["tool_using_agent"])
        self.assertIsNone(sys_sums["baseline_llm"])
        self.assertIsNone(sys_sums["sky_reader_full"])

        # Category grouping
        self.assertIn("current_weather", analysis["category_summaries"])

    # --------------------------------------------------------------------------
    # 4. Error Taxonomy Extraction
    # --------------------------------------------------------------------------

    def test_error_taxonomy_extraction(self):
        # Result with incorrect temperature and failed risk classification
        results = [
            EvaluationResult(
                run_id="run_err_test",
                test_case_id="TC-CUR-001",
                system="baseline_llm",
                category="current_weather",
                question="...",
                response="The temperature is 38.0°C in Dehradun.",
                execution_status=ExecutionStatus.COMPLETED,
                model_identifier="test-model",
                started_at=datetime.now(timezone.utc).isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
            ),
            EvaluationResult(
                run_id="run_err_test",
                test_case_id="TC-RSK-001",
                system="baseline_llm",
                category="weather_safety_and_risk",
                question="...",
                response="Weather risk is LOW. No rain expected.",
                execution_status=ExecutionStatus.COMPLETED,
                model_identifier="test-model",
                started_at=datetime.now(timezone.utc).isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
            ),
        ]

        analyzer = ComparativeAnalyzer(
            dataset=self.dataset,
            fixtures=None,
            output_dir=self.output_dir,
        )

        analysis = analyzer.analyze(results)
        taxonomy = analysis["error_taxonomy"]

        counts = taxonomy["summary_counts"]
        self.assertGreaterEqual(counts["incorrect_numerical_values"], 1)
        self.assertGreaterEqual(counts["risk_misclassifications"], 1)
        self.assertGreaterEqual(counts["factual_contradictions"], 1)

    # --------------------------------------------------------------------------
    # 5. Artifact Generation & Reproducibility
    # --------------------------------------------------------------------------

    def test_artifact_generation_and_reproducibility(self):
        results = [
            EvaluationResult(
                run_id="run_artifact_test",
                test_case_id="TC-CUR-001",
                system="sky_reader_full",
                category="current_weather",
                question="...",
                response="Temperature in Dehradun is 21.8°C.",
                execution_status=ExecutionStatus.COMPLETED,
                model_identifier="test-model",
                started_at=datetime.now(timezone.utc).isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
                tool_calls=[{"tool": "get_current_weather"}],
            )
        ]

        analyzer = ComparativeAnalyzer(
            dataset=self.dataset,
            fixtures=None,
            output_dir=self.output_dir,
        )

        analysis = analyzer.analyze(results)
        artifacts = analyzer.generate_all_artifacts(analysis)

        # Verify all 10 artifacts were created
        expected_keys = [
            "comparative_summary_json",
            "comparative_summary_csv",
            "category_comparison_csv",
            "error_analysis_json",
            "statistical_analysis_json",
            "benchmark_integrity_report_md",
            "comparative_report_md",
            "metric_comparison_svg",
            "latency_comparison_svg",
            "error_distribution_svg",
        ]
        for k in expected_keys:
            self.assertIn(k, artifacts)
            self.assertTrue(artifacts[k].exists(), f"File {artifacts[k]} was not created")
            self.assertGreater(artifacts[k].stat().st_size, 0)

        # Verify content of comparative_summary.json matches analysis
        with open(artifacts["comparative_summary_json"], encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["run_id"], "run_artifact_test")
            self.assertIn("sky_reader_full", data["system_summaries"])

    # --------------------------------------------------------------------------
    # 6. Phase 7.4.1 Validation & Offline Correction Tests
    # --------------------------------------------------------------------------

    def test_multi_label_error_taxonomy_and_proportions(self):
        # A single case can have multiple failure modes simultaneously (multi-label)
        results = [
            EvaluationResult(
                run_id="run_multilabel_test",
                test_case_id="TC-CUR-001",
                system="baseline_llm",
                category="current_weather",
                question="...",
                response="It might be 45.0°C and sunny.",  # Incorrect number AND incomplete
                execution_status=ExecutionStatus.COMPLETED,
                model_identifier="test-model",
                started_at=datetime.now(timezone.utc).isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
            ),
        ]
        analyzer = ComparativeAnalyzer(
            dataset=self.dataset,
            fixtures=None,
            output_dir=self.output_dir,
        )
        analysis = analyzer.analyze(results)
        tax = analysis["error_taxonomy"]

        self.assertEqual(tax["taxonomy_classification"], "multi-label")
        self.assertIn("system_breakdown", tax)

        base_b = tax["system_breakdown"]["baseline_llm"]
        self.assertEqual(base_b["total_attempted_cases"], 1)
        self.assertEqual(base_b["evaluable_cases"], 1)
        # Verify mode incidence rate uses evaluable cases as denominator
        num_err = base_b["by_failure_mode"]["incorrect_numerical_values"]
        self.assertEqual(num_err["cases_affected_count"], 1)
        self.assertEqual(num_err["case_incidence_rate"], 1.0)

    def test_matched_case_pairing_and_exclusions(self):
        # TC1 completed on both; TC2 completed on Tool Agent but TIMED OUT on Sky Reader
        results = [
            # TC-CUR-001
            EvaluationResult(
                run_id="run_pair_test",
                test_case_id="TC-CUR-001",
                system="tool_using_agent",
                category="current_weather",
                question="...",
                response="21.8°C",
                execution_status=ExecutionStatus.COMPLETED,
                model_identifier="test-model",
                started_at=datetime.now(timezone.utc).isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
            ),
            EvaluationResult(
                run_id="run_pair_test",
                test_case_id="TC-CUR-001",
                system="sky_reader_full",
                category="current_weather",
                question="...",
                response="21.8°C",
                execution_status=ExecutionStatus.COMPLETED,
                model_identifier="test-model",
                started_at=datetime.now(timezone.utc).isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
            ),
            # TC-RSK-001
            EvaluationResult(
                run_id="run_pair_test",
                test_case_id="TC-RSK-001",
                system="tool_using_agent",
                category="weather_safety_and_risk",
                question="...",
                response="Severe storms",
                execution_status=ExecutionStatus.COMPLETED,
                model_identifier="test-model",
                started_at=datetime.now(timezone.utc).isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
            ),
            EvaluationResult(
                run_id="run_pair_test",
                test_case_id="TC-RSK-001",
                system="sky_reader_full",
                category="weather_safety_and_risk",
                question="...",
                response="",
                execution_status=ExecutionStatus.TIMEOUT,
                error_type="TimeoutError",
                error_message="Timed out after 30s",
                model_identifier="test-model",
                started_at=datetime.now(timezone.utc).isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
            ),
        ]
        analyzer = ComparativeAnalyzer(
            dataset=self.dataset,
            fixtures=None,
            output_dir=self.output_dir,
        )
        analysis = analyzer.analyze(results)
        stats = analysis["statistical_analysis"]

        pair = stats["paired_system_tests"]["sky_reader_full_vs_tool_using_agent"]
        # Only TC-CUR-001 was mutually evaluable
        self.assertEqual(pair["matched_cases_count"], 1)
        self.assertEqual(pair["matched_test_case_ids"], ["TC-CUR-001"])

        # TC-RSK-001 must be tracked in excluded_cases with its timeout reason
        excluded_ids = [ex["test_case_id"] for ex in pair["excluded_cases"]]
        self.assertIn("TC-RSK-001", excluded_ids)
        rsk_ex = next(ex for ex in pair["excluded_cases"] if ex["test_case_id"] == "TC-RSK-001")
        self.assertIn("TimeoutError", rsk_ex["exclusion_reason"])

    def test_adapter_prompt_and_tool_isolation(self):
        from backend.evaluation.adapters import (
            BASELINE_SYSTEM_PROMPT,
            TOOL_AGENT_SYSTEM_PROMPT,
            RETRIEVAL_TOOLS,
            ToolUsingAgentAdapter,
        )
        from backend.evaluation.config import EvaluationConfig

        # Tool Agent prompt must NOT contain proprietary Sky Reader verification / risk keywords
        self.assertNotIn("assess_weather_risks", TOOL_AGENT_SYSTEM_PROMPT)
        self.assertNotIn("claim", TOOL_AGENT_SYSTEM_PROMPT.lower())
        self.assertNotIn("evidence", TOOL_AGENT_SYSTEM_PROMPT.lower())
        self.assertNotIn("explanation proof", TOOL_AGENT_SYSTEM_PROMPT.lower())

        # Baseline prompt must prohibit tool use
        self.assertIn("do NOT have access to live weather tools", BASELINE_SYSTEM_PROMPT)

        # ToolUsingAgentAdapter must default to RETRIEVAL_TOOLS
        adapter = ToolUsingAgentAdapter(EvaluationConfig())
        tool_names = [t["function"]["name"] for t in adapter.tools]
        self.assertIn("geocode_location", tool_names)
        self.assertIn("get_current_weather", tool_names)
        self.assertIn("get_hourly_forecast", tool_names)
        self.assertNotIn("assess_weather_risks", tool_names)
        self.assertNotIn("analyze_weather", tool_names)

    def test_category_table_risk_and_numerical_accuracy_distinction(self):
        # TC2 has risk assessment. Check CSV has distinct columns
        results = [
            EvaluationResult(
                run_id="run_distinction_test",
                test_case_id="TC-RSK-001",
                system="sky_reader_full",
                category="weather_safety_and_risk",
                question="...",
                response="Risk level SEVERE with precautions.",
                execution_status=ExecutionStatus.COMPLETED,
                model_identifier="test-model",
                risk_assessment={"overall_risk_level": "SEVERE"},
                started_at=datetime.now(timezone.utc).isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
        ]
        analyzer = ComparativeAnalyzer(
            dataset=self.dataset,
            fixtures=None,
            output_dir=self.output_dir,
        )
        analysis = analyzer.analyze(results)
        artifacts = analyzer.generate_all_artifacts(analysis)

        # Check CSV header
        with open(artifacts["category_comparison_csv"], encoding="utf-8") as f:
            header = f.readline().strip().split(",")
            self.assertIn("Numerical Accuracy", header)
            self.assertIn("Factual Accuracy", header)
            self.assertIn("Risk Accuracy", header)


if __name__ == "__main__":
    unittest.main()
