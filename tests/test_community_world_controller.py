import asyncio

from stream_cheremsha.overlays.community_world_controller import CommunityWorldController
from stream_cheremsha.overlays.pubsub import OverlayPubSub


def _controller(pubsub: OverlayPubSub) -> CommunityWorldController:
    return CommunityWorldController(
        pubsub=pubsub,
        get_locale=lambda: "uk",
        instance="main",
    )


def test_initial_state_shape() -> None:
    ps = OverlayPubSub()
    c = _controller(ps)
    state = c.initial_state()
    assert state["config"]["enabled"] is True
    assert state["level"] == 1
    assert "quests" in state
    assert "elders" in state
    assert state["locale"] == "uk"


def test_events_schedule_and_publish() -> None:
    ps = OverlayPubSub()
    c = _controller(ps)

    async def _run() -> dict:
        q = ps.subscribe("overlay:community_world:main")
        c.on_follow(user="alice", user_key="k-a")
        c.on_like(user="bob", n=100, user_key="k-b")
        await c._publish_patch()
        patch = await asyncio.wait_for(q.get(), timeout=1.0)
        return patch

    patch = asyncio.run(_run())
    assert patch["follows"] == 1
    assert patch["likes"] == 100
    assert patch["config"]["enabled"] is True
    assert "elders" in patch


def test_reset_session() -> None:
    ps = OverlayPubSub()
    c = _controller(ps)
    c.on_follow(user="alice", user_key="k-a")
    assert c._session.follows == 1
    c.reset_session()
    assert c._session.follows == 0


def test_badge_persistence(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("STREAM_CHEREMSHA_COMMUNITY_WORLD_DB", str(tmp_path / "cw.sqlite"))
    from stream_cheremsha.persistence.community_world_sqlite import (
        fetch_community_badges_for_user,
    )

    ps = OverlayPubSub()
    c = _controller(ps)
    c.on_follow(user="alice", user_key="k-a")
    c.on_gift(user="alice", user_key="k-a", gift_name="Rose", coins=200)
    badges = fetch_community_badges_for_user("k-a")
    assert {b["badge"] for b in badges} == {"founder", "gifter", "supporter"}