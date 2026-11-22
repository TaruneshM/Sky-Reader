"""Bounded text and function-call protocol shared by the adapters."""
from dataclasses import dataclass
from typing import Literal

if __package__ == "backend.llm_gateway":
    from backend.agent.llm_budget import UnsafePayload, encode_wire, MAX_ARGUMENT_BYTES, MAX_TOOL_CALLS, MAX_TOOL_REPLY_BYTES
else:
    from agent.llm_budget import UnsafePayload, encode_wire, MAX_ARGUMENT_BYTES, MAX_TOOL_CALLS, MAX_TOOL_REPLY_BYTES


def message_fields(message):
    if type(message) is not dict or message.get("role") not in ("system", "user", "assistant", "tool"):
        raise UnsafePayload("Invalid message.")
    role = message["role"]
    allowed = {"role", "content"} | ({"tool_calls"} if role == "assistant" else
                                    {"tool_call_id", "name"} if role == "tool" else set())
    content = message.get("content")
    if message.keys() - allowed or (type(content) is not str and not (
        role == "assistant" and content is None and message.get("tool_calls")
    )):
        raise UnsafePayload("Invalid message fields.")
    if role == "tool":
        if not valid_id(message.get("tool_call_id")):
            raise UnsafePayload("Invalid tool result identifier.")
        encode_wire(content, MAX_TOOL_REPLY_BYTES)
    if "tool_calls" in message:
        calls = message["tool_calls"]
        if type(calls) is not list or len(calls) > MAX_TOOL_CALLS:
            raise UnsafePayload("Invalid tool calls.")
        for call in calls:
            if (type(call) is not dict or set(call) != {"type", "id", "function"}
                    or call["type"] != "function" or not valid_id(call["id"])):
                raise UnsafePayload("Invalid tool call.")
            fn = call["function"]
            if (type(fn) is not dict or set(fn) != {"name", "arguments"}
                    or not valid_id(fn["name"]) or type(fn["arguments"]) is not str):
                raise UnsafePayload("Invalid tool function.")
            encode_wire(fn["arguments"], MAX_ARGUMENT_BYTES)
    return message


def valid_id(value):
    return type(value) is str and 0 < len(value) <= 128


@dataclass(frozen=True)
class Request:
    model: str
    messages: list
    max_tokens: int
    tools: list | None = None
    tool_choice: Literal["auto"] | None = None

    def wire(self):
        if type(self.model) is not str or not self.model or len(self.model) > 128:
            raise UnsafePayload("Invalid model identifier.")
        if type(self.max_tokens) is not int or not 0 < self.max_tokens <= 100_000:
            raise UnsafePayload("Invalid output token limit.")
        payload = {"model": self.model, "messages": self.messages, "max_tokens": self.max_tokens}
        if self.tools is not None:
            payload["tools"] = self.tools
        if self.tool_choice is not None:
            if self.tool_choice != "auto" or not self.tools:
                raise UnsafePayload("Unsupported tool choice.")
            payload["tool_choice"] = self.tool_choice
        encode_wire(payload)
        if type(self.messages) is not list or not self.messages:
            raise UnsafePayload("Invalid message list.")
        pending = {}
        for message in self.messages:
            message_fields(message)
            if message["role"] == "tool":
                name = pending.pop(message["tool_call_id"], None)
                if name is None or message.get("name", name) != name:
                    raise UnsafePayload("Unmatched tool result.")
            else:
                if pending:
                    raise UnsafePayload("Missing tool results.")
                for call in message.get("tool_calls", []):
                    if call["id"] in pending:
                        raise UnsafePayload("Duplicate tool call identifier.")
                    pending[call["id"]] = call["function"]["name"]
        if pending:
            raise UnsafePayload("Missing tool results.")
        if self.tools is not None:
            if type(self.tools) is not list:
                raise UnsafePayload("Invalid tool definitions.")
            for tool in self.tools:
                if type(tool) is not dict or set(tool) != {"type", "function"} or tool["type"] != "function":
                    raise UnsafePayload("Unsupported tool definition.")
                fn = tool["function"]
                if (type(fn) is not dict or not valid_id(fn.get("name"))
                        or fn.keys() - {"name", "description", "parameters"}):
                    raise UnsafePayload("Invalid function definition.")
        return payload


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    @classmethod
    def read(cls, getter, fields):
        values = [getter(field) for field in fields]
        return cls(*(value if type(value) is int and value >= 0 else None for value in values))


@dataclass(frozen=True)
class Response:
    provider: str
    model: str
    message: dict
    finish_reason: str | None
    usage: Usage
