import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock
from groq import RateLimitError
import httpx

from backend.agent.router import (
    detect_weather_intent,
    extract_location_from_query_or_history,
    synthesize_deterministic_weather_buddy_response,
)
from backend.agent.tracer import LifecycleTracer
from backend.agent.agent import run_agent


class TestRateLimitAndRouting(unittest.TestCase):
    def test_detect_weather_intent(self):
        self.assertEqual(detect_weather_intent("Should I carry a coat?"), "coat_clothing")
        self.assertEqual(detect_weather_intent("Will it rain tomorrow?"), "rain_check")
        self.assertEqual(detect_weather_intent("Do I need an umbrella?"), "umbrella")
        self.assertEqual(detect_weather_intent("Can I go for a morning walk?"), "morning_walk")
        self.assertEqual(detect_weather_intent("What is the humidity and wind speed?"), "wind_humidity")
        self.assertEqual(detect_weather_intent("What about tomorrow?"), "tomorrow_forecast")
        # Complex queries should NOT match simple intents
        self.assertIsNone(detect_weather_intent("Compare Delhi and Dehradun."))
        self.assertIsNone(detect_weather_intent("Explain the weather forecast in detail."))

    def test_extract_location_from_query_and_history(self):
        # In query
        self.assertEqual(extract_location_from_query_or_history("How's the weather in Tanakpur?"), "Tanakpur")
        self.assertEqual(extract_location_from_query_or_history("Weather in Dehradun please"), "Dehradun")
        # In history
        history = [
            {"role": "user", "content": "How's the weather in Tanakpur?"},
            {"role": "assistant", "content": "It's 22°C and pleasant in Tanakpur."}
        ]
        self.assertEqual(extract_location_from_query_or_history("Should I carry a coat?", history), "Tanakpur")
        self.assertEqual(extract_location_from_query_or_history("What about tomorrow?", history), "Tanakpur")

    def test_lifecycle_tracer(self):
        tracer = LifecycleTracer()
        tracer.record_span("parsing", 5.2)
        tracer.record_llm_call(
            model="openai/gpt-oss-120b",
            latency_ms=210.5,
            prompt_tokens=150,
            completion_tokens=40,
            total_tokens=190,
        )
        tracer.record_tool_execution("get_current_weather", {"latitude": 29.0, "longitude": 80.0}, 45.0, cached=True)
        summary = tracer.get_summary()

        self.assertEqual(summary["llm_calls_count"], 1)
        self.assertEqual(summary["tool_calls_count"], 1)
        self.assertEqual(summary["total_tokens"], 190)
        self.assertIn("parsing", summary["spans"])

    def test_deterministic_synthesis(self):
        text = synthesize_deterministic_weather_buddy_response(
            intent="umbrella",
            location_name="Tanakpur",
            hourly_slice={"rain_probabilities": [0.0]}
        )
        self.assertIn("No umbrella needed in Tanakpur", text)

        text_rain = synthesize_deterministic_weather_buddy_response(
            intent="rain_check",
            location_name="Tanakpur",
            hourly_slice={"rain_probabilities": [0.0]}
        )
        self.assertIn("virtually no chance of rain", text_rain)

    def test_rate_limit_daily_quota_mock(self):
        """Mocked Groq client returning 429 daily limit must return friendly message."""
        mock_client = MagicMock()
        mock_response = httpx.Response(
            status_code=429,
            request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
            json={"error": {"message": "Rate limit reached: Request was rejected with 198,615 of 200,000 daily tokens already used."}}
        )
        rle = RateLimitError(
            message="Rate limit reached: Request was rejected with 198,615 of 200,000 daily tokens already used.",
            response=mock_response,
            body={"error": {"message": "daily tokens used"}}
        )
        mock_client.chat.completions.create = AsyncMock(side_effect=rle)

        # Run query with mock client
        res = asyncio.run(
            run_agent(
                "Compare Delhi and Dehradun.",
                client=mock_client
            )
        )
        self.assertEqual(
            res["response"],
            "Sky Reader has reached its AI usage limit for now 🌤️ Please try again later."
        )


if __name__ == "__main__":
    unittest.main()
