# Cheremsha — Ukrainian Streamer Assistant for Twitch, YouTube & TikTok

**Cheremsha** is a free, open-source desktop application for Ukrainian-speaking streamers. It aggregates live chat from **Twitch**, **YouTube**, and **TikTok** in real time, reads messages aloud using **Ukrainian Text-to-Speech (TTS)**, manages a music queue via a **Telegram bot**, displays beautiful **OBS browser source overlays**, integrates with **OBS WebSocket**, and handles **donations** from Donatik and Donatello — all in one app.

> **Keywords:** Ukrainian TTS streamer tool · Twitch Ukrainian TTS · YouTube chat reader · TikTok live chat · OBS overlay Ukrainian · donation alert Ukraine · music queue Telegram bot · multi-platform streamer assistant · stream helper Ukrainian · Черемша стрімер

---

## Why Cheremsha?

Most streamer tools are English-only and spread across many separate apps. Cheremsha solves that for **Ukrainian streamers** by combining everything in a single Qt-based desktop app:

- Unified chat from Twitch + YouTube + TikTok
- High-quality **Ukrainian TTS** that reads chat messages and donation alerts aloud
- Music request system via a **Telegram bot** with an audio queue
- Live **OBS overlays** (Browser Source) for chat, music, activity, and viewer count
- **OBS Studio WebSocket** remote control (scene switch, source visibility)
- Donation tracking from **Donatik** and **Donatello**
- Playback to any output device (perfect for **OBS virtual cable**)
- Runs on **Windows** and **Linux**

---

## Features

### Multi-Platform Live Chat Aggregation
- **Twitch** — connects via twitchio IRC WebSocket with device-code OAuth; auto-reconnects on drops
- **YouTube Live** — uses YouTube Data API v3 with OAuth2; auto-discovers active broadcasts
- **TikTok Live** — connects via TikTokLive library; just enter a username

### Ukrainian Text-to-Speech (TTS)
- Multiple TTS engines: **Edge TTS** (Microsoft, high quality) and Google Translate TTS
- Audio normalization and gain via **ffmpeg**
- Plays to any system audio output device — compatible with OBS virtual audio cables
- Bounded queues prevent message pile-up during busy streams

### Music Player & Queue
- Downloads and plays music from YouTube via **yt-dlp**
- **Telegram bot** (`python-telegram-bot`) lets viewers request songs directly in chat
- Queue management: skip, clear, view now-playing
- `ffmpeg` used for normalization and smooth playback

### OBS Browser Source Overlays
Local overlay server on `http://127.0.0.1:17171` — add these as OBS Browser Sources:

| Overlay | URL |
|---------|-----|
| Chat overlay | `http://127.0.0.1:17171/overlay/chat?instance=main` |
| Music now-playing | `http://127.0.0.1:17171/overlay/music?instance=main` |
| Activity feed | `http://127.0.0.1:17171/overlay/activity?instance=main` |
| Online / viewer count | `http://127.0.0.1:17171/overlay/online?instance=main` |
| Actions / alerts | `http://127.0.0.1:17171/overlay/actions?instance=main` |

OBS Docks (custom browser panels inside OBS):

| Dock | URL |
|------|-----|
| Multi-chat | `http://127.0.0.1:17171/dock/multichat` |
| Activity | `http://127.0.0.1:17171/dock/activity` |
| Online | `http://127.0.0.1:17171/dock/online` |

Healthcheck: `http://127.0.0.1:17171/health`

### OBS Studio WebSocket Integration
- Connects to **OBS WebSocket v5** (via `obsws-python`)
- Remote control: scene switching, source visibility toggle
- Default: `127.0.0.1:4455`; password stored securely in OS keyring

### Donation Alerts (Donatik & Donatello)
- Polls **Donatik** and **Donatello** donation APIs
- Reads donation amounts and messages aloud via Ukrainian TTS
- Tokens stored locally in the OS keyring (never sent anywhere)

### Secure Credential Storage
All secrets live in the **OS keyring** (Windows Credential Manager / Secret Service / KWallet) — never in plain-text files:

- Twitch: access token, Client ID, Client secret, channel name
- YouTube: OAuth client JSON + token
- TikTok: username
- Donatik / Donatello: API tokens
- OBS WebSocket: password
- Telegram: bot token

ENV override available: `STREAM_CHEREMSHA_TWITCH_CLIENT_ID`

---

## Requirements

- **Python 3.11** (`>=3.11,<3.12`)
- **ffmpeg** in `PATH` (for TTS normalization and music via yt-dlp)
- On Linux: system backends/codecs for QtMultimedia (distro-dependent)

---

## Installation

### Windows (PowerShell)

```powershell
cd D:\dev\stream-cheremsha
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### Linux / macOS (bash)

```bash
cd /path/to/stream-cheremsha
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

> If `keyring` reports **No recommended backend**, install [`keyrings.alt`](https://pypi.org/project/keyrings.alt/) or use your OS integration (Secret Service / KWallet).

---

## Running

```bash
cheremsha
# or
python -m stream_cheremsha
```

---

## Platform Setup Guides

### Twitch
1. Click **Sign in with Twitch** — device-code OAuth flow opens in the browser
2. Tokens are saved to the OS keyring automatically
3. The channel name can be inferred from the login
4. Alternative: paste an access token manually

### YouTube Live
1. In [Google Cloud Console](https://console.cloud.google.com/), enable **YouTube Data API v3**
2. Create a **Desktop** OAuth client and download the JSON (`"installed"` block)
3. In the app: **Sign in with Google** — first run asks for the JSON file, then uses keyring
4. Optional: set `GOOGLE_OAUTH_CLIENT_JSON` (full JSON string) to skip the file picker
5. **Start YouTube**: leave the field empty to auto-discover active broadcasts, or paste a video URL/ID

### TikTok Live
Enter a username (with or without `@`) — the app connects via `TikTokLive` and forwards comments and events into the pipeline.

### Telegram Bot (Music Requests)
1. Create a bot via [@BotFather](https://t.me/BotFather) and copy the token
2. Paste the token in the app (saved to keyring)
3. Viewers can send `/play <song name or YouTube URL>` to request music

Optional **TikTok Live lyrics screening** (Settings → Telegram): Genius + **Groq** ([GroqCloud](https://console.groq.com/)). The app uses OpenAI-compatible `POST /openai/v1/chat/completions`. Default model is **`llama-3.1-8b-instant`**. Override with **`STREAM_CHEREMSHA_GROQ_MODEL`** (see Groq’s model list).

### OBS WebSocket
1. In OBS: **Tools → WebSocket Server Settings** → enable, set port `4455` and a password
2. Enter the password in the app (saved to keyring)
3. Control scenes and sources directly from Cheremsha

---

## Development

```bash
ruff check src tests
pytest
```

### Memory Profiling

```bash
pip install -e ".[profile]"
# Optional plot support:
pip install -e ".[profile-plot]"

python -m stream_cheremsha.profile_memory
```

Runtime metrics (periodic RSS + queue sizes in logs):

```powershell
$env:CHEREMSHA_METRICS="1"
$env:CHEREMSHA_METRICS_SEC="5"
python -m stream_cheremsha.profile_memory
```

---

## Binary Build (Nuitka — Windows Standalone .exe)

```bash
pip install -e ".[build]"
cheremsha-build
```

Artifacts output to `dist/nuitka/`.

Additional flags:

| Flag | Description |
|------|-------------|
| `--onefile` | Single `.exe` (slower startup) |
| `--debug` | Slower build, more diagnostics |
| `--console` | Windows: show console window |

---

## Tech Stack

| Component | Library |
|-----------|---------|
| Desktop UI | PySide6 (Qt 6) + PySide6-Frameless-Window |
| Twitch chat | twitchio 2.x (IRC WebSocket) |
| YouTube API | google-api-python-client + google-auth-oauthlib |
| TikTok Live | TikTokLive |
| TTS | edge-tts (Microsoft Edge) + Google Translate TTS |
| Music download | yt-dlp |
| Telegram bot | python-telegram-bot |
| OBS control | obsws-python (WebSocket v5) |
| Overlay server | aiohttp |
| HTTP client | httpx |
| Async Qt bridge | qasync |
| Credentials | keyring |
| Audio processing | ffmpeg |

---

## Frequently Asked Questions

**Q: Does Cheremsha support Ukrainian language TTS?**  
Yes. Ukrainian TTS is the primary language. Edge TTS provides high-quality Ukrainian voices.

**Q: Can I use Cheremsha with OBS Studio?**  
Absolutely. Browser source overlays, OBS Docks, and OBS WebSocket v5 remote control are all built in.

**Q: Does it work with virtual audio cables?**  
Yes. You can select any system audio output device — perfect for routing TTS and music through a virtual cable into OBS.

**Q: Is it free?**  
Yes, Cheremsha is free and open-source.

**Q: What platforms does the chat aggregation support?**  
Twitch, YouTube Live, and TikTok Live simultaneously.

**Q: How are my API tokens stored?**  
All credentials are stored in your OS keyring (Windows Credential Manager on Windows, Secret Service on Linux). Nothing is stored in plain text.

---

## License

See [LICENSE](LICENSE) for details.

---

*Cheremsha — стрімерський асистент для україномовних стрімерів: Twitch, YouTube, TikTok, TTS, OBS, донати, музика.*
