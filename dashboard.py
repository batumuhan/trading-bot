"""
dashboard.py — Trading Bot Dashboard v3
pip install streamlit plotly pandas yfinance requests
streamlit run dashboard.py
"""

import streamlit as st
import json, os, math, time
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import yfinance as yf
import requests

st.set_page_config(page_title="Trading Dashboard", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
*, body { font-family: 'Outfit', sans-serif !important; }
.mono { font-family: 'JetBrains Mono', monospace !important; }
html, body, [class*="css"], .main, .block-container { background:#f4f6fa !important; color:#1e293b !important; }
section[data-testid="stSidebar"] { background:linear-gradient(160deg,#4f46e5 0%,#7c3aed 100%) !important; }
section[data-testid="stSidebar"] * { color:white !important; }
section[data-testid="stSidebar"] .stRadio label {
    background:rgba(255,255,255,0.12) !important; border-radius:10px !important;
    padding:8px 14px !important; margin:3px 0 !important; display:block !important;
}
section[data-testid="stSidebar"] .stRadio label:hover { background:rgba(255,255,255,0.22) !important; }
div[data-testid="stMetric"] {
    background:white; border-radius:14px; padding:14px 18px;
    box-shadow:0 1px 6px rgba(0,0,0,0.05); border:1px solid #e8edf3;
}
div[data-testid="stMetric"] label { color:#94a3b8 !important; font-size:10px !important; font-weight:700 !important; text-transform:uppercase; letter-spacing:1px; }
.stTabs [data-baseweb="tab-list"] { background:#edf2f7; border-radius:12px; padding:4px; }
.stTabs [data-baseweb="tab"] { border-radius:8px; color:#64748b; font-weight:500; }
.stTabs [aria-selected="true"] { background:white !important; color:#1e293b !important; box-shadow:0 1px 4px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

SIM_DOSYA = "sim.json"
KATLAR = {
    "bist_trade": {"isim":"BIST Teknik","emoji":"📈","renk":"#6366f1"},
    "bist_temel": {"isim":"BIST Temel", "emoji":"📊","renk":"#8b5cf6"},
    "kripto":     {"isim":"Kripto",      "emoji":"🪙","renk":"#f59e0b"},
    "metal":      {"isim":"Emtia",       "emoji":"🥇","renk":"#10b981"},
}
POS_TL = 10_000

# ── FIYAT GÜNCELLEME ──────────────────────────────────

def guncel_fiyat_cek(ticker, yon_hint="bist"):
    """Gerçek zamanlı fiyat çek."""
    try:
        if "USDT" in ticker:
            r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={ticker}", timeout=5)
            return float(r.json()["price"])
        elif ticker in ["ALTIN","GUMUS","PLATIN","PALADYUM"]:
            mp = {"ALTIN":"GC=F","GUMUS":"SI=F","PLATIN":"PL=F","PALADYUM":"PA=F"}
            kur_d = yf.download("USDTRY=X", period="2d", progress=False, auto_adjust=True)
            kur   = float(kur_d["Close"].iloc[-1])
            d     = yf.download(mp[ticker], period="2d", progress=False, auto_adjust=True)
            return float(d["Close"].iloc[-1]) / 31.1035 * kur
        else:
            d = yf.download(ticker+".IS", period="2d", progress=False, auto_adjust=True)
            if d.empty: return None
            v = d["Close"].iloc[-1]
            return float(v.iloc[0]) if hasattr(v,"iloc") else float(v)
    except:
        return None

def sim_guncelle_ve_kaydet():
    """Tüm açık pozisyonların fiyatını çekip sim.json'u güncelle."""
    if not os.path.exists(SIM_DOSYA): return
    with open(SIM_DOSYA,"r",encoding="utf-8") as f:
        sim = json.load(f)

    degisti = False
    for kat in KATLAR:
        for poz in sim.get(kat,{}).get("acik",[]):
            cp = guncel_fiyat_cek(poz["ticker"])
            if cp is None: continue
            poz["guncel"] = round(cp, 6)
            yon = poz.get("yon","LONG")
            if yon == "SHORT":
                poz["kz_pct"] = (poz["giris"] - cp) / poz["giris"]
            else:
                poz["kz_pct"] = (cp - poz["giris"]) / poz["giris"]
            poz["kz_tl"] = round(poz["kz_pct"] * poz.get("yatirim", POS_TL), 2)

            # TP geçiş kontrol
            tp1 = poz.get("tp1"); tp2 = poz.get("tp2")
            if tp1 and not poz.get("tp1_gecildi"):
                if (yon=="LONG" and cp>=tp1) or (yon=="SHORT" and cp<=tp1):
                    poz["tp1_gecildi"] = True
            if tp2 and not poz.get("tp2_gecildi"):
                if (yon=="LONG" and cp>=tp2) or (yon=="SHORT" and cp<=tp2):
                    poz["tp2_gecildi"] = True

            # TP bazlı stop çekme
            if yon == "LONG":
                if tp2 and cp >= tp2 and tp1:
                    yeni = tp1
                    if not poz.get("stop") or yeni > poz["stop"]:
                        poz["stop"] = round(yeni,4)
                elif tp1 and cp >= tp1:
                    if not poz.get("stop") or poz["giris"] > poz["stop"]:
                        poz["stop"] = round(poz["giris"],4)
            degisti = True

    if degisti:
        with open(SIM_DOSYA,"w",encoding="utf-8") as f:
            json.dump(sim, f, ensure_ascii=False, indent=2)

# ── VERİ ──────────────────────────────────────────────

def yukle():
    if not os.path.exists(SIM_DOSYA): return {}
    with open(SIM_DOSYA,"r",encoding="utf-8") as f:
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
        "ort_kaz":(sum(p.get("kz_tl",0) for p in kaz)/len(kaz)) if kaz else 0,
        "ort_kay":(sum(p.get("kz_tl",0) for p in kay)/len(kay)) if kay else 0,
    }

def gun(ts):
    try: return (datetime.now()-datetime.strptime(ts,"%d.%m.%Y %H:%M")).days
    except: return 0

def tl(v):
    if v is None: return "—"
    return f"+{v:,.0f} ₺" if v>=0 else f"{v:,.0f} ₺"

def pct(v):
    if v is None: return "—"
    return f"+{v*100:.2f}%" if v>=0 else f"{v*100:.2f}%"

def rk(v): return "#10b981" if v>=0 else "#ef4444"

# ── PROGRESS BAR ──────────────────────────────────────

def pozisyon_progress(p):
    """
    Giriş fiyatı merkez.
    Sağ taraf: TP1→TP2→TP3 (yeşil)
    Sol taraf: Stop (kırmızı)
    Güncel fiyat hareketli nokta.
    """
    giris = p.get("giris",0)
    gunc  = p.get("guncel", giris)
    stop  = p.get("stop")
    tp1   = p.get("tp1")
    tp2   = p.get("tp2")
    tp3   = p.get("tp3")
    yon   = p.get("yon","LONG")
    tp1ok = p.get("tp1_gecildi",False)
    tp2ok = p.get("tp2_gecildi",False)
    kz_tl = p.get("kz_tl",0)

    if not giris: return

    # Referans aralık: stop ile tp3 arası (yoksa giriş±%15)
    sol = stop if stop else giris * (0.85 if yon=="LONG" else 1.15)
    sag = tp3  if tp3  else giris * (1.15 if yon=="LONG" else 0.85)
    aralik = abs(sag - sol)
    if aralik == 0: return

    # Pozisyon yüzdesi (0=stop, 50=giriş, 100=tp3)
    giris_pct = abs(giris - sol) / aralik * 100
    gunc_pct  = max(0, min(100, abs(gunc - sol) / aralik * 100))
    tp1_pct   = abs(tp1 - sol) / aralik * 100 if tp1 else None
    tp2_pct   = abs(tp2 - sol) / aralik * 100 if tp2 else None
    tp3_pct   = 100.0 if tp3 else None

    # Renk: karda yeşil, zararda kırmızı
    renk = "#10b981" if kz_tl >= 0 else "#ef4444"

    # Bar SVG
    w = 100  # yüzde cinsinden genişlik
    svg_items = []

    # Arka plan
    svg_items.append(f'<rect x="0" y="8" width="100%" height="6" rx="3" fill="#e2e8f0"/>')

    # Dolu kısım (giriş'ten güncel'e)
    if yon == "LONG":
        fill_x     = f"{min(giris_pct, gunc_pct):.1f}%"
        fill_width = f"{abs(gunc_pct - giris_pct):.1f}%"
    else:
        fill_x     = f"{min(gunc_pct, giris_pct):.1f}%"
        fill_width = f"{abs(giris_pct - gunc_pct):.1f}%"

    svg_items.append(f'<rect x="{fill_x}" y="8" width="{fill_width}" height="6" rx="3" fill="{renk}" opacity="0.7"/>')

    # Stop çizgisi (kırmızı dikey)
    if stop:
        stop_pct = abs(sol - sol) / aralik * 100  # = 0
        svg_items.append(f'<rect x="0%" y="4" width="3" height="14" rx="1" fill="#ef4444"/>')
        svg_items.append(f'<text x="2%" y="26" font-size="9" fill="#ef4444" font-family="JetBrains Mono">STP {stop:.2f}</text>')

    # Giriş noktası (gri dikey)
    svg_items.append(f'<rect x="{giris_pct:.1f}%" y="2" width="2" height="18" rx="1" fill="#94a3b8"/>')
    svg_items.append(f'<text x="{giris_pct:.1f}%" y="26" font-size="9" fill="#94a3b8" text-anchor="middle" font-family="JetBrains Mono">GİR</text>')

    # TP çizgileri
    for tp_pct, tp_val, tp_lbl, tp_ok in [
        (tp1_pct, tp1, "TP1", tp1ok),
        (tp2_pct, tp2, "TP2", tp2ok),
        (tp3_pct, tp3, "TP3", False),
    ]:
        if tp_pct is None or tp_val is None: continue
        c = "#10b981" if tp_ok else "#94a3b8"
        svg_items.append(f'<rect x="{tp_pct:.1f}%" y="4" width="2" height="14" rx="1" fill="{c}"/>')
        svg_items.append(f'<text x="{tp_pct:.1f}%" y="26" font-size="9" fill="{c}" text-anchor="middle" font-family="JetBrains Mono">{"✓" if tp_ok else ""}{tp_lbl}</text>')

    # Güncel fiyat noktası (dolu daire)
    svg_items.append(f'''
        <circle cx="{gunc_pct:.1f}%" cy="11" r="6" fill="{renk}" stroke="white" stroke-width="2"/>
        <text x="{gunc_pct:.1f}%" y="38" font-size="9" fill="{renk}" text-anchor="middle"
              font-family="JetBrains Mono" font-weight="bold">{gunc:.2f}</text>
    ''')

    svg_html = f'''
    <svg width="100%" height="44" style="overflow:visible;margin:12px 0 20px 0">
        {"".join(svg_items)}
    </svg>
    '''
    st.markdown(svg_html, unsafe_allow_html=True)

# ── POZİSYON KARTI ────────────────────────────────────

def poz_kart(p, ana_renk="#6366f1"):
    kz   = p.get("kz_tl",0)
    kz_p = p.get("kz_pct",0)
    yon  = p.get("yon","LONG")
    puan = p.get("puan")
    g    = gun(p.get("giris_tarih", p.get("tarih","")))
    renk = rk(kz)
    gunc = p.get("guncel", p.get("giris",0))

    # Başlık satırı
    c1, c2 = st.columns([4,1])
    with c1:
        badges = f"**{p['ticker']}**  "
        if puan: badges += f"`{puan}/100`  "
        badges += ("🟢 LONG" if yon=="LONG" else "🔴 SHORT") + f"  ·  {g}g"
        st.markdown(badges)
        st.caption(
            f"Giriş: `{p.get('giris',0):.4f}`  →  Şimdi: `{gunc:.4f}`"
            + (f"  ·  Stop: `{p.get('stop'):.4f}`" if p.get("stop") else "")
        )
    with c2:
        st.metric("", tl(kz), pct(kz_p))

    # Progress bar SVG
    pozisyon_progress(p)

    if p.get("notlar"):
        st.caption(f"📝 {p['notlar']}")
    st.markdown("<hr style='border:none;border-top:1px solid #f1f5f9;margin:4px 0 14px'>",
                unsafe_allow_html=True)

def kapali_kart(p):
    kz   = p.get("kz_tl",0)
    kz_p = p.get("kz_pct",0)
    neden = {"stop":"🛑 Stop","tp3":"🎯 TP3","trailing_stop":"🔀 İz Stop"}.get(
             p.get("durum", p.get("cikis_neden","")), "✅")
    renk = rk(kz)
    puan = p.get("puan")
    g    = gun(p.get("giris_tarih", p.get("tarih","")))

    c1, c2 = st.columns([4,1])
    with c1:
        badges = f"**{p['ticker']}**  {neden}"
        if puan: badges += f"  `{puan}/100`"
        st.markdown(badges)
        st.caption(
            f"{p.get('giris_tarih','—')} → {p.get('cikis_tarih','—')}  ·  {g}g"
        )
    with c2:
        st.metric("", tl(kz), pct(kz_p))
    st.markdown("<hr style='border:none;border-top:1px solid #f1f5f9;margin:4px 0 14px'>",
                unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📊 Trading Bot")
    veri = yukle()

    tum_acik  = sum(len(veri.get(k,{}).get("acik",[])) for k in KATLAR)
    tum_kap   = sum(len(veri.get(k,{}).get("kapali",[])) for k in KATLAR)
    top_kz    = sum(
        sum(p.get("kz_tl",0) for p in veri.get(k,{}).get("acik",[])+veri.get(k,{}).get("kapali",[]))
        for k in KATLAR)
    top_yat   = tum_acik * POS_TL
    guncel_but = POS_TL * (tum_acik + tum_kap) + top_kz

    renk_top = "#a7f3d0" if top_kz >= 0 else "#fca5a5"
    st.markdown(f"""
    <div style='background:rgba(255,255,255,0.15);border-radius:16px;padding:16px;margin:12px 0'>
        <div style='font-size:10px;opacity:0.7;text-transform:uppercase;letter-spacing:1px'>Toplam K/Z</div>
        <div style='font-family:JetBrains Mono;font-size:22px;font-weight:700;color:{renk_top};margin:4px 0'>{tl(top_kz)}</div>
        <div style='font-size:11px;opacity:0.6'>{tum_acik} açık · {tum_kap} kapandı</div>
    </div>
    """, unsafe_allow_html=True)

    secim = st.radio("", ["🏠 Genel", "📈 Performans"] +
                     [f"{v['emoji']} {v['isim']}" for v in KATLAR.values()],
                     label_visibility="collapsed")

    st.markdown("---")
    if st.button("🔄 Fiyatları Güncelle", use_container_width=True):
        with st.spinner("Fiyatlar çekiliyor..."):
            sim_guncelle_ve_kaydet()
        st.success("Güncellendi!")
        st.rerun()

    st.markdown(f"<div style='opacity:0.4;font-size:10px;margin-top:8px'>⏱ {datetime.now().strftime('%H:%M:%S')}</div>",
                unsafe_allow_html=True)

# ── GENEL BAKIŞ ───────────────────────────────────────

def genel(veri):
    st.markdown("## 🏠 Genel Bakış")

    tum_acik, tum_kap = [], []
    for k in KATLAR:
        tum_acik += veri.get(k,{}).get("acik",[])
        tum_kap  += veri.get(k,{}).get("kapali",[])
    s = ist(tum_acik, tum_kap)

    toplam_yatirilan = (s["acik"] + s["kapali"]) * POS_TL
    guncel_butce     = toplam_yatirilan + s["top_kz"]

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("💰 Toplam K/Z",      tl(s["top_kz"]))
    c2.metric("🏦 Giriş Bütçesi",   tl(toplam_yatirilan))
    c3.metric("📈 Güncel Bütçe",    tl(guncel_butce), tl(s["top_kz"]))
    c4.metric("🎯 Başarı",          f"%{s['basari']:.1f}", f"{s['kazanan']}✅ {s['kaybeden']}❌")
    c5.metric("📂 Açık",            s["acik"])
    c6.metric("✅ Kapanan",          s["kapali"])

    st.markdown("<br>", unsafe_allow_html=True)

    # Kategori kartları
    cols = st.columns(4)
    for i,(k,bilgi) in enumerate(KATLAR.items()):
        acik   = veri.get(k,{}).get("acik",[])
        kapali = veri.get(k,{}).get("kapali",[])
        s2     = ist(acik,kapali)
        renk   = rk(s2["top_kz"])
        with cols[i]:
            st.markdown(f"""
            <div style='background:white;border-radius:18px;padding:20px;text-align:center;
                        box-shadow:0 2px 10px rgba(0,0,0,0.06);border:1px solid #e8edf3'>
                <div style='font-size:30px'>{bilgi['emoji']}</div>
                <div style='font-weight:600;color:{bilgi['renk']};font-size:14px;margin:8px 0'>{bilgi['isim']}</div>
                <div style='font-family:JetBrains Mono;font-size:20px;font-weight:700;color:{renk}'>{tl(s2['top_kz'])}</div>
                <div style='font-size:12px;color:#94a3b8;margin-top:8px'>
                    %{s2['basari']:.0f} başarı &nbsp;·&nbsp; {s2['acik']} açık
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Grafikler
    st.markdown("---")
    g1, g2 = st.columns([3,2])

    with g1:
        st.markdown("### Kategori K/Z")
        isimler = [v["isim"] for v in KATLAR.values()]
        kzlar   = [ist(veri.get(k,{}).get("acik",[]),veri.get(k,{}).get("kapali",[])).get("top_kz",0) for k in KATLAR]
        renkler = [KATLAR[k]["renk"] for k in KATLAR]
        fig = go.Figure(go.Bar(
            x=isimler, y=kzlar,
            marker=dict(color=renkler, opacity=0.8, line=dict(width=0)),
            text=[tl(k) for k in kzlar], textposition="outside",
            textfont=dict(size=11, family="JetBrains Mono"),
        ))
        fig.update_layout(
            paper_bgcolor="white", plot_bgcolor="white",
            font=dict(color="#64748b", family="Outfit"),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9", zeroline=True, zerolinecolor="#e2e8f0", showticklabels=False),
            xaxis=dict(showgrid=False),
            margin=dict(t=20,b=10,l=10,r=10), height=260, showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    with g2:
        st.markdown("### Kazanan / Kaybeden")
        kaz_l, kay_l, ism_l = [], [], []
        for k,bilgi in KATLAR.items():
            s3 = ist(veri.get(k,{}).get("acik",[]),veri.get(k,{}).get("kapali",[]))
            if s3["kapali"]>0:
                kaz_l.append(s3["kazanan"]); kay_l.append(s3["kaybeden"])
                ism_l.append(bilgi["isim"])
        if kaz_l:
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(name="Kazanan", x=ism_l, y=kaz_l, marker_color="#34d399", opacity=0.85))
            fig2.add_trace(go.Bar(name="Kaybeden", x=ism_l, y=kay_l, marker_color="#f87171", opacity=0.85))
            fig2.update_layout(
                barmode="stack", paper_bgcolor="white", plot_bgcolor="white",
                font=dict(color="#64748b",family="Outfit"),
                yaxis=dict(showgrid=True,gridcolor="#f1f5f9"),
                xaxis=dict(showgrid=False),
                margin=dict(t=20,b=10,l=10,r=10), height=260,
                legend=dict(orientation="h",y=-0.25),
            )
            st.plotly_chart(fig2, use_container_width=True)

    # Açık pozisyonlar
    if any(veri.get(k,{}).get("acik",[]) for k in KATLAR):
        st.markdown("---")
        st.markdown("### 📂 Açık Pozisyonlar")
        for k,bilgi in KATLAR.items():
            pozlar = veri.get(k,{}).get("acik",[])
            if pozlar:
                st.markdown(f"**{bilgi['emoji']} {bilgi['isim']}**")
                for p in pozlar: poz_kart(p, bilgi["renk"])

# ── PERFORMANS SEKMESİ ────────────────────────────────

def performans(veri):
    st.markdown("## 📈 Performans Analizi")

    tum_acik, tum_kap = [], []
    for k in KATLAR:
        for p in veri.get(k,{}).get("acik",[]): tum_acik.append({**p,"kategori":k})
        for p in veri.get(k,{}).get("kapali",[]): tum_kap.append({**p,"kategori":k})

    s = ist(tum_acik, tum_kap)
    toplam_yat = (s["acik"]+s["kapali"]) * POS_TL
    guncel_but = toplam_yat + s["top_kz"]

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Başlangıç Bütçesi", tl(toplam_yat))
    c2.metric("Güncel Bütçe",      tl(guncel_but), tl(s["top_kz"]))
    c3.metric("Toplam Getiri",      pct(s["top_kz"]/toplam_yat if toplam_yat else 0))
    c4.metric("Başarı Oranı",       f"%{s['basari']:.1f}")

    st.markdown("---")

    # Bütçe gidişat grafiği
    if tum_kap:
        st.markdown("### 💰 Bütçe Gidişatı")
        siralı = sorted(tum_kap, key=lambda x: x.get("cikis_tarih","") or "")
        tarihler, kum, but_list = [], [], []
        toplam = toplam_yat
        for p in siralı:
            toplam += p.get("kz_tl",0)
            tarihler.append(p.get("cikis_tarih",""))
            kum.append(p.get("kz_tl",0))
            but_list.append(toplam)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=tarihler, y=but_list, mode="lines+markers",
            name="Bütçe",
            line=dict(color="#6366f1", width=3),
            marker=dict(size=6, color="#6366f1"),
            fill="tozeroy",
            fillcolor="rgba(99,102,241,0.08)",
        ))
        fig.add_hline(y=toplam_yat, line_dash="dash", line_color="#94a3b8",
                      annotation_text="Başlangıç", annotation_position="right")
        fig.update_layout(
            paper_bgcolor="white", plot_bgcolor="white",
            font=dict(color="#64748b", family="Outfit"),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
            xaxis=dict(showgrid=False),
            margin=dict(t=20,b=20,l=10,r=10), height=300,
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Kümülatif K/Z
    if tum_kap:
        st.markdown("### 📊 Kümülatif K/Z")
        siralı2 = sorted(tum_kap, key=lambda x: x.get("cikis_tarih","") or "")
        tarihler2, kum2 = [], []
        toplam2 = 0
        for p in siralı2:
            toplam2 += p.get("kz_tl",0)
            tarihler2.append(p.get("cikis_tarih",""))
            kum2.append(toplam2)

        renk_son = "#10b981" if (kum2[-1] if kum2 else 0) >= 0 else "#ef4444"
        fig3 = go.Figure(go.Scatter(
            x=tarihler2, y=kum2, mode="lines",
            fill="tozeroy",
            fillcolor=f"{'rgba(16,185,129,0.1)' if renk_son=='#10b981' else 'rgba(239,68,68,0.1)'}",
            line=dict(color=renk_son, width=2.5),
        ))
        fig3.update_layout(
            paper_bgcolor="white", plot_bgcolor="white",
            font=dict(color="#64748b",family="Outfit"),
            yaxis=dict(showgrid=True,gridcolor="#f1f5f9",zeroline=True,zerolinecolor="#e2e8f0"),
            xaxis=dict(showgrid=False),
            margin=dict(t=20,b=20,l=10,r=10), height=260, showlegend=False,
        )
        st.plotly_chart(fig3, use_container_width=True)

    # Puan bazlı analiz
    st.markdown("### 🎯 Puan Bazlı Performans")
    gruplar = {"65-69":[],"70-79":[],"80-89":[],"90-99":[],"100":[]}
    for p in tum_acik+tum_kap:
        puan = p.get("puan",0)
        if   puan>=100: gruplar["100"].append(p)
        elif puan>=90:  gruplar["90-99"].append(p)
        elif puan>=80:  gruplar["80-89"].append(p)
        elif puan>=70:  gruplar["70-79"].append(p)
        else:           gruplar["65-69"].append(p)

    rows = []
    for aralik, pozlar in gruplar.items():
        if not pozlar: continue
        kap_poz = [p for p in pozlar if p.get("durum","acik")!="acik"]
        kaz     = [p for p in kap_poz if p.get("kz_tl",0)>0]
        rows.append({
            "Puan":         aralik,
            "İşlem":        len(pozlar),
            "Kapanan":      len(kap_poz),
            "Başarı":       f"%{len(kaz)/len(kap_poz)*100:.0f}" if kap_poz else "—",
            "Toplam K/Z":   tl(sum(p.get("kz_tl",0) for p in pozlar)),
            "Ort. K/Z":     tl(sum(p.get("kz_tl",0) for p in pozlar)/len(pozlar)),
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.info("Puan verisi henüz yok")

# ── KATEGORİ DETAY ────────────────────────────────────

def detay(kat_key, veri):
    bilgi  = KATLAR[kat_key]
    acik   = veri.get(kat_key,{}).get("acik",[])
    kapali = veri.get(kat_key,{}).get("kapali",[])
    s      = ist(acik, kapali)

    st.markdown(f"## {bilgi['emoji']} {bilgi['isim']}")

    toplam_yat = (s["acik"]+s["kapali"]) * POS_TL
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Toplam K/Z",   tl(s["top_kz"]))
    c2.metric("Başarı",        f"%{s['basari']:.1f}")
    c3.metric("Giriş Bütçesi", tl(toplam_yat))
    c4.metric("Kazanan",       s["kazanan"])
    c5.metric("Kaybeden",      s["kaybeden"])

    tab1, tab2 = st.tabs(["📂 Açık Pozisyonlar", "✅ Kapananlar"])

    with tab1:
        if acik:
            for p in acik: poz_kart(p, bilgi["renk"])
        else:
            st.info("Açık pozisyon yok")

    with tab2:
        if kapali:
            filtre = st.selectbox("", ["Tümü","Kazananlar","Kaybedenler"], label_visibility="collapsed")
            liste  = kapali
            if filtre=="Kazananlar":  liste=[p for p in kapali if p.get("kz_tl",0)>0]
            if filtre=="Kaybedenler": liste=[p for p in kapali if p.get("kz_tl",0)<=0]
            for p in reversed(liste[-30:]): kapali_kart(p)
        else:
            st.info("Kapanan işlem yok")

# ── ROUTING ───────────────────────────────────────────

veri = yukle()

if secim == "🏠 Genel":
    genel(veri)
elif secim == "📈 Performans":
    performans(veri)
else:
    for k, bilgi in KATLAR.items():
        if f"{bilgi['emoji']} {bilgi['isim']}" == secim:
            detay(k, veri)
            break
