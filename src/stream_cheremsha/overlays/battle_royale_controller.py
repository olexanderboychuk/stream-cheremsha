from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject

from stream_cheremsha.battle_royale.controller import BattleRoyaleController
from stream_cheremsha.battle_royale.models import BattleFighter, BattlePhase
from stream_cheremsha.overlays.battle_royale_overlay_config import (
    battle_royale_overlay_config_to_json_text,
)
from stream_cheremsha.overlays.pubsub import OverlayPubSub

_LOG = logging.getLogger(__name__)
_PUBLISH_DEBOUNCE_MS = 200


class BattleRoyaleInstanceController(QObject):
    """Per-instance QObject adapter over the pure ``BattleRoyaleController`` engine.

    Mirrors ``BattleController`` (1v1/2v2): one engine per widget instance, each
    loading its own merged instance settings and publishing only to its own
    ``overlay:battle_royale:{instance}`` topic. There is intentionally no
    shared/singleton battle state.
    """

    OVERLAY_TYPE = "battle_royale"

    def __init__(
        self,
        *,
        pubsub: OverlayPubSub | None,
        get_locale: Callable[[], str],
        instance: str = "main",
        parent: QObject | None = None,
        config_loader: Callable[[], Any] | None = None,
        on_battle_ended: Callable[[BattleFighter | None, str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._pubsub = pubsub
        self._get_locale = get_locale
        self._instance = str(instance or "main").strip() or "main"
        self._config_loader = config_loader
        self._engine = BattleRoyaleController(config_loader=config_loader)
        self._on_battle_ended = on_battle_ended
        self._engine._on_battle_ended.append(self._forward_battle_ended)
        self._publish_handle: asyncio.TimerHandle | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._last_candidates = -1

    def _load_cfg(self):  # noqa: ANN202 - generic config object
        return self._engine.config()

    def config(self):  # noqa: ANN202 - generic config object
        return self._load_cfg()

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
        self._last_candidates = -1
        self.schedule_publish()

    def initial_state(self) -> dict[str, Any]:
        return self._build_state()

    def reset_for_new_stream(self) -> None:
        self._engine.reset()
        self._last_candidates = -1
        self.schedule_publish()
        self._publish_patch_sync()

    def phase_value(self) -> str:
        try:
            return str(self._engine.state().phase.value)
        except Exception:  # noqa: BLE001 - never break callers
            return str(BattlePhase.IDLE.value)

    def is_vip_user(self, user_key: str) -> bool:
        try:
            return bool(self._engine.is_vip_user(user_key))
        except Exception:  # noqa: BLE001 - never break chat path
            return False

    def start_manual(self, fighters: list[dict[str, str]]) -> bool:
        cfg = self._load_cfg()
        try:
            ok = bool(self._engine.start_manual(fighters, cfg=cfg))
        except Exception as exc:  # noqa: BLE001 - keep live on bad input
            _LOG.warning("battle_royale manual start failed: %s", exc)
            return False
        if ok:
            self.schedule_publish()
            self._publish_patch_sync()
        return ok

    def stop_battle(self) -> None:
        try:
            self._engine.stop()
        except Exception as exc:  # noqa: BLE001 - best effort
            _LOG.warning("battle_royale stop failed: %s", exc)
        self._last_candidates = -1
        self.schedule_publish()
        self._publish_patch_sync()

    def on_gift(
        self,
        sender: str,
        count: int,
        tiktok_coin_each: int = 0,
        gift_id: str = "",
        gift_name: str = "",
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
        # Unknown-price gifts (each=0) fall back to gift count so they still
        # qualify for auto-arm — same pattern as Battle/live_leaderboard.
        diamonds = c * each if each > 0 else c
        display = str(sender or "").strip()
        key = str(sender_user_key or "").strip()
        if not display and not key:
            return
        prev_phase = self._engine.state().phase
        try:
            hit = self._engine.on_gift(
                sender_user_key=key,
                sender_display=display,
                sender_avatar_url=str(sender_avatar_url or ""),
                diamonds=diamonds,
                gift_id=str(gift_id or ""),
                gift_name=str(gift_name or ""),
            )
        except Exception as exc:  # noqa: BLE001 - never break gift fan-out
            _LOG.warning("battle_royale on_gift failed: %s", exc)
            return
        new_phase = self._engine.state().phase
        if new_phase != prev_phase:
            self.schedule_publish()
            self._publish_patch_sync()
            return
        if hit is not None:
            self.schedule_publish()
            self._publish_patch_sync()
            return
        if new_phase == BattlePhase.IDLE:
            try:
                n = int(self._engine.count_auto_arm_candidates(cfg=self._load_cfg()))
            except Exception:  # noqa: BLE001 - counter is best effort
                return
            if n != self._last_candidates:
                self._last_candidates = n
                self.schedule_publish()

    def on_like(self, *args: Any, **kwargs: Any) -> None:
        return

    def on_follow(self, *args: Any, **kwargs: Any) -> None:
        return

    def tick_advance(self, now: float | None = None) -> bool:
        t = time.monotonic() if now is None else float(now)
        prev_phase = self._engine.state().phase
        try:
            changed = bool(self._engine.tick(now=t))
        except Exception as exc:  # noqa: BLE001 - never break shared tick
            _LOG.warning("battle_royale tick failed: %s", exc)
            return False
        if not changed:
            return False
        new_phase = self._engine.state().phase
        if prev_phase != BattlePhase.VICTORY and new_phase == BattlePhase.VICTORY:
            self._publish_patch_sync()
        else:
            self.schedule_publish()
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
            _LOG.warning("battle_royale build_state failed: %s", exc)
            return
        topic = f"overlay:{type(self).OVERLAY_TYPE}:{self._instance}"
        try:
            pubsub.publish_sync(topic, patch)
        except Exception as exc:  # noqa: BLE001 - state already mutated
            _LOG.warning("battle_royale publish failed: %s", exc)

    async def _publish_patch(self) -> None:
        self._publish_patch_sync()

    def _build_state(self) -> dict[str, Any]:
        cfg = self._load_cfg()
        try:
            locale = str(self._get_locale() or "uk")
        except Exception:  # noqa: BLE001
            locale = "uk"
        try:
            cfg_payload = json.loads(battle_royale_overlay_config_to_json_text(cfg))
        except Exception:  # noqa: BLE001 - engine patch still valuable
            cfg_payload = {}
        return {
            "config": cfg_payload,
            "locale": locale,
            **self._engine.overlay_patch(),
        }

    def _forward_battle_ended(self, winner: BattleFighter | None) -> None:
        cb = self._on_battle_ended
        if cb is None:
            return
        try:
            cb(winner, self._instance)
        except Exception as exc:  # noqa: BLE001 - side effects must not break engine
            _LOG.warning("battle_royale ended callback failed: %s", exc)
