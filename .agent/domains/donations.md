# DOMAIN: Donations & Tip Alerts

## Subsystem Responsibility
Ingests donation alerts and tip messages from Ukrainian payment platforms (Donatello, Donatik), tracks deduplication to prevent double-alerts, and routes donation events to the TTS pipeline, desktop alerts, and overlay widgets.

## Important Concepts
- **Multi-Gateway Polling / Webhooks**: Connects to Donatello and Donatik APIs to ingest recent payments.
- **Seen State / Deduplication**: `tts_seen_store.py` tracks previously announced donation IDs in SQLite or persistent storage so alerts are not re-triggered upon app restart or poll cycles.
- **Donation Event Dispatch**: Converts raw donation payloads (donor nickname, amount, currency, message) into a standard internal event for TTS and action triggers.

## Important Files & Canonical Locations
- `src/stream_cheremsha/donations/donatello_client.py`: Donatello API client and polling logic.
- `src/stream_cheremsha/donations/donatik_client.py`: Donatik API client and webhook/polling handlers.
- `src/stream_cheremsha/donations/tts_seen_store.py`: Persistent storage tracking seen donation IDs.
- `src/stream_cheremsha/domain/models.py`: Unified `DonationEvent` dataclass.

## Important Symbols
- `DonatelloClient` / `DonatikClient`:
  - `start_polling()` / `stop()`: Lifecycle methods.
  - `on_donation` signal / callback: Dispatches new `DonationEvent`.
- `TtsSeenStore`:
  - `is_seen(donation_id: str) -> bool`: Checks if already processed.
  - `mark_seen(donation_id: str)`: Persists ID.

## Relationships with Other Domains
- **TTS Pipeline**: High-priority routing sends donation author notes directly to `TTSCoordinator`.
- **Actions Engine**: Donations exceeding configured thresholds can trigger platform automation actions.
- **Overlays**: Stream goal and donation alert widgets subscribe to donation events.
- **Config & Keyring**: Reads Donatello and Donatik API tokens from `keyring_store.py`.

## Common Extension Points
1. **Adding a New Donation Provider**:
   - Create `src/stream_cheremsha/donations/<provider>_client.py`.
   - Implement polling or webhook listener and dispatch normalized `DonationEvent`.
   - Register client in `MainWindow` connection managers.

## Relevant Invariants
- Donations must be deduplicated before triggering audio or visual alerts.
- API tokens must be stored in the OS keyring only.
- Polling intervals must respect API rate limits.

## Architectural Decisions
- See [.agent/decisions/keyring_and_secrets.md](file:///home/oleksandrboichuk/Dev/Self/stream-cheremsha/.agent/decisions/keyring_and_secrets.md)
