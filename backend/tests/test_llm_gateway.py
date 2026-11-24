import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from backend.agent.failures import FailureCategory, RequestFailure
from backend.agent.llm_budget import UnsafePayload
from backend.llm_gateway.gateway import Gateway, Request

TOOL = {"type": "function", "function": {"name": "weather", "parameters": {"type": "object"}}}
START = [{"role": "system", "content": "Use evidence."}, {"role": "user", "content": "Weather?"}]


def test_groq_normalizes_sdk_shape_and_unknown_usage():
    create = AsyncMock(return_value=SimpleNamespace(choices=[
        SimpleNamespace(message=SimpleNamespace(content="hello", tool_calls=None), finish_reason="stop"),
    ]))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    response = asyncio.run(Gateway(groq_client=client).complete(Request("groq-model", START, 80)))
    assert response.provider == "groq" and response.finish_reason == "stop"
    assert response.message["content"] == "hello"
    assert response.usage.total_tokens is None
    create.assert_awaited_once_with(model="groq-model", messages=START, max_tokens=80)


def test_gemini_preserves_system_tools_ids_signatures_and_usage(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED_PROVIDERS", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "mock")
    requests = []
    call = {"functionCall": {"id": "provider-id", "name": "weather", "args": {"city": "Osaka"}},
            "thoughtSignature": "opaque"}

    def fake(request):
        assert request.method == "POST"
        assert str(request.url) == "https://generativelanguage.googleapis.com/v1beta/models/gemini-fixture:generateContent"
        assert request.headers["x-goog-api-key"] == "mock"
        assert request.headers["content-type"] == "application/json"
        assert "authorization" not in request.headers
        payload = json.loads(request.content)
        requests.append(payload)
        parts = [call] if len(requests) == 1 else [{"text": "A forecast summary."}]
        return httpx.Response(200, json={
            "candidates": [{"content": {"parts": parts}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 20, "candidatesTokenCount": 5, "totalTokenCount": 25},
        })

    async def run():
        gateway = Gateway("gemini", transport=httpx.MockTransport(fake))
        first = await gateway.complete(Request("gemini-fixture", START, 80, [TOOL], "auto"))
        assert first.message["tool_calls"][0]["id"] == "provider-id"
        return await gateway.complete(Request("gemini-fixture", START + [first.message, {
            "role": "tool", "tool_call_id": "provider-id", "content": "Fixture result",
        }], 80, [TOOL], "auto"))

    response = asyncio.run(run())
    assert response.usage.total_tokens == 25
    assert requests[0]["systemInstruction"]["parts"][0]["text"] == "Use evidence."
    assert requests[0]["tools"][0]["functionDeclarations"][0]["parametersJsonSchema"]["type"] == "object"
    assert requests[1]["contents"][1]["parts"] == [call]
    assert requests[1]["contents"][2]["parts"][0]["functionResponse"]["id"] == "provider-id"


def test_gemini_requires_a_bare_model_id_and_never_dispatches_a_prefixed_name(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED_PROVIDERS", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "mock")

    def unexpected_request(_request):
        pytest.fail("A model resource name must be rejected before dispatch")

    gateway = Gateway("gemini", transport=httpx.MockTransport(unexpected_request))
    with pytest.raises(RequestFailure) as caught:
        asyncio.run(gateway.complete(Request("models/gemini-2.5-flash", START, 80)))
    assert caught.value.category is FailureCategory.LLM_UNAVAILABLE


@pytest.fixture
def router_gateway(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED_PROVIDERS", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "mock")
    return lambda handler: Gateway("openrouter", transport=httpx.MockTransport(handler))


def test_openrouter_free_only_and_normalizes_response(router_gateway):
    def mock(request):
        assert request.method == "POST"
        assert str(request.url) == "https://openrouter.ai/api/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer mock"
        assert request.headers["content-type"] == "application/json"
        assert "x-goog-api-key" not in request.headers
        payload = json.loads(request.content)
        assert payload["model"] == "qwen/qwen3-coder:free"
        assert payload["provider"] == {"allow_fallbacks": False, "require_parameters": True,
                                       "max_price": {"prompt": 0, "completion": 0}}
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": "Fixture"}}]})

    gateway = router_gateway(mock)
    response = asyncio.run(gateway.complete(Request("qwen/qwen3-coder:free", START, 80)))
    assert response.message["content"] == "Fixture" and response.usage.prompt_tokens is None
    with pytest.raises(RequestFailure) as caught:
        asyncio.run(gateway.complete(Request("qwen/qwen3-coder", START, 80)))
    assert caught.value.category is FailureCategory.LLM_UNAVAILABLE


@pytest.mark.parametrize(("status", "category"), [
    (429, FailureCategory.LLM_THROTTLED), (401, FailureCategory.LLM_AUTHENTICATION),
    (503, FailureCategory.LLM_SERVICE), (504, FailureCategory.LLM_TIMEOUT),
])
def test_provider_error_is_typed_and_has_no_retry(router_gateway, status, category):
    calls = []

    def mock(request):
        calls.append(request.url.host)
        return httpx.Response(status, text="synthetic-secret", headers={"Retry-After": "3"})

    with pytest.raises(RequestFailure) as caught:
        asyncio.run(router_gateway(mock).complete(Request("qwen/qwen3-coder:free", START, 80)))
    assert caught.value.category is category
    assert len(calls) == 1
    assert "synthetic-secret" not in str(caught.value)
    if status == 429:
        assert caught.value.retry_after == 3


def test_missing_configuration(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED_PROVIDERS", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RequestFailure) as caught:
        Gateway("gemini")
    assert caught.value.category is FailureCategory.LLM_UNAVAILABLE


@pytest.mark.parametrize("message", [
    MagicMock(), {"role": "user", "content": "a" * 200_000},
    {"role": "tool", "content": "orphan", "tool_call_id": "missing"},
    {"role": "user", "content": "question", "unrecognized": True},
])
def test_invalid_and_oversized_messages_fail_closed(message):
    with pytest.raises(UnsafePayload):
        Request("model", [message], 80).wire()


def test_cancellation_propagates_to_provider_without_fallback(router_gateway):
    async def run():
        entered = asyncio.Event()

        async def mock(request):
            entered.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(router_gateway(mock).complete(Request("qwen/qwen3-coder:free", START, 80)))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run())


def test_default_groq_without_credentials_is_unavailable(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_ENABLED_PROVIDERS", raising=False)
    with pytest.raises(RequestFailure) as caught:
        Gateway()
    assert caught.value.category is FailureCategory.LLM_UNAVAILABLE
