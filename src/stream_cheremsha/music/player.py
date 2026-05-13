from __future__ import annotations

import asyncio
import json
import logging
import shutil
import time
import uuid
from collections.abc import Callable
from typing import BinaryIO, Protocol

from stream_cheremsha.chat.video_id import extract_youtube_video_id
from stream_cheremsha.domain.protocols import AudioSink
from stream_cheremsha.music.queue_controller import MusicQueueController


class ResolveResult(Protocol):
    title: str
    audio_bytes: bytes


logger = logging.getLogger(__name__)

ResolveFunc = Callable[[str], ResolveResult]

MusicBackend = str  # "app" | "mpv"


class MusicPlayer:
    """Consume MusicQueueController and play tracks locally via AudioSink."""

    def __init__(
        self,
        *,
        queue: MusicQueueController,
        sink: AudioSink,
        resolver: ResolveFunc | None = None,
        on_status: Callable[[str], None] | None = None,
        backend: MusicBackend = "app",
    ) -> None:
        self._queue = queue
        self._sink = sink
        if resolver is None:
            # Avoid importing yt-dlp at module import time (tests / minimal installs).
            from stream_cheremsha.music.yt_dlp_resolver import resolve_youtube_audio_bytes

            self._resolver = resolve_youtube_audio_bytes
        else:
            self._resolver = resolver
        self._on_status = on_status or (lambda _s: None)
        self._backend: MusicBackend = "mpv" if backend == "mpv" else "app"
        self._volume_percent: int = 100
        self._paused: bool = False
        self._task: asyncio.Task[None] | None = None
        self._play_task: asyncio.Task[None] | None = None
        self._mpv_proc: asyncio.subprocess.Process | None = None
        self._mpv_ipc: str = ""
        self._mpv_lock = asyncio.Lock()
        self._mpv_pipe_r: BinaryIO | None = None
        self._mpv_pipe_w: BinaryIO | None = None
        self._mpv_reader_task: asyncio.Task[None] | None = None
        self._mpv_waiter_task: asyncio.Task[None] | None = None
        self._mpv_events: asyncio.Queue[dict[str, object]] = asyncio.Queue(maxsize=200)
        self._mpv_proc_exited = asyncio.Event()
        self._now_title: str = ""
        self._now_video_id: str = ""
        self._closing = False

    async def _abandon_mpv_state(self, why: str) -> None:
        """Drop IPC state immediately (for fast restart), kill process in background."""
        async with self._mpv_lock:
            proc = self._mpv_proc
            self._status(f"Music: abandoning mpv state ({why})")
            self._stop_mpv_reader_locked()
            self._mpv_proc = None
            self._mpv_ipc = ""
        if proc is not None and proc.returncode is None:
            asyncio.create_task(self._terminate_proc(proc), name="mpv-terminate")

    async def _terminate_proc(self, proc: asyncio.subprocess.Process) -> None:
        try:
            proc.terminate()
        except ProcessLookupError:
            return
        try:
            await asyncio.wait_for(proc.wait(), timeout=1.5)
        except TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                return
            await asyncio.gather(proc.wait(), return_exceptions=True)

    def set_backend(self, backend: MusicBackend) -> None:
        self._backend = "mpv" if backend == "mpv" else "app"

    def set_volume_percent(self, percent: int) -> None:
        p = int(percent)
        self._volume_percent = max(0, min(100, p))
        if self._backend == "mpv":
            asyncio.create_task(self._mpv_set_volume(self._volume_percent))
            return
        # In-app playback: apply volume immediately (affects current playback too).
        set_vol = getattr(self._sink, "set_volume", None)
        if callable(set_vol):
            try:
                set_vol(self._volume_percent / 100.0)
            except (TypeError, ValueError, RuntimeError):
                return

    def now_playing(self) -> tuple[str, str]:
        """(video_id, title)"""
        return (self._now_video_id, self._now_title)

    def is_paused(self) -> bool:
        return bool(self._paused)

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.running:
            return
        self._closing = False
        t = asyncio.create_task(self._loop(), name="music-player")
        t.add_done_callback(MusicPlayer._supervisor_task_done)
        self._task = t

    @staticmethod
    def _supervisor_task_done(task: asyncio.Task[None]) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.error("Music player supervisor exited with error", exc_info=exc)

    async def stop(self) -> None:
        self._closing = True
        await self._kill_mpv()
        if self._play_task is not None:
            self._play_task.cancel()
            await asyncio.gather(self._play_task, return_exceptions=True)
            self._play_task = None
        t = self._task
        self._task = None
        if t is not None:
            t.cancel()
            await asyncio.gather(t, return_exceptions=True)

    async def skip_now(self) -> None:
        self._status("Music: skip requested")
        # Switch queue immediately so the supervisor loop won't restart the old current
        # while we are cancelling/stopping mpv.
        await self._queue.skip()
        cur = await self._queue.current_track()
        self._status(f"Music: skipped -> {(cur.video_id if cur else '—')}")

        # For mpv backend, do NOT kill the process: switch the file in the same window.
        if self._backend == "mpv":
            if cur is None:
                # No next track: close mpv, but never block the UI waiting for it.
                # First, ask mpv to quit via IPC (best-effort).
                await self._mpv_send({"command": ["quit"]})
                await self._abandon_mpv_state("no-next-track")
            elif (cur.video_id or "").strip():
                await self._mpv_load_replace(cur.video_id)
        else:
            # In-app playback: stop current playback ASAP.
            # (Qt sink does not expose a hard-stop; cancelling play_task is enough.)
            pass
        if self._play_task is not None:
            self._play_task.cancel()
            await asyncio.gather(self._play_task, return_exceptions=True)
            self._play_task = None
        self._paused = False

    async def toggle_pause(self) -> None:
        if self._backend == "mpv":
            await self._mpv_toggle_pause()
            self._paused = not self._paused
            return
        pause = getattr(self._sink, "pause", None)
        resume = getattr(self._sink, "resume", None)
        if self._paused:
            if callable(resume):
                resume()
            self._paused = False
        else:
            if callable(pause):
                pause()
                self._paused = True

    def _status(self, s: str) -> None:
        try:
            self._on_status(str(s))
        except Exception:
            return

    async def _loop(self) -> None:
        while not self._closing:
            try:
                cur = await self._queue.current_track()
                if cur is None:
                    # Avoid missing a Condition notify race: periodically re-check.
                    try:
                        await asyncio.wait_for(self._queue.wait_changed(), timeout=0.5)
                    except TimeoutError:
                        pass
                    continue

                # Already playing something: wait for change.
                if self._play_task is not None and not self._play_task.done():
                    try:
                        await asyncio.wait_for(self._queue.wait_changed(), timeout=0.5)
                    except TimeoutError:
                        pass
                    continue

                self._status(f"Music: start track {cur.video_id}")
                self._play_task = asyncio.create_task(self._play_one(cur.id, cur.video_id))
                was_cancelled = False
                finished_naturally = False
                try:
                    finished_naturally = bool(await self._play_task)
                except asyncio.CancelledError:
                    # Skip/stop may cancel the per-track task. Do not let that stop the
                    # supervisor loop; it should continue and pick up the next track.
                    was_cancelled = True
                finally:
                    self._play_task = None

                # Advance only if current is still the same track (not skipped externally).
                cur2 = await self._queue.current_track()
                if (
                    (not was_cancelled)
                    and finished_naturally
                    and cur2 is not None
                    and cur2.id == cur.id
                ):
                    self._status(f"Music: finished {cur.video_id}, advancing queue")
                    await self._queue.skip()
                    # If the queue is now empty, close mpv instead of leaving an idle window.
                    if self._backend == "mpv":
                        cur3 = await self._queue.current_track()
                        if cur3 is None:
                            await self._mpv_send({"command": ["quit"]})
                            await self._abandon_mpv_state("queue-empty")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("MusicPlayer loop crashed: %s", e)
                self._status(f"Music: loop error: {e}")
                await asyncio.sleep(0.2)

    async def _play_one(self, track_id: str, video_id: str) -> bool:
        _ = track_id
        vid = (video_id or "").strip()
        if not vid:
            return False
        self._now_video_id = vid
        self._now_title = ""
        self._paused = False
        if self._backend == "mpv":
            self._status(f"Music: mpv play {vid}")
            await self._play_mpv_track(vid)
            # mpv track finishing is handled inside _play_mpv_track; if it returns, treat as
            # natural.
            return True
        self._status(f"Music: loading {vid}…")
        try:
            res = await asyncio.to_thread(self._resolver, vid)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("Music resolve failed: %s", e)
            self._status(f"Music: failed to load {vid}: {e}")
            return False

        title = (res.title or "").strip()
        self._now_title = title
        if title:
            await self._queue.set_track_title(track_id, title)
        self._status(f"Music: playing {title or vid}")
        try:
            await self._sink.play_mp3(res.audio_bytes)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("Music playback failed: %s", e)
            self._status(f"Music: playback failed: {e}")
            return False
        return True

    async def _kill_mpv(self) -> None:
        async with self._mpv_lock:
            self._stop_mpv_reader_locked()
            await self._kill_mpv_locked()

    def _stop_mpv_reader_locked(self) -> None:
        t = self._mpv_reader_task
        self._mpv_reader_task = None
        if t is not None:
            t.cancel()
        wt = self._mpv_waiter_task
        self._mpv_waiter_task = None
        if wt is not None:
            wt.cancel()
        fr = self._mpv_pipe_r
        fw = self._mpv_pipe_w
        self._mpv_pipe_r = None
        self._mpv_pipe_w = None
        if fr is not None:
            try:
                fr.close()
            except OSError:
                pass
        if fw is not None:
            try:
                fw.close()
            except OSError:
                pass
        # Drop any stale IPC events.
        try:
            while True:
                self._mpv_events.get_nowait()
        except asyncio.QueueEmpty:
            pass
        self._mpv_proc_exited.clear()

    async def _kill_mpv_locked(self) -> None:
        """Kill current mpv process. Caller must hold ``_mpv_lock``."""
        p = self._mpv_proc
        if p is None:
            return
        if p.returncode is not None:
            # Already exited; just clear refs.
            if self._mpv_proc is p:
                self._mpv_proc = None
                self._mpv_ipc = ""
            return
        try:
            # Ask mpv to quit gracefully (best-effort).
            if self._mpv_ipc:
                await self._mpv_send({"command": ["quit"]})
            self._status(f"Music: stopping mpv (pid={p.pid})")
            p.terminate()
        except ProcessLookupError:
            return
        try:
            await asyncio.wait_for(p.wait(), timeout=2.0)
        except TimeoutError:
            try:
                p.kill()
            except ProcessLookupError:
                return
            await asyncio.gather(p.wait(), return_exceptions=True)
        finally:
            self._status("Music: mpv stopped")
            if self._mpv_proc is p:
                self._mpv_proc = None
                self._mpv_ipc = ""

    async def _ensure_mpv_running(self) -> bool:
        async with self._mpv_lock:
            p = self._mpv_proc
            if p is not None and p.returncode is not None:
                # mpv was closed (e.g. by the user). Clean up stale handles so we can restart.
                self._stop_mpv_reader_locked()
                self._mpv_proc = None
                self._mpv_ipc = ""
                p = None
            if (
                p is not None
                and p.returncode is None
                and self._mpv_ipc
                and self._mpv_pipe_r is not None
                and self._mpv_pipe_w is not None
                and self._mpv_reader_task is not None
                and not self._mpv_reader_task.done()
            ):
                return True

            mpv = shutil.which("mpv")
            if not mpv:
                self._status("Music: mpv не знайдено (встанови mpv і додай у PATH)")
                return False

            # Start a persistent mpv instance and control it via IPC. We will "loadfile"
            # for each track to reuse the same window instead of spawning new ones.
            self._stop_mpv_reader_locked()
            self._mpv_ipc = rf"\\.\pipe\cheremsha-mpv-{uuid.uuid4()}"
            self._status("Music: starting mpv…")
            try:
                proc = await asyncio.create_subprocess_exec(
                    mpv,
                    "--no-terminal",
                    "--idle=yes",
                    "--force-window=yes",
                    f"--volume={int(self._volume_percent)}",
                    f"--input-ipc-server={self._mpv_ipc}",
                )
            except OSError as e:
                self._status(f"Music: mpv запуск не вдався: {e}")
                self._mpv_ipc = ""
                return False
            self._mpv_proc = proc
            self._mpv_proc_exited.clear()

        self._status(f"Music: mpv started (pid={proc.pid})")
        # Track mpv lifecycle: if the user closes the window, we must clear IPC state
        # so the next track can restart mpv.
        async with self._mpv_lock:
            if self._mpv_waiter_task is None or self._mpv_waiter_task.done():
                self._mpv_waiter_task = asyncio.create_task(
                    self._mpv_waiter_loop(proc),
                    name="mpv-proc-waiter",
                )

        ok = await self._wait_mpv_ipc_ready(timeout_s=2.0)
        if not ok:
            self._status("Music: mpv IPC not ready (mpv closed?)")
            await self._kill_mpv()
            return False
        await self._ensure_mpv_reader()
        async with self._mpv_lock:
            ready = (
                self._mpv_pipe_r is not None
                and self._mpv_pipe_w is not None
                and self._mpv_proc is not None
                and self._mpv_proc.returncode is None
                and self._mpv_reader_task is not None
                and not self._mpv_reader_task.done()
            )
        if not ready:
            self._status("Music: mpv IPC pipe not ready")
            return False
        self._status("Music: mpv IPC ready")
        return True

    async def _mpv_waiter_loop(self, proc: asyncio.subprocess.Process) -> None:
        try:
            await proc.wait()
        except asyncio.CancelledError:
            raise
        except Exception:
            return
        # Ensure state is cleared even if no IPC event arrived.
        async with self._mpv_lock:
            if self._mpv_proc is proc:
                self._status(f"Music: mpv exited (rc={proc.returncode})")
                self._mpv_proc_exited.set()
                # Also wake up any waiters that might be blocked on events.
                try:
                    self._mpv_events.put_nowait(
                        {"event": "proc-exit", "returncode": proc.returncode}
                    )
                except asyncio.QueueFull:
                    pass
                self._stop_mpv_reader_locked()
                self._mpv_proc = None
                self._mpv_ipc = ""

    async def _ensure_mpv_reader(self) -> None:
        # Never hold the mpv lock while doing a potentially blocking pipe open.
        async with self._mpv_lock:
            if self._mpv_reader_task is not None and not self._mpv_reader_task.done():
                return
            path = self._mpv_ipc
            if not path:
                return
            # If we had stale handles (e.g., reader died), drop them before reopening.
            self._mpv_pipe_r = None
            self._mpv_pipe_w = None

        def _open_pipe_r(p: str) -> BinaryIO:
            # Can block until server (mpv) is ready.
            return open(p, "rb", buffering=0)  # noqa: PTH123

        def _open_pipe_w(p: str) -> BinaryIO:
            return open(p, "wb", buffering=0)  # noqa: PTH123

        try:
            fr = await asyncio.wait_for(asyncio.to_thread(_open_pipe_r, path), timeout=1.5)
            fw = await asyncio.wait_for(asyncio.to_thread(_open_pipe_w, path), timeout=1.5)
        except (TimeoutError, OSError):
            try:
                fr.close()  # type: ignore[possibly-undefined]
            except Exception:
                pass
            return

        async with self._mpv_lock:
            # IPC may have changed while we were opening the pipe.
            if self._mpv_ipc != path:
                try:
                    fr.close()
                    fw.close()
                except OSError:
                    pass
                return
            # Reader may have been started by another task in the meantime.
            if self._mpv_reader_task is not None and not self._mpv_reader_task.done():
                try:
                    fr.close()
                    fw.close()
                except OSError:
                    pass
                return
            self._mpv_pipe_r = fr
            self._mpv_pipe_w = fw
            self._mpv_reader_task = asyncio.create_task(
                self._mpv_reader_loop(), name="mpv-ipc-reader"
            )

    async def _mpv_reader_loop(self) -> None:
        """Read mpv IPC events and enqueue them."""
        while True:
            fr = self._mpv_pipe_r
            if fr is None:
                return

            def _readline() -> bytes:
                return fr.readline()

            try:
                raw = await asyncio.to_thread(_readline)
            except (OSError, ValueError):
                return

            if not raw:
                await asyncio.sleep(0.05)
                continue

            try:
                msg = json.loads(raw.decode("utf-8", errors="replace"))
            except json.JSONDecodeError:
                continue

            if not isinstance(msg, dict):
                continue
            ev = msg.get("event")
            if ev not in ("end-file", "file-loaded"):
                continue
            try:
                self._mpv_events.put_nowait(msg)  # type: ignore[arg-type]
            except asyncio.QueueFull:
                try:
                    _ = self._mpv_events.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    self._mpv_events.put_nowait(msg)  # type: ignore[arg-type]
                except asyncio.QueueFull:
                    pass

    def _mpv_events_drain(self) -> None:
        try:
            while True:
                self._mpv_events.get_nowait()
        except asyncio.QueueEmpty:
            return

    async def _mpv_wait_event(self, name: str, *, timeout_s: float) -> dict[str, object] | None:
        deadline = time.monotonic() + max(0.05, float(timeout_s))
        while time.monotonic() < deadline:
            if self._mpv_proc_exited.is_set():
                return {"event": "proc-exit"}
            remaining = max(0.01, deadline - time.monotonic())
            try:
                msg = await asyncio.wait_for(self._mpv_events.get(), timeout=remaining)
            except TimeoutError:
                return None
            ev = msg.get("event") if isinstance(msg, dict) else None
            if ev == name:
                return msg
        return None

    @staticmethod
    def _normalize_mpv_url(video_id_or_url: str) -> str:
        raw = (video_id_or_url or "").strip()
        # Accept either URL or id; normalize to watch URL for mpv.
        url = raw if "://" in raw else f"https://www.youtube.com/watch?v={raw}"
        # If the user pasted a non-YouTube URL, keep it as-is.
        if extract_youtube_video_id(raw) and "://" in raw and "youtube" not in raw:
            url = raw
        return url

    async def _mpv_stop_playback(self) -> None:
        # Best-effort: stop current file but keep window open (idle).
        await self._mpv_send({"command": ["stop"]})

    async def _mpv_load_replace(self, video_id_or_url: str) -> None:
        url = self._normalize_mpv_url(video_id_or_url)
        if not await self._ensure_mpv_running():
            self._status("Music: mpv not ready for loadfile; restarting")
            await self._abandon_mpv_state("loadfile-not-ready")
            if not await self._ensure_mpv_running():
                self._status("Music: mpv still not ready")
                return
        self._status("Music: mpv loadfile (replace)…")
        ok = await self._mpv_send({"command": ["loadfile", url, "replace"]})
        if ok:
            self._status("Music: mpv loadfile ok")
            return
        self._status("Music: mpv loadfile failed; restarting")
        await self._abandon_mpv_state("loadfile-failed")
        if not await self._ensure_mpv_running():
            self._status("Music: mpv restart failed")
            return
        ok2 = await self._mpv_send({"command": ["loadfile", url, "replace"]})
        self._status("Music: mpv loadfile ok" if ok2 else "Music: mpv loadfile failed")

    async def _mpv_get_property(self, name: str) -> object | None:
        """Best-effort property read. Returns None on any error."""
        req_id = uuid.uuid4().int & 0x7FFFFFFF
        # mpv replies on the same pipe; we do not have a read loop, so this is best-effort.
        # To avoid blocking, we rely on idle-active polling via existence of playback-time.
        _ = req_id
        await self._mpv_send({"command": ["get_property", name]})
        return None

    async def _play_mpv_track(self, video_id_or_url: str) -> None:
        """Play one track in mpv.

        If mpv is closed by the user, restart mpv and continue the *same* track.
        We only return when mpv reports end-of-file (normal completion) or when cancelled.
        """
        url = self._normalize_mpv_url(video_id_or_url)

        while True:
            if self._closing:
                return

            # Ensure mpv + IPC are ready; if not, keep trying.
            if not await self._ensure_mpv_running():
                await asyncio.sleep(0.2)
                continue

            self._status("Music: opening in mpv…")
            self._mpv_events_drain()

            ok = await self._mpv_send({"command": ["loadfile", url, "replace"]})
            if not ok:
                self._status("Music: mpv loadfile failed; restarting mpv")
                await self._kill_mpv()
                await asyncio.sleep(0.2)
                continue

            # Wait for file-loaded. If it never arrives, treat it as broken IPC and restart.
            file_loaded_deadline = time.monotonic() + 5.0
            while True:
                if self._closing:
                    return
                msg = await self._mpv_wait_event("file-loaded", timeout_s=0.6)
                if msg is not None and msg.get("event") == "proc-exit":
                    self._status("Music: mpv closed; restarting same track")
                    await self._kill_mpv()
                    await asyncio.sleep(0.2)
                    break
                if msg is not None:
                    break
                if time.monotonic() >= file_loaded_deadline:
                    self._status("Music: mpv did not load file; restarting same track")
                    await self._kill_mpv()
                    await asyncio.sleep(0.2)
                    break

            # If we broke out due to restart request, restart outer loop.
            if self._mpv_proc_exited.is_set():
                continue

            # Now wait for end-file. If reason indicates user closed mpv / quit, restart.
            while True:
                if self._closing:
                    return
                msg = await self._mpv_wait_event("end-file", timeout_s=0.6)
                if msg is not None and msg.get("event") == "proc-exit":
                    self._status("Music: mpv closed; restarting same track")
                    await self._kill_mpv()
                    await asyncio.sleep(0.2)
                    break
                if msg is None:
                    continue

                reason = str(msg.get("reason") or "").strip()
                if reason in ("eof", "stop"):
                    # eof = natural end; stop may happen on loadfile replace for old file.
                    # In both cases, treat current file as completed.
                    return
                if reason in ("quit", "error"):
                    self._status(f"Music: mpv end-file reason={reason}; restarting same track")
                    await self._abandon_mpv_state(f"end-file:{reason}")
                    break
                # Unknown reasons: be conservative and restart same track.
                self._status(f"Music: mpv end-file reason={reason or '??'}; restarting same track")
                await self._abandon_mpv_state(f"end-file:{reason or '??'}")
                break

    async def _wait_mpv_ipc_ready(self, *, timeout_s: float) -> bool:
        path = self._mpv_ipc
        proc = self._mpv_proc
        if not path or proc is None:
            return False
        deadline = time.monotonic() + max(0.05, float(timeout_s))

        def _probe() -> bool:
            try:
                with open(path, "r+b", buffering=0):  # noqa: PTH123
                    return True
            except OSError:
                return False

        while time.monotonic() < deadline:
            if proc.returncode is not None:
                return False
            # Never let a named-pipe open block forever (Windows quirk).
            try:
                ok = await asyncio.wait_for(asyncio.to_thread(_probe), timeout=0.25)
            except TimeoutError:
                ok = False
            if ok:
                return True
            await asyncio.sleep(0.05)
        return False

    async def _mpv_send(self, obj: dict[str, object]) -> bool:
        path = self._mpv_ipc
        if not path:
            return False

        raw = (json.dumps(obj) + "\n").encode("utf-8")
        # Never block the event loop on pipe I/O; do it in a worker thread.
        async with self._mpv_lock:
            fw = self._mpv_pipe_w
            p = self._mpv_proc
            if p is None or p.returncode is not None:
                return False
        if fw is None:
            return False

        def _write() -> None:
            fw.write(raw)
            try:
                fw.flush()
            except Exception:
                pass

        try:
            await asyncio.wait_for(asyncio.to_thread(_write), timeout=0.5)
        except (TimeoutError, OSError, ValueError):
            return False
        return True

    async def _mpv_toggle_pause(self) -> None:
        await self._mpv_send({"command": ["cycle", "pause"]})

    async def _mpv_set_volume(self, percent: int) -> None:
        await self._mpv_send({"command": ["set_property", "volume", int(percent)]})
