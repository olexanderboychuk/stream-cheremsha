from __future__ import annotations

from dataclasses import dataclass
from typing import Any

STREAM_PET_PRESETS = frozenset(
    (
        "classic_gold",
        "cyber_purple",
        "cotton_candy",
        "forest_fox",
        "midnight_shadow",
        "sunset_shiba",
        "custom",
    ),
)


@dataclass(frozen=True, slots=True)
class StreamPetAppearance:
    body: str
    ear: str
    outline: str
    eye: str
    mouth: str
    collar: str
    collar_enabled: bool
    blush_enabled: bool
    blanket: str
    spark: str
    hyper_glow: str
    bubble_bg: str
    bubble_border: str
    bubble_text: str


_PRESET_TABLE: dict[str, StreamPetAppearance] = {
    "classic_gold": StreamPetAppearance(
        body="#fbbf24",
        ear="#f59e0b",
        outline="#1e293b",
        eye="#1e293b",
        mouth="#1e293b",
        collar="#ef4444",
        collar_enabled=True,
        blush_enabled=True,
        blanket="#818cf8",
        spark="#fde047",
        hyper_glow="#fbbf24",
        bubble_bg="#ffffff",
        bubble_border="#1e293b",
        bubble_text="#0f172a",
    ),
    "cyber_purple": StreamPetAppearance(
        body="#a78bfa",
        ear="#7c3aed",
        outline="#1e1b4b",
        eye="#22d3ee",
        mouth="#1e1b4b",
        collar="#22d3ee",
        collar_enabled=True,
        blush_enabled=False,
        blanket="#312e81",
        spark="#67e8f9",
        hyper_glow="#c084fc",
        bubble_bg="#1e1b4b",
        bubble_border="#22d3ee",
        bubble_text="#e0e7ff",
    ),
    "cotton_candy": StreamPetAppearance(
        body="#f9a8d4",
        ear="#f472b6",
        outline="#831843",
        eye="#831843",
        mouth="#be185d",
        collar="#60a5fa",
        collar_enabled=True,
        blush_enabled=True,
        blanket="#fbcfe8",
        spark="#fda4af",
        hyper_glow="#f472b6",
        bubble_bg="#fff1f2",
        bubble_border="#f472b6",
        bubble_text="#831843",
    ),
    "forest_fox": StreamPetAppearance(
        body="#ea580c",
        ear="#c2410c",
        outline="#292524",
        eye="#292524",
        mouth="#292524",
        collar="#16a34a",
        collar_enabled=True,
        blush_enabled=True,
        blanket="#86efac",
        spark="#fbbf24",
        hyper_glow="#fb923c",
        bubble_bg="#fff7ed",
        bubble_border="#c2410c",
        bubble_text="#431407",
    ),
    "midnight_shadow": StreamPetAppearance(
        body="#475569",
        ear="#334155",
        outline="#0f172a",
        eye="#e2e8f0",
        mouth="#0f172a",
        collar="#a855f7",
        collar_enabled=True,
        blush_enabled=False,
        blanket="#312e81",
        spark="#c4b5fd",
        hyper_glow="#94a3b8",
        bubble_bg="#1e293b",
        bubble_border="#a855f7",
        bubble_text="#f1f5f9",
    ),
    "sunset_shiba": StreamPetAppearance(
        body="#fcd34d",
        ear="#f59e0b",
        outline="#78350f",
        eye="#78350f",
        mouth="#92400e",
        collar="#14b8a6",
        collar_enabled=True,
        blush_enabled=True,
        blanket="#fdba74",
        spark="#fde68a",
        hyper_glow="#fbbf24",
        bubble_bg="#fffbeb",
        bubble_border="#d97706",
        bubble_text="#78350f",
    ),
}


def stream_pet_preset_appearance(preset: str) -> StreamPetAppearance:
    key = (preset or "").strip().lower()
    if key not in _PRESET_TABLE:
        return _PRESET_TABLE["classic_gold"]
    return _PRESET_TABLE[key]


def stream_pet_appearance_from_config_fields(
    *,
    body: str,
    ear: str,
    outline: str,
    eye: str,
    mouth: str,
    collar: str,
    collar_enabled: bool,
    blush_enabled: bool,
    blanket: str,
    spark: str,
    hyper_glow: str,
    bubble_bg: str,
    bubble_border: str,
    bubble_text: str,
) -> StreamPetAppearance:
    defaults = _PRESET_TABLE["classic_gold"]
    return StreamPetAppearance(
        body=(body or defaults.body).strip() or defaults.body,
        ear=(ear or defaults.ear).strip() or defaults.ear,
        outline=(outline or defaults.outline).strip() or defaults.outline,
        eye=(eye or defaults.eye).strip() or defaults.eye,
        mouth=(mouth or defaults.mouth).strip() or defaults.mouth,
        collar=(collar or defaults.collar).strip() or defaults.collar,
        collar_enabled=bool(collar_enabled),
        blush_enabled=bool(blush_enabled),
        blanket=(blanket or defaults.blanket).strip() or defaults.blanket,
        spark=(spark or defaults.spark).strip() or defaults.spark,
        hyper_glow=(hyper_glow or defaults.hyper_glow).strip() or defaults.hyper_glow,
        bubble_bg=(bubble_bg or defaults.bubble_bg).strip() or defaults.bubble_bg,
        bubble_border=(bubble_border or defaults.bubble_border).strip() or defaults.bubble_border,
        bubble_text=(bubble_text or defaults.bubble_text).strip() or defaults.bubble_text,
    )


def resolve_stream_pet_appearance(cfg: object) -> StreamPetAppearance:
    preset = str(getattr(cfg, "preset", "classic_gold") or "classic_gold").strip().lower()
    if preset != "custom":
        return stream_pet_preset_appearance(preset)
    return stream_pet_appearance_from_config_fields(
        body=str(getattr(cfg, "pet_body_color", "") or ""),
        ear=str(getattr(cfg, "pet_ear_color", "") or ""),
        outline=str(getattr(cfg, "pet_outline_color", "") or ""),
        eye=str(getattr(cfg, "pet_eye_color", "") or ""),
        mouth=str(getattr(cfg, "pet_mouth_color", "") or ""),
        collar=str(getattr(cfg, "collar_color", "") or ""),
        collar_enabled=bool(getattr(cfg, "collar_enabled", True)),
        blush_enabled=bool(getattr(cfg, "blush_enabled", True)),
        blanket=str(getattr(cfg, "blanket_color", "") or ""),
        spark=str(getattr(cfg, "spark_color", "") or ""),
        hyper_glow=str(getattr(cfg, "hyper_glow_color", "") or ""),
        bubble_bg=str(getattr(cfg, "bubble_bg_color", "") or ""),
        bubble_border=str(getattr(cfg, "bubble_border_color", "") or ""),
        bubble_text=str(getattr(cfg, "bubble_text_color", "") or ""),
    )


def stream_pet_appearance_to_dict(app: StreamPetAppearance) -> dict[str, Any]:
    return {
        "body": app.body,
        "ear": app.ear,
        "outline": app.outline,
        "eye": app.eye,
        "mouth": app.mouth,
        "collar": app.collar,
        "collar_enabled": bool(app.collar_enabled),
        "blush_enabled": bool(app.blush_enabled),
        "blanket": app.blanket,
        "spark": app.spark,
        "hyper_glow": app.hyper_glow,
        "bubble_bg": app.bubble_bg,
        "bubble_border": app.bubble_border,
        "bubble_text": app.bubble_text,
    }
