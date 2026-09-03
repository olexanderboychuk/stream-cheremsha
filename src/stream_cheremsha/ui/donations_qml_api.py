"""QML bridge for the «Your donations» tab (Donatik, Donatello, …)."""

from __future__ import annotations

import asyncio
import json
import logging
import typing
import weakref

import httpx
from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox

from stream_cheremsha.config import constants, keyring_store
from stream_cheremsha.donations import tts_seen_store as _tts_seen
from stream_cheremsha.donations.donatello_client import fetch_donatello_donates
from stream_cheremsha.donations.donatik_client import fetch_donations

if typing.TYPE_CHECKING:
    from stream_cheremsha.ui.main_window import MainWindow

logger = logging.getLogger(__name__)

_SETTINGS_DONATIK_LIVE = "donations/donatik_live_poll"
_SETTINGS_DONATIK_TTS = "donations/donatik_tts_new"
_SETTINGS_DONATELLO_LIVE = "donations/donatello_live_poll"
_SETTINGS_DONATELLO_TTS = "donations/donatello_tts_new"

_SEEN_CAP = 4000
_MSG_TTS_MAX = 240


def donation_row_amount_name_donatik(row: dict) -> tuple[str, float]:
    name = str(row.get("name") or "—").strip() or "—"
    pay = row.get("payment") if isinstance(row.get("payment"), dict) else {}
    raw = pay.get("amount") if isinstance(pay, dict) else row.get("amount")
    try:
        amount = float(raw)
    except (TypeError, ValueError):
        amount = 0.0
    return name, max(0.0, amount)


def donation_row_amount_name_donatello(row: dict) -> tuple[str, float]:
    name = str(row.get("clientName") or "—").strip() or "—"
    raw = row.get("amount")
    try:
        amount = float(raw)
    except (TypeError, ValueError):
        amount = 0.0
    return name, max(0.0, amount)


class DonationsQmlApi(QObject):
    """Exposes donation list fetch + token persistence to Qt Quick."""

    donatikLoadingChanged = Signal()
    donatelloLoadingChanged = Signal()
    errorMessageChanged = Signal()
    donationsJsonChanged = Signal()
    listMetaChanged = Signal()
    donatikConfiguredChanged = Signal()
    donatelloJsonChanged = Signal()
    donatelloMetaChanged = Signal()
    donatelloConfiguredChanged = Signal()
    donatikLivePollChanged = Signal()
    donatikTtsNewChanged = Signal()
    donatelloLivePollChanged = Signal()
    donatelloTtsNewChanged = Signal()
    uiTickChanged = Signal()

    def __init__(self, main: MainWindow) -> None:
        super().__init__(parent=main)
        self._m: weakref.ref[MainWindow] = weakref.ref(main)
        self._donatik_loading = False
        self._donatello_loading = False
        self._error_message = ""
        self._donations_json = "[]"
        self._total = 0
        self._page = 1
        self._per_page = 500
        self._donatik_configured = self._donatik_token_from_store() != ""
        self._donatello_json = "[]"
        self._donatello_page = 0
        self._donatello_pages = 0
        self._donatello_total = 0
        self._donatello_size = 50
        self._donatello_first = True
        self._donatello_last = True
        self._donatello_configured = self._donatello_token_from_store() != ""
        self._ui_tick = 0

        self._donatik_lock = asyncio.Lock()
        self._donatello_lock = asyncio.Lock()
        self._donatik_seen: set[str] = _tts_seen.load_ids(_tts_seen.KEY_DONATIK)
        self._donatello_seen: set[str] = _tts_seen.load_ids(_tts_seen.KEY_DONATELLO)
        self._donatik_prime_poll = False
        self._donatello_prime_poll = False
        self._last_donatik_from = ""
        self._last_donatik_to = ""
        self._donation_listener: typing.Callable[[str, float, str], None] | None = None

        st = self._settings_store()
        self._donatik_live_poll = bool(st and st.value(_SETTINGS_DONATIK_LIVE, False, bool))
        self._donatik_tts_new = bool(st and st.value(_SETTINGS_DONATIK_TTS, False, bool))
        self._donatello_live_poll = bool(st and st.value(_SETTINGS_DONATELLO_LIVE, False, bool))
        self._donatello_tts_new = bool(st and st.value(_SETTINGS_DONATELLO_TTS, False, bool))

        if self._donatik_live_poll and self._donatik_token_from_store() and not self._donatik_seen:
            self._donatik_prime_poll = True
        if (
            self._donatello_live_poll
            and self._donatello_token_from_store()
            and not self._donatello_seen
        ):
            self._donatello_prime_poll = True

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(5000)
        self._poll_timer.timeout.connect(self._on_poll_timer_tick)
        self._refresh_poll_timer()

    def set_donation_listener(self, cb: typing.Callable[[str, float, str], None] | None) -> None:
        self._donation_listener = cb

    def _notify_donation(self, name: str, amount: float, source: str) -> None:
        cb = self._donation_listener
        if cb is None:
            return
        try:
            cb(name, amount, source)
        except (AttributeError, RuntimeError, TypeError, ValueError) as e:
            logger.debug("donation listener failed: %s", e)

    def _settings_store(self):
        w = self._win()
        return w._settings if w is not None else None  # noqa: SLF001

    def _persist_donatik_seen(self) -> None:
        _tts_seen.save_ids(_tts_seen.KEY_DONATIK, self._donatik_seen)

    def _persist_donatello_seen(self) -> None:
        _tts_seen.save_ids(_tts_seen.KEY_DONATELLO, self._donatello_seen)

    def _win(self) -> MainWindow | None:
        return self._m()

    @Property(int, notify=uiTickChanged)
    def uiTick(self) -> int:  # noqa: ANN201
        return self._ui_tick

    @Slot()
    def refreshUi(self) -> None:
        self._ui_tick += 1
        self.uiTickChanged.emit()

    @Property(bool, notify=donatikLivePollChanged)
    def donatikLivePoll(self) -> bool:  # noqa: ANN201
        return self._donatik_live_poll

    @Property(bool, notify=donatikTtsNewChanged)
    def donatikTtsNew(self) -> bool:  # noqa: ANN201
        return self._donatik_tts_new

    @Property(bool, notify=donatelloLivePollChanged)
    def donatelloLivePoll(self) -> bool:  # noqa: ANN201
        return self._donatello_live_poll

    @Property(bool, notify=donatelloTtsNewChanged)
    def donatelloTtsNew(self) -> bool:  # noqa: ANN201
        return self._donatello_tts_new

    @Slot(bool)
    def setDonatikLivePoll(self, on: bool) -> None:
        v = bool(on)
        if v == self._donatik_live_poll:
            return
        self._donatik_live_poll = v
        st = self._settings_store()
        if st is not None:
            st.setValue(_SETTINGS_DONATIK_LIVE, v)
        if v:
            self._donatik_prime_poll = True
        self.donatikLivePollChanged.emit()
        self._refresh_poll_timer()

    @Slot(bool)
    def setDonatikTtsNew(self, on: bool) -> None:
        v = bool(on)
        if v == self._donatik_tts_new:
            return
        self._donatik_tts_new = v
        st = self._settings_store()
        if st is not None:
            st.setValue(_SETTINGS_DONATIK_TTS, v)
        self.donatikTtsNewChanged.emit()

    @Slot(bool)
    def setDonatelloLivePoll(self, on: bool) -> None:
        v = bool(on)
        if v == self._donatello_live_poll:
            return
        self._donatello_live_poll = v
        st = self._settings_store()
        if st is not None:
            st.setValue(_SETTINGS_DONATELLO_LIVE, v)
        if v:
            self._donatello_prime_poll = True
        self.donatelloLivePollChanged.emit()
        self._refresh_poll_timer()

    @Slot(bool)
    def setDonatelloTtsNew(self, on: bool) -> None:
        v = bool(on)
        if v == self._donatello_tts_new:
            return
        self._donatello_tts_new = v
        st = self._settings_store()
        if st is not None:
            st.setValue(_SETTINGS_DONATELLO_TTS, v)
        self.donatelloTtsNewChanged.emit()

    @Slot(str, str)
    def donatikSyncPollDates(self, from_date: str, to_date: str) -> None:
        self._last_donatik_from = (from_date or "").strip()
        self._last_donatik_to = (to_date or "").strip()

    def _refresh_poll_timer(self) -> None:
        t = self._poll_timer
        don_on = self._donatik_live_poll and self._donatik_token_from_store() != ""
        del_on = self._donatello_live_poll and self._donatello_token_from_store() != ""
        if don_on or del_on:
            if not t.isActive():
                t.start()
        else:
            t.stop()

    @Slot()
    def _on_poll_timer_tick(self) -> None:
        asyncio.ensure_future(self._async_poll_tick())

    async def _async_poll_tick(self) -> None:
        if self._donatik_live_poll and self._donatik_token_from_store():
            await self._async_donatik_poll()
        if self._donatello_live_poll and self._donatello_token_from_store():
            await self._async_donatello_poll()

    async def _async_donatik_poll(self) -> None:
        if not self._last_donatik_from or not self._last_donatik_to:
            return
        tts_lines: list[tuple[str, str]] = []
        snap: tuple[str, int] | None = None
        async with self._donatik_lock:
            if self._donatik_loading:
                return
            token = self._donatik_token_from_store()
            if not token:
                return
            try:
                rows, total = await fetch_donations(
                    token,
                    self._last_donatik_from,
                    self._last_donatik_to,
                    page=1,
                    per_page=self._per_page,
                )
            except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError) as e:
                logger.debug("Donatik poll: %s", e)
                return

            ids = _donatik_ids_ordered(rows)
            self._trim_seen(self._donatik_seen, ids)

            if self._donatik_prime_poll:
                self._donatik_seen.update(ids)
                self._donatik_prime_poll = False
            else:
                new_ids = [i for i in ids if i not in self._donatik_seen]
                by_id = {str(r.get("id", "")): r for r in rows if r.get("id")}
                for nid in reversed(new_ids):
                    row = by_id.get(nid)
                    if row is None:
                        continue
                    name, amount = donation_row_amount_name_donatik(row)
                    self._notify_donation(name, amount, "donatik")
                    if self._donatik_tts_new:
                        donor = str(row.get("name") or "—").strip() or "—"
                        tts_lines.append((_donatik_tts_line(self._win(), row), donor))
                self._donatik_seen.update(ids)
            self._persist_donatik_seen()

            if self._page == 1:
                snap = (json.dumps(rows, ensure_ascii=False), int(total))

        for line, donor in tts_lines:
            await self._speak_line(line, donor)
        if snap is not None:
            async with self._donatik_lock:
                self._donations_json = snap[0]
                self._total = snap[1]
                self._page = 1
                self.donationsJsonChanged.emit()
                self.listMetaChanged.emit()

    async def _async_donatello_poll(self) -> None:
        tts_lines: list[tuple[str, str]] = []
        snap: tuple[str, dict[str, typing.Any]] | None = None
        async with self._donatello_lock:
            if self._donatello_loading:
                return
            token = self._donatello_token_from_store()
            if not token:
                return
            try:
                rows, meta = await fetch_donatello_donates(token, page=0, size=self._donatello_size)
            except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError) as e:
                logger.debug("Donatello poll: %s", e)
                return

            ids = _donatello_ids_ordered(rows)
            self._trim_seen(self._donatello_seen, ids)

            if self._donatello_prime_poll:
                self._donatello_seen.update(ids)
                self._donatello_prime_poll = False
            else:
                new_ids = [i for i in ids if i not in self._donatello_seen]
                by_id = {str(r.get("pubId", "")): r for r in rows if r.get("pubId")}
                for nid in reversed(new_ids):
                    row = by_id.get(nid)
                    if row is None:
                        continue
                    name, amount = donation_row_amount_name_donatello(row)
                    self._notify_donation(name, amount, "donatello")
                    if self._donatello_tts_new:
                        donor = str(row.get("clientName") or "—").strip() or "—"
                        tts_lines.append((_donatello_tts_line(self._win(), row), donor))
                self._donatello_seen.update(ids)
            self._persist_donatello_seen()

            if self._donatello_page == 0:
                snap = (json.dumps(rows, ensure_ascii=False), meta)

        for line, donor in tts_lines:
            await self._speak_line(line, donor)
        if snap is not None:
            raw, meta = snap
            async with self._donatello_lock:
                self._donatello_json = raw
                self._donatello_page = int(meta.get("page", 0))
                self._donatello_pages = int(meta.get("pages", 0))
                self._donatello_total = int(meta.get("total", 0))
                self._donatello_size = int(meta.get("size", self._donatello_size))
                self._donatello_first = bool(meta.get("first", True))
                self._donatello_last = bool(meta.get("last", True))
                self.donatelloJsonChanged.emit()
                self.donatelloMetaChanged.emit()

    @staticmethod
    def _trim_seen(seen: set[str], latest_ids: list[str]) -> None:
        if len(seen) <= _SEEN_CAP:
            return
        seen.intersection_update(latest_ids)
        if len(seen) > _SEEN_CAP:
            seen.clear()

    async def _speak_line(self, line: str, donor_name: str | None = None) -> None:
        w = self._win()
        if w is None:
            return
        await w.announce_donation_tts(line, donor_name)  # noqa: SLF001

    @Property(bool, notify=donatikLoadingChanged)
    def donatikLoading(self) -> bool:  # noqa: ANN201
        return self._donatik_loading

    @Property(bool, notify=donatelloLoadingChanged)
    def donatelloLoading(self) -> bool:  # noqa: ANN201
        return self._donatello_loading

    @Property(str, notify=errorMessageChanged)
    def errorMessage(self) -> str:  # noqa: ANN201
        return self._error_message

    @Property(str, notify=donationsJsonChanged)
    def donationsJson(self) -> str:  # noqa: ANN201
        return self._donations_json

    @Property(int, notify=listMetaChanged)
    def total(self) -> int:  # noqa: ANN201
        return self._total

    @Property(int, notify=listMetaChanged)
    def page(self) -> int:  # noqa: ANN201
        return self._page

    @Property(int, notify=listMetaChanged)
    def perPage(self) -> int:  # noqa: ANN201
        return self._per_page

    @Property(bool, notify=donatikConfiguredChanged)
    def donatikConfigured(self) -> bool:  # noqa: ANN201
        return self._donatik_configured

    @Property(str, notify=donatelloJsonChanged)
    def donatelloJson(self) -> str:  # noqa: ANN201
        return self._donatello_json

    @Property(int, notify=donatelloMetaChanged)
    def donatelloPage(self) -> int:  # noqa: ANN201
        return self._donatello_page

    @Property(int, notify=donatelloMetaChanged)
    def donatelloPages(self) -> int:  # noqa: ANN201
        return self._donatello_pages

    @Property(int, notify=donatelloMetaChanged)
    def donatelloTotal(self) -> int:  # noqa: ANN201
        return self._donatello_total

    @Property(int, notify=donatelloMetaChanged)
    def donatelloSize(self) -> int:  # noqa: ANN201
        return self._donatello_size

    @Property(bool, notify=donatelloConfiguredChanged)
    def donatelloConfigured(self) -> bool:  # noqa: ANN201
        return self._donatello_configured

    @Property(bool, notify=donatelloMetaChanged)
    def donatelloFirst(self) -> bool:  # noqa: ANN201
        return self._donatello_first

    @Property(bool, notify=donatelloMetaChanged)
    def donatelloLast(self) -> bool:  # noqa: ANN201
        return self._donatello_last

    @Property(int, notify=listMetaChanged)
    def pageCount(self) -> int:  # noqa: ANN201
        if self._total <= 0:
            return 1
        return max(1, (self._total + self._per_page - 1) // self._per_page)

    @Property(str, notify=listMetaChanged)
    def summaryLine(self) -> str:  # noqa: ANN201
        w = self._win()
        if w is None:
            return ""
        pc = max(1, (self._total + self._per_page - 1) // self._per_page) if self._total > 0 else 1
        return w._tr("donations.summary", n=self._total, p=self._page, pc=pc)  # noqa: SLF001

    @Property(str, notify=donatelloMetaChanged)
    def donatelloSummaryLine(self) -> str:  # noqa: ANN201
        w = self._win()
        if w is None:
            return ""
        pages_disp = self._donatello_pages
        if self._donatello_total > 0 and pages_disp < 1:
            pages_disp = max(
                1,
                (self._donatello_total + self._donatello_size - 1) // max(1, self._donatello_size),
            )
        else:
            pages_disp = max(1, pages_disp) if self._donatello_total > 0 else 1
        p_human = self._donatello_page + 1
        return w._tr(  # noqa: SLF001
            "donations.donatello_summary",
            n=self._donatello_total,
            p=p_human,
            pc=pages_disp,
        )

    @staticmethod
    def _donatik_token_from_store() -> str:
        return (keyring_store.get_password(constants.KEY_DONATIK_API_TOKEN) or "").strip()

    @staticmethod
    def _donatello_token_from_store() -> str:
        return (keyring_store.get_password(constants.KEY_DONATELLO_API_TOKEN) or "").strip()

    def _set_donatik_loading(self, v: bool) -> None:
        if self._donatik_loading != v:
            self._donatik_loading = v
            self.donatikLoadingChanged.emit()

    def _set_donatello_loading(self, v: bool) -> None:
        if self._donatello_loading != v:
            self._donatello_loading = v
            self.donatelloLoadingChanged.emit()

    def _set_error(self, msg: str) -> None:
        self._error_message = msg or ""
        self.errorMessageChanged.emit()

    def _sync_donatik_flag(self) -> None:
        has = self._donatik_token_from_store() != ""
        if has != self._donatik_configured:
            self._donatik_configured = has
            self.donatikConfiguredChanged.emit()
        self._refresh_poll_timer()

    def _sync_donatello_flag(self) -> None:
        has = self._donatello_token_from_store() != ""
        if has != self._donatello_configured:
            self._donatello_configured = has
            self.donatelloConfiguredChanged.emit()
        self._refresh_poll_timer()

    @Slot(str, result=str)
    def loc(self, key: str) -> str:
        w = self._win()
        if w is None:
            return key
        return w._tr(key)  # noqa: SLF001

    @Slot(str)
    def openUrl(self, url: str) -> None:
        u = (url or "").strip()
        if u.startswith("http://") or u.startswith("https://"):
            QDesktopServices.openUrl(QUrl(u))

    @Slot(str, str, str)
    def donatikFetch(self, from_date: str, to_date: str, page: str) -> None:
        try:
            pg = max(1, int((page or "1").strip() or "1"))
        except ValueError:
            pg = 1
        asyncio.ensure_future(self._async_donatik_fetch(from_date, to_date, pg))

    async def _async_donatik_fetch(self, from_date: str, to_date: str, page: int) -> None:
        w = self._win()
        token = self._donatik_token_from_store()
        if not token:
            self._set_error(w._tr("donations.err_no_token") if w else "No token")  # noqa: SLF001
            return
        async with self._donatik_lock:
            self._set_donatik_loading(True)
            self._set_error("")
            try:
                rows, total = await fetch_donations(
                    token,
                    from_date.strip(),
                    to_date.strip(),
                    page=page,
                    per_page=self._per_page,
                )
            except httpx.HTTPStatusError as e:
                detail = _http_error_detail(e)
                code = e.response.status_code
                self._set_error(
                    w._tr("donations.err_http", code=code, detail=detail) if w else f"HTTP {code}",  # noqa: SLF001
                )
            except (httpx.TimeoutException, httpx.RequestError) as e:
                self._set_error(
                    w._tr("donations.err_network", detail=str(e)) if w else str(e),  # noqa: SLF001
                )
            except (ValueError, TypeError, KeyError, OSError) as e:
                logger.exception("Donatik fetch")
                self._set_error(
                    w._tr("donations.err_bad_response", detail=str(e)) if w else str(e),  # noqa: SLF001
                )
            else:
                self._last_donatik_from = from_date.strip()
                self._last_donatik_to = to_date.strip()
                self._donations_json = json.dumps(rows, ensure_ascii=False)
                self._total = total
                self._page = page
                self.donationsJsonChanged.emit()
                self.listMetaChanged.emit()
                self._donatik_seen = set(_donatik_ids_ordered(rows))
                self._donatik_prime_poll = False
                self._persist_donatik_seen()
            finally:
                self._set_donatik_loading(False)

    @Slot(str, result=bool)
    def donatikSaveToken(self, token: str) -> bool:
        w = self._win()
        t = (token or "").strip()
        if not t:
            return False
        prev = self._donatik_token_from_store().strip()
        try:
            keyring_store.set_password(constants.KEY_DONATIK_API_TOKEN, t)
        except RuntimeError as e:
            if w is not None:
                QMessageBox.warning(w, w._tr("dlg.keyring"), str(e))  # noqa: SLF001
            return False
        if prev != t:
            self._donatik_seen.clear()
            _tts_seen.clear_provider(_tts_seen.KEY_DONATIK)
            if self._donatik_live_poll:
                self._donatik_prime_poll = True
        self._sync_donatik_flag()
        return True

    @Slot()
    def donatikForgetToken(self) -> None:
        keyring_store.delete_password(constants.KEY_DONATIK_API_TOKEN)
        self._donations_json = "[]"
        self._total = 0
        self._page = 1
        self._donatik_seen.clear()
        _tts_seen.clear_provider(_tts_seen.KEY_DONATIK)
        self._last_donatik_from = ""
        self._last_donatik_to = ""
        self._set_error("")
        self.donationsJsonChanged.emit()
        self.listMetaChanged.emit()
        self._sync_donatik_flag()
        st = self._settings_store()
        if st is not None:
            st.setValue(_SETTINGS_DONATIK_LIVE, False)
            st.setValue(_SETTINGS_DONATIK_TTS, False)
        self._donatik_live_poll = False
        self._donatik_tts_new = False
        self.donatikLivePollChanged.emit()
        self.donatikTtsNewChanged.emit()
        self._refresh_poll_timer()

    @Slot(str)
    def donatelloFetch(self, page: str) -> None:
        try:
            pg = int((page or "0").strip() or "0")
        except ValueError:
            pg = 0
        asyncio.ensure_future(self._async_donatello_fetch(max(0, pg)))

    async def _async_donatello_fetch(self, page: int) -> None:
        w = self._win()
        token = self._donatello_token_from_store()
        if not token:
            self._set_error(
                w._tr("donations.err_no_token_donatello") if w else "No token",  # noqa: SLF001
            )
            return
        async with self._donatello_lock:
            self._set_donatello_loading(True)
            self._set_error("")
            try:
                rows, meta = await fetch_donatello_donates(
                    token,
                    page=page,
                    size=self._donatello_size,
                )
            except httpx.HTTPStatusError as e:
                detail = _http_error_detail(e)
                code = e.response.status_code
                self._set_error(
                    w._tr("donations.err_http_donatello", code=code, detail=detail)  # noqa: SLF001
                    if w
                    else f"HTTP {code}",
                )
            except (httpx.TimeoutException, httpx.RequestError) as e:
                self._set_error(
                    w._tr("donations.err_network_donatello", detail=str(e)) if w else str(e),  # noqa: SLF001
                )
            except (ValueError, TypeError, KeyError, OSError) as e:
                logger.exception("Donatello fetch")
                self._set_error(
                    w._tr("donations.err_bad_response_donatello", detail=str(e)) if w else str(e),  # noqa: SLF001
                )
            else:
                self._donatello_json = json.dumps(rows, ensure_ascii=False)
                self._donatello_page = int(meta.get("page", page))
                self._donatello_pages = int(meta.get("pages", 0))
                self._donatello_total = int(meta.get("total", 0))
                self._donatello_size = int(meta.get("size", self._donatello_size))
                self._donatello_first = bool(meta.get("first", True))
                self._donatello_last = bool(meta.get("last", True))
                self.donatelloJsonChanged.emit()
                self.donatelloMetaChanged.emit()
                self._donatello_seen = set(_donatello_ids_ordered(rows))
                self._donatello_prime_poll = False
                self._persist_donatello_seen()
            finally:
                self._set_donatello_loading(False)

    @Slot(str, result=bool)
    def donatelloSaveToken(self, token: str) -> bool:
        w = self._win()
        t = (token or "").strip()
        if not t:
            return False
        prev = self._donatello_token_from_store().strip()
        try:
            keyring_store.set_password(constants.KEY_DONATELLO_API_TOKEN, t)
        except RuntimeError as e:
            if w is not None:
                QMessageBox.warning(w, w._tr("dlg.keyring"), str(e))  # noqa: SLF001
            return False
        if prev != t:
            self._donatello_seen.clear()
            _tts_seen.clear_provider(_tts_seen.KEY_DONATELLO)
            if self._donatello_live_poll:
                self._donatello_prime_poll = True
        self._sync_donatello_flag()
        return True

    @Slot()
    def donatelloForgetToken(self) -> None:
        keyring_store.delete_password(constants.KEY_DONATELLO_API_TOKEN)
        self._donatello_json = "[]"
        self._donatello_page = 0
        self._donatello_pages = 0
        self._donatello_total = 0
        self._donatello_first = True
        self._donatello_last = True
        self._donatello_seen.clear()
        _tts_seen.clear_provider(_tts_seen.KEY_DONATELLO)
        self._set_error("")
        self.donatelloJsonChanged.emit()
        self.donatelloMetaChanged.emit()
        self._sync_donatello_flag()
        st = self._settings_store()
        if st is not None:
            st.setValue(_SETTINGS_DONATELLO_LIVE, False)
            st.setValue(_SETTINGS_DONATELLO_TTS, False)
        self._donatello_live_poll = False
        self._donatello_tts_new = False
        self.donatelloLivePollChanged.emit()
        self.donatelloTtsNewChanged.emit()
        self._refresh_poll_timer()


def _donatik_ids_ordered(rows: list[dict]) -> list[str]:
    out: list[str] = []
    for r in rows:
        rid = r.get("id")
        if rid is None:
            continue
        s = str(rid).strip()
        if s:
            out.append(s)
    return out


def _donatello_ids_ordered(rows: list[dict]) -> list[str]:
    out: list[str] = []
    for r in rows:
        pid = r.get("pubId")
        if pid is None:
            continue
        s = str(pid).strip()
        if s:
            out.append(s)
    return out


def _donatik_tts_line(w: MainWindow | None, row: dict) -> str:
    if w is None:
        return ""
    name = str(row.get("name") or "—").strip() or "—"
    pay = row.get("payment") if isinstance(row.get("payment"), dict) else {}
    amt = str(pay.get("amount") if isinstance(pay, dict) else "") or "?"
    cur = str(pay.get("currency") if isinstance(pay, dict) else "").strip()
    msg = str(row.get("message") or "").replace("\n", " ").strip()
    if len(msg) > _MSG_TTS_MAX:
        msg = msg[: _MSG_TTS_MAX - 1] + "…"
    if not msg:
        msg = "—"
    return w._tr("donations.tts_announce", author=name, amount=amt, currency=cur, message=msg)  # noqa: SLF001


def _donatello_tts_line(w: MainWindow | None, row: dict) -> str:
    if w is None:
        return ""
    name = str(row.get("clientName") or "—").strip() or "—"
    amt = str(row.get("amount") or "").strip() or "?"
    cur = str(row.get("currency") or "").strip()
    msg = str(row.get("message") or "").replace("\n", " ").strip()
    if len(msg) > _MSG_TTS_MAX:
        msg = msg[: _MSG_TTS_MAX - 1] + "…"
    if not msg:
        msg = "—"
    return w._tr("donations.tts_announce", author=name, amount=amt, currency=cur, message=msg)  # noqa: SLF001


def _http_error_detail(e: httpx.HTTPStatusError) -> str:
    try:
        raw = (e.response.text or "")[:400]
    except OSError:
        return ""
    try:
        data = e.response.json()
    except (ValueError, json.JSONDecodeError, OSError):
        return raw
    if isinstance(data, dict):
        msg = data.get("message")
        if isinstance(msg, str) and msg.strip():
            return msg.strip()
    return raw
