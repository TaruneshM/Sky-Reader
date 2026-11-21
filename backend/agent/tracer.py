import time
import uuid
from typing import Any, Dict, List, Optional


class LifecycleTracer:
    """
    Request-scoped lifecycle tracer for Sky Reader.
    Instruments each phase of execution: parsing, LLM calls, tool executions,
    evidence generation, claim validation, hallucination correction, and risk assessment.
    """

    def __init__(self, trace_id: Optional[str] = None):
        self.trace_id = trace_id or f"tr_{uuid.uuid4().hex[:8]}"
        self.start_time = time.time()
        self.spans: Dict[str, float] = {}
        self.llm_calls: List[Dict[str, Any]] = []
        self.tool_executions: List[Dict[str, Any]] = []
        self.milestones: List[Dict[str, Any]] = []

    def record_span(self, name: str, duration_ms: float):
        """Records the duration in milliseconds for a named lifecycle phase."""
        self.spans[name] = round(duration_ms, 2)

    def record_llm_call(
        self,
        model: str,
        latency_ms: float,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        finish_reason: Optional[str] = None,
        call_purpose: str = "agent_reasoning",
    ):
        """Records detailed metrics for an individual Groq LLM API invocation."""
        self.llm_calls.append({
            "call_index": len(self.llm_calls) + 1,
            "purpose": call_purpose,
            "model": model,
            "latency_ms": round(latency_ms, 2),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "finish_reason": finish_reason or "stop",
        })

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
            "tool": tool_name,
            "arguments": arguments,
            "latency_ms": round(latency_ms, 2),
            "cached": cached,
            "error": error,
        })

    def get_summary(self) -> Dict[str, Any]:
        """Calculates aggregate metrics across the request lifecycle."""
        total_elapsed_ms = round((time.time() - self.start_time) * 1000, 2)
        total_prompt_tokens = sum(c["prompt_tokens"] for c in self.llm_calls)
        total_completion_tokens = sum(c["completion_tokens"] for c in self.llm_calls)
        total_tokens = sum(c["total_tokens"] for c in self.llm_calls)
        total_llm_latency_ms = sum(c["latency_ms"] for c in self.llm_calls)
        total_tool_latency_ms = sum(t["latency_ms"] for t in self.tool_executions)

        return {
            "trace_id": self.trace_id,
            "total_latency_ms": total_elapsed_ms,
            "llm_latency_ms": round(total_llm_latency_ms, 2),
            "tool_latency_ms": round(total_tool_latency_ms, 2),
            "llm_calls_count": len(self.llm_calls),
            "tool_calls_count": len(self.tool_executions),
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "spans": self.spans,
            "llm_calls": self.llm_calls,
            "tool_executions": self.tool_executions,
        }
