import unittest
from datetime import datetime
from backend.weather.risk_engine import WeatherRiskEngine
from backend.weather.risk_models import RiskLevel, RiskType, RiskThresholds


def create_mock_hourly(
    temperatures=None,
    precipitation_probabilities=None,
    precipitations=None,
    wind_speeds=None,
    weather_codes=None,
    count=48,
):
    """Generates synthetic 48-hour hourly weather data dictionary for testing."""
    times = [f"2026-11-16T{i%24:02d}:00" for i in range(count)]
    return {
        "latitude": 30.33,
        "longitude": 78.03,
        "hourly": {
            "time": times,
            "temperature_2m": temperatures if temperatures is not None else [20.0] * count,
            "precipitation_probability": (
                precipitation_probabilities if precipitation_probabilities is not None else [0.0] * count
            ),
            "precipitation": precipitations if precipitations is not None else [0.0] * count,
            "wind_speed_10m": wind_speeds if wind_speeds is not None else [10.0] * count,
            "weather_code": weather_codes if weather_codes is not None else [0] * count,
        },
    }


class TestWeatherRiskEngine(unittest.TestCase):
    def setUp(self):
        self.engine = WeatherRiskEngine()

    # -----------------------------------------------------------------
    # Test 1: Normal weather conditions with no significant risk
    # -----------------------------------------------------------------
    def test_normal_weather_low_risk(self):
        # 20°C mild temp, 0% rain, 10 km/h gentle breeze, clear skies
        data = create_mock_hourly(
            temperatures=[22.0] * 48,
            precipitation_probabilities=[5.0] * 48,
            precipitations=[0.0] * 48,
            wind_speeds=[12.0] * 48,
            weather_codes=[0] * 48,
        )
        assessment = self.engine.assess_risks(data, day_offset=1)
        self.assertEqual(assessment.overall_risk_level, RiskLevel.LOW)
        self.assertEqual(len(assessment.detected_risks), 0)
        self.assertIn("No significant weather hazards", assessment.overall_summary)
        self.assertTrue(len(assessment.safety_recommendations) > 0)

    # -----------------------------------------------------------------
    # Test 2: Heavy rainfall conditions (MODERATE, HIGH, SEVERE)
    # -----------------------------------------------------------------
    def test_heavy_rainfall_risks(self):
        # Test Moderate Rain: 18 mm accumulation
        data_mod = create_mock_hourly(precipitations=[0.0] * 24 + [1.5] * 12 + [0.0] * 12)
        res_mod = self.engine.assess_risks(data_mod, day_offset=1)
        rain_risks = [r for r in res_mod.detected_risks if r.risk_type == RiskType.HEAVY_RAINFALL]
        self.assertEqual(len(rain_risks), 1)
        self.assertEqual(rain_risks[0].severity, RiskLevel.MODERATE)

        # Test High Rain: 35 mm accumulation
        data_high = create_mock_hourly(precipitations=[0.0] * 24 + [3.0] * 12 + [0.0] * 12)
        res_high = self.engine.assess_risks(data_high, day_offset=1)
        rain_risks_high = [r for r in res_high.detected_risks if r.risk_type == RiskType.HEAVY_RAINFALL]
        self.assertEqual(len(rain_risks_high), 1)
        self.assertEqual(rain_risks_high[0].severity, RiskLevel.HIGH)

        # Test Severe Rain: 65 mm accumulation or intense hourly rate (22 mm/h)
        data_sev = create_mock_hourly(precipitations=[0.0] * 24 + [22.0] + [2.0] * 23)
        res_sev = self.engine.assess_risks(data_sev, day_offset=1)
        rain_risks_sev = [r for r in res_sev.detected_risks if r.risk_type == RiskType.HEAVY_RAINFALL]
        self.assertEqual(len(rain_risks_sev), 1)
        self.assertEqual(rain_risks_sev[0].severity, RiskLevel.SEVERE)
        self.assertEqual(res_sev.overall_risk_level, RiskLevel.SEVERE)

    # -----------------------------------------------------------------
    # Test 3: Thunderstorm conditions (WMO 95, 96, 99)
    # -----------------------------------------------------------------
    def test_thunderstorm_conditions(self):
        # Code 95: Moderate thunderstorm
        data_ts = create_mock_hourly(weather_codes=[0] * 30 + [95] + [0] * 17)
        res_ts = self.engine.assess_risks(data_ts, day_offset=1)
        ts_risks = [r for r in res_ts.detected_risks if r.risk_type == RiskType.THUNDERSTORM]
        self.assertEqual(len(ts_risks), 1)
        self.assertEqual(ts_risks[0].severity, RiskLevel.HIGH)
        self.assertIn("indoors", " ".join(ts_risks[0].recommendations).lower())

        # Code 96/99: Severe thunderstorm with hail
        data_hail = create_mock_hourly(weather_codes=[0] * 30 + [99] + [0] * 17)
        res_hail = self.engine.assess_risks(data_hail, day_offset=1)
        hail_risks = [r for r in res_hail.detected_risks if r.risk_type == RiskType.THUNDERSTORM]
        self.assertEqual(len(hail_risks), 1)
        self.assertEqual(hail_risks[0].severity, RiskLevel.SEVERE)
        self.assertTrue(hail_risks[0].measurements["hail_detected"])

    # -----------------------------------------------------------------
    # Test 4: Strong wind conditions
    # -----------------------------------------------------------------
    def test_strong_wind_conditions(self):
        # Moderate wind: 35 km/h
        data_mod = create_mock_hourly(wind_speeds=[10.0] * 24 + [35.0] + [15.0] * 23)
        res_mod = self.engine.assess_risks(data_mod, day_offset=1)
        wind_mod = [r for r in res_mod.detected_risks if r.risk_type == RiskType.STRONG_WIND]
        self.assertEqual(len(wind_mod), 1)
        self.assertEqual(wind_mod[0].severity, RiskLevel.MODERATE)

        # High wind: 50 km/h
        data_high = create_mock_hourly(wind_speeds=[10.0] * 24 + [50.0] + [15.0] * 23)
        res_high = self.engine.assess_risks(data_high, day_offset=1)
        wind_high = [r for r in res_high.detected_risks if r.risk_type == RiskType.STRONG_WIND]
        self.assertEqual(len(wind_high), 1)
        self.assertEqual(wind_high[0].severity, RiskLevel.HIGH)

        # Severe gale: 70 km/h
        data_sev = create_mock_hourly(wind_speeds=[10.0] * 24 + [70.0] + [15.0] * 23)
        res_sev = self.engine.assess_risks(data_sev, day_offset=1)
        wind_sev = [r for r in res_sev.detected_risks if r.risk_type == RiskType.STRONG_WIND]
        self.assertEqual(len(wind_sev), 1)
        self.assertEqual(wind_sev[0].severity, RiskLevel.SEVERE)

    # -----------------------------------------------------------------
    # Test 5: Extreme heat conditions
    # -----------------------------------------------------------------
    def test_extreme_heat_conditions(self):
        # 37°C Moderate
        data_mod = create_mock_hourly(temperatures=[25.0] * 24 + [37.0] + [25.0] * 23)
        res_mod = self.engine.assess_risks(data_mod, day_offset=1)
        heat_mod = [r for r in res_mod.detected_risks if r.risk_type == RiskType.EXTREME_HEAT]
        self.assertEqual(len(heat_mod), 1)
        self.assertEqual(heat_mod[0].severity, RiskLevel.MODERATE)

        # 42°C High
        data_high = create_mock_hourly(temperatures=[25.0] * 24 + [42.0] + [25.0] * 23)
        res_high = self.engine.assess_risks(data_high, day_offset=1)
        heat_high = [r for r in res_high.detected_risks if r.risk_type == RiskType.EXTREME_HEAT]
        self.assertEqual(len(heat_high), 1)
        self.assertEqual(heat_high[0].severity, RiskLevel.HIGH)

        # 47°C Severe
        data_sev = create_mock_hourly(temperatures=[25.0] * 24 + [47.0] + [25.0] * 23)
        res_sev = self.engine.assess_risks(data_sev, day_offset=1)
        heat_sev = [r for r in res_sev.detected_risks if r.risk_type == RiskType.EXTREME_HEAT]
        self.assertEqual(len(heat_sev), 1)
        self.assertEqual(heat_sev[0].severity, RiskLevel.SEVERE)
        all_text = " ".join(heat_sev[0].recommendations).lower() + " " + heat_sev[0].reason.lower()
        self.assertIn("hydrat", all_text)

    # -----------------------------------------------------------------
    # Test 6: Extreme cold conditions
    # -----------------------------------------------------------------
    def test_extreme_cold_conditions(self):
        # -2°C Moderate freeze
        data_mod = create_mock_hourly(temperatures=[15.0] * 24 + [-2.0] + [10.0] * 23)
        res_mod = self.engine.assess_risks(data_mod, day_offset=1)
        cold_mod = [r for r in res_mod.detected_risks if r.risk_type == RiskType.EXTREME_COLD]
        self.assertEqual(len(cold_mod), 1)
        self.assertEqual(cold_mod[0].severity, RiskLevel.MODERATE)

        # -12°C High extreme cold
        data_high = create_mock_hourly(temperatures=[15.0] * 24 + [-12.0] + [5.0] * 23)
        res_high = self.engine.assess_risks(data_high, day_offset=1)
        cold_high = [r for r in res_high.detected_risks if r.risk_type == RiskType.EXTREME_COLD]
        self.assertEqual(len(cold_high), 1)
        self.assertEqual(cold_high[0].severity, RiskLevel.HIGH)

        # -25°C Severe hazard
        data_sev = create_mock_hourly(temperatures=[15.0] * 24 + [-25.0] + [0.0] * 23)
        res_sev = self.engine.assess_risks(data_sev, day_offset=1)
        cold_sev = [r for r in res_sev.detected_risks if r.risk_type == RiskType.EXTREME_COLD]
        self.assertEqual(len(cold_sev), 1)
        self.assertEqual(cold_sev[0].severity, RiskLevel.SEVERE)
        self.assertIn("frostbite", cold_sev[0].reason.lower())

    # -----------------------------------------------------------------
    # Test 7: Missing or incomplete weather data
    # -----------------------------------------------------------------
    def test_missing_and_incomplete_weather_data(self):
        # Empty dictionary
        res_empty = self.engine.assess_risks({}, day_offset=1)
        self.assertEqual(res_empty.overall_risk_level, RiskLevel.LOW)
        self.assertTrue(len(res_empty.data_limitations) > 0)
        # Verify no false alarms triggered
        self.assertEqual(len(res_empty.detected_risks), 0)

        # Dictionary with None values in temperatures
        data_nulls = create_mock_hourly(temperatures=[None] * 48)
        res_nulls = self.engine.assess_risks(data_nulls, day_offset=1)
        self.assertTrue(any("temperature data unavailable" in s.lower() for s in res_nulls.data_limitations))
        self.assertEqual(len([r for r in res_nulls.detected_risks if r.risk_type in (RiskType.EXTREME_HEAT, RiskType.EXTREME_COLD)]), 0)

    # -----------------------------------------------------------------
    # Test 8: Multiple simultaneous weather risks
    # -----------------------------------------------------------------
    def test_multiple_simultaneous_risks(self):
        # Heavy rain (40mm) + Thunderstorm (WMO 95) + Gale Wind (65 km/h)
        data_multi = create_mock_hourly(
            precipitations=[0.0] * 24 + [3.5] * 12 + [0.0] * 12,
            weather_codes=[0] * 24 + [95] * 6 + [0] * 18,
            wind_speeds=[10.0] * 24 + [65.0] + [20.0] * 23,
        )
        res_multi = self.engine.assess_risks(data_multi, day_offset=1)
        self.assertEqual(res_multi.overall_risk_level, RiskLevel.SEVERE)
        risk_types = [r.risk_type for r in res_multi.detected_risks]
        self.assertIn(RiskType.HEAVY_RAINFALL, risk_types)
        self.assertIn(RiskType.THUNDERSTORM, risk_types)
        self.assertIn(RiskType.STRONG_WIND, risk_types)
        self.assertTrue(len(res_multi.detected_risks) >= 3)
        # Recommendations must contain combined precautions without duplicates
        self.assertTrue(len(res_multi.safety_recommendations) >= 3)

    # -----------------------------------------------------------------
    # Test 9: Uncertainty communication
    # -----------------------------------------------------------------
    def test_uncertainty_communication(self):
        # High probability (85%) with modest accumulation (2.0 mm)
        data_prob = create_mock_hourly(
            precipitation_probabilities=[0.0] * 24 + [85.0] * 10 + [10.0] * 14,
            precipitations=[0.0] * 24 + [0.2] * 10 + [0.0] * 14,
        )
        res_prob = self.engine.assess_risks(data_prob, day_offset=1)
        # Check uncertainty notes distinguish probability vs amount
        notes_str = " ".join(res_prob.uncertainty_notes)
        self.assertIn("probability", notes_str.lower())
        self.assertIn("volume", notes_str.lower())
        self.assertIn("probabilistic", notes_str.lower())

    # -----------------------------------------------------------------
    # Test 10: Official alerts vs. AI-generated assessments distinction
    # -----------------------------------------------------------------
    def test_official_alerts_vs_ai_assessments(self):
        data = create_mock_hourly()
        res = self.engine.assess_risks(data, day_offset=1)
        # Must clearly identify as NOT an official alert
        self.assertFalse(res.is_official_alert)
        self.assertFalse(res.official_alerts_available)
        self.assertIsNone(res.official_alert_source)
        self.assertIn("NOT an official government weather alert", res.assessment_source)


if __name__ == "__main__":
    unittest.main()
