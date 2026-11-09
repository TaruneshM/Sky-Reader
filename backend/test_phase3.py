import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.agent.agent import run_agent
from backend.agent.executor import execute_tool
from fastapi.testclient import TestClient
from backend.main import app


async def test_tool_executor_analysis():
    print("\n" + "=" * 60)
    print("PHASE 3 TEST 1: Tool Executor Analytical Tools")
    print("=" * 60)

    # Test analyze_weather tool directly
    lat, lon = 30.32443, 78.03392
    analysis = await execute_tool("analyze_weather", {
        "latitude": lat,
        "longitude": lon,
        "focus": "temperature",
        "day_offset": 1
    })
    assert analysis["status"] == "ok"
    assert "temperature" in analysis
    assert "trend" in analysis["temperature"]
    print("  -> analyze_weather execution successful:")
    print(f"     Trend: {analysis['temperature']['trend']}")
    print(f"     Min: {analysis['temperature']['min_temperature']}°C, Max: {analysis['temperature']['max_temperature']}°C")

    # Test get_weather_recommendations tool directly
    recommendations = await execute_tool("get_weather_recommendations", {
        "latitude": lat,
        "longitude": lon,
        "day_offset": 1
    })
    assert recommendations["status"] == "ok"
    assert "umbrella" in recommendations
    assert "outdoor_activities" in recommendations
    assert "travel" in recommendations
    print("  -> get_weather_recommendations execution successful:")
    print(f"     Umbrella recommended: {recommendations['umbrella']['recommended']}")
    print(f"     Outdoor best window: {recommendations['outdoor_activities']['best_period']}")
    print(f"     Travel status: {recommendations['travel']['suitability_status']}")

    print(">>> PHASE 3 TEST 1 PASSED: Analysis tools execute and return valid meteorological intelligence.")
    return True


async def test_agent_umbrella_decision():
    print("\n" + "=" * 60)
    print("PHASE 3 TEST 2: Agent Umbrella Decision Support")
    print("=" * 60)
    query = "Should I carry an umbrella tomorrow in Dehradun?"
    result = await run_agent(query)
    tools_called = [tc["tool"] for tc in result["tool_calls"]]
    print(f"Query: {query}")
    print(f"Tools called ({len(tools_called)}): {tools_called}")
    print(f"Response:\n{result['response']}\n")

    assert "geocode_location" in tools_called, "Expected geocode_location"
    assert any(t in tools_called for t in ["get_weather_recommendations", "analyze_weather", "get_hourly_forecast"]), (
        "Expected weather analysis/forecast tool to be called"
    )
    resp_lower = result["response"].lower()
    assert "umbrella" in resp_lower, "Response must address umbrella question"
    assert "rain" in resp_lower or "precipitation" in resp_lower, "Response must cite rain evidence"
    print(">>> PHASE 3 TEST 2 PASSED: Agent successfully reasoned about umbrella need based on forecast.")
    return True


async def test_agent_temperature_trend():
    print("\n" + "=" * 60)
    print("PHASE 3 TEST 3: Agent Temperature Trend Analysis")
    print("=" * 60)
    await asyncio.sleep(2)  # brief pause for TPM budget
    query = "Is the temperature in Dehradun increasing or decreasing over the next 24 hours?"
    result = await run_agent(query)
    tools_called = [tc["tool"] for tc in result["tool_calls"]]
    print(f"Query: {query}")
    print(f"Tools called ({len(tools_called)}): {tools_called}")
    print(f"Response:\n{result['response']}\n")

    assert "geocode_location" in tools_called, "Expected geocode_location"
    resp_lower = result["response"].lower()
    assert any(w in resp_lower for w in ["increase", "decreasing", "decrease", "steady", "warm", "drop", "rise", "stable"]), (
        "Response must explain temperature trend direction"
    )
    print(">>> PHASE 3 TEST 3 PASSED: Agent successfully identified temperature trend direction.")
    return True


async def test_agent_outdoor_activities():
    print("\n" + "=" * 60)
    print("PHASE 3 TEST 4: Best Time for Outdoor Activities")
    print("=" * 60)
    await asyncio.sleep(2)
    query = "What is the best time of day for outdoor activities tomorrow in Dehradun?"
    result = await run_agent(query)
    tools_called = [tc["tool"] for tc in result["tool_calls"]]
    print(f"Query: {query}")
    print(f"Tools called ({len(tools_called)}): {tools_called}")
    print(f"Response:\n{result['response']}\n")

    assert "geocode_location" in tools_called, "Expected geocode_location"
    resp_lower = result["response"].lower()
    assert any(p in resp_lower for p in ["morning", "afternoon", "evening", "best", "window", "hour"]), (
        "Response must suggest best time window"
    )
    print(">>> PHASE 3 TEST 4 PASSED: Agent provided evidence-based outdoor activity timing.")
    return True


def test_fastapi_analysis_endpoint():
    print("\n" + "=" * 60)
    print("PHASE 3 TEST 5: FastAPI Analysis Endpoint")
    print("=" * 60)
    client = TestClient(app)

    # Test /api/weather/analysis
    res = client.get("/api/weather/analysis?location=Dehradun&focus=all")
    assert res.status_code == 200
    data = res.json()
    assert "location" in data
    assert "analysis" in data
    assert data["analysis"]["status"] == "ok"
    assert "temperature" in data["analysis"]
    assert "precipitation" in data["analysis"]
    assert "decision_support" in data["analysis"]

    print(f"  -> Location: {data['location']['name']}")
    print(f"  -> Day analyzed: {data['analysis']['day_analyzed']}")
    print(f"  -> Umbrella advice: {data['analysis']['decision_support']['umbrella']['reason']}")

    # Test invalid location on analysis endpoint
    res_bad = client.get("/api/weather/analysis?location=XxxNonExistentPlace999")
    assert res_bad.status_code == 404
    print("  -> Correctly returned 404 for ungeocodeable location.")

    print(">>> PHASE 3 TEST 5 PASSED: FastAPI analysis endpoint functioning properly.")
    return True


async def run_all_phase3_tests():
    print("\n" + "#" * 60)
    print("STARTING SKY READER PHASE 3 INTEGRATION TEST SUITE")
    print("#" * 60)

    results = {}

    try:
        results["Tool Executor Analysis"] = await test_tool_executor_analysis()
    except Exception as e:
        print(f"TEST 1 FAILED: {e}")
        results["Tool Executor Analysis"] = False

    try:
        results["Agent Umbrella Decision"] = await test_agent_umbrella_decision()
    except Exception as e:
        print(f"TEST 2 FAILED: {e}")
        results["Agent Umbrella Decision"] = False

    try:
        results["Agent Temperature Trend"] = await test_agent_temperature_trend()
    except Exception as e:
        print(f"TEST 3 FAILED: {e}")
        results["Agent Temperature Trend"] = False

    try:
        results["Agent Outdoor Activity"] = await test_agent_outdoor_activities()
    except Exception as e:
        print(f"TEST 4 FAILED: {e}")
        results["Agent Outdoor Activity"] = False

    try:
        results["FastAPI Analysis Endpoint"] = test_fastapi_analysis_endpoint()
    except Exception as e:
        import traceback
        traceback.print_exc()
        results["FastAPI Analysis Endpoint"] = False

    print("\n" + "#" * 60)
    print("PHASE 3 TEST SUITE SUMMARY:")
    print("#" * 60)
    all_passed = True
    for name, status in results.items():
        state = "PASSED" if status else "FAILED"
        print(f" - {name}: {state}")
        if not status:
            all_passed = False

    if all_passed:
        print("\nALL PHASE 3 INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
    else:
        print("\nSOME PHASE 3 TESTS FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all_phase3_tests())
