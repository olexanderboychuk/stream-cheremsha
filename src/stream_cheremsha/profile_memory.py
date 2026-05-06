from __future__ import annotations

import importlib
import logging
import os
import weakref


def _try_patch_targets() -> None:
    """
    Apply optional @profile wrappers when memory_profiler is present.

    We keep this module importable without memory-profiler installed.
    """
    try:
        mp = importlib.import_module("memory_profiler")
    except ModuleNotFoundError:
        return

    prof = getattr(mp, "profile", None)
    if prof is None:
        return

    # Patch a few hot paths. We wrap methods to get line-by-line RSS deltas when they run.
    try:
        from stream_cheremsha.ui.qml_api import StreamCheremshaQmlApi

        StreamCheremshaQmlApi.refresh = prof(StreamCheremshaQmlApi.refresh)  # type: ignore[method-assign]
    except (ImportError, AttributeError):
        pass

    try:
        from stream_cheremsha.audio.qt_sink import QtAudioSink

        QtAudioSink.play_mp3 = prof(QtAudioSink.play_mp3)  # type: ignore[method-assign]
    except (ImportError, AttributeError):
        pass

    # Lightweight runtime metrics (periodic RSS + queue sizes) for long streams.
    # Enable via:
    #   set CHEREMSHA_METRICS=1
    #   set CHEREMSHA_METRICS_SEC=5
    try:
        import psutil
        from PySide6.QtCore import QTimer

        from stream_cheremsha.ui.main_window import MainWindow

        orig_init = MainWindow.__init__
        win_ref: weakref.ReferenceType[MainWindow] | None = None

        def _patched_init(self: MainWindow) -> None:  # type: ignore[misc]
            nonlocal win_ref
            orig_init(self)
            win_ref = weakref.ref(self)
            if os.environ.get("CHEREMSHA_METRICS", "").strip() not in {
                "1",
                "true",
                "True",
                "yes",
                "YES",
            }:
                return
            try:
                sec = float(os.environ.get("CHEREMSHA_METRICS_SEC", "5").strip() or "5")
            except ValueError:
                sec = 5.0
            sec = max(0.5, min(60.0, sec))
            proc = psutil.Process(os.getpid())

            t = QTimer(self)
            t.setInterval(int(sec * 1000))

            def _tick() -> None:
                w = win_ref() if win_ref is not None else None
                if w is None:
                    return
                try:
                    rss_mb = proc.memory_info().rss / (1024 * 1024)
                except OSError:
                    rss_mb = -1.0
                try:
                    chat_q = int(getattr(w._coordinator.chat_in, "qsize")())  # noqa: SLF001
                    tts_q = int(getattr(w._coordinator.tts_jobs, "qsize")())  # noqa: SLF001
                except Exception:
                    chat_q, tts_q = -1, -1
                try:
                    pubsub = w._overlay_server.pubsub()  # noqa: SLF001
                    subs = len(getattr(pubsub, "_subs", []))
                except Exception:
                    subs = -1
                logging.getLogger("cheremsha.metrics").info(
                    "rss=%.1fMB chat_q=%s tts_q=%s overlay_subs=%s",
                    rss_mb,
                    chat_q,
                    tts_q,
                    subs,
                )

            t.timeout.connect(_tick)
            t.start()
            # One immediate sample to confirm it's running.
            _tick()

        MainWindow.__init__ = _patched_init  # type: ignore[method-assign]
    except Exception:
        # Metrics are best-effort; profiling should never fail to start because of them.
        pass

    # Stream/runtime targets: analytics feed churn, overlays pubsub fan-out, donation polling.
    try:
        from stream_cheremsha.ui.tiktok_analytics_api import (
            TikTokAnalyticsApi,
            TikTokAnalyticsFeedModel,
        )

        TikTokAnalyticsFeedModel.prepend = prof(TikTokAnalyticsFeedModel.prepend)  # type: ignore[method-assign]
        TikTokAnalyticsApi._apply_gift = prof(TikTokAnalyticsApi._apply_gift)  # type: ignore[method-assign]
        TikTokAnalyticsApi._apply_follow = prof(TikTokAnalyticsApi._apply_follow)  # type: ignore[method-assign]
        TikTokAnalyticsApi._apply_join = prof(TikTokAnalyticsApi._apply_join)  # type: ignore[method-assign]
        TikTokAnalyticsApi.resetSession = prof(TikTokAnalyticsApi.resetSession)  # type: ignore[method-assign]
    except (ImportError, AttributeError):
        pass

    try:
        from stream_cheremsha.overlays.pubsub import OverlayPubSub

        OverlayPubSub.subscribe = prof(OverlayPubSub.subscribe)  # type: ignore[method-assign]
        OverlayPubSub.unsubscribe = prof(OverlayPubSub.unsubscribe)  # type: ignore[method-assign]
        OverlayPubSub.publish = prof(OverlayPubSub.publish)  # type: ignore[method-assign]
    except (ImportError, AttributeError):
        pass

    try:
        from stream_cheremsha.ui.donations_qml_api import DonationsQmlApi

        DonationsQmlApi._async_poll_tick = prof(DonationsQmlApi._async_poll_tick)  # type: ignore[method-assign]
        DonationsQmlApi._async_donatik_poll = prof(DonationsQmlApi._async_donatik_poll)  # type: ignore[method-assign]
        DonationsQmlApi._async_donatello_poll = prof(DonationsQmlApi._async_donatello_poll)  # type: ignore[method-assign]
    except (ImportError, AttributeError):
        pass

    try:
        from stream_cheremsha.pipeline.coordinator import StreamCoordinator

        StreamCoordinator.enqueue_chat = prof(StreamCoordinator.enqueue_chat)  # type: ignore[method-assign]
        StreamCoordinator._tts_loop = prof(StreamCoordinator._tts_loop)  # type: ignore[method-assign]
    except (ImportError, AttributeError):
        pass


def main() -> None:
    """
    Entrypoint for memory profiling.

    Usage:
      python -m stream_cheremsha.profile_memory
      mprof run python -m stream_cheremsha.profile_memory

    Notes:
    - Set CHEREMSHA_PROFILE=0 to disable patching even if memory_profiler is installed.
    - Set CHEREMSHA_METRICS=1 to emit periodic RSS/queue metrics to logs.
    - Logging is INFO to keep mprof output readable.
    """
    logging.basicConfig(level=logging.INFO)
    if os.environ.get("CHEREMSHA_PROFILE", "1").strip() not in ("0", "false", "False", "no", "NO"):
        _try_patch_targets()

    from stream_cheremsha.app.main import main as app_main

    app_main()


if __name__ == "__main__":
    main()
