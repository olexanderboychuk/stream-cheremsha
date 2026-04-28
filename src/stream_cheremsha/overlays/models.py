from __future__ import annotations

import re
from typing import Any

_INSTANCE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")


def normalize_instance_id(v: str) -> str:
    s = (v or "").strip()
    if not s:
        return "default"
    if not _INSTANCE_RE.match(s):
        raise ValueError("Invalid overlay instance id")
    return s


def overlays_initial_state_msg(state: dict[str, Any]) -> dict[str, Any]:
    return {"op": "initial_state", "state": dict(state)}


def overlays_patch_msg(patch: dict[str, Any]) -> dict[str, Any]:
    return {"op": "patch", "patch": dict(patch)}

