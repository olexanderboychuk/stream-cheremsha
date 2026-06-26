from __future__ import annotations

# ruff: noqa: E501
import json
from typing import Any

from stream_cheremsha.overlays.models import normalize_instance_id
from stream_cheremsha.overlays.stream_pet_overlay_config import (
    load_stream_pet_overlay_config,
    stream_pet_overlay_config_to_public_dict,
)
from stream_cheremsha.overlays.ui_locale import load_ui_locale


def _json_for_script(value: Any) -> str:
    s = json.dumps(value, ensure_ascii=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


class StreamPetOverlayType:
    type = "stream_pet"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "default"

        subscribe_msg = {
            "op": "subscribe",
            "type": "stream_pet",
            "instance": instance,
            "params": {},
        }
        locale = load_ui_locale()

        return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>StreamPet</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap" rel="stylesheet" />
    <style>
      html, body {{ margin:0; padding:0; background:transparent; overflow:hidden; height:100%; }}
      * {{ box-sizing:border-box; }}
      .root {{
        position:absolute; inset:0;
        display:flex; flex-direction:column; align-items:center; justify-content:flex-end;
        padding:16px;
        pointer-events:none;
        font-family: var(--sp-font, 'Press Start 2P', monospace);
      }}
      .energy-wrap {{
        width: min(280px, 90vw);
        margin-bottom: 10px;
        display: none;
      }}
      .root.show-bar .energy-wrap {{ display:block; }}
      .level-row {{
        margin-bottom: 6px;
        display:flex; justify-content:center;
      }}
      .level-badge {{
        color:#fde047; font-size:9px; font-weight:bold;
        text-shadow: 1px 1px 0 #000, -1px -1px 0 #000;
        letter-spacing: 0.6px;
        white-space: nowrap;
        padding: 2px 6px;
        border: 2px solid #1e293b;
        background: rgba(15,23,42,0.75);
      }}
      .level-2 .level-badge {{ color:#22d3ee; }}
      .level-3 .level-badge {{ color:#f472b6; }}
      .energy-row {{
        display:flex; justify-content:space-between; align-items:baseline;
        margin-bottom: 4px; gap: 8px;
      }}
      .energy-label {{
        color:#e2e8f0; font-size:8px;
        text-shadow: 1px 1px 0 #000;
        letter-spacing: 0.5px;
      }}
      .energy-track {{
        height: 10px; border: 2px solid #1e293b;
        background: #0f172a; border-radius: 2px; overflow:hidden;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
      }}
      .energy-fill {{
        height:100%; width:70%;
        background: linear-gradient(90deg, #22c55e, #84cc16);
        transition: width 0.6s ease, background 0.4s ease;
      }}
      .mood-hungry .energy-fill {{ background: linear-gradient(90deg, #ef4444, #f97316); }}
      .mood-hyper .energy-fill {{ background: linear-gradient(90deg, #f59e0b, #fde047); }}
      .mood-sleep .energy-fill {{ background: linear-gradient(90deg, #6366f1, #818cf8); }}
      .stage {{
        position:relative;
        width: min(220px, 75vw);
        min-height: 120px;
        display:flex; align-items:flex-end; justify-content:center;
        transform: scale(var(--sp-scale, 1));
        transform-origin: bottom center;
      }}
      .pet-cluster {{
        display:flex;
        flex-direction:column;
        align-items:center;
        position:relative;
      }}
      .bubble {{
        position:relative;
        max-width: min(300px, 90vw);
        margin-bottom: 6px;
        opacity: 0;
        transition: opacity 0.12s step-end;
        z-index: 5;
        pointer-events:none;
      }}
      .bubble.on {{ opacity: 1; }}
      .bubble-box {{
        position:relative;
        padding: 8px 10px 9px;
        background: var(--sp-bubble-bg, #fff);
        border: 3px solid var(--sp-bubble-border, #1e293b);
        border-radius: 0;
        color: var(--sp-bubble-text, #0f172a);
        font-family: 'VT323', var(--sp-font, 'Press Start 2P'), monospace;
        font-size: var(--sp-bubble-font-size, 20px);
        line-height: 1.15;
        letter-spacing: 0.4px;
        text-align: center;
        word-break: break-word;
        overflow-wrap: anywhere;
        width: fit-content;
        max-width: min(300px, 90vw);
        min-width: 48px;
        box-shadow:
          inset 2px 2px 0 rgba(255,255,255,0.45),
          4px 4px 0 var(--sp-bubble-border, #1e293b);
        image-rendering: pixelated;
      }}
      /* 8-bit pixel tail — stepped blocks pointing at pet head */
      .bubble-tail {{
        position:relative;
        width: 8px;
        height: 8px;
        margin: -3px auto 0;
        background: var(--sp-bubble-bg, #fff);
        border-left: 3px solid var(--sp-bubble-border, #1e293b);
        border-right: 3px solid var(--sp-bubble-border, #1e293b);
        border-bottom: 3px solid var(--sp-bubble-border, #1e293b);
        box-shadow:
          0 8px 0 0 var(--sp-bubble-border, #1e293b),
          0 16px 0 0 var(--sp-bubble-border, #1e293b);
      }}
      .bubble-tail::after {{
        content:'';
        position:absolute;
        top: 5px;
        left: -3px;
        width: 8px;
        height: 8px;
        background: var(--sp-bubble-bg, #fff);
        box-shadow: 0 8px 0 0 var(--sp-bubble-bg, #fff);
      }}
      .pet {{
        position:relative;
        width: 72px; height: 72px;
        image-rendering: pixelated;
      }}
      .pet-body {{
        width:100%; height:100%;
        background: var(--sp-body, #fbbf24);
        border: 3px solid var(--sp-outline, #1e293b);
        border-radius: 8px;
        position:relative;
        box-shadow: inset -4px -4px 0 rgba(0,0,0,0.15);
      }}
      .pet-eye {{
        position:absolute; top: 18px; width: 10px; height: 10px;
        background: var(--sp-eye, #1e293b); border-radius: 1px;
      }}
      .pet-eye.left {{ left: 16px; }}
      .pet-eye.right {{ right: 16px; }}
      .pet-mouth {{
        position:absolute; bottom: 16px; left:50%; transform:translateX(-50%);
        width: 20px; height: 6px; background: var(--sp-mouth, #1e293b); border-radius: 0 0 6px 6px;
      }}
      .pet-ear {{
        position:absolute; top: -8px; width: 14px; height: 14px;
        background: var(--sp-ear, #f59e0b); border: 3px solid var(--sp-outline, #1e293b);
      }}
      .pet-ear.left {{ left: 8px; transform: rotate(-12deg); }}
      .pet-ear.right {{ right: 8px; transform: rotate(12deg); }}
      .pet-collar {{
        display:none;
        position:absolute; left: 8px; right: 8px; bottom: 10px; height: 8px;
        background: var(--sp-collar, #ef4444);
        border: 2px solid var(--sp-outline, #1e293b);
        border-radius: 3px;
        z-index: 2;
      }}
      .root.show-collar .pet-collar {{ display:block; }}
      .pet-blush {{
        display:none;
        position:absolute; top: 30px; width: 8px; height: 5px;
        background: rgba(248, 113, 113, 0.55); border-radius: 50%;
      }}
      .pet-blush.left {{ left: 10px; }}
      .pet-blush.right {{ right: 10px; }}
      .root.show-blush .pet-blush {{ display:block; }}
      .pet-glasses {{
        display:none; position:absolute; top: 14px; left: 10px; right: 10px; height: 12px;
        border: 3px solid var(--sp-outline, #1e293b); border-top: 3px solid #22d3ee;
        background: rgba(34, 211, 238, 0.25); z-index: 4;
      }}
      .level-2 .pet-glasses, .level-3 .pet-glasses {{ display:block; }}
      .pet-speaker {{
        display:none; position:absolute; top: 28px; width: 10px; height: 18px;
        background: var(--sp-outline, #1e293b); border: 2px solid #a78bfa;
      }}
      .pet-speaker::after {{
        content:''; position:absolute; top: 4px; width: 4px; height: 8px;
        background: #c084fc; animation: soundWave 0.5s steps(2) infinite;
      }}
      .pet-speaker.left {{ left: -14px; }}
      .pet-speaker.right {{ right: -14px; }}
      .pet-speaker.left::after {{ right: 2px; }}
      .pet-speaker.right::after {{ left: 2px; }}
      .level-3 .pet-speaker {{ display:block; }}
      .level-3 .pet {{
        width: 84px; height: 84px;
        animation: petDj 4s linear infinite;
      }}
      .level-2.mood-hyper .pet,
      .level-2.mood-chill .pet {{
        filter: drop-shadow(0 0 8px #22c55e);
      }}
      .level-3.mood-hyper .pet {{
        filter: drop-shadow(0 0 12px #fde047);
        animation: petDj 3s linear infinite;
      }}
      .disco-fx {{
        display:none; position:absolute; inset:0; pointer-events:none; z-index: 20;
        overflow:hidden;
      }}
      .root.disco-on .disco-fx {{ display:block; }}
      .disco-flash {{
        position:absolute; inset:0;
        animation: discoFlash 0.35s steps(2) infinite;
        opacity: 0.35;
      }}
      .confetti-piece {{
        position:absolute; width: 6px; height: 6px;
        animation: confettiFall 2.2s linear infinite;
      }}
      .root.talking .pet-eye {{
        animation: eyeBlink 0.45s steps(2) infinite;
      }}
      .root.talking .pet-mouth {{
        height: 4px; animation: mouthTalk 0.25s steps(2) infinite;
        background: #a78bfa;
      }}
      .anim-shake .pet-cluster {{
        animation: clusterShake 0.8s ease-in-out !important;
      }}
      .blanket {{
        display:none; position:absolute; bottom:0; left:50%; transform:translateX(-50%);
        width: 90px; height: 36px; background: var(--sp-blanket, #818cf8); border:3px solid var(--sp-outline, #1e293b);
        border-radius: 6px 6px 0 0; z-index:2;
      }}
      .zzz {{
        display:none; position:absolute; top: 20px; right: 10px;
        color:#c7d2fe; font-size: 14px; animation: zzzFloat 2s ease-in-out infinite;
        text-shadow: 2px 2px 0 #312e81;
      }}
      .tear {{
        display:none; position:absolute; top: 28px; left: 20px;
        width: 6px; height: 10px; background:#38bdf8; border-radius: 50%;
        animation: tearDrop 1.2s ease-in infinite;
      }}
      .tear.r {{ left:auto; right: 20px; animation-delay: 0.4s; }}
      .spark {{
        display:none; position:absolute; width: 6px; height: 6px;
        background: var(--sp-spark, #fde047); box-shadow: 0 0 6px var(--sp-hyper-glow, #f59e0b);
        animation: sparkFly 1.4s linear infinite;
      }}
      .spark.s1 {{ top:10px; left:0; }}
      .spark.s2 {{ top:30px; right:0; animation-delay:0.3s; }}
      .spark.s3 {{ bottom:40px; left:-10px; animation-delay:0.6s; }}
      .custom-sprite {{
        display:none; width:100%; height:100%;
        background-size: contain; background-repeat:no-repeat; background-position:center bottom;
        image-rendering: pixelated;
      }}
      .root.has-sprite .pet-body,
      .root.has-sprite .pet-eye,
      .root.has-sprite .pet-mouth,
      .root.has-sprite .pet-ear {{ display:none; }}
      .root.has-sprite .custom-sprite {{ display:block; }}

      .mood-hungry .pet {{ animation: petSad 2s ease-in-out infinite; }}
      .mood-hungry .tear {{ display:block; }}
      .mood-chill .pet {{ animation: petWalk 3s ease-in-out infinite; }}
      .mood-hyper .pet {{ animation: petDance 0.5s ease-in-out infinite; filter: drop-shadow(0 0 8px var(--sp-hyper-glow, #fbbf24)); }}
      .mood-hyper .spark {{ display:block; }}
      .mood-sleep .pet {{ opacity: 0.85; }}
      .mood-sleep .blanket {{ display:block; }}
      .mood-sleep .zzz {{ display:block; }}
      .mood-sleep .pet-eye {{ height: 3px; top: 22px; border-radius: 2px; }}

      .anim-jump .pet {{ animation: petJump 0.6s ease-out !important; }}
      .anim-chew .pet {{ animation: petChew 0.5s ease-in-out 3 !important; }}
      .anim-backflip .pet {{ animation: petFlip 0.8s ease-in-out !important; }}
      .anim-scared .pet {{ animation: petScared 0.4s ease-in-out 2 !important; }}
      .anim-dance .pet {{ animation: petDance 0.5s ease-in-out infinite !important; }}

      @keyframes clusterShake {{
        0%,100% {{ transform: translate(0,0); }}
        15% {{ transform: translate(-4px,-6px) rotate(-2deg); }}
        30% {{ transform: translate(4px,2px) rotate(2deg); }}
        45% {{ transform: translate(-3px,4px); }}
        60% {{ transform: translate(3px,-3px); }}
      }}
      @keyframes eyeBlink {{
        0%,100% {{ transform: scaleY(1); }}
        50% {{ transform: scaleY(0.15); }}
      }}
      @keyframes mouthTalk {{
        0%,100% {{ height: 4px; }}
        50% {{ height: 9px; }}
      }}
      @keyframes soundWave {{
        0%,100% {{ opacity: 0.4; transform: scaleY(0.6); }}
        50% {{ opacity: 1; transform: scaleY(1.2); }}
      }}
      @keyframes petDj {{
        0% {{ transform: rotate(0deg); }}
        25% {{ transform: rotate(3deg); }}
        50% {{ transform: rotate(0deg); }}
        75% {{ transform: rotate(-3deg); }}
        100% {{ transform: rotate(0deg); }}
      }}
      @keyframes discoFlash {{
        0% {{ background: rgba(167,139,250,0.45); }}
        50% {{ background: rgba(34,211,238,0.45); }}
        100% {{ background: rgba(253,224,71,0.45); }}
      }}
      @keyframes confettiFall {{
        0% {{ transform: translateY(-20px) rotate(0deg); opacity: 1; }}
        100% {{ transform: translateY(180px) rotate(360deg); opacity: 0; }}
      }}

      @keyframes petWalk {{
        0%,100% {{ transform: translateX(0); }}
        50% {{ transform: translateX(8px); }}
      }}
      @keyframes petSad {{
        0%,100% {{ transform: translateY(8px) scale(0.95); }}
        50% {{ transform: translateY(10px) scale(0.93); }}
      }}
      @keyframes petDance {{
        0%,100% {{ transform: rotate(-4deg) scale(1.05); }}
        50% {{ transform: rotate(4deg) scale(1.08); }}
      }}
      @keyframes petJump {{
        0%,100% {{ transform: translateY(0); }}
        40% {{ transform: translateY(-24px); }}
      }}
      @keyframes petChew {{
        0%,100% {{ transform: scaleY(1); }}
        50% {{ transform: scaleY(0.92); }}
      }}
      @keyframes petFlip {{
        0% {{ transform: rotate(0); }}
        100% {{ transform: rotate(360deg); }}
      }}
      @keyframes petScared {{
        0%,100% {{ transform: translateX(0); }}
        25% {{ transform: translateX(-6px); }}
        75% {{ transform: translateX(6px); }}
      }}
      @keyframes tearDrop {{
        0% {{ opacity:1; transform: translateY(0); }}
        100% {{ opacity:0; transform: translateY(18px); }}
      }}
      @keyframes sparkFly {{
        0% {{ opacity:0; transform: translate(0,0) scale(0.5); }}
        30% {{ opacity:1; }}
        100% {{ opacity:0; transform: translate(12px,-20px) scale(1.2); }}
      }}
      @keyframes zzzFloat {{
        0%,100% {{ opacity:0.4; transform: translateY(0); }}
        50% {{ opacity:1; transform: translateY(-8px); }}
      }}
    </style>
  </head>
  <body>
    <div class="root mood-chill level-1" id="root">
      <div class="disco-fx" id="discoFx" aria-hidden="true">
        <div class="disco-flash"></div>
      </div>
      <div class="level-row"><div class="level-badge" id="levelBadge">LVL 1</div></div>
      <div class="energy-wrap" id="energyWrap">
        <div class="energy-label" id="energyLabel">ENERGY</div>
        <div class="energy-track"><div class="energy-fill" id="energyFill"></div></div>
      </div>
      <div class="stage" id="stage">
        <div class="pet-cluster" id="petCluster">
          <div class="bubble" id="bubble">
            <div class="bubble-box"><span id="bubbleText"></span></div>
            <div class="bubble-tail" aria-hidden="true"></div>
          </div>
          <div class="pet-speaker left" aria-hidden="true"></div>
          <div class="pet-speaker right" aria-hidden="true"></div>
          <div class="pet" id="pet">
          <div class="custom-sprite" id="customSprite"></div>
          <div class="pet-ear left"></div>
          <div class="pet-ear right"></div>
          <div class="pet-body">
            <div class="pet-glasses" aria-hidden="true"></div>
            <div class="pet-eye left"></div>
            <div class="pet-eye right"></div>
            <div class="pet-blush left"></div>
            <div class="pet-blush right"></div>
            <div class="pet-collar"></div>
            <div class="pet-mouth"></div>
          </div>
          <div class="tear"></div>
          <div class="tear r"></div>
          <div class="spark s1"></div>
          <div class="spark s2"></div>
          <div class="spark s3"></div>
          </div>
        </div>
        <div class="blanket"></div>
        <div class="zzz">Zzz</div>
      </div>
    </div>
    <script>
      (function() {{
        const locale = {_json_for_script(locale)};
        const T = {{
          uk: {{ energy: 'ЕНЕРГІЯ', level: 'РІВЕНЬ' }},
          en: {{ energy: 'ENERGY', level: 'LVL' }}
        }};
        function tr(key) {{
          const row = T[locale] || T.uk;
          return row[key] || key;
        }}

        const root = document.getElementById('root');
        const bubble = document.getElementById('bubble');
        const bubbleText = document.getElementById('bubbleText');
        const energyWrap = document.getElementById('energyWrap');
        const energyFill = document.getElementById('energyFill');
        const energyLabel = document.getElementById('energyLabel');
        const levelBadge = document.getElementById('levelBadge');
        const customSprite = document.getElementById('customSprite');
        const pet = document.getElementById('pet');
        const petCluster = document.getElementById('petCluster');
        const discoFx = document.getElementById('discoFx');
        const stage = document.getElementById('stage');

        let cfg = null;
        let energy = 70;
        let mood = 'chill';
        let level = 1;
        let animSeq = 0;
        let bubbleTimer = null;
        let talkTimer = null;

        const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
        let ws = null;
        let tries = 0;
        const subscribeMsg = {_json_for_script(subscribe_msg)};

        function clamp(n, lo, hi) {{
          return Math.max(lo, Math.min(hi, n));
        }}

        function applyAppearance(app) {{
          const a = app || {{}};
          root.style.setProperty('--sp-body', a.body || '#fbbf24');
          root.style.setProperty('--sp-ear', a.ear || '#f59e0b');
          root.style.setProperty('--sp-outline', a.outline || '#1e293b');
          root.style.setProperty('--sp-eye', a.eye || '#1e293b');
          root.style.setProperty('--sp-mouth', a.mouth || '#1e293b');
          root.style.setProperty('--sp-collar', a.collar || '#ef4444');
          root.style.setProperty('--sp-blanket', a.blanket || '#818cf8');
          root.style.setProperty('--sp-spark', a.spark || '#fde047');
          root.style.setProperty('--sp-hyper-glow', a.hyper_glow || '#fbbf24');
          root.style.setProperty('--sp-bubble-bg', a.bubble_bg || '#ffffff');
          root.style.setProperty('--sp-bubble-border', a.bubble_border || '#1e293b');
          root.style.setProperty('--sp-bubble-text', a.bubble_text || '#0f172a');
          root.classList.toggle('show-collar', a.collar_enabled !== false && a.collar_enabled !== 0);
          root.classList.toggle('show-blush', a.blush_enabled !== false && a.blush_enabled !== 0);
        }}

        function applyCfg(c) {{
          cfg = c || {{}};
          const font = (cfg.bubble_font_family || 'Press Start 2P').trim();
          root.style.setProperty('--sp-font', "'" + font.replace(/'/g, '') + "', monospace");
          const bubblePx = clamp(parseInt(cfg.bubble_font_size_px, 10) || 20, 12, 48);
          root.style.setProperty('--sp-bubble-font-size', bubblePx + 'px');
          const scale = clamp(parseInt(cfg.pet_scale_pct, 10) || 100, 50, 200) / 100;
          root.style.setProperty('--sp-scale', String(scale));
          root.classList.toggle('show-bar', cfg.show_energy_bar !== false && cfg.show_energy_bar !== 0);
          const sprite = (cfg.pet_sprite_url || '').trim();
          root.classList.toggle('has-sprite', !!sprite);
          if (sprite) customSprite.style.backgroundImage = "url('" + sprite.replace(/'/g, '%27') + "')";
          else customSprite.style.backgroundImage = '';
          applyAppearance(cfg.appearance || null);
          energyLabel.textContent = tr('energy');
        }}

        function setMood(m) {{
          mood = m || 'chill';
          root.classList.remove('mood-hungry','mood-chill','mood-hyper','mood-sleep');
          root.classList.add('mood-' + mood);
        }}

        function setEnergy(e) {{
          energy = clamp(Number(e) || 0, 0, 100);
          energyFill.style.width = energy.toFixed(1) + '%';
        }}

        function setLevel(lv) {{
          level = clamp(parseInt(lv, 10) || 1, 1, 3);
          root.classList.remove('level-1','level-2','level-3');
          root.classList.add('level-' + level);
          if (levelBadge) levelBadge.textContent = tr('level') + ' ' + level;
        }}

        setLevel(1);

        function setDisco(on) {{
          root.classList.toggle('disco-on', !!on);
          if (!on) return;
          if (discoFx.querySelectorAll('.confetti-piece').length > 0) return;
          const colors = ['#f472b6','#22d3ee','#fde047','#a78bfa','#4ade80'];
          for (let i = 0; i < 10; i++) {{
            const p = document.createElement('div');
            p.className = 'confetti-piece';
            p.style.left = (8 + Math.random() * 84) + '%';
            p.style.top = (-10 - Math.random() * 30) + 'px';
            p.style.background = colors[i % colors.length];
            p.style.animationDelay = (Math.random() * 1.2) + 's';
            p.style.animationDuration = (1.6 + Math.random() * 1.2) + 's';
            discoFx.appendChild(p);
          }}
        }}

        function setTalking(on) {{
          root.classList.toggle('talking', !!on);
        }}

        function clearBubbleTimer() {{
          if (bubbleTimer) {{ clearTimeout(bubbleTimer); bubbleTimer = null; }}
          if (talkTimer) {{ clearTimeout(talkTimer); talkTimer = null; }}
          setTalking(false);
        }}

        function showSpeech(sp) {{
          clearBubbleTimer();
          if (!sp || !sp.text) {{
            bubble.classList.remove('on');
            bubbleText.textContent = '';
            setTalking(false);
            return;
          }}
          bubbleText.textContent = String(sp.text);
          bubble.classList.add('on');
          setTalking(true);
          const ttl = parseInt(sp.ttl_ms, 10);
          if (ttl > 0) {{
            bubbleTimer = setTimeout(() => {{
              bubble.classList.remove('on');
              setTalking(false);
            }}, ttl);
          }}
          const anim = (sp.anim || '').trim();
          if (anim) {{
            root.classList.remove('anim-jump','anim-chew','anim-backflip','anim-scared','anim-shake','anim-dance');
            petCluster.classList.remove('anim-shake');
            void root.offsetWidth;
            if (anim === 'shake') {{
              petCluster.classList.add('anim-shake');
              setTimeout(() => petCluster.classList.remove('anim-shake'), 900);
            }} else {{
              root.classList.add('anim-' + anim);
              setTimeout(() => root.classList.remove('anim-jump','anim-chew','anim-backflip','anim-scared','anim-dance'), 1200);
            }}
          }}
        }}

        function applyState(st) {{
          if (!st) return;
          if (st.config) applyCfg(st.config);
          if (st.energy !== undefined) setEnergy(st.energy);
          if (st.mood) setMood(st.mood);
          if (st.level !== undefined) setLevel(st.level);
          if (st.disco_active !== undefined) setDisco(st.disco_active);
          if (st.anim_seq !== undefined && st.anim_seq !== animSeq) {{
            animSeq = st.anim_seq;
            void pet.offsetWidth;
          }}
          if (st.speech !== undefined) showSpeech(st.speech);
        }}

        function handleMsg(data) {{
          if (data.op === 'initial_state') applyState(data.state || {{}});
          if (data.op === 'patch') applyState(data.patch || {{}});
        }}

        function connect() {{
          tries += 1;
          const backoff = Math.min(5000, 250 + Math.floor(Math.random() * 250) + (tries * 350));
          try {{ ws = new WebSocket(wsUrl); }}
          catch (e) {{ setTimeout(connect, backoff); return; }}
          ws.onopen = () => {{
            tries = 0;
            ws.send(JSON.stringify(subscribeMsg));
          }};
          ws.onmessage = (ev) => {{
            try {{ handleMsg(JSON.parse(ev.data)); }}
            catch (e) {{}}
          }};
          ws.onclose = () => setTimeout(connect, backoff);
        }}

        connect();
      }})();
    </script>
  </body>
</html>"""

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        cfg = load_stream_pet_overlay_config()
        return {
            "config": stream_pet_overlay_config_to_public_dict(cfg),
            "energy": float(cfg.initial_energy),
            "mood": "chill",
            "level": 1,
            "evolution_count": 0,
            "disco_active": False,
            "sleeping": False,
            "speech": None,
            "anim_seq": 0,
            "last_donor": "",
        }
