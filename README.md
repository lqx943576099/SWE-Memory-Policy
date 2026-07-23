# SWE-Memory-Policy

Framework-agnostic policies for representing coding-agent Action/Observation
(OA) history as text or images. This repository contains only the reusable
history, rendering, and composition layer; it does not contain SWE-bench data,
OpenHands, provider credentials, agent runners, or experiment outputs.

## Included policies

- Deterministic grouping of OpenAI-compatible assistant/tool messages into OA
  units with strict `tool_call_id` validation.
- Compact, human-readable OA text that preserves source indentation, command
  output, tracebacks, Unicode, and message order.
- White-background, black-text PNG rendering with font coverage checks,
  deterministic pagination, and no cropping or ellipsis.
- `fixed_2x`: scale each source OA page to 0.5× in both dimensions and compose
  pages in chronological two-column order.
- `dynamic_recursive`: shrink the previous accumulated canvas to 0.5× and add
  the newest OA at the highest available resolution.
- `dynamic_reference`: rebuild the same recency weighting from original source
  pages for measuring recursive resampling degradation.

## Boundary with agent frameworks

An adapter outside this package captures a framework's actual chat-completions
request. It passes `messages` to `parse_chat_history`, stores the resulting OA
records, renders the selected representation, and constructs the model request.
This package does not call an LLM and does not execute agent tools.

Native-agent experiments may derive the same OA records for audit and human
inspection while continuing to send the original role-structured history to the
model. Derived native OA records must be marked as audit-only.

## Minimal example

```python
from pathlib import Path

from swe_memory_policy import (
    compose_fixed_2x,
    parse_chat_history,
    render_flat_history,
    render_oa_display,
    render_text_pages,
)

parsed = parse_chat_history(messages)
flat_history = render_flat_history(parsed.oa_units)

sources = []
for oa in parsed.oa_units:
    pages = render_text_pages(
        text=render_oa_display(oa),
        output_dir=Path("artifacts/source_images"),
        stem=f"OA{oa.oa_index:04d}",
    )
    sources.extend((oa.oa_index, page) for page in pages)

canvases, ledger = compose_fixed_2x(
    sources,
    Path("artifacts/request_canvases"),
    request_index=2,
)
```

## Development

```bash
uv sync --extra test
uv run pytest
uv run ruff check src tests
```

Generated images and session data are ignored by Git. Font files are supplied
by the runtime environment through `IMAGE_MEMORY_FONT_PATHS`; no third-party
font binaries are redistributed in this repository.
