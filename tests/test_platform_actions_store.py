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

    out = ruleset_from_json_text(text)
    assert [rule_to_json_obj(r) for r in out] == [rule_to_json_obj(rule)]


def test_ruleset_rejects_unsupported_schema_version() -> None:
    with pytest.raises(ValueError, match="schema_version"):
        ruleset_from_json_text('{"schema_version":2,"rules":[]}')


def test_ruleset_rejects_non_object_json() -> None:
    with pytest.raises(ValueError, match="Ruleset JSON must be an object"):
        ruleset_from_json_text("[]")
