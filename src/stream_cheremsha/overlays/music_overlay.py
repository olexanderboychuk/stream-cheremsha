from __future__ import annotations

import json
from typing import Any

from stream_cheremsha.overlays.models import normalize_instance_id


def _json_for_script(value: Any) -> str:
    s = json.dumps(value, ensure_ascii=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


class MusicOverlayType:
    type = "music"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "default"

        subscribe_msg = {
            "op": "subscribe",
            "type": "music",
            "instance": instance,
            "params": {},
        }

        return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <meta name="referrer" content="strict-origin-when-cross-origin" />
    <title>Music Overlay</title>
    <style>
      html, body {{ margin: 0; padding: 0; background: transparent; overflow: hidden;
        height: 100%; }}
      body {{ font-family: system-ui, sans-serif; color: #e5e7eb; }}
      #wrap {{ position: absolute; inset: 0; display: block; }}
      #player {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
    </style>
  </head>
  <body>
    <div id="wrap"><div id="player"></div></div>

    <script>
      (function() {{
        const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
        let ws = null;
        let tries = 0;
        let state = null;
        let player = null;
        let playerReady = false;
        let lastTrackId = '';
        let lastVideoId = '';
        const wrapEl = document.getElementById('wrap');

        function setVisible(on) {{
          try {{
            // Avoid display:none: it can break YT iframe initialization/autoplay in some browsers.
            wrapEl.style.visibility = on ? 'visible' : 'hidden';
            wrapEl.style.opacity = on ? '1' : '0';
            wrapEl.style.pointerEvents = on ? 'auto' : 'none';
          }} catch (e) {{}}
        }}

        function sendEvent(eventName, payload) {{
          try {{
            if (!ws || ws.readyState !== 1) return;
            const msg = {{
              op: 'event',
              type: 'music',
              instance: {_json_for_script(instance)},
              event: String(eventName || ''),
              payload: payload || {{}},
            }};
            ws.send(JSON.stringify(msg));
          }} catch (e) {{}}
        }}

        function applyEmptyStateIfNeeded() {{
          const vid = currentVideoId();
          if (!vid) {{
            setVisible(false);
            try {{ if (playerReady && player) player.stopVideo(); }} catch (e) {{}}
            lastTrackId = '';
            lastVideoId = '';
            return true;
          }}
          setVisible(true);
          return false;
        }}

        function currentTrackId() {{
          const st = state && state.set_state ? state.set_state : state;
          const cur = st && st.current ? st.current : null;
          const tid = cur && cur.id ? String(cur.id) : '';
          return tid;
        }}

        function ensureIframeApi() {{
          return new Promise((resolve) => {{
            if (window.YT && window.YT.Player) {{
              resolve();
              return;
            }}
            const tag = document.createElement('script');
            tag.src = 'https://www.youtube.com/iframe_api';
            document.head.appendChild(tag);
            window.onYouTubeIframeAPIReady = function() {{
              resolve();
            }};
          }});
        }}

        function createPlayer() {{
          if (player) return;
          player = new YT.Player('player', {{
            height: '100%',
            width: '100%',
            videoId: '',
            host: 'https://www.youtube-nocookie.com',
            playerVars: {{
              autoplay: 1,
              controls: 0,
              rel: 0,
              modestbranding: 1,
              playsinline: 1,
            }},
            events: {{
              onReady: function() {{
                playerReady = true;
                try {{
                  const ifr = player.getIframe && player.getIframe();
                  if (ifr && ifr.setAttribute) {{
                    ifr.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
                  }}
                }} catch (e) {{}}
                sendEvent('ready', {{}});
                maybeLoadCurrent();
              }},
              onStateChange: function(ev) {{
                try {{
                  if (ev && ev.data === YT.PlayerState.ENDED) {{
                    sendEvent('ended', {{
                      track_id: String(lastTrackId || ''),
                      video_id: String(lastVideoId || '')
                    }});
                  }}
                }} catch (e) {{}}
              }},
              onError: function(ev) {{
                sendEvent('error', {{
                  track_id: String(lastTrackId || ''),
                  video_id: String(lastVideoId || ''),
                  code: ev && ev.data
                }});
              }},
            }}
          }});
        }}

        function currentVideoId() {{
          const st = state && state.set_state ? state.set_state : state;
          const cur = st && st.current ? st.current : null;
          const vid = cur && cur.video_id ? String(cur.video_id) : '';
          return vid;
        }}

        function isMutedByConfig() {{
          const st = state && state.set_state ? state.set_state : state;
          const cfg = st && st.config ? st.config : null;
          if (!cfg) return false;
          return cfg.autoplay_muted === undefined ? false : !!cfg.autoplay_muted;
        }}

        function maybeLoadCurrent() {{
          if (!playerReady || !player) return;
          if (applyEmptyStateIfNeeded()) return;
          const tid = currentTrackId();
          const vid = currentVideoId();
          if (!vid) return;
          if (tid && tid === lastTrackId) return;
          lastTrackId = tid;
          lastVideoId = vid;
          try {{
            // Autoplay in OBS/CEF may be blocked when unmuted. Start muted, force play,
            // then try to unmute if configured.
            try {{ player.mute(); }} catch (e) {{}}
            player.loadVideoById(vid);
            // Aggressive play() retries to avoid "stuck first frame".
            setTimeout(() => {{ try {{ player.playVideo(); }} catch (e) {{}} }}, 50);
            setTimeout(() => {{ try {{ player.playVideo(); }} catch (e) {{}} }}, 250);
            setTimeout(() => {{ try {{ player.playVideo(); }} catch (e) {{}} }}, 900);

            setTimeout(() => {{
              try {{ player.setVolume(100); }} catch (e) {{}}
              if (isMutedByConfig()) {{
                try {{ player.mute(); }} catch (e) {{}}
              }} else {{
                try {{ player.unMute(); }} catch (e) {{}}
              }}
            }}, 120);
          }} catch (e) {{}}
        }}

        function connect() {{
          tries += 1;
          const backoff = Math.min(5000, 250 + Math.floor(Math.random() * 250) + (tries * 350));
          try {{ ws = new WebSocket(wsUrl); }}
          catch (e) {{
            setTimeout(connect, backoff);
            return;
          }}
          ws.onopen = () => {{
            tries = 0;
            ws.send(JSON.stringify({_json_for_script(subscribe_msg)}));
          }};
          ws.onmessage = (ev) => {{
            let obj = null;
            try {{ obj = JSON.parse(ev.data); }} catch (e) {{ return; }}
            if (!obj || !obj.op) return;
            if (obj.op === 'initial_state') {{
              state = obj.state || null;
              maybeLoadCurrent();
              return;
            }}
            if (obj.op === 'patch') {{
              const p = obj.patch || {{}};
              if (p.set_state) {{
                state = p.set_state;
              }} else {{
                state = p;
              }}
              maybeLoadCurrent();
            }}
          }};
          ws.onclose = () => {{
            setTimeout(connect, backoff);
          }};
        }}

        ensureIframeApi().then(() => {{
          createPlayer();
          connect();
          setVisible(false);
        }});
      }})();
    </script>
  </body>
</html>"""

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        _ = params
        return {
            "current": None,
            "queue": [],
            "config": {"autoplay_muted": False, "max_queue_items": 20},
        }
