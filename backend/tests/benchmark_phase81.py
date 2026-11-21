import asyncio
import json
import time
from backend.agent.agent import run_agent

queries = [
    ("How's the weather in Tanakpur?", "thread"),
    ("Should I carry a coat?", "thread"),
    ("What about tomorrow?", "thread"),
    ("Is it too hot to go outside?", "thread"),
    ("Will it rain?", "thread"),
    ("Can I go for a morning walk?", "thread"),
    ("Compare Delhi and Dehradun.", "isolated"),
    ("There's a severe storm coming. Is it safe to travel?", "isolated"),
    ("What's the humidity and wind speed in Tanakpur?", "isolated"),
    ("Explain the weather forecast for Tanakpur in detail.", "isolated"),
]

async def main():
    results = []
    thread_history = []

    print("=== Running Phase 8.1 Verification Benchmark ===")
    for idx, (query, mode) in enumerate(queries, 1):
        hist = list(thread_history) if mode == "thread" else []
        t0 = time.time()
        res = await run_agent(query, conversation_history=hist)
        elapsed = round(time.time() - t0, 2)
        resp_text = res.get("response", "")
        word_count = len(resp_text.split())
        token_usage = res.get("token_usage", {})
        val_rep = res.get("validation_report") or {}
        tot_claims = val_rep.get("total_claims", 0)
        supp_claims = val_rep.get("supported_claims", 0)
        risk = res.get("risk_assessment")

        risk_level = "None"
        if risk and isinstance(risk, dict):
            risk_level = risk.get("overall_risk_level") or risk.get("risk_level", "LOW")

        item = {
            "index": idx,
            "query": query,
            "mode": mode,
            "response": resp_text,
            "word_count": word_count,
            "total_latency_seconds": elapsed,
            "llm_calls_count": token_usage.get("llm_calls_count", token_usage.get("llm_calls", 1)),
            "tool_calls_count": len(res.get("tool_calls", [])),
            "tool_names": [t.get("tool") for t in res.get("tool_calls", [])],
            "prompt_tokens": token_usage.get("prompt_tokens", 0),
            "completion_tokens": token_usage.get("completion_tokens", 0),
            "total_tokens": token_usage.get("total_tokens", 0),
            "validation_status": f"Verified ({supp_claims}/{tot_claims} claims)" if tot_claims > 0 else "Direct / Safe Fallback",
            "risk_level": risk_level,
            "iterations": res.get("iterations", 1),
            "spans": token_usage.get("spans", {}),
            "trace_id": token_usage.get("trace_id", "none"),
        }
        results.append(item)
        print(f"[{idx}/10] {query} -> {elapsed}s | LLM calls: {item['llm_calls_count']} | Tokens: {item['total_tokens']} | Tools: {item['tool_names']}")
        print(f"       Response: {resp_text[:110]}...")

        if mode == "thread":
            thread_history.append({"role": "user", "content": query})
            thread_history.append({"role": "assistant", "content": resp_text})

        await asyncio.sleep(1)

    with open("/home/victus/.gemini/antigravity/brain/2737cad0-e367-41d0-a8c1-1150a2500d65/scratch/phase81_benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nBenchmark saved to phase81_benchmark_results.json")

if __name__ == "__main__":
    asyncio.run(main())
