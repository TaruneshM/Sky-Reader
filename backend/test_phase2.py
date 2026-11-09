import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.agent.agent import run_agent, WeatherAgent
from backend.agent.executor import execute_tool
from fastapi.testclient import TestClient
from backend.main import app


async def test_scenario_1_current_weather():
    print("\n" + "=" * 60)
    print("TEST 1: Current weather in Dehradun")
    print("=" * 60)
    result = await run_agent("What's the current weather in Dehradun?")
    print(f"Iterations: {result['iterations']}")
    print(f"Tool calls made ({len(result['tool_calls'])}):")
    tool_names = [tc["tool"] for tc in result["tool_calls"]]
    for tc in result["tool_calls"]:
        print(f"  - Tool: {tc['tool']}, Arguments: {tc['arguments']}")
    print(f"Response:\n{result['response']}\n")

    assert "geocode_location" in tool_names, "Expected geocode_location tool call"
    assert "get_current_weather" in tool_names, "Expected get_current_weather tool call"
    assert len(result["response"]) > 20, "Expected meaningful response"
    print(">>> TEST 1 PASSED: Successfully fetched and reported current weather for Dehradun.")
    return True


async def test_scenario_2_hourly_forecast():
    print("\n" + "=" * 60)
    print("TEST 2: Hourly forecast for Dehradun")
    print("=" * 60)
    result = await run_agent("Will it rain tomorrow in Dehradun? Give me the forecast details.")
    print(f"Iterations: {result['iterations']}")
    print(f"Tool calls made ({len(result['tool_calls'])}):")
    tool_names = [tc["tool"] for tc in result["tool_calls"]]
    for tc in result["tool_calls"]:
        print(f"  - Tool: {tc['tool']}, Arguments: {tc['arguments']}")
    print(f"Response:\n{result['response']}\n")

    assert "geocode_location" in tool_names, "Expected geocode_location tool call"
    assert "get_hourly_forecast" in tool_names or "analyze_weather" in tool_names, (
        "Expected get_hourly_forecast or analyze_weather tool call"
    )
    assert len(result["response"]) > 20, "Expected meaningful response"
    print(">>> TEST 2 PASSED: Successfully fetched and reported hourly forecast for Dehradun.")
    return True


async def test_scenario_3_current_and_forecast():
    print("\n" + "=" * 60)
    print("TEST 3: Current weather and forecast in one question")
    print("=" * 60)
    query = "What is the weather like right now in Dehradun, and how will it change over the next few hours?"
    result = await run_agent(query)
    print(f"Iterations: {result['iterations']}")
    print(f"Tool calls made ({len(result['tool_calls'])}):")
    tool_names = [tc["tool"] for tc in result["tool_calls"]]
    for tc in result["tool_calls"]:
        print(f"  - Tool: {tc['tool']}, Arguments: {tc['arguments']}")
    print(f"Response:\n{result['response']}\n")

    assert "geocode_location" in tool_names, "Expected geocode_location tool call"
    assert "get_current_weather" in tool_names or "get_hourly_forecast" in tool_names, (
        "Expected weather or forecast tool call"
    )
    assert len(result["response"]) > 20, "Expected meaningful response"
    print(">>> TEST 3 PASSED: Successfully handled combined current and forecast query.")
    return True


async def test_scenario_4_general_question():
    print("\n" + "=" * 60)
    print("TEST 4: General question that does not require weather tools")
    print("=" * 60)
    result = await run_agent("What is the capital of France?")
    print(f"Iterations: {result['iterations']}")
    print(f"Tool calls made: {result['tool_calls']}")
    print(f"Response:\n{result['response']}\n")

    assert len(result["tool_calls"]) == 0, f"Expected 0 tool calls, got {len(result['tool_calls'])}"
    assert "paris" in result["response"].lower(), "Expected Paris in response"
    print(">>> TEST 4 PASSED: Successfully answered general query without invoking weather tools.")
    return True


async def test_scenario_5_invalid_tool_call():
    print("\n" + "=" * 60)
    print("TEST 5: Invalid or unknown tool call")
    print("=" * 60)
    
    # 5a. Direct executor validation: unknown tool
    unknown_tool_caught = False
    try:
        await execute_tool("non_existent_tool_123", {"arg": "value"})
    except ValueError as ve:
        unknown_tool_caught = True
        print(f"  5a. Correctly caught unknown tool: {ve}")
    assert unknown_tool_caught, "Expected ValueError for unknown tool"

    # 5b. Direct executor validation: invalid arguments (not dict)
    invalid_arg_caught = False
    try:
        await execute_tool("geocode_location", "invalid_string_argument")
    except ValueError as ve:
        invalid_arg_caught = True
        print(f"  5b. Correctly caught invalid argument type: {ve}")
    assert invalid_arg_caught, "Expected ValueError for non-dict arguments"

    print(">>> TEST 5 PASSED: Tool executor safely rejects invalid tool names and arguments.")
    return True


async def test_scenario_6_ungeocodeable_location():
    print("\n" + "=" * 60)
    print("TEST 6: A location that cannot be geocoded")
    print("=" * 60)
    result = await run_agent("What is the current weather in Xqzzjkllmno987fakeplace?")
    print(f"Iterations: {result['iterations']}")
    print(f"Tool calls made ({len(result['tool_calls'])}):")
    for tc in result["tool_calls"]:
        print(f"  - Tool: {tc['tool']}, Arguments: {tc['arguments']}")
    print(f"Response:\n{result['response']}\n")

    tool_names = [tc["tool"] for tc in result["tool_calls"]]
    assert "geocode_location" in tool_names, "Expected geocode_location to be attempted"
    # Agent should gracefully tell user the location wasn't found without crashing
    assert len(result["response"]) > 10, "Expected a polite failure explanation"
    print(">>> TEST 6 PASSED: Gracefully handled ungeocodeable location without crashing.")
    return True


async def test_scenario_7_missing_or_invalid_api_key():
    print("\n" + "=" * 60)
    print("TEST 7: Missing or invalid Groq API key")
    print("=" * 60)

    # 7a. Missing API key (empty string)
    missing_key_caught = False
    try:
        await run_agent("Weather in Dehradun", api_key="")
    except ValueError as ve:
        missing_key_caught = True
        print(f"  7a. Correctly caught missing API key: {ve}")
    assert missing_key_caught, "Expected ValueError when API key is empty"

    # 7b. Invalid API key
    invalid_key_caught = False
    try:
        await run_agent("Weather in Dehradun", api_key="gsk_invalid_test_key_12345")
    except Exception as e:
        invalid_key_caught = True
        print(f"  7b. Correctly caught invalid API key ({type(e).__name__}): {e}")
    assert invalid_key_caught, "Expected exception when API key is invalid"

    print(">>> TEST 7 PASSED: Missing and invalid API keys are properly identified and rejected.")
    return True


def test_scenario_8_fastapi_endpoints():
    print("\n" + "=" * 60)
    print("TEST 8: FastAPI Integration Endpoints")
    print("=" * 60)
    client = TestClient(app)

    # 8a. Root and Health
    root_res = client.get("/")
    assert root_res.status_code == 200
    print("  8a. GET /: 200 OK ->", root_res.json())

    health_res = client.get("/health")
    assert health_res.status_code == 200
    print("  8b. GET /health: 200 OK ->", health_res.json())

    # 8c. Existing Phase 1 /weather endpoint
    weather_res = client.get("/weather?location=Dehradun")
    assert weather_res.status_code == 200
    w_json = weather_res.json()
    assert "location" in w_json and "current" in w_json and "forecast" in w_json
    print(f"  8c. GET /weather: 200 OK -> Location: {w_json['location']['name']}, Temp: {w_json['current']['temperature']}°C")

    # 8d. Agent chat endpoint - empty validation
    bad_chat_res = client.post("/api/agent/chat", json={"message": "   "})
    assert bad_chat_res.status_code == 400
    print("  8d. POST /api/agent/chat empty: 400 Bad Request correctly rejected")

    # 8e. Agent chat endpoint - general question
    chat_res = client.post("/api/agent/chat", json={"message": "What is the capital of Japan?"})
    assert chat_res.status_code == 200
    c_json = chat_res.json()
    assert "response" in c_json
    assert "tokyo" in c_json["response"].lower()
    print("  8e. POST /api/agent/chat general question: 200 OK ->", c_json["response"])

    # 8f. Agent chat endpoint - weather question
    weather_chat_res = client.post("/api/agent/chat", json={"message": "What is the weather in Dehradun?"})
    assert weather_chat_res.status_code == 200
    wc_json = weather_chat_res.json()
    assert "response" in wc_json
    assert len(wc_json["tool_calls"]) > 0
    print("  8f. POST /api/agent/chat weather question: 200 OK -> Tools called:", [t["tool"] for t in wc_json["tool_calls"]])

    print(">>> TEST 8 PASSED: FastAPI endpoints successfully handle health, Phase 1 weather, and Phase 2 agent chat.")
    return True


async def run_all_tests():
    results = {}
    print("\n" + "#" * 60)
    print("STARTING SKY READER PHASE 2 TEST SUITE")
    print("#" * 60)

    try:
        results["Scenario 1 (Current weather)"] = await test_scenario_1_current_weather()
    except Exception as e:
        print(f"TEST 1 FAILED: {e}")
        results["Scenario 1 (Current weather)"] = False

    try:
        results["Scenario 2 (Hourly forecast)"] = await test_scenario_2_hourly_forecast()
    except Exception as e:
        print(f"TEST 2 FAILED: {e}")
        results["Scenario 2 (Hourly forecast)"] = False

    try:
        await asyncio.sleep(2)
        results["Scenario 3 (Combined query)"] = await test_scenario_3_current_and_forecast()
    except Exception as e:
        print(f"TEST 3 FAILED: {e}")
        results["Scenario 3 (Combined query)"] = False

    try:
        results["Scenario 4 (General question)"] = await test_scenario_4_general_question()
    except Exception as e:
        print(f"TEST 4 FAILED: {e}")
        results["Scenario 4 (General question)"] = False

    try:
        results["Scenario 5 (Invalid tool call)"] = await test_scenario_5_invalid_tool_call()
    except Exception as e:
        print(f"TEST 5 FAILED: {e}")
        results["Scenario 5 (Invalid tool call)"] = False

    try:
        results["Scenario 6 (Ungeocodeable location)"] = await test_scenario_6_ungeocodeable_location()
    except Exception as e:
        print(f"TEST 6 FAILED: {e}")
        results["Scenario 6 (Ungeocodeable location)"] = False

    try:
        results["Scenario 7 (Missing/invalid API key)"] = await test_scenario_7_missing_or_invalid_api_key()
    except Exception as e:
        print(f"TEST 7 FAILED: {e}")
        results["Scenario 7 (Missing/invalid API key)"] = False

    try:
        await asyncio.sleep(4)
        results["Scenario 8 (FastAPI Endpoints)"] = test_scenario_8_fastapi_endpoints()
    except Exception as e:
        import traceback
        traceback.print_exc()
        results["Scenario 8 (FastAPI Endpoints)"] = False

    print("\n" + "#" * 60)
    print("TEST SUITE SUMMARY:")
    print("#" * 60)
    all_passed = True
    for name, status in results.items():
        state = "PASSED" if status else "FAILED"
        print(f" - {name}: {state}")
        if not status:
            all_passed = False

    if all_passed:
        print("\nALL 8 TEST SUITES COMPLETED SUCCESSFULLY!")
    else:
        print("\nSOME TESTS FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all_tests())

