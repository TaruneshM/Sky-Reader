from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.agent.llm_budget import (
    MAX_ARGUMENT_BYTES, MAX_TOOL_REPLY_BYTES, UnsafePayload, assistant_fields, encode_wire, wire_size,
)


def test_dynamic_mock_is_rejected_without_invoking_serializer():
    mock = MagicMock()
    with pytest.raises(UnsafePayload):
        wire_size({"messages": [mock]})
    assert mock.mock_calls == []


def test_oversized_tool_reply_is_rejected_before_encoding():
    with pytest.raises(UnsafePayload):
        encode_wire({"forecast": "x" * (MAX_TOOL_REPLY_BYTES + 1)}, MAX_TOOL_REPLY_BYTES)


def test_oversized_tool_arguments_are_rejected():
    call = SimpleNamespace(id="test", function=SimpleNamespace(
        name="get_hourly_forecast", arguments=" " * (MAX_ARGUMENT_BYTES + 1),
    ))
    with pytest.raises(UnsafePayload):
        assistant_fields(SimpleNamespace(content=None, tool_calls=[call]))


@pytest.mark.parametrize("message", [
    SimpleNamespace(content=object(), tool_calls=None),
    SimpleNamespace(content=None, tool_calls=[object()]),
    {"role": "assistant", "content": "Unexpected SDK shape"},
])
def test_malformed_message_is_rejected(message):
    with pytest.raises(UnsafePayload):
        assistant_fields(message)


def test_payload_nesting_and_cycles_are_rejected():
    cycle = []
    cycle.append(cycle)
    with pytest.raises(UnsafePayload):
        wire_size(cycle)


def test_budget_is_shared_by_correction_and_main_attempts():
    from backend.agent.llm_budget import LLMBudget, LLMLimits

    budget = LLMBudget(LLMLimits(attempts=2, corrections=1, input_tokens=500, output_tokens=100))
    assert budget.reserve("agent_turn_1", 30, 60) == (42, 60)
    budget.observe(42, 60, None)
    assert budget.reserve("hallucination_correction", 30, 60) == (42, 40)
    assert budget.reserve("agent_turn_2", 30, 60) is None
