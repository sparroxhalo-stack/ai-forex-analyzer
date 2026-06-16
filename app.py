import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import requests
import hashlib

# ─── APP CONFIGURATION ────────────────────────────────────────────────────────
st.set_page_config(page_title="Sparro FX AI", layout="wide", page_icon="🚀")

st.markdown("""
<style>
body,.main{background:#0d1117;color:#e6edf3}
.block-container{padding-top:1.5rem}
.stTabs [data-baseweb="tab-list"]{gap:4px;background:#161b22;border-radius:12px;padding:5px}
.stTabs [data-baseweb="tab"]{border-radius:8px;padding:7px 14px;color:#8b949e;font-weight:600;font-size:12px}
.stTabs [aria-selected="true"]{background:linear-gradient(90deg,#0072ff,#00c6ff) !important;color:#fff !important}
.stMetric{background:#161b22;border-radius:10px;padding:12px}
.stProgress>div>div{background:linear-gradient(90deg,#00c6ff,#0072ff)}
.login-box{background:#161b22;border-radius:16px;padding:28px;border:1px solid #30363d}
.card{background:#161b22;border-radius:12px;padding:16px;margin-bottom:10px;border:1px solid #30363d}
.tier-box{background:#161b22;border-radius:14px;padding:20px;text-align:center;border:2px solid #30363d}
.tier-box.gold{border-color:#ffd200}
.pulse-dot{display:inline-block;width:9px;height:9px;background:#3fb950;border-radius:50%;margin-right:6px;animation:blink 1.2s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0.2}}
.smc-badge{background:#7c3aed;color:#fff;border-radius:5px;padding:1px 7px;font-size:11px;font-weight:700}
.gold-badge{background:linear-gradient(90deg,#ffd200,#ff8c00);color:#000;border-radius:5px;padding:1px 7px;font-size:11px;font-weight:700}
.btc-badge{background:linear-gradient(90deg,#f7931a,#ff6600);color:#fff;border-radius:5px;padding:1px 7px;font-size:11px;font-weight:700}
.eur-badge{background:linear-gradient(90deg,#003399,#0055cc);color:#fff;border-radius:5px;padding:1px 7px;font-size:11px;font-weight:700}
.specialist-card{border:2px solid #ffd200 !important;box-shadow:0 0 12px rgba(255,210,0,0.2)}
@media(max-width:768px){
  .block-container{padding:0.5rem !important}
  .stTabs [data-baseweb="tab"]{padding:5px 7px !important;font-size:10px !important}
  h1{font-size:20px !important}
}
</style>
""", unsafe_allow_html=True)

# ─── SOUND ALERT ──────────────────────────────────────────────────────────────
def play_sound(sig):
    f1="880" if "BUY" in sig else "440"
    f2="1100" if "BUY" in sig else "330"
    st.markdown(f"""<script>(function(){{try{{
    var c=new(window.AudioContext||window.webkitAudioContext)();
    function b(f,t,d){{var o=c.createOscillator(),g=c.createGain();
    o.connect(g);g.connect(c.destination);o.frequency.value=f;o.type='sine';
    g.gain.setValueAtTime(0.3,t);g.gain.exponentialRampToValueAtTime(0.001,t+d);
    o.start(t);o.stop(t+d)}}
    b({f1},c.currentTime,0.4);b({f2},c.currentTime+0.45,0.35);
    }}catch(e){{}}}})()</script>""",unsafe_allow_html=True)

# ─── PERSISTENT LOGIN ──────────────────────────────────────────────────────────
def _tok(at,em,ts):
    return hashlib.sha256(f"{at}|{em}|{ts}|fx2026".encode()).hexdigest()[:16]

def save_session(at,em,ts=""):
    st.query_params["s"]=f"{at}|{em}|{ts}|{_tok(at,em,ts)}"

def load_session():
    try:
        raw=st.query_params.get("s","")
        if not raw: return None
        at,em,ts,tok=raw.split("|")
        if tok!=_tok(at,em,ts): return None
        return {"account_type":at,"email":em,
                "trial_start":datetime.datetime.fromisoformat(ts) if ts else None}
    except: return None

def clear_session(): st.query_params.clear()

# ─── SESSION STATE ─────────────────────────────────────────────────────────────
DEFS={"logged_in":False,"account_type":None,"trial_start":None,
      "email":"","journal":[],"subscribers":[],"sig_history":[],
      "page":"Dashboard","_loaded":False}
for k,v in DEFS.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state._loaded:
    s=load_session()
    if s: st.session_state.update(logged_in=True,email=s["email"],
                                   account_type=s["account_type"],
                                   trial_start=s["trial_start"])
    st.session_state._loaded=True

def _sec(k,fb):
    try: return st.secrets.get(k,fb)
    except: return fb

ADM_PW  = _sec("ADMIN_PASSWORD","sparro_admin_2026")
PRE_PW  = _sec("PREMIUM_PASSWORD","sparro_pro_2026")
FREE_PW = _sec("FREE_PASSWORD","sparro_free")
AI_KEY  = _sec("ANTHROPIC_API_KEY","")
TRIAL_H = 48

def hours_left():
    if not st.session_state.trial_start: return 0
    return max(0,TRIAL_H-int((datetime.datetime.now()-st.session_state.trial_start).total_seconds()/3600))

def is_pro():
    at=st.session_state.account_type
    if at in ("admin","premium"): return True
    if at=="trial" and hours_left()>0: return True
    return False

# ─── LOGIN ─────────────────────────────────────────────────────────────────────
def login_page():
    st.markdown("""<div style='text-align:center;padding:40px 0 20px'>
    <div style='font-size:60px'>🚀</div>
    <div style='font-size:36px;font-weight:900;background:linear-gradient(90deg,#00c6ff,#0072ff);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent'>Sparro FX AI</div>
    <div style='color:#8b949e;margin-top:6px'>Professional AI-Powered Forex & Commodity Signal Platform</div>
    </div>""",unsafe_allow_html=True)

    st.markdown("""<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:12px;
    max-width:700px;margin:0 auto 24px auto'>
    <div style='background:linear-gradient(135deg,#1a1400,#2a2000);border:2px solid #ffd200;
    border-radius:12px;padding:14px;text-align:center'>
    <div style='font-size:24px'>🥇</div>
    <div style='font-weight:900;color:#ffd200;font-size:15px'>Gold</div>
    <div style='font-size:11px;color:#8b949e;margin-top:4px'>SMC + S/R + EMA200<br>Specialist Analysis</div>
    </div>
    <div style='background:linear-gradient(135deg,#1a0d00,#2a1500);border:2px solid #f7931a;
    border-radius:12px;padding:14px;text-align:center'>
    <div style='font-size:24px'>₿</div>
    <div style='font-weight:900;color:#f7931a;font-size:15px'>Bitcoin</div>
    <div style='font-size:11px;color:#8b949e;margin-top:4px'>FVG + Divergence<br>Specialist Analysis</div>
    </div>
    <div style='background:linear-gradient(135deg,#00001a,#000033);border:2px solid #4488ff;
    border-radius:12px;padding:14px;text-align:center'>
    <div style='font-size:24px'>€</div>
    <div style='font-weight:900;color:#4488ff;font-size:15px'>EUR/USD</div>
    <div style='font-size:11px;color:#8b949e;margin-top:4px'>EMA + ADX + FVG<br>Specialist Analysis</div>
    </div>
    </div>""",unsafe_allow_html=True)

    _,mid,_=st.columns([1,2,1])
    with mid:
        t1,t2,t3=st.tabs(["🔑 Login","🎁 48hr Free Trial","ℹ️ About"])
        with t1:
            st.markdown("<div class='login-box'>",unsafe_allow_html=True)
            st.markdown("#### Welcome back 👋")
            em=st.text_input("Email",key="l_em",placeholder="you@email.com")
            pw=st.text_input("Password",key="l_pw",type="password")
            rem=st.checkbox("Stay logged in",value=True,key="l_rem")
            if st.button("🔓 Login",use_container_width=True,type="primary",key="l_btn"):
                at=("admin" if pw==ADM_PW else "premium" if pw==PRE_PW
                    else "free" if pw==FREE_PW else None)
                if at:
                    st.session_state.update(logged_in=True,account_type=at,email=em)
                    if rem: save_session(at,em)
                    st.rerun()
                else: st.error("❌ Wrong password.")
            st.markdown("</div>",unsafe_allow_html=True)
        with t2:
            st.markdown("<div class='login-box'>",unsafe_allow_html=True)
            st.markdown("""<div style='text-align:center;margin-bottom:14px'>
            <span style='background:linear-gradient(90deg,#ffd200,#ff8c00);color:#000;
            border-radius:20px;padding:5px 16px;font-
