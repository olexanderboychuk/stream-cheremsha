from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Self


@dataclass(frozen=True, slots=True)
class RuleV1:
    """Schema v1 rule for mapping events -> actions.

    Minimal and extensible container with JSON round-trip utilities.
    """

    id: str
    enabled: bool
    event: Mapping[str, Any]
    actions: list[Mapping[str, Any]]

    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "enabled": self.enabled,
            "event": dict(self.event),
            "actions": [dict(a) for a in self.actions],
        }

    def to_json_text(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Self:
        schema_version = payload.get("schema_version")
        if schema_version != 1:
            raise ValueError(f"Unsupported schema_version: {schema_version}")

        return cls(
            id=str(payload["id"]),
            enabled=bool(payload["enabled"]),
            event=payload["event"],
            actions=list(payload["actions"]),
        )

    @classmethod
    def from_json_text(cls, text: str) -> Self:
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise TypeError("Rule JSON must decode to an object")
        return cls.from_dict(payload)
