from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, NotRequired, TypedDict

from stream_cheremsha.actions.trigger_meta import (
    ALLOWED_TRIGGER_PLATFORMS,
    default_trigger_platform_for_event_type,
    normalize_trigger_platform,
)


class TypedBlob(TypedDict):
    type: str
    params: dict[str, Any]
    platform: NotRequired[str]


_RULE_NAME_MAX_LEN = 200
_FOLDER_NAME_MAX_LEN = 120


def _event_dict_for_json(e: TypedBlob) -> dict[str, Any]:
    d: dict[str, Any] = {"type": e["type"], "params": dict(e["params"])}
    plat_raw = e.get("platform")
    if isinstance(plat_raw, str) and plat_raw.strip():
        p = plat_raw.strip().lower()
        if p in ALLOWED_TRIGGER_PLATFORMS:
            default = default_trigger_platform_for_event_type(e["type"])
            if p != default:
                d["platform"] = p
    return d


def _parse_event_blob(ev: Mapping[str, Any], *, index: int | None = None) -> TypedBlob:
    idx = "" if index is None else f"[{index}]"
    ev_t = ev.get("type")
    if not isinstance(ev_t, str) or not ev_t.strip():
        raise ValueError(f"Rule event{idx}.type is required")
    ev_p = ev.get("params", {})
    if not isinstance(ev_p, Mapping):
        raise ValueError(f"Rule event{idx}.params must be an object")
    blob: TypedBlob = {"type": ev_t.strip(), "params": dict(ev_p)}
    plat = normalize_trigger_platform(ev.get("platform"))
    if plat is not None:
        blob["platform"] = plat
    return blob


@dataclass(frozen=True, slots=True)
class RuleV1:
    """Schema v1 rule: multiple OR triggers in `events`, one shared `actions` list."""

    id: str
    enabled: bool
    events: tuple[TypedBlob, ...]
    actions: list[TypedBlob]
    name: str = ""


class UiFolderNode(TypedDict):
    kind: str  # "folder"
    id: str
    name: str
    expanded: NotRequired[bool]
    children: list[UiTreeNode]


class UiRuleRefNode(TypedDict):
    kind: str  # "rule"
    rule_id: str


UiTreeNode = UiFolderNode | UiRuleRefNode


class UiRulesLayoutV1(TypedDict):
    schema_version: int
    tree: list[UiTreeNode]


def _strip_ui_folder_name(raw: object) -> str:
    if not isinstance(raw, str):
        return ""
    return raw.strip()[:_FOLDER_NAME_MAX_LEN]


def _parse_ui_rule_ref(obj: Mapping[str, Any], *, index: int | None = None) -> UiRuleRefNode:
    idx = "" if index is None else f"[{index}]"
    rid = obj.get("rule_id")
    if not isinstance(rid, str) or not rid.strip():
        raise ValueError(f"ui_layout.tree rule node{idx}.rule_id is required")
    return {"kind": "rule", "rule_id": rid.strip()}


def _parse_ui_folder(
    obj: Mapping[str, Any], *, index: int | None = None, depth: int
) -> UiFolderNode:
    if depth > 8:
        raise ValueError("ui_layout.tree folders are nested too deeply (max depth 8)")
    idx = "" if index is None else f"[{index}]"
    fid = obj.get("id")
    if not isinstance(fid, str) or not fid.strip():
        raise ValueError(f"ui_layout.tree folder node{idx}.id is required")
    name = _strip_ui_folder_name(obj.get("name"))
    if not name:
        raise ValueError(f"ui_layout.tree folder node{idx}.name is required")

    expanded_raw = obj.get("expanded", True)
    expanded = True if not isinstance(expanded_raw, bool) else expanded_raw

    ch_raw = obj.get("children")
    if ch_raw is None:
        ch_raw = []
    if not isinstance(ch_raw, list):
        raise ValueError(f"ui_layout.tree folder node{idx}.children must be a list")

    children: list[UiTreeNode] = []
    for i, item in enumerate(ch_raw):
        children.append(_parse_ui_tree_node(item, index=i, depth=depth + 1))

    out: UiFolderNode = {
        "kind": "folder",
        "id": fid.strip(),
        "name": name,
        "children": children,
    }
    if expanded is not True:
        out["expanded"] = expanded
    return out


def _parse_ui_tree_node(obj: object, *, index: int | None = None, depth: int) -> UiTreeNode:
    idx = "" if index is None else f"[{index}]"
    if not isinstance(obj, Mapping):
        raise ValueError(f"ui_layout.tree node{idx} must be an object")
    kind = obj.get("kind")
    if kind == "rule":
        return _parse_ui_rule_ref(obj, index=index)
    if kind == "folder":
        return _parse_ui_folder(obj, index=index, depth=depth)
    raise ValueError(f"ui_layout.tree node{idx}.kind must be folder or rule")


def ui_rules_layout_from_json_obj(obj: Mapping[str, Any]) -> UiRulesLayoutV1:
    sv = obj.get("schema_version")
    if sv != 1:
        raise ValueError(f"Unsupported ui_layout.schema_version: {sv}")
    tr = obj.get("tree")
    if not isinstance(tr, list):
        raise ValueError("ui_layout.tree must be a list")
    tree: list[UiTreeNode] = []
    for i, item in enumerate(tr):
        tree.append(_parse_ui_tree_node(item, index=i, depth=0))
    return {"schema_version": 1, "tree": tree}


def ui_rules_layout_from_json_text(text: str) -> UiRulesLayoutV1:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"ui_layout JSON is invalid: {e.msg}") from e
    if not isinstance(raw, Mapping):
        raise ValueError("ui_layout JSON must be an object")
    return ui_rules_layout_from_json_obj(raw)


def ui_rules_layout_to_json_obj(layout: UiRulesLayoutV1) -> dict[str, Any]:
    def folder_dict(n: UiFolderNode) -> dict[str, Any]:
        out_f: dict[str, Any] = {
            "children": [node_dict(ch) for ch in n["children"]],
            "id": n["id"],
            "kind": "folder",
            "name": n["name"],
        }
        exp = n.get("expanded", True)
        if exp is not True:
            out_f["expanded"] = exp
        return out_f

    def rule_dict(n: UiRuleRefNode) -> dict[str, Any]:
        return {"kind": "rule", "rule_id": n["rule_id"]}

    def node_dict(n: UiTreeNode) -> dict[str, Any]:
        if n["kind"] == "folder":
            return folder_dict(n)
        return rule_dict(n)

    return {"schema_version": 1, "tree": [node_dict(n) for n in layout["tree"]]}


def ui_rules_layout_to_json_text(layout: UiRulesLayoutV1) -> str:
    payload = ui_rules_layout_to_json_obj(layout)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def normalize_ui_rules_layout_v1(
    layout: UiRulesLayoutV1 | None, rules: list[RuleV1]
) -> UiRulesLayoutV1 | None:
    """Drop stale rule refs / folders, dedupe rule ids, append missing rules (stable).

    Returns None when there is nothing meaningful to persist (no folders and default ordering).
    """
    ids_in_order: list[str] = [
        r.id.strip() for r in rules if isinstance(r.id, str) and r.id.strip()
    ]
    id_set = set(ids_in_order)

    def normalize_children(children: list[UiTreeNode]) -> tuple[list[UiTreeNode], list[str]]:
        out_children: list[UiTreeNode] = []
        emitted: list[str] = []
        seen_folder_ids: set[str] = set()
        for node in children:
            if node["kind"] == "rule":
                rid = node["rule_id"].strip()
                if rid not in id_set:
                    continue
                if rid in emitted:
                    continue
                out_children.append({"kind": "rule", "rule_id": rid})
                emitted.append(rid)
                continue

            fid = node["id"].strip()
            if not fid or fid in seen_folder_ids:
                continue
            seen_folder_ids.add(fid)
            nested, nested_emitted = normalize_children(list(node["children"]))
            name = _strip_ui_folder_name(node["name"]) or "Folder"
            folder_out: UiFolderNode = {
                "kind": "folder",
                "id": fid,
                "name": name,
                "children": nested,
            }
            exp = node.get("expanded", True)
            if exp is not True:
                folder_out["expanded"] = exp
            out_children.append(folder_out)
            emitted.extend(nested_emitted)

        return out_children, emitted

    base_layout: UiRulesLayoutV1 = {"schema_version": 1, "tree": []} if layout is None else layout
    tree2, emitted = normalize_children(list(base_layout["tree"]))
    missing = [rid for rid in ids_in_order if rid not in set(emitted)]
    tail_rules: list[UiRuleRefNode] = [{"kind": "rule", "rule_id": rid} for rid in missing]
    tree3 = tree2 + tail_rules

    has_folder = any(n["kind"] == "folder" for n in tree3)
    if not has_folder and tail_rules == [{"kind": "rule", "rule_id": rid} for rid in ids_in_order]:
        return None

    return {"schema_version": 1, "tree": tree3}


def default_ui_rules_layout_v1(rules: list[RuleV1]) -> UiRulesLayoutV1:
    return {
        "schema_version": 1,
        "tree": [
            {"kind": "rule", "rule_id": r.id.strip()}
            for r in rules
            if isinstance(r.id, str) and r.id.strip()
        ],
    }


def new_ui_folder_id() -> str:
    return str(uuid.uuid4())


def rule_to_json_obj(rule: RuleV1) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": rule.id,
        "enabled": rule.enabled,
        "actions": [{"type": a["type"], "params": dict(a["params"])} for a in rule.actions],
    }
    if len(rule.events) == 1:
        e = rule.events[0]
        out["event"] = _event_dict_for_json(e)
    else:
        out["events"] = [_event_dict_for_json(e) for e in rule.events]
    if rule.name.strip():
        out["name"] = rule.name.strip()
    return out


def rule_from_json_obj(obj: Mapping[str, Any]) -> RuleV1:
    if not isinstance(obj, Mapping):
        raise ValueError("Rule must be an object")

    rid = obj.get("id")
    if not isinstance(rid, str) or not rid.strip():
        raise ValueError("Rule id is required")

    enabled = obj.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError("Rule enabled must be boolean")

    events_raw = obj.get("events")
    events_list: list[TypedBlob] = []
    if isinstance(events_raw, list) and len(events_raw) > 0:
        for i, item in enumerate(events_raw):
            if not isinstance(item, Mapping):
                raise ValueError(f"Rule events[{i}] must be an object")
            events_list.append(_parse_event_blob(item, index=i))
    else:
        ev = obj.get("event")
        if not isinstance(ev, Mapping):
            raise ValueError("Rule event must be an object (or provide non-empty events[])")
        events_list.append(_parse_event_blob(ev))

    acts = obj.get("actions")
    if acts is None:
        acts = []
    if not isinstance(acts, list):
        raise ValueError("Rule actions must be a list")
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

    name_raw = obj.get("name", "")
    if not isinstance(name_raw, str):
        name_raw = ""
    name = name_raw.strip()[:_RULE_NAME_MAX_LEN]

    return RuleV1(
        id=rid.strip(),
        enabled=enabled,
        events=tuple(events_list),
        actions=actions,
        name=name,
    )


def ruleset_to_json_text(rules: list[RuleV1], *, ui_layout: UiRulesLayoutV1 | None = None) -> str:
    payload: dict[str, Any] = {"schema_version": 1, "rules": [rule_to_json_obj(r) for r in rules]}
    if ui_layout is not None:
        payload["ui_layout"] = ui_rules_layout_to_json_obj(ui_layout)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def ruleset_from_json_text(text: str) -> list[RuleV1]:
    rules, _layout = ruleset_bundle_from_json_text(text)
    return rules


def ruleset_bundle_from_json_text(text: str) -> tuple[list[RuleV1], UiRulesLayoutV1 | None]:
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
    rules = [rule_from_json_obj(r) for r in rr]

    ui_raw = raw.get("ui_layout")
    if ui_raw is None:
        return rules, None
    if not isinstance(ui_raw, Mapping):
        raise ValueError("Ruleset ui_layout must be an object")
    layout = ui_rules_layout_from_json_obj(ui_raw)
    layout2 = normalize_ui_rules_layout_v1(layout, rules)
    return rules, layout2
