from swe_memory_policy.history import OAUnit, _content_text, _tool_calls
from swe_memory_policy.utils import compact_json


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
