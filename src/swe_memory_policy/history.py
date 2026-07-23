from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from swe_memory_policy.utils import compact_json

ALLOWED_ROLES = {"system", "developer", "user", "assistant", "tool"}


class HistoryProtocolError(ValueError):
    """Raised when an OpenAI history cannot be grouped without guessing."""


@dataclass(frozen=True)
class OAUnit:
    oa_index: int
    assistant: dict[str, Any]
    observations: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "oa_index": self.oa_index,
            "assistant": self.assistant,
            "observations": list(self.observations),
        }


@dataclass(frozen=True)
class ParsedHistory:
    static_messages: tuple[dict[str, Any], ...]
    oa_units: tuple[OAUnit, ...]


def _tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    calls = message.get("tool_calls") or []
    if not isinstance(calls, list):
        raise HistoryProtocolError("assistant.tool_calls must be a list")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for call in calls:
        if not isinstance(call, dict):
            raise HistoryProtocolError("tool call must be an object")
        call_id = call.get("id")
        if not isinstance(call_id, str) or not call_id:
            raise HistoryProtocolError("tool call id is missing")
        if call_id in seen:
            raise HistoryProtocolError(f"duplicate tool call id: {call_id}")
        seen.add(call_id)
        result.append(call)
    return result


def parse_chat_history(messages: list[dict[str, Any]]) -> ParsedHistory:
    if not isinstance(messages, list) or not messages:
        raise HistoryProtocolError("messages must be a non-empty list")
    for message in messages:
        if not isinstance(message, dict):
            raise HistoryProtocolError("each message must be an object")
        role = message.get("role")
        if role not in ALLOWED_ROLES:
            raise HistoryProtocolError(f"unsupported message role: {role!r}")

    first_assistant = next(
        (
            index
            for index, message in enumerate(messages)
            if message["role"] == "assistant"
        ),
        len(messages),
    )
    static = messages[:first_assistant]
    if any(message["role"] in {"assistant", "tool"} for message in static):
        raise HistoryProtocolError("static prefix contains historical messages")

    units: list[OAUnit] = []
    cursor = first_assistant
    while cursor < len(messages):
        assistant = messages[cursor]
        if assistant["role"] != "assistant":
            raise HistoryProtocolError(
                f"expected assistant at history position {cursor}, "
                f"got {assistant['role']}"
            )
        declared_calls = _tool_calls(assistant)
        expected_ids = {call["id"] for call in declared_calls}
        cursor += 1
        observations: list[dict[str, Any]] = []
        matched_ids: set[str] = set()
        while cursor < len(messages) and messages[cursor]["role"] != "assistant":
            observation = messages[cursor]
            role = observation["role"]
            if role == "tool":
                call_id = observation.get("tool_call_id")
                if not isinstance(call_id, str) or not call_id:
                    raise HistoryProtocolError(
                        "tool observation is missing tool_call_id"
                    )
                if call_id not in expected_ids:
                    raise HistoryProtocolError(
                        f"observation references undeclared tool call: {call_id}"
                    )
                if call_id in matched_ids:
                    raise HistoryProtocolError(
                        f"duplicate observation for tool call: {call_id}"
                    )
                matched_ids.add(call_id)
            elif role != "user":
                raise HistoryProtocolError(
                    f"unexpected {role} message inside OA {len(units) + 1}"
                )
            observations.append(observation)
            cursor += 1
        missing = expected_ids - matched_ids
        if missing:
            raise HistoryProtocolError(
                "assistant tool calls have no observations: "
                + ", ".join(sorted(missing))
            )
        if not declared_calls and not observations:
            raise HistoryProtocolError(
                "terminal assistant message cannot be historical input "
                "to a later request"
            )
        units.append(
            OAUnit(
                oa_index=len(units) + 1,
                assistant=assistant,
                observations=tuple(observations),
            )
        )
    return ParsedHistory(tuple(static), tuple(units))


def _content_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") in {"text", "input_text"}:
                text = item.get("text")
                if isinstance(text, str):
                    chunks.append(text)
            else:
                chunks.append(compact_json(item))
        return "\n".join(chunks)
    return compact_json(content)


def render_oa_display(unit: OAUnit) -> str:
    index = unit.oa_index
    lines = [f"OA {index:04d} | ACTION"]
    assistant_text = _content_text(unit.assistant.get("content"))
    if assistant_text:
        lines.append(assistant_text)
    for number, call in enumerate(_tool_calls(unit.assistant), start=1):
        function = call.get("function") or {}
        name = function.get("name") or call.get("name") or "unknown"
        arguments = function.get("arguments", call.get("arguments", {}))
        if isinstance(arguments, str):
            argument_text = arguments
        else:
            argument_text = compact_json(arguments)
        lines.append(f"TOOL {number:02d} | {name} | {argument_text}")
    lines.append(f"OA {index:04d} | OBSERVATION")
    for number, observation in enumerate(unit.observations, start=1):
        role = observation["role"]
        if role == "tool":
            name = observation.get("name") or "unknown"
            call_id = observation.get("tool_call_id") or "unknown"
            lines.append(f"RESULT {number:02d} | {name} | call_id={call_id}")
        else:
            lines.append(f"FRAMEWORK {number:02d}")
        text = _content_text(observation.get("content"))
        if text:
            lines.append(text)
    lines.append(f"OA {index:04d} | END")
    return "\n".join(lines) + "\n"


def render_flat_history(units: tuple[OAUnit, ...]) -> str:
    return "".join(render_oa_display(unit) for unit in units)


def render_init_oa_display(unit: OAUnit) -> str:
    """Render one native OpenHands action/result step for init baselines.

    This deliberately omits transport identifiers and audit metadata. The
    canonical :class:`OAUnit` remains the lossless audit representation; this
    function defines only the bytes visible to the model in ``text_init`` and
    ``image_init``.
    """

    index = unit.oa_index
    lines = [f"[Action {index}]"]
    assistant_text = _content_text(unit.assistant.get("content"))
    if assistant_text:
        lines.append(assistant_text)
    for number, call in enumerate(_tool_calls(unit.assistant), start=1):
        function = call.get("function") or {}
        name = function.get("name") or call.get("name") or "unknown"
        arguments = function.get("arguments", call.get("arguments", {}))
        argument_text = (
            arguments if isinstance(arguments, str) else compact_json(arguments)
        )
        lines.extend([f"[Tool {number}]", str(name)])
        if argument_text:
            lines.append(argument_text)

    lines.append(f"[Observation {index}]")
    for number, observation in enumerate(unit.observations, start=1):
        if len(unit.observations) > 1:
            kind = "Tool Result" if observation["role"] == "tool" else "Framework"
            lines.append(f"[{kind} {number}]")
        text = _content_text(observation.get("content"))
        if text:
            lines.append(text)
    return "\n".join(lines) + "\n"


def render_init_history(units: tuple[OAUnit, ...]) -> str:
    """Render the complete request history from scratch in chronological order."""

    return "\n".join(render_init_oa_display(unit).rstrip("\n") for unit in units) + (
        "\n" if units else ""
    )
