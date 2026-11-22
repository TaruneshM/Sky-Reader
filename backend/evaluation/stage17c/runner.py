"""Controlled provider validation, with no network dispatch in the default mode."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from time import perf_counter
from unittest.mock import AsyncMock, patch

import httpx
from groq import AsyncGroq

from backend.agent import agent
from backend.agent.llm_budget import LLMLimits
from backend.evaluation.stage165.runner import consume_approval, verified_cgroup
from backend.llm_gateway.config import FREE_MODELS, KEYS, configured, model_for
from backend.llm_gateway.gateway import Gateway
from backend.weather.location_models import ConfirmedLocation, Resolved, ResolutionProvenance

from .diagnostics import ERROR_BYTES, draft_diagnostic, error_diagnostic

PROVIDERS = ("groq", "gemini", "openrouter")
PROMPT = "Explain the current temperature in Lisbon, Portugal."
CASE_LIMITS = LLMLimits(attempts=3, tool_rounds=1, corrections=0, input_tokens=6000,
                       output_tokens=1050, deadline_seconds=20)
MAX_BODY = 192 * 1024


def endpoint(provider, model):
    return {
        "groq": "https://api.groq.com/openai/v1/chat/completions",
        "gemini": f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    }[provider]


class LimitedBody(httpx.AsyncByteStream):
    def __init__(self, stream, record):
        self.stream = stream
        self.record = record

    async def __aiter__(self):
        async for chunk in self.stream:
            self.record["response_bytes"] += len(chunk)
            if self.record["response_bytes"] > MAX_BODY:
                raise httpx.ProtocolError("Provider response exceeded the byte cap.")
            yield chunk

    async def aclose(self):
        await self.stream.aclose()


class Outbound:
    def __init__(self, models, live=False, network=None):
        if live and network is None:
            raise ValueError("Live transport required.")
        self.models = models
        self.live = live
        self.network = network
        self.real_attempts = set()
        self.active = False
        self.rows = []

    def transport(self, provider, target):
        return httpx.MockTransport(lambda request: self.handle(provider, target, request))

    async def handle(self, provider, target, request):
        if provider not in self.models or target not in self.models:
            raise httpx.ProtocolError("Provider is outside the approved matrix.")
        expected = endpoint(provider, self.models[provider])
        if request.method != "POST" or str(request.url) != expected or self.active:
            raise httpx.ProtocolError("Outbound endpoint or concurrency violation.")
        payload = json.loads(request.content)
        output_cap = (payload.get("generationConfig", {}).get("maxOutputTokens")
                      if provider == "gemini" else payload.get("max_tokens"))
        if (type(output_cap) is not int or not 0 < output_cap <= 350
                or (provider != "gemini" and payload.get("model") != self.models[provider])
                or payload.get("tools") or payload.get("stream")):
            raise httpx.ProtocolError("Unexpected model, tools or output budget.")
        if provider == "openrouter":
            if (payload.get("model") not in FREE_MODELS or "models" in payload
                    or payload.get("provider", {}).get("allow_fallbacks") is not False
                    or payload.get("provider", {}).get("max_price") != {"prompt": 0, "completion": 0}):
                raise httpx.ProtocolError("OpenRouter cost policy blocked the request.")
        simulated = provider != target
        record = {"case": target, "provider": provider, "source": "fault_injection" if simulated else
                  "live" if self.live else "mock", "http_status": None, "response_bytes": 0}
        self.rows.append(record)
        start = perf_counter()
        self.active = True
        try:
            if simulated:
                code = 429 if provider == "groq" else 503
                response = httpx.Response(code, json={"error": {"message": "Injected failure"}})
            elif self.live:
                if provider in self.real_attempts:
                    raise httpx.ProtocolError("Live provider cap exhausted.")
                self.real_attempts.add(provider)
                response = await self.network.handle_async_request(request)
                record["http_status"] = response.status_code
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    await response.aclose()
                    raise httpx.ProtocolError("Unexpected response encoding.")
                if response.is_error:
                    try:
                        body = bytearray()
                        async for chunk in response.aiter_raw(ERROR_BYTES):
                            body.extend(chunk)
                            if len(body) >= ERROR_BYTES:
                                break
                    finally:
                        await response.aclose()
                    record["response_bytes"] = len(body)
                    record["error_diagnostic"] = error_diagnostic(provider, self.models[provider],
                                                                  response.status_code, body)
                    # Preserve original HTTP status and retry metadata without forwarding arbitrary error text.
                    retry = response.headers.get("retry-after", "")
                    safe_headers = {"Retry-After": retry} if retry.isascii() and retry.isdigit() and len(retry) <= 8 else {}
                    safe_body = {"error": {"message": record["error_diagnostic"]["sanitized_message"]}}
                    return httpx.Response(response.status_code, headers=safe_headers, json=safe_body)
                response = httpx.Response(response.status_code, headers=response.headers,
                                          stream=LimitedBody(response.stream, record))
            elif provider == "gemini":
                response = httpx.Response(200, json={"candidates": [{"content": {"parts": [
                    {"text": "Currently in Lisbon, the temperature is 21 °C."},
                ]}}], "usageMetadata": {"promptTokenCount": 123, "candidatesTokenCount": 15}})
            else:
                response = httpx.Response(200, json={"choices": [{"index": 0, "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "Currently in Lisbon, the temperature is 21 °C."}}]})
            record["http_status"] = response.status_code
            if response.is_stream_consumed:
                record["response_bytes"] = len(response.content)
            return response
        finally:
            record["headers_latency_ms"] = round((perf_counter() - start) * 1000, 2)
            self.active = False


def preflight():
    models = {provider: model_for(provider) for provider in PROVIDERS}
    return {
        provider: {
            "credential_present": bool(os.getenv(KEYS[provider], "").strip()),
            "model": models[provider],
            "configured": configured(provider, models[provider]),
            "endpoint": endpoint(provider, models[provider]) if configured(provider, models[provider]) else None,
        } for provider in PROVIDERS
    }


async def evaluate(models, outbound, *, inject=True, targets=PROVIDERS):
    if outbound.live and not inject and targets != ("groq",):
        raise ValueError("Live run must use the approved combined matrix.")
    location = ConfirmedLocation(name="Lisbon", country="Portugal", latitude=38.72, longitude=-9.14,
                                 provenance=ResolutionProvenance(method="standalone"))
    resolution = Resolved(query="Lisbon, Portugal", location=location)
    rows = []
    for index, target in enumerate(targets):
        started = perf_counter()
        start_row = len(outbound.rows)
        transport = outbound.transport("groq", target)
        drafts = []
        observation = {"current": {"temperature_2m": 21, "weather_code": 0}}
        async with httpx.AsyncClient(transport=transport, timeout=8, trust_env=False, follow_redirects=False,
                                     headers={"Accept-Encoding": "identity"}) as http:
            client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY") if outbound.live else "offline-fixture",
                               base_url="https://api.groq.com", max_retries=0, timeout=8, http_client=http)

            class ObservedGateway:
                def __init__(self, name, **kwargs):
                    self.gateway = Gateway(name, transport=outbound.transport(name, target), **kwargs)

                async def complete(self, request):
                    response = await self.gateway.complete(request)
                    drafts.append(draft_diagnostic(response, PROMPT, observation, location.as_legacy_place(),
                                                   request.max_tokens))
                    return response

            with patch.object(agent, "Gateway", ObservedGateway), patch.object(
                agent, "get_groq_client", return_value=client,
            ), patch.object(agent, "resolve_location", AsyncMock(return_value=resolution)), patch.object(
                agent, "get_current_weather", AsyncMock(return_value=observation),
            ), patch.dict(os.environ, {"GEMINI_TIMEOUT_SECONDS": "8", "OPENROUTER_TIMEOUT_SECONDS": "8"}), patch.object(agent, "get_hourly_forecast", AsyncMock(side_effect=AssertionError("Unexpected forecast"))):
                row = {"provider": target, "model": models[target]}
                try:
                    result = await agent.run_agent(
                        PROMPT, provider=target if not inject or index == 0 else None, fallback=inject and index > 0,
                        provider_priority=PROVIDERS[:index + 1], llm_limits=CASE_LIMITS,
                    )
                    report = result.get("validation_report") or {}
                    trace = result["token_usage"]
                    checks = report.get("validation_results", [])
                    supported_temperature = any(item.get("status") == "SUPPORTED"
                        and item["claim"].get("variable") == "temperature"
                        and item["claim"].get("claimed_value") == 21
                        and item.get("supporting_evidence_ids") for item in checks)
                    row.update(pass_=bool(report.get("is_trustworthy") and supported_temperature
                                          and trace["successful_provider"] == target
                                          and trace["answer_complete"] and trace["weather_http_attempts"] == 0),
                               audited=bool(report.get("is_trustworthy")), complete=trace["answer_complete"])
                except agent.RequestFailure as error:
                    trace = error.metrics or {}
                    row.update(pass_=False, failure=error.category.value)
                row["attempts"] = [{key: call.get(key) for key in (
                    "provider", "latency_ms", "prompt_tokens", "completion_tokens", "total_tokens",
                    "failure_category", "provider_status",
                )} for call in trace.get("llm_calls", [])]
                row["draft_diagnostics"] = drafts
                row["fallback_events"] = trace.get("fallback_events", [])
                row["elapsed_ms"] = round((perf_counter() - started) * 1000, 2)
                row["http"] = outbound.rows[start_row:]
                rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--groq-only", action="store_true")
    parser.add_argument("--approval-receipt", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        cgroup = verified_cgroup()
        config = preflight()
        if not args.live:
            print(json.dumps(config, indent=2))
            return 0
        if not args.approval_receipt or not args.output or args.output.exists() or not args.output.parent.is_dir():
            raise ValueError("An unused receipt and output path are required.")
        targets = ("groq",) if args.groq_only else PROVIDERS
        if not all(config[name]["configured"] for name in targets):
            raise ValueError("Live configuration incomplete.")
        models = {name: config[name]["model"] for name in targets}
        if args.groq_only and models != {"groq": "openai/gpt-oss-120b"}:
            raise ValueError("Unapproved Groq model.")
        consume_approval(args.approval_receipt)

        async def run():
            async with httpx.AsyncHTTPTransport(retries=0, trust_env=False) as network, asyncio.timeout(65):
                return await evaluate(models, Outbound(models, True, network),
                                      inject=not args.groq_only, targets=targets)

        rows = asyncio.run(run())
        with args.output.open("x", encoding="utf-8") as output:
            json.dump({"rows": rows, "peak_bytes": int((cgroup / "memory.peak").read_text())}, output, indent=2)
        return 0 if all(row["pass_"] for row in rows) else 1
    except KeyboardInterrupt:
        return 130
    except Exception:
        print("Stage 1.7C stopped. Verify cgroup, model configuration, receipt and output path.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
