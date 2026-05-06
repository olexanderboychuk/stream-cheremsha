import json

import pytest

from stream_cheremsha.actions.models import (
    RuleV1,
    normalize_ui_rules_layout_v1,
    rule_to_json_obj,
    ruleset_from_json_text,
    ruleset_to_json_text,
    ui_rules_layout_from_json_text,
)


def test_ruleset_roundtrip_v1_includes_schema_version_1() -> None:
    rule = RuleV1(
        id="rule-1",
        enabled=True,
        events=(
            {"type": "chat_keyword", "params": {"text": "hello", "match": "contains", "case_sensitive": False}},
        ),
        actions=[{"type": "play_sound", "params": {"file_path": r"C:\tmp\a.mp3"}}],
    )

    text = ruleset_to_json_text([rule])

    payload = json.loads(text)
    assert payload["schema_version"] == 1
    assert "schema_version" not in payload["rules"][0]

    out = ruleset_from_json_text(text)
    assert [rule_to_json_obj(r) for r in out] == [rule_to_json_obj(rule)]


def test_ruleset_rejects_unsupported_schema_version() -> None:
    with pytest.raises(ValueError, match="schema_version"):
        ruleset_from_json_text('{"schema_version":2,"rules":[]}')


def test_ruleset_rejects_non_object_json() -> None:
    with pytest.raises(ValueError, match="Ruleset JSON must be an object"):
        ruleset_from_json_text("[]")


def test_ruleset_rejects_invalid_json_text() -> None:
    with pytest.raises(ValueError, match="Ruleset JSON is invalid"):
        ruleset_from_json_text("{")


def test_rule_validation_mentions_action_index() -> None:
    with pytest.raises(ValueError, match=r"Rule actions\[0\]\.type is required"):
        ruleset_from_json_text('{"schema_version":1,"rules":[{"id":"r1","enabled":true,"event":{"type":"x","params":{}},"actions":[{"type":"","params":{}}]}]}')


def test_rule_allows_empty_actions_list() -> None:
    out = ruleset_from_json_text('{"schema_version":1,"rules":[{"id":"r1","enabled":true,"event":{"type":"x","params":{}},"actions":[]}]}')
    assert out[0].actions == []


def test_rule_name_roundtrip() -> None:
    rule = RuleV1(
        id="r1",
        enabled=True,
        events=({"type": "gift_received", "params": {"gift_name": "Rose", "min_count": 1}},),
        actions=[{"type": "play_sound", "params": {"file_path": "/x/a.mp3"}}],
        name="  Троянда  ",
    )
    text = ruleset_to_json_text([rule])
    out = ruleset_from_json_text(text)
    assert out[0].name == "Троянда"
    assert out[0].id == "r1"


def test_event_trigger_platform_roundtrip_non_default() -> None:
    rule = RuleV1(
        id="r1",
        enabled=True,
        events=(
            {
                "type": "chat_keyword",
                "platform": "tiktok",
                "params": {"text": "hi", "match": "contains", "case_sensitive": False},
            },
        ),
        actions=[],
    )
    text = ruleset_to_json_text([rule])
    out = ruleset_from_json_text(text)
    assert out[0].events[0].get("platform") == "tiktok"


def test_event_default_platform_omitted_from_json() -> None:
    rule = RuleV1(
        id="r1",
        enabled=True,
        events=(
            {"type": "chat_keyword", "params": {"text": "hi", "match": "contains", "case_sensitive": False}},
        ),
        actions=[],
    )
    obj = rule_to_json_obj(rule)
    assert "platform" not in obj["event"]


def test_ruleset_multi_events_roundtrip_uses_events_array() -> None:
    rule = RuleV1(
        id="r2",
        enabled=True,
        events=(
            {"type": "chat_keyword", "params": {"text": "a", "match": "contains", "case_sensitive": False}},
            {"type": "chat_keyword", "params": {"text": "b", "match": "contains", "case_sensitive": False}},
        ),
        actions=[{"type": "play_sound", "params": {"file_path": "/x/a.mp3"}}],
    )
    text = ruleset_to_json_text([rule])
    out = ruleset_from_json_text(text)
    assert len(out[0].events) == 2
    assert "events" in json.loads(text)["rules"][0]
    assert "event" not in json.loads(text)["rules"][0]


def test_ruleset_roundtrip_preserves_ui_layout() -> None:
    rule = RuleV1(
        id="rule-1",
        enabled=True,
        events=(
            {"type": "chat_keyword", "params": {"text": "hello", "match": "contains", "case_sensitive": False}},
        ),
        actions=[{"type": "play_sound", "params": {"file_path": r"C:\tmp\a.mp3"}}],
    )
    layout = ui_rules_layout_from_json_text(
        '{"schema_version":1,"tree":[{"kind":"folder","id":"f1","name":"Group","expanded":false,"children":[{"kind":"rule","rule_id":"rule-1"}]}]}'
    )
    text = ruleset_to_json_text([rule], ui_layout=layout)
    payload = json.loads(text)
    assert payload["schema_version"] == 1
    assert "ui_layout" in payload
    assert payload["ui_layout"]["tree"][0]["kind"] == "folder"

    out = ruleset_from_json_text(text)
    assert len(out) == 1
    assert out[0].id == "rule-1"


def test_normalize_ui_layout_drops_unknown_rule_refs() -> None:
    rule = RuleV1(
        id="rA",
        enabled=True,
        events=({"type": "chat_keyword", "params": {"text": "x", "match": "contains", "case_sensitive": False}},),
        actions=[],
    )
    layout = ui_rules_layout_from_json_text(
        '{"schema_version":1,"tree":[{"kind":"rule","rule_id":"missing"},{"kind":"rule","rule_id":"rA"}]}'
    )
    norm = normalize_ui_rules_layout_v1(layout, [rule])
    assert norm is not None
    assert norm["tree"] == [{"kind": "rule", "rule_id": "rA"}]


