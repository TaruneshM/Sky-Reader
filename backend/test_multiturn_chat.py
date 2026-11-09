import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from backend.main import app


def test_multiturn_chat_flow():
    print("\n" + "=" * 60)
    print("TESTING MULTI-TURN CONTEXTUAL CONVERSATION FLOW")
    print("=" * 60)
    client = TestClient(app)

    history = []

    # -------------------------------------------------------------
    # TURN 1: Initial question establishing city and date
    # -------------------------------------------------------------
    q1 = "What's the weather in Dehradun tomorrow?"
    print(f"\n[Turn 1] User: {q1}")

    res1 = client.post("/api/agent/chat", json={
        "message": q1,
        "conversation_history": history,
    })
    assert res1.status_code == 200, f"Turn 1 failed: {res1.text}"
    data1 = res1.json()
    resp1 = data1["response"]
    tools1 = [tc["tool"] for tc in data1.get("tool_calls", [])]

    print(f"[Turn 1] Tools called: {tools1}")
    print(f"[Turn 1] AI Response snippet: {resp1[:180]}...")
    assert "geocode_location" in tools1
    assert any(t in tools1 for t in ["get_hourly_forecast", "analyze_weather", "get_weather_recommendations"])
    assert len(resp1) > 20

    # Append Turn 1 to history
    history.append({"role": "user", "content": q1})
    history.append({"role": "assistant", "content": resp1})

    # -------------------------------------------------------------
    # TURN 2: Follow-up question without repeating city or date
    # -------------------------------------------------------------
    q2 = "Should I carry an umbrella?"
    print(f"\n[Turn 2] User: {q2}")

    res2 = client.post("/api/agent/chat", json={
        "message": q2,
        "conversation_history": history,
    })
    assert res2.status_code == 200, f"Turn 2 failed: {res2.text}"
    data2 = res2.json()
    resp2 = data2["response"]
    tools2 = [tc["tool"] for tc in data2.get("tool_calls", [])]

    print(f"[Turn 2] Tools called: {tools2}")
    print(f"[Turn 2] AI Response snippet: {resp2[:180]}...")
    resp2_lower = resp2.lower()
    assert "umbrella" in resp2_lower, "Response must address umbrella"
    # Agent should have understood city context (Dehradun) from history
    assert "dehradun" in resp2_lower or any(tc.get("arguments", {}).get("location") == "Dehradun" for tc in data2.get("tool_calls", [])), (
        "Agent must preserve Dehradun context in follow-up"
    )

    # Append Turn 2 to history
    history.append({"role": "user", "content": q2})
    history.append({"role": "assistant", "content": resp2})

    # -------------------------------------------------------------
    # TURN 3: Second follow-up without repeating city or date
    # -------------------------------------------------------------
    q3 = "What about travelling?"
    print(f"\n[Turn 3] User: {q3}")

    res3 = client.post("/api/agent/chat", json={
        "message": q3,
        "conversation_history": history,
    })
    assert res3.status_code == 200, f"Turn 3 failed: {res3.text}"
    data3 = res3.json()
    resp3 = data3["response"]
    tools3 = [tc["tool"] for tc in data3.get("tool_calls", [])]

    print(f"[Turn 3] Tools called: {tools3}")
    print(f"[Turn 3] AI Response snippet: {resp3[:180]}...")
    resp3_lower = resp3.lower()
    assert any(w in resp3_lower for w in ["travel", "road", "transit", "journey", "trip", "condition", "suitable"]), (
        "Response must address travel suitability"
    )

    # -------------------------------------------------------------
    # TURN 4: New Chat simulation (history reset to empty)
    # -------------------------------------------------------------
    print("\n[Turn 4] Simulating 'New Chat' reset (empty history)...")
    clean_history = []
    q4 = "Should I carry an umbrella?"
    res4 = client.post("/api/agent/chat", json={
        "message": q4,
        "conversation_history": clean_history,
    })
    assert res4.status_code == 200
    data4 = res4.json()
    resp4 = data4["response"].lower()
    print(f"[Turn 4] AI Response snippet: {data4['response'][:180]}...")
    # Without history, agent cannot know which city the user is in and asks for location
    assert any(w in resp4 for w in ["which city", "what city", "location", "where", "specify", "tell me"]), (
        "Without conversation history, agent should ask for a location"
    )

    print("\n>>> ALL MULTI-TURN CONVERSATION TESTS PASSED SUCCESSFULLY! <<<\n")
    return True


if __name__ == "__main__":
    test_multiturn_chat_flow()
