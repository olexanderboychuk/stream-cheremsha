from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from PySide6.QtCore import QObject, QTimer

from stream_cheremsha import l10n
from stream_cheremsha.overlays.pubsub import OverlayPubSub
from stream_cheremsha.overlays.stream_pet_overlay_config import (
    load_stream_pet_overlay_config,
    stream_pet_overlay_config_to_public_dict,
)
from stream_cheremsha.overlays.stream_pet_phrases import (
    HUNGRY_DONOR_FALLBACK_KEY,
    HUNGRY_DONOR_PHRASE_KEY,
    LEVEL3_VIP_KEYS,
    SLEEP_PHRASE_KEYS,
    thanks_templates_for,
)
from stream_cheremsha.overlays.stream_pet_session import (
    GiftTier,
    StreamPetEventKind,
    StreamPetSession,
    StreamPetSpeechKind,
    classify_gift_tier,
    event_anim,
    is_sleep_command,
    is_wake_command,
    truncate_stream_pet_phrase,
)

_LOG = logging.getLogger(__name__)
_PUBLISH_DEBOUNCE_MS = 200
_VIP_TIMER_MS = 60_000


class StreamPetController(QObject):
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
        cfg = load_stream_pet_overlay_config()
        self._session = StreamPetSession.fresh(cfg)
        self._publish_handle: asyncio.TimerHandle | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

        self._decay_timer = QTimer(self)
        self._decay_timer.setInterval(60_000)
        self._decay_timer.timeout.connect(self._on_decay_tick)

        self._sleep_timer = QTimer(self)
        self._sleep_timer.setInterval(30_000)
        self._sleep_timer.timeout.connect(self._on_sleep_watch)

        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(15_000)
        self._idle_timer.timeout.connect(self._on_idle_check)

        self._vip_timer = QTimer(self)
        self._vip_timer.setInterval(_VIP_TIMER_MS)
        self._vip_timer.timeout.connect(self._on_vip_tick)

    def set_pubsub(self, pubsub: OverlayPubSub | None) -> None:
        self._pubsub = pubsub

    def set_event_loop(self, loop: asyncio.AbstractEventLoop | None) -> None:
        self._loop = loop

    def start(self) -> None:
        self._reload_config()
        self._decay_timer.start()
        self._sleep_timer.start()
        self._idle_timer.start()
        self._vip_timer.start()
        self.schedule_publish()

    def stop(self) -> None:
        self._decay_timer.stop()
        self._sleep_timer.stop()
        self._idle_timer.stop()
        self._vip_timer.stop()
        if self._publish_handle is not None:
            self._publish_handle.cancel()
            self._publish_handle = None

    def reset_session(self) -> None:
        cfg = load_stream_pet_overlay_config()
        self._session = StreamPetSession.fresh(cfg)
        self.schedule_publish()

    def reset_for_new_stream(self) -> None:
        self._session.reset_for_new_stream()
        self.schedule_publish()

    def reload_config(self) -> None:
        self._reload_config()
        self.schedule_publish()

    def initial_state(self) -> dict[str, Any]:
        cfg = load_stream_pet_overlay_config()
        now = datetime.now(UTC)
        state = self._session.to_overlay_dict(now=now)
        state["config"] = stream_pet_overlay_config_to_public_dict(cfg)
        state["speech"] = self._resolved_speech_dict()
        return state

    def on_chat(self, *, author: str, text: str) -> None:
        cfg = load_stream_pet_overlay_config()
        if not cfg.enabled:
            return
        now = datetime.now(UTC)
        body = (text or "").strip()

        if is_sleep_command(body):
            phrase_key = random.choice(SLEEP_PHRASE_KEYS)
            phrase = self._truncate(self._tr(phrase_key))
            if self._session.force_sleep(now, phrase=phrase):
                self.schedule_publish()
            return

        if is_wake_command(body):
            if self._session.on_chat(author=author, text=body, now=now)[0]:
                self._after_session_change(now)
            return

        changed, event_kind = self._session.on_chat(author=author, text=body, now=now)
        if event_kind is not None:
            anim = event_anim(event_kind)
            phrase = self._thanks_phrase(event_kind, author)
            self._session.emit_reaction(
                now,
                author=author,
                phrase=phrase,
                anim=anim,
            )
            changed = True
        if changed:
            self._after_session_change(now)

    def on_follow(self, *, user: str) -> None:
        cfg = load_stream_pet_overlay_config()
        if not cfg.enabled:
            return
        now = datetime.now(UTC)
        phrase = self._thanks_phrase(StreamPetEventKind.FOLLOW, user)
        if self._session.on_follow(user=user, now=now, phrase=phrase):
            self._after_session_change(now)

    def on_join(self, *, user: str) -> None:
        cfg = load_stream_pet_overlay_config()
        if not cfg.enabled:
            return
        now = datetime.now(UTC)
        phrase = self._thanks_phrase(StreamPetEventKind.JOIN, user)
        if self._session.on_join(user=user, now=now, phrase=phrase):
            self._after_session_change(now)

    def on_like_burst(self, *, user: str) -> None:
        cfg = load_stream_pet_overlay_config()
        if not cfg.enabled:
            return
        now = datetime.now(UTC)
        phrase = self._thanks_phrase(StreamPetEventKind.LIKE, user)
        if self._session.on_like(user=user, now=now, phrase=phrase):
            self._after_session_change(now)

    def on_member(self, *, user: str) -> None:
        cfg = load_stream_pet_overlay_config()
        if not cfg.enabled:
            return
        now = datetime.now(UTC)
        phrase = self._thanks_phrase(StreamPetEventKind.MEMBER, user)
        if self._session.on_member(user=user, now=now, phrase=phrase):
            self._after_session_change(now)

    def on_gift(
        self,
        *,
        platform: str,
        user: str,
        gift_name: str = "",
        tiktok_coins: int = 0,
        twitch_bits: int = 0,
        youtube_amount_micros: int = 0,
    ) -> None:
        cfg = load_stream_pet_overlay_config()
        if not cfg.enabled:
            return
        tier = classify_gift_tier(
            platform=platform,
            cfg=cfg,
            tiktok_coins=tiktok_coins,
            twitch_bits=twitch_bits,
            youtube_amount_micros=youtube_amount_micros,
        )
        now = datetime.now(UTC)
        label_name = (gift_name or "").strip() or self._default_gift_label(platform, tier)
        if tier == GiftTier.LARGE:
            kind = StreamPetEventKind.GIFT_LARGE
            anim = "shake"
        else:
            kind = StreamPetEventKind.GIFT
            anim = event_anim(kind)
        phrase = self._thanks_phrase(kind, user, gift_name=label_name)

        if self._session.on_gift(
            user=user,
            tier=tier,
            gift_name=label_name,
            now=now,
            phrase=phrase,
            anim=anim,
        ):
            self._after_session_change(now)

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
        cfg = load_stream_pet_overlay_config()
        now = datetime.now(UTC)
        patch = self._session.to_overlay_dict(now=now)
        patch["speech"] = self._resolved_speech_dict()
        patch["config"] = stream_pet_overlay_config_to_public_dict(cfg)
        topic = f"overlay:stream_pet:{self._instance}"
        await pubsub.publish(topic, patch)

    def _on_decay_tick(self) -> None:
        cfg = load_stream_pet_overlay_config()
        if not cfg.enabled:
            return
        now = datetime.now(UTC)
        if self._session.tick_decay(now):
            self.schedule_publish()

    def _on_sleep_watch(self) -> None:
        cfg = load_stream_pet_overlay_config()
        if not cfg.enabled:
            return
        now = datetime.now(UTC)
        if self._session.check_auto_sleep(now):
            phrase_key = random.choice(SLEEP_PHRASE_KEYS)
            phrase = self._truncate(self._tr(phrase_key))
            self._session.speech = self._session.speech or None
            if self._session.speech is not None:
                self._session.speech.text = phrase
            self.schedule_publish()

    def _on_idle_check(self) -> None:
        cfg = load_stream_pet_overlay_config()
        if not cfg.enabled:
            return
        now = datetime.now(UTC)
        if self._session.check_idle_bubble(now):
            self._resolve_session_speech()
            self.schedule_publish()

    def _on_vip_tick(self) -> None:
        cfg = load_stream_pet_overlay_config()
        if not cfg.enabled or self._session.level < 3:
            return
        interval_ms = max(30_000, int(cfg.level3_vip_interval_sec) * 1000)
        if self._vip_timer.interval() != interval_ms:
            self._vip_timer.setInterval(interval_ms)
        now = datetime.now(UTC)
        if self._emit_vip_bonus(now):
            self.schedule_publish()

    def _schedule_deferred_vip(self) -> None:
        QTimer.singleShot(6200, self._deferred_vip_bonus)

    def _deferred_vip_bonus(self) -> None:
        cfg = load_stream_pet_overlay_config()
        if not cfg.enabled or self._session.level < 3:
            return
        now = datetime.now(UTC)
        if self._emit_vip_bonus(now):
            self.schedule_publish()

    def _after_session_change(self, now: datetime) -> None:
        if self._session.vip_bonus_due and self._session.level >= 3:
            self._session.vip_bonus_due = False
            self._schedule_deferred_vip()
        self.schedule_publish()

    def _emit_vip_bonus(self, now: datetime, *, allow_overwrite: bool = True) -> bool:
        if self._session.level < 3:
            return False
        if (
            not allow_overwrite
            and self._session.speech is not None
            and self._session.speech.kind == StreamPetSpeechKind.REACTION
        ):
            return False
        viewer = self._session.pick_vip_viewer()
        if not viewer:
            return False
        key = random.choice(LEVEL3_VIP_KEYS)
        return self._session.emit_vip_bonus(now, phrase_key=key, user=viewer)

    def _reload_config(self) -> None:
        cfg = load_stream_pet_overlay_config()
        self._session.cfg = cfg
        interval_ms = max(30_000, int(cfg.level3_vip_interval_sec) * 1000)
        self._vip_timer.setInterval(interval_ms)

    def _resolved_speech_dict(self) -> dict[str, Any] | None:
        self._resolve_session_speech()
        sp = self._session.speech
        if sp is None:
            return None
        return sp.to_dict()

    def _thanks_phrase(
        self,
        kind: StreamPetEventKind,
        user: str,
        *,
        gift_name: str = "",
    ) -> str:
        event = self._event_label(kind, gift_name=gift_name)
        template = random.choice(thanks_templates_for(kind, self._session.level))
        text = self._tr(template, user=self._mention(user), event=event)
        return self._truncate(text)

    def _event_label(self, kind: StreamPetEventKind, *, gift_name: str = "") -> str:
        if kind in (StreamPetEventKind.GIFT, StreamPetEventKind.GIFT_LARGE):
            name = (gift_name or "").strip() or self._tr("stream_pet.event_label.gift_fallback")
            return self._tr("stream_pet.event_label.gift", gift_name=name)
        if kind == StreamPetEventKind.SPAM:
            return self._tr("stream_pet.event_label.spam")
        return self._tr(f"stream_pet.event_label.{kind.value}")

    def _default_gift_label(self, platform: str, tier: GiftTier) -> str:
        plat = (platform or "").strip().lower()
        if plat == "twitch":
            return self._tr("stream_pet.event_label.cheer_fallback")
        if plat == "youtube":
            return self._tr("stream_pet.event_label.superchat_fallback")
        if tier == GiftTier.LARGE:
            return self._tr("stream_pet.event_label.gift_big_fallback")
        return self._tr("stream_pet.event_label.gift_fallback")

    def _resolve_session_speech(self) -> None:
        sp = self._session.speech
        if sp is None:
            return
        key = sp.text
        if not key.startswith("stream_pet."):
            sp.text = self._truncate(key)
            return
        if key == HUNGRY_DONOR_PHRASE_KEY:
            if self._session.last_donor_name:
                sp.text = self._truncate(
                    self._tr(key, last_donor=self._session.last_donor_name),
                )
            else:
                sp.text = self._truncate(self._tr(HUNGRY_DONOR_FALLBACK_KEY))
            return
        if key.startswith("stream_pet.l3.vip."):
            sp.text = self._truncate(self._tr(key, user=self._mention(sp.user)))
            return
        sp.text = self._truncate(self._tr(key))

    def _truncate(self, text: str) -> str:
        return truncate_stream_pet_phrase(text, self._session.cfg.bubble_max_chars)

    def _tr(self, key: str, **kwargs: object) -> str:
        return l10n.tr(self._get_locale(), key, **kwargs)

    @staticmethod
    def _mention(user: str) -> str:
        u = (user or "").strip()
        if not u:
            return "?"
        return u if u.startswith("@") else f"@{u}"
