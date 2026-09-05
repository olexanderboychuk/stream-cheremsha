from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from stream_cheremsha.overlays.actions_overlay import ActionsOverlayType
from stream_cheremsha.overlays.activity_overlay import ActivityOverlayType
from stream_cheremsha.overlays.battle_royale_overlay import BattleRoyaleOverlayType
from stream_cheremsha.overlays.chat_overlay import ChatOverlayType
from stream_cheremsha.overlays.community_world_overlay import CommunityWorldOverlayType
from stream_cheremsha.overlays.king_of_live_overlay import KingOfLiveOverlayType
from stream_cheremsha.overlays.layout_overlay import LayoutOverlayType
from stream_cheremsha.overlays.live_leaderboard_overlay import LiveLeaderboardOverlayType
from stream_cheremsha.overlays.models import normalize_instance_id
from stream_cheremsha.overlays.music_overlay import MusicOverlayType
from stream_cheremsha.overlays.online_overlay import OnlineOverlayType
from stream_cheremsha.overlays.signal_system_overlay import SignalSystemOverlayType
from stream_cheremsha.overlays.social_rotator_overlay import SocialRotatorOverlayType
from stream_cheremsha.overlays.stream_goal_overlay import StreamGoalOverlayType
from stream_cheremsha.overlays.stream_pet_overlay import StreamPetOverlayType
from stream_cheremsha.overlays.top_gifters_overlay import TopGiftersOverlayType
from stream_cheremsha.overlays.top_likers_overlay import TopLikersOverlayType
from stream_cheremsha.overlays.webcam_frame_overlay import WebcamFrameOverlayType


class UnknownOverlayTypeError(KeyError):
    pass


class OverlayType(Protocol):
    type: str

    def render_html(self, params: dict[str, Any]) -> str: ...

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]: ...


def _json_for_script(value: Any) -> str:
    s = json.dumps(value, ensure_ascii=False)
    # Prevent `</script>` termination and other HTML parser edge-cases.
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


@dataclass(frozen=True, slots=True)
class _DebugOverlayType:
    type: str = "debug"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "default"

        subscribe_msg = {"op": "subscribe", "type": "debug", "instance": instance, "params": {}}

        return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Overlay Debug</title>
    <style>
      html, body {{ margin: 0; padding: 0; background: transparent; color: #e5e7eb;
        font-family: system-ui, sans-serif; }}
      .box {{
        padding: 10px;
        background: rgba(10,12,18,0.60);
        border: 1px solid rgba(148,163,184,0.25);
      }}
      pre {{ white-space: pre-wrap; word-break: break-word; margin: 8px 0 0; }}
    </style>
  </head>
  <body>
    <div class="box">
      <div><strong>overlay:</strong> debug</div>
      <div><strong>instance:</strong> <span id="instance"></span></div>
      <pre id="log">connecting…</pre>
    </div>
    <script>
      (function() {{
        const instance = {_json_for_script(instance)};
        document.getElementById('instance').textContent = instance;

        const log = document.getElementById('log');
        const wsUrl =
          (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
        let ws = null;
        let tries = 0;

        function connect() {{
          tries += 1;
          const backoff = Math.min(5000, 250 + Math.floor(Math.random() * 250) + (tries * 350));
          if (tries > 1) log.textContent = 'reconnecting… (' + tries + ')';
          try {{ ws = new WebSocket(wsUrl); }}
          catch (e) {{
            log.textContent = 'ws create failed';
            setTimeout(connect, backoff);
            return;
          }}

          ws.onopen = () => {{
            tries = 0;
            const subscribeMsg = {_json_for_script(subscribe_msg)};
            ws.send(JSON.stringify(subscribeMsg));
            log.textContent = 'connected';
          }};
          ws.onmessage = (ev) => {{
            log.textContent = ev.data;
          }};
          ws.onerror = () => {{
            log.textContent = 'ws error';
          }};
          ws.onclose = () => {{
            log.textContent = 'ws closed';
            setTimeout(connect, backoff);
          }};
        }}

        connect();
      }})();
    </script>
  </body>
</html>"""

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"params": dict(params)}


class OverlayRegistry:
    def __init__(self) -> None:
        self._types: dict[str, OverlayType] = {}
        self.register(_DebugOverlayType())
        self.register(ChatOverlayType())
        self.register(MusicOverlayType())
        self.register(ActivityOverlayType())
        self.register(OnlineOverlayType())
        self.register(TopLikersOverlayType())
        self.register(TopGiftersOverlayType())
        self.register(KingOfLiveOverlayType())
        self.register(BattleRoyaleOverlayType())
        self.register(StreamPetOverlayType())
        self.register(StreamGoalOverlayType())
        self.register(LiveLeaderboardOverlayType())
        self.register(SocialRotatorOverlayType())
        self.register(CommunityWorldOverlayType())
        self.register(ActionsOverlayType())
        self.register(WebcamFrameOverlayType())
        self.register(SignalSystemOverlayType())
        self.register(LayoutOverlayType())

    def register(self, t: OverlayType) -> None:
        self._types[str(t.type)] = t

    def registered_types(self) -> list[str]:
        return sorted(self._types.keys())

    def get(self, overlay_type: str) -> OverlayType:
        k = str(overlay_type or "").strip()
        t = self._types.get(k)
        if t is None:
            raise UnknownOverlayTypeError(k)
        return t
