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
    "chat.clear_hint": {
        "uk": "Видалити всі повідомлення з вікна чату",
        "en": "Remove all messages from the chat pane",
    },
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
    # Updates
    "dlg.update": {"uk": "Оновлення", "en": "Update"},
    "settings.updates_group": {"uk": "Оновлення", "en": "Updates"},
    "settings.updates_check_on_startup": {
        "uk": "Перевіряти оновлення при запуску",
        "en": "Check for updates on startup",
    },
    "settings.updates_check_now": {"uk": "Перевірити оновлення", "en": "Check for updates"},
    "updates.up_to_date": {
        "uk": "У вас остання версія ({version}).",
        "en": "You're up to date ({version}).",
    },
    "updates.redirect_releases": {
        "uk": "Оновлення для Linux поки вручну: відкриваємо сторінку релізів.",
        "en": "Linux updates are manual for now: opening the Releases page.",
    },
    "updates.available": {
        "uk": 'Доступна нова версія: <b>{latest}</b> (у вас {current}).<br/><a href="{url}">Changelog</a>',
        "en": 'A new version is available: <b>{latest}</b> (you have {current}).<br/><a href="{url}">Changelog</a>',
    },
    "updates.btn_update": {"uk": "Оновити", "en": "Update"},
    "updates.btn_not_now": {"uk": "Не зараз", "en": "Not now"},
    "updates.ignore_this_version": {
        "uk": "Більше не нагадувати цю версію",
        "en": "Don’t remind me for this version",
    },
    "updates.no_windows_asset": {
        "uk": "Для цього релізу немає Windows інсталятора.",
        "en": "This release has no Windows installer asset.",
    },
    "updates.downloading": {"uk": "Завантаження інсталятора…", "en": "Downloading installer…"},
    "updates.ready_to_install": {"uk": "Готово до встановлення.", "en": "Ready to install."},
    "updates.sha_mismatch": {
        "uk": "Помилка безпеки: SHA-256 не збігається. Оновлення скасовано.",
        "en": "Security error: SHA-256 mismatch. Update aborted.",
    },
    "updates.signature_invalid": {
        "uk": "Помилка безпеки: підпис інсталятора недійсний. Оновлення скасовано.",
        "en": "Security error: invalid installer signature. Update aborted.",
    },
    "ui.settings_tooltip": {"uk": "Налаштування", "en": "Settings"},
    "ui.nav_music": {"uk": "Музика", "en": "Music"},
    "ui.nav_music_hint": {"uk": "Черга музики", "en": "Music queue"},
    # App chrome (QML + shell)
    "ui.app_header_title": {"uk": "Stream Cheremsha", "en": "Stream Cheremsha"},
    "ui.twitch_head": {"uk": "Twitch", "en": "Twitch"},
    "ui.youtube_head": {"uk": "YouTube", "en": "YouTube"},
    "ui.tiktok_head": {"uk": "TikTok", "en": "TikTok"},
    "connections.tts_chat": {"uk": "Озвучувати чат (TTS)", "en": "Speak chat (TTS)"},
    "connections.platform_enabled": {"uk": "Платформа увімкнена", "en": "Platform enabled"},
    "connections.analytics_soon_title": {
        "uk": "Аналітика — скоро",
        "en": "Analytics — coming soon",
    },
    "connections.analytics_soon_sub": {
        "uk": "Тут буде статистика по чату, TTS, активності й підключеннях.",
        "en": "Here you'll see chat, TTS, activity, and connection stats.",
    },
    "connections.tiktok_analytics_title": {"uk": "TikTok — аналітика", "en": "TikTok analytics"},
    "connections.tiktok_analytics_online": {"uk": "Онлайн", "en": "Live viewers"},
    "connections.tiktok_analytics_total": {"uk": "Всього глядачів", "en": "Total viewers"},
    "connections.tiktok_analytics_gifts": {"uk": "Подарунки (шт.)", "en": "Gifts (count)"},
    "connections.tiktok_analytics_diamonds": {"uk": "Діаманти", "en": "Diamonds"},
    "connections.tiktok_analytics_activity": {"uk": "Події", "en": "Events"},
    "connections.tiktok_analytics_offline": {
        "uk": "Увімкніть TikTok зліва, щоб збирати статистику за цей сеанс.",
        "en": "Enable TikTok on the left to collect stats for this session.",
    },
    "connections.tiktok_analytics_follow": {"uk": "підписка", "en": "followed"},
    "connections.tiktok_analytics_join": {"uk": "зайшов у ефір", "en": "joined"},
    "connections.tiktok_analytics_gift_suffix": {"uk": "подарунок", "en": "gift"},
    # Connections — Twitch analytics
    "connections.twitch_analytics_title": {"uk": "Twitch — аналітика", "en": "Twitch analytics"},
    "connections.twitch_analytics_offline": {
        "uk": "Увімкніть Twitch зліва та виконайте OAuth, щоб збирати події й онлайн за цей сеанс.",
        "en": "Enable Twitch on the left and run OAuth to collect events and viewers for this session.",
    },
    "connections.twitch_analytics_viewers": {"uk": "Онлайн", "en": "Live viewers"},
    "connections.twitch_analytics_peak": {"uk": "Пік", "en": "Peak"},
    "connections.twitch_analytics_follows": {"uk": "Фолови (сеанс)", "en": "Follows (session)"},
    "connections.twitch_analytics_subs": {"uk": "Саби (сеанс)", "en": "Subs (session)"},
    "connections.twitch_analytics_bits": {"uk": "Біти (сеанс)", "en": "Bits (session)"},
    "connections.twitch_analytics_raids": {"uk": "Рейди (сеанс)", "en": "Raids (session)"},
    "connections.twitch_analytics_activity": {"uk": "Події", "en": "Events"},
    "connections.twitch_analytics_follow": {"uk": "зафоловив", "en": "followed"},
    "connections.twitch_analytics_sub": {"uk": "саб", "en": "sub"},
    "connections.twitch_analytics_cheer": {"uk": "біти", "en": "bits"},
    "connections.twitch_analytics_raid": {"uk": "рейд", "en": "raid"},
    # Connections — YouTube analytics
    "connections.youtube_analytics_title": {"uk": "YouTube — аналітика", "en": "YouTube analytics"},
    "connections.youtube_analytics_offline": {
        "uk": "Увімкніть YouTube зліва та виконайте OAuth, щоб збирати статистику за цей сеанс.",
        "en": "Enable YouTube on the left and run OAuth to collect stats for this session.",
    },
    "connections.youtube_analytics_viewers": {"uk": "Онлайн", "en": "Live viewers"},
    "connections.youtube_analytics_peak": {"uk": "Пік", "en": "Peak"},
    "connections.youtube_analytics_messages": {"uk": "Повідомлення", "en": "Messages"},
    "connections.youtube_analytics_unique": {"uk": "Унікальні", "en": "Unique chatters"},
    "connections.youtube_analytics_superchats": {"uk": "Суперчати", "en": "Super Chats"},
    "connections.youtube_analytics_memberships": {"uk": "Підписки", "en": "Memberships"},
    "connections.youtube_analytics_activity": {"uk": "Події", "en": "Events"},
    "connections.youtube_analytics_chat": {"uk": "чат", "en": "chat"},
    "connections.youtube_analytics_superchat": {"uk": "суперчат", "en": "super chat"},
    "connections.youtube_analytics_supersticker": {"uk": "стікер", "en": "sticker"},
    "connections.youtube_analytics_member": {"uk": "учасник", "en": "member"},
    "obs.test_ok": {
        "uk": "OBS: з’єднано, версія {version}",
        "en": "OBS: connected, version {version}",
    },
    "obs.test_fail": {"uk": "OBS: помилка — {detail}", "en": "OBS: error — {detail}"},
    # Settings — Telegram / Music
    "settings.telegram_group": {"uk": "Telegram", "en": "Telegram"},
    "settings.telegram_enabled": {"uk": "Увімкнути Telegram-бота", "en": "Enable Telegram bot"},
    "settings.telegram_token": {"uk": "Токен бота", "en": "Bot token"},
    "settings.telegram_admin_id": {"uk": "Admin id", "en": "Admin id"},
    "settings.telegram_song_requests": {
        "uk": "Увімкнути запити пісень",
        "en": "Enable song requests",
    },
    "settings.telegram_tiktok_lyrics_filter": {
        "uk": "Автоматична перевірка слів пісні перед TikTok Live",
        "en": "Automatically check song lyrics before TikTok Live",
    },
    "settings.telegram_genius_token": {
        "uk": "Токен для пошуку текстів пісень",
        "en": "Token for looking up song lyrics",
    },
    "settings.telegram_groq_api_key": {
        "uk": "Ключ для перевірки, чи трек пасує для ефіру",
        "en": "Key for checking whether a track fits the stream",
    },
    "settings.telegram_tiktok_filter_hint": {
        "uk": "Увімкни й заповни два поля нижче — тоді перед TikTok Live замовлення з Telegram "
        "перевірятимуться автоматично. Якщо поля порожні, перевірка не працюватиме. Якщо текст "
        "пісні не знайшли — трек усе одно можна додати без цієї перевірки. Ключі зберігаються на "
        "цьому комп’ютері, як у звичайних програмах.",
        "en": "Turn this on and fill in the two fields below — then Telegram song requests are "
        "checked automatically before TikTok Live. If they’re empty, nothing runs. If we can’t find "
        "lyrics, the song can still be added without this step. Your keys are stored on this "
        "computer, like in other apps.",
    },
    # Telegram bot — song request errors (viewer-facing: plain language, no tech jargon)
    "telegram.song.empty_link": {
        "uk": "Не вийшло додати: посилання виглядає криво. Кинь звичайне посилання на одне YouTube-відео.",
        "en": "Couldn’t add it: that link looks wrong. Paste a normal single-video YouTube link.",
    },
    "telegram.song.duration_unknown": {
        "uk": "Не вийшло додати: з цим роликом не зрозуміло, скільки він триває. Спробуй інше відео.",
        "en": "Couldn’t add it: we couldn’t read how long this video is. Try another one.",
    },
    "telegram.song.too_long": {
        "uk": "Не вийшло додати: ролик занадто довгий для цієї черги (у нас ~{mins} хв, а стрімер поставив максимум {limit} хв). Обери коротше.",
        "en": "Couldn’t add it: this one’s too long for this queue (about {mins} min; the streamer’s max is {limit} min). Pick something shorter.",
    },
    "telegram.song.tiktok_need_keys": {
        "uk": "Зараз стрімер не може приймати такі замовлення — у нього не дороблені налаштування перевірки. Напиши йому в чат.",
        "en": "The streamer can’t take this kind of request right now — their check setup isn’t finished. Message them in chat.",
    },
    "telegram.song.title_unknown": {
        "uk": "Не вийшло додати: не зрозуміло, що це за відео. Кинь інше посилання.",
        "en": "Couldn’t add it: we couldn’t tell what video this is. Try another link.",
    },
    "telegram.song.genius_unavailable": {
        "uk": "Не вийшло додати: не знайшли нормальний текст до цієї пісні. Обери інший трек або інше відео.",
        "en": "Couldn’t add it: we couldn’t find a usable lyric sheet for this one. Try another song/video.",
    },
    "telegram.song.check_unavailable": {
        "uk": "Не вийшло перевірити трек зараз. Спробуй ще раз за хвилину-дві.",
        "en": "We couldn’t run the check right now. Try again in a minute or two.",
    },
    "telegram.song.groq_busy": {
        "uk": "Зараз дуже багато замовлень — сервіс просить почекати. Спробуй через хвилину.",
        "en": "It’s really busy right now — please wait a bit and try again in a minute.",
    },
    "telegram.song.groq_service": {
        "uk": "Щось пішло не так під час перевірки. Спробуй пізніше або інший трек.",
        "en": "Something went wrong while checking the song. Try later, or pick another track.",
    },
    "telegram.song.moderating_line": {
        "uk": "ТРЕК МОДЕРУЄТЬСЯ…",
        "en": "CHECKING THE TRACK…",
    },
    "telegram.song.musicbrainz_russian_origin": {
        "uk": "Цей трек не додали: у каталогу виконавець пов’язаний з Росією. Обери інший.",
        "en": "We didn’t add this track: the performer is linked to Russia in the music catalog. "
        "Pick another one.",
    },
    "telegram.song.tiktok_soft_no": {
        "uk": "Цей трек не додали: за словами він так собі для стріму — можуть прилітати скарги чи різко обірвати ефір. Краще щось спокійніше.",
        "en": "We didn’t add this track: the lyrics aren’t a great fit for streaming — reports or a sudden takedown can happen. Pick something calmer.",
    },
    "telegram.song.tiktok_hard_no": {
        "uk": "Цей трек не додали: текст занадто жорсткий для ефіру, таке на стрім не ставимо. Обери інший.",
        "en": "We didn’t add this track: the lyrics are too heavy for a live stream — we won’t put that on air. Choose another one.",
    },
    "telegram.song.risky_sent_to_admin": {
        "uk": "Трек на межі правил перевірки - зачекай на рішення в цьому чаті.",
        "en": "This track is borderline for the safety check — Wait here for the decision.",
    },
    "telegram.song.points_link_required": {
        "uk": "Щоб замовляти пісні за бали, спочатку прив'яжи свій TikTok: у меню тисни "
        "«Прив'язати TikTok» (/link), отримай код і напиши його у чаті ефіру.",
        "en": "To order songs with points, first link your TikTok: tap “Link TikTok” (/link), "
        "get a code, and post it in the live chat.",
    },
    "telegram.link.verified": {
        "uk": "✅ Прив'язано TikTok: @{handle}. Тепер твоя активність на стрімі дає бали.",
        "en": "✅ TikTok linked: @{handle}. Your live activity now earns points.",
    },
    "telegram.song.points_insufficient": {
        "uk": "Не вистачає балів: у тебе <b>{balance}</b>, а пісня коштує <b>{cost}</b>.\n\n"
        "Як заробити на стрімі:\n"
        "• Подарунок — +{per_coin} за 1 монету\n"
        "• Лайки — +1 за {likes_per_point} лайків\n"
        "• Шер — +{per_share}\n"
        "• Підписка — +{per_follow} (раз за ефір)\n"
        "• Перегляд — +{watch_points} кожні {watch_interval} хв (потрібна активність у ефірі)",
        "en": "Not enough points: you have <b>{balance}</b>, a song costs <b>{cost}</b>.\n\n"
        "How to earn on the live:\n"
        "• Gift — +{per_coin} per coin\n"
        "• Likes — +1 per {likes_per_point} likes\n"
        "• Share — +{per_share}\n"
        "• Follow — +{per_follow} (once per stream)\n"
        "• Watch time — +{watch_points} every {watch_interval} min (stay active on the live)",
    },
    "telegram.points.earned": {
        "uk": "✨ +{delta} балів ({reasons})\nБаланс: <b>{balance}</b>",
        "en": "✨ +{delta} points ({reasons})\nBalance: <b>{balance}</b>",
    },
    "telegram.points.reason.gift": {"uk": "подарунок", "en": "gift"},
    "telegram.points.reason.like": {"uk": "лайки", "en": "likes"},
    "telegram.points.reason.share": {"uk": "шер", "en": "share"},
    "telegram.points.reason.follow": {"uk": "підписка", "en": "follow"},
    "telegram.points.reason.watch": {"uk": "перегляд", "en": "watch"},
    "telegram.points.reason.other": {"uk": "активність", "en": "activity"},
    "telegram.song.risky_approved": {
        "uk": "✅ Адмін додав трек у чергу: <code>{video_id}</code>",
        "en": "✅ The admin added your track to the queue: <code>{video_id}</code>",
    },
    "telegram.song.risky_rejected": {
        "uk": "Адмін не схвалив цей трек для черги. Спробуй інше відео.",
        "en": "The admin didn’t approve this track for the queue. Try another video.",
    },
    "telegram.admin.risky_track": {
        "uk": "⚠️ <b>Ризиковий трек</b> (перевірка)\n"
        "<b>Назва:</b> {title}\n"
        "<b>Відео:</b> <code>{video_id}</code>\n"
        "<b>Хто замовив:</b> {requested_by}\n"
        "<b>Оцінка ризику:</b> {risk_score}\n"
        "<b>Примітки:</b> {violations}",
        "en": "⚠️ <b>Risky track</b> (AI check)\n"
        "<b>Title:</b> {title}\n"
        "<b>Video:</b> <code>{video_id}</code>\n"
        "<b>Requested by:</b> {requested_by}\n"
        "<b>Risk score:</b> {risk_score}\n"
        "<b>Notes:</b> {violations}",
    },
    "telegram.admin.risky_already_done": {
        "uk": "Вже оброблено або застаріло.",
        "en": "Already handled or expired.",
    },
    "telegram.admin.risky_approved_answer": {
        "uk": "Додано в чергу.",
        "en": "Added to queue.",
    },
    "telegram.admin.risky_rejected_answer": {
        "uk": "Відхилено.",
        "en": "Rejected.",
    },
    "telegram.admin.risky_enqueue_failed": {
        "uk": "Не вдалося додати в чергу — спробуй ще раз.",
        "en": "Couldn’t add to the queue — try again.",
    },
    "settings.points_enabled": {
        "uk": "Бали за пісні (замовлення в Telegram коштують бали)",
        "en": "Points for songs (Telegram orders cost points)",
    },
    "settings.points_configure": {
        "uk": "Налаштувати бали…",
        "en": "Configure points…",
    },
    "settings.points_hint": {
        "uk": "Глядачі заробляють бали на TikTok-стрімі і витрачають їх на замовлення пісень "
        "через Telegram. Прив'язка TikTok — код у чаті ефіру (/link у боті).",
        "en": "Viewers earn points on the TikTok live and spend them on song requests via "
        "Telegram. TikTok linking uses a one-time code in live chat (/link in the bot).",
    },
    "settings.points_dialog_title": {
        "uk": "Налаштування балів",
        "en": "Points settings",
    },
    "settings.points_dialog_intro": {
        "uk": "Задай ціну пісні, курс подарунків і скільки балів дає кожна дія на стрімі. "
        "Лімітів за ефір немає — глядач заробляє, поки активний.",
        "en": "Set song price, gift conversion, and how many points each action earns. "
        "There are no per-stream caps — viewers keep earning while they stay active.",
    },
    "settings.points_dialog_hint": {
        "uk": "Баланс накопичується між стрімами. Підписка — раз за ефір і не частіше "
        "раз на 24 год; шери — не частіше раз на 5 хв. Після збереження Telegram-бот "
        "перезапуститься.",
        "en": "Balance carries over between streams. Follow awards once per stream and at "
        "most once per 24 h; shares at most once per 5 min. The Telegram bot restarts "
        "after you save.",
    },
    "settings.points_dialog_ok": {"uk": "Зберегти", "en": "Save"},
    "settings.points_dialog_cancel": {"uk": "Скасувати", "en": "Cancel"},
    "settings.points_group_general": {"uk": "Загальне", "en": "General"},
    "settings.points_group_likes": {"uk": "Лайки", "en": "Likes"},
    "settings.points_group_shares": {"uk": "Шери", "en": "Shares"},
    "settings.points_group_follow": {"uk": "Підписка", "en": "Follow"},
    "settings.points_group_watch": {"uk": "Перегляд стріму", "en": "Watch time"},
    "settings.points_song_cost": {
        "uk": "Ціна пісні (балів)",
        "en": "Song price (points)",
    },
    "settings.points_per_coin": {
        "uk": "Балів за 1 монету подарунка",
        "en": "Points per gift coin",
    },
    "settings.points_likes_per_point": {
        "uk": "Лайків на 1 бал",
        "en": "Likes per 1 point",
    },
    "settings.points_per_share": {
        "uk": "Балів за один шер",
        "en": "Points per share",
    },
    "settings.points_per_follow": {
        "uk": "Балів за підписку",
        "en": "Points per follow",
    },
    "settings.points_watch_per_interval": {
        "uk": "Балів за інтервал перегляду",
        "en": "Points per watch interval",
    },
    "settings.points_watch_interval_min": {
        "uk": "Інтервал перегляду (хв)",
        "en": "Watch interval (min)",
    },
    "settings.music_group": {"uk": "Музика", "en": "Music"},
    "settings.music_open_in_mpv": {
        "uk": "Відкривати в mpv (замість програвання в додатку)",
        "en": "Open in mpv (instead of playing in app)",
    },
    "settings.music_backend_hint": {
        "uk": "Потрібно встановити mpv і додати його в PATH. Якщо вимкнено — трек грає в самій програмі (yt-dlp + ffmpeg).",
        "en": "mpv must be installed and available in PATH. If disabled, the track plays inside the app (yt-dlp + ffmpeg).",
    },
    "settings.music_max_duration": {
        "uk": "Макс. тривалість (хв)",
        "en": "Max duration (min)",
    },
    "settings.music_max_duration_hint": {
        "uk": "0 = без ліміту. Якщо тривалість невідома (live/премʼєра) — посилання буде відхилено.",
        "en": "0 = no limit. If duration is unknown (live/premiere) the link will be rejected.",
    },
    "settings.music_check_mpv": {"uk": "Перевірити mpv", "en": "Check mpv"},
    # Music page
    "music.title": {"uk": "Музика", "en": "Music"},
    "music.play_pause": {"uk": "Пауза/Відтворити", "en": "Play/Pause"},
    "music.next": {"uk": "Далі", "en": "Next"},
    "music.volume": {"uk": "Гучність", "en": "Volume"},
    # Platform actions
    "actions.btn": {"uk": "Дії", "en": "Actions"},
    "actions.title": {"uk": "Дії", "en": "Actions"},
    "actions.window_title": {"uk": "Дії — Stream Cheremsha", "en": "Actions — Stream Cheremsha"},
    "actions.add_rule": {"uk": "+ Додати правило", "en": "+ Add rule"},
    "actions.add_folder": {"uk": "+ Папка", "en": "+ Folder"},
    "actions.folder_default_name": {"uk": "Нова папка", "en": "New folder"},
    "actions.folder_delete": {"uk": "Видалити папку", "en": "Delete folder"},
    "actions.drag_handle_tt": {"uk": "Перетягнути", "en": "Drag to reorder"},
    "actions.save": {"uk": "Зберегти", "en": "Save"},
    "actions.saved": {"uk": "Збережено", "en": "Saved"},
    "actions.close": {"uk": "Закрити", "en": "Close"},
    "actions.rule_name": {"uk": "Назва", "en": "Name"},
    "actions.rule_name_ph": {"uk": "наприклад: Троянда → OBS", "en": "e.g. Rose → OBS"},
    "actions.rule_chat_brief": {"uk": "Чат", "en": "Chat"},
    "actions.rule_gift_brief": {"uk": "Подарунок", "en": "Gift"},
    "actions.rule_no_actions": {"uk": "немає дій", "en": "no actions"},
    "actions.delete": {"uk": "Видалити", "en": "Delete"},
    "actions.duplicate_btn": {"uk": "Копія", "en": "Copy"},
    "actions.rule_preview_tt": {
        "uk": "Перевірити правило (прев'ю дій)",
        "en": "Test this rule (preview actions)",
    },
    "actions.rule_name_copy_suffix": {"uk": " (копія)", "en": " (copy)"},
    "actions.placeholders_hint_file": {
        "uk": "Плейсхолдери (в тексті й у шляху файла): giftcount, giftname, …",
        "en": "Placeholders (in text and file path): giftcount, giftname, …",
    },
    "actions.edit": {"uk": "Редагування", "en": "Edit"},
    "actions.pick_rule_hint": {"uk": "Оберіть правило зліва.", "en": "Pick a rule on the left."},
    "actions.trigger_platform_label": {"uk": "Платформа тригера", "en": "Trigger platform"},
    "actions.trigger_kind_label": {"uk": "Тип події", "en": "Event type"},
    "actions.trigger_platform_all": {"uk": "Усі платформи", "en": "All platforms"},
    "actions.trigger_platform_tiktok": {"uk": "TikTok", "en": "TikTok"},
    "actions.trigger_platform_twitch": {"uk": "Twitch", "en": "Twitch"},
    "actions.trigger_platform_youtube": {"uk": "YouTube", "en": "YouTube"},
    "actions.event.chat_keyword": {"uk": "Певне слово в чаті", "en": "Chat keyword"},
    "actions.event.gift_received": {"uk": "Певний подарунок", "en": "Gift received"},
    "actions.event.tiktok_any_gift_received": {
        "uk": "Будь-який подарунок (за ціною)",
        "en": "Any gift (by price)",
    },
    "actions.event.tiktok_likes_received": {
        "uk": "Отримані лайки TikTok",
        "en": "TikTok likes received",
    },
    "actions.event.tiktok_joined": {"uk": "Приєднався", "en": "Joined"},
    "actions.event.tiktok_followed": {"uk": "Підписався", "en": "Followed"},
    "actions.event.tiktok_shared": {"uk": "Пошерив", "en": "Shared"},
    "actions.event.tiktok_paid_subscribed": {"uk": "Платний саб", "en": "Paid sub"},
    "actions.event.tiktok_first_activity": {"uk": "Перша активність", "en": "First activity"},
    "actions.event.twitch_follow": {"uk": "Фоллов (Twitch)", "en": "Follow (Twitch)"},
    "actions.event.twitch_subscribe": {
        "uk": "Нова підписка (Twitch)",
        "en": "New subscription (Twitch)",
    },
    "actions.event.twitch_resub": {
        "uk": "Продовження підписки / повідомлення (Twitch)",
        "en": "Resub / sub message (Twitch)",
    },
    "actions.event.twitch_sub_gift": {
        "uk": "Подарована підписка (Twitch)",
        "en": "Gift sub (Twitch)",
    },
    "actions.event.twitch_cheer": {"uk": "Біти / cheer (Twitch)", "en": "Bits / cheer (Twitch)"},
    "actions.event.twitch_raid": {"uk": "Рейд (Twitch)", "en": "Raid (Twitch)"},
    "actions.event.youtube_superchat": {
        "uk": "Super Chat (YouTube)",
        "en": "Super Chat (YouTube)",
    },
    "actions.event.youtube_supersticker": {
        "uk": "Super Sticker (YouTube)",
        "en": "Super Sticker (YouTube)",
    },
    "actions.event.youtube_member": {
        "uk": "Новий учасник (YouTube)",
        "en": "New member (YouTube)",
    },
    "actions.twitch_min_bits": {"uk": "Мін. бітів", "en": "Min bits"},
    "actions.twitch_min_viewers": {"uk": "Мін. глядачів у рейді", "en": "Min raid viewers"},
    "actions.twitch_raider_filter": {
        "uk": "Канал рейдера (опційно)",
        "en": "Raider channel (optional)",
    },
    "actions.youtube_min_amount": {
        "uk": "Мін. сума доната",
        "en": "Min donation amount",
    },
    "actions.likes_min_count": {
        "uk": "Кількість лайків для спрацювання",
        "en": "Like count to trigger",
    },
    "actions.likes_scope_label": {"uk": "Рахувати", "en": "Count"},
    "actions.likes_scope_all": {
        "uk": "Усі глядачі (сума за стрім)",
        "en": "All viewers (stream total)",
    },
    "actions.likes_scope_user_stream": {
        "uk": "Будь-який глядач (його сума за стрім)",
        "en": "Any viewer (their total this stream)",
    },
    "actions.likes_scope_user_combo": {
        "uk": "Один глядач (одне натискання / комбо)",
        "en": "One viewer (single tap combo)",
    },
    "actions.likes_scope_user_every_n": {
        "uk": "Один глядач (кожні N його лайків за стрім)",
        "en": "One viewer (every N likes from them this stream)",
    },
    "actions.likes_user_label": {
        "uk": "Ім'я глядача (як у TikTok), необов'язково",
        "en": "Viewer name as in TikTok (optional)",
    },
    "actions.likes_user_ph": {"uk": "нікнейм…", "en": "nickname…"},
    "actions.rule_likes_brief": {"uk": "Лайки", "en": "Likes"},
    "actions.triggers": {"uk": "Тригери", "en": "Triggers"},
    "actions.trigger_or_sep": {"uk": " або ", "en": " | "},
    "actions.keyword": {"uk": "Слово", "en": "Keyword"},
    "actions.keyword_ph": {"uk": "наприклад: привіт", "en": "e.g. hello"},
    "actions.gift_name": {"uk": "Назва подарунка", "en": "Gift name"},
    "actions.gift_name_ph": {"uk": "наприклад: Rose", "en": "e.g. Rose"},
    "actions.gift_pick": {"uk": "Подарунок", "en": "Gift"},
    "actions.min_count": {"uk": "Мін. кількість", "en": "Min count"},
    "actions.min_price": {"uk": "Мін. ціна (🪙)", "en": "Min price (🪙)"},
    "actions.exclude_gifts": {
        "uk": "Виключити подарунки (не спрацьовувати)",
        "en": "Exclude gifts (do not fire)",
    },
    "actions.exclude_gifts_ph": {
        "uk": "Оберіть подарунок або введіть назву/ID…",
        "en": "Select a gift or type a name/id…",
    },
    "actions.user_filter": {"uk": "Користувач (необов'язково)", "en": "User (optional)"},
    "actions.user_filter_ph": {"uk": "нікнейм…", "en": "nickname…"},
    "actions.actions": {"uk": "Дії", "en": "Actions"},
    "actions.play_sound": {"uk": "Програти звук", "en": "Play sound"},
    "actions.play_random_myinstants_ua": {
        "uk": "Випадковий MyInstants UA",
        "en": "Random MyInstants UA",
    },
    "actions.pick_mp3": {"uk": "Оберіть .mp3…", "en": "Pick .mp3…"},
    "actions.play_sound_volume": {"uk": "Гучність (%)", "en": "Volume (%)"},
    "actions.play_sound_skip_if_same_playing": {
        "uk": "Грати тільки один раз унікально (не додавати в чергу, якщо цей файл уже грає або чекає)",
        "en": "Play uniquely — skip if this file is already playing or queued",
    },
    "actions.play_immediately": {
        "uk": "Грати негайно (без черги)",
        "en": "Play immediately (ignore queue)",
    },
    "actions.respect_gift_combo": {
        "uk": "Враховувати комбо подарунків (повторити дію N разів)",
        "en": "Respect gift combo count (repeat N times)",
    },
    "actions.max_duration_seconds": {"uk": "Макс. тривалість (сек)", "en": "Max duration (sec)"},
    "actions.myinstants_max_page": {"uk": "Макс. сторінка", "en": "Max page"},
    "actions.myinstants_skip_words": {"uk": "Фільтр слів", "en": "Word filter"},
    "actions.myinstants_skip_words_ph": {
        "uk": "через кому: сирена, рингтон…",
        "en": "comma-separated: siren, ringtone…",
    },
    "actions.write_file": {"uk": "Запис у файл", "en": "Write to file"},
    "actions.write_mode": {"uk": "Режим запису", "en": "Write mode"},
    "actions.write_mode_overwrite": {"uk": "Перезаписати", "en": "Overwrite"},
    "actions.write_mode_append": {"uk": "Дописати в кінець", "en": "Append"},
    "actions.speak_tts": {"uk": "Озвучити текст (TTS)", "en": "Speak text (TTS)"},
    "actions.speak_tts_text": {"uk": "Текст для озвучення", "en": "Text to speak"},
    "actions.speak_tts_text_ph": {
        "uk": "фраза або з плейсхолдерами…",
        "en": "phrase or with placeholders…",
    },
    "actions.run_program": {"uk": "Запустити програму", "en": "Run program"},
    "actions.simulate_keystrokes": {
        "uk": "Симуляція натискання клавіш",
        "en": "Simulate keystrokes",
    },
    "actions.keystrokes_sequence_label": {
        "uk": "Послідовність (текст і теги {ENTER}, {F7}…)",
        "en": "Sequence (text and tags like {ENTER}, {F7}…)",
    },
    "actions.keystrokes_sequence_ph": {
        "uk": "наприклад: {END}{F7} або привіт {username}",
        "en": "e.g. {END}{F7} or hi {username}",
    },
    "actions.keystrokes_insert_hint": {
        "uk": "Вставка тегів у позицію курсора",
        "en": "Insert tags at the text cursor",
    },
    "actions.keystrokes_tab_nav": {"uk": "Навігація", "en": "Navigation"},
    "actions.keystrokes_tab_editing": {"uk": "Редагування", "en": "Editing"},
    "actions.keystrokes_tab_fn": {"uk": "F-клавіші", "en": "Function keys"},
    "actions.keystrokes_tab_mouse": {"uk": "Миша", "en": "Mouse"},
    "actions.keystrokes_modifiers": {
        "uk": "Модифікатори (лише для тегів {…})",
        "en": "Modifiers (for {…} tags only)",
    },
    "actions.keystrokes_advanced": {"uk": "Додатково", "en": "Advanced"},
    "actions.keystrokes_game_mode": {
        "uk": "Скан-коди для тегів {F1}, {ENTER}… (частіше потрібно в іграх; літери x, A… — завжди фізично)",
        "en": "Scan codes for {F1}, {ENTER}, … tags (often needed in games; letters x, A… are always physical on Windows)",
    },
    "actions.keystrokes_interception": {
        "uk": "Драйвер Interception (низькорівневий ввід для ігор)",
        "en": "Interception driver (low-level input for games)",
    },
    "actions.keystrokes_interception_hint": {
        "uk": (
            "Потрібен драйвер oblitum Interception. Після встановлення драйвера — перезавантаження ПК. "
            "Якщо натискань не видно: вимкни цей режим і перевір звичайну симуляцію без Interception. "
            "Після оновлення застосунку зроби повний перезапуск програми (прив’язка Interception "
            "робиться один раз при старті). "
            "Текст у дії відповідає розкладці вікна з фокусом (гра), а не фонового потоку застосунку."
        ),
        "en": (
            "Requires the oblitum Interception driver. Reboot after installing the driver. "
            "If nothing happens on screen: turn this off and try normal simulation without Interception. "
            "After an app update, fully restart the program (Interception binds once at startup). "
            "Typed text follows the focused window's keyboard layout (the game), not a background thread."
        ),
    },
    "actions.keystrokes_hold_ms": {
        "uk": "Тривалість утримання клавіші (мс)",
        "en": "Key hold duration (ms)",
    },
    "actions.keystrokes_left_click": {"uk": "Лівий клік", "en": "Left click"},
    "actions.keystrokes_right_click": {"uk": "Правий клік", "en": "Right click"},
    "actions.keystrokes_admin_hint": {
        "uk": (
            "Символи потрапляють у вікно з фокусом клавіатури (клацни в Блокнот і знову "
            "запусти правило). Windows: за потреби — від адміністратора. macOS: доступність "
            "(Accessibility) для застосунку. Linux: зазвичай X11; Wayland може блокувати "
            "синтетичний ввід."
        ),
        "en": (
            "Characters go to the window that has keyboard focus (click in Notepad, then fire "
            "the rule again). Windows: run as Administrator if needed. macOS: grant Accessibility "
            "to the app. Linux: typically X11; Wayland may block synthetic input."
        ),
    },
    "actions.keystrokes_placeholders_hint": {
        "uk": "Плейсхолдери: sender, username, giftname, giftcount, likecount, totallikecount, comment, submonth, platform…",
        "en": "Placeholders: sender, username, giftname, giftcount, likecount, totallikecount, comment, submonth, platform…",
    },
    "actions.pick_program": {"uk": "Оберіть виконуваний файл…", "en": "Pick executable…"},
    "actions.program_args": {"uk": "Параметри командного рядка", "en": "Command-line arguments"},
    "actions.program_args_ph": {"uk": "наприклад: --foo bar", "en": "e.g. --foo bar"},
    "actions.placeholders_hint": {
        "uk": (
            "У фігурних дужках, напр. {giftcount}, {giftname}, {likebatch}, {liketotal}. "
            "Подарунок: gift_id, sender, platform. Лайки TikTok: sender, likebatch, liketotal. "
            "Чат: author, text, platform."
        ),
        "en": (
            "Use braces, e.g. {giftcount}, {giftname}, {likebatch}, {liketotal}. "
            "Gift: gift_id, sender, platform. TikTok likes: sender, likebatch, liketotal. "
            "Chat: author, text, platform."
        ),
    },
    "actions.pick_file": {"uk": "Оберіть файл…", "en": "Pick file…"},
    "actions.write_text": {"uk": "Текст", "en": "Text"},
    "actions.write_text_ph": {"uk": "що записати…", "en": "text to append…"},
    "actions.browse": {"uk": "Огляд…", "en": "Browse…"},
    "actions.clear": {"uk": "Очистити", "en": "Clear"},
    "actions.add_action": {"uk": "+ Додати дію", "en": "+ Add action"},
    "actions.show_overlay": {"uk": "Показати в оверлеї Actions", "en": "Show on Actions overlay"},
    "actions.show_overlay_text": {"uk": "Текст", "en": "Text"},
    "actions.show_overlay_text_ph": {
        "uk": "наприклад: {sender} подарував {giftname} x{giftcount}",
        "en": "e.g. {sender} sent {giftname} x{giftcount}",
    },
    "actions.show_overlay_seconds": {"uk": "Секунди", "en": "Seconds"},
    "actions.obs_scene": {"uk": "OBS: сцена / видимість", "en": "OBS: scene / visibility"},
    "actions.obs_mode": {"uk": "Режим", "en": "Mode"},
    "actions.obs_mode_program": {
        "uk": "Перемкнути сцену програми (ефір)",
        "en": "Switch program scene (live)",
    },
    "actions.obs_mode_source": {
        "uk": "Показати/сховати джерело у сцені",
        "en": "Show/hide source in scene",
    },
    "actions.obs_scene_name": {"uk": "Назва сцени", "en": "Scene name"},
    "actions.obs_scene_name_ph": {"uk": "наприклад: Game", "en": "e.g. Game"},
    "actions.obs_source_name": {
        "uk": "Назва джерела (у списку сцени)",
        "en": "Source name (in scene list)",
    },
    "actions.obs_source_name_ph": {"uk": "наприклад: Alert", "en": "e.g. Alert"},
    "actions.obs_visible": {"uk": "Видимо", "en": "Visible"},
    "actions.obs_canvas": {"uk": "Полотно (canvas)", "en": "Canvas"},
    "actions.obs_canvas_default": {"uk": "Головне полотно", "en": "Main canvas"},
    "actions.obs_refresh_from_obs": {"uk": "Оновити списки з OBS", "en": "Refresh lists from OBS"},
    "actions.obs_scene_pick": {"uk": "Сцена з OBS", "en": "Scene from OBS"},
    "actions.obs_source_pick": {"uk": "Джерело з OBS", "en": "Source from OBS"},
    "actions.obs_manual_names_hint": {
        "uk": "Нижче можна ввести назви вручну (підтримуються плейсхолдери).",
        "en": "You can still type names below (placeholders supported).",
    },
    "actions.obs_revert_checkbox": {
        "uk": "Повернути попередній стан видимості (як до дії)",
        "en": "Revert visibility to how it was before",
    },
    "actions.obs_revert_after": {"uk": "Через", "en": "After"},
    "actions.obs_revert_seconds_suffix": {"uk": "с", "en": "s"},
    "actions.obs_revert_seconds_hint": {
        "uk": "Після затримки OBS отримає протилежний стан (як до дії). Лише для режиму «джерело у сцені».",
        "en": "After the delay, OBS applies the opposite visibility (as before the action). Source-in-scene mode only.",
    },
    "ui.nav_chat": {"uk": "Чат", "en": "Chat"},
    "ui.nav_tts": {"uk": "TTS", "en": "TTS"},
    "ui.nav_chat_hint": {"uk": "Відкрити чат", "en": "Open chat"},
    "ui.nav_tts_hint": {"uk": "Відкрити озвучення (TTS)", "en": "Open TTS / audio output"},
    "ui.open_settings": {"uk": "Налаштування", "en": "Settings"},
    "ui.open_settings_hint": {"uk": "Мова, автозапуск, TTS", "en": "Language, autostart, TTS"},
    "ui.nav_logs": {"uk": "Логи", "en": "Logs"},
    "ui.nav_logs_hint": {"uk": "Відкрити технічні логи", "en": "Open technical logs"},
    "ui.back_home_hint": {
        "uk": "Повернутися до зв'язків (головна)",
        "en": "Back to connections (home)",
    },
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
    "ui.nav_actions": {"uk": "Дії", "en": "Actions"},
    "ui.nav_actions_hint": {
        "uk": "Правила за подіями TikTok: подарунки, чат, лайки…",
        "en": "TikTok event rules: gifts, chat, likes…",
    },
    "ui.nav_widgets": {"uk": "Віджети", "en": "Widgets"},
    "ui.nav_widgets_hint": {
        "uk": "Налаштування віджетів (оверлеї, URL для OBS)",
        "en": "Widget settings (overlays, OBS URLs)",
    },
    "battle.winner_music_toast": {
        "uk": "BATTLE ROYALE: переможець {user} — може замовити 1 трек у Telegram /music",
        "en": "BATTLE ROYALE: winner {user} — may request 1 track via Telegram /music",
    },
    "battle.auto_started": {
        "uk": "BATTLE ROYALE: авто-старт — {fighters}",
        "en": "BATTLE ROYALE: auto-start — {fighters}",
    },
    "battle.manual_started": {
        "uk": "BATTLE ROYALE: бій почався — {fighters}",
        "en": "BATTLE ROYALE: battle started — {fighters}",
    },
    "battle.start_failed": {
        "uk": "BATTLE ROYALE: не вдалося стартувати (потрібно мінімум 2 різних бійці)",
        "en": "BATTLE ROYALE: could not start (need at least 2 distinct fighters)",
    },
    "battle.need_second_viewer": {
        "uk": "BATTLE ROYALE: очікуємо 2-го глядача з гіфтом ≥ {threshold} (зараз кваліфіковано: {count})",
        "en": "BATTLE ROYALE: waiting for a 2nd viewer with gift ≥ {threshold} (qualified: {count})",
    },
    "ui.nav_docks": {"uk": "Доки", "en": "Docks"},
    "ui.nav_docks_hint": {
        "uk": "Док-панелі для OBS (URL, мультичат)",
        "en": "OBS dock panels (URLs, multichat)",
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
    "settings.general_group": {"uk": "Загальне", "en": "General"},
    "settings.autostart_twitch": {
        "uk": "Автозапуск Twitch при старті додатку (потрібен вхід у Twitch і канал)",
        "en": "Auto-start Twitch on launch (requires Twitch sign-in and channel)",
    },
    "settings.autostart_youtube": {
        "uk": "Автозапуск YouTube при старті додатку (потрібен вхід у Google)",
        "en": "Auto-start YouTube on launch (requires Google sign-in)",
    },
    "settings.autostart_tiktok": {
        "uk": "Автозапуск TikTok при старті додатку (потрібен юзернейм на вкладці «Зв'язки»)",
        "en": "Auto-start TikTok on launch (requires username on Connections)",
    },
    "settings.obs_group": {"uk": "OBS WebSocket", "en": "OBS WebSocket"},
    "settings.obs_enabled": {
        "uk": "Увімкнути з’єднання з OBS (WebSocket)",
        "en": "Enable OBS WebSocket connection",
    },
    "settings.obs_picker_disabled": {
        "uk": "З’єднання з OBS вимкнено в налаштуваннях.",
        "en": "OBS connection is disabled in Settings.",
    },
    "settings.obs_test_when_disabled": {
        "uk": "Увімкніть «Увімкнути з’єднання з OBS (WebSocket)» вище, щоб перевірити WebSocket.",
        "en": "Turn on «Enable OBS WebSocket connection» above to test.",
    },
    "settings.obs_help_html": {
        "uk": (
            "Для дій «OBS» (перемикання сцени програми, видимість джерел).<br>"
            "Пароль той самий, що в OBS: <b>Налаштування</b> → <b>Мережа</b> → <b>OBS WebSocket</b>.<br>"
            '<a href="https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md">'
            "Протокол obs-websocket</a>."
        ),
        "en": (
            "For Actions (program scene, source visibility).<br>"
            "Use the same password as in OBS: <b>Settings</b> → <b>Network</b> → <b>OBS WebSocket</b>.<br>"
            '<a href="https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md">'
            "obs-websocket protocol</a>."
        ),
    },
    "settings.obs_host": {"uk": "Хост", "en": "Host"},
    "settings.obs_port": {"uk": "Порт", "en": "Port"},
    "settings.obs_password": {"uk": "Пароль WebSocket", "en": "WebSocket password"},
    "settings.obs_test": {"uk": "Перевірити з’єднання з OBS", "en": "Test OBS connection"},
    "settings.obs_test_busy": {"uk": "Перевірка…", "en": "Testing…"},
    "settings.obs_test_hint": {
        "uk": "Результат з’явиться тут і у вікні повідомлення.",
        "en": "The result appears here and in a message box.",
    },
    # Connections — TikTok
    "tk.username": {"uk": "Юзернейм", "en": "Username"},
    "tk.username_ph": {"uk": "нікнейм без @", "en": "username without @"},
    # TikTok source
    "tk.connecting": {
        "uk": "TikTok: підключення до @{user}…",
        "en": "TikTok: connecting to @{user}…",
    },
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
    "tk.bad_username": {
        "uk": "TikTok: введіть юзернейм (нік) стрімера",
        "en": "TikTok: enter the streamer username",
    },
    # Audio / TTS
    "audio.flush_queues": {
        "uk": "Зупинити озвучення (очистити черги)",
        "en": "Stop speech (clear queues)",
    },
    "audio.flush_queues_hint": {
        "uk": "Скинути відкладені фрази TTS та зупинити поточне відтворення, якщо зависло/накопичилось.",
        "en": "Drop pending TTS phrases and stop current playback if it got stuck or queued up.",
    },
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
    "tw.token_placeholder": {
        "uk": "Або вставте access token вручну",
        "en": "Or paste an access token manually",
    },
    "tw.token_manual": {"uk": "Токен вручну", "en": "Manual token"},
    "tw.save_app": {"uk": "Зберегти дані застосунку", "en": "Save application credentials"},
    "tw.client_id_env_required": {
        "uk": "Ця збірка очікує Client ID через змінну середовища: <code>{env}</code>",
        "en": "This build expects Client ID via environment variable: <code>{env}</code>",
    },
    "tw.logout": {"uk": "Вийти з Twitch", "en": "Sign out of Twitch"},
    "tw.channel": {"uk": "Канал чату", "en": "Chat channel"},
    "tw.channel_ph": {"uk": "логін каналу без #", "en": "channel login without #"},
    "tw.connected_as": {
        "uk": "Підключено до Twitch як @{login}",
        "en": "Connected to Twitch as @{login}",
    },
    "tw.connected_oauth": {
        "uk": "Підключено до Twitch (OAuth).",
        "en": "Connected to Twitch (OAuth).",
    },
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
    "yt.forget_json": {
        "uk": "Забути збережений JSON клієнта Google…",
        "en": "Forget saved Google client JSON…",
    },
    "yt.connected_default": {
        "uk": "Обліковий запис Google підключено для YouTube.",
        "en": "Google account linked for YouTube.",
    },
    "yt.logout": {"uk": "Вийти з Google (YouTube)", "en": "Sign out of Google (YouTube)"},
    "yt.video_ph": {
        "uk": "Порожньо — знайти всі ваші активні ефіри; або URL / ID одного live-відео",
        "en": "Empty — discover all your live streams; or one live video URL / ID",
    },
    "yt.video_label": {
        "uk": "URL або ID відео (необов'язково)",
        "en": "Video URL or ID (optional)",
    },
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
    "audio.tts_engine_google": {
        "uk": "Google Translate (мережа)",
        "en": "Google Translate (online)",
    },
    "audio.tts_engine_edge": {"uk": "Edge TTS (мережа)", "en": "Edge TTS (online)"},
    "audio.edge_voice_group": {"uk": "Edge — голос", "en": "Edge — voice"},
    "audio.edge_voice_label": {"uk": "Голос", "en": "Voice"},
    "audio.tts_language": {"uk": "Мова озвучення (TTS)", "en": "Speech language (TTS)"},
    "tts_lang.uk_UA": {"uk": "Українська (uk-UA)", "en": "Ukrainian (uk-UA)"},
    "tts_lang.en_US": {"uk": "English US (en-US)", "en": "English US (en-US)"},
    "tts_lang.en_GB": {"uk": "English UK (en-GB)", "en": "English UK (en-GB)"},
    "tts_lang.de_DE": {"uk": "Німецька (de-DE)", "en": "German (de-DE)"},
    "tts_lang.pl_PL": {"uk": "Польська (pl-PL)", "en": "Polish (pl-PL)"},
    "audio.volume": {"uk": "Гучність", "en": "Volume"},
    "audio.volume_tip": {
        "uk": "Гучність виходу програми (колонки / гарнітура).",
        "en": "App output level (speakers/headset).",
    },
    "audio.tts_rate": {"uk": "Швидкість вимови", "en": "Speech rate"},
    "audio.tts_rate_tip": {
        "uk": "Швидкість озвучення голосу: 100% — звичайна, нижче — повільніше, вище — швидше "
        "(50–200%). Працює для Edge (нативно) і Google (через ffmpeg). Зберігається між запусками.",
        "en": "Voice playback speed: 100% is normal, lower is slower, higher is faster "
        "(50–200%). Works for Edge (native) and Google (via ffmpeg). Persisted between runs.",
    },
    "audio.tts_gain": {"uk": "Підсилення TTS (ffmpeg)", "en": "TTS gain (ffmpeg)"},
    "audio.tts_gain_tip": {
        "uk": "Базове підсилення TTS у ffmpeg (volume + dynaudnorm / loudnorm). "
        "Зберігається між запусками.",
        "en": "Base TTS gain in ffmpeg (volume + dynaudnorm / loudnorm). Persisted between runs.",
    },
    "audio.tts_hint": {
        "uk": "Google: часто тихий — підніміть гучність; ffmpeg підсилює перед відтворенням "
        "(MP3 або WAV). "
        "Для фонемізації в системі зазвичай потрібен espeak-ng. "
        "У «Логах» після тесту — «TTS: ffmpeg ok» або попередження.",
        "en": "Google: often quiet — raise volume; ffmpeg boosts before playback (MP3 or WAV). "
        "espeak-ng is usually required on the system for phonemization. "
        "After a test, Logs shows «TTS: ffmpeg ok» or a warning.",
    },
    "audio.test": {"uk": "Тест", "en": "Test"},
    "audio.test_phrase_default": {"uk": "Привіт, це тест.", "en": "Hello, this is a test."},
    "audio.speak_test": {"uk": "Відтворити тестову фразу", "en": "Speak test phrase"},
    "audio.card_test_header": {"uk": "Тест озвучення", "en": "TTS test"},
    "audio.card_tts_title": {"uk": "Мова та рушій TTS", "en": "TTS language & engine"},
    "audio.openai_moderate": {
        "uk": "Перевіряти текст через OpenAI Moderation",
        "en": "Validate text with OpenAI Moderation",
    },
    "audio.openai_moderate_hint": {
        "uk": "Перед озвученням текст надсилається в OpenAI; якщо вміст порушує політики — "
        "замість оригіналу озвучується коротке повідомлення з іменем автора.",
        "en": "Before speaking, text is sent to OpenAI; if it violates policies, a short "
        "replacement message with the author name is spoken instead of the original.",
    },
    "audio.speak_author_name": {
        "uk": "Озвучувати ім’я автора (чат)",
        "en": "Speak author name (chat)",
    },
    "audio.speak_author_name_hint": {
        "uk": "Перед текстом повідомлення з чату озвучується, хто його написав (формулювання "
        "залежить від обраної мови TTS). Для оголошень донатів не додається.",
        "en": "Before each chat message, the speaker name is announced (phrasing follows the "
        "selected TTS language). Not added for donation announcements.",
    },
    "audio.strip_non_alpha": {
        "uk": "Не озвучувати символи та емодзі",
        "en": "Do not speak symbols and emoji",
    },
    "audio.strip_non_alpha_hint": {
        "uk": "Залишаються лише літери та цифри; розділові знаки, емодзі, назви емодзі в "
        "дужках ([heart]) та інші символи прибираються. Текст заміни після модерації OpenAI не змінюється.",
        "en": "Only letters and digits are kept; punctuation, emoji, bracketed emote names "
        "([heart]), and other symbols are removed. OpenAI moderation replacement lines are left unchanged.",
    },
    "audio.card_levels_title": {"uk": "Вихід і рівні", "en": "Output & levels"},
    "settings.ai_shield_group": {"uk": "AI Shield", "en": "AI Shield"},
    "settings.ai_shield_section_tts": {
        "uk": "Чат і голос (TTS)",
        "en": "Chat & voice (TTS)",
    },
    "settings.ai_shield_section_songs": {
        "uk": "Замовлення пісень (Telegram)",
        "en": "Song requests (Telegram)",
    },
    "settings.openai_api_key": {"uk": "API-ключ", "en": "API key"},
    "settings.openai_api_key_hint": {
        "uk": "Для Moderation API (platform.openai.com). Зберігається в системному keyring.",
        "en": "For the Moderation API (platform.openai.com). Stored in the OS keyring.",
    },
    "openai.moderation_no_api_key": {
        "uk": "OpenAI: увімкнено перевірку TTS, але не задано API-ключ (Налаштування → AI Shield).",
        "en": "OpenAI: TTS validation is on but no API key is set (Settings → AI Shield).",
    },
    "openai.moderation_error": {
        "uk": "OpenAI Moderation: {err}",
        "en": "OpenAI Moderation: {err}",
    },
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
    # Main-window status messages (exact match routing uses all locales)
    "status.logout_twitch": {"uk": "Вийшли з Twitch.", "en": "Signed out of Twitch."},
    "status.logout_youtube": {
        "uk": "Вийшли з Google (YouTube).",
        "en": "Signed out of Google (YouTube).",
    },
    "status.twitch_keys_saved": {"uk": "Дані Twitch збережено.", "en": "Twitch credentials saved."},
    "status.twitch_browser_ok": {
        "uk": "Twitch: увійшли через браузер.",
        "en": "Twitch: signed in via browser.",
    },
    "status.youtube_json_removed": {
        "uk": "YouTube: JSON клієнта Google видалено зі сховища.",
        "en": "YouTube: Google client JSON removed from storage.",
    },
    "status.youtube_signed_in": {
        "uk": "YouTube: увійшли через Google.",
        "en": "YouTube: signed in with Google.",
    },
    "startup.workers": {"uk": "Запуск обробників пайплайну…", "en": "Starting pipeline workers…"},
    "startup.ready": {
        "uk": "Готово — підключіть Twitch і/або YouTube",
        "en": "Ready — connect Twitch and/or YouTube",
    },
    "status.app_idle": {"uk": "Готово", "en": "Ready"},
    "status.edge_voices_loading": {"uk": "Edge: завантажую голоси…", "en": "Edge: loading voices…"},
    "status.edge_voices_failed": {
        "uk": "Edge: не вдалося отримати список голосів",
        "en": "Edge: failed to fetch voices",
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
    "twitch.oauth_token_err": {
        "uk": "Помилка токена Twitch: {detail}",
        "en": "Twitch token error: {detail}",
    },
    # YouTube source
    "yt.oauth_browser": {
        "uk": "YouTube: відкриваємо браузер для OAuth…",
        "en": "YouTube: opening browser for OAuth…",
    },
    "yt.oauth_saved": {"uk": "YouTube: токен OAuth збережено", "en": "YouTube: OAuth token saved"},
    "yt.run_oauth_first": {
        "uk": "YouTube: спочатку виконайте OAuth",
        "en": "YouTube: run OAuth first",
    },
    "yt.token_expired": {
        "uk": "YouTube: токен прострочено — знову OAuth",
        "en": "YouTube: token expired — run OAuth again",
    },
    "yt.oauth_refresh_failed": {
        "uk": (
            "YouTube: доступ скасовано або токен більше не дійсний "
            "(invalid_grant) — увійдіть через Google знову."
        ),
        "en": (
            "YouTube: access was revoked or the token is no longer valid "
            "(invalid_grant) — sign in with Google again."
        ),
    },
    "yt.stopped": {"uk": "YouTube: зупинено", "en": "YouTube: stopped"},
    "yt.bad_url": {
        "uk": "YouTube: некоректний URL або ID відео",
        "en": "YouTube: invalid video URL or ID",
    },
    "yt.token_missing": {
        "uk": "YouTube: немає токена OAuth — увійдіть знову",
        "en": "YouTube: OAuth token missing — run login again",
    },
    "yt.api_init_retry": {
        "uk": "YouTube API init error: {err} — повтор через {sec:.0f}s…",
        "en": "YouTube API init error: {err} — retry in {sec:.0f}s…",
    },
    "yt.retry": {
        "uk": "YouTube: {err} — повтор через {sec:.0f}s…",
        "en": "YouTube: {err} — retry in {sec:.0f}s…",
    },
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
    "yt.fallback_switching": {
        "uk": "YouTube: квота API вичерпана — перехід на фоллбек читання чату…",
        "en": "YouTube: API quota exhausted — switching to fallback chat reader…",
    },
    "yt.fallback_polling": {
        "uk": "YouTube: фоллбек — читаємо чат без API…",
        "en": "YouTube: fallback — reading chat without the API…",
    },
    "yt.fallback_error": {
        "uk": "YouTube: помилка фоллбек-чату: {err}",
        "en": "YouTube: fallback chat error: {err}",
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
    "dlg.twitch_need_channel": {
        "uk": "Потрібен канал (логін без #).",
        "en": "Channel login is required (without #).",
    },
    "dlg.twitch_need_token": {
        "uk": "Немає токена: увійдіть через браузер, збережіть дані застосунку або вставте токен.",
        "en": "No token: sign in via browser, save app credentials, or paste a token.",
    },
    "dlg.youtube": {"uk": "YouTube", "en": "YouTube"},
    "dlg.tiktok": {"uk": "TikTok", "en": "TikTok"},
    "dlg.tiktok_need_username": {
        "uk": "Потрібен юзернейм (нік) стрімера.",
        "en": "Streamer username is required.",
    },
    "dlg.youtube_next_json": {
        "uk": "Наступний вхід через Google знову запропонує обрати JSON клієнта.",
        "en": "The next Google sign-in will ask you to pick the client JSON again.",
    },
    "dlg.google_json_title": {
        "uk": "Оберіть JSON OAuth-клієнта Google (один раз)",
        "en": "Select Google OAuth client JSON (one-time)",
    },
    "dlg.tts": {"uk": "TTS", "en": "TTS"},
    "dlg.json_filter": {"uk": "JSON (*.json);;Усі файли (*)", "en": "JSON (*.json);;All files (*)"},
}


def moderation_blocked_for_tts(tts_output_language: str, author: str) -> str:
    """
    Spoken replacement when OpenAI moderation flags content.
    Wording follows the selected TTS output language (BCP-47 tag), not the UI locale.
    """
    a = (author or "").strip() or "?"
    tag = (tts_output_language or "").strip().lower()
    if tag.startswith("uk"):
        return f"Повідомлення від {a} не було озвучено через недопустимий вміст."
    if tag.startswith("de"):
        return f"Die Nachricht von {a} wurde wegen unzulässigen Inhalts nicht vorgelesen."
    if tag.startswith("pl"):
        return f"Wiadomość użytkownika {a} nie została odczytana z powodu niedopuszczalnej treści."
    return f"A message from {a} was not spoken due to disallowed content."


def tts_chat_author_lead(tts_output_language: str, author: str) -> str:
    """
    Prefix spoken before chat message body, e.g. «Author writes: …».
    Phrasing follows the selected TTS output language (BCP-47 tag).
    """
    a = (author or "").strip() or "?"
    tag = (tts_output_language or "").strip().lower()
    if tag.startswith("uk"):
        return f"{a} пише: "
    if tag.startswith("de"):
        return f"{a} schreibt: "
    if tag.startswith("pl"):
        return f"{a} pisze: "
    return f"{a} writes: "


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
