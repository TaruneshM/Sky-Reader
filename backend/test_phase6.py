import asyncio
import os
import sys
from fastapi.testclient import TestClient

try:
    from backend.main import app
    from backend.agent.executor import execute_tool
    from backend.weather.risk_engine import WeatherRiskEngine
    from backend.weather.risk_models import RiskLevel, RiskType
    from backend.agent.agent import run_agent
except ImportError:
    from main import app
    from agent.executor import execute_tool
    from weather.risk_engine import WeatherRiskEngine
    from weather.risk_models import RiskLevel, RiskType
    from agent.agent import run_agent


def test_tool_executor_risk_tool():
    print("\n" + "=" * 60)
    print("PHASE 6 TEST 1: Tool Executor - assess_weather_risks")
    print("=" * 60)

    # Dehradun coordinates: 30.3165, 78.0322
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            execute_tool("assess_weather_risks", {"latitude": 30.3165, "longitude": 78.0322, "day_offset": 1})
        )
        assert isinstance(result, dict), "Result must be a dictionary"
        assert "overall_risk_level" in result, "Missing overall_risk_level"
        assert "detected_risks" in result, "Missing detected_risks"
        assert "is_official_alert" in result, "Missing is_official_alert"
        assert result["is_official_alert"] is False, "is_official_alert must be False"
        assert "NOT an official government" in result["assessment_source"], "Missing official disclaimer"
        assert "uncertainty_notes" in result, "Missing uncertainty_notes"
        print(f"  -> Risk Level: {result['overall_risk_level']}")
        print(f"  -> Summary: {result['overall_summary']}")
        print(f"  -> Disclaimer: {result['assessment_source']}")
        print(">>> TEST 1 PASSED: assess_weather_risks executes cleanly and returns valid risk models.")
        return True
    finally:
        loop.close()


def test_fastapi_risk_endpoint():
    print("\n" + "=" * 60)
    print("PHASE 6 TEST 2: FastAPI /api/weather/risks Endpoint")
    print("=" * 60)

    client = TestClient(app)

    # 1. Test valid location
    res = client.get("/api/weather/risks?location=Dehradun&day_offset=1")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert "location" in data, "Missing location metadata"
    assert "risk_assessment" in data, "Missing risk_assessment"
    ra = data["risk_assessment"]
    assert "overall_risk_level" in ra, "Missing overall_risk_level"
    assert ra["is_official_alert"] is False, "Must not be official alert"
    print(f"  -> Location: {data['location'].get('name')}")
    print(f"  -> Risk Level: {ra.get('overall_risk_level')}")
    print(f"  -> Recommendations Count: {len(ra.get('safety_recommendations', []))}")

    # 2. Test unknown location (404)
    res_404 = client.get("/api/weather/risks?location=InvalidUnknownCityXYZ999")
    assert res_404.status_code == 404, f"Expected 404, got {res_404.status_code}"
    print("  -> Unknown city handled with 404 status correctly.")

    print(">>> TEST 2 PASSED: /api/weather/risks endpoint operating properly.")
    return True


def test_agent_risk_tool_calling():
    print("\n" + "=" * 60)
    print("PHASE 6 TEST 3: Agentic Tool Calling with assess_weather_risks")
    print("=" * 60)

    query = "Are there any weather risks, storms, or severe safety hazards in Dehradun tomorrow?"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_agent(query))
        tools_called = [t["tool"] for t in result.get("tool_calls", [])]
        print(f"Query: {query}")
        print(f"Tools called ({len(tools_called)}): {tools_called}")
        print(f"Response:\n{result['response'][:400]}...")
        if result.get("risk_assessment"):
            print(f"Risk Assessment captured: {result['risk_assessment']['overall_risk_level']}")

        # Ensure agent used tools to evaluate the hazard
        assert any(t in tools_called for t in ("assess_weather_risks", "analyze_weather", "get_weather_recommendations")), (
            f"Expected risk or analysis tool, got {tools_called}"
        )
        print(">>> TEST 3 PASSED: Agent successfully routed query to meteorological evaluation.")
        return True
    finally:
        loop.close()


def run_all_phase6_tests():
    print("#" * 60)
    print("STARTING SKY READER PHASE 6 INTEGRATION TEST SUITE")
    print("#" * 60)

    results = {}
    try:
        results["Tool Executor Risk Tool"] = test_tool_executor_risk_tool()
    except Exception as e:
        print(f"TEST 1 FAILED: {e}")
        results["Tool Executor Risk Tool"] = False

    try:
        results["FastAPI Risk Endpoint"] = test_fastapi_risk_endpoint()
    except Exception as e:
        print(f"TEST 2 FAILED: {e}")
        results["FastAPI Risk Endpoint"] = False

    try:
        results["Agent Risk Tool Calling"] = test_agent_risk_tool_calling()
    except Exception as e:
        print(f"TEST 3 FAILED: {e}")
        results["Agent Risk Tool Calling"] = False

    print("\n" + "#" * 60)
    print("PHASE 6 TEST SUITE SUMMARY:")
    print("#" * 60)
    all_passed = True
    for name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f" - {name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\nALL PHASE 6 INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
        return 0
    else:
        print("\nSOME PHASE 6 TESTS FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_phase6_tests())
