# ruff: noqa: E501
from __future__ import annotations

import json
from typing import Any

from stream_cheremsha import l10n
from stream_cheremsha.overlays.models import normalize_instance_id
from stream_cheremsha.overlays.signal_system_overlay_config import (
    load_signal_system_overlay_config,
    signal_system_overlay_config_to_public_dict,
)
from stream_cheremsha.overlays.ui_locale import load_ui_locale


def _overlay_i18n_bundle() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {"uk": {}, "en": {}}
    for short in _I18N_KEYS:
        key = f"signal_system.{short}"
        # Store under short keys (goal.system) — matches tr('goal.system') in HTML
        out["uk"][short] = l10n.tr("uk", key)
        out["en"][short] = l10n.tr("en", key)
    return out


_I18N_KEYS = (
    "goal.detected",
    "goal.mega",
    "goal.milestone",
    "goal.milestone_reached",
    "goal.milestone_default",
    "goal.milestone_sub",
    "goal.milestone_test_sub",
    "goal.milestone_test_value",
    "goal.surge",
    "goal.overdrive",
    "goal.surge_sub",
    "goal.ai",
    "goal.ai_title",
    "goal.ai_default_sub",
    "goal.ai_test_sub",
    "goal.anomaly",
    "goal.anomaly_title",
    "goal.anomaly_sub",
    "goal.anomaly_test_sub",
    "goal.test",
    "goal.test_sub",
    "goal.system",
    "goal.unknown",
    "goal.online",
    "goal.offline",
    "goal.activity",
    "goal.gifts",
    "goal.gift",
    "goal.coins",
    "goal.coins_fmt",
    "goal.per_min_fmt",
    "goal.min_gift",
    "goal.anonymous",
    "goal.community",
    "goal.test_pilot",
    "overlay.gift_prefix",
    "overlay.signal_lost",
    "overlay.signal_intensity",
    "overlay.neural_scan",
    "overlay.conf",
    "overlay.pattern_observed",
    "overlay.new_record",
    "overlay.sys",
    "overlay.act",
    "overlay.per_min",
    "overlay.grid_link",
    "overlay.sec_pwr",
    "ui.scale_hint",
    "ui.scale",
    "ui.core_vertical",
    "ui.core_vertical_hint",
    "ui.theme",
    "ui.title",
    "ui.perimeter",
    "ui.particles",
    "ui.glitch",
    "ui.sound",
    "ui.font",
    "ui.opacity_idle",
    "ui.opacity_active",
    "ui.cooldown",
    "ui.min_gift_coins",
)


def _json_for_script(value: Any) -> str:
    s = json.dumps(value, ensure_ascii=False)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


class SignalSystemOverlayType:
    type = "signal_system"

    def render_html(self, params: dict[str, Any]) -> str:
        raw_instance = params.get("instance")
        try:
            instance = normalize_instance_id(str(raw_instance or ""))
        except ValueError:
            instance = "main"

        subscribe_msg = {
            "op": "subscribe",
            "type": self.type,
            "instance": instance,
            "params": params,
        }

        locale = load_ui_locale()
        cfg = load_signal_system_overlay_config()
        i18n = _overlay_i18n_bundle()
        return self._render_template(
            params,
            locale,
            subscribe_msg,
            cfg.theme,
            cfg.scale_percent,
            i18n,
        )

    def initial_state(self, params: dict[str, Any]) -> dict[str, Any]:
        _ = normalize_instance_id(str(params.get("instance") or ""))
        cfg = load_signal_system_overlay_config()
        return {
            "config": signal_system_overlay_config_to_public_dict(cfg),
            "current_event": None,
            "event_seq": 0,
            "idle_metrics": {
                "activity_rate": 0,
                "system_status": "ONLINE",
                "uptime_s": 0,
            },
            "locale": load_ui_locale(),
            "scale_percent": int(cfg.scale_percent),
        }

    def _render_template(
        self,
        params: dict[str, Any],
        locale: str,
        subscribe_msg: dict[str, Any],
        theme: str = "neon_cyber",
        scale_percent: int = 100,
        i18n: dict[str, dict[str, str]] | None = None,
    ) -> str:
        _ = params
        i18n_bundle = i18n or _overlay_i18n_bundle()
        scale_val = max(40, min(250, int(scale_percent)))
        template = _HTML_TEMPLATE
        template = template.replace("__INITIAL_SCALE__", str(scale_val))
        template = template.replace("__LOCALE_JSON__", _json_for_script(locale))
        template = template.replace("__I18N_JSON__", _json_for_script(i18n_bundle))
        template = template.replace("__SUBSCRIBE_JSON__", _json_for_script(subscribe_msg))
        return template


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Signal System Overlay</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800;900&family=Rajdhani:wght@600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet" />
<style>
*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background: transparent;user-select:none;-webkit-user-select:none;pointer-events:none}
#canvas{position:absolute;inset: 0;width:100%;height:100%;display:block}
</style>
</head>
<body>
<canvas id="canvas"></canvas>
<script>
(function(){
'use strict';
/* signal system broadcast renderer: particlePool, glitchEngine, audioContext, scale, locale */
/* Layers: background / perimeter frame / orbital / core / event data / glitch */

var locale = __LOCALE_JSON__;
var I18N = __I18N_JSON__;
function tr(key){var p=I18N[locale]||I18N.uk||{};return p[key]||(I18N.en||{})[key]||key;}
function trf(key,vars){var s=tr(key);if(vars){for(var k in vars)s=s.split('{'+k+'}').join(String(vars[k]));}return s;}

var wsUrl=(location.protocol==='https:'?'wss://':'ws://')+location.host+'/ws';
var ws=null,tries=0;
var canvas=document.getElementById('canvas');
var ctx=canvas.getContext('2d',{alpha:true});
var dpr=window.devicePixelRatio||1;
var VW=0,VH=0;

/* ---------- themes ---------- */
var THEME_PRESETS={
neon_cyber:{primary:'#00f0ff',secondary:'#bf00ff',accent:'#ff2a6d',text:'#e8fbff',subtext:'#8be9fa',rail:'#00c8dc'},
toxic_system:{primary:'#39ff14',secondary:'#c6ff00',accent:'#00ffa3',text:'#f0ffe8',subtext:'#a9ff8d',rail:'#2fe00f'},
ice_protocol:{primary:'#6fc8ff',secondary:'#e6f5ff',accent:'#2f9dff',text:'#f5fbff',subtext:'#a5dcff',rail:'#4fb4f0'},
amber_core:{primary:'#ffb300',secondary:'#ff5e00',accent:'#ffe600',text:'#fff8e7',subtext:'#ffd580',rail:'#e09a00'},
critical:{primary:'#ff2a55',secondary:'#ff7a5c',accent:'#ff003c',text:'#ffebee',subtext:'#ff9d8a',rail:'#e01e44'}};

function hexToRgb(h){h=String(h||'').replace('#','');if(h.length===3){h=h[0]+h[0]+h[1]+h[1]+h[2]+h[2];}if(h.length!==6)return null;var n=parseInt(h,16);if(isNaN(n))return null;return{r:(n>>16)&255,g:(n>>8)&255,b:n&255};}
function rgba(hex,a){var c=hexToRgb(hex);if(!c)return 'rgba(0,240,255,'+a+')';return 'rgba('+c.r+','+c.g+','+c.b+','+a+')';}
function deriveTheme(name,pa,sa){
var base=THEME_PRESETS[name]||THEME_PRESETS.neon_cyber;
var t={primary:base.primary,secondary:base.secondary,accent:base.accent,text:base.text,subtext:base.subtext,rail:base.rail};
if(pa&&hexToRgb(pa)){t.primary=pa.toLowerCase();t.rail=pa.toLowerCase();}
if(sa&&hexToRgb(sa)){t.secondary=sa.toLowerCase();}
t.glow=rgba(t.primary,0.35);t.glowStrong=rgba(t.primary,0.6);
t.glowSecondary=rgba(t.secondary,0.35);t.glowAccent=rgba(t.accent,0.5);
t.dataRail=rgba(t.primary,0.14);t.dataRailActive=rgba(t.primary,0.65);
t.field=rgba(t.primary,0.07);
return t;
}
var activeTheme=deriveTheme('neon_cyber','','');

/* ---------- state ---------- */
var state={config:{theme:'neon_cyber',idle_opacity_pct:35,active_opacity_pct:100,particles_enabled:true,glitch_enabled:true,perimeter_enabled:true,sound_enabled:false,font_family:'Share Tech Mono',custom_title:'SIGNAL // SYSTEM',scale_percent:100,core_vertical_pct:50,intensity_multiplier:1.0,primary_accent:'',secondary_accent:'',frame_detail_level:'full',particle_density:'standard',gift_icon_enabled:true,show_gift_quantity:true,show_coin_value:true,show_gift_name:true,reduced_motion:false},current_event:null,event_seq:0,idle_metrics:{activity_rate:0,system_status:'ONLINE',uptime_s:0}};
var reducedMotion=false;
try{reducedMotion=!!(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches);}catch(e){}
function motionOK(){return !(reducedMotion||!!state.config.reduced_motion);}
function updateTheme(){activeTheme=deriveTheme(state.config.theme||'neon_cyber',state.config.primary_accent||'',state.config.secondary_accent||'');}
/* Fill available browser-source box; scale element sizes (not uniform zoom) */
var widgetScale=1;
function u(n){return n*widgetScale;}
function applyScale(p){var v=Number(p);if(!isFinite(v))v=100;v=Math.max(40,Math.min(250,v));widgetScale=v/100;Layout.measure();}

/* ---------- ResponsiveLayout ---------- */
/* ---------- FrameCache: precomputed corner paths (must precede resize()) ---------- */
var FrameCache={corners:null,key:'',invalidate:function(){this.key='';},ensure:function(){var k=VW+'x'+VH+'|'+Layout.margin+'|'+Layout.corner;if(k===this.key&&this.corners)return;this.key=k;this.corners=this.build();},build:function(){var m=Layout.margin,c=Layout.corner;return{x0:m,y0:m,x1:VW-m,y1:VH-m,c:c};}};
function drawCross(x,y,s){ctx.beginPath();ctx.moveTo(x-s,y);ctx.lineTo(x+s,y);ctx.moveTo(x,y-s);ctx.lineTo(x,y+s);ctx.stroke();}
var Layout={margin:16,corner:40,minDim:100,coreR:80,giftBox:96,centerX:0,centerY:0,stageY:0,coreY:0,dataY:0,headerY:0,orbitR:90,nameY:0,userY:0,coinY:0,compact:false,narrow:false,tall:false,
measure:function(){
  var m=Math.max(14,Math.min(VW,VH)*0.022);var c=Math.max(24,Math.min(VW,VH)*0.048);
  this.margin=m;this.corner=c;this.minDim=Math.min(VW,VH);this.centerX=VW/2;
  this.compact=this.minDim<420;this.narrow=VW<480;this.tall=VH>VW*1.15;
  /* Core vertical position from config (%, default 50 = center); scale only sizes elements */
  var vPct=Number(state.config.core_vertical_pct);if(!isFinite(vPct))vPct=50;vPct=Math.max(20,Math.min(80,vPct));
  this.stageY=VH*(vPct/100);this.coreY=this.stageY;this.centerY=this.stageY;
  var safeTop=m+c+u(8);
  var safeBot=VH-(m+c+u(8));
  var headerBand=u(this.compact?26:32);
  var dataBand=u(this.compact?88:112);
  var gap=u(this.compact?12:18);
  /* Max radius that still leaves room for header above + data below */
  var maxUp=Math.max(u(36),this.stageY-(safeTop+headerBand+gap));
  var maxDown=Math.max(u(36),safeBot-dataBand-gap-this.stageY);
  var maxR=Math.min(maxUp,maxDown);
  var giftCap=Math.max(u(44),Math.min(this.minDim*(this.compact?0.15:0.11),u(118),maxR*0.85));
  this.giftBox=giftCap;
  this.orbitR=Math.max(this.giftBox*0.92,Math.min(maxR*0.98,this.giftBox*1.32,this.minDim*0.17*Math.min(widgetScale,1.35)));
  this.coreR=this.orbitR*0.70;
  /* Header above core; data stack below — both clear of rings */
  this.headerY=Math.max(safeTop+u(16),this.stageY-this.orbitR-gap-u(6));
  this.dataY=this.stageY+this.orbitR+gap;
  this.nameY=this.dataY;
  this.userY=this.nameY+u(this.compact?26:34);
  this.coinY=this.userY+u(this.compact?28:36);
  /* If coin rail would clip bottom, compress text gaps only — never move core */
  var coinRail=this.coinY+u(14);
  if(coinRail>safeBot){var squeeze=coinRail-safeBot;var step=Math.max(u(18),u(this.compact?26:34)-squeeze*0.35);this.userY=this.nameY+step;this.coinY=this.userY+Math.max(u(18),u(this.compact?28:36)-squeeze*0.35);}
}};
function resize(){
  dpr=Math.min(window.devicePixelRatio||1,1.5);
  VW=window.innerWidth;VH=window.innerHeight;
  canvas.width=Math.max(2,Math.floor(VW*dpr));
  canvas.height=Math.max(2,Math.floor(VH*dpr));
  ctx.setTransform(dpr,0,0,dpr,0,0);
  Layout.measure();FrameCache.invalidate();
}
window.addEventListener('resize',resize);
if(window.ResizeObserver){try{new ResizeObserver(function(){resize();}).observe(document.documentElement);}catch(e){}}
resize();

/* ---------- AudioController: layered restrained synth ---------- */
function AudioController(){this.ctx=null;this.master=null;}
AudioController.prototype.ensure=function(){if(!state.config.sound_enabled)return null;try{var AC=window.AudioContext||window.webkitAudioContext;if(!AC)return null;if(!this.ctx){this.ctx=new AC();this.master=this.ctx.createGain();this.master.gain.value=0.5;this.master.connect(this.ctx.destination);}if(this.ctx.state==='suspended'){this.ctx.resume().catch(function(){});}return this.ctx;}catch(e){return null;}};
AudioController.prototype.tone=function(o){var ac=this.ensure();if(!ac)return;try{var t0=ac.currentTime+(o.delay||0);var osc=ac.createOscillator();var g=ac.createGain();osc.type=o.type||'sine';osc.frequency.setValueAtTime(o.f0||440,t0);if(o.f1)osc.frequency.exponentialRampToValueAtTime(Math.max(20,o.f1),t0+(o.dur||0.2));g.gain.setValueAtTime(0.0001,t0);g.gain.exponentialRampToValueAtTime(o.vol||0.1,t0+(o.attack||0.012));g.gain.exponentialRampToValueAtTime(0.0001,t0+(o.dur||0.2));osc.connect(g);g.connect(this.master);osc.start(t0);osc.stop(t0+(o.dur||0.2)+0.05);}catch(e){}};
AudioController.prototype.activation=function(){this.tone({type:'sawtooth',f0:180,f1:900,dur:0.28,vol:0.05});this.tone({type:'sine',f0:1200,f1:2400,dur:0.16,vol:0.04,delay:0.05});};
AudioController.prototype.acquisition=function(){this.tone({type:'sine',f0:1560,f1:3120,dur:0.14,vol:0.05});};
AudioController.prototype.charge=function(i){this.tone({type:'triangle',f0:220,f1:660,dur:0.7,vol:0.05+0.05*(i||0.5)});this.tone({type:'sine',f0:440,f1:1320,dur:0.7,vol:0.035,delay:0.08});};
AudioController.prototype.tick=function(){this.tone({type:'square',f0:2400,f1:1800,dur:0.03,vol:0.018});};
AudioController.prototype.peak=function(i){var v=0.10+0.10*(i||0.7);this.tone({type:'sine',f0:90,f1:45,dur:0.5,vol:v});this.tone({type:'triangle',f0:330,f1:990,dur:0.4,vol:v*0.7,delay:0.02});this.tone({type:'sine',f0:1980,f1:3960,dur:0.3,vol:v*0.4,delay:0.04});};
AudioController.prototype.discharge=function(){this.tone({type:'sawtooth',f0:800,f1:120,dur:0.4,vol:0.05});};
AudioController.prototype.lost=function(){this.tone({type:'sine',f0:620,f1:310,dur:0.18,vol:0.045});};
var audio=new AudioController();

/* ---------- ParticleSystem (bounded) ---------- */
function ParticleSystem(){this.MAX=80;this.pool=[];this.activeCount=0;for(var i=0;i<this.MAX;i++)this.pool.push({active:false,x:0,y:0,vx:0,vy:0,size:2,life:1,maxLife:1,color:'#00f0ff'});this.cursor=0;}
ParticleSystem.prototype.densityMul=function(){var d=state.config.particle_density||'standard';if(d==='none')return 0;if(d==='low')return 0.4;if(d==='high')return 1.35;return 1.0;};
ParticleSystem.prototype.spawn=function(x,y,vx,vy,size,life,color){if(!state.config.particles_enabled)return;if(this.densityMul()<=0)return;var p=this.pool[this.cursor];this.cursor=(this.cursor+1)%this.MAX;if(!p.active)this.activeCount++;p.active=true;p.x=x;p.y=y;p.vx=vx;p.vy=vy;p.size=size;p.life=life;p.maxLife=life;p.color=color||activeTheme.primary;};
ParticleSystem.prototype.burst=function(cx,cy,count,speed,color){var m=this.densityMul();if(m<=0||!state.config.particles_enabled)return;count=Math.min(40,Math.round(count*m));for(var i=0;i<count;i++){var a=Math.random()*Math.PI*2;var s=(0.4+Math.random()*0.9)*speed;var vx=Math.cos(a)*s,vy=Math.sin(a)*s;this.spawn(cx,cy,vx,vy,1.4+Math.random()*2.6,0.5+Math.random()*0.9,color);}};
/* Ambient sparkles only during active signals — idle ambient is free FPS on OBS */
ParticleSystem.prototype.ambient=function(dt,active){if(!active||!state.config.particles_enabled||this.densityMul()<=0)return;if(Math.random()<dt*2.2*this.densityMul()){var edge=Math.floor(Math.random()*4);var x=Math.random()*VW,y=Math.random()*VH;if(edge===0)y=Layout.margin+Math.random()*20;else if(edge===1)y=VH-Layout.margin-Math.random()*20;this.spawn(x,y,(Math.random()-0.5)*8,(Math.random()-0.5)*8,1+Math.random()*1.6,2+Math.random()*2,activeTheme.primary);}};
ParticleSystem.prototype.updateDraw=function(dt){if(this.activeCount<=0)return;ctx.save();ctx.shadowBlur=0;for(var i=0;i<this.MAX;i++){var p=this.pool[i];if(!p.active)continue;p.x+=p.vx*(motionOK()?1:0.15);p.y+=p.vy*(motionOK()?1:0.15);p.life-=dt;if(p.life<=0){p.active=false;this.activeCount=Math.max(0,this.activeCount-1);continue;}var lr=p.life/p.maxLife;ctx.globalAlpha=lr*0.8;ctx.fillStyle=p.color;ctx.fillRect(p.x-p.size/2,p.y-p.size/2,p.size,p.size);}ctx.restore();};
var particles=new ParticleSystem();

/* ---------- glitchEngine ---------- */
var glitchIntensity=0,glitchOX=0,glitchOY=0;
function triggerGlitch(a){if(!state.config.glitch_enabled||!motionOK())return;glitchIntensity=Math.max(glitchIntensity,a);}

/* ---------- helpers ---------- */
var CHAR_SET='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789//<>_#@$%&*!=+';
function scramble(target,progress){if(progress>=1)return target;target=String(target==null?'':target);var locked=Math.floor(target.length*progress);var out='';for(var i=0;i<target.length;i++){var ch=target[i];if(i<locked||ch===' '||ch==='/'||ch===':'||ch==='.')out+=ch;else out+=CHAR_SET[(Math.random()*CHAR_SET.length)|0];}return out;}
function hexA(hex,a){return rgba(hex,a);}
function fontOf(px,w,fam){return w+' '+u(px)+'px "'+fam+'", "Share Tech Mono", monospace';}
/* edge-anchored HUD readouts: status/title/coords pinned to frame rails */
function parseCoins(valueStr){var m=String(valueStr||'').replace(/,/g,'').match(/([0-9]+)/);if(!m)return 0;return parseInt(m[1],10)||0;}
function clamp(v,a,b){return Math.max(a,Math.min(b,v));}
function easeOut(t){return 1-Math.pow(1-t,3);}
function easeInOut(t){return t<0.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2;}

/* ---------- SignalStateMachine ---------- */
function SignalStateMachine(){}
SignalStateMachine.prototype.phaseFor=function(elapsed,duration){if(duration<=0)return{phase:'idle',progress:0,t:0};var t=clamp(elapsed/duration,0,1);
var bounds=[['detecting',0,0.07],['acquiring',0.07,0.18],['decoding',0.18,0.34],['active',0.34,0.66],['peak',0.66,0.84],['discharge',0.84,0.94],['lost',0.94,0.985],['return_to_idle',0.985,1.01]];
for(var i=0;i<bounds.length;i++){var b=bounds[i];if(t>=b[1]&&t<b[2])return{phase:b[0],progress:(t-b[1])/(b[2]-b[1]),t:t};}return{phase:'idle',progress:0,t:t};};
var stateMachine=new SignalStateMachine();

/* ---------- SignalEventProcessor: normalize raw event ---------- */
function SignalEventProcessor(){}
SignalEventProcessor.prototype.isGift=function(ev){return ev&&(ev.type==='big_gift'||ev.type==='mega_gift');};
SignalEventProcessor.prototype.giftModel=function(ev){ev=ev||{};var q=parseInt(ev.gift_quantity,10);if(!isFinite(q)||q<1)q=1;var coins=parseInt(ev.coin_value,10);if(!isFinite(coins))coins=parseCoins(ev.value);return{giftId:String(ev.gift_id||''),giftName:String(ev.gift_name||''),iconUrl:String(ev.gift_icon_url||''),iconSource:String(ev.gift_icon_source||'none'),quantity:q,coins:coins,sender:String(ev.username||ev.sender||''),hasIcon:!!String(ev.gift_icon_url||'')&&state.config.gift_icon_enabled!==false};};
var eventProcessor=new SignalEventProcessor();

/* ---------- FrameRenderer (sequential wake TOP→RIGHT→BOTTOM→LEFT→corners) ---------- */
function FrameRenderer(){this.railPos=0;this.railPos2=0.37;this.lockGlow=0;}
FrameRenderer.prototype.update=function(dt,active){this.railPos=(this.railPos+dt*(active?0.9:0.14)*(motionOK()?1:0.2))%1;this.railPos2=(this.railPos2+dt*(active?0.7:0.09)*(motionOK()?1:0.2))%1;if(active)this.lockGlow=Math.min(1,this.lockGlow+dt*1.8);else this.lockGlow=Math.max(0,this.lockGlow-dt*1.2);};
FrameRenderer.prototype.wake=function(info){
  /* Frame wake progress: rails illuminate in engineered order during signal acquisition */
  var phase=info.phase,pp=info.phaseProgress||0;
  if(phase==='idle'||phase==='return_to_idle')return{top:1,right:1,bottom:1,left:1,corners:0.35,energy:0,locked:false};
  if(phase==='detecting')return{top:clamp(pp,0,1),right:0,bottom:0,left:0,corners:0,energy:0,locked:false};
  if(phase==='acquiring')return{top:1,right:clamp(pp,0,1),bottom:0,left:0,corners:pp*0.25,energy:pp*0.55,locked:false};
  if(phase==='decoding')return{top:1,right:1,bottom:clamp(pp,0,1),left:clamp(pp,0,1),corners:0.35+pp*0.65,energy:0.55+pp*0.45,locked:pp>0.82};
  if(phase==='lost'||phase==='discharge')return{top:1,right:1,bottom:1,left:1,corners:1-pp*0.4,energy:1-pp*0.5,locked:true};
  return{top:1,right:1,bottom:1,left:1,corners:1,energy:1,locked:true};
};
FrameRenderer.prototype.angularCorner=function(x,y,s,flipX,flipY,bright){var fx=flipX?-1:1,fy=flipY?-1:1;ctx.save();ctx.translate(x,y);ctx.scale(fx,fy);ctx.beginPath();ctx.moveTo(0,s);ctx.lineTo(0,10);ctx.lineTo(6,4);ctx.lineTo(10,4);ctx.lineTo(16,10);ctx.lineTo(16,16);ctx.lineTo(10,16);ctx.lineTo(4,10);ctx.lineTo(4,s*0.55);ctx.lineTo(s*0.55,4);ctx.lineTo(s,4);ctx.lineTo(s,0);ctx.lineTo(0,0);ctx.closePath();ctx.stroke();ctx.restore();};
FrameRenderer.prototype.draw=function(info){if(!state.config.perimeter_enabled)return;FrameCache.ensure();var g=FrameCache.corners;var m=Layout.margin;var x0=g.x0,y0=g.y0,x1=g.x1,y1=g.y1,c=g.c;var active=info.phase!=='idle';var detail=state.config.frame_detail_level||'full';var inten=info.intensity||0.6;
var idleA=(state.config.idle_opacity_pct||35)/100,actA=(state.config.active_opacity_pct||100)/100;var master=active?actA:idleA;var breathe=motionOK()?0.86+Math.sin(info.time*1.6)*0.14:0.95;var alpha=master*(active?1:breathe);
var wake=this.wake(info);var glowOn=active&&motionOK();
ctx.save();ctx.shadowBlur=0;
function seg(xa,ya,xb,yb,t0,t1){ctx.beginPath();ctx.moveTo(xa+(xb-xa)*t0,ya+(yb-ya)*t0);ctx.lineTo(xa+(xb-xa)*t1,ya+(yb-ya)*t1);ctx.stroke();}
ctx.strokeStyle=activeTheme.rail;ctx.lineWidth=2;if(glowOn){ctx.shadowColor=activeTheme.glow;ctx.shadowBlur=Math.min(10,8*inten);}
/* TOP rail */
if(wake.top>0.02){ctx.globalAlpha=alpha*wake.top;seg(x0+c+8,y0,x1-c-8,y0,0,0.42);seg(x0+c+8,y0,x1-c-8,y0,0.47,1);}
/* RIGHT rail */
if(wake.right>0.02){ctx.globalAlpha=alpha*wake.right;seg(x1,y0+c+8,x1,y1-c-8,0,0.62);seg(x1,y0+c+8,x1,y1-c-8,0.70,1);}
/* BOTTOM rail */
if(wake.bottom>0.02){ctx.globalAlpha=alpha*wake.bottom;seg(x0+c+8,y1,x1-c-8,y1,0,0.55);seg(x0+c+8,y1,x1-c-8,y1,0.63,1);}
/* LEFT rail */
if(wake.left>0.02){ctx.globalAlpha=alpha*wake.left;seg(x0,y0+c+8,x0,y1-c-8,0,0.30);seg(x0,y0+c+8,x0,y1-c-8,0.38,1);}
ctx.shadowBlur=0;ctx.globalAlpha=alpha*Math.max(wake.corners,0.15);
/* angular corners — lock intensity rises after rails */
this.angularCorner(x0,y0,c,false,false,active);this.angularCorner(x1,y0,c,true,false,active);this.angularCorner(x0,y1,c,false,true,active);this.angularCorner(x1,y1,c,true,true,active);
/* secondary inner rail */
if(detail!=='minimal'&&wake.top>0.4){ctx.lineWidth=1;ctx.globalAlpha=alpha*0.5*wake.top;var ins=7;seg(x0+c+ins+14,y0+ins,x1-c-ins-14,y0+ins,0,0.36);seg(x0+c+ins+14,y0+ins,x1-c-ins-14,y0+ins,0.44,1);if(wake.bottom>0.3){seg(x0+c+ins+14,y1-ins,x1-c-ins-14,y1-ins,0,0.6);seg(x0+c+ins+14,y1-ins,x1-c-ins-14,y1-ins,0.68,1);}if(wake.left>0.3)seg(x0+ins,y0+c+ins+14,x0+ins,y1-c-ins-14,0,1);if(wake.right>0.3){seg(x1-ins,y0+c+ins+14,x1-ins,y1-c-ins-14,0,0.5);seg(x1-ins,y0+c+ins+14,x1-ins,y1-c-ins-14,0.58,1);}}
/* calibration ticks — only while active (idle FPS win); batch into one path */
if(detail==='full'&&active&&wake.top>0.6){ctx.lineWidth=1;ctx.globalAlpha=alpha*0.55*wake.top;ctx.beginPath();var tw=(x1-c-30)-(x0+c+30);var n=Math.max(6,Math.min(18,Math.floor(tw/52)));for(var i=0;i<=n;i++){var tx=(x0+c+30)+tw*i/n;var big=(i%4===0);ctx.moveTo(tx,y0+3);ctx.lineTo(tx,y0+(big?9:6));if(wake.bottom>0.5){ctx.moveTo(tx,y1-3);ctx.lineTo(tx,y1-(big?9:6));}}ctx.stroke();}
/* connector nodes */
ctx.globalAlpha=alpha*0.9*Math.max(wake.top,wake.right,wake.bottom,wake.left);ctx.fillStyle=activeTheme.primary;if(glowOn){ctx.shadowColor=activeTheme.glow;ctx.shadowBlur=6;}
var nodes=[[x0+c+4,y0,wake.top],[x1-c-4,y0,wake.top],[x0+c+4,y1,wake.bottom],[x1-c-4,y1,wake.bottom],[x0,y0+c+4,wake.left],[x0,y1-c-4,wake.left],[x1,y0+c+4,wake.right],[x1,y1-c-4,wake.right]];
for(var ni=0;ni<nodes.length;ni++){if(nodes[ni][2]<0.15)continue;ctx.globalAlpha=alpha*0.9*nodes[ni][2];ctx.fillRect(nodes[ni][0]-2,nodes[ni][1]-2,4,4);}
ctx.shadowBlur=0;
/* corner lock diamonds */
if(active&&wake.corners>0.2){ctx.save();ctx.globalAlpha=alpha*(0.35+0.65*wake.corners);ctx.fillStyle=activeTheme.secondary;if(glowOn){ctx.shadowColor=activeTheme.glowSecondary;ctx.shadowBlur=wake.locked?10:6;}var cs=[[x0,y0],[x1,y0],[x0,y1],[x1,y1]];for(var ci=0;ci<4;ci++){var px=cs[ci][0],py=cs[ci][1];ctx.beginPath();ctx.moveTo(px-5,py);ctx.lineTo(px,py-5);ctx.lineTo(px+5,py);ctx.lineTo(px,py+5);ctx.closePath();if(wake.locked||wake.corners>0.7)ctx.fill();else ctx.stroke();}ctx.restore();}
/* energy traces: frame → stage center */
if(active&&wake.energy>0.08){ctx.save();ctx.globalAlpha=alpha*0.32*wake.energy;ctx.strokeStyle=activeTheme.primary;ctx.lineWidth=1;ctx.shadowBlur=0;var cx=Layout.centerX,cy=Layout.stageY;var pts=[[x0+c,y0],[x1-c,y0],[x0,y1-c],[x1,y1-c]];ctx.beginPath();for(var pi=0;pi<4;pi++){ctx.moveTo(pts[pi][0],pts[pi][1]);ctx.lineTo(pts[pi][0]+(cx-pts[pi][0])*wake.energy,pts[pi][1]+(cy-pts[pi][1])*wake.energy);}ctx.stroke();ctx.restore();}
/* moving energy packets — only on woken rails */
ctx.save();ctx.shadowBlur=0;ctx.fillStyle=activeTheme.secondary;
var topLen=(x1-c-8)-(x0+c+8);if(topLen>30&&wake.top>0.5){var px=this.railPos*topLen;ctx.globalAlpha=alpha*0.95*wake.top;ctx.fillRect(x0+c+8+px-9,y0-1.5,18,3);if(wake.bottom>0.5){var px2=this.railPos2*topLen;ctx.globalAlpha=alpha*0.6*wake.bottom;ctx.fillRect(x1-c-8-px2-7,y1-1.5,14,3);}}
var sideLen=(y1-c-8)-(y0+c+8);if(sideLen>30){if(wake.left>0.5){var py=this.railPos2*sideLen;ctx.globalAlpha=alpha*0.7*wake.left;ctx.fillRect(x0-1.5,y0+c+8+py-7,3,14);}if(wake.right>0.5){var py2=this.railPos*sideLen;ctx.globalAlpha=alpha*0.85*wake.right;ctx.fillRect(x1-1.5,y1-c-8-py2-7,3,14);}}
ctx.restore();
/* micro HUD */
ctx.save();ctx.shadowBlur=0;var fam=state.config.font_family||'Share Tech Mono';ctx.font=fontOf(11,600,fam);ctx.fillStyle=activeTheme.text;ctx.globalAlpha=alpha*0.8*Math.max(0.4,wake.top);
ctx.textAlign='left';var sysRaw=(state.idle_metrics.system_status||'ONLINE');var sysSt=(sysRaw==='OFFLINE')?tr('goal.offline'):tr('goal.online');var actR=(state.idle_metrics.activity_rate||0);
ctx.fillText(tr('overlay.sys')+' '+sysSt+'  |  '+tr('overlay.act')+' '+actR+tr('overlay.per_min'),x0+8,y0+c+17);
var title=state.config.custom_title;if(!title||title==='SIGNAL // SYSTEM')title=tr('goal.system');ctx.textAlign='right';ctx.fillText('[ '+title+' ]',x1-8,y0+c+17);ctx.textAlign='left';
if(!Layout.compact&&active&&wake.bottom>0.4){ctx.globalAlpha=alpha*0.55*wake.bottom;ctx.fillText(tr('overlay.grid_link'),x0+8,y1-c-8);ctx.fillText(trf('overlay.sec_pwr',{n:Math.round(60+inten*40)}),x0+8,y1-c-22);}
var bars=6,bw=4,bgap=3;var sx=x1-(bars*(bw+bgap))-8;for(var b=0;b<bars;b++){var bh=4+Math.abs(Math.sin(info.time*2.4+b*0.9))*(active?12:8);ctx.globalAlpha=alpha*0.8*Math.max(0.35,wake.right);ctx.fillStyle=b>3?activeTheme.secondary:activeTheme.primary;ctx.fillRect(sx+b*(bw+bgap),y1-c-4-bh,bw,bh);}
ctx.globalAlpha=alpha*0.7*Math.max(0.35,wake.top);for(var sg=0;sg<4;sg++){ctx.strokeStyle=sg<3?activeTheme.primary:activeTheme.secondary;ctx.lineWidth=1;ctx.strokeRect(x1-8-3*8+sg*8-4,y0+6,5,5);}
ctx.restore();ctx.restore();
};
var frameRenderer=new FrameRenderer();

/* ---------- CoreRenderer: orbital containment around gift / signal core for non-gifts ---------- */
function CoreRenderer(){}
CoreRenderer.prototype.polygon=function(r,sides,rot,irr,time){ctx.beginPath();for(var i=0;i<sides;i++){var a=rot+i/sides*Math.PI*2;var rr=r*(1+irr*Math.sin(time*1.3+i*2.1));var x=Math.cos(a)*rr,y=Math.sin(a)*rr;if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);}ctx.closePath();};
CoreRenderer.prototype.isGiftEvent=function(){if(!activeEvent)return false;var k=activeEvent.type||'';return k==='big_gift'||k==='mega_gift';};
CoreRenderer.prototype.draw=function(info){if(this.isGiftEvent())this.drawGiftContainment(info);else this.drawSignalCore(info);};
CoreRenderer.prototype.drawEnergyWell=function(alpha,inten,phase,time,flare){
  /* Subdued energy well under gift — small, does not cover the icon */
  var wellR=Layout.giftBox*0.38*(1+flare*0.35);var pulse=0.85+(motionOK()?Math.sin(time*(phase==='peak'?8:4))*0.1:0);
  var cg=ctx.createRadialGradient(0,0,0,0,0,wellR*1.5);
  cg.addColorStop(0,hexA('#ffffff',0.12+flare*0.22));
  cg.addColorStop(0.35,hexA(activeTheme.primary,0.14*inten+0.05+flare*0.15));
  cg.addColorStop(0.7,hexA(activeTheme.secondary,0.06+flare*0.08));
  cg.addColorStop(1,'rgba(0,0,0,0)');
  ctx.globalAlpha=alpha*(0.4+flare*0.3)*pulse;ctx.fillStyle=cg;ctx.beginPath();ctx.arc(0,0,wellR*1.5,0,Math.PI*2);ctx.fill();
};
CoreRenderer.prototype.drawGiftContainment=function(info){
  /* Engineered orbital rings contain the gift hero; independent ring motions */
  var cx=Layout.centerX+glitchOX,cy=Layout.stageY+glitchOY;var R=Layout.orbitR;var inten=info.intensity||0.6;var phase=info.phase,pp=info.phaseProgress,time=info.time;
  var scale=1,alpha=1;
  if(phase==='detecting'){scale=0.55+pp*0.25;alpha=pp*0.7;}
  else if(phase==='acquiring'){scale=0.8+pp*0.2;alpha=0.75+pp*0.25;}
  else if(phase==='decoding'||phase==='active'){scale=1+(motionOK()?Math.sin(time*2.4)*0.015:0);alpha=1;}
  else if(phase==='peak'){scale=1.02+(motionOK()?Math.sin(time*28)*0.012*inten:0);alpha=1;}
  else if(phase==='discharge'){scale=1+pp*0.2;alpha=1-pp*0.85;}
  else if(phase==='lost'||phase==='return_to_idle'){scale=1.15;alpha=Math.max(0,1-pp*1.35);}
  alpha*=(info.alphaMul==null?1:info.alphaMul);if(alpha<=0.01)return;
  var glowOn=motionOK();var dens=0.7+inten*0.5;var spd=0.7+inten*0.9;var RR=R*scale;
  var flare=0;if(phase==='active')flare=0.25+pp*0.35;else if(phase==='peak')flare=0.85+pp*0.15;else if(phase==='decoding')flare=pp*0.2;
  ctx.save();ctx.globalAlpha=alpha;ctx.translate(cx,cy);ctx.shadowBlur=0;
  /* dim ambient field (under gift) — keep tight so text below stays clear */
  var bg=ctx.createRadialGradient(0,0,4,0,0,RR*1.15);bg.addColorStop(0,hexA(activeTheme.primary,0.05*inten+0.02+flare*0.04));bg.addColorStop(0.65,hexA(activeTheme.primary,0.015));bg.addColorStop(1,'rgba(0,0,0,0)');ctx.fillStyle=bg;ctx.beginPath();ctx.arc(0,0,RR*1.15,0,Math.PI*2);ctx.fill();
  this.drawEnergyWell(alpha,inten,phase,time,flare);
  /* OUTER: calibration ticks — stay within orbitR */
  ctx.save();ctx.rotate(time*0.18*spd*(motionOK()?1:0.2));ctx.strokeStyle=activeTheme.primary;ctx.globalAlpha=alpha*0.5*dens;ctx.lineWidth=1;ctx.beginPath();
  var tickN=phase==='peak'?28:18;for(var ti=0;ti<tickN;ti++){var a=ti/tickN*Math.PI*2;var big=ti%5===0;var r1=RR*0.96,r2=RR*0.96+(big?6:3);ctx.moveTo(Math.cos(a)*r1,Math.sin(a)*r1);ctx.lineTo(Math.cos(a)*r2,Math.sin(a)*r2);}ctx.stroke();ctx.restore();
  /* OUTER thin ring */
  ctx.save();ctx.globalAlpha=alpha*0.65;ctx.strokeStyle=activeTheme.primary;ctx.lineWidth=1.15;if(glowOn&&flare>0.2){ctx.shadowColor=activeTheme.glow;ctx.shadowBlur=Math.min(6,4+flare*3);}ctx.beginPath();ctx.arc(0,0,RR*0.94,0,Math.PI*2);ctx.stroke();ctx.restore();
  /* MIDDLE: segmented containment ring */
  ctx.save();ctx.rotate(-time*(phase==='peak'?2.4:1.05)*spd*(motionOK()?1:0.25));ctx.strokeStyle=activeTheme.secondary;if(glowOn){ctx.shadowColor=activeTheme.glowSecondary;ctx.shadowBlur=Math.min(6,4+inten*3);}ctx.lineWidth=2.2;ctx.setLineDash([RR*0.34,RR*0.18,RR*0.07,RR*0.18]);ctx.globalAlpha=alpha*0.8*dens;ctx.beginPath();ctx.arc(0,0,RR*0.78,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);ctx.restore();
  /* tracking diamonds on middle ring */
  ctx.save();ctx.rotate(time*0.65*spd*(motionOK()?1:0.2));ctx.shadowBlur=0;var mk=phase==='peak'?8:6;for(var mi=0;mi<mk;mi++){var ma=mi/mk*Math.PI*2;var mx=Math.cos(ma)*RR*0.78,my=Math.sin(ma)*RR*0.78;ctx.save();ctx.translate(mx,my);ctx.rotate(ma);ctx.fillStyle=mi%2?activeTheme.secondary:activeTheme.primary;ctx.globalAlpha=alpha*(mi%2?0.8:0.45)*dens;var ms=mi%2?2.6:1.8;ctx.beginPath();ctx.moveTo(0,-ms);ctx.lineTo(ms,0);ctx.lineTo(0,ms);ctx.lineTo(-ms,0);ctx.closePath();ctx.fill();ctx.restore();}ctx.restore();
  /* INNER irregular containment polygon */
  ctx.save();ctx.rotate(time*0.32*(motionOK()?1:0.15));ctx.strokeStyle=activeTheme.text;ctx.globalAlpha=alpha*0.35;ctx.lineWidth=1;ctx.shadowBlur=0;this.polygon(RR*0.58,7,time*0.15,0.04,time);ctx.stroke();ctx.restore();
  /* broken arcs */
  ctx.save();ctx.strokeStyle=activeTheme.secondary;ctx.globalAlpha=alpha*0.55*dens;ctx.lineWidth=1.4;ctx.shadowBlur=0;ctx.beginPath();ctx.arc(0,0,RR*0.45,time*0.85*spd,time*0.85*spd+1.8);ctx.stroke();ctx.beginPath();ctx.arc(0,0,RR*0.38,-time*0.6*spd+1,-time*0.6*spd+2.2);ctx.stroke();ctx.restore();
  /* transfer filaments — peak/active only, stay inside middle ring */
  if(phase==='active'||phase==='peak'||(phase==='decoding'&&pp>0.7)){ctx.save();ctx.shadowBlur=0;var fil=phase==='peak'?4:2;for(var li=0;li<fil;li++){var la=time*(phase==='peak'?1.6:0.65)*spd*(motionOK()?1:0.2)+li/fil*Math.PI*2;ctx.strokeStyle=li%2?activeTheme.primary:activeTheme.text;ctx.globalAlpha=alpha*(0.15+0.2*inten+flare*0.15);ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(Math.cos(la)*RR*0.3,Math.sin(la)*RR*0.3);ctx.lineTo(Math.cos(la)*RR*0.1,Math.sin(la)*RR*0.1);ctx.stroke();}ctx.restore();}
  ctx.restore();
};
CoreRenderer.prototype.drawSignalCore=function(info){var cx=Layout.centerX+glitchOX,cy=Layout.stageY+glitchOY;var r=Layout.coreR;var inten=info.intensity||0.6;var phase=info.phase,pp=info.phaseProgress,time=info.time;
var scale=1,alpha=1;
if(phase==='detecting'){scale=0.25+pp*0.5;alpha=pp;}
else if(phase==='acquiring'){scale=0.75+pp*0.25;alpha=1;}
else if(phase==='decoding'||phase==='active'){scale=1+(motionOK()?Math.sin(time*3.2)*0.03:0);alpha=1;}
else if(phase==='peak'){var j=motionOK()?Math.sin(time*31)*0.02*inten:0;scale=1.02+j;alpha=1;}
else if(phase==='discharge'){scale=1+pp*0.35;alpha=1-pp;}
else if(phase==='lost'||phase==='return_to_idle'){scale=1.3;alpha=Math.max(0,1-pp*1.4);}
alpha*=(info.alphaMul==null?1:info.alphaMul);
if(alpha<=0.01)return;var R=r*scale;var glowOn=motionOK();
ctx.save();ctx.globalAlpha=alpha;ctx.translate(cx,cy);ctx.shadowBlur=0;
var bg=ctx.createRadialGradient(0,0,4,0,0,R*2.0);bg.addColorStop(0,hexA(activeTheme.primary,0.10*inten+0.04));bg.addColorStop(0.55,hexA(activeTheme.primary,0.03));bg.addColorStop(1,'rgba(0,0,0,0)');ctx.fillStyle=bg;ctx.beginPath();ctx.arc(0,0,R*2.0,0,Math.PI*2);ctx.fill();
ctx.save();ctx.rotate(time*0.25*(motionOK()?1:0.2));ctx.strokeStyle=activeTheme.primary;ctx.globalAlpha=alpha*0.7;ctx.lineWidth=1;ctx.beginPath();
var tickN=phase==='peak'?36:24;for(var ti=0;ti<tickN;ti++){var a=ti/tickN*Math.PI*2;var big=ti%6===0;var r1=R*1.18,r2=R*1.18+(big?9:5);ctx.moveTo(Math.cos(a)*r1,Math.sin(a)*r1);ctx.lineTo(Math.cos(a)*r2,Math.sin(a)*r2);}ctx.stroke();ctx.restore();
ctx.save();ctx.globalAlpha=alpha*0.85;ctx.strokeStyle=activeTheme.primary;ctx.lineWidth=1.4;if(glowOn){ctx.shadowColor=activeTheme.glow;ctx.shadowBlur=8;}ctx.beginPath();ctx.arc(0,0,R,0,Math.PI*2);ctx.stroke();ctx.restore();
ctx.save();ctx.rotate(-time*(phase==='peak'?3.4:1.5)*(motionOK()?1:0.25));ctx.strokeStyle=activeTheme.secondary;if(glowOn){ctx.shadowColor=activeTheme.glowSecondary;ctx.shadowBlur=8;}ctx.lineWidth=3;ctx.setLineDash([R*0.42,R*0.22,R*0.10,R*0.22]);ctx.globalAlpha=alpha*0.95;ctx.beginPath();ctx.arc(0,0,R*0.85,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);ctx.restore();
ctx.save();ctx.rotate(time*0.9*(motionOK()?1:0.2));ctx.shadowBlur=0;for(var mi=0;mi<8;mi++){var ma=mi/8*Math.PI*2;var mx=Math.cos(ma)*R*0.85,my=Math.sin(ma)*R*0.85;ctx.save();ctx.translate(mx,my);ctx.rotate(ma);ctx.fillStyle=mi%2?activeTheme.secondary:activeTheme.primary;ctx.globalAlpha=alpha*(mi%2?0.9:0.6);var ms=mi%2?3.4:2.2;ctx.beginPath();ctx.moveTo(0,-ms);ctx.lineTo(ms,0);ctx.lineTo(0,ms);ctx.lineTo(-ms,0);ctx.closePath();ctx.fill();ctx.restore();}ctx.restore();
ctx.save();ctx.rotate(time*0.5*(motionOK()?1:0.15));ctx.strokeStyle=activeTheme.text;ctx.globalAlpha=alpha*0.5;ctx.lineWidth=1.2;ctx.shadowBlur=0;this.polygon(R*0.62,7,time*0.2,0.06,time);ctx.stroke();ctx.restore();
if(phase==='peak'||phase==='decoding'||phase==='active'){ctx.save();for(var fi=0;fi<3;fi++){ctx.save();ctx.rotate(time*(0.4+fi*0.23)*(fi%2?1:-1)*(motionOK()?1:0.2)+fi*2.1);ctx.globalAlpha=alpha*0.13;ctx.fillStyle=activeTheme.primary;ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(Math.cos(fi*2.1)*R*0.55,Math.sin(fi*2.1)*R*0.55);ctx.lineTo(Math.cos(fi*2.1+0.9)*R*0.42,Math.sin(fi*2.1+0.9)*R*0.42);ctx.closePath();ctx.fill();ctx.restore();}ctx.restore();}
ctx.save();ctx.strokeStyle=activeTheme.secondary;ctx.globalAlpha=alpha*0.75;ctx.lineWidth=2;if(glowOn){ctx.shadowColor=activeTheme.glowSecondary;ctx.shadowBlur=6;}ctx.beginPath();ctx.arc(0,0,R*0.45,time*1.1,time*1.1+2.2);ctx.stroke();ctx.beginPath();ctx.arc(0,0,R*0.38,-time*0.8+1,-time*0.8+2.6);ctx.stroke();ctx.restore();
ctx.save();ctx.shadowBlur=0;var fil=phase==='peak'?6:4;for(var li=0;li<fil;li++){var la=time*(phase==='peak'?2.2:0.9)*(motionOK()?1:0.2)+li/fil*Math.PI*2;var wob=motionOK()?Math.sin(time*6+li*1.7)*R*0.06:0;ctx.strokeStyle=li%2?activeTheme.primary:activeTheme.text;ctx.globalAlpha=alpha*(0.35+0.3*inten);ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(0,0);ctx.quadraticCurveTo(Math.cos(la)*R*0.2+wob,Math.sin(la)*R*0.2,Math.cos(la)*R*0.42,Math.sin(la)*R*0.42);ctx.stroke();}ctx.restore();
var pulse=0.85+(motionOK()?Math.sin(time*(phase==='peak'?11:6))*0.15:0);var nr=R*0.26*pulse*(phase==='peak'?1.25:1);var cg=ctx.createRadialGradient(0,0,0,0,0,nr*1.7);cg.addColorStop(0,'#ffffff');cg.addColorStop(0.28,activeTheme.primary);cg.addColorStop(0.65,activeTheme.secondary);cg.addColorStop(1,'rgba(0,0,0,0)');ctx.fillStyle=cg;ctx.globalAlpha=alpha;ctx.beginPath();ctx.arc(0,0,nr*1.7,0,Math.PI*2);ctx.fill();
ctx.restore();};
var coreRenderer=new CoreRenderer();

/* ---------- GiftRenderer ---------- */
function GiftRenderer(){this.cache=new Map();this.sweepT=0;}
GiftRenderer.prototype.allowedHost=function(url){try{var a=document.createElement('a');a.href=url;var h=(a.hostname||'').toLowerCase();if(!h)return false;var ok=['tiktokcdn.com','tiktokcdn-us.com','tiktokcdn-eu.com','ibytedtos.com'];for(var i=0;i<ok.length;i++){if(h===ok[i]||h.slice(-ok[i].length-1)==='.'+ok[i])return true;}return false;}catch(e){return false;}};
GiftRenderer.prototype.getIcon=function(url){if(!url)return null;if(this.cache.has(url)){var e=this.cache.get(url);this.cache.delete(url);this.cache.set(url,e);return e;}var img=new Image();img.crossOrigin='anonymous';img.referrerPolicy='no-referrer';var entry={img:img,loaded:false,broken:false};var self=this;img.onload=function(){entry.loaded=true;};img.onerror=function(){entry.broken=true;};try{img.src=url;}catch(e){entry.broken=true;}this.cache.set(url,entry);if(this.cache.size>50){var k=this.cache.keys().next().value;this.cache.delete(k);}return entry;};
GiftRenderer.prototype.drawSocket=function(x,y,box,prog,time,inten,scan){var half=box/2;ctx.save();ctx.translate(x,y);ctx.shadowBlur=0;
/* containment energy field under gift */
var fg=ctx.createRadialGradient(0,0,4,0,0,half*1.55);fg.addColorStop(0,hexA(activeTheme.primary,0.12*inten+0.05));fg.addColorStop(1,'rgba(0,0,0,0)');ctx.fillStyle=fg;ctx.fillRect(-half*1.55,-half*1.55,half*3.1,half*3.1);
/* empty socket plate */
ctx.globalAlpha=clamp(prog*1.5,0,1)*0.35;ctx.fillStyle=hexA(activeTheme.primary,0.08);ctx.fillRect(-half+4,-half+4,box-8,box-8);
/* segmented containment brackets */
ctx.strokeStyle=activeTheme.primary;ctx.lineWidth=1.7;ctx.globalAlpha=clamp(prog*1.4,0,1);var bl=half*0.44;
ctx.beginPath();ctx.moveTo(-half,-half+bl);ctx.lineTo(-half,-half);ctx.lineTo(-half+bl,-half);ctx.stroke();
ctx.beginPath();ctx.moveTo(half-bl,-half);ctx.lineTo(half,-half);ctx.lineTo(half,-half+bl);ctx.stroke();
ctx.beginPath();ctx.moveTo(-half,half-bl);ctx.lineTo(-half,half);ctx.lineTo(-half+bl,half);ctx.stroke();
ctx.beginPath();ctx.moveTo(half-bl,half);ctx.lineTo(half,half);ctx.lineTo(half,half-bl);ctx.stroke();
/* side ticks */
ctx.globalAlpha=clamp(prog,0,1)*0.55;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(-half,-4);ctx.lineTo(-half-6,-4);ctx.moveTo(-half,4);ctx.lineTo(-half-6,4);ctx.moveTo(half,-4);ctx.lineTo(half+6,-4);ctx.moveTo(half,4);ctx.lineTo(half+6,4);ctx.stroke();
/* scan beam across empty/filling socket */
if(scan&&scan>0&&scan<1){var sy=-half+box*easeOut(scan);ctx.globalAlpha=0.55;ctx.fillStyle=hexA(activeTheme.secondary,0.55);ctx.fillRect(-half,sy-1,box,2);ctx.globalAlpha=0.18;ctx.fillStyle=hexA(activeTheme.secondary,0.35);ctx.fillRect(-half,-half,box,sy+half);}
ctx.restore();
/* micro-ring rotating around socket */
ctx.save();ctx.translate(x,y);ctx.rotate((motionOK()?time*1.35:0.4));ctx.strokeStyle=activeTheme.secondary;ctx.globalAlpha=clamp(prog,0,1)*0.75;ctx.lineWidth=1.15;ctx.shadowBlur=0;ctx.setLineDash([half*0.48,half*0.28]);ctx.beginPath();ctx.arc(0,0,half+8,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);ctx.restore();
ctx.save();ctx.translate(x,y);ctx.rotate((motionOK()?time*2.1:0.6));ctx.fillStyle=activeTheme.secondary;ctx.globalAlpha=clamp(prog,0,1);ctx.beginPath();ctx.arc(half+8,0,2.1,0,Math.PI*2);ctx.fill();ctx.restore();};
GiftRenderer.prototype.drawIcon=function(entry,x,y,box,prog,time,inten,acq){if(!entry||!entry.loaded||entry.broken)return false;var half=box/2;var iw=entry.img.naturalWidth||box,ih=entry.img.naturalHeight||box;var s=Math.min((box*0.78)/iw,(box*0.78)/ih);var dw=iw*s,dh=ih*s;
/* fragment / glitch resolve → clean materialization */
var jx=0,jy=0,frag=acq!=null&&acq<1;if(frag&&motionOK()){jx=(Math.random()-0.5)*10*(1-acq);jy=(Math.random()-0.5)*7*(1-acq);}
ctx.save();ctx.globalAlpha=clamp(prog,0,1);ctx.shadowBlur=0;
var floatY=(!frag&&motionOK())?Math.sin(time*1.05)*2.5:0;
if(frag&&acq<0.55){/* sliced fragments before resolve */
  var slices=4;var sh=dh/slices;for(var si=0;si<slices;si++){var ox=(Math.random()-0.5)*14*(1-acq);ctx.drawImage(entry.img,0,si*(ih/slices),iw,ih/slices,x-dw/2+ox+jx,y-dh/2+floatY+si*sh+jy,dw,sh);}}
else{ctx.drawImage(entry.img,x-dw/2+jx,y-dh/2+floatY+jy,dw,dh);}
/* holographic scanline */
if(motionOK()&&acq!=null&&acq>0.4){var sy=y-half+((time*24)%(box));ctx.fillStyle=hexA(activeTheme.primary,0.11);ctx.fillRect(x-half,sy,box,2);}
/* light sweep after clean resolve */
if(acq!=null&&acq>0.85){var sw=(time*0.38)%1.6-0.3;if(sw>0&&sw<1){var gx=x-half+box*sw;var grd=ctx.createLinearGradient(gx-18,0,gx+18,0);grd.addColorStop(0,'rgba(255,255,255,0)');grd.addColorStop(0.5,'rgba(255,255,255,0.30)');grd.addColorStop(1,'rgba(255,255,255,0)');ctx.fillStyle=grd;ctx.fillRect(x-half,y-half,box,box);}}
ctx.restore();return true;};
var giftRenderer=new GiftRenderer();
var coinPulsed=false;

/* ---------- event visuals ---------- */
var activeEvent=null,eventStart=0,lastSeq=0,playedDetect=false,playedPeak=false,playedCharge=false,lastTick=0,peakBurstT=-1,dischargeFlash=0;
function checkTransition(now){if(state.event_seq!==lastSeq){lastSeq=state.event_seq;if(state.current_event){activeEvent={};for(var k in state.current_event)activeEvent[k]=state.current_event[k];eventStart=now;playedDetect=false;playedPeak=false;playedCharge=false;triggerGlitch(0.85);audio.activation();if(state.config.particles_enabled)particles.burst(Layout.centerX,Layout.stageY,22,4,activeTheme.primary);}else activeEvent=null;}}
function eventKind(ev){if(!ev)return 'none';return ev.type||'unknown';}

function drawEnergyBurst(info){if(peakBurstT<0)return;var age=(info.nowMs-peakBurstT)/700;if(age>1){peakBurstT=-1;return;}var e=easeOut(clamp(age,0,1));var cx=Layout.centerX,cy=Layout.stageY;ctx.save();ctx.globalAlpha=(1-e)*0.9;ctx.strokeStyle=activeTheme.secondary;ctx.lineWidth=2.5;ctx.shadowColor=activeTheme.glowSecondary;ctx.shadowBlur=18;ctx.beginPath();ctx.arc(cx,cy,Layout.orbitR*(0.35+e*2.4),0,Math.PI*2);ctx.stroke();ctx.globalAlpha=(1-e)*0.5;ctx.strokeStyle=activeTheme.primary;ctx.lineWidth=1.4;ctx.beginPath();ctx.arc(cx,cy,Layout.orbitR*(0.25+e*3.1),0,Math.PI*2);ctx.stroke();ctx.restore();
if(dischargeFlash>0){ctx.save();ctx.globalAlpha=dischargeFlash*0.5;ctx.strokeStyle=activeTheme.primary;ctx.lineWidth=3;var m=Layout.margin;ctx.strokeRect(m,m,VW-2*m,VH-2*m);ctx.restore();}}

function drawDataModule(info){if(!activeEvent)return;var phase=info.phase,pp=info.phaseProgress;if(phase==='detecting')return;var alpha=1;if(phase==='acquiring')alpha=pp;else if(phase==='discharge')alpha=1-pp;else if(phase==='lost')alpha=clamp(1-pp*2,0,1);else if(phase==='return_to_idle')alpha=0;if(alpha<=0.01)return;
var kind=eventKind(activeEvent);var isGift=(kind==='big_gift'||kind==='mega_gift');var gm=eventProcessor.giftModel(activeEvent);
var cx=Layout.centerX;var time=info.time;var inten=info.intensity;
var cp=0;if(phase==='acquiring')cp=pp*0.28;else if(phase==='decoding')cp=0.28+pp*0.52;else cp=1;
/* header — fully inside safe top (no top clip) */
var headY=Layout.headerY;
ctx.save();ctx.globalAlpha=alpha;ctx.textAlign='center';ctx.textBaseline='alphabetic';
var rawTitle=activeEvent.title||tr('goal.detected');
var tp=phase==='decoding'?0.3+pp*0.7:1;
var title=scramble(String(rawTitle).toUpperCase(),clamp(tp,0,1));
var fsHead=Layout.compact?12:14;ctx.font=fontOf(fsHead,800,'Orbitron');
ctx.fillStyle=activeTheme.secondary;ctx.shadowColor=activeTheme.glowSecondary;ctx.shadowBlur=Math.min(8,6);
ctx.fillText('[ '+title+' ]',cx,headY);
ctx.shadowBlur=0;ctx.globalAlpha=alpha*0.55;ctx.strokeStyle=activeTheme.dataRailActive;ctx.lineWidth=1;
var railW=Math.min(VW*0.38,280)*(phase==='decoding'?easeOut(pp):1);ctx.beginPath();ctx.moveTo(cx-railW/2-20,headY+10);ctx.lineTo(cx+railW/2+20,headY+10);ctx.stroke();
ctx.globalAlpha=alpha;
if(isGift){drawGiftComposition(info,gm,cx,cp,alpha,time,inten);}
else if(kind==='activity_surge'){drawSurgeComposition(info,cx,cp,alpha,time,inten);}
else if(kind==='milestone'){drawMilestoneComposition(info,cx,cp,alpha,time,inten);}
else if(kind==='ai_observation'){drawAIComposition(info,cx,cp,alpha,time,inten);}
else{drawUnknownComposition(info,cx,cp,alpha,time,inten);}
ctx.restore();}

function drawGiftComposition(info,gm,cx,cp,alpha,time,inten){
/* Approach A: gift hero at stageY; 3 text rows spaced below orbit (no heap) */
var sockY=Layout.stageY;var box=Layout.giftBox;var phase=info.phase;
var sockProg=clamp(cp/0.14,0,1);
var scanProg=(cp>0.12&&cp<0.32)?clamp((cp-0.12)/0.16,0,1):((cp>=0.32)?1:0);
var iconAcq=clamp((cp-0.28)/0.22,0,1);
var iconProg=clamp((cp-0.26)/0.2,0,1);
giftRenderer.drawSocket(cx,sockY,box,sockProg,time,inten,scanProg<1?scanProg:0);
var entry=null,iconOK=false;
if(gm.hasIcon&&gm.iconUrl&&cp>0.26){entry=giftRenderer.getIcon(gm.iconUrl);if(entry&&entry.loaded&&!entry.broken){iconOK=giftRenderer.drawIcon(entry,cx,sockY,box,iconProg,time,inten,iconAcq);}}
if(!iconOK&&cp>0.12&&cp<0.55){
ctx.save();ctx.globalAlpha=alpha*(0.4+0.25*Math.sin(time*2.2))*(1-iconProg);ctx.strokeStyle=activeTheme.primary;ctx.lineWidth=1.3;var d=9+inten*5;ctx.beginPath();ctx.moveTo(cx,sockY-d);ctx.lineTo(cx+d,sockY);ctx.lineTo(cx,sockY+d);ctx.lineTo(cx-d,sockY);ctx.closePath();ctx.stroke();ctx.restore();}
/* ×N locked to gift — right of socket, vertically centered */
if(state.config.show_gift_quantity!==false&&cp>0.58){var qA=clamp((cp-0.58)/0.1,0,1);var q='×'+gm.quantity;ctx.save();ctx.globalAlpha=alpha*qA;ctx.font=fontOf(Layout.compact?15:18,800,'Orbitron');ctx.fillStyle='#ffffff';ctx.shadowColor=activeTheme.glowStrong;ctx.shadowBlur=8;ctx.textAlign='left';ctx.textBaseline='middle';var qw=ctx.measureText(q).width;var qx=cx+box/2+u(14);ctx.fillText(q,qx,sockY);ctx.strokeStyle=activeTheme.dataRailActive;ctx.lineWidth=1;ctx.shadowBlur=0;ctx.globalAlpha=alpha*0.65*qA;ctx.strokeRect(qx-4,sockY-12,qw+8,24);ctx.restore();}
/* Row 1: gift name — clear of orbitals */
if(state.config.show_gift_name!==false&&gm.giftName&&cp>0.68){var nA=clamp((cp-0.68)/0.1,0,1);ctx.save();ctx.globalAlpha=alpha*0.9*nA;ctx.font=fontOf(Layout.compact?11:13,600,'Share Tech Mono');ctx.fillStyle=activeTheme.subtext;ctx.shadowBlur=0;ctx.textAlign='center';ctx.textBaseline='alphabetic';ctx.fillText(tr('overlay.gift_prefix')+' '+String(gm.giftName).toUpperCase().slice(0,34),cx,Layout.nameY);ctx.restore();}
/* Row 2: username */
if(cp>0.78){var uA=clamp((cp-0.78)/0.1,0,1);var rawU=(gm.sender||tr('goal.anonymous')).toUpperCase();var du=scramble(rawU,uA);var ufs=clamp(Math.min(VW,VH)*0.036,16,28);if(Layout.narrow)ufs=Math.min(ufs,20);ufs=Math.min(ufs,u(28));ctx.save();ctx.globalAlpha=alpha*uA;ctx.font=fontOf(ufs,700,'Rajdhani');ctx.fillStyle=activeTheme.text;ctx.shadowColor=activeTheme.glow;ctx.shadowBlur=8;ctx.textAlign='center';ctx.textBaseline='alphabetic';
if(glitchIntensity>0.15){ctx.fillStyle=activeTheme.primary;ctx.fillText(du,cx-2,Layout.userY);ctx.fillStyle=activeTheme.secondary;ctx.fillText(du,cx+2,Layout.userY);ctx.fillStyle='#ffffff';}
ctx.fillText(du,cx,Layout.userY);ctx.restore();}
/* Row 3: coins */
if(state.config.show_coin_value!==false&&cp>0.88){var cA=clamp((cp-0.88)/0.12,0,1);var targetCoins=gm.coins;var shown=Math.round(targetCoins*easeOut(cA));var cstr=trf('goal.coins_fmt',{n:shown.toLocaleString(locale==='uk'?'uk-UA':'en-US')});ctx.save();ctx.globalAlpha=alpha*cA;ctx.font=fontOf(Layout.compact?14:17,800,'Share Tech Mono');ctx.fillStyle=activeTheme.text;ctx.shadowColor=activeTheme.glowStrong;ctx.shadowBlur=8;ctx.textAlign='center';ctx.textBaseline='alphabetic';ctx.fillText(cstr,cx,Layout.coinY);
var vy=Layout.coinY+u(12);var vw=Math.min(VW*0.32,240)*cA;ctx.globalAlpha=alpha*0.9*cA;ctx.shadowBlur=0;ctx.fillStyle=activeTheme.dataRail;ctx.fillRect(cx-vw/2,vy,vw,2);ctx.fillStyle=activeTheme.primary;ctx.fillRect(cx-vw/2,vy,vw*cA,2);ctx.restore();
if(cA>=1&&!coinPulsed&&state.config.particles_enabled){coinPulsed=true;particles.burst(cx,vy,6,1.6,activeTheme.primary);}if(cA<1)coinPulsed=false;}
/* subtle transfer lines — keep short so they don't crowd text */
if(phase==='active'||phase==='peak'){ctx.save();ctx.globalAlpha=alpha*(phase==='peak'?0.35:0.18)*inten;ctx.strokeStyle=activeTheme.secondary;ctx.lineWidth=1;ctx.shadowBlur=0;var half=box*0.35;for(var i=0;i<4;i++){var a=i*Math.PI/2+Math.PI/4;ctx.beginPath();ctx.moveTo(cx+Math.cos(a)*half,sockY+Math.sin(a)*half);ctx.lineTo(cx+Math.cos(a)*half*0.25,sockY+Math.sin(a)*half*0.25);ctx.stroke();}ctx.restore();}
}

function drawSurgeComposition(info,cx,cp,alpha,time,inten){
var y=Layout.dataY;ctx.save();ctx.globalAlpha=alpha;ctx.textAlign='center';
var pct=clamp(cp*1.4,0,1);var big=Math.round(480*pct);
ctx.font=fontOf(clamp(Math.min(VW,VH)*0.07,30,52),900,'Rajdhani');ctx.fillStyle=activeTheme.text;ctx.shadowColor=activeTheme.glowStrong;ctx.shadowBlur=18;ctx.fillText('+'+big+tr('overlay.per_min'),cx,y);
var bw=Math.min(VW*0.4,300);var n=12;for(var i=0;i<n;i++){var on=i/n<inten*clamp(cp*1.6,0,1);ctx.fillStyle=on?activeTheme.primary:activeTheme.dataRail;ctx.globalAlpha=alpha*(on?0.95:0.5);ctx.fillRect(cx-bw/2+i*(bw/n),y+16,bw/n-3,4+on*8*inten);}
ctx.globalAlpha=alpha*0.8;ctx.font=fontOf(12,600,'Share Tech Mono');ctx.fillStyle=activeTheme.subtext;ctx.fillText(scramble(tr('overlay.signal_intensity')+' '+(Math.round(inten*100))+'%',clamp(cp*1.8,0,1)),cx,y+48);
ctx.restore();}

function drawMilestoneComposition(info,cx,cp,alpha,time,inten){
var y=Layout.dataY;ctx.save();ctx.globalAlpha=alpha;ctx.textAlign='center';
var sub=scramble(String(activeEvent.subtitle||tr('overlay.new_record')).toUpperCase(),clamp(cp*1.6,0,1));
ctx.font=fontOf(clamp(Math.min(VW,VH)*0.055,26,44),900,'Rajdhani');ctx.fillStyle='#ffffff';ctx.shadowColor=activeTheme.glowStrong;ctx.shadowBlur=20;ctx.fillText(sub,cx,y);
var val=scramble(String(activeEvent.value||activeEvent.username||'').toUpperCase(),clamp((cp-0.3)*1.8,0,1));
if(val){ctx.font=fontOf(15,700,'Share Tech Mono');ctx.fillStyle=activeTheme.secondary;ctx.shadowColor=activeTheme.glowSecondary;ctx.shadowBlur=10;ctx.fillText('[ '+val+' ]',cx,y+30);}
ctx.restore();}

function drawAIComposition(info,cx,cp,alpha,time,inten){
var y=Layout.dataY;ctx.save();ctx.globalAlpha=alpha;ctx.textAlign='center';
ctx.font=fontOf(12,600,'Share Tech Mono');ctx.fillStyle=activeTheme.secondary;ctx.shadowBlur=8;ctx.fillText(tr('overlay.neural_scan'),cx,y-34);
var full=(activeEvent.metadata&&activeEvent.metadata.full_text)||activeEvent.subtitle||tr('overlay.pattern_observed');
var msg=scramble(String(full).toUpperCase().slice(0,64),clamp(cp*1.5,0,1));
ctx.font=fontOf(Layout.narrow?15:19,700,'Rajdhani');ctx.fillStyle=activeTheme.text;ctx.shadowColor=activeTheme.glow;ctx.shadowBlur=12;
var words=msg.split(' ');var l1='',l2='';for(var i=0;i<words.length;i++){if((l1+' '+words[i]).trim().length<26&&!l2)l1=(l1+' '+words[i]).trim();else l2=(l2+' '+words[i]).trim();}
ctx.fillText(l1,cx,y);if(l2)ctx.fillText(l2.slice(0,30),cx,y+24);
var conf=scramble(String(activeEvent.value||(tr('overlay.conf')+': --')),clamp((cp-0.4)*1.8,0,1));ctx.font=fontOf(12,600,'Share Tech Mono');ctx.fillStyle=activeTheme.subtext;ctx.fillText(conf,cx,y+(l2?50:34));
ctx.restore();}

function drawUnknownComposition(info,cx,cp,alpha,time,inten){
var y=Layout.dataY;ctx.save();ctx.globalAlpha=alpha;ctx.textAlign='center';
ctx.save();ctx.translate(cx,Layout.stageY);ctx.rotate((motionOK()?time*0.8:0.3));ctx.strokeStyle=activeTheme.accent;ctx.shadowColor=activeTheme.glowAccent;ctx.shadowBlur=10;for(var i=0;i<3;i++){ctx.save();ctx.rotate(i*2.09);ctx.strokeRect(-14,-14,28,28);ctx.restore();}ctx.restore();
var code=scramble(String(activeEvent.value||'0x7F9A::DEEP_SCAN'),clamp(cp*1.6,0,1));
ctx.font=fontOf(16,700,'Share Tech Mono');ctx.fillStyle=activeTheme.accent;ctx.shadowColor=activeTheme.glowAccent;ctx.shadowBlur=12;ctx.fillText(code,cx,y);
var rs=scramble(String(activeEvent.subtitle||tr('goal.anomaly_sub')).toUpperCase(),clamp((cp-0.3)*1.6,0,1));
ctx.font=fontOf(12,600,'Share Tech Mono');ctx.fillStyle=activeTheme.subtext;ctx.shadowBlur=6;ctx.fillText(rs,cx,y+24);
ctx.restore();}

function drawSignalLost(info){if(info.phase!=='lost')return;ctx.save();ctx.globalAlpha=clamp(info.phaseProgress*2,0,1)*clamp((1-info.phaseProgress)*2,0,1);ctx.textAlign='center';ctx.font=fontOf(13,800,'Orbitron');ctx.fillStyle=activeTheme.accent;ctx.shadowColor=activeTheme.glowAccent;ctx.shadowBlur=12;ctx.fillText(tr('overlay.signal_lost'),Layout.centerX,Layout.stageY+Layout.orbitR+22);ctx.restore();}

/* ---------- main loop (idle FPS throttle + no getImageData) ---------- */
var lastT=performance.now(),animTime=0,lastIdleDraw=0;
var IDLE_FRAME_MS=1000/15; /* ~15fps while idle — OBS GPU win */
function render(now){requestAnimationFrame(render);var dt=Math.min(0.1,(now-lastT)/1000);lastT=now;var mScale=motionOK()?1:0.25;animTime+=dt*mScale;
checkTransition(now);
var phase='idle',phaseProgress=0,intensity=0.45,t01=0;
if(activeEvent){var elapsed=now-eventStart;var dur=activeEvent.duration_ms||5000;var sm=stateMachine.phaseFor(elapsed,dur);phase=sm.phase;phaseProgress=clamp(sm.progress,0,1);t01=sm.t;intensity=clamp(activeEvent.intensity||0.7,0,1);
try{var im=parseFloat(state.config.intensity_multiplier)||1;intensity=clamp(intensity*im,0,1);}catch(e){}
if(sm.t>=1){activeEvent=null;phase='idle';}
else{
if(phase==='decoding'&&!playedCharge){playedCharge=true;audio.charge(intensity);}
if((phase==='active'||phase==='peak')&&!playedPeak){playedPeak=true;audio.peak(intensity);triggerGlitch(0.4+0.4*intensity);if(state.config.particles_enabled)particles.burst(Layout.centerX,Layout.stageY,Math.round(16+24*intensity),5,activeTheme.secondary);peakBurstT=now;dischargeFlash=1;}
if(phase==='decoding'&&motionOK()&&now-lastTick>90){lastTick=now;audio.tick();}
if(phase==='peak'&&motionOK()&&Math.random()<dt*2.2)triggerGlitch(0.35);
}}
if(dischargeFlash>0)dischargeFlash=Math.max(0,dischargeFlash-dt*1.4);
/* glitch decay */
if(glitchIntensity>0.01){glitchIntensity*=Math.pow(0.04,dt);glitchOX=(Math.random()-0.5)*18*glitchIntensity;glitchOY=(Math.random()-0.5)*9*glitchIntensity;}else{glitchIntensity=0;glitchOX=0;glitchOY=0;}
var busy=(phase!=='idle')||(particles.activeCount>0)||(glitchIntensity>0.05)||(peakBurstT>=0)||(dischargeFlash>0.02);
if(!busy){
  if((now-lastIdleDraw)<IDLE_FRAME_MS)return;
  lastIdleDraw=now;
}
var info={phase:phase,phaseProgress:phaseProgress,intensity:intensity,time:animTime,nowMs:now};
frameRenderer.update(dt,phase!=='idle');
ctx.clearRect(0,0,VW,VH);
/* L1 background particles — active signals only */
particles.ambient(dt,phase!=='idle');
/* L2 perimeter frame */
frameRenderer.draw(info);
/* L3 particles */
particles.updateDraw(dt);
/* L4 orbital/well — only during an active signal, never as idle decoration */
if(activeEvent&&phase!=='idle')coreRenderer.draw(info);
/* L5 gift hero + data above well; peak energy story */
drawEnergyBurst(info);
if(activeEvent){drawDataModule(info);drawSignalLost(info);}
/* L6 cheap glitch streaks (never getImageData — GPU sync killer in OBS) */
if(glitchIntensity>0.12&&motionOK()){ctx.save();ctx.shadowBlur=0;for(var g=0;g<2;g++){var gy=Math.random()*VH;var gh=2+Math.random()*5;var go=(Math.random()-0.5)*28*glitchIntensity;ctx.globalAlpha=0.14*glitchIntensity;ctx.fillStyle=activeTheme.primary;ctx.fillRect(go,gy,VW,gh);}ctx.restore();}
}

/* ---------- websocket ---------- */
function handleMsg(data){if(!data||!data.op)return;if(data.op==='initial_state'){var st=data.state||{};if(st.locale)locale=st.locale;if(st.config){for(var k in st.config)state.config[k]=st.config[k];updateTheme();applyScale(state.config.scale_percent);Layout.measure();}if(st.current_event!==undefined)state.current_event=st.current_event;if(st.event_seq!==undefined)state.event_seq=st.event_seq;if(st.idle_metrics!==undefined)state.idle_metrics=st.idle_metrics;return;}if(data.op==='patch'){var p=data.patch||{};if(p.locale)locale=p.locale;if(p.config){for(var k2 in p.config)state.config[k2]=p.config[k2];updateTheme();if(p.config.scale_percent!==undefined)applyScale(p.config.scale_percent);else Layout.measure();}if(p.current_event!==undefined)state.current_event=p.current_event;if(p.event_seq!==undefined)state.event_seq=p.event_seq;if(p.idle_metrics!==undefined)state.idle_metrics=p.idle_metrics;}}
function connect(){tries++;var backoff=Math.min(5000,250+Math.floor(Math.random()*250)+tries*350);try{ws=new WebSocket(wsUrl);}catch(e){setTimeout(connect,backoff);return;}ws.onopen=function(){tries=0;try{ws.send(JSON.stringify(__SUBSCRIBE_JSON__));}catch(e){}};ws.onmessage=function(ev){try{handleMsg(JSON.parse(ev.data));}catch(e){}};ws.onclose=function(){setTimeout(connect,backoff);};ws.onerror=function(){};}
window.addEventListener('message',function(ev){try{var d=ev.data;if(d&&d.op==='patch')handleMsg(d);}catch(e){}});
updateTheme();applyScale(__INITIAL_SCALE__);
connect();requestAnimationFrame(render);
})();
</script>
</body>
</html>"""
