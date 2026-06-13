KEYRING_SERVICE = "stream-cheremsha"
KEY_TWITCH_TOKEN = "twitch_token"
KEY_TWITCH_CLIENT_ID = "twitch_client_id"
KEY_TWITCH_CLIENT_SECRET = "twitch_client_secret"
KEY_TWITCH_CHANNEL = "twitch_channel"
KEY_TWITCH_OAUTH = "twitch_oauth_json"
KEY_YOUTUBE_OAUTH = "youtube_oauth_json"
KEY_YOUTUBE_CLIENT_CONFIG = "youtube_google_client_json"
KEY_TIKTOK_USERNAME = "tiktok_username"
# QSettings scope for TikTok actions: one ruleset for the platform, not per streamer login.
TIKTOK_ACTIONS_ACCOUNT_KEY = "app"
KEY_DONATIK_API_TOKEN = "donatik_api_token"
KEY_DONATELLO_API_TOKEN = "donatello_api_token"
KEY_OBS_WEBSOCKET_PASSWORD = "obs_websocket_password"
KEY_TELEGRAM_BOT_TOKEN = "telegram_bot_token"
KEY_GENIUS_CLIENT_ACCESS_TOKEN = "genius_client_access_token"
KEY_GROQ_API_KEY = "groq_api_key"
# Older builds stored a Gemini key here; still read if KEY_GROQ_API_KEY is unset.
KEY_LEGACY_GEMINI_API_KEY = "gemini_api_key"
KEY_OPENAI_API_KEY = "openai_api_key"
KEY_NGROK_AUTHTOKEN = "ngrok_authtoken"
SETTINGS_OBS_WS_HOST = "obs/websocket_host"
SETTINGS_OBS_WS_PORT = "obs/websocket_port"
# When false, the app does not open OBS WebSocket connections (no scene pickers, no actions).
SETTINGS_OBS_WS_ENABLED = "obs/websocket_enabled"
SETTINGS_OVERLAY_TUNNEL_ENABLED = "overlay/tunnel_enabled"
SETTINGS_OVERLAY_TUNNEL_PROVIDER = "overlay/tunnel_provider"
SETTINGS_OVERLAY_TUNNEL_CUSTOM_URL = "overlay/tunnel_custom_url"
SETTINGS_OVERLAY_NGROK_DOMAIN = "overlay/ngrok_domain"
SETTINGS_OVERLAY_CLOUDFLARE_HOSTNAME = "overlay/cloudflare_hostname"
KEY_CLOUDFLARE_TUNNEL_TOKEN = "cloudflare_tunnel_token"
ENV_CLOUDFLARE_TUNNEL_TOKEN = "STREAM_CHEREMSHA_CLOUDFLARE_TUNNEL_TOKEN"
ENV_CLOUDFLARE_TUNNEL_HOSTNAME = "STREAM_CHEREMSHA_CLOUDFLARE_HOSTNAME"

# Public (non-secret) build/run-time overrides.
# Example (PowerShell): $env:STREAM_CHEREMSHA_TWITCH_CLIENT_ID="..."
ENV_TWITCH_CLIENT_ID = "STREAM_CHEREMSHA_TWITCH_CLIENT_ID"

ENV_MUSICBRAINZ_CONTACT = "STREAM_CHEREMSHA_MUSICBRAINZ_CONTACT"
# yt-dlp: age-restricted / login-only YouTube (see yt-dlp FAQ on cookies).
ENV_YTDLP_COOKIESFILE = "STREAM_CHEREMSHA_YTDLP_COOKIES"
ENV_YTDLP_COOKIES_FROM_BROWSER = "STREAM_CHEREMSHA_YTDLP_COOKIES_FROM_BROWSER"

YOUTUBE_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"

MAX_MESSAGE_CHARS = 400
TTS_CHUNK_CHARS = 180
# Sub-chunks shorter than this merge with neighbors (single message) to cut TTS calls.
TTS_MIN_MERGE_CHUNK_CHARS = 40

CHAT_QUEUE_MAX = 500
TTS_QUEUE_MAX = 200

TTS_MIN_INTERVAL_SEC = 0.4
