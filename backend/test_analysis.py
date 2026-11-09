import math
import sys
from pathlib import Path

# Ensure backend can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.weather.analysis import (
    degrees_to_cardinal,
    analyze_temperature,
    analyze_humidity,
    analyze_precipitation,
    analyze_wind,
    detect_weather_patterns,
    aggregate_6hour_blocks,
    compare_days,
    evaluate_umbrella_recommendation,
    evaluate_outdoor_suitability,
    evaluate_travel_suitability,
    get_weather_decision_support,
    analyze_weather_data,
)


def create_mock_forecast():
    """Generates a deterministic 48-hour mock forecast."""
    times_d1 = [f"2026-11-09T{h:02d}:00" for h in range(24)]
    times_d2 = [f"2026-11-10T{h:02d}:00" for h in range(24)]
    all_times = times_d1 + times_d2

    # Day 1: cool dry day (12°C to 22°C), zero rain, gentle wind
    # Day 2: warmer day (15°C to 26°C), afternoon thunderstorm (14:00-18:00) with rain & wind
    temps = []
    humidities = []
    probs = []
    rains = []
    codes = []
    winds = []
    wind_dirs = []
    pressures = []
    clouds = []

    for h in range(48):
        day = h // 24
        hour = h % 24

        if day == 0:
            # Day 1
            t = 12.0 + 10.0 * math.sin(math.pi * (hour - 6) / 12) if 6 <= hour <= 18 else 12.0
            hum = 70.0 - 25.0 * math.sin(math.pi * (hour - 6) / 12) if 6 <= hour <= 18 else 70.0
            p = 0.0
            r = 0.0
            c = 0
            w = 8.0 + 4.0 * math.sin(math.pi * hour / 12)
            wdir = 90.0  # East
            press = 945.0
            cloud = 10.0
        else:
            # Day 2
            t = 15.0 + 11.0 * math.sin(math.pi * (hour - 6) / 12) if 6 <= hour <= 18 else 15.0
            hum = 65.0 - 15.0 * math.sin(math.pi * (hour - 6) / 12) if 6 <= hour <= 18 else 65.0
            # Afternoon rain at hours 14-17 (h=38 to 41)
            if 14 <= hour <= 17:
                p = 80.0
                r = 2.5
                c = 95  # Thunderstorm
                w = 32.0  # Strong breeze
                press = 938.0  # Pressure drop
                cloud = 95.0
                hum = 88.0
            else:
                p = 10.0
                r = 0.0
                c = 1  # Mainly clear
                w = 12.0
                press = 943.0
                cloud = 25.0
            wdir = 270.0  # West

        temps.append(round(t, 1))
        humidities.append(round(hum, 1))
        probs.append(round(p, 1))
        rains.append(round(r, 2))
        codes.append(c)
        winds.append(round(w, 1))
        wind_dirs.append(wdir)
        pressures.append(press)
        clouds.append(cloud)

    return {
        "hourly": {
            "time": all_times,
            "temperature_2m": temps,
            "relative_humidity_2m": humidities,
            "precipitation_probability": probs,
            "precipitation": rains,
            "weather_code": codes,
            "wind_speed_10m": winds,
            "wind_direction_10m": wind_dirs,
            "surface_pressure": pressures,
            "cloud_cover": clouds,
        }
    }


def test_cardinal_conversion():
    print("Testing cardinal direction conversions...")
    assert degrees_to_cardinal(0) == "N"
    assert degrees_to_cardinal(360) == "N"
    assert degrees_to_cardinal(90) == "E"
    assert degrees_to_cardinal(180) == "S"
    assert degrees_to_cardinal(270) == "W"
    assert degrees_to_cardinal(45) == "NE"
    assert degrees_to_cardinal(225) == "SW"
    assert degrees_to_cardinal(None) == "Unknown"
    print("  -> Passed cardinal conversions.")


def test_temperature_analysis():
    print("Testing temperature analysis...")
    mock = create_mock_forecast()

    # Day 1 analysis (hours 0-23)
    res_d1 = analyze_temperature(mock, 0, 24)
    assert res_d1["status"] == "ok"
    assert res_d1["min_temperature"] == 12.0
    assert res_d1["max_temperature"] == 22.0
    assert res_d1["temperature_range"] == 10.0
    assert "average_temperature" in res_d1
    assert "steepest_rise" in res_d1

    # Rising trend dataset
    rising_data = {
        "hourly": {
            "time": [f"T{h:02d}" for h in range(10)],
            "temperature_2m": [10.0, 11.5, 13.0, 15.0, 17.0, 18.5, 20.0, 21.0, 22.5, 24.0],
        }
    }
    res_rise = analyze_temperature(rising_data, 0, 10)
    assert res_rise["trend"] == "increasing"
    assert res_rise["net_temperature_difference"] == 14.0

    # Falling trend dataset
    falling_data = {
        "hourly": {
            "time": [f"T{h:02d}" for h in range(10)],
            "temperature_2m": [25.0, 24.0, 22.5, 20.0, 18.0, 16.5, 15.0, 14.0, 13.0, 12.0],
        }
    }
    res_fall = analyze_temperature(falling_data, 0, 10)
    assert res_fall["trend"] == "decreasing"
    assert res_fall["net_temperature_difference"] == -13.0

    # Sub-zero negative temperatures
    cold_data = {
        "hourly": {
            "time": ["T1", "T2", "T3"],
            "temperature_2m": [-15.5, -8.0, -12.0],
        }
    }
    res_cold = analyze_temperature(cold_data, 0, 3)
    assert res_cold["min_temperature"] == -15.5
    assert res_cold["max_temperature"] == -8.0
    print("  -> Passed temperature analysis.")


def test_humidity_analysis():
    print("Testing humidity analysis...")
    # Test comfortable humidity
    mock = create_mock_forecast()
    res_h1 = analyze_humidity(mock, 0, 24)
    assert res_h1["status"] == "ok"
    assert 40.0 <= res_h1["average_humidity"] <= 70.0

    # Test extreme dry humidity
    dry_data = {"hourly": {"relative_humidity_2m": [15, 18, 22, 20]}}
    res_dry = analyze_humidity(dry_data, 0, 4)
    assert res_dry["comfort_level"] == "dry"

    # Test oppressive humidity with surge
    oppressive_data = {"hourly": {"time": ["T0", "T1", "T2"], "relative_humidity_2m": [60, 75, 88]}}
    res_opp = analyze_humidity(oppressive_data, 0, 3)
    assert res_opp["significant_shifts_count"] >= 1
    assert res_opp["significant_shifts"][0]["type"] == "surge"
    print("  -> Passed humidity analysis.")


def test_precipitation_analysis():
    print("Testing precipitation analysis...")
    mock = create_mock_forecast()

    # Day 1: dry
    res_p1 = analyze_precipitation(mock, 0, 24)
    assert res_p1["status"] == "ok"
    assert res_p1["risk_level"] == "none"
    assert res_p1["total_expected_rain_mm"] == 0.0

    # Day 2: rainy afternoon
    res_p2 = analyze_precipitation(mock, 24, 24)
    assert res_p2["status"] == "ok"
    assert res_p2["risk_level"] == "high"
    assert res_p2["max_probability"] == 80.0
    assert res_p2["total_expected_rain_mm"] == 10.0
    assert len(res_p2["elevated_periods"]) == 4

    # High probability, low accumulation (sprinkles)
    sprinkles = {"hourly": {"precipitation_probability": [75, 80], "precipitation": [0.05, 0.05]}}
    res_sp = analyze_precipitation(sprinkles, 0, 2)
    assert "minimal accumulation" in res_sp["distinction_note"].lower()
    print("  -> Passed precipitation analysis.")


def test_wind_analysis():
    print("Testing wind analysis...")
    mock = create_mock_forecast()

    # Day 1: light wind
    res_w1 = analyze_wind(mock, 0, 24)
    assert res_w1["status"] == "ok"
    assert res_w1["max_wind_speed"] < 15.0
    assert res_w1["prevailing_direction"] == "E"

    # Day 2: strong wind during storm
    res_w2 = analyze_wind(mock, 24, 24)
    assert res_w2["max_wind_speed"] == 32.0
    assert res_w2["strong_periods_count"] >= 4
    assert res_w2["prevailing_direction"] == "W"
    print("  -> Passed wind analysis.")


def test_pattern_detection():
    print("Testing weather pattern detection...")
    mock = create_mock_forecast()

    # Day 2 storm pattern
    res_pat = detect_weather_patterns(mock, 24, 24)
    assert res_pat["status"] == "ok"
    assert len(res_pat["conditions_sequence"]) >= 2
    # Pressure dropped from 943 to 938 during storm
    assert res_pat["pressure_trend"] in ("falling", "falling_rapidly")
    print("  -> Passed pattern detection.")


def test_time_aggregations():
    print("Testing time aggregations (6-hour blocks & day comparison)...")
    mock = create_mock_forecast()

    # 6-hour blocks for Day 1
    blocks_d1 = aggregate_6hour_blocks(mock, day_offset=0)
    assert len(blocks_d1["blocks"]) == 4
    names = [b["period"] for b in blocks_d1["blocks"]]
    assert names == ["Night", "Morning", "Afternoon", "Evening"]

    # Day comparison (Day 1 vs Day 2)
    comp = compare_days(mock)
    assert comp["status"] == "ok"
    assert "warmer" in comp["comparison_summary"].lower()
    assert comp["deltas"]["rain_diff_mm"] == 10.0
    print("  -> Passed time aggregations.")


def test_decision_support():
    print("Testing decision support rules (umbrella, outdoor, travel)...")
    mock = create_mock_forecast()

    # Day 1: No umbrella, Good outdoor, Suitable travel
    dec_d1 = get_weather_decision_support(mock, day_offset=0)
    assert dec_d1["umbrella"]["recommended"] is False
    assert dec_d1["travel"]["caution_level"] == "low"
    assert "best_period" in dec_d1["outdoor_activities"]

    # Day 2: Umbrella recommended, Caution advised due to thunderstorm
    dec_d2 = get_weather_decision_support(mock, day_offset=1)
    assert dec_d2["umbrella"]["recommended"] is True
    assert dec_d2["umbrella"]["confidence"] == "high"
    assert dec_d2["travel"]["caution_level"] in ("moderate", "high")
    assert any("thunderstorm" in a.lower() or "rain" in a.lower() for a in dec_d2["travel"]["advisories"])
    print("  -> Passed decision support.")


def test_edge_cases_and_missing_data():
    print("Testing edge cases and missing data handling...")

    # Completely empty dict
    res_empty_temp = analyze_temperature({}, 0, 24)
    assert "status" in res_empty_temp

    res_empty_precip = analyze_precipitation({}, 0, 24)
    assert res_empty_precip["status"] == "ok"
    assert res_empty_precip["total_expected_rain_mm"] == 0.0

    res_empty_wind = analyze_wind({}, 0, 24)
    assert res_empty_wind["status"] == "ok"

    # None and corrupted data
    corrupted = {
        "hourly": {
            "time": ["T1", "T2", "T3"],
            "temperature_2m": [None, "invalid", 18.0],
            "precipitation_probability": [None, None, 10.0],
        }
    }
    res_corrupt_t = analyze_temperature(corrupted, 0, 3)
    assert res_corrupt_t["status"] == "ok"

    # Non-dict input
    res_none = analyze_temperature(None, 0, 24)
    assert "status" in res_none

    mock = create_mock_forecast()
    # Full analyzer coordinator call with focus="recommendations"
    full_rec = analyze_weather_data(mock, focus="recommendations", day_offset=1)
    assert full_rec["umbrella"]["recommended"] is True

    # Full analyzer with focus="all"
    full_all = analyze_weather_data(mock, focus="all", day_offset=1)
    assert "temperature" in full_all
    assert "precipitation" in full_all
    assert "wind" in full_all
    assert "humidity" in full_all
    assert "6hour_blocks" in full_all
    assert "decision_support" in full_all
    print("  -> Passed edge cases and corrupted data handling.")


def run_all():
    print("\n" + "=" * 60)
    print("RUNNING PYTHON WEATHER ANALYSIS ENGINE UNIT TESTS")
    print("=" * 60)
    test_cardinal_conversion()
    test_temperature_analysis()
    test_humidity_analysis()
    test_precipitation_analysis()
    test_wind_analysis()
    test_pattern_detection()
    test_time_aggregations()
    test_decision_support()
    test_edge_cases_and_missing_data()
    print("\nALL WEATHER ANALYSIS ENGINE UNIT TESTS PASSED SUCCESSFULLY!\n")


if __name__ == "__main__":
    run_all()
