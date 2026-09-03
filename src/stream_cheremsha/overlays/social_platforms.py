from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlatformDefinition:
    id: str
    name: str
    accent: str
    icon_key: str
    url_template: str


_PLATFORM_LIST: tuple[PlatformDefinition, ...] = (
    PlatformDefinition(
        id="twitch",
        name="TWITCH",
        accent="#9146FF",
        icon_key="twitch",
        url_template="https://twitch.tv/{username}",
    ),
    PlatformDefinition(
        id="youtube",
        name="YOUTUBE",
        accent="#FF0000",
        icon_key="youtube",
        url_template="https://youtube.com/@{username}",
    ),
    PlatformDefinition(
        id="kick",
        name="KICK",
        accent="#53FC18",
        icon_key="kick",
        url_template="https://kick.com/{username}",
    ),
    PlatformDefinition(
        id="telegram",
        name="TELEGRAM",
        accent="#29B6F6",
        icon_key="telegram",
        url_template="https://t.me/{username}",
    ),
    PlatformDefinition(
        id="tiktok",
        name="TIKTOK",
        accent="#69C9D0",
        icon_key="tiktok",
        url_template="https://tiktok.com/@{username}",
    ),
    PlatformDefinition(
        id="instagram",
        name="INSTAGRAM",
        accent="#E1306C",
        icon_key="instagram",
        url_template="https://instagram.com/{username}",
    ),
    PlatformDefinition(
        id="discord",
        name="DISCORD",
        accent="#5865F2",
        icon_key="discord",
        url_template="",
    ),
    PlatformDefinition(
        id="x",
        name="X",
        accent="#FFFFFF",
        icon_key="x",
        url_template="https://x.com/{username}",
    ),
    PlatformDefinition(
        id="facebook",
        name="FACEBOOK",
        accent="#1877F2",
        icon_key="facebook",
        url_template="https://facebook.com/{username}",
    ),
)

PLATFORM_DEFINITIONS: dict[str, PlatformDefinition] = {p.id: p for p in _PLATFORM_LIST}
ALL_PLATFORM_IDS: tuple[str, ...] = tuple(p.id for p in _PLATFORM_LIST)

_STRIP_AT = frozenset(
    {"twitch", "youtube", "tiktok", "telegram", "kick", "x", "instagram", "facebook"}
)
_LOWERCASE = frozenset({"twitch", "kick"})


def get_platform(platform_id: str) -> PlatformDefinition | None:
    key = str(platform_id or "").strip().lower()
    return PLATFORM_DEFINITIONS.get(key)


def normalize_username(platform_id: str, username: str) -> str:
    pid = str(platform_id or "").strip().lower()
    raw = str(username or "").strip()
    if not raw:
        return ""
    if pid in _STRIP_AT and raw.startswith("@"):
        raw = raw[1:].strip()
    if pid in _LOWERCASE:
        return raw.lower()
    return raw


def build_platform_url(platform_id: str, username: str, url_override: str = "") -> str:
    override = str(url_override or "").strip()
    if override:
        return override
    p = get_platform(platform_id)
    if p is None:
        return ""
    if not p.url_template:
        return ""
    uname = normalize_username(platform_id, username)
    if not uname:
        return ""
    return p.url_template.replace("{username}", uname)
