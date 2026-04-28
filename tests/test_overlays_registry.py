import pytest

from stream_cheremsha.overlays.models import (
    normalize_instance_id,
    overlays_initial_state_msg,
    overlays_patch_msg,
)


def test_normalize_instance_id_default() -> None:
    assert normalize_instance_id("") == "default"
    assert normalize_instance_id("   ") == "default"


def test_normalize_instance_id_trim() -> None:
    assert normalize_instance_id(" main ") == "main"


def test_envelopes_shape() -> None:
    assert overlays_initial_state_msg({"a": 1}) == {"op": "initial_state", "state": {"a": 1}}
    assert overlays_patch_msg({"x": "y"}) == {"op": "patch", "patch": {"x": "y"}}


def test_normalize_instance_id_rejects_bad_chars() -> None:
    with pytest.raises(ValueError):
        normalize_instance_id("../x")

