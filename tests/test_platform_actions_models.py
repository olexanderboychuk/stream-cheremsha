import json

import pytest

from stream_cheremsha.actions.models import RuleV1, rule_to_json_obj, ruleset_from_json_text, ruleset_to_json_text


def test_ruleset_roundtrip_v1_includes_schema_version_1() -> None:
    rule = RuleV1(
        id="rule-1",
        enabled=True,
        event={"type": "chat_keyword", "params": {"text": "hello", "match": "contains", "case_sensitive": False}},
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
        event={"type": "gift_received", "params": {"gift_name": "Rose", "min_count": 1}},
        actions=[{"type": "play_sound", "params": {"file_path": "/x/a.mp3"}}],
        name="  Троянда  ",
    )
    text = ruleset_to_json_text([rule])
    out = ruleset_from_json_text(text)
    assert out[0].name == "Троянда"
    assert out[0].id == "r1"

