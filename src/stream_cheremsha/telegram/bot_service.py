from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from stream_cheremsha.chat.video_id import extract_youtube_video_id

logger = logging.getLogger(__name__)

_CB_MENU = "menu"
_CB_ORDER = "order"
_CB_CANCEL = "cancel"
_CB_PLAYER = "player"
_CB_REFRESH = "refresh"
_CB_SKIP = "skip"
_CB_RM_PREFIX = "rm:"  # rm:<track_id>
_CB_RISKY_Y = "risky:y:"  # + pending_id (hex)
_CB_RISKY_N = "risky:n:"

MainLoopCall = Callable[[Callable[[], Awaitable[None]]], None]
ModerationNoticeFn = Callable[[], str]
EnqueueSongOutcome = str | tuple[str, Literal["info"]] | None


@dataclass(frozen=True, slots=True)
class RiskyDecisionResult:
    """Result of admin approve/deny for a risky TikTok-filter pending track."""

    handled: bool
    answer_hint: str


def _safe_user_display(update: Update) -> str:
    u = update.effective_user
    if u is None:
        return "?"
    if u.username:
        return f"@{u.username}"
    parts = [p for p in [u.first_name, u.last_name] if p]
    return " ".join(parts).strip() or str(u.id)


class TelegramBotService:
    """Telegram bot running in its own thread (python-telegram-bot async)."""

    def __init__(
        self,
        *,
        token: str,
        admin_id: int,
        song_requests_enabled: bool,
        call_on_main_loop: MainLoopCall,
        enqueue_song: Callable[[str, str, int], Awaitable[EnqueueSongOutcome]],
        skip_song: Callable[[], Awaitable[None]],
        remove_song_by_id: Callable[[str], Awaitable[bool]],
        list_queue: Callable[
            [int],
            Awaitable[tuple[dict[str, str] | None, list[dict[str, str]]]],
        ],
        on_risky_admin_decision: Callable[[str, bool], Awaitable[RiskyDecisionResult]],
        tiktok_lyrics_filter_enabled: bool = False,
        moderation_notice_text: ModerationNoticeFn | None = None,
    ) -> None:
        self._token = (token or "").strip()
        self._admin_id = int(admin_id)
        self._song_requests_enabled = bool(song_requests_enabled)
        self._tiktok_lyrics_filter_enabled = bool(tiktok_lyrics_filter_enabled)
        self._moderation_notice_text = moderation_notice_text
        self._call_on_main_loop = call_on_main_loop
        self._enqueue_song = enqueue_song
        self._on_risky_admin_decision = on_risky_admin_decision
        self._skip_song = skip_song
        self._remove_song_by_id = remove_song_by_id
        self._list_queue = list_queue

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._app: Application | None = None

        # Per-user state: waiting for a YouTube link after pressing "Order song".
        self._awaiting_link: set[int] = set()

    @property
    def running(self) -> bool:
        t = self._thread
        return t is not None and t.is_alive() and not self._stop.is_set()

    def start(self) -> None:
        if self.running:
            return
        if not self._token:
            raise ValueError("Telegram bot token is empty")
        self._stop.clear()
        self._thread = threading.Thread(target=self._thread_main, name="telegram-bot", daemon=True)
        self._thread.start()

    def stop(self, timeout_sec: float = 6.0) -> None:
        # Only signal the bot thread; shutdown order must be updater.stop → app.stop →
        # app.shutdown inside _run. Scheduling app.stop() from here races _run and causes
        # "This Application is not running!" on exit.
        self._stop.set()
        t = self._thread
        if t is not None:
            t.join(timeout=timeout_sec)
        self._thread = None

    def schedule_risky_review(self, *, pending_id: str, admin_message_html: str) -> None:
        """Called from the main UI thread after a song is flagged Risky by the AI filter."""
        loop = self._loop
        if loop is None:
            logger.warning("Telegram bot: event loop not ready; risky admin prompt skipped")
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self._deliver_risky_admin_prompt(admin_message_html, pending_id),
                loop,
            )
        except Exception as e:
            logger.warning("schedule_risky_review failed: %s", e)

    def send_html_message_to_chat(self, chat_id: int, html: str) -> None:
        """Fire-and-forget HTML message from the main thread (e.g. risky approve/deny notice)."""
        if chat_id <= 0 or not (html or "").strip():
            return
        loop = self._loop
        if loop is None:
            return

        async def _go() -> None:
            app = self._app
            if app is None:
                return
            await app.bot.send_message(
                int(chat_id),
                html,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )

        try:
            asyncio.run_coroutine_threadsafe(_go(), loop)
        except Exception as e:
            logger.warning("send_html_message_to_chat failed: %s", e)

    async def _deliver_risky_admin_prompt(self, admin_message_html: str, pending_id: str) -> None:
        app = self._app
        if app is None:
            return
        y_data = f"{_CB_RISKY_Y}{pending_id}"
        n_data = f"{_CB_RISKY_N}{pending_id}"
        if len(y_data) > 64 or len(n_data) > 64:
            logger.warning("risky callback_data too long for pending_id=%r", pending_id)
            return
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ У чергу", callback_data=y_data),
                    InlineKeyboardButton("❌ Ні", callback_data=n_data),
                ],
            ],
        )
        await app.bot.send_message(
            int(self._admin_id),
            admin_message_html,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
            disable_web_page_preview=True,
        )

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._run())
        except Exception as e:
            logger.exception("Telegram bot thread crashed: %s", e)

    def _main_menu_markup(self, *, is_admin: bool) -> InlineKeyboardMarkup:
        rows: list[list[InlineKeyboardButton]] = []
        if self._song_requests_enabled:
            rows.append([InlineKeyboardButton("Замовити пісню", callback_data=_CB_ORDER)])
        rows.append([InlineKeyboardButton("Меню", callback_data=_CB_MENU)])
        if is_admin:
            rows.append([InlineKeyboardButton("Плеєр", callback_data=_CB_PLAYER)])
        return InlineKeyboardMarkup(rows)

    def _cancel_markup(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton("Скасувати", callback_data=_CB_CANCEL)]])

    async def _teardown_polling_app(self, app: Application) -> None:
        """Stop polling then the application; tolerate duplicate stop during exit."""
        with contextlib.suppress(RuntimeError):
            await app.updater.stop()
        with contextlib.suppress(RuntimeError):
            await app.stop()
        await app.shutdown()

    async def _run(self) -> None:
        self._loop = asyncio.get_running_loop()

        app = Application.builder().token(self._token).build()
        self._app = app

        app.add_handler(CommandHandler("start", self._on_start))
        app.add_handler(CommandHandler("menu", self._on_start))
        app.add_handler(CommandHandler("music", self._on_music))
        app.add_handler(CommandHandler("player", self._on_player))
        app.add_handler(CallbackQueryHandler(self._on_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_text))

        await app.initialize()
        try:
            await app.bot.set_my_commands(
                [
                    BotCommand("start", "Меню"),
                    BotCommand("music", "Замовити пісню"),
                    BotCommand("player", "Плеєр (admin)"),
                    BotCommand("menu", "Меню (швидко)"),
                ],
            )
        except Exception as e:
            # Non-fatal: commands list is UX-only.
            logger.info("Telegram: set_my_commands failed: %s", e)
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        try:
            while not self._stop.is_set():
                await asyncio.sleep(0.25)
        finally:
            await self._teardown_polling_app(app)

    async def _on_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        _ = context
        if update.effective_user is None or update.effective_chat is None:
            return
        is_admin = int(update.effective_user.id) == int(self._admin_id)
        self._awaiting_link.discard(int(update.effective_user.id))
        await update.effective_chat.send_message(
            "Меню:",
            reply_markup=self._main_menu_markup(is_admin=is_admin),
            parse_mode=ParseMode.HTML,
        )

    async def _on_music(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        _ = context
        if update.effective_user is None or update.effective_chat is None:
            return
        if not self._song_requests_enabled:
            await update.effective_chat.send_message("Функція вимкнена в налаштуваннях.")
            return
        uid = int(update.effective_user.id)
        self._awaiting_link.add(uid)
        await update.effective_chat.send_message(
            "Надішли посилання на YouTube (або video id).",
            reply_markup=self._cancel_markup(),
        )

    async def _on_player(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        _ = context
        if update.effective_user is None or update.effective_chat is None:
            return
        if int(update.effective_user.id) != int(self._admin_id):
            await update.effective_chat.send_message("Недостатньо прав.")
            return
        # show admin controls
        await self._render_player(update.effective_chat)

    async def _on_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        _ = context
        q = update.callback_query
        if q is None:
            return
        user = update.effective_user
        uid = int(user.id) if user is not None else 0
        is_admin = uid == int(self._admin_id)
        data = (q.data or "").strip()

        if data.startswith(_CB_RISKY_Y) or data.startswith(_CB_RISKY_N):
            if not is_admin:
                await q.answer("Недостатньо прав.", show_alert=True)
                return
            approved = data.startswith(_CB_RISKY_Y)
            prefix = _CB_RISKY_Y if approved else _CB_RISKY_N
            pid = data[len(prefix) :].strip()
            if not pid:
                await q.answer("Невірний ідентифікатор.", show_alert=True)
                return
            fut: asyncio.Future[RiskyDecisionResult] = asyncio.get_running_loop().create_future()

            async def _work() -> None:
                try:
                    res = await self._on_risky_admin_decision(pid, approved)
                    fut.set_result(res)
                except Exception as e:
                    fut.set_exception(e)

            self._call_on_main_loop(_work)
            try:
                res = await asyncio.wait_for(fut, timeout=120.0)
            except Exception:
                logger.exception("risky admin decision failed")
                await q.answer("Помилка обробки.", show_alert=True)
                return
            hint = (res.answer_hint or "OK").strip()
            if len(hint) > 180:
                hint = hint[:177] + "…"
            await q.answer(hint, show_alert=False)
            if res.handled and q.message is not None:
                try:
                    await q.message.edit_reply_markup(reply_markup=None)
                except Exception as e:
                    logger.debug("edit_reply_markup after risky: %s", e)
            return

        await q.answer()

        if data in (_CB_MENU,):
            if q.message is not None:
                await self._send_menu(q.message, is_admin=is_admin)
            return

        if data == _CB_CANCEL:
            self._awaiting_link.discard(uid)
            if q.message is not None:
                await q.message.reply_text(
                    "Скасовано.", reply_markup=self._main_menu_markup(is_admin=is_admin)
                )
            return

        if data == _CB_ORDER:
            if not self._song_requests_enabled:
                await q.message.reply_text("Функція вимкнена в налаштуваннях.")
                return
            self._awaiting_link.add(uid)
            await q.message.reply_text(
                "Надішли посилання на YouTube (або video id).",
                reply_markup=self._cancel_markup(),
            )
            return

        if data in (_CB_PLAYER, _CB_REFRESH):
            if not is_admin:
                await q.message.reply_text("Недостатньо прав.")
                return
            await self._render_player(q.message)
            return

        if data == _CB_SKIP:
            if not is_admin:
                await q.message.reply_text("Недостатньо прав.")
                return
            self._call_on_main_loop(self._skip_song)
            await q.message.reply_text("⏭️ Skip.")
            return

        if data.startswith(_CB_RM_PREFIX):
            if not is_admin:
                await q.message.reply_text("Недостатньо прав.")
                return
            tid = data[len(_CB_RM_PREFIX) :].strip()
            if not tid:
                await q.message.reply_text("Невірна команда.")
                return

            async def _rm() -> None:
                ok = await self._remove_song_by_id(tid)
                # Response back to user must happen on bot loop, so we send after scheduling:
                await q.message.reply_text("Видалено." if ok else "Немає такого елемента.")

            self._call_on_main_loop(_rm)
            return

    async def _send_menu(self, message, *, is_admin: bool) -> None:  # telegram.Message
        await message.reply_text("Меню:", reply_markup=self._main_menu_markup(is_admin=is_admin))

    async def _render_player(self, message) -> None:  # telegram.Message type (kept loose)
        async def _fetch() -> tuple[dict[str, str] | None, list[dict[str, str]]]:
            return await self._list_queue(12)

        fut: asyncio.Future[tuple[dict[str, str] | None, list[dict[str, str]]]] = (
            asyncio.get_running_loop().create_future()
        )

        async def _run_fetch() -> None:
            cur, q = await _fetch()
            fut.set_result((cur, q))

        self._call_on_main_loop(_run_fetch)
        cur, q = await fut

        lines: list[str] = []
        cur_vid = (cur or {}).get("video_id", "") if cur else ""
        cur_by = (cur or {}).get("requested_by", "") if cur else ""
        lines.append(f"<b>Now</b>: {('<code>' + cur_vid + '</code>') if cur_vid else '—'}")
        if cur_by:
            lines.append(f"<i>by</i> {cur_by}")

        if q:
            lines.append("")
            lines.append("<b>Next</b>:")
            for i, it in enumerate(q[:12], start=1):
                vid = str(it.get("video_id") or "")
                rb = str(it.get("requested_by") or "")
                lines.append(f"{i}. <code>{vid}</code>{(' — ' + rb) if rb else ''}")

        kb: list[list[InlineKeyboardButton]] = []
        kb.append(
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=_CB_REFRESH),
                InlineKeyboardButton("⏭️ Skip", callback_data=_CB_SKIP),
            ],
        )
        if q:
            # One-tap remove for first few items (stable by track_id).
            for it in q[:5]:
                tid = str(it.get("id") or "").strip()
                vid = str(it.get("video_id") or "").strip()
                if not tid or not vid:
                    continue
                kb.append(
                    [InlineKeyboardButton(f"🗑️ Remove {vid}", callback_data=f"{_CB_RM_PREFIX}{tid}")]
                )
        kb.append([InlineKeyboardButton("⬅️ Menu", callback_data=_CB_MENU)])

        await message.reply_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )

    async def _on_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        _ = context
        if update.effective_user is None or update.effective_chat is None:
            return
        uid = int(update.effective_user.id)
        if uid not in self._awaiting_link:
            return
        self._awaiting_link.discard(uid)
        txt = (update.message.text or "").strip() if update.message else ""
        vid = extract_youtube_video_id(txt)
        if not vid:
            await update.effective_chat.send_message(
                "Невірне посилання на YouTube. Спробуй ще раз або натисни «Скасувати».",
                reply_markup=self._cancel_markup(),
            )
            return
        who = _safe_user_display(update)

        if self._tiktok_lyrics_filter_enabled and self._moderation_notice_text is not None:
            notice = self._moderation_notice_text()
            if (notice or "").strip():
                await update.effective_chat.send_message(
                    notice.strip(),
                    reply_markup=self._cancel_markup(),
                )

        fut: asyncio.Future[EnqueueSongOutcome] = asyncio.get_running_loop().create_future()
        chat_id = int(update.effective_chat.id)

        async def _enqueue() -> None:
            out = await self._enqueue_song(vid, who, chat_id)
            fut.set_result(out)

        self._call_on_main_loop(_enqueue)
        outcome = await fut
        is_admin = int(update.effective_user.id) == int(self._admin_id)
        if isinstance(outcome, tuple):
            msg, kind = outcome
            if kind == "info":
                await update.effective_chat.send_message(
                    msg,
                    reply_markup=self._main_menu_markup(is_admin=is_admin),
                    disable_web_page_preview=True,
                )
                return
        if outcome:
            await update.effective_chat.send_message(
                f"❌ {outcome}",
                parse_mode=ParseMode.HTML,
                reply_markup=self._main_menu_markup(is_admin=is_admin),
                disable_web_page_preview=True,
            )
            return
        await update.effective_chat.send_message(
            f"✅ Додано в чергу: <code>{vid}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=self._main_menu_markup(is_admin=is_admin),
            disable_web_page_preview=True,
        )
