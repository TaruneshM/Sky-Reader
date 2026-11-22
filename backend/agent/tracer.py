import time
import uuid
from typing import Any, Dict, List, Optional

from .tools import tools

_TOOL_NAMES = frozenset(tool["function"]["name"] for tool in tools)


class LifecycleTracer:
    """
    Request-scoped lifecycle tracer for Sky Reader.
    Instruments each phase of execution: parsing, LLM calls, tool executions,
    evidence generation, claim validation, hallucination correction, and risk assessment.
    """

    def __init__(self, trace_id: Optional[str] = None):
        self.trace_id = trace_id or f"tr_{uuid.uuid4().hex[:8]}"
        self.start_time = time.perf_counter()
        self.weather_http_attempts = 0
        self.weather_provider_latency_ms = 0.0
        self.spans: Dict[str, float] = {}
        self.initial_provider: str | None = None
        self.successful_provider: str | None = None
        self.fallback_events: list[dict] = []
        self.llm_calls: List[Dict[str, Any]] = []
        self.tool_executions: List[Dict[str, Any]] = []
        self.failure_category: str | None = None
        self.deterministic_fallback = False
        self.deterministic_selected = False
        self.suppressed_tools = 0
        self.budget_exhausted = False
        self.answer_complete: bool | None = None

    def record_span(self, name: str, duration_ms: float):
        """Records the duration in milliseconds for a named lifecycle phase."""
        self.spans[name] = round(duration_ms, 2)

    def record_llm_call(
        self,
        model: str,
        latency_ms: float,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        total_tokens: int | None,
        finish_reason: Optional[str] = None,
        call_purpose: str = "agent_reasoning",
        failure_category: str | None = None,
        prompt_bytes: int | None = None,
        schema_bytes: int | None = None,
        estimated_prompt_tokens: int | None = None,
        provider: str = "groq",
        provider_status: int | None = None,
        retry_after: int | None = None,
        transient: bool = False,
        dispatched: bool | None = None,
        replay_safe: bool = False,
    ):
        """Records detailed metrics for an individual Groq LLM API invocation."""
        self.llm_calls.append({
            "call_index": len(self.llm_calls) + 1,
            "purpose": call_purpose,
            "model": model,
            "provider": provider,
            "provider_status": provider_status,
            "retry_after": retry_after,
            "transient": transient,
            "dispatched": dispatched,
            "replay_safe": replay_safe,
            "latency_ms": round(latency_ms, 2),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "finish_reason": finish_reason,
            "failure_category": failure_category,
            "prompt_bytes": prompt_bytes,
            "schema_bytes": schema_bytes,
            "estimated_prompt_tokens": estimated_prompt_tokens,
        })

    def record_weather_http(self, duration_ms: float):
        self.weather_http_attempts += 1
        self.weather_provider_latency_ms += duration_ms

    def record_tool_execution(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        latency_ms: float,
        cached: bool = False,
        error: Optional[str] = None,
    ):
        """Records metrics for an executed weather service tool."""
        self.tool_executions.append({
            "tool": tool_name if tool_name in _TOOL_NAMES else "unknown_tool",
            "argument_count": len(arguments) if isinstance(arguments, dict) else 0,
            "latency_ms": round(latency_ms, 2),
            "cached": cached,
            "failed": error is not None,
        })

    def get_summary(self) -> Dict[str, Any]:
        """Calculates aggregate metrics across the request lifecycle."""
        total_elapsed_ms = round((time.perf_counter() - self.start_time) * 1000, 2)

        def token_total(key):
            values = [call[key] for call in self.llm_calls]
            return sum(values) if all(value is not None for value in values) else None

        usage_by_provider = {}
        for call in self.llm_calls:
            group = usage_by_provider.setdefault(call["provider"], [])
            group.append(call)
        provider_usage = {
            name: {
                "attempts": len(calls),
                **{key: {
                    "known_total": sum(call[key] for call in calls if call[key] is not None)
                    if any(call[key] is not None for call in calls) else None,
                    "unknown_attempts": sum(call[key] is None for call in calls),
                } for key in ("prompt_tokens", "completion_tokens")},
            }
            for name, calls in usage_by_provider.items()
        }

        total_llm_latency_ms = sum(c["latency_ms"] for c in self.llm_calls)
        total_tool_latency_ms = sum(t["latency_ms"] for t in self.tool_executions)

        return {
            "trace_id": self.trace_id,
            "total_latency_ms": total_elapsed_ms,
            "llm_latency_ms": round(total_llm_latency_ms, 2),
            "tool_latency_ms": round(total_tool_latency_ms, 2),
            "llm_calls_count": len(self.llm_calls),
            "llm_calls_attempted": len(self.llm_calls),
            "llm_calls_completed": sum(call["failure_category"] is None for call in self.llm_calls),
            "llm_calls_with_usage": sum(call["total_tokens"] is not None for call in self.llm_calls),
            "planner_latency_ms": self.spans.get("planner", 0),
            "weather_provider_latency_ms": round(self.weather_provider_latency_ms, 2),
            "weather_http_attempts": self.weather_http_attempts,
            "failure_category": self.failure_category,
            "deterministic_fallback": self.deterministic_fallback,
            "deterministic_selected": self.deterministic_selected,
            "suppressed_tool_requests": self.suppressed_tools,
            "llm_budget_exhausted": self.budget_exhausted,
            "answer_complete": self.answer_complete,
            "estimated_llm_calls_avoided": 1 if self.deterministic_selected and not self.llm_calls else 0,
            "tool_calls_count": len(self.tool_executions),
            "prompt_tokens": token_total("prompt_tokens"),
            "completion_tokens": token_total("completion_tokens"),
            "total_tokens": token_total("total_tokens"),
            "spans": self.spans,
            "initial_provider": self.initial_provider,
            "successful_provider": self.successful_provider,
            "attempted_providers": [call["provider"] for call in self.llm_calls],
            "fallback_events": self.fallback_events,
            "provider_usage": provider_usage,
            "llm_calls": self.llm_calls,
            "tool_executions": self.tool_executions,
        }
