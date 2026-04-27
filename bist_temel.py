"""
bist_temel.py — BIST Orta-Uzun Vade Temel Analiz

Tek başına çalışır: python bist_temel.py
Çalışma sıklığı: 6 ayda bir (bilanço dönemlerinde)

İki aşamalı sistem:
1. TARAMA (6 ayda bir): Tüm BIST hisselerini bilanço kriterlerine göre tara
   → En iyi 5-10 hisse seçilir, seçilen_hisseler.json'a kaydedilir

2. TAKİP (her sabah): Sadece seçilen hisselerin
   → Güncel fiyat ve kar/zarar durumu
   → KAP bildirimleri (yeni haber var mı?)
   → Telegram bildirimi

Metodoloji:
- F/K, PD/DD, ROE, büyüme (yfinance)
- KAP haberleri (kap.org.tr)
- Stop yok — uzun vade, yüksek getiri hedefi (min %25)
"""

import json
import os
import time
import logging
import sys
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import BIST_HISSELER, BIST_TEMEL, SIM_POZISYON_TL
from utils import sf, simdi, para, yuzde, em, yf_ohlcv, yf_fiyat
from simulasyon import pozisyon_ac, guncelle, rapor_mesaji, uyari_mesaji
from telegram_bot import gonder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bist_temel.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

KATEGORI       = "bist_temel"
SECILEN_DOSYA  = "secilen_hisseler.json"


# ── TEMEL ANALİZ ──────────────────────────────────────

def _hedef_hesapla(fiyat, fk, eps, pddd, bvps, kar_buyume, analist_hedef) -> float | None:
    """
    Kendi hedef fiyat modelimiz.

    3 yöntem birleştirilir, ağırlıklı ortalama alınır:
    1. F/K bazlı    — makul F/K × EPS
    2. PD/DD bazlı  — makul PD/DD × defter değeri/hisse
    3. Analist hedef — varsa ve mantıklıysa kısmen dahil edilir

    Analist hedefi %50'den fazla yüksekse indirgenmiş değer kullanılır.
    """
    tahminler = []
    agirliklar = []

    # 1. F/K bazlı hedef
    if fk and eps and eps > 0 and fiyat and fiyat > 0:
        # Makul F/K: mevcut F/K ile 12 arasının ortalaması (piyasa F/K ~10-12)
        makul_fk = (fk + 12) / 2
        makul_fk = min(makul_fk, 15)   # max 15 F/K
        hedef_fk = makul_fk * eps
        if hedef_fk > fiyat * 0.9:     # En az mevcut fiyata yakın olmalı
            tahminler.append(hedef_fk)
            agirliklar.append(0.4)

    # 2. PD/DD bazlı hedef
    if pddd and bvps and bvps > 0 and fiyat and fiyat > 0:
        # Makul PD/DD: mevcut ile 1.5 arasının ortalaması
        makul_pddd = min((pddd + 1.5) / 2, 2.0)
        hedef_pddd = makul_pddd * bvps
        if hedef_pddd > fiyat * 0.9:
            tahminler.append(hedef_pddd)
            agirliklar.append(0.35)

    # 3. Analist hedefi — varsa ve mantıklıysa
    if analist_hedef and fiyat and fiyat > 0:
        analist_pot = (analist_hedef - fiyat) / fiyat
        if analist_pot > 0.5:
            # %50'den fazla yüksekse — muhafazakâr tut, %30 ile sınırla
            analist_hedef = fiyat * 1.30
        elif analist_pot < 0:
            # Aşağı yönlü analist tahmini — dikkate alma
            analist_hedef = None

        if analist_hedef:
            tahminler.append(analist_hedef)
            agirliklar.append(0.25)

    if not tahminler:
        # Hiç veri yoksa büyüme bazlı basit tahmin
        if kar_buyume and fiyat and kar_buyume > 0:
            return round(fiyat * (1 + min(kar_buyume, 0.40)), 2)
        return None

    # Ağırlıklı ortalama
    toplam_agirlik = sum(agirliklar)
    if toplam_agirlik == 0:
        return None

    hedef = sum(t * a for t, a in zip(tahminler, agirliklar)) / toplam_agirlik

    # Son kontrol: mevcut fiyattan en az %5 yukarıda olmalı
    if hedef <= fiyat * 1.05:
        return None

    return round(hedef, 2)



def temel_analiz(ticker: str) -> dict | None:
    """
    Bir hisse için temel analiz yap.
    Puan eşiğini geçenleri döndür.

    Puanlama (toplam 100):
      F/K < 15         → 20 puan
      PD/DD < 2.5      → 15 puan
      ROE > %15        → 20 puan
      Kar büyümesi>%10 → 20 puan
      Borç/ÖK < 1      → 15 puan
      Getiri pot. >%25 → 10 puan
    """
    try:
        import yfinance as yf
        tk   = yf.Ticker(ticker + ".IS")
        info = tk.info
        if not info or not info.get("regularMarketPrice"):
            return None

        # Net kar büyümesi
        kar_buyume = None
        try:
            fin = tk.financials
            if fin is not None and not fin.empty and "Net Income" in fin.index:
                ni = fin.loc["Net Income"].dropna()
                if len(ni) >= 2 and ni.iloc[1] != 0:
                    kar_buyume = float((ni.iloc[0] - ni.iloc[1]) / abs(ni.iloc[1]))
        except: pass
        if kar_buyume is None:
            kar_buyume = sf(info.get("earningsGrowth"))

        fiyat  = sf(info.get("currentPrice") or info.get("regularMarketPrice"))
        fk     = sf(info.get("trailingPE"))
        eps    = sf(info.get("trailingEps"))
        pddd   = sf(info.get("priceToBook"))
        bvps   = sf(info.get("bookValue"))

        # Hedef fiyat hesapla
        analist_hedef = sf(info.get("targetMeanPrice"))
        hedef = _hedef_hesapla(fiyat, fk, eps, pddd, bvps, kar_buyume, analist_hedef)
        pddd   = sf(info.get("priceToBook"))
        roe    = sf(info.get("returnOnEquity"))
        bo_r   = sf(info.get("debtToEquity"))
        bo     = (bo_r / 100) if bo_r is not None else None
        pot    = ((hedef - fiyat) / fiyat) if (hedef and fiyat and fiyat > 0) else None
        mcap   = sf(info.get("marketCap"))
        sektor = info.get("sector", "—")
        isim   = info.get("longName", ticker)

        puan = 0
        detay = []

        def kontrol(deger, kosul, pt, etiket, yuzde_goster=False):
            nonlocal puan
            v = sf(deger)
            if v is None:
                detay.append(f"⚠️ {etiket}: veri yok")
                return
            goster = f"%{v*100:.1f}" if yuzde_goster else f"{v:.2f}"
            if kosul(v):
                puan += pt
                detay.append(f"✅ {etiket}: {goster}")
            else:
                detay.append(f"❌ {etiket}: {goster}")

        kontrol(fk,         lambda v: v < BIST_TEMEL["max_fk"],          20, "F/K")
        kontrol(pddd,       lambda v: v < BIST_TEMEL["max_pddd"],         15, "PD/DD")
        kontrol(roe,        lambda v: v >= BIST_TEMEL["min_roe"],          20, "ROE", True)
        kontrol(kar_buyume, lambda v: v >= BIST_TEMEL["min_kar_buyume"],   20, "Kar büyümesi", True)
        kontrol(bo,         lambda v: v < BIST_TEMEL["max_borc_ok"],       15, "Borç/ÖK")
        kontrol(pot,        lambda v: v >= BIST_TEMEL["min_getiri_pot"],   10, "Getiri pot.", True)

        if puan < 50:  # minimum 50 puan
            return None

        return {
            "ticker":     ticker,
            "isim":       isim,
            "sektor":     sektor,
            "fiyat":      fiyat,
            "hedef":      hedef,
            "potansiyel": pot,
            "fk":         fk,
            "pddd":       pddd,
            "roe":        roe,
            "kar_buyume": kar_buyume,
            "bo":         bo,
            "mcap":       mcap,
            "puan":       puan,
            "detay":      detay,
            "tarama_tarihi": simdi(),
        }

    except Exception as e:
        log.error(f"Temel analiz hatası [{ticker}]: {e}")
        return None


# ── KAP HABERLERİ ─────────────────────────────────────

def kap_haberleri(ticker: str, gun: int = 1) -> list[dict]:
    """
    KAP'tan son N günün bildirimlerini çek.
    kap.org.tr'nin açık API'sini kullanır.
    """
    haberler = []
    try:
        # KAP bildirim sorgu URL'i
        url = f"https://www.kap.org.tr/tr/api/memberNotification/{ticker}"
        r   = requests.get(url, timeout=10,
                          headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []

        veriler = r.json()
        if not veriler:
            return []

        # Son N günün haberlerini filtrele
        sinir = datetime.now() - timedelta(days=gun)

        for item in veriler[:20]:  # Son 20 bildirimi kontrol et
            try:
                tarih_str = item.get("publishDate") or item.get("date", "")
                if not tarih_str:
                    continue
                # Tarih parse
                tarih = datetime.fromisoformat(tarih_str.replace("Z",""))
                if tarih < sinir:
                    continue

                baslik  = item.get("title","") or item.get("subject","")
                tur     = item.get("type","") or item.get("notificationType","")
                link    = f"https://www.kap.org.tr/tr/Bildirim/{item.get('id','')}"

                # Önemli bildirimleri işaretle
                onemli = any(k in baslik.lower() for k in [
                    "kar", "zarar", "bilanço", "temettü", "sermaye",
                    "yönetim", "önemli", "acil", "birleşme", "satın",
                    "ihraç", "halka arz", "bedelsiz", "bedelli"
                ])

                haberler.append({
                    "tarih":   tarih.strftime("%d.%m.%Y %H:%M"),
                    "baslik":  baslik,
                    "tur":     tur,
                    "link":    link,
                    "onemli":  onemli,
                })
            except:
                continue

    except Exception as e:
        log.error(f"KAP haber hatası [{ticker}]: {e}")

    return haberler


def kap_haberleri_alternatif(ticker: str, gun: int = 1) -> list[dict]:
    """
    KAP API çalışmazsa alternatif — KAP web scraping.
    """
    haberler = []
    try:
        url = f"https://www.kap.org.tr/tr/sirket-bilgileri/bildirimleri/{ticker}"
        r   = requests.get(url, timeout=10,
                          headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []

        soup = BeautifulSoup(r.text, "html.parser")
        sinir = datetime.now() - timedelta(days=gun)

        for row in soup.select("tr.w-clearfix")[:10]:
            try:
                tarih_el  = row.select_one(".w-col-3")
                baslik_el = row.select_one(".w-col-9 a")
                if not tarih_el or not baslik_el:
                    continue

                tarih_str = tarih_el.get_text(strip=True)
                baslik    = baslik_el.get_text(strip=True)
                link      = "https://www.kap.org.tr" + baslik_el.get("href","")

                onemli = any(k in baslik.lower() for k in [
                    "kar", "zarar", "bilanço", "temettü", "sermaye",
                    "önemli", "acil", "birleşme", "satın"
                ])

                haberler.append({
                    "tarih":  tarih_str,
                    "baslik": baslik,
                    "link":   link,
                    "onemli": onemli,
                })
            except:
                continue

    except Exception as e:
        log.error(f"KAP scraping hatası [{ticker}]: {e}")

    return haberler


# ── SEÇİLEN HİSSELER ──────────────────────────────────

def secilen_yukle() -> list[dict]:
    if os.path.exists(SECILEN_DOSYA):
        with open(SECILEN_DOSYA, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def secilen_kaydet(hisseler: list[dict]):
    with open(SECILEN_DOSYA, "w", encoding="utf-8") as f:
        json.dump(hisseler, f, ensure_ascii=False, indent=2)


# ── TARAMA (6 AYDA BİR) ───────────────────────────────

def tam_tarama() -> list[dict]:
    """
    Tüm BIST hisselerini tara, en iyi N hisseyi seç.
    Bu işlem 30-40 dakika sürer — 6 ayda bir çalıştır.
    """
    log.info(f"Temel analiz tam taraması — {len(BIST_HISSELER)} hisse...")
    gonder("🔍 <b>BIST Temel Analiz Taraması Başladı</b>\n"
           f"📊 {len(BIST_HISSELER)} hisse taranıyor...\n"
           "⏳ Bu işlem 30-40 dakika sürebilir.")

    sonuclar = []
    for i, ticker in enumerate(BIST_HISSELER, 1):
        r = temel_analiz(ticker)
        if r:
            sonuclar.append(r)
            log.info(f"  ✅ {ticker} — Puan: {r['puan']}/100 | Getiri: {yuzde(r.get('potansiyel'))}")
        if i % 50 == 0:
            log.info(f"  [{i}/{len(BIST_HISSELER)}] tarandı...")
        time.sleep(0.5)

    # Puana göre sırala, en iyi N'i seç
    sonuclar.sort(key=lambda x: x["puan"], reverse=True)
    secilen = sonuclar[:BIST_TEMEL["max_secim"]]

    # Kaydet
    secilen_kaydet(secilen)
    log.info(f"Tarama bitti — {len(secilen)} hisse seçildi")
    return secilen


# ── GÜNLÜK TAKİP ──────────────────────────────────────

def gunluk_takip():
    """
    Her sabah çalışır.
    Seçilen hisselerin fiyatını günceller ve KAP haberlerini kontrol eder.
    """
    secilen = secilen_yukle()
    if not secilen:
        log.info("Seçilen hisse yok — önce 'python bist_temel.py TARA' çalıştır")
        return

    log.info(f"Günlük takip — {len(secilen)} hisse...")
    kap_bildirimleri = []

    for h in secilen:
        ticker = h["ticker"]

        # Güncel fiyat
        guncel = yf_fiyat(ticker + ".IS")
        if guncel:
            h["guncel_fiyat"] = guncel
            if h.get("fiyat") and h["fiyat"] > 0:
                h["guncel_getiri"] = (guncel - h["fiyat"]) / h["fiyat"]
            log.info(f"  {ticker}: {guncel:.2f} TL | Getiri: {yuzde(h.get('guncel_getiri', 0))}")

        # KAP haberleri
        haberler = kap_haberleri(ticker, gun=1)
        if not haberler:
            haberler = kap_haberleri_alternatif(ticker, gun=1)

        if haberler:
            for haber in haberler:
                haber["ticker"] = ticker
                kap_bildirimleri.append(haber)

        time.sleep(0.3)

    # Güncel fiyatları kaydet
    secilen_kaydet(secilen)

    # Simülasyon güncelle
    kapananlar = guncelle(KATEGORI)
    for poz in kapananlar.get(KATEGORI, []):
        gonder(uyari_mesaji(KATEGORI, poz))

    # Telegram mesajı gönder
    gonder(_takip_mesaji(secilen, kap_bildirimleri))
    gonder(rapor_mesaji(KATEGORI, "BIST TEMEL ANALİZ", "📊"))


# ── MESAJLAR ──────────────────────────────────────────

def _tarama_mesaji(secilen: list[dict]) -> str:
    if not secilen:
        return "📊 <b>BIST Temel Analiz</b>\nKriterleri karşılayan hisse bulunamadı."

    satirlar = [
        f"📊 <b>BIST TEMEL ANALİZ — SEÇILEN HİSSELER</b>",
        f"🕐 {simdi()} | {len(secilen)} hisse seçildi\n",
        "⚠️ Stop yok — uzun vadeli pozisyon\n",
    ]

    for s in secilen:
        pot_str = yuzde(s.get("potansiyel")) if s.get("potansiyel") else "—"
        fk_str  = f"{s['fk']:.1f}" if s.get("fk") else "—"
        roe_str = yuzde(s.get("roe")) if s.get("roe") else "—"

        satirlar.append(
            f"🟢 <b>{s['ticker']}</b> — {s.get('sektor','—')}\n"
            f"   {s.get('isim','')}\n"
            f"   Puan: {s['puan']}/100 | Fiyat: {s.get('fiyat',0):.2f} TL\n"
            f"   Hedef: {s.get('hedef',0):.2f} TL | Potansiyel: <b>{pot_str}</b>\n"
            f"   F/K: {fk_str} | ROE: {roe_str}\n"
            f"   {' | '.join(s.get('detay',[])[:3])}\n"
        )

    return "\n".join(satirlar)

def _takip_mesaji(secilen: list[dict], kap_bildirimleri: list[dict]) -> str:
    satirlar = [
        f"📊 <b>BIST TEMEL — GÜNLÜK TAKİP</b>",
        f"🕐 {simdi()}\n",
    ]

    for h in secilen:
        getiri = h.get("guncel_getiri", 0)
        guncel = h.get("guncel_fiyat", h.get("fiyat", 0))
        em_i   = "🟢" if getiri >= 0 else "🔴"
        satirlar.append(
            f"{em_i} <b>{h['ticker']}</b>\n"
            f"   Giriş: {h.get('fiyat',0):.2f} → Şimdi: {guncel:.2f} TL\n"
            f"   Getiri: <b>{yuzde(getiri)}</b> | Hedef: {yuzde(h.get('potansiyel'))}\n"
        )

    if kap_bildirimleri:
        satirlar.append(f"\n📰 <b>KAP BİLDİRİMLERİ ({len(kap_bildirimleri)} yeni):</b>")
        for b in kap_bildirimleri[:10]:
            onemli_em = "🔴" if b.get("onemli") else "📄"
            satirlar.append(
                f"{onemli_em} <b>{b['ticker']}</b> — {b['baslik'][:60]}\n"
                f"   {b['tarih']} | <a href='{b['link']}'>KAP'ta Gör</a>"
            )
    else:
        satirlar.append("\n📰 Bugün yeni KAP bildirimi yok.")

    return "\n".join(satirlar)


# ── ANA FONKSİYON ─────────────────────────────────────

def calistir():
    """Varsayılan: günlük takip."""
    log.info("=== BIST Temel başlıyor ===")
    gunluk_takip()
    log.info("=== BIST Temel bitti ===")


# ── DOĞRUDAN ÇALIŞTIRMA ───────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        komut = sys.argv[1].upper()

        if komut == "TARA":
            # 6 ayda bir: python bist_temel.py TARA
            secilen = tam_tarama()
            mesaj   = _tarama_mesaji(secilen)
            print(mesaj)
            gonder(mesaj)

            # Simülasyona pozisyon aç
            for s in secilen:
                if s.get("fiyat"):
                    tp1 = s["fiyat"] * 1.15  # %15 ilk hedef
                    tp2 = s["fiyat"] * 1.25  # %25 ikinci hedef
                    tp3 = s["fiyat"] * 1.40  # %40 ana hedef
                    if s.get("hedef") and s["hedef"] > tp3:
                        tp3 = s["hedef"]     # Analist hedefini kullan

                    pozisyon_ac(
                        kategori = KATEGORI,
                        ticker   = s["ticker"],
                        fiyat    = s["fiyat"],
                        yon      = "LONG",
                        stop     = None,      # Stop yok
                        tp1      = round(tp1, 2),
                        tp2      = round(tp2, 2),
                        tp3      = round(tp3, 2),
                        puan     = s["puan"],
                        notlar   = f"Hedef:{s.get('hedef',0):.2f} Pot:{yuzde(s.get('potansiyel'))}",
                    )
            gonder(rapor_mesaji(KATEGORI, "BIST TEMEL ANALİZ", "📊"))

        elif komut == "TAKIP":
            # Günlük takip: python bist_temel.py TAKIP
            gunluk_takip()

        elif komut == "LISTE":
            # Seçilen hisseleri göster: python bist_temel.py LISTE
            secilen = secilen_yukle()
            if secilen:
                print(_tarama_mesaji(secilen))
            else:
                print("Seçilen hisse yok. Önce: python bist_temel.py TARA")

        elif komut == "TEST" and len(sys.argv) > 2:
            # Tek hisse test: python bist_temel.py TEST AKBNK
            ticker = sys.argv[2].upper()
            print(f"\nTest: {ticker}")
            r = temel_analiz(ticker)
            if r:
                print(f"✅ Puan: {r['puan']}/100")
                for d in r["detay"]:
                    print(f"  {d}")
                hedef_str = f"{r['hedef']:.2f} TL" if r.get('hedef') else "hesaplanamadı"
                print(f"Fiyat: {r.get('fiyat',0):.2f} TL → Hedef: {hedef_str}")
                print(f"Potansiyel: {yuzde(r.get('potansiyel'))}")
            else:
                print("❌ Kriterleri karşılamıyor")

        elif komut == "KAP" and len(sys.argv) > 2:
            # KAP haber test: python bist_temel.py KAP THYAO
            ticker = sys.argv[2].upper()
            print(f"\nKAP haberleri: {ticker}")
            haberler = kap_haberleri(ticker, gun=7)
            if not haberler:
                haberler = kap_haberleri_alternatif(ticker, gun=7)
            if haberler:
                for h in haberler:
                    print(f"  {'🔴' if h['onemli'] else '📄'} {h['tarih']} — {h['baslik']}")
            else:
                print("  Haber bulunamadı")

        elif komut == "RAPOR":
            kapananlar = guncelle(KATEGORI)
            for poz in kapananlar.get(KATEGORI, []):
                gonder(uyari_mesaji(KATEGORI, poz))
            gonder(rapor_mesaji(KATEGORI, "BIST TEMEL ANALİZ", "📊"))
            print("Rapor gönderildi")

        elif komut == "SIM":
            print(rapor_mesaji(KATEGORI, "BIST TEMEL ANALİZ", "📊"))

        elif komut == "OZET":
            from simulasyon import ozet_kaydet
            ozet_kaydet(KATEGORI)

    else:
        calistir()
