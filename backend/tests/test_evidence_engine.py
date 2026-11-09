import sys
from pathlib import Path

# Ensure backend directory is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.evidence.evidence_models import (
    EvidenceSourceType,
    WeatherVariable,
)
from backend.evidence.evidence_engine import EvidenceEngine


def test_evidence_engine_extraction():
    print("Testing EvidenceEngine extraction...")
    engine = EvidenceEngine()

    mock_current = {
        "time": "2026-11-09T16:00",
        "temperature_2m": 22.5,
        "apparent_temperature": 24.0,
        "relative_humidity_2m": 65.0,
        "wind_speed_10m": 12.0,
        "wind_direction_10m": 90.0,
        "surface_pressure": 945.0,
        "cloud_cover": 20.0,
        "weather_code": 0,
    }

    mock_hourly = {
        "time": [f"2026-11-09T{h:02d}:00" for h in range(12)],
        "temperature_2m": [15.0 + h for h in range(12)],
        "relative_humidity_2m": [60.0 for _ in range(12)],
        "precipitation_probability": [0.0 if h < 6 else 40.0 for h in range(12)],
        "precipitation": [0.0 for _ in range(12)],
        "wind_speed_10m": [10.0 for _ in range(12)],
        "weather_code": [0 for _ in range(12)],
    }

    mock_location = {
        "name": "Dehradun",
        "latitude": 30.32,
        "longitude": 78.03,
    }

    collection = engine.generate_evidence(
        current_data={"current": mock_current},
        hourly_data={"hourly": mock_hourly},
        location_meta=mock_location,
    )

    assert collection.location_name == "Dehradun"
    assert len(collection.items) > 0

    # 1. Check Observed current evidence items
    obs_temps = [it for it in collection.items if it.id == "ev_obs_temp_current"]
    assert len(obs_temps) == 1
    assert obs_temps[0].value == 22.5
    assert obs_temps[0].unit == "°C"
    assert obs_temps[0].source_type == EvidenceSourceType.OBSERVED
    assert obs_temps[0].source_name == "Open-Meteo Current Weather API"

    obs_humidity = [it for it in collection.items if it.id == "ev_obs_humidity_current"]
    assert len(obs_humidity) == 1
    assert obs_humidity[0].value == 65.0

    obs_wind = [it for it in collection.items if it.id == "ev_obs_wind_dir_current"]
    assert len(obs_wind) == 1
    assert obs_wind[0].value == "E"  # 90 degrees = East

    # 2. Check Forecast hourly items
    fc_temps = collection.find_by_variable(WeatherVariable.TEMPERATURE)
    assert len(fc_temps) >= 12
    # Verify forecast source type
    fc_item = [it for it in fc_temps if it.source_type == EvidenceSourceType.FORECAST][0]
    assert fc_item.source_type == EvidenceSourceType.FORECAST

    # 3. Check Derived analysis items
    derived_items = [it for it in collection.items if it.source_type == EvidenceSourceType.DERIVED]
    assert len(derived_items) > 0
    # Umbrella item should be derived
    umbrella_items = collection.find_by_variable(WeatherVariable.UMBRELLA_NEED)
    assert len(umbrella_items) == 1
    assert umbrella_items[0].source_type == EvidenceSourceType.DERIVED

    # 4. Check query helpers
    found = collection.find_by_variable_and_period(WeatherVariable.TEMPERATURE, "16:00")
    assert len(found) >= 1

    by_id = collection.get_by_id("ev_obs_temp_current")
    assert by_id is not None
    assert by_id.value == 22.5

    summary = collection.to_summary_dict()
    assert "temperature" in summary
    assert "humidity" in summary

    print("  -> Passed EvidenceEngine extraction and provenance tests.")


def test_empty_and_partial_data():
    print("Testing EvidenceEngine with empty and partial inputs...")
    engine = EvidenceEngine()

    # Completely empty inputs must not raise exceptions
    empty_col = engine.generate_evidence()
    assert len(empty_col.items) == 0

    # Current only
    cur_col = engine.generate_evidence(current_data={"current": {"temperature_2m": 18.0}})
    assert len(cur_col.items) == 1
    assert cur_col.items[0].value == 18.0

    print("  -> Passed empty and partial data tests.")


def run_all():
    print("\n" + "=" * 60)
    print("RUNNING EVIDENCE ENGINE UNIT TESTS")
    print("=" * 60)
    test_evidence_engine_extraction()
    test_empty_and_partial_data()
    print("\nALL EVIDENCE ENGINE UNIT TESTS PASSED SUCCESSFULLY!\n")


if __name__ == "__main__":
    run_all()
