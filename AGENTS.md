# AGENTS.md

## PROJECT
Cheremsha is a Ukrainian streamer assistant that aggregates live chat from Twitch, YouTube, TikTok, and Kick into a unified interface with Ukrainian Text-to-Speech (TTS), music queue management via Telegram, OBS browser source overlays, and OBS WebSocket integration.

---

## AGENT STARTUP PROTOCOL
1. Read `AGENTS.md`.
2. Read `PROJECT_MAP.md`.
3. Identify the relevant subsystem based on the task.
4. Read ONLY the corresponding `.agent/modules/*.md` file for that subsystem.
5. Read a flow file (e.g., in `.agent/flows/`) only if the task involves an end-to-end runtime flow.
6. Inspect the actual implementation files identified in the context documents.
7. Modify the minimum required files.
8. Run the relevant tests found in `tests/`.
9. Do not perform unrelated exploration of other modules.

---

## CONTEXT LOADING RULE
- **DO NOT** recursively read the repository.
- **DO NOT** inspect unrelated modules.
- **DO NOT** read every file in a directory; use the "Canonical Locations" in module files.
- **DO NOT** inspect `generated/`, `build/`, `dist/`, or `.venv/` unless specifically required for debugging build issues.
- Use `PROJECT_MAP.md` to determine where to start.
- Load `.agent/modules/<module>.md` only when working inside that module.
- Load `.agent/flows/<flow>.md` only when the task involves that flow.

---

## IMPORTANT DIRECTORIES
- `src/stream_cheremsha/chat`: Chat source implementations (Twitch, YouTube, TikTok, Kick).
- `src/stream_cheremsha/overlays`: Overlay server logic and specific widget implementations.
- `src/stream_cheremsha/music`: Music player, queue management, and Telegram bot integration.
- `src/stream_cheremsha/pipeline`: TTS processing pipeline (chunking, filtering).
- `src/stream_cheremsha/actions`: Platform-specific automation actions.
- `src/stream_cheremsha/config`: Configuration, keyring storage, and secrets.

---

## EXCLUDED DIRECTORIES
- `node_modules/`
- `.venv/`
- `build/`
- `dist/`
- `.pytest_cache/`
- `.ruff_cache/`
- `__pycache__/`

---

## COMMANDS
- **Development**: `ruff check src tests`, `pytest`
- **Linting**: `ruff check .`
- **Formatting**: `ruff format .`
- **Type Checking**: (Not explicitly configured, but use `mypy` if available)
- **Build**: `pip install -e ".[build]" && cheremsha-build`
- **Database/Persistence**: Handled via `sqlite3` or `qsettings` depending on the module.

---

## ARCHITECTURAL RULES
- **Source of Truth**: The code is the source of truth. Documentation is a navigation index.
- **Keyring First**: All secrets must be stored in the OS keyring using `config/keyring_store.py`. Never hardcode or store in plain text files.
- **Asyncio Everywhere**: Most I/O (Chat, TTS, Overlays) is handled via `qasync` and `asyncio`.
- **Modular Isolation**: Modules should interact through defined interfaces; avoid direct cross-module imports where possible.

---

## HIGH-RISK AREAS
- **TTS Pipeline**: Changes to `pipeline/` can affect all audio output.
- **Overlay Server**: Errors here can crash the web server serving OBS sources.
- **Keyring Logic**: Incorrect handling of secrets can lead to data loss or security vulnerabilities.

---

## DOCUMENTATION NAVIGATION
- `PROJECT_MAP.md`: Repository navigation index (Where things are).
- `ARCHITECTURE.md`: High-level system design (How things work).
- `.agent/modules/`: Subsystem-specific context and change guides.
- `.agent/flows/`: Important end-to-end runtime flows.
- `.agent/decisions/`: Key architectural decisions.
