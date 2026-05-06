from __future__ import annotations

import json


def _json_for_script(value: object) -> str:
    """JSON safe for embedding into <script> (avoid closing tags / entity injection)."""
    s = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def render_multichat_dock_html() -> str:
    subscribe_msg = {"op": "subscribe", "type": "chat", "instance": "main", "params": {}}
    return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>MultiChat Dock</title>
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
      }}
      .msg {{
        padding: 8px 10px;
        border: 1px solid rgba(42,49,66,0.65);
        background: rgba(10,12,18,0.35);
        border-radius: 12px;
        margin: 0 0 10px 0;
      }}
      .meta {{
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 4px;
      }}
      .platformIcon {{
        width: 16px;
        height: 16px;
        display: inline-block;
        opacity: 0.95;
        filter: drop-shadow(0 0 0 rgba(0,0,0,0));
      }}
      .author {{
        font-weight: 700;
        font-size: 12px;
        color: var(--ink);
      }}
      .time {{
        font-size: 11px;
        color: var(--muted);
        margin-left: auto;
      }}
      .text {{
        font-size: 13px;
        line-height: 1.35;
        white-space: pre-wrap;
        word-wrap: break-word;
      }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="top">
        <div>
          <div class="title">MultiChat</div>
          <div class="hint" id="status">connecting…</div>
        </div>
        <div class="spacer"></div>
        <button class="btn" id="jumpBtn" hidden>Jump to latest</button>
      </div>
      <div class="list" id="list"></div>
    </div>

    <script>
      (function() {{
        const isUk = String((navigator && navigator.language) || '').toLowerCase().startsWith('uk');
        const T = isUk ? {{
          connected: 'підключено',
          connecting: 'підключення…',
          disconnected: 'відключено',
          error: 'помилка',
          reconnectingIn: (s) => 'перепідключення через ' + s + 'с…',
          jump: 'До останніх',
        }} : {{
          connected: 'connected',
          connecting: 'connecting…',
          disconnected: 'disconnected',
          error: 'error',
          reconnectingIn: (s) => 'reconnecting in ' + s + 's…',
          jump: 'Jump to latest',
        }};

        const statusEl = document.getElementById('status');
        const listEl = document.getElementById('list');
        const jumpBtn = document.getElementById('jumpBtn');
        jumpBtn.textContent = T.jump;

        const MAX_ITEMS = 400;
        const FOLLOW_EPS_PX = 40; // near-bottom threshold

        let follow = true;

        function wsUrl() {{
          const proto = (location.protocol === 'https:') ? 'wss://' : 'ws://';
          return proto + location.host + '/ws';
        }}

        function atBottom() {{
          const d = listEl.scrollHeight - listEl.clientHeight - listEl.scrollTop;
          return d <= FOLLOW_EPS_PX;
        }}

        function setFollow(v) {{
          follow = !!v;
          jumpBtn.hidden = follow;
        }}

        function scrollToBottom() {{
          listEl.scrollTop = listEl.scrollHeight;
        }}

        function fmtTime(received_at) {{
          // received_at may be "x" in tests; best-effort.
          try {{
            const d = new Date(received_at);
            if (!isFinite(d.getTime())) return '';
            return d.toLocaleTimeString([], {{ hour: '2-digit', minute: '2-digit', second: '2-digit' }});
          }} catch (_) {{
            return '';
          }}
        }}

        function platformIconSrc(platform) {{
          const p = String(platform || '').toLowerCase();
          if (p === 'twitch') return '/assets/twitch.svg';
          if (p === 'youtube') return '/assets/youtube.svg';
          if (p === 'tiktok') return '/assets/tiktok.svg';
          return '';
        }}

        function renderOne(it) {{
          const row = document.createElement('div');
          row.className = 'msg';

          const meta = document.createElement('div');
          meta.className = 'meta';

          const pl = document.createElement('img');
          pl.className = 'platformIcon';
          const src = platformIconSrc(it.platform);
          if (src) {{
            pl.src = src;
            pl.alt = String(it.platform || '');
            pl.loading = 'lazy';
          }} else {{
            pl.hidden = true;
          }}

          const au = document.createElement('span');
          au.className = 'author';
          au.textContent = (it.author || '—');

          const tm = document.createElement('span');
          tm.className = 'time';
          tm.textContent = fmtTime(it.received_at || '');

          meta.appendChild(pl);
          meta.appendChild(au);
          meta.appendChild(tm);

          const txt = document.createElement('div');
          txt.className = 'text';
          txt.textContent = (it.text || '');

          row.appendChild(meta);
          row.appendChild(txt);
          return row;
        }}

        function renderAppend(it) {{
          const wasBottom = atBottom();
          listEl.appendChild(renderOne(it));
          if (listEl.children.length > MAX_ITEMS) {{
            listEl.removeChild(listEl.firstChild);
          }}
          if (follow && wasBottom) {{
            scrollToBottom();
          }} else {{
            setFollow(atBottom());
          }}
        }}

        listEl.addEventListener('scroll', () => {{
          setFollow(atBottom());
        }});

        jumpBtn.addEventListener('click', () => {{
          scrollToBottom();
          setFollow(true);
        }});

        let ws = null;
        let reconnectTimer = null;
        let reconnectAttempt = 0;

        function setStatus(text) {{
          statusEl.textContent = text;
        }}

        function reconnectDelayMs(attempt) {{
          // Exponential backoff with jitter: 0.5s, 1s, 2s, ... capped at 10s.
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
          // Prevent duplicate sockets/timers.
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
            try {{
              ws.send(JSON.stringify({_json_for_script(subscribe_msg)}));
            }} catch (_) {{
              // If send fails, let close handler reconnect.
            }}
          }};

          ws.onclose = () => {{
            setStatus(T.disconnected);
            scheduleReconnect();
          }};

          ws.onerror = () => {{
            // Typically followed by close; keep status informative.
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
              for (const it of items) {{
                listEl.appendChild(renderOne(it));
              }}
              scrollToBottom();
              setFollow(true);
              return;
            }}
            if (obj.op === 'patch') {{
              const p = obj.patch || {{}};
              if (p.append) {{
                renderAppend(p.append);
              }}
            }}
          }};
        }}

        // Start and keep trying while the app/server is restarted.
        connectWs();
      }})();
    </script>
  </body>
</html>"""

