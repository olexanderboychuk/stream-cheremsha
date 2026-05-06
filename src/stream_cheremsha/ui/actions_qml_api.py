"""QML bridge for the platform Actions editor (rules: Event -> Actions)."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import typing
import weakref
from dataclasses import dataclass
from datetime import UTC, datetime

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QFileDialog

from stream_cheremsha.actions import store as actions_store
from stream_cheremsha.actions.action_placeholders import _PLACEHOLDER_RE
from stream_cheremsha.actions.engine import PlatformActionsEngine
from stream_cheremsha.actions.events import ChatMessageEvent, GiftReceivedEvent
from stream_cheremsha.actions.models import (
    RuleV1,
    TypedBlob,
    normalize_ui_rules_layout_v1,
    rule_from_json_obj,
    ruleset_bundle_from_json_text,
    ruleset_to_json_text,
    ui_rules_layout_from_json_text,
    ui_rules_layout_to_json_text,
)
from stream_cheremsha.actions.store import (
    load_rules,
    load_rules_bundle,
    save_rules_bundle,
)
from stream_cheremsha.actions.tiktok_gifts import TIKTOK_GIFTS
from stream_cheremsha.actions.trigger_meta import (
    chat_platform_for_preview,
    trigger_platform_effective,
)
from stream_cheremsha.config import constants, keyring_store
from stream_cheremsha.domain.models import ChatPlatform
from stream_cheremsha.obs_ws.control import (
    obs_list_canvases,
    obs_list_scene_sources,
    obs_list_scenes,
)

if typing.TYPE_CHECKING:
    from stream_cheremsha.ui.main_window import MainWindow


logger = logging.getLogger(__name__)

# Back-compat export for older tests/callers that monkeypatch `save_rules` directly.
save_rules = actions_store.save_rules


_LIKE_PLACEHOLDER_TOKENS = frozenset(
    {
        "likebatch",
        "likes_batch",
        "likecount",
        "liketotal",
        "likes_total",
    }
)
_GIFT_PLACEHOLDER_TOKENS = frozenset(
    {
        "giftcount",
        "gift_count",
        "giftname",
        "gift_name",
        "giftid",
        "gift_id",
    }
)
_CHAT_PLACEHOLDER_TOKENS = frozenset({"author", "text"})
_ENGAGEMENT_PLACEHOLDER_TOKENS = frozenset(
    {"sender", "user", "kind", "months", "message", "bits", "raider", "viewers"}
)


def _schedule_preview_task(coro: typing.Coroutine[typing.Any, typing.Any, typing.Any]) -> None:
    """Schedule preview coroutines on the qasync/Qt loop and log failures."""

    task = asyncio.ensure_future(coro)

    def _done(t: asyncio.Task[typing.Any]) -> None:
        try:
            exc = t.exception()
        except asyncio.CancelledError:
            return
        if exc is None:
            return
        logger.error("Actions preview task failed", exc_info=exc)

    task.add_done_callback(_done)


def _collect_placeholder_tokens_from_actions(
    actions: list[typing.Mapping[str, typing.Any]],
) -> set[str]:
    """Collect lowercase `{token}` names referenced anywhere in action params."""

    found: set[str] = set()

    def walk(obj: object) -> None:
        if isinstance(obj, str):
            for m in _PLACEHOLDER_RE.finditer(obj):
                raw = (m.group(1) or "").strip()
                if not raw:
                    continue
                # Expressions like `{giftcount-1}` — capture referenced identifiers cheaply.
                for piece in re.split(r"[^a-zA-Z0-9_]+", raw):
                    p = piece.strip().lower()
                    if p:
                        found.add(p)
            return
        if isinstance(obj, list):
            for it in obj:
                walk(it)
            return
        if isinstance(obj, dict):
            for v in obj.values():
                walk(v)

    for a in actions:
        params = a.get("params") if isinstance(a, dict) else None
        if isinstance(params, dict):
            walk(params)
    return found


@dataclass(frozen=True, slots=True)
class _PreviewHints:
    likes: bool
    gift: bool
    chat: bool
    engagement_no_count: bool
    ambiguous_count: bool


def _preview_hints_from_tokens(tokens: set[str]) -> _PreviewHints:
    likes = bool(tokens & _LIKE_PLACEHOLDER_TOKENS)
    gift = bool(tokens & _GIFT_PLACEHOLDER_TOKENS)
    chat = bool(tokens & _CHAT_PLACEHOLDER_TOKENS)
    engagement_tokens = tokens & _ENGAGEMENT_PLACEHOLDER_TOKENS
    engagement_no_count = bool(engagement_tokens and ("count" not in tokens))
    ambiguous_count = "count" in tokens and not likes and not gift
    return _PreviewHints(
        likes=likes,
        gift=gift,
        chat=chat,
        engagement_no_count=engagement_no_count,
        ambiguous_count=ambiguous_count,
    )


def pick_preview_trigger_for_rule(
    events: tuple[TypedBlob, ...],
    *,
    actions: list[typing.Mapping[str, typing.Any]],
    store_platform: str,
) -> TypedBlob:
    """Pick which OR-trigger to simulate for Actions preview.

    Runtime OR rules fire on any matching trigger, but preview can only simulate one event. We
    prefer the trigger that best matches placeholders used in action templates.
    """

    if not events:
        raise ValueError("pick_preview_trigger_for_rule requires non-empty events")
    if len(events) == 1:
        return events[0]

    p = (store_platform or "").strip().lower()
    tokens = _collect_placeholder_tokens_from_actions(actions)
    hints = _preview_hints_from_tokens(tokens)

    best_i = 0
    best_score = -1

    for i, ev in enumerate(events):
        t = (str(ev.get("type") or "")).strip()
        score = 0
        tp = trigger_platform_effective(ev)

        if t == "tiktok_likes_received":
            if p != "tiktok" or tp not in ("all", "tiktok"):
                continue
            if hints.likes:
                score += 50
            elif hints.gift or hints.chat:
                score -= 50
            elif hints.ambiguous_count:
                score += 5

        elif t == "gift_received":
            if hints.gift:
                score += 50
            elif hints.likes:
                score -= 50

        elif t == "tiktok_any_gift_received":
            if p != "tiktok" or tp not in ("all", "tiktok"):
                continue
            if hints.gift:
                score += 45
            elif hints.likes:
                score -= 50

        elif t == "chat_keyword":
            if hints.chat:
                score += 50
            elif hints.likes:
                score -= 20

        elif t in ("tiktok_joined", "tiktok_followed", "tiktok_paid_subscribed"):
            if p != "tiktok" or tp not in ("all", "tiktok"):
                continue
            if hints.engagement_no_count and not hints.likes and not hints.gift:
                score += 25

        elif t == "tiktok_shared":
            if p != "tiktok" or tp not in ("all", "tiktok"):
                continue
            if ("count" in tokens) and not hints.likes and not hints.gift:
                score += 25

        elif t == "tiktok_first_activity":
            if p != "tiktok" or tp not in ("all", "tiktok"):
                continue
            if ("kind" in tokens) and not hints.likes and not hints.gift:
                score += 30
            elif hints.engagement_no_count and not hints.likes and not hints.gift:
                score += 10

        elif t in ("twitch_follow", "twitch_subscribe", "twitch_resub", "twitch_sub_gift"):
            if p != "twitch" or tp not in ("all", "twitch"):
                continue
            if hints.engagement_no_count and not hints.likes and not hints.gift:
                score += 25
            if t == "twitch_resub" and ("message" in tokens or "text" in tokens):
                score += 15

        elif t == "twitch_cheer":
            if p != "twitch" or tp not in ("all", "twitch"):
                continue
            if "bits" in tokens or hints.ambiguous_count:
                score += 30

        elif t == "twitch_raid":
            if p != "twitch" or tp not in ("all", "twitch"):
                continue
            if "viewers" in tokens or "raider" in tokens:
                score += 30

        else:
            score = 0

        if score > best_score:
            best_score = score
            best_i = i

    if best_score <= 0:
        return events[0]
    return events[best_i]


def _obs_host_port_password_from_main(w: MainWindow | None) -> tuple[str, int, str]:
    if w is None:
        return "127.0.0.1", 4455, ""
    host = (w._obs_ws_host.text() or "").strip() or "127.0.0.1"  # noqa: SLF001
    port_s = (w._obs_ws_port.text() or "").strip() or "4455"
    try:
        port = int(port_s)
    except ValueError:
        port = 4455
    port = max(1, min(65535, port))
    pw = (w._obs_ws_password.text() or "").strip()  # noqa: SLF001
    if not pw:
        pw = keyring_store.get_password(constants.KEY_OBS_WEBSOCKET_PASSWORD) or ""
    return host, port, pw


class ActionsQmlApi(QObject):
    refreshUiRequested = Signal()

    def __init__(self, main: MainWindow) -> None:
        super().__init__(parent=main)
        self._m: weakref.ref[MainWindow] = weakref.ref(main)

    def _win(self) -> MainWindow | None:
        return self._m()

    @staticmethod
    def _store_account_key(platform: str, accountKey: str) -> str:
        p = (platform or "").strip().lower()
        if p == "tiktok":
            return constants.TIKTOK_ACTIONS_ACCOUNT_KEY
        return (accountKey or "").strip()

    @Slot(str, str, result=str)
    def loadRulesJson(self, platform: str, accountKey: str) -> str:
        """Return ruleset JSON (wrapper: schema_version + rules list)."""
        p = (platform or "").strip()
        if not p:
            return '{"schema_version":1,"rules":[]}'
        ak = self._store_account_key(p, accountKey)
        if not ak:
            return '{"schema_version":1,"rules":[]}'
        w0 = self._win()
        if w0 is not None and p == "tiktok" and ak == constants.TIKTOK_ACTIONS_ACCOUNT_KEY:
            w0._maybe_migrate_tiktok_actions()  # noqa: SLF001
        rules, layout = load_rules_bundle(p, ak)
        layout2 = normalize_ui_rules_layout_v1(layout, rules)
        return ruleset_to_json_text(rules, ui_layout=layout2)

    @Slot(str, str, str)
    def saveRulesJson(self, platform: str, accountKey: str, rulesJson: str) -> None:
        """Validate & persist ruleset JSON. Also refresh in-memory engines."""
        p = (platform or "").strip()
        if not p:
            return
        ak = self._store_account_key(p, accountKey)
        if not ak:
            return
        txt = (rulesJson or "").strip()
        if not txt:
            # Match Widgets overlay APIs: never wipe persisted state on empty/whitespace payloads.
            # Clearing rules is done explicitly via JSON {"schema_version":1,"rules":[]}.
            logger.debug(
                (
                    "saveRulesJson ignored: empty payload for platform=%s account=%s "
                    "(rules not cleared)"
                ),
                p,
                ak,
            )
            return

        rules, incoming_layout = ruleset_bundle_from_json_text(txt)
        save_rules_bundle(p, ak, rules, incoming_layout)
        w = self._win()
        if w is not None:
            w._actions_reload_scope(p, ak)  # noqa: SLF001

    @Slot(str, str, result=str)
    def loadRulesUiLayoutJson(self, platform: str, accountKey: str) -> str:
        """Return persisted Actions UI layout JSON (folders/order).

        Empty object if absent.
        """
        p = (platform or "").strip()
        if not p:
            return "{}"
        ak = self._store_account_key(p, accountKey)
        if not ak:
            return "{}"
        w0 = self._win()
        if w0 is not None and p == "tiktok" and ak == constants.TIKTOK_ACTIONS_ACCOUNT_KEY:
            w0._maybe_migrate_tiktok_actions()  # noqa: SLF001
        rules, layout = load_rules_bundle(p, ak)
        layout2 = normalize_ui_rules_layout_v1(layout, rules)
        if layout2 is None:
            return "{}"
        return ui_rules_layout_to_json_text(layout2)

    @Slot(str, str, str)
    def saveRulesUiLayoutJson(self, platform: str, accountKey: str, layoutJson: str) -> None:
        """Persist UI layout without touching rule payloads."""
        p = (platform or "").strip()
        if not p:
            return
        ak = self._store_account_key(p, accountKey)
        if not ak:
            return
        w0 = self._win()
        if w0 is not None and p == "tiktok" and ak == constants.TIKTOK_ACTIONS_ACCOUNT_KEY:
            w0._maybe_migrate_tiktok_actions()  # noqa: SLF001
        try:
            rules = load_rules(p, ak)
        except ValueError:
            logger.warning(
                "saveRulesUiLayoutJson skipped: unreadable rules JSON for platform=%s account=%s",
                p,
                ak,
            )
            return
        txt = (layoutJson or "").strip()
        if not txt or txt == "{}":
            save_rules_bundle(p, ak, rules, None)
        else:
            layout_in = ui_rules_layout_from_json_text(txt)
            save_rules_bundle(p, ak, rules, layout_in)
        w = self._win()
        if w is not None:
            w._actions_reload_scope(p, ak)  # noqa: SLF001

    @Slot(result=str)
    def pickSoundFile(self) -> str:
        """Open file picker for an MP3 clip and return a path or empty string."""
        w = self._win()
        parent = w if w is not None else None
        path, _ = QFileDialog.getOpenFileName(
            parent,
            "Select MP3",
            "",
            "MP3 (*.mp3);;All files (*)",
        )
        return str(path or "")

    @Slot(result=str)
    def pickWriteFile(self) -> str:
        """Pick an output text file path for write_file action."""
        w = self._win()
        parent = w if w is not None else None
        path, _ = QFileDialog.getSaveFileName(
            parent,
            "Select output file",
            "",
            "Text (*.txt);;All files (*)",
        )
        return str(path or "")

    @Slot(result=str)
    def pickProgramFile(self) -> str:
        """Pick a program binary for the launch-program action (any OS)."""
        w = self._win()
        parent = w if w is not None else None
        path, _ = QFileDialog.getOpenFileName(
            parent,
            "Select program",
            "",
            "All files (*)",
        )
        return str(path or "")

    @Slot(str, str, result=str)
    def giftOptionsJson(self, platform: str, accountKey: str) -> str:
        """Return JSON array of gift options for this platform scope."""
        w = self._win()
        if w is None:
            return "[]"
        p = (platform or "").strip().lower()
        _ = (accountKey or "").strip()
        if p == "tiktok":
            from stream_cheremsha.actions.tiktok_gifts import TIKTOK_GIFTS  # noqa: PLC0415

            return json.dumps(TIKTOK_GIFTS, ensure_ascii=False)
        return "[]"

    @Slot(result=str)
    def obsListCanvasesJson(self) -> str:
        """JSON ``{items:[{name,value}], error: str|null}`` for OBS canvas picker."""
        w = self._win()
        h, p, pw = _obs_host_port_password_from_main(w)
        items, err = obs_list_canvases(h, p, pw)
        return json.dumps({"items": items, "error": err}, ensure_ascii=False)

    @Slot(str, result=str)
    def obsListScenesJson(self, canvasUuid: str) -> str:
        """JSON ``{items:[{name,value}], error: str|null}`` — ``GetSceneList``."""
        w = self._win()
        h, port, pw = _obs_host_port_password_from_main(w)
        items, err = obs_list_scenes(h, port, pw, canvas_uuid=canvasUuid or "")
        return json.dumps({"items": items, "error": err}, ensure_ascii=False)

    @Slot(str, str, result=str)
    def obsListSceneSourcesJson(self, canvasUuid: str, sceneName: str) -> str:
        """JSON ``{items:[{name,value}], error: str|null}`` — ``GetSceneItemList``."""
        w = self._win()
        h, port, pw = _obs_host_port_password_from_main(w)
        items, err = obs_list_scene_sources(
            h,
            port,
            pw,
            canvas_uuid=canvasUuid or "",
            scene_name=sceneName or "",
        )
        return json.dumps({"items": items, "error": err}, ensure_ascii=False)

    def _preview_engine_run(self, w: typing.Any, rule: RuleV1, p: str) -> str:
        """Schedule preview tasks for a resolved RuleV1 (saved disk rules or live UI object)."""
        # IMPORTANT: use a fresh engine instance for preview, so that session-local counters
        # (likes totals, first-activity one-shot gates, etc.) never block the preview.
        ps = w._overlay_server.pubsub()  # type: ignore[attr-defined]  # noqa: SLF001
        wants_overlay = any(
            isinstance(a, dict) and str(a.get("type") or "").strip() == "show_overlay"
            for a in rule.actions
        )
        status_cb = getattr(w, "_on_user_status", None)  # noqa: SLF001

        def _noop_status(_msg: str) -> None:
            return None

        if not callable(status_cb):
            status_cb = _noop_status
        tts_cb = getattr(w, "speak_action_tts", None)
        if not callable(tts_cb):
            tts_cb = None
        eng = PlatformActionsEngine(
            w._sink,  # type: ignore[attr-defined]  # noqa: SLF001
            [rule],
            status_callback=status_cb,
            tts_speak=tts_cb,
            pubsub=ps,
            obs_execute=getattr(w, "_obs_execute_for_actions", None),  # noqa: SLF001
        )
        now = datetime.now(UTC)

        ev0 = pick_preview_trigger_for_rule(rule.events, actions=rule.actions, store_platform=p)
        ev_type = (ev0.get("type") or "").strip()
        if ev_type == "chat_keyword":
            params = ev0.get("params") or {}
            kw = ""
            if isinstance(params, dict):
                kw = str(params.get("text") or params.get("keyword") or "").strip()
            if not kw:
                kw = "test"
            tp_eff = trigger_platform_effective(ev0)
            chat_plat = chat_platform_for_preview(tp_eff, store_platform=p)
            ev = ChatMessageEvent(
                platform=chat_plat,
                author="preview",
                text=f"{kw}",
                received_at=now,
            )
            _schedule_preview_task(eng.on_chat_message(ev))
            msg = ""
            if wants_overlay and ps is None:
                msg = "Overlay preview unavailable (overlay server missing)."
            return msg

        if ev_type == "gift_received":
            params = ev0.get("params") or {}
            gift_id = ""
            gift_name = ""
            min_count = 1
            if isinstance(params, dict):
                gift_id = str(params.get("gift_id") or "").strip()
                gift_name = str(params.get("gift_name") or "").strip()
                try:
                    min_count = int(params.get("min_count", 1))
                except (TypeError, ValueError):
                    min_count = 1
            if min_count < 1:
                min_count = 1
            tp_g = trigger_platform_effective(ev0)
            gift_plat = (
                ChatPlatform.TIKTOK
                if tp_g in ("all", "tiktok")
                else ChatPlatform.TWITCH
                if tp_g == "twitch"
                else ChatPlatform.YOUTUBE
            )
            ev = GiftReceivedEvent(
                platform=gift_plat,
                sender="preview",
                gift_id=gift_id,
                gift_name=gift_name or "Rose",
                count=min_count,
                gift_icon_url="",
                received_at=now,
            )
            _schedule_preview_task(eng.on_gift_received(ev))
            msg = ""
            if wants_overlay and ps is None:
                msg = "Overlay preview unavailable (overlay server missing)."
            return msg

        if ev_type == "tiktok_likes_received":
            if p != "tiktok":
                return "Preview skipped (likes triggers are TikTok-only)."
            params = ev0.get("params") or {}
            min_count = 1
            scope = "all_users"
            user_s = ""
            if isinstance(params, dict):
                try:
                    min_count = int(params.get("min_count", 1))
                except (TypeError, ValueError):
                    min_count = 1
                if min_count < 1:
                    min_count = 1
                sc = str(params.get("scope") or "all_users").strip()
                if sc in ("all_users", "user_stream", "user_combo", "user_every_n"):
                    scope = sc
                user_s = str(params.get("user") or "").strip()
            # Synthetic batch sized to min_count (fresh engine; no cumulative totals).
            # user_combo / user_every_n with empty user matches any viewer; use a display name for
            # preview.
            display_user = (
                (user_s or "preview") if scope in ("user_combo", "user_every_n") else "preview"
            )
            likes_preview_n = max(1, min_count)
            _schedule_preview_task(
                eng.on_tiktok_likes_received(display_user, likes_preview_n, now)
            )
            msg = ""
            if wants_overlay and ps is None:
                msg = "Overlay preview unavailable (overlay server missing)."
            return msg

        if ev_type == "tiktok_joined":
            if p != "tiktok":
                return "Preview skipped (TikTok-only trigger)."
            params = ev0.get("params") or {}
            u = "preview"
            if isinstance(params, dict):
                u = str(params.get("user") or "preview").strip() or "preview"
            _schedule_preview_task(eng.on_tiktok_joined(u, now))
            msg = ""
            if wants_overlay and ps is None:
                msg = "Overlay preview unavailable (overlay server missing)."
            return msg

        if ev_type == "tiktok_followed":
            if p != "tiktok":
                return "Preview skipped (TikTok-only trigger)."
            params = ev0.get("params") or {}
            u = "preview"
            if isinstance(params, dict):
                u = str(params.get("user") or "preview").strip() or "preview"
            _schedule_preview_task(eng.on_tiktok_followed(u, now))
            msg = ""
            if wants_overlay and ps is None:
                msg = "Overlay preview unavailable (overlay server missing)."
            return msg

        if ev_type == "tiktok_shared":
            if p != "tiktok":
                return "Preview skipped (TikTok-only trigger)."
            params = ev0.get("params") or {}
            u = "preview"
            n = 1
            if isinstance(params, dict):
                u = str(params.get("user") or "preview").strip() or "preview"
                try:
                    n = int(params.get("min_count", 1))
                except (TypeError, ValueError):
                    n = 1
            if n < 1:
                n = 1
            _schedule_preview_task(eng.on_tiktok_shared(u, n, now))
            msg = ""
            if wants_overlay and ps is None:
                msg = "Overlay preview unavailable (overlay server missing)."
            return msg

        if ev_type == "tiktok_paid_subscribed":
            if p != "tiktok":
                return "Preview skipped (TikTok-only trigger)."
            params = ev0.get("params") or {}
            u = "preview"
            if isinstance(params, dict):
                u = str(params.get("user") or "preview").strip() or "preview"
            _schedule_preview_task(eng.on_tiktok_paid_subscribed(u, now))
            msg = ""
            if wants_overlay and ps is None:
                msg = "Overlay preview unavailable (overlay server missing)."
            return msg

        if ev_type == "tiktok_first_activity":
            if p != "tiktok":
                return "Preview skipped (TikTok-only trigger)."
            params = ev0.get("params") or {}
            u = "preview"
            if isinstance(params, dict):
                u = str(params.get("user") or "preview").strip() or "preview"
            # Trigger first activity by simulating a join (engine will gate one-shot).
            _schedule_preview_task(eng.on_tiktok_joined(u, now))
            msg = ""
            if wants_overlay and ps is None:
                msg = "Overlay preview unavailable (overlay server missing)."
            return msg

        if ev_type == "twitch_follow":
            if p != "twitch":
                return "Preview skipped (Twitch-only trigger)."
            params = ev0.get("params") or {}
            u = "preview"
            if isinstance(params, dict):
                u = str(params.get("user") or "preview").strip() or "preview"
            _schedule_preview_task(eng.on_twitch_follow(u, now))
            msg = ""
            if wants_overlay and ps is None:
                msg = "Overlay preview unavailable (overlay server missing)."
            return msg

        if ev_type == "twitch_subscribe":
            if p != "twitch":
                return "Preview skipped (Twitch-only trigger)."
            params = ev0.get("params") or {}
            u = "preview"
            if isinstance(params, dict):
                u = str(params.get("user") or "preview").strip() or "preview"
            _schedule_preview_task(eng.on_twitch_subscribe(u, 1, now))
            msg = ""
            if wants_overlay and ps is None:
                msg = "Overlay preview unavailable (overlay server missing)."
            return msg

        if ev_type == "twitch_resub":
            if p != "twitch":
                return "Preview skipped (Twitch-only trigger)."
            params = ev0.get("params") or {}
            u = "preview"
            if isinstance(params, dict):
                u = str(params.get("user") or "preview").strip() or "preview"
            _schedule_preview_task(eng.on_twitch_resub(u, 3, "thanks!", now))
            msg = ""
            if wants_overlay and ps is None:
                msg = "Overlay preview unavailable (overlay server missing)."
            return msg

        if ev_type == "twitch_sub_gift":
            if p != "twitch":
                return "Preview skipped (Twitch-only trigger)."
            params = ev0.get("params") or {}
            u = "preview"
            if isinstance(params, dict):
                u = str(params.get("user") or "preview").strip() or "preview"
            _schedule_preview_task(eng.on_twitch_sub_gift(u, 1, now))
            msg = ""
            if wants_overlay and ps is None:
                msg = "Overlay preview unavailable (overlay server missing)."
            return msg

        if ev_type == "twitch_cheer":
            if p != "twitch":
                return "Preview skipped (Twitch-only trigger)."
            params = ev0.get("params") or {}
            min_bits = 1
            if isinstance(params, dict):
                try:
                    min_bits = int(params.get("min_bits", 1))
                except (TypeError, ValueError):
                    min_bits = 1
            if min_bits < 1:
                min_bits = 1
            u = "preview"
            if isinstance(params, dict):
                u = str(params.get("user") or "preview").strip() or "preview"
            _schedule_preview_task(eng.on_twitch_cheer(u, min_bits, now))
            msg = ""
            if wants_overlay and ps is None:
                msg = "Overlay preview unavailable (overlay server missing)."
            return msg

        if ev_type == "twitch_raid":
            if p != "twitch":
                return "Preview skipped (Twitch-only trigger)."
            params = ev0.get("params") or {}
            min_v = 1
            if isinstance(params, dict):
                try:
                    min_v = int(params.get("min_viewers", 1))
                except (TypeError, ValueError):
                    min_v = 1
            if min_v < 1:
                min_v = 1
            raider = "preview"
            if isinstance(params, dict):
                raider = str(params.get("user") or "preview").strip() or "preview"
            _schedule_preview_task(eng.on_twitch_raid(raider, min_v, now))
            msg = ""
            if wants_overlay and ps is None:
                msg = "Overlay preview unavailable (overlay server missing)."
            return msg

        if ev_type == "tiktok_any_gift_received":
            if p != "tiktok":
                return "Preview skipped (TikTok-only trigger)."
            params = ev0.get("params") or {}
            min_price = 1
            user_s = "preview"
            if isinstance(params, dict):
                try:
                    min_price = int(params.get("min_price", 1))
                except (TypeError, ValueError):
                    min_price = 1
                user_s = str(params.get("user") or "preview").strip() or "preview"
            if min_price < 1:
                min_price = 1
            # Prefer a known priced gift; unknown gifts won't match min_price rules.
            gift_name = "Unknown Gift"
            for g in TIKTOK_GIFTS:
                if not isinstance(g, dict):
                    continue
                price = g.get("price")
                name = g.get("name")
                name_ok = isinstance(name, str) and bool(name.strip())
                if isinstance(price, int) and price >= min_price and name_ok:
                    gift_name = name.strip()
                    break
            ev = GiftReceivedEvent(
                platform=ChatPlatform.TIKTOK,
                sender=user_s,
                gift_id="",
                gift_name=gift_name,
                count=1,
                gift_icon_url="",
                received_at=now,
            )
            _schedule_preview_task(eng.on_gift_received(ev))
            msg = ""
            if wants_overlay and ps is None:
                msg = "Overlay preview unavailable (overlay server missing)."
            return msg

        if ev_type:
            return f'Preview not implemented for trigger type "{ev_type}".'
        return "Preview skipped (no triggers)."

    @Slot(str, str, "QVariantMap", result=str)
    def previewRuleLive(self, platform: str, accountKey: str, rule_map: object) -> str:
        """Preview using the rule from the editor list.

        Includes unsaved edits, e.g. play_sound options.
        """
        w = self._win()
        if w is None:
            return "Preview unavailable (window)."
        p = (platform or "").strip().lower()
        ak = self._store_account_key(p, accountKey)
        if not p or not ak:
            return ""
        try:
            cleaned = json.loads(json.dumps(rule_map))
            if not isinstance(cleaned, dict):
                return "Preview skipped (invalid rule object)."
            rule = rule_from_json_obj(cleaned)
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            return f"Preview skipped ({e})."
        if not rule.enabled:
            return "Preview skipped (rule disabled)."
        return self._preview_engine_run(w, rule, p)

    @Slot(str, str, str, result=str)
    def previewRule(self, platform: str, accountKey: str, ruleId: str) -> str:
        """Simulate a matching event to preview the rule actions (loaded from saved settings)."""
        w = self._win()
        if w is None:
            return "Preview unavailable (window)."
        p = (platform or "").strip().lower()
        ak = self._store_account_key(p, accountKey)
        rid = (ruleId or "").strip()
        if not p or not ak or not rid:
            return ""

        rules = load_rules(p, ak)
        rule = next((r for r in rules if r.id == rid), None)
        if rule is None:
            return "Preview skipped (rule missing)."
        if not rule.enabled:
            return "Preview skipped (rule disabled)."

        return self._preview_engine_run(w, rule, p)
