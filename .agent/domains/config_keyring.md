# DOMAIN: Configuration, Secrets & Keyring

## Subsystem Responsibility
Provides application configuration management, constant definitions, build-time embedded secrets, and secure credential storage via the OS Keyring.

## Important Concepts
- **Keyring Security**: All user tokens, passwords, and API secrets are stored securely in the native OS credential store (Windows Credential Manager, Secret Service, macOS Keychain) via `keyring_store.py`.
- **Non-Sensitive Configuration**: Stored via PySide6 `QSettings` (`~/.config/StreamCheremsha/` on Linux, registry on Windows).
- **Embedded Build Configuration**: Compile-time embedded defaults used when building standalone binaries with Nuitka.
- **Tunnel Secrets**: Secure configuration and token handling for Cloudflare quick tunnels.

## Important Files & Canonical Locations
- `src/stream_cheremsha/config/keyring_store.py`: Abstraction layer over `keyring`.
- `src/stream_cheremsha/config/constants.py`: Application-wide constants, default URLs, timeout values.
- `src/stream_cheremsha/config/embedded.py`: Build-time configuration values.
- `src/stream_cheremsha/config/tunnel_secrets.py`: Cloudflare tunnel credentials.

## Important Symbols
- `KeyringStore`:
  - `get_secret(key: str) -> str | None`: Retrieves secret from OS keyring.
  - `set_secret(key: str, value: str)`: Stores secret.
  - `delete_secret(key: str)`: Removes secret.

## Relationships with Other Domains
- **Desktop UI**: Populates credential input fields in Settings tab lazily on demand.
- **Chat & Donations & Music**: Retrieves API tokens to authenticate with Twitch, YouTube, Telegram, Donatello, and Donatik.

## Common Extension Points
1. **Adding a New Secret Field**:
   - Define the key constant in `src/stream_cheremsha/config/constants.py`.
   - Access via `keyring_store.get_secret()` and `keyring_store.set_secret()`.
   - Add field in Settings tab with lazy loading.

## Relevant Invariants
- Secrets MUST NEVER be written to `QSettings`, SQLite, or log files.
- Keyring calls must be cached or lazily evaluated; never query keyring in hot loops.

## Architectural Decisions
- See [.agent/decisions/keyring_and_secrets.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/decisions/keyring_and_secrets.md)
