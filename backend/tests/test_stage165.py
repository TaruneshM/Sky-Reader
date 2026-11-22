import asyncio
from types import SimpleNamespace

import pytest

from backend.agent.failures import FailureCategory, RequestFailure
from backend.agent.tracer import LifecycleTracer
from backend.evaluation.stage165.cases import CASES
from backend.evaluation.stage165.runner import BudgetDenied, GroqBudget, consume_approval, evaluate, summarize


def test_dispatch_budget_checks_global_and_case_limits():
    async def exercise():
        calls = 0

        async def create(**kwargs):
            nonlocal calls
            calls += 1
            return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=11))

        budget = GroqBudget(create, maximum=1)
        with pytest.raises(BudgetDenied):
            await budget.client(CASES[0]).chat.completions.create()
        guarded = budget.client(CASES[6]).chat.completions.create
        await guarded()
        with pytest.raises(BudgetDenied):
            await guarded()
        assert calls == 1
        assert budget.records["synthesis"] == [
            {"prompt_tokens": 11, "completion_tokens": None, "status": "completed"},
        ]

        per_case = GroqBudget(create)
        guarded = per_case.client(CASES[6]).chat.completions.create
        await guarded()
        await guarded()
        with pytest.raises(BudgetDenied):
            await guarded()

    asyncio.run(exercise())


def test_cancellation_charges_attempt_and_releases_concurrency_guard():
    async def exercise():
        started = asyncio.Event()

        async def create(**kwargs):
            started.set()
            await asyncio.Future()

        budget = GroqBudget(create)
        guarded = budget.client(CASES[6]).chat.completions.create
        task = asyncio.create_task(guarded())
        await started.wait()
        with pytest.raises(BudgetDenied):
            await guarded()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert budget.remaining == 1 and not budget.active
        assert budget.records["synthesis"][0]["status"] == "cancelled"

    asyncio.run(exercise())


def test_error_report_is_safe_and_missing_usage_remains_unknown():
    async def provider(**kwargs):
        raise RequestFailure(FailureCategory.GROQ_TIMEOUT)

    async def run_agent(message, *, client, **kwargs):
        await client.chat.completions.create()

    rows = asyncio.run(evaluate(run_agent, GroqBudget(provider), str, None, LifecycleTracer, [CASES[6]]))
    assert rows[0]["failure"] == "groq_timeout"
    totals = summarize(rows)
    assert totals["groq_attempts"] == 1
    assert totals["usage"]["prompt_tokens"] == {"known_total": None, "missing_calls": 1}
    assert totals["passed"] == 0


def test_approval_receipt_is_single_use(tmp_path):
    receipt = tmp_path / "approval.used"
    consume_approval(receipt)
    with pytest.raises(FileExistsError):
        consume_approval(receipt)


def test_outbound_allowlist_and_weather_attempt_cap():
    import httpx

    from backend.evaluation.stage165.runner import OutboundBudget

    budget = OutboundBudget()
    request = httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
    for _ in range(36):
        budget.reserve(request, "weather")
    with pytest.raises(BudgetDenied):
        budget.reserve(request, "weather")
    assert budget.attempts == {"weather": 36, "groq": 0}
    other = OutboundBudget()
    with pytest.raises(BudgetDenied):
        other.reserve(httpx.Request("POST", "https://example.invalid/openai/v1/chat/completions"), "groq")
    assert other.attempts["groq"] == 0


@pytest.mark.parametrize(("base_url", "path_override", "redirect", "expected_url"), [
    (None, None, False, "https://api.groq.com/openai/v1/chat/completions"),
    ("https://api.groq.com/openai/v1", None, False, None),
    ("https://example.invalid", None, False, None),
    (None, "/unexpected", False, None),
    (None, None, True, "https://api.groq.com/openai/v1/chat/completions"),
])
def test_installed_groq_sdk_request_respects_exact_allowlist(
    monkeypatch, base_url, path_override, redirect, expected_url,
):
    import httpx
    from groq import APIConnectionError, APIStatusError, AsyncGroq

    from backend.evaluation.stage165.runner import GROQ_ORIGIN, OutboundBudget, RestrictedTransport

    async def exercise():
        sent = []

        async def fake_network(transport, request):
            sent.append((request.method, str(request.url)))
            if redirect:
                return httpx.Response(307, headers={"Location": "https://example.invalid/redirect"})
            return httpx.Response(200, json={"choices": []})

        monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", fake_network)
        budget = OutboundBudget()
        transport = RestrictedTransport(budget, "groq")
        async with httpx.AsyncClient(transport=transport, follow_redirects=False, trust_env=False) as http:
            sdk = AsyncGroq(api_key="mock-key", base_url=base_url or GROQ_ORIGIN, http_client=http, max_retries=0)
            if path_override:
                original = sdk.chat.completions._post

                async def other_path(_path, **kwargs):
                    return await original(path_override, **kwargs)

                monkeypatch.setattr(sdk.chat.completions, "_post", other_path)
            kwargs = {"model": "mock-model", "messages": [{"role": "user", "content": "Mock request"}]}
            if expected_url is None:
                with pytest.raises(APIConnectionError):
                    await sdk.chat.completions.create(**kwargs)
                assert budget.stop == "outbound_request_blocked"
                assert budget.attempts["groq"] == 0
                assert sent == []
            elif redirect:
                with pytest.raises(APIStatusError) as caught:
                    await sdk.chat.completions.create(**kwargs)
                assert caught.value.status_code == 307
                assert sent == [("POST", expected_url)]
                assert budget.attempts["groq"] == 1
            else:
                await sdk.chat.completions.create(**kwargs)
                assert sent == [("POST", expected_url)]
                assert budget.attempts["groq"] == 1

    asyncio.run(exercise())
