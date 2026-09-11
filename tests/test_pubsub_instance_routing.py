from __future__ import annotations

import pytest

from stream_cheremsha.overlays.pubsub import OverlayPubSub


@pytest.mark.asyncio
async def test_chat_message_reaches_custom_instance() -> None:
    ps = OverlayPubSub()
    q_main = ps.subscribe("overlay:chat:main")
    q_custom = ps.subscribe("overlay:chat:custom_inst_id_123")

    msg = {
        "append": {
            "author": "TestUser",
            "text": "Hello world",
            "platform": "twitch",
            "received_at": "2026-09-11T23:00:00Z",
        }
    }
    ps.publish_sync("overlay:chat:main", msg)

    assert not q_main.empty()
    assert not q_custom.empty()
    rec_main = q_main.get_nowait()
    rec_custom = q_custom.get_nowait()

    assert rec_main == msg
    assert rec_custom == msg


@pytest.mark.asyncio
async def test_config_only_patch_isolated_to_main() -> None:
    ps = OverlayPubSub()
    q_main = ps.subscribe("overlay:chat:main")
    q_custom = ps.subscribe("overlay:chat:custom_inst_id_123")

    cfg_patch = {"config": {"max_items": 20}, "timestamp": 12345.6}
    ps.publish_sync("overlay:chat:main", cfg_patch)

    assert not q_main.empty()
    assert q_custom.empty()
    assert q_main.get_nowait() == cfg_patch


@pytest.mark.asyncio
async def test_stream_event_with_config_strips_config_for_custom_instance() -> None:
    ps = OverlayPubSub()
    q_main = ps.subscribe("overlay:stream_goal:main")
    q_custom = ps.subscribe("overlay:stream_goal:my_goal_instance_456")

    progress_patch = {
        "current_value": 42,
        "target_value": 100,
        "progress": 0.42,
        "visual_events": [{"type": "like", "amount": 5}],
        "config": {"skin": "cyberpunk", "accent_color": "#ff0055"},
    }
    ps.publish_sync("overlay:stream_goal:main", progress_patch)

    assert not q_main.empty()
    assert not q_custom.empty()

    rec_main = q_main.get_nowait()
    rec_custom = q_custom.get_nowait()

    # Main gets the singleton config
    assert rec_main["config"] == {"skin": "cyberpunk", "accent_color": "#ff0055"}
    assert rec_main["current_value"] == 42

    # Custom instance gets the progress and events, but NOT the singleton config
    assert "config" not in rec_custom
    assert rec_custom["current_value"] == 42
    assert rec_custom["progress"] == 0.42
    assert rec_custom["visual_events"] == [{"type": "like", "amount": 5}]


@pytest.mark.asyncio
async def test_custom_instance_targeted_publish_reaches_only_target() -> None:
    ps = OverlayPubSub()
    q_main = ps.subscribe("overlay:chat:main")
    q_custom1 = ps.subscribe("overlay:chat:inst_1")
    q_custom2 = ps.subscribe("overlay:chat:inst_2")

    patch = {"config": {"font_size": 24}, "timestamp": 999.0}
    ps.publish_sync("overlay:chat:inst_1", patch)

    assert q_main.empty()
    assert q_custom2.empty()
    assert not q_custom1.empty()
    assert q_custom1.get_nowait() == patch


@pytest.mark.asyncio
async def test_wildcard_broadcast_reaches_all_instances_of_same_type() -> None:
    ps = OverlayPubSub()
    q_chat1 = ps.subscribe("overlay:chat:main")
    q_chat2 = ps.subscribe("overlay:chat:custom_inst")
    q_goal = ps.subscribe("overlay:stream_goal:main")

    patch = {"clear": True}
    ps.publish_sync("overlay:chat:*", patch)

    assert not q_chat1.empty()
    assert not q_chat2.empty()
    assert q_goal.empty()
    assert q_chat1.get_nowait() == patch
    assert q_chat2.get_nowait() == patch
