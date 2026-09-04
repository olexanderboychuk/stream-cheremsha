from __future__ import annotations

import json
from dataclasses import dataclass, replace

from PySide6.QtCore import QSettings

WEBCAM_FRAME_OVERLAY_CONFIG_SCHEMA_VERSION = 1
WEBCAM_FRAME_OVERLAY_CONFIG_QSETTINGS_KEY = "overlays/webcam_frame/main/config_json"
_WEBCAM_FRAME_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY = "overlays/webcam_frame/main/config_json_backup"

VALID_THEMES = frozenset({"neon_cyber", "synthwave", "toxic", "ice", "amber", "critical"})
VALID_INTENSITIES = frozenset({"low", "medium", "high"})
VALID_FRAME_STYLES = frozenset({"primary", "minimal", "tactical", "broadcast", "hologram"})


@dataclass(frozen=True, slots=True)
class WebcamFrameOverlayConfig:
    schema_version: int

    enabled: bool
    theme: str
    intensity: str
    frame_style: str
    scale_percent: int
    cam_label: str

    enable_status_indicator: bool
    enable_energy_flow: bool
    enable_breathing_glow: bool
    enable_light_sweep: bool
    enable_micro_glitch: bool
    enable_sparks: bool
    enable_crt: bool
    enable_boot_animation: bool
    enable_shutdown_animation: bool

    def replace(self, **kwargs: object) -> WebcamFrameOverlayConfig:
        return replace(self, **kwargs)


def webcam_frame_overlay_config_defaults() -> WebcamFrameOverlayConfig:
    return WebcamFrameOverlayConfig(
        schema_version=WEBCAM_FRAME_OVERLAY_CONFIG_SCHEMA_VERSION,
        enabled=True,
        theme="neon_cyber",
        intensity="medium",
        frame_style="primary",
        scale_percent=100,
        cam_label="CAM // 01",
        enable_status_indicator=True,
        enable_energy_flow=True,
        enable_breathing_glow=True,
        enable_light_sweep=True,
        enable_micro_glitch=True,
        enable_sparks=True,
        enable_crt=True,
        enable_boot_animation=True,
        enable_shutdown_animation=True,
    )


def _ensure_int(v: object, *, default: int) -> int:
    try:
        return int(v)  # type: ignore[arg-type]
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


def _validate_theme(v: object) -> str:
    s = _ensure_str(v, default="neon_cyber")
    return s if s in VALID_THEMES else "neon_cyber"


def _validate_intensity(v: object) -> str:
    s = _ensure_str(v, default="medium")
    return s if s in VALID_INTENSITIES else "medium"


def _validate_frame_style(v: object) -> str:
    s = _ensure_str(v, default="primary")
    return s if s in VALID_FRAME_STYLES else "primary"


def _validate_scale_percent(v: object) -> int:
    return max(40, min(250, _ensure_int(v, default=100)))


def _validate_cam_label(v: object) -> str:
    s = _ensure_str(v, default="CAM // 01")
    return s[:24]


def webcam_frame_overlay_config_from_json_text(text: str) -> WebcamFrameOverlayConfig:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("webcam_frame overlay config must be a JSON object")
    d = raw
    defaults = webcam_frame_overlay_config_defaults()
    return WebcamFrameOverlayConfig(
        schema_version=_ensure_int(d.get("schema_version"), default=defaults.schema_version),
        enabled=_ensure_bool(d.get("enabled"), default=defaults.enabled),
        theme=_validate_theme(d.get("theme")),
        intensity=_validate_intensity(d.get("intensity")),
        frame_style=_validate_frame_style(d.get("frame_style")),
        scale_percent=_validate_scale_percent(d.get("scale_percent")),
        cam_label=_validate_cam_label(d.get("cam_label")),
        enable_status_indicator=_ensure_bool(
            d.get("enable_status_indicator"), default=defaults.enable_status_indicator
        ),
        enable_energy_flow=_ensure_bool(
            d.get("enable_energy_flow"), default=defaults.enable_energy_flow
        ),
        enable_breathing_glow=_ensure_bool(
            d.get("enable_breathing_glow"), default=defaults.enable_breathing_glow
        ),
        enable_light_sweep=_ensure_bool(
            d.get("enable_light_sweep"), default=defaults.enable_light_sweep
        ),
        enable_micro_glitch=_ensure_bool(
            d.get("enable_micro_glitch"), default=defaults.enable_micro_glitch
        ),
        enable_sparks=_ensure_bool(d.get("enable_sparks"), default=defaults.enable_sparks),
        enable_crt=_ensure_bool(d.get("enable_crt"), default=defaults.enable_crt),
        enable_boot_animation=_ensure_bool(
            d.get("enable_boot_animation"), default=defaults.enable_boot_animation
        ),
        enable_shutdown_animation=_ensure_bool(
            d.get("enable_shutdown_animation"), default=defaults.enable_shutdown_animation
        ),
    )


def webcam_frame_overlay_config_to_public_dict(
    cfg: WebcamFrameOverlayConfig,
) -> dict[str, object]:
    return {
        "schema_version": int(cfg.schema_version),
        "enabled": bool(cfg.enabled),
        "theme": str(cfg.theme),
        "intensity": str(cfg.intensity),
        "frame_style": str(cfg.frame_style),
        "scale_percent": int(cfg.scale_percent),
        "cam_label": str(cfg.cam_label),
        "enable_status_indicator": bool(cfg.enable_status_indicator),
        "enable_energy_flow": bool(cfg.enable_energy_flow),
        "enable_breathing_glow": bool(cfg.enable_breathing_glow),
        "enable_light_sweep": bool(cfg.enable_light_sweep),
        "enable_micro_glitch": bool(cfg.enable_micro_glitch),
        "enable_sparks": bool(cfg.enable_sparks),
        "enable_crt": bool(cfg.enable_crt),
        "enable_boot_animation": bool(cfg.enable_boot_animation),
        "enable_shutdown_animation": bool(cfg.enable_shutdown_animation),
    }


def webcam_frame_overlay_config_to_json_text(cfg: WebcamFrameOverlayConfig) -> str:
    return json.dumps(
        webcam_frame_overlay_config_to_public_dict(cfg),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def load_webcam_frame_overlay_config(
    settings: QSettings | None = None,
) -> WebcamFrameOverlayConfig:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    raw = (s.value(WEBCAM_FRAME_OVERLAY_CONFIG_QSETTINGS_KEY, "", str) or "").strip()
    if not raw:
        return webcam_frame_overlay_config_defaults()
    try:
        return webcam_frame_overlay_config_from_json_text(raw)
    except (ValueError, TypeError, json.JSONDecodeError):
        bak = (s.value(_WEBCAM_FRAME_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, "", str) or "").strip()
        if bak:
            try:
                cfg = webcam_frame_overlay_config_from_json_text(bak)
            except (ValueError, TypeError, json.JSONDecodeError):
                return webcam_frame_overlay_config_defaults()
            s.setValue(
                WEBCAM_FRAME_OVERLAY_CONFIG_QSETTINGS_KEY,
                webcam_frame_overlay_config_to_json_text(cfg),
            )
            return cfg
        return webcam_frame_overlay_config_defaults()


def save_webcam_frame_overlay_config(
    cfg: WebcamFrameOverlayConfig,
    settings: QSettings | None = None,
) -> None:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    txt = webcam_frame_overlay_config_to_json_text(cfg)
    s.setValue(WEBCAM_FRAME_OVERLAY_CONFIG_QSETTINGS_KEY, txt)
    s.setValue(_WEBCAM_FRAME_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, txt)
    s.sync()
