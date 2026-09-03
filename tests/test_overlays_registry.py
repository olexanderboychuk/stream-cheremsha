import asyncio

import pytest

from stream_cheremsha.overlays.models import (
    normalize_instance_id,
    overlays_initial_state_msg,
    overlays_patch_msg,
)
from stream_cheremsha.overlays.pubsub import OverlayPubSub
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


def test_debug_overlay_invalid_instance_falls_back_to_default() -> None:
    reg = OverlayRegistry()
    t = reg.get("debug")
    html = t.render_html({"instance": "</script>"})
    # If the untrusted input were reflected into the <script>, we'd likely see an
    # extra `</script>` (beyond the template's own closing tag).
    assert html.lower().count("</script>") == 1
    # And ensure we actually fell back to the safe default instance in JS.
    assert 'const instance = "default"' in html


def test_registry_has_chat_overlay() -> None:
    reg = OverlayRegistry()
    t = reg.get("chat")
    assert t.type == "chat"
    html = t.render_html({"instance": "main"})
    assert "/ws" in html
    st = t.initial_state({"instance": "main"})
    assert "config" in st


def test_registry_has_activity_overlay() -> None:
    reg = OverlayRegistry()
    t = reg.get("activity")
    assert t.type == "activity"
    html = t.render_html({"instance": "main"})
    assert "/ws" in html
    st = t.initial_state({"instance": "main"})
    assert "items" in st


def test_registry_has_online_overlay() -> None:
    reg = OverlayRegistry()
    t = reg.get("online")
    assert t.type == "online"
    html = t.render_html({"instance": "main"})
    assert "/ws" in html
    st = t.initial_state({"instance": "main"})
    assert "online" in st
    assert "config" in st
    assert st["config"].get("layout_mode") in ("combined", "per_platform")


def test_registry_has_top_likers_overlay() -> None:
    reg = OverlayRegistry()
    t = reg.get("top_likers")
    assert t.type == "top_likers"


def test_registry_has_top_gifters_overlay() -> None:
    reg = OverlayRegistry()
    t = reg.get("top_gifters")
    assert t.type == "top_gifters"
    html = t.render_html({"instance": "main"})
    assert "/ws" in html
    st = t.initial_state({"instance": "main"})
    assert "config" in st
    assert "leaders" in st


def test_registry_has_battle_royale_overlay() -> None:
    reg = OverlayRegistry()
    t = reg.get("battle_royale")
    assert t.type == "battle_royale"
    html = t.render_html({"instance": "main"})
    assert "/ws" in html
    st = t.initial_state({"instance": "main"})
    assert "config" in st
    assert st["phase"] == "idle"


def test_registry_has_king_of_live_overlay() -> None:
    reg = OverlayRegistry()
    t = reg.get("king_of_live")
    assert t.type == "king_of_live"
    html = t.render_html({"instance": "main"})
    assert "/ws" in html
    st = t.initial_state({"instance": "main"})
    assert "config" in st
    assert "king" in st


def test_registry_has_actions_overlay() -> None:
    reg = OverlayRegistry()
    t = reg.get("actions")
    assert t.type == "actions"
    html = t.render_html({"instance": "main"})
    assert "/ws" in html
    st = t.initial_state({"instance": "main"})
    assert "config" in st


def test_registry_has_stream_pet_overlay() -> None:
    reg = OverlayRegistry()
    t = reg.get("stream_pet")
    assert t.type == "stream_pet"
    html = t.render_html({"instance": "main"})
    assert "/ws" in html
    assert "StreamPet" in html
    st = t.initial_state({"instance": "main"})
    assert "config" in st
    assert "energy" in st
    assert st["mood"] == "chill"


def test_registry_has_stream_goal_overlay() -> None:
    reg = OverlayRegistry()
    t = reg.get("stream_goal")
    assert t.type == "stream_goal"
    html = t.render_html({"instance": "main"})
    assert "/ws" in html
    assert "Stream Goal" in html
    st = t.initial_state({"instance": "main"})
    assert "config" in st
    assert "goal_type" in st
    assert "current_value" in st


def test_registry_has_social_rotator_overlay() -> None:
    reg = OverlayRegistry()
    t = reg.get("social_rotator")
    assert t.type == "social_rotator"
    html = t.render_html({"instance": "main"})
    assert "/ws" in html
    assert "LIVE SOCIAL" in html
    st = t.initial_state({"instance": "main"})
    assert "config" in st
    assert "rotation" in st
    assert "stats" in st


def test_pubsub_publishes_to_subscribers() -> None:
    async def _run() -> dict[str, int]:
        ps = OverlayPubSub()
        q = ps.subscribe(topic="t")
        await ps.publish(topic="t", patch={"x": 1})
        got = await asyncio.wait_for(q.get(), timeout=1.0)
        return got

    assert asyncio.run(_run()) == {"x": 1}
