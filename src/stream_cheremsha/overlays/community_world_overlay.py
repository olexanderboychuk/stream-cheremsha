from __future__ import annotations

# ruff: noqa: E501
import json
from typing import Any

from stream_cheremsha.overlays.community_world_config import (
    community_world_overlay_config_to_public_dict,
    load_community_world_overlay_config,
)
from stream_cheremsha.overlays.community_world_session import CommunityWorldSession
from stream_cheremsha.overlays.models import normalize_instance_id
from stream_cheremsha.overlays.ui_locale import load_ui_locale
from stream_cheremsha.persistence.community_world_sqlite import fetch_village_elders


def _json_for_script(value: Any) -> str:
    s = json.dumps(value, ensure_ascii=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


class CommunityWorldOverlayType:
    type = "community_world"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "default"

        locale = load_ui_locale()
        subscribe_msg = {
            "op": "subscribe",
            "type": "community_world",
            "instance": instance,
            "params": {},
        }

        return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Community World</title>
    <style>
      html, body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; height: 100%; }}
      * {{ box-sizing: border-box; }}
      .world {{
        position: absolute; inset: 0;
        font-family: var(--cw-font, system-ui, sans-serif);
        display: flex; flex-direction: column; align-items: stretch;
        justify-content: flex-start;
        overflow: hidden;
        user-select: none;
      }}
      .sky {{
        position: absolute; inset: 0;
        background: linear-gradient(180deg, var(--sky1), var(--sky2));
        pointer-events: none;
      }}
      .ground {{
        position: absolute; left: 0; right: 0; bottom: 0; height: 34%;
        background: linear-gradient(180deg, var(--ground1), var(--ground2));
        border-top: 3px solid rgba(0,0,0,0.25);
        pointer-events: none;
      }}
      .cloud {{
        position: absolute; top: 8%; width: 90px; height: 26px;
        background: var(--cloud, rgba(255,255,255,0.22)); border-radius: 999px;
        animation: drift 42s linear infinite; pointer-events: none;
      }}
      .cloud::before {{ content:''; position:absolute; top:-12px; left:16px; width:40px; height:34px;
        background:inherit; border-radius:50%; }}
      .cloud::after {{ content:''; position:absolute; top:-7px; left:44px; width:30px; height:26px;
        background:inherit; border-radius:50%; }}
      .cloud.c2 {{ top: 22%; transform: scale(0.7); animation-duration: 64s; animation-delay: -20s; }}
      .cloud.c3 {{ top: 3%; transform: scale(1.25); animation-duration: 78s; animation-delay: -55s; }}
      @keyframes drift {{ from {{ left: -120px; }} to {{ left: 105%; }} }}

      .world.theme-ukrainian {{
        --sky1: #7fb6dd; --sky2: #e9f5ff;
        --ground1: #7cb342; --ground2: #3f6b2c;
        --cloud: rgba(255,255,255,0.55);
        --panel: rgba(20,28,46,0.55);
      }}
      .world.theme-pixel {{
        --sky1: #1b2b4b; --sky2: #35507f;
        --ground1: #2e7d32; --ground2: #1b5e20;
        --cloud: rgba(255,255,255,0.25);
        --panel: rgba(10,15,30,0.6);
      }}
      .world.theme-fantasy {{
        --sky1: #2e1065; --sky2: #7c3aed;
        --ground1: #6d28d9; --ground2: #312e81;
        --cloud: rgba(255,255,255,0.15);
        --panel: rgba(30,10,60,0.55);
      }}
      .world.theme-cyber {{
        --sky1: #05070f; --sky2: #0b1a33;
        --ground1: #0f2b3a; --ground2: #06202e;
        --cloud: rgba(100,200,255,0.18);
        --panel: rgba(5,10,20,0.65);
      }}
      .theme-pixel .building .glyph {{ image-rendering: pixelated; filter: drop-shadow(0 4px 0 rgba(0,0,0,0.55)) saturate(1.2); }}
      .theme-fantasy .building .glyph {{ filter: drop-shadow(0 4px 6px rgba(0,0,0,0.45)) saturate(1.5) hue-rotate(-20deg); }}
      .theme-cyber .building .glyph {{ filter: drop-shadow(0 0 8px rgba(34,211,238,0.6)) saturate(1.3) hue-rotate(120deg); }}
      .theme-cyber .cloud {{ background: rgba(34,211,238,0.22); }}

      .layout-compact .content {{
        position: absolute; left: 8px; right: 8px; bottom: 8px; top: auto;
        max-height: 92%; justify-content: flex-end; gap: 6px; padding: 0;
        z-index: 3;
      }}
      .layout-compact .village-scene {{
        position: absolute; inset: 0; z-index: 1; pointer-events: none;
        display: flex; align-items: flex-end; justify-content: center;
      }}
      .layout-compact .village-scene .village {{
        flex-wrap: wrap; gap: 4px; padding: 6px;
      }}
      .layout-compact .village-scene .building .glyph {{
        font-size: calc(26px * var(--cw-scale, 1));
      }}
      .layout-compact .village-scene .building .bname {{
        font-size: calc(8px * var(--cw-scale, 1));
      }}
      .layout-compact .panel {{
        padding: 8px 10px;
        background: var(--panel, rgba(10,12,18,0.68));
        box-shadow: 0 4px 14px rgba(0,0,0,0.3);
      }}
      .layout-compact .hud {{ gap: 8px; }}
      .layout-compact .level-badge {{ min-width: 48px; padding: 5px 8px; font-size: 13px; }}
      .layout-compact .counts {{ font-size: 10px; }}
      .layout-compact .count-chip {{ padding: 1px 7px; }}
      .layout-compact .feed-mini {{ max-height: 26%; overflow: hidden; }}
      .layout-compact .feed-item {{ font-size: 11px; padding: 3px 6px; }}

      .content {{
        position: relative; z-index: 2;
        flex: 1 1 auto; min-height: 0;
        display: flex; flex-direction: column; align-items: stretch;
        padding: 12px; gap: 8px;
      }}
      .panel {{
        background: var(--panel, rgba(10,12,18,0.55));
        border: 1px solid rgba(255,255,255,0.14);
        border-radius: 14px;
        padding: 10px 12px;
        color: var(--cw-text, #f1f5f9);
        font-size: var(--cw-font-size, 16px);
      }}
      .title {{ color: var(--cw-title, #fde047); font-weight: 800; letter-spacing: 0.04em; }}
      .sub {{ color: rgba(241,245,249,0.78); font-size: 12px; }}

      .hud {{
        display: flex; flex-direction: row; align-items: center; gap: 10px;
      }}
      .level-badge {{
        flex: 0 0 auto;
        min-width: 56px; text-align: center;
        padding: 6px 10px;
        background: var(--accent, #fde047);
        color: #1c1917; font-weight: 900; font-size: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.35);
      }}
      .xp-wrap {{ flex: 1 1 auto; min-width: 0; }}
      .xp-row {{ display: flex; flex-direction: row; justify-content: space-between;
        font-size: 11px; color: rgba(241,245,249,0.85); font-weight: 700; }}
      .xp-track {{ height: 10px; margin-top: 3px; border-radius: 999px; overflow: hidden;
        background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.14); }}
      .xp-fill {{ height: 100%; width: 0%; border-radius: 999px;
        background: linear-gradient(90deg, var(--progress, #4ade80), var(--accent, #fde047));
        transition: width 0.6s ease; }}
      .counts {{ display: flex; flex-direction: row; gap: 8px; flex-wrap: wrap;
        font-size: 11px; font-weight: 700; color: rgba(241,245,249,0.9); }}
      .count-chip {{ background: rgba(0,0,0,0.28); border: 1px solid rgba(255,255,255,0.12);
        border-radius: 999px; padding: 2px 8px; }}

      .village-wrap {{ flex: 1 1 auto; min-height: 0; display: flex; align-items: flex-end;
        justify-content: center; position: relative; }}
      .village {{ display: flex; flex-direction: row; align-items: flex-end; gap: 6px;
        padding: 8px; }}
      .building {{ display: flex; flex-direction: column; align-items: center; gap: 2px;
        transform-origin: bottom center; animation: popIn 0.5s cubic-bezier(0.34,1.56,0.64,1); }}
      @keyframes popIn {{ 0% {{ transform: scale(0); opacity: 0; }} 100% {{ transform: scale(1); opacity: 1; }} }}
      .building .glyph {{ font-size: calc(34px * var(--cw-scale, 1)); line-height: 1;
        filter: drop-shadow(0 4px 6px rgba(0,0,0,0.45)); }}
      .building .bname {{ font-size: calc(9px * var(--cw-scale, 1)); font-weight: 800;
        color: rgba(255,255,255,0.92); text-shadow: 0 1px 3px rgba(0,0,0,0.8);
        white-space: nowrap; }}
      .building.founder .glyph {{ animation: founderBob 2.2s ease-in-out infinite; }}
      @keyframes founderBob {{ 0%,100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-5px); }} }}
      .founder-tag {{ position: absolute; top: 0; left: 50%; transform: translateX(-50%);
        font-size: 10px; font-weight: 800; color: var(--accent, #fde047);
        background: rgba(0,0,0,0.45); border: 1px solid rgba(255,255,255,0.2);
        padding: 2px 8px; border-radius: 999px; white-space: nowrap; }}

      .quests {{ display: flex; flex-direction: column; gap: 6px; }}
      .quest {{ display: flex; flex-direction: column; gap: 3px; }}
      .quest-head {{ display: flex; flex-direction: row; justify-content: space-between;
        align-items: center; font-size: 12px; font-weight: 700; gap: 6px; }}
      .quest-name {{ min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
      .quest-target {{ flex: 0 0 auto; white-space: nowrap; font-size: 11px; color: rgba(241,245,249,0.8); }}
      .quest.done .quest-head {{ color: #86efac; }}
      .quest-track {{ height: 8px; border-radius: 999px; overflow: hidden;
        background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.12); }}
      .quest-fill {{ height: 100%; width: 0%; border-radius: 999px;
        background: var(--progress, #4ade80); transition: width 0.5s ease; }}
      .quest.done .quest-fill {{ background: #86efac; }}
      .quest-icon {{ margin-right: 4px; }}

      .side {{
        position: absolute; z-index: 3; top: 88px; right: 10px; bottom: 10px;
        width: 200px; display: flex; flex-direction: column; gap: 8px;
        pointer-events: none;
      }}
      .feed {{ flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column;
        gap: 4px; overflow: hidden; }}
      .feed-item {{ display: flex; flex-direction: row; align-items: center; gap: 6px;
        font-size: 12px; background: var(--panel, rgba(10,12,18,0.5));
        border: 1px solid rgba(255,255,255,0.12); border-radius: 10px; padding: 4px 8px;
        animation: slideIn 0.35s ease; }}
      @keyframes slideIn {{ from {{ transform: translateX(14px); opacity: 0; }} }}
      .feed-item .fi {{
        flex: 0 0 auto; width: 18px; height: 18px; border-radius: 999px;
        display: flex; align-items: center; justify-content: center;
        font-size: 12px; overflow: hidden; background: rgba(255,255,255,0.12);
      }}
      .feed-item .fi img {{ width: 100%; height: 100%; object-fit: cover; }}
      .feed-item .ft {{ min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
      .feed-item .fd {{ color: rgba(241,245,249,0.65); }}

      .passports {{ position: absolute; z-index: 3; left: 10px; bottom: 10px;
        width: 210px; display: flex; flex-direction: column; gap: 5px; }}
      .passport {{ display: flex; flex-direction: row; align-items: center; gap: 7px;
        font-size: 12px; }}
      .passport .av {{ flex: 0 0 auto; width: 24px; height: 24px; border-radius: 999px;
        background: rgba(255,255,255,0.14); overflow: hidden;
        display: flex; align-items: center; justify-content: center; font-weight: 800; }}
      .passport .av img {{ width: 100%; height: 100%; object-fit: cover; }}
      .passport .pn {{ min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        font-weight: 700; }}
      .passport .badges {{ margin-left: auto; display: flex; flex-direction: row; gap: 1px;
        font-size: 12px; }}
      .passport .pt {{ color: rgba(241,245,249,0.6); font-size: 10px; margin-left: 4px; }}

      .elders {{ position: absolute; z-index: 3; left: 50%; bottom: 8px; transform: translateX(-50%);
        display: flex; flex-direction: row; gap: 6px; flex-wrap: wrap; justify-content: center;
        max-width: 92%; }}
      .elder {{ display: flex; flex-direction: row; align-items: center; gap: 4px;
        font-size: 10px; font-weight: 700; color: rgba(255,255,255,0.9);
        background: rgba(0,0,0,0.35); border: 1px solid rgba(255,255,255,0.14);
        border-radius: 999px; padding: 2px 8px; }}

      .celebrate {{
        position: absolute; inset: 0; z-index: 20; pointer-events: none;
        display: flex; align-items: center; justify-content: center;
      }}
      .celebrate .banner {{
        font-size: calc(22px * var(--cw-scale, 1)); font-weight: 900;
        color: var(--accent, #fde047); text-shadow: 0 3px 10px rgba(0,0,0,0.85);
        background: rgba(0,0,0,0.5); border: 2px solid rgba(255,255,255,0.25);
        border-radius: 16px; padding: 10px 22px;
        animation: bannerIn 0.5s cubic-bezier(0.34,1.56,0.64,1);
      }}
      @keyframes bannerIn {{ 0% {{ transform: scale(0.4); opacity: 0; }} 100% {{ transform: scale(1); opacity: 1; }} }}
      .confetti {{ position: absolute; width: 8px; height: 8px;
        animation: confFall linear forwards; }}
      @keyframes confFall {{
        0% {{ transform: translateY(-40px) rotate(0); opacity: 1; }}
        100% {{ transform: translateY(105vh) rotate(720deg); opacity: 0; }}
      }}
    </style>
  </head>
  <body>
    <div id="root" class="world theme-ukrainian"></div>
    <script>
      (function() {{
        const locale = {_json_for_script(locale)};
        const T = locale === 'en' ? {{
          level: 'LVL', xp: 'XP', to: 'до', village: 'Село', follows: 'Фолови',
          likes: 'Лайки', shares: 'Шери', gifts: 'Койни', viewers: 'Глядачів',
          quest: 'Завдання', questDone: 'Виконано!', founder: 'Засновано',
          building: 'Нова будівля', questFinished: 'Завдання виконано!',
          levelUp: 'Село зросло до рівня', elders: 'Старійшини',
          followsK: 'follows', likesK: 'likes', sharesK: 'shares', giftsK: 'gift coins',
          viewersK: 'viewers',
        }} : {{
          level: 'РІВЕНЬ', xp: 'ДОСВІД', to: 'до', village: 'Село', follows: 'Фолови',
          likes: 'Лайки', shares: 'Шери', gifts: 'Койни', viewers: 'Глядачів',
          quest: 'Завдання', questDone: 'Виконано!', founder: 'Засновано',
          building: 'Нова будівля', questFinished: 'Завдання виконано!',
          levelUp: 'Село зросло до рівня', elders: 'Старійшини',
          followsK: 'фолови', likesK: 'лайки', sharesK: 'шери', giftsK: 'койни',
          viewersK: 'глядачів',
        }};
        const NAMES = locale === 'en' ? {{
          house: 'House', tree: 'Tree', house2: 'House', well: 'Well', bridge: 'Bridge',
          church: 'Church', market: 'Market', monument: 'Monument', tower: 'Tower',
          castle: 'Castle',
          quest_likes: 'Likes', quest_shares: 'Shares', quest_gifts: 'Gift coins',
          quest_follows: 'Follows',
        }} : {{
          house: 'Хата', tree: 'Дерево', house2: 'Хата', well: 'Криниця', bridge: 'Міст',
          church: 'Церква', market: 'Маркет', monument: 'Пам\u2019ятник', tower: 'Вежа',
          castle: 'Замок',
          quest_likes: 'Лайки', quest_shares: 'Шери', quest_gifts: 'Койни',
          quest_follows: 'Фолови',
        }};
        const BADGES = locale === 'en' ? {{
          founder: 'Founder', gifter: 'First gift', supporter: 'Supporter',
          top_liker: 'Top liker', sharer: 'Sharer', regular: 'Regular',
          quest_finisher: 'Quest finisher', battle_champion: 'Battle champion',
        }} : {{
          founder: 'Засновник', gifter: 'Перший подарунок', supporter: 'Прихильник',
          top_liker: 'Топ лайкер', sharer: 'Шер', regular: 'Завсідник',
          quest_finisher: 'Виконав квест', battle_champion: 'Чемпіон батлу',
        }};
        const BADGE_ICONS = {{
          founder: '👑', gifter: '💝', supporter: '🤝', top_liker: '👍', sharer: '🔁',
          regular: '☕', quest_finisher: '🎯', battle_champion: '🏆',
        }};
        const FEED_ICONS = {{
          follow: '❤️', join: '👋', like: '👍', share: '🔁', gift: '🎁',
          battle: '🏆', chat: '💬',
        }};
        const BUILDINGS = {{
          house: '🏠', tree: '🌳', house2: '🏡', well: '⛲', bridge: '🌉',
          church: '⛪', market: '🛒', monument: '🗿', tower: '🗼', castle: '🏰',
        }};
        const QUEST_ICONS = {{ likes: '👍', shares: '🔁', gifts: '🎁', follows: '❤️' }};

        const root = document.getElementById('root');
        let ws = null; let tries = 0;
        let cfg = {{}};
        let cfgSig = '';
        let unlockedIds = new Set();
        let lastQuestSeq = 0;
        let lastFeedSeq = 0;
        let lastLevel = 1;
        const subscribeMsg = {_json_for_script(subscribe_msg)};

        function esc(s) {{
          return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {{
            return {{ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }}[c];
          }});
        }}

        function cfgSignature(c) {{
          c = c || {{}};
          return [c.theme, c.layout_mode, c.font_family, c.font_size_px, c.scale_pct,
            !!c.show_level, !!c.show_quests, !!c.show_recognition, !!c.show_passports,
            !!c.show_buildings, !!c.show_elders, !!c.quiet_mode].join('|');
        }}

        function applyTheme(theme) {{
          const t = String(theme || 'ukrainian');
          root.classList.remove('theme-ukrainian','theme-pixel','theme-fantasy','theme-cyber');
          root.classList.add('theme-' + (['pixel','fantasy','cyber'].indexOf(t) >= 0 ? t : 'ukrainian'));
        }}

        function applyCfg(c) {{
          cfg = c || {{}};
          const sig = cfgSignature(cfg);
          if (sig !== cfgSig) {{ cfgSig = sig; buildHtml(); }}
          applyTheme(cfg.theme);
          const font = (cfg.font_family || 'Segoe UI').trim();
          root.style.setProperty('--cw-font', "'" + font.replace(/'/g, '') + "', sans-serif");
          const scale = Math.max(0.4, Math.min(2, parseInt(cfg.scale_pct, 10) || 100) / 100);
          root.style.setProperty('--cw-scale', String(scale));
          root.style.setProperty('--cw-title', cfg.color_title || '#fde047');
          root.style.setProperty('--cw-text', cfg.color_text || '#f1f5f9');
          root.style.setProperty('--cw-accent', cfg.color_accent || '#a78bfa');
          root.style.setProperty('--accent', cfg.color_accent || '#a78bfa');
          root.style.setProperty('--progress', cfg.color_progress || '#4ade80');
          if (cfg.color_quest_bg) {{
            root.style.setProperty('--panel', cfg.color_quest_bg);
          }} else {{
            root.style.removeProperty('--panel');
          }}
          const fs = Math.max(8, Math.min(120, parseInt(cfg.font_size_px, 10) || 16));
          root.style.setProperty('--cw-font-size', fs + 'px');
        }}

        function buildHtml() {{
          const show = (k, dflt) => cfg[k] !== false && cfg[k] !== 0 && cfg[k] !== '0' && cfg[k] !== 'false';
          const compact = String(cfg.layout_mode || 'full').toLowerCase() === 'compact';
          root.classList.toggle('layout-compact', compact);
          root.classList.toggle('layout-full', !compact);
          const parts = [];
          parts.push('<div class="sky"></div><div class="cloud c1"></div><div class="cloud c2"></div><div class="cloud c3"></div><div class="ground"></div>');

          if (compact && show('show_buildings', true)) {{
            parts.push('<div class="village-scene"><div class="village" id="village"></div></div>');
          }}

          parts.push('<div class="content">');
          if (compact) {{
            if (show('show_level', true)) {{
              parts.push('<div class="panel hud"><div class="level-badge" id="levelBadge">РІВЕНЬ 1</div>' +
                '<div class="xp-wrap"><div class="xp-row"><span id="xpLabel">ДОСВІД 0</span><span id="xpNext">0/120</span></div>' +
                '<div class="xp-track"><div class="xp-fill" id="xpFill" style="width:0%"></div></div></div></div>');
              parts.push('<div class="counts" id="counts"></div>');
            }}
            if (show('show_quests', true)) {{
              parts.push('<div class="panel quests" id="quests"></div>');
            }}
            if (show('show_recognition', true)) {{
              parts.push('<div class="panel feed-mini" id="feedMini"></div>');
            }}
          }} else {{
            if (show('show_level', true)) {{
              parts.push('<div class="panel hud"><div class="level-badge" id="levelBadge">РІВЕНЬ 1</div>' +
                '<div class="xp-wrap"><div class="xp-row"><span id="xpLabel">ДОСВІД 0</span><span id="xpNext">0/120</span></div>' +
                '<div class="xp-track"><div class="xp-fill" id="xpFill" style="width:0%"></div></div></div></div>');
              parts.push('<div class="counts" id="counts"></div>');
            }}
            if (show('show_quests', true)) {{
              parts.push('<div class="panel quests" id="quests"></div>');
            }}
            if (show('show_buildings', true)) {{
              parts.push('<div class="village-wrap"><div class="village" id="village"></div></div>');
            }}
            parts.push('</div>');

            if (show('show_recognition', true)) {{
              parts.push('<div class="side"><div class="panel" style="display:flex;flex-direction:column;min-height:0;">' +
                '<div class="title" style="font-size:11px;margin-bottom:4px;">' + esc(T.quest) + '</div>' +
                '<div class="feed" id="feed"></div></div></div>');
            }}
            if (show('show_passports', true)) {{
              parts.push('<div class="passports" id="passports"></div>');
            }}
            if (show('show_elders', true)) {{
              parts.push('<div class="elders" id="elders"></div>');
            }}
          }}
          parts.push('<div class="celebrate" id="celebrate" style="display:none;"></div>');
          root.innerHTML = parts.join('');
          lastFeedSeq = 0;
        }}

        function renderCounts(st) {{
          const el = document.getElementById('counts');
          if (!el) return;
          const chips = [
            [T.followsK, st.follows], [T.likesK, st.likes], [T.sharesK, st.shares],
            [T.giftsK, st.gift_coins], [T.viewersK, st.unique_viewers],
          ];
          el.innerHTML = chips.map(function (c) {{
            return '<span class="count-chip">' + esc(c[0]) + ' · ' + esc(String(c[1])) + '</span>';
          }}).join('');
        }}

        function renderLevel(st) {{
          const badge = document.getElementById('levelBadge');
          const fill = document.getElementById('xpFill');
          const xpLabel = document.getElementById('xpLabel');
          const xpNext = document.getElementById('xpNext');
          if (badge) badge.textContent = T.level + ' ' + st.level;
          if (fill) fill.style.width = Math.max(0, Math.min(100, Number(st.progress) * 100 || 0)) + '%';
          if (xpLabel) xpLabel.textContent = T.xp + ' ' + st.xp;
          if (xpNext) xpNext.textContent = T.xp + ' ' + st.xp + ' / ' + (st.xp + st.xp_to_next);
        }}

        function renderVillage(st, celebrate) {{
          const el = document.getElementById('village');
          if (!el) return;
          const unlocked = (st.buildings || []).filter(function (b) {{ return b && b.unlocked; }});
          const nextUnlocked = new Set(unlocked.map(function (b) {{ return b.id; }}));
          const fresh = [];
          nextUnlocked.forEach(function (id) {{ if (!unlockedIds.has(id)) fresh.push(id); }});
          const founderId = unlocked.length ? (st.founder ? 'house' : '') : '';
          el.innerHTML = unlocked.map(function (b) {{
            const glyph = BUILDINGS[b.id] || '🏠';
            const name = NAMES[b.id] || b.id;
            const founderCls = (st.founder && (b.id === 'house' || b.id === 'house2')) ? ' founder' : '';
            return '<div class="building' + founderCls + '" data-id="' + esc(b.id) + '">' +
              '<div class="glyph">' + glyph + '</div>' +
              '<div class="bname">' + esc(name) + '</div></div>';
          }}).join('');
          unlockedIds = nextUnlocked;
          if (fresh.length) celebrate('b', NAMES[fresh[0]] || fresh[0]);
          if (st.founder) {{
            const wrap = document.querySelector('.village-wrap, .village-scene');
            if (wrap && !document.getElementById('founderTag')) {{
              const tag = document.createElement('div');
              tag.id = 'founderTag'; tag.className = 'founder-tag';
              tag.textContent = T.founder + ': ' + st.founder;
              wrap.appendChild(tag);
            }}
          }}
        }}

        function renderQuests(st) {{
          const el = document.getElementById('quests');
          if (!el) return;
          const doneIds = {{}};
          (st.quests || []).forEach(function (q) {{ if (q.completed) doneIds[q.type] = true; }});
          el.innerHTML = (st.quests || []).map(function (q) {{
            const pct = Math.min(100, Math.round(Number(q.current) / Number(q.target) * 100));
            const icon = QUEST_ICONS[q.type] || '⭐';
            const done = q.completed;
            return '<div class="quest' + (done ? ' done' : '') + '">' +
              '<div class="quest-head"><span class="quest-name"><span class="quest-icon">' + icon + '</span>' +
              esc(NAMES['quest_' + q.type] || q.type) + '</span>' +
              '<span class="quest-target">' + esc(String(q.current)) + ' / ' + esc(String(q.target)) + (done ? ' · ' + esc(T.questDone) : '') + '</span></div>' +
              '<div class="quest-track"><div class="quest-fill" style="width:' + pct + '%"></div></div></div>';
          }}).join('');
          if (st.quest_complete_seq > lastQuestSeq) {{
            lastQuestSeq = st.quest_complete_seq;
            celebrate('q', T.questFinished);
          }}
        }}

        function renderFeed(st) {{
          if (!Array.isArray(st.recent)) return;
          const el = document.getElementById('feed') || document.getElementById('feedMini');
          if (!el) return;
          const mini = el.id === 'feedMini';
          const cap = mini ? 6 : 12;
          const items = st.recent.slice(-cap).reverse();
          const build = function (it) {{
            const icon = it.icon || FEED_ICONS[it.kind] || '⭐';
            const hasImg = !!it.icon;
            return '<div class="feed-item"><span class="fi">' +
              (hasImg ? '<img src="' + esc(it.icon) + '" alt="" />' : esc(icon)) +
              '</span><span class="ft"><span style="font-weight:800;">' + esc(it.user) + '</span>' +
              (it.detail ? ' <span class="fd">' + esc(it.detail) + '</span>' : '') + '</span></div>';
          }};
          if (!items.length) {{ el.innerHTML = ''; lastFeedSeq = 0; return; }}
          const maxSeq = Number(items[0].seq) || 0;
          if (lastFeedSeq === 0) {{
            el.innerHTML = items.map(build).join('');
            lastFeedSeq = maxSeq;
            return;
          }}
          const fresh = [];
          for (let i = 0; i < items.length; i++) {{
            const s = Number(items[i].seq) || 0;
            if (s > lastFeedSeq) fresh.push(items[i]); else break;
          }}
          if (fresh.length) {{
            el.insertAdjacentHTML('afterbegin', fresh.map(build).join(''));
            lastFeedSeq = maxSeq;
          }}
          while (el.children.length > cap) el.removeChild(el.lastChild);
        }}

        function renderPassports(st) {{
          const el = document.getElementById('passports');
          if (!el) return;
          const list = (st.passports || []).slice(0, 6);
          if (!list.length) {{ el.innerHTML = ''; return; }}
          el.innerHTML = '<div class="panel" style="display:flex;flex-direction:column;gap:5px;">' +
            '<div class="title" style="font-size:11px;">' + esc(T.village) + '</div>' +
            list.map(function (p) {{
              const av = p.avatar_url
                ? '<img src="' + esc(p.avatar_url) + '" alt="" />'
                : esc((p.user || '?').slice(0, 1).toUpperCase());
              const badges = (p.badges || []).slice(0, 5).map(function (b) {{
                return '<span title="' + esc(BADGES[b] || b) + '">' + (BADGE_ICONS[b] || '⭐') + '</span>';
              }}).join('');
              return '<div class="passport"><span class="av">' + av + '</span>' +
                '<span class="pn">' + esc(p.user) + '</span>' +
                (badges ? '<span class="badges">' + badges + '</span>' : '') +
                '<span class="pt">' + esc(String(p.points)) + '</span></div>';
            }}).join('') + '</div>';
        }}

        function renderElders(st) {{
          const el = document.getElementById('elders');
          if (!el) return;
          const list = st.elders || [];
          if (!list.length) {{ el.innerHTML = ''; return; }}
          el.innerHTML = list.slice(0, 6).map(function (e) {{
            return '<span class="elder">🏛 ' + esc(e.user) + ' · ' + esc(String(e.badge_count)) + '</span>';
          }}).join('');
        }}

        function celebrate(kind, text) {{
          const el = document.getElementById('celebrate');
          if (!el || !text) return;
          if (cfg.quiet_mode) return;
          el.style.display = 'flex';
          el.innerHTML = '<div class="banner">' + esc(text) + '</div>';
          const colors = ['#f472b6','#22d3ee','#fde047','#a78bfa','#4ade80','#fb923c'];
          for (let i = 0; i < 26; i++) {{
            const p = document.createElement('div');
            p.className = 'confetti';
            p.style.left = (Math.random() * 100) + '%';
            p.style.background = colors[i % colors.length];
            p.style.animationDelay = (Math.random() * 0.4) + 's';
            p.style.animationDuration = (1.2 + Math.random() * 1.4) + 's';
            el.appendChild(p);
          }}
          setTimeout(function () {{ el.style.display = 'none'; el.innerHTML = ''; }}, 3400);
        }}

        function applyState(st) {{
          if (!st) return;
          if (st.config) applyCfg(st.config);
          renderLevel(st);
          renderCounts(st);
          renderVillage(st, celebrate);
          renderQuests(st);
          renderFeed(st);
          renderPassports(st);
          renderElders(st);
          if (st.level !== undefined && st.level > lastLevel) {{
            lastLevel = st.level;
            celebrate('l', T.levelUp + ' ' + st.level + '!');
          }}
        }}

        function handleMsg(data) {{
          if (data.op === 'initial_state') {{
            applyCfg((data.state || {{}}).config || {{}});
            buildHtml();
            lastLevel = data.state.level || 1;
            unlockedIds = new Set(((data.state || {{}}).buildings || [])
              .filter(function (b) {{ return b && b.unlocked; }}).map(function (b) {{ return b.id; }}));
            lastQuestSeq = data.state.quest_complete_seq || 0;
            applyState(data.state || {{}});
          }} else if (data.op === 'patch') {{
            applyState(data.patch || {{}});
          }}
        }}

        function connect() {{
          tries += 1;
          const backoff = Math.min(5000, 250 + Math.floor(Math.random() * 250) + (tries * 350));
          try {{ ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws'); }}
          catch (e) {{ setTimeout(connect, backoff); return; }}
          ws.onopen = function () {{ tries = 0; ws.send(JSON.stringify(subscribeMsg)); }};
          ws.onmessage = function (ev) {{ try {{ handleMsg(JSON.parse(ev.data)); }} catch (e) {{}} }};
          ws.onclose = function () {{ setTimeout(connect, backoff); }};
        }}

        buildHtml();
        connect();
      }})();
    </script>
  </body>
</html>"""

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        cfg = load_community_world_overlay_config()
        session = CommunityWorldSession.fresh(cfg)
        state = session.to_overlay_dict()
        state["config"] = community_world_overlay_config_to_public_dict(cfg)
        state["elders"] = fetch_village_elders(limit=8)
        state["locale"] = load_ui_locale()
        return state