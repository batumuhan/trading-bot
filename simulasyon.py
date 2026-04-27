"""
simulasyon.py — Ortak simülasyon motoru

Her modül (bist_trade, kripto, altin_gumus, bist_temel) bu modülü kullanır.
Her kategori ayrı takip edilir. 10.000 TL sabit pozisyon.
"""

import json
import os
import logging
from utils import simdi, sf, para, yuzde, em, yf_fiyat, binance_fiyat
from config import SIM_POZISYON_TL

log = logging.getLogger(__name__)

DOSYA = "sim.json"

KATEGORILER = ["bist_trade", "bist_temel", "kripto", "metal"]


# ── YÜKLEME / KAYDETME ────────────────────────────────

def yukle() -> dict:
    if os.path.exists(DOSYA):
        with open(DOSYA, "r", encoding="utf-8") as f:
            return json.load(f)
    return {k: {"acik": [], "kapali": []} for k in KATEGORILER}

def kaydet(sim: dict):
    with open(DOSYA, "w", encoding="utf-8") as f:
        json.dump(sim, f, ensure_ascii=False, indent=2)


# ── POZİSYON AÇ ───────────────────────────────────────

def pozisyon_ac(
    kategori:   str,
    ticker:     str,
    fiyat:      float,
    yon:        str = "LONG",    # LONG veya SHORT
    stop:       float = None,
    tp1:        float = None,
    tp2:        float = None,
    tp3:        float = None,
    trailing:   float = None,    # iz süren stop yüzdesi (örn: 0.05)
    kaldirac:   float = 1.0,
    puan:       int   = 0,       # sinyal puanı (0-100)
    notlar:     str   = "",
):
    sim = yukle()
    if kategori not in sim:
        sim[kategori] = {"acik": [], "kapali": []}

    # Aynı ticker zaten açıksa girme
    if any(p["ticker"] == ticker for p in sim[kategori]["acik"]):
        log.info(f"[{kategori}] {ticker} zaten açık, atlandı")
        return False

    tutar = SIM_POZISYON_TL
    adet  = tutar / fiyat

    poz = {
        "ticker":        ticker,
        "yon":           yon,
        "giris":         round(fiyat, 6),
        "tutar":         tutar,
        "adet":          round(adet, 6),
        "kaldirac":      kaldirac,
        "giris_tarih":   simdi(),
        "stop":          round(stop, 6) if stop else None,
        "tp1":           round(tp1, 6)  if tp1  else None,
        "tp2":           round(tp2, 6)  if tp2  else None,
        "tp3":           round(tp3, 6)  if tp3  else None,
        "tp1_gecildi":   False,
        "tp2_gecildi":   False,
        "trailing_pct":  trailing,
        "trailing_stop": None,     # dinamik olarak güncellenir
        "guncel":        round(fiyat, 6),
        "kz_tl":         0.0,
        "kz_pct":        0.0,
        "puan":          puan,
        "notlar":        notlar,
        "durum":         "acik",
        "cikis":         None,
        "cikis_tarih":   None,
        "cikis_neden":   None,
    }

    sim[kategori]["acik"].append(poz)
    kaydet(sim)
    log.info(f"[{kategori}] {yon} açıldı: {ticker} @ {fiyat:.4f}")
    return True


# ── FİYAT GÜNCELLE ────────────────────────────────────

def _guncel_fiyat(poz: dict) -> float | None:
    """Pozisyon için güncel fiyatı çek."""
    ticker = poz["ticker"]
    # Kripto ise Binance'den çek
    if poz.get("notlar","").startswith("kripto") or "USDT" in ticker:
        return binance_fiyat(ticker)
    # Metal veya BIST ise yfinance
    sembol = ticker if ("." in ticker or "=F" in ticker) else ticker + ".IS"
    return yf_fiyat(sembol)

def _kz_hesapla(poz: dict, cp: float) -> tuple[float, float]:
    """K/Z hesapla. LONG ve SHORT için farklı formül."""
    giris = poz["giris"]
    kaldirac = poz.get("kaldirac", 1.0)
    if poz["yon"] == "SHORT":
        pct = (giris - cp) / giris * kaldirac
    else:
        pct = (cp - giris) / giris * kaldirac
    tl = pct * poz["tutar"]
    return round(pct, 6), round(tl, 2)

def _trailing_guncelle(poz: dict, cp: float) -> float | None:
    """İz süren stop güncelle — Kripto için."""
    pct = poz.get("trailing_pct")
    if not pct:
        return None
    yon = poz["yon"]
    ts  = poz.get("trailing_stop")
    if yon == "LONG":
        yeni = cp * (1 - pct)
        if ts is None or yeni > ts:
            return round(yeni, 6)
    else:
        yeni = cp * (1 + pct)
        if ts is None or yeni < ts:
            return round(yeni, 6)
    return ts

def _tp_stop_guncelle(poz: dict, cp: float):
    """
    TP geçince stop yukarı çek (LONG için):
      TP1 geçildi → stop = giriş fiyatı (başa baş)
      TP2 geçildi → stop = TP1 seviyesi
    Kaynak: Brooks — pozisyon lehine gidince riski sıfırla.
    """
    if poz["yon"] != "LONG":
        return
    giris = poz["giris"]
    tp1   = poz.get("tp1")
    tp2   = poz.get("tp2")
    stop  = poz.get("stop", 0) or 0

    if tp2 and cp >= tp2 and tp1:
        # TP2 geçildi → stop TP1'e çek
        if tp1 > stop:
            poz["stop"] = round(tp1, 4)
            poz["stop_neden"] = f"TP2 geçildi → stop TP1'e ({tp1:.4f})"
    elif tp1 and cp >= tp1:
        # TP1 geçildi → stop başa baş
        if giris > stop:
            poz["stop"] = round(giris, 4)
            poz["stop_neden"] = f"TP1 geçildi → stop başa baş ({giris:.4f})"

def _kapat_mi(poz: dict, cp: float) -> str | None:
    """
    Pozisyon kapatılacak mı? Kapatılacaksa nedeni döner.
    Önce TP bazlı stop güncellenir, sonra kontrol yapılır.
    Neden: 'stop', 'trailing_stop', 'tp3'
    """
    # TP bazlı stop güncelle
    _tp_stop_guncelle(poz, cp)

    yon  = poz["yon"]
    stop = poz.get("stop")
    ts   = poz.get("trailing_stop")
    tp3  = poz.get("tp3")

    if yon == "LONG":
        if ts   and cp <= ts:   return "trailing_stop"
        if stop and cp <= stop: return "stop"
        if tp3  and cp >= tp3:  return "tp3"
    else:  # SHORT
        if ts   and cp >= ts:   return "trailing_stop"
        if stop and cp >= stop: return "stop"
        if tp3  and cp <= tp3:  return "tp3"
    return None


# ── GÜNCELLEME ────────────────────────────────────────

def guncelle(kategori: str = None) -> dict:
    """
    Açık pozisyonları güncelle.
    kategori=None ise tüm kategoriler güncellenir.
    Döner: {kategori: [kapanan_pozisyonlar]}
    """
    sim = yukle()
    kapananlar = {k: [] for k in KATEGORILER}

    for k in KATEGORILER:
        if kategori and k != kategori:
            continue
        acik_kalanlar = []
        for poz in sim[k]["acik"]:
            cp = _guncel_fiyat(poz)
            if cp is None:
                acik_kalanlar.append(poz)
                continue

            # K/Z güncelle
            poz["guncel"] = round(cp, 6)
            poz["kz_pct"], poz["kz_tl"] = _kz_hesapla(poz, cp)

            # TP geçiş işaretleri
            yon = poz["yon"]
            if poz.get("tp1") and not poz["tp1_gecildi"]:
                if (yon=="LONG" and cp >= poz["tp1"]) or (yon=="SHORT" and cp <= poz["tp1"]):
                    poz["tp1_gecildi"] = True
            if poz.get("tp2") and not poz["tp2_gecildi"]:
                if (yon=="LONG" and cp >= poz["tp2"]) or (yon=="SHORT" and cp <= poz["tp2"]):
                    poz["tp2_gecildi"] = True

            # İz süren stop güncelle
            yeni_ts = _trailing_guncelle(poz, cp)
            if yeni_ts:
                poz["trailing_stop"] = yeni_ts

            # Kapat mı?
            neden = _kapat_mi(poz, cp)
            if neden:
                poz["durum"]       = neden
                poz["cikis"]       = round(cp, 6)
                poz["cikis_tarih"] = simdi()
                poz["cikis_neden"] = neden
                kapananlar[k].append(poz)
                sim[k]["kapali"].append(poz)
                log.info(f"[{k}] {poz['ticker']} kapandı: {neden} @ {cp:.4f}")
            else:
                acik_kalanlar.append(poz)

        sim[k]["acik"] = acik_kalanlar

    kaydet(sim)
    return kapananlar


# ── İSTATİSTİK ────────────────────────────────────────

def istatistik(kategori: str) -> dict:
    sim = yukle()
    if kategori not in sim:
        return {}
    acik   = sim[kategori]["acik"]
    kapali = sim[kategori]["kapali"]

    kazanan  = [p for p in kapali if p["kz_tl"] > 0]
    kaybeden = [p for p in kapali if p["kz_tl"] <= 0]
    basari   = (len(kazanan) / len(kapali) * 100) if kapali else 0.0

    return {
        "acik_sayi":    len(acik),
        "kapali_sayi":  len(kapali),
        "kazanan":      len(kazanan),
        "kaybeden":     len(kaybeden),
        "basari_pct":   basari,
        "acik_kz":      sum(p["kz_tl"] for p in acik),
        "kapali_kz":    sum(p["kz_tl"] for p in kapali),
        "toplam_kz":    sum(p["kz_tl"] for p in acik) + sum(p["kz_tl"] for p in kapali),
        "ort_kazanc":   (sum(p["kz_tl"] for p in kazanan) / len(kazanan)) if kazanan else 0,
        "ort_kayip":    (sum(p["kz_tl"] for p in kaybeden) / len(kaybeden)) if kaybeden else 0,
        "acik_pozlar":  acik,
        "son_kapananlar": kapali[-5:],
    }


# ── RAPOR MESAJI ──────────────────────────────────────

def rapor_mesaji(kategori: str, baslik: str, emoji: str) -> str:
    ist = istatistik(kategori)
    if not ist:
        return f"{emoji} <b>{baslik}</b>\nVeri yok."

    tp_cubugu = lambda p: (
        ("✅" if p.get("tp1_gecildi") else "⬜") +
        "TP1 " +
        ("✅" if p.get("tp2_gecildi") else "⬜") +
        "TP2 " +
        "⬜TP3"
    )

    satirlar = [
        f"{emoji} <b>{baslik} SİMÜLASYON RAPORU</b>\n",
        f"💰 Toplam K/Z: <b>{para(ist['toplam_kz'])}</b>",
        f"   Açık: {para(ist['acik_kz'])}  |  Kapalı: {para(ist['kapali_kz'])}",
        f"📊 {ist['kapali_sayi']} işlem kapandı  /  {ist['acik_sayi']} açık",
        f"   Başarı: <b>%{ist['basari_pct']:.1f}</b>  ({ist['kazanan']}✅  {ist['kaybeden']}❌)",
        f"   Ort. Kazanç: {para(ist['ort_kazanc'])}",
        f"   Ort. Kayıp: {para(ist['ort_kayip'])}",
    ]

    # Açık pozisyonlar
    if ist["acik_pozlar"]:
        satirlar.append(f"\n📂 <b>Açık Pozisyonlar ({ist['acik_sayi']}):</b>")
        for p in ist["acik_pozlar"]:
            yon_em = "⬆️" if p["yon"]=="LONG" else "⬇️"
            kz_em  = em(p["kz_tl"])
            st     = p.get("trailing_stop") or p.get("stop") or 0
            stop_neden = p.get("stop_neden", "")
            stop_label = f"✅ {stop_neden}" if stop_neden else f"🔴 Stop: {st:.4f}"
            puan_label = f"Puan: {p.get('puan', 0)}/100" if p.get('puan') else ""
            satirlar.append(
                f"  {kz_em}{yon_em} <b>{p['ticker']}</b>"
                + (f" | {puan_label}" if puan_label else "") + "\n"
                f"     Giriş: {p['giris']:.4f}  →  Şimdi: {p['guncel']:.4f}\n"
                f"     K/Z: {yuzde(p['kz_pct'])} ({para(p['kz_tl'])})\n"
                f"     {tp_cubugu(p)}\n"
                f"     {stop_label}\n"
                f"     📅 {p['giris_tarih']}"
            )

    # Son kapanan işlemler
    if ist["son_kapananlar"]:
        satirlar.append(f"\n✅ <b>Son 5 Kapanan:</b>")
        neden_lbl = {
            "stop":         "🛑 STOP",
            "trailing_stop":"🔀 İZ STOP",
            "tp3":          "🎯 TP3",
        }
        for p in reversed(ist["son_kapananlar"]):
            kz_em = em(p["kz_tl"])
            lbl   = neden_lbl.get(p.get("cikis_neden",""), "✅ KAPANDI")
            yon_em = "⬆️" if p["yon"]=="LONG" else "⬇️"
            satirlar.append(
                f"  {kz_em}{yon_em} {p['ticker']} [{lbl}]\n"
                f"     {yuzde(p['kz_pct'])} ({para(p['kz_tl'])})\n"
                f"     {p['giris_tarih']} → {p.get('cikis_tarih','—')}"
            )

    return "\n".join(satirlar)

def uyari_mesaji(kategori: str, poz: dict) -> str:
    """Stop/TP tetiklenince gönderilecek uyarı."""
    neden = poz.get("cikis_neden","")
    yon_em = "⬆️" if poz["yon"]=="LONG" else "⬇️"
    kz_em  = em(poz["kz_tl"])
    icons  = {"stop":"🛑","trailing_stop":"🔀","tp3":"🎯"}
    lbls   = {"stop":"STOP LOSS","trailing_stop":"İZ SÜREN STOP","tp3":"TP3 ULAŞILDI"}
    return (
        f"{icons.get(neden,'✅')} <b>[{kategori.upper()}] {lbls.get(neden,'KAPANDI')}</b>\n"
        f"{kz_em}{yon_em} {poz['ticker']}\n"
        f"Giriş: {poz['giris']:.4f}  →  Çıkış: {poz['cikis']:.4f}\n"
        f"K/Z: {yuzde(poz['kz_pct'])} ({para(poz['kz_tl'])})\n"
        f"📅 {poz['giris_tarih']} → {poz.get('cikis_tarih','—')}"
    )


# ── AYLIK ÖZET RAPORU ─────────────────────────────────

def aylik_ozet(kategori: str) -> str:
    """
    Puan aralığına göre performans analizi.
    Hangi puan grubu daha karlı?

    Örnek çıktı:
      70-79 puan: 4 işlem, %62.5 başarı, ort. +450 TL
      80-89 puan: 2 işlem, %100 başarı, ort. +820 TL
      100 puan:   1 işlem, %100 başarı, ort. +1240 TL
    """
    sim = yukle()
    if kategori not in sim:
        return "Veri yok."

    kapali = sim[kategori]["kapali"]
    acik   = sim[kategori]["acik"]
    tumu   = kapali + acik

    if not tumu:
        return f"📊 {kategori} — Henüz işlem yok."

    # Puan gruplarına ayır
    gruplar = {
        "65-69": [],
        "70-79": [],
        "80-89": [],
        "90-99": [],
        "100":   [],
    }

    for p in tumu:
        puan = p.get("puan", 0)
        if puan >= 100:
            gruplar["100"].append(p)
        elif puan >= 90:
            gruplar["90-99"].append(p)
        elif puan >= 80:
            gruplar["80-89"].append(p)
        elif puan >= 70:
            gruplar["70-79"].append(p)
        else:
            gruplar["65-69"].append(p)

    satirlar = [
        f"📊 <b>AYLIK ÖZET — {kategori.upper()}</b>\n",
        f"Toplam işlem: {len(tumu)} ({len(kapali)} kapandı / {len(acik)} açık)\n",
        "<b>Puan Aralığına Göre Performans:</b>",
    ]

    for aralik, pozlar in gruplar.items():
        if not pozlar:
            continue

        kapanan_poz = [p for p in pozlar if p["durum"] != "acik"]
        acik_poz    = [p for p in pozlar if p["durum"] == "acik"]
        kazanan     = [p for p in kapanan_poz if p["kz_tl"] > 0]
        kaybeden    = [p for p in kapanan_poz if p["kz_tl"] <= 0]
        basari      = (len(kazanan) / len(kapanan_poz) * 100) if kapanan_poz else 0
        ort_kz      = (sum(p["kz_tl"] for p in pozlar) / len(pozlar)) if pozlar else 0
        toplam_kz   = sum(p["kz_tl"] for p in pozlar)

        em_ort = "🟢" if ort_kz >= 0 else "🔴"

        satirlar.append(
            f"\n<b>{aralik} puan</b> — {len(pozlar)} işlem"
            + (f" ({len(acik_poz)} açık)" if acik_poz else "") + "\n"
            f"  Başarı: %{basari:.1f} ({len(kazanan)}✅ {len(kaybeden)}❌)\n"
            f"  Ort. K/Z: {em_ort} {para(ort_kz)}\n"
            f"  Toplam: {em_ort} {para(toplam_kz)}"
        )

    # Genel toplam
    toplam = sum(p["kz_tl"] for p in tumu)
    em_top = "🟢" if toplam >= 0 else "🔴"
    satirlar.append(f"\n━━━━━━━━━━━━━━━━━━━━")
    satirlar.append(f"Genel Toplam: {em_top} <b>{para(toplam)}</b>")

    return "\n".join(satirlar)


def ozet_kaydet(kategori: str, dosya_adi: str = None):
    """Özet raporu hem Telegram'a gönder hem dosyaya kaydet."""
    from telegram_bot import gonder
    from datetime import datetime

    rapor = aylik_ozet(kategori)
    gonder(rapor)

    if dosya_adi is None:
        dosya_adi = f"ozet_{kategori}_{datetime.now().strftime('%Y%m')}.txt"

    # HTML taglarını temizle
    import re
    temiz = re.sub(r'<[^>]+>', '', rapor)

    with open(dosya_adi, 'w', encoding='utf-8') as f:
        f.write(temiz)

    print(f"✅ Özet kaydedildi: {dosya_adi}")
    return dosya_adi
