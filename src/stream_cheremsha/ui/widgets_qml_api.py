from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib.parse import quote

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot
from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtQml import QJSValue
from PySide6.QtQuick import QQuickView

from stream_cheremsha.overlays.actions_config import (
    actions_config_from_json_text,
    actions_config_to_json_text,
    load_actions_config,
    save_actions_config,
)
from stream_cheremsha.overlays.battle_royale_overlay_config import (
    battle_royale_overlay_config_from_json_text,
    battle_royale_overlay_config_to_json_text,
    load_battle_royale_overlay_config,
    save_battle_royale_overlay_config,
)
from stream_cheremsha.overlays.chat_config import (
    chat_config_from_json_text,
    chat_config_to_json_text,
    load_chat_config,
    save_chat_config,
)
from stream_cheremsha.overlays.community_world_config import (
    community_world_overlay_config_from_json_text,
    community_world_overlay_config_to_json_text,
    load_community_world_overlay_config,
    save_community_world_overlay_config,
)
from stream_cheremsha.overlays.king_of_live_overlay_config import (
    king_of_live_overlay_config_from_json_text,
    king_of_live_overlay_config_to_json_text,
    load_king_of_live_overlay_config,
    save_king_of_live_overlay_config,
)
from stream_cheremsha.overlays.live_leaderboard_overlay_config import (
    live_leaderboard_overlay_config_from_json_text,
    live_leaderboard_overlay_config_to_json_text,
    load_live_leaderboard_overlay_config,
    save_live_leaderboard_overlay_config,
)
from stream_cheremsha.overlays.online_overlay_config import (
    load_online_overlay_config,
    online_overlay_config_from_json_text,
    online_overlay_config_to_json_text,
    save_online_overlay_config,
)
from stream_cheremsha.overlays.pubsub import OverlayPubSub
from stream_cheremsha.overlays.social_rotator_overlay_config import (
    load_social_rotator_overlay_config,
    save_social_rotator_overlay_config,
    social_rotator_overlay_config_from_json_text,
    social_rotator_overlay_config_to_json_text,
)
from stream_cheremsha.overlays.stream_goal_overlay_config import (
    load_stream_goal_overlay_config,
    save_stream_goal_overlay_config,
    stream_goal_overlay_config_from_json_text,
    stream_goal_overlay_config_to_json_text,
)
from stream_cheremsha.overlays.stream_pet_overlay_config import (
    apply_stream_pet_preset,
    load_stream_pet_overlay_config,
    save_stream_pet_overlay_config,
    stream_pet_overlay_config_defaults,
    stream_pet_overlay_config_from_json_text,
    stream_pet_overlay_config_to_json_text,
    stream_pet_overlay_config_to_public_dict,
)
from stream_cheremsha.overlays.top_gifters_overlay_config import (
    load_top_gifters_overlay_config,
    save_top_gifters_overlay_config,
    top_gifters_overlay_config_from_json_text,
    top_gifters_overlay_config_to_json_text,
)
from stream_cheremsha.overlays.top_likers_overlay_config import (
    load_top_likers_overlay_config,
    save_top_likers_overlay_config,
    top_likers_overlay_config_from_json_text,
    top_likers_overlay_config_to_json_text,
)
from stream_cheremsha.overlays.ui_locale import load_ui_locale as _ui_locale


def _sorted_system_font_families() -> list[str]:
    db = QFontDatabase()
    names = [str(x).strip() for x in db.families() if str(x).strip()]
    return sorted(set(names), key=str.casefold)


_FONT_FALLBACK_NO_GUI_APP = sorted(
    {"Segoe UI", "Arial", "Tahoma", "Consolas", "Verdana"},
    key=str.casefold,
)

_LOG = logging.getLogger(__name__)


def _json_normalize_for_dump(value: Any) -> Any:
    """Make values ``json.dumps``-safe.

    Qt may hand back maps with non-str keys or odd leaf types.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_normalize_for_dump(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_normalize_for_dump(value[k]) for k in value}
    keys_method = getattr(value, "keys", None)
    if callable(keys_method):
        try:
            return {str(k): _json_normalize_for_dump(value[k]) for k in keys_method()}
        except (TypeError, KeyError, AttributeError):
            pass
    return str(value)


def _qml_js_to_plain_cfg(cfg_js: object) -> object | None:
    """Convert a QML ``QJSValue`` (or plain Python ``dict``) to a Python value for JSON."""
    if cfg_js is None:
        return None
    if isinstance(cfg_js, QJSValue):
        if cfg_js.isUndefined() or cfg_js.isNull():
            return None
        return cfg_js.toVariant()
    return cfg_js


def _qml_cfg_map_to_json_text(cfg_map: object) -> str | None:
    """Serialize a QML ``var``/``QVariantMap`` to JSON for overlay config parsers.

    QML ``JSON.stringify`` on maps returned from ``load*ConfigMap()`` often yields ``"{}"``
    because those objects are not plain JS objects. Prefer ``save*ConfigMap(QJSValue)``
    from QML so ``toVariant()`` yields a real ``dict`` before ``json.dumps``.
    """
    if cfg_map is None:
        return None
    plain_raw: dict[str, Any]
    if isinstance(cfg_map, dict):
        plain_raw = dict(cfg_map)
    else:
        try:
            keys_method = getattr(cfg_map, "keys", None)
            if callable(keys_method):
                plain_raw = {str(k): cfg_map[k] for k in keys_method()}  # type: ignore[index]
            else:
                plain_raw = dict(cfg_map)  # type: ignore[arg-type]
        except (TypeError, ValueError, AttributeError):
            return None
    plain_any = _json_normalize_for_dump(plain_raw)
    if not isinstance(plain_any, dict):
        return None
    plain = plain_any
    try:
        return json.dumps(plain, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    except TypeError:
        try:
            return json.dumps(
                plain, ensure_ascii=False, separators=(",", ":"), sort_keys=True, default=str
            )
        except TypeError:
            return None


class WidgetsQmlApi(QObject):
    def __init__(
        self,
        *,
        overlay_base_url: str = "",
        pubsub: OverlayPubSub | None = None,
        actions_instance: str = "main",
        online_instance: str = "main",
    ) -> None:
        super().__init__()
        self._base = str(overlay_base_url or "").rstrip("/")
        self._pubsub = pubsub
        self._actions_instance = str(actions_instance or "main").strip() or "main"
        self._chat_instance = "main"
        self._online_instance = str(online_instance or "main").strip() or "main"
        self._top_likers_instance = str(online_instance or "main").strip() or "main"
        self._top_gifters_instance = str(online_instance or "main").strip() or "main"
        self._king_of_live_instance = str(online_instance or "main").strip() or "main"
        self._battle_royale_instance = str(online_instance or "main").strip() or "main"
        self._stream_pet_instance = str(online_instance or "main").strip() or "main"
        self._stream_goal_instance = str(online_instance or "main").strip() or "main"
        self._live_leaderboard_instance = str(online_instance or "main").strip() or "main"
        self._social_rotator_instance = str(online_instance or "main").strip() or "main"
        self._community_world_instance = str(online_instance or "main").strip() or "main"
        self._battle_host: Any | None = None
        self._stream_goal_controller: Any | None = None
        self._live_leaderboard_controller: Any | None = None
        self._social_rotator_controller: Any | None = None
        self._system_font_families: list[str] | None = None

    def set_battle_host(self, host: Any) -> None:
        self._battle_host = host

    def set_stream_goal_controller(self, controller: Any) -> None:
        self._stream_goal_controller = controller

    def set_live_leaderboard_controller(self, controller: Any) -> None:
        self._live_leaderboard_controller = controller

    def set_social_rotator_controller(self, controller: Any) -> None:
        self._social_rotator_controller = controller

    def _current_tiktok_anchor_username(self) -> str:
        host = self._battle_host
        if host is None:
            return ""
        getter = getattr(host, "current_tiktok_anchor_username", None)
        if not callable(getter):
            return ""
        return str(getter() or "").strip().lstrip("@").strip()

    @Slot(result="QStringList")
    def systemFontFamilies(self) -> list[str]:
        """Font families Qt reads from the OS (picker for overlay widgets).

        Requires a running ``QGuiApplication``; headless/unit-test callers get a tiny fallback list.
        """
        if QGuiApplication.instance() is None:
            return list(_FONT_FALLBACK_NO_GUI_APP)
        if self._system_font_families is None:
            families = _sorted_system_font_families()
            # Some headless/test environments still create a QGuiApplication but expose no fonts.
            # Keep the picker usable (and tests stable) by falling back in that case too.
            self._system_font_families = families if families else list(_FONT_FALLBACK_NO_GUI_APP)
        return list(self._system_font_families)

    chatOverlayUrlChanged = Signal()

    def set_overlay_base_url(self, base_url: str) -> None:
        base = str(base_url or "").rstrip("/")
        if base == self._base:
            return
        self._base = base
        self.chatOverlayUrlChanged.emit()
        self.actionsOverlayUrlChanged.emit()
        self.onlineOverlayUrlChanged.emit()
        self.topLikersOverlayUrlChanged.emit()
        self.topGiftersOverlayUrlChanged.emit()
        self.kingOfLiveOverlayUrlChanged.emit()
        self.battleRoyaleOverlayUrlChanged.emit()
        self.streamPetOverlayUrlChanged.emit()
        self.communityWorldOverlayUrlChanged.emit()
        self.liveLeaderboardOverlayUrlChanged.emit()
        self.socialRotatorOverlayUrlChanged.emit()
        self.streamGoalOverlayUrlChanged.emit()

    @Property(str, notify=chatOverlayUrlChanged)
    def chatOverlayUrlValue(self) -> str:  # noqa: ANN201 - PySide pattern
        return self.chatOverlayUrl()

    @Slot(result=str)
    def chatOverlayUrl(self) -> str:
        if not self._base:
            return ""
        return f"{self._base}/overlay/chat?instance={self._chat_instance}"

    @Slot()
    def copyChatOverlayUrl(self) -> None:
        url = self.chatOverlayUrl()
        if not url:
            return
        clip = QGuiApplication.clipboard()
        if clip is None:
            return
        clip.setText(url)

    # Music overlay was removed (local playback via yt-dlp instead of BrowserSource).

    actionsOverlayUrlChanged = Signal()

    @Property(str, notify=actionsOverlayUrlChanged)
    def actionsOverlayUrlValue(self) -> str:  # noqa: ANN201 - PySide pattern
        return self.actionsOverlayUrl()

    @Slot(result=str)
    def actionsOverlayUrl(self) -> str:
        if not self._base:
            return ""
        return f"{self._base}/overlay/actions?instance={self._actions_instance}"

    @Slot()
    def copyActionsOverlayUrl(self) -> None:
        url = self.actionsOverlayUrl()
        if not url:
            return
        clip = QGuiApplication.clipboard()
        if clip is None:
            return
        clip.setText(url)

    onlineOverlayUrlChanged = Signal()

    topLikersOverlayUrlChanged = Signal()

    @Property(str, notify=topLikersOverlayUrlChanged)
    def topLikersOverlayUrlValue(self) -> str:  # noqa: ANN201 - PySide pattern
        return self.topLikersOverlayUrl()

    @Slot(result=str)
    def topLikersOverlayUrl(self) -> str:
        if not self._base:
            return ""
        return f"{self._base}/overlay/top_likers?instance={self._top_likers_instance}"

    @Slot()
    def copyTopLikersOverlayUrl(self) -> None:
        url = self.topLikersOverlayUrl()
        if not url:
            return
        clip = QGuiApplication.clipboard()
        if clip is None:
            return
        clip.setText(url)

    topGiftersOverlayUrlChanged = Signal()

    @Property(str, notify=topGiftersOverlayUrlChanged)
    def topGiftersOverlayUrlValue(self) -> str:  # noqa: ANN201 - PySide pattern
        return self.topGiftersOverlayUrl()

    @Slot(result=str)
    def topGiftersOverlayUrl(self) -> str:
        if not self._base:
            return ""
        return f"{self._base}/overlay/top_gifters?instance={self._top_gifters_instance}"

    @Slot()
    def copyTopGiftersOverlayUrl(self) -> None:
        url = self.topGiftersOverlayUrl()
        if not url:
            return
        clip = QGuiApplication.clipboard()
        if clip is None:
            return
        clip.setText(url)

    kingOfLiveOverlayUrlChanged = Signal()

    @Property(str, notify=kingOfLiveOverlayUrlChanged)
    def kingOfLiveOverlayUrlValue(self) -> str:  # noqa: ANN201 - PySide pattern
        return self.kingOfLiveOverlayUrl()

    @Slot(result=str)
    def kingOfLiveOverlayUrl(self) -> str:
        if not self._base:
            return ""
        qs = f"instance={self._king_of_live_instance}"
        anchor = self._current_tiktok_anchor_username()
        if anchor:
            qs += f"&anchor={quote(anchor, safe='')}"
        return f"{self._base}/overlay/king_of_live?{qs}"

    @Slot()
    def copyKingOfLiveOverlayUrl(self) -> None:
        url = self.kingOfLiveOverlayUrl()
        if not url:
            return
        clip = QGuiApplication.clipboard()
        if clip is None:
            return
        clip.setText(url)

    battleRoyaleOverlayUrlChanged = Signal()

    @Property(str, notify=battleRoyaleOverlayUrlChanged)
    def battleRoyaleOverlayUrlValue(self) -> str:  # noqa: ANN201 - PySide pattern
        return self.battleRoyaleOverlayUrl()

    @Slot(result=str)
    def battleRoyaleOverlayUrl(self) -> str:
        if not self._base:
            return ""
        return f"{self._base}/overlay/battle_royale?instance={self._battle_royale_instance}"

    @Slot()
    def copyBattleRoyaleOverlayUrl(self) -> None:
        url = self.battleRoyaleOverlayUrl()
        if not url:
            return
        clip = QGuiApplication.clipboard()
        if clip is None:
            return
        clip.setText(url)

    streamPetOverlayUrlChanged = Signal()

    @Property(str, notify=streamPetOverlayUrlChanged)
    def streamPetOverlayUrlValue(self) -> str:  # noqa: ANN201 - PySide pattern
        return self.streamPetOverlayUrl()

    @Slot(result=str)
    def streamPetOverlayUrl(self) -> str:
        if not self._base:
            return ""
        return f"{self._base}/overlay/stream_pet?instance={self._stream_pet_instance}"

    @Slot()
    def copyStreamPetOverlayUrl(self) -> None:
        url = self.streamPetOverlayUrl()
        if not url:
            return
        clip = QGuiApplication.clipboard()
        if clip is None:
            return
        clip.setText(url)

    @Slot()
    def previewStreamPetOverlay(self) -> None:
        topic = f"overlay:stream_pet:{self._stream_pet_instance}"
        cfg = load_stream_pet_overlay_config()
        patch: dict[str, Any] = {
            "config": stream_pet_overlay_config_to_public_dict(cfg),
            "energy": 88,
            "mood": "hyper",
            "sleeping": False,
            "anim_seq": 1,
            "last_donor": "PreviewDonor",
            "speech": {
                "text": "АААА! МЕНЕ ПРЕЕЕЕ! 🔥🚀",
                "kind": "idle",
                "ttl_ms": 5000,
                "anim": "dance",
            },
        }
        self._publish_patch(topic=topic, patch=patch)

    streamGoalOverlayUrlChanged = Signal()

    @Property(str, notify=streamGoalOverlayUrlChanged)
    def streamGoalOverlayUrlValue(self) -> str:  # noqa: ANN201 - PySide pattern
        return self.streamGoalOverlayUrl()

    @Slot(result=str)
    def streamGoalOverlayUrl(self) -> str:
        if not self._base:
            return ""
        return f"{self._base}/overlay/stream_goal?instance={self._stream_goal_instance}"

    @Slot()
    def copyStreamGoalOverlayUrl(self) -> None:
        url = self.streamGoalOverlayUrl()
        if not url:
            return
        clip = QGuiApplication.clipboard()
        if clip is None:
            return
        clip.setText(url)

    @Slot()
    def previewStreamGoalOverlay(self) -> None:
        topic = f"overlay:stream_goal:{self._stream_goal_instance}"
        cfg = load_stream_goal_overlay_config()
        patch = {
            "config": json.loads(stream_goal_overlay_config_to_json_text(cfg)),
            "goal_type": cfg.goal_type,
            "title": cfg.title,
            "subtitle": cfg.subtitle,
            "current_value": min(cfg.target_value, max(0, int(cfg.target_value * 0.65))),
            "target_value": cfg.target_value,
            "progress": 0.65,
            "progress_percent": 65,
            "remaining": max(0, cfg.target_value - int(cfg.target_value * 0.65)),
            "skin": cfg.skin,
            "accent_color": cfg.accent_color,
            "scale_percent": int(cfg.scale_percent),
            "animation_intensity": cfg.animation_intensity,
            "enable_particles": cfg.enable_particles,
            "enable_glitch": cfg.enable_glitch,
            "combo_count": 5,
            "core_level": 2,
            "completed_goals": 1,
            "milestones": [
                {"percent": 25, "label": "CORE ONLINE", "reached": True, "active": False},
                {"percent": 50, "label": "ENERGY STABLE", "reached": True, "active": True},
                {"percent": 75, "label": "CRITICAL ENERGY", "reached": False, "active": False},
                {"percent": 100, "label": "CORE BREACH", "reached": False, "active": False},
            ],
            "visual_events": [
                {
                    "type": "event_absorbed",
                    "payload": {
                        "type": "like",
                        "amount": 42,
                        "batched": True,
                        "progress": 0.65,
                        "progress_percent": 65,
                        "combo": 5,
                        "metadata": {"batched": True, "count": 42},
                    },
                    "timestamp": 0,
                }
            ],
        }
        self._publish_patch(topic=topic, patch=patch)

    liveLeaderboardOverlayUrlChanged = Signal()

    @Property(str, notify=liveLeaderboardOverlayUrlChanged)
    def liveLeaderboardOverlayUrlValue(self) -> str:  # noqa: ANN201 - PySide pattern
        return self.liveLeaderboardOverlayUrl()

    @Slot(result=str)
    def liveLeaderboardOverlayUrl(self) -> str:
        if not self._base:
            return ""
        return f"{self._base}/overlay/live_leaderboard?instance={self._live_leaderboard_instance}"

    @Slot()
    def copyLiveLeaderboardOverlayUrl(self) -> None:
        url = self.liveLeaderboardOverlayUrl()
        if not url:
            return
        clip = QGuiApplication.clipboard()
        if clip is None:
            return
        clip.setText(url)

    @Slot()
    def previewLiveLeaderboardOverlay(self) -> None:
        topic = f"overlay:live_leaderboard:{self._live_leaderboard_instance}"
        cfg = load_live_leaderboard_overlay_config()
        demo = [
            {
                "key": "1",
                "rank": 1,
                "user": "VOIDWALKER",
                "value": 12480,
                "avatar_url": "",
                "unit": "likes",
            },
            {
                "key": "2",
                "rank": 2,
                "user": "STELLAR_99",
                "value": 8240,
                "avatar_url": "",
                "unit": "likes",
            },
            {
                "key": "3",
                "rank": 3,
                "user": "CYBER_NOVA",
                "value": 5120,
                "avatar_url": "",
                "unit": "likes",
            },
            {
                "key": "4",
                "rank": 4,
                "user": "PIXEL_GHOST",
                "value": 3900,
                "avatar_url": "",
                "unit": "likes",
            },
            {
                "key": "5",
                "rank": 5,
                "user": "RETROGRADE",
                "value": 2740,
                "avatar_url": "",
                "unit": "likes",
            },
        ]
        patch = {
            "config": json.loads(live_leaderboard_overlay_config_to_json_text(cfg)),
            "locale": _ui_locale(),
            "rankings": {
                "likers": demo,
                "gifters": [
                    {**demo[0], "value": 18420, "unit": "coins"},
                    {**demo[1], "value": 9100, "unit": "coins"},
                    {**demo[2], "value": 6400, "unit": "coins"},
                ],
                "sharers": [],
                "commenters": [],
                "contributors": demo,
            },
            "presentation": {
                "source_id": "likers",
                "scene_id": "hall_of_fame",
                "sequence_index": 0,
                "scene_started_at_ms": 0,
                "scene_duration_ms": 8000,
                "transition_token": 1,
                "server_now_ms": 0,
            },
        }
        self._publish_patch(topic=topic, patch=patch)

    socialRotatorOverlayUrlChanged = Signal()

    @Property(str, notify=socialRotatorOverlayUrlChanged)
    def socialRotatorOverlayUrlValue(self) -> str:  # noqa: ANN201 - PySide pattern
        return self.socialRotatorOverlayUrl()

    @Slot(result=str)
    def socialRotatorOverlayUrl(self) -> str:
        if not self._base:
            return ""
        return f"{self._base}/overlay/social_rotator?instance={self._social_rotator_instance}"

    @Slot()
    def copySocialRotatorOverlayUrl(self) -> None:
        url = self.socialRotatorOverlayUrl()
        if not url:
            return
        clip = QGuiApplication.clipboard()
        if clip is None:
            return
        clip.setText(url)

    @Slot()
    def previewSocialRotatorOverlay(self) -> None:
        topic = f"overlay:social_rotator:{self._social_rotator_instance}"
        if self._social_rotator_controller is not None:
            try:
                patch = self._social_rotator_controller.initial_state()
                self._publish_patch(topic=topic, patch=patch)
                return
            except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
                _LOG.warning("previewSocialRotatorOverlay controller state failed: %s", exc)
        cfg = load_social_rotator_overlay_config()
        patch = {
            "config": json.loads(social_rotator_overlay_config_to_json_text(cfg)),
            "locale": _ui_locale(),
            "stats": {
                "latest_follower": {"name": "kittencat_42"},
                "latest_donation": {"name": "Dimon4ik", "value": 250, "source": "donatik"},
                "top_donator": {"name": "Diamond_ua", "value": 1500},
                "stream_started_at_ms": int(time.time() * 1000) - 95 * 60 * 1000,
                "viewers_by_platform": {"tiktok": 100, "twitch": 40, "kick": 12},
                "viewers_total": 152,
            },
        }
        self._publish_patch(topic=topic, patch=patch)

    communityWorldOverlayUrlChanged = Signal()

    @Property(str, notify=communityWorldOverlayUrlChanged)
    def communityWorldOverlayUrlValue(self) -> str:  # noqa: ANN201 - PySide pattern
        return self.communityWorldOverlayUrl()

    @Slot(result=str)
    def communityWorldOverlayUrl(self) -> str:
        if not self._base:
            return ""
        return f"{self._base}/overlay/community_world?instance={self._community_world_instance}"

    @Slot()
    def copyCommunityWorldOverlayUrl(self) -> None:
        url = self.communityWorldOverlayUrl()
        if not url:
            return
        clip = QGuiApplication.clipboard()
        if clip is None:
            return
        clip.setText(url)

    @Slot()
    def previewCommunityWorldOverlay(self) -> None:
        topic = f"overlay:community_world:{self._community_world_instance}"
        cfg = load_community_world_overlay_config()
        buildings = [
            {"id": "house", "unlocked": True, "new": True},
            {"id": "tree", "unlocked": True, "new": True},
            {"id": "house2", "unlocked": True, "new": False},
            {"id": "well", "unlocked": True, "new": False},
            {"id": "bridge", "unlocked": True, "new": False},
            {"id": "church", "unlocked": False, "new": False},
        ]
        quests = [
            {"type": "likes", "current": 5200, "target": 5000, "completed": True},
            {"type": "shares", "current": 32, "target": 50, "completed": False},
            {"type": "gifts", "current": 780, "target": 1000, "completed": False},
        ]
        recent = [
            {"kind": "follow", "user": "Preview Fan", "detail": "", "icon": "", "seq": 1},
            {"kind": "gift", "user": "Preview Donor", "detail": "Rose", "icon": "", "seq": 2},
            {"kind": "share", "user": "Preview Follower", "detail": "3", "icon": "", "seq": 3},
        ]
        passports = [
            {
                "key": "a",
                "user": "Preview Fan",
                "avatar_url": "",
                "points": 420,
                "badges": ["founder", "regular"],
            },
            {
                "key": "b",
                "user": "Preview Donor",
                "avatar_url": "",
                "points": 310,
                "badges": ["gifter", "supporter"],
            },
        ]
        patch: dict[str, Any] = {
            "config": json.loads(community_world_overlay_config_to_json_text(cfg)),
            "level": 3,
            "xp": 420,
            "xp_to_next": 210,
            "progress": 0.68,
            "follows": 47,
            "likes": 5200,
            "shares": 32,
            "gift_coins": 780,
            "joins": 120,
            "chat_messages": 640,
            "unique_viewers": 210,
            "buildings": buildings,
            "quests": quests,
            "recent": recent,
            "passports": passports,
            "founder": "Preview Fan",
            "elders": [
                {"user": "Elder Alpha", "badge_count": 12},
                {"user": "Elder Beta", "badge_count": 9},
            ],
            "anim_seq": 1,
            "quest_complete_seq": 1,
            "locale": _ui_locale(),
        }
        self._publish_patch(topic=topic, patch=patch)

    @Slot()
    def previewBattleRoyaleOverlay(self) -> None:
        topic = f"overlay:battle_royale:{self._battle_royale_instance}"
        cfg = load_battle_royale_overlay_config()
        patch: dict[str, Any] = {
            "config": json.loads(battle_royale_overlay_config_to_json_text(cfg)),
            "phase": "active",
            "fighters": [
                {
                    "user_key": "a",
                    "user": "RomBom",
                    "avatar_url": "",
                    "hp": 850,
                    "max_hp": 1200,
                    "side": "left",
                    "session_donated": 2300,
                    "wins": 0,
                    "rank": 11,
                },
                {
                    "user_key": "b",
                    "user": "StarDust",
                    "avatar_url": "",
                    "hp": 1150,
                    "max_hp": 1300,
                    "side": "right",
                    "session_donated": 5800,
                    "wins": 1,
                    "rank": 27,
                },
            ],
            "timer_remaining_s": 75,
            "countdown_remaining_s": 0,
            "last_hit": {"from": 1, "to": 0, "damage": 150, "heal": 0, "crit": False},
            "last_attack": {
                "attacker": "StarDust",
                "target": "RomBom",
                "damage": 150,
                "amount": 200,
                "crit": False,
            },
            "fx_seq": 3,
            "winner": None,
        }
        self._publish_patch(topic=topic, patch=patch)

    @Slot(result=bool)
    def battleRoyaleStartFromLeaders(self) -> bool:
        host = self._battle_host
        if host is None:
            return False
        fn = getattr(host, "battle_royale_start_from_leaders", None)
        if not callable(fn):
            return False
        return bool(fn())

    @Slot()
    def battleRoyaleStop(self) -> None:
        host = self._battle_host
        if host is None:
            return
        fn = getattr(host, "battle_royale_stop", None)
        if callable(fn):
            fn()

    @Slot(result=str)
    def battleRoyalePhase(self) -> str:
        host = self._battle_host
        if host is None:
            return "idle"
        ctrl = getattr(host, "_battle_controller", None)
        if ctrl is None:
            return "idle"
        return str(ctrl.state().phase.value)

    @Property(str, notify=onlineOverlayUrlChanged)
    def onlineOverlayUrlValue(self) -> str:  # noqa: ANN201 - PySide pattern
        return self.onlineOverlayUrl()

    @Slot(result=str)
    def onlineOverlayUrl(self) -> str:
        if not self._base:
            return ""
        return f"{self._base}/overlay/online?instance={self._online_instance}"

    @Slot()
    def copyOnlineOverlayUrl(self) -> None:
        url = self.onlineOverlayUrl()
        if not url:
            return
        clip = QGuiApplication.clipboard()
        if clip is None:
            return
        clip.setText(url)

    def _publish_patch(self, *, topic: str, patch: dict[str, Any]) -> None:
        ps = self._pubsub
        if ps is None:
            return
        ps.publish_sync(topic, patch)

    @Slot()
    def previewActionsOverlay(self) -> None:
        topic = f"overlay:actions:{self._actions_instance}"
        patch = {
            "append": {
                "username": "username",
                "text": "action triggered",
                "profile_picture_url": "",
                "gift_picture_url": "",
                "platform": "tiktok",
                # Lets ▶ preview show the asset row without persisting show_action_platform_icon on.
                "preview_force_platform_icon": True,
            }
        }
        self._publish_patch(topic=topic, patch=patch)

    @Slot()
    def previewTopLikersOverlay(self) -> None:
        topic = f"overlay:top_likers:{self._top_likers_instance}"
        cfg = load_top_likers_overlay_config()
        lim = max(1, min(10, int(cfg.top_count)))
        leaders: list[dict[str, str | int]] = []
        for i in range(lim):
            leaders.append(
                {
                    "rank": i + 1,
                    "user": f"Example User {i + 1}",
                    "likes": 15005 - i * 1200,
                    "avatar_url": "",
                }
            )
        patch: dict[str, Any] = {
            "leaders": leaders,
            "config": json.loads(top_likers_overlay_config_to_json_text(cfg)),
        }
        self._publish_patch(topic=topic, patch=patch)

    @Slot()
    def previewTopGiftersOverlay(self) -> None:
        topic = f"overlay:top_gifters:{self._top_gifters_instance}"
        cfg = load_top_gifters_overlay_config()
        lim = max(1, min(10, int(cfg.top_count)))
        leaders: list[dict[str, str | int]] = []
        for i in range(lim):
            leaders.append(
                {
                    "rank": i + 1,
                    "user": f"Example User {i + 1}",
                    "coins": 15005 - i * 1200,
                    "avatar_url": "",
                }
            )
        patch: dict[str, Any] = {
            "leaders": leaders,
            "config": json.loads(top_gifters_overlay_config_to_json_text(cfg)),
        }
        self._publish_patch(topic=topic, patch=patch)

    @Slot()
    def previewKingOfLiveOverlay(self) -> None:
        topic = f"overlay:king_of_live:{self._king_of_live_instance}"
        cfg = load_king_of_live_overlay_config()
        patch: dict[str, Any] = {
            "config": json.loads(king_of_live_overlay_config_to_json_text(cfg)),
            "king": {
                "key": "preview_king",
                "user": "Preview Monarch",
                "avatar_url": "",
                "diamonds": 1_250_000,
            },
            "gap_diamonds": 42_000,
            "runner_up_user": "Runner-up Rex",
            "session_challenger": {
                "key": "ch",
                "user": "Challenger",
                "coins": 1_100_000,
                "ratio": 0.88,
            },
            "throne_danger": True,
            "king_revision": 0,
            "king_presence_seq": 0,
            "chat_highlight_seq": 0,
        }
        self._publish_patch(topic=topic, patch=patch)

    @Slot(result="QVariantMap")
    def loadChatConfigMap(self) -> dict[str, Any]:
        """Plain dict for QML (avoids JSON.parse failures wiping UI → disk)."""
        cfg = load_chat_config()
        return json.loads(chat_config_to_json_text(cfg))

    @Slot(result="QVariantMap")
    def loadActionsConfigMap(self) -> dict[str, Any]:
        cfg = load_actions_config()
        return json.loads(actions_config_to_json_text(cfg))

    @Slot(result=str)
    def loadChatConfigJson(self) -> str:
        cfg = load_chat_config()
        return chat_config_to_json_text(cfg)

    @Slot(str)
    def saveChatConfigJson(self, cfg_json: str) -> None:
        txt = (cfg_json or "").strip()
        if not txt:
            # Do not overwrite existing settings on empty payloads (transient UI states).
            return
        try:
            cfg = chat_config_from_json_text(txt)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            _LOG.warning(
                "saveChatConfigJson: rejected payload (%s): %s", exc.__class__.__name__, exc
            )
            return
        save_chat_config(cfg)
        if self._pubsub is not None:
            topic = f"overlay:chat:{self._chat_instance}"
            patch = {"config": json.loads(chat_config_to_json_text(cfg))}
            self._publish_patch(topic=topic, patch=patch)

    @Slot(QJSValue)
    def saveChatConfigMap(self, cfg_js: QJSValue) -> None:
        plain = _qml_js_to_plain_cfg(cfg_js)
        _LOG.info("widgets ConfigMap save: chat (plain_type=%s)", type(plain).__name__)
        if plain is None:
            _LOG.warning("widgets ConfigMap save: chat rejected (null/undefined)")
            return
        txt = _qml_cfg_map_to_json_text(plain)
        if not txt or txt == "{}":
            _LOG.warning("widgets ConfigMap save: chat rejected empty_or_non_serializable")
            return
        _LOG.info("widgets ConfigMap save: chat ok json_len=%d", len(txt))
        self.saveChatConfigJson(txt)

    @Slot(result=str)
    def loadActionsConfigJson(self) -> str:
        cfg = load_actions_config()
        return actions_config_to_json_text(cfg)

    @Slot(str)
    def saveActionsConfigJson(self, cfg_json: str) -> None:
        txt = (cfg_json or "").strip()
        if not txt:
            # Do not overwrite existing settings on empty payloads (transient UI states).
            return
        try:
            cfg = actions_config_from_json_text(txt)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            _LOG.warning(
                "saveActionsConfigJson: rejected payload (%s): %s", exc.__class__.__name__, exc
            )
            return
        save_actions_config(cfg)
        if self._pubsub is not None:
            topic = f"overlay:actions:{self._actions_instance}"
            patch = {"config": json.loads(actions_config_to_json_text(cfg))}
            self._publish_patch(topic=topic, patch=patch)

    @Slot(QJSValue)
    def saveActionsConfigMap(self, cfg_js: QJSValue) -> None:
        plain = _qml_js_to_plain_cfg(cfg_js)
        _LOG.info("widgets ConfigMap save: actions (plain_type=%s)", type(plain).__name__)
        if plain is None:
            _LOG.warning("widgets ConfigMap save: actions rejected (null/undefined)")
            return
        txt = _qml_cfg_map_to_json_text(plain)
        if not txt or txt == "{}":
            _LOG.warning("widgets ConfigMap save: actions rejected empty_or_non_serializable")
            return
        _LOG.info("widgets ConfigMap save: actions ok json_len=%d", len(txt))
        self.saveActionsConfigJson(txt)

    @Slot(result="QVariantMap")
    def loadOnlineOverlayConfigMap(self) -> dict[str, Any]:
        cfg = load_online_overlay_config()
        return json.loads(online_overlay_config_to_json_text(cfg))

    @Slot(result=str)
    def loadOnlineOverlayConfigJson(self) -> str:
        cfg = load_online_overlay_config()
        return online_overlay_config_to_json_text(cfg)

    @Slot(str)
    def saveOnlineOverlayConfigJson(self, cfg_json: str) -> None:
        txt = (cfg_json or "").strip()
        if not txt:
            return
        try:
            cfg = online_overlay_config_from_json_text(txt)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            _LOG.warning(
                "saveOnlineOverlayConfigJson: rejected payload (%s): %s",
                exc.__class__.__name__,
                exc,
            )
            return
        save_online_overlay_config(cfg)
        if self._pubsub is not None:
            topic = f"overlay:online:{self._online_instance}"
            patch = {"config": json.loads(online_overlay_config_to_json_text(cfg))}
            self._publish_patch(topic=topic, patch=patch)

    @Slot(QJSValue)
    def saveOnlineOverlayConfigMap(self, cfg_js: QJSValue) -> None:
        plain = _qml_js_to_plain_cfg(cfg_js)
        _LOG.info("widgets ConfigMap save: online (plain_type=%s)", type(plain).__name__)
        if plain is None:
            _LOG.warning("widgets ConfigMap save: online rejected (null/undefined)")
            return
        txt = _qml_cfg_map_to_json_text(plain)
        if not txt or txt == "{}":
            _LOG.warning("widgets ConfigMap save: online rejected empty_or_non_serializable")
            return
        _LOG.info("widgets ConfigMap save: online ok json_len=%d", len(txt))
        self.saveOnlineOverlayConfigJson(txt)

    @Slot(result="QVariantMap")
    def loadTopLikersOverlayConfigMap(self) -> dict[str, Any]:
        cfg = load_top_likers_overlay_config()
        return json.loads(top_likers_overlay_config_to_json_text(cfg))

    @Slot(result=str)
    def loadTopLikersOverlayConfigJson(self) -> str:
        cfg = load_top_likers_overlay_config()
        return top_likers_overlay_config_to_json_text(cfg)

    @Slot(str)
    def saveTopLikersOverlayConfigJson(self, cfg_json: str) -> None:
        txt = (cfg_json or "").strip()
        if not txt:
            return
        try:
            cfg = top_likers_overlay_config_from_json_text(txt)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            _LOG.warning(
                "saveTopLikersOverlayConfigJson: rejected payload (%s): %s",
                exc.__class__.__name__,
                exc,
            )
            return
        save_top_likers_overlay_config(cfg)
        _LOG.info("widgets overlay persisted: top_likers")
        if self._pubsub is not None:
            topic = f"overlay:top_likers:{self._top_likers_instance}"
            patch = {"config": json.loads(top_likers_overlay_config_to_json_text(cfg))}
            self._publish_patch(topic=topic, patch=patch)

    @Slot(QJSValue)
    def saveTopLikersOverlayConfigMap(self, cfg_js: QJSValue) -> None:
        plain = _qml_js_to_plain_cfg(cfg_js)
        _LOG.info("widgets ConfigMap save: top_likers (plain_type=%s)", type(plain).__name__)
        if plain is None:
            _LOG.warning("widgets ConfigMap save: top_likers rejected (null/undefined)")
            return
        txt = _qml_cfg_map_to_json_text(plain)
        if not txt or txt == "{}":
            _LOG.warning("widgets ConfigMap save: top_likers rejected empty_or_non_serializable")
            return
        _LOG.info("widgets ConfigMap save: top_likers ok json_len=%d", len(txt))
        self.saveTopLikersOverlayConfigJson(txt)

    @Slot(result="QVariantMap")
    def loadTopGiftersOverlayConfigMap(self) -> dict[str, Any]:
        cfg = load_top_gifters_overlay_config()
        return json.loads(top_gifters_overlay_config_to_json_text(cfg))

    @Slot(result=str)
    def loadTopGiftersOverlayConfigJson(self) -> str:
        cfg = load_top_gifters_overlay_config()
        return top_gifters_overlay_config_to_json_text(cfg)

    @Slot(str)
    def saveTopGiftersOverlayConfigJson(self, cfg_json: str) -> None:
        txt = (cfg_json or "").strip()
        if not txt:
            return
        try:
            cfg = top_gifters_overlay_config_from_json_text(txt)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            _LOG.warning(
                "saveTopGiftersOverlayConfigJson: rejected payload (%s): %s",
                exc.__class__.__name__,
                exc,
            )
            return
        save_top_gifters_overlay_config(cfg)
        _LOG.info("widgets overlay persisted: top_gifters")
        if self._pubsub is not None:
            topic = f"overlay:top_gifters:{self._top_gifters_instance}"
            patch = {"config": json.loads(top_gifters_overlay_config_to_json_text(cfg))}
            self._publish_patch(topic=topic, patch=patch)

    @Slot(QJSValue)
    def saveTopGiftersOverlayConfigMap(self, cfg_js: QJSValue) -> None:
        plain = _qml_js_to_plain_cfg(cfg_js)
        _LOG.info("widgets ConfigMap save: top_gifters (plain_type=%s)", type(plain).__name__)
        if plain is None:
            _LOG.warning("widgets ConfigMap save: top_gifters rejected (null/undefined)")
            return
        txt = _qml_cfg_map_to_json_text(plain)
        if not txt or txt == "{}":
            _LOG.warning("widgets ConfigMap save: top_gifters rejected empty_or_non_serializable")
            return
        _LOG.info("widgets ConfigMap save: top_gifters ok json_len=%d", len(txt))
        self.saveTopGiftersOverlayConfigJson(txt)

    @Slot(result="QVariantMap")
    def loadKingOfLiveOverlayConfigMap(self) -> dict[str, Any]:
        cfg = load_king_of_live_overlay_config()
        return json.loads(king_of_live_overlay_config_to_json_text(cfg))

    @Slot(result=str)
    def loadKingOfLiveOverlayConfigJson(self) -> str:
        cfg = load_king_of_live_overlay_config()
        return king_of_live_overlay_config_to_json_text(cfg)

    @Slot(str)
    def saveKingOfLiveOverlayConfigJson(self, cfg_json: str) -> None:
        txt = (cfg_json or "").strip()
        if not txt:
            return
        try:
            cfg = king_of_live_overlay_config_from_json_text(txt)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            _LOG.warning(
                "saveKingOfLiveOverlayConfigJson: rejected payload (%s): %s",
                exc.__class__.__name__,
                exc,
            )
            return
        save_king_of_live_overlay_config(cfg)
        _LOG.info("widgets overlay persisted: king_of_live")
        if self._pubsub is not None:
            topic = f"overlay:king_of_live:{self._king_of_live_instance}"
            patch = {"config": json.loads(king_of_live_overlay_config_to_json_text(cfg))}
            self._publish_patch(topic=topic, patch=patch)

    @Slot(QJSValue)
    def saveKingOfLiveOverlayConfigMap(self, cfg_js: QJSValue) -> None:
        plain = _qml_js_to_plain_cfg(cfg_js)
        _LOG.info("widgets ConfigMap save: king_of_live (plain_type=%s)", type(plain).__name__)
        if plain is None:
            _LOG.warning("widgets ConfigMap save: king_of_live rejected (null/undefined)")
            return
        txt = _qml_cfg_map_to_json_text(plain)
        if not txt or txt == "{}":
            _LOG.warning("widgets ConfigMap save: king_of_live rejected empty_or_non_serializable")
            return
        _LOG.info("widgets ConfigMap save: king_of_live ok json_len=%d", len(txt))
        self.saveKingOfLiveOverlayConfigJson(txt)

    @Slot(result="QVariantMap")
    def loadBattleRoyaleOverlayConfigMap(self) -> dict[str, Any]:
        cfg = load_battle_royale_overlay_config()
        return json.loads(battle_royale_overlay_config_to_json_text(cfg))

    @Slot(result=str)
    def loadBattleRoyaleOverlayConfigJson(self) -> str:
        cfg = load_battle_royale_overlay_config()
        return battle_royale_overlay_config_to_json_text(cfg)

    @Slot(str)
    def saveBattleRoyaleOverlayConfigJson(self, cfg_json: str) -> None:
        txt = (cfg_json or "").strip()
        if not txt:
            return
        try:
            cfg = battle_royale_overlay_config_from_json_text(txt)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            _LOG.warning(
                "saveBattleRoyaleOverlayConfigJson: rejected payload (%s): %s",
                exc.__class__.__name__,
                exc,
            )
            return
        save_battle_royale_overlay_config(cfg)
        _LOG.info("widgets overlay persisted: battle_royale")
        if self._pubsub is not None:
            topic = f"overlay:battle_royale:{self._battle_royale_instance}"
            patch = {"config": json.loads(battle_royale_overlay_config_to_json_text(cfg))}
            self._publish_patch(topic=topic, patch=patch)

    @Slot(QJSValue)
    def saveBattleRoyaleOverlayConfigMap(self, cfg_js: QJSValue) -> None:
        plain = _qml_js_to_plain_cfg(cfg_js)
        _LOG.info("widgets ConfigMap save: battle_royale (plain_type=%s)", type(plain).__name__)
        if plain is None:
            _LOG.warning("widgets ConfigMap save: battle_royale rejected (null/undefined)")
            return
        txt = _qml_cfg_map_to_json_text(plain)
        if not txt or txt == "{}":
            _LOG.warning("widgets ConfigMap save: battle_royale rejected empty_or_non_serializable")
            return
        _LOG.info("widgets ConfigMap save: battle_royale ok json_len=%d", len(txt))
        self.saveBattleRoyaleOverlayConfigJson(txt)

    @Slot(str, result="QVariantMap")
    def streamPetPresetDefaultsMap(self, preset: str) -> dict[str, Any]:
        cfg = apply_stream_pet_preset(stream_pet_overlay_config_defaults(), preset)
        return stream_pet_overlay_config_to_public_dict(cfg)

    @Slot(result="QVariantMap")
    def loadStreamPetOverlayConfigMap(self) -> dict[str, Any]:
        cfg = load_stream_pet_overlay_config()
        return stream_pet_overlay_config_to_public_dict(cfg)

    @Slot(result=str)
    def loadStreamPetOverlayConfigJson(self) -> str:
        cfg = load_stream_pet_overlay_config()
        return stream_pet_overlay_config_to_json_text(cfg)

    @Slot(str)
    def saveStreamPetOverlayConfigJson(self, cfg_json: str) -> None:
        txt = (cfg_json or "").strip()
        if not txt:
            return
        try:
            cfg = stream_pet_overlay_config_from_json_text(txt)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            _LOG.warning(
                "saveStreamPetOverlayConfigJson: rejected payload (%s): %s",
                exc.__class__.__name__,
                exc,
            )
            return
        save_stream_pet_overlay_config(cfg)
        _LOG.info("widgets overlay persisted: stream_pet")
        if self._pubsub is not None:
            topic = f"overlay:stream_pet:{self._stream_pet_instance}"
            patch = {"config": stream_pet_overlay_config_to_public_dict(cfg)}
            self._publish_patch(topic=topic, patch=patch)

    @Slot(QJSValue)
    def saveStreamPetOverlayConfigMap(self, cfg_js: QJSValue) -> None:
        plain = _qml_js_to_plain_cfg(cfg_js)
        _LOG.info("widgets ConfigMap save: stream_pet (plain_type=%s)", type(plain).__name__)
        if plain is None:
            _LOG.warning("widgets ConfigMap save: stream_pet rejected (null/undefined)")
            return
        txt = _qml_cfg_map_to_json_text(plain)
        if not txt or txt == "{}":
            _LOG.warning("widgets ConfigMap save: stream_pet rejected empty_or_non_serializable")
            return
        _LOG.info("widgets ConfigMap save: stream_pet ok json_len=%d", len(txt))
        self.saveStreamPetOverlayConfigJson(txt)

    @Slot(result="QVariantMap")
    def loadCommunityWorldOverlayConfigMap(self) -> dict[str, Any]:
        cfg = load_community_world_overlay_config()
        return json.loads(community_world_overlay_config_to_json_text(cfg))

    @Slot(result=str)
    def loadCommunityWorldOverlayConfigJson(self) -> str:
        cfg = load_community_world_overlay_config()
        return community_world_overlay_config_to_json_text(cfg)

    @Slot(str)
    def saveCommunityWorldOverlayConfigJson(self, cfg_json: str) -> None:
        txt = (cfg_json or "").strip()
        if not txt:
            return
        try:
            cfg = community_world_overlay_config_from_json_text(txt)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            _LOG.warning(
                "saveCommunityWorldOverlayConfigJson: rejected payload (%s): %s",
                exc.__class__.__name__,
                exc,
            )
            return
        save_community_world_overlay_config(cfg)
        _LOG.info("widgets overlay persisted: community_world")
        if self._pubsub is not None:
            topic = f"overlay:community_world:{self._community_world_instance}"
            patch = {"config": json.loads(community_world_overlay_config_to_json_text(cfg))}
            self._publish_patch(topic=topic, patch=patch)

    @Slot(QJSValue)
    def saveCommunityWorldOverlayConfigMap(self, cfg_js: QJSValue) -> None:
        plain = _qml_js_to_plain_cfg(cfg_js)
        _LOG.info("widgets ConfigMap save: community_world (plain_type=%s)", type(plain).__name__)
        if plain is None:
            _LOG.warning("widgets ConfigMap save: community_world rejected (null/undefined)")
            return
        txt = _qml_cfg_map_to_json_text(plain)
        if not txt or txt == "{}":
            _LOG.warning(
                "widgets ConfigMap save: community_world rejected empty_or_non_serializable"
            )
            return
        _LOG.info("widgets ConfigMap save: community_world ok json_len=%d", len(txt))
        self.saveCommunityWorldOverlayConfigJson(txt)

    @Slot(result="QVariant")
    def loadStreamGoalOverlayConfigMap(self) -> dict[str, Any]:
        cfg = load_stream_goal_overlay_config()
        return json.loads(stream_goal_overlay_config_to_json_text(cfg))

    @Slot(result=str)
    def loadStreamGoalOverlayConfigJson(self) -> str:
        cfg = load_stream_goal_overlay_config()
        return stream_goal_overlay_config_to_json_text(cfg)

    @Slot(str)
    def saveStreamGoalOverlayConfigJson(self, cfg_json: str) -> None:
        txt = (cfg_json or "").strip()
        if not txt:
            return
        try:
            cfg = stream_goal_overlay_config_from_json_text(txt)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            _LOG.warning(
                "saveStreamGoalOverlayConfigJson: rejected payload (%s): %s",
                exc.__class__.__name__,
                exc,
            )
            return
        save_stream_goal_overlay_config(cfg)
        _LOG.info("widgets overlay persisted: stream_goal")
        if self._stream_goal_controller is not None:
            try:
                self._stream_goal_controller.reload_config()
            except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
                _LOG.warning("Failed to reload stream_goal_controller config: %s", exc)
        if self._pubsub is not None:
            topic = f"overlay:stream_goal:{self._stream_goal_instance}"
            cfg_dict = json.loads(stream_goal_overlay_config_to_json_text(cfg))
            cur = int(cfg.current_value)
            tgt = int(cfg.target_value)
            prog = float(cur / tgt) if tgt > 0 else 0.0
            patch = {
                "config": cfg_dict,
                "goal_type": str(cfg.goal_type),
                "title": str(cfg.title),
                "subtitle": str(cfg.subtitle),
                "current_value": cur,
                "target_value": tgt,
                "progress": prog,
                "progress_percent": int(prog * 100),
                "remaining": max(0, tgt - cur),
                "skin": str(cfg.skin),
                "accent_color": str(cfg.accent_color),
                "scale_percent": int(cfg.scale_percent),
                "animation_intensity": str(cfg.animation_intensity),
                "enable_particles": bool(cfg.enable_particles),
                "enable_glitch": bool(cfg.enable_glitch),
            }
            self._publish_patch(topic=topic, patch=patch)

    @Slot(QJSValue)
    def saveStreamGoalOverlayConfigMap(self, cfg_js: QJSValue) -> None:
        plain = _qml_js_to_plain_cfg(cfg_js)
        _LOG.info("widgets ConfigMap save: stream_goal (plain_type=%s)", type(plain).__name__)
        if plain is None:
            _LOG.warning("widgets ConfigMap save: stream_goal rejected (null/undefined)")
            return
        txt = _qml_cfg_map_to_json_text(plain)
        if not txt or txt == "{}":
            _LOG.warning("widgets ConfigMap save: stream_goal rejected empty_or_non_serializable")
            return
        _LOG.info("widgets ConfigMap save: stream_goal ok json_len=%d", len(txt))
        self.saveStreamGoalOverlayConfigJson(txt)

    @Slot(result="QVariant")
    def loadLiveLeaderboardOverlayConfigMap(self) -> dict[str, Any]:
        cfg = load_live_leaderboard_overlay_config()
        return json.loads(live_leaderboard_overlay_config_to_json_text(cfg))

    @Slot(result=str)
    def loadLiveLeaderboardOverlayConfigJson(self) -> str:
        cfg = load_live_leaderboard_overlay_config()
        return live_leaderboard_overlay_config_to_json_text(cfg)

    @Slot(str)
    def saveLiveLeaderboardOverlayConfigJson(self, cfg_json: str) -> None:
        txt = (cfg_json or "").strip()
        if not txt:
            return
        try:
            cfg = live_leaderboard_overlay_config_from_json_text(txt)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            _LOG.warning(
                "saveLiveLeaderboardOverlayConfigJson: rejected payload (%s): %s",
                exc.__class__.__name__,
                exc,
            )
            return
        save_live_leaderboard_overlay_config(cfg)
        _LOG.info("widgets overlay persisted: live_leaderboard")
        if self._live_leaderboard_controller is not None:
            try:
                self._live_leaderboard_controller.reload_config()
            except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
                _LOG.warning("Failed to reload live_leaderboard_controller config: %s", exc)
        if self._pubsub is not None:
            topic = f"overlay:live_leaderboard:{self._live_leaderboard_instance}"
            if self._live_leaderboard_controller is not None:
                try:
                    patch = self._live_leaderboard_controller.initial_state()
                except (AttributeError, RuntimeError, TypeError, ValueError):
                    patch = {
                        "config": json.loads(live_leaderboard_overlay_config_to_json_text(cfg))
                    }
            else:
                patch = {"config": json.loads(live_leaderboard_overlay_config_to_json_text(cfg))}
            self._publish_patch(topic=topic, patch=patch)

    @Slot(QJSValue)
    def saveLiveLeaderboardOverlayConfigMap(self, cfg_js: QJSValue) -> None:
        plain = _qml_js_to_plain_cfg(cfg_js)
        _LOG.info("widgets ConfigMap save: live_leaderboard (plain_type=%s)", type(plain).__name__)
        if plain is None:
            _LOG.warning("widgets ConfigMap save: live_leaderboard rejected (null/undefined)")
            return
        txt = _qml_cfg_map_to_json_text(plain)
        if not txt or txt == "{}":
            _LOG.warning(
                "widgets ConfigMap save: live_leaderboard rejected empty_or_non_serializable"
            )
            return
        _LOG.info("widgets ConfigMap save: live_leaderboard ok json_len=%d", len(txt))
        self.saveLiveLeaderboardOverlayConfigJson(txt)

    @Slot(result="QVariant")
    def loadSocialRotatorOverlayConfigMap(self) -> dict[str, Any]:
        cfg = load_social_rotator_overlay_config()
        return json.loads(social_rotator_overlay_config_to_json_text(cfg))

    @Slot(result=str)
    def loadSocialRotatorOverlayConfigJson(self) -> str:
        cfg = load_social_rotator_overlay_config()
        return social_rotator_overlay_config_to_json_text(cfg)

    @Slot(str)
    def saveSocialRotatorOverlayConfigJson(self, cfg_json: str) -> None:
        txt = (cfg_json or "").strip()
        if not txt:
            return
        try:
            cfg = social_rotator_overlay_config_from_json_text(txt)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            _LOG.warning(
                "saveSocialRotatorOverlayConfigJson: rejected payload (%s): %s",
                exc.__class__.__name__,
                exc,
            )
            return
        save_social_rotator_overlay_config(cfg)
        _LOG.info("widgets overlay persisted: social_rotator")
        if self._social_rotator_controller is not None:
            try:
                self._social_rotator_controller.reload_config()
            except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
                _LOG.warning("Failed to reload social_rotator_controller config: %s", exc)
        if self._pubsub is not None:
            topic = f"overlay:social_rotator:{self._social_rotator_instance}"
            if self._social_rotator_controller is not None:
                try:
                    patch = self._social_rotator_controller.initial_state()
                except (AttributeError, RuntimeError, TypeError, ValueError):
                    patch = {"config": json.loads(social_rotator_overlay_config_to_json_text(cfg))}
            else:
                patch = {"config": json.loads(social_rotator_overlay_config_to_json_text(cfg))}
            self._publish_patch(topic=topic, patch=patch)

    @Slot(QJSValue)
    def saveSocialRotatorOverlayConfigMap(self, cfg_js: QJSValue) -> None:
        plain = _qml_js_to_plain_cfg(cfg_js)
        _LOG.info("widgets ConfigMap save: social_rotator (plain_type=%s)", type(plain).__name__)
        if plain is None:
            _LOG.warning("widgets ConfigMap save: social_rotator rejected (null/undefined)")
            return
        txt = _qml_cfg_map_to_json_text(plain)
        if not txt or txt == "{}":
            _LOG.warning(
                "widgets ConfigMap save: social_rotator rejected empty_or_non_serializable"
            )
            return
        _LOG.info("widgets ConfigMap save: social_rotator ok json_len=%d", len(txt))
        self.saveSocialRotatorOverlayConfigJson(txt)


class WidgetsWindowQmlApi(QObject):
    def __init__(self, *, view: QQuickView) -> None:
        super().__init__()
        self._view = view

    @Slot()
    def close(self) -> None:
        self._view.close()

    @Slot()
    def minimize(self) -> None:
        self._view.showMinimized()

    @Slot()
    def toggleMaximize(self) -> None:
        if self._view.visibility() == QQuickView.Visibility.Maximized:
            self._view.showNormal()
        else:
            self._view.showMaximized()

    @Slot(result=bool)
    def isMaximized(self) -> bool:
        return self._view.visibility() == QQuickView.Visibility.Maximized

    @Slot()
    def startMove(self) -> None:
        # Best effort: on supported platforms this enables native window dragging.
        try:
            self._view.startSystemMove()
        except (AttributeError, RuntimeError):
            return

    @Slot(int)
    def startResize(self, edges: int) -> None:
        # edges: Qt.Edge bitmask (Qt.LeftEdge | Qt.TopEdge | ...)
        try:
            self._view.startSystemResize(Qt.Edges(edges))
        except (AttributeError, RuntimeError, TypeError):
            return
