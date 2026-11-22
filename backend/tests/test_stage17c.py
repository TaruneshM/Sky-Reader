import asyncio
import json

import httpx
import pytest

from backend.evaluation.stage17c.runner import Outbound, PROVIDERS, endpoint, evaluate

MODELS = {"groq": "openai/gpt-oss-120b", "gemini": "gemini-fixture", "openrouter": "qwen/qwen3-coder:free"}


def test_mock_matrix_uses_production_gate_and_fault_injection(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED_PROVIDERS", ",".join(PROVIDERS))
    for name, model in MODELS.items():
        monkeypatch.setenv(f"{name.upper()}_MODEL", model)
        monkeypatch.setenv(f"{name.upper()}_API_KEY", "mock")
    outbound = Outbound(MODELS)
    rows = asyncio.run(evaluate(MODELS, outbound))
    assert all(row["pass_"] for row in rows), rows
    assert [[call["provider"] for call in row["attempts"]] for row in rows] == [
        ["groq"], ["groq", "gemini"], ["groq", "gemini", "openrouter"],
    ]
    assert [call["http_status"] for call in outbound.rows if call["source"] == "fault_injection"] == [429, 429, 503]
    assert not outbound.real_attempts
    independent = Outbound(MODELS)
    rows = asyncio.run(evaluate(MODELS, independent, inject=False))
    assert all(row["pass_"] and len(row["attempts"]) == 1 for row in rows)


def test_live_mode_guard_uses_fake_network_and_never_dispatches_injected_failures():
    class FakeNetwork:
        calls = []

        async def handle_async_request(self, request):
            self.calls.append(str(request.url))
            return httpx.Response(200, stream=httpx.ByteStream(b"{}"))

    async def run():
        network = FakeNetwork()
        outbound = Outbound(MODELS, live=True, network=network)
        url = endpoint("groq", MODELS["groq"])
        request = httpx.Request("POST", url, json={"model": MODELS["groq"], "max_tokens": 350})
        assert (await outbound.handle("groq", "gemini", request)).status_code == 429
        assert not network.calls
        response = await outbound.handle("groq", "groq", request)
        assert await response.aread() == b"{}"
        with pytest.raises(httpx.ProtocolError):
            await outbound.handle("groq", "groq", request)
        with pytest.raises(httpx.ProtocolError):
            await outbound.handle("groq", "groq", httpx.Request("POST", url + "?unexpected=1"))
        assert network.calls == [url]
        assert outbound.rows[1]["response_bytes"] == 2

    asyncio.run(run())


def test_openrouter_cost_guard_blocks_paid_or_fallback_payload():
    outbound = Outbound(MODELS)
    url = endpoint("openrouter", MODELS["openrouter"])
    payload = {"model": MODELS["openrouter"], "max_tokens": 350, "provider": {"allow_fallbacks": True}}
    with pytest.raises(httpx.ProtocolError):
        asyncio.run(outbound.handle("openrouter", "openrouter", httpx.Request(
            "POST", url, content=json.dumps(payload),
        )))
    assert not outbound.rows


def test_transport_cancellation_releases_guard():
    class Stall:
        async def handle_async_request(self, request):
            await asyncio.Event().wait()

    async def run():
        outbound = Outbound(MODELS, live=True, network=Stall())
        task = asyncio.create_task(outbound.handle("groq", "groq", httpx.Request(
            "POST", endpoint("groq", MODELS["groq"]),
            json={"model": MODELS["groq"], "max_tokens": 350},
        )))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not outbound.active
        assert outbound.real_attempts == {"groq"}

    asyncio.run(run())


@pytest.mark.parametrize(("provider", "error", "code", "summary"), [
    ("gemini", {"status": "NOT_FOUND", "message": "Model abc is not found. x-goog-api-key: dummy-key"},
     "NOT_FOUND", "model was unavailable"),
    ("openrouter", {"code": 404, "message": "No endpoints found: https://secret.invalid/?token=dummy-key"},
     404, "No matching provider endpoint"),
])
def test_rejection_records_only_safe_diagnostic(provider, error, code, summary):
    class Network:
        async def handle_async_request(self, request):
            return httpx.Response(404, stream=httpx.ByteStream(json.dumps({"error": error}).encode()),
                                  headers={"Authorization": "dummy-header"})

    async def run():
        outbound = Outbound(MODELS, live=True, network=Network())
        payload = {"generationConfig": {"maxOutputTokens": 350}} if provider == "gemini" else {
            "model": MODELS[provider], "max_tokens": 350,
            "provider": {"allow_fallbacks": False, "max_price": {"prompt": 0, "completion": 0}},
        }
        response = await outbound.handle(provider, provider, httpx.Request(
            "POST", endpoint(provider, MODELS[provider]), json=payload,
        ))
        diagnostic = outbound.rows[0]["error_diagnostic"]
        assert diagnostic["provider_code"] == code and summary in diagnostic["sanitized_message"]
        assert diagnostic["http_status"] == 404
        assert not diagnostic["retryable"] and not diagnostic["fallback_allowed"]
        saved = json.dumps(outbound.rows) + response.text
        assert all(secret not in saved for secret in ("dummy-key", "dummy-header", "secret.invalid", "Authorization"))

    asyncio.run(run())


def test_unknown_fields_and_oversized_errors_remain_redacted():
    from backend.evaluation.stage17c.diagnostics import error_diagnostic

    for error in (
        {"code": "unmarkedSecret", "status": [], "message": "opaquePrivateValue"},
        {"message": "opaquePrivateValue" * 200},
    ):
        result = error_diagnostic("gemini", MODELS["gemini"], 404, json.dumps({"error": error}).encode())
        assert result["provider_code"] is None
        assert "opaquePrivateValue" not in json.dumps(result)
        assert "unmarkedSecret" not in json.dumps(result)


def test_draft_diagnostics_explain_missing_unsupported_and_truncation():
    from backend.evaluation.stage17c.diagnostics import draft_diagnostic
    from backend.llm_gateway.models import Response, Usage

    draft = Response("groq", MODELS["groq"], {"content": "It is currently 43 °C."}, "length", Usage(210, 350))
    result = draft_diagnostic(draft, "Explain the temperature in Lisbon.",
                              {"current": {"temperature_2m": 21}}, {"name": "Lisbon"}, 350)
    assert result["missing_requirements"] == ("temperature",)
    assert result["unsupported_claims"][0]["variable"] == "temperature"
    assert result["temperature_units_present"] and not result["named_location_present"]
    assert result["truncated"] and result["reported_usage_reached_cap"]
    assert draft.message["content"] not in json.dumps(result)


@pytest.mark.parametrize(("draft", "reason"), [
    ("Currently in Lisbon the temperature is 21 °C. In Lisbon it will be sunny tomorrow.",
     "no_extractable_clause_claim"),
    ("Currently in Lisbon the temperature is 21 °C and the humidity in the other city is 64%.",
     "missing_clause_location"),
])
def test_fixture_isolates_final_gate_rejection_without_persisting_draft(draft, reason):
    from backend.evaluation.stage17c.diagnostics import draft_diagnostic
    from backend.llm_gateway.models import Response, Usage

    info = draft_diagnostic(
        Response("groq", MODELS["groq"], {"content": draft}, "stop", Usage(224, 296)),
        "Explain the current temperature in Lisbon, Portugal.",
        {"current": {"temperature_2m": 21, "relative_humidity_2m": 64, "weather_code": 0}},
        {"name": "Lisbon"}, 350,
    )
    assert info["draft_audited"] and not info["missing_requirements"]
    assert not info["draft_passed_model_evidence_gate"]
    assert "ev_obs_temp_current" in info["supporting_fixture_evidence_ids"]
    assert info["final_gate_rejection"]["clause_index"] == 2
    assert info["final_gate_rejection"]["reason"] == reason
    assert draft not in json.dumps(info)


def test_groq_only_fixture_uses_one_attempt_and_rejects_other_providers(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED_PROVIDERS", "groq")
    monkeypatch.setenv("GROQ_MODEL", MODELS["groq"])
    models = {"groq": MODELS["groq"]}
    outbound = Outbound(models)

    async def run():
        rows = await evaluate(models, outbound, inject=False, targets=("groq",))
        assert len(rows) == 1 and rows[0]["pass_"]
        assert len(outbound.rows) == 1
        with pytest.raises(httpx.ProtocolError):
            await outbound.handle("gemini", "groq", httpx.Request(
                "POST", endpoint("gemini", MODELS["gemini"]),
            ))

    asyncio.run(run())
