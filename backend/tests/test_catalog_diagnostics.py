import asyncio
import json

import httpx
import pytest

from backend.llm_gateway import catalog_diagnostics as catalog


GEMINI = "gemini-2.5-flash"
OPENROUTER = "qwen/qwen3-coder:free"
GEMINI_FIXTURE_KEY = "gemini-fixture-redact"
OPENROUTER_FIXTURE_KEY = "openrouter-fixture-redact"


def inspect(transport, gemini=GEMINI):
    return asyncio.run(catalog.inspect_catalogs(
        gemini, GEMINI_FIXTURE_KEY, OPENROUTER, OPENROUTER_FIXTURE_KEY,
        transport=httpx.MockTransport(transport),
    ))


@pytest.mark.parametrize("gemini", [GEMINI, f"models/{GEMINI}"])
def test_only_two_sequential_catalog_gets_with_scoped_headers_and_bounded_output(gemini):
    calls = []

    async def mock(request):
        assert request.method == "GET" and not request.content
        calls.append(request)
        if len(calls) == 1:
            assert str(request.url) == f"{catalog.GEMINI_CATALOG}?pageSize=1000"
            assert request.headers["x-goog-api-key"] == GEMINI_FIXTURE_KEY
            assert "authorization" not in request.headers
            return httpx.Response(200, json={"models": [{
                "name": f"models/{GEMINI}",
                "supportedGenerationMethods": ["generateContent", "countTokens", GEMINI_FIXTURE_KEY],
                "description": "private response content",
            }]})
        assert str(request.url) == catalog.OPENROUTER_CATALOG
        assert request.headers["authorization"] == f"Bearer {OPENROUTER_FIXTURE_KEY}"
        assert "x-goog-api-key" not in request.headers
        return httpx.Response(200, json={"data": [
            {"id": OPENROUTER.removesuffix(":free"), "pricing": {"prompt": "1", "completion": "1"}},
            {
                "id": OPENROUTER,
                "pricing": {"prompt": "0", "completion": 0},
                "top_provider": {"context_length": 8192},
                "links": {"details": "/api/v1/models/qwen/qwen3-coder:free/endpoints"},
            },
        ]})

    result = inspect(mock, gemini)
    assert len(calls) == 2
    assert result == {
        "gemini": {"model_listed": True, "supported_generation_methods": ["countTokens", "generateContent"]},
        "openrouter": {
            "model_listed": True, "zero_prompt_and_completion_price": True, "serving_endpoints_listed": None,
        },
    }
    assert GEMINI_FIXTURE_KEY not in json.dumps(result)
    assert OPENROUTER_FIXTURE_KEY not in json.dumps(result)


@pytest.mark.parametrize("failure", ["redirect", "timeout", "http", "oversized", "invalid"])
def test_catalog_failure_does_not_redirect_retry_or_disclose_body(failure, monkeypatch):
    monkeypatch.setattr(catalog, "BODY_LIMIT", 128)
    urls = []

    def mock(request):
        urls.append(request.url.host)
        if request.url.host == "openrouter.ai":
            return httpx.Response(200, json={"data": []})
        if failure == "redirect":
            return httpx.Response(302, headers={"location": "https://invalid.example"})
        if failure == "timeout":
            raise httpx.ReadTimeout("private fixture error")
        if failure == "http":
            return httpx.Response(403, text="private fixture error")
        if failure == "oversized":
            return httpx.Response(200, text="x" * 129)
        return httpx.Response(200, text="private fixture error")

    assert inspect(mock) == {
        "gemini": {"model_listed": None, "supported_generation_methods": None},
        "openrouter": {
            "model_listed": False, "zero_prompt_and_completion_price": None, "serving_endpoints_listed": None,
        },
    }
    assert urls == ["generativelanguage.googleapis.com", "openrouter.ai"]


def test_partial_catalog_cannot_establish_absence():
    def mock(request):
        if request.url.host == "openrouter.ai":
            return httpx.Response(200, json={"data": [], "total_count": 1})
        return httpx.Response(200, json={"models": [], "nextPageToken": "never-follow"})

    assert all(result["model_listed"] is None for result in inspect(mock).values())


@pytest.mark.parametrize(("lexical_price", "endpoints", "expected"), [
    ("1e-500", [{}], (False, True)),
    ("0", [], (True, False)),
    ('"unavailable"', None, (None, None)),
])
def test_openrouter_prices_are_checked_exactly_and_endpoints_require_an_explicit_list(
    lexical_price, endpoints, expected,
):
    def mock(request):
        if request.url.host != "openrouter.ai":
            return httpx.Response(200, json={"models": []})
        return httpx.Response(200, text=(
            '{"data":[{"id":' + json.dumps(OPENROUTER)
            + ',"pricing":{"prompt":"0","completion":' + lexical_price
            + '},"endpoints":' + json.dumps(endpoints) + '}]}'
        ))

    checked = inspect(mock)["openrouter"]
    assert (checked["zero_prompt_and_completion_price"], checked["serving_endpoints_listed"]) == expected
