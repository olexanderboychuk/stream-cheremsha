# stream-cheremsha

MVP desktop tool: **Twitch** and **YouTube Live** chat → bounded queues → **Ukrainian** Google Translate–style TTS → **Qt** audio on a chosen output device (for OBS / virtual cables).

## Requirements

- Python **3.11** (the project is pinned to the 3.11 line for compatibility).
- Fedora/Linux: Qt Multimedia backends (e.g. GStreamer plugins for MP3) as provided by your distro’s PySide6 packages.

## Virtual environment

```bash
cd /path/to/stream-cheremsha
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

If `keyring` reports **No recommended backend** (common in minimal containers), install a backend such as [`keyrings.alt`](https://pypi.org/project/keyrings.alt/) or use your desktop’s Secret Service / KWallet integration.

Run:

```bash
cheremsha
# or
python -m stream_cheremsha
```

## Twitch (twitchio 2.x IRC)

The app pins **`twitchio>=2.10,<3`** so chat stays on classic **IRC WebSocket** (simpler MVP than twitchio 3’s EventSub-only model).

Register a Twitch Developer application and note the **Client ID** (and **Client secret** if your app is confidential—helps token refresh).

- **Sign in with Twitch (browser)** runs Twitch’s **device-code OAuth** (opens the browser; approve access on twitch.tv). Tokens are stored in the OS **keyring**. The **channel** field is prefilled from the validated token login when possible.
- **Manual token** remains optional if you prefer to paste an access token yourself. **Save Twitch app to keyring** persists Client ID, optional secret, channel, and optional manual token.
- **Enable Twitch** opens **IRC** to that channel’s chat; the broadcast does **not** need to be live. If the connection drops or fails to open, the client **retries every 15 seconds** until you press Stop or it stays connected.

## YouTube

1. In [Google Cloud Console](https://console.cloud.google.com/), enable **YouTube Data API v3** and create an OAuth client of type **Desktop**; download the JSON (it contains an `"installed"` block).
2. In the app: **Sign in with Google (browser)** — the **first** time only, a file picker asks for that JSON; it is stored in the OS keyring. Later, login is just the button and the browser (same idea as many desktop apps that ship or cache OAuth client metadata).
3. Optional: set env **`GOOGLE_OAUTH_CLIENT_JSON`** to the full JSON string to skip the file picker (e.g. CI or advanced setups).
4. **Start YouTube** with the field **empty** to auto-detect every **active** live broadcast on the signed-in channel (via `liveBroadcasts.list`, with a `search`+`videos` fallback), or paste one **live** / VOD URL (or 11-character video ID) to pin a single stream. If nothing is live yet, the app **re-checks about every 45 seconds** until a live chat exists or you press Stop. Several simultaneous lives **share one poll cadence** (round-robin) so quota use stays closer to a single chat. `liveChatMessages.list` uses `maxResults=2000`, a **minimum 5 s** gap between calls, and the API’s `pollingIntervalMillis` when higher — see [YouTube Data API](https://developers.google.com/youtube/v3/getting-started).

## TTS disclaimer

Playback uses an **undocumented** Google Translate TTS endpoint. It may break or rate-limit; the code isolates TTS behind a small interface so you can swap engines later.

## Development

### Memory profiling (RSS / leak hunting)

Install the optional profiling dependencies:

```bash
pip install -e ".[profile]"
# For mprof plot:
pip install -e ".[profile-plot]"
```

Run the app under `memory_profiler`/`mprof`:

```bash
# Line-by-line RSS output in console (shows when profiled functions run)
python -m memory_profiler scripts/profile_memory_run.py

# Timeline plot-friendly run (writes an .dat file)
mprof run python scripts/profile_memory_run.py
mprof plot
```

Lightweight long-run metrics (good for 2–12h streams):

```bash
# Periodic RSS + queue sizes in logs (no line-by-line spam)
set CHEREMSHA_METRICS=1
set CHEREMSHA_METRICS_SEC=5
python scripts/profile_memory_run.py
```

What is profiled by default:
- `StreamCheremshaQmlApi.refresh()` (QML “refreshCounter” invalidation trigger)
- `QtAudioSink.play_mp3()` (ffmpeg + temp file + QMediaPlayer path)
- TikTok analytics feed ingestion: `TikTokAnalyticsFeedModel.prepend()`, `TikTokAnalyticsApi._apply_*()`
- Donations live polling: `DonationsQmlApi._async_*poll*()`
- Overlays pubsub: `OverlayPubSub.publish()/subscribe()`
- Pipeline: `StreamCoordinator.enqueue_chat()`, `StreamCoordinator._tts_loop()`

Tips for interpretation:
- If RSS grows steadily while **idle** (no incoming events), suspect a leak (tasks/timers/queues, QML image cache, signals).
- If RSS grows during bursts and then stabilizes, it may be a cache (Qt Quick image/texture cache, Python module caches).
- For GPU VRAM spikes, `memory_profiler` won’t see VRAM — correlate with Task Manager GPU memory and reduce QML invalidations / image churn.

```bash
source .venv/bin/activate
ruff check src tests
pytest
```

## Binary builds (Nuitka)

Install build dependencies:

```bash
pip install -e ".[build]"
```

Build a **standalone** binary:

```bash
cheremsha-build
```

Artifacts will be placed under `dist/nuitka/`.

Notes:

- **CUDA build (NVIDIA)**: the Nuitka build will bundle whichever `torch` you have installed in the build venv.
  For a CUDA-enabled build, install CUDA wheels **before** running `cheremsha-build` (example: CUDA 12.8):

  ```bash
  pip uninstall -y torch torchaudio
  pip install --index-url https://download.pytorch.org/whl/cu128 torch torchaudio
  ```

- Linux audio: the build includes Qt plugins for **QML + QtMultimedia**. If your system lacks codecs/backends
  (e.g. GStreamer plugins for MP3 on Fedora), install them via your distro packages.
- **Windows**: install **ffmpeg** and ensure `ffmpeg.exe` is in `PATH` for the built app.
- **Nuitka version**: pinned to `<4.0` because 4.x is known to crash on some dependency graphs (e.g. librosa).
- **PyTorch in standalone**: the build uses `--python-flag=isolated` to avoid importing external site-packages
  at runtime (fixes duplicate torch extension loads like `RpcBackendOptions already defined`).

Tips:

- Use `--debug` only when diagnosing build/runtime issues (it is **much slower**).
- `--onefile` is also slower to build and slower to start; prefer standalone dir for iteration.
