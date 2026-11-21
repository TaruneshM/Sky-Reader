import unittest
from backend.weather.service import (
    format_hourly_forecast,
    get_temporal_forecast_slice,
    _GEOCODE_CACHE,
    GEOCODE_TTL,
    clear_weather_cache,
)


class TestTemporalContext(unittest.TestCase):
    def setUp(self):
        clear_weather_cache()
        # Generate 48 hours of mock hourly data starting 2026-11-21T00:00 to 2026-11-22T23:00
        self.times = []
        self.temps = []
        self.rain_probs = []
        self.rain_amounts = []
        self.winds = []

        for d in ("2026-11-21", "2026-11-22"):
            for h in range(24):
                t_str = f"{d}T{h:02d}:00"
                self.times.append(t_str)
                self.temps.append(15.0 + h * 0.5 if d.endswith("21") else 14.0 + h * 0.4)
                self.rain_probs.append(0 if h < 18 else 10)
                self.rain_amounts.append(0.0)
                self.winds.append(5.0)

        self.mock_weather = {
            "current": {"time": "2026-11-21T16:15", "temperature_2m": 22.5},
            "hourly": {
                "time": self.times,
                "temperature_2m": self.temps,
                "precipitation_probability": self.rain_probs,
                "precipitation": self.rain_amounts,
                "wind_speed_10m": self.winds,
                "weather_code": [0] * len(self.times),
            }
        }

    def test_format_hourly_forecast_with_minutes(self):
        """Current time with minutes (16:15) should start at 16:00, not 00:00 midnight."""
        forecast = format_hourly_forecast(self.mock_weather, "2026-11-21T16:15", hours=8)
        self.assertEqual(len(forecast), 8)
        self.assertEqual(forecast[0]["time"], "2026-11-21T16:00")
        self.assertEqual(forecast[-1]["time"], "2026-11-21T23:00")

    def test_temporal_slice_tonight(self):
        """'tonight' slice should accurately select 18:00 to 23:00 of the current day."""
        slice_res = get_temporal_forecast_slice(self.mock_weather, period="tonight", current_time="2026-11-21T16:15")
        self.assertEqual(slice_res["period"], "tonight")
        self.assertEqual(len(slice_res["times"]), 6)
        self.assertEqual(slice_res["times"][0], "2026-11-21T18:00")
        self.assertEqual(slice_res["times"][-1], "2026-11-21T23:00")

    def test_temporal_slice_tomorrow(self):
        """'tomorrow' slice should select hours belonging to 2026-11-22."""
        slice_res = get_temporal_forecast_slice(self.mock_weather, period="tomorrow", current_time="2026-11-21T16:15")
        self.assertEqual(slice_res["period"], "tomorrow")
        self.assertEqual(len(slice_res["times"]), 24)
        self.assertTrue(all(t.startswith("2026-11-22") for t in slice_res["times"]))
        self.assertEqual(slice_res["times"][0], "2026-11-22T00:00")
        self.assertEqual(slice_res["times"][-1], "2026-11-22T23:00")

    def test_temporal_slice_current_today(self):
        """'current' slice should select 24 hours starting forward from current hour."""
        slice_res = get_temporal_forecast_slice(self.mock_weather, period="current", current_time="2026-11-21T16:15")
        self.assertEqual(slice_res["period"], "current")
        self.assertEqual(len(slice_res["times"]), 24)
        self.assertEqual(slice_res["times"][0], "2026-11-21T16:00")

    def test_cache_freshness_and_clear(self):
        """Weather cache stores timestamps and respects TTL."""
        import time
        _GEOCODE_CACHE["delhi"] = (time.time(), {"name": "Delhi", "latitude": 28.6, "longitude": 77.2})
        self.assertIn("delhi", _GEOCODE_CACHE)
        clear_weather_cache()
        self.assertEqual(len(_GEOCODE_CACHE), 0)


if __name__ == "__main__":
    unittest.main()
