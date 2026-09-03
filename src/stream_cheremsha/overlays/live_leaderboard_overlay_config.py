from __future__ import annotations

import json
from dataclasses import dataclass, replace

from PySide6.QtCore import QSettings

from stream_cheremsha.overlays.live_leaderboard_rotation import (
    ALL_SCENES,
    ALL_SOURCES,
    SCENE_ARENA,
    SCENE_ENERGY_NETWORK,
    SCENE_HALL_OF_FAME,
    SOURCE_COMMENTERS,
    SOURCE_CONTRIBUTORS,
    SOURCE_GIFTERS,
    SOURCE_LIKERS,
    SOURCE_SHARERS,
    RotationStep,
)

LIVE_LEADERBOARD_OVERLAY_CONFIG_SCHEMA_VERSION = 1
LIVE_LEADERBOARD_OVERLAY_CONFIG_QSETTINGS_KEY = "overlays/live_leaderboard/main/config_json"
_LIVE_LEADERBOARD_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY = (
    "overlays/live_leaderboard/main/config_json_backup"
)


def _default_sequence() -> list[dict[str, object]]:
    return [
        {"source_id": SOURCE_LIKERS, "scene_id": SCENE_HALL_OF_FAME, "duration_sec": 8},
        {"source_id": SOURCE_LIKERS, "scene_id": SCENE_ARENA, "duration_sec": 6},
        {"source_id": SOURCE_LIKERS, "scene_id": SCENE_ENERGY_NETWORK, "duration_sec": 6},
        {"source_id": SOURCE_GIFTERS, "scene_id": SCENE_HALL_OF_FAME, "duration_sec": 8},
        {"source_id": SOURCE_GIFTERS, "scene_id": SCENE_ARENA, "duration_sec": 6},
        {"source_id": SOURCE_SHARERS, "scene_id": SCENE_HALL_OF_FAME, "duration_sec": 8},
        {"source_id": SOURCE_COMMENTERS, "scene_id": SCENE_HALL_OF_FAME, "duration_sec": 8},
        {"source_id": SOURCE_CONTRIBUTORS, "scene_id": SCENE_HALL_OF_FAME, "duration_sec": 8},
    ]


@dataclass(frozen=True, slots=True)
class LiveLeaderboardOverlayConfig:
    schema_version: int

    enabled: bool

    enable_likers: bool
    enable_gifters: bool
    enable_sharers: bool
    enable_commenters: bool
    enable_contributors: bool

    enable_hall_of_fame: bool
    enable_arena: bool
    enable_energy_network: bool

    sequence_json: str

    top_n: int
    period: str

    transition: str
    animation_intensity: str
    enable_rank_change_anim: bool
    enable_particles: bool
    enable_crt: bool

    scale_percent: int
    accent_color: str

    weight_like: int
    weight_gift_coin: int
    weight_share: int
    weight_comment: int

    def replace(self, **kwargs: object) -> LiveLeaderboardOverlayConfig:
        return replace(self, **kwargs)


def live_leaderboard_overlay_config_defaults() -> LiveLeaderboardOverlayConfig:
    return LiveLeaderboardOverlayConfig(
        schema_version=LIVE_LEADERBOARD_OVERLAY_CONFIG_SCHEMA_VERSION,
        enabled=True,
        enable_likers=True,
        enable_gifters=True,
        enable_sharers=True,
        enable_commenters=True,
        enable_contributors=True,
        enable_hall_of_fame=True,
        enable_arena=True,
        enable_energy_network=True,
        sequence_json=json.dumps(_default_sequence(), ensure_ascii=False),
        top_n=10,
        period="this_stream",
        transition="glitch_morph",
        animation_intensity="medium",
        enable_rank_change_anim=True,
        enable_particles=True,
        enable_crt=True,
        scale_percent=100,
        accent_color="#00ffff",
        weight_like=1,
        weight_gift_coin=10,
        weight_share=50,
        weight_comment=5,
    )


def _ensure_int(v: object, *, default: int) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _ensure_float(v: object, *, default: float) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _ensure_bool(v: object, *, default: bool) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("1", "true", "yes", "on"):
            return True
        if s in ("0", "false", "no", "off"):
            return False
    return default


def _ensure_str(v: object, *, default: str) -> str:
    s = str(v or "").strip()
    return s if s else default


def _ensure_hex_color(v: object, *, default: str) -> str:
    s = str(v or "").strip()
    if s.startswith("#") and len(s) in (4, 7, 9):
        return s
    return default


def _validate_animation_intensity(v: object) -> str:
    s = _ensure_str(v, default="medium")
    return s if s in {"low", "medium", "high"} else "medium"


def _validate_transition(v: object) -> str:
    s = _ensure_str(v, default="glitch_morph")
    valid = {"glitch_morph", "digital_dissolve", "scan", "energy_burst", "slide", "fade"}
    return s if s in valid else "glitch_morph"


def _validate_period(v: object) -> str:
    # v1 only supports this_stream; keep the argument for API symmetry with other validators.
    del v
    return "this_stream"


def _validate_scale_percent(v: object) -> int:
    return max(40, min(250, _ensure_int(v, default=100)))


def _validate_top_n(v: object) -> int:
    return max(1, min(10, _ensure_int(v, default=10)))


def _normalize_sequence_list(raw: object) -> list[dict[str, object]]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            return list(_default_sequence())
    if not isinstance(raw, list):
        return list(_default_sequence())
    out: list[dict[str, object]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        src = str(item.get("source_id") or item.get("source") or "").strip().lower()
        scene = str(item.get("scene_id") or item.get("scene") or "").strip().lower()
        if src not in ALL_SOURCES or scene not in ALL_SCENES:
            continue
        dur = max(
            1.0,
            min(
                120.0, _ensure_float(item.get("duration_sec", item.get("duration", 8)), default=8.0)
            ),
        )
        out.append({"source_id": src, "scene_id": scene, "duration_sec": dur})
    return out if out else list(_default_sequence())


def _validate_sequence_json(v: object) -> str:
    seq = _normalize_sequence_list(v)
    return json.dumps(seq, ensure_ascii=False)


def parse_sequence_steps(cfg: LiveLeaderboardOverlayConfig) -> list[RotationStep]:
    seq = _normalize_sequence_list(cfg.sequence_json)
    return [
        RotationStep(
            source_id=str(item["source_id"]),
            scene_id=str(item["scene_id"]),
            duration_sec=float(item["duration_sec"]),
        )
        for item in seq
    ]


def enabled_sources_from_config(cfg: LiveLeaderboardOverlayConfig) -> set[str]:
    out: set[str] = set()
    if cfg.enable_likers:
        out.add(SOURCE_LIKERS)
    if cfg.enable_gifters:
        out.add(SOURCE_GIFTERS)
    if cfg.enable_sharers:
        out.add(SOURCE_SHARERS)
    if cfg.enable_commenters:
        out.add(SOURCE_COMMENTERS)
    if cfg.enable_contributors:
        out.add(SOURCE_CONTRIBUTORS)
    return out or {SOURCE_LIKERS}


def enabled_scenes_from_config(cfg: LiveLeaderboardOverlayConfig) -> set[str]:
    out: set[str] = set()
    if cfg.enable_hall_of_fame:
        out.add(SCENE_HALL_OF_FAME)
    if cfg.enable_arena:
        out.add(SCENE_ARENA)
    if cfg.enable_energy_network:
        out.add(SCENE_ENERGY_NETWORK)
    return out or {SCENE_HALL_OF_FAME}


def ensure_enabled_sources_in_sequence(
    cfg: LiveLeaderboardOverlayConfig,
) -> LiveLeaderboardOverlayConfig:
    """Append Hall of Fame steps for enabled sources missing from the rotation sequence.

    Source toggles only filter the show; without sequence entries those sources never appear.
    """
    enabled = enabled_sources_from_config(cfg)
    steps = parse_sequence_steps(cfg)
    present = {s.source_id for s in steps}
    missing = [src for src in ALL_SOURCES if src in enabled and src not in present]
    if not missing:
        return cfg
    seq = [
        {
            "source_id": s.source_id,
            "scene_id": s.scene_id,
            "duration_sec": float(s.duration_sec),
        }
        for s in steps
    ]
    for src in missing:
        seq.append({"source_id": src, "scene_id": SCENE_HALL_OF_FAME, "duration_sec": 8.0})
    return cfg.replace(sequence_json=json.dumps(seq, ensure_ascii=False))


def migrate_live_leaderboard_overlay_config(
    cfg: LiveLeaderboardOverlayConfig,
) -> LiveLeaderboardOverlayConfig:
    """Repair legacy configs where optional sources were off and absent from the sequence."""
    seq_sources = {s.source_id for s in parse_sequence_steps(cfg)}
    optional = {SOURCE_SHARERS, SOURCE_COMMENTERS, SOURCE_CONTRIBUTORS}
    patched = cfg
    if not (optional & seq_sources) and not (
        cfg.enable_sharers or cfg.enable_commenters or cfg.enable_contributors
    ):
        # Classic old defaults: optional sources disabled and never scheduled.
        patched = cfg.replace(
            enable_sharers=True,
            enable_commenters=True,
            enable_contributors=True,
        )
    return ensure_enabled_sources_in_sequence(patched)


def live_leaderboard_overlay_config_from_json_text(text: str) -> LiveLeaderboardOverlayConfig:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("live_leaderboard overlay config must be a JSON object")
    d = raw
    defaults = live_leaderboard_overlay_config_defaults()
    seq_raw = d.get("sequence", d.get("sequence_json", defaults.sequence_json))
    cfg = LiveLeaderboardOverlayConfig(
        schema_version=_ensure_int(d.get("schema_version"), default=defaults.schema_version),
        enabled=_ensure_bool(d.get("enabled"), default=defaults.enabled),
        enable_likers=_ensure_bool(d.get("enable_likers"), default=defaults.enable_likers),
        enable_gifters=_ensure_bool(d.get("enable_gifters"), default=defaults.enable_gifters),
        enable_sharers=_ensure_bool(d.get("enable_sharers"), default=defaults.enable_sharers),
        enable_commenters=_ensure_bool(
            d.get("enable_commenters"), default=defaults.enable_commenters
        ),
        enable_contributors=_ensure_bool(
            d.get("enable_contributors"), default=defaults.enable_contributors
        ),
        enable_hall_of_fame=_ensure_bool(
            d.get("enable_hall_of_fame"), default=defaults.enable_hall_of_fame
        ),
        enable_arena=_ensure_bool(d.get("enable_arena"), default=defaults.enable_arena),
        enable_energy_network=_ensure_bool(
            d.get("enable_energy_network"), default=defaults.enable_energy_network
        ),
        sequence_json=_validate_sequence_json(seq_raw),
        top_n=_validate_top_n(d.get("top_n")),
        period=_validate_period(d.get("period")),
        transition=_validate_transition(d.get("transition")),
        animation_intensity=_validate_animation_intensity(d.get("animation_intensity")),
        enable_rank_change_anim=_ensure_bool(
            d.get("enable_rank_change_anim"), default=defaults.enable_rank_change_anim
        ),
        enable_particles=_ensure_bool(d.get("enable_particles"), default=defaults.enable_particles),
        enable_crt=_ensure_bool(d.get("enable_crt"), default=defaults.enable_crt),
        scale_percent=_validate_scale_percent(d.get("scale_percent")),
        accent_color=_ensure_hex_color(d.get("accent_color"), default=defaults.accent_color),
        weight_like=max(0, _ensure_int(d.get("weight_like"), default=defaults.weight_like)),
        weight_gift_coin=max(
            0, _ensure_int(d.get("weight_gift_coin"), default=defaults.weight_gift_coin)
        ),
        weight_share=max(0, _ensure_int(d.get("weight_share"), default=defaults.weight_share)),
        weight_comment=max(
            0, _ensure_int(d.get("weight_comment"), default=defaults.weight_comment)
        ),
    )
    return migrate_live_leaderboard_overlay_config(cfg)


def live_leaderboard_overlay_config_to_public_dict(
    cfg: LiveLeaderboardOverlayConfig,
) -> dict[str, object]:
    return {
        "schema_version": int(cfg.schema_version),
        "enabled": bool(cfg.enabled),
        "enable_likers": bool(cfg.enable_likers),
        "enable_gifters": bool(cfg.enable_gifters),
        "enable_sharers": bool(cfg.enable_sharers),
        "enable_commenters": bool(cfg.enable_commenters),
        "enable_contributors": bool(cfg.enable_contributors),
        "enable_hall_of_fame": bool(cfg.enable_hall_of_fame),
        "enable_arena": bool(cfg.enable_arena),
        "enable_energy_network": bool(cfg.enable_energy_network),
        "sequence": _normalize_sequence_list(cfg.sequence_json),
        "sequence_json": str(cfg.sequence_json),
        "top_n": int(cfg.top_n),
        "period": str(cfg.period),
        "transition": str(cfg.transition),
        "animation_intensity": str(cfg.animation_intensity),
        "enable_rank_change_anim": bool(cfg.enable_rank_change_anim),
        "enable_particles": bool(cfg.enable_particles),
        "enable_crt": bool(cfg.enable_crt),
        "scale_percent": int(cfg.scale_percent),
        "accent_color": str(cfg.accent_color),
        "weight_like": int(cfg.weight_like),
        "weight_gift_coin": int(cfg.weight_gift_coin),
        "weight_share": int(cfg.weight_share),
        "weight_comment": int(cfg.weight_comment),
    }


def live_leaderboard_overlay_config_to_json_text(cfg: LiveLeaderboardOverlayConfig) -> str:
    return json.dumps(
        live_leaderboard_overlay_config_to_public_dict(cfg),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def load_live_leaderboard_overlay_config(
    settings: QSettings | None = None,
) -> LiveLeaderboardOverlayConfig:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    raw = (s.value(LIVE_LEADERBOARD_OVERLAY_CONFIG_QSETTINGS_KEY, "", str) or "").strip()
    if not raw:
        return live_leaderboard_overlay_config_defaults()
    try:
        cfg = live_leaderboard_overlay_config_from_json_text(raw)
    except (ValueError, TypeError, json.JSONDecodeError):
        bak = (
            s.value(_LIVE_LEADERBOARD_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, "", str) or ""
        ).strip()
        if bak:
            try:
                cfg = live_leaderboard_overlay_config_from_json_text(bak)
                s.setValue(
                    LIVE_LEADERBOARD_OVERLAY_CONFIG_QSETTINGS_KEY,
                    live_leaderboard_overlay_config_to_json_text(cfg),
                )
                return cfg
            except (ValueError, TypeError, json.JSONDecodeError):
                pass
        return live_leaderboard_overlay_config_defaults()
    # Persist migration (legacy optional sources / missing sequence steps).
    repaired = live_leaderboard_overlay_config_to_json_text(cfg)
    if repaired.strip() != raw:
        save_live_leaderboard_overlay_config(cfg, s)
    return cfg


def save_live_leaderboard_overlay_config(
    cfg: LiveLeaderboardOverlayConfig,
    settings: QSettings | None = None,
) -> None:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    txt = live_leaderboard_overlay_config_to_json_text(cfg)
    s.setValue(LIVE_LEADERBOARD_OVERLAY_CONFIG_QSETTINGS_KEY, txt)
    s.setValue(_LIVE_LEADERBOARD_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, txt)
    s.sync()
