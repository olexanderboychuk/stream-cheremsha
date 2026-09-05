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
    "chat.popout_close": {"uk": "Закрити", "en": "Close"},
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
    "ui.big_picture_tooltip": {"uk": "Режим Big Picture", "en": "Big Picture mode"},
    "ui.big_picture_exit_tooltip": {
        "uk": "Вийти з Big Picture (Esc)",
        "en": "Exit Big Picture (Esc)",
    },
    "ui.big_picture_platforms": {"uk": "Платформи", "en": "Platforms"},
    "ui.big_picture_chat": {"uk": "Чат", "en": "Chat"},
    "ui.big_picture_analytics": {"uk": "Аналітика", "en": "Analytics"},
    "ui.nav_music": {"uk": "Музика", "en": "Music"},
    "ui.nav_music_hint": {"uk": "Черга музики", "en": "Music queue"},
    # App chrome (QML + shell)
    "ui.app_header_title": {"uk": "Stream Cheremsha", "en": "Stream Cheremsha"},
    "ui.twitch_head": {"uk": "Twitch", "en": "Twitch"},
    "ui.youtube_head": {"uk": "YouTube", "en": "YouTube"},
    "ui.tiktok_head": {"uk": "TikTok", "en": "TikTok"},
    "ui.kick_head": {"uk": "Kick", "en": "Kick"},
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
    "connections.kick_analytics_title": {"uk": "Kick — аналітика", "en": "Kick analytics"},
    "connections.kick_analytics_offline": {
        "uk": "Підключіть Kick на вкладці «Зв'язки», щоб бачити статистику.",
        "en": "Connect Kick on the Connections tab to see stats.",
    },
    "connections.kick_analytics_viewers": {"uk": "Онлайн", "en": "Live viewers"},
    "connections.kick_analytics_peak": {"uk": "Пік", "en": "Peak"},
    "connections.kick_analytics_messages": {"uk": "Повідомлення", "en": "Messages"},
    "connections.kick_analytics_follows": {"uk": "Фолови", "en": "Follows"},
    "connections.kick_analytics_subs": {"uk": "Саби", "en": "Subscriptions"},
    "connections.kick_analytics_gift_subs": {"uk": "Подарункові саби", "en": "Gift subs"},
    "connections.kick_analytics_kicks": {"uk": "KICKS", "en": "KICKS"},
    "connections.kick_analytics_activity": {"uk": "Події", "en": "Events"},
    "connections.kick_analytics_follow": {"uk": "зафоловив", "en": "followed"},
    "connections.kick_analytics_sub": {"uk": "саб", "en": "sub"},
    "connections.kick_analytics_gift_sub": {"uk": "подарунковий саб", "en": "gift sub"},
    "connections.kick_analytics_kick_gift": {"uk": "KICKS", "en": "KICKS"},
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
    "actions.trigger_platform_kick": {"uk": "Kick", "en": "Kick"},
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
    "actions.event.kick_follow": {"uk": "Фоллов (Kick)", "en": "Follow (Kick)"},
    "actions.event.kick_subscription": {"uk": "Підписка (Kick)", "en": "Subscription (Kick)"},
    "actions.event.kick_gift_sub": {"uk": "Подарунковий саб (Kick)", "en": "Gift sub (Kick)"},
    "actions.event.kick_gift": {"uk": "KICKS (Kick)", "en": "KICKS gifted (Kick)"},
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
    "ui.brand_name": {"uk": "CHEREMSHA", "en": "CHEREMSHA"},
    "ui.brand_tagline": {"uk": "STREAM TOGETHER", "en": "STREAM TOGETHER"},
    "ui.nav_home": {"uk": "Головна", "en": "Home"},
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
    "settings.autostart_kick": {
        "uk": "Автозапуск Kick при старті додатку (потрібен канал на вкладці «Зв'язки»)",
        "en": "Auto-start Kick on launch (requires channel on Connections)",
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
    # Kick Connections card
    "kick.btn_browser": {"uk": "Увійти через браузер", "en": "Sign in with browser"},
    "kick.account": {"uk": "Обліковий запис", "en": "Account"},
    "kick.logout": {"uk": "Вийти з Kick", "en": "Sign out of Kick"},
    "kick.channel": {"uk": "Канал (слаг)", "en": "Channel (slug)"},
    "kick.channel_ph": {"uk": "слаг каналу, напр. xqc", "en": "channel slug, e.g. xqc"},
    "kick.client_id_env_required": {
        "uk": "Ця збірка очікує дані Kick через змінні середовища: <code>{env}</code> та <code>{secret_env}</code>",
        "en": "This build expects Kick credentials via env vars: <code>{env}</code> and <code>{secret_env}</code>",
    },
    "kick.oauth_redirect": {
        "uk": "Redirect URI: <code>{uri}</code> — вкажіть його в застосунку Kick.",
        "en": "Redirect URI: <code>{uri}</code> — register it in your Kick app.",
    },
    "kick.connected_as": {
        "uk": "Підключено до Kick як @{login}",
        "en": "Connected to Kick as @{login}",
    },
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
    "audio.tts_engine_respeecher": {"uk": "ReSpeecher (мережа)", "en": "ReSpeecher (online)"},
    "audio.edge_voice_group": {"uk": "Edge — голос", "en": "Edge — voice"},
    "audio.edge_voice_label": {"uk": "Голос", "en": "Voice"},
    "audio.respeecher_voice_group": {"uk": "ReSpeecher — голос", "en": "ReSpeecher — voice"},
    "audio.respeecher_voice_label": {"uk": "Голос", "en": "Voice"},
    "audio.tts_randomize_voice": {"uk": "Випадковий голос", "en": "Randomize voice"},
    "audio.tts_randomize_voice_hint": {
        "uk": "Кожне озвучення буде використовувати випадковий голос із доступного списку.",
        "en": "Each speech will use a random voice from the available list.",
    },
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
    "audio.tts_whitelist": {
        "uk": "Білий список TTS (нікнейми)",
        "en": "TTS whitelist (usernames)",
    },
    "audio.tts_whitelist_hint": {
        "uk": "Ніки / @хендли через кому або з нового рядка. Якщо список не порожній — озвучуються лише ці користувачі "
        "(для TikTok підходить і nickname, і unique_id).",
        "en": "Nicks / @handles, comma- or newline-separated. If not empty — only these users are spoken "
        "(for TikTok both nickname and unique_id match).",
    },
    "audio.tts_whitelist_ph": {
        "uk": "user1, @user2, kodi_the_cat",
        "en": "user1, @user2, kodi_the_cat",
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
    "footer.kick": {"uk": "Kick", "en": "Kick"},
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
    "status.logout_kick": {"uk": "Вийшли з Kick.", "en": "Signed out of Kick."},
    "status.kick_browser_ok": {
        "uk": "Kick: увійшли через браузер.",
        "en": "Kick: signed in via browser.",
    },
    "status.kick_oauth_prompt": {
        "uk": "Kick: авторизація відкрита у браузері…",
        "en": "Kick: authorization opened in your browser…",
    },
    "status.kick_oauth_denied": {
        "uk": "Kick: авторизацію скасовано.",
        "en": "Kick: authorization denied.",
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
    # Kick (Pusher compatibility transport + OAuth)
    "kick.stopped": {"uk": "Kick: зупинено", "en": "Kick: stopped"},
    "kick.transport_start": {"uk": "Підключити", "en": "Connect"},
    "kick.transport_stop": {"uk": "Відключити", "en": "Disconnect"},
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
    "dlg.kick": {"uk": "Kick", "en": "Kick"},
    "dlg.kick_oauth": {"uk": "Kick OAuth", "en": "Kick OAuth"},
    "dlg.kick_need_client_config": {
        "uk": "Встановіть змінні оточення STREAM_CHEREMSHA_KICK_CLIENT_ID і STREAM_CHEREMSHA_KICK_CLIENT_SECRET, або налаштуйте їх у середовищі перед запуском.",
        "en": "Set STREAM_CHEREMSHA_KICK_CLIENT_ID and STREAM_CHEREMSHA_KICK_CLIENT_SECRET env vars (or configure them) before signing in.",
    },
    "dlg.kick_need_channel": {
        "uk": "Введіть канал Kick (слаг) або спочатку увійдіть.",
        "en": "Enter a Kick channel (slug) or sign in first.",
    },
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
    # StreamPet overlay
    "stream_pet.hungry.1": {
        "uk": "Тут так тихо... Про мене всі забули? 🥺",
        "en": "It's so quiet... Did everyone forget me? 🥺",
    },
    "stream_pet.hungry.2": {
        "uk": "Стрімер, твій чат спить! Скиньте хоч троянду, я зараз зникну...",
        "en": "Streamer, chat is asleep! Drop a rose or I'll fade away...",
    },
    "stream_pet.hungry.3": {
        "uk": "{last_donor}, врятуй мене, у мене пустий шлунок! 💔",
        "en": "{last_donor}, save me, my tummy is empty! 💔",
    },
    "stream_pet.hungry.3_fallback": {
        "uk": "Глядачі, хто мене нагодує? 💔",
        "en": "Viewers, who will feed me? 💔",
    },
    "stream_pet.hungry.4": {
        "uk": "Звуки бурчання в животі 👾",
        "en": "*stomach growling sounds* 👾",
    },
    "stream_pet.chill.1": {
        "uk": "О, а що це за гра? Стрімер, ти знову нубиш? 😏",
        "en": "Oh, what game is this? Streamer, you're noobing again? 😏",
    },
    "stream_pet.chill.2": {
        "uk": "Глядачі, ви топ. Накидайте лайків, піднімемо вайб!",
        "en": "Viewers, you're the best. Drop some likes, let's raise the vibe!",
    },
    "stream_pet.chill.3": {
        "uk": "Хтось бачив мої печеньки?",
        "en": "Has anyone seen my cookies?",
    },
    "stream_pet.chill.4": {
        "uk": "Зараз би чіпсіків... 🍟",
        "en": "Some chips would hit right now... 🍟",
    },
    "stream_pet.hyper.1": {
        "uk": "АААА! МЕНЕ ПРЕЕЕЕ! 🔥🚀",
        "en": "AAAA! I'M HYPED! 🔥🚀",
    },
    "stream_pet.hyper.2": {
        "uk": "Я бачу космос! Енергія зашкалює! 🌌",
        "en": "I see space! Energy is off the charts! 🌌",
    },
    "stream_pet.hyper.3": {
        "uk": "ТАК СТОЯТИ! ЦЕЙ СТРІМ ОФІЦІЙНО ГАРЯЧИЙ!",
        "en": "THAT'S IT! THIS STREAM IS OFFICIALLY HOT!",
    },
    "stream_pet.sleep.1": {
        "uk": "Zzz... я трохи посплю... 😴",
        "en": "Zzz... I'll nap a bit... 😴",
    },
    "stream_pet.sleep.2": {
        "uk": "Тихо-тихо, я бачу сни про чіпси...",
        "en": "Shhh, I'm dreaming about chips...",
    },
    "stream_pet.hungry.5": {
        "uk": "Мій метаболізм — це чорна діра... 🕳️",
        "en": "My metabolism is a black hole... 🕳️",
    },
    "stream_pet.hungry.6": {
        "uk": "Стрімер, мені потрібен хоч один донат — я вже прозорий!",
        "en": "Streamer, I need at least one donation — I'm turning transparent!",
    },
    "stream_pet.hungry.7": {
        "uk": "Чуєте? Це мій живіт грає джаз... 🎷",
        "en": "Hear that? My stomach is playing jazz... 🎷",
    },
    "stream_pet.hungry.8": {
        "uk": "Голодний пет — злий пет. Не перевіряйте... 😤",
        "en": "A hungry pet is a grumpy pet. Don't test it... 😤",
    },
    "stream_pet.hungry.9": {
        "uk": "Останній раз їв, коли чат був активний. Той самий вік...",
        "en": "Last ate when chat was active. Same era...",
    },
    "stream_pet.hungry.10": {
        "uk": "Може хтось кинуть сердечко? Я не про романтику... 💔",
        "en": "Maybe drop a heart? Not the romantic kind... 💔",
    },
    "stream_pet.hungry.11": {
        "uk": "Тут так пусто, що я чую власне бурчання в HD 🔊",
        "en": "It's so empty I hear my own growling in HD 🔊",
    },
    "stream_pet.hungry.12": {
        "uk": "Якщо зараз ніхто не нагодує — їстиму алерти...",
        "en": "If nobody feeds me now — I'll eat the alerts...",
    },
    "stream_pet.chill.5": {
        "uk": "Стрімер, не забудь попити водички 💧",
        "en": "Streamer, don't forget to drink some water 💧",
    },
    "stream_pet.chill.6": {
        "uk": "Чілл-режим активовано. Мур. 😌",
        "en": "Chill mode activated. Purr. 😌",
    },
    "stream_pet.chill.7": {
        "uk": "Чат сьогодні солодкий, як цукерка 🍬",
        "en": "Chat is sweet as candy today 🍬",
    },
    "stream_pet.chill.8": {
        "uk": "Я б зараз полежав на клавіатурі...",
        "en": "I'd lie on the keyboard right about now...",
    },
    "stream_pet.chill.9": {
        "uk": "Хтось розказує історію? Я слухаю 👂",
        "en": "Someone telling a story? I'm listening 👂",
    },
    "stream_pet.chill.10": {
        "uk": "Стрім норм, пет задоволений ✅",
        "en": "Stream's good, pet is pleased ✅",
    },
    "stream_pet.chill.11": {
        "uk": "Не стресуй, все під контролем (майже) 😅",
        "en": "Don't stress, everything's under control (mostly) 😅",
    },
    "stream_pet.chill.12": {
        "uk": "О, новий віп! ...ні, то просто алерт 😹",
        "en": "Oh, a new VIP! ...nope, just an alert 😹",
    },
    "stream_pet.hyper.4": {
        "uk": "ПОЛЕТІЛИ! ЧАТ, ВИ БОМБА! 💣",
        "en": "WE'RE FLYING! CHAT, YOU'RE A BOMB! 💣",
    },
    "stream_pet.hyper.5": {
        "uk": "ЕНЕРГІЯ 9999! НЕ ЗУПИНЯЙТЕСЯ!",
        "en": "ENERGY 9999! DON'T STOP!",
    },
    "stream_pet.hyper.6": {
        "uk": "Я танцюю так, ніби мене ніхто не бачить! 💃",
        "en": "I'm dancing like nobody's watching! 💃",
    },
    "stream_pet.hyper.7": {
        "uk": "Стрімер, тримай темп — я не встигаю! ⚡",
        "en": "Streamer, keep the pace — I can't keep up! ⚡",
    },
    "stream_pet.hyper.8": {
        "uk": "Це не хайп — це торнадо! 🌪️",
        "en": "This isn't hype — it's a tornado! 🌪️",
    },
    "stream_pet.hyper.9": {
        "uk": "МЕНЕ НЕСЕ! Хтось натисніть гальмо! 🛸",
        "en": "I'M BEING CARRIED AWAY! Someone hit the brakes! 🛸",
    },
    "stream_pet.hyper.10": {
        "uk": "Лайки йдуть — пет літає! 🚀",
        "en": "Likes incoming — pet is airborne! 🚀",
    },
    "stream_pet.sleep.3": {
        "uk": "Ннн... ще п'ять хвилиночок... 😴",
        "en": "Mmm... five more minutes... 😴",
    },
    "stream_pet.sleep.4": {
        "uk": "Не будити... сниться перемога... 🏆",
        "en": "Don't wake me... dreaming of victory... 🏆",
    },
    "stream_pet.sleep.5": {
        "uk": "Zzz... *тихо мурчить*",
        "en": "Zzz... *soft purring*",
    },
    "stream_pet.sleep.6": {
        "uk": "Я в режимі економії батарейки 🔋",
        "en": "Battery saver mode engaged 🔋",
    },
    "stream_pet.sleep.7": {
        "uk": "Сни про донат-вірус... 💤",
        "en": "Dreaming of a donation virus... 💤",
    },
    "stream_pet.sleep.8": {
        "uk": "Тихше... я на рейді в Morpheus 🌙",
        "en": "Shhh... I'm raiding Morpheus 🌙",
    },
    "stream_pet.react.follow": {
        "uk": "О, новий друг! Привіт, {user}! Ставай у чергу на погладжування!",
        "en": "Oh, a new friend! Hi, {user}! Get in line for pets!",
    },
    "stream_pet.react.small_gift": {
        "uk": "Ням! Дякую, {user}, це було смачно! +5% до ситості!",
        "en": "Yum! Thanks, {user}, that was tasty! +5% fullness!",
    },
    "stream_pet.react.large_gift": {
        "uk": "БОЖЕ МІЙ! {user} — ти мій герой! Стрімер, вклонися йому!",
        "en": "OH MY! {user} — you're my hero! Streamer, bow to them!",
    },
    "stream_pet.react.spam": {
        "uk": "{user}, чого ти кричиш? У мене аж вуха заклало! 😵",
        "en": "{user}, why are you yelling? My ears are ringing! 😵",
    },
    "stream_pet.event_label.chat": {
        "uk": "повідомлення в чаті",
        "en": "your chat message",
    },
    "stream_pet.event_label.like": {
        "uk": "лайки",
        "en": "the likes",
    },
    "stream_pet.event_label.follow": {
        "uk": "підписку",
        "en": "the follow",
    },
    "stream_pet.event_label.join": {
        "uk": "візит на стрім",
        "en": "joining the stream",
    },
    "stream_pet.event_label.member": {
        "uk": "членство на каналі",
        "en": "channel membership",
    },
    "stream_pet.event_label.gift": {
        "uk": "подарунок «{gift_name}»",
        "en": "the gift «{gift_name}»",
    },
    "stream_pet.event_label.gift_fallback": {
        "uk": "подарунок",
        "en": "the gift",
    },
    "stream_pet.event_label.gift_big_fallback": {
        "uk": "мега-подарунок",
        "en": "the mega gift",
    },
    "stream_pet.event_label.cheer_fallback": {
        "uk": "bits",
        "en": "the bits",
    },
    "stream_pet.event_label.superchat_fallback": {
        "uk": "Super Chat",
        "en": "the Super Chat",
    },
    "stream_pet.event_label.spam": {
        "uk": "той крик у чаті",
        "en": "all that yelling",
    },
    "stream_pet.event_label.chat_burst": {
        "uk": "такий жвавий чат",
        "en": "this lively chat",
    },
    "stream_pet.thanks.1": {
        "uk": "{user}, дякую за {event}! 🙏",
        "en": "{user}, thanks for {event}! 🙏",
    },
    "stream_pet.thanks.2": {
        "uk": "Ого, {user}! Дякую за {event}! ✨",
        "en": "Wow, {user}! Thanks for {event}! ✨",
    },
    "stream_pet.thanks.3": {
        "uk": "{user}, ти топ! Дякую за {event}! 💛",
        "en": "{user}, you're awesome! Thanks for {event}! 💛",
    },
    "stream_pet.thanks.4": {
        "uk": "Йее! {user}, дякую за {event}! Я це помітив 👀",
        "en": "Yay! {user}, thanks for {event}! I noticed 👀",
    },
    "stream_pet.thanks.hype.1": {
        "uk": "ВАУ! {user}, дякую за {event}! Я в шоці! 🔥",
        "en": "WOW! {user}, thanks for {event}! I'm shook! 🔥",
    },
    "stream_pet.thanks.hype.2": {
        "uk": "{user} — ЛЕГЕНДА! Дякую за {event}! 🚀",
        "en": "{user} — LEGEND! Thanks for {event}! 🚀",
    },
    "stream_pet.thanks.hype.3": {
        "uk": "ААА! {user}, дякую за {event}! Я лечу в космос! 🌟",
        "en": "AAA! {user}, thanks for {event}! I'm flying to space! 🌟",
    },
    "stream_pet.thanks.5": {
        "uk": "{user}, ти зробив мій день! Дякую за {event}! ☀️",
        "en": "{user}, you made my day! Thanks for {event}! ☀️",
    },
    "stream_pet.thanks.6": {
        "uk": "О, {user}! Це було мило — дякую за {event}! 🥰",
        "en": "Oh, {user}! That was sweet — thanks for {event}! 🥰",
    },
    "stream_pet.thanks.7": {
        "uk": "{user}, я це запам'ятаю! Дякую за {event}! 📝",
        "en": "{user}, I'll remember this! Thanks for {event}! 📝",
    },
    "stream_pet.thanks.8": {
        "uk": "Клас, {user}! Дякую за {event}! Ти в топі! 🏅",
        "en": "Nice one, {user}! Thanks for {event}! You're in the top tier! 🏅",
    },
    "stream_pet.thanks.9": {
        "uk": "{user}, дякую за {event}! Обіймаю віртуально! 🤗",
        "en": "{user}, thanks for {event}! Virtual hug! 🤗",
    },
    "stream_pet.thanks.10": {
        "uk": "Ура! {user} зробив(ла) {event} — я щасливий! 💫",
        "en": "Yay! {user} did {event} — I'm happy! 💫",
    },
    "stream_pet.thanks.11": {
        "uk": "{user}, дякую за {event}! Стрімер, подивись на цього героя!",
        "en": "{user}, thanks for {event}! Streamer, look at this hero!",
    },
    "stream_pet.thanks.12": {
        "uk": "Пет схвалює! {user}, дякую за {event}! 👍",
        "en": "Pet approves! {user}, thanks for {event}! 👍",
    },
    "stream_pet.thanks.hype.4": {
        "uk": "НЕМОЖЛИВО! {user}, дякую за {event}! Я ПЛАВЛЮ! 🔥",
        "en": "UNREAL! {user}, thanks for {event}! I'M MELTING! 🔥",
    },
    "stream_pet.thanks.hype.5": {
        "uk": "{user} — БОС РЕЙДУ! Дякую за {event}! 👑",
        "en": "{user} — RAID BOSS! Thanks for {event}! 👑",
    },
    "stream_pet.thanks.hype.6": {
        "uk": "ЧАТ, ДИВІТЬСЯ! {user} зробив(ла) {event}! 🎉",
        "en": "CHAT, LOOK! {user} did {event}! 🎉",
    },
    "stream_pet.thanks.hype.7": {
        "uk": "{user}, це було ЕПІЧНО! Дякую за {event}! ⚔️",
        "en": "{user}, that was EPIC! Thanks for {event}! ⚔️",
    },
    "stream_pet.thanks.hype.8": {
        "uk": "Я КРИЧУ! {user}, дякую за {event}! 📢",
        "en": "I'M SCREAMING! {user}, thanks for {event}! 📢",
    },
    "stream_pet.thanks.hype.9": {
        "uk": "{user}, ти зламав(ла) шкалу хайпу! {event} — топ! 📈",
        "en": "{user}, you broke the hype meter! {event} — top tier! 📈",
    },
    "stream_pet.thanks.hype.10": {
        "uk": "МІСІЯ ВИКОНАНА! {user}, дякую за {event}! 🎯",
        "en": "MISSION COMPLETE! {user}, thanks for {event}! 🎯",
    },
    "stream_pet.thanks.chat.1": {
        "uk": "{user}, круте повідомлення! Дякую за {event}! 💬",
        "en": "{user}, great message! Thanks for {event}! 💬",
    },
    "stream_pet.thanks.chat.2": {
        "uk": "{user}, я прочитав — і усміхнувся! Дякую за {event}! 😊",
        "en": "{user}, I read it and smiled! Thanks for {event}! 😊",
    },
    "stream_pet.thanks.chat.3": {
        "uk": "О, {user}! Гарні слова — дякую за {event}! ✨",
        "en": "Oh, {user}! Nice words — thanks for {event}! ✨",
    },
    "stream_pet.thanks.chat.4": {
        "uk": "{user}, чат оживає завдяки тобі! {event} — супер!",
        "en": "{user}, chat comes alive because of you! {event} — awesome!",
    },
    "stream_pet.thanks.chat.5": {
        "uk": "{user}, дякую за {event}! Я це зберіг у пам'яті! 🧠",
        "en": "{user}, thanks for {event}! Saved to memory! 🧠",
    },
    "stream_pet.thanks.chat.6": {
        "uk": "Ха! {user}, дякую за {event}! Ти підняв(ла) настрій!",
        "en": "Ha! {user}, thanks for {event}! You boosted the mood!",
    },
    "stream_pet.thanks.chat.7": {
        "uk": "{user}, дякую за {event}! Пиши ще! ✍️",
        "en": "{user}, thanks for {event}! Keep typing! ✍️",
    },
    "stream_pet.thanks.chat.8": {
        "uk": "Стрімер, {user} написав(ла) щось цікаве! Дякую за {event}!",
        "en": "Streamer, {user} wrote something cool! Thanks for {event}!",
    },
    "stream_pet.thanks.chat.9": {
        "uk": "{user}, твій {event} — як печиво для пета! 🍪",
        "en": "{user}, your {event} is like cookies for the pet! 🍪",
    },
    "stream_pet.thanks.chat.10": {
        "uk": "Пет киває! {user}, дякую за {event}! 🙂",
        "en": "Pet nods! {user}, thanks for {event}! 🙂",
    },
    "stream_pet.thanks.like.1": {
        "uk": "{user}, ці {event} — вогонь! Дякую! 🔥",
        "en": "{user}, those {event} are fire! Thanks! 🔥",
    },
    "stream_pet.thanks.like.2": {
        "uk": "{user}, дякую за {event}! Ще трохи — і я злітаю! 🎈",
        "en": "{user}, thanks for {event}! A bit more and I'll take off! 🎈",
    },
    "stream_pet.thanks.like.3": {
        "uk": "Лайк від {user}! Дякую за {event}! ❤️",
        "en": "A like from {user}! Thanks for {event}! ❤️",
    },
    "stream_pet.thanks.like.4": {
        "uk": "{user}, ти машина лайків! Дякую за {event}! ⚙️",
        "en": "{user}, you're a like machine! Thanks for {event}! ⚙️",
    },
    "stream_pet.thanks.like.5": {
        "uk": "Ого, {user}! {event} — це сила! Дякую! 💪",
        "en": "Whoa, {user}! {event} — that's power! Thanks! 💪",
    },
    "stream_pet.thanks.like.6": {
        "uk": "{user}, дякую за {event}! Пет світиться! ✨",
        "en": "{user}, thanks for {event}! Pet is glowing! ✨",
    },
    "stream_pet.thanks.like.7": {
        "uk": "Так-так! {user}, дякую за {event}! 👆",
        "en": "Yes yes! {user}, thanks for {event}! 👆",
    },
    "stream_pet.thanks.like.8": {
        "uk": "{user}, кожен лайк — як цукерка для мене! Дякую за {event}! 🍬",
        "en": "{user}, every like is candy for me! Thanks for {event}! 🍬",
    },
    "stream_pet.thanks.like.9": {
        "uk": "{user}, дякую за {event}! Чат, беремо приклад!",
        "en": "{user}, thanks for {event}! Chat, take notes!",
    },
    "stream_pet.thanks.like.10": {
        "uk": "Плюс вайб від {user}! Дякую за {event}! 📈",
        "en": "Plus vibe from {user}! Thanks for {event}! 📈",
    },
    "stream_pet.thanks.follow.1": {
        "uk": "{user}, ласкаво просимо в зграю! Дякую за {event}! 🐾",
        "en": "{user}, welcome to the pack! Thanks for {event}! 🐾",
    },
    "stream_pet.thanks.follow.2": {
        "uk": "Новий друг! {user}, дякую за {event}! 🤝",
        "en": "New friend! {user}, thanks for {event}! 🤝",
    },
    "stream_pet.thanks.follow.3": {
        "uk": "{user}, ти тепер з нами! Дякую за {event}! 🎊",
        "en": "{user}, you're with us now! Thanks for {event}! 🎊",
    },
    "stream_pet.thanks.follow.4": {
        "uk": "Ого, {user} підписав(лася)! Дякую за {event}! ⭐",
        "en": "Whoa, {user} followed! Thanks for {event}! ⭐",
    },
    "stream_pet.thanks.follow.5": {
        "uk": "{user}, дякую за {event}! Ставай у чергу на погладжування!",
        "en": "{user}, thanks for {event}! Get in line for pets!",
    },
    "stream_pet.thanks.follow.6": {
        "uk": "Пет танцює! {user}, дякую за {event}! 💃",
        "en": "Pet is dancing! {user}, thanks for {event}! 💃",
    },
    "stream_pet.thanks.follow.7": {
        "uk": "{user}, дякую за {event}! Тепер ти офіційно крутий(а)!",
        "en": "{user}, thanks for {event}! You're officially cool now!",
    },
    "stream_pet.thanks.follow.8": {
        "uk": "Вітаю, {user}! Дякую за {event}! Не зникай! 👋",
        "en": "Welcome, {user}! Thanks for {event}! Don't disappear! 👋",
    },
    "stream_pet.thanks.follow.9": {
        "uk": "{user}, дякую за {event}! +1 до родини стріму!",
        "en": "{user}, thanks for {event}! +1 to the stream family!",
    },
    "stream_pet.thanks.follow.10": {
        "uk": "Стрімер, дивись — {user} зробив(ла) {event}! Клас!",
        "en": "Streamer, look — {user} did {event}! Nice!",
    },
    "stream_pet.thanks.join.1": {
        "uk": "{user}, привіт! Дякую за {event}! 👋",
        "en": "{user}, hi! Thanks for {event}! 👋",
    },
    "stream_pet.thanks.join.2": {
        "uk": "О, {user} зайшов(ла)! Дякую за {event}! 🚪",
        "en": "Oh, {user} joined! Thanks for {event}! 🚪",
    },
    "stream_pet.thanks.join.3": {
        "uk": "{user}, раді тебе бачити! Дякую за {event}! 😄",
        "en": "{user}, glad you're here! Thanks for {event}! 😄",
    },
    "stream_pet.thanks.join.4": {
        "uk": "Вітаю на стрімі, {user}! Дякую за {event}! 🎬",
        "en": "Welcome to the stream, {user}! Thanks for {event}! 🎬",
    },
    "stream_pet.thanks.join.5": {
        "uk": "{user}, заходь зручніше! Дякую за {event}! 🛋️",
        "en": "{user}, make yourself comfy! Thanks for {event}! 🛋️",
    },
    "stream_pet.thanks.join.6": {
        "uk": "Пет махає лапкою! {user}, дякую за {event}! 🐾",
        "en": "Pet waves a paw! {user}, thanks for {event}! 🐾",
    },
    "stream_pet.thanks.join.7": {
        "uk": "{user}, ти вчасно! Дякую за {event}! ⏰",
        "en": "{user}, perfect timing! Thanks for {event}! ⏰",
    },
    "stream_pet.thanks.join.8": {
        "uk": "Нове обличчя! {user}, дякую за {event}! 🌟",
        "en": "New face! {user}, thanks for {event}! 🌟",
    },
    "stream_pet.thanks.gift.1": {
        "uk": "Ням! {user}, дякую за {event}! Смачно! 🍽️",
        "en": "Yum! {user}, thanks for {event}! Tasty! 🍽️",
    },
    "stream_pet.thanks.gift.2": {
        "uk": "{user}, дякую за {event}! +енергія для пета! ⚡",
        "en": "{user}, thanks for {event}! +energy for the pet! ⚡",
    },
    "stream_pet.thanks.gift.3": {
        "uk": "Ого, {user}! {event} — це любов! Дякую! 💝",
        "en": "Wow, {user}! {event} — that's love! Thanks! 💝",
    },
    "stream_pet.thanks.gift.4": {
        "uk": "{user}, дякую за {event}! Я ситий(а) і щасливий(а)! 😋",
        "en": "{user}, thanks for {event}! I'm full and happy! 😋",
    },
    "stream_pet.thanks.gift.5": {
        "uk": "Подарунок від {user}! Дякую за {event}! 🎁",
        "en": "A gift from {user}! Thanks for {event}! 🎁",
    },
    "stream_pet.thanks.gift.6": {
        "uk": "{user}, дякую за {event}! Стрімер, це для тебе теж!",
        "en": "{user}, thanks for {event}! Streamer, this is for you too!",
    },
    "stream_pet.thanks.gift.7": {
        "uk": "Чмок! {user}, дякую за {event}! 😘",
        "en": "Mwah! {user}, thanks for {event}! 😘",
    },
    "stream_pet.thanks.gift.8": {
        "uk": "{user}, ти нагодував(ла) пета! Дякую за {event}! 🥣",
        "en": "{user}, you fed the pet! Thanks for {event}! 🥣",
    },
    "stream_pet.thanks.gift.9": {
        "uk": "Дякую, {user}! {event} — як домашня їжа! 🏠",
        "en": "Thanks, {user}! {event} — like home cooking! 🏠",
    },
    "stream_pet.thanks.gift.10": {
        "uk": "{user}, дякую за {event}! Пет облизується! 👅",
        "en": "{user}, thanks for {event}! Pet is licking lips! 👅",
    },
    "stream_pet.thanks.gift_large.1": {
        "uk": "БОЖЕ МІЙ! {user} — легенда! Дякую за {event}! 👑",
        "en": "OH MY! {user} — a legend! Thanks for {event}! 👑",
    },
    "stream_pet.thanks.gift_large.2": {
        "uk": "{user}, це МЕГА! Дякую за {event}! Стрімер, вклонися!",
        "en": "{user}, that's MEGA! Thanks for {event}! Streamer, bow down!",
    },
    "stream_pet.thanks.gift_large.3": {
        "uk": "ВАУ! {user}, дякую за {event}! Я в шоці! 🤯",
        "en": "WOW! {user}, thanks for {event}! I'm shook! 🤯",
    },
    "stream_pet.thanks.gift_large.4": {
        "uk": "{user} — WHALE ALERT! Дякую за {event}! 🐋",
        "en": "{user} — WHALE ALERT! Thanks for {event}! 🐋",
    },
    "stream_pet.thanks.gift_large.5": {
        "uk": "НЕМОЖЛИВО! {user}, дякую за {event}! Пет сяє! ✨",
        "en": "UNREAL! {user}, thanks for {event}! Pet is shining! ✨",
    },
    "stream_pet.thanks.gift_large.6": {
        "uk": "{user}, ти зламав(ла) банк! Дякую за {event}! 💰",
        "en": "{user}, you broke the bank! Thanks for {event}! 💰",
    },
    "stream_pet.thanks.gift_large.7": {
        "uk": "ЧАТ, АПЛОДУЙТЕ! {user} — {event}! 👏",
        "en": "CHAT, APPLAUD! {user} — {event}! 👏",
    },
    "stream_pet.thanks.gift_large.8": {
        "uk": "{user}, дякую за {event}! Я пам'ятатиму це вічно! 🏆",
        "en": "{user}, thanks for {event}! I'll remember this forever! 🏆",
    },
    "stream_pet.thanks.gift_large.9": {
        "uk": "ЕПІК ДОНАТ! {user}, дякую за {event}! 🎆",
        "en": "EPIC DONATION! {user}, thanks for {event}! 🎆",
    },
    "stream_pet.thanks.gift_large.10": {
        "uk": "{user} — MVP стріму! Дякую за {event}! 🥇",
        "en": "{user} — stream MVP! Thanks for {event}! 🥇",
    },
    "stream_pet.thanks.member.1": {
        "uk": "{user}, дякую за {event}! Ти VIP пета! 💎",
        "en": "{user}, thanks for {event}! You're pet VIP! 💎",
    },
    "stream_pet.thanks.member.2": {
        "uk": "О, член каналу! {user}, дякую за {event}! 🎖️",
        "en": "Oh, a channel member! {user}, thanks for {event}! 🎖️",
    },
    "stream_pet.thanks.member.3": {
        "uk": "{user}, дякую за {event}! Елітний статус підтверджено!",
        "en": "{user}, thanks for {event}! Elite status confirmed!",
    },
    "stream_pet.thanks.member.4": {
        "uk": "Пет вітає свого! {user}, дякую за {event}! 🫡",
        "en": "Pet salutes their own! {user}, thanks for {event}! 🫡",
    },
    "stream_pet.thanks.member.5": {
        "uk": "{user}, дякую за {event}! Ти — сім'я! ❤️",
        "en": "{user}, thanks for {event}! You're family! ❤️",
    },
    "stream_pet.thanks.member.6": {
        "uk": "Преміум! {user}, дякую за {event}! 🌟",
        "en": "Premium! {user}, thanks for {event}! 🌟",
    },
    "stream_pet.thanks.member.7": {
        "uk": "{user}, дякую за {event}! Спеціальне мурчання для тебе!",
        "en": "{user}, thanks for {event}! Special purring for you!",
    },
    "stream_pet.thanks.member.8": {
        "uk": "Стрімер, {user} — член! Дякую за {event}! 🎉",
        "en": "Streamer, {user} is a member! Thanks for {event}! 🎉",
    },
    "stream_pet.thanks.spam.1": {
        "uk": "{user}, полегше! Дякую за {event}... мабуть 😅",
        "en": "{user}, easy there! Thanks for {event}... I guess 😅",
    },
    "stream_pet.thanks.spam.2": {
        "uk": "{user}, чого ти кричиш? Дякую за {event}! 😵",
        "en": "{user}, why are you yelling? Thanks for {event}! 😵",
    },
    "stream_pet.thanks.spam.3": {
        "uk": "У мене вуха дзвенять, {user}! {event} — гучно! 🔊",
        "en": "My ears are ringing, {user}! {event} — loud! 🔊",
    },
    "stream_pet.thanks.spam.4": {
        "uk": "{user}, дякую за {event}! Але тихіше, будь ласка! 🤫",
        "en": "{user}, thanks for {event}! But quieter, please! 🤫",
    },
    "stream_pet.thanks.spam.5": {
        "uk": "Пет здригнувся від {event}! {user}, дякую... 🫨",
        "en": "Pet flinched from {event}! {user}, thanks... 🫨",
    },
    "stream_pet.thanks.spam.6": {
        "uk": "{user}, CAPS LOCK застряг? Дякую за {event}! ⌨️",
        "en": "{user}, CAPS LOCK stuck? Thanks for {event}! ⌨️",
    },
    "stream_pet.thanks.spam.7": {
        "uk": "Ой! {user}, дякую за {event}! Я в шоку! 😱",
        "en": "Ouch! {user}, thanks for {event}! I'm shocked! 😱",
    },
    "stream_pet.thanks.spam.8": {
        "uk": "{user}, дякую за {event}! Наступного разу — без емодзі-бомби!",
        "en": "{user}, thanks for {event}! Next time — no emoji bomb!",
    },
    "stream_pet.thanks.chat_burst.1": {
        "uk": "ЧАТ ВИБУХАЄ! {user}, дякую за {event}! 💥",
        "en": "CHAT IS EXPLODING! {user}, thanks for {event}! 💥",
    },
    "stream_pet.thanks.chat_burst.2": {
        "uk": "{user}, дякую за {event}! Вайб зашкалює! 📈",
        "en": "{user}, thanks for {event}! Vibe is off the charts! 📈",
    },
    "stream_pet.thanks.chat_burst.3": {
        "uk": "Ого, який актив! {user}, дякую за {event}! 🎊",
        "en": "Whoa, such activity! {user}, thanks for {event}! 🎊",
    },
    "stream_pet.thanks.chat_burst.4": {
        "uk": "{user}, дякую за {event}! Чат — як новорічна ялинка! 🎄",
        "en": "{user}, thanks for {event}! Chat is like a Christmas tree! 🎄",
    },
    "stream_pet.thanks.chat_burst.5": {
        "uk": "Пет в захваті! {user}, дякую за {event}! 🤩",
        "en": "Pet is thrilled! {user}, thanks for {event}! 🤩",
    },
    "stream_pet.thanks.chat_burst.6": {
        "uk": "{user}, дякую за {event}! Стрімер, чат живий!",
        "en": "{user}, thanks for {event}! Streamer, chat is alive!",
    },
    "stream_pet.thanks.chat_burst.7": {
        "uk": "ТАК СТОЯТИ! {user}, дякую за {event}! 🔥",
        "en": "THAT'S IT! {user}, thanks for {event}! 🔥",
    },
    "stream_pet.thanks.chat_burst.8": {
        "uk": "{user}, дякую за {event}! Я танцюю разом з чатом! 💃",
        "en": "{user}, thanks for {event}! I'm dancing with chat! 💃",
    },
    "stream_pet.evolve.2": {
        "uk": "АПГРЕЙД! Тепер я бачу чат у 4K! 😎",
        "en": "UPGRADE! I see chat in 4K now! 😎",
    },
    "stream_pet.evolve.3": {
        "uk": "МАКСИМАЛЬНИЙ РІВЕНЬ! ДИСКОТЕКА! 🎉",
        "en": "MAX LEVEL! DISCO TIME! 🎉",
    },
    "stream_pet.l1.idle.1": {
        "uk": "мм... тут тихо... може хтось напише? 🥺",
        "en": "mm... it's quiet... maybe someone types? 🥺",
    },
    "stream_pet.l1.idle.2": {
        "uk": "пі-пі! я маленький пет... голодний трохи",
        "en": "beep beep! i'm a tiny pet... a bit hungry",
    },
    "stream_pet.l1.idle.3": {
        "uk": "хтось... є тут? 👀",
        "en": "anyone... here? 👀",
    },
    "stream_pet.l1.idle.4": {
        "uk": "я чекаю на друзя...",
        "en": "waiting for frens...",
    },
    "stream_pet.l1.idle.5": {
        "uk": "пі! мені холодно без лайків",
        "en": "peep! i'm cold without likes",
    },
    "stream_pet.l1.idle.6": {
        "uk": "може печевко? ...ні, донат краще",
        "en": "maybe cookie? ...no, donation better",
    },
    "stream_pet.l1.idle.7": {
        "uk": "я трохи соромлюсь... але я тут!",
        "en": "i'm a bit shy... but i'm here!",
    },
    "stream_pet.l1.idle.8": {
        "uk": "пі-пі-пі! стрімер, привіт!",
        "en": "beep beep beep! hi streamer!",
    },
    "stream_pet.l1.thanks.1": {
        "uk": "мм... {user}, дякую за {event}! 🙏",
        "en": "mm... {user}, thanks for {event}! 🙏",
    },
    "stream_pet.l1.thanks.2": {
        "uk": "пі! {user}, це за {event}? дякую! ✨",
        "en": "peep! {user}, that's for {event}? thanks! ✨",
    },
    "stream_pet.l1.thanks.3": {
        "uk": "{user}... дякую за {event}... ти добрий(а)",
        "en": "{user}... thanks for {event}... you're kind",
    },
    "stream_pet.l1.thanks.4": {
        "uk": "ого! {user} зробив(ла) {event}! дякую!",
        "en": "wow! {user} did {event}! thanks!",
    },
    "stream_pet.l1.thanks.5": {
        "uk": "{user}, я це помітив! дякую за {event}! 👀",
        "en": "{user}, i noticed! thanks for {event}! 👀",
    },
    "stream_pet.l1.thanks.6": {
        "uk": "пі-пі! {user}, дякую за {event}! 💛",
        "en": "beep! {user}, thanks for {event}! 💛",
    },
    "stream_pet.l1.thanks.7": {
        "uk": "{user}, ти мене нагодував(ла) {event}! ням",
        "en": "{user}, you fed me {event}! yum",
    },
    "stream_pet.l1.thanks.8": {
        "uk": "дякую, {user}! {event} — це тепло",
        "en": "thanks, {user}! {event} feels warm",
    },
    "stream_pet.l2.idle.1": {
        "uk": "О, тепер я бачу чат у 4K! Непогано...",
        "en": "Oh, I see chat in 4K now! Not bad...",
    },
    "stream_pet.l2.idle.2": {
        "uk": "Стрімер, грай краще — на моє оновлення скидалися!",
        "en": "Streamer, play better — they donated for MY upgrade!",
    },
    "stream_pet.l2.idle.3": {
        "uk": "Чат, я тепер крутіший за вас. Майже.",
        "en": "Chat, I'm cooler than you now. Almost.",
    },
    "stream_pet.l2.idle.4": {
        "uk": "Окуляри ON. Сарказм ON. 😎",
        "en": "Glasses ON. Sarcasm ON. 😎",
    },
    "stream_pet.l2.idle.5": {
        "uk": "Хто там без донату? Я бачу всіх.",
        "en": "Who's here without donating? I see everyone.",
    },
    "stream_pet.l2.idle.6": {
        "uk": "Мій firmware оновили — тепер я дерзкий.",
        "en": "They patched my firmware — now I'm sassy.",
    },
    "stream_pet.l2.idle.7": {
        "uk": "Стрімер, не фейли — я тут заради вайбу.",
        "en": "Streamer, no fails — I'm here for the vibe.",
    },
    "stream_pet.l2.idle.8": {
        "uk": "Кібер-панк режим: активовано.",
        "en": "Cyber-punk mode: activated.",
    },
    "stream_pet.l2.thanks.1": {
        "uk": "О, {user}! Твій {event} ну такий собі... але дякую. 😏",
        "en": "Oh, {user}! Your {event} is meh... but thanks. 😏",
    },
    "stream_pet.l2.thanks.2": {
        "uk": "{user}, дякую за {event}. Давай краще троянду наступного разу.",
        "en": "{user}, thanks for {event}. Drop a rose next time though.",
    },
    "stream_pet.l2.thanks.3": {
        "uk": "Непогано, {user}! {event} — зарахую.",
        "en": "Not bad, {user}! {event} — i'll count it.",
    },
    "stream_pet.l2.thanks.4": {
        "uk": "{user}, дякую за {event}! Чат, беремо приклад... ні, не беремо.",
        "en": "{user}, thanks for {event}! Chat, follow... nah don't.",
    },
    "stream_pet.l2.thanks.5": {
        "uk": "Ого, {user}! {event} — нарешті щось норм.",
        "en": "Whoa, {user}! {event} — finally something decent.",
    },
    "stream_pet.l2.thanks.6": {
        "uk": "{user}, дякую за {event}! Я це бачу в HD.",
        "en": "{user}, thanks for {event}! I see it in HD.",
    },
    "stream_pet.l2.thanks.7": {
        "uk": "Стрімер, {user} скинув(ла) {event}! Подивись, як треба.",
        "en": "Streamer, {user} did {event}! That's how it's done.",
    },
    "stream_pet.l2.thanks.8": {
        "uk": "{user}, дякую за {event}! Не розслабляйся.",
        "en": "{user}, thanks for {event}! Don't get comfy.",
    },
    "stream_pet.l3.idle.1": {
        "uk": "Я БОС ЦЬОГО СТРІМУ! Чуєте?! 👑",
        "en": "I'M THE BOSS OF THIS STREAM! Hear me?! 👑",
    },
    "stream_pet.l3.idle.2": {
        "uk": "ДИНАМІКИ НА МАКСИМУМ! БАС ЙДЕ!",
        "en": "SPEAKERS AT MAX! FEEL THE BASS!",
    },
    "stream_pet.l3.idle.3": {
        "uk": "Стрімер, танцюй! Я кручу диск!",
        "en": "Streamer, dance! I'm spinning the deck!",
    },
    "stream_pet.l3.idle.4": {
        "uk": "Чат, хто не донатив — ви в бані... жартую. Майже.",
        "en": "Chat, no donate — banned... kidding. Almost.",
    },
    "stream_pet.l3.idle.5": {
        "uk": "VIP-режим увімкнено. Я роздаю бонуси!",
        "en": "VIP mode on. I'm handing out bonuses!",
    },
    "stream_pet.l3.idle.6": {
        "uk": "МЕГА-ПЕТ АКТИВНИЙ! ЕНЕРГІЯ 9999!",
        "en": "MEGA PET ACTIVE! ENERGY 9999!",
    },
    "stream_pet.l3.idle.7": {
        "uk": "Цей стрім тепер МІЙ. Ви лише гості.",
        "en": "This stream is MINE now. You're just guests.",
    },
    "stream_pet.l3.idle.8": {
        "uk": "ДИСКОТЕКА НЕ ЗАКІНЧУЄТЬСЯ! 🎶",
        "en": "THE DISCO NEVER ENDS! 🎶",
    },
    "stream_pet.l3.thanks.1": {
        "uk": "ЛЕГЕНДА! {user}, дякую за {event}! БОС СХВАЛЮЄ! 👑",
        "en": "LEGEND! {user}, thanks for {event}! BOSS APPROVES! 👑",
    },
    "stream_pet.l3.thanks.2": {
        "uk": "{user}! {event} — ЕПІЧНО! Чат, аплодуйте!",
        "en": "{user}! {event} — EPIC! Chat, applaud!",
    },
    "stream_pet.l3.thanks.3": {
        "uk": "Стрімер, {user} зробив(ла) {event}! Вклонися!",
        "en": "Streamer, {user} did {event}! Bow down!",
    },
    "stream_pet.l3.thanks.4": {
        "uk": "{user}, дякую за {event}! Ти в моєму топі!",
        "en": "{user}, thanks for {event}! You're in my top tier!",
    },
    "stream_pet.l3.thanks.5": {
        "uk": "ВАУ! {user}, {event} — це донат боса!",
        "en": "WOW! {user}, {event} — boss-tier donation!",
    },
    "stream_pet.l3.thanks.6": {
        "uk": "{user}, дякую за {event}! +100 до репутації!",
        "en": "{user}, thanks for {event}! +100 rep!",
    },
    "stream_pet.l3.thanks.7": {
        "uk": "ЧАТ! Дивіться на {user} — {event}! Так треба!",
        "en": "CHAT! Look at {user} — {event}! That's the way!",
    },
    "stream_pet.l3.thanks.8": {
        "uk": "{user}, дякую за {event}! Я оголошую тебе крутим(ою)!",
        "en": "{user}, thanks for {event}! I declare you cool!",
    },
    "stream_pet.l3.vip.1": {
        "uk": "{user} — VIP-персона хвилини! Усі, вітайте! 👑",
        "en": "{user} — VIP of the minute! Everyone, greet them! 👑",
    },
    "stream_pet.l3.vip.2": {
        "uk": "Оголошую: {user} — король/королева чату! 🎉",
        "en": "I declare: {user} — chat royalty! 🎉",
    },
    "stream_pet.l3.vip.3": {
        "uk": "{user} отримує бонус від БОС-пета! ⭐",
        "en": "{user} gets a bonus from BOSS pet! ⭐",
    },
    "stream_pet.l3.vip.4": {
        "uk": "VIP-алерт! {user} — зірка цього моменту! ✨",
        "en": "VIP alert! {user} — star of this moment! ✨",
    },
    "stream_pet.l3.vip.5": {
        "uk": "Чат, аплодуйте {user} — VIP хвилини! 👏",
        "en": "Chat, applaud {user} — VIP of the minute! 👏",
    },
    "stream_pet.l3.vip.6": {
        "uk": "{user} — обраний(а) петом! Почувайтесь особливо!",
        "en": "{user} — chosen by the pet! Feel special!",
    },
    "stream_pet.l3.vip.7": {
        "uk": "Бонус! {user} — почесний гість стріму! 🏅",
        "en": "Bonus! {user} — honorary stream guest! 🏅",
    },
    "stream_pet.l3.vip.8": {
        "uk": "Увага! {user} — VIP! Стрімер, запам'ятай ім'я!",
        "en": "Attention! {user} — VIP! Streamer, remember the name!",
    },
    "widgets.stream_pet.title": {
        "uk": "StreamPet (Тамагочі)",
        "en": "StreamPet (Tamagotchi)",
    },
    # Live Leaderboard overlay + widgets chrome
    "live_leaderboard.kicker": {
        "uk": "ЖИВИЙ РЕЙТИНГ",
        "en": "LIVE LEADERBOARD",
    },
    "live_leaderboard.source.likers": {
        "uk": "ТОП ЛАЙКЕРІВ",
        "en": "TOP LIKERS",
    },
    "live_leaderboard.source.gifters": {
        "uk": "ТОП ДОНОРІВ",
        "en": "TOP GIFTERS",
    },
    "live_leaderboard.source.sharers": {
        "uk": "ТОП ШЕРІВ",
        "en": "TOP SHARERS",
    },
    "live_leaderboard.source.commenters": {
        "uk": "ТОП КОМЕНТАТОРІВ",
        "en": "TOP COMMENTERS",
    },
    "live_leaderboard.source.contributors": {
        "uk": "ТОП КОНТРИБ'ЮТОРІВ",
        "en": "TOP CONTRIBUTORS",
    },
    "live_leaderboard.scene.hall_of_fame": {
        "uk": "ЗАЛ СЛАВИ",
        "en": "HALL OF FAME",
    },
    "live_leaderboard.scene.arena": {
        "uk": "АРЕНА",
        "en": "ARENA",
    },
    "live_leaderboard.scene.energy_network": {
        "uk": "ЕНЕРГОМЕРЕЖА",
        "en": "ENERGY NETWORK",
    },
    "live_leaderboard.empty.awaiting": {
        "uk": "ОЧІКУЄМО СИГНАЛ",
        "en": "AWAITING SIGNAL",
    },
    "live_leaderboard.empty.arena": {
        "uk": "АРЕНА ПОРОЖНЯ",
        "en": "ARENA EMPTY",
    },
    "live_leaderboard.fallback": {
        "uk": "РЕЙТИНГ",
        "en": "LEADERBOARD",
    },
    "widgets.live_leaderboard.title": {
        "uk": "Live Leaderboard (Живий рейтинг)",
        "en": "Live Leaderboard (Live Ranking Show)",
    },
    # Stream Goal overlay + widgets chrome
    "widgets.stream_goal.title": {
        "uk": "Stream Goal (Мета стріму)",
        "en": "Stream Goal (Cyberpunk Digital Core)",
    },
    "widgets.stream_goal.settings_title": {
        "uk": "Stream Goal — Мета стріму",
        "en": "Stream Goal — Stream goal",
    },
    "widgets.stream_goal.settings_blurb": {
        "uk": "Cyberpunk Digital Core відстежує прогрес каналу наживо (фолови, лайки, гіфти, шери, коментарі). Підтримує серії подій (combo), еволюцію енергетичного ядра та візуальні ефекти.",
        "en": "Cyberpunk Digital Core tracks live channel progress (follows, likes, gifts, shares, comments). Supports event combos, core evolution, and visual effects.",
    },
    "widgets.social_rotator.title": {
        "uk": "Social Rotator (Універсальний)",
        "en": "Social Rotator (Universal)",
    },
    "widgets.social_rotator.settings_title": {
        "uk": "Social Rotator — Універсальна ротація соцмереж",
        "en": "Social Rotator — Universal social rotation",
    },
    "widgets.common.enabled": {"uk": "Увімкнено", "en": "Enabled"},
    "widgets.common.copy_url": {"uk": "Скопіювати URL", "en": "Copy URL"},
    "widgets.common.save": {"uk": "Зберегти", "en": "Save"},
    "widgets.common.back": {"uk": "Назад", "en": "Back"},
    "widgets.common.edit": {"uk": "Редагувати", "en": "Edit"},
    "widgets.common.on": {"uk": "Увімк.", "en": "On"},
    "widgets.common.remove": {"uk": "Видалити", "en": "Remove"},
    "widgets.common.username": {"uk": "Нікнейм", "en": "Username"},
    "widgets.common.scale_percent": {"uk": "Масштаб (%)", "en": "Scale (%)"},
    "widgets.common.theme": {"uk": "Тема", "en": "Theme"},
    "stream_goal.goal.followers": {"uk": "ЦІЛЬ: ФОЛОВИ", "en": "FOLLOW GOAL"},
    "stream_goal.goal.likes": {"uk": "ЦІЛЬ: ЛАЙКИ", "en": "LIKE GOAL"},
    "stream_goal.goal.gifts": {"uk": "ЦІЛЬ: ПОДАРУНКИ", "en": "GIFT GOAL"},
    "stream_goal.goal.shares": {"uk": "ЦІЛЬ: ШЕРИ", "en": "SHARE GOAL"},
    "stream_goal.goal.comments": {"uk": "ЦІЛЬ: КОМЕНТАРІ", "en": "COMMENT GOAL"},
    "stream_goal.goal.generic": {"uk": "ЦІЛЬ", "en": "GOAL"},
    "stream_goal.breach": {"uk": "ПРОРИВ ЯДРА", "en": "CORE BREACH"},
    "stream_goal.combo": {"uk": "КОМБО x{n}", "en": "COMBO x{n}"},
    "stream_goal.new_target": {"uk": "НОВА ЦІЛЬ {n}", "en": "NEW TARGET {n}"},
    "stream_goal.notif.follow": {"uk": "+1 ФОЛОВ", "en": "+1 FOLLOW"},
    "stream_goal.notif.like_one": {"uk": "+1 ЛАЙК", "en": "+1 LIKE"},
    "stream_goal.notif.like_many": {"uk": "+{n} ЛАЙКІВ", "en": "+{n} LIKES"},
    "stream_goal.notif.share": {"uk": "ШЕР ВИЯВЛЕНО", "en": "SHARE DETECTED"},
    "stream_goal.notif.gift": {"uk": "ПОДАРУНОК: {name}", "en": "GIFT: {name}"},
    "stream_goal.notif.gift_fallback": {"uk": "Подарунок", "en": "Gift"},
    "stream_goal.notif.comment": {"uk": "КОМЕНТАР", "en": "COMMENT"},
    "stream_goal.skin_target.digital_core": {"uk": "ЦІЛЬ", "en": "TARGET"},
    "stream_goal.skin_target.boss": {"uk": "МАКС HP", "en": "HP MAX"},
    "stream_goal.skin_target.reactor": {"uk": "ЄМНІСТЬ", "en": "CAPACITY"},
    "stream_goal.skin_target.rocket": {"uk": "ТЯГА", "en": "THRUST"},
    "stream_goal.skin_target.vault": {"uk": "ЗАМОК", "en": "LOCK"},
    "stream_goal.skin_target.tower": {"uk": "ВИСОТА", "en": "HEIGHT"},
    "stream_goal.skin_target.creature": {"uk": "БІОМАСА", "en": "BIOMASS"},
    "stream_goal.ui.goal_type": {"uk": "Тип цілі", "en": "Goal type"},
    "stream_goal.ui.title": {"uk": "Заголовок", "en": "Title"},
    "stream_goal.ui.subtitle": {"uk": "Підзаголовок", "en": "Subtitle"},
    "stream_goal.ui.current": {"uk": "Поточне значення", "en": "Current value"},
    "stream_goal.ui.target": {"uk": "Цільове значення", "en": "Target value"},
    "stream_goal.ui.skin": {"uk": "Скин / Тема", "en": "Skin / Theme"},
    "stream_goal.ui.accent": {"uk": "Акцентний колір", "en": "Accent color"},
    "stream_goal.ui.scale_hint": {
        "uk": "Масштаб елементів у межах віджета (не zoom за край)",
        "en": "Scales elements inside the widget (does not zoom past edges)",
    },
    "stream_goal.ui.anim_intensity": {"uk": "Інтенсивність анімацій", "en": "Animation intensity"},
    "stream_goal.ui.anim.low": {"uk": "Низька", "en": "Low"},
    "stream_goal.ui.anim.medium": {"uk": "Середня", "en": "Medium"},
    "stream_goal.ui.anim.high": {"uk": "Висока", "en": "High"},
    "stream_goal.ui.enable_combo": {"uk": "Показувати комбо лічильник", "en": "Show combo counter"},
    "stream_goal.ui.enable_milestones": {
        "uk": "Показувати контрольні точки",
        "en": "Show milestones",
    },
    "stream_goal.ui.enable_particles": {"uk": "Частинки", "en": "Particles"},
    "stream_goal.ui.enable_glitch": {"uk": "Глітч ефекти", "en": "Glitch effects"},
    "stream_goal.ui.reset_behavior": {"uk": "Поведінка скидання", "en": "Reset behavior"},
    "stream_goal.ui.reset.after_completion": {
        "uk": "Авто-скидання та нова мета",
        "en": "Auto-reset and new target",
    },
    "stream_goal.ui.reset.manual": {"uk": "Ручне скидання", "en": "Manual reset"},
    "stream_goal.ui.reset.new_stream": {
        "uk": "Скидати з новим стрімом",
        "en": "Reset on new stream",
    },
    "stream_goal.ui.next_target": {"uk": "Наступна мета", "en": "Next target"},
    "stream_goal.ui.type.followers": {"uk": "Фолови", "en": "Followers"},
    "stream_goal.ui.type.likes": {"uk": "Лайки", "en": "Likes"},
    "stream_goal.ui.type.gifts": {"uk": "Подарунки", "en": "Gifts"},
    "stream_goal.ui.type.shares": {"uk": "Шери", "en": "Shares"},
    "stream_goal.ui.type.comments": {"uk": "Коментарі", "en": "Comments"},
    "stream_goal.ui.skin.digital_core": {
        "uk": "Digital Core (Cyberpunk)",
        "en": "Digital Core (Cyberpunk)",
    },
    "stream_goal.ui.skin.boss": {"uk": "Boss HP (Healthbar)", "en": "Boss HP (Healthbar)"},
    "stream_goal.ui.skin.reactor": {"uk": "Nuclear Reactor", "en": "Nuclear Reactor"},
    "stream_goal.ui.skin.rocket": {"uk": "Space Rocket", "en": "Space Rocket"},
    "stream_goal.ui.skin.vault": {"uk": "Cyber Vault", "en": "Cyber Vault"},
    "stream_goal.ui.skin.tower": {"uk": "Neontower", "en": "Neontower"},
    "stream_goal.ui.skin.creature": {"uk": "Bio Core", "en": "Bio Core"},
    # Social Rotator overlay + widgets chrome
    "social_rotator.kicker": {"uk": "СОЦМЕРЕЖІ LIVE", "en": "LIVE SOCIAL"},
    "social_rotator.next": {"uk": "ДАЛІ", "en": "NEXT"},
    "social_rotator.sec": {"uk": "СЕК", "en": "SEC"},
    "social_rotator.stat.latest_follower": {"uk": "ОСТАННІЙ ФОЛОВЕР", "en": "LATEST FOLLOWER"},
    "social_rotator.stat.latest_donation": {"uk": "ОСТАННІЙ ДОНАТ", "en": "LATEST DONATION"},
    "social_rotator.stat.stream_time": {"uk": "ЧАС СТРІМУ", "en": "STREAM TIME"},
    "social_rotator.stat.top_donator": {"uk": "ТОП ДОНАТЕР", "en": "TOP DONATOR"},
    "social_rotator.stat.online": {"uk": "ОНЛАЙН", "en": "ONLINE"},
    "social_rotator.empty": {"uk": "ОЧІКУЄМО ПЛАТФОРМИ", "en": "AWAITING PLATFORMS"},
    "social_rotator.ui.platforms": {"uk": "ПЛАТФОРМИ", "en": "PLATFORMS"},
    "social_rotator.ui.url_override": {"uk": "URL (опційно)", "en": "URL override"},
    "social_rotator.ui.add_platform": {"uk": "+ ДОДАТИ ПЛАТФОРМУ", "en": "+ ADD PLATFORM"},
    "social_rotator.ui.rotation_ms": {"uk": "Ротація (мс)", "en": "Rotation (ms)"},
    "social_rotator.ui.rotation_hint": {"uk": "8000 = 8 секунд", "en": "8000 = 8 seconds"},
    "social_rotator.ui.transition": {"uk": "Перехід", "en": "Transition"},
    "social_rotator.ui.display": {"uk": "ВІДОБРАЖЕННЯ", "en": "DISPLAY"},
    "social_rotator.ui.show_url": {"uk": "Показувати URL", "en": "Show URL"},
    "social_rotator.ui.show_secondary": {
        "uk": "Показувати інші платформи",
        "en": "Show secondary platforms",
    },
    "social_rotator.ui.show_countdown": {"uk": "Показувати таймер", "en": "Show countdown"},
    "social_rotator.ui.glow": {"uk": "Світіння", "en": "Glow"},
    "social_rotator.ui.particles": {"uk": "Частинки", "en": "Particles"},
    "social_rotator.ui.crt": {"uk": "CRT-ефекти", "en": "CRT effects"},
    "social_rotator.ui.bg_opacity": {"uk": "Непрозорість фону", "en": "Background opacity"},
    "social_rotator.ui.stats_strip": {"uk": "СМУГА СТАТИСТИКИ", "en": "STATS STRIP"},
    "social_rotator.ui.stat.latest_follower": {"uk": "Останній фоловер", "en": "Latest Follower"},
    "social_rotator.ui.stat.latest_donation": {"uk": "Останній донат", "en": "Latest Donation"},
    "social_rotator.ui.stat.stream_time": {"uk": "Час стріму", "en": "Stream Time"},
    "social_rotator.ui.stat.top_donator": {"uk": "Топ донатер", "en": "Top Donator"},
    "social_rotator.ui.stat.online": {"uk": "Онлайн", "en": "Online"},
    "social_rotator.ui.coin_rate": {
        "uk": "TikTok coin → курс вартості",
        "en": "TikTok coin → value rate",
    },
    "social_rotator.ui.transition.glitch_morph": {"uk": "Glitch Morph", "en": "Glitch Morph"},
    "social_rotator.ui.transition.data_stream": {"uk": "Data Stream", "en": "Data Stream"},
    "social_rotator.ui.transition.energy_burst": {"uk": "Energy Burst", "en": "Energy Burst"},
    "social_rotator.ui.transition.scan": {"uk": "Scan", "en": "Scan"},
    "social_rotator.ui.transition.pixel_dissolve": {"uk": "Pixel Dissolve", "en": "Pixel Dissolve"},
    "social_rotator.ui.transition.fade": {"uk": "Fade", "en": "Fade"},
    "social_rotator.ui.theme.neon_cyber": {"uk": "Neon Cyber", "en": "Neon Cyber"},
    "social_rotator.ui.theme.synthwave": {"uk": "Synthwave", "en": "Synthwave"},
    "social_rotator.ui.theme.toxic": {"uk": "Toxic", "en": "Toxic"},
    "social_rotator.ui.theme.ice": {"uk": "Ice", "en": "Ice"},
    "social_rotator.ui.theme.amber": {"uk": "Amber", "en": "Amber"},
    # Live Webcam Frame overlay + widgets chrome
    "widgets.webcam_frame.title": {
        "uk": "CAM // LINK (Рамка для веб-камери)",
        "en": "CAM // LINK (Live Webcam Frame)",
    },
    "widgets.webcam_frame.settings_title": {
        "uk": "CAM // LINK — Рамка для веб-камери",
        "en": "CAM // LINK — Live Webcam Frame",
    },
    "widgets.webcam_frame.settings_blurb": {
        "uk": "Декоративна анімована HUD-рамка для області веб-камери в OBS. Центр залишається повністю прозорим — камера видно крізь рамку.",
        "en": "A decorative animated HUD frame for your webcam area in OBS. The center stays fully transparent so the camera shows through.",
    },
    "webcam_frame.ui.theme.neon_cyber": {"uk": "Neon Cyber", "en": "Neon Cyber"},
    "webcam_frame.ui.theme.synthwave": {"uk": "Synthwave", "en": "Synthwave"},
    "webcam_frame.ui.theme.toxic": {"uk": "Toxic System", "en": "Toxic System"},
    "webcam_frame.ui.theme.ice": {"uk": "Ice", "en": "Ice"},
    "webcam_frame.ui.theme.amber": {"uk": "Amber Core", "en": "Amber Core"},
    "webcam_frame.ui.theme.critical": {"uk": "Critical", "en": "Critical"},
    "webcam_frame.ui.intensity.low": {"uk": "Низька", "en": "Low"},
    "webcam_frame.ui.intensity.medium": {"uk": "Середня", "en": "Medium"},
    "webcam_frame.ui.intensity.high": {"uk": "Висока", "en": "High"},
    "webcam_frame.ui.frame_style.primary": {"uk": "Основна рамка", "en": "Primary Frame"},
    "webcam_frame.ui.frame_style.minimal": {"uk": "Мінімалістична", "en": "Minimal Corners"},
    "webcam_frame.ui.frame_style.tactical": {"uk": "Тактична сітка", "en": "Tactical Reticle"},
    "webcam_frame.ui.frame_style.broadcast": {"uk": "Ефірні панелі", "en": "Broadcast Bars"},
    "webcam_frame.ui.frame_style.hologram": {"uk": "Голограма", "en": "Hologram"},
    "webcam_frame.ui.intensity_label": {"uk": "Інтенсивність", "en": "Intensity"},
    "webcam_frame.ui.frame_style_label": {"uk": "Стиль рамки", "en": "Frame Style"},
    "webcam_frame.ui.cam_label": {"uk": "Мітка камери", "en": "Cam Label"},
    "webcam_frame.ui.effects": {"uk": "ЕФЕКТИ", "en": "EFFECTS"},
    "webcam_frame.ui.energy_flow": {"uk": "Потік енергії", "en": "Energy Flow"},
    "webcam_frame.ui.breathing_glow": {"uk": "Дихаюче світіння", "en": "Breathing Glow"},
    "webcam_frame.ui.light_sweep": {"uk": "Світлова хвиля", "en": "Light Sweep"},
    "webcam_frame.ui.micro_glitch": {"uk": "Мікроглітч", "en": "Micro Glitch"},
    "webcam_frame.ui.sparks": {"uk": "Іскри", "en": "Sparks"},
    "webcam_frame.ui.crt": {"uk": "CRT-ефекти", "en": "CRT Effects"},
    "webcam_frame.ui.status_indicator": {"uk": "Індикатор стану", "en": "Status Indicator"},
    "webcam_frame.ui.boot_animation": {"uk": "Анімація завантаження", "en": "Boot Animation"},
    "webcam_frame.ui.shutdown_animation": {"uk": "Анімація вимкнення", "en": "Shutdown Animation"},
    "webcam_frame.status.online": {"uk": "SIGNAL // ONLINE", "en": "SIGNAL // ONLINE"},
    "webcam_frame.status.offline": {"uk": "SIGNAL // OFFLINE", "en": "SIGNAL // OFFLINE"},
    "webcam_frame.status.live": {"uk": "LIVE", "en": "LIVE"},
    "webcam_frame.boot.online": {"uk": "SYSTEM ONLINE", "en": "SYSTEM ONLINE"},
    # Signal System overlay + widgets chrome
    "widgets.signal_system.title": {
        "uk": "Система сигналів",
        "en": "Signal System",
    },
    "widgets.signal_system.settings_title": {
        "uk": "Система сигналів — налаштування",
        "en": "Signal System — settings",
    },
    "widgets.signal_system.settings_blurb": {
        "uk": "Система сигналів відстежує події чату, подарунки та активність із візуальними ефектами та звуковими підказками.",
        "en": "Signal System tracks chat events, gifts, and activity with visual effects and audio cues.",
    },
    "widgets.signal_system.card_title": {
        "uk": "Система сигналів (оверлей)",
        "en": "Signal System (overlay)",
    },
    "widgets.signal_system.edit_header": {
        "uk": "СИГНАЛ // СИСТЕМА — кінематографічний оверлей",
        "en": "SIGNAL // SYSTEM — cinematic stream overlay",
    },
    "signal_system.goal.detected": {"uk": "СИГНАЛ // ВИЯВЛЕНО", "en": "SIGNAL // DETECTED"},
    "signal_system.goal.mega": {"uk": "МЕГА // ТРАНСМІСІЯ", "en": "MEGA // TRANSMISSION"},
    "signal_system.goal.milestone": {"uk": "СИГНАЛ // РЕКОРД", "en": "SIGNAL // MILESTONE"},
    "signal_system.goal.milestone_reached": {
        "uk": "РЕКОРД // ДОСЯГНУТО",
        "en": "MILESTONE // REACHED",
    },
    "signal_system.goal.milestone_default": {
        "uk": "СТРІМ // РЕКОРД",
        "en": "STREAM // MILESTONE",
    },
    "signal_system.goal.milestone_sub": {
        "uk": "НОВИЙ РЕКОРД",
        "en": "NEW RECORD REACHED",
    },
    "signal_system.goal.milestone_test_sub": {
        "uk": "10 000 ПІДПИСНИКІВ",
        "en": "10,000 FOLLOWERS",
    },
    "signal_system.goal.milestone_test_value": {
        "uk": "РІВЕНЬ 3 ВІДКРИТО",
        "en": "TIER 3 UNLOCKED",
    },
    "signal_system.goal.surge": {"uk": "СИГНАЛ // СПЛЕСК", "en": "SIGNAL // SURGE"},
    "signal_system.goal.overdrive": {
        "uk": "ОВЕРДРАЙВ // ВИЯВЛЕНО",
        "en": "OVERDRIVE // DETECTED",
    },
    "signal_system.goal.surge_sub": {
        "uk": "КРИТИЧНА ШВИДКІСТЬ ЧАТУ",
        "en": "CHAT VELOCITY CRITICAL",
    },
    "signal_system.goal.ai": {"uk": "СИГНАЛ // КОГНІЦІЯ", "en": "SIGNAL // COGNITION"},
    "signal_system.goal.ai_title": {
        "uk": "СИСТЕМА // КОГНІЦІЯ",
        "en": "SYSTEM // COGNITION",
    },
    "signal_system.goal.ai_default_sub": {
        "uk": "ВИЯВЛЕНО АНОМАЛЬНИЙ ПАТЕРН ЧАТУ",
        "en": "ANOMALOUS CHAT PATTERN OBSERVED",
    },
    "signal_system.goal.ai_test_sub": {
        "uk": "ВИСОКА ЕМОЦІЙНА АКТИВНІСТЬ",
        "en": "HIGH SENTIMENT ENGAGEMENT",
    },
    "signal_system.goal.anomaly": {"uk": "СИГНАЛ // АНОМАЛІЯ", "en": "SIGNAL // ANOMALY"},
    "signal_system.goal.anomaly_title": {
        "uk": "АНОМАЛІЯ // ВИЯВЛЕНО",
        "en": "ANOMALY // DETECTED",
    },
    "signal_system.goal.anomaly_sub": {
        "uk": "НЕІДЕНТИФІКОВАНА ЧАСТОТА",
        "en": "UNIDENTIFIED FREQUENCY",
    },
    "signal_system.goal.anomaly_test_sub": {
        "uk": "НЕІДЕНТИФІКОВАНИЙ СПЕКТРАЛЬНИЙ СЛІД",
        "en": "UNIDENTIFIED SPECTRAL TRACE",
    },
    "signal_system.goal.test": {"uk": "СИГНАЛ // ТЕСТ", "en": "SIGNAL // TEST"},
    "signal_system.goal.test_sub": {
        "uk": "ТЕСТОВА ТРАНСМІСІЯ",
        "en": "TEST TRANSMISSION",
    },
    "signal_system.goal.system": {"uk": "СИГНАЛ // СИСТЕМА", "en": "SIGNAL // SYSTEM"},
    "signal_system.goal.unknown": {"uk": "НЕВІДОМА СУТНІСТЬ", "en": "UNKNOWN ENTITY"},
    "signal_system.goal.online": {"uk": "ОНЛАЙН", "en": "ONLINE"},
    "signal_system.goal.offline": {"uk": "ОФЛАЙН", "en": "OFFLINE"},
    "signal_system.goal.activity": {"uk": "АКТИВНІСТЬ", "en": "ACTIVITY"},
    "signal_system.goal.gifts": {"uk": "ПОДАРУНКИ", "en": "GIFTS"},
    "signal_system.goal.gift": {"uk": "ПОДАРУНОК", "en": "GIFT"},
    "signal_system.goal.coins": {"uk": "МОНЕТИ", "en": "COINS"},
    "signal_system.goal.coins_fmt": {"uk": "{n} МОНЕТ", "en": "{n} COINS"},
    "signal_system.goal.per_min_fmt": {"uk": "+{n}/ХВ", "en": "+{n}/MIN"},
    "signal_system.goal.min_gift": {"uk": "МІН. ПОДАРУНОК", "en": "MIN GIFT"},
    "signal_system.goal.anonymous": {"uk": "АНОНІМ", "en": "ANONYMOUS"},
    "signal_system.goal.community": {"uk": "СПІЛЬНОТА", "en": "COMMUNITY"},
    "signal_system.goal.test_pilot": {"uk": "ТЕСТ-ПІЛОТ", "en": "TEST PILOT"},
    "signal_system.overlay.gift_prefix": {"uk": "ПОДАРУНОК //", "en": "GIFT //"},
    "signal_system.overlay.signal_lost": {
        "uk": "// СИГНАЛ ВТРАЧЕНО //",
        "en": "// SIGNAL LOST //",
    },
    "signal_system.overlay.signal_intensity": {
        "uk": "ІНТЕНСИВНІСТЬ СИГНАЛУ",
        "en": "SIGNAL INTENSITY",
    },
    "signal_system.overlay.neural_scan": {
        "uk": "НЕЙРОСКАН :: АКТИВНИЙ",
        "en": "NEURAL SCAN :: ACTIVE",
    },
    "signal_system.overlay.conf": {"uk": "ДОВІРА", "en": "CONF"},
    "signal_system.overlay.pattern_observed": {
        "uk": "СПОСТЕРЕЖЕНО ПАТЕРН",
        "en": "PATTERN OBSERVED",
    },
    "signal_system.overlay.new_record": {"uk": "НОВИЙ РЕКОРД", "en": "NEW RECORD"},
    "signal_system.overlay.sys": {"uk": "СИС //", "en": "SYS //"},
    "signal_system.overlay.act": {"uk": "АКТ", "en": "ACT"},
    "signal_system.overlay.per_min": {"uk": "/ХВ", "en": "/MIN"},
    "signal_system.overlay.grid_link": {
        "uk": "МЕРЕЖА 48.21 // 16.34  [ЗВ'ЯЗОК OK]",
        "en": "GRID 48.21 // 16.34  [LINK OK]",
    },
    "signal_system.overlay.sec_pwr": {
        "uk": "СЕК-A :: ЖИВ {n}%",
        "en": "SEC-A :: PWR {n}%",
    },
    "signal_system.ui.scale_hint": {
        "uk": "Масштаб елементів у межах віджета (не zoom за край)",
        "en": "Scales elements inside the widget (does not zoom past edges)",
    },
    "signal_system.ui.scale": {"uk": "Масштаб (%)", "en": "Scale (%)"},
    "signal_system.ui.core_vertical": {
        "uk": "Висота core (%)",
        "en": "Core height (%)",
    },
    "signal_system.ui.core_vertical_hint": {
        "uk": "Вертикальна позиція ядра: 50 = центр, менше = вище, більше = нижче",
        "en": "Core vertical position: 50 = center, lower = higher up, higher = lower down",
    },
    "signal_system.ui.theme": {"uk": "Тема", "en": "Theme"},
    "signal_system.ui.title": {"uk": "Заголовок", "en": "Title"},
    "signal_system.ui.perimeter": {"uk": "Периметр", "en": "Perimeter"},
    "signal_system.ui.particles": {"uk": "Частинки", "en": "Particles"},
    "signal_system.ui.glitch": {"uk": "Глітч", "en": "Glitch"},
    "signal_system.ui.sound": {"uk": "Звук", "en": "Sound"},
    "signal_system.ui.font": {"uk": "Шрифт", "en": "Font"},
    "signal_system.ui.opacity_idle": {"uk": "Прозорість у спокої", "en": "Idle opacity"},
    "signal_system.ui.opacity_active": {"uk": "Прозорість при сигналі", "en": "Active opacity"},
    "signal_system.ui.cooldown": {"uk": "Кулдаун (мс)", "en": "Cooldown (ms)"},
    "signal_system.ui.min_gift_coins": {"uk": "Мін. монет для подарунка", "en": "Min gift coins"},
    "signal_system.theme.neon_cyber": {
        "uk": "Neon Cyber (ціан / пурпур)",
        "en": "Neon Cyber (Cyan / Magenta)",
    },
    "signal_system.theme.toxic_system": {
        "uk": "Toxic System (матричний зелений)",
        "en": "Toxic System (Matrix Green)",
    },
    "signal_system.theme.ice_protocol": {
        "uk": "Ice Protocol (кобальт)",
        "en": "Ice Protocol (Cobalt Blue)",
    },
    "signal_system.theme.amber_core": {
        "uk": "Amber Core (золото / бурштин)",
        "en": "Amber Core (Gold / Amber)",
    },
    "signal_system.theme.critical": {
        "uk": "Critical (червона тривога)",
        "en": "Critical (Red Alert)",
    },
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
