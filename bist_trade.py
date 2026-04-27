"""
bist_trade.py — BIST Kısa Vade Teknik Analiz

Tek başına çalışır: python bist_trade.py
Ya da main.py tarafından çağrılır.

Metodoloji:
- Murphy: Trend yönü, hacim onayı, destek/direnç
- Shannon: Çoklu zaman dilimi (günlük trend, 4h giriş)
- Kaufman: ATR bazlı stop/TP (volatiliteye göre dinamik)
- Brooks: Momentum dönüşü (MACD histogram kesişimi)
"""

import time
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import BIST_HISSELER, BIST_TRADE, SIM_POZISYON_TL
from utils import (
    sf, simdi, para, yuzde, em,
    ema, rsi, macd, atr,
    hacim_artti, trend_yukari, macd_pozitif_kesisim,
    yf_ohlcv, yf_fiyat,
)
from simulasyon import pozisyon_ac, guncelle, rapor_mesaji, uyari_mesaji
from telegram_bot import gonder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bist_trade.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

KATEGORI = "bist_trade"


# ── TEKNİK ANALİZ ─────────────────────────────────────

def analiz_et(ticker: str) -> dict | None:
    """
    Bir hisse için teknik analiz yap.
    BUY sinyali varsa dict döner, yoksa None.

    Puanlama (toplam 100):
      Trend   (EMA20>EMA50)        → 30 puan   [Murphy]
      RSI     (40-60 arası)        → 20 puan   [Murphy]
      MACD    (pozitif kesişim)    → 30 puan   [Brooks]
      Hacim   (%20 üstünde)       → 10 puan   [Murphy]
      ATR     (düşük volatilite)  → 10 puan   [Kaufman]
    """
    try:
        # Günlük veri çek — en az 60 gün lazım
        d = yf_ohlcv(ticker + ".IS", periyot="6mo", aralik="1d")
        if d is None or len(d) < 60:
            return None

        # Sütunları al
        kapanis = d["close"]
        yuksek  = d["high"]
        dusuk   = d["low"]
        hacim   = d["volume"]

        # İndikatörler hesapla
        cfg = BIST_TRADE
        ema_h = ema(kapanis, cfg["ema_hizli"])
        ema_y = ema(kapanis, cfg["ema_yavas"])
        rsi_v = rsi(kapanis, cfg["rsi_periyot"])
        _, _, hist = macd(kapanis)
        atr_v = atr(yuksek, dusuk, kapanis, cfg["atr_periyot"])

        # Son değerler
        fiyat   = float(kapanis.iloc[-1])
        rsi_son = float(rsi_v.iloc[-1])
        atr_son = float(atr_v.iloc[-1])

        # Koşullar
        trend_ok  = trend_yukari(ema_h, ema_y)
        rsi_ok    = cfg["rsi_min"] <= rsi_son <= cfg["rsi_max"]
        macd_ok   = macd_pozitif_kesisim(hist)
        hacim_ok  = hacim_artti(hacim)
        # ATR/fiyat oranı düşükse volatilite makul
        atr_oran  = atr_son / fiyat
        atr_ok    = atr_oran < 0.04   # %4'ten az volatilite

        # Puanlama
        puan = 0
        if trend_ok:  puan += 30
        if rsi_ok:    puan += 20
        if macd_ok:   puan += 30
        if hacim_ok:  puan += 10
        if atr_ok:    puan += 10

        if puan < cfg["min_puan"]:
            return None

        # ATR bazlı stop ve TP hesapla (Kaufman)
        stop = fiyat - cfg["atr_stop"] * atr_son
        tp1  = fiyat + cfg["atr_tp1"] * atr_son
        tp2  = fiyat + cfg["atr_tp2"] * atr_son
        tp3  = fiyat + cfg["atr_tp3"] * atr_son

        # Risk/Ödül kontrolü (Brooks: minimum 1:2)
        risk  = fiyat - stop
        odül  = tp3 - fiyat
        rr    = odül / risk if risk > 0 else 0

        if rr < 1.5:   # minimum 1.5:1
            return None

        return {
            "ticker":    ticker,
            "fiyat":     round(fiyat, 2),
            "puan":      puan,
            "rsi":       round(rsi_son, 1),
            "atr":       round(atr_son, 2),
            "atr_oran":  round(atr_oran * 100, 2),
            "trend_ok":  trend_ok,
            "rsi_ok":    rsi_ok,
            "macd_ok":   macd_ok,
            "hacim_ok":  hacim_ok,
            "stop":      round(stop, 2),
            "tp1":       round(tp1, 2),
            "tp2":       round(tp2, 2),
            "tp3":       round(tp3, 2),
            "rr":        round(rr, 2),
        }

    except Exception as e:
        log.error(f"Analiz hatası [{ticker}]: {e}")
        return None


# ── TARAMA ────────────────────────────────────────────

def tara() -> list[dict]:
    """Tüm BIST hisselerini tara, BUY sinyali verenleri döndür."""
    log.info(f"BIST Trade taraması başlıyor — {len(BIST_HISSELER)} hisse...")
    sonuclar = []

    for i, ticker in enumerate(BIST_HISSELER, 1):
        r = analiz_et(ticker)
        if r:
            sonuclar.append(r)
            log.info(f"  ✅ {ticker} — Puan: {r['puan']}/100 | RSI: {r['rsi']} | R/R: {r['rr']}")

        # Her 10 hissede bir ilerleme göster
        if i % 10 == 0:
            log.info(f"  [{i}/{len(BIST_HISSELER)}] tarandı...")

        time.sleep(0.3)

    sonuclar.sort(key=lambda x: x["puan"], reverse=True)
    log.info(f"Tarama bitti — {len(sonuclar)} sinyal bulundu")
    return sonuclar


# ── MESAJLAR ──────────────────────────────────────────

def sinyal_mesaji(sonuclar: list[dict]) -> str:
    if not sonuclar:
        return (
            f"📈 <b>BIST TRADE — TEKNİK TARAMA</b>\n"
            f"🕐 {simdi()}\n\n"
            f"Bu taramada BUY sinyali bulunamadı."
        )

    satirlar = [
        f"📈 <b>BIST TRADE — TEKNİK TARAMA</b>",
        f"🕐 {simdi()} | {len(sonuclar)} sinyal\n",
    ]

    for s in sonuclar:
        satirlar.append(
            f"🟢 <b>{s['ticker']}</b> | Puan: {s['puan']}/100\n"
            f"   Fiyat: <b>{s['fiyat']:.2f} TL</b> | RSI: {s['rsi']} | R/R: 1:{s['rr']:.1f}\n"
            f"   🔴 Stop: {s['stop']:.2f} TL\n"
            f"   🎯 TP1: {s['tp1']:.2f} | TP2: {s['tp2']:.2f} | TP3: {s['tp3']:.2f}\n"
            f"   Trend:{'✅' if s['trend_ok'] else '❌'} "
            f"RSI:{'✅' if s['rsi_ok'] else '❌'} "
            f"MACD:{'✅' if s['macd_ok'] else '❌'} "
            f"Hacim:{'✅' if s['hacim_ok'] else '❌'}\n"
        )

    return "\n".join(satirlar)


# ── ANA FONKSİYON ─────────────────────────────────────

def calistir():
    """Tarama yap, simülasyona ekle, Telegram'a gönder."""
    log.info("=== BIST Trade başlıyor ===")

    # 1. Tarama
    sonuclar = tara()

    # 2. Sinyal mesajı gönder
    gonder(sinyal_mesaji(sonuclar))

    # 3. Simülasyona pozisyon aç
    for s in sonuclar:
        acildi = pozisyon_ac(
            kategori = KATEGORI,
            ticker   = s["ticker"],
            fiyat    = s["fiyat"],
            yon      = "LONG",
            stop     = s["stop"],
            tp1      = s["tp1"],
            tp2      = s["tp2"],
            tp3      = s["tp3"],
            puan     = s["puan"],
            notlar   = f"RSI:{s['rsi']} RR:{s['rr']}",
        )
        if acildi:
            log.info(f"Sim pozisyon açıldı: {s['ticker']} @ {s['fiyat']:.2f}")

    # 4. Mevcut pozisyonları güncelle
    kapananlar = guncelle(KATEGORI)
    for poz in kapananlar.get(KATEGORI, []):
        gonder(uyari_mesaji(KATEGORI, poz))

    # 5. Rapor gönder
    gonder(rapor_mesaji(KATEGORI, "BIST TRADE", "📈"))

    log.info("=== BIST Trade bitti ===")


# ── ZAMANLANMIŞ GÖREV ────────────────────────────────

def gunluk_guncelle():
    """
    Günde 3 kez çalışır (09:00, 13:00, 18:00).
    Sabah: tarama + güncelleme
    Öğle ve akşam: sadece güncelleme + rapor
    """
    import datetime
    saat = datetime.datetime.now().hour

    if saat < 11:
        # Sabah: hem tara hem güncelle
        log.info("=== Sabah tarama + güncelleme ===")
        calistir()
    else:
        # Öğle/akşam: sadece güncelle
        log.info(f"=== Gün içi güncelleme (saat {saat}) ===")
        kapananlar = guncelle(KATEGORI)
        for poz in kapananlar.get(KATEGORI, []):
            gonder(uyari_mesaji(KATEGORI, poz))
        gonder(rapor_mesaji(KATEGORI, "BIST TRADE", "📈"))


# ── DOĞRUDAN ÇALIŞTIRMA ───────────────────────────────

if __name__ == "__main__":
    import sys
    import schedule

    if len(sys.argv) > 1:
        komut = sys.argv[1].upper()

        if komut == "TEST" and len(sys.argv) > 2:
            ticker = sys.argv[2].upper()
            print(f"\nTest: {ticker}")
            r = analiz_et(ticker)
            if r:
                print(f"✅ BUY Sinyali!")
                for k, v in r.items():
                    print(f"  {k}: {v}")
            else:
                print("❌ Sinyal yok")

        elif komut == "TARA":
            sonuclar = tara()
            print(sinyal_mesaji(sonuclar))

        elif komut == "RAPOR":
            kapananlar = guncelle(KATEGORI)
            for poz in kapananlar.get(KATEGORI, []):
                gonder(uyari_mesaji(KATEGORI, poz))
            gonder(rapor_mesaji(KATEGORI, "BIST TRADE", "📈"))
            print("Rapor gönderildi")

        elif komut == "SIM":
            print(rapor_mesaji(KATEGORI, "BIST TRADE", "📈"))

        elif komut == "OZET":
            # Aylık özet: python bist_trade.py OZET
            from simulasyon import ozet_kaydet
            ozet_kaydet(KATEGORI)

        elif komut == "BASLAT":
            # Otomatik çalışma: python bist_trade.py BASLAT
            log.info("Zamanlayıcı başlatılıyor...")
            schedule.every().day.at("09:00").do(gunluk_guncelle)
            schedule.every().day.at("13:00").do(gunluk_guncelle)
            schedule.every().day.at("18:00").do(gunluk_guncelle)
            log.info("✅ 09:00, 13:00, 18:00 saatlerinde çalışacak")
            # İlk çalışmayı hemen yap
            calistir()
            while True:
                schedule.run_pending()
                time.sleep(30)

    else:
        # Argümansız: hemen çalıştır
        calistir()
