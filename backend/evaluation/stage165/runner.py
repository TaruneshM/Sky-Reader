"""Approval-gated runner. Execute serially inside the documented systemd scope."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from statistics import median
from time import perf_counter
from types import SimpleNamespace
from unittest.mock import patch

import httpx

from .cases import CASES
from .metrics import assess

GROQ_ORIGIN = "https://api.groq.com"


class BudgetDenied(RuntimeError):
    """Raised before dispatching an over-budget API attempt."""


class OutboundBudget:
    routes = {
        ("GET", "geocoding-api.open-meteo.com", "/v1/search"): "weather",
        ("GET", "api.open-meteo.com", "/v1/forecast"): "weather",
        ("POST", "api.groq.com", "/openai/v1/chat/completions"): "groq",
    }

    def __init__(self):
        self.attempts = {"weather": 0, "groq": 0}
        self.limits = {"weather": 36, "groq": 2}
        self.stop = None

    def reserve(self, request, provider):
        url = request.url
        if (self.stop or url.scheme != "https" or url.port not in (None, 443)
                or self.routes.get((request.method, url.host, url.path)) != provider):
            self.stop = self.stop or "outbound_request_blocked"
            raise BudgetDenied("Outbound dispatch blocked.")
        if self.attempts[provider] >= self.limits[provider]:
            self.stop = f"{provider}_http_budget_exhausted"
            raise BudgetDenied("HTTP budget exhausted.")
        self.attempts[provider] += 1


class RestrictedTransport(httpx.AsyncHTTPTransport):
    def __init__(self, budget, provider):
        super().__init__(retries=0)
        self.budget = budget
        self.provider = provider

    async def handle_async_request(self, request):
        self.budget.reserve(request, self.provider)
        response = await super().handle_async_request(request)
        if response.status_code in {401, 403, 429}:
            self.budget.stop = f"{self.provider}_http_{response.status_code}"
        return response


class GroqBudget:
    def __init__(self, create, maximum=2):
        if not 0 <= maximum <= 2:
            raise ValueError("Invalid suite budget.")
        self.create = create
        self.remaining = maximum
        self.active = False
        self.records = {}

    def client(self, case):
        records = self.records.setdefault(case.name, [])

        async def guarded(**kwargs):
            if self.active or not self.remaining or len(records) >= min(2, case.max_groq):
                raise BudgetDenied("Groq dispatch blocked.")
            record = {"prompt_tokens": None, "completion_tokens": None, "status": "failed"}
            records.append(record)
            self.remaining -= 1
            self.active = True
            try:
                response = await self.create(**kwargs)
                usage = getattr(response, "usage", None)
                for field in ("prompt_tokens", "completion_tokens"):
                    value = getattr(usage, field, None)
                    record[field] = value if type(value) is int and value >= 0 else None
                record["status"] = "completed"
                return response
            except asyncio.CancelledError:
                record["status"] = "cancelled"
                raise
            finally:
                self.active = False

        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=guarded)))


def verified_cgroup(root=Path("/sys/fs/cgroup")):
    group = next(line[3:] for line in Path("/proc/self/cgroup").read_text().splitlines()
                 if line.startswith("0::"))
    directory = root / group.lstrip("/")
    expected = {"high": "536870912", "max": "805306368", "swap.max": "0"}
    if any((directory / f"memory.{name}").read_text().strip() != value for name, value in expected.items()):
        raise RuntimeError("Memory protection is missing or incorrect.")
    return directory


def consume_approval(receipt):
    # Keep the receipt even after cancellation or failure. A retry requires fresh approval.
    descriptor = os.open(receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)


def summarize(rows):
    calls = [call for row in rows for call in row["groq"]]
    return {
        "cases": len(rows), "passed": sum(row["checks"]["pass"] for row in rows),
        "groq_attempts": len(calls), "groq_completed": sum(call["status"] == "completed" for call in calls),
        "weather_http_attempts": sum(row["weather_http_attempts"] for row in rows),
        "median_case_ms": round(median(row["elapsed_ms"] for row in rows), 2) if rows else None,
        "usage": {
            field: {"known_total": sum(values) if values else None, "missing_calls": len(calls) - len(values)}
            for field in ("prompt_tokens", "completion_tokens")
            for values in [[call[field] for call in calls if call[field] is not None]]
        },
    }


async def evaluate(run_agent, budget, scope, limits, trace_factory, cases=CASES, outbound=None):
    from backend.agent.failures import RequestFailure

    if not 1 <= len(cases) <= 8 or len({case.name for case in cases}) != len(cases):
        raise ValueError("Invalid case matrix.")
    current_state = None
    rows = []
    for case in cases:
        if outbound and outbound.stop:
            break
        if case.follow_up and current_state is None:
            rows.append({"case": case.name, "checks": {"pass": False}, "failure": "prerequisite_failed",
                         "elapsed_ms": 0, "groq": [], "weather_http_attempts": 0})
            continue
        trace = trace_factory()
        state = current_state if case.follow_up else None
        case_scope = scope("current" if case.follow_up else case.name)
        started = perf_counter()
        failure = None
        try:
            result = await asyncio.wait_for(run_agent(
                case.message, request_scope=case_scope, trusted_state=state, tracer=trace,
                client=budget.client(case), llm_limits=limits,
            ), timeout=40)
            next_state = result.get("conversation_state")
            checks = assess(case, result, next_state)
            if case.name == "current" and checks["pass"]:
                current_state = next_state
        except RequestFailure as error:
            failure = error.category.value
            checks = {"pass": False}
        except TimeoutError:
            failure = "case_timeout"
            checks = {"pass": False}
        except Exception:
            failure = "unexpected_harness_or_agent_error"
            checks = {"pass": False}
        metrics = trace.get_summary()
        rows.append({
            "case": case.name, "checks": checks, "failure": failure or metrics.get("failure_category"),
            "elapsed_ms": round((perf_counter() - started) * 1000, 2),
            "weather_http_attempts": metrics["weather_http_attempts"], "groq": budget.records.get(case.name, []),
            "estimated_prompt_tokens": sum(call.get("estimated_prompt_tokens") or 0 for call in metrics["llm_calls"]),
        })
    return rows


async def live(args, cgroup):
    from backend.agent.agent import get_groq_client, run_agent
    from backend.agent.conversation_state import ConversationScope
    from backend.agent.llm_budget import LLMLimits
    from backend.agent.tracer import LifecycleTracer
    from backend.weather import service

    if not os.getenv("GROQ_API_KEY", "").strip():
        raise RuntimeError("Groq key unavailable.")
    if args.output.exists() or not args.output.parent.is_dir():
        raise RuntimeError("Choose an unused output path in an existing directory.")
    if len(CASES) != 8 or sorted(case.max_groq for case in CASES) != [0] * 7 + [2]:
        raise RuntimeError("Unexpected approved case matrix.")
    cases = CASES
    if args.retest:
        cases = tuple(case for case in CASES if case.name in {"synthesis", "unsupported"})
        if tuple((case.name, case.max_groq) for case in cases) != (("synthesis", 2), ("unsupported", 0)):
            raise RuntimeError("Unexpected approved retest matrix.")
    outbound = OutboundBudget()
    if outbound.limits != {"weather": 36, "groq": 2}:
        raise RuntimeError("Unexpected HTTP budget.")
    consume_approval(args.approval_receipt)
    service.clear_weather_cache()
    weather_fetch = service._fetch_with_retry

    async def weather_without_retry(url, params):
        return await weather_fetch(url, params, retries=1)

    class WeatherHTTP:
        def __getattr__(self, name):
            return getattr(httpx, name)

        def AsyncClient(self, **kwargs):
            return httpx.AsyncClient(
                **kwargs, transport=RestrictedTransport(outbound, "weather"), trust_env=False,
            )

    async with get_groq_client() as base, httpx.AsyncClient(
        transport=RestrictedTransport(outbound, "groq"), trust_env=False, follow_redirects=False,
    ) as transport_client:
        client = base.with_options(
            base_url=GROQ_ORIGIN, http_client=transport_client, timeout=15, max_retries=0,
        )
        with patch.object(service, "httpx", WeatherHTTP()), patch.object(
            service, "_fetch_with_retry", weather_without_retry if args.retest else weather_fetch,
        ):
            rows = await evaluate(
                run_agent, GroqBudget(client.chat.completions.create),
                lambda name: ConversationScope(owner_kind="guest", owner_id="stage165", thread_id=name),
                LLMLimits(attempts=2, tool_rounds=2, corrections=1), LifecycleTracer, cases=cases, outbound=outbound,
            )
    status = 0 if len(rows) == len(cases) and not outbound.stop and all(row["checks"]["pass"] for row in rows) else 1
    output = {"rows": rows, "summary": summarize(rows), "exit_status": status,
              "outbound_attempts": outbound.attempts, "stop_reason": outbound.stop,
              "cgroup_memory_peak_bytes": int((cgroup / "memory.peak").read_text())}
    with args.output.open("x", encoding="utf-8") as report:
        json.dump(output, report, indent=2)
        report.write("\n")
    return status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--retest", action="store_true")
    parser.add_argument("--approval-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        return asyncio.run(live(args, verified_cgroup()))
    except KeyboardInterrupt:
        return 130
    except Exception:
        print("Live validation stopped. Check limits, key availability, receipt and output path.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
