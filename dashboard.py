"""
dashboard.py — Trading Dashboard
Pastel krem/mavi tema, Streamlit native bileşenler

pip install streamlit plotly pandas yfinance requests
streamlit run dashboard.py
"""

import streamlit as st
import json, os, requests
import plotly.graph_objects as go
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
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500&display=swap');

:root {
    --cream:   #faf7f2;
    --cream2:  #f4efe6;
    --cream3:  #ede5d8;
    --blue:    #b8cfe8;
    --blue2:   #8ab0d4;
    --blue3:   #5d8ab8;
    --sage:    #a8c5a8;
    --rose:    #e8b4b4;
    --gold:    #d4b896;
    --text:    #3d3530;
    --text2:   #6b5f58;
    --muted:   #a09590;
    --border:  #e0d8cc;
    --green:   #6aaa7a;
    --red:     #d4706a;
    --white:   #ffffff;
}

html, body, [class*="css"], .main, .block-container {
    background: var(--cream) !important;
    color: var(--text) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.block-container { padding: 1.5rem 2rem !important; max-width: 1400px !important; }

section[data-testid="stSidebar"] {
    background: var(--cream2) !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] * { color: var(--text) !important; }
section[data-testid="stSidebar"] .stRadio label {
    background: transparent !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
    margin: 2px 0 !important;
    display: block !important;
    font-size: 13px !important;
    color: var(--text2) !important;
    border: 1px solid transparent !important;
    transition: all 0.15s !important;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    background: var(--cream3) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
}

div[data-testid="stMetric"] {
    background: var(--white) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 14px 16px !important;
    box-shadow: 0 1px 4px rgba(61,53,48,0.04) !important;
}
div[data-testid="stMetric"] label {
    color: var(--muted) !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
}
div[data-testid="stMetric"] [data-testid="metric-container"] > div:nth-child(2) {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 18px !important;
    color: var(--text) !important;
}

.stTabs [data-baseweb="tab-list"] {
    background: var(--cream2) !important;
    border-radius: 10px !important;
    padding: 3px !important;
    border: 1px solid var(--border) !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 7px !important;
    color: var(--muted) !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    padding: 6px 16px !important;
}
.stTabs [aria-selected="true"] {
    background: white !important;
    color: var(--text) !important;
    box-shadow: 0 1px 3px rgba(61,53,48,0.08) !important;
}

.stButton button {
    background: var(--blue2) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    padding: 6px 16px !important;
}
.stButton button:hover { background: var(--blue3) !important; }
.stDataFrame { border: 1px solid var(--border) !important; border-radius: 10px !important; }
hr { border-color: var(--border) !important; margin: 10px 0 !important; }
</style>
""", unsafe_allow_html=True)

# ── SABİTLER ──────────────────────────────────────────
SIM    = "sim.json"
POS_TL = 10_000

KATLAR = {
    "bist_trade": {"isim":"BIST Teknik", "emoji":"📈","renk":"#8ab0d4","bg":"#eef4fa"},
    "kripto":     {"isim":"Kripto",       "emoji":"🪙","renk":"#d4b896","bg":"#faf4ec"},
    "metal":      {"isim":"Emtia",        "emoji":"🥇","renk":"#c4a8c4","bg":"#f5eef5"},
}

# ── YARDIMCI ──────────────────────────────────────────
def yukle():
    if not os.path.exists(SIM): return {}
    with open(SIM,"r",encoding="utf-8") as f: return json.load(f)

def ist(acik, kapali):
    kaz=[p for p in kapali if p.get("kz_tl",0)>0]
    kay=[p for p in kapali if p.get("kz_tl",0)<=0]
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
    if sign: return f"+{v:,.0f} ₺" if v>=0 else f"{v:,.0f} ₺"
    return f"{v:,.0f} ₺"

def pct(v):
    if v is None: return "—"
    return f"+{v*100:.2f}%" if v>=0 else f"{v*100:.2f}%"

def rk(v): return "#6aaa7a" if v>=0 else "#d4706a"

def plt_cfg(fig, h=200, legend=False):
    fig.update_layout(
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(color="#a09590", family="Plus Jakarta Sans", size=10),
        yaxis=dict(showgrid=True, gridcolor="#f4efe6", zeroline=True,
                   zerolinecolor="#e0d8cc", tickfont=dict(size=9)),
        xaxis=dict(showgrid=False, tickfont=dict(size=9)),
        margin=dict(t=8,b=8,l=8,r=8), height=h, showlegend=legend,
    )
    return fig

# ── FİYAT GÜNCELLEME ──────────────────────────────────
def fiyat_cek(ticker):
    try:
        if "USDT" in ticker:
            r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={ticker}",timeout=5)
            return float(r.json()["price"])
        elif ticker in ["ALTIN","GUMUS","PLATIN","PALADYUM"]:
            mp={"ALTIN":"GC=F","GUMUS":"SI=F","PLATIN":"PL=F","PALADYUM":"PA=F"}
            kd=yf.download("USDTRY=X",period="2d",progress=False,auto_adjust=True)
            kur=float(kd["Close"].iloc[-1])
            d=yf.download(mp[ticker],period="2d",progress=False,auto_adjust=True)
            return float(d["Close"].iloc[-1])/31.1035*kur
        else:
            d=yf.download(ticker+".IS",period="2d",progress=False,auto_adjust=True)
            if d.empty: return None
            v=d["Close"].iloc[-1]
            return float(v.iloc[0]) if hasattr(v,"iloc") else float(v)
    except: return None

def sim_guncelle():
    if not os.path.exists(SIM): return
    with open(SIM,"r",encoding="utf-8") as f: sim=json.load(f)
    for kat in KATLAR:
        for p in sim.get(kat,{}).get("acik",[]):
            cp=fiyat_cek(p["ticker"])
            if cp is None: continue
            p["guncel"]=round(cp,6)
            yon=p.get("yon","LONG")
            p["kz_pct"]=(cp-p["giris"])/p["giris"] if yon=="LONG" else (p["giris"]-cp)/p["giris"]
            p["kz_tl"]=round(p["kz_pct"]*POS_TL,2)
            tp1=p.get("tp1"); tp2=p.get("tp2")
            if tp1 and not p.get("tp1_gecildi"):
                if (yon=="LONG" and cp>=tp1) or (yon=="SHORT" and cp<=tp1): p["tp1_gecildi"]=True
            if tp2 and not p.get("tp2_gecildi"):
                if (yon=="LONG" and cp>=tp2) or (yon=="SHORT" and cp<=tp2): p["tp2_gecildi"]=True
    with open(SIM,"w",encoding="utf-8") as f: json.dump(sim,f,ensure_ascii=False,indent=2)

# ── POZİSYON KARTI ────────────────────────────────────
def poz_kart(p, renk="#8ab0d4", bg="#eef4fa"):
    kz    = p.get("kz_tl",0)
    kzp   = p.get("kz_pct",0)
    yon   = p.get("yon","LONG")
    puan  = p.get("puan")
    g     = gun(p.get("giris_tarih",p.get("tarih","")))
    gunc  = p.get("guncel",p.get("giris",0))
    giris = p.get("giris",0)
    stop  = p.get("stop")
    tp1   = p.get("tp1"); tp2=p.get("tp2"); tp3=p.get("tp3")
    tp1ok = p.get("tp1_gecildi",False)
    tp2ok = p.get("tp2_gecildi",False)
    r     = rk(kz)

    # Başlık satırı
    col1, col2 = st.columns([4,1])
    with col1:
        yon_em = "▲" if yon=="LONG" else "▼"
        yon_c  = "green" if yon=="LONG" else "red"
        puan_t = f" `{puan}/100`" if puan else ""
        st.markdown(
            f"**{p['ticker']}**{puan_t}  "
            f":{yon_c}[{yon_em} {yon}]  "
            f"*{g} gün*"
        )
        info = f"`Giriş: {giris:.4f}` → `Şimdi: {gunc:.4f}`"
        if stop: info += f"  🔴 `Stop: {stop:.4f}`"
        st.caption(info)
    with col2:
        st.metric("", tl(kz), pct(kzp))

    # Seviyeler — sayısal
    seviye_cols = st.columns(4)
    with seviye_cols[0]:
        if stop:
            stop_pct = (stop - giris) / giris * 100
            st.markdown(
                f"<div style='background:#fdf2f2;border:1px solid #f5c6c6;border-radius:8px;"
                f"padding:8px 10px;text-align:center'>"
                f"<div style='font-size:9px;color:#d4706a;font-weight:600;text-transform:uppercase;letter-spacing:0.5px'>Stop</div>"
                f"<div style='font-family:JetBrains Mono;font-size:13px;color:#d4706a;margin-top:2px'>{stop:.4f}</div>"
                f"<div style='font-size:9px;color:#d4706a;opacity:0.7'>{stop_pct:+.1f}%</div>"
                f"</div>",
                unsafe_allow_html=True
            )
    with seviye_cols[1]:
        if tp1:
            tp1_pct = (tp1 - giris) / giris * 100
            tp1_c = "#6aaa7a" if tp1ok else "#a09590"
            tp1_bg = "#f2fdf4" if tp1ok else "#f8f6f4"
            tp1_border = "#c6e8cc" if tp1ok else "#e0d8cc"
            st.markdown(
                f"<div style='background:{tp1_bg};border:1px solid {tp1_border};border-radius:8px;"
                f"padding:8px 10px;text-align:center'>"
                f"<div style='font-size:9px;color:{tp1_c};font-weight:600;text-transform:uppercase;letter-spacing:0.5px'>{'✓ ' if tp1ok else ''}TP1</div>"
                f"<div style='font-family:JetBrains Mono;font-size:13px;color:{tp1_c};margin-top:2px'>{tp1:.4f}</div>"
                f"<div style='font-size:9px;color:{tp1_c};opacity:0.7'>{tp1_pct:+.1f}%</div>"
                f"</div>",
                unsafe_allow_html=True
            )
    with seviye_cols[2]:
        if tp2:
            tp2_pct = (tp2 - giris) / giris * 100
            tp2_c = "#6aaa7a" if tp2ok else "#a09590"
            tp2_bg = "#f2fdf4" if tp2ok else "#f8f6f4"
            tp2_border = "#c6e8cc" if tp2ok else "#e0d8cc"
            st.markdown(
                f"<div style='background:{tp2_bg};border:1px solid {tp2_border};border-radius:8px;"
                f"padding:8px 10px;text-align:center'>"
                f"<div style='font-size:9px;color:{tp2_c};font-weight:600;text-transform:uppercase;letter-spacing:0.5px'>{'✓ ' if tp2ok else ''}TP2</div>"
                f"<div style='font-family:JetBrains Mono;font-size:13px;color:{tp2_c};margin-top:2px'>{tp2:.4f}</div>"
                f"<div style='font-size:9px;color:{tp2_c};opacity:0.7'>{tp2_pct:+.1f}%</div>"
                f"</div>",
                unsafe_allow_html=True
            )
    with seviye_cols[3]:
        if tp3:
            tp3_pct = (tp3 - giris) / giris * 100
            st.markdown(
                f"<div style='background:#f8f6f4;border:1px solid #e0d8cc;border-radius:8px;"
                f"padding:8px 10px;text-align:center'>"
                f"<div style='font-size:9px;color:#a09590;font-weight:600;text-transform:uppercase;letter-spacing:0.5px'>TP3</div>"
                f"<div style='font-family:JetBrains Mono;font-size:13px;color:#a09590;margin-top:2px'>{tp3:.4f}</div>"
                f"<div style='font-size:9px;color:#a09590;opacity:0.7'>{tp3_pct:+.1f}%</div>"
                f"</div>",
                unsafe_allow_html=True
            )
    st.markdown("<div style='margin-bottom:4px'></div>", unsafe_allow_html=True)

    if p.get("notlar"): st.caption(f"📝 {p['notlar']}")
    st.divider()

def kapali_kart(p):
    kz   = p.get("kz_tl",0)
    kzp  = p.get("kz_pct",0)
    neden= {"stop":"🛑 Stop","tp3":"🎯 TP3","trailing_stop":"🔀 İz Stop"}.get(
            p.get("durum",p.get("cikis_neden","")), "✅")
    puan = p.get("puan")
    g    = gun(p.get("giris_tarih",p.get("tarih","")))
    r    = rk(kz)

    col1,col2 = st.columns([4,1])
    with col1:
        puan_t = f" `{puan}/100`" if puan else ""
        st.markdown(f"**{p['ticker']}**{puan_t}  {neden}  *{g}g*")
        st.caption(f"{p.get('giris_tarih','—')} → {p.get('cikis_tarih','—')}")
    with col2:
        st.metric("", tl(kz), pct(kzp))
    st.divider()

# ── SIDEBAR ───────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 Trading Bot")

    veri = yukle()
    top_kz   = sum(sum(p.get("kz_tl",0) for p in veri.get(k,{}).get("acik",[])+veri.get(k,{}).get("kapali",[])) for k in KATLAR)
    top_acik = sum(len(veri.get(k,{}).get("acik",[])) for k in KATLAR)
    top_kap  = sum(len(veri.get(k,{}).get("kapali",[])) for k in KATLAR)

    r = "#6aaa7a" if top_kz>=0 else "#d4706a"
    st.markdown(f"""
    <div style='background:white;border:1px solid #e0d8cc;border-radius:12px;
                padding:14px;margin:8px 0 16px'>
        <div style='font-size:10px;text-transform:uppercase;letter-spacing:1px;
                    color:#a09590;margin-bottom:6px'>Toplam K/Z</div>
        <div style='font-family:JetBrains Mono;font-size:20px;color:{r};font-weight:500'>{tl(top_kz)}</div>
        <div style='font-size:11px;color:#a09590;margin-top:6px'>{top_acik} açık · {top_kap} kapandı</div>
    </div>
    """, unsafe_allow_html=True)

    secim = st.radio("",
        ["🏠 Genel Bakış","📈 Performans",
         "📈 BIST Teknik","🪙 Kripto","🥇 Emtia"],
        label_visibility="collapsed"
    )

    st.divider()
    if st.button("🔄 Fiyat Güncelle", use_container_width=True):
        with st.spinner("Fiyatlar çekiliyor..."):
            sim_guncelle()
        st.success("Güncellendi!")
        st.rerun()

    st.caption(datetime.now().strftime("%d.%m.%Y %H:%M"))

# ── GENEL BAKIŞ ───────────────────────────────────────
def genel(veri):
    st.markdown("## 🏠 Genel Bakış")
    st.caption(datetime.now().strftime("%A, %d %B %Y"))

    tum_a,tum_k=[],[]
    for k in KATLAR:
        tum_a+=veri.get(k,{}).get("acik",[])
        tum_k+=veri.get(k,{}).get("kapali",[])
    s   = ist(tum_a,tum_k)
    yat = (s["acik"]+s["kapali"])*POS_TL
    gun_but = yat+s["top_kz"]

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Toplam K/Z",   tl(s["top_kz"]))
    c2.metric("Getiri",       pct(s["top_kz"]/yat if yat else 0))
    c3.metric("Güncel Bütçe", tl(gun_but,False))
    c4.metric("Başarı",       f"%{s['basari']:.0f}")
    c5.metric("Açık",         s["acik"])
    c6.metric("Kapanan",      s["kapali"])

    st.markdown("<br>", unsafe_allow_html=True)

    # Kategori kartları
    cols = st.columns(4)
    for i,(k,b) in enumerate(KATLAR.items()):
        a=veri.get(k,{}).get("acik",[])
        ka=veri.get(k,{}).get("kapali",[])
        s2=ist(a,ka)
        r=rk(s2["top_kz"])
        with cols[i]:
            st.markdown(f"""
            <div style='background:white;border:1px solid #e0d8cc;border-radius:14px;
                        padding:16px;box-shadow:0 1px 4px rgba(61,53,48,0.04)'>
                <div style='font-size:24px;margin-bottom:8px'>{b['emoji']}</div>
                <div style='font-size:12px;font-weight:600;color:{b['renk']};margin-bottom:8px'>{b['isim']}</div>
                <div style='font-family:JetBrains Mono;font-size:18px;color:{r};font-weight:500'>{tl(s2['top_kz'])}</div>
                <div style='margin-top:10px;background:{b['bg']};border-radius:4px;height:4px;overflow:hidden'>
                    <div style='height:100%;width:{s2['basari']:.0f}%;background:{b['renk']};border-radius:4px'></div>
                </div>
                <div style='font-size:10px;color:#a09590;margin-top:6px'>
                    %{s2['basari']:.0f} başarı · {s2['acik']} açık · {s2['kapali']} kapandı
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    g1,g2 = st.columns(2)

    with g1:
        st.markdown("##### Kategori K/Z")
        isimler=[b["isim"] for b in KATLAR.values()]
        kzlar=[ist(veri.get(k,{}).get("acik",[]),veri.get(k,{}).get("kapali",[])).get("top_kz",0) for k in KATLAR]
        fig=go.Figure(go.Bar(
            x=isimler,y=kzlar,
            marker=dict(color=[rk(v) for v in kzlar],opacity=0.7,line=dict(width=0)),
            text=[tl(k) for k in kzlar],textposition="outside",
            textfont=dict(size=10,family="JetBrains Mono"),
        ))
        st.plotly_chart(plt_cfg(fig,220),use_container_width=True)

    with g2:
        st.markdown("##### Kazanan / Kaybeden")
        kaz_l,kay_l,ism_l=[],[],[]
        for k,b in KATLAR.items():
            s3=ist(veri.get(k,{}).get("acik",[]),veri.get(k,{}).get("kapali",[]))
            if s3["kapali"]>0:
                kaz_l.append(s3["kazanan"]); kay_l.append(s3["kaybeden"]); ism_l.append(b["isim"])
        if kaz_l:
            fig2=go.Figure()
            fig2.add_trace(go.Bar(name="Kazanan",x=ism_l,y=kaz_l,marker_color="#6aaa7a",opacity=0.7,marker_line_width=0))
            fig2.add_trace(go.Bar(name="Kaybeden",x=ism_l,y=kay_l,marker_color="#d4706a",opacity=0.7,marker_line_width=0))
            fig2.update_layout(barmode="stack",showlegend=True,legend=dict(orientation="h",y=-0.3,font=dict(size=10)))
            st.plotly_chart(plt_cfg(fig2,220,True),use_container_width=True)

    if tum_a:
        st.markdown("---")
        st.markdown("##### Açık Pozisyonlar")
        for k,b in KATLAR.items():
            pozlar=veri.get(k,{}).get("acik",[])
            if pozlar:
                st.markdown(f"**{b['emoji']} {b['isim']}**")
                for p in pozlar: poz_kart(p, b["renk"], b["bg"])

# ── PERFORMANS ────────────────────────────────────────
def performans(veri):
    st.markdown("## 📈 Performans")

    tum_a,tum_k=[],[]
    for k in KATLAR:
        for p in veri.get(k,{}).get("acik",[]): tum_a.append({**p,"kat":k})
        for p in veri.get(k,{}).get("kapali",[]): tum_k.append({**p,"kat":k})
    s=ist(tum_a,tum_k)
    yat=(s["acik"]+s["kapali"])*POS_TL
    gun_but=yat+s["top_kz"]

    c1,c2,c3,c4=st.columns(4)
    c1.metric("Başlangıç",  tl(yat,False))
    c2.metric("Güncel",     tl(gun_but,False), tl(s["top_kz"]))
    c3.metric("Getiri",     pct(s["top_kz"]/yat if yat else 0))
    c4.metric("Başarı",     f"%{s['basari']:.1f}")

    st.markdown("<br>", unsafe_allow_html=True)

    if tum_k:
        g1,g2=st.columns(2)
        siralı=sorted(tum_k,key=lambda x: x.get("cikis_tarih","") or "")

        with g1:
            st.markdown("##### Bütçe Gidişatı")
            tarihler,but_list=[],[]
            toplam=yat
            for p in siralı:
                toplam+=p.get("kz_tl",0)
                tarihler.append(p.get("cikis_tarih",""))
                but_list.append(toplam)
            fig=go.Figure(go.Scatter(
                x=tarihler,y=but_list,mode="lines+markers",
                line=dict(color="#8ab0d4",width=2),
                marker=dict(size=5,color="#8ab0d4"),
                fill="tozeroy",fillcolor="rgba(138,176,212,0.08)",
            ))
            fig.add_hline(y=yat,line_dash="dot",line_color="#e0d8cc",
                          annotation_text="Başlangıç",annotation_font_size=9)
            st.plotly_chart(plt_cfg(fig,240),use_container_width=True)

        with g2:
            st.markdown("##### Kümülatif K/Z")
            tarihler2,kum=[],[]
            t=0
            for p in siralı:
                t+=p.get("kz_tl",0)
                tarihler2.append(p.get("cikis_tarih",""))
                kum.append(t)
            sr="#6aaa7a" if (kum[-1] if kum else 0)>=0 else "#d4706a"
            fig3=go.Figure(go.Scatter(
                x=tarihler2,y=kum,mode="lines",
                fill="tozeroy",
                fillcolor=f"{'rgba(106,170,122,0.1)' if sr=='#6aaa7a' else 'rgba(212,112,106,0.1)'}",
                line=dict(color=sr,width=2),
            ))
            st.plotly_chart(plt_cfg(fig3,240),use_container_width=True)

    # ── BENCHMARK KARŞILAŞTIRMASI ─────────────────────
    st.markdown("---")
    st.markdown("##### 📊 BIST 100 vs Portföy")

    try:
        import yfinance as yf
        from datetime import timedelta

        # BIST 100 verisi
        xu100 = yf.download("XU100.IS", period="6mo", progress=False, auto_adjust=True)

        if not xu100.empty:
            b1, b2 = st.columns(2)

            with b1:
                st.markdown("**Günlük Karşılaştırma**")
                # BIST 100 günlük değişim
                if len(xu100) >= 2:
                    dun = float(xu100["Close"].iloc[-2])
                    bugun = float(xu100["Close"].iloc[-1])
                    bist_gunluk = (bugun - dun) / dun * 100

                    # Portföy günlük değişim — açık pozisyonların bugünkü K/Z
                    portfolyo_gunluk_tl = sum(p.get("kz_tl", 0) for p in tum_a)
                    portfolyo_yat = len(tum_a) * POS_TL if tum_a else POS_TL
                    portfolyo_gunluk = portfolyo_gunluk_tl / portfolyo_yat * 100 if portfolyo_yat else 0

                    c1, c2 = st.columns(2)
                    renk_bist = "#6aaa7a" if bist_gunluk >= 0 else "#d4706a"
                    renk_port = "#6aaa7a" if portfolyo_gunluk >= 0 else "#d4706a"

                    c1.metric("BIST 100 Bugün",
                              f"%{bist_gunluk:+.2f}",
                              f"{bugun:,.0f} puan")
                    c2.metric("Portföy Bugün",
                              f"%{portfolyo_gunluk:+.2f}",
                              f"{tl(portfolyo_gunluk_tl)}")

                    # Fark
                    fark = portfolyo_gunluk - bist_gunluk
                    fark_r = "#6aaa7a" if fark >= 0 else "#d4706a"
                    st.markdown(
                        f"<div style='background:white;border:1px solid #e0d8cc;border-radius:10px;"
                        f"padding:10px 14px;margin-top:8px;text-align:center'>"
                        f"<div style='font-size:10px;color:#a09590;margin-bottom:4px'>Alpha (Portföy - BIST 100)</div>"
                        f"<div style='font-family:JetBrains Mono;font-size:18px;color:{fark_r};font-weight:500'>"
                        f"%{fark:+.2f}</div></div>",
                        unsafe_allow_html=True
                    )

            with b2:
                st.markdown("**Kümülatif Karşılaştırma**")

                if tum_k:
                    # Portföy kümülatif getiri
                    siralı_port = sorted(tum_k, key=lambda x: x.get("cikis_tarih","") or "")

                    # İlk işlem tarihinden itibaren BIST 100
                    try:
                        ilk_tarih = siralı_port[0].get("cikis_tarih","")
                        if ilk_tarih:
                            ilk_dt = datetime.strptime(ilk_tarih, "%d.%m.%Y %H:%M")
                            xu100_filtered = xu100[xu100.index >= ilk_dt.strftime("%Y-%m-%d")]

                            if not xu100_filtered.empty:
                                bist_baslangic = float(xu100_filtered["Close"].iloc[0])
                                bist_tarihler  = [str(d.date()) for d in xu100_filtered.index]
                                bist_getiri    = [(float(v) - bist_baslangic) / bist_baslangic * 100
                                                  for v in xu100_filtered["Close"]]

                                # Portföy kümülatif
                                port_tarihler, port_getiri = [], []
                                kum_tl = 0
                                baslangic_yat = len(tum_k) * POS_TL
                                for p in siralı_port:
                                    kum_tl += p.get("kz_tl", 0)
                                    port_tarihler.append(p.get("cikis_tarih","")[:10])
                                    port_getiri.append(kum_tl / baslangic_yat * 100 if baslangic_yat else 0)

                                fig_bench = go.Figure()
                                fig_bench.add_trace(go.Scatter(
                                    x=bist_tarihler, y=bist_getiri,
                                    name="BIST 100", mode="lines",
                                    line=dict(color="#8ab0d4", width=1.5, dash="dot"),
                                ))
                                fig_bench.add_trace(go.Scatter(
                                    x=port_tarihler, y=port_getiri,
                                    name="Portföy", mode="lines+markers",
                                    line=dict(color="#6aaa7a", width=2),
                                    marker=dict(size=4, color="#6aaa7a"),
                                    fill="tozeroy",
                                    fillcolor="rgba(106,170,122,0.06)",
                                ))
                                fig_bench.add_hline(y=0, line_dash="dot", line_color="#e0d8cc")
                                fig_bench.update_layout(
                                    paper_bgcolor="white", plot_bgcolor="white",
                                    font=dict(color="#a09590", family="Plus Jakarta Sans", size=10),
                                    yaxis=dict(showgrid=True, gridcolor="#f4efe6",
                                               zeroline=False, ticksuffix="%", tickfont=dict(size=9)),
                                    xaxis=dict(showgrid=False, tickfont=dict(size=9)),
                                    margin=dict(t=8,b=8,l=8,r=8), height=220,
                                    showlegend=True,
                                    legend=dict(orientation="h", y=-0.3, font=dict(size=10)),
                                )
                                st.plotly_chart(fig_bench, use_container_width=True)
                    except Exception as e:
                        st.caption(f"Grafik yüklenemedi: {e}")
                else:
                    st.info("Karşılaştırma için kapanan işlem gerekli")
    except Exception as e:
        st.caption(f"BIST 100 verisi alınamadı: {e}")

    st.markdown("---")
    st.markdown("##### Puan Bazlı Performans")
    gruplar={"65-69":[],"70-79":[],"80-89":[],"90-99":[],"100":[]}
    for p in tum_a+tum_k:
        puan=p.get("puan",0)
        if   puan>=100: gruplar["100"].append(p)
        elif puan>=90:  gruplar["90-99"].append(p)
        elif puan>=80:  gruplar["80-89"].append(p)
        elif puan>=70:  gruplar["70-79"].append(p)
        else:           gruplar["65-69"].append(p)
    rows=[]
    for aralik,pozlar in gruplar.items():
        if not pozlar: continue
        kap=[p for p in pozlar if p.get("durum","acik")!="acik"]
        kaz=[p for p in kap if p.get("kz_tl",0)>0]
        rows.append({
            "Puan":aralik,"İşlem":len(pozlar),"Kapanan":len(kap),
            "Başarı":f"%{len(kaz)/len(kap)*100:.0f}" if kap else "—",
            "Toplam K/Z":tl(sum(p.get("kz_tl",0) for p in pozlar)),
            "Ort. K/Z":tl(sum(p.get("kz_tl",0) for p in pozlar)/len(pozlar)),
        })
    if rows: st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)

# ── KATEGORİ DETAY ────────────────────────────────────
def detay(kat_key,veri):
    b=KATLAR[kat_key]
    acik=veri.get(kat_key,{}).get("acik",[])
    kapali=veri.get(kat_key,{}).get("kapali",[])
    s=ist(acik,kapali)
    yat=(s["acik"]+s["kapali"])*POS_TL

    st.markdown(f"## {b['emoji']} {b['isim']}")

    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("Toplam K/Z",  tl(s["top_kz"]))
    c2.metric("Giriş Bütçesi",tl(yat,False))
    c3.metric("Başarı",      f"%{s['basari']:.1f}")
    c4.metric("Kazanan",     s["kazanan"])
    c5.metric("Kaybeden",    s["kaybeden"])

    st.markdown("<br>", unsafe_allow_html=True)
    tab1,tab2,tab3=st.tabs(["📂 Açık Pozisyonlar","✅ Kapananlar","📊 Analiz"])

    with tab1:
        if acik:
            for p in acik: poz_kart(p,b["renk"],b["bg"])
        else:
            st.info("Açık pozisyon yok")

    with tab2:
        if kapali:
            filtre=st.selectbox("",["Tümü","Kazananlar","Kaybedenler"],label_visibility="collapsed")
            liste=kapali
            if filtre=="Kazananlar":  liste=[p for p in kapali if p.get("kz_tl",0)>0]
            if filtre=="Kaybedenler": liste=[p for p in kapali if p.get("kz_tl",0)<=0]
            for p in reversed(liste[-30:]): kapali_kart(p)
        else:
            st.info("Kapanan işlem yok")

    with tab3:
        if kapali:
            st.markdown("##### Kümülatif K/Z")
            siralı=sorted(kapali,key=lambda x: x.get("cikis_tarih","") or "")
            tarihler,kum=[],[]
            t=0
            for p in siralı:
                t+=p.get("kz_tl",0)
                tarihler.append(p.get("cikis_tarih",""))
                kum.append(t)
            r="#6aaa7a" if (kum[-1] if kum else 0)>=0 else "#d4706a"
            fig=go.Figure(go.Scatter(
                x=tarihler,y=kum,mode="lines+markers",
                line=dict(color=r,width=2),marker=dict(size=5,color=r),
                fill="tozeroy",
                fillcolor=f"{'rgba(106,170,122,0.1)' if r=='#6aaa7a' else 'rgba(212,112,106,0.1)'}",
            ))
            st.plotly_chart(plt_cfg(fig,200),use_container_width=True)

        gruplar={"65-69":[],"70-79":[],"80-89":[],"90-99":[],"100":[]}
        for p in acik+kapali:
            puan=p.get("puan",0)
            if   puan>=100: gruplar["100"].append(p)
            elif puan>=90:  gruplar["90-99"].append(p)
            elif puan>=80:  gruplar["80-89"].append(p)
            elif puan>=70:  gruplar["70-79"].append(p)
            else:           gruplar["65-69"].append(p)
        rows=[]
        for aralik,pozlar in gruplar.items():
            if not pozlar: continue
            kap=[p for p in pozlar if p.get("durum","acik")!="acik"]
            kaz=[p for p in kap if p.get("kz_tl",0)>0]
            rows.append({
                "Puan":aralik,"İşlem":len(pozlar),
                "Başarı":f"%{len(kaz)/len(kap)*100:.0f}" if kap else "—",
                "K/Z":tl(sum(p.get("kz_tl",0) for p in pozlar)),
            })
        if rows:
            st.markdown("##### Puan Bazlı")
            st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)

# ── ROUTING ───────────────────────────────────────────
veri=yukle()
if   secim=="🏠 Genel Bakış":  genel(veri)
elif secim=="📈 Performans":    performans(veri)
elif secim=="📈 BIST Teknik":   detay("bist_trade",veri)
elif secim=="🪙 Kripto":        detay("kripto",veri)
elif secim=="🥇 Emtia":         detay("metal",veri)
