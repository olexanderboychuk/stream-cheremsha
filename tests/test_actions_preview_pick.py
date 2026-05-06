from __future__ import annotations

from stream_cheremsha.actions.models import RuleV1
from stream_cheremsha.ui.actions_qml_api import pick_preview_trigger_for_rule


def _rule(
    *,
    ev_likes: dict,
    ev_chat: dict,
    actions: list[dict],
) -> RuleV1:
    return RuleV1(
        id="r1",
        enabled=True,
        events=(ev_chat, ev_likes),
        actions=actions,
        name="",
    )


def test_preview_picks_likes_trigger_when_liketotal_placeholder_present() -> None:
    likes = {"type": "tiktok_likes_received", "params": {"min_count": 250, "scope": "all_users"}}
    chat = {
        "type": "chat_keyword",
        "params": {"text": "hi", "match": "contains", "case_sensitive": False},
    }
    r = _rule(
        ev_likes=likes,
        ev_chat=chat,
        actions=[{"type": "show_overlay", "params": {"text": "{liketotal}", "seconds": 5}}],
    )
    picked = pick_preview_trigger_for_rule(r.events, actions=r.actions, store_platform="tiktok")
    assert picked["type"] == "tiktok_likes_received"


def test_preview_falls_back_to_first_trigger_without_decisive_placeholders() -> None:
    likes = {"type": "tiktok_likes_received", "params": {"min_count": 250, "scope": "all_users"}}
    chat = {
        "type": "chat_keyword",
        "params": {"text": "hi", "match": "contains", "case_sensitive": False},
    }
    r = _rule(
        ev_likes=likes,
        ev_chat=chat,
        actions=[{"type": "play_sound", "params": {"file_path": "C:/x.mp3"}}],
    )
    picked = pick_preview_trigger_for_rule(r.events, actions=r.actions, store_platform="tiktok")
    assert picked["type"] == "chat_keyword"
