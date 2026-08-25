# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.13.0] — 2026-08-25

### Added

- **Kick platform** support:
  - Realtime chat via Kick's Pusher WebSocket (outbound — no public URL or tunnel required)
  - Official REST + OAuth 2.1 (PKCE) sign-in with a local callback server; tokens stored in the OS keyring
  - Kick Connections card, analytics panel, footer/status routing, per-platform TTS, and auto-start
  - Viewer counts and message sending via the official Kick API
  - Action triggers for Kick chat, follows, subscriptions, gift subscriptions, and KICKS gifts
  - Kick presence in chat/activity/online docks and the Online overlay

## [0.12.0] — 2026-08-25

### Added

- **Community World** overlay (`/overlay/community_world`): a live Ukrainian-village that grows with chat — follows build houses, likes fill the well, shares build bridges, gifts unlock monuments and towers, and level-ups unlock the castle. Includes live quest board (4 quest slots), XP/levels, recognition feed, viewer passports with badges, all-time village elders (SQLite), and animated celebrations (confetti, new-building pop-ins). Configurable themes (pixel / fantasy / cyber / ukrainian), **compact vertical layout** for narrow widgets under the chat on vertical streams (the village stays as a live background scene), quiet mode, XP weights, quest targets, and display toggles in the Widgets editor.

## [0.11.2] — 2026-07-23

### Changed

- Release workflow: temporarily disable VirusTotal scan so publish no longer waits on that job.

## [0.11.1] — 2026-06-26

### Fixed

- VirusTotal CI upload: include API key headers on the file upload POST request.

## [0.11.0] — 2026-06-26

### Added

- **Stream Pet** overlay: interactive on-stream companion with evolution, presets, localized phrases, and session persistence.
- Big Picture **analytics** and **platform cards** panels (QML components).
- VirusTotal scanning of release artifacts in the GitHub Actions release workflow (`scripts/ci/virustotal_scan.py`).

### Changed

- Connections view refactored into reusable QML components (`ConnTheme`, `ConnPillButton`, `PlatformCardsPanel`, etc.).
- Widgets view expanded for Stream Pet configuration and overlay management.
- Top gifters and top likers overlays updated for consistency with the new overlay stack.

## [0.10.0] — 2026-06-16

### Changed

- Chat popout: replace Minimize with Close; independent font settings persisted in QSettings; own message view synced from history instead of sharing the main chat document.
- Chat popout: top-level window (no Qt parent) so Windows does not minimize it with the main window; closes when the main window exits.

## [0.9.0] — 2026-06-16

### Changed

- YouTube integration: explicit CA bundle for httplib2 in standalone (Nuitka) builds; invalidate and rebuild the Data API client after SSL/runtime errors.
- YouTube chat supervisor restarts after poll/fallback cycles instead of exiting (fixes UI toggle snapping off in Nuitka builds).
- Nuitka build: bundle `googleapiclient`, `httplib2`, `chat_downloader`, and related packages for YouTube.

## [0.8.0] — 2026-06-16

### Added

- **Points economy** for song requests: viewers earn balance from likes, shares, follows, watch time, and TikTok gifts; configurable costs and rates in a new Points settings dialog.
- **TikTok ↔ Telegram linking** via a one-time word code typed in live chat, with anti-abuse cooldowns for follow/share farming.
- SQLite persistence for points balances, ledger, and cross-stream cooldowns.
- TTS speech rate control in Audio settings (50–200%, 100% = normal). Applies natively for Edge voices and via ffmpeg `atempo` (pitch-preserving) for Google, persisted between runs.
- Tests for points domain, SQLite store, settings dialog, TikTok link challenge, TTS rate, and YouTube Data API runner.

### Changed

- TikTok chat source: engagement events feed the points ledger; gift coin totals stored for conversion.
- Telegram bot: points balance checks and TikTok link flow for song requests.
- YouTube chat source refactored for clearer Data API polling.

### Removed

- Bundled RVC voice model assets (Stalker bandit `.pth` / index files).

## [0.7.3] — 2026-06-15

### Fixed

- Linux AppImage build: set `APPIMAGE_EXTRACT_AND_RUN=1` when invoking appimagetool.
- Linux release CI: add `libfuse2` so AppImages run on systems without FUSE3.

## [0.7.2] — 2026-06-14

### Fixed

- Linux AppImage build: correct path when copying `cheremsha.desktop` into the AppDir.

### Added

- `scripts/ci/cheremsha.desktop` for AppImage desktop integration (name, icon, categories).

## [0.7.1] — 2026-06-14

### Added

- Normalized keystroke and mouse button tags in actions simulation for consistent recognition across input backends.

### Changed

- CI and release workflows: disable Microsoft and Azure apt repositories before installing PySide6 system libraries on Linux.

### Removed

- Audio backend test suite (normalization and settings tests).

## [0.7.0] — 2026-06-13

### Added

- YouTube Super Chat, Super Sticker, and Member events for actions and donations UI.
- Cloudflare tunnel provider for overlay URLs (embedded credentials, cloudflared install prompts).
- Linux AppImage release job in GitHub Actions.
- RVC voice model assets (Stalker bandit) bundled for release builds.
- Tests for Cloudflare tunnel, tunnel secrets, embedded build config, and YouTube quota fallback.

### Changed

- Actions engine and QML views extended for new YouTube event types and placeholders.
- Overlay tunnel API and Connections UI: Cloudflare alongside ngrok.
- Release workflow: AppImage build, `latest.json` generation, NSIS version injection.
- README: Cloudflare tunnel setup instructions.

## [0.6.0] — 2026-06-12

### Added

- qasync-safe asyncio helpers (`asyncio_qt.py`) to prevent task re-entry issues in the Qt event loop.
- Runtime diagnostics (`diagnostics/runtime.py`) for asyncio and thread failures, with optional heavy diagnostics.
- Overlay UI locale helper (`ui_locale.py`) for localized overlay strings.
- Tests for asyncio helpers, runtime diagnostics, and audio backend.

### Changed

- Battle Royale and King of Live overlays: localization support.
- Main window: asyncio/Qt integration and error-handling improvements.

## [0.5.0] — 2026-05-31

### Added

- **Battle Royale** TikTok overlay: event PvP by gifts (HP, crit hits, timer, fatality FX), manual/auto start from Widgets, hall of fame on KING overlay, VIP gold chat nick for winners.
- Overlay tunnel: ngrok integration for public overlay URLs (install, domain config, QML API).
- Twitch EventSub/Helix: profile picture handling for chat and overlay display.
- Battle Royale wins persistence (SQLite) and expanded TikTok gifts catalog support.

### Changed

- Dependencies: `pyngrok` for overlay tunnel support.
- Activity dock, YouTube discovery, TTS sanitization, and actions engine updates for Battle Royale flow.
- README: overlay URL and ngrok configuration instructions.

### Fixed

- Windows: suppress console window flash for `ffprobe` and `mpv` subprocesses during audio playback.

## [0.4.0] — 2026-05-15

### Added

- MusicBrainz integration to screen artists linked to Russia during song requests (Telegram / moderation flow).
- Actions: cross-platform keystroke simulation (`pynput`, Windows `interception-python`).
- TikTok chat source: stable user identification key for downstream logic.

### Changed

- Dependencies: `pynput`, `interception-python` for input simulation.
- Localization strings for song-filter / moderation messages.

### Fixed

- CI: validate Genius token before using `lyricsgenius`; module-level imports for reliable test setup.

## [0.3.0] — 2026-05-13

### Added

- TikTok Live: optional Genius.com lyrics screening before going live (ruleset, UI, Telegram notices).
- Dependencies: `lyricsgenius` for lyrics lookup.

### Changed

- YouTube/TikTok chat sources, OBS control, music player, and connections UI updates supporting the new flow.

## [0.2.0] — 2026-05-08

### Added

- GitHub Releases auto-update flow (manifest generation and update client/downloader).
- Pre-commit configuration.

### Changed

- Audio playback: Qt sink improvements and engine/playback hardening.

## [0.1.8] — 2026-05-07

### Added

- Ukrainian localization module (`l10n`) and UI localization improvements.
- YouTube download resolver based on `yt-dlp`.
- Music settings editor improvements.

### Changed

- Actions editor: improved Random MyInstants UA workflow, including word filters and UI layout.
- Actions engine: dispatcher updates and validation hardening.

### Fixed

- UI: avoid autosave focus loss while editing `skip_words`.
- TikTok gifts: small refactor for readability.

## [0.1.3] — 2026-05-07

### Added

- OpenAI-based moderation module and tests.
- TTS text sanitization pipeline and tests.
- `paths` helper and related coordinator, UI, and actions updates.

### Changed

- Release (Nuitka) CI: `cheremsha-build` runs with `--low-memory` and a single job for more reliable GitHub Actions builds.

### Other

- Comment and formatting consistency in several modules after merging PR #5.

[0.13.0]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.12.0...v0.13.0
[0.12.0]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.11.2...v0.12.0
[0.11.2]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.11.1...v0.11.2
[0.11.1]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.11.0...v0.11.1
[0.11.0]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.10.0...v0.11.0
[0.10.0]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.7.3...v0.8.0
[0.7.3]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.7.2...v0.7.3
[0.7.2]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.1.8...v0.2.0
[0.1.8]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.1.7...v0.1.8
[0.1.3]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.1.2...v0.1.3
