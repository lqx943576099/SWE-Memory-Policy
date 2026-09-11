from __future__ import annotations

from swe_memory_policy.image_response_only_observation import (
    build_responses_observation_image_block,
)
from swe_memory_policy.image_response_only_observation_2x import (
    LINEAR_DOWNSCALE_FACTOR as FACTOR_2X,
)
from swe_memory_policy.image_response_only_observation_2x import (
    build_responses_observation_image_block_2x,
)
from swe_memory_policy.image_response_only_observation_4x import (
    LINEAR_DOWNSCALE_FACTOR as FACTOR_4X,
)
from swe_memory_policy.image_response_only_observation_4x import (
    build_responses_observation_image_block_4x,
)


def test_scaled_policies_share_the_exact_canonical_observation_source() -> None:
    kwargs = {
        "sequence_index": 1,
        "oa_index": 3,
        "tool_index": 1,
        "tool_call_id": "call-3",
        "content": "<returncode>0</returncode>\n<output>visible</output>",
    }
    original = build_responses_observation_image_block(**kwargs)
    scaled_2x = build_responses_observation_image_block_2x(**kwargs)
    scaled_4x = build_responses_observation_image_block_4x(**kwargs)
    assert original == scaled_2x == scaled_4x
    assert (FACTOR_2X, FACTOR_4X) == (2, 4)
