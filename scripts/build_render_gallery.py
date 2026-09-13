"""Build the public synthetic 1–10× gallery with the actual renderer."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from fractions import Fraction
from importlib.metadata import version
from pathlib import Path

from swe_memory_policy.offline import render_history


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = root / "examples/render_gallery.json"
    value = json.loads(source.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="swe-memory-gallery-") as temporary:
        rendered_dir = Path(temporary) / "rendered"
        rendered = render_history(
            value,
            rendered_dir,
            factors=tuple(Fraction(k) for k in range(1, 11)),
            model="gpt-5.6-luna",
            detail="high",
        )
        observation = rendered["observations"][0]
        images = observation["images"]
        if len(images) != 10 or any(item["status"] != "rendered" for item in images):
            raise ValueError(
                "the gallery requires one successfully rendered page per factor"
            )
        records = []
        for item in images:
            name = f"image{item['factor']}x.png"
            shutil.copyfile(rendered_dir / item["path"], args.output_dir / name)
            records.append(
                {
                    key: item[key]
                    for key in (
                        "factor",
                        "sha256",
                        "width",
                        "height",
                        "original_width",
                        "original_height",
                        "baseline_visual_tokens",
                        "target_visual_tokens",
                        "token_budget",
                        "estimated_visual_tokens",
                        "budget_satisfied",
                        "budget_slack_tokens",
                        "achieved_estimated_compression_factor",
                        "achieved_visual_token_ratio",
                        "resampling",
                        "baseline_preprocessing",
                        "output_preprocessing",
                    )
                }
                | {"path": name}
            )
        compact = observation["compact_rendering"]
        metadata = {
            "schema_version": "swe-memory-public-gallery-v1",
            "compression_definition": "visual_token_ratio",
            "generator": {
                "path": "scripts/build_render_gallery.py",
                "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            },
            "input": "examples/render_gallery.json",
            "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "source_observation_sha256": observation["source_sha256"],
            "synthetic_input": True,
            "model_api_called": False,
            "provider_usage_measured": False,
            "visual_token_estimator": rendered["visual_token_estimator"],
            "model": rendered["model"],
            "detail": rendered["input_image_detail"],
            "dependencies": {name: version(name) for name in ("pillow", "fonttools")},
            "fonts": [
                {
                    "name": Path(font["path"]).name,
                    "index": font["index"],
                    "sha256": font["sha256"],
                }
                for font in compact["fonts"]
            ],
            "classification": observation["classification"],
            "layout": compact["visual_layout"],
            "generated_structure": compact["generated_structure"],
            "path_mappings": compact["path_mappings"],
            "source_files": [
                {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                for path in sorted((root / "src/swe_memory_policy").rglob("*.py"))
            ],
            "images": records,
        }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = ["| 1× | 2× | 3× | 4× | 5× |", "|---|---|---|---|---|"]
    for row in (range(1, 6), range(6, 11)):
        if row.start == 6:
            lines.extend(["", "| 6× | 7× | 8× | 9× | 10× |", "|---|---|---|---|---|"])
        lines.append(
            "| "
            + " | ".join(
                f"[![{k}×](docs/images/gallery/image{k}x.png)](docs/images/gallery/image{k}x.png)"
                for k in row
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "| 档位 | 实际尺寸（px） | Token 预算 | 估算视觉 Token | "
            "实际估算压缩倍率 |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for item in records:
        lines.append(
            f"| {item['factor']}× | {item['width']} × {item['height']} | "
            f"{item['token_budget']} | {item['estimated_visual_tokens']} | "
            f"{item['achieved_estimated_compression_factor']:.4f}× |"
        )
    (args.output_dir / "README.gallery.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(args.output_dir / "manifest.json")


if __name__ == "__main__":
    main()
