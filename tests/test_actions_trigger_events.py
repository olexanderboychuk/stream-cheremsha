"""TDD: trigger event build + persist for Kick (same contract as Twitch/YouTube/TikTok)."""

from __future__ import annotations

import json

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from stream_cheremsha.actions.models import RuleV1, ruleset_from_json_text, ruleset_to_json_text
from stream_cheremsha.actions.trigger_events import (
    build_trigger_event,
    kind_values_for_platform,
    merge_platform_change,
)


@pytest.fixture()
def qapplication() -> QApplication:
    app = QApplication.instance()
    if app is None:
        return QApplication([])
    return app


def test_kind_values_for_kick_includes_all_kick_events() -> None:
    kinds = kind_values_for_platform("kick")
    assert "chat_keyword" in kinds
    assert "kick_follow" in kinds
    assert "kick_subscription" in kinds
    assert "kick_gift_sub" in kinds
    assert "kick_gift" in kinds


def test_build_kick_subscription_on_kick_platform() -> None:
    ev = build_trigger_event("kick_subscription", "kick")
    assert ev["type"] == "kick_subscription"
    assert ev.get("platform") == "kick"
    assert ev["params"] == {"user": ""}


def test_build_kick_subscription_preserves_user_filter() -> None:
    ev = build_trigger_event(
        "kick_subscription",
        "kick",
        existing_params={"user": "bob"},
    )
    assert ev["params"]["user"] == "bob"


def test_kick_subscription_ruleset_roundtrip() -> None:
    rule = RuleV1(
        id="r-kick-sub",
        enabled=True,
        events=(build_trigger_event("kick_subscription", "kick"),),
        actions=[{"type": "play_sound", "params": {"file_path": "/x/a.mp3"}}],
    )
    text = ruleset_to_json_text([rule])
    out = ruleset_from_json_text(text)
    assert out[0].events[0]["type"] == "kick_subscription"


@pytest.mark.usefixtures("qapplication")
def test_build_kick_subscription_json_api(qapplication: QApplication) -> None:
    import stream_cheremsha.ui.actions_qml_api as mod

    api = mod.ActionsQmlApi(QWidget())
    txt = api.buildTriggerEventJson("kick_subscription", "kick", "{}")
    ev = json.loads(txt)
    assert ev["type"] == "kick_subscription"
    assert ev.get("platform") == "kick"
    assert ev["params"] == {"user": ""}


def test_build_kick_follow_on_kick_platform() -> None:
    ev = build_trigger_event("kick_follow", "kick")
    assert ev["type"] == "kick_follow"
    assert ev.get("platform") == "kick"
    assert ev["params"] == {"user": ""}


def test_build_kick_follow_preserves_user_filter() -> None:
    ev = build_trigger_event(
        "kick_follow",
        "kick",
        existing_params={"user": "alice"},
    )
    assert ev["params"]["user"] == "alice"


def test_build_chat_keyword_on_kick_platform() -> None:
    ev = build_trigger_event(
        "chat_keyword",
        "kick",
        existing_params={"text": "hello", "match": "contains", "case_sensitive": False},
    )
    assert ev["type"] == "chat_keyword"
    assert ev.get("platform") == "kick"
    assert ev["params"]["text"] == "hello"


def test_merge_platform_change_keeps_kick_follow() -> None:
    current = build_trigger_event("kick_follow", "kick")
    merged = merge_platform_change(current, "kick")
    assert merged["type"] == "kick_follow"
    assert merged.get("platform") == "kick"


def test_merge_platform_change_resets_incompatible_kind_to_chat() -> None:
    current = build_trigger_event("twitch_follow", "twitch")
    merged = merge_platform_change(current, "kick")
    assert merged["type"] == "chat_keyword"
    assert merged.get("platform") == "kick"


def test_kick_follow_ruleset_roundtrip() -> None:
    rule = RuleV1(
        id="r-kick",
        enabled=True,
        events=(build_trigger_event("kick_follow", "kick"),),
        actions=[{"type": "play_sound", "params": {"file_path": "/x/a.mp3"}}],
    )
    text = ruleset_to_json_text([rule])
    out = ruleset_from_json_text(text)
    assert out[0].events[0]["type"] == "kick_follow"


@pytest.mark.usefixtures("qapplication")
def test_save_rules_json_accepts_kick_follow_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    import stream_cheremsha.ui.actions_qml_api as mod

    saved: list[str] = []

    def _capture(_p: str, _ak: str, rules: list[RuleV1], _layout: object) -> None:
        saved.append(rules[0].events[0]["type"])

    monkeypatch.setattr(mod, "save_rules_bundle", _capture)

    class _Stub(QWidget):
        def _actions_reload_scope(self, _p: str, _ak: str) -> None:
            return None

    api = mod.ActionsQmlApi(_Stub())
    ev = build_trigger_event("kick_follow", "kick")
    payload = {
        "schema_version": 1,
        "rules": [
            {
                "id": "r1",
                "enabled": True,
                "event": ev,
                "actions": [{"type": "play_sound", "params": {"file_path": "/a.mp3"}}],
            }
        ],
    }
    api.saveRulesJson("tiktok", "app", json.dumps(payload))
    assert saved == ["kick_follow"]


@pytest.mark.usefixtures("qapplication")
def test_build_trigger_event_json_api(qapplication: QApplication) -> None:
    import stream_cheremsha.ui.actions_qml_api as mod

    api = mod.ActionsQmlApi(QWidget())
    txt = api.buildTriggerEventJson("kick_follow", "kick", "{}")
    ev = json.loads(txt)
    assert ev["type"] == "kick_follow"
    assert ev.get("platform") == "kick"
