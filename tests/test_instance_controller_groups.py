"""Per-instance event delivery: no main defaults, events reach every instance.

Regression: after removing the main->instance fan-out, widget instances
starved (no WS events). Live data must flow again, but strictly without
singleton config leakage:
- stateless appends broadcast to ``overlay:{type}:*`` (no "config" key),
- leaderboard engines are per-instance (own sequence/weights/timeline),
- other stateful controllers publish state-only patches to ``:*``.
"""

from __future__ import annotations

import json

import pytest
from PySide6.QtCore import QSettings

from stream_cheremsha.overlays import widget_instances as wimod
from stream_cheremsha.overlays.instance_groups import (
    InstanceControllerGroup,
    instance_config_loader,
)
from stream_cheremsha.overlays.pubsub import OverlayPubSub


def _iso(monkeypatch: pytest.MonkeyPatch, tag: str) -> None:
    monkeypatch.setattr(
        wimod, "QSettings", lambda *a, **k: QSettings("t-org-icg", f"t-app-icg-{tag}")
    )
    QSettings("t-org-icg", f"t-app-icg-{tag}").clear()


def _lb_factory(ps: OverlayPubSub):
    from stream_cheremsha.overlays.live_leaderboard_simple_config import (
        live_leaderboard_simple_config_defaults,
        live_leaderboard_simple_config_from_json_text,
    )
    from stream_cheremsha.overlays.live_leaderboard_simple_controller import (
        LiveLeaderboardSimpleController,
    )

    def _make(iid: str) -> LiveLeaderboardSimpleController:
        return LiveLeaderboardSimpleController(
            pubsub=ps,
            get_locale=lambda: "uk",
            instance=iid,
            config_loader=instance_config_loader(
                "live_leaderboard_simple",
                iid,
                live_leaderboard_simple_config_from_json_text,
                live_leaderboard_simple_config_defaults,
            ),
        )

    return _make


def test_group_syncs_members_from_store(monkeypatch: pytest.MonkeyPatch) -> None:
    _iso(monkeypatch, "sync")
    ps = OverlayPubSub()
    a = wimod.create_instance("live_leaderboard_simple", "A")
    b = wimod.create_instance("live_leaderboard_simple", "B")
    wimod.create_instance("chat", "Other")
    grp = InstanceControllerGroup("live_leaderboard_simple", _lb_factory(ps))
    grp.sync_instances()
    assert grp.instance_ids() == sorted([a.id, b.id])
    assert wimod.delete_instance(a.id) is True
    grp.sync_instances()
    assert grp.instance_ids() == [b.id]


def test_per_instance_state_isolated(monkeypatch: pytest.MonkeyPatch) -> None:
    _iso(monkeypatch, "iso")
    ps = OverlayPubSub()
    seq_a = [{"source_id": "likers", "scene_id": "arena", "duration_sec": 5}]
    seq_b = [
        {"source_id": "gifters", "scene_id": "hall_of_fame", "duration_sec": 9},
        {"source_id": "likers", "scene_id": "hall_of_fame", "duration_sec": 9},
    ]
    a = wimod.create_instance("live_leaderboard_simple", "A")
    b = wimod.create_instance("live_leaderboard_simple", "B")
    wimod.update_instance_settings(
        a.id, {"top_n": 3, "sequence": seq_a, "sequence_json": json.dumps(seq_a)}
    )
    wimod.update_instance_settings(
        b.id, {"top_n": 7, "sequence": seq_b, "sequence_json": json.dumps(seq_b)}
    )
    grp = InstanceControllerGroup("live_leaderboard_simple", _lb_factory(ps))
    grp.sync_instances()
    qa = ps.subscribe(f"overlay:live_leaderboard_simple:{a.id}")
    qb = ps.subscribe(f"overlay:live_leaderboard_simple:{b.id}")

    grp.on_like("kriss", 100, user_key="k")
    for ctl in grp._members.values():  # noqa: SLF001 - flush test-only timers
        ctl._ranking.flush_likes()
        ctl._publish_patch_sync()

    got_a = qa.get_nowait()
    got_b = qb.get_nowait()
    assert qa.empty() and qb.empty()
    # Each instance receives its own topic with its own config.
    assert got_a["config"]["top_n"] == 3
    assert got_b["config"]["top_n"] == 7
    assert got_a["config"]["sequence"] == [
        {"source_id": "likers", "scene_id": "arena", "duration_sec": 5.0}
    ]
    assert len(got_b["config"]["sequence"]) == 2
    # Rankings flow to both.
    assert got_a["rankings"]["likers"][0]["value"] == 100
    assert got_b["rankings"]["likers"][0]["value"] == 100


def test_group_reload_instance_picks_up_saved_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _iso(monkeypatch, "reload")
    ps = OverlayPubSub()
    inst = wimod.create_instance("live_leaderboard_simple", "A")
    grp = InstanceControllerGroup("live_leaderboard_simple", _lb_factory(ps))
    grp.sync_instances()
    seq = [{"source_id": "gifters", "scene_id": "arena", "duration_sec": 11}]
    wimod.update_instance_settings(
        inst.id, {"sequence": seq, "sequence_json": json.dumps(seq)}
    )
    assert grp.reload_instance(inst.id) is True
    assert grp.reload_instance("nope") is False


def test_star_broadcast_reaches_all_chat_instances() -> None:
    ps = OverlayPubSub()
    qa = ps.subscribe("overlay:chat:idA")
    qb = ps.subscribe("overlay:chat:idB")
    q_other = ps.subscribe("overlay:online:idA")
    q_main = ps.subscribe("overlay:chat:main")
    ps.publish_sync("overlay:chat:*", {"append": {"author": "u", "text": "hi"}})
    assert not qa.empty()
    assert not qb.empty()
    assert q_other.empty()
    # Legacy main subscribers also keep working (state-only appends, no config).
    assert not q_main.empty()


@pytest.mark.parametrize(
    "type_id,make",
    [
        (
            "social_rotator",
            lambda ps: __import__(
                "stream_cheremsha.overlays.social_rotator_controller", fromlist=["x"]
            ).SocialRotatorController(pubsub=ps, get_locale=lambda: "uk"),
        ),
        (
            "webcam_frame",
            lambda ps: __import__(
                "stream_cheremsha.overlays.webcam_frame_controller", fromlist=["x"]
            ).WebcamFrameController(pubsub=ps, get_locale=lambda: "uk"),
        ),
        (
            "stream_pet",
            lambda ps: __import__(
                "stream_cheremsha.overlays.stream_pet_controller", fromlist=["x"]
            ).StreamPetController(pubsub=ps, get_locale=lambda: "uk"),
        ),
        (
            "stream_goal",
            lambda ps: __import__(
                "stream_cheremsha.overlays.stream_goal_controller", fromlist=["x"]
            ).StreamGoalController(pubsub=ps, get_locale=lambda: "uk"),
        ),
        (
            "community_world",
            lambda ps: __import__(
                "stream_cheremsha.overlays.community_world_controller", fromlist=["x"]
            ).CommunityWorldController(pubsub=ps, get_locale=lambda: "uk"),
        ),
        (
            "signal_system",
            lambda ps: __import__(
                "stream_cheremsha.overlays.signal_system_controller", fromlist=["x"]
            ).SignalSystemController(pubsub=ps, get_locale=lambda: "uk"),
        ),
    ],
)
def test_stateful_publish_omits_config(type_id: str, make) -> None:
    """Periodic patches must be state-only (instance keeps its own config)."""
    ps = OverlayPubSub()
    q = ps.subscribe(f"overlay:{type_id}:*")
    ctl = make(ps)
    ctl._publish_patch_sync()
    got = q.get_nowait()
    assert "config" not in got, type_id
