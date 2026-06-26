from __future__ import annotations

import json
from dataclasses import dataclass, replace

from PySide6.QtCore import QSettings

from stream_cheremsha.overlays.stream_pet_presets import (
    STREAM_PET_PRESETS,
    resolve_stream_pet_appearance,
    stream_pet_appearance_to_dict,
    stream_pet_preset_appearance,
)

STREAM_PET_OVERLAY_CONFIG_SCHEMA_VERSION = 3
STREAM_PET_OVERLAY_CONFIG_QSETTINGS_KEY = "overlays/stream_pet/main/config_json"
_STREAM_PET_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY = "overlays/stream_pet/main/config_json_backup"


@dataclass(frozen=True, slots=True)
class StreamPetOverlayConfig:
    schema_version: int

    enabled: bool
    decay_per_2min: float
    small_gift_threshold_coins: int
    large_gift_threshold_coins: int
    small_gift_threshold_bits: int
    large_gift_threshold_bits: int
    youtube_small_amount_micros: int
    youtube_large_amount_micros: int
    idle_bubble_min_sec: int
    idle_bubble_max_sec: int
    sleep_idle_sec: int
    bubble_font_family: str
    bubble_font_size_px: int
    pet_sprite_url: str
    show_energy_bar: bool
    pet_scale_pct: int
    initial_energy: float

    preset: str
    pet_body_color: str
    pet_ear_color: str
    pet_outline_color: str
    pet_eye_color: str
    pet_mouth_color: str
    collar_color: str
    collar_enabled: bool
    blush_enabled: bool
    blanket_color: str
    spark_color: str
    hyper_glow_color: str
    bubble_bg_color: str
    bubble_border_color: str
    bubble_text_color: str

    evolution_enabled: bool
    bubble_max_chars: int
    level3_vip_interval_sec: int
    disco_duration_ms: int
    post_evolution_energy: float

    def replace(self, **kwargs: object) -> StreamPetOverlayConfig:
        return replace(self, **kwargs)


def _classic_defaults() -> StreamPetAppearanceFields:
    app = stream_pet_preset_appearance("classic_gold")
    return StreamPetAppearanceFields.from_appearance(app)


@dataclass(frozen=True, slots=True)
class StreamPetAppearanceFields:
    pet_body_color: str
    pet_ear_color: str
    pet_outline_color: str
    pet_eye_color: str
    pet_mouth_color: str
    collar_color: str
    collar_enabled: bool
    blush_enabled: bool
    blanket_color: str
    spark_color: str
    hyper_glow_color: str
    bubble_bg_color: str
    bubble_border_color: str
    bubble_text_color: str

    @classmethod
    def from_appearance(cls, app: object) -> StreamPetAppearanceFields:
        return cls(
            pet_body_color=str(getattr(app, "body", "#fbbf24")),
            pet_ear_color=str(getattr(app, "ear", "#f59e0b")),
            pet_outline_color=str(getattr(app, "outline", "#1e293b")),
            pet_eye_color=str(getattr(app, "eye", "#1e293b")),
            pet_mouth_color=str(getattr(app, "mouth", "#1e293b")),
            collar_color=str(getattr(app, "collar", "#ef4444")),
            collar_enabled=bool(getattr(app, "collar_enabled", True)),
            blush_enabled=bool(getattr(app, "blush_enabled", True)),
            blanket_color=str(getattr(app, "blanket", "#818cf8")),
            spark_color=str(getattr(app, "spark", "#fde047")),
            hyper_glow_color=str(getattr(app, "hyper_glow", "#fbbf24")),
            bubble_bg_color=str(getattr(app, "bubble_bg", "#ffffff")),
            bubble_border_color=str(getattr(app, "bubble_border", "#1e293b")),
            bubble_text_color=str(getattr(app, "bubble_text", "#0f172a")),
        )


def stream_pet_overlay_config_defaults() -> StreamPetOverlayConfig:
    classic = _classic_defaults()
    return StreamPetOverlayConfig(
        schema_version=STREAM_PET_OVERLAY_CONFIG_SCHEMA_VERSION,
        enabled=True,
        decay_per_2min=1.0,
        small_gift_threshold_coins=50,
        large_gift_threshold_coins=99,
        small_gift_threshold_bits=100,
        large_gift_threshold_bits=500,
        youtube_small_amount_micros=2_000_000,
        youtube_large_amount_micros=5_000_000,
        idle_bubble_min_sec=180,
        idle_bubble_max_sec=300,
        sleep_idle_sec=900,
        bubble_font_family="Press Start 2P",
        bubble_font_size_px=20,
        pet_sprite_url="",
        show_energy_bar=True,
        pet_scale_pct=100,
        initial_energy=70.0,
        preset="classic_gold",
        pet_body_color=classic.pet_body_color,
        pet_ear_color=classic.pet_ear_color,
        pet_outline_color=classic.pet_outline_color,
        pet_eye_color=classic.pet_eye_color,
        pet_mouth_color=classic.pet_mouth_color,
        collar_color=classic.collar_color,
        collar_enabled=classic.collar_enabled,
        blush_enabled=classic.blush_enabled,
        blanket_color=classic.blanket_color,
        spark_color=classic.spark_color,
        hyper_glow_color=classic.hyper_glow_color,
        bubble_bg_color=classic.bubble_bg_color,
        bubble_border_color=classic.bubble_border_color,
        bubble_text_color=classic.bubble_text_color,
        evolution_enabled=True,
        bubble_max_chars=110,
        level3_vip_interval_sec=180,
        disco_duration_ms=5000,
        post_evolution_energy=50.0,
    )


def _ensure_float(v: object, *, default: float) -> float:
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


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


def _ensure_preset(v: object) -> str:
    s = str(v or "").strip().lower()
    if s in STREAM_PET_PRESETS:
        return s
    return "classic_gold"


def _ensure_hex_color(v: object, *, default: str) -> str:
    s = str(v or "").strip()
    if s.startswith("#") and len(s) in (4, 7, 9):
        return s
    return default


def stream_pet_overlay_config_from_json_text(text: str) -> StreamPetOverlayConfig:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("stream_pet overlay config must be a JSON object")
    d = raw
    defaults = stream_pet_overlay_config_defaults()
    classic = _classic_defaults()
    preset = _ensure_preset(d.get("preset"))
    return StreamPetOverlayConfig(
        schema_version=_ensure_int(d.get("schema_version"), default=defaults.schema_version),
        enabled=_ensure_bool(d.get("enabled"), default=defaults.enabled),
        decay_per_2min=_ensure_float(d.get("decay_per_2min"), default=defaults.decay_per_2min),
        small_gift_threshold_coins=_ensure_int(
            d.get("small_gift_threshold_coins"),
            default=defaults.small_gift_threshold_coins,
        ),
        large_gift_threshold_coins=_ensure_int(
            d.get("large_gift_threshold_coins"),
            default=defaults.large_gift_threshold_coins,
        ),
        small_gift_threshold_bits=_ensure_int(
            d.get("small_gift_threshold_bits"),
            default=defaults.small_gift_threshold_bits,
        ),
        large_gift_threshold_bits=_ensure_int(
            d.get("large_gift_threshold_bits"),
            default=defaults.large_gift_threshold_bits,
        ),
        youtube_small_amount_micros=_ensure_int(
            d.get("youtube_small_amount_micros"),
            default=defaults.youtube_small_amount_micros,
        ),
        youtube_large_amount_micros=_ensure_int(
            d.get("youtube_large_amount_micros"),
            default=defaults.youtube_large_amount_micros,
        ),
        idle_bubble_min_sec=_ensure_int(
            d.get("idle_bubble_min_sec"),
            default=defaults.idle_bubble_min_sec,
        ),
        idle_bubble_max_sec=_ensure_int(
            d.get("idle_bubble_max_sec"),
            default=defaults.idle_bubble_max_sec,
        ),
        sleep_idle_sec=_ensure_int(d.get("sleep_idle_sec"), default=defaults.sleep_idle_sec),
        bubble_font_family=str(d.get("bubble_font_family") or defaults.bubble_font_family).strip()
        or defaults.bubble_font_family,
        bubble_font_size_px=max(
            12,
            min(
                48, _ensure_int(d.get("bubble_font_size_px"), default=defaults.bubble_font_size_px)
            ),
        ),
        pet_sprite_url=str(d.get("pet_sprite_url") or "").strip(),
        show_energy_bar=_ensure_bool(d.get("show_energy_bar"), default=defaults.show_energy_bar),
        pet_scale_pct=max(
            50, min(200, _ensure_int(d.get("pet_scale_pct"), default=defaults.pet_scale_pct))
        ),
        initial_energy=max(
            0.0,
            min(100.0, _ensure_float(d.get("initial_energy"), default=defaults.initial_energy)),
        ),
        preset=preset,
        pet_body_color=_ensure_hex_color(d.get("pet_body_color"), default=classic.pet_body_color),
        pet_ear_color=_ensure_hex_color(d.get("pet_ear_color"), default=classic.pet_ear_color),
        pet_outline_color=_ensure_hex_color(
            d.get("pet_outline_color"),
            default=classic.pet_outline_color,
        ),
        pet_eye_color=_ensure_hex_color(d.get("pet_eye_color"), default=classic.pet_eye_color),
        pet_mouth_color=_ensure_hex_color(
            d.get("pet_mouth_color"), default=classic.pet_mouth_color
        ),
        collar_color=_ensure_hex_color(d.get("collar_color"), default=classic.collar_color),
        collar_enabled=_ensure_bool(d.get("collar_enabled"), default=classic.collar_enabled),
        blush_enabled=_ensure_bool(d.get("blush_enabled"), default=classic.blush_enabled),
        blanket_color=_ensure_hex_color(d.get("blanket_color"), default=classic.blanket_color),
        spark_color=_ensure_hex_color(d.get("spark_color"), default=classic.spark_color),
        hyper_glow_color=_ensure_hex_color(
            d.get("hyper_glow_color"),
            default=classic.hyper_glow_color,
        ),
        bubble_bg_color=_ensure_hex_color(
            d.get("bubble_bg_color"), default=classic.bubble_bg_color
        ),
        bubble_border_color=_ensure_hex_color(
            d.get("bubble_border_color"),
            default=classic.bubble_border_color,
        ),
        bubble_text_color=_ensure_hex_color(
            d.get("bubble_text_color"),
            default=classic.bubble_text_color,
        ),
        evolution_enabled=_ensure_bool(
            d.get("evolution_enabled"), default=defaults.evolution_enabled
        ),
        bubble_max_chars=max(
            40, min(200, _ensure_int(d.get("bubble_max_chars"), default=defaults.bubble_max_chars))
        ),
        level3_vip_interval_sec=max(
            30,
            min(
                3600,
                _ensure_int(
                    d.get("level3_vip_interval_sec"), default=defaults.level3_vip_interval_sec
                ),
            ),
        ),
        disco_duration_ms=max(
            1000,
            min(30000, _ensure_int(d.get("disco_duration_ms"), default=defaults.disco_duration_ms)),
        ),
        post_evolution_energy=max(
            31.0,
            min(
                100.0,
                _ensure_float(
                    d.get("post_evolution_energy"), default=defaults.post_evolution_energy
                ),
            ),
        ),
    )


def stream_pet_overlay_config_to_public_dict(cfg: StreamPetOverlayConfig) -> dict[str, object]:
    appearance = stream_pet_appearance_to_dict(resolve_stream_pet_appearance(cfg))
    return {
        "schema_version": int(cfg.schema_version),
        "enabled": bool(cfg.enabled),
        "decay_per_2min": float(cfg.decay_per_2min),
        "small_gift_threshold_coins": int(cfg.small_gift_threshold_coins),
        "large_gift_threshold_coins": int(cfg.large_gift_threshold_coins),
        "small_gift_threshold_bits": int(cfg.small_gift_threshold_bits),
        "large_gift_threshold_bits": int(cfg.large_gift_threshold_bits),
        "youtube_small_amount_micros": int(cfg.youtube_small_amount_micros),
        "youtube_large_amount_micros": int(cfg.youtube_large_amount_micros),
        "idle_bubble_min_sec": int(cfg.idle_bubble_min_sec),
        "idle_bubble_max_sec": int(cfg.idle_bubble_max_sec),
        "sleep_idle_sec": int(cfg.sleep_idle_sec),
        "bubble_font_family": str(cfg.bubble_font_family),
        "bubble_font_size_px": int(cfg.bubble_font_size_px),
        "pet_sprite_url": str(cfg.pet_sprite_url),
        "show_energy_bar": bool(cfg.show_energy_bar),
        "pet_scale_pct": int(cfg.pet_scale_pct),
        "initial_energy": float(cfg.initial_energy),
        "preset": str(cfg.preset),
        "pet_body_color": str(cfg.pet_body_color),
        "pet_ear_color": str(cfg.pet_ear_color),
        "pet_outline_color": str(cfg.pet_outline_color),
        "pet_eye_color": str(cfg.pet_eye_color),
        "pet_mouth_color": str(cfg.pet_mouth_color),
        "collar_color": str(cfg.collar_color),
        "collar_enabled": bool(cfg.collar_enabled),
        "blush_enabled": bool(cfg.blush_enabled),
        "blanket_color": str(cfg.blanket_color),
        "spark_color": str(cfg.spark_color),
        "hyper_glow_color": str(cfg.hyper_glow_color),
        "bubble_bg_color": str(cfg.bubble_bg_color),
        "bubble_border_color": str(cfg.bubble_border_color),
        "bubble_text_color": str(cfg.bubble_text_color),
        "evolution_enabled": bool(cfg.evolution_enabled),
        "bubble_max_chars": int(cfg.bubble_max_chars),
        "level3_vip_interval_sec": int(cfg.level3_vip_interval_sec),
        "disco_duration_ms": int(cfg.disco_duration_ms),
        "post_evolution_energy": float(cfg.post_evolution_energy),
        "appearance": appearance,
    }


def stream_pet_overlay_config_to_json_text(cfg: StreamPetOverlayConfig) -> str:
    return json.dumps(
        stream_pet_overlay_config_to_public_dict(cfg),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def apply_stream_pet_preset(cfg: StreamPetOverlayConfig, preset: str) -> StreamPetOverlayConfig:
    key = _ensure_preset(preset)
    if key == "custom":
        return cfg.replace(preset="custom")
    app = stream_pet_preset_appearance(key)
    fields = StreamPetAppearanceFields.from_appearance(app)
    return cfg.replace(
        preset=key,
        pet_body_color=fields.pet_body_color,
        pet_ear_color=fields.pet_ear_color,
        pet_outline_color=fields.pet_outline_color,
        pet_eye_color=fields.pet_eye_color,
        pet_mouth_color=fields.pet_mouth_color,
        collar_color=fields.collar_color,
        collar_enabled=fields.collar_enabled,
        blush_enabled=fields.blush_enabled,
        blanket_color=fields.blanket_color,
        spark_color=fields.spark_color,
        hyper_glow_color=fields.hyper_glow_color,
        bubble_bg_color=fields.bubble_bg_color,
        bubble_border_color=fields.bubble_border_color,
        bubble_text_color=fields.bubble_text_color,
    )


def load_stream_pet_overlay_config(settings: QSettings | None = None) -> StreamPetOverlayConfig:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    raw = (s.value(STREAM_PET_OVERLAY_CONFIG_QSETTINGS_KEY, "", str) or "").strip()
    if not raw:
        return stream_pet_overlay_config_defaults()
    try:
        return stream_pet_overlay_config_from_json_text(raw)
    except (ValueError, TypeError, json.JSONDecodeError):
        bak = (s.value(_STREAM_PET_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, "", str) or "").strip()
        if bak:
            try:
                cfg = stream_pet_overlay_config_from_json_text(bak)
            except (ValueError, TypeError, json.JSONDecodeError):
                return stream_pet_overlay_config_defaults()
            s.setValue(
                STREAM_PET_OVERLAY_CONFIG_QSETTINGS_KEY, stream_pet_overlay_config_to_json_text(cfg)
            )
            return cfg
        return stream_pet_overlay_config_defaults()


def save_stream_pet_overlay_config(
    cfg: StreamPetOverlayConfig,
    settings: QSettings | None = None,
) -> None:
    s = settings or QSettings("stream-cheremsha", "cheremsha")
    txt = stream_pet_overlay_config_to_json_text(cfg)
    s.setValue(STREAM_PET_OVERLAY_CONFIG_QSETTINGS_KEY, txt)
    s.setValue(_STREAM_PET_OVERLAY_CONFIG_QSETTINGS_BACKUP_KEY, txt)
    s.sync()
