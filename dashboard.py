"""
dashboard.py — Trading Bot Dashboard
Krem/bej tema, kompakt layout, profesyonel

pip install streamlit plotly pandas yfinance requests
streamlit run dashboard.py
"""

import streamlit as st
import json, os, requests
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime
import yfinance as yf

st.set_page_config(
    page_title="Trading Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=DM+Mono:wght@400;500&family=Lato:wght@300;400;700&display=swap');

:root {
    --cream:    #f7f3ee;
    --cream2:   #efe9df;
    --warm:     #e8ddd0;
    --brown:    #8b6f5e;
    --brown2:   #6b4f3f;
    --dark:     #2c1f16;
    --text:     #3d2b1f;
    --muted:    #9a836e;
    --green:    #4a7c5f;
    --red:      #b85450;
    --gold:     #c4962a;
    --border:   #ddd0c0;
}

html, body, [class*="css"], .main, .block-container {
    background: var(--cream) !important;
    color: var(--text) !important;
    font-family: 'Lato', sans-serif !important;
}

.block-container { padding: 1rem 2rem !important; max-width: 1400px !important; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: var(--dark) !important;
    border-right: 1px solid #3d2b1f !important;
}
section[data-testid="stSidebar"] * { color: #e8ddd0 !important; }
section[data-testid="stSidebar"] .stRadio label {
    background: rgba(232,221,208,0.08) !important;
    border-radius: 8px !important;
    padding: 6px 12px !important;
    margin: 2px 0 !important;
    display: block !important;
    font-size: 13px !important;
    transition: background 0.15s !important;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(232,221,208,0.18) !important;
}

/* Metrikler */
div[data-testid="stMetric"] {
    background: white !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
    box-shadow: 0 1px 3px rgba(44,31,22,0.06) !important;
}
div[data-testid="stMetric"] label {
    color: var(--muted) !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
    font-family: 'Lato', sans-serif !important;
}
div[data-testid="stMetric"] [data-testid="metric-container"] > div:nth-child(2) {
    font-family: 'DM Mono', monospace !important;
    font-size: 18px !important;
    color: var(--dark) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: var(--cream2) !important;
    border-radius: 8px !important;
    padding: 3px !important;
    border: 1px solid var(--border) !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 6px !important;
    color: var(--muted) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 6px 14px !important;
}
.stTabs [aria-selected="true"] {
    background: white !important;
    color: var(--dark) !important;
    box-shadow: 0 1px 3px rgba(44,31,22,0.1) !important;
}

/* Butonlar */
.stButton button {
    background: var(--brown) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
}
.stButton button:hover { background: var(--brown2) !important; }

/* Dataframe */
.stDataFrame { border: 1px solid var(--border) !important; border-radius: 8px !important; }

hr { border-color: var(--border) !important; margin: 8px 0 !important; }

h1 { font-family: 'Playfair Display', serif !important; color: var(--dark) !important; font-size: 24px !important; margin-bottom: 4px !important; }
h2 { font-family: 'Playfair Display', serif !important; color: var(--dark) !important; font-size: 20px !important; margin-bottom: 4px !important; }
h3 { font-family: 'Lato', sans-serif !important; color: var(--brown) !important; font-size: 13px !important; font-weight: 700 !important; text-transform: uppercase !important; letter-spacing: 1px !important; margin: 10px 0 4px !important; }
</style>
""", unsafe_allow_html=True)

# ── SABİTLER ──────────────────────────────────────────
SIM   = "sim.json"
POS_TL = 10_000

KATLAR = {
    "bist_trade": {"isim": "BIST Teknik", "emoji": "📈", "renk": "#8b6f5e"},
    "bist_temel": {"isim": "BIST Temel",  "emoji": "📊", "renk": "#4a7c5f"},
    "kripto":     {"isim": "Kripto",       "emoji": "🪙", "renk": "#c4962a"},
    "metal":      {"isim": "Emtia",        "emoji": "🥇", "renk": "#b85450"},
}

# ── YARDIMCI ──────────────────────────────────────────
def yukle():
    if not os.path.exists(SIM): return {}
    with open(SIM, "r", encoding="utf-8") as f:
        return json.load(f)

def ist(acik, kapali):
    kaz = [p for p in kapali if p.get("kz_tl",0) > 0]
    kay = [p for p in kapali if p.get("kz_tl",0) <= 0]
    return {
        "acik": len(acik), "kapali": len(kapali),
        "kazanan": len(kaz), "kaybeden": len(kay),
        "basari": len(kaz)/len(kapali)*100 if kapali else 0,
        "acik_kz":  sum(p.get("kz_tl",0) for p in acik),
        "kap_kz":   sum(p.get("kz_tl",0) for p in kapali),
        "top_kz":   sum(p.get("kz_tl",0) for p in acik+kapali),
        "ort_kaz":  sum(p.get("kz_tl",0) for p in kaz)/len(kaz) if kaz else 0,
        "ort_kay":  sum(p.get("kz_tl",0) for p in kay)/len(kay) if kay else 0,
    }

def gun(ts):
    try: return (datetime.now()-datetime.strptime(ts,"%d.%m.%Y %H:%M")).days
    except: return 0

def tl(v, signed=True):
    if v is None: return "—"
    if signed: return f"+{v:,.0f} ₺" if v>=0 else f"{v:,.0f} ₺"
    return f"{v:,.0f} ₺"

def pct(v):
    if v is None: return "—"
    return f"+{v*100:.2f}%" if v>=0 else f"{v*100:.2f}%"

def rk(v): return "#4a7c5f" if v>=0 else "#b85450"

def fig_layout(fig, h=220):
    fig.update_layout(
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(color="#9a836e", family="Lato", size=11),
        yaxis=dict(showgrid=True, gridcolor="#efe9df", zeroline=True, zerolinecolor="#ddd0c0", tickfont=dict(size=10)),
        xaxis=dict(showgrid=False, tickfont=dict(size=10)),
        margin=dict(t=16,b=8,l=8,r=8), height=h,
        showlegend=False,
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
            return float(d["Close"].iloc[-1]) / 31.1035 * kur
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
            p["kz_tl"]  = round(p["kz_pct"]*POS_TL, 2)
            tp1=p.get("tp1"); tp2=p.get("tp2")
            if tp1 and not p.get("tp1_gecildi"):
                if (yon=="LONG" and cp>=tp1) or (yon=="SHORT" and cp<=tp1): p["tp1_gecildi"]=True
            if tp2 and not p.get("tp2_gecildi"):
                if (yon=="LONG" and cp>=tp2) or (yon=="SHORT" and cp<=tp2): p["tp2_gecildi"]=True
    with open(SIM,"w",encoding="utf-8") as f: json.dump(sim,f,ensure_ascii=False,indent=2)

# ── PROGRESS BAR ──────────────────────────────────────
def progress_bar(p):
    giris = p.get("giris",0)
    gunc  = p.get("guncel",giris)
    stop  = p.get("stop")
    tp1   = p.get("tp1"); tp2=p.get("tp2"); tp3=p.get("tp3")
    yon   = p.get("yon","LONG")
    kz    = p.get("kz_tl",0)
    tp1ok = p.get("tp1_gecildi",False)
    tp2ok = p.get("tp2_gecildi",False)
    if not giris: return

    sol = stop if stop else giris*(0.88 if yon=="LONG" else 1.12)
    sag = tp3  if tp3  else giris*(1.12 if yon=="LONG" else 0.88)
    if sag==sol: return
    aralik = abs(sag-sol)

    def pos(v): return max(0,min(100,abs(v-sol)/aralik*100))

    gp   = pos(gunc)
    gp_r = pos(giris)
    dot_r = "#4a7c5f" if kz>=0 else "#b85450"
    bar_r = "#4a7c5f" if kz>=0 else "#b85450"

    # TP işaretleri
    marks = ""
    for tv,lbl,ok in [(tp1,"T1",tp1ok),(tp2,"T2",tp2ok),(tp3,"T3",False)]:
        if tv:
            pp = pos(tv)
            c  = "#4a7c5f" if ok else "#c4b5a0"
            marks += f'<div style="position:absolute;left:{pp:.1f}%;top:0;width:1.5px;height:10px;background:{c};transform:translateX(-50%)"></div>'
            marks += f'<div style="position:absolute;left:{pp:.1f}%;top:11px;font-size:8px;color:{c};transform:translateX(-50%);font-family:DM Mono;white-space:nowrap">{"✓" if ok else ""}{lbl}</div>'

    if stop:
        marks += f'<div style="position:absolute;left:0;top:0;width:1.5px;height:10px;background:#b85450"></div>'
        marks += f'<div style="position:absolute;left:0;top:11px;font-size:8px;color:#b85450;font-family:DM Mono">STP</div>'

    giris_mark = f'<div style="position:absolute;left:{gp_r:.1f}%;top:-2px;width:1px;height:14px;background:#9a836e;transform:translateX(-50%)"></div>'

    html = f"""
    <div style="margin:6px 0 22px;position:relative;padding-bottom:18px">
        <div style="display:flex;justify-content:space-between;font-size:9px;color:#9a836e;font-family:DM Mono;margin-bottom:4px">
            <span>{f"{stop:.2f}" if stop else "—"}</span>
            <span style="color:{dot_r};font-weight:600">{gunc:.4f}</span>
            <span>{f"{tp3:.2f}" if tp3 else "—"}</span>
        </div>
        <div style="position:relative;height:10px;background:#efe9df;border-radius:999px;overflow:visible">
            <div style="position:absolute;height:100%;width:{gp:.1f}%;background:{bar_r};border-radius:999px;opacity:0.6"></div>
            {marks}
            {giris_mark}
            <div style="position:absolute;left:{gp:.1f}%;top:50%;transform:translate(-50%,-50%);width:10px;height:10px;background:{dot_r};border-radius:50%;border:2px solid white;box-shadow:0 1px 3px rgba(44,31,22,0.2)"></div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# ── POZİSYON KARTI ────────────────────────────────────
def poz_kart(p, renk="#8b6f5e"):
    kz   = p.get("kz_tl",0)
    kzp  = p.get("kz_pct",0)
    yon  = p.get("yon","LONG")
    puan = p.get("puan")
    g    = gun(p.get("giris_tarih",p.get("tarih","")))
    gunc = p.get("guncel",p.get("giris",0))
    giris = p.get("giris",0)

    r = rk(kz)
    yon_em = "▲" if yon=="LONG" else "▼"

    col1, col2 = st.columns([5,1])
    with col1:
        meta = f"**{p['ticker']}**"
        if puan: meta += f"  `{puan}/100`"
        meta += f"  <span style='color:{'#4a7c5f' if yon=='LONG' else '#b85450'};font-size:11px'>{yon_em} {yon}</span>"
        meta += f"  <span style='color:#9a836e;font-size:11px'>{g}g</span>"
        st.markdown(meta, unsafe_allow_html=True)
        st.markdown(
            f"<span style='font-family:DM Mono;font-size:11px;color:#9a836e'>"
            f"Giriş {giris:.4f} → Şimdi {gunc:.4f}"
            + (f"  ·  Stop {p['stop']:.4f}" if p.get("stop") else "")
            + "</span>",
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"<div style='text-align:right;margin-top:2px'>"
            f"<div style='font-family:DM Mono;font-size:15px;font-weight:600;color:{r}'>{tl(kz)}</div>"
            f"<div style='font-size:10px;color:{r}'>{pct(kzp)}</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    progress_bar(p)

def kapali_kart(p):
    kz  = p.get("kz_tl",0)
    kzp = p.get("kz_pct",0)
    neden = {"stop":"🛑","tp3":"🎯","trailing_stop":"🔀"}.get(p.get("durum",p.get("cikis_neden","")), "✅")
    puan  = p.get("puan")
    g     = gun(p.get("giris_tarih",p.get("tarih","")))
    r     = rk(kz)

    col1,col2 = st.columns([5,1])
    with col1:
        meta = f"{neden} **{p['ticker']}**"
        if puan: meta += f"  `{puan}/100`"
        st.markdown(meta, unsafe_allow_html=True)
        st.markdown(
            f"<span style='font-size:10px;color:#9a836e;font-family:DM Mono'>"
            f"{p.get('giris_tarih','—')} → {p.get('cikis_tarih','—')}  ·  {g}g"
            f"</span>", unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"<div style='text-align:right'>"
            f"<div style='font-family:DM Mono;font-size:14px;font-weight:600;color:{r}'>{tl(kz)}</div>"
            f"<div style='font-size:10px;color:{r}'>{pct(kzp)}</div></div>",
            unsafe_allow_html=True
        )
    st.markdown("<hr>", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='font-family:Playfair Display,serif;font-size:20px;font-weight:700;"
        "color:#e8ddd0;margin-bottom:2px'>Trading Bot</div>"
        "<div style='font-size:11px;color:#7a6a5a;margin-bottom:16px'>Portföy Takip</div>",
        unsafe_allow_html=True
    )

    veri = yukle()
    top_kz = sum(
        sum(p.get("kz_tl",0) for p in veri.get(k,{}).get("acik",[])+veri.get(k,{}).get("kapali",[]))
        for k in KATLAR
    )
    top_acik = sum(len(veri.get(k,{}).get("acik",[])) for k in KATLAR)
    top_kap  = sum(len(veri.get(k,{}).get("kapali",[])) for k in KATLAR)

    r = "#4a7c5f" if top_kz>=0 else "#b85450"
    st.markdown(f"""
    <div style='background:rgba(232,221,208,0.1);border:1px solid rgba(232,221,208,0.15);
                border-radius:10px;padding:12px;margin-bottom:14px'>
        <div style='font-size:9px;letter-spacing:1px;text-transform:uppercase;color:#7a6a5a;margin-bottom:4px'>Toplam K/Z</div>
        <div style='font-family:DM Mono;font-size:20px;font-weight:600;color:{r}'>{tl(top_kz)}</div>
        <div style='font-size:10px;color:#5a4a3a;margin-top:4px'>{top_acik} açık · {top_kap} kapandı</div>
    </div>
    """, unsafe_allow_html=True)

    secim = st.radio("",
        ["🏠 Genel", "📈 Performans",
         "📈 BIST Teknik", "📊 BIST Temel", "🪙 Kripto", "🥇 Emtia"],
        label_visibility="collapsed"
    )

    st.markdown("<hr style='border-color:#3d2b1f;margin:10px 0'>", unsafe_allow_html=True)

    if st.button("🔄 Fiyatları Güncelle", use_container_width=True):
        with st.spinner("Çekiliyor..."):
            sim_guncelle()
        st.success("Güncellendi!")
        st.rerun()

    st.markdown(
        f"<div style='font-size:9px;color:#5a4a3a;margin-top:8px'>{datetime.now().strftime('%d.%m.%Y %H:%M')}</div>",
        unsafe_allow_html=True
    )

# ── GENEL BAKIŞ ───────────────────────────────────────
def genel(veri):
    st.markdown("# Genel Bakış")

    tum_a, tum_k = [], []
    for k in KATLAR:
        tum_a += veri.get(k,{}).get("acik",[])
        tum_k += veri.get(k,{}).get("kapali",[])
    s = ist(tum_a, tum_k)
    yat = (s["acik"]+s["kapali"])*POS_TL
    guncel = yat + s["top_kz"]

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Toplam K/Z",    tl(s["top_kz"]))
    c2.metric("Giriş Bütçesi", tl(yat, False))
    c3.metric("Güncel Bütçe",  tl(guncel, False))
    c4.metric("Başarı",        f"%{s['basari']:.0f}")
    c5.metric("Açık",          s["acik"])
    c6.metric("Kapanan",       s["kapali"])

    st.markdown("---")

    # Kategori kartları
    cols = st.columns(4)
    for i,(k,b) in enumerate(KATLAR.items()):
        a = veri.get(k,{}).get("acik",[])
        ka= veri.get(k,{}).get("kapali",[])
        s2= ist(a,ka)
        r = rk(s2["top_kz"])
        with cols[i]:
            st.markdown(f"""
            <div style='background:white;border:1px solid #ddd0c0;border-radius:12px;
                        padding:14px;box-shadow:0 1px 4px rgba(44,31,22,0.06)'>
                <div style='font-size:22px;margin-bottom:6px'>{b['emoji']}</div>
                <div style='font-size:11px;font-weight:700;color:{b['renk']};
                            text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px'>{b['isim']}</div>
                <div style='font-family:DM Mono;font-size:18px;font-weight:600;color:{r}'>{tl(s2['top_kz'])}</div>
                <div style='font-size:10px;color:#9a836e;margin-top:6px;border-top:1px solid #efe9df;padding-top:6px'>
                    %{s2['basari']:.0f} başarı &nbsp;·&nbsp; {s2['acik']} açık &nbsp;·&nbsp; {s2['kapali']} kapandı
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Grafikler
    st.markdown("---")
    g1,g2 = st.columns([3,2])

    with g1:
        st.markdown("### Kategori K/Z")
        isimler = [b["isim"] for b in KATLAR.values()]
        kzlar   = [ist(veri.get(k,{}).get("acik",[]),veri.get(k,{}).get("kapali",[])).get("top_kz",0) for k in KATLAR]
        renkler = [rk(v) for v in kzlar]
        fig = go.Figure(go.Bar(
            x=isimler, y=kzlar,
            marker=dict(color=renkler, opacity=0.75, line=dict(width=0)),
            text=[tl(k) for k in kzlar], textposition="outside",
            textfont=dict(size=10, family="DM Mono"),
        ))
        st.plotly_chart(fig_layout(fig), use_container_width=True)

    with g2:
        st.markdown("### Kazanan / Kaybeden")
        kaz_l,kay_l,ism_l = [],[],[]
        for k,b in KATLAR.items():
            s3 = ist(veri.get(k,{}).get("acik",[]),veri.get(k,{}).get("kapali",[]))
            if s3["kapali"]>0:
                kaz_l.append(s3["kazanan"]); kay_l.append(s3["kaybeden"]); ism_l.append(b["isim"])
        if kaz_l:
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(name="Kazanan",x=ism_l,y=kaz_l,marker_color="#4a7c5f",opacity=0.8))
            fig2.add_trace(go.Bar(name="Kaybeden",x=ism_l,y=kay_l,marker_color="#b85450",opacity=0.8))
            fig2.update_layout(barmode="stack", showlegend=True,
                               legend=dict(orientation="h",y=-0.3,font=dict(size=10)))
            st.plotly_chart(fig_layout(fig2), use_container_width=True)

    # Açık pozisyonlar
    if any(veri.get(k,{}).get("acik",[]) for k in KATLAR):
        st.markdown("---")
        st.markdown("### Açık Pozisyonlar")
        for k,b in KATLAR.items():
            pozlar = veri.get(k,{}).get("acik",[])
            if pozlar:
                st.markdown(f"**{b['emoji']} {b['isim']}**")
                for p in pozlar: poz_kart(p, b["renk"])

# ── PERFORMANS ────────────────────────────────────────
def performans(veri):
    st.markdown("# Performans")

    tum_a,tum_k = [],[]
    for k in KATLAR:
        for p in veri.get(k,{}).get("acik",[]): tum_a.append({**p,"kat":k})
        for p in veri.get(k,{}).get("kapali",[]): tum_k.append({**p,"kat":k})
    s = ist(tum_a,tum_k)
    yat = (s["acik"]+s["kapali"])*POS_TL
    guncel = yat+s["top_kz"]

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Başlangıç",    tl(yat, False))
    c2.metric("Güncel",       tl(guncel, False), tl(s["top_kz"]))
    c3.metric("Getiri",       pct(s["top_kz"]/yat if yat else 0))
    c4.metric("Başarı",       f"%{s['basari']:.1f}")

    st.markdown("---")

    if tum_k:
        g1,g2 = st.columns(2)

        with g1:
            st.markdown("### Bütçe Gidişatı")
            siralı = sorted(tum_k, key=lambda x: x.get("cikis_tarih","") or "")
            tarihler,but_list = [],[]
            toplam = yat
            for p in siralı:
                toplam += p.get("kz_tl",0)
                tarihler.append(p.get("cikis_tarih",""))
                but_list.append(toplam)
            fig = go.Figure(go.Scatter(
                x=tarihler, y=but_list, mode="lines+markers",
                line=dict(color="#8b6f5e",width=2),
                marker=dict(size=5,color="#8b6f5e"),
                fill="tozeroy", fillcolor="rgba(139,111,94,0.08)",
            ))
            fig.add_hline(y=yat, line_dash="dot", line_color="#9a836e",
                          annotation_text="Başlangıç", annotation_font_size=9)
            st.plotly_chart(fig_layout(fig,240), use_container_width=True)

        with g2:
            st.markdown("### Kümülatif K/Z")
            siralı2 = sorted(tum_k, key=lambda x: x.get("cikis_tarih","") or "")
            tarihler2,kum = [],[]
            toplam2 = 0
            for p in siralı2:
                toplam2 += p.get("kz_tl",0)
                tarihler2.append(p.get("cikis_tarih",""))
                kum.append(toplam2)
            son_r = "#4a7c5f" if (kum[-1] if kum else 0)>=0 else "#b85450"
            fig3 = go.Figure(go.Scatter(
                x=tarihler2, y=kum, mode="lines",
                fill="tozeroy",
                fillcolor=f"{'rgba(74,124,95,0.1)' if son_r=='#4a7c5f' else 'rgba(184,84,80,0.1)'}",
                line=dict(color=son_r,width=2),
            ))
            st.plotly_chart(fig_layout(fig3,240), use_container_width=True)

    st.markdown("### Puan Bazlı Performans")
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
            "Toplam K/Z": tl(sum(p.get("kz_tl",0) for p in pozlar)),
            "Ort. K/Z": tl(sum(p.get("kz_tl",0) for p in pozlar)/len(pozlar)),
        })
    if rows: st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

# ── KATEGORİ DETAY ────────────────────────────────────
def detay(kat_key, veri):
    b      = KATLAR[kat_key]
    acik   = veri.get(kat_key,{}).get("acik",[])
    kapali = veri.get(kat_key,{}).get("kapali",[])
    s      = ist(acik,kapali)
    yat    = (s["acik"]+s["kapali"])*POS_TL

    st.markdown(f"# {b['emoji']} {b['isim']}")

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Toplam K/Z",   tl(s["top_kz"]))
    c2.metric("Giriş Bütçesi",tl(yat, False))
    c3.metric("Başarı",       f"%{s['basari']:.1f}")
    c4.metric("Kazanan",      s["kazanan"])
    c5.metric("Kaybeden",     s["kaybeden"])

    tab1,tab2,tab3 = st.tabs(["📂 Açık Pozisyonlar","✅ Kapananlar","📊 Analiz"])

    with tab1:
        if acik:
            for p in acik: poz_kart(p, b["renk"])
        else:
            st.info("Açık pozisyon yok")

    with tab2:
        if kapali:
            filtre = st.selectbox("",["Tümü","Kazananlar","Kaybedenler"],label_visibility="collapsed")
            liste  = kapali
            if filtre=="Kazananlar":  liste=[p for p in kapali if p.get("kz_tl",0)>0]
            if filtre=="Kaybedenler": liste=[p for p in kapali if p.get("kz_tl",0)<=0]
            for p in reversed(liste[-30:]): kapali_kart(p)
        else:
            st.info("Kapanan işlem yok")

    with tab3:
        if kapali:
            st.markdown("### Kümülatif K/Z")
            siralı = sorted(kapali, key=lambda x: x.get("cikis_tarih","") or "")
            tarihler,kum = [],[]
            t = 0
            for p in siralı:
                t += p.get("kz_tl",0)
                tarihler.append(p.get("cikis_tarih",""))
                kum.append(t)
            r = "#4a7c5f" if (kum[-1] if kum else 0)>=0 else "#b85450"
            fig = go.Figure(go.Scatter(
                x=tarihler, y=kum, mode="lines",
                fill="tozeroy",
                fillcolor=f"{'rgba(74,124,95,0.1)' if r=='#4a7c5f' else 'rgba(184,84,80,0.1)'}",
                line=dict(color=r,width=2),
            ))
            st.plotly_chart(fig_layout(fig,220), use_container_width=True)

        st.markdown("### Puan Bazlı")
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
                "Puan": aralik, "İşlem": len(pozlar),
                "Başarı": f"%{len(kaz)/len(kap)*100:.0f}" if kap else "—",
                "Toplam K/Z": tl(sum(p.get("kz_tl",0) for p in pozlar)),
            })
        if rows: st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)

# ── ROUTING ───────────────────────────────────────────
veri = yukle()

if   secim == "🏠 Genel":        genel(veri)
elif secim == "📈 Performans":    performans(veri)
elif secim == "📈 BIST Teknik":   detay("bist_trade", veri)
elif secim == "📊 BIST Temel":    detay("bist_temel", veri)
elif secim == "🪙 Kripto":        detay("kripto", veri)
elif secim == "🥇 Emtia":         detay("metal", veri)
