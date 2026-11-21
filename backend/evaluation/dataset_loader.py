import json
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

try:
    from backend.evaluation.models import (
        EvaluationDataset,
        FixtureCollection,
        TestCase,
        WeatherFixture,
    )
except ImportError:
    from evaluation.models import (
        EvaluationDataset,
        FixtureCollection,
        TestCase,
        WeatherFixture,
    )

_BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET_PATH = _BASE_DIR / "datasets" / "weather_benchmark.json"
DEFAULT_FIXTURES_PATH = _BASE_DIR / "fixtures" / "weather_fixtures.json"


def load_dataset(filepath: Optional[Union[str, Path]] = None) -> EvaluationDataset:
    """
    Loads and validates the benchmark evaluation dataset from JSON.

    Args:
        filepath: Optional path to dataset JSON. Defaults to datasets/weather_benchmark.json.

    Returns:
        Validated EvaluationDataset instance.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If JSON is malformed or schema validation fails.
    """
    path = Path(filepath) if filepath is not None else DEFAULT_DATASET_PATH
    if not path.exists():
        raise FileNotFoundError(f"Evaluation dataset file not found at: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as jde:
        raise ValueError(f"Malformed JSON in dataset file '{path}': {jde}") from jde

    try:
        return EvaluationDataset.model_validate(data)
    except Exception as e:
        raise ValueError(f"Dataset schema validation failed for '{path}': {e}") from e


def load_fixtures(filepath: Optional[Union[str, Path]] = None) -> FixtureCollection:
    """
    Loads and validates synthetic weather data fixtures from JSON.

    Args:
        filepath: Optional path to fixtures JSON. Defaults to fixtures/weather_fixtures.json.

    Returns:
        Validated FixtureCollection instance.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If JSON is malformed or schema validation fails.
    """
    path = Path(filepath) if filepath is not None else DEFAULT_FIXTURES_PATH
    if not path.exists():
        raise FileNotFoundError(f"Weather fixtures file not found at: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as jde:
        raise ValueError(f"Malformed JSON in fixtures file '{path}': {jde}") from jde

    try:
        return FixtureCollection.model_validate(data)
    except Exception as e:
        raise ValueError(f"Fixtures schema validation failed for '{path}': {e}") from e


def load_benchmark_suite(
    dataset_path: Optional[Union[str, Path]] = None,
    fixtures_path: Optional[Union[str, Path]] = None,
) -> Tuple[EvaluationDataset, FixtureCollection]:
    """
    Loads both dataset and fixtures and performs cross-validation to ensure all
    fixture references resolve cleanly.

    Returns:
        Tuple of (EvaluationDataset, FixtureCollection).

    Raises:
        ValueError: If any test case references a non-existent fixture_id.
    """
    dataset = load_dataset(dataset_path)
    fixtures = load_fixtures(fixtures_path)

    # Cross-reference validation
    missing_fixtures = []
    for tc in dataset.test_cases:
        if tc.fixture_id and not fixtures.contains(tc.fixture_id):
            missing_fixtures.append((tc.id, tc.fixture_id))

    if missing_fixtures:
        details = ", ".join([f"[{tc_id} -> {f_id}]" for tc_id, f_id in missing_fixtures])
        raise ValueError(
            f"Dataset cross-validation failed. Test cases reference unknown fixture IDs: {details}"
        )

    return dataset, fixtures


def get_test_case(test_id: str, dataset_path: Optional[Union[str, Path]] = None) -> Optional[TestCase]:
    """Quick lookup for a single test case by its ID."""
    dataset = load_dataset(dataset_path)
    return dataset.get_by_id(test_id)


def get_fixture(fixture_id: str, fixtures_path: Optional[Union[str, Path]] = None) -> Optional[WeatherFixture]:
    """Quick lookup for a single fixture by its ID."""
    fixtures = load_fixtures(fixtures_path)
    return fixtures.get(fixture_id)
