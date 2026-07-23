from __future__ import annotations

from pathlib import Path

from PIL import Image

from swe_memory_policy.rendering import render_text_pages
from swe_memory_policy.strategies import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    compose_dynamic_recursive,
    compose_fixed_2x,
)
from swe_memory_policy.utils import sha256_file


def test_white_render_is_deterministic_and_preserves_unicode(tmp_path: Path) -> None:
    text = "OA 0001 | ACTION\nprint('中文 ✓')\n\treturn 1\\2\n"
    first = render_text_pages(text, tmp_path / "a", "OA0001")
    second = render_text_pages(text, tmp_path / "b", "OA0001")
    assert len(first) == len(second) == 1
    assert sha256_file(first[0]) == sha256_file(second[0])
    with Image.open(first[0]) as image:
        assert image.width == CANVAS_WIDTH
        assert image.getpixel((0, 0)) == (255, 255, 255)


def test_fixed_2x_is_ordered_and_uses_half_scale(tmp_path: Path) -> None:
    sources = []
    for index in range(1, 4):
        path = render_text_pages(
            f"OA {index:04d} | ACTION\nvalue={index}\n",
            tmp_path / "source",
            f"OA{index:04d}",
        )[0]
        sources.append((index, path))
    canvases, record = compose_fixed_2x(sources, tmp_path / "canvas", 2)
    assert len(canvases) == 1
    assert [item["oa_index"] for item in record["placements"]] == [1, 2, 3]
    assert all(item["linear_scale"] == 0.5 for item in record["placements"])
    with Image.open(canvases[0]) as image:
        assert image.size == (CANVAS_WIDTH, CANVAS_HEIGHT)


def test_dynamic_canvas_records_parent_hash(tmp_path: Path) -> None:
    first_source = render_text_pages(
        "OA 0001 | ACTION\na\n", tmp_path / "s", "OA0001"
    )
    first, first_record = compose_dynamic_recursive(
        None, first_source, tmp_path / "c", 1
    )
    second_source = render_text_pages(
        "OA 0002 | ACTION\nb\n", tmp_path / "s", "OA0002"
    )
    second, record = compose_dynamic_recursive(
        first, second_source, tmp_path / "c", 2
    )
    assert first_record["parent_sha256"] is None
    assert record["parent_sha256"] == sha256_file(first)
    assert record["parent_linear_scale"] == 0.5
    with Image.open(second) as image:
        assert image.size == (CANVAS_WIDTH, CANVAS_HEIGHT)
