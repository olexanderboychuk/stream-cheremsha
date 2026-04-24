from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, TypedDict


class TypedBlob(TypedDict):
    type: str
    params: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RuleV1:
    """Schema v1 rule for mapping events -> actions (no wrapper metadata)."""

    id: str
    enabled: bool
    event: TypedBlob
    actions: list[TypedBlob]


def rule_to_json_obj(rule: RuleV1) -> dict[str, Any]:
    return {
        "id": rule.id,
        "enabled": rule.enabled,
        "event": {"type": rule.event["type"], "params": dict(rule.event["params"])},
        "actions": [
            {"type": a["type"], "params": dict(a["params"])}
            for a in rule.actions
        ],
    }


def rule_from_json_obj(obj: Mapping[str, Any]) -> RuleV1:
    if not isinstance(obj, Mapping):
        raise ValueError("Rule must be an object")

    rid = obj.get("id")
    if not isinstance(rid, str) or not rid.strip():
        raise ValueError("Rule id is required")

    enabled = obj.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError("Rule enabled must be boolean")

    ev = obj.get("event")
    if not isinstance(ev, Mapping):
        raise ValueError("Rule event must be an object")
    ev_t = ev.get("type")
    if not isinstance(ev_t, str) or not ev_t.strip():
        raise ValueError("Rule event.type is required")
    ev_p = ev.get("params", {})
    if not isinstance(ev_p, Mapping):
        raise ValueError("Rule event.params must be an object")
    event: TypedBlob = {"type": ev_t, "params": dict(ev_p)}

    acts = obj.get("actions")
    if not isinstance(acts, list) or not acts:
        raise ValueError("Rule actions must be a non-empty list")
    actions: list[TypedBlob] = []
    for i, a in enumerate(acts):
        if not isinstance(a, Mapping):
            raise ValueError(f"Rule actions[{i}] must be an object")
        a_t = a.get("type")
        if not isinstance(a_t, str) or not a_t.strip():
            raise ValueError(f"Rule actions[{i}].type is required")
        a_p = a.get("params", {})
        if not isinstance(a_p, Mapping):
            raise ValueError(f"Rule actions[{i}].params must be an object")
        actions.append({"type": a_t, "params": dict(a_p)})

    return RuleV1(id=rid.strip(), enabled=enabled, event=event, actions=actions)


def ruleset_to_json_text(rules: list[RuleV1]) -> str:
    payload = {"schema_version": 1, "rules": [rule_to_json_obj(r) for r in rules]}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def ruleset_from_json_text(text: str) -> list[RuleV1]:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Ruleset JSON is invalid: {e.msg}") from e
    if not isinstance(raw, Mapping):
        raise ValueError("Ruleset JSON must be an object")
    sv = raw.get("schema_version")
    if sv != 1:
        raise ValueError(f"Unsupported schema_version: {sv}")
    rr = raw.get("rules")
    if not isinstance(rr, list):
        raise ValueError("Ruleset rules must be a list")
    return [rule_from_json_obj(r) for r in rr]
