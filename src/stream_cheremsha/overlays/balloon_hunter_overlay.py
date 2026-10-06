"""``balloon_hunter`` overlay — transparent Canvas balloon-pop reaction layer.

Balloons float upward continuously (client-side ambient ``requestAnimationFrame``
loop with fixed object/particle pools — no WebSocket traffic for motion).
Each balloon carries a real TikTok gift from the bundled catalog (face icon
drawn inside the balloon). Spawn rarity follows five price tiers — cheap
gifts spawn often, legendary (1000+ coins) ones rarely — with tier bounds
following the configured gold/epic thresholds. Strict matching only: a
gift event pops the balloon showing that exact gift, otherwise nothing
happens — no fallbacks. The pop is delivered by a homing projectile: a
tier-colored comet with a spark trail launches from the screen edge, tracks
the balloon along a curved path, and detonates it on impact:
squeeze → flash → confetti particles → gift icon + value/sender/combo popup.

The layer is **fully transparent** — only balloons and effects are visible.
"""

from __future__ import annotations

import json
from typing import Any

from stream_cheremsha.overlays.models import normalize_instance_id


def _balloon_hunter_gift_catalog() -> list[dict[str, Any]]:
    """Compact bundled TikTok gift catalog for balloon faces.

    Sent once in ``initial_state`` (not on every patch): ``id``/``n``ame/
    ``p``rice + icon ``u``rl. Only gifts with an icon URL are included.
    """
    try:
        from stream_cheremsha.actions.tiktok_gifts import TIKTOK_GIFTS
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for g in TIKTOK_GIFTS:
        try:
            url = str(g.get("image_url") or "").strip()
            name = str(g.get("name") or "").strip()
            price = int(g.get("price") or 0)
            gid = str(g.get("id") or "").strip()
        except (TypeError, ValueError, AttributeError):
            continue
        if not url or not name:
            continue
        out.append({"id": gid, "n": name, "p": price, "u": url})
    return out


_HTML_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Cheremsha Balloon Hunter</title>
<style>
html, body { margin: 0; padding: 0; background: transparent; overflow: hidden; height: 100%; width: 100%; }
* { box-sizing: border-box; }
#bhCanvas { position: absolute; inset: 0; width: 100%; height: 100%; background: transparent; pointer-events: none; }
</style>
</head>
<body>
<canvas id="bhCanvas"></canvas>
<script>
(function() {
  var canvas = document.getElementById('bhCanvas');
  var ctx = canvas.getContext('2d');
  var instance = __BH_INSTANCE__;
  var cfg = {};
  var lastSeenAt = 0;
  var popQueue = [];
  var popping = 0;
  var maxSimultaneous = 10;

  var KIND_COLORS = {
    NORMAL: ['#22d3ee', '#0ea5e9', '#a5f3fc'],
    GOLD: ['#facc15', '#f59e0b', '#fef3c7'],
    EPIC: ['#f472b6', '#a78bfa', '#ffffff']
  };

  var balloons = [];
  var particles = [];
  var popups = [];
  var flashes = [];
  var iconCache = {};
  var iconLoading = {};
  var catalog = [];
  var recentGifts = [];
  var rafId = 0;
  var lastT = 0;
  var spawnAcc = 0;

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function rand(a, b) { return a + Math.random() * (b - a); }
  function pickKind() {
    var r = Math.random();
    if (r < 0.06) return 'EPIC';
    if (r < 0.24) return 'GOLD';
    return 'NORMAL';
  }

  // Gift identity: bundled catalog ids are empty, so match by id when both
  // sides carry one, otherwise by casefolded gift name.
  function giftKey(id, name) {
    var k = String(id || '').trim().toLowerCase();
    if (k) return 'id:' + k;
    return 'nm:' + String(name || '').trim().toLowerCase();
  }
  function kindForPrice(price) {
    var p = Number(price) || 0;
    var epic = Number(cfg.epic_min_coins || 200);
    var gold = Number(cfg.gold_min_coins || 50);
    if (p >= epic) return 'EPIC';
    if (p >= gold) return 'GOLD';
    return 'NORMAL';
  }
  // Spawn rarity tiers by gift price: cheap gifts spawn often, expensive
  // ones rarely. Bounds follow the configured gold/epic thresholds so the
  // tier visuals always agree with the pop value tiers.
  var TIER_WEIGHTS = [45, 25, 17, 9, 4];
  var TIER_KINDS = ['NORMAL', 'NORMAL', 'GOLD', 'EPIC', 'EPIC'];
  function tierBounds() {
    var gold = Number(cfg.gold_min_coins || 50);
    var epic = Number(cfg.epic_min_coins || 200);
    var b1 = 10;
    var b2 = Math.max(gold, b1 + 1);
    var b3 = Math.max(epic, b2 + 1);
    var b4 = Math.max(1000, b3 + 1);
    return [b1, b2, b3, b4];
  }
  function tierIndexForPrice(p) {
    var b = tierBounds(), price = Number(p) || 0;
    for (var i = 0; i < b.length; i++) if (price < b[i]) return i;
    return b.length;
  }
  function pickGift() {
    // Recently gifted items resurface quickly, so the screen keeps showing
    // gifts the chat is actually sending (and their balloons can be popped).
    if (recentGifts.length && Math.random() < 0.5) {
      var rg = recentGifts[(Math.random() * recentGifts.length) | 0];
      return { gift: rg, tier: tierIndexForPrice(rg.p) };
    }
    if (!catalog.length) return null;
    var roll = Math.random() * 100, acc = 0, idx = 0;
    for (var j = 0; j < TIER_WEIGHTS.length; j++) {
      acc += TIER_WEIGHTS[j];
      if (roll < acc) { idx = j; break; }
    }
    var b = tierBounds();
    var lo = idx === 0 ? 0 : b[idx - 1];
    var hi = idx < b.length ? b[idx] : Infinity;
    var pool = [];
    for (var k = 0; k < catalog.length; k++) {
      var price = Number(catalog[k].p) || 0;
      if (price >= lo && price < hi) pool.push(catalog[k]);
    }
    if (!pool.length) return { gift: catalog[(Math.random() * catalog.length) | 0], tier: idx };
    return { gift: pool[(Math.random() * pool.length) | 0], tier: idx };
  }
  function learnGift(p) {
    var key = giftKey(p.gift_id, p.gift_name);
    if (key === 'nm:') return;
    for (var i = 0; i < recentGifts.length; i++) {
      if (recentGifts[i].key === key) return;
    }
    recentGifts.push({ key: key, n: p.gift_name || '', u: p.icon_url || '', p: Number(p.value) || 0 });
    if (recentGifts.length > 20) recentGifts.shift();
  }

  function resize() {
    var dpr = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = Math.floor(window.innerWidth * dpr);
    canvas.height = Math.floor(window.innerHeight * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  window.addEventListener('resize', resize);
  resize();

  function desiredCount() {
    return clamp(Math.floor(Number(cfg.balloon_count || 8)), 3, 20);
  }
  function speedMul() {
    return clamp(Number(cfg.float_speed_percent || 100), 40, 250) / 100;
  }
  function maxParticles() {
    var m = clamp(Math.floor(Number(cfg.max_particles || 200)), 50, 500);
    if (cfg.reduced_effects) m = Math.ceil(m / 2);
    return m;
  }

  function spawnBalloon(fromTop) {
    var W = window.innerWidth, H = window.innerHeight;
    var pick = pickGift();
    var gift = pick ? pick.gift : null;
    var tier = pick ? pick.tier : 0;
    var kind = gift ? (TIER_KINDS[tier] || kindForPrice(gift.p)) : pickKind();
    var base = kind === 'EPIC' ? 46 : kind === 'GOLD' ? 38 : 30;
    if (tier >= 4) base = 58;
    var r = base * rand(0.85, 1.2);
    var b = {
      x: rand(r, Math.max(r + 1, W - r)),
      y: fromTop ? rand(0, H) : H + r + rand(0, 80),
      r: r,
      vy: rand(28, 62),
      swayAmp: rand(12, 34),
      swayFreq: rand(0.5, 1.4),
      phase: rand(0, Math.PI * 2),
      kind: kind,
      legendary: tier >= 4,
      reserved: false,
      wobble: 0,
      popT: -1,
      giftKey: '',
      giftName: '',
      giftUrl: ''
    };
    if (gift) dressBalloon(b, gift, tier);
    return b;
  }

  function ensureBalloons() {
    var want = desiredCount();
    while (balloons.length < want) balloons.push(spawnBalloon(true));
    if (balloons.length > want) balloons.length = want;
  }

  function dressBalloon(b, gift, tier) {
    b.giftKey = gift ? (gift.key || giftKey(gift.id, gift.n)) : '';
    b.giftName = gift ? (gift.n || '') : '';
    b.giftUrl = gift ? (gift.u || '') : '';
    if (tier !== undefined && TIER_KINDS[tier]) b.kind = TIER_KINDS[tier];
    if (tier !== undefined && tier >= 4) b.legendary = true;
    prefetchIcon(b.giftUrl);
  }

  function backfillBalloonGifts() {
    // Balloons spawn before the catalog arrives (boot state has no catalog),
    // so dress the pre-spawned generic ones once the catalog lands.
    for (var i = 0; i < balloons.length; i++) {
      var b = balloons[i];
      if (b.popT >= 0 || b.giftKey) continue;
      var pick = pickGift();
      if (!pick || !pick.gift) continue;
      dressBalloon(b, pick.gift, pick.tier);
    }
  }

  function loadIcon(url, cb) {
    if (!url) { cb(null); return; }
    var hit = iconCache[url];
    if (hit === 'bad') { cb(null); return; }
    if (hit) { cb(hit); return; }
    var img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = function() { iconCache[url] = img; cb(img); };
    img.onerror = function() { iconCache[url] = 'bad'; cb(null); };
    img.src = url;
  }

  function prefetchIcon(url) {
    if (!url || iconCache[url] !== undefined || iconLoading[url]) return;
    iconLoading[url] = true;
    loadIcon(url, function() { delete iconLoading[url]; });
  }

  function findBalloonByGift(p) {
    var key = giftKey(p.gift_id, p.gift_name);
    var url = String(p.icon_url || '').trim();
    var best = null, bestScore = 1e9;
    var cx = window.innerWidth / 2, cy = window.innerHeight * 0.45;
    for (var i = 0; i < balloons.length; i++) {
      var b = balloons[i];
      if (b.popT >= 0 || b.reserved || !b.giftKey) continue;
      if (key !== 'nm:' && b.giftKey === key) {
        var d = Math.hypot(b.x - cx, b.y - cy);
        if (d < bestScore) { bestScore = d; best = b; }
      } else if (!best && url && b.giftUrl === url) {
        best = b;
      }
    }
    return best;
  }

  function burst(x, y, kind, n, gold) {
    var colors = kind === 'EPIC' ? ['#fde68a', '#f472b6', '#ffffff', '#a78bfa']
      : gold ? ['#fde68a', '#fbbf24', '#fff7ed']
      : ['#a5f3fc', '#22d3ee', '#ffffff', '#f0abfc'];
    for (var i = 0; i < n; i++) {
      if (particles.length >= maxParticles()) particles.shift();
      var a = rand(0, Math.PI * 2), sp = rand(60, kind === 'EPIC' ? 420 : 280);
      particles.push({
        x: x, y: y,
        vx: Math.cos(a) * sp, vy: Math.sin(a) * sp - 120,
        life: rand(0.5, 1.1), age: 0,
        size: rand(2, kind === 'EPIC' ? 7 : 5),
        color: colors[(Math.random() * colors.length) | 0],
        gold: gold && Math.random() < 0.5
      });
    }
    flashes.push({ x: x, y: y, age: 0, life: 0.35, kind: kind });
  }

  function doPop(ev) {
    var p = ev.payload || {};
    var kind = p.target_balloon_kind || p.intensity || 'NORMAL';
    // Strict matching only: fire a projectile at the balloon showing this
    // exact gift, or nothing at all — no fallbacks, no re-dressing.
    var b = findBalloonByGift(p);
    if (!b || b.popT >= 0) return;
    fireProjectile(b, ev, kind);
  }

  var projectiles = [];
  var PROJECTILE_FLIGHT_MS = { NORMAL: 550, GOLD: 650, EPIC: 800 };
  var PROJECTILE_COLORS = {
    NORMAL: { head: '#a5f3fc', trail: ['#a5f3fc', '#22d3ee', '#ffffff'] },
    GOLD: { head: '#fef3c7', trail: ['#fde68a', '#fbbf24', '#fff7ed'] },
    EPIC: { head: '#ffffff', trail: ['#fde68a', '#f472b6', '#ffffff', '#a78bfa'] }
  };

  function fireProjectile(b, ev, kind) {
    var W = window.innerWidth, H = window.innerHeight;
    var fromLeft = Math.random() < 0.5;
    var dur = (PROJECTILE_FLIGHT_MS[kind] || 550) / 1000;
    if (cfg.reduced_effects) dur = dur * 0.7;
    b.reserved = true;
    var sx = fromLeft ? -30 : W + 30, sy = H * rand(0.75, 1.0);
    projectiles.push({
      sx: sx,
      sy: sy,
      x: sx,
      y: H * 0.9,
      px: sx,
      py: H * 0.9,
      t: 0, dur: dur,
      target: b, ev: ev, kind: kind,
      seed: Math.random() * Math.PI * 2,
      size: b.legendary ? 16 : kind === 'EPIC' ? 13 : kind === 'GOLD' ? 10 : 8,
      trailAcc: 0
    });
  }

  function stepProjectiles(dt) {
    for (var i = projectiles.length - 1; i >= 0; i--) {
      var pt = projectiles[i];
      var tgt = pt.target;
      if (balloons.indexOf(tgt) < 0 || tgt.popT >= 0) {
        // Target vanished mid-flight: fizzle out with a small puff.
        burst(pt.x, pt.y, 'NORMAL', 6, false);
        projectiles.splice(i, 1);
        continue;
      }
      pt.t += dt / pt.dur;
      // Homing quadratic bezier: fixed launch point, live balloon position.
      var tx = tgt.x, ty = tgt.y;
      var mx = (pt.sx + tx) / 2, my = (pt.sy + ty) / 2 - window.innerHeight * 0.12;
      var k = Math.min(1, pt.t), inv = 1 - k;
      pt.px = pt.x; pt.py = pt.y;
      pt.x = inv * inv * pt.sx + 2 * inv * k * mx + k * k * tx;
      pt.y = inv * inv * pt.sy + 2 * inv * k * my + k * k * ty;
      pt.trailAcc += dt;
      var cols = (PROJECTILE_COLORS[pt.kind] || PROJECTILE_COLORS.NORMAL).trail;
      while (pt.trailAcc > 0.010) {
        pt.trailAcc -= 0.010;
        if (particles.length < maxParticles()) {
          particles.push({
            x: pt.x + rand(-5, 5), y: pt.y + rand(-5, 5),
            vx: rand(-40, 40), vy: rand(-40, 40),
            life: rand(0.35, 0.7), age: 0,
            size: rand(2, 5),
            color: cols[(Math.random() * cols.length) | 0], gold: false
          });
        }
      }
      if (pt.t >= 1) {
        projectiles.splice(i, 1);
        tgt.reserved = false;
        popBalloon(tgt, pt.ev, pt.kind);
      }
    }
  }

  function detonateExitingTarget(b) {
    // A locked target floated off the top mid-flight: drop its projectile
    // and detonate at the visible edge instead of losing the gift.
    // Off-screen balloons are always replaced and can never trigger pops.
    var ev = null, kind = b.kind;
    for (var i = projectiles.length - 1; i >= 0; i--) {
      if (projectiles[i].target === b) {
        ev = projectiles[i].ev;
        kind = projectiles[i].kind;
        projectiles.splice(i, 1);
      }
    }
    if (!ev) return;
    b.reserved = false;
    b.y = Math.max(b.y, 50);
    popBalloon(b, ev, kind);
  }

  function drawProjectile(pt, t) {
    var pal = PROJECTILE_COLORS[pt.kind] || PROJECTILE_COLORS.NORMAL;
    var pulse = 1 + 0.18 * Math.sin(t * 18 + pt.seed);
    var R = pt.size * 5 * pulse;
    // Wide aura.
    var g = ctx.createRadialGradient(pt.x, pt.y, 1, pt.x, pt.y, R);
    g.addColorStop(0, '#ffffff');
    g.addColorStop(0.25, pal.head);
    g.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(pt.x, pt.y, R, 0, Math.PI * 2); ctx.fill();
    // Fiery tail streak along the motion direction.
    var dx = pt.x - pt.px, dy = pt.y - pt.py;
    var len = Math.hypot(dx, dy);
    if (len > 0.5) {
      var tailLen = pt.size * (pt.kind === 'NORMAL' ? 7 : 10);
      var tx = pt.x - (dx / len) * tailLen, ty = pt.y - (dy / len) * tailLen;
      var tg = ctx.createLinearGradient(pt.x, pt.y, tx, ty);
      tg.addColorStop(0, pal.head);
      tg.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.strokeStyle = tg;
      ctx.lineWidth = pt.size * 1.1;
      ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(pt.x, pt.y); ctx.lineTo(tx, ty); ctx.stroke();
    }
    // Hot pulsing core.
    ctx.fillStyle = '#ffffff';
    ctx.beginPath(); ctx.arc(pt.x, pt.y, pt.size * 0.55 * pulse, 0, Math.PI * 2); ctx.fill();
  }

  function popBalloon(b, ev, kind) {
    var p = ev.payload || {};
    b.popT = 0;
    var dur = clamp(Number(cfg.effect_duration_ms || 800), 300, 2000) / 1000;
    var n = kind === 'EPIC' ? 46 : kind === 'GOLD' ? 28 : 14;
    if (b.legendary) n = Math.round(n * 1.4);
    if (cfg.reduced_effects) n = Math.ceil(n / 2);
    burst(b.x, b.y, kind, n, kind !== 'NORMAL');
    var label = '+' + (p.value || 0);
    if ((p.count || 1) > 1) label += ' x' + p.count;
    popups.push({ x: b.x, y: b.y - b.r - 8, age: 0, life: 0.9, text: label, big: kind === 'EPIC', kind: 'value' });
    if (cfg.show_sender !== false && p.sender) {
      popups.push({ x: b.x, y: b.y + b.r + 18, age: 0, life: 1.0, text: String(p.sender).slice(0, 24), big: false, kind: 'sender' });
    }
    if ((p.combo || 0) > 1) {
      popups.push({ x: b.x, y: b.y - b.r - 44, age: 0, life: 1.1, text: 'COMBO x' + p.combo, big: kind === 'EPIC', kind: 'combo' });
    }
    if (kind !== 'NORMAL') {
      popups.push({ x: b.x, y: b.y - b.r - 76, age: 0, life: 0.9, text: b.legendary ? 'LEGENDARY!' : (kind === 'EPIC' ? 'EPIC!' : 'GOLD!'), big: true, kind: 'badge' });
    }
    var url = (cfg.show_gift_icon !== false && p.icon_url) ? p.icon_url : '';
    if (url) {
      loadIcon(url, function(img) {
        if (img) popups.push({ x: b.x, y: b.y, age: 0, life: Math.max(0.8, dur), text: '', big: false, kind: 'icon', img: img });
      });
    }
    setTimeout(function() {
      var idx = balloons.indexOf(b);
      if (idx >= 0) balloons[idx] = spawnBalloon(false);
    }, 180);
  }

  function pumpQueue() {
    if (!popQueue.length) return;
    if (popping >= maxSimultaneous) return;
    popping++;
    var ev = popQueue.shift();
    try { doPop(ev); } catch (e) {}
    setTimeout(function() { popping = Math.max(0, popping - 1); pumpQueue(); }, 150);
  }

  function processEvents(state) {
    if (!state || !Array.isArray(state.events)) return;
    for (var i = 0; i < state.events.length; i++) {
      var e = state.events[i];
      if (!e || (e.type !== 'pop' && e.type !== 'gift')) continue;
      var at = Number(e.at) || 0;
      if (at <= lastSeenAt + 0.0001) continue;
      lastSeenAt = Math.max(lastSeenAt, at);
      if (cfg.event_animations === false) continue;
      if (e.payload) learnGift(e.payload);
      popQueue.push(e);
      if (popQueue.length > 32) popQueue.shift();
    }
    pumpQueue();
  }

  function drawBalloon(b, t) {
    var swayX = Math.sin(t * b.swayFreq + b.phase) * b.swayAmp;
    var x = b.x + swayX, y = b.y;
    var sq = b.popT >= 0 ? Math.min(1, b.popT / 0.12) : 0;
    var sx = 1 + sq * 0.35, sy = 1 - sq * 0.45;
    if (sq >= 1) return;
    var c = KIND_COLORS[b.kind] || KIND_COLORS.NORMAL;
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(sx, sy);
    var g = ctx.createRadialGradient(-b.r * 0.3, -b.r * 0.35, b.r * 0.1, 0, 0, b.r * 1.15);
    g.addColorStop(0, c[2]);
    g.addColorStop(0.45, c[0]);
    g.addColorStop(1, c[1]);
    ctx.fillStyle = g;
    ctx.globalAlpha = 0.92;
    ctx.beginPath();
    ctx.ellipse(0, 0, b.r, b.r * 1.18, 0, 0, Math.PI * 2);
    ctx.fill();
    if (b.legendary) {
      ctx.globalAlpha = 0.85;
      ctx.strokeStyle = '#fde68a';
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.ellipse(0, 0, b.r + 5, b.r * 1.18 + 5, 0, 0, Math.PI * 2);
      ctx.stroke();
      ctx.globalAlpha = 0.92;
    }
    ctx.globalAlpha = 0.35;
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.ellipse(-b.r * 0.32, -b.r * 0.42, b.r * 0.16, b.r * 0.26, -0.4, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
    // The balloon's TikTok gift: real icon photo when loaded, otherwise a
    // generic gift box placeholder (also shown when catalog is unavailable).
    var gimg = b.giftUrl ? iconCache[b.giftUrl] : null;
    if (gimg && gimg !== 'bad') {
      ctx.save();
      ctx.beginPath();
      ctx.arc(0, 0, b.r * 0.62, 0, Math.PI * 2);
      ctx.clip();
      var iw = gimg.width || 1, ih = gimg.height || 1;
      var s = Math.max((b.r * 1.24) / iw, (b.r * 1.24) / ih);
      ctx.drawImage(gimg, -iw * s / 2, -ih * s / 2, iw * s, ih * s);
      ctx.restore();
      ctx.globalAlpha = 0.22;
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.ellipse(-b.r * 0.3, -b.r * 0.4, b.r * 0.2, b.r * 0.3, -0.4, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
    } else {
      if (b.giftUrl) prefetchIcon(b.giftUrl);
      var gs = b.r * 0.52;
      ctx.fillStyle = 'rgba(255,255,255,0.92)';
      ctx.fillRect(-gs / 2, -gs / 2, gs, gs);
      ctx.fillStyle = b.kind === 'EPIC' ? '#f472b6' : b.kind === 'GOLD' ? '#f59e0b' : '#0ea5e9';
      ctx.fillRect(-gs / 2, -gs * 0.12, gs, gs * 0.24);
      ctx.fillRect(-gs * 0.12, -gs / 2, gs * 0.24, gs);
    }
    // knot + string
    ctx.fillStyle = c[1];
    ctx.beginPath();
    ctx.moveTo(-5, b.r * 1.18); ctx.lineTo(5, b.r * 1.18); ctx.lineTo(0, b.r * 1.18 + 8);
    ctx.closePath(); ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,0.5)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(0, b.r * 1.18 + 8);
    ctx.quadraticCurveTo(Math.sin(t * 2 + b.phase) * 10, b.r * 1.18 + 40, 0, b.r * 1.18 + 70);
    ctx.stroke();
    ctx.restore();
  }

  function frame(ts) {
    rafId = requestAnimationFrame(frame);
    var t = ts / 1000;
    var dt = Math.min(0.05, lastT ? t - lastT : 0.016);
    lastT = t;
    ensureBalloons();
    var W = window.innerWidth, H = window.innerHeight;
    ctx.clearRect(0, 0, W, H);
    var spd = speedMul();
    var interval = clamp(Number(cfg.spawn_interval_ms || 1500), 500, 5000) / 1000;
    spawnAcc += dt;
    if (spawnAcc >= interval) { spawnAcc = 0; }

    for (var i = 0; i < balloons.length; i++) {
      var b = balloons[i];
      if (b.popT >= 0) b.popT += dt;
      b.y -= b.vy * spd * dt;
      if (b.y < -b.r * 2 - 90) {
        if (b.reserved) detonateExitingTarget(b);
        balloons[i] = spawnBalloon(false);
      }
      else drawBalloon(b, t);
    }
    // Homing projectiles: fly to their reserved balloon, pop on impact.
    stepProjectiles(dt);
    for (var pi = 0; pi < projectiles.length; pi++) drawProjectile(projectiles[pi], t);
    // flashes
    for (var f = flashes.length - 1; f >= 0; f--) {
      var fl = flashes[f];
      fl.age += dt;
      if (fl.age >= fl.life) { flashes.splice(f, 1); continue; }
      var k = 1 - fl.age / fl.life;
      var rr = (fl.kind === 'EPIC' ? 130 : 80) * (1 - k * 0.4);
      var fg = ctx.createRadialGradient(fl.x, fl.y, 4, fl.x, fl.y, rr);
      fg.addColorStop(0, 'rgba(255,255,255,' + (0.85 * k).toFixed(3) + ')');
      fg.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.fillStyle = fg;
      ctx.beginPath(); ctx.arc(fl.x, fl.y, rr, 0, Math.PI * 2); ctx.fill();
    }
    // particles
    for (var q = particles.length - 1; q >= 0; q--) {
      var pt = particles[q];
      pt.age += dt;
      if (pt.age >= pt.life) { particles.splice(q, 1); continue; }
      pt.vy += 520 * dt;
      pt.x += pt.vx * dt; pt.y += pt.vy * dt;
      var a = 1 - pt.age / pt.life;
      ctx.globalAlpha = a;
      ctx.fillStyle = pt.gold ? '#fde68a' : pt.color;
      ctx.fillRect(pt.x - pt.size / 2, pt.y - pt.size / 2, pt.size, pt.size * 0.6);
      ctx.globalAlpha = 1;
    }
    // popups
    ctx.textAlign = 'center';
    for (var u = popups.length - 1; u >= 0; u--) {
      var pu = popups[u];
      pu.age += dt;
      if (pu.age >= pu.life) { popups.splice(u, 1); continue; }
      var pa = 1 - pu.age / pu.life;
      var rise = pu.age * 34;
      if (pu.kind === 'icon' && pu.img) {
        ctx.globalAlpha = pa;
        var is = 54;
        ctx.drawImage(pu.img, pu.x - is / 2, pu.y - rise - is / 2, is, is);
        ctx.globalAlpha = 1;
      } else if (pu.kind === 'value') {
        ctx.globalAlpha = pa;
        ctx.font = '900 ' + (pu.big ? 44 : 34) + 'px system-ui, sans-serif';
        ctx.lineWidth = 5; ctx.strokeStyle = 'rgba(0,0,0,0.6)';
        ctx.strokeText(pu.text, pu.x, pu.y - rise);
        ctx.fillStyle = pu.big ? '#fde68a' : '#ffffff';
        ctx.fillText(pu.text, pu.x, pu.y - rise);
        ctx.globalAlpha = 1;
      } else if (pu.kind === 'sender') {
        ctx.globalAlpha = pa * 0.85;
        ctx.font = '600 15px system-ui, sans-serif';
        ctx.fillStyle = 'rgba(255,255,255,0.9)';
        ctx.fillText(pu.text, pu.x, pu.y - rise * 0.5);
        ctx.globalAlpha = 1;
      } else {
        ctx.globalAlpha = pa;
        ctx.font = '900 ' + (pu.big ? 26 : 20) + 'px system-ui, sans-serif';
        ctx.fillStyle = pu.kind === 'badge' ? '#fde68a' : '#22d3ee';
        ctx.fillText(pu.text, pu.x, pu.y - rise);
        ctx.globalAlpha = 1;
      }
    }
  }

  function applyState(state) {
    if (state && state.config) {
      cfg = state.config;
      maxSimultaneous = clamp(Math.floor(Number(cfg.max_simultaneous_events || 10)) || 10, 1, 12);
    }
    // The catalog arrives once with initial_state; live patches carry no
    // catalog, so never clear a populated one.
    if (state && Array.isArray(state.catalog) && state.catalog.length) {
      var hadCatalog = catalog.length > 0;
      catalog = state.catalog;
      if (!hadCatalog) backfillBalloonGifts();
    }
    ensureBalloons();
  }

  function handleMsg(obj) {
    if (!obj || typeof obj !== 'object') return;
    if (obj.op === 'initial_state' && obj.state) {
      lastSeenAt = 0;
      applyState(obj.state);
      processEvents(obj.state);
    } else if (obj.op === 'patch' && obj.patch) {
      if (obj.patch.config) applyState(obj.patch);
      processEvents(obj.patch);
    }
  }

  applyState({ config: { balloon_count: 8 } });
  rafId = requestAnimationFrame(frame);

  var subscribeMsg = { op: 'subscribe', type: 'balloon_hunter', instance: instance, params: {} };
  var wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
  var ws = null, tries = 0;
  function connect() {
    tries += 1;
    var backoff = Math.min(5000, 250 + Math.floor(Math.random() * 250) + (tries * 350));
    try { ws = new WebSocket(wsUrl); }
    catch (e) { setTimeout(connect, backoff); return; }
    ws.onopen = function() { tries = 0; ws.send(JSON.stringify(subscribeMsg)); };
    ws.onmessage = function(ev) {
      var obj = null;
      try { obj = JSON.parse(ev.data); } catch (err) { return; }
      handleMsg(obj);
    };
    ws.onclose = function() { setTimeout(connect, backoff); };
  }
  connect();
})();
</script>
</body>
</html>
"""


class BalloonHunterOverlayType:
    """Overlay type serving the transparent balloon-hunter Canvas page."""

    type = "balloon_hunter"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "default"
        instance_lit = json.dumps(instance)
        return _HTML_TEMPLATE.replace("__BH_INSTANCE__", instance_lit)

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        from stream_cheremsha.overlays.balloon_hunter_config import (
            balloon_hunter_overlay_config_from_json_text,
            balloon_hunter_overlay_config_to_json_text,
            load_balloon_hunter_overlay_config,
        )
        from stream_cheremsha.overlays.widget_instances import typed_config_for_type

        cfg = typed_config_for_type(
            "balloon_hunter",
            params,
            load_balloon_hunter_overlay_config,
            balloon_hunter_overlay_config_from_json_text,
        )
        cfg_payload = json.loads(balloon_hunter_overlay_config_to_json_text(cfg))
        return {
            "config": cfg_payload,
            "locale": "uk",
            "events": [],
            "catalog": _balloon_hunter_gift_catalog(),
        }
