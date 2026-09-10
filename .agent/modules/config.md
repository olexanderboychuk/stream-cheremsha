# MODULE: Configuration & Secrets

## Purpose
Manages all application configuration, including constants, environment variables, and secure storage of secrets (API tokens, passwords) in the OS keyring.

## Canonical Locations
- `src/stream_cheremsha/config/`: Main config directory.
- `src/stream_cheremsha/config/keyring_store.py` (Secret management)
- `src/stream_cheremsha/config/constants.py` (Hardcoded constants)
- `src/stream_cheremsha/config/embedded.py` (Build-time embedded secrets)
- `src/stream_cheremsha/config/tunnel_secrets.py` (Cloudflare tunnel config)

## Public Surface
Provides a unified interface for the rest of the application to access configuration values and retrieve secrets securely.

## Internal Structure
- **Keyring Store**: Abstracts OS-specific secret storage (Windows Credential Manager, Secret Service, KWallet).
- **Embedded Config**: Handles secrets compiled into the binary during Nuitka builds.
- **Constants**: Centralized repository for non-sensitive configuration values.

## Dependencies
- `keyring` (OS integration)

## Tests
- `tests/test_tunnel_secrets.py`

## Change Guide
- **Add a new secret type**: Update `config/keyring_store.py` to handle the new key and ensure it's initialized correctly in the UI.
- **Add a new constant**: Add to `src/stream_cheremsha/config/constants.py`.
- **Modify build-time secrets**: Update `src/stream_cheremsha/config/embedded.py` and update the build script if necessary.

## Invariants
- Secrets MUST NEVER be stored in plain text files or logs.
- The keyring must be checked before falling back to environment variables for sensitive data.

## Pitfalls
- Missing `keyrings.alt` on some Linux distributions can cause the keyring to fail.
- Incorrectly handling build-time secrets can lead to them being leaked if not properly scoped in `embedded.py`.

## Avoid
Do not add any new secret storage logic outside of `config/keyring_store.py`.
