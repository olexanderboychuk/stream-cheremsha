from __future__ import annotations

import json


def _json_for_script(value: object) -> str:
    s = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def render_activity_dock_html() -> str:
    subscribe_msg = {"op": "subscribe", "type": "activity", "instance": "main", "params": {}}
    return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Activity Dock</title>
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
      .spacer {{ flex: 1; }}
      .btn {{
        appearance: none;
        border: 1px solid var(--chip-border);
        background: var(--btn);
        color: var(--ink);
        border-radius: 10px;
        padding: 6px 10px;
        font-size: 12px;
        cursor: pointer;
      }}
      .btn:hover {{ background: var(--btn-hover); }}
      .btn[hidden] {{ display: none; }}
      .list {{
        flex: 1;
        overflow: auto;
        padding: 12px;
        background: var(--panel);
        display: flex;
        flex-direction: column-reverse;
      }}
      .row {{
        display: flex;
        align-items: flex-start;
        gap: 10px;
        padding: 8px 10px;
        border: 1px solid rgba(42,49,66,0.65);
        background: rgba(10,12,18,0.35);
        border-radius: 12px;
        margin: 0 0 10px 0;
      }}
      .platformIcon {{
        width: 16px;
        height: 16px;
        margin-top: 2px;
        opacity: 0.95;
      }}
      .body {{
        flex: 1;
        min-width: 0;
      }}
      .line {{
        display: flex;
        gap: 8px;
        align-items: baseline;
        flex-wrap: wrap;
      }}
      .time {{
        font-size: 11px;
        color: var(--muted);
      }}
      .user {{
        font-weight: 700;
        font-size: 12px;
        color: var(--ink);
      }}
      .text {{
        font-size: 13px;
        line-height: 1.35;
        white-space: pre-wrap;
        word-wrap: break-word;
        color: var(--ink);
      }}
      .muted {{
        color: var(--muted);
      }}
      .giftIcon {{
        width: 22px;
        height: 22px;
        border-radius: 6px;
        object-fit: cover;
        border: 1px solid rgba(42,49,66,0.8);
        background: rgba(18,22,32,0.6);
        flex-shrink: 0;
      }}
      .joinTicker {{
        flex-shrink: 0;
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 14px;
        min-height: 44px;
        border-top: 1px solid var(--border);
        background: rgba(12, 15, 22, 0.92);
        opacity: 0;
        transform: translateY(6px);
        transition: opacity 0.18s ease, transform 0.18s ease;
        pointer-events: none;
      }}
      .joinTicker.visible {{
        opacity: 1;
        transform: translateY(0);
      }}
      .joinTicker[hidden] {{
        display: none;
      }}
      .joinUser {{
        font-weight: 700;
        font-size: 13px;
        color: var(--ink);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 70%;
      }}
      .joinVerb {{
        font-size: 12px;
        color: var(--muted);
        white-space: nowrap;
      }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="top">
        <div>
          <div class="title" id="title">Activity</div>
          <div class="hint" id="status">connecting…</div>
        </div>
        <div class="spacer"></div>
        <button class="btn" id="jumpBtn" hidden>Jump to latest</button>
      </div>
      <div class="list" id="list"></div>
      <div class="joinTicker" id="joinTicker" hidden>
        <img class="platformIcon" id="joinPlatformIcon" alt="" />
        <span class="joinUser" id="joinUser"></span>
        <span class="joinVerb" id="joinVerb"></span>
      </div>
    </div>

    <script>
      (function() {{
        const isUk = String((navigator && navigator.language) || '').toLowerCase().startsWith('uk');
        const T = isUk ? {{
          title: 'Активність',
          connected: 'підключено',
          connecting: 'підключення…',
          disconnected: 'відключено',
          error: 'помилка',
          reconnectingIn: (s) => 'перепідключення через ' + s + 'с…',
          jump: 'До останніх',
          follow: 'підписка',
          sub: 'підписка (sub)',
          resub: 'повторна підписка',
          gift: 'подарунок',
          join: 'зайшов(ла)',
          like: (n) => 'лайки' + (n > 1 ? (' × ' + String(n)) : ''),
          share: (n) => 'шер' + (n > 1 ? (' × ' + String(n)) : ''),
          superchat: 'суперчат',
          supersticker: 'стікер',
          member: 'учасник',
          event: 'подія',
          sep: ' · ',
        }} : {{
          title: 'Activity',
          connected: 'connected',
          connecting: 'connecting…',
          disconnected: 'disconnected',
          error: 'error',
          reconnectingIn: (s) => 'reconnecting in ' + s + 's…',
          jump: 'Jump to latest',
          follow: 'follow',
          sub: 'sub',
          resub: 'resub',
          gift: 'gift',
          join: 'joined',
          like: (n) => 'likes' + (n > 1 ? (' × ' + String(n)) : ''),
          share: (n) => 'shares' + (n > 1 ? (' × ' + String(n)) : ''),
          superchat: 'super chat',
          supersticker: 'sticker',
          member: 'member',
          event: 'event',
          sep: ' · ',
        }};

        const titleEl = document.getElementById('title');
        const statusEl = document.getElementById('status');
        const listEl = document.getElementById('list');
        const jumpBtn = document.getElementById('jumpBtn');
        const joinTickerEl = document.getElementById('joinTicker');
        const joinPlatformIconEl = document.getElementById('joinPlatformIcon');
        const joinUserEl = document.getElementById('joinUser');
        const joinVerbEl = document.getElementById('joinVerb');
        if (titleEl) titleEl.textContent = T.title;
        jumpBtn.textContent = T.jump;
        if (joinVerbEl) joinVerbEl.textContent = T.join;

        const MAX_ITEMS = 450;
        const FOLLOW_EPS_PX = 40;
        const JOIN_TICK_MS = 1000;
        const joinQueue = [];
        let joinPumpTimer = null;

        let follow = true;

        function wsUrl() {{
          const proto = (location.protocol === 'https:') ? 'wss://' : 'ws://';
          return proto + location.host + '/ws';
        }}

        function atTop() {{
          return listEl.scrollTop <= FOLLOW_EPS_PX;
        }}

        function setFollow(v) {{
          follow = !!v;
          jumpBtn.hidden = follow;
        }}

        function scrollToTop() {{
          listEl.scrollTop = 0;
        }}

        function setStatus(text) {{
          statusEl.textContent = text;
        }}

        function platformIconSrc(platform) {{
          const p = String(platform || '').toLowerCase();
          if (p === 'twitch') return '/assets/twitch.svg';
          if (p === 'youtube') return '/assets/youtube.svg';
          if (p === 'tiktok') return '/assets/tiktok.svg';
          if (p === 'kick') return '/assets/kick.svg';
          return '';
        }}

        function giftActionText(detail, count) {{
          const nm = String(detail || '').trim();
          const c = Math.max(1, Number(count || 1));
          if (nm) return nm + ' × ' + String(c);
          return T.gift + ' × ' + String(c);
        }}

        function actionText(kind, detail, count) {{
          const k = String(kind || '').toLowerCase();
          const c = Number(count || 0);
          if (k === 'follow') return T.follow;
          if (k === 'sub') return T.sub;
          if (k === 'resub') return T.resub;
          if (k === 'gift') return giftActionText(detail, count);
          if (k === 'join') return T.join;
          if (k === 'like') return T.like(c);
          if (k === 'share') return T.share(c);
          if (k === 'superchat') return T.superchat;
          if (k === 'supersticker') return T.supersticker;
          if (k === 'member') return T.member;
          return k || T.event;
        }}

        function renderOne(it) {{
          const row = document.createElement('div');
          row.className = 'row';

          const picon = document.createElement('img');
          picon.className = 'platformIcon';
          const src = platformIconSrc(it.platform);
          if (src) {{
            picon.src = src;
            picon.alt = String(it.platform || '');
            picon.loading = 'lazy';
          }} else {{
            picon.hidden = true;
          }}

          const body = document.createElement('div');
          body.className = 'body';

          const line = document.createElement('div');
          line.className = 'line';

          const tm = document.createElement('span');
          tm.className = 'time';
          tm.textContent = String(it.time || '');

          const user = document.createElement('span');
          user.className = 'user';
          user.textContent = String(it.user || '').trim() || '—';

          const txt = document.createElement('span');
          txt.className = 'text';
          const kindLc = String(it.kind || '').toLowerCase();
          const detail = String(it.detail || '');
          if (kindLc === 'gift') {{
            txt.textContent = giftActionText(detail, it.count);
          }} else {{
            const tail = detail ? (T.sep + detail) : '';
            txt.textContent = actionText(it.kind, detail, it.count) + tail;
          }}

          line.appendChild(tm);
          line.appendChild(user);
          line.appendChild(txt);

          const iconUrl = String(it.icon_url || '');
          row.appendChild(picon);
          if (iconUrl && kindLc === 'gift') {{
            const gi = document.createElement('img');
            gi.className = 'giftIcon';
            gi.src = iconUrl;
            gi.alt = detail || T.gift;
            gi.loading = 'lazy';
            row.appendChild(gi);
          }}

          body.appendChild(line);
          row.appendChild(body);
          return row;
        }}

        function showJoinTicker(it) {{
          if (!joinTickerEl || !joinUserEl) return;
          const src = platformIconSrc(it.platform);
          if (joinPlatformIconEl) {{
            if (src) {{
              joinPlatformIconEl.src = src;
              joinPlatformIconEl.alt = String(it.platform || '');
              joinPlatformIconEl.hidden = false;
            }} else {{
              joinPlatformIconEl.hidden = true;
            }}
          }}
          joinUserEl.textContent = String(it.user || '').trim() || '—';
          joinTickerEl.hidden = false;
          joinTickerEl.classList.remove('visible');
          requestAnimationFrame(() => joinTickerEl.classList.add('visible'));
        }}

        function hideJoinTicker() {{
          if (!joinTickerEl) return;
          joinTickerEl.classList.remove('visible');
        }}

        function enqueueJoin(it) {{
          joinQueue.push(it);
          if (joinQueue.length > 200) joinQueue.splice(0, joinQueue.length - 200);
          if (!joinPumpTimer) pumpJoinTicker();
        }}

        function pumpJoinTicker() {{
          if (!joinQueue.length) {{
            joinPumpTimer = null;
            hideJoinTicker();
            if (joinTickerEl) joinTickerEl.hidden = true;
            return;
          }}
          const it = joinQueue.shift();
          showJoinTicker(it);
          joinPumpTimer = setTimeout(() => {{
            joinPumpTimer = null;
            pumpJoinTicker();
          }}, JOIN_TICK_MS);
        }}

        function renderPrepend(it) {{
          const wasTop = atTop();
          const node = renderOne(it);
          if (listEl.firstChild) {{
            listEl.insertBefore(node, listEl.firstChild);
          }} else {{
            listEl.appendChild(node);
          }}
          if (listEl.children.length > MAX_ITEMS) {{
            listEl.removeChild(listEl.lastChild);
          }}
          if (follow && wasTop) {{
            scrollToTop();
          }} else {{
            setFollow(atTop());
          }}
        }}

        listEl.addEventListener('scroll', () => {{
          setFollow(atTop());
        }});

        jumpBtn.addEventListener('click', () => {{
          scrollToTop();
          setFollow(true);
        }});

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
          try {{
            ws = new WebSocket(wsUrl());
          }} catch (_) {{
            scheduleReconnect();
            return;
          }}

          ws.onopen = () => {{
            reconnectAttempt = 0;
            setStatus(T.connected);
            ws.send(JSON.stringify({_json_for_script(subscribe_msg)}));
          }};

          ws.onclose = () => {{
            setStatus(T.disconnected);
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
              const items = st.items || [];
              listEl.innerHTML = '';
              // When list is column-reverse, the first DOM child is rendered at the bottom.
              // Keep newest at the bottom by inserting items in reverse order.
              for (let i = items.length - 1; i >= 0; i--) {{
                renderPrepend(items[i]);
              }}
              scrollToTop();
              setFollow(true);
              return;
            }}
            if (obj.op === 'patch') {{
              const p = obj.patch || {{}};
              if (p.append_join) {{
                enqueueJoin(p.append_join);
                return;
              }}
              if (p.append) {{
                renderPrepend(p.append);
              }}
            }}
          }};
        }}

        connectWs();
      }})();
    </script>
  </body>
</html>"""
