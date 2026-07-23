from __future__ import annotations

import hashlib
import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            separators=(",", ": "),
        )
        + "\n"
    ).encode("utf-8")


def compact_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        with suppress(FileNotFoundError):
            os.unlink(temporary)
        raise


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_bytes(path, canonical_json_bytes(value))


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = compact_json(value).encode("utf-8") + b"\n"
    with path.open("ab") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def redact_data_urls(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: redact_data_urls(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_data_urls(item) for item in value]
    if isinstance(value, str) and value.startswith("data:") and ";base64," in value:
        media, encoded = value.split(",", 1)
        return {
            "redacted_data_url": True,
            "media_type": media[5:].split(";", 1)[0],
            "encoded_length": len(encoded),
            "sha256": sha256_bytes(encoded.encode("ascii")),
        }
    return value
