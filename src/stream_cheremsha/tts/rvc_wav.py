"""RVC (Retrieval-based Voice Conversion) post-process for any TTS output, via ``rvc-python``."""

from __future__ import annotations

import asyncio
import ctypes
import gc
import logging
import multiprocessing
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from itertools import count
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Any, Final

logger = logging.getLogger(__name__)

_RVC_LOAD_TIMEOUT_SEC = 600.0
_RVC_INFER_TIMEOUT_SEC = 600.0

_TORCH_LOAD_PATCHED: bool = False
_RVC_STACK_IMPORT_ERROR: str | None = None


def clear_rvc_python_pipeline_caches() -> tuple[int, bool, bool]:
    """Clear rvc_python module-level RAM leaks (not touched by ``unload_model``).

    ``pipeline.input_audio_path2wav`` stores full float64 audio per temp path forever;
    ``cache_harvest_f0`` LRU holds derived arrays. Both grow with every RVC chunk.

    Returns ``(path2wav_entries_cleared, harvest_lru_cleared, import_ok)``.
    """
    try:
        from rvc_python.modules.vc import pipeline as rvc_pipe  # noqa: PLC0415
    except ImportError:
        logger.warning("RVC pipeline cache: skip (rvc_python not importable)")
        return 0, False, False

    n_path = 0
    blob = getattr(rvc_pipe, "input_audio_path2wav", None)
    if isinstance(blob, dict):
        n_path = len(blob)
        blob.clear()

    harvest_ok = False
    harvest = getattr(rvc_pipe, "cache_harvest_f0", None)
    if callable(harvest) and hasattr(harvest, "cache_clear"):
        harvest.cache_clear()
        harvest_ok = True

    return n_path, harvest_ok, True


def release_rvc_torch_memory() -> None:
    """Release RVC-related host RAM and (if used) CUDA cache after unload.

    PyTorch + NumPy can leave a large glibc heap; ``malloc_trim(0)`` on Linux nudges
    the C allocator to return pages to the kernel so RSS drops in ``top``/System Monitor.
    """
    n_path, harvest_ok, pipe_import_ok = clear_rvc_python_pipeline_caches()
    gc.collect()
    gc.collect()
    host_ok = False
    cuda_ok = False
    torch_err: str | None = None
    try:
        import torch  # noqa: PLC0415

        host_empty = getattr(torch._C, "_host_emptyCache", None)
        if callable(host_empty):
            host_empty()
            host_ok = True
        if torch.cuda.is_available():
            torch.cuda.synchronize()
            torch.cuda.empty_cache()
            cuda_ok = True
    except (ImportError, RuntimeError) as e:
        torch_err = str(e)
        logger.debug("RVC torch memory release: %s", e)

    trim_ok = False
    if sys.platform.startswith("linux"):
        try:
            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
            trim_ok = True
        except (AttributeError, OSError) as e:
            logger.debug("malloc_trim after RVC unload: %s", e)

    logger.info(
        "RVC memory trim: pipeline_import=%s path2wav_cleared=%s harvest_lru=%s "
        "torch_host_empty=%s cuda_empty=%s malloc_trim=%s%s",
        pipe_import_ok,
        n_path,
        harvest_ok,
        host_ok,
        cuda_ok,
        trim_ok,
        f" torch_note={torch_err!r}" if torch_err else "",
    )


def _patch_torch_load_for_fairseq_checkpoints() -> None:
    """Restore full unpickle for fairseq Hubert: PyTorch 2.6+ default ``weights_only`` breaks it."""
    global _TORCH_LOAD_PATCHED
    if _TORCH_LOAD_PATCHED:
        return
    import torch  # noqa: PLC0415

    _orig: Callable[..., Any] = torch.load

    def _patched(f: object, *args: object, **kwargs: object) -> object:
        if "weights_only" not in kwargs:
            kwargs = {**kwargs, "weights_only": False}
        return _orig(f, *args, **kwargs)

    torch.load = _patched
    _TORCH_LOAD_PATCHED = True


def _rvc_work_dir() -> str | None:
    """Use RAM-backed temp dir (e.g. /dev/shm) when available to cut disk I/O for RVC."""
    for p in ("/dev/shm", os.environ.get("XDG_RUNTIME_DIR")):
        if not p:
            continue
        if os.path.isdir(p) and os.access(p, os.W_OK | os.X_OK):
            return p
    # On Windows (and other systems) fall back to a writable temp dir.
    try:
        return tempfile.gettempdir()
    except OSError:
        return None


def is_rvc_stack_available() -> bool:
    global _RVC_STACK_IMPORT_ERROR
    try:
        from rvc_python.infer import RVCInference  # noqa: F401, PLC0415
    except Exception as e:
        _RVC_STACK_IMPORT_ERROR = f"{type(e).__name__}: {e}"
        logger.warning("RVC stack import failed: %s", _RVC_STACK_IMPORT_ERROR)
        return False
    _RVC_STACK_IMPORT_ERROR = None
    return True


def rvc_stack_import_error() -> str | None:
    return _RVC_STACK_IMPORT_ERROR


def rvc_device_string(use_cuda: bool) -> str:
    return "cuda:0" if use_cuda else "cpu:0"


def _mp3_to_wav_bytes(mp3: bytes) -> bytes:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not mp3:
        raise OSError(
            "ffmpeg is required to convert TTS (MP3) to WAV for RVC. "
            "Install ffmpeg and ensure it is in PATH (Windows: ffmpeg.exe in PATH).",
        )
    try:
        proc = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-i",
                "pipe:0",
                "-f",
                "wav",
                "-c:a",
                "pcm_s16le",
                "pipe:1",
            ],
            input=mp3,
            capture_output=True,
            timeout=60,
            check=False,
        )
    except OSError as e:
        raise OSError(f"ffmpeg failed: {e}") from e
    if proc.returncode != 0 or not proc.stdout:
        err = (proc.stderr or b"")[:500].decode(errors="replace")
        raise OSError(f"MP3 to WAV for RVC failed: {err}")
    return proc.stdout


def audio_bytes_to_wav_for_rvc(data: bytes) -> bytes:
    """RVC ingests WAV; Google TTS returns MP3, Piper returns WAV."""
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return data
    return _mp3_to_wav_bytes(data)


@dataclass(frozen=True)
class RvcChainRebuildParams:
    """Snapshot of RVC settings for :func:`rvc_rebuild_chain` (thread-safe, no Qt)."""

    enabled: bool
    model_pth: str
    index_path: str
    use_cuda: bool


class RvcWavChain:
    """RVC runs in a ``spawn`` child process; stopping it returns RAM to the OS."""

    def __init__(self, model_pth: Path, index_path: Path | None, *, use_cuda: bool) -> None:
        from stream_cheremsha.tts import rvc_worker_entry  # noqa: PLC0415

        p = model_pth.expanduser().resolve()
        if not p.is_file():
            raise ValueError(f"RVC model not found: {p}")
        if index_path is not None:
            ip = index_path.expanduser().resolve()
            if not ip.is_file():
                raise ValueError(f"RVC index not found: {ip}")
        else:
            ip = None
        self._pth: Final[Path] = p
        self._index: Final[Path | None] = ip
        self._use_cuda = bool(use_cuda)
        self._device = rvc_device_string(use_cuda)

        mp_ctx = multiprocessing.get_context("spawn")
        parent_conn, child_conn = mp_ctx.Pipe(duplex=True)
        self._proc: multiprocessing.Process | None = mp_ctx.Process(
            target=rvc_worker_entry.rvc_worker_main,
            args=(child_conn,),
            name="cheremsha-rvc",
            daemon=False,
        )
        self._conn: Connection | None = parent_conn
        try:
            proc = self._proc
            assert proc is not None
            proc.start()
            models_dir = str(p.parent)
            idx_str = str(ip) if ip is not None else ""
            tmp_base = _rvc_work_dir() or ""
            conn = self._conn
            assert conn is not None
            conn.send(
                ("load", models_dir, str(p), idx_str, self._use_cuda, tmp_base),
            )
            if not conn.poll(_RVC_LOAD_TIMEOUT_SEC):
                raise TimeoutError("RVC worker load timed out")
            resp = conn.recv()
            if not isinstance(resp, tuple) or not resp:
                raise RuntimeError("RVC worker: invalid load response")
            if resp[0] == "err":
                raise RuntimeError(resp[1] if len(resp) > 1 else "RVC worker load failed")
            if resp[0] != "ok":
                raise RuntimeError(f"RVC worker load: unexpected {resp!r}")
        except BaseException:
            self._shutdown_worker_norelease()
            raise

        logger.info(
            "RVC model in worker process (spawn): %s (device=%s)",
            p,
            self._device,
        )

    def _shutdown_worker_norelease(self) -> None:
        conn, proc = self._conn, self._proc
        self._conn, self._proc = None, None
        if conn is not None and not conn.closed:
            try:
                conn.send(("shutdown",))
            except (BrokenPipeError, EOFError, OSError):
                pass
            try:
                conn.close()
            except OSError:
                pass
        if proc is not None:
            proc.join(timeout=5)
            if proc.is_alive():
                proc.kill()
                proc.join(timeout=10)

    @property
    def model_pth(self) -> Path:
        return self._pth

    @property
    def index_path(self) -> Path | None:
        return self._index

    def process_wav_bytes(self, wav_bytes: bytes) -> bytes:
        if not wav_bytes or wav_bytes[:4] != b"RIFF":
            raise ValueError("RVC: expected RIFF/WAV input")
        conn = self._conn
        if conn is None or conn.closed:
            raise RuntimeError("RVC worker is not running")
        conn.send(("infer", wav_bytes))
        if not conn.poll(_RVC_INFER_TIMEOUT_SEC):
            raise TimeoutError("RVC worker infer timed out")
        resp = conn.recv()
        if not isinstance(resp, tuple) or not resp:
            raise RuntimeError("RVC worker: empty infer response")
        if resp[0] == "err":
            raise RuntimeError(str(resp[1]) if len(resp) > 1 else "RVC infer failed")
        if resp[0] != "ok" or len(resp) < 2:
            raise RuntimeError(f"RVC worker: bad infer response {resp!r}")
        out = resp[1]
        if not isinstance(out, (bytes, bytearray)):
            raise TypeError("RVC worker: expected bytes output")
        return bytes(out)

    def close(self) -> None:
        """Terminate the worker; parent RSS drops because torch/fairseq lived only in the child."""
        self._shutdown_worker_norelease()
        release_rvc_torch_memory()

    def __del__(self) -> None:
        if self._proc is None and self._conn is None:
            return
        try:
            self._shutdown_worker_norelease()
        except (OSError, RuntimeError, TypeError, ValueError):
            self._conn, self._proc = None, None


def rvc_rebuild_chain(
    prev: RvcWavChain | None,
    params: RvcChainRebuildParams,
) -> tuple[RvcWavChain | None, BaseException | None]:
    """Close *prev* and build a new chain from *params* when enabled.

    Safe to call from a worker thread (no QSettings). Return value ``(None, None)``
    means RVC is off or left unconfigured the same way as a synchronous UI rebuild
    (missing stack, missing model file). ``(None, exc)`` means load/ctor failed.
    """
    if prev is not None:
        prev.close()
    if not params.enabled:
        if prev is None:
            release_rvc_torch_memory()
        return None, None
    if not is_rvc_stack_available():
        return None, None
    pth = params.model_pth.strip()
    if not pth or not Path(pth).expanduser().is_file():
        return None, None
    idx_s = params.index_path.strip()
    idx: Path | None = None
    if idx_s:
        ip = Path(idx_s).expanduser()
        if ip.is_file():
            idx = ip
    try:
        chain = RvcWavChain(
            Path(pth).expanduser().resolve(),
            idx,
            use_cuda=params.use_cuda,
        )
    except (ImportError, OSError, ValueError, RuntimeError, TimeoutError) as e:
        logger.warning("RVC chain: %s", e)
        return None, e
    return chain, None


@dataclass
class RvcRuntime:
    """Mutable RVC handle for :class:`StreamCoordinator` and settings rebuilds."""

    chain: RvcWavChain | None = None
    queue: asyncio.PriorityQueue[tuple[int, int, bytes, asyncio.Future[bytes]]] | None = None
    dispatcher: asyncio.Task[None] | None = None
    in_flight: bool = False
    max_pending: int = 24


_RVC_SEQ = count(1)


def _rvc_runtime_ensure_queue(runtime: RvcRuntime) -> asyncio.PriorityQueue[
    tuple[int, int, bytes, asyncio.Future[bytes]]
]:
    q = runtime.queue
    if q is None or q.maxsize != runtime.max_pending:
        runtime.queue = asyncio.PriorityQueue(maxsize=runtime.max_pending)
        q = runtime.queue
    assert q is not None
    return q


async def _rvc_dispatch_loop(runtime: RvcRuntime) -> None:
    q = _rvc_runtime_ensure_queue(runtime)
    while True:
        prio, _seq, audio, fut = await q.get()
        try:
            if fut.cancelled():
                continue
            chain = runtime.chain
            if chain is None:
                fut.set_exception(RuntimeError("RVC is not running"))
                continue
            runtime.in_flight = True

            def _work() -> bytes:
                w = audio_bytes_to_wav_for_rvc(audio)
                return chain.process_wav_bytes(w)

            out = await asyncio.to_thread(_work)
            fut.set_result(out)
        except Exception as e:
            if not fut.cancelled():
                fut.set_exception(e)
        finally:
            runtime.in_flight = False
            q.task_done()


def rvc_runtime_queue_size(runtime: RvcRuntime) -> int:
    """Queued + currently processing (best-effort)."""
    q = runtime.queue
    queued = q.qsize() if q is not None else 0
    return queued + (1 if runtime.in_flight else 0)


def rvc_runtime_cancel_pending(runtime: RvcRuntime, reason: BaseException | None = None) -> int:
    """Cancel/finish all queued requests so callers don't hang."""
    q = runtime.queue
    if q is None:
        return 0
    n = 0
    while True:
        try:
            _prio, _seq, _audio, fut = q.get_nowait()
        except asyncio.QueueEmpty:
            break
        try:
            if not fut.done():
                if reason is None:
                    fut.cancel()
                else:
                    fut.set_exception(reason)
            n += 1
        finally:
            q.task_done()
    return n


async def rvc_runtime_stop_dispatcher(runtime: RvcRuntime) -> None:
    t = runtime.dispatcher
    if t is None:
        return
    runtime.dispatcher = None
    t.cancel()
    await asyncio.gather(t, return_exceptions=True)


def rvc_runtime_start_dispatcher(runtime: RvcRuntime) -> None:
    """Ensure a single RVC dispatcher task exists for this runtime."""
    if runtime.dispatcher is not None and not runtime.dispatcher.done():
        return
    runtime.dispatcher = asyncio.create_task(_rvc_dispatch_loop(runtime), name="cheremsha-rvc-queue")


async def apply_rvc_if_active(runtime: RvcRuntime, audio: bytes, *, priority: int = 10) -> bytes:
    """RVC post-process with a priority queue to avoid flooding the worker.

    Lower ``priority`` number = higher priority. When the queue is full, returns raw audio.
    """
    if runtime.chain is None or not audio:
        return audio
    rvc_runtime_start_dispatcher(runtime)
    q = _rvc_runtime_ensure_queue(runtime)
    loop = asyncio.get_running_loop()
    fut: asyncio.Future[bytes] = loop.create_future()
    seq = next(_RVC_SEQ)
    try:
        q.put_nowait((int(priority), int(seq), audio, fut))
    except asyncio.QueueFull:
        return audio
    return await fut
