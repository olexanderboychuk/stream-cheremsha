# stream-cheremsha

MVP desktop tool: **Twitch** and **YouTube Live** chat → bounded queues → **Ukrainian** Google Translate–style TTS → **Qt** audio on a chosen output device (for OBS / virtual cables).

## Requirements

- Python **3.11** (the project is pinned to the 3.11 line for compatibility, including optional RVC).
- Fedora/Linux: Qt Multimedia backends (e.g. GStreamer plugins for MP3) as provided by your distro’s PySide6 packages.
- **Optional `[rvc]` (Linux):** `pyworld` has no manylinux wheel on PyPI, so `pip` **builds it from source** and you need a compiler plus CPython headers. On Fedora, install before `pip install -e ".[rvc]"` for example:  
  `sudo dnf install python3.11-devel gcc-c++`  
  (Debian/Ubuntu: `python3.11-dev` and `g++`.) If you see `Python.h: No such file or directory`, the devel package is missing.

## Virtual environment

```bash
cd /path/to/stream-cheremsha
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

If `keyring` reports **No recommended backend** (common in minimal containers), install a backend such as [`keyrings.alt`](https://pypi.org/project/keyrings.alt/) or use your desktop’s Secret Service / KWallet integration.

### Optional: RVC (voice conversion)

Install **devel** headers first on Linux (see **Requirements** above) so `pyworld` can compile.

The `[rvc]` extra uses **[fairseq-fixed](https://pypi.org/project/fairseq-fixed/)** (same `import fairseq` as the original) because **fairseq 0.12.2** from PyPI **crashes on Python 3.11** (`dataclasses` / mutable defaults). If you previously installed the old `fairseq` package, remove it first: `pip uninstall -y fairseq`.

`rvc-python` on PyPI still conflicts with this app’s `numpy` pins, so it is installed **with `--no-deps`** after the rest. Install the project in editable mode so the helper script exists (e.g. `pip install -e ".[dev]"`), then:

```bash
cheremsha-bootstrap-rvc
# or: python -m stream_cheremsha.bootstrap_rvc
```

**Manual:** `pip install -e ".[rvc]"` then `cheremsha-install-rvc` (or `python -m stream_cheremsha.install_rvc`).

For **CUDA** PyTorch, use the [PyTorch](https://pytorch.org/get-started/locally/) wheels first, then the commands above.

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
4. **Start YouTube** with the field **empty** to auto-detect every **active** live broadcast on the signed-in channel (via `liveBroadcasts.list`, with a `search`+`videos` fallback), or paste one **live** / VOD URL (or 11-character video ID) to pin a single stream. If nothing is live yet, the app **re-checks about every 15 seconds** until a live chat exists or you press Stop. Multiple simultaneous lives are polled in parallel (higher API quota use). Uses `liveChatMessages.list` with the API’s poll interval — see [YouTube Data API](https://developers.google.com/youtube/v3/getting-started).

## TTS disclaimer

Playback uses an **undocumented** Google Translate TTS endpoint. It may break or rate-limit; the code isolates TTS behind a small interface so you can swap engines later.

## Development

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

- Linux audio: the build includes Qt plugins for **QML + QtMultimedia**. If your system lacks codecs/backends
  (e.g. GStreamer plugins for MP3 on Fedora), install them via your distro packages.
- **Windows**: install **ffmpeg** and ensure `ffmpeg.exe` is in `PATH` for the built app (Google TTS → WAV for RVC).
- **RVC**: build in an environment where you already ran `cheremsha-bootstrap-rvc` (so `rvc_python` is installed);
  the build script force-includes the RVC stack into the standalone dist.
- **Nuitka version**: pinned to `<4.0` because 4.x is known to crash on some dependency graphs (e.g. librosa).
- **PyTorch/RVC in standalone**: the build uses `--python-flag=isolated` to avoid importing external site-packages
  at runtime (fixes duplicate torch extension loads like `RpcBackendOptions already defined`).

Tips:

- Use `--debug` only when diagnosing build/runtime issues (it is **much slower**).
- `--onefile` is also slower to build and slower to start; prefer standalone dir for iteration.
