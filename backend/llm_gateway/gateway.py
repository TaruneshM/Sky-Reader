"""Provider adapters with one dispatch and no automatic fallback."""
import asyncio
import json
import os
import re

import httpx
from groq import AsyncGroq

from .config import FREE_MODELS, KEYS, enabled, timeout_for
from .models import Request, Response, Usage, message_fields, valid_id

if __package__ == "backend.llm_gateway":
    from backend.agent.failures import FailureCategory, RequestFailure, classify_groq_failure
    from backend.agent.llm_budget import UnsafePayload, assistant_fields, encode_wire, MAX_TOOL_REPLY_BYTES
else:
    from agent.failures import FailureCategory, RequestFailure, classify_groq_failure
    from agent.llm_budget import UnsafePayload, assistant_fields, encode_wire, MAX_TOOL_REPLY_BYTES

USAGE_FIELDS = ("prompt_tokens", "completion_tokens", "total_tokens")


class GroqAdapter:
    name = "groq"

    def __init__(self, client):
        self.client = client

    async def complete(self, request):
        try:
            result = await self.client.chat.completions.create(**request.wire())
            choices = getattr(result, "choices", None)
            if type(choices) not in (list, tuple) or not choices:
                raise UnsafePayload("Missing choices.")
            choice = choices[0]
            message = message_fields(assistant_fields(getattr(choice, "message", None)))
            usage = getattr(result, "usage", None)
            finish = getattr(choice, "finish_reason", None)
            return Response(self.name, request.model, message, finish if valid_id(finish) else None,
                            Usage.read(lambda field: getattr(usage, field, None), USAGE_FIELDS))
        except (RequestFailure, UnsafePayload):
            raise
        except Exception as error:
            raise classify_groq_failure(error) from None


class HTTPAdapter:
    def __init__(self, key, timeout, transport=None):
        self.key = key
        self.timeout = timeout
        self.transport = transport

    async def post(self, url, payload, headers):
        try:
            async with asyncio.timeout(self.timeout), httpx.AsyncClient(
                timeout=self.timeout, follow_redirects=False, trust_env=False, transport=self.transport,
                headers={"Accept-Encoding": "identity"},
            ) as client, client.stream("POST", url, headers=headers, content=encode_wire(payload)[0]) as response:
                code = response.status_code
                if code == 429:
                    retry = response.headers.get("retry-after", "")
                    raise RequestFailure(FailureCategory.LLM_THROTTLED,
                                         retry_after=int(retry) if re.fullmatch(r"[0-9]{1,8}", retry) else None,
                                         provider_status=429, transient=True, dispatched=True)
                if code in (401, 403):
                    raise RequestFailure(FailureCategory.LLM_AUTHENTICATION, provider_status=code, dispatched=True)
                if code in (408, 504):
                    raise RequestFailure(FailureCategory.LLM_TIMEOUT, provider_status=code,
                                         transient=code == 504, dispatched=True)
                if not response.is_success:
                    raise RequestFailure(FailureCategory.LLM_SERVICE, provider_status=code,
                                         transient=code in {502, 503, 504}, dispatched=True)
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    raise UnsafePayload("Unsupported provider response encoding.")
                data = bytearray()
                # MockTransport can return an already buffered response.
                chunks = response.aiter_bytes(8192) if response.is_stream_consumed else response.aiter_raw(8192)
                async for chunk in chunks:
                    if len(data) + len(chunk) > 192 * 1024:
                        raise UnsafePayload("Provider response is too large.")
                    data.extend(chunk)
                result = json.loads(data)
                encode_wire(result)
                return result
        except (TimeoutError, httpx.TimeoutException):
            raise RequestFailure(FailureCategory.LLM_TIMEOUT, transient=True) from None
        except httpx.ConnectError:
            raise RequestFailure(FailureCategory.LLM_SERVICE, transient=True) from None
        except (httpx.HTTPError, ValueError, RecursionError):
            raise RequestFailure(FailureCategory.LLM_SERVICE) from None


class OpenRouterAdapter(HTTPAdapter):
    name = "openrouter"

    async def complete(self, request):
        if request.model not in FREE_MODELS:
            raise RequestFailure(FailureCategory.LLM_UNAVAILABLE)
        payload = request.wire()
        payload["provider"] = {"allow_fallbacks": False, "require_parameters": True,
                               "max_price": {"prompt": 0, "completion": 0}}
        result = await self.post("https://openrouter.ai/api/v1/chat/completions", payload,
                                 {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"})
        choice = result["choices"][0]
        message = choice["message"]
        if type(message) is dict:
            # Common Chat Completions metadata may be present even on text-only answers.
            ignored = {"refusal", "reasoning", "reasoning_details", "annotations"}
            if message.get("refusal") or message.get("annotations") or (
                message.get("tool_calls") and (message.get("reasoning") or message.get("reasoning_details"))
            ):
                raise UnsafePayload("Unsupported OpenRouter assistant metadata.")
            message = {key: value for key, value in message.items() if key not in ignored}
        message_fields(message)
        encode_wire(message, MAX_TOOL_REPLY_BYTES)
        return Response(self.name, request.model, message, choice.get("finish_reason"),
                        Usage.read((result.get("usage") or {}).get, USAGE_FIELDS))


class GeminiAdapter(HTTPAdapter):
    name = "gemini"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = {}
        self.turn = 0

    async def complete(self, request):
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}", request.model):
            raise RequestFailure(FailureCategory.LLM_UNAVAILABLE)
        payload = self.payload(request)
        result = await self.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{request.model}:generateContent",
            payload, {"x-goog-api-key": self.key, "Content-Type": "application/json"},
        )
        candidate = result["candidates"][0]
        message = {"role": "assistant", "content": None}
        text, calls = [], []
        self.turn += 1
        for part in candidate["content"]["parts"]:
            if part.get("thought"):
                continue
            if "functionCall" in part:
                if part.keys() - {"functionCall", "thoughtSignature"}:
                    raise UnsafePayload("Unsupported Gemini tool metadata.")
                fn = part["functionCall"]
                identifier = fn.get("id") or f"gemini-{self.turn}-{len(calls)}"
                if identifier in self.calls or len(self.calls) >= 32:
                    raise UnsafePayload("Too many or duplicate Gemini tool identifiers.")
                if type(fn.get("args", {})) is not dict:
                    raise UnsafePayload("Gemini requires object arguments.")
                arguments = encode_wire(fn.get("args", {}))[0]
                call = {"id": identifier, "type": "function",
                        "function": {"name": fn["name"], "arguments": arguments}}
                calls.append(call)
                self.calls[identifier] = part
            elif "text" in part and part.keys() == {"text"}:
                text.append(part["text"])
            else:
                raise UnsafePayload("Unsupported Gemini content part.")
        if text and calls:
            raise UnsafePayload("Mixed Gemini text and tool turns are unsupported.")
        if calls:
            message["tool_calls"] = calls
        if text:
            message["content"] = "".join(text)
        message_fields(message)
        encode_wire(message, MAX_TOOL_REPLY_BYTES)
        metadata = result.get("usageMetadata") or {}
        usage = Usage.read(metadata.get, ("promptTokenCount", "candidatesTokenCount", "totalTokenCount"))
        thought_tokens = metadata.get("thoughtsTokenCount")
        if usage.completion_tokens is not None and type(thought_tokens) is int and thought_tokens >= 0:
            usage = Usage(usage.prompt_tokens, usage.completion_tokens + thought_tokens, usage.total_tokens)
        finish = candidate.get("finishReason")
        finish = "tool_calls" if calls else {"STOP": "stop", "MAX_TOKENS": "length",
                                            "SAFETY": "content_filter"}.get(finish, finish)
        return Response(self.name, request.model, message, finish, usage)

    def payload(self, request):
        normalized = request.wire()
        system, contents = [], []
        names = {}
        for message in normalized["messages"]:
            role = message["role"]
            if role == "system":
                system.append({"text": message["content"]})
                continue
            parts = []
            if role == "tool":
                identifier = message["tool_call_id"]
                saved = self.calls.get(identifier, {}).get("functionCall", {})
                function_response = {"name": names[identifier], "response": {"output": message["content"]}}
                if "id" in saved:
                    function_response["id"] = saved["id"]
                parts.append({"functionResponse": function_response})
            else:
                if message.get("content") is not None:
                    parts.append({"text": message["content"]})
                for call in message.get("tool_calls", []):
                    fn = call["function"]
                    names[call["id"]] = fn["name"]
                    saved = self.calls.get(call["id"])
                    arguments = json.loads(fn["arguments"])
                    if type(arguments) is not dict:
                        raise UnsafePayload("Gemini requires object arguments.")
                    if saved and (saved["functionCall"]["name"] != fn["name"]
                                  or saved["functionCall"].get("args", {}) != arguments):
                        raise UnsafePayload("Gemini tool history was modified.")
                    parts.append(saved or {"functionCall": {"name": fn["name"], "args": arguments}})
            mapped_role = "model" if role == "assistant" else "user"
            if role == "tool" and contents and "functionResponse" in contents[-1]["parts"][-1]:
                contents[-1]["parts"].extend(parts)
            else:
                contents.append({"role": mapped_role, "parts": parts})
        result = {"contents": contents, "generationConfig": {"maxOutputTokens": request.max_tokens}}
        if system:
            result["systemInstruction"] = {"parts": system}
        if request.tools:
            result["tools"] = [{"functionDeclarations": [
                {("parametersJsonSchema" if key == "parameters" else key): value
                 for key, value in tool["function"].items()} for tool in request.tools
            ]}]
        return result


class Gateway:
    def __init__(self, provider="groq", *, groq_client=None, transport=None):
        if provider == "groq" and groq_client is not None:
            self.adapter = GroqAdapter(groq_client)
            return
        adapter = {"gemini": GeminiAdapter, "openrouter": OpenRouterAdapter}.get(provider)
        key = os.getenv(KEYS.get(provider, ""), "").strip()
        if provider == "groq" and enabled(provider) and key:
            self.adapter = GroqAdapter(None)
            self.groq_key = key
            return
        if not enabled(provider) or not adapter or not key:
            raise RequestFailure(FailureCategory.LLM_UNAVAILABLE)
        try:
            self.adapter = adapter(key, timeout_for(provider), transport)
        except ValueError:
            raise RequestFailure(FailureCategory.LLM_UNAVAILABLE) from None

    async def complete(self, request: Request):
        try:
            if self.adapter.name == "groq" and self.adapter.client is None:
                timeout = {"timeout": timeout_for("groq")} if "GROQ_TIMEOUT_SECONDS" in os.environ else {}
                async with AsyncGroq(api_key=self.groq_key, max_retries=0, **timeout) as client:
                    return await GroqAdapter(client).complete(request)
            return await self.adapter.complete(request)
        except (UnsafePayload, KeyError, IndexError, TypeError, ValueError, RecursionError):
            category = FailureCategory.GROQ_SERVICE if self.adapter.name == "groq" else FailureCategory.LLM_SERVICE
            raise RequestFailure(category) from None
