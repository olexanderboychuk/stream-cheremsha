from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject

from stream_cheremsha.battle.engine import BattleEngine
from stream_cheremsha.overlays.battle_overlay_config import (
    battle_overlay_config_to_public_dict,
    load_battle_overlay_config,
)
from stream_cheremsha.overlays.pubsub import OverlayPubSub

_LOG = logging.getLogger(__name__)
_PUBLISH_DEBOUNCE_MS = 200

_DECISION_EVENT_TYPES = frozenset(
    {"battle_finished", "comeback", "final_push", "big_gift", "close_battle"}
)


class BattleController(QObject):
    OVERLAY_TYPE = "battle"

    def __init__(
        self,
        *,
        pubsub: OverlayPubSub | None,
        get_locale: Callable[[], str],
        instance: str = "main",
        parent: QObject | None = None,
        config_loader: Callable[[], Any] | None = None,
    ) -> None:
        super().__init__(parent)
        self._pubsub = pubsub
        self._get_locale = get_locale
        self._instance = str(instance or "main").strip() or "main"
        self._config_loader = config_loader
        self._engine = BattleEngine(self._load_cfg)
        self._publish_handle: asyncio.TimerHandle | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._decision = None
        self._last_remaining = -1
        self._last_countdown = -1

    def _load_cfg(self):  # noqa: ANN202 - generic config object
        if self._config_loader is not None:
            return self._config_loader()
        return load_battle_overlay_config()

    def set_pubsub(self, pubsub: OverlayPubSub | None) -> None:
        self._pubsub = pubsub

    def set_event_loop(self, loop: asyncio.AbstractEventLoop | None) -> None:
        self._loop = loop

    def start(self) -> None:
        self.reload_config()
        self.schedule_publish()

    def stop(self) -> None:
        if self._publish_handle is not None:
            try:
                self._publish_handle.cancel()
            except Exception:  # noqa: BLE001 - best effort teardown
                pass
            self._publish_handle = None

    def reload_config(self) -> None:
        try:
            cfg = self._load_cfg()
            best_of = int(getattr(cfg, "best_of", 3))
        except Exception:  # noqa: BLE001 - keep live battle on bad config
            best_of = 3
        try:
            live_best = int(self._engine.snapshot().get("best_of", best_of))
        except Exception:  # noqa: BLE001
            live_best = best_of
        status = str(self._engine.snapshot().get("status", "idle"))
        if best_of != live_best and status == "idle":
            self._engine.reset()
        self.schedule_publish()

    def initial_state(self) -> dict[str, Any]:
        return self._build_state()

    def reset_for_new_stream(self) -> None:
        self._engine.reset()
        self._last_remaining = -1
        self._last_countdown = -1
        self.schedule_publish()
        self._publish_patch_sync()

    def on_gift(
        self,
        sender: str,
        count: int,
        tiktok_coin_each: int = 0,
        sender_avatar_url: str = "",
        sender_user_key: str = "",
    ) -> None:
        try:
            c = max(1, int(count))
        except (TypeError, ValueError):
            c = 1
        try:
            each = max(0, int(tiktok_coin_each or 0))
        except (TypeError, ValueError):
            each = 0
        coins = c * each if each > 0 else c
        display = str(sender or "").strip()
        key = str(sender_user_key or "").strip()
        if not display and not key:
            return
        events = self._engine.on_gift(
            user_key=key or display,
            display=display or "?",
            avatar_url=str(sender_avatar_url or ""),
            diamonds=coins,
        )
        if not events:
            return
        self._maybe_decide(events)
        self.schedule_publish()
        types = {str(e.get("type") or "") for e in events if isinstance(e, dict)}
        if types & {"battle_finished", "round_finished"}:
            self._publish_patch_sync()

    def on_like(self, *args: Any, **kwargs: Any) -> None:
        return

    def on_follow(self, *args: Any, **kwargs: Any) -> None:
        return

    def tick_advance(self, now: float | None = None) -> bool:
        t = time.monotonic() if now is None else float(now)
        events = self._engine.tick(t)
        snap = self._engine.snapshot()
        remaining = int(snap.get("remaining_seconds", -1))
        countdown = int(snap.get("countdown_remaining_s", -1))
        dirty = bool(events)
        if remaining != self._last_remaining or countdown != self._last_countdown:
            dirty = True
            self._last_remaining = remaining
            self._last_countdown = countdown
        if not dirty:
            return False
        if events:
            self._maybe_decide(events)
        self.schedule_publish()
        types = set()
        for e in events:
            if isinstance(e, dict):
                types.add(str(e.get("type") or ""))
        if "battle_finished" in types:
            self._publish_patch_sync()
        return True

    def schedule_publish(self) -> None:
        loop = self._loop
        pubsub = self._pubsub
        if loop is None or pubsub is None:
            return
        if self._publish_handle is not None:
            try:
                self._publish_handle.cancel()
            except Exception:  # noqa: BLE001
                pass
        delay = _PUBLISH_DEBOUNCE_MS / 1000.0

        def _fire() -> None:
            self._publish_handle = None
            self._publish_patch_sync()

        try:
            self._publish_handle = loop.call_later(delay, _fire)
        except Exception:  # noqa: BLE001 - loop closed in tests
            self._publish_handle = None

    def _publish_patch_sync(self) -> None:
        pubsub = self._pubsub
        if pubsub is None:
            return
        try:
            patch = self._build_state()
        except Exception as exc:  # noqa: BLE001 - never break callers
            _LOG.warning("battle build_state failed: %s", exc)
            return
        topic = f"overlay:{type(self).OVERLAY_TYPE}:{self._instance}"
        try:
            pubsub.publish_sync(topic, patch)
        except Exception as exc:  # noqa: BLE001 - state already mutated
            _LOG.warning("battle publish failed: %s", exc)

    async def _publish_patch(self) -> None:
        self._publish_patch_sync()

    def _build_state(self) -> dict[str, Any]:
        cfg = self._load_cfg()
        snap = self._engine.snapshot()
        try:
            locale = str(self._get_locale() or "uk")
        except Exception:  # noqa: BLE001
            locale = "uk"
        return {
            "config": battle_overlay_config_to_public_dict(cfg),
            "locale": locale,
            **snap,
        }

    def _maybe_decide(self, events: list[dict[str, Any]]) -> None:
        try:
            cfg = self._load_cfg()
            enabled = bool(getattr(cfg, "decision_layer_enabled", False))
        except Exception:  # noqa: BLE001
            return
        if not enabled or self._decision is None:
            return
        decide = getattr(self._decision, "decide", None)
        if not callable(decide):
            return
        for ev in events:
            if not isinstance(ev, dict):
                continue
            if str(ev.get("type") or "") not in _DECISION_EVENT_TYPES:
                continue
            try:
                decision = decide(dict(ev))
                to_dict = getattr(decision, "to_dict", None)
                payload = ev.setdefault("payload", {})
                if callable(to_dict) and isinstance(payload, dict):
                    payload["decision"] = dict(to_dict())
            except Exception as exc:  # noqa: BLE001 - core events already emitted
                _LOG.warning("battle decision hook failed: %s", exc)
            break
