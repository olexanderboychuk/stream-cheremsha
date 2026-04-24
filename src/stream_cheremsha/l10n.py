"""Application UI strings (Ukrainian / English). Qt-free for use from async workers."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Final, Literal

AppLocale = Literal["uk", "en"]

SETTINGS_UI_LOCALE: Final[str] = "ui/locale"
DEFAULT_LOCALE: Final[AppLocale] = "uk"

_TABLE: dict[str, dict[AppLocale, str]] = {
    "app.window_title": {"uk": "Stream Cheremsha", "en": "Stream Cheremsha"},
    # Tabs
    "tab.connections": {"uk": "Зв'язки", "en": "Connections"},
    "tab.settings": {"uk": "Налаштування", "en": "Settings"},
    "tab.chat": {"uk": "Чат", "en": "Chat"},
    "chat.font": {"uk": "Шрифт", "en": "Font"},
    "chat.font_size": {"uk": "Розмір", "en": "Size"},
    "chat.clear": {"uk": "Очистити чат", "en": "Clear chat"},
    "chat.clear_hint": {"uk": "Видалити всі повідомлення з вікна чату", "en": "Remove all messages from the chat pane"},
    "chat.test_message": {"uk": "Тестове повідомлення", "en": "Test chat message"},
    "chat.test_hint": {
        "uk": "Показати приклади повідомлень Twitch і YouTube — лише для перевірки вигляду (не йдуть у стрім)",
        "en": "Show sample Twitch and YouTube lines to preview appearance (not sent to the stream)",
    },
    "chat.test_author": {"uk": "Cheremsha", "en": "Cheremsha"},
    "chat.test_body_twitch": {
        "uk": "Вітаю з Twitch! Перевірка відображення чату 😀",
        "en": "Hello from Twitch! Chat display check 😀",
    },
    "chat.test_body_youtube": {
        "uk": "Вітаю з YouTube! Перевірка відображення чату 🎬",
        "en": "Hello from YouTube! Chat display check 🎬",
    },
    "chat.open_popout": {
        "uk": "В окремому вікні",
        "en": "Open in separate window",
    },
    "chat.open_popout_hint": {
        "uk": "Той самий чат у новому вікні: прозорий лише фон, текст лишається чітким; можна поверх сцени",
        "en": "Same chat in a new window: background opacity only, text stays sharp; for overlaying the scene",
    },
    "chat.popout_title": {
        "uk": "Чат — Stream Cheremsha",
        "en": "Chat — Stream Cheremsha",
    },
    "chat.popout_opacity": {"uk": "Прозорість", "en": "Opacity"},
    "chat.popout_minimize": {"uk": "Згорнути", "en": "Minimize"},
    "chat.popout_show_controls": {
        "uk": "Показати панель керування",
        "en": "Show control bar",
    },
    "chat.popout_hide_controls": {
        "uk": "Сховати панель керування",
        "en": "Hide control bar",
    },
    "tab.audio": {"uk": "Аудіо", "en": "Audio"},
    "tab.logs": {"uk": "Логи", "en": "Logs"},
    # App chrome (QML + shell)
    "ui.app_header_title": {"uk": "Stream Cheremsha", "en": "Stream Cheremsha"},
    "ui.twitch_head": {"uk": "Twitch", "en": "Twitch"},
    "ui.youtube_head": {"uk": "YouTube", "en": "YouTube"},
    "ui.tiktok_head": {"uk": "TikTok", "en": "TikTok"},
    # Platform actions
    "actions.btn": {"uk": "Дії", "en": "Actions"},
    "actions.title": {"uk": "Дії", "en": "Actions"},
    "actions.window_title": {"uk": "Дії — Stream Cheremsha", "en": "Actions — Stream Cheremsha"},
    "actions.add_rule": {"uk": "+ Додати правило", "en": "+ Add rule"},
    "actions.delete": {"uk": "Видалити", "en": "Delete"},
    "actions.edit": {"uk": "Редагування", "en": "Edit"},
    "actions.pick_rule_hint": {"uk": "Оберіть правило зліва.", "en": "Pick a rule on the left."},
    "actions.event.chat_keyword": {"uk": "Певне слово в чаті", "en": "Chat keyword"},
    "actions.event.gift_received": {"uk": "Певний подарунок", "en": "Gift received"},
    "actions.keyword": {"uk": "Слово", "en": "Keyword"},
    "actions.keyword_ph": {"uk": "наприклад: привіт", "en": "e.g. hello"},
    "actions.gift_name": {"uk": "Назва подарунка", "en": "Gift name"},
    "actions.gift_name_ph": {"uk": "наприклад: Rose", "en": "e.g. Rose"},
    "actions.min_count": {"uk": "Мін. кількість", "en": "Min count"},
    "actions.actions": {"uk": "Дії", "en": "Actions"},
    "actions.play_sound": {"uk": "Програти звук", "en": "Play sound"},
    "actions.pick_mp3": {"uk": "Оберіть .mp3…", "en": "Pick .mp3…"},
    "actions.browse": {"uk": "Огляд…", "en": "Browse…"},
    "actions.clear": {"uk": "Очистити", "en": "Clear"},
    "ui.nav_chat": {"uk": "Чат", "en": "Chat"},
    "ui.nav_tts": {"uk": "TTS", "en": "TTS"},
    "ui.nav_chat_hint": {"uk": "Відкрити чат", "en": "Open chat"},
    "ui.nav_tts_hint": {"uk": "Відкрити озвучення (TTS)", "en": "Open TTS / audio output"},
    "ui.open_settings": {"uk": "Налаштування", "en": "Settings"},
    "ui.open_settings_hint": {"uk": "Мова, автозапуск, TTS", "en": "Language, autostart, TTS"},
    "ui.nav_logs": {"uk": "Логи", "en": "Logs"},
    "ui.nav_logs_hint": {"uk": "Відкрити технічні логи", "en": "Open technical logs"},
    "ui.back_home_hint": {"uk": "Повернутися до зв'язків (головна)", "en": "Back to connections (home)"},
    "ui.nav_home": {"uk": "Додому", "en": "Home"},
    "ui.nav_home_hint": {
        "uk": "Повернутися на екран підключення Twitch / YouTube",
        "en": "Back to Twitch / YouTube connections",
    },
    "ui.nav_donations": {"uk": "Донати", "en": "Donations"},
    "ui.nav_donations_hint": {
        "uk": "Донати з Donatik та інших сервісів",
        "en": "Donations from Donatik and other services",
    },
    # Donations tab (Donatik)
    "donations.title_pick": {"uk": "Ваші донати", "en": "Your donations"},
    "donations.title_donatik": {"uk": "Donatik", "en": "Donatik"},
    "donations.title_donatello": {"uk": "Donatello", "en": "Donatello"},
    "donations.card_donatello_hint": {
        "uk": "Донати через API Donatello (токен у заголовку X-Token).",
        "en": "Donations via Donatello API (X-Token header).",
    },
    "donations.setup_intro_donatello_html": {
        "uk": "Токен з кабінету Donatello: "
        '<a href="https://donatello.to">donatello.to</a> — зберігається локально в сховищі ОС.',
        "en": "Token from your Donatello dashboard: "
        '<a href="https://donatello.to">donatello.to</a> — stored locally in the OS keyring.',
    },
    "donations.donatello_summary": {
        "uk": "Усього: {n} · стор. {p}/{pc}",
        "en": "Total: {n} · page {p}/{pc}",
    },
    "donations.err_no_token_donatello": {
        "uk": "Немає токена Donatello.",
        "en": "No Donatello token saved.",
    },
    "donations.err_http_donatello": {
        "uk": "Donatello HTTP {code}: {detail}",
        "en": "Donatello HTTP {code}: {detail}",
    },
    "donations.err_network_donatello": {
        "uk": "Мережа / Donatello: {detail}",
        "en": "Network / Donatello: {detail}",
    },
    "donations.err_bad_response_donatello": {
        "uk": "Некоректна відповідь Donatello: {detail}",
        "en": "Invalid Donatello response: {detail}",
    },
    "donations.donatello_published": {"uk": "На сайті", "en": "Published"},
    "donations.donatello_draft": {"uk": "Чернетка", "en": "Draft"},
    "donations.subtitle_pick": {
        "uk": "Оберіть сервіс. Пізніше з’являться й інші платформи.",
        "en": "Pick a provider. More platforms will appear later.",
    },
    "donations.card_donatik_hint": {
        "uk": "Перегляд донатів через API Donatik (токен з кабінету).",
        "en": "View donations via Donatik API (token from your dashboard).",
    },
    "donations.tap_to_open": {"uk": "Натисніть, щоб відкрити", "en": "Tap to open"},
    "donations.more_soon": {"uk": "Інші сервіси — незабаром", "en": "More providers coming soon"},
    "donations.back_services": {"uk": "Сервіси", "en": "Services"},
    "donations.setup_intro_html": {
        "uk": "Створіть API-токен у кабінеті Donatik: "
        '<a href="https://donatik.io">donatik.io</a> — він зберігається локально в сховищі ОС.',
        "en": "Create an API token in your Donatik dashboard: "
        '<a href="https://donatik.io">donatik.io</a> — it is stored locally in the OS keyring.',
    },
    "donations.api_token": {"uk": "API токен", "en": "API token"},
    "donations.token_ph": {"uk": "Вставте токен", "en": "Paste token"},
    "donations.save_token": {"uk": "Зберегти й завантажити", "en": "Save & load"},
    "donations.from": {"uk": "Від", "en": "From"},
    "donations.to": {"uk": "До", "en": "To"},
    "donations.refresh": {"uk": "Оновити", "en": "Refresh"},
    "donations.live_poll": {"uk": "Оновлення кожні 5 с", "en": "Live refresh (5s)"},
    "donations.tts_new": {"uk": "Озвучувати нові", "en": "TTS for new"},
    "donations.tts_announce": {
        "uk": "Новий донат від {author}: {amount} {currency}. Текст: {message}",
        "en": "New donation from {author}: {amount} {currency}. Message: {message}",
    },
    "donations.card_live_abbr": {"uk": "Live", "en": "Live"},
    "donations.card_tts_abbr": {"uk": "TTS", "en": "TTS"},
    "donations.forget_token": {"uk": "Видалити токен", "en": "Remove token"},
    "donations.summary": {
        "uk": "Усього: {n} · стор. {p}/{pc}",
        "en": "Total: {n} · page {p}/{pc}",
    },
    "donations.prev": {"uk": "Назад", "en": "Prev"},
    "donations.next": {"uk": "Далі", "en": "Next"},
    "donations.err_no_token": {"uk": "Немає токена Donatik.", "en": "No Donatik token saved."},
    "donations.err_http": {
        "uk": "Donatik HTTP {code}: {detail}",
        "en": "Donatik HTTP {code}: {detail}",
    },
    "donations.err_network": {
        "uk": "Мережа / Donatik: {detail}",
        "en": "Network / Donatik: {detail}",
    },
    "donations.err_bad_response": {
        "uk": "Некоректна відповідь Donatik: {detail}",
        "en": "Invalid Donatik response: {detail}",
    },
    # Settings
    "settings.lang_label": {"uk": "Мова інтерфейсу", "en": "Interface language"},
    "settings.lang.uk": {"uk": "Українська", "en": "Ukrainian"},
    "settings.lang.en": {"uk": "English", "en": "English"},
    "settings.intro": {
        "uk": "Якщо увімкнено галочку і ви вже залогінені на вкладці «Зв'язки», "
        "платформа стартує автоматично при наступному запуску додатку.",
        "en": "If the box is checked and you are already signed in on the Connections tab, "
        "that platform starts automatically on the next app launch.",
    },
    "settings.autostart_twitch": {
        "uk": "Автозапуск Twitch при старті додатку (потрібен вхід у Twitch і канал)",
        "en": "Auto-start Twitch on launch (requires Twitch sign-in and channel)",
    },
    "settings.autostart_youtube": {
        "uk": "Автозапуск YouTube при старті додатку (потрібен вхід у Google)",
        "en": "Auto-start YouTube on launch (requires Google sign-in)",
    },
    # Connections — TikTok
    "tk.username": {"uk": "Юзернейм", "en": "Username"},
    "tk.username_ph": {"uk": "нікнейм без @", "en": "username without @"},
    # TikTok source
    "tk.connecting": {"uk": "TikTok: підключення до @{user}…", "en": "TikTok: connecting to @{user}…"},
    "tk.connected": {"uk": "TikTok: підключено (@{user})", "en": "TikTok: connected (@{user})"},
    "tk.disconnected_retry": {
        "uk": "TikTok: роз'єднано — повтор через {sec:.0f}s…",
        "en": "TikTok: disconnected — retry in {sec:.0f}s…",
    },
    "tk.live_ended_retry": {
        "uk": "TikTok: ефір завершено — перевірка знову через {sec:.0f}s…",
        "en": "TikTok: live ended — checking again in {sec:.0f}s…",
    },
    "tk.user_offline": {
        "uk": "TikTok: @{user} офлайн — повтор через {sec:.0f}s…",
        "en": "TikTok: @{user} is offline — retry in {sec:.0f}s…",
    },
    "tk.user_not_found": {
        "uk": "TikTok: не знайдено @{user} — повтор через {sec:.0f}s…",
        "en": "TikTok: user @{user} not found — retry in {sec:.0f}s…",
    },
    "tk.age_restricted": {
        "uk": "TikTok: ефір @{user} віковий (18+) — повтор через {sec:.0f}s…",
        "en": "TikTok: @{user} is age restricted — retry in {sec:.0f}s…",
    },
    "tk.rate_limited": {
        "uk": "TikTok: ліміт підключень — пауза {sec:.0f}s…",
        "en": "TikTok: rate limited — pausing {sec:.0f}s…",
    },
    "tk.error_retry": {
        "uk": "TikTok error: {err} — повтор через {sec:.0f}s…",
        "en": "TikTok error: {err} — retry in {sec:.0f}s…",
    },
    "tk.stopped": {"uk": "TikTok: зупинено", "en": "TikTok: stopped"},
    "tk.bad_username": {"uk": "TikTok: введіть юзернейм (нік) стрімера", "en": "TikTok: enter the streamer username"},
    # Connections — Twitch
    "tw.group": {"uk": "Twitch", "en": "Twitch"},
    "tw.apps_help": {
        "uk": "Де взяти Client ID / secret: "
        '<a href="{url}">Twitch Developer Console → Applications</a>',
        "en": "Where to get Client ID / secret: "
        '<a href="{url}">Twitch Developer Console → Applications</a>',
    },
    "tw.client_id": {"uk": "Client ID (застосунок Twitch)", "en": "Client ID (Twitch application)"},
    "tw.client_secret": {"uk": "Client secret (необов'язково)", "en": "Client secret (optional)"},
    "tw.btn_browser": {"uk": "Увійти через браузер", "en": "Sign in with browser"},
    "tw.account": {"uk": "Обліковий запис", "en": "Account"},
    "tw.token_placeholder": {"uk": "Або вставте access token вручну", "en": "Or paste an access token manually"},
    "tw.token_manual": {"uk": "Токен вручну", "en": "Manual token"},
    "tw.save_app": {"uk": "Зберегти дані застосунку", "en": "Save application credentials"},
    "tw.client_id_env_required": {
        "uk": "Ця збірка очікує Client ID через змінну середовища: <code>{env}</code>",
        "en": "This build expects Client ID via environment variable: <code>{env}</code>",
    },
    "tw.logout": {"uk": "Вийти з Twitch", "en": "Sign out of Twitch"},
    "tw.channel": {"uk": "Канал чату", "en": "Chat channel"},
    "tw.channel_ph": {"uk": "логін каналу без #", "en": "channel login without #"},
    "tw.connected_as": {"uk": "Підключено до Twitch як @{login}", "en": "Connected to Twitch as @{login}"},
    "tw.connected_oauth": {"uk": "Підключено до Twitch (OAuth).", "en": "Connected to Twitch (OAuth)."},
    "tw.connected_token": {
        "uk": "Підключено до Twitch (збережений токен).",
        "en": "Connected to Twitch (saved token).",
    },
    "tw.connected_generic": {"uk": "Підключено до Twitch.", "en": "Connected to Twitch."},
    "tw.transport_stop": {"uk": "⏹ Зупинити Twitch", "en": "⏹ Stop Twitch"},
    "tw.transport_start": {"uk": "▶ Увімкнути Twitch", "en": "▶ Start Twitch"},
    # Connections — YouTube
    "yt.group": {"uk": "YouTube", "en": "YouTube"},
    "yt.oauth_help": {
        "uk": "Де створити OAuth-клієнт (тип Desktop) і JSON: "
        '<a href="{creds_url}">Google Cloud → Облікові дані</a>'
        " · "
        '<a href="{api_url}">увімкнути YouTube Data API v3</a>',
        "en": "Create an OAuth client (Desktop) and JSON: "
        '<a href="{creds_url}">Google Cloud → Credentials</a>'
        " · "
        '<a href="{api_url}">enable YouTube Data API v3</a>',
    },
    "yt.btn_google": {"uk": "Увійти через Google (браузер)", "en": "Sign in with Google (browser)"},
    "yt.forget_json": {"uk": "Забути збережений JSON клієнта Google…", "en": "Forget saved Google client JSON…"},
    "yt.connected_default": {
        "uk": "Обліковий запис Google підключено для YouTube.",
        "en": "Google account linked for YouTube.",
    },
    "yt.logout": {"uk": "Вийти з Google (YouTube)", "en": "Sign out of Google (YouTube)"},
    "yt.video_ph": {
        "uk": "Порожньо — знайти всі ваші активні ефіри; або URL / ID одного live-відео",
        "en": "Empty — discover all your live streams; or one live video URL / ID",
    },
    "yt.video_label": {"uk": "URL або ID відео (необов'язково)", "en": "Video URL or ID (optional)"},
    "yt.studio_link": {
        "uk": 'Посилання на ефір: <a href="https://studio.youtube.com/">YouTube Studio</a>',
        "en": 'Stream link: <a href="https://studio.youtube.com/">YouTube Studio</a>',
    },
    "yt.transport_stop": {"uk": "⏹ Зупинити YouTube", "en": "⏹ Stop YouTube"},
    "yt.transport_start": {"uk": "▶ Увімкнути YouTube", "en": "▶ Start YouTube"},
    # Logs tab
    "logs.hint": {
        "uk": "Рядки статусу додатку та записи логера "
        "<code>stream_cheremsha</code> (рівень INFO і вище).",
        "en": "App status lines and <code>stream_cheremsha</code> logger output (INFO and above).",
    },
    "logs.clear": {"uk": "Очистити", "en": "Clear"},
    # Audio
    "audio.output": {"uk": "Вихід", "en": "Output"},
    "audio.refresh": {"uk": "Оновити пристрої", "en": "Refresh devices"},
    "audio.tts_engine": {"uk": "Рушій TTS", "en": "TTS engine"},
    "audio.tts_engine_google": {"uk": "Google Translate (мережа)", "en": "Google Translate (online)"},
    "audio.tts_engine_piper": {"uk": "Piper (локально, piper-tts)", "en": "Piper (local, piper-tts)"},
    "audio.piper_voice_group": {"uk": "Piper — голос (.onnx)", "en": "Piper — voice (.onnx)"},
    "audio.piper_path_short": {"uk": "Файл", "en": "File"},
    "audio.piper_voice_intro": {
        "uk": (
            "Потрібен файл голосу. Оберіть один із варіантів (можна комбінувати: спочатку завантажити, "
            "потім за потреби змінити шлях)."
        ),
        "en": (
            "You need a voice file. Pick one approach (you can combine: download first, then adjust the path if "
            "needed)."
        ),
    },
    "audio.piper_option_download": {
        "uk": "1) Завантажити з інтернету — для мови з поля «Мова озвучення (TTS)» вище. Потрібен інтернет.",
        "en": (
            "1) Download from the Internet — uses the “Speech language (TTS)” field above. Internet access is "
            "required."
        ),
    },
    "audio.piper_option_file": {
        "uk": "2) Або вкажіть локальний файл .onnx (і зазвичай .onnx.json поруч), якщо модель уже є на диску:",
        "en": "2) Or point to a local .onnx file (and usually a matching .onnx.json) if you already have the model:",
    },
    "audio.piper_model": {"uk": "Шлях до ONNX-моделі Piper", "en": "Piper ONNX model path"},
    "audio.piper_browse": {"uk": "Огляд…", "en": "Browse…"},
    "audio.tts_language": {"uk": "Мова озвучення (TTS)", "en": "Speech language (TTS)"},
    "tts_lang.uk_UA": {"uk": "Українська (uk-UA)", "en": "Ukrainian (uk-UA)"},
    "tts_lang.en_US": {"uk": "English US (en-US)", "en": "English US (en-US)"},
    "tts_lang.en_GB": {"uk": "English UK (en-GB)", "en": "English UK (en-GB)"},
    "tts_lang.de_DE": {"uk": "Німецька (de-DE)", "en": "German (de-DE)"},
    "tts_lang.pl_PL": {"uk": "Польська (pl-PL)", "en": "Polish (pl-PL)"},
    "audio.piper_cuda": {"uk": "Використовувати GPU (CUDA)", "en": "Use GPU (CUDA)"},
    "audio.piper_cuda_tip": {
        "uk": "Потрібен відповідний драйвер NVIDIA. Якщо помилок немає — залишайте ввімкненим.",
        "en": "Requires a suitable NVIDIA driver. If things work, leave it on.",
    },
    "audio.piper_download": {"uk": "Завантажити голос", "en": "Download voice"},
    "audio.piper_help_tooltip": {"uk": "Довідка про Piper", "en": "Piper help"},
    "audio.piper_help_title": {"uk": "Piper TTS — довідка", "en": "Piper TTS — help"},
    "audio.rvc_group": {
        "uk": "RVC (тембр після TTS)",
        "en": "RVC (timbre after TTS)",
    },
    "audio.rvc_intro": {
        "uk": "RVC (Retrieval-based Voice Conversion) застосовується до вже синтезованого звуку (Google чи Piper) "
        "і змінює тембр (мем, клон). У venv: `cheremsha-bootstrap-rvc` (див. README). "
        "Для Google TTS звук тимчасово перетворюється в WAV (ffmpeg) перед RVC.",
        "en": (
            "RVC (Retrieval-based Voice Conversion) runs on synthesized audio (Google or Piper) to change timbre. "
            "Run `cheremsha-bootstrap-rvc` in the venv (see README). Google TTS (MP3) is decoded to WAV via ffmpeg "
            "before RVC."
        ),
    },
    "audio.rvc_enable": {
        "uk": "Увімкнути RVC (після будь-якого TTS)",
        "en": "Enable RVC (after any TTS engine)",
    },
    "audio.rvc_model": {"uk": "Модель (.pth)", "en": "Model (.pth)"},
    "audio.rvc_index": {
        "uk": "Індекс (.index, за бажанням)",
        "en": "Index (.index, optional)",
    },
    "audio.rvc_cuda": {
        "uk": "Використовувати GPU (CUDA)",
        "en": "Use GPU (CUDA)",
    },
    "audio.rvc_cuda_tip": {
        "uk": "RVC важчий за Piper; на GPU зазвичай швидше. Повний опис — у підказці для блоку RVC.",
        "en": "RVC is heavier than Piper; GPU is usually faster. Full details: tooltip on the RVC group.",
    },
    "audio.rvc_loading": {
        "uk": "Завантаження RVC…",
        "en": "Loading RVC…",
    },
    "audio.rvc_unloading": {
        "uk": "Вимкнення RVC…",
        "en": "Stopping RVC…",
    },
    "audio.volume": {"uk": "Гучність", "en": "Volume"},
    "audio.volume_tip": {
        "uk": "Гучність виходу програми (колонки / гарнітура).",
        "en": "App output level (speakers/headset).",
    },
    "audio.tts_gain": {"uk": "Підсилення TTS (ffmpeg)", "en": "TTS gain (ffmpeg)"},
    "audio.tts_gain_tip": {
        "uk": "Базове підсилення TTS у ffmpeg (volume + dynaudnorm / loudnorm). "
        "Зберігається між запусками.",
        "en": "Base TTS gain in ffmpeg (volume + dynaudnorm / loudnorm). Persisted between runs.",
    },
    "audio.tts_hint": {
        "uk": "Google: часто тихий — підніміть гучність; ffmpeg підсилює перед відтворенням "
        "(MP3 або WAV). Piper: локальний синтез; модель голосу може бути вже в збірці "
        "або її вказують/завантажують у блоці «Модель голосу Piper» вище. "
        "RVC (опційно) змінює тембр після TTS. "
        "Для фонемізації в системі зазвичай потрібен espeak-ng. "
        "У «Логах» після тесту — «TTS: ffmpeg ok» або попередження.",
        "en": "Google: often quiet — raise volume; ffmpeg boosts before playback (MP3 or WAV). "
        "Piper: local synthesis; the voice model may be bundled with the app, or you set it "
        "in the “Piper voice model” section above (download or browse). "
        "Optional RVC remaps timbre after synthesis. "
        "espeak-ng is usually required on the system for phonemization. "
        "After a test, Logs shows «TTS: ffmpeg ok» or a warning.",
    },
    "audio.test": {"uk": "Тест", "en": "Test"},
    "audio.test_phrase_default": {"uk": "Привіт, це тест.", "en": "Hello, this is a test."},
    "audio.speak_test": {"uk": "Відтворити тестову фразу", "en": "Speak test phrase"},
    "audio.card_test_header": {"uk": "Тест озвучення", "en": "TTS test"},
    "audio.card_tts_title": {"uk": "Мова та рушій TTS", "en": "TTS language & engine"},
    "audio.card_levels_title": {"uk": "Вихід і рівні", "en": "Output & levels"},
    # Status / footer
    "footer.pipeline": {"uk": "Пайплайн", "en": "Pipeline"},
    "footer.twitch": {"uk": "Twitch", "en": "Twitch"},
    "footer.youtube": {"uk": "YouTube", "en": "YouTube"},
    "footer.tiktok": {"uk": "TikTok", "en": "TikTok"},
    "footer.queues": {"uk": "Черги", "en": "Queues"},
    "footer.on": {"uk": "увімк", "en": "on"},
    "footer.off": {"uk": "вимк", "en": "off"},
    "footer.chat": {"uk": "чат", "en": "chat"},
    "footer.tts": {"uk": "tts", "en": "tts"},
    "footer.rvc": {"uk": "rvc", "en": "rvc"},
    # Main-window status messages (exact match routing uses all locales)
    "status.logout_twitch": {"uk": "Вийшли з Twitch.", "en": "Signed out of Twitch."},
    "status.logout_youtube": {"uk": "Вийшли з Google (YouTube).", "en": "Signed out of Google (YouTube)."},
    "status.twitch_keys_saved": {"uk": "Дані Twitch збережено.", "en": "Twitch credentials saved."},
    "status.twitch_browser_ok": {"uk": "Twitch: увійшли через браузер.", "en": "Twitch: signed in via browser."},
    "status.youtube_json_removed": {
        "uk": "YouTube: JSON клієнта Google видалено зі сховища.",
        "en": "YouTube: Google client JSON removed from storage.",
    },
    "status.youtube_signed_in": {"uk": "YouTube: увійшли через Google.", "en": "YouTube: signed in with Google."},
    "startup.workers": {"uk": "Запуск обробників пайплайну…", "en": "Starting pipeline workers…"},
    "startup.ready": {
        "uk": "Готово — підключіть Twitch і/або YouTube",
        "en": "Ready — connect Twitch and/or YouTube",
    },
    "status.app_idle": {"uk": "Готово", "en": "Ready"},
    "status.piper_download_start": {
        "uk": "Piper: завантаження голосу {voice}…",
        "en": "Piper: downloading voice {voice}…",
    },
    "status.piper_download_ok": {"uk": "Piper: модель збережено — {path}", "en": "Piper: model saved — {path}"},
    "audio.piper_downloading": {"uk": "Завантаження голосу…", "en": "Downloading voice…"},
    "status.piper_need_model": {
        "uk": (
            "Piper: немає .onnx — натисніть «Завантажити голос» або «Огляд…»; "
            "до цього використовується Google TTS."
        ),
        "en": "Piper: no .onnx yet — use “Download voice” or “Browse…”; Google TTS is used until a model is set.",
    },
    # Coordinator
    "coord.chat_queue_full": {
        "uk": "Черга чату переповнена — повідомлення відкинуто",
        "en": "Chat queue full — dropping message",
    },
    "coord.tts_queue_full": {
        "uk": "Черга TTS переповнена — подальші частини цього повідомлення відкинуто",
        "en": "TTS queue full — dropping further chunks for this message",
    },
    "coord.audio_error": {"uk": "Помилка аудіо: {err}", "en": "Audio error: {err}"},
    "coord.tts_http_error": {"uk": "Помилка HTTP TTS: {err}", "en": "TTS HTTP error: {err}"},
    "coord.tts_error": {"uk": "Помилка TTS: {err}", "en": "TTS error: {err}"},
    # Twitch IRC / lifecycle
    "twitch.connecting": {"uk": "Twitch: підключення…", "en": "Twitch: connecting…"},
    "twitch.irc_ready": {
        "uk": "Twitch: у IRC (@{nick}), чат #{channel}",
        "en": "Twitch: in IRC (@{nick}), chat #{channel}",
    },
    "twitch.error_retry": {
        "uk": "Twitch error: {err} — повтор через {sec:.0f}s…",
        "en": "Twitch error: {err} — retry in {sec:.0f}s…",
    },
    "twitch.closed_retry": {
        "uk": "Twitch: з'єднання закрито — повторне підключення через {sec:.0f}s…",
        "en": "Twitch: connection closed — reconnecting in {sec:.0f}s…",
    },
    "twitch.stopped": {"uk": "Twitch: зупинено", "en": "Twitch: stopped"},
    # Twitch device OAuth (twitch_oauth_device)
    "twitch.oauth_prompt": {
        "uk": "Twitch: підтвердіть доступ у браузері — за потреби код: {code} (закінчується за {sec}s)",
        "en": "Twitch: approve access in the browser — if needed, code: {code} (expires in {sec}s)",
    },
    "twitch.oauth_signed_in": {"uk": "Twitch: увійшли", "en": "Twitch: signed in"},
    "twitch.oauth_denied": {
        "uk": "Вхід Twitch за пристроєм прострочено або відхилено — спробуйте знову",
        "en": "Twitch device login expired or was denied — try again",
    },
    "twitch.oauth_timeout": {
        "uk": "Вхід Twitch за пристроєм: час очікування підтвердження в браузері вичерпано",
        "en": "Twitch device login timed out waiting for browser approval",
    },
    "twitch.oauth_token_err": {"uk": "Помилка токена Twitch: {detail}", "en": "Twitch token error: {detail}"},
    # YouTube source
    "yt.oauth_browser": {"uk": "YouTube: відкриваємо браузер для OAuth…", "en": "YouTube: opening browser for OAuth…"},
    "yt.oauth_saved": {"uk": "YouTube: токен OAuth збережено", "en": "YouTube: OAuth token saved"},
    "yt.run_oauth_first": {"uk": "YouTube: спочатку виконайте OAuth", "en": "YouTube: run OAuth first"},
    "yt.token_expired": {
        "uk": "YouTube: токен прострочено — знову OAuth",
        "en": "YouTube: token expired — run OAuth again",
    },
    "yt.stopped": {"uk": "YouTube: зупинено", "en": "YouTube: stopped"},
    "yt.bad_url": {"uk": "YouTube: некоректний URL або ID відео", "en": "YouTube: invalid video URL or ID"},
    "yt.token_missing": {
        "uk": "YouTube: немає токена OAuth — увійдіть знову",
        "en": "YouTube: OAuth token missing — run login again",
    },
    "yt.api_init_retry": {
        "uk": "YouTube API init error: {err} — повтор через {sec:.0f}s…",
        "en": "YouTube API init error: {err} — retry in {sec:.0f}s…",
    },
    "yt.retry": {"uk": "YouTube: {err} — повтор через {sec:.0f}s…", "en": "YouTube: {err} — retry in {sec:.0f}s…"},
    "yt.wait_live": {
        "uk": "YouTube: {err} — очікування live ({sec:.0f}s)…",
        "en": "YouTube: {err} — waiting for live ({sec:.0f}s)…",
    },
    "yt.no_live_retry": {
        "uk": "YouTube: немає активного ефіру — перевірка знову через {sec:.0f}s…",
        "en": "YouTube: no active stream — checking again in {sec:.0f}s…",
    },
    "yt.no_chat_retry": {
        "uk": "YouTube: для цього відео ще немає live-чату — перевірка через {sec:.0f}s…",
        "en": "YouTube: no live chat for this video yet — checking again in {sec:.0f}s…",
    },
    "yt.polling": {"uk": "YouTube: опитування чату…", "en": "YouTube: polling chat…"},
    "yt.multi_streams": {
        "uk": "YouTube: знайдено {n} ефірів — чати по черзі (менше витрата квоти)…",
        "en": "YouTube: found {n} streams — rotating chats (lower API quota use)…",
    },
    "yt.quota_backoff": {
        "uk": "YouTube: квота API вичерпана — пауза ~{min:.0f} хв без запитів…",
        "en": "YouTube: API quota exhausted — pausing ~{min:.0f} min without requests…",
    },
    "yt.api_init": {"uk": "YouTube API init error: {err}", "en": "YouTube API init error: {err}"},
    "yt.http_error": {"uk": "YouTube HTTP error: {err}", "en": "YouTube HTTP error: {err}"},
    "yt.error": {"uk": "YouTube error: {err}", "en": "YouTube error: {err}"},
    # Dialogs — titles and text
    "dlg.keyring": {"uk": "Сховище паролів", "en": "Keyring"},
    "dlg.twitch": {"uk": "Twitch", "en": "Twitch"},
    "dlg.twitch_oauth": {"uk": "Twitch OAuth", "en": "Twitch OAuth"},
    "dlg.twitch_need_client_id": {
        "uk": "Спочатку введіть Client ID застосунку Twitch.",
        "en": "Enter the Twitch application Client ID first.",
    },
    "dlg.twitch_need_channel": {"uk": "Потрібен канал (логін без #).", "en": "Channel login is required (without #)."},
    "dlg.twitch_need_token": {
        "uk": "Немає токена: увійдіть через браузер, збережіть дані застосунку або вставте токен.",
        "en": "No token: sign in via browser, save app credentials, or paste a token.",
    },
    "dlg.youtube": {"uk": "YouTube", "en": "YouTube"},
    "dlg.tiktok": {"uk": "TikTok", "en": "TikTok"},
    "dlg.tiktok_need_username": {"uk": "Потрібен юзернейм (нік) стрімера.", "en": "Streamer username is required."},
    "dlg.youtube_next_json": {
        "uk": "Наступний вхід через Google знову запропонує обрати JSON клієнта.",
        "en": "The next Google sign-in will ask you to pick the client JSON again.",
    },
    "dlg.google_json_title": {
        "uk": "Оберіть JSON OAuth-клієнта Google (один раз)",
        "en": "Select Google OAuth client JSON (one-time)",
    },
    "dlg.tts": {"uk": "TTS", "en": "TTS"},
    "dlg.piper_not_installed": {
        "uk": (
            "Рушій Piper у цій збірці недоступний. Спробуйте перевстановити додаток або зверніться до автора збірки."
        ),
        "en": "The bundled Piper engine is not available. Try reinstalling the app or contact the packager.",
    },
    "dlg.rvc_missing": {
        "uk": (
            "RVC: стек не зібрано. У venv виконайте `cheremsha-bootstrap-rvc` (див. README), перезапустіть додаток. "
            "GPU — PyTorch (CUDA)."
        ),
        "en": (
            "RVC stack is not available. In the same venv run `cheremsha-bootstrap-rvc` (see README), then restart. "
            "For GPU use a CUDA PyTorch build."
        ),
    },
    "dlg.rvc_missing_detail": {
        "uk": (
            "RVC: стек не зібрано. Деталі:\n{detail}\n\nУ venv виконайте `cheremsha-bootstrap-rvc` (див. README), "
            "перезапустіть додаток."
        ),
        "en": (
            "RVC stack is not available. Details:\n{detail}\n\nIn the same venv run `cheremsha-bootstrap-rvc` "
            "(see README), then restart."
        ),
    },
    "dlg.rvc_toggle_failed": {
        "uk": "Помилка RVC:\n{detail}",
        "en": "RVC error:\n{detail}",
    },
    "dlg.piper_download_failed": {"uk": "Завантаження голосу Piper", "en": "Piper voice download"},
    "dlg.piper_voice_unknown": {
        "uk": "Для цієї мови немає вбудованого id голосу Piper — оберіть .onnx вручну.",
        "en": "No bundled Piper voice id for this language — pick an .onnx file manually.",
    },
    "dlg.json_filter": {"uk": "JSON (*.json);;Усі файли (*)", "en": "JSON (*.json);;All files (*)"},
    "help.piper_html": {
        "uk": (
            "<h2>Piper TTS</h2>"
            "<p><b>Piper</b> — локальний нейромережевий синтез мовлення. У збірці додатка рушій вже вбудований; "
            "кожен голос — це файли <code>.onnx</code> і зазвичай <code>.onnx.json</code> поруч.</p>"
            "<h3>Що варто знати</h3>"
            "<ul>"
            "<li><b>Голос</b> може бути вже в поставці додатка, або доданий кнопками «Завантажити голос» / «Огляд…» "
            "у блоці «Модель голосу Piper» на вкладці «Аудіо».</li>"
            "<li>Для <b>фонемізації</b> у системі зазвичай має бути <b>espeak-ng</b> — без нього Piper на частині "
            "систем може не стартувати.</li>"
            "<li><b>CUDA</b>: за потреби встановіть драйвер NVIDIA, потім увімкніть у додатку "
            "«Прискорення GPU (CUDA)» — важливо мати поєднання: відеокарта, драйвер і збірка додатка з підтримкою GPU."
            "</li>"
            "</ul>"
            "<h3>Модель і мова</h3>"
            "<p>«Мова озвучення (TTS)» впливає на Google TTS і на те, <i>який голос завантажиться</i> для Piper. "
            "За «Завантажити голос» файли зберігаються, зазвичай під "
            "<code>~/.local/share/stream-cheremsha/piper-voices/</code> "
            "або <code>$XDG_DATA_HOME/stream-cheremsha/piper-voices/</code>.</p>"
            "<h3>Вимоги до ПК</h3>"
            "<ul>"
            "<li><b>CPU</b>: голоси «medium» зазвичай нормально на сучасному 4+ ядерному CPU; «x_low» легші.</li>"
            "<li><b>GPU</b>: з CUDA менше навантаження на CPU; потрібна підтримувана відеокарта NVIDIA у цьому "
            "режимі.</li>"
            "<li><b>Диск</b>: одна модель — порядку десятків–сотень МБ.</li>"
            "</ul>"
            "<p>Документація: "
            '<a href="https://github.com/OHF-Voice/piper1-gpl">OHF-Voice/piper1-gpl</a>, '
            'каталог голосів: <a href="https://huggingface.co/rhasspy/piper-voices">rhasspy/piper-voices</a>.</p>'
        ),
        "en": (
            "<h2>Piper TTS</h2>"
            "<p><b>Piper</b> is a local neural TTS engine. The app ships the engine; each voice is an "
            "<code>.onnx</code> file (and usually a matching <code>.onnx.json</code> next to it).</p>"
            "<h3>Good to know</h3>"
            "<ul>"
            "<li><b>Voices</b> may be bundled with the app, or you add one via “Download voice” / “Browse…” in the "
            "“Piper voice model” block on the Audio tab.</li>"
            "<li><b>espeak-ng</b> is usually required on the system for phonemization; without it, Piper may fail to "
            "start on some setups.</li>"
            "<li><b>CUDA</b>: install a suitable NVIDIA driver, then turn on “GPU (CUDA)” in the app. "
            "The GPU build of the app must match your environment (driver + a GPU-enabled build).</li>"
            "</ul>"
            "<h3>Model & language</h3>"
            "<p>“Speech language (TTS)” affects both Google and <i>which voice is fetched</i> for Piper. "
            "“Download voice” stores files, typically under "
            "<code>~/.local/share/stream-cheremsha/piper-voices/</code> or "
            "<code>$XDG_DATA_HOME/stream-cheremsha/piper-voices/</code>.</p>"
            "<h3>Hardware</h3>"
            "<ul>"
            "<li><b>CPU</b>: “medium” voices are usually fine on a modern 4+ core CPU; “x_low” is lighter.</li>"
            "<li><b>GPU</b>: CUDA reduces CPU load; a supported NVIDIA GPU and a compatible app build are needed."
            "</li>"
            "<li><b>Disk</b>: one voice is on the order of tens–hundreds of MB.</li>"
            "</ul>"
            "<p>Docs: "
            '<a href="https://github.com/OHF-Voice/piper1-gpl">OHF-Voice/piper1-gpl</a>, '
            'voice catalog: <a href="https://huggingface.co/rhasspy/piper-voices">rhasspy/piper-voices</a>.</p>'
        ),
    },
}


def normalize_locale(raw: str) -> AppLocale:
    v = (raw or "").strip().lower()
    if v in ("en", "english", "анг"):
        return "en"
    return "uk"


def tr(locale: str, key: str, **kwargs: object) -> str:
    lc = normalize_locale(locale)
    row = _TABLE.get(key)
    if row is None:
        raise KeyError(f"Unknown l10n key: {key}")
    template = row.get(lc) or row["uk"]
    return template.format(**kwargs) if kwargs else template


def all_locale_strings(key: str) -> frozenset[str]:
    """Every localized variant of a message (for comparing inbound status lines)."""
    row = _TABLE[key]
    return frozenset({row["uk"], row["en"]})


def all_locale_strings_many(*keys: str) -> frozenset[str]:
    out: set[str] = set()
    for k in keys:
        out.update(all_locale_strings(k))
    return frozenset(out)
