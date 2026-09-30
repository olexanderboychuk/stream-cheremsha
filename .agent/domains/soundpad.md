# Soundpad (tab 11)

Instant sounds for streaming: hotkey-triggered playback, categories, waveform cards, and a MyInstants **Library** (browse → preview → add).

## Key files

| Symbol | File | Responsibility |
|--------|------|----------------|
| `SoundpadStore` | `src/stream_cheremsha/soundpad/store.py` | QSettings-backed entries; `library_dir`; `resolve_library_path()` copies into `<AppData>/soundpad/sounds/` |
| `SoundpadAudioEngine` | `src/stream_cheremsha/soundpad/engine.py` | Playback modes (restart/overlap/replace/queue/hold), cooldowns, ducking; preview via `play_preview()` / `stop_preview()` (sink key prefix `soundpad-preview:`) |
| `GlobalHotkeyManager` + backends | `src/stream_cheremsha/soundpad/hotkeys.py` | pynput X11 backend; `FakeHotkeyBackend` for tests |
| `MyInstantsClient` | `src/stream_cheremsha/soundpad/myinstants.py` | Rate-limited (≥1.2 s between requests) MyInstants fetcher; bounded caches: index LRU ≤32 pages / TTL 600 s, MP3 disk cache ≤128 files & ≤256 MB with atomic writes |
| `ensure_x_authority` | `src/stream_cheremsha/x11_auth.py` | Self-heals stale-hostname `$XAUTHORITY` entries before pynput import (shared with actions keystroke simulation) |
| `SoundpadQmlApi` | `src/stream_cheremsha/ui/soundpad_qml_api.py` | QML bridge: grid CRUD + library slots (`openLibrary`, `loadLibraryPage`, `previewSound`, `stopPreview`, `addLibrarySound`) + l10n (`libraryStrings`, `tr()`, `set_locale()`) |
| `SoundpadView.qml` / `components/SoundpadLibraryPanel.qml` | `src/stream_cheremsha/qml/` | UI; library modal via `CheremshaModal` (`preferredWidth: 720`) |

## Invariants & decisions

- **Lazy everything**: the soundpad stack is built only on first tab open (`MainWindow._soundpad_api_lazy`, called from `_bind_qml_context_properties`); never in `_build_ui`.
- **curl_cffi stays a lazy import** inside `myinstants.py` (module `__getattr__`) — Chrome TLS impersonation to get past Cloudflare; must not appear in startup imports.
- **Library adds are copied into the store dir** (`resolve_library_path`) so bounded cache eviction can never break an added sound. The MP3 cache is disposable by design.
- **Locale**: app locale uk → MyInstants `ua` (fallback `en`), en → `en`. `l10n.tr()` raises `KeyError` on unknown keys — API slots catch and fall back to the key itself.
- **Preview** uses sink dedupe-key prefix `soundpad-preview:`; a cancelled preview must NOT emit `previewFinished`.
- QML collections are exposed as JSON strings (`soundsJson`, `libraryRowsJson`) — codebase convention, not QVariantList.
- **X auth self-heal**: pynput connects to X at *import* time and python-xlib matches the xauth cookie by exact hostname; some sessions ship `$XAUTHORITY` entries keyed by a stale host (Qt tolerates this, pynput does not). `x11_auth.ensure_x_authority()` must run before every pynput import — it copies the file to `~/.cache/cheremsha/xauth`, appends `<hostname>/unix:0` reusing an existing MIT-MAGIC-COOKIE-1 (source file never modified), and points XAUTHORITY at the copy. Called from hotkeys grab, actions keystroke simulation, and `tests/conftest.py`.

## Tests

`tests/test_soundpad_myinstants.py` (parsing/client/caches), `test_soundpad_engine.py` (playback/hold/preview), `test_soundpad_library_api.py` (l10n + library slots with FakeSession DI), `test_soundpad_nav_lazy.py` (static wiring checks), `test_soundpad_library_qml.py` (QML static + QQmlEngine compile check), `test_soundpad_hotkeys.py` (grab/release/debounce + xauth self-heal).
