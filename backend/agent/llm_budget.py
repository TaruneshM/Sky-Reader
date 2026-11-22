"""Request-local limits shared by synthesis, tool turns and correction."""
from dataclasses import dataclass, field
import json
from math import ceil


MAX_PROMPT_BYTES = 192 * 1024
MAX_TOOL_REPLY_BYTES = 24 * 1024
MAX_ARGUMENT_BYTES = 4 * 1024
MAX_TOOL_CALLS = 8


class UnsafePayload(ValueError):
    """Payload cannot safely be put on the model wire."""


def encode_wire(value, limit=MAX_PROMPT_BYTES):
    """Serialize only bounded JSON primitives, with no object hooks."""
    remaining = limit

    def check(item, depth=0):
        nonlocal remaining
        remaining -= 1
        if depth > 12 or remaining < 0:
            raise UnsafePayload("Payload exceeds structural limits.")
        kind = type(item)
        if kind is str:
            if len(item) > remaining:
                raise UnsafePayload("Payload exceeds size limit.")
            remaining -= len(item)
        elif kind is list:
            if len(item) > remaining:
                raise UnsafePayload("Payload exceeds size limit.")
            for child in item:
                check(child, depth + 1)
        elif kind is dict:
            if len(item) > remaining:
                raise UnsafePayload("Payload exceeds size limit.")
            for name, child in item.items():
                if type(name) is not str:
                    raise UnsafePayload("Invalid JSON key.")
                check(name, depth + 1)
                check(child, depth + 1)
        elif kind is int:
            if item.bit_length() > 64:
                raise UnsafePayload("Invalid integer.")
        elif kind is not float and kind is not bool and item is not None:
            raise UnsafePayload("Unexpected payload object.")

    check(value)
    try:
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        size = len(encoded.encode("utf-8"))
    except (ValueError, UnicodeError) as error:
        raise UnsafePayload("Invalid JSON payload.") from error
    if size > limit:
        raise UnsafePayload("Payload exceeds size limit.")
    return encoded, size


def wire_size(value):
    return encode_wire(value)[1]


def assistant_fields(message):
    """Copy only provider protocol fields rather than serializing provider objects."""
    from types import SimpleNamespace
    from groq.types.chat import ChatCompletionMessage
    from groq.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
    from groq.types.chat.chat_completion_message_tool_call import Function

    if type(message) not in (ChatCompletionMessage, SimpleNamespace):
        raise UnsafePayload("Malformed assistant message.")
    content = getattr(message, "content", None)
    calls = getattr(message, "tool_calls", None)
    if (content is not None and type(content) is not str
            or calls is not None and type(calls) not in (list, tuple)
            or calls and len(calls) > MAX_TOOL_CALLS):
        raise UnsafePayload("Malformed assistant message.")
    result = {"role": "assistant", "content": content}
    if calls:
        result["tool_calls"] = []
        for call in calls:
            if type(call) not in (ChatCompletionMessageToolCall, SimpleNamespace):
                raise UnsafePayload("Malformed tool call.")
            function = getattr(call, "function", None)
            identifier = getattr(call, "id", None)
            if type(function) not in (Function, SimpleNamespace) or type(identifier) is not str or len(identifier) > 128:
                raise UnsafePayload("Malformed tool call.")
            name = getattr(function, "name", None)
            arguments = getattr(function, "arguments", None)
            if type(name) is not str or not name or len(name) > 128 or type(arguments) not in (str, dict):
                raise UnsafePayload("Malformed tool call.")
            if type(arguments) is dict:
                arguments = encode_wire(arguments, MAX_ARGUMENT_BYTES)[0]
            else:
                encode_wire(arguments, MAX_ARGUMENT_BYTES)
            result["tool_calls"].append({"id": identifier, "type": "function", "function": {
                "name": name, "arguments": arguments,
            }})
    encode_wire(result, MAX_TOOL_REPLY_BYTES)
    return result


@dataclass(frozen=True)
class LLMLimits:
    attempts: int = 4
    tool_rounds: int = 3
    corrections: int = 1
    input_tokens: int = 16_000
    output_tokens: int = 3_600

    def __post_init__(self):
        if min(self.attempts, self.tool_rounds, self.input_tokens, self.output_tokens) < 1 or self.corrections < 0:
            raise ValueError("Invalid LLM budget limits.")


@dataclass
class LLMBudget:
    limits: LLMLimits
    attempts: int = field(default=0, init=False)
    corrections: int = field(default=0, init=False)
    input_used: int = field(default=0, init=False)
    output_used: int = field(default=0, init=False)

    def reserve(self, purpose, payload_bytes, requested_output):
        estimated_input = ceil(payload_bytes / 3) + 32
        correction = purpose == "hallucination_correction"
        allowed_output = min(requested_output, self.limits.output_tokens - self.output_used)
        if (self.attempts >= self.limits.attempts
                or (correction and self.corrections >= self.limits.corrections)
                or self.input_used + estimated_input > self.limits.input_tokens or allowed_output < 1):
            return None
        self.attempts += 1
        self.corrections += correction
        self.input_used += estimated_input
        self.output_used += allowed_output
        return estimated_input, allowed_output

    def observe(self, reserved_input, reserved_output, usage):
        prompt = getattr(usage, "prompt_tokens", None)
        completion = getattr(usage, "completion_tokens", None)
        if type(prompt) is int and prompt >= 0:
            self.input_used += prompt - reserved_input
        if type(completion) is int and completion >= 0:
            self.output_used += completion - reserved_output
