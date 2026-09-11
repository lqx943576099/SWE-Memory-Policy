from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image

from swe_memory_policy import (
    build_noframe_observation_image_block,
    render_noframe_observation_pages,
)


def test_noframe_block_preserves_observation_byte_for_byte() -> None:
    content = (
        "<returncode>0</returncode>\r\n"
        "<output>\n"
        "def value():\n    return 'unchanged'\n"
        "</output>"
    )
    block = build_noframe_observation_image_block(
        sequence_index=1,
        oa_index=6,
        tool_index=1,
        tool_call_id="call_exact",
        content=content,
    )
    assert block.raw_content == content
    assert block.manifest()["content_rewritten"] is False
    assert block.manifest()["newline_count"] == content.count("\n")
    assert block.manifest()["carriage_return_count"] == content.count("\r")
    assert "call_id=call_exact" in block.metadata


def test_noframe_renderer_is_dense_deterministic_and_one_x(tmp_path: Path) -> None:
    text = "\n".join(f"line {index}" for index in range(20))
    first = render_noframe_observation_pages(
        text, tmp_path / "first", "observation", metadata="OA=1 role=tool"
    )
    second = render_noframe_observation_pages(
        text, tmp_path / "second", "observation", metadata="OA=1 role=tool"
    )
    assert len(first) == len(second) == 1
    assert (
        hashlib.sha256(first[0].read_bytes()).digest()
        == hashlib.sha256(second[0].read_bytes()).digest()
    )
    with Image.open(first[0]) as image:
        assert image.width == 2048
        assert image.height <= 8 * 2 + 21 * 4
        assert image.height < 8 * 2 + 21 * 21
