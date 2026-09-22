"""Explicit per-key allowlist for Cloud Sync.

Rules (per spec):
- Anything not explicitly in ``ALLOWLIST`` is NEVER synced. The sync layer is
  therefore structurally unable to upload secrets or device-specific values.
- ``audio/*`` is NEVER synced (entire namespace).
- ``tts/*`` and ``tts_chat/*`` ARE synced (portable user preference).
- Widget/Action data live in dedicated kind entities, not under QSettings, so
  they are also explicitly handled here.
"""

from __future__ import annotations

# Top-level kinds synced to the cloud. The QSettings-allow-listed keys map to
# ``account_settings`` (single per-account entity, field-level merge handled by
# the backend). Widgets and Actions live in their own kinds.
SYNC_KIND_WIDGET = "widget"
SYNC_KIND_ACTIONS = "actions"
SYNC_KIND_ACCOUNT_SETTINGS = "account_settings"
SYNC_KIND_LAYOUTS = "layouts"

# --- explicitly cloud-synced QSettings keys ------------------------------
# Field-level merge is handled by the backend (see app/sync/merge.py).
#
# Each entry maps "qsettings key suffix" -> expected value type (a string label
# used in tests; no runtime cost). Anything not in this set is dropped by
# ``_build_account_settings_payload``.
ALLOWLISTED_QSETTINGS_KEYS: tuple[str, ...] = (
    # Portable UI/user preference.
    "ui/locale",
    # TTS is portable per spec.
    "tts/engine",
    "tts/output_language",
    "tts/rate_percent",
    "tts/whitelist",
    "tts/strip_non_alphabetic",
    "tts/randomize_edge",
    "tts/randomize_respeecher",
    "tts/speak_chat_author_name",
    "tts/min_interval_sec",
    "tts/tts_gain_db",
    # Per-platform TTS chat opt-in (portable per spec).
    "tts_chat/twitch_enabled",
    "tts_chat/youtube_enabled",
    "tts_chat/tiktok_enabled",
    "tts_chat/kick_enabled",
    # Music: portable per spec.
    "music/backend",
    "music/max_duration_minutes",
    "music/volume_percent",
    # Audit/updates.
    "updates/check_on_startup",
    "updates/ignored_version",
    # Donations (UI preferences only — tokens are not these keys).
    "donations/donatik_live_poll",
    "donations/donatik_tts_new",
    "donations/donatello_live_poll",
    "donations/donatello_tts_new",
    # Points cloud-detected preferences.
    "points/song_cost",
    "points/per_coin",
    "points/likes_per_point",
    "points/per_share",
    "points/per_follow",
    "points/watch_points_per_interval",
    "points/watch_interval_minutes",
)

# --- explicitly device-local keys (NEVER synced) -------------------------
DEVICE_LOCAL_KEYS_SAMPLE: tuple[str, ...] = (
    "audio/volume",
    "audio/input_device",
    "audio/output_device",
    "audio/monitor_device",
    "ui/main_window_geometry",
    "ui/chat_popout_geometry",
    "ui/chat_popout_opacity",
    "ui/chat_popout_controls_visible",
    "ui/chat_popout_font_pt",
    "ui/chat_popout_font_family",
    "ui/chat_font_pt",
    "ui/chat_font_family",
    "obs/websocket_host",
    "obs/websocket_port",
    "overlay/tunnel_enabled",
    "overlay/tunnel_provider",
    "overlay/tunnel_custom_url",
    "overlay/ngrok_domain",
    "overlay/cloudflare_hostname",
)


def is_audio_key(key: str) -> bool:
    return key.startswith("audio/")


def is_allowed_qsettings_key(key: str) -> bool:
    """A key is cloud-synced only if explicitly allow-listed AND not
    a known device-local key. ``None`` for hidden/private keys."""
    if not key:
        return False
    if is_audio_key(key):
        # Defence-in-depth: even if added by mistake, audio/* is forbidden.
        return False
    if key in DEVICE_LOCAL_KEYS_SAMPLE:
        return False
    return key in ALLOWLISTED_QSETTINGS_KEYS


def redact_dangerous_blob(blob: dict) -> dict:
    """Final guard before any upload: drop any key that smells like a
    token / OAuth blob / private credential. Never trust a payload whose
    string values look credential-shaped.

    Heuristic only — explicit allowlist is the primary defense.
    """
    import re as _re

    pattern = _re.compile(
        r"(?i)(access_token|refresh_token|client_secret|secret|password|bearer|authorization|tunnel|api_key|api-key|apikey|session|cookie|verifier)"
    )
    out: dict = {}
    for k, v in blob.items():
        if isinstance(k, str) and pattern.search(k):
            continue
        if isinstance(v, str) and (
            pattern.search(v)
            or (len(v) > 32 and v.startswith(("sk-", "Bearer ", "ya29.", "ghp_", "gho_", "xox")))
        ):
            continue
        out[k] = v
    return out
