from __future__ import annotations

import pytest

from swe_memory_policy.history import (
    HistoryProtocolError,
    parse_chat_history,
    render_flat_history,
)


def _messages() -> list[dict[str, object]]:
    return [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "task"},
        {
            "role": "assistant",
            "content": "inspect",
            "tool_calls": [
                {
                    "id": "call-1",
                    "type": "function",
                    "function": {
                        "name": "terminal",
                        "arguments": '{"command":"sed -n \'1,20p\' a.py"}',
                    },
                },
                {
                    "id": "call-2",
                    "type": "function",
                    "function": {"name": "terminal", "arguments": "{}"},
                },
            ],
        },
        {
            "role": "tool",
            "name": "terminal",
            "tool_call_id": "call-1",
            "content": "def f():\n    return '中文 ✓'\n",
        },
        {
            "role": "tool",
            "name": "terminal",
            "tool_call_id": "call-2",
            "content": "",
        },
    ]


def test_parse_multi_tool_oa_and_render_exact_content() -> None:
    parsed = parse_chat_history(_messages())
    assert len(parsed.static_messages) == 2
    assert len(parsed.oa_units) == 1
    assert len(parsed.oa_units[0].observations) == 2
    display = render_flat_history(parsed.oa_units)
    assert "OA 0001 | ACTION" in display
    assert "def f():\n    return '中文 ✓'" in display
    assert "call_id=call-2" in display


def test_framework_feedback_is_part_of_oa() -> None:
    messages = _messages()[:2] + [
        {"role": "assistant", "content": "bad call", "tool_calls": []},
        {"role": "user", "content": "Function call validation failed"},
    ]
    parsed = parse_chat_history(messages)
    assert parsed.oa_units[0].observations[0]["role"] == "user"
    assert "FRAMEWORK 01" in render_flat_history(parsed.oa_units)


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda data: data[-1].update(tool_call_id="unknown"), "undeclared"),
        (lambda data: data.pop(), "no observations"),
        (
            lambda data: data.append({"role": "developer", "content": "x"}),
            "unexpected",
        ),
    ],
)
def test_invalid_pairing_fails_closed(mutation, match: str) -> None:  # noqa: ANN001
    messages = _messages()
    mutation(messages)
    with pytest.raises(HistoryProtocolError, match=match):
        parse_chat_history(messages)
