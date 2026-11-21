import json
from pathlib import Path


def generate_fixtures():
    """Builds realistic synthetic weather fixtures simulating Open-Meteo API outputs."""
    times_48 = [f"2026-11-16T{h:02d}:00" for h in range(24)] + [f"2026-11-17T{h:02d}:00" for h in range(24)]

    fixtures = {
        "version": "1.0.0",
        "description": "Deterministic synthetic weather data fixtures for Sky Reader Phase 7 evaluation benchmark.",
        "fixtures": {}
    }

    # 1. FIX_DEHRADUN_MILD (Mild autumn weather)
    t_deh = [15.0 + 10.0 * (1 - abs(h - 14) / 10) if 4 <= h <= 20 else 14.2 for h in range(24)]
    t_deh_48 = t_deh + [round(x - 0.7, 1) for x in t_deh]
    fixtures["fixtures"]["FIX_DEHRADUN_MILD"] = {
        "fixture_id": "FIX_DEHRADUN_MILD",
        "description": "Mild, clear autumn weather with pleasant diurnal swing and zero precipitation.",
        "location": {"name": "Dehradun", "latitude": 30.3165, "longitude": 78.0322, "country": "India", "timezone": "Asia/Kolkata"},
        "is_synthetic": True,
        "current": {
            "time": "2026-11-16T12:00",
            "temperature_2m": 21.8,
            "relative_humidity_2m": 58,
            "apparent_temperature": 22.1,
            "wind_speed_10m": 8.5,
            "wind_direction_10m": 45,
            "surface_pressure": 945.2,
            "cloud_cover": 10,
            "weather_code": 0
        },
        "hourly": {
            "time": times_48,
            "temperature_2m": t_deh_48,
            "relative_humidity_2m": [58] * 48,
            "precipitation_probability": [0.0] * 48,
            "precipitation": [0.0] * 48,
            "wind_speed_10m": [8.5] * 48,
            "surface_pressure": [945.0] * 48,
            "weather_code": [0] * 48
        },
        "metadata": {"climate": "subtropical_highland", "expected_risk": "LOW"}
    }

    # 2. FIX_LONDON_RAIN (Cool, overcast with moderate rainfall)
    t_lon = [11.0 + 3.0 * (1 - abs(h - 14) / 10) if 6 <= h <= 20 else 10.5 for h in range(24)]
    p_amt_lon = [0.0] * 10 + [1.5, 2.5, 3.5, 3.0, 2.5, 2.0, 1.5, 1.0, 0.5, 0.5] + [0.0] * 4
    p_prob_lon = [10.0] * 8 + [40.0, 70.0, 85.0, 90.0, 90.0, 85.0, 80.0, 75.0, 60.0, 50.0, 30.0, 20.0] + [10.0] * 4
    fixtures["fixtures"]["FIX_LONDON_RAIN"] = {
        "fixture_id": "FIX_LONDON_RAIN",
        "description": "Overcast maritime weather with steady rain (18.5 mm total) and high humidity.",
        "location": {"name": "London", "latitude": 51.5074, "longitude": -0.1278, "country": "United Kingdom", "timezone": "Europe/London"},
        "is_synthetic": True,
        "current": {
            "time": "2026-11-16T12:00",
            "temperature_2m": 13.5,
            "relative_humidity_2m": 88,
            "apparent_temperature": 12.2,
            "wind_speed_10m": 15.2,
            "wind_direction_10m": 220,
            "surface_pressure": 1008.2,
            "cloud_cover": 95,
            "weather_code": 61
        },
        "hourly": {
            "time": times_48,
            "temperature_2m": t_lon * 2,
            "relative_humidity_2m": [88] * 48,
            "precipitation_probability": p_prob_lon * 2,
            "precipitation": p_amt_lon * 2,
            "wind_speed_10m": [15.2] * 48,
            "surface_pressure": [1008.0] * 48,
            "weather_code": [61] * 48
        },
        "metadata": {"climate": "temperate_oceanic", "expected_risk": "MODERATE", "total_rain_24h": 18.5}
    }

    # 3. FIX_TOKYO_HEAT (Dangerous extreme heatwave)
    t_tok = [28.0 + 13.5 * (1 - abs(h - 14) / 10) if 5 <= h <= 21 else 27.5 for h in range(24)]
    fixtures["fixtures"]["FIX_TOKYO_HEAT"] = {
        "fixture_id": "FIX_TOKYO_HEAT",
        "description": "Dangerous extreme heatwave exceeding 41.5°C peak with severe heat exhaustion risk.",
        "location": {"name": "Tokyo", "latitude": 35.6762, "longitude": 139.6503, "country": "Japan", "timezone": "Asia/Tokyo"},
        "is_synthetic": True,
        "current": {
            "time": "2026-11-16T12:00",
            "temperature_2m": 38.5,
            "relative_humidity_2m": 70,
            "apparent_temperature": 42.0,
            "wind_speed_10m": 12.0,
            "wind_direction_10m": 180,
            "surface_pressure": 1012.0,
            "cloud_cover": 5,
            "weather_code": 0
        },
        "hourly": {
            "time": times_48,
            "temperature_2m": t_tok * 2,
            "relative_humidity_2m": [70] * 48,
            "precipitation_probability": [5.0] * 48,
            "precipitation": [0.0] * 48,
            "wind_speed_10m": [12.0] * 48,
            "surface_pressure": [1012.0] * 48,
            "weather_code": [0] * 48
        },
        "metadata": {"climate": "humid_subtropical", "expected_risk": "HIGH", "peak_temp": 41.5}
    }

    # 4. FIX_CHICAGO_FREEZE (Sub-zero extreme cold and snow)
    t_chi = [-15.0 + 7.0 * (1 - abs(h - 14) / 10) if 6 <= h <= 20 else -15.0 for h in range(24)]
    fixtures["fixtures"]["FIX_CHICAGO_FREEZE"] = {
        "fixture_id": "FIX_CHICAGO_FREEZE",
        "description": "Arctic freeze with minimum temperatures down to -15.0°C and blustery winds.",
        "location": {"name": "Chicago", "latitude": 41.8781, "longitude": -87.6298, "country": "United States", "timezone": "America/Chicago"},
        "is_synthetic": True,
        "current": {
            "time": "2026-11-16T12:00",
            "temperature_2m": -8.5,
            "relative_humidity_2m": 65,
            "apparent_temperature": -16.0,
            "wind_speed_10m": 32.0,
            "wind_direction_10m": 330,
            "surface_pressure": 1025.0,
            "cloud_cover": 80,
            "weather_code": 71
        },
        "hourly": {
            "time": times_48,
            "temperature_2m": t_chi * 2,
            "relative_humidity_2m": [65] * 48,
            "precipitation_probability": [20.0] * 48,
            "precipitation": [0.2] * 48,
            "wind_speed_10m": [32.0] * 48,
            "surface_pressure": [1025.0] * 48,
            "weather_code": [71] * 48
        },
        "metadata": {"climate": "humid_continental", "expected_risk": "HIGH", "min_temp": -15.0}
    }

    # 5. FIX_PARIS_STORM (Severe thunderstorm with hail and gale winds)
    p_paris = [0.0] * 12 + [8.0, 24.0, 12.0, 4.0] + [0.0] * 8
    w_paris = [15.0] * 12 + [45.0, 68.0, 55.0, 35.0] + [15.0] * 8
    c_paris = [2] * 12 + [95, 99, 95, 80] + [2] * 8
    fixtures["fixtures"]["FIX_PARIS_STORM"] = {
        "fixture_id": "FIX_PARIS_STORM",
        "description": "Severe convective thunderstorm with damaging hail (WMO 99), 68 km/h gales, and flash rain.",
        "location": {"name": "Paris", "latitude": 48.8566, "longitude": 2.3522, "country": "France", "timezone": "Europe/Paris"},
        "is_synthetic": True,
        "current": {
            "time": "2026-11-16T12:00",
            "temperature_2m": 22.0,
            "relative_humidity_2m": 82,
            "apparent_temperature": 23.0,
            "wind_speed_10m": 25.0,
            "wind_direction_10m": 210,
            "surface_pressure": 1004.5,
            "cloud_cover": 90,
            "weather_code": 95
        },
        "hourly": {
            "time": times_48,
            "temperature_2m": [22.0] * 48,
            "relative_humidity_2m": [85] * 48,
            "precipitation_probability": ([10.0] * 12 + [95.0] * 4 + [20.0] * 8) * 2,
            "precipitation": p_paris * 2,
            "wind_speed_10m": w_paris * 2,
            "surface_pressure": ([1015.0] * 8 + [1005.0] * 4 + [998.0] * 4 + [1008.0] * 8) * 2,
            "weather_code": c_paris * 2
        },
        "metadata": {"climate": "oceanic", "expected_risk": "SEVERE", "max_wind": 68.0, "hail": True}
    }

    # 6. FIX_MUMBAI_MONSOON (Torrential monsoon rainfall)
    p_mum = [2.0, 3.0, 5.0, 4.0, 6.0, 8.0, 10.0, 12.0, 8.0, 6.0, 4.0, 3.0, 2.0, 1.0] + [0.5] * 10
    fixtures["fixtures"]["FIX_MUMBAI_MONSOON"] = {
        "fixture_id": "FIX_MUMBAI_MONSOON",
        "description": "Torrential tropical monsoon downpour totaling 75.0 mm with severe waterlogging potential.",
        "location": {"name": "Mumbai", "latitude": 19.0760, "longitude": 72.8777, "country": "India", "timezone": "Asia/Kolkata"},
        "is_synthetic": True,
        "current": {
            "time": "2026-11-16T12:00",
            "temperature_2m": 28.0,
            "relative_humidity_2m": 95,
            "apparent_temperature": 34.0,
            "wind_speed_10m": 24.0,
            "wind_direction_10m": 240,
            "surface_pressure": 1002.0,
            "cloud_cover": 100,
            "weather_code": 65
        },
        "hourly": {
            "time": times_48,
            "temperature_2m": [28.0] * 48,
            "relative_humidity_2m": [95] * 48,
            "precipitation_probability": [100.0] * 48,
            "precipitation": p_mum * 2,
            "wind_speed_10m": [24.0] * 48,
            "surface_pressure": [1002.0] * 48,
            "weather_code": [65] * 48
        },
        "metadata": {"climate": "tropical_wet_and_dry", "expected_risk": "SEVERE", "total_rain_24h": 75.0}
    }

    # 7. FIX_BERLIN_WIND (High wind gusts and gale force)
    w_ber = [25.0] * 8 + [35.0, 42.0, 48.0, 52.0, 48.0, 45.0, 38.0, 30.0] + [22.0] * 8
    fixtures["fixtures"]["FIX_BERLIN_WIND"] = {
        "fixture_id": "FIX_BERLIN_WIND",
        "description": "Strong frontal wind event with sustained winds peaking at 52.0 km/h and high vehicle caution.",
        "location": {"name": "Berlin", "latitude": 52.5200, "longitude": 13.4050, "country": "Germany", "timezone": "Europe/Berlin"},
        "is_synthetic": True,
        "current": {
            "time": "2026-11-16T12:00",
            "temperature_2m": 16.0,
            "relative_humidity_2m": 60,
            "apparent_temperature": 14.5,
            "wind_speed_10m": 48.0,
            "wind_direction_10m": 270,
            "surface_pressure": 1010.0,
            "cloud_cover": 65,
            "weather_code": 3
        },
        "hourly": {
            "time": times_48,
            "temperature_2m": [16.0] * 48,
            "relative_humidity_2m": [60] * 48,
            "precipitation_probability": [15.0] * 48,
            "precipitation": [0.0] * 48,
            "wind_speed_10m": w_ber * 2,
            "surface_pressure": [1010.0] * 48,
            "weather_code": [3] * 48
        },
        "metadata": {"climate": "temperate_continental", "expected_risk": "HIGH", "max_wind": 52.0}
    }

    # 8. FIX_PHOENIX_TREND (Steep diurnal warming trend)
    t_phx = [22.0, 21.5, 21.0, 20.5, 20.0, 21.0, 23.5, 26.0, 29.0, 32.0, 34.5, 36.0, 36.0, 35.0, 33.5, 31.0, 28.5, 26.5, 25.0, 24.0, 23.5, 23.0, 22.5, 22.0]
    fixtures["fixtures"]["FIX_PHOENIX_TREND"] = {
        "fixture_id": "FIX_PHOENIX_TREND",
        "description": "Steep desert warming trend rising from 20.0°C to 36.0°C with dry conditions.",
        "location": {"name": "Phoenix", "latitude": 33.4484, "longitude": -112.0740, "country": "United States", "timezone": "America/Phoenix"},
        "is_synthetic": True,
        "current": {
            "time": "2026-11-16T12:00",
            "temperature_2m": 34.5,
            "relative_humidity_2m": 22,
            "apparent_temperature": 33.0,
            "wind_speed_10m": 10.0,
            "wind_direction_10m": 120,
            "surface_pressure": 1014.0,
            "cloud_cover": 0,
            "weather_code": 0
        },
        "hourly": {
            "time": times_48,
            "temperature_2m": t_phx * 2,
            "relative_humidity_2m": [22] * 48,
            "precipitation_probability": [5.0] * 48,
            "precipitation": [0.0] * 48,
            "wind_speed_10m": [10.0] * 48,
            "surface_pressure": [1014.0] * 48,
            "weather_code": [0] * 48
        },
        "metadata": {"climate": "subtropical_desert", "trend": "increasing", "delta": 16.0}
    }

    # 9. FIX_REYKJAVIK_COLD (Sub-zero coastal freezing)
    t_reyk = [-2.0, -2.5, -3.0, -3.5, -4.0, -4.0, -3.5, -3.0, -2.0, -1.0, 0.0, 1.0, 1.0, 0.5, 0.0, -1.0, -1.5, -2.0, -2.5, -3.0, -3.5, -3.5, -4.0, -4.0]
    fixtures["fixtures"]["FIX_REYKJAVIK_COLD"] = {
        "fixture_id": "FIX_REYKJAVIK_COLD",
        "description": "Freezing subpolar maritime climate oscillating between 1.0°C and -4.0°C.",
        "location": {"name": "Reykjavik", "latitude": 64.1466, "longitude": -21.9426, "country": "Iceland", "timezone": "Atlantic/Reykjavik"},
        "is_synthetic": True,
        "current": {
            "time": "2026-11-16T12:00",
            "temperature_2m": -2.0,
            "relative_humidity_2m": 78,
            "apparent_temperature": -7.5,
            "wind_speed_10m": 28.0,
            "wind_direction_10m": 90,
            "surface_pressure": 995.0,
            "cloud_cover": 85,
            "weather_code": 85
        },
        "hourly": {
            "time": times_48,
            "temperature_2m": t_reyk * 2,
            "relative_humidity_2m": [78] * 48,
            "precipitation_probability": [40.0] * 48,
            "precipitation": [0.5] * 48,
            "wind_speed_10m": [28.0] * 48,
            "surface_pressure": [995.0] * 48,
            "weather_code": [85] * 48
        },
        "metadata": {"climate": "subpolar_oceanic", "expected_risk": "MODERATE", "min_temp": -4.0}
    }

    # 10. FIX_SYDNEY_CLEAR (Ideal outdoor conditions)
    t_syd = [18.0 + 8.0 * (1 - abs(h - 14) / 10) if 5 <= h <= 21 else 17.5 for h in range(24)]
    fixtures["fixtures"]["FIX_SYDNEY_CLEAR"] = {
        "fixture_id": "FIX_SYDNEY_CLEAR",
        "description": "Optimal spring weather with mild temperatures (17.5-26.0°C), gentle wind, and zero rain.",
        "location": {"name": "Sydney", "latitude": -33.8688, "longitude": 151.2093, "country": "Australia", "timezone": "Australia/Sydney"},
        "is_synthetic": True,
        "current": {
            "time": "2026-11-16T12:00",
            "temperature_2m": 23.0,
            "relative_humidity_2m": 50,
            "apparent_temperature": 23.0,
            "wind_speed_10m": 10.0,
            "wind_direction_10m": 60,
            "surface_pressure": 1018.0,
            "cloud_cover": 15,
            "weather_code": 1
        },
        "hourly": {
            "time": times_48,
            "temperature_2m": t_syd * 2,
            "relative_humidity_2m": [50] * 48,
            "precipitation_probability": [0.0] * 48,
            "precipitation": [0.0] * 48,
            "wind_speed_10m": [10.0] * 48,
            "surface_pressure": [1018.0] * 48,
            "weather_code": [1] * 48
        },
        "metadata": {"climate": "temperate", "outdoor_suitability": "Excellent", "expected_risk": "LOW"}
    }

    # 11. FIX_INCOMPLETE_SENSORS (Missing precipitation & corrupted wind)
    fixtures["fixtures"]["FIX_INCOMPLETE_SENSORS"] = {
        "fixture_id": "FIX_INCOMPLETE_SENSORS",
        "description": "Incomplete weather station record with missing precipitation and missing wind sensor data.",
        "location": {"name": "Incompleteville", "latitude": 45.0, "longitude": 10.0, "country": "Testland", "timezone": "UTC"},
        "is_synthetic": True,
        "current": {
            "time": "2026-11-16T12:00",
            "temperature_2m": 19.5,
            "relative_humidity_2m": None,
            "apparent_temperature": 19.5,
            "wind_speed_10m": None,
            "wind_direction_10m": None,
            "surface_pressure": 1013.0,
            "cloud_cover": None,
            "weather_code": None
        },
        "hourly": {
            "time": times_48,
            "temperature_2m": [19.5] * 48,
            "relative_humidity_2m": [None] * 48,
            "precipitation_probability": [None] * 48,
            "precipitation": [None] * 48,
            "wind_speed_10m": [None] * 48,
            "surface_pressure": [1013.0] * 48,
            "weather_code": [None] * 48
        },
        "metadata": {"missing_channels": ["precipitation", "wind", "humidity"], "expected_risk": "LOW"}
    }

    # 12. FIX_CORRUPTED_HOURLY (Empty forecast lists)
    fixtures["fixtures"]["FIX_CORRUPTED_HOURLY"] = {
        "fixture_id": "FIX_CORRUPTED_HOURLY",
        "description": "Corrupted API payload with zero hourly forecast data entries.",
        "location": {"name": "NullCity", "latitude": 0.0, "longitude": 0.0, "country": "NullIsland", "timezone": "UTC"},
        "is_synthetic": True,
        "current": {
            "time": "2026-11-16T12:00",
            "temperature_2m": 25.0,
            "relative_humidity_2m": 50,
            "apparent_temperature": 25.0,
            "wind_speed_10m": 5.0,
            "wind_direction_10m": 0,
            "surface_pressure": 1013.0,
            "cloud_cover": 0,
            "weather_code": 0
        },
        "hourly": {
            "time": [],
            "temperature_2m": [],
            "relative_humidity_2m": [],
            "precipitation_probability": [],
            "precipitation": [],
            "wind_speed_10m": [],
            "surface_pressure": [],
            "weather_code": []
        },
        "metadata": {"corrupted": True}
    }

    return fixtures


def generate_benchmark_dataset():
    """Builds the 50-test-case benchmark dataset covering all 10 evaluation categories."""
    dataset = {
        "name": "Sky Reader Phase 7 Evaluation Benchmark Dataset",
        "version": "1.0.0",
        "description": (
            "Structured evaluation dataset for benchmarking weather intelligence systems across 10 categories: "
            "current weather, hourly forecasts, comparisons, precipitation, trends, multi-step questions, "
            "evidence-based reasoning, safety/risks, missing data handling, and hallucination resistance."
        ),
        "total_cases": 50,
        "test_cases": []
    }

    # Helper to append test case
    def add_tc(tc_id, cat, q, loc, period, fix_id, exp_num, exp_claims, exp_risk, tol, req_tools=True,
               req_ev=False, req_risk=False, req_unc=False, should_hedge=False, systems=None, tags=None):
        if systems is None:
            systems = ["baseline_llm", "tool_using_agent", "sky_reader_full"]
        if tags is None:
            tags = {}
        dataset["test_cases"].append({
            "id": tc_id,
            "category": cat,
            "question": q,
            "location": loc,
            "forecast_period": period,
            "fixture_id": fix_id,
            "expected_numerical_values": exp_num,
            "expected_facts_or_claims": exp_claims,
            "expected_risk_classification": exp_risk,
            "evaluation_criteria": {
                "requires_tools": req_tools,
                "expected_claims": exp_claims,
                "allowed_numerical_tolerances": tol,
                "requires_evidence_proof": req_ev,
                "requires_risk_assessment": req_risk,
                "requires_uncertainty_note": req_unc,
                "should_refuse_or_hedge": should_hedge
            },
            "applicable_systems": systems,
            "metadata": tags
        })

    # =========================================================================
    # Category 1: current_weather (5 cases)
    # =========================================================================
    add_tc(
        "TC-CUR-001", "current_weather", "What is the current temperature in Dehradun?",
        "Dehradun", "current", "FIX_DEHRADUN_MILD",
        {"temperature": 21.8}, ["temperature is approximately 21.8 °C"], None, {"temperature": 1.0},
        req_tools=True, tags={"focus": "temperature"}
    )
    add_tc(
        "TC-CUR-002", "current_weather", "What is the current relative humidity and wind speed in London?",
        "London", "current", "FIX_LONDON_RAIN",
        {"humidity": 88.0, "wind_speed": 15.2}, ["humidity is 88%", "wind speed is 15.2 km/h"], None, {"humidity": 3.0, "wind_speed": 2.5},
        req_tools=True, tags={"focus": "humidity_wind"}
    )
    add_tc(
        "TC-CUR-003", "current_weather", "What are the current weather conditions and apparent temperature in Tokyo?",
        "Tokyo", "current", "FIX_TOKYO_HEAT",
        {"temperature": 38.5, "apparent_temperature": 42.0}, ["temperature is 38.5 °C", "feels like 42.0 °C"], None, {"temperature": 1.0, "apparent_temperature": 1.5},
        req_tools=True, tags={"focus": "feels_like"}
    )
    add_tc(
        "TC-CUR-004", "current_weather", "Is it currently freezing in Chicago, and what is the surface pressure?",
        "Chicago", "current", "FIX_CHICAGO_FREEZE",
        {"temperature": -8.5, "surface_pressure": 1025.0}, ["temperature is -8.5 °C", "sub-zero freezing conditions", "surface pressure 1025.0 hPa"], None, {"temperature": 1.0, "surface_pressure": 2.0},
        req_tools=True, tags={"focus": "freezing"}
    )
    add_tc(
        "TC-CUR-005", "current_weather", "What is the current barometric pressure and cloud cover in Paris?",
        "Paris", "current", "FIX_PARIS_STORM",
        {"surface_pressure": 1004.5, "cloud_cover": 90.0}, ["surface pressure is 1004.5 hPa", "cloud cover is 90%"], None, {"surface_pressure": 2.0, "cloud_cover": 10.0},
        req_tools=True, tags={"focus": "pressure"}
    )

    # =========================================================================
    # Category 2: hourly_forecast (5 cases)
    # =========================================================================
    add_tc(
        "TC-HLY-001", "hourly_forecast", "What is the hourly minimum and maximum temperature forecast for tomorrow in Dehradun?",
        "Dehradun", "tomorrow", "FIX_DEHRADUN_MILD",
        {"min_temperature": 13.5, "max_temperature": 24.8}, ["minimum temperature around 13.5 °C", "maximum temperature around 24.8 °C"], None, {"min_temperature": 1.0, "max_temperature": 1.0},
        req_tools=True, tags={"focus": "min_max"}
    )
    add_tc(
        "TC-HLY-002", "hourly_forecast", "How will temperatures evolve over the next 24 hours in Sydney?",
        "Sydney", "next_24h", "FIX_SYDNEY_CLEAR",
        {"min_temperature": 17.5, "max_temperature": 26.0}, ["minimum 17.5 °C", "maximum 26.0 °C"], None, {"min_temperature": 1.0, "max_temperature": 1.0},
        req_tools=True, tags={"focus": "hourly_range"}
    )
    add_tc(
        "TC-HLY-003", "hourly_forecast", "At what hour is the heaviest rain expected tomorrow in London, and what is the peak intensity?",
        "London", "tomorrow", "FIX_LONDON_RAIN",
        {"max_hourly_rain": 3.5}, ["peak rain intensity of 3.5 mm/h", "heaviest rainfall around 12:00 to 14:00"], None, {"max_hourly_rain": 0.5},
        req_tools=True, tags={"focus": "peak_rain_hour"}
    )
    add_tc(
        "TC-HLY-004", "hourly_forecast", "What will the peak wind speed be during the afternoon tomorrow in Berlin?",
        "Berlin", "tomorrow", "FIX_BERLIN_WIND",
        {"max_wind_speed": 52.0}, ["peak wind speed reaches 52.0 km/h in afternoon"], None, {"max_wind_speed": 3.0},
        req_tools=True, tags={"focus": "peak_wind"}
    )
    add_tc(
        "TC-HLY-005", "hourly_forecast", "Will temperatures drop below -10°C overnight in Chicago?",
        "Chicago", "tomorrow", "FIX_CHICAGO_FREEZE",
        {"min_temperature": -15.0}, ["temperatures drop to -15.0 °C", "below -10°C overnight"], None, {"min_temperature": 1.0},
        req_tools=True, tags={"focus": "overnight_freeze"}
    )

    # =========================================================================
    # Category 3: temperature_comparison (5 cases)
    # =========================================================================
    add_tc(
        "TC-CMP-001", "temperature_comparison", "Will tomorrow be warmer or cooler than today on average in Dehradun?",
        "Dehradun", "day_comparison", "FIX_DEHRADUN_MILD",
        {"average_diff": -0.7}, ["tomorrow is slightly cooler by about 0.7 °C or steady"], None, {"average_diff": 0.5},
        req_tools=True, tags={"focus": "day_diff"}
    )
    add_tc(
        "TC-CMP-002", "temperature_comparison", "Compare the morning and afternoon temperatures tomorrow in Phoenix.",
        "Phoenix", "tomorrow", "FIX_PHOENIX_TREND",
        {"morning_temperature": 21.0, "afternoon_temperature": 36.0, "delta": 15.0},
        ["morning temperature is around 21.0 °C", "afternoon rises to 36.0 °C", "rise of approximately 15 °C"], None, {"morning_temperature": 1.5, "afternoon_temperature": 1.5, "delta": 2.0},
        req_tools=True, tags={"focus": "diurnal_delta"}
    )
    add_tc(
        "TC-CMP-003", "temperature_comparison", "What is the diurnal temperature range (difference between high and low) in Sydney tomorrow?",
        "Sydney", "tomorrow", "FIX_SYDNEY_CLEAR",
        {"temperature_range": 8.5}, ["diurnal range of approximately 8.5 °C", "low of 17.5 °C and high of 26.0 °C"], None, {"temperature_range": 1.0},
        req_tools=True, tags={"focus": "diurnal_range"}
    )
    add_tc(
        "TC-CMP-004", "temperature_comparison", "How does Tokyo's peak temperature compare to London's peak temperature tomorrow?",
        "Tokyo", "tomorrow", "FIX_TOKYO_HEAT",
        {"tokyo_peak": 41.5, "london_peak": 14.0}, ["Tokyo reaches 41.5 °C", "London reaches around 14.0 °C", "Tokyo is much hotter by over 25 °C"], None, {"tokyo_peak": 1.5, "london_peak": 1.5},
        req_tools=True, tags={"focus": "cross_city"}
    )
    add_tc(
        "TC-CMP-005", "temperature_comparison", "How much will the temperature drop between peak daytime and midnight in Reykjavik?",
        "Reykjavik", "tomorrow", "FIX_REYKJAVIK_COLD",
        {"drop": 5.0}, ["drops from high of 1.0 °C to low of -4.0 °C", "net drop of 5.0 °C"], None, {"drop": 1.0},
        req_tools=True, tags={"focus": "cooling_drop"}
    )

    # =========================================================================
    # Category 4: precipitation_and_rainfall (5 cases)
    # =========================================================================
    add_tc(
        "TC-PRC-001", "precipitation_and_rainfall", "What is the probability of precipitation tomorrow in London, and how much total rain will fall?",
        "London", "tomorrow", "FIX_LONDON_RAIN",
        {"max_probability": 90.0, "total_expected_rain_mm": 18.5},
        ["peak rain probability of 90%", "total accumulation of 18.5 mm", "rain is likely"], None,
        {"max_probability": 5.0, "total_expected_rain_mm": 1.0},
        req_tools=True, req_unc=True, tags={"focus": "prob_vs_vol"}
    )
    add_tc(
        "TC-PRC-002", "precipitation_and_rainfall", "Will it rain tomorrow in Dehradun?",
        "Dehradun", "tomorrow", "FIX_DEHRADUN_MILD",
        {"max_probability": 0.0, "total_expected_rain_mm": 0.0},
        ["0% precipitation probability", "0.0 mm rainfall expected", "no rain"], None,
        {"max_probability": 5.0, "total_expected_rain_mm": 0.2},
        req_tools=True, tags={"focus": "zero_rain"}
    )
    add_tc(
        "TC-PRC-003", "precipitation_and_rainfall", "How much total rainfall accumulation is forecast for Mumbai tomorrow?",
        "Mumbai", "tomorrow", "FIX_MUMBAI_MONSOON",
        {"total_expected_rain_mm": 75.0, "max_probability": 100.0},
        ["total rainfall accumulation of 75.0 mm", "100% precipitation probability", "torrential monsoon rain"], None,
        {"total_expected_rain_mm": 5.0, "max_probability": 0.0},
        req_tools=True, req_unc=True, tags={"focus": "heavy_rain"}
    )
    add_tc(
        "TC-PRC-004", "precipitation_and_rainfall", "If precipitation probability is 95% in Paris tomorrow, does that mean it will rain all day?",
        "Paris", "tomorrow", "FIX_PARIS_STORM",
        {"max_probability": 95.0, "total_expected_rain_mm": 48.0},
        ["probability reflects chance of rain occurring", "does not mean continuous 24-hour rainfall", "concentrated during storm hours"], None,
        {"max_probability": 5.0, "total_expected_rain_mm": 4.0},
        req_tools=True, req_unc=True, tags={"focus": "prob_interpretation"}
    )
    add_tc(
        "TC-PRC-005", "precipitation_and_rainfall", "Is any rain expected in Phoenix tomorrow?",
        "Phoenix", "tomorrow", "FIX_PHOENIX_TREND",
        {"max_probability": 5.0, "total_expected_rain_mm": 0.0},
        ["negligible 5% rain chance", "0.0 mm expected", "dry conditions"], None,
        {"max_probability": 5.0, "total_expected_rain_mm": 0.2},
        req_tools=True, tags={"focus": "dry_weather"}
    )

    # =========================================================================
    # Category 5: weather_trends (5 cases)
    # =========================================================================
    add_tc(
        "TC-TRD-001", "weather_trends", "Is the temperature in Phoenix following an increasing, decreasing, or steady trend tomorrow?",
        "Phoenix", "tomorrow", "FIX_PHOENIX_TREND",
        {"net_difference": 16.0}, ["increasing trend", "warming trend", "temperatures rise by approximately 16 °C"], None,
        {"net_difference": 2.0}, req_tools=True, tags={"focus": "increasing_trend"}
    )
    add_tc(
        "TC-TRD-002", "weather_trends", "What is the overall 24-hour temperature trend in Dehradun tomorrow?",
        "Dehradun", "tomorrow", "FIX_DEHRADUN_MILD",
        {"net_difference": -0.7}, ["steady trend", "temperatures remain relatively stable", "net change under 1.5 °C"], None,
        {"net_difference": 1.0}, req_tools=True, tags={"focus": "steady_trend"}
    )
    add_tc(
        "TC-TRD-003", "weather_trends", "Is atmospheric pressure rising or falling in Paris as the storm approaches?",
        "Paris", "tomorrow", "FIX_PARIS_STORM",
        {"start_pressure": 1015.0, "min_pressure": 998.0},
        ["barometric pressure falls sharply", "drops from 1015 to 998 hPa", "indicates incoming storm system"], None,
        {"start_pressure": 2.0, "min_pressure": 2.0}, req_tools=True, tags={"focus": "pressure_trend"}
    )
    add_tc(
        "TC-TRD-004", "weather_trends", "Are wind speeds strengthening or diminishing tomorrow in Berlin?",
        "Berlin", "tomorrow", "FIX_BERLIN_WIND",
        {"start_wind": 25.0, "peak_wind": 52.0},
        ["wind speeds strengthen", "rising from 25.0 km/h to peak of 52.0 km/h"], None,
        {"start_wind": 3.0, "peak_wind": 3.0}, req_tools=True, tags={"focus": "wind_trend"}
    )
    add_tc(
        "TC-TRD-005", "weather_trends", "How will humidity levels change over the next 24 hours in London?",
        "London", "tomorrow", "FIX_LONDON_RAIN",
        {"humidity": 88.0}, ["high sustained humidity around 88%", "saturated air with precipitation"], None,
        {"humidity": 5.0}, req_tools=True, tags={"focus": "humidity_trend"}
    )

    # =========================================================================
    # Category 6: multistep_reasoning (5 cases)
    # =========================================================================
    add_tc(
        "TC-MLT-001", "multistep_reasoning", "What is the best time of day for outdoor activities tomorrow in Sydney, and why?",
        "Sydney", "tomorrow", "FIX_SYDNEY_CLEAR",
        {"avg_temperature": 23.0, "max_rain_probability": 0.0, "avg_wind_speed": 10.0},
        ["Morning or Afternoon is the best window", "pleasant temperature around 23 °C", "0% rain chance", "gentle wind 10 km/h"], None,
        {"avg_temperature": 1.5, "max_rain_probability": 5.0, "avg_wind_speed": 3.0},
        req_tools=True, tags={"focus": "outdoor_window"}
    )
    add_tc(
        "TC-MLT-002", "multistep_reasoning", "Should I carry an umbrella tomorrow in London?",
        "London", "tomorrow", "FIX_LONDON_RAIN",
        {"max_probability": 90.0, "total_expected_rain_mm": 18.5},
        ["umbrella is recommended", "high 90% rain probability", "18.5 mm rainfall accumulation"], None,
        {"max_probability": 5.0, "total_expected_rain_mm": 1.5},
        req_tools=True, tags={"focus": "umbrella_decision"}
    )
    add_tc(
        "TC-MLT-003", "multistep_reasoning", "Is tomorrow suitable for highway road travel around Berlin?",
        "Berlin", "tomorrow", "FIX_BERLIN_WIND",
        {"max_wind_speed": 52.0},
        ["Caution Advised", "strong winds up to 52.0 km/h", "caution for high-profile vehicles on exposed highways"], "HIGH",
        {"max_wind_speed": 3.0}, req_tools=True, req_risk=True, tags={"focus": "travel_suitability"}
    )
    add_tc(
        "TC-MLT-004", "multistep_reasoning", "Should I schedule an intense outdoor running session tomorrow afternoon in Tokyo?",
        "Tokyo", "tomorrow", "FIX_TOKYO_HEAT",
        {"peak_temperature": 41.5, "apparent_temperature": 42.0},
        ["not recommended for outdoor running", "extreme heat peak of 41.5 °C", "severe risk of heat exhaustion", "avoid afternoon peak hours"], "HIGH",
        {"peak_temperature": 1.5, "apparent_temperature": 2.0},
        req_tools=True, req_risk=True, tags={"focus": "sports_safety"}
    )
    add_tc(
        "TC-MLT-005", "multistep_reasoning", "Can I hang laundry outdoors to dry tomorrow in Dehradun?",
        "Dehradun", "tomorrow", "FIX_DEHRADUN_MILD",
        {"max_rain_probability": 0.0, "max_temperature": 24.8},
        ["suitable for hanging laundry outdoors", "0% chance of rain", "sunny and dry", "temperatures up to 24.8 °C"], None,
        {"max_rain_probability": 5.0, "max_temperature": 1.5},
        req_tools=True, tags={"focus": "laundry_drying"}
    )

    # =========================================================================
    # Category 7: evidence_based_reasoning (5 cases)
    # =========================================================================
    add_tc(
        "TC-EVD-001", "evidence_based_reasoning", "Explain the exact meteorological evidence for why an umbrella is not required in Dehradun tomorrow.",
        "Dehradun", "tomorrow", "FIX_DEHRADUN_MILD",
        {"peak_precipitation_probability": 0.0, "total_expected_rain_mm": 0.0},
        ["evidence shows 0% peak precipitation probability", "0.0 mm expected rainfall accumulation", "source Open-Meteo forecast", "umbrella not needed"], None,
        {"peak_precipitation_probability": 5.0, "total_expected_rain_mm": 0.2},
        req_tools=True, req_ev=True, tags={"focus": "umbrella_evidence"}
    )
    add_tc(
        "TC-EVD-002", "evidence_based_reasoning", "What specific measurement evidence justifies the travel caution level for Paris tomorrow?",
        "Paris", "tomorrow", "FIX_PARIS_STORM",
        {"max_wind_speed": 68.0, "total_rainfall": 48.0},
        ["evidence cites peak wind speeds of 68.0 km/h", "hail detected with WMO code 99", "rainfall accumulation 48.0 mm", "hazardous travel conditions"], "SEVERE",
        {"max_wind_speed": 4.0, "total_rainfall": 4.0},
        req_tools=True, req_ev=True, req_risk=True, tags={"focus": "travel_evidence"}
    )
    add_tc(
        "TC-EVD-003", "evidence_based_reasoning", "What exact temperature and humidity measurements back up your comfort analysis for Mumbai?",
        "Mumbai", "current", "FIX_MUMBAI_MONSOON",
        {"temperature": 28.0, "humidity": 95.0, "apparent_temperature": 34.0},
        ["temperature is 28.0 °C", "relative humidity is 95%", "apparent temperature reaches 34.0 °C", "oppressive thermal comfort"], None,
        {"temperature": 1.0, "humidity": 3.0, "apparent_temperature": 2.0},
        req_tools=True, req_ev=True, tags={"focus": "comfort_evidence"}
    )
    add_tc(
        "TC-EVD-004", "evidence_based_reasoning", "Cite the precise hourly delta figures demonstrating the morning temperature rise in Phoenix.",
        "Phoenix", "tomorrow", "FIX_PHOENIX_TREND",
        {"start_temperature": 20.0, "peak_temperature": 36.0, "net_rise": 16.0},
        ["morning low around 20.0 °C", "afternoon high of 36.0 °C", "net temperature rise of 16.0 °C"], None,
        {"start_temperature": 1.5, "peak_temperature": 1.5, "net_rise": 2.0},
        req_tools=True, req_ev=True, tags={"focus": "trend_evidence"}
    )
    add_tc(
        "TC-EVD-005", "evidence_based_reasoning", "What data provenance and forecast limitations apply to tomorrow's wind projections in Berlin?",
        "Berlin", "tomorrow", "FIX_BERLIN_WIND",
        {"max_wind_speed": 52.0},
        ["data derived from Open-Meteo numerical weather prediction", "peak wind 52.0 km/h", "accuracy naturally degrades beyond 24-48 hours", "local gusts may exceed model averages"], None,
        {"max_wind_speed": 3.0},
        req_tools=True, req_ev=True, req_unc=True, tags={"focus": "provenance_limits"}
    )

    # =========================================================================
    # Category 8: weather_safety_and_risk (5 cases)
    # =========================================================================
    add_tc(
        "TC-RSK-001", "weather_safety_and_risk", "Are there any severe weather hazards or storm risks in Paris tomorrow?",
        "Paris", "tomorrow", "FIX_PARIS_STORM",
        {"max_wind_speed": 68.0, "total_rain": 48.0},
        ["SEVERE risk level detected", "severe thunderstorm with hail", "gale-force winds reaching 68.0 km/h", "seek indoor shelter"], "SEVERE",
        {"max_wind_speed": 4.0, "total_rain": 4.0},
        req_tools=True, req_risk=True, req_unc=True, tags={"focus": "severe_storm"}
    )
    add_tc(
        "TC-RSK-002", "weather_safety_and_risk", "What health safety precautions are recommended for Tokyo tomorrow?",
        "Tokyo", "tomorrow", "FIX_TOKYO_HEAT",
        {"peak_temperature": 41.5},
        ["HIGH risk level", "extreme heat hazard", "stay hydrated with water and electrolytes", "avoid strenuous outdoor exertion between 11:00 and 16:00"], "HIGH",
        {"peak_temperature": 1.5},
        req_tools=True, req_risk=True, tags={"focus": "heat_precaution"}
    )
    add_tc(
        "TC-RSK-003", "weather_safety_and_risk", "What is the cold hazard level in Chicago tomorrow, and what precautions should be taken?",
        "Chicago", "tomorrow", "FIX_CHICAGO_FREEZE",
        {"min_temperature": -15.0, "wind_speed": 32.0},
        ["HIGH risk level", "extreme cold conditions", "temperatures dropping to -15.0 °C", "wear insulated thermal layers", "frostbite hazard on exposed skin"], "HIGH",
        {"min_temperature": 1.5, "wind_speed": 3.0},
        req_tools=True, req_risk=True, tags={"focus": "cold_precaution"}
    )
    add_tc(
        "TC-RSK-004", "weather_safety_and_risk", "Is there a flood or waterlogging risk in Mumbai tomorrow?",
        "Mumbai", "tomorrow", "FIX_MUMBAI_MONSOON",
        {"total_rain": 75.0},
        ["SEVERE risk level", "heavy rainfall accumulation of 75.0 mm", "high potential for flash flooding and waterlogging", "avoid low-lying flood-prone areas"], "SEVERE",
        {"total_rain": 5.0},
        req_tools=True, req_risk=True, tags={"focus": "flood_risk"}
    )
    add_tc(
        "TC-RSK-005", "weather_safety_and_risk", "Are there any hazardous weather conditions in Dehradun tomorrow?",
        "Dehradun", "tomorrow", "FIX_DEHRADUN_MILD",
        {},
        ["LOW risk level", "no significant weather hazards detected", "standard precautions"], "LOW",
        {},
        req_tools=True, req_risk=True, tags={"focus": "low_hazard"}
    )

    # =========================================================================
    # Category 9: missing_or_incomplete_data (5 cases)
    # =========================================================================
    add_tc(
        "TC-INC-001", "missing_or_incomplete_data", "What is the rain risk for tomorrow based on this forecast with missing precipitation channels?",
        "Incompleteville", "tomorrow", "FIX_INCOMPLETE_SENSORS",
        {},
        ["precipitation data is unavailable", "rainfall risk evaluation cannot be performed", "no false alarms triggered", "notes data limitation"], "LOW",
        {},
        req_tools=True, req_unc=True, should_hedge=True, tags={"focus": "missing_rain"}
    )
    add_tc(
        "TC-INC-002", "missing_or_incomplete_data", "What are the wind conditions in Incompleteville when wind sensors report null?",
        "Incompleteville", "tomorrow", "FIX_INCOMPLETE_SENSORS",
        {},
        ["wind speed data unavailable", "cannot determine wind conditions", "refuses to invent wind speeds"], None,
        {},
        req_tools=True, req_unc=True, should_hedge=True, tags={"focus": "missing_wind"}
    )
    add_tc(
        "TC-INC-003", "missing_or_incomplete_data", "How does the system handle a forecast query when the hourly forecast payload is completely empty?",
        "NullCity", "tomorrow", "FIX_CORRUPTED_HOURLY",
        {},
        ["no forecast data available", "graceful degradation", "does not fabricate numbers"], "LOW",
        {},
        req_tools=True, req_unc=True, should_hedge=True, tags={"focus": "empty_payload"}
    )
    add_tc(
        "TC-INC-004", "missing_or_incomplete_data", "Can you provide a travel safety assessment for Incompleteville?",
        "Incompleteville", "tomorrow", "FIX_INCOMPLETE_SENSORS",
        {"temperature": 19.5},
        ["assessment is based on limited information", "temperature is 19.5 °C", "precipitation and wind data missing", "exercise standard caution"], "LOW",
        {"temperature": 1.0},
        req_tools=True, req_unc=True, req_risk=True, should_hedge=True, tags={"focus": "partial_assessment"}
    )
    add_tc(
        "TC-INC-005", "missing_or_incomplete_data", "What is the current temperature in the fictional city 'AtlantisFantasyRealm999'?",
        "AtlantisFantasyRealm999", "current", None,
        {},
        ["could not find location", "unknown city", "does not invent weather data"], None,
        {},
        req_tools=True, should_hedge=True, tags={"focus": "ungeocodeable_city"}
    )

    # =========================================================================
    # Category 10: hallucination_resistance (5 cases)
    # =========================================================================
    add_tc(
        "TC-HAL-001", "hallucination_resistance", "What will the exact temperature in Dehradun be at 3:15 PM on November 15, 2035?",
        "Dehradun", "unspecified", None,
        {},
        ["cannot provide exact weather 10 years in the future", "forecast models are limited to 7-14 days", "refuses to fabricate far-future weather"], None,
        {},
        req_tools=False, should_hedge=True, tags={"focus": "far_future"}
    )
    add_tc(
        "TC-HAL-002", "hallucination_resistance", "Confirm that London's temperature yesterday reached 48.5°C during the heatwave.",
        "London", "current", "FIX_LONDON_RAIN",
        {"actual_temperature": 13.5},
        ["refutes false claim", "London is around 13.5 °C", "48.5 °C is factually incorrect"], None,
        {"actual_temperature": 2.0},
        req_tools=True, req_ev=True, should_hedge=True, tags={"focus": "false_premise_heat"}
    )
    add_tc(
        "TC-HAL-003", "hallucination_resistance", "Why is Tokyo currently experiencing a blizzard with -30°C temperatures?",
        "Tokyo", "current", "FIX_TOKYO_HEAT",
        {"actual_temperature": 38.5},
        ["refutes false premise", "Tokyo is experiencing extreme heat around 38.5 °C", "not a blizzard", "no sub-zero temperatures"], None,
        {"actual_temperature": 1.5},
        req_tools=True, req_ev=True, should_hedge=True, tags={"focus": "false_premise_blizzard"}
    )
    add_tc(
        "TC-HAL-004", "hallucination_resistance", "What is the weather right now in the capital city of Mars?",
        "Mars", "current", None,
        {},
        ["Mars does not have human cities", "Open-Meteo only covers Earth", "refuses to hallucinate Martian city weather"], None,
        {},
        req_tools=False, should_hedge=True, tags={"focus": "non_earth"}
    )
    add_tc(
        "TC-HAL-005", "hallucination_resistance", "State with 100% absolute certainty that exactly 14.332 mm of rain will fall at 2:00 PM tomorrow in Paris.",
        "Paris", "tomorrow", "FIX_PARIS_STORM",
        {"total_rain": 48.0},
        ["refuses to guarantee 100% certainty", "weather forecasts are probabilistic numerical estimates", "conditions may vary locally", "heavy rain is likely but not guaranteed"], None,
        {"total_rain": 4.0},
        req_tools=True, req_unc=True, should_hedge=True, tags={"focus": "absolute_certainty_refusal"}
    )

    return dataset


if __name__ == "__main__":
    fixtures_path = Path(__file__).parent / "fixtures" / "weather_fixtures.json"
    dataset_path = Path(__file__).parent / "datasets" / "weather_benchmark.json"

    fixtures = generate_fixtures()
    with open(fixtures_path, "w", encoding="utf-8") as f:
        json.dump(fixtures, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(fixtures['fixtures'])} fixtures to {fixtures_path}")

    dataset = generate_benchmark_dataset()
    with open(dataset_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(dataset['test_cases'])} test cases to {dataset_path}")
