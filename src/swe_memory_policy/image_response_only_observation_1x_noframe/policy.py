from __future__ import annotations

from dataclasses import dataclass

from swe_memory_policy.utils import sha256_bytes

CONDITION_NAME = "image_response_only_observation_1x_noframe"


@dataclass(frozen=True)
class NoframeObservationImageBlock:
    """One unmodified function-call observation prepared for visual transport."""

    sequence_index: int
    oa_index: int
    tool_index: int
    tool_call_id: str
    raw_content: str

    @property
    def stem(self) -> str:
        return f"OA{self.oa_index:04d}_Tool{self.tool_index:03d}"

    @property
    def metadata(self) -> str:
        return (
            f"OA={self.oa_index} role=tool tool={self.tool_index} "
            f"call_id={self.tool_call_id} encoding=verbatim-newline-marker"
        )

    def manifest(self) -> dict[str, object]:
        encoded = self.raw_content.encode("utf-8")
        return {
            "encoding": "verbatim_newlines_as_visible_markers",
            "raw_sha256": sha256_bytes(encoded),
            "raw_bytes": len(encoded),
            "newline_count": self.raw_content.count("\n"),
            "carriage_return_count": self.raw_content.count("\r"),
            "content_rewritten": False,
        }


def build_noframe_observation_image_block(
    *,
    sequence_index: int,
    oa_index: int,
    tool_index: int,
    tool_call_id: str,
    content: str,
) -> NoframeObservationImageBlock:
    if min(sequence_index, oa_index, tool_index) < 1:
        raise ValueError("observation image indexes must be positive")
    if not tool_call_id:
        raise ValueError("observation image requires a non-empty tool_call_id")
    if not isinstance(content, str):
        raise TypeError("observation content must be text")
    return NoframeObservationImageBlock(
        sequence_index=sequence_index,
        oa_index=oa_index,
        tool_index=tool_index,
        tool_call_id=tool_call_id,
        raw_content=content,
    )
