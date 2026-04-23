KEYRING_SERVICE = "stream-cheremsha"
KEY_TWITCH_TOKEN = "twitch_token"
KEY_TWITCH_CLIENT_ID = "twitch_client_id"
KEY_TWITCH_CLIENT_SECRET = "twitch_client_secret"
KEY_TWITCH_CHANNEL = "twitch_channel"
KEY_TWITCH_OAUTH = "twitch_oauth_json"
KEY_YOUTUBE_OAUTH = "youtube_oauth_json"
KEY_YOUTUBE_CLIENT_CONFIG = "youtube_google_client_json"

YOUTUBE_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"

MAX_MESSAGE_CHARS = 400
TTS_CHUNK_CHARS = 180
# Sub-chunks shorter than this merge with neighbors (single message) to cut TTS/RVC calls.
TTS_MIN_MERGE_CHUNK_CHARS = 40

CHAT_QUEUE_MAX = 500
TTS_QUEUE_MAX = 200

TTS_MIN_INTERVAL_SEC = 0.4
