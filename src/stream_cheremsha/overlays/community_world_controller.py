from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject

from stream_cheremsha.overlays.community_world_config import (
    community_world_overlay_config_to_public_dict,
    load_community_world_overlay_config,
)
from stream_cheremsha.overlays.community_world_session import (
    CommunityWorldSession,
)
from stream_cheremsha.overlays.pubsub import OverlayPubSub
from stream_cheremsha.persistence.community_world_sqlite import (
    award_community_badge,
    fetch_village_elders,
)

_LOG = logging.getLogger(__name__)
_PUBLISH_DEBOUNCE_MS = 220
_BADGES_MAX_PERSIST = 12


class CommunityWorldController(QObject):
    """Owns the live Community World session and publishes overlay patches.

    Mirrors ``StreamPetController``: a QObject holding the session, with a
    debounced publish to ``overlay:community_world:{instance}``. Long-term
    viewer badges are persisted best-effort to SQLite.
    """

    def __init__(
        self,
        *,
        pubsub: OverlayPubSub | None,
        get_locale: Callable[[], str],
        instance: str = "main",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._pubsub = pubsub
        self._get_locale = get_locale
        self._instance = str(instance or "main").strip() or "main"
        cfg = load_community_world_overlay_config()
        self._session = CommunityWorldSession.fresh(cfg)
        self._publish_handle: asyncio.TimerHandle | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_pubsub(self, pubsub: OverlayPubSub | None) -> None:
        self._pubsub = pubsub

    def set_event_loop(self, loop: asyncio.AbstractEventLoop | None) -> None:
        self._loop = loop

    def start(self) -> None:
        self._reload_config()
        self.schedule_publish()

    def stop(self) -> None:
        if self._publish_handle is not None:
            self._publish_handle.cancel()
            self._publish_handle = None

    def reset_session(self) -> None:
        self._session = CommunityWorldSession.fresh(load_community_world_overlay_config())
        self.schedule_publish()

    def reload_config(self) -> None:
        self._reload_config()
        self.schedule_publish()

    def initial_state(self) -> dict[str, Any]:
        cfg = load_community_world_overlay_config()
        state = self._session.to_overlay_dict()
        state["config"] = community_world_overlay_config_to_public_dict(cfg)
        state["elders"] = fetch_village_elders(limit=8)
        state["locale"] = str(self._get_locale() or "uk")
        return state

    def on_chat(self, *, user: str, text: str) -> None:
        cfg = load_community_world_overlay_config()
        if not cfg.enabled:
            return
        self._session.on_chat(user=user, text=text)
        self.schedule_publish()

    def on_follow(self, *, user: str, user_key: str = "", avatar_url: str = "") -> None:
        cfg = load_community_world_overlay_config()
        if not cfg.enabled:
            return
        self._session.on_follow(user=user, user_key=user_key, avatar_url=avatar_url)
        self._persist_session_badges()
        self.schedule_publish()

    def on_join(self, *, user: str, user_key: str = "") -> None:
        cfg = load_community_world_overlay_config()
        if not cfg.enabled:
            return
        self._session.on_join(user=user, user_key=user_key)
        self.schedule_publish()

    def on_like(
        self,
        *,
        user: str,
        n: int,
        user_key: str = "",
        avatar_url: str = "",
    ) -> None:
        cfg = load_community_world_overlay_config()
        if not cfg.enabled:
            return
        self._session.on_like(user=user, n=n, user_key=user_key, avatar_url=avatar_url)
        self._persist_session_badges()
        self.schedule_publish()

    def on_share(self, *, user: str, n: int, user_key: str = "") -> None:
        cfg = load_community_world_overlay_config()
        if not cfg.enabled:
            return
        self._session.on_share(user=user, n=n, user_key=user_key)
        self._persist_session_badges()
        self.schedule_publish()

    def on_gift(
        self,
        *,
        user: str,
        user_key: str = "",
        gift_name: str = "",
        coins: int = 0,
        icon_url: str = "",
        avatar_url: str = "",
    ) -> None:
        cfg = load_community_world_overlay_config()
        if not cfg.enabled:
            return
        self._session.on_gift(
            user=user,
            user_key=user_key,
            gift_name=gift_name,
            coins=coins,
            icon_url=icon_url,
            avatar_url=avatar_url,
        )
        self._persist_session_badges()
        self.schedule_publish()

    def on_battle_win(
        self,
        *,
        user: str,
        user_key: str = "",
        avatar_url: str = "",
    ) -> None:
        cfg = load_community_world_overlay_config()
        if not cfg.enabled:
            return
        self._session.on_battle_win(user=user, user_key=user_key, avatar_url=avatar_url)
        self._persist_session_badges()
        self.schedule_publish()

    def schedule_publish(self) -> None:
        loop = self._loop
        pubsub = self._pubsub
        if loop is None or pubsub is None:
            return
        if self._publish_handle is not None:
            self._publish_handle.cancel()
        delay = _PUBLISH_DEBOUNCE_MS / 1000.0

        def _fire() -> None:
            self._publish_handle = None
            asyncio.ensure_future(self._publish_patch())

        self._publish_handle = loop.call_later(delay, _fire)

    async def _publish_patch(self) -> None:
        pubsub = self._pubsub
        if pubsub is None:
            return
        cfg = load_community_world_overlay_config()
        patch = self._session.to_overlay_dict()
        patch["config"] = community_world_overlay_config_to_public_dict(cfg)
        patch["elders"] = fetch_village_elders(limit=8)
        patch["locale"] = str(self._get_locale() or "uk")
        topic = f"overlay:community_world:{self._instance}"
        await pubsub.publish(topic, patch)
        self._session.consume_pending_buildings()

    def _persist_session_badges(self) -> None:
        """Best-effort persist badges earned during the session to SQLite."""
        try:
            viewers = self._session.passports(limit=_BADGES_MAX_PERSIST)
            for v in viewers:
                for badge in v.get("badges") or []:
                    award_community_badge(
                        user_key=str(v.get("key") or "") or str(v.get("user") or ""),
                        display_name=str(v.get("user") or "?"),
                        badge=str(badge),
                        avatar_url=str(v.get("avatar_url") or ""),
                    )
        except Exception:  # noqa: BLE001 - persistence must never break the stream
            _LOG.debug("community_world: badge persistence skipped", exc_info=True)

    def _reload_config(self) -> None:
        cfg = load_community_world_overlay_config()
        if self._session.cfg != cfg:
            self._session.cfg = cfg
