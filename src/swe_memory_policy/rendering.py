from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from fontTools.ttLib import TTCollection, TTFont
from PIL import Image, ImageDraw, ImageFont

from swe_memory_policy.utils import sha256_file

BACKGROUND = "#FFFFFF"
FOREGROUND = "#111111"
BASE_WIDTH = 2048
MAX_PAGE_HEIGHT = 4096
FONT_SIZE = 18
LINE_HEIGHT = 25
PADDING = 24


class FontCoverageError(ValueError):
    pass


@dataclass(frozen=True)
class FontFace:
    path: Path
    index: int
    coverage: frozenset[int]
    font: ImageFont.FreeTypeFont


def _font_candidates() -> list[Path]:
    configured = os.getenv("IMAGE_MEMORY_FONT_PATHS")
    if configured:
        return [Path(item) for item in configured.split(os.pathsep) if item]
    return [
        Path("/usr/local/share/fonts/CascadiaMono.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/consola.ttf"),
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/seguisym.ttf"),
    ]


def _coverage(font: TTFont) -> frozenset[int]:
    result: set[int] = set()
    for table in font["cmap"].tables:
        result.update(table.cmap)
    return frozenset(result)


def load_font_faces() -> tuple[FontFace, ...]:
    faces: list[FontFace] = []
    for path in _font_candidates():
        if not path.is_file():
            continue
        if path.suffix.lower() == ".ttc":
            collection = TTCollection(path, lazy=True)
            for index, font_data in enumerate(collection.fonts):
                faces.append(
                    FontFace(
                        path=path,
                        index=index,
                        coverage=_coverage(font_data),
                        font=ImageFont.truetype(str(path), FONT_SIZE, index=index),
                    )
                )
            collection.close()
        else:
            font_data = TTFont(path, lazy=True)
            faces.append(
                FontFace(
                    path=path,
                    index=0,
                    coverage=_coverage(font_data),
                    font=ImageFont.truetype(str(path), FONT_SIZE),
                )
            )
            font_data.close()
    if not faces:
        raise FontCoverageError("none of the configured fonts could be loaded")
    return tuple(faces)


class FontResolver:
    def __init__(self) -> None:
        self.faces = load_font_faces()
        self._cache: dict[str, FontFace] = {}

    def face_for(self, character: str) -> FontFace:
        cached = self._cache.get(character)
        if cached is not None:
            return cached
        codepoint = ord(character)
        for face in self.faces:
            if codepoint in face.coverage:
                self._cache[character] = face
                return face
        raise FontCoverageError(
            f"no configured font covers U+{codepoint:04X} ({character!r})"
        )

    def manifest(self) -> list[dict[str, str | int]]:
        records: list[dict[str, str | int]] = []
        seen: set[tuple[Path, int]] = set()
        for face in self.faces:
            key = (face.path, face.index)
            if key in seen:
                continue
            seen.add(key)
            records.append(
                {
                    "path": str(face.path),
                    "index": face.index,
                    "sha256": sha256_file(face.path),
                }
            )
        return records


def _expand_tabs(text: str) -> str:
    output: list[str] = []
    column = 0
    for character in text:
        if character == "\t":
            count = 4 - (column % 4)
            output.append(" " * count)
            column += count
        else:
            output.append(character)
            column = 0 if character == "\n" else column + 1
    return "".join(output)


def _visual_lines(
    text: str, resolver: FontResolver, available_width: int
) -> list[list[tuple[str, FontFace]]]:
    text = _expand_tabs(text.replace("\r\n", "\n").replace("\r", "\n"))
    logical_lines = text.split("\n")
    visual: list[list[tuple[str, FontFace]]] = []
    for logical in logical_lines:
        current: list[tuple[str, FontFace]] = []
        width = 0.0
        if not logical:
            visual.append(current)
            continue
        for character in logical:
            face = resolver.face_for(character)
            advance = face.font.getlength(character)
            if current and width + advance > available_width:
                visual.append(current)
                current = []
                width = 0.0
            current.append((character, face))
            width += advance
        visual.append(current)
    if text.endswith("\n") and visual and not visual[-1]:
        visual.pop()
    return visual or [[]]


def _draw_visual_line(
    draw: ImageDraw.ImageDraw,
    line: list[tuple[str, FontFace]],
    x: int,
    y: int,
) -> None:
    cursor = float(x)
    run: list[str] = []
    run_face: FontFace | None = None

    def flush() -> None:
        nonlocal cursor, run
        if run_face is None or not run:
            return
        text = "".join(run)
        draw.text((cursor, y), text, font=run_face.font, fill=FOREGROUND)
        cursor += run_face.font.getlength(text)
        run = []

    for character, face in line:
        if run_face is not None and face != run_face:
            flush()
        run_face = face
        run.append(character)
    flush()


def render_text_pages(text: str, output_dir: Path, stem: str) -> list[Path]:
    text.encode("utf-8", errors="strict")
    resolver = FontResolver()
    lines = _visual_lines(text, resolver, BASE_WIDTH - 2 * PADDING)
    lines_per_page = max(1, (MAX_PAGE_HEIGHT - 2 * PADDING) // LINE_HEIGHT)
    chunks = [
        lines[index : index + lines_per_page]
        for index in range(0, len(lines), lines_per_page)
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for page_index, chunk in enumerate(chunks, start=1):
        height = min(
            MAX_PAGE_HEIGHT,
            max(2 * PADDING + LINE_HEIGHT, 2 * PADDING + len(chunk) * LINE_HEIGHT),
        )
        image = Image.new("RGB", (BASE_WIDTH, height), BACKGROUND)
        draw = ImageDraw.Draw(image)
        for line_index, line in enumerate(chunk):
            _draw_visual_line(draw, line, PADDING, PADDING + line_index * LINE_HEIGHT)
        filename = (
            f"{stem}.png" if len(chunks) == 1 else f"{stem}_p{page_index:03d}.png"
        )
        path = output_dir / filename
        image.save(path, format="PNG", optimize=False, compress_level=9)
        paths.append(path)
    return paths


def rendering_manifest() -> dict[str, object]:
    resolver = FontResolver()
    return {
        "background": BACKGROUND,
        "foreground": FOREGROUND,
        "base_width": BASE_WIDTH,
        "max_page_height": MAX_PAGE_HEIGHT,
        "font_size": FONT_SIZE,
        "line_height": LINE_HEIGHT,
        "padding": PADDING,
        "fonts": resolver.manifest(),
    }
