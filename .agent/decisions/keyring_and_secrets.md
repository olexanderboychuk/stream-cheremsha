# Architectural Decision: Keyring Storage & Secret Handling

## Context & Problem
Streaming assistants interact with external APIs (Twitch OAuth, YouTube API keys, TikTok credentials, Telegram Bot tokens, Donatello API tokens). Storing credentials in plain text files, environment files, or SQLite risks accidental leaks during streaming or commits.

## Decision & Invariant Architecture
1. **OS Keyring as Single Source of Truth**:
   - All sensitive secrets (passwords, tokens, API keys) MUST be retrieved from and saved to the OS keyring using `src/stream_cheremsha/config/keyring_store.py`.
   - Supported backends: Windows Credential Manager, Linux Secret Service / KWallet, macOS Keychain.
2. **Never in Plain Text**:
   - Secrets MUST NEVER be written to `QSettings` (`ini`/registry), SQLite tables, `.env` files, or log outputs.
   - When logging configuration or API requests, sensitive fields must be redacted.
3. **Lazy Keyring Retrieval**:
   - Keyring access can block or trigger OS prompt dialogs. Therefore, keyring retrieval must be lazy and cached in memory for the duration of the session.
   - Never query the keyring repeatedly in hot loops or UI paint events.
4. **Graceful Fallback**:
   - If the OS keyring is unavailable (e.g. headless Linux or CI container), `keyring_store.py` provides controlled fallback handling. Code must gracefully handle `None` / empty values without crashing.

## What Must Never Happen
- DO NOT save API keys, tokens, or passwords to `QSettings` under any circumstance.
- DO NOT print raw tokens or authorization headers in logger output.
- DO NOT read from keyring during startup constructor phases before the UI or splash is active.
