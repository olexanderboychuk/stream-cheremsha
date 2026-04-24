import json

from stream_cheremsha.actions.models import RuleV1


def test_rule_v1_roundtrip_json_text_includes_schema_version_1():
    rule = RuleV1(
        id='rule-1',
        enabled=True,
        event={
            'type': 'chat_message',
            'params': {'platform': 'youtube'},
        },
        actions=[
            {
                'type': 'tts',
                'params': {'voice': 'uk-UA', 'text': 'hello'},
            }
        ],
    )

    text = rule.to_json_text()

    # JSON should be valid and include schema_version=1
    payload = json.loads(text)
    assert payload['schema_version'] == 1

    rule2 = RuleV1.from_json_text(text)
    assert rule2 == rule
