import copy
from fractions import Fraction

import pytest
from PIL import Image

from swe_memory_policy import downscale_png_to_visual_token_ratio
from swe_memory_policy.offline import render_history, select_observations
from swe_memory_policy.utils import sha256_file


def history(count=5):
    items = []
    for index in range(count):
        items.extend(
            [
                {
                    "type": "function_call",
                    "call_id": f"call_{index}",
                    "name": "bash",
                    "arguments": '{"command":"echo hello"}',
                },
                {
                    "type": "function_call_output",
                    "call_id": f"call_{index}",
                    "output": "<returncode>0</returncode>\n<output>hello</output>",
                },
            ]
        )
    return {"input": items}


def test_recent_partition_preserves_input():
    value = history()
    before = copy.deepcopy(value)
    observations, metadata = select_observations(value)
    assert [o.observation_index for o in observations] == [1, 2]
    assert metadata["text_oa_indexes"] == [3, 4, 5]
    assert value == before
    assert select_observations(history(3))[0] == []


def test_parallel_tools_share_window():
    value = {
        "input": [
            {"type": "function_call", "call_id": "a"},
            {"type": "function_call", "call_id": "b"},
            {"type": "function_call_output", "call_id": "b", "output": "B"},
            {"type": "function_call_output", "call_id": "a", "output": "A"},
        ]
    }
    assert len(select_observations(value, recent=0)[0]) == 2
    assert select_observations(value, recent=1)[0] == []


def test_invalid_linkage_and_output_directory(tmp_path):
    value = history()
    value["input"].append({"type": "function_call", "call_id": "unfinished"})
    with pytest.raises(ValueError):
        select_observations(value)
    with pytest.raises(FileExistsError):
        render_history("hello", tmp_path)
    with pytest.raises(ValueError):
        render_history("hello", tmp_path / "unused", factors=(Fraction(0),))
    assert not (tmp_path / "unused").exists()


def test_trajectory_terminal_batch_is_reported():
    items = history(2)["input"]
    value = {
        "messages": [
            {"object": "response", "output": [items[0]]},
            items[1],
            {"object": "response", "output": [items[2]]},
            items[3],
            {
                "object": "response",
                "output": [{"type": "function_call", "call_id": "submit"}],
            },
        ]
    }
    observations, metadata = select_observations(value, recent=0)
    assert len(observations) == 2
    assert metadata["ignored_terminal_call_ids"] == ["submit"]


def test_scaling_matches_local_helper(tmp_path):
    output = tmp_path / "render"
    result = render_history("hello world", output, factors=(Fraction(1), Fraction(2)))
    images = result["observations"][0]["images"]
    assert len(images) == 2
    assert images[0]["sha256"] == images[0]["base_sha256"]
    reference = tmp_path / "reference.png"
    reference.write_bytes((output / images[1]["base_path"]).read_bytes())
    geometry = downscale_png_to_visual_token_ratio(
        reference, target_numerator=1, target_denominator=2
    )
    assert sha256_file(reference) == images[1]["sha256"]
    assert (
        geometry["achieved_visual_token_ratio"]
        == images[1]["achieved_visual_token_ratio"]
    )
    assert all((output / r["path"]).exists() for r in images)


def test_linear_factor(tmp_path):
    result = render_history(
        "hello world",
        tmp_path / "linear",
        factors=(Fraction(5, 2),),
        scale_mode="linear",
    )
    record = result["observations"][0]["images"][0]
    with Image.open(tmp_path / "linear" / record["base_path"]) as image:
        assert record["width"] == max(1, image.width * 2 // 5)
        assert record["height"] == max(1, image.height * 2 // 5)


def test_small_image_token_floor(tmp_path):
    image = tmp_path / "small.png"
    Image.new("RGB", (100, 100), "white").save(image)
    geometry = downscale_png_to_visual_token_ratio(
        image, target_numerator=1, target_denominator=10
    )
    assert geometry["achieved_visual_token_ratio"] == 1
    assert geometry["target_visual_tokens"] < geometry["estimated_visual_tokens"]
