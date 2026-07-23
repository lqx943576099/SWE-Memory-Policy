from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops

from swe_memory_policy.utils import sha256_file

CANVAS_WIDTH = 2048
CANVAS_HEIGHT = 4096
WHITE = (255, 255, 255)


def _open_rgb(path: Path) -> Image.Image:
    with Image.open(path) as source:
        return source.convert("RGB")


def _trim_white(image: Image.Image) -> Image.Image:
    background = Image.new("RGB", image.size, WHITE)
    box = ImageChops.difference(image, background).getbbox()
    return image.crop(box) if box is not None else image.crop((0, 0, 1, 1))


def _resize_half(image: Image.Image) -> Image.Image:
    size = (max(1, image.width // 2), max(1, image.height // 2))
    return image.resize(size, Image.Resampling.LANCZOS)


def compose_fixed_2x(
    source_pages: Sequence[tuple[int, Path]],
    output_dir: Path,
    request_index: int,
) -> tuple[list[Path], dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    canvases: list[Image.Image] = [
        Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), WHITE)
    ]
    placements: list[dict[str, Any]] = []
    row_y = 0
    row_height = 0
    column = 0
    for oa_index, path in source_pages:
        source = _open_rgb(path)
        scaled = source.resize(
            (CANVAS_WIDTH // 2, max(1, source.height // 2)),
            Image.Resampling.LANCZOS,
        )
        if scaled.height > CANVAS_HEIGHT:
            raise ValueError(f"scaled source page is taller than a canvas: {path}")
        if column == 0 and row_y + scaled.height > CANVAS_HEIGHT:
            canvases.append(Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), WHITE))
            row_y = 0
            row_height = 0
        x = column * (CANVAS_WIDTH // 2)
        canvases[-1].paste(scaled, (x, row_y))
        placements.append(
            {
                "oa_index": oa_index,
                "source_path": str(path),
                "source_sha256": sha256_file(path),
                "canvas_page": len(canvases),
                "x": x,
                "y": row_y,
                "width": scaled.width,
                "height": scaled.height,
                "linear_scale": 0.5,
            }
        )
        row_height = max(row_height, scaled.height)
        column += 1
        if column == 2:
            column = 0
            row_y += row_height
            row_height = 0
    paths: list[Path] = []
    for page, canvas in enumerate(canvases, start=1):
        path = output_dir / f"request_{request_index:04d}_p{page:03d}.png"
        canvas.save(path, format="PNG", optimize=False, compress_level=9)
        paths.append(path)
    return paths, {"strategy": "image_fixed_2x", "placements": placements}


def _vertical_source(paths: Sequence[Path]) -> Image.Image:
    images = [_open_rgb(path) for path in paths]
    width = max(image.width for image in images)
    height = sum(image.height for image in images)
    output = Image.new("RGB", (width, height), WHITE)
    y = 0
    for image in images:
        output.paste(image, (0, y))
        y += image.height
    return output


def _fit(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
    scale = min(max_width / image.width, max_height / image.height, 1.0)
    if scale == 1.0:
        return image
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)


def compose_dynamic_recursive(
    parent_path: Path | None,
    latest_pages: Sequence[Path],
    output_dir: Path,
    request_index: int,
) -> tuple[Path, dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), WHITE)
    parent_hash: str | None = None
    old_height = 0
    if parent_path is not None:
        parent_hash = sha256_file(parent_path)
        parent = _trim_white(_open_rgb(parent_path))
        parent = _resize_half(parent)
        parent = _fit(parent, CANVAS_WIDTH, CANVAS_HEIGHT // 2)
        canvas.paste(parent, (0, 0))
        old_height = parent.height
    latest = _fit(_vertical_source(latest_pages), CANVAS_WIDTH, CANVAS_HEIGHT // 2)
    latest_y = old_height
    if latest_y + latest.height > CANVAS_HEIGHT:
        latest_y = CANVAS_HEIGHT - latest.height
    canvas.paste(latest, (0, latest_y))
    path = output_dir / f"request_{request_index:04d}.png"
    canvas.save(path, format="PNG", optimize=False, compress_level=9)
    return path, {
        "strategy": "image_dynamic_recursive",
        "parent_path": str(parent_path) if parent_path else None,
        "parent_sha256": parent_hash,
        "parent_linear_scale": 0.5 if parent_path else None,
        "latest_sources": [
            {"path": str(item), "sha256": sha256_file(item)} for item in latest_pages
        ],
        "latest_y": latest_y,
        "latest_width": latest.width,
        "latest_height": latest.height,
    }


def compose_dynamic_reference(
    oa_pages: Sequence[Sequence[Path]],
    output_path: Path,
) -> Path:
    canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), WHITE)
    composites = [_vertical_source(paths) for paths in oa_pages]
    weights = [0.5 ** (len(composites) - 1 - index) for index in range(len(composites))]
    total = sum(weights) or 1.0
    y = 0
    for composite, weight in zip(composites, weights, strict=True):
        allocated = max(1, round(CANVAS_HEIGHT * weight / total))
        fitted = _fit(composite, CANVAS_WIDTH, allocated)
        canvas.paste(fitted, (0, y))
        y += allocated
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="PNG", optimize=False, compress_level=9)
    return output_path
