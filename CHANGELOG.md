# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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

[0.2.0]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.1.8...v0.2.0
[0.1.8]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.1.7...v0.1.8
[0.1.3]: https://github.com/olexanderboychuk/stream-cheremsha/compare/v0.1.2...v0.1.3
