import pytest

from stream_cheremsha.overlays.models import (
    normalize_instance_id,
    overlays_initial_state_msg,
    overlays_patch_msg,
)
from stream_cheremsha.overlays.registry import OverlayRegistry, UnknownOverlayTypeError


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


def test_registry_register_and_get() -> None:
    reg = OverlayRegistry()
    t = reg.get("debug")
    assert t.type == "debug"


def test_registry_unknown_type() -> None:
    reg = OverlayRegistry()
    with pytest.raises(UnknownOverlayTypeError):
        reg.get("missing")


def test_debug_overlay_renders_html() -> None:
    reg = OverlayRegistry()
    t = reg.get("debug")
    html = t.render_html({"instance": "default"})
    assert "<html" in html.lower()
    assert "/ws" in html
    assert "subscribe" in html.lower()

