KEYRING_SERVICE = "stream-cheremsha"
KEY_TWITCH_TOKEN = "twitch_token"
KEY_TWITCH_CLIENT_ID = "twitch_client_id"
KEY_TWITCH_CLIENT_SECRET = "twitch_client_secret"
KEY_TWITCH_CHANNEL = "twitch_channel"
KEY_TWITCH_OAUTH = "twitch_oauth_json"
KEY_YOUTUBE_OAUTH = "youtube_oauth_json"
KEY_YOUTUBE_CLIENT_CONFIG = "youtube_google_client_json"
KEY_TIKTOK_USERNAME = "tiktok_username"
KEY_DONATIK_API_TOKEN = "donatik_api_token"
KEY_DONATELLO_API_TOKEN = "donatello_api_token"

# Public (non-secret) build/run-time overrides.
# Example (PowerShell): $env:STREAM_CHEREMSHA_TWITCH_CLIENT_ID="..."
ENV_TWITCH_CLIENT_ID = "STREAM_CHEREMSHA_TWITCH_CLIENT_ID"

YOUTUBE_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"

MAX_MESSAGE_CHARS = 400
TTS_CHUNK_CHARS = 180
# Sub-chunks shorter than this merge with neighbors (single message) to cut TTS/RVC calls.
TTS_MIN_MERGE_CHUNK_CHARS = 40

CHAT_QUEUE_MAX = 500
TTS_QUEUE_MAX = 200

TTS_MIN_INTERVAL_SEC = 0.4
