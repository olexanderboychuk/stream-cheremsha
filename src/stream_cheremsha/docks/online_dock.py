from __future__ import annotations

import json


def _json_for_script(value: object) -> str:
    s = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def render_online_dock_html() -> str:
    subscribe_msg = {"op": "subscribe", "type": "online", "instance": "main", "params": {}}
    return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Online Dock</title>
    <style>
      :root {{
        color-scheme: dark;
        --bg: #0a0b0e;
        --panel: #0c0f16;
        --border: #1e2430;
        --ink: #e8eaed;
        --muted: #8b95a5;
        --chip-border: #2a3142;
        --btn: #1c2434;
        --btn-hover: #263246;
        --ok: #47d18c;
        --bad: #ff5d5d;
      }}
      html, body {{
        margin: 0;
        padding: 0;
        height: 100%;
        background: var(--bg);
        color: var(--ink);
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
      }}
      .wrap {{
        height: 100%;
        display: flex;
        flex-direction: column;
      }}
      .top {{
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 12px;
        border-bottom: 1px solid var(--border);
        background: rgba(18, 22, 32, 0.70);
        backdrop-filter: blur(6px);
      }}
      .title {{
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.2px;
        color: var(--ink);
        opacity: 0.9;
      }}
      .hint {{
        font-size: 11px;
        color: var(--muted);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }}
      .content {{
        flex: 1;
        overflow: auto;
        padding: 12px;
        background: var(--panel);
      }}
      .grid {{
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 12px;
      }}
      @media (max-width: 740px) {{
        .grid {{
          grid-template-columns: 1fr;
        }}
      }}
      .card {{
        border: 1px solid rgba(42,49,66,0.65);
        background: rgba(10,12,18,0.35);
        border-radius: 14px;
        padding: 12px;
        min-width: 0;
      }}
      .cardTop {{
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
      }}
      .picon {{
        width: 18px;
        height: 18px;
        opacity: 0.95;
      }}
      .pname {{
        font-size: 13px;
        font-weight: 800;
        letter-spacing: 0.2px;
      }}
      .spacer {{
        flex: 1;
      }}
      .updated {{
        font-size: 11px;
        color: var(--muted);
      }}
      .rows {{
        display: grid;
        grid-template-columns: 1fr;
        gap: 8px;
      }}
      .row {{
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 12px;
        padding: 8px 10px;
        border: 1px solid rgba(42,49,66,0.55);
        border-radius: 12px;
        background: rgba(10,12,18,0.25);
      }}
      .k {{
        font-size: 12px;
        color: var(--muted);
      }}
      .v {{
        font-size: 16px;
        font-weight: 900;
        letter-spacing: 0.2px;
      }}
      .dot {{
        width: 8px;
        height: 8px;
        border-radius: 999px;
        background: var(--bad);
        box-shadow: 0 0 0 2px rgba(255,93,93,0.12);
      }}
      .dot.ok {{
        background: var(--ok);
        box-shadow: 0 0 0 2px rgba(71,209,140,0.12);
      }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="top">
        <div>
          <div class="title" id="title">Online</div>
          <div class="hint" id="status">connecting…</div>
        </div>
      </div>
      <div class="content">
        <div class="grid">
          <div class="card" id="twitchCard">
            <div class="cardTop">
              <img class="picon" src="/assets/twitch.svg" alt="Twitch" />
              <div class="pname" id="twitchTitle">Twitch</div>
              <div class="spacer"></div>
              <div class="updated" id="updatedAt">—</div>
            </div>
            <div class="rows">
              <div class="row">
                <div class="k" id="twCurrentK">Current</div>
                <div class="v" id="twCurrentV">0</div>
              </div>
              <div class="row">
                <div class="k" id="twPeakK">Peak</div>
                <div class="v" id="twPeakV">0</div>
              </div>
            </div>
          </div>
          <div class="card" id="youtubeCard">
            <div class="cardTop">
              <img class="picon" src="/assets/youtube.svg" alt="YouTube" />
              <div class="pname" id="youtubeTitle">YouTube</div>
              <div class="spacer"></div>
            </div>
            <div class="rows">
              <div class="row">
                <div class="k" id="ytCurrentK">Current</div>
                <div class="v" id="ytCurrentV">0</div>
              </div>
              <div class="row">
                <div class="k" id="ytPeakK">Peak</div>
                <div class="v" id="ytPeakV">0</div>
              </div>
              <div class="row">
                <div class="k" id="ytMsgK">Messages</div>
                <div class="v" id="ytMsgV">0</div>
              </div>
              <div class="row">
                <div class="k" id="ytUniqueK">Unique</div>
                <div class="v" id="ytUniqueV">0</div>
              </div>
              <div class="row">
                <div class="k" id="ytSuperK">Super</div>
                <div class="v" id="ytSuperV">0</div>
              </div>
              <div class="row">
                <div class="k" id="ytMemberK">Members</div>
                <div class="v" id="ytMemberV">0</div>
              </div>
            </div>
          </div>
          <div class="card" id="tiktokCard">
            <div class="cardTop">
              <img class="picon" src="/assets/tiktok.svg" alt="TikTok" />
              <div class="pname" id="tiktokTitle">TikTok</div>
              <div class="spacer"></div>
              <div class="dot" id="connDot" title="ws"></div>
            </div>
            <div class="rows">
              <div class="row">
                <div class="k" id="ttCurrentK">Current</div>
                <div class="v" id="ttCurrentV">0</div>
              </div>
              <div class="row">
                <div class="k" id="ttTotalK">Total</div>
                <div class="v" id="ttTotalV">0</div>
              </div>
              <div class="row">
                <div class="k" id="ttGiftsK">Gifts</div>
                <div class="v" id="ttGiftsV">0</div>
              </div>
              <div class="row">
                <div class="k" id="ttDiamondsK">Diamonds</div>
                <div class="v" id="ttDiamondsV">0</div>
              </div>
            </div>
          </div>
          <div class="card" id="kickCard">
            <div class="cardTop">
              <img class="picon" src="/assets/kick.svg" alt="Kick" />
              <div class="pname" id="kickTitle">Kick</div>
              <div class="spacer"></div>
            </div>
            <div class="rows">
              <div class="row">
                <div class="k" id="kkCurrentK">Current</div>
                <div class="v" id="kkCurrentV">0</div>
              </div>
              <div class="row">
                <div class="k" id="kkPeakK">Peak</div>
                <div class="v" id="kkPeakV">0</div>
              </div>
              <div class="row">
                <div class="k" id="kkMsgK">Messages</div>
                <div class="v" id="kkMsgV">0</div>
              </div>
              <div class="row">
                <div class="k" id="kkFollowsK">Follows</div>
                <div class="v" id="kkFollowsV">0</div>
              </div>
              <div class="row">
                <div class="k" id="kkSubsK">Subs</div>
                <div class="v" id="kkSubsV">0</div>
              </div>
              <div class="row">
                <div class="k" id="kkGiftSubsK">Gift subs</div>
                <div class="v" id="kkGiftSubsV">0</div>
              </div>
              <div class="row">
                <div class="k" id="kkKicksK">Kicks</div>
                <div class="v" id="kkKicksV">0</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <script>
      (function() {{
        const isUk = String((navigator && navigator.language) || '').toLowerCase().startsWith('uk');
        const T = isUk ? {{
          title: 'Онлайн',
          connected: 'підключено',
          connecting: 'підключення…',
          disconnected: 'відключено',
          error: 'помилка',
          reconnectingIn: (s) => 'перепідключення через ' + s + 'с…',
          twitch: 'Twitch',
          youtube: 'YouTube',
          tiktok: 'TikTok',
          kick: 'Kick',
          current: 'Зараз',
          peak: 'Пік',
          total: 'Всього',
          gifts: 'Подарунки',
          diamonds: 'Діаманти',
          messages: 'Повідомлення',
          unique: 'Унікальні',
          super: 'Суперчати',
          members: 'Підписки',
          follows: 'Фолови',
          subs: 'Саби',
          giftSubs: 'Подарункові саби',
          kicks: 'KICKS',
          updatedAt: (s) => 'оновлено: ' + s,
        }} : {{
          title: 'Online',
          connected: 'connected',
          connecting: 'connecting…',
          disconnected: 'disconnected',
          error: 'error',
          reconnectingIn: (s) => 'reconnecting in ' + s + 's…',
          twitch: 'Twitch',
          youtube: 'YouTube',
          tiktok: 'TikTok',
          kick: 'Kick',
          current: 'Current',
          peak: 'Peak',
          total: 'Total',
          gifts: 'Gifts',
          diamonds: 'Diamonds',
          messages: 'Messages',
          unique: 'Unique',
          super: 'Super Chats',
          members: 'Memberships',
          follows: 'Follows',
          subs: 'Subs',
          giftSubs: 'Gift subs',
          kicks: 'KICKS',
          updatedAt: (s) => 'updated: ' + s,
        }};

        const titleEl = document.getElementById('title');
        const statusEl = document.getElementById('status');
        const updatedAtEl = document.getElementById('updatedAt');
        const connDot = document.getElementById('connDot');

        const twCurrentV = document.getElementById('twCurrentV');
        const twPeakV = document.getElementById('twPeakV');
        const ytCurrentV = document.getElementById('ytCurrentV');
        const ytPeakV = document.getElementById('ytPeakV');
        const ytMsgV = document.getElementById('ytMsgV');
        const ytUniqueV = document.getElementById('ytUniqueV');
        const ytSuperV = document.getElementById('ytSuperV');
        const ytMemberV = document.getElementById('ytMemberV');
        const ttCurrentV = document.getElementById('ttCurrentV');
        const ttTotalV = document.getElementById('ttTotalV');
        const ttGiftsV = document.getElementById('ttGiftsV');
        const ttDiamondsV = document.getElementById('ttDiamondsV');
        const kkCurrentV = document.getElementById('kkCurrentV');
        const kkPeakV = document.getElementById('kkPeakV');
        const kkMsgV = document.getElementById('kkMsgV');
        const kkFollowsV = document.getElementById('kkFollowsV');
        const kkSubsV = document.getElementById('kkSubsV');
        const kkGiftSubsV = document.getElementById('kkGiftSubsV');
        const kkKicksV = document.getElementById('kkKicksV');

        if (titleEl) titleEl.textContent = T.title;
        const twitchTitle = document.getElementById('twitchTitle');
        const youtubeTitle = document.getElementById('youtubeTitle');
        const tiktokTitle = document.getElementById('tiktokTitle');
        const kickTitle = document.getElementById('kickTitle');
        if (twitchTitle) twitchTitle.textContent = T.twitch;
        if (youtubeTitle) youtubeTitle.textContent = T.youtube;
        if (tiktokTitle) tiktokTitle.textContent = T.tiktok;
        if (kickTitle) kickTitle.textContent = T.kick;
        const twCurrentK = document.getElementById('twCurrentK');
        const twPeakK = document.getElementById('twPeakK');
        const ytCurrentK = document.getElementById('ytCurrentK');
        const ytPeakK = document.getElementById('ytPeakK');
        const ytMsgK = document.getElementById('ytMsgK');
        const ytUniqueK = document.getElementById('ytUniqueK');
        const ytSuperK = document.getElementById('ytSuperK');
        const ytMemberK = document.getElementById('ytMemberK');
        const ttCurrentK = document.getElementById('ttCurrentK');
        const ttTotalK = document.getElementById('ttTotalK');
        const ttGiftsK = document.getElementById('ttGiftsK');
        const ttDiamondsK = document.getElementById('ttDiamondsK');
        const kkCurrentK = document.getElementById('kkCurrentK');
        const kkPeakK = document.getElementById('kkPeakK');
        const kkMsgK = document.getElementById('kkMsgK');
        const kkFollowsK = document.getElementById('kkFollowsK');
        const kkSubsK = document.getElementById('kkSubsK');
        const kkGiftSubsK = document.getElementById('kkGiftSubsK');
        const kkKicksK = document.getElementById('kkKicksK');
        if (twCurrentK) twCurrentK.textContent = T.current;
        if (twPeakK) twPeakK.textContent = T.peak;
        if (ytCurrentK) ytCurrentK.textContent = T.current;
        if (ytPeakK) ytPeakK.textContent = T.peak;
        if (ytMsgK) ytMsgK.textContent = T.messages;
        if (ytUniqueK) ytUniqueK.textContent = T.unique;
        if (ytSuperK) ytSuperK.textContent = T.super;
        if (ytMemberK) ytMemberK.textContent = T.members;
        if (ttCurrentK) ttCurrentK.textContent = T.current;
        if (ttTotalK) ttTotalK.textContent = T.total;
        if (ttGiftsK) ttGiftsK.textContent = T.gifts;
        if (ttDiamondsK) ttDiamondsK.textContent = T.diamonds;
        if (kkCurrentK) kkCurrentK.textContent = T.current;
        if (kkPeakK) kkPeakK.textContent = T.peak;
        if (kkMsgK) kkMsgK.textContent = T.messages;
        if (kkFollowsK) kkFollowsK.textContent = T.follows;
        if (kkSubsK) kkSubsK.textContent = T.subs;
        if (kkGiftSubsK) kkGiftSubsK.textContent = T.giftSubs;
        if (kkKicksK) kkKicksK.textContent = T.kicks;

        function setStatus(text) {{
          if (statusEl) statusEl.textContent = text;
        }}

        function setConnected(yes) {{
          if (!connDot) return;
          if (yes) connDot.classList.add('ok'); else connDot.classList.remove('ok');
        }}

        function wsUrl() {{
          const proto = (location.protocol === 'https:') ? 'wss://' : 'ws://';
          return proto + location.host + '/ws';
        }}

        function toInt(x) {{
          const n = Number(x);
          if (!Number.isFinite(n)) return 0;
          return Math.trunc(n);
        }}

        function applyOnline(online) {{
          const o = online || {{}};
          const twitch = o.twitch || {{}};
          const youtube = o.youtube || {{}};
          const tiktok = o.tiktok || {{}};
          const kick = o.kick || {{}};

          if (twCurrentV) twCurrentV.textContent = String(toInt(twitch.current));
          if (twPeakV) twPeakV.textContent = String(toInt(twitch.peak));
          if (ytCurrentV) ytCurrentV.textContent = String(toInt(youtube.current));
          if (ytPeakV) ytPeakV.textContent = String(toInt(youtube.peak));
          if (ytMsgV) ytMsgV.textContent = String(toInt(youtube.messages));
          if (ytUniqueV) ytUniqueV.textContent = String(toInt(youtube.unique));
          if (ytSuperV) ytSuperV.textContent = String(toInt(youtube.superchats));
          if (ytMemberV) ytMemberV.textContent = String(toInt(youtube.memberships));
          if (ttCurrentV) ttCurrentV.textContent = String(toInt(tiktok.current));
          if (ttTotalV) ttTotalV.textContent = String(toInt(tiktok.total));
          if (ttGiftsV) ttGiftsV.textContent = String(toInt(tiktok.gifts));
          if (ttDiamondsV) ttDiamondsV.textContent = String(toInt(tiktok.diamonds));
          if (kkCurrentV) kkCurrentV.textContent = String(toInt(kick.current));
          if (kkPeakV) kkPeakV.textContent = String(toInt(kick.peak));
          if (kkMsgV) kkMsgV.textContent = String(toInt(kick.messages));
          if (kkFollowsV) kkFollowsV.textContent = String(toInt(kick.follows));
          if (kkSubsV) kkSubsV.textContent = String(toInt(kick.subscriptions));
          if (kkGiftSubsV) kkGiftSubsV.textContent = String(toInt(kick.gift_subs));
          if (kkKicksV) kkKicksV.textContent = String(toInt(kick.kicks));

          const updatedAt = String(o.updated_at || '').trim();
          if (updatedAtEl) updatedAtEl.textContent = updatedAt ? T.updatedAt(updatedAt) : '—';
        }}

        let ws = null;
        let reconnectTimer = null;
        let reconnectAttempt = 0;

        function reconnectDelayMs(attempt) {{
          const base = Math.min(10000, 500 * Math.pow(2, Math.max(0, attempt)));
          const jitter = Math.floor(Math.random() * 250);
          return base + jitter;
        }}

        function scheduleReconnect() {{
          if (reconnectTimer !== null) return;
          reconnectAttempt += 1;
          const delay = reconnectDelayMs(reconnectAttempt);
          setStatus(T.reconnectingIn(Math.round(delay / 1000)));
          setConnected(false);
          reconnectTimer = setTimeout(() => {{
            reconnectTimer = null;
            connectWs();
          }}, delay);
        }}

        function connectWs() {{
          if (reconnectTimer !== null) {{
            clearTimeout(reconnectTimer);
            reconnectTimer = null;
          }}
          if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {{
            return;
          }}
          setStatus(T.connecting);
          setConnected(false);
          try {{
            ws = new WebSocket(wsUrl());
          }} catch (_) {{
            scheduleReconnect();
            return;
          }}

          ws.onopen = () => {{
            reconnectAttempt = 0;
            setStatus(T.connected);
            setConnected(true);
            ws.send(JSON.stringify({_json_for_script(subscribe_msg)}));
          }};

          ws.onclose = () => {{
            setStatus(T.disconnected);
            setConnected(false);
            scheduleReconnect();
          }};

          ws.onerror = () => {{
            setStatus(T.error);
          }};

          ws.onmessage = (ev) => {{
            let obj = null;
            try {{ obj = JSON.parse(ev.data); }} catch (_) {{ return; }}
            if (!obj || !obj.op) return;
            if (obj.op === 'initial_state') {{
              const st = obj.state || {{}};
              if (st.online) applyOnline(st.online);
              return;
            }}
            if (obj.op === 'patch') {{
              const p = obj.patch || {{}};
              if (p.online) applyOnline(p.online);
            }}
          }};
        }}

        connectWs();
      }})();
    </script>
  </body>
</html>"""
