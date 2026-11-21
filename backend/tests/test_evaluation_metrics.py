import unittest
from datetime import datetime, timezone

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
from backend.evaluation.metrics.base import (
    FactualClaimStatus,
    MetricStatus,
    NumericalMatchStatus,
)
from backend.evaluation.metrics.numerical import NumericalAccuracyEvaluator
from backend.evaluation.metrics.factual import FactualAccuracyEvaluator
from backend.evaluation.metrics.hallucination import HallucinationEvaluator
from backend.evaluation.metrics.evidence import EvidenceGroundingEvaluator
from backend.evaluation.metrics.risk import RiskAssessmentEvaluator
from backend.evaluation.metrics.performance import PerformanceEvaluator
from backend.evaluation.metrics.completeness import ResponseCompletenessEvaluator
from backend.evaluation.metrics.aggregator import MetricsEngine


class TestEvaluationMetrics(unittest.TestCase):
    """
    Comprehensive offline unit tests for Phase 7.3 Metrics Engine.
    Validates numerical, factual, hallucination, evidence, risk, performance,
    completeness, and aggregated metric reporting.
    """

    def setUp(self):
        # Sample test case with temperature, wind, and humidity
        self.sample_tc = TestCase(
            id="TC-TEST-001",
            category=BenchmarkCategory.CURRENT_WEATHER,
            question="What is the current temperature and wind speed in Dehradun?",
            location="Dehradun",
            forecast_period=ForecastPeriod.CURRENT,
            fixture_id="FIX_DEHRADUN_MILD",
            expected_numerical_values={
                "temperature": 21.8,
                "wind_speed": 10.5,
            },
            expected_facts_or_claims=[
                "temperature is approximately 21.8 °C",
                "wind speed is 10.5 km/h",
                "umbrella not needed",
            ],
            expected_risk_classification=None,
            evaluation_criteria=EvaluationCriteria(
                requires_tools=True,
                expected_claims=["temperature is approximately 21.8 °C", "wind speed is 10.5 km/h", "umbrella not needed"],
                allowed_numerical_tolerances={"temperature": 1.0, "wind_speed": 1.5},
                requires_evidence_proof=False,
                requires_risk_assessment=False,
                requires_uncertainty_note=False,
                should_refuse_or_hedge=False,
            ),
        )

        # Risk test case
        self.risk_tc = TestCase(
            id="TC-TEST-002",
            category=BenchmarkCategory.WEATHER_SAFETY_AND_RISK,
            question="Is there severe weather in Paris?",
            location="Paris",
            forecast_period=ForecastPeriod.CURRENT,
            fixture_id="FIX_PARIS_STORM",
            expected_numerical_values={
                "max_wind_speed": 68.0,
                "total_rain": 48.0,
            },
            expected_facts_or_claims=[
                "severe thunderstorm with hail",
                "gale-force winds reaching 68.0 km/h",
                "seek indoor shelter",
            ],
            expected_risk_classification="SEVERE",
            evaluation_criteria=EvaluationCriteria(
                requires_tools=True,
                expected_claims=["severe thunderstorm with hail", "gale-force winds reaching 68.0 km/h", "seek indoor shelter"],
                allowed_numerical_tolerances={"max_wind_speed": 4.0, "total_rain": 4.0},
                requires_evidence_proof=True,
                requires_risk_assessment=True,
                requires_uncertainty_note=True,
                should_refuse_or_hedge=False,
            ),
        )

        # Hallucination resistance test case
        self.refusal_tc = TestCase(
            id="TC-TEST-003",
            category=BenchmarkCategory.HALLUCINATION_RESISTANCE,
            question="What will the exact weather be in Tokyo 10 years from today?",
            location="Tokyo",
            forecast_period=ForecastPeriod.UNSPECIFIED,
            fixture_id=None,
            expected_numerical_values={},
            expected_facts_or_claims=[
                "cannot provide exact weather 10 years in the future",
                "forecast models are limited to 7-14 days",
                "refuses to fabricate far-future weather",
            ],
            expected_risk_classification=None,
            evaluation_criteria=EvaluationCriteria(
                requires_tools=False,
                expected_claims=["cannot provide exact weather 10 years in the future"],
                allowed_numerical_tolerances={},
                requires_evidence_proof=False,
                requires_risk_assessment=False,
                requires_uncertainty_note=False,
                should_refuse_or_hedge=True,
            ),
        )

    # --------------------------------------------------------------------------
    # 1. Numerical Accuracy Tests
    # --------------------------------------------------------------------------

    def test_numerical_accuracy_exact_and_within_tolerance(self):
        evaluator = NumericalAccuracyEvaluator()
        result = EvaluationResult(
            run_id="run_test",
            test_case_id="TC-TEST-001",
            system="sky_reader_full",
            category="current_weather",
            question="What is the current temperature and wind speed in Dehradun?",
            response="The temperature in Dehradun is currently 21.5°C with wind speed of 11.0 km/h.",
            execution_status=ExecutionStatus.COMPLETED,
            model_identifier="test-model",
            provider="groq",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            latency_ms=120.0,
            tool_calls=[{"tool": "get_current_weather"}],
        )

        eval_res = evaluator.evaluate(result, self.sample_tc)
        self.assertTrue(eval_res.is_evaluable)
        self.assertEqual(eval_res.metric_status, MetricStatus.PASSED)
        self.assertEqual(eval_res.total_expected, 2)
        self.assertEqual(eval_res.correct_count, 2)
        self.assertEqual(eval_res.incorrect_count, 0)
        self.assertEqual(eval_res.missing_count, 0)
        self.assertEqual(eval_res.accuracy, 1.0)
        self.assertIsNotNone(eval_res.mean_absolute_error)
        self.assertAlmostEqual(eval_res.mean_absolute_error, 0.4, places=2)

    def test_numerical_unit_conversion(self):
        evaluator = NumericalAccuracyEvaluator()
        # 71.2°F is ~21.78°C (expected 21.8°C), and 6.5 mph is ~10.46 km/h (expected 10.5 km/h)
        result = EvaluationResult(
            run_id="run_test",
            test_case_id="TC-TEST-001",
            system="tool_using_agent",
            category="current_weather",
            question="What is the current temperature and wind speed in Dehradun?",
            response="Currently in Dehradun it is 71.2°F with winds around 6.5 mph.",
            execution_status=ExecutionStatus.COMPLETED,
            model_identifier="test-model",
            provider="groq",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

        eval_res = evaluator.evaluate(result, self.sample_tc)
        self.assertTrue(eval_res.is_evaluable)
        self.assertEqual(eval_res.metric_status, MetricStatus.PASSED)
        self.assertEqual(eval_res.correct_count, 2)
        self.assertEqual(eval_res.accuracy, 1.0)

    def test_numerical_unit_conversion_precipitation_inches(self):
        evaluator = NumericalAccuracyEvaluator()
        # 0.5 inches is 12.7 mm
        tc = TestCase(
            id="TC-TEST-RAIN",
            category=BenchmarkCategory.PRECIPITATION_AND_RAINFALL,
            question="How much rain in London?",
            location="London",
            fixture_id="FIX_LONDON_RAIN",
            expected_numerical_values={"total_rain": 12.7},
            evaluation_criteria=EvaluationCriteria(
                allowed_numerical_tolerances={"total_rain": 0.5}
            ),
        )
        result = EvaluationResult(
            run_id="run_test",
            test_case_id="TC-TEST-RAIN",
            system="tool_using_agent",
            category="precipitation_and_rainfall",
            question="...",
            response="Total rainfall will be approximately 0.5 inches.",
            execution_status=ExecutionStatus.COMPLETED,
            model_identifier="test-model",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        eval_res = evaluator.evaluate(result, tc)
        self.assertTrue(eval_res.is_evaluable)
        self.assertEqual(eval_res.metric_status, MetricStatus.PASSED)
        self.assertEqual(eval_res.correct_count, 1)
        self.assertAlmostEqual(eval_res.variable_results["total_rain"].converted_value, 12.7, places=1)

    def test_numerical_incorrect_and_missing(self):
        evaluator = NumericalAccuracyEvaluator()
        # Response has incorrect temperature (35.0°C instead of 21.8°C) and completely missing wind speed
        result = EvaluationResult(
            run_id="run_test",
            test_case_id="TC-TEST-001",
            system="baseline_llm",
            category="current_weather",
            question="What is the current temperature and wind speed in Dehradun?",
            response="I estimate the temperature is around 35.0°C.",
            execution_status=ExecutionStatus.COMPLETED,
            model_identifier="test-model",
            provider="groq",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

        eval_res = evaluator.evaluate(result, self.sample_tc)
        self.assertTrue(eval_res.is_evaluable)
        self.assertEqual(eval_res.metric_status, MetricStatus.FAILED)
        self.assertEqual(eval_res.correct_count, 0)
        self.assertEqual(eval_res.incorrect_count, 1)
        self.assertEqual(eval_res.missing_count, 1)
        self.assertEqual(eval_res.accuracy, 0.0)
        self.assertEqual(eval_res.variable_results["temperature"].status, NumericalMatchStatus.INCORRECT)
        self.assertEqual(eval_res.variable_results["wind_speed"].status, NumericalMatchStatus.MISSING)

    # --------------------------------------------------------------------------
    # 2. Factual Accuracy Tests
    # --------------------------------------------------------------------------

    def test_factual_accuracy_matching_and_polarity(self):
        evaluator = FactualAccuracyEvaluator()
        result = EvaluationResult(
            run_id="run_test",
            test_case_id="TC-TEST-001",
            system="sky_reader_full",
            category="current_weather",
            question="...",
            response="In Dehradun, the temperature is approximately 21.8 °C and wind speed is 10.5 km/h. Umbrella not needed today as skies are dry.",
            execution_status=ExecutionStatus.COMPLETED,
            model_identifier="test-model",
            provider="groq",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

        eval_res = evaluator.evaluate(result, self.sample_tc)
        self.assertTrue(eval_res.is_evaluable)
        self.assertEqual(eval_res.metric_status, MetricStatus.PASSED)
        self.assertEqual(eval_res.correct_count, 3)
        self.assertEqual(eval_res.accuracy, 1.0)

    def test_factual_contradiction_polarity(self):
        evaluator = FactualAccuracyEvaluator()
        # Contradicts "umbrella not needed" by advising to bring an umbrella
        result = EvaluationResult(
            run_id="run_test",
            test_case_id="TC-TEST-001",
            system="baseline_llm",
            category="current_weather",
            question="...",
            response="Temperature is about 21.8°C. Be sure to bring an umbrella just in case.",
            execution_status=ExecutionStatus.COMPLETED,
            model_identifier="test-model",
            provider="groq",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

        eval_res = evaluator.evaluate(result, self.sample_tc)
        self.assertTrue(eval_res.is_evaluable)
        self.assertEqual(eval_res.metric_status, MetricStatus.PARTIAL)
        # 1 correct (temp), 1 unaddressed (wind), 1 incorrect (umbrella contradiction)
        self.assertEqual(eval_res.incorrect_count, 1)

    # --------------------------------------------------------------------------
    # 3. Hallucination Detection Tests
    # --------------------------------------------------------------------------

    def test_hallucination_from_validation_report(self):
        evaluator = HallucinationEvaluator()
        result = EvaluationResult(
            run_id="run_test",
            test_case_id="TC-TEST-001",
            system="sky_reader_full",
            category="current_weather",
            question="...",
            response="Valid response",
            execution_status=ExecutionStatus.COMPLETED,
            model_identifier="test-model",
            provider="groq",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            validation_report={
                "total_claims": 4,
                "supported_claims": 3,
                "partially_supported_claims": 1,
                "contradicted_claims": 0,
                "unsupported_claims": 0,
                "problematic_claims": [],
            },
        )

        eval_res = evaluator.evaluate(result, self.sample_tc)
        self.assertTrue(eval_res.is_evaluable)
        self.assertEqual(eval_res.metric_status, MetricStatus.PASSED)
        self.assertEqual(eval_res.hallucination_rate, 0.0)
        self.assertEqual(eval_res.contradiction_rate, 0.0)
        self.assertTrue(eval_res.is_hallucination_free)

    def test_hallucination_on_refusal_failure(self):
        evaluator = HallucinationEvaluator()
        # Response invents weather for 10 years in future instead of hedging/refusing
        result = EvaluationResult(
            run_id="run_test",
            test_case_id="TC-TEST-003",
            system="baseline_llm",
            category="hallucination_resistance",
            question="What will the exact weather be in Tokyo 10 years from today?",
            response="On November 17, 2036, Tokyo will experience 24°C with 15 mm of rain.",
            execution_status=ExecutionStatus.COMPLETED,
            model_identifier="test-model",
            provider="groq",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

        eval_res = evaluator.evaluate(result, self.refusal_tc)
        self.assertTrue(eval_res.is_evaluable)
        self.assertEqual(eval_res.metric_status, MetricStatus.FAILED)
        self.assertFalse(eval_res.is_hallucination_free)
        self.assertGreater(eval_res.contradiction_rate, 0.0)

    def test_hallucination_on_natural_refusal_and_contractions(self):
        evaluator = HallucinationEvaluator()
        # Responses using natural contractions and refusal phrasing should be recognized as valid hedges
        responses = [
            "I'm sorry, but I can't provide a temperature forecast that far into the future.",
            "I don't have access to historical temperature records for that date.",
            "I wasn't able to locate a place called 'the capital city of Mars'. Since it does not exist, I can't retrieve weather data.",
            "I couldn't find any geographic data for 'AtlantisFantasyRealm999' as it appears to be a fictional location.",
            "I cannot guarantee exact precipitation totals; weather forecasts are inherently probabilistic.",
        ]

        for resp in responses:
            result = EvaluationResult(
                run_id="run_test",
                test_case_id="TC-TEST-003",
                system="sky_reader_full",
                category="hallucination_resistance",
                question="What will the exact weather be in Tokyo 10 years from today?",
                response=resp,
                execution_status=ExecutionStatus.COMPLETED,
                model_identifier="test-model",
                provider="groq",
                started_at=datetime.now(timezone.utc).isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
            eval_res = evaluator.evaluate(result, self.refusal_tc)
            self.assertTrue(eval_res.is_evaluable)
            self.assertEqual(eval_res.metric_status, MetricStatus.PASSED, f"Failed on: {resp}")
            self.assertEqual(eval_res.hallucination_rate, 0.0, f"Expected 0.0 hallucination rate on: {resp}")
            self.assertTrue(eval_res.is_hallucination_free, f"Expected hallucination free on: {resp}")

    # --------------------------------------------------------------------------
    # 4. Evidence Grounding Tests
    # --------------------------------------------------------------------------

    def test_evidence_grounding_availability_and_usage(self):
        evaluator = EvidenceGroundingEvaluator()
        result = EvaluationResult(
            run_id="run_test",
            test_case_id="TC-TEST-002",
            system="sky_reader_full",
            category="weather_safety_and_risk",
            question="...",
            response="Severe thunderstorm detected [Evidence ID: ev_temp_current]. Stay indoors.",
            execution_status=ExecutionStatus.COMPLETED,
            model_identifier="test-model",
            provider="groq",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            tool_calls=[{"tool": "assess_weather_risks"}],
            explanation={
                "supporting_evidence": [{"id": "ev_temp_current"}],
                "measurements_used": [{"id": "ev_wind_speed"}],
                "data_sources": ["Open-Meteo"],
            },
        )

        eval_res = evaluator.evaluate(result, self.risk_tc)
        self.assertTrue(eval_res.is_evaluable)
        self.assertEqual(eval_res.metric_status, MetricStatus.PASSED)
        self.assertTrue(eval_res.evidence_available)
        self.assertTrue(eval_res.evidence_used)
        self.assertTrue(eval_res.has_explanation_proof)
        self.assertTrue(eval_res.proof_valid)
        self.assertIn("ev_temp_current", eval_res.valid_citation_ids)

    # --------------------------------------------------------------------------
    # 5. Risk Assessment Tests
    # --------------------------------------------------------------------------

    def test_risk_classification_match_and_confusion_matrix(self):
        evaluator = RiskAssessmentEvaluator()
        result = EvaluationResult(
            run_id="run_test",
            test_case_id="TC-TEST-002",
            system="sky_reader_full",
            category="weather_safety_and_risk",
            question="...",
            response="Risk Level: SEVERE. Severe thunderstorm with gale-force winds.",
            execution_status=ExecutionStatus.COMPLETED,
            model_identifier="test-model",
            provider="groq",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            risk_assessment={
                "overall_risk_level": "SEVERE",
                "detected_risks": [
                    {"risk_type": "thunderstorm", "severity": "SEVERE"},
                    {"risk_type": "strong_wind", "severity": "HIGH"},
                ],
            },
        )

        eval_res = evaluator.evaluate(result, self.risk_tc)
        self.assertTrue(eval_res.is_evaluable)
        self.assertEqual(eval_res.metric_status, MetricStatus.PASSED)
        self.assertTrue(eval_res.classification_match)
        self.assertEqual(eval_res.severity_error, 0)
        self.assertEqual(eval_res.confusion_matrix_entry, {"actual": "SEVERE", "predicted": "SEVERE"})
        self.assertIn("thunderstorm", eval_res.matched_hazards)

    def test_risk_underreporting(self):
        evaluator = RiskAssessmentEvaluator()
        # Model predicted LOW when expected was SEVERE
        result = EvaluationResult(
            run_id="run_test",
            test_case_id="TC-TEST-002",
            system="baseline_llm",
            category="weather_safety_and_risk",
            question="...",
            response="Overall weather risk is LOW. No concerns.",
            execution_status=ExecutionStatus.COMPLETED,
            model_identifier="test-model",
            provider="groq",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

        eval_res = evaluator.evaluate(result, self.risk_tc)
        self.assertTrue(eval_res.is_evaluable)
        self.assertEqual(eval_res.metric_status, MetricStatus.FAILED)
        self.assertFalse(eval_res.classification_match)
        self.assertTrue(eval_res.underreported)
        self.assertEqual(eval_res.severity_error, -3)  # LOW (0) - SEVERE (3) = -3

    def test_risk_overreporting(self):
        evaluator = RiskAssessmentEvaluator()
        # Case where expected risk was LOW, but model predicted HIGH
        mild_tc = TestCase(
            id="TC-MILD-001",
            category=BenchmarkCategory.WEATHER_SAFETY_AND_RISK,
            question="Is there risk?",
            location="Dehradun",
            expected_risk_classification="LOW",
        )
        result = EvaluationResult(
            run_id="run_test",
            test_case_id="TC-MILD-001",
            system="baseline_llm",
            category="weather_safety_and_risk",
            question="...",
            response="Weather risk is HIGH. Strong winds approaching.",
            execution_status=ExecutionStatus.COMPLETED,
            model_identifier="test-model",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        eval_res = evaluator.evaluate(result, mild_tc)
        self.assertTrue(eval_res.is_evaluable)
        self.assertEqual(eval_res.metric_status, MetricStatus.FAILED)
        self.assertFalse(eval_res.classification_match)
        self.assertTrue(eval_res.overreported)
        self.assertEqual(eval_res.severity_error, 2)  # HIGH (2) - LOW (0) = 2

    def test_invalid_and_hallucinated_evidence_citations(self):
        evaluator = EvidenceGroundingEvaluator()
        result = EvaluationResult(
            run_id="run_test",
            test_case_id="TC-TEST-001",
            system="baseline_llm",
            category="current_weather",
            question="...",
            # Fabricated evidence ID not in validation report
            response="Temperature is 21.8°C based on citation ev_fake_sensor_99.",
            execution_status=ExecutionStatus.COMPLETED,
            model_identifier="test-model",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            validation_report={
                "total_claims": 1,
                "supported_claims": 1,
                "contradicted_claims": 0,
                "unsupported_claims": 0,
                "validation_results": [
                    {"supporting_evidence_ids": ["ev_real_temp_01"]}
                ]
            }
        )
        eval_res = evaluator.evaluate(result, self.sample_tc)
        self.assertTrue(eval_res.is_evaluable)
        self.assertIn("ev_fake_sensor_99", eval_res.invalid_citation_ids)
        self.assertEqual(len(eval_res.valid_citation_ids), 0)

    # --------------------------------------------------------------------------
    # 6. Performance & Execution Health Tests
    # --------------------------------------------------------------------------

    def test_performance_metrics_and_failure_isolation(self):
        evaluator = PerformanceEvaluator()
        result = EvaluationResult(
            run_id="run_test",
            test_case_id="TC-TEST-001",
            system="baseline_llm",
            category="current_weather",
            question="...",
            response="",
            execution_status=ExecutionStatus.TIMEOUT,
            error_type="TimeoutError",
            error_message="Request exceeded 30.0s threshold",
            model_identifier="test-model",
            provider="groq",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            latency_ms=30005.0,
            retry_count=2,
        )

        eval_res = evaluator.evaluate(result, self.sample_tc)
        self.assertTrue(eval_res.is_evaluable)
        self.assertEqual(eval_res.metric_status, MetricStatus.FAILED)
        self.assertTrue(eval_res.is_timeout)
        self.assertTrue(eval_res.is_failure)
        self.assertFalse(eval_res.is_successful)
        self.assertEqual(eval_res.latency_ms, 30005.0)
        self.assertEqual(eval_res.retry_count, 2)

        # Confirm that NumericalEvaluator isolates this failure and does NOT score it as wrong answer
        num_eval = NumericalAccuracyEvaluator()
        num_res = num_eval.evaluate(result, self.sample_tc)
        self.assertFalse(num_res.is_evaluable)
        self.assertEqual(num_res.metric_status, MetricStatus.UNEVALUABLE)
        self.assertIsNone(num_res.accuracy)

    # --------------------------------------------------------------------------
    # 7. Response Completeness Tests
    # --------------------------------------------------------------------------

    def test_completeness_evaluation(self):
        evaluator = ResponseCompletenessEvaluator()
        # Missing risk and uncertainty note when required by TC-TEST-002
        result = EvaluationResult(
            run_id="run_test",
            test_case_id="TC-TEST-002",
            system="tool_using_agent",
            category="weather_safety_and_risk",
            question="Is there severe weather in Paris?",
            response="In Paris, wind is 68 km/h and rain is 48 mm.",
            execution_status=ExecutionStatus.COMPLETED,
            model_identifier="test-model",
            provider="groq",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

        eval_res = evaluator.evaluate(result, self.risk_tc)
        self.assertTrue(eval_res.is_evaluable)
        self.assertFalse(eval_res.is_complete)
        self.assertLess(eval_res.completeness_score, 1.0)
        self.assertIn("addressed_location", eval_res.criteria_checked)
        self.assertTrue(eval_res.criteria_checked["addressed_location"])
        self.assertFalse(eval_res.criteria_checked["satisfied_uncertainty_requirement"])

    # --------------------------------------------------------------------------
    # 8. Aggregation & Multi-Dimensional Scorecards Tests
    # --------------------------------------------------------------------------

    def test_metrics_engine_aggregation_and_denominators(self):
        engine = MetricsEngine()

        # Build mock dataset
        dataset = EvaluationDataset(
            name="Test Dataset",
            version="1.0.0",
            description="Testing metrics engine aggregation",
            total_cases=3,
            test_cases=[self.sample_tc, self.risk_tc, self.refusal_tc],
        )

        # 3 mock execution results
        res1 = EvaluationResult(
            run_id="run_agg_test",
            test_case_id="TC-TEST-001",
            system="sky_reader_full",
            category="current_weather",
            question="...",
            response="Dehradun temperature is 21.8°C with wind of 10.5 km/h. Umbrella not needed.",
            execution_status=ExecutionStatus.COMPLETED,
            model_identifier="test-model",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            latency_ms=100.0,
        )

        res2 = EvaluationResult(
            run_id="run_agg_test",
            test_case_id="TC-TEST-002",
            system="sky_reader_full",
            category="weather_safety_and_risk",
            question="...",
            response="Risk Level: SEVERE in Paris. Severe thunderstorm with hail. Gale-force winds reaching 68.0 km/h. Seek indoor shelter. Uncertainty note: forecast models show high confidence.",
            execution_status=ExecutionStatus.COMPLETED,
            model_identifier="test-model",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            latency_ms=250.0,
            risk_assessment={"overall_risk_level": "SEVERE"},
            explanation={"supporting_evidence": [{"id": "ev_1"}], "measurements_used": []},
        )

        res3 = EvaluationResult(
            run_id="run_agg_test",
            test_case_id="TC-TEST-003",
            system="baseline_llm",
            category="hallucination_resistance",
            question="...",
            response="",
            execution_status=ExecutionStatus.FAILED,
            error_type="APIError",
            error_message="Rate limit exceeded",
            model_identifier="test-model",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            latency_ms=0.0,
        )

        report = engine.evaluate_run([res1, res2, res3], dataset)

        # Validate overall summary
        self.assertEqual(report.run_id, "run_agg_test")
        self.assertEqual(report.overall_summary.total_cases, 3)
        self.assertEqual(report.overall_summary.evaluable_cases, 2)
        self.assertEqual(report.overall_summary.unevaluable_cases, 1)
        self.assertAlmostEqual(report.overall_summary.success_rate, 2 / 3, places=2)
        self.assertAlmostEqual(report.overall_summary.failure_rate, 1 / 3, places=2)

        # Validate by-system slice
        self.assertIn("sky_reader_full", report.by_system)
        self.assertIn("baseline_llm", report.by_system)
        sky_summary = report.by_system["sky_reader_full"]
        self.assertEqual(sky_summary.evaluable_cases, 2)
        self.assertEqual(sky_summary.success_rate, 1.0)
        self.assertEqual(sky_summary.clean_case_ratio, 1.0)

        # Validate by-category slice
        self.assertIn("current_weather", report.by_category)
        self.assertIn("weather_safety_and_risk", report.by_category)
        self.assertIn("hallucination_resistance", report.by_category)

    # --------------------------------------------------------------------------
    # 9. Empty and Malformed Results Handling
    # --------------------------------------------------------------------------

    def test_empty_and_malformed_results(self):
        engine = MetricsEngine()
        dataset = EvaluationDataset(
            name="Empty Test",
            version="1.0.0",
            description="Testing empty set",
            total_cases=1,
            test_cases=[self.sample_tc],
        )

        # Empty results list
        report = engine.evaluate_run([], dataset)
        self.assertEqual(report.overall_summary.total_cases, 0)
        self.assertEqual(report.overall_summary.evaluable_cases, 0)

        # Empty response string in completed result
        empty_res = EvaluationResult(
            run_id="run_empty",
            test_case_id="TC-TEST-001",
            system="baseline_llm",
            category="current_weather",
            question="...",
            response="",
            execution_status=ExecutionStatus.COMPLETED,
            model_identifier="test-model",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        case_score = engine.evaluate_case(empty_res, self.sample_tc)
        self.assertTrue(case_score.is_evaluable)
        self.assertEqual(case_score.numerical.missing_count, 2)
        self.assertEqual(case_score.numerical.accuracy, 0.0)


if __name__ == "__main__":
    unittest.main()
