"""
dashboard.py — Trading Intelligence Dashboard
pip install streamlit plotly pandas yfinance requests
streamlit run dashboard.py
"""

import streamlit as st
import json, os, requests
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf

st.set_page_config(
    page_title="Trading Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300&family=Inter:wght@300;400;500&display=swap');

:root {
    --bg:        #0d0d0d;
    --surface:   #141414;
    --surface2:  #1a1a1a;
    --surface3:  #222222;
    --border:    #2a2a2a;
    --border2:   #333333;
    --text:      #f0ede8;
    --muted:     #666666;
    --muted2:    #444444;
    --accent:    #c8b89a;
    --accent2:   #a89070;
    --green:     #4ade80;
    --green2:    #166534;
    --red:       #f87171;
    --red2:      #7f1d1d;
    --gold:      #fbbf24;
    --blue:      #60a5fa;
}

html, body, [class*="css"] { 
    background: var(--bg) !important; 
    color: var(--text) !important;
    font-family: 'Inter', sans-serif !important;
}

.main, .block-container { 
    background: var(--bg) !important;
    padding: 1.2rem 2rem !important;
    max-width: 1600px !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
    width: 240px !important;
}
section[data-testid="stSidebar"] * { color: var(--text) !important; }
section[data-testid="stSidebar"] .stRadio label {
    font-family: 'Inter', sans-serif !important;
    font-size: 12px !important;
    font-weight: 400 !important;
    color: var(--muted) !important;
    background: transparent !important;
    border-radius: 6px !important;
    padding: 7px 12px !important;
    margin: 1px 0 !important;
    display: block !important;
    letter-spacing: 0.3px !important;
    transition: all 0.15s !important;
    border: 1px solid transparent !important;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    color: var(--text) !important;
    background: var(--surface2) !important;
    border-color: var(--border) !important;
}
section[data-testid="stSidebar"] .stRadio [aria-checked="true"] label {
    color: var(--accent) !important;
    background: var(--surface2) !important;
    border-color: var(--border2) !important;
}

/* Metrikler */
div[data-testid="stMetric"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
}
div[data-testid="stMetric"] label {
    color: var(--muted) !important;
    font-size: 9px !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 1.2px !important;
    font-family: 'Inter', sans-serif !important;
}
div[data-testid="stMetric"] [data-testid="metric-container"] > div:nth-child(2) {
    font-family: 'DM Mono', monospace !important;
    font-size: 17px !important;
    color: var(--text) !important;
    font-weight: 400 !important;
}
div[data-testid="stMetric"] [data-testid="metric-container"] > div:nth-child(3) {
    font-family: 'DM Mono', monospace !important;
    font-size: 11px !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid var(--border) !important;
    gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    color: var(--muted) !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
    padding: 8px 16px !important;
    margin-right: 4px !important;
    font-family: 'Inter', sans-serif !important;
}
.stTabs [aria-selected="true"] {
    background: transparent !important;
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
}

/* Selectbox */
.stSelectbox > div > div {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    color: var(--text) !important;
    font-size: 12px !important;
}

/* Button */
.stButton button {
    background: var(--surface2) !important;
    border: 1px solid var(--border2) !important;
    color: var(--accent) !important;
    border-radius: 6px !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    letter-spacing: 0.5px !important;
    font-family: 'Inter', sans-serif !important;
    padding: 6px 14px !important;
    transition: all 0.15s !important;
}
.stButton button:hover {
    background: var(--surface3) !important;
    border-color: var(--accent2) !important;
}

/* Dataframe */
.stDataFrame { 
    border: 1px solid var(--border) !important; 
    border-radius: 8px !important;
    overflow: hidden !important;
}

/* Info/Success */
.stAlert {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    color: var(--muted) !important;
    font-size: 12px !important;
}

hr { border-color: var(--border) !important; margin: 12px 0 !important; opacity: 0.5 !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }
</style>
""", unsafe_allow_html=True)

# ── SABİTLER ──────────────────────────────────────────
SIM    = "sim.json"
POS_TL = 10_000

KATLAR = {
    "bist_trade": {"isim": "BIST Teknik",  "emoji": "◈", "renk": "#60a5fa", "tag": "EQ"},
    "bist_temel": {"isim": "BIST Temel",   "emoji": "◆", "renk": "#a78bfa", "tag": "FA"},
    "kripto":     {"isim": "Kripto",        "emoji": "◉", "renk": "#fbbf24", "tag": "CR"},
    "metal":      {"isim": "Emtia",         "emoji": "◎", "renk": "#34d399", "tag": "CM"},
}

# ── YARDIMCI ──────────────────────────────────────────
def yukle():
    if not os.path.exists(SIM): return {}
    with open(SIM, "r", encoding="utf-8") as f:
        return json.load(f)

def ist(acik, kapali):
    kaz = [p for p in kapali if p.get("kz_tl",0)>0]
    kay = [p for p in kapali if p.get("kz_tl",0)<=0]
    return {
        "acik":len(acik),"kapali":len(kapali),
        "kazanan":len(kaz),"kaybeden":len(kay),
        "basari":len(kaz)/len(kapali)*100 if kapali else 0,
        "acik_kz":sum(p.get("kz_tl",0) for p in acik),
        "kap_kz": sum(p.get("kz_tl",0) for p in kapali),
        "top_kz": sum(p.get("kz_tl",0) for p in acik+kapali),
        "ort_kaz":sum(p.get("kz_tl",0) for p in kaz)/len(kaz) if kaz else 0,
        "ort_kay":sum(p.get("kz_tl",0) for p in kay)/len(kay) if kay else 0,
    }

def gun(ts):
    try: return (datetime.now()-datetime.strptime(ts,"%d.%m.%Y %H:%M")).days
    except: return 0

def tl(v, sign=True):
    if v is None: return "—"
    if sign: return f"+{v:,.0f}₺" if v>=0 else f"{v:,.0f}₺"
    return f"{v:,.0f}₺"

def pct(v):
    if v is None: return "—"
    return f"+{v*100:.2f}%" if v>=0 else f"{v*100:.2f}%"

def rk(v): return "#4ade80" if v>=0 else "#f87171"

def plt_cfg(fig, h=200, legend=False):
    fig.update_layout(
        paper_bgcolor="#141414", plot_bgcolor="#141414",
        font=dict(color="#666666", family="DM Mono", size=10),
        yaxis=dict(showgrid=True, gridcolor="#1e1e1e", zeroline=True,
                   zerolinecolor="#2a2a2a", tickfont=dict(size=9), showline=False),
        xaxis=dict(showgrid=False, tickfont=dict(size=9), showline=False),
        margin=dict(t=8,b=8,l=8,r=8), height=h,
        showlegend=legend,
        legend=dict(font=dict(size=9), bgcolor="rgba(0,0,0,0)") if legend else None,
    )
    return fig

# ── FİYAT GÜNCELLEME ──────────────────────────────────
def fiyat_cek(ticker):
    try:
        if "USDT" in ticker:
            r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={ticker}", timeout=5)
            return float(r.json()["price"])
        elif ticker in ["ALTIN","GUMUS","PLATIN","PALADYUM"]:
            mp = {"ALTIN":"GC=F","GUMUS":"SI=F","PLATIN":"PL=F","PALADYUM":"PA=F"}
            kd = yf.download("USDTRY=X",period="2d",progress=False,auto_adjust=True)
            kur = float(kd["Close"].iloc[-1])
            d   = yf.download(mp[ticker],period="2d",progress=False,auto_adjust=True)
            return float(d["Close"].iloc[-1])/31.1035*kur
        else:
            d = yf.download(ticker+".IS",period="2d",progress=False,auto_adjust=True)
            if d.empty: return None
            v = d["Close"].iloc[-1]
            return float(v.iloc[0]) if hasattr(v,"iloc") else float(v)
    except: return None

def sim_guncelle():
    if not os.path.exists(SIM): return
    with open(SIM,"r",encoding="utf-8") as f: sim=json.load(f)
    for kat in KATLAR:
        for p in sim.get(kat,{}).get("acik",[]):
            cp = fiyat_cek(p["ticker"])
            if cp is None: continue
            p["guncel"] = round(cp,6)
            yon = p.get("yon","LONG")
            p["kz_pct"] = (cp-p["giris"])/p["giris"] if yon=="LONG" else (p["giris"]-cp)/p["giris"]
            p["kz_tl"]  = round(p["kz_pct"]*POS_TL,2)
            tp1=p.get("tp1"); tp2=p.get("tp2")
            if tp1 and not p.get("tp1_gecildi"):
                if (yon=="LONG" and cp>=tp1) or (yon=="SHORT" and cp<=tp1): p["tp1_gecildi"]=True
            if tp2 and not p.get("tp2_gecildi"):
                if (yon=="LONG" and cp>=tp2) or (yon=="SHORT" and cp<=tp2): p["tp2_gecildi"]=True
    with open(SIM,"w",encoding="utf-8") as f: json.dump(sim,f,ensure_ascii=False,indent=2)

# ── PROGRESS BAR ──────────────────────────────────────
def seviye_bar(p, kat_renk="#60a5fa"):
    giris = p.get("giris",0)
    gunc  = p.get("guncel",giris)
    stop  = p.get("stop")
    tp1   = p.get("tp1"); tp2=p.get("tp2"); tp3=p.get("tp3")
    yon   = p.get("yon","LONG")
    kz    = p.get("kz_tl",0)
    tp1ok = p.get("tp1_gecildi",False)
    tp2ok = p.get("tp2_gecildi",False)
    if not giris: return ""

    sol = stop if stop else giris*(0.88 if yon=="LONG" else 1.12)
    sag = tp3  if tp3  else giris*(1.15 if yon=="LONG" else 0.85)
    if sag == sol: return ""
    ar = abs(sag-sol)

    def pos(v): return max(0,min(100,abs(v-sol)/ar*100))

    gp = pos(gunc)
    gp_r = pos(giris)
    dr = "#4ade80" if kz>=0 else "#f87171"

    tps = []
    for tv,lb,ok in [(tp1,"TP1",tp1ok),(tp2,"TP2",tp2ok),(tp3,"TP3",False)]:
        if tv:
            pp = pos(tv)
            c = "#4ade80" if ok else "#333333"
            tc = "#4ade80" if ok else "#444444"
            tps.append(f'''
            <div style="position:absolute;left:{pp:.1f}%;top:0;width:1px;height:12px;background:{c};transform:translateX(-50%)"></div>
            <div style="position:absolute;left:{pp:.1f}%;top:14px;font-size:8px;color:{tc};transform:translateX(-50%);font-family:DM Mono;white-space:nowrap;letter-spacing:0.5px">{"✓" if ok else ""}{lb}</div>
            ''')

    stop_html = ""
    if stop:
        stop_html = '''<div style="position:absolute;left:0;top:0;width:1px;height:12px;background:#f87171"></div>
        <div style="position:absolute;left:0;top:14px;font-size:8px;color:#f87171;font-family:DM Mono;letter-spacing:0.5px">STP</div>'''

    giris_html = f'<div style="position:absolute;left:{gp_r:.1f}%;top:-1px;width:1px;height:14px;background:#333333;transform:translateX(-50%)"></div>'

    fill_pct = abs(gp - gp_r)
    fill_left = min(gp, gp_r)

    return f"""
    <div style="margin:8px 0 26px;position:relative">
        <div style="display:flex;justify-content:space-between;margin-bottom:5px;font-family:DM Mono;font-size:9px;color:#444444;letter-spacing:0.5px">
            <span style="color:#666666">{f"{stop:.4f}" if stop else "—"}</span>
            <span style="color:{dr};font-weight:500">{gunc:.4f}</span>
            <span style="color:#666666">{f"{tp3:.4f}" if tp3 else "—"}</span>
        </div>
        <div style="position:relative;height:12px;background:#1a1a1a;border-radius:2px;overflow:visible">
            <div style="position:absolute;left:{fill_left:.1f}%;height:100%;width:{fill_pct:.1f}%;background:{dr};opacity:0.25;border-radius:2px"></div>
            {stop_html}
            {"".join(tps)}
            {giris_html}
            <div style="position:absolute;left:{gp:.1f}%;top:50%;transform:translate(-50%,-50%);width:8px;height:8px;background:{dr};border-radius:50%;border:1.5px solid #0d0d0d;box-shadow:0 0 6px {dr}40"></div>
        </div>
    </div>
    """

# ── POZİSYON KARTI ────────────────────────────────────
def poz_kart(p, kat_renk="#60a5fa", tag="EQ"):
    kz   = p.get("kz_tl",0)
    kzp  = p.get("kz_pct",0)
    yon  = p.get("yon","LONG")
    puan = p.get("puan")
    g    = gun(p.get("giris_tarih",p.get("tarih","")))
    gunc = p.get("guncel",p.get("giris",0))
    giris = p.get("giris",0)
    tp1ok = p.get("tp1_gecildi",False)
    tp2ok = p.get("tp2_gecildi",False)
    r = rk(kz)

    yon_sym = "▲" if yon=="LONG" else "▼"
    yon_c   = "#4ade80" if yon=="LONG" else "#f87171"

    bar = seviye_bar(p, kat_renk)

    html = f"""
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;
                padding:14px 16px;margin-bottom:8px;position:relative;
                border-left:2px solid {kat_renk}">

        <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div style="display:flex;align-items:center;gap:10px">
                <span style="font-family:Syne,sans-serif;font-size:15px;font-weight:700;
                             color:var(--text);letter-spacing:0.5px">{p['ticker']}</span>
                <span style="font-size:8px;font-weight:600;letter-spacing:1px;color:{kat_renk};
                             background:{kat_renk}18;border:1px solid {kat_renk}30;
                             padding:2px 6px;border-radius:3px">{tag}</span>
                <span style="font-size:9px;color:{yon_c};font-weight:500">{yon_sym} {yon}</span>
                {"<span style='font-size:9px;color:#666666;font-family:DM Mono'>"+str(puan)+"/100</span>" if puan else ""}
                <span style="font-size:9px;color:var(--muted2);font-family:DM Mono">{g}g</span>
            </div>
            <div style="text-align:right">
                <div style="font-family:DM Mono;font-size:16px;color:{r};font-weight:400">{tl(kz)}</div>
                <div style="font-size:10px;color:{r};font-family:DM Mono">{pct(kzp)}</div>
            </div>
        </div>

        <div style="margin-top:6px;display:flex;gap:16px;font-family:DM Mono;font-size:9px;color:#444444;letter-spacing:0.5px">
            <span>GİRİŞ <span style="color:#666666">{giris:.4f}</span></span>
            <span>ŞİMDİ <span style="color:{r}">{gunc:.4f}</span></span>
            {"<span>STOP <span style='color:#f87171'>"+str(round(p['stop'],4))+"</span></span>" if p.get('stop') else ""}
            <span>
                {"<span style='color:#4ade80'>TP1✓</span>" if tp1ok else "<span style='color:#333333'>TP1</span>"}
                {"<span style='color:#4ade80'> TP2✓</span>" if tp2ok else "<span style='color:#333333'> TP2</span>"}
                <span style="color:#333333"> TP3</span>
            </span>
        </div>

        {bar}

        {"<div style='font-size:9px;color:#333333;font-family:DM Mono;margin-top:-16px'>"+p['notlar']+"</div>" if p.get('notlar') else ""}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def kapali_kart(p, kat_renk="#60a5fa", tag="EQ"):
    kz   = p.get("kz_tl",0)
    kzp  = p.get("kz_pct",0)
    neden = {"stop":"STP","tp3":"TP3","trailing_stop":"TSL"}.get(
             p.get("durum",p.get("cikis_neden","")), "CLS")
    puan = p.get("puan")
    g    = gun(p.get("giris_tarih",p.get("tarih","")))
    r    = rk(kz)

    html = f"""
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;
                padding:11px 16px;margin-bottom:6px;opacity:0.75">
        <div style="display:flex;justify-content:space-between;align-items:center">
            <div style="display:flex;align-items:center;gap:8px">
                <span style="font-family:Syne,sans-serif;font-size:13px;font-weight:700;color:var(--text)">{p['ticker']}</span>
                <span style="font-size:8px;font-weight:600;letter-spacing:1px;color:#444444;
                             background:#1a1a1a;border:1px solid #2a2a2a;padding:1px 5px;border-radius:2px">{neden}</span>
                {"<span style='font-size:9px;color:#444444;font-family:DM Mono'>"+str(puan)+"/100</span>" if puan else ""}
                <span style="font-size:9px;color:#333333;font-family:DM Mono">{g}g</span>
            </div>
            <div style="text-align:right">
                <span style="font-family:DM Mono;font-size:14px;color:{r}">{tl(kz)}</span>
                <span style="font-size:9px;color:{r};font-family:DM Mono;margin-left:8px">{pct(kzp)}</span>
            </div>
        </div>
        <div style="margin-top:4px;font-size:9px;color:#333333;font-family:DM Mono">
            {p.get('giris_tarih','—')} → {p.get('cikis_tarih','—')}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:8px 0 20px">
        <div style="font-family:Syne,sans-serif;font-size:18px;font-weight:800;
                    color:#f0ede8;letter-spacing:-0.5px">TRADING</div>
        <div style="font-family:DM Mono,monospace;font-size:9px;color:#444444;
                    letter-spacing:2px;margin-top:2px">INTELLIGENCE</div>
    </div>
    """, unsafe_allow_html=True)

    veri = yukle()
    top_kz   = sum(sum(p.get("kz_tl",0) for p in veri.get(k,{}).get("acik",[])+veri.get(k,{}).get("kapali",[])) for k in KATLAR)
    top_acik = sum(len(veri.get(k,{}).get("acik",[])) for k in KATLAR)
    top_kap  = sum(len(veri.get(k,{}).get("kapali",[])) for k in KATLAR)
    r = "#4ade80" if top_kz>=0 else "#f87171"

    st.markdown(f"""
    <div style="background:#111111;border:1px solid #1e1e1e;border-radius:8px;
                padding:14px;margin-bottom:20px">
        <div style="font-size:8px;letter-spacing:1.5px;text-transform:uppercase;
                    color:#444444;margin-bottom:6px;font-family:Inter">Toplam P&L</div>
        <div style="font-family:DM Mono;font-size:22px;font-weight:400;color:{r}">{tl(top_kz)}</div>
        <div style="margin-top:8px;display:flex;gap:12px">
            <span style="font-size:9px;color:#333333;font-family:DM Mono">{top_acik} AÇIK</span>
            <span style="font-size:9px;color:#333333;font-family:DM Mono">{top_kap} KAPANDI</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Nav
    st.markdown('<div style="font-size:8px;letter-spacing:1.5px;color:#333333;margin-bottom:8px;font-family:Inter">NAVIGATION</div>', unsafe_allow_html=True)
    secim = st.radio("", [
        "Overview", "Performance",
        "◈ BIST Teknik", "◆ BIST Temel", "◉ Kripto", "◎ Emtia"
    ], label_visibility="collapsed")

    st.markdown('<div style="font-size:8px;letter-spacing:1.5px;color:#333333;margin:16px 0 8px;font-family:Inter">ACTIONS</div>', unsafe_allow_html=True)
    if st.button("↻  Fiyat Güncelle", use_container_width=True):
        with st.spinner(""):
            sim_guncelle()
        st.rerun()

    st.markdown(f"""
    <div style="margin-top:20px;padding-top:16px;border-top:1px solid #1e1e1e">
        <div style="font-family:DM Mono;font-size:8px;color:#2a2a2a;letter-spacing:0.5px">
            {datetime.now().strftime('%d.%m.%Y %H:%M')}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── OVERVIEW ──────────────────────────────────────────
def overview(veri):
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:24px;font-weight:800;letter-spacing:-0.5px;margin-bottom:4px">Portfolio Overview</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-family:DM Mono;font-size:10px;color:#444444;letter-spacing:1px;margin-bottom:20px">{datetime.now().strftime("%A, %d %B %Y").upper()}</div>', unsafe_allow_html=True)

    tum_a,tum_k = [],[]
    for k in KATLAR:
        tum_a += veri.get(k,{}).get("acik",[])
        tum_k += veri.get(k,{}).get("kapali",[])
    s   = ist(tum_a,tum_k)
    yat = (s["acik"]+s["kapali"])*POS_TL
    gun_but = yat+s["top_kz"]
    getiri_pct = s["top_kz"]/yat if yat else 0

    # Üst metrikler
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("P&L",          tl(s["top_kz"]))
    c2.metric("Getiri",       pct(getiri_pct))
    c3.metric("Bütçe",        tl(gun_but, False))
    c4.metric("Başarı",       f"%{s['basari']:.0f}")
    c5.metric("Açık",         f"{s['acik']} pozisyon")
    c6.metric("Kapanan",      f"{s['kapali']} işlem")

    st.markdown("<br>", unsafe_allow_html=True)

    # Strateji kartları
    cols = st.columns(4)
    for i,(k,b) in enumerate(KATLAR.items()):
        a  = veri.get(k,{}).get("acik",[])
        ka = veri.get(k,{}).get("kapali",[])
        s2 = ist(a,ka)
        r  = rk(s2["top_kz"])
        with cols[i]:
            basari_w = s2["basari"]
            st.markdown(f"""
            <div style="background:#111111;border:1px solid #1e1e1e;border-radius:10px;
                        padding:16px;position:relative;overflow:hidden">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
                    <div>
                        <div style="font-size:8px;letter-spacing:1.5px;color:{b['renk']};
                                    text-transform:uppercase;font-weight:600;font-family:Inter">{b['tag']}</div>
                        <div style="font-family:Syne,sans-serif;font-size:14px;font-weight:700;
                                    color:#f0ede8;margin-top:2px">{b['isim']}</div>
                    </div>
                    <div style="font-size:20px;opacity:0.3;color:{b['renk']}">{b['emoji']}</div>
                </div>
                <div style="font-family:DM Mono;font-size:20px;color:{r};margin-bottom:10px">{tl(s2['top_kz'])}</div>
                <div style="background:#1a1a1a;border-radius:2px;height:2px;margin-bottom:8px;overflow:hidden">
                    <div style="height:100%;width:{basari_w:.0f}%;background:{b['renk']};opacity:0.6"></div>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:9px;font-family:DM Mono">
                    <span style="color:#444444">%{s2['basari']:.0f} başarı</span>
                    <span style="color:#333333">{s2['acik']} açık</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Grafikler
    st.markdown("<br>", unsafe_allow_html=True)
    g1,g2,g3 = st.columns([2,2,1])

    with g1:
        st.markdown('<div style="font-size:9px;letter-spacing:1px;color:#444444;margin-bottom:8px;font-family:Inter">P&L DAĞILIMI</div>', unsafe_allow_html=True)
        isimler = [b["isim"] for b in KATLAR.values()]
        kzlar   = [ist(veri.get(k,{}).get("acik",[]),veri.get(k,{}).get("kapali",[])).get("top_kz",0) for k in KATLAR]
        renkler = [rk(v) for v in kzlar]
        fig = go.Figure(go.Bar(
            x=isimler, y=kzlar,
            marker=dict(color=renkler, opacity=0.7, line=dict(width=0)),
            text=[tl(k) for k in kzlar], textposition="outside",
            textfont=dict(size=9, family="DM Mono", color="#666666"),
        ))
        st.plotly_chart(plt_cfg(fig, 180), use_container_width=True)

    with g2:
        st.markdown('<div style="font-size:9px;letter-spacing:1px;color:#444444;margin-bottom:8px;font-family:Inter">KAZANAN / KAYBEDEN</div>', unsafe_allow_html=True)
        kaz_l,kay_l,ism_l = [],[],[]
        for k,b in KATLAR.items():
            s3 = ist(veri.get(k,{}).get("acik",[]),veri.get(k,{}).get("kapali",[]))
            if s3["kapali"]>0:
                kaz_l.append(s3["kazanan"]); kay_l.append(s3["kaybeden"]); ism_l.append(b["tag"])
        if kaz_l:
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(name="Win",x=ism_l,y=kaz_l,marker_color="#4ade80",opacity=0.7,marker_line_width=0))
            fig2.add_trace(go.Bar(name="Loss",x=ism_l,y=kay_l,marker_color="#f87171",opacity=0.7,marker_line_width=0))
            fig2.update_layout(barmode="stack")
            st.plotly_chart(plt_cfg(fig2,180,True), use_container_width=True)

    with g3:
        st.markdown('<div style="font-size:9px;letter-spacing:1px;color:#444444;margin-bottom:8px;font-family:Inter">STATS</div>', unsafe_allow_html=True)
        stats = [
            ("Ort. Kazanç", tl(s["ort_kaz"])),
            ("Ort. Kayıp",  tl(s["ort_kay"])),
            ("Açık P&L",    tl(s["acik_kz"])),
            ("Kapanan P&L", tl(s["kap_kz"])),
        ]
        for label, val in stats:
            st.markdown(f"""
            <div style="background:#111111;border:1px solid #1e1e1e;border-radius:6px;
                        padding:10px 12px;margin-bottom:6px">
                <div style="font-size:8px;letter-spacing:1px;color:#333333;font-family:Inter">{label}</div>
                <div style="font-family:DM Mono;font-size:13px;color:#666666;margin-top:2px">{val}</div>
            </div>
            """, unsafe_allow_html=True)

    # Açık pozisyonlar
    if tum_a:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div style="font-size:9px;letter-spacing:1px;color:#444444;margin-bottom:12px;font-family:Inter">AÇIK POZİSYONLAR</div>', unsafe_allow_html=True)
        for k,b in KATLAR.items():
            pozlar = veri.get(k,{}).get("acik",[])
            if pozlar:
                st.markdown(f'<div style="font-size:8px;letter-spacing:1.5px;color:{b["renk"]};margin:12px 0 6px;font-family:Inter">{b["tag"]} — {b["isim"].upper()}</div>', unsafe_allow_html=True)
                for p in pozlar: poz_kart(p, b["renk"], b["tag"])

# ── PERFORMANCE ───────────────────────────────────────
def performance(veri):
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:24px;font-weight:800;letter-spacing:-0.5px;margin-bottom:20px">Performance Analytics</div>', unsafe_allow_html=True)

    tum_a,tum_k = [],[]
    for k in KATLAR:
        for p in veri.get(k,{}).get("acik",[]): tum_a.append({**p,"kat":k})
        for p in veri.get(k,{}).get("kapali",[]): tum_k.append({**p,"kat":k})
    s   = ist(tum_a,tum_k)
    yat = (s["acik"]+s["kapali"])*POS_TL
    gun_but = yat+s["top_kz"]

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Başlangıç",  tl(yat,False))
    c2.metric("Güncel",     tl(gun_but,False), tl(s["top_kz"]))
    c3.metric("Getiri",     pct(s["top_kz"]/yat if yat else 0))
    c4.metric("Başarı",     f"%{s['basari']:.1f}")

    st.markdown("<br>", unsafe_allow_html=True)

    if tum_k:
        g1,g2 = st.columns(2)
        siralı = sorted(tum_k, key=lambda x: x.get("cikis_tarih","") or "")

        with g1:
            st.markdown('<div style="font-size:9px;letter-spacing:1px;color:#444444;margin-bottom:8px;font-family:Inter">BÜTÇE GİDİŞATI</div>', unsafe_allow_html=True)
            tarihler,but_list = [],[]
            toplam = yat
            for p in siralı:
                toplam += p.get("kz_tl",0)
                tarihler.append(p.get("cikis_tarih",""))
                but_list.append(toplam)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=tarihler, y=but_list, mode="lines",
                line=dict(color="#c8b89a",width=1.5),
                fill="tozeroy", fillcolor="rgba(200,184,154,0.05)",
            ))
            fig.add_hline(y=yat, line_dash="dot", line_color="#333333",
                          annotation_text=f"Start {tl(yat,False)}", 
                          annotation_font_size=8, annotation_font_color="#444444")
            st.plotly_chart(plt_cfg(fig,220), use_container_width=True)

        with g2:
            st.markdown('<div style="font-size:9px;letter-spacing:1px;color:#444444;margin-bottom:8px;font-family:Inter">KÜMÜLATİF P&L</div>', unsafe_allow_html=True)
            tarihler2,kum = [],[]
            t = 0
            for p in siralı:
                t += p.get("kz_tl",0)
                tarihler2.append(p.get("cikis_tarih",""))
                kum.append(t)
            son_r = "#4ade80" if (kum[-1] if kum else 0)>=0 else "#f87171"
            fig3 = go.Figure(go.Scatter(
                x=tarihler2, y=kum, mode="lines",
                fill="tozeroy",
                fillcolor=f"{'rgba(74,222,128,0.06)' if son_r=='#4ade80' else 'rgba(248,113,113,0.06)'}",
                line=dict(color=son_r, width=1.5),
            ))
            st.plotly_chart(plt_cfg(fig3,220), use_container_width=True)

    # Puan tablosu
    st.markdown('<div style="font-size:9px;letter-spacing:1px;color:#444444;margin-bottom:8px;font-family:Inter">PUAN BAZLI PERFORMANS</div>', unsafe_allow_html=True)
    gruplar = {"65-69":[],"70-79":[],"80-89":[],"90-99":[],"100":[]}
    for p in tum_a+tum_k:
        puan = p.get("puan",0)
        if   puan>=100: gruplar["100"].append(p)
        elif puan>=90:  gruplar["90-99"].append(p)
        elif puan>=80:  gruplar["80-89"].append(p)
        elif puan>=70:  gruplar["70-79"].append(p)
        else:           gruplar["65-69"].append(p)
    rows = []
    for aralik,pozlar in gruplar.items():
        if not pozlar: continue
        kap = [p for p in pozlar if p.get("durum","acik")!="acik"]
        kaz = [p for p in kap if p.get("kz_tl",0)>0]
        rows.append({
            "Puan": aralik, "İşlem": len(pozlar), "Kapanan": len(kap),
            "Başarı": f"%{len(kaz)/len(kap)*100:.0f}" if kap else "—",
            "Toplam P&L": tl(sum(p.get("kz_tl",0) for p in pozlar)),
            "Ort. P&L": tl(sum(p.get("kz_tl",0) for p in pozlar)/len(pozlar)),
        })
    if rows: st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

# ── KATEGORİ DETAY ────────────────────────────────────
def detay(kat_key, veri):
    b      = KATLAR[kat_key]
    acik   = veri.get(kat_key,{}).get("acik",[])
    kapali = veri.get(kat_key,{}).get("kapali",[])
    s      = ist(acik,kapali)
    yat    = (s["acik"]+s["kapali"])*POS_TL

    st.markdown(f'<div style="font-family:Syne,sans-serif;font-size:24px;font-weight:800;letter-spacing:-0.5px;margin-bottom:4px">{b["isim"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-family:DM Mono;font-size:9px;color:{b["renk"]};letter-spacing:2px;margin-bottom:20px">{b["tag"]} STRATEGY</div>', unsafe_allow_html=True)

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("P&L",         tl(s["top_kz"]))
    c2.metric("Bütçe",       tl(yat,False))
    c3.metric("Başarı",      f"%{s['basari']:.1f}")
    c4.metric("Kazanan",     s["kazanan"])
    c5.metric("Kaybeden",    s["kaybeden"])

    st.markdown("<br>", unsafe_allow_html=True)

    tab1,tab2,tab3 = st.tabs(["Açık Pozisyonlar","Kapananlar","Analiz"])

    with tab1:
        if acik:
            for p in acik: poz_kart(p, b["renk"], b["tag"])
        else:
            st.markdown('<div style="color:#333333;font-size:12px;font-family:DM Mono;padding:20px">Açık pozisyon yok</div>', unsafe_allow_html=True)

    with tab2:
        if kapali:
            filtre = st.selectbox("",["Tümü","Kazananlar","Kaybedenler"],label_visibility="collapsed")
            liste  = kapali
            if filtre=="Kazananlar":  liste=[p for p in kapali if p.get("kz_tl",0)>0]
            if filtre=="Kaybedenler": liste=[p for p in kapali if p.get("kz_tl",0)<=0]
            for p in reversed(liste[-30:]): kapali_kart(p, b["renk"], b["tag"])
        else:
            st.markdown('<div style="color:#333333;font-size:12px;font-family:DM Mono;padding:20px">Kapanan işlem yok</div>', unsafe_allow_html=True)

    with tab3:
        if kapali:
            st.markdown('<div style="font-size:9px;letter-spacing:1px;color:#444444;margin-bottom:8px;font-family:Inter">KÜMÜLATİF P&L</div>', unsafe_allow_html=True)
            siralı = sorted(kapali, key=lambda x: x.get("cikis_tarih","") or "")
            tarihler,kum = [],[]
            t = 0
            for p in siralı:
                t += p.get("kz_tl",0)
                tarihler.append(p.get("cikis_tarih",""))
                kum.append(t)
            r = "#4ade80" if (kum[-1] if kum else 0)>=0 else "#f87171"
            fig = go.Figure(go.Scatter(
                x=tarihler, y=kum, mode="lines+markers",
                line=dict(color=r,width=1.5),
                marker=dict(size=4,color=r),
                fill="tozeroy",
                fillcolor=f"{'rgba(74,222,128,0.06)' if r=='#4ade80' else 'rgba(248,113,113,0.06)'}",
            ))
            st.plotly_chart(plt_cfg(fig,200), use_container_width=True)

        # Puan tablosu
        gruplar = {"65-69":[],"70-79":[],"80-89":[],"90-99":[],"100":[]}
        for p in acik+kapali:
            puan = p.get("puan",0)
            if   puan>=100: gruplar["100"].append(p)
            elif puan>=90:  gruplar["90-99"].append(p)
            elif puan>=80:  gruplar["80-89"].append(p)
            elif puan>=70:  gruplar["70-79"].append(p)
            else:           gruplar["65-69"].append(p)
        rows = []
        for aralik,pozlar in gruplar.items():
            if not pozlar: continue
            kap = [p for p in pozlar if p.get("durum","acik")!="acik"]
            kaz = [p for p in kap if p.get("kz_tl",0)>0]
            rows.append({
                "Puan": aralik,"İşlem": len(pozlar),
                "Başarı": f"%{len(kaz)/len(kap)*100:.0f}" if kap else "—",
                "P&L": tl(sum(p.get("kz_tl",0) for p in pozlar)),
            })
        if rows:
            st.markdown('<div style="font-size:9px;letter-spacing:1px;color:#444444;margin:16px 0 8px;font-family:Inter">PUAN BAZLI</div>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)

# ── ROUTING ───────────────────────────────────────────
veri = yukle()
if   secim == "Overview":       overview(veri)
elif secim == "Performance":    performance(veri)
elif secim == "◈ BIST Teknik":  detay("bist_trade", veri)
elif secim == "◆ BIST Temel":   detay("bist_temel", veri)
elif secim == "◉ Kripto":       detay("kripto", veri)
elif secim == "◎ Emtia":        detay("metal", veri)
