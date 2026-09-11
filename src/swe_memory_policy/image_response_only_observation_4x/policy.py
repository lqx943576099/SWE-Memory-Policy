from __future__ import annotations

from swe_memory_policy.image_response_only_observation.policy import (
    ObservationImageBlock,
    build_responses_observation_image_block,
    render_responses_image_response_only_observation,
)

CONDITION_NAME = "image_response_only_observation_4x"
LINEAR_DOWNSCALE_FACTOR = 4


def render_responses_image_response_only_observation_4x(
    *, oa_index: int, tool_index: int, tool_call_id: str, content: str
) -> str:
    """Render the same canonical source used by the full-resolution policy."""

    return render_responses_image_response_only_observation(
        oa_index=oa_index,
        tool_index=tool_index,
        tool_call_id=tool_call_id,
        content=content,
    )


def build_responses_observation_image_block_4x(
    *,
    sequence_index: int,
    oa_index: int,
    tool_index: int,
    tool_call_id: str,
    content: str,
) -> ObservationImageBlock:
    """Build an observation block whose PNG pages are downscaled by the caller."""

    return build_responses_observation_image_block(
        sequence_index=sequence_index,
        oa_index=oa_index,
        tool_index=tool_index,
        tool_call_id=tool_call_id,
        content=content,
    )
