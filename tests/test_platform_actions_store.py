from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from stream_cheremsha.actions.models import RuleV1
from stream_cheremsha.actions.store import actions_rules_key_is_set, load_rules, save_rules


@pytest.fixture()
def ini_settings(tmp_path: Path) -> QSettings:
    # Ensure tests do not touch Windows registry (NativeFormat).
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
    org = f"test-org-{uuid.uuid4()}"
    app = f"test-app-{uuid.uuid4()}"
    s = QSettings(QSettings.IniFormat, QSettings.UserScope, org, app)
    s.clear()
    s.sync()
    return s


def _rule(rule_id: str) -> RuleV1:
    return RuleV1(
        id=rule_id,
        enabled=True,
        events=(
            {
                "type": "chat_keyword",
                "params": {"text": "hello", "match": "contains", "case_sensitive": False},
            },
        ),
        actions=[{"type": "play_sound", "params": {"file_path": r"C:\tmp\a.mp3"}}],
    )


def test_load_rules_returns_empty_list_when_missing(ini_settings: QSettings) -> None:
    out = load_rules("twitch", "acc-1", settings=ini_settings)
    assert out == []


def test_actions_rules_key_is_set_false_until_saved_even_if_rules_empty(
    ini_settings: QSettings,
) -> None:
    assert not actions_rules_key_is_set("tiktok", "app", settings=ini_settings)
    save_rules("tiktok", "app", [], settings=ini_settings)
    assert actions_rules_key_is_set("tiktok", "app", settings=ini_settings)


def test_rules_are_scoped_by_account_key(ini_settings: QSettings) -> None:
    platform = "twitch"
    a1 = "account-1"
    a2 = "account-2"

    save_rules(platform, a1, [_rule("r1")], settings=ini_settings)
    save_rules(platform, a2, [_rule("r2")], settings=ini_settings)

    out1 = load_rules(platform, a1, settings=ini_settings)
    out2 = load_rules(platform, a2, settings=ini_settings)

    assert [r.id for r in out1] == ["r1"]
    assert [r.id for r in out2] == ["r2"]


def test_store_uses_expected_key_and_ruleset_wrapper(ini_settings: QSettings) -> None:
    platform = "twitch"
    account_key = "acc-1"
    save_rules(platform, account_key, [_rule("r1")], settings=ini_settings)

    key = f"actions/{platform}/{account_key}/rules_json"
    text = ini_settings.value(key, "", str)
    assert isinstance(text, str) and text.strip()
    payload = json.loads(text)
    assert payload["schema_version"] == 1
    assert isinstance(payload["rules"], list) and payload["rules"]


@pytest.mark.parametrize(
    ("platform", "account_key"),
    [
        ("", "a"),
        ("  ", "a"),
        ("twitch", ""),
        ("twitch", "  "),
        ("twi/tch", "a"),
        ("twitch", "a/b"),
        ("twi\\tch", "a"),
        ("twitch", "a\\b"),
    ],
)
def test_validate_platform_and_account_key_non_empty(
    platform: str, account_key: str, ini_settings: QSettings
) -> None:
    with pytest.raises(ValueError):
        load_rules(platform, account_key, settings=ini_settings)
    with pytest.raises(ValueError):
        save_rules(platform, account_key, [], settings=ini_settings)
