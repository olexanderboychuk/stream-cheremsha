from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Coroutine, Mapping
from datetime import datetime
from typing import Any

import httpx

from stream_cheremsha.actions.action_placeholders import apply_action_placeholders
from stream_cheremsha.actions.actions_launch_program import launch_program
from stream_cheremsha.actions.actions_play_sound import play_sound_from_file
from stream_cheremsha.actions.actions_write_file import write_text_to_file
from stream_cheremsha.actions.events import (
    ChatMessageEvent,
    GiftReceivedEvent,
    TikTokFirstActivityEvent,
    TikTokFollowedEvent,
    TikTokJoinedEvent,
    TikTokLikesReceivedEvent,
    TikTokPaidSubscribedEvent,
    TikTokSharedEvent,
    TwitchCheerEvent,
    TwitchFollowEvent,
    TwitchRaidEvent,
    TwitchResubscribeEvent,
    TwitchSubscribeEvent,
    TwitchSubscriptionGiftEvent,
)
from stream_cheremsha.actions.models import RuleV1
from stream_cheremsha.actions.registry import match_chat_keyword
from stream_cheremsha.actions.tiktok_gifts import TIKTOK_GIFTS, tiktok_catalog_gift_image_url
from stream_cheremsha.actions.trigger_meta import (
    trigger_platform_applies_to_chat,
    trigger_platform_applies_to_gift,
    trigger_platform_applies_to_tiktok_likes,
    trigger_platform_applies_to_twitch_channel_events,
)
from stream_cheremsha.config.constants import MAX_MESSAGE_CHARS
from stream_cheremsha.domain.models import ChatPlatform
from stream_cheremsha.domain.protocols import AudioSink
from stream_cheremsha.overlays.pubsub import OverlayPubSub

logger = logging.getLogger(__name__)

StatusCallback = Callable[[str], None]
ObsExecute = Callable[[dict[str, Any]], Awaitable[None]]

_MAX_OBS_REVERT_DELAY_S = 3600.0


def _obs_visible_from_params(raw: object) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    if isinstance(raw, str):
        s = raw.strip().lower()
        if s in ("0", "false", "no", "off", ""):
            return False
        if s in ("1", "true", "yes", "on"):
            return True
        return True
    if raw is None:
        return True
    return True


def _obs_bool_flag(raw: object, *, default: bool = False) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    if isinstance(raw, str):
        s = raw.strip().lower()
        if s in ("0", "false", "no", "off", ""):
            return False
        if s in ("1", "true", "yes", "on"):
            return True
        return default
    if raw is None:
        return default
    return default


def _obs_revert_delay_seconds(raw: object, ev: object) -> float:
    if isinstance(raw, str):
        st = apply_action_placeholders(raw, ev).strip()
    elif isinstance(raw, (int, float)):
        st = str(raw)
    elif raw is None:
        return 0.0
    else:
        st = str(raw).strip()
    if not st:
        return 0.0
    try:
        v = float(st.replace(",", "."))
    except ValueError:
        return 0.0
    return max(0.0, min(float(_MAX_OBS_REVERT_DELAY_S), v))


def _show_overlay_platform_slug(ev: object) -> str:
    """Lowercase ChatPlatform value for Actions overlay (embedded SVG data URIs)."""
    p = getattr(ev, "platform", None)
    if isinstance(p, ChatPlatform):
        return str(p.value)
    if isinstance(p, str):
        s = p.strip().lower()
        if s in ("tiktok", "twitch", "youtube"):
            return s
    return ""
TtsSpeakCallback = Callable[[str], Awaitable[None]]


def _chat_trigger_matches(
    ev_blob: Mapping[str, Any],
    ev: ChatMessageEvent,
    *,
    rule_id: str,
    status: StatusCallback,
) -> bool:
    if ev_blob.get("type") != "chat_keyword":
        return False
    params: Any = ev_blob.get("params")
    if not isinstance(params, dict):
        status(f"Rule {rule_id}: event.params must be an object")
        return False
    keyword = params.get("text", params.get("keyword"))
    if not isinstance(keyword, str) or not keyword.strip():
        status(f"Rule {rule_id}: chat keyword is required")
        return False
    keyword = keyword.strip()
    mode = params.get("match", params.get("mode", "contains"))
    case_sensitive = bool(params.get("case_sensitive", False))
    try:
        return match_chat_keyword(
            ev.text,
            keyword,
            mode=mode,  # type: ignore[arg-type]
            case_sensitive=case_sensitive,
        )
    except ValueError as e:
        status(f"Rule {rule_id}: invalid chat_keyword params: {e}")
        return False


def _gift_trigger_matches(ev_blob: Mapping[str, Any], ev: GiftReceivedEvent, *, rule_id: str, status: StatusCallback) -> bool:
    if ev_blob.get("type") != "gift_received":
        return False
    params: Any = ev_blob.get("params")
    if not isinstance(params, dict):
        status(f"Rule {rule_id}: event.params must be an object")
        return False
    min_count_raw = params.get("min_count", 1)
    try:
        min_count = int(min_count_raw)
    except (TypeError, ValueError):
        status(f"Rule {rule_id}: min_count must be an integer")
        return False
    if min_count < 1:
        min_count = 1
    gift_id = params.get("gift_id")
    gift_name = params.get("gift_name")
    match_ok = False
    if isinstance(gift_id, str) and gift_id.strip():
        match_ok = ev.gift_id.strip() == gift_id.strip()
    elif isinstance(gift_name, str) and gift_name.strip():
        match_ok = ev.gift_name.strip().casefold() == gift_name.strip().casefold()
    else:
        status(f"Rule {rule_id}: gift_id or gift_name is required")
        return False
    return match_ok and int(ev.count) >= min_count


def _norm_like_user(name: str) -> str:
    return (name or "").strip().casefold()


def _norm_simple_user(name: str) -> str:
    return (name or "").strip().casefold()


def _tiktok_simple_user_matches(rule_user: object, actual_user: str) -> bool:
    """Return True if optional `user` filter matches; empty filter matches any."""
    ru = _norm_simple_user(str(rule_user) if rule_user is not None else "")
    if not ru:
        return True
    return _norm_simple_user(actual_user) == ru


def _tiktok_simple_user_trigger_matches(
    ev_blob: Mapping[str, Any],
    *,
    expected_type: str,
    rule_id: str,
    status: StatusCallback,
    actual_user: str,
) -> bool:
    if ev_blob.get("type") != expected_type:
        return False
    params: Any = ev_blob.get("params")
    if not isinstance(params, dict):
        status(f"Rule {rule_id}: event.params must be an object")
        return False
    return _tiktok_simple_user_matches(params.get("user", ""), actual_user)


def _twitch_cheer_trigger_matches(
    ev_blob: Mapping[str, Any],
    *,
    rule_id: str,
    status: StatusCallback,
    actual_user: str,
    bits: int,
) -> bool:
    if ev_blob.get("type") != "twitch_cheer":
        return False
    params: Any = ev_blob.get("params")
    if not isinstance(params, dict):
        status(f"Rule {rule_id}: event.params must be an object")
        return False
    min_bits_raw = params.get("min_bits", 1)
    try:
        min_bits = int(min_bits_raw)
    except (TypeError, ValueError):
        status(f"Rule {rule_id}: min_bits must be an integer")
        return False
    if min_bits < 1:
        min_bits = 1
    if not _tiktok_simple_user_matches(params.get("user", ""), actual_user):
        return False
    return int(bits) >= min_bits


def _twitch_raid_trigger_matches(
    ev_blob: Mapping[str, Any],
    *,
    rule_id: str,
    status: StatusCallback,
    raider: str,
    viewers: int,
) -> bool:
    if ev_blob.get("type") != "twitch_raid":
        return False
    params: Any = ev_blob.get("params")
    if not isinstance(params, dict):
        status(f"Rule {rule_id}: event.params must be an object")
        return False
    min_v_raw = params.get("min_viewers", 1)
    try:
        min_v = int(min_v_raw)
    except (TypeError, ValueError):
        status(f"Rule {rule_id}: min_viewers must be an integer")
        return False
    if min_v < 1:
        min_v = 1
    if not _tiktok_simple_user_matches(params.get("user", ""), raider):
        return False
    return int(viewers) >= min_v


def _tiktok_share_trigger_matches(
    ev_blob: Mapping[str, Any],
    *,
    rule_id: str,
    status: StatusCallback,
    actual_user: str,
    count: int,
) -> bool:
    if ev_blob.get("type") != "tiktok_shared":
        return False
    params: Any = ev_blob.get("params")
    if not isinstance(params, dict):
        status(f"Rule {rule_id}: event.params must be an object")
        return False
    min_count_raw = params.get("min_count", 1)
    try:
        min_count = int(min_count_raw)
    except (TypeError, ValueError):
        status(f"Rule {rule_id}: min_count must be an integer")
        return False
    if min_count < 1:
        min_count = 1
    if not _tiktok_simple_user_matches(params.get("user", ""), actual_user):
        return False
    return int(count) >= min_count


def _tiktok_first_activity_trigger_matches(
    ev_blob: Mapping[str, Any],
    *,
    rule_id: str,
    status: StatusCallback,
) -> bool:
    if ev_blob.get("type") != "tiktok_first_activity":
        return False
    params: Any = ev_blob.get("params")
    if not isinstance(params, dict):
        status(f"Rule {rule_id}: event.params must be an object")
        return False
    return True


def _tiktok_gift_price_map() -> tuple[dict[str, int], dict[str, int]]:
    """Return (gift_id->price, gift_name_casefold->price) maps."""
    by_id: dict[str, int] = {}
    by_name: dict[str, int] = {}
    for g in TIKTOK_GIFTS:
        if not isinstance(g, dict):
            continue
        price = g.get("price")
        if not isinstance(price, int):
            continue
        gid = g.get("id")
        if isinstance(gid, str) and gid.strip():
            by_id[gid.strip()] = int(price)
        name = g.get("name")
        if isinstance(name, str) and name.strip():
            by_name[name.strip().casefold()] = int(price)
    return (by_id, by_name)


_TIKTOK_GIFT_PRICE_BY_ID, _TIKTOK_GIFT_PRICE_BY_NAME = _tiktok_gift_price_map()


def _tiktok_gift_price_coins(ev: GiftReceivedEvent) -> int:
    gid = (ev.gift_id or "").strip()
    if gid:
        p = _TIKTOK_GIFT_PRICE_BY_ID.get(gid)
        if isinstance(p, int):
            return p
    name = (ev.gift_name or "").strip()
    if name:
        p = _TIKTOK_GIFT_PRICE_BY_NAME.get(name.casefold())
        if isinstance(p, int):
            return p
    live = int(getattr(ev, "tiktok_coin_each", 0) or 0)
    if live > 0:
        return live
    return 0


def _tiktok_any_gift_received_min_price_if_matches(
    ev_blob: Mapping[str, Any],
    ev: GiftReceivedEvent,
    *,
    rule_id: str,
    status: StatusCallback,
) -> int | None:
    """If this TikTok any-gift trigger matches, return its min_price threshold; else None."""
    if ev_blob.get("type") != "tiktok_any_gift_received":
        return None
    if ev.platform != ChatPlatform.TIKTOK:
        return None
    params: Any = ev_blob.get("params")
    if not isinstance(params, dict):
        status(f"Rule {rule_id}: event.params must be an object")
        return None
    min_price_raw = params.get("min_price", 1)
    try:
        min_price = int(min_price_raw)
    except (TypeError, ValueError):
        status(f"Rule {rule_id}: min_price must be an integer")
        return None
    if min_price < 1:
        min_price = 1
    if not _tiktok_simple_user_matches(params.get("user", ""), ev.sender):
        return None
    if _tiktok_gift_price_coins(ev) >= min_price:
        return min_price
    return None


def _tiktok_any_gift_received_trigger_matches(
    ev_blob: Mapping[str, Any],
    ev: GiftReceivedEvent,
    *,
    rule_id: str,
    status: StatusCallback,
) -> bool:
    return (
        _tiktok_any_gift_received_min_price_if_matches(
            ev_blob, ev, rule_id=rule_id, status=status
        )
        is not None
    )


_MAX_USER_EVERY_N_DISPATCHES_PER_BATCH = 128


def _tiktok_like_blob_fire_totals(
    ev_blob: Mapping[str, Any],
    *,
    rule_id: str,
    status: StatusCallback,
    uk: str,
    n_i: int,
    prev_all: int,
    next_all: int,
    prev_u: int,
    next_u: int,
) -> list[int]:
    """Milestone totals for TikTok likes dispatches (`likes_total_for_scope` each); empty if none."""
    if ev_blob.get("type") != "tiktok_likes_received":
        return []
    params: Any = ev_blob.get("params")
    if not isinstance(params, dict):
        status(f"Rule {rule_id}: event.params must be an object")
        return []
    min_count_raw = params.get("min_count", 1)
    try:
        min_count = int(min_count_raw)
    except (TypeError, ValueError):
        status(f"Rule {rule_id}: min_count must be an integer")
        return []
    if min_count < 1:
        min_count = 1
    scope_raw = params.get("scope", "all_users")
    if not isinstance(scope_raw, str):
        status(f"Rule {rule_id}: scope must be a string")
        return []
    scope = scope_raw.strip()
    if scope not in ("all_users", "user_stream", "user_combo", "user_every_n"):
        status(
            f"Rule {rule_id}: scope must be all_users, user_stream, user_combo, or user_every_n"
        )
        return []
    rule_user_raw = params.get("user", "")
    rule_user = _norm_like_user(str(rule_user_raw) if rule_user_raw is not None else "")
    # user_stream = any single viewer's cumulative stream total (no named user).
    # user_combo / user_every_n = optional user filters to that viewer only.
    if scope in ("user_combo", "user_every_n"):
        if rule_user and uk != rule_user:
            return []
    if scope == "all_users":
        # Fire once when the running stream total first crosses min_count.
        if prev_all < min_count <= next_all:
            return [next_all]
        return []
    if scope == "user_stream":
        # Fire once when any viewer's running total first crosses min_count.
        if prev_u < min_count <= next_u:
            return [next_u]
        return []
    if scope == "user_every_n":
        step = min_count
        prev_bucket = prev_u // step
        next_bucket = next_u // step
        out: list[int] = []
        for b in range(prev_bucket + 1, next_bucket + 1):
            out.append(b * step)
            if len(out) >= _MAX_USER_EVERY_N_DISPATCHES_PER_BATCH:
                logger.warning(
                    "Rule %s: tiktok likes user_every_n capped dispatches (%s) for one batch",
                    rule_id,
                    _MAX_USER_EVERY_N_DISPATCHES_PER_BATCH,
                )
                break
        return out
    # user_combo
    if n_i >= min_count:
        return [n_i]
    return []


class PlatformActionsEngine:
    def __init__(
        self,
        sink: AudioSink,
        rules: list[RuleV1] | None = None,
        *,
        status_callback: StatusCallback | None = None,
        tts_speak: TtsSpeakCallback | None = None,
        pubsub: OverlayPubSub | None = None,
        actions_overlay_instance: str = "main",
        obs_execute: ObsExecute | None = None,
    ) -> None:
        self._sink = sink
        self._rules: list[RuleV1] = list(rules or [])
        self._status_callback: StatusCallback = status_callback or (lambda _msg: None)
        self._tts_speak: TtsSpeakCallback | None = tts_speak
        self._pubsub = pubsub
        self._actions_overlay_instance = (actions_overlay_instance or "main").strip() or "main"
        self._obs_execute: ObsExecute | None = obs_execute
        self._dispatch_lock = asyncio.Lock()
        # TikTok like totals for tiktok_likes_received rules (session-local, not persisted).
        self._tiktok_like_all_total: int = 0
        self._tiktok_like_user_totals: dict[str, int] = {}
        self._tiktok_first_activity_fired: bool = False

    def set_rules(self, rules: list[RuleV1]) -> None:
        self._rules = list(rules)

    def reset_tiktok_like_totals(self) -> None:
        """Reset TikTok per-stream counters used by TikTok triggers."""
        self._tiktok_like_all_total = 0
        self._tiktok_like_user_totals.clear()
        self._tiktok_first_activity_fired = False

    async def _maybe_dispatch_tiktok_first_activity(
        self,
        *,
        kind: str,
        user: str,
        count: int,
        received_at: datetime,
    ) -> None:
        if self._tiktok_first_activity_fired:
            return
        self._tiktok_first_activity_fired = True
        for rule in self._rules:
            if not rule.enabled:
                continue
            matched = False
            for ev_blob in rule.events:
                if _tiktok_first_activity_trigger_matches(
                    ev_blob,
                    rule_id=rule.id,
                    status=self._status_callback,
                ):
                    matched = True
                    break
            if not matched:
                continue
            ev = TikTokFirstActivityEvent(
                platform=ChatPlatform.TIKTOK,
                kind=(kind or "").strip(),
                user=(user or "").strip(),
                count=max(0, int(count)),
                received_at=received_at,
            )
            await self._dispatch_actions(rule, ev)

    async def on_tiktok_joined(self, user: str, received_at: datetime) -> None:
        u = (user or "").strip()
        await self._maybe_dispatch_tiktok_first_activity(
            kind="join",
            user=u,
            count=1,
            received_at=received_at,
        )
        for rule in self._rules:
            if not rule.enabled:
                continue
            matched = False
            for ev_blob in rule.events:
                if _tiktok_simple_user_trigger_matches(
                    ev_blob,
                    expected_type="tiktok_joined",
                    rule_id=rule.id,
                    status=self._status_callback,
                    actual_user=u,
                ):
                    matched = True
                    break
            if not matched:
                continue
            ev = TikTokJoinedEvent(platform=ChatPlatform.TIKTOK, user=u, received_at=received_at)
            await self._dispatch_actions(rule, ev)

    async def on_tiktok_followed(self, user: str, received_at: datetime) -> None:
        u = (user or "").strip()
        await self._maybe_dispatch_tiktok_first_activity(
            kind="follow",
            user=u,
            count=1,
            received_at=received_at,
        )
        for rule in self._rules:
            if not rule.enabled:
                continue
            matched = False
            for ev_blob in rule.events:
                if _tiktok_simple_user_trigger_matches(
                    ev_blob,
                    expected_type="tiktok_followed",
                    rule_id=rule.id,
                    status=self._status_callback,
                    actual_user=u,
                ):
                    matched = True
                    break
            if not matched:
                continue
            ev = TikTokFollowedEvent(platform=ChatPlatform.TIKTOK, user=u, received_at=received_at)
            await self._dispatch_actions(rule, ev)

    async def on_tiktok_shared(self, user: str, count: int, received_at: datetime) -> None:
        u = (user or "").strip()
        try:
            c = max(1, int(count))
        except (TypeError, ValueError):
            c = 1
        await self._maybe_dispatch_tiktok_first_activity(
            kind="share",
            user=u,
            count=c,
            received_at=received_at,
        )
        for rule in self._rules:
            if not rule.enabled:
                continue
            matched = False
            for ev_blob in rule.events:
                if _tiktok_share_trigger_matches(
                    ev_blob,
                    rule_id=rule.id,
                    status=self._status_callback,
                    actual_user=u,
                    count=c,
                ):
                    matched = True
                    break
            if not matched:
                continue
            ev = TikTokSharedEvent(platform=ChatPlatform.TIKTOK, user=u, count=c, received_at=received_at)
            await self._dispatch_actions(rule, ev)

    async def on_tiktok_paid_subscribed(self, user: str, received_at: datetime) -> None:
        u = (user or "").strip()
        await self._maybe_dispatch_tiktok_first_activity(
            kind="paid_sub",
            user=u,
            count=1,
            received_at=received_at,
        )
        for rule in self._rules:
            if not rule.enabled:
                continue
            matched = False
            for ev_blob in rule.events:
                if _tiktok_simple_user_trigger_matches(
                    ev_blob,
                    expected_type="tiktok_paid_subscribed",
                    rule_id=rule.id,
                    status=self._status_callback,
                    actual_user=u,
                ):
                    matched = True
                    break
            if not matched:
                continue
            ev = TikTokPaidSubscribedEvent(platform=ChatPlatform.TIKTOK, user=u, received_at=received_at)
            await self._dispatch_actions(rule, ev)

    async def on_twitch_follow(self, user: str, received_at: datetime) -> None:
        u = (user or "").strip()
        plat = ChatPlatform.TWITCH
        for rule in self._rules:
            if not rule.enabled:
                continue
            matched = False
            for ev_blob in rule.events:
                if not trigger_platform_applies_to_twitch_channel_events(ev_blob):
                    continue
                if _tiktok_simple_user_trigger_matches(
                    ev_blob,
                    expected_type="twitch_follow",
                    rule_id=rule.id,
                    status=self._status_callback,
                    actual_user=u,
                ):
                    matched = True
                    break
            if not matched:
                continue
            ev = TwitchFollowEvent(platform=plat, user=u, received_at=received_at)
            await self._dispatch_actions(rule, ev)

    async def on_twitch_subscribe(self, user: str, months: int, received_at: datetime) -> None:
        u = (user or "").strip()
        try:
            m = max(0, int(months))
        except (TypeError, ValueError):
            m = 0
        plat = ChatPlatform.TWITCH
        for rule in self._rules:
            if not rule.enabled:
                continue
            matched = False
            for ev_blob in rule.events:
                if not trigger_platform_applies_to_twitch_channel_events(ev_blob):
                    continue
                if _tiktok_simple_user_trigger_matches(
                    ev_blob,
                    expected_type="twitch_subscribe",
                    rule_id=rule.id,
                    status=self._status_callback,
                    actual_user=u,
                ):
                    matched = True
                    break
            if not matched:
                continue
            ev = TwitchSubscribeEvent(platform=plat, user=u, months=m, received_at=received_at)
            await self._dispatch_actions(rule, ev)

    async def on_twitch_resub(
        self, user: str, months: int, message: str, received_at: datetime
    ) -> None:
        u = (user or "").strip()
        msg = (message or "").strip()
        try:
            m = max(0, int(months))
        except (TypeError, ValueError):
            m = 0
        plat = ChatPlatform.TWITCH
        for rule in self._rules:
            if not rule.enabled:
                continue
            matched = False
            for ev_blob in rule.events:
                if not trigger_platform_applies_to_twitch_channel_events(ev_blob):
                    continue
                if _tiktok_simple_user_trigger_matches(
                    ev_blob,
                    expected_type="twitch_resub",
                    rule_id=rule.id,
                    status=self._status_callback,
                    actual_user=u,
                ):
                    matched = True
                    break
            if not matched:
                continue
            ev = TwitchResubscribeEvent(
                platform=plat, user=u, months=m, message=msg, received_at=received_at
            )
            await self._dispatch_actions(rule, ev)

    async def on_twitch_sub_gift(self, user: str, months: int, received_at: datetime) -> None:
        u = (user or "").strip()
        try:
            m = max(0, int(months))
        except (TypeError, ValueError):
            m = 0
        plat = ChatPlatform.TWITCH
        for rule in self._rules:
            if not rule.enabled:
                continue
            matched = False
            for ev_blob in rule.events:
                if not trigger_platform_applies_to_twitch_channel_events(ev_blob):
                    continue
                if _tiktok_simple_user_trigger_matches(
                    ev_blob,
                    expected_type="twitch_sub_gift",
                    rule_id=rule.id,
                    status=self._status_callback,
                    actual_user=u,
                ):
                    matched = True
                    break
            if not matched:
                continue
            ev = TwitchSubscriptionGiftEvent(platform=plat, user=u, months=m, received_at=received_at)
            await self._dispatch_actions(rule, ev)

    async def on_twitch_cheer(self, user: str, bits: int, received_at: datetime) -> None:
        u = (user or "").strip()
        try:
            b = max(0, int(bits))
        except (TypeError, ValueError):
            b = 0
        plat = ChatPlatform.TWITCH
        for rule in self._rules:
            if not rule.enabled:
                continue
            matched = False
            for ev_blob in rule.events:
                if not trigger_platform_applies_to_twitch_channel_events(ev_blob):
                    continue
                if _twitch_cheer_trigger_matches(
                    ev_blob,
                    rule_id=rule.id,
                    status=self._status_callback,
                    actual_user=u,
                    bits=b,
                ):
                    matched = True
                    break
            if not matched:
                continue
            ev = TwitchCheerEvent(platform=plat, user=u, bits=b, received_at=received_at)
            await self._dispatch_actions(rule, ev)

    async def on_twitch_raid(self, raider: str, viewers: int, received_at: datetime) -> None:
        r = (raider or "").strip()
        try:
            v = max(0, int(viewers))
        except (TypeError, ValueError):
            v = 0
        plat = ChatPlatform.TWITCH
        for rule in self._rules:
            if not rule.enabled:
                continue
            matched = False
            for ev_blob in rule.events:
                if not trigger_platform_applies_to_twitch_channel_events(ev_blob):
                    continue
                if _twitch_raid_trigger_matches(
                    ev_blob,
                    rule_id=rule.id,
                    status=self._status_callback,
                    raider=r,
                    viewers=v,
                ):
                    matched = True
                    break
            if not matched:
                continue
            ev = TwitchRaidEvent(platform=plat, raider=r, viewers=v, received_at=received_at)
            await self._dispatch_actions(rule, ev)

    async def on_chat_message(self, ev: ChatMessageEvent) -> None:
        if ev.platform == ChatPlatform.TIKTOK:
            await self._maybe_dispatch_tiktok_first_activity(
                kind="comment",
                user=(ev.author or "").strip(),
                count=1,
                received_at=ev.received_at,
            )
        for rule in self._rules:
            if not rule.enabled:
                continue
            matched = False
            for ev_blob in rule.events:
                if not trigger_platform_applies_to_chat(ev_blob, ev.platform):
                    continue
                if _chat_trigger_matches(
                    ev_blob, ev, rule_id=rule.id, status=self._status_callback
                ):
                    matched = True
                    break
            if matched:
                await self._dispatch_actions(rule, ev)

    async def on_gift_received(self, ev: GiftReceivedEvent) -> None:
        logger.info(
            "Actions gift_received: platform=%s sender=%s gift_id=%s gift_name=%s count=%s rules=%s",
            getattr(ev.platform, "value", ev.platform),
            ev.sender,
            ev.gift_id,
            ev.gift_name,
            ev.count,
            len(self._rules),
        )
        if ev.platform == ChatPlatform.TIKTOK:
            await self._maybe_dispatch_tiktok_first_activity(
                kind="gift",
                user=(ev.sender or "").strip(),
                count=max(1, int(ev.count)),
                received_at=ev.received_at,
            )
        matched_any = False
        if ev.platform != ChatPlatform.TIKTOK:
            for rule in self._rules:
                if not rule.enabled:
                    continue
                matched_rule = False
                for ev_blob in rule.events:
                    if not trigger_platform_applies_to_gift(ev_blob, ev.platform):
                        continue
                    if _gift_trigger_matches(
                        ev_blob, ev, rule_id=rule.id, status=self._status_callback
                    ) or _tiktok_any_gift_received_trigger_matches(
                        ev_blob,
                        ev,
                        rule_id=rule.id,
                        status=self._status_callback,
                    ):
                        matched_rule = True
                        break
                if matched_rule:
                    matched_any = True
                    logger.info("Actions gift_received matched rule=%s", rule.id)
                    await self._dispatch_actions(rule, ev)
        else:
            # TikTok: many any-gift rules with different min_price are tiers — only the
            # highest satisfied threshold wins among tiktok_any_gift_received triggers.
            # gift_received (specific gift) rules still fire whenever they match.
            plans: list[tuple[RuleV1, bool, int | None]] = []
            for rule in self._rules:
                if not rule.enabled:
                    continue
                spec_match = False
                any_gift_mins: list[int] = []
                for ev_blob in rule.events:
                    if not trigger_platform_applies_to_gift(ev_blob, ev.platform):
                        continue
                    if _gift_trigger_matches(
                        ev_blob, ev, rule_id=rule.id, status=self._status_callback
                    ):
                        spec_match = True
                    mp = _tiktok_any_gift_received_min_price_if_matches(
                        ev_blob,
                        ev,
                        rule_id=rule.id,
                        status=self._status_callback,
                    )
                    if mp is not None:
                        any_gift_mins.append(mp)
                best_any = max(any_gift_mins) if any_gift_mins else None
                plans.append((rule, spec_match, best_any))

            tier_winning_min = max(
                (b for _, _, b in plans if b is not None),
                default=None,
            )

            for rule, spec_match, best_any in plans:
                if spec_match or (
                    best_any is not None
                    and tier_winning_min is not None
                    and best_any == tier_winning_min
                ):
                    matched_any = True
                    logger.info("Actions gift_received matched rule=%s", rule.id)
                    await self._dispatch_actions(rule, ev)
        if not matched_any:
            logger.info("Actions gift_received no matching rule")

    async def on_tiktok_likes_received(
        self,
        user: str,
        n: int,
        received_at: datetime,
        *,
        profile_picture_url: str = "",
    ) -> None:
        """Handle one TikTok LikeEvent batch (n likes, often a tap combo)."""
        try:
            n_i = max(1, int(n))
        except (TypeError, ValueError):
            n_i = 1
        await self._maybe_dispatch_tiktok_first_activity(
            kind="like",
            user=(user or "").strip(),
            count=n_i,
            received_at=received_at,
        )
        uk = _norm_like_user(user)
        prev_all = self._tiktok_like_all_total
        next_all = prev_all + n_i
        self._tiktok_like_all_total = next_all
        prev_u = self._tiktok_like_user_totals.get(uk, 0)
        next_u = prev_u + n_i
        self._tiktok_like_user_totals[uk] = next_u

        display_user = (user or "").strip()

        for rule in self._rules:
            if not rule.enabled:
                continue
            fire_totals: list[int] = []
            for ev_blob in rule.events:
                if not trigger_platform_applies_to_tiktok_likes(ev_blob):
                    continue
                fts = _tiktok_like_blob_fire_totals(
                    ev_blob,
                    rule_id=rule.id,
                    status=self._status_callback,
                    uk=uk,
                    n_i=n_i,
                    prev_all=prev_all,
                    next_all=next_all,
                    prev_u=prev_u,
                    next_u=next_u,
                )
                if fts:
                    fire_totals = fts
                    break

            if not fire_totals:
                continue

            for total_for_scope in fire_totals:
                ev = TikTokLikesReceivedEvent(
                    platform=ChatPlatform.TIKTOK,
                    user=display_user,
                    likes_in_batch=n_i,
                    likes_total_for_scope=total_for_scope,
                    received_at=received_at,
                    profile_picture_url=str(profile_picture_url or "").strip(),
                )
                logger.info("Actions tiktok_likes_received matched rule=%s", rule.id)
                await self._dispatch_actions(rule, ev)

    def tiktok_likes_preview_batch(self, *, scope: str, min_count: int, user: str) -> tuple[int, str] | None:
        """Return (batch_n, display_user) so one synthetic batch crosses one trigger intent, or None.

        For `user_every_n`, crossing means reaching the viewer's next N · k milestone (session totals).
        """
        u = (user or "").strip() or "preview"
        uk = _norm_like_user(u)
        if scope == "all_users":
            prev = self._tiktok_like_all_total
            if prev >= min_count:
                return None
            return (max(1, min_count - prev), u)
        if scope == "user_stream":
            prev = self._tiktok_like_user_totals.get(uk, 0)
            if prev >= min_count:
                return None
            return (max(1, min_count - prev), u)
        if scope == "user_combo":
            return (max(min_count, 1), u)
        if scope == "user_every_n":
            step = max(1, min_count)
            prev = self._tiktok_like_user_totals.get(uk, 0)
            next_ms = ((prev // step) + 1) * step
            delta = next_ms - prev
            if delta <= 0:
                return None
            return (max(1, delta), u)
        return None

    async def _dispatch_actions(self, rule: RuleV1, ev: object) -> None:
        if not rule.actions:
            self._status_callback(f"Rule {rule.id}: no actions configured")
            return

        async with self._dispatch_lock:
            coros: list[Coroutine[Any, Any, None]] = []
            for i, action in enumerate(rule.actions):
                if not isinstance(action, dict):
                    self._status_callback(f"Rule {rule.id}: actions[{i}] must be an object")
                    continue
                t = action.get("type")
                if not isinstance(t, str) or not t.strip():
                    self._status_callback(f"Rule {rule.id}: actions[{i}].type is required")
                    continue
                params = action.get("params")
                if not isinstance(params, dict):
                    self._status_callback(f"Rule {rule.id}: actions[{i}].params must be an object")
                    continue

                if t == "play_sound":
                    file_path = params.get("file_path")
                    if not isinstance(file_path, str) or not file_path.strip():
                        self._status_callback(f"Rule {rule.id}: actions[{i}].file_path is required")
                        continue
                    vol_raw = params.get("volume_percent", 100)
                    try:
                        vol = int(vol_raw)
                    except (TypeError, ValueError):
                        vol = 100
                    if vol < 0:
                        vol = 0
                    if vol > 100:
                        vol = 100
                    skip_if_same = _obs_bool_flag(params.get("skip_if_same_playing"), default=False)

                    async def _play(
                        fp: str = file_path,
                        v: int = vol,
                        skip_dup: bool = skip_if_same,
                    ) -> None:
                        try:
                            await play_sound_from_file(
                                fp,
                                sink=self._sink,
                                volume_percent=v,
                                skip_queue_if_same=skip_dup,
                            )
                        except FileNotFoundError:
                            self._status_callback(f"Rule {rule.id}: sound file not found: {fp}")
                        except (OSError, ValueError) as e:
                            self._status_callback(f"Rule {rule.id}: play_sound failed: {e}")

                    coros.append(_play())
                    continue

                if t == "write_file":
                    file_path = params.get("file_path")
                    if not isinstance(file_path, str) or not file_path.strip():
                        self._status_callback(f"Rule {rule.id}: actions[{i}].file_path is required")
                        continue
                    text = params.get("text", "")
                    if not isinstance(text, str):
                        self._status_callback(f"Rule {rule.id}: actions[{i}].text must be a string")
                        continue
                    mode = params.get("mode", "overwrite")
                    if not isinstance(mode, str):
                        self._status_callback(f"Rule {rule.id}: actions[{i}].mode must be a string")
                        continue
                    file_path = apply_action_placeholders(file_path, ev).strip()
                    if not file_path:
                        self._status_callback(
                            f"Rule {rule.id}: actions[{i}].file_path is empty after placeholders"
                        )
                        continue
                    text = apply_action_placeholders(text, ev)

                    async def _write(fp: str = file_path, tx: str = text, m: str = mode) -> None:
                        try:
                            write_text_to_file(fp, tx, mode=m)
                        except (OSError, ValueError) as e:
                            self._status_callback(f"Rule {rule.id}: write_file failed: {e}")

                    coros.append(_write())
                    continue

                if t in ("run_program", "run_exe"):
                    program_path = params.get("program_path") or params.get("exe_path")
                    if not isinstance(program_path, str) or not program_path.strip():
                        self._status_callback(
                            f"Rule {rule.id}: actions[{i}].program_path (or legacy exe_path) is required"
                        )
                        continue
                    args_raw = params.get("arguments", "")
                    if not isinstance(args_raw, str):
                        self._status_callback(f"Rule {rule.id}: actions[{i}].arguments must be a string")
                        continue
                    args_raw = apply_action_placeholders(args_raw, ev)

                    async def _run(prog: str = program_path, ar: str = args_raw) -> None:
                        try:
                            await launch_program(prog, ar)
                        except FileNotFoundError:
                            self._status_callback(f"Rule {rule.id}: program not found: {prog}")
                        except PermissionError as e:
                            self._status_callback(f"Rule {rule.id}: launch_program failed: {e}")
                        except (OSError, ValueError) as e:
                            self._status_callback(f"Rule {rule.id}: launch_program failed: {e}")

                    coros.append(_run())
                    continue

                if t == "speak_tts":
                    raw = params.get("text", "")
                    if not isinstance(raw, str):
                        self._status_callback(f"Rule {rule.id}: actions[{i}].text must be a string")
                        continue
                    resolved = apply_action_placeholders(raw, ev).strip()
                    if not resolved:
                        self._status_callback(f"Rule {rule.id}: actions[{i}].text is empty after placeholders")
                        continue
                    if self._tts_speak is None:
                        self._status_callback(f"Rule {rule.id}: speak_tts requires TTS (not configured)")
                        continue
                    if len(resolved) > MAX_MESSAGE_CHARS:
                        resolved = resolved[:MAX_MESSAGE_CHARS]

                    async def _tts_line(s: str = resolved) -> None:
                        try:
                            await self._tts_speak(s)
                        except (OSError, ValueError, httpx.HTTPError) as e:
                            self._status_callback(f"Rule {rule.id}: speak_tts failed: {e}")

                    coros.append(_tts_line())
                    continue

                if t == "show_overlay":
                    raw = params.get("text", "")
                    if not isinstance(raw, str):
                        self._status_callback(f"Rule {rule.id}: actions[{i}].text must be a string")
                        continue
                    seconds_raw = params.get("seconds", 0)
                    try:
                        seconds = float(seconds_raw)
                    except (TypeError, ValueError):
                        seconds = 0.0
                    if seconds < 0:
                        seconds = 0.0
                    if seconds > 600:
                        seconds = 600.0

                    if self._pubsub is None:
                        self._status_callback(f"Rule {rule.id}: show_overlay requires overlays (not configured)")
                        continue

                    text = apply_action_placeholders(raw, ev).strip()
                    if not text:
                        self._status_callback(f"Rule {rule.id}: actions[{i}].text is empty after placeholders")
                        continue
                    if len(text) > MAX_MESSAGE_CHARS:
                        text = text[:MAX_MESSAGE_CHARS]

                    username = (
                        str(
                            getattr(ev, "sender", "")
                            or getattr(ev, "author", "")
                            or getattr(ev, "user", "")
                            or getattr(ev, "raider", "")
                        ).strip()
                    )
                    if not username:
                        username = "?"

                    gift_picture_url = ""
                    if isinstance(ev, GiftReceivedEvent):
                        gift_picture_url = str(getattr(ev, "gift_icon_url", "") or "").strip()
                        if (
                            not gift_picture_url
                            and getattr(ev, "platform", None) == ChatPlatform.TIKTOK
                        ):
                            gift_picture_url = tiktok_catalog_gift_image_url(
                                gift_id=ev.gift_id,
                                gift_name=ev.gift_name,
                            )

                    profile_picture_url = ""
                    if isinstance(ev, ChatMessageEvent):
                        profile_picture_url = str(getattr(ev, "profile_picture_url", "") or "").strip()
                    elif isinstance(ev, GiftReceivedEvent):
                        profile_picture_url = str(getattr(ev, "sender_avatar_url", "") or "").strip()
                    elif isinstance(ev, TikTokLikesReceivedEvent):
                        profile_picture_url = str(getattr(ev, "profile_picture_url", "") or "").strip()

                    patch = {
                        "append": {
                            "username": username,
                            "text": text,
                            "profile_picture_url": profile_picture_url,
                            "gift_picture_url": gift_picture_url,
                            "platform": _show_overlay_platform_slug(ev),
                            "show_seconds": int(seconds) if float(seconds).is_integer() else seconds,
                        }
                    }
                    topic = f"overlay:actions:{self._actions_overlay_instance}"

                    async def _pub(p: dict[str, object] = patch, tpc: str = topic) -> None:
                        await self._pubsub.publish(tpc, p)  # type: ignore[arg-type]

                    coros.append(_pub())
                    continue

                if t == "obs_scene":
                    if self._obs_execute is None:
                        self._status_callback(
                            f"Rule {rule.id}: obs_scene needs OBS "
                            f"(host/port/password in Settings)"
                        )
                        continue
                    mode_raw = params.get("mode", "program_scene")
                    if not isinstance(mode_raw, str) or not mode_raw.strip():
                        self._status_callback(f"Rule {rule.id}: obs_scene mode is required")
                        continue
                    mode_s = mode_raw.strip()
                    mode_norm = mode_s.lower().replace("-", "_")
                    is_source_visible = mode_norm in (
                        "source_visible",
                        "scene_item",
                        "item_visible",
                    )
                    sn_raw = params.get("scene_name", "")
                    if not isinstance(sn_raw, str):
                        self._status_callback(f"Rule {rule.id}: obs_scene scene_name must be a string")
                        continue
                    scene_name = apply_action_placeholders(sn_raw, ev).strip()
                    if not scene_name:
                        self._status_callback(
                            f"Rule {rule.id}: obs_scene scene_name empty after placeholders"
                        )
                        continue
                    src_raw = params.get("source_name", "")
                    source_name = ""
                    if isinstance(src_raw, str) and src_raw.strip():
                        source_name = apply_action_placeholders(src_raw, ev).strip()
                    visible = _obs_visible_from_params(params.get("visible", True))
                    canvas_uuid = ""
                    cu_raw = params.get("canvas_uuid", "")
                    if isinstance(cu_raw, str) and cu_raw.strip():
                        canvas_uuid = apply_action_placeholders(cu_raw, ev).strip()
                    payload: dict[str, Any] = {
                        "mode": mode_s,
                        "scene_name": scene_name,
                        "source_name": source_name,
                        "visible": visible,
                        "canvas_uuid": canvas_uuid,
                    }
                    delay_s = _obs_revert_delay_seconds(params.get("revert_delay_seconds", 0), ev)
                    revert_after = (
                        is_source_visible
                        and bool(source_name)
                        and _obs_bool_flag(params.get("revert_previous_state", False))
                        and delay_s > 0.0
                    )

                    async def _obs_then_maybe_revert(
                        p: dict[str, Any] = payload,
                        *,
                        do_revert: bool = revert_after,
                        wait_s: float = delay_s,
                        vis: bool = visible,
                    ) -> None:
                        await self._obs_execute(dict(p))
                        if do_revert and wait_s > 0.0:
                            await asyncio.sleep(wait_s)
                            rev = dict(p)
                            rev["visible"] = not vis
                            await self._obs_execute(rev)

                    coros.append(_obs_then_maybe_revert())
                    continue

                # Unknown action types are ignored in v1 (future extensibility).
                self._status_callback(f"Rule {rule.id}: unknown action type: {t}")

            if not coros:
                return

        # Run actions outside the dispatch lock so overlapping triggers can see play_sound
        # dedupe state and similar cross-event behaviour while audio is still playing.
        await asyncio.gather(*coros)
