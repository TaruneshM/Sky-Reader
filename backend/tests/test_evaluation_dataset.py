import json
import tempfile
import unittest
from pathlib import Path
from pydantic import ValidationError

from backend.evaluation.dataset_loader import (
    load_benchmark_suite,
    load_dataset,
    load_fixtures,
    get_test_case,
    get_fixture,
)
from backend.evaluation.models import (
    ApplicableSystem,
    BenchmarkCategory,
    EvaluationCriteria,
    EvaluationDataset,
    FixtureCollection,
    ForecastPeriod,
    TestCase,
    WeatherFixture,
)


class TestEvaluationDatasetFoundation(unittest.TestCase):
    def setUp(self):
        self.dataset, self.fixtures = load_benchmark_suite()

    # -----------------------------------------------------------------
    # 1. Dataset loading & integrity
    # -----------------------------------------------------------------
    def test_dataset_loading(self):
        """Verifies dataset loads successfully with expected top-level metadata."""
        self.assertIsNotNone(self.dataset)
        self.assertEqual(self.dataset.name, "Sky Reader Phase 7 Evaluation Benchmark Dataset")
        self.assertEqual(self.dataset.version, "1.0.0")
        self.assertEqual(self.dataset.total_cases, len(self.dataset.test_cases))
        self.assertTrue(40 <= len(self.dataset.test_cases) <= 60, f"Expected 40-60 test cases, got {len(self.dataset.test_cases)}")

    # -----------------------------------------------------------------
    # 2. Category coverage & distribution
    # -----------------------------------------------------------------
    def test_category_coverage(self):
        """Verifies all 10 mandatory evaluation categories are represented."""
        expected_categories = {
            BenchmarkCategory.CURRENT_WEATHER,
            BenchmarkCategory.HOURLY_FORECAST,
            BenchmarkCategory.TEMPERATURE_COMPARISON,
            BenchmarkCategory.PRECIPITATION_AND_RAINFALL,
            BenchmarkCategory.WEATHER_TRENDS,
            BenchmarkCategory.MULTISTEP_REASONING,
            BenchmarkCategory.EVIDENCE_BASED_REASONING,
            BenchmarkCategory.WEATHER_SAFETY_AND_RISK,
            BenchmarkCategory.MISSING_INCOMPLETE_DATA,
            BenchmarkCategory.HALLUCINATION_RESISTANCE,
        }
        present_categories = {tc.category for tc in self.dataset.test_cases}
        self.assertEqual(present_categories, expected_categories, "All 10 benchmark categories must be present")

        dist = self.dataset.category_distribution()
        for cat in expected_categories:
            self.assertGreaterEqual(dist.get(cat.value, 0), 3, f"Category {cat.value} should have at least 3 test cases")

    # -----------------------------------------------------------------
    # 3. Duplicate IDs validation
    # -----------------------------------------------------------------
    def test_duplicate_id_detection(self):
        """Verifies dataset validator rejects duplicate test case IDs."""
        raw_cases = [tc.model_dump() for tc in self.dataset.test_cases[:3]]
        # Duplicate the first ID
        raw_cases[1]["id"] = raw_cases[0]["id"]

        with self.assertRaises(ValueError) as ctx:
            EvaluationDataset(
                name="Duplicate Test",
                version="1.0.0",
                description="Test",
                total_cases=len(raw_cases),
                test_cases=raw_cases,
            )
        self.assertIn("Duplicate test case IDs found", str(ctx.exception))

    # -----------------------------------------------------------------
    # 4. Missing required fields
    # -----------------------------------------------------------------
    def test_missing_required_fields(self):
        """Verifies Pydantic raises ValidationError when essential fields are omitted."""
        # Missing 'question'
        with self.assertRaises(ValidationError):
            TestCase(
                id="TC-ERR-001",
                category=BenchmarkCategory.CURRENT_WEATHER,
                question="",  # Empty question rejected
                location="Dehradun",
                forecast_period=ForecastPeriod.CURRENT,
            )

        # Missing 'location'
        with self.assertRaises(ValidationError):
            TestCase(
                id="TC-ERR-002",
                category=BenchmarkCategory.CURRENT_WEATHER,
                question="What is the weather?",
                location="",  # Empty location rejected
                forecast_period=ForecastPeriod.CURRENT,
            )

    # -----------------------------------------------------------------
    # 5. Invalid numerical values & negative tolerances
    # -----------------------------------------------------------------
    def test_invalid_numerical_values(self):
        """Verifies validator rejects non-numeric expected values or negative tolerances."""
        # Negative tolerance rejected
        with self.assertRaises(ValueError) as ctx:
            EvaluationCriteria(
                allowed_numerical_tolerances={"temperature": -1.5}
            )
        self.assertIn("must be a non-negative number", str(ctx.exception))

        # Non-numeric expected value rejected
        with self.assertRaises(ValidationError):
            TestCase(
                id="TC-ERR-003",
                category=BenchmarkCategory.CURRENT_WEATHER,
                question="Valid question?",
                location="Paris",
                expected_numerical_values={"temperature": "twenty-two"},  # type: ignore
            )

    # -----------------------------------------------------------------
    # 6. Fixtures loading & synthetic marker enforcement
    # -----------------------------------------------------------------
    def test_fixtures_loading_and_synthetic_enforcement(self):
        """Verifies synthetic fixtures load properly and is_synthetic=True is strictly enforced."""
        self.assertIsNotNone(self.fixtures)
        self.assertGreaterEqual(len(self.fixtures.fixtures), 10)

        for fix_id, fix in self.fixtures.fixtures.items():
            self.assertTrue(fix.is_synthetic, f"Fixture {fix_id} must have is_synthetic=True")
            self.assertIn("name", fix.location)
            self.assertIn("latitude", fix.location)
            self.assertIn("longitude", fix.location)

        # Reject fixture that attempts to claim it is not synthetic
        with self.assertRaises(ValidationError) as ctx:
            WeatherFixture(
                fixture_id="FIX_FAKE_LIVE",
                description="Fake live",
                location={"name": "Test", "latitude": 0.0, "longitude": 0.0},
                is_synthetic=False,  # Must be True
            )
        self.assertIn("Evaluation fixtures must be explicitly marked with is_synthetic=True", str(ctx.exception))

    # -----------------------------------------------------------------
    # 7. Fixture reference cross-validation
    # -----------------------------------------------------------------
    def test_fixture_cross_referencing(self):
        """Verifies that all fixture_ids in the benchmark dataset exist in the fixtures collection."""
        for tc in self.dataset.test_cases:
            if tc.fixture_id:
                self.assertTrue(
                    self.fixtures.contains(tc.fixture_id),
                    f"Test case {tc.id} references missing fixture {tc.fixture_id}"
                )

        # Verify load_benchmark_suite fails if an unknown fixture_id is referenced
        broken_dataset = self.dataset.model_dump()
        broken_dataset["test_cases"][0]["fixture_id"] = "NON_EXISTENT_FIXTURE_999"

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(broken_dataset, f)
            temp_path = f.name

        try:
            with self.assertRaises(ValueError) as ctx:
                load_benchmark_suite(dataset_path=temp_path)
            self.assertIn("references missing fixture" if "missing" in str(ctx.exception) else "unknown fixture ID", str(ctx.exception))
        finally:
            Path(temp_path).unlink(missing_ok=True)

    # -----------------------------------------------------------------
    # 8. Querying & Filtering helpers
    # -----------------------------------------------------------------
    def test_filtering_and_retrieval(self):
        """Verifies get_by_id, filter_by_category, and filter_by_system methods."""
        tc_curr = self.dataset.get_by_id("TC-CUR-001")
        self.assertIsNotNone(tc_curr)
        self.assertEqual(tc_curr.location, "Dehradun")

        # Test non-existent ID
        self.assertIsNone(self.dataset.get_by_id("TC-NONEXISTENT"))

        # Category filter
        risk_cases = self.dataset.filter_by_category(BenchmarkCategory.WEATHER_SAFETY_AND_RISK)
        self.assertEqual(len(risk_cases), 5)
        self.assertTrue(all(tc.category == BenchmarkCategory.WEATHER_SAFETY_AND_RISK for tc in risk_cases))

        # System filter
        baseline_cases = self.dataset.filter_by_system(ApplicableSystem.BASELINE_LLM)
        self.assertTrue(len(baseline_cases) > 0)

        # Quick module-level helper lookup
        tc_via_loader = get_test_case("TC-CUR-002")
        self.assertEqual(tc_via_loader.location, "London")

        fix_via_loader = get_fixture("FIX_DEHRADUN_MILD")
        self.assertEqual(fix_via_loader.location["name"], "Dehradun")


if __name__ == "__main__":
    unittest.main()
