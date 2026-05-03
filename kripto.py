"""
kripto.py — Kripto Long/Short Teknik Analiz

Tek başına çalışır: python kripto.py
Ya da main.py tarafından çağrılır.

Veri kaynağı: Binance public API (key gerekmez)
Metodoloji:
- Çoklu zaman dilimi: 1d trend + 4h giriş + 1h tetikleyici
- EMA21/55 trend filtresi
- RSI momentum
- MACD histogram kesişimi
- ATR bazlı stop/TP
- Long ve Short sinyali
- İz süren stop: TP1 geçince başa baş, TP2 geçince TP1'e çek
"""

import time
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import KRIPTO, SIM_POZISYON_TL
from utils import (
    sf, simdi, para, yuzde, em,
    ema, rsi, macd, atr,
    trend_yukari, macd_pozitif_kesisim, macd_negatif_kesisim,
    binance_ohlcv, binance_fiyat,
)
from simulasyon import pozisyon_ac, guncelle, rapor_mesaji, uyari_mesaji
from telegram_bot import gonder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("kripto.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

KATEGORI = "kripto"


# ── ANALİZ ────────────────────────────────────────────

def analiz_et(sembol: str) -> dict | None:
    """
    Bir kripto için Long/Short sinyali üret.

    Çoklu zaman dilimi (Shannon):
      1D  → ana trend yönü
      4H  → giriş sinyali
      1H  → tetikleyici (hassas giriş)

    Puanlama Long (toplam 100):
      1D trend yukarı        → 25 puan
      4H trend yukarı        → 20 puan
      4H RSI 45-65 arası     → 15 puan
      4H MACD pozitif kesişim→ 25 puan
      1H MACD pozitif kesişim→ 15 puan

    Short için tam tersi koşullar.
    """
    try:
        cfg = KRIPTO

        # Veri çek — 3 zaman dilimi
        d1d = binance_ohlcv(sembol, "1d",  200)
        d4h = binance_ohlcv(sembol, "4h",  200)
        d1h = binance_ohlcv(sembol, "1h",  100)

        if d1d is None or d4h is None or d1h is None:
            return None
        if len(d1d) < 60 or len(d4h) < 60 or len(d1h) < 30:
            return None

        # İndikatörler — 1D
        ema21_1d = ema(d1d["close"], cfg["ema_hizli"])
        ema55_1d = ema(d1d["close"], cfg["ema_yavas"])
        trend_1d_yukari = trend_yukari(ema21_1d, ema55_1d)

        # İndikatörler — 4H
        ema21_4h = ema(d4h["close"], cfg["ema_hizli"])
        ema55_4h = ema(d4h["close"], cfg["ema_yavas"])
        rsi_4h   = rsi(d4h["close"], cfg["rsi_periyot"])
        _, _, hist_4h = macd(d4h["close"])
        atr_4h   = atr(d4h["high"], d4h["low"], d4h["close"], cfg["atr_periyot"])

        trend_4h_yukari  = trend_yukari(ema21_4h, ema55_4h)
        rsi_4h_son       = float(rsi_4h.iloc[-1])
        macd_4h_long     = float(hist_4h.iloc[-1]) > 0   # Pozitif bölgede
        macd_4h_short    = float(hist_4h.iloc[-1]) < 0   # Negatif bölgede

        # İndikatörler — 1H
        _, _, hist_1h = macd(d1h["close"])
        macd_1h_long  = float(hist_1h.iloc[-1]) > 0   # Pozitif bölgede yeterli
        macd_1h_short = float(hist_1h.iloc[-1]) < 0   # Negatif bölgede yeterli

        # Son değerler
        fiyat   = float(d4h["close"].iloc[-1])
        atr_son = float(atr_4h.iloc[-1])

        # ── LONG PUANLAMA ──
        long_puan = 0
        long_detay = {}

        long_detay["1d_trend"] = trend_1d_yukari
        long_detay["4h_trend"] = trend_4h_yukari
        long_detay["4h_rsi"]   = 45 <= rsi_4h_son <= 65
        long_detay["4h_macd"]  = macd_4h_long
        long_detay["1h_macd"]  = macd_1h_long

        if long_detay["1d_trend"]: long_puan += 25
        if long_detay["4h_trend"]: long_puan += 20
        if long_detay["4h_rsi"]:   long_puan += 15
        if long_detay["4h_macd"]:  long_puan += 25
        if long_detay["1h_macd"]:  long_puan += 15

        # ── SHORT PUANLAMA ──
        short_puan = 0
        short_detay = {}

        short_detay["1d_trend"] = not trend_1d_yukari
        short_detay["4h_trend"] = not trend_4h_yukari
        short_detay["4h_rsi"]   = 35 <= rsi_4h_son <= 55
        short_detay["4h_macd"]  = macd_4h_short
        short_detay["1h_macd"]  = macd_1h_short

        if short_detay["1d_trend"]: short_puan += 25
        if short_detay["4h_trend"]: short_puan += 20
        if short_detay["4h_rsi"]:   short_puan += 15
        if short_detay["4h_macd"]:  short_puan += 25
        if short_detay["1h_macd"]:  short_puan += 15

        # ── KARAR ──
        min_puan = cfg["min_puan"]
        yon = None
        puan = 0
        detay = {}

        # Long ve Short aynı anda çakışmasın — hangisi daha güçlüyse
        if long_puan >= min_puan and long_puan > short_puan:
            yon   = "LONG"
            puan  = long_puan
            detay = long_detay
            stop  = fiyat - cfg["long_stop_atr"]  * atr_son
            tp1   = fiyat + cfg["long_tp1_atr"]   * atr_son
            tp2   = fiyat + cfg["long_tp2_atr"]   * atr_son
            tp3   = fiyat + cfg["long_tp3_atr"]   * atr_son

        elif short_puan >= min_puan and short_puan > long_puan:
            yon   = "SHORT"
            puan  = short_puan
            detay = short_detay
            stop  = fiyat + cfg["short_stop_atr"] * atr_son
            tp1   = fiyat - cfg["short_tp1_atr"]  * atr_son
            tp2   = fiyat - cfg["short_tp2_atr"]  * atr_son
            tp3   = fiyat - cfg["short_tp3_atr"]  * atr_son
        else:
            return None

        # Risk/Ödül kontrolü (minimum 1.5:1)
        risk = abs(fiyat - stop)
        odul = abs(tp3   - fiyat)
        rr   = odul / risk if risk > 0 else 0

        if rr < 1.5:
            return None

        return {
            "sembol":   sembol,
            "isim":     sembol.replace("USDT",""),
            "yon":      yon,
            "fiyat":    fiyat,
            "puan":     puan,
            "rsi_4h":   round(rsi_4h_son, 1),
            "atr":      atr_son,
            "detay":    detay,
            "stop":     round(stop, 6),
            "tp1":      round(tp1,  6),
            "tp2":      round(tp2,  6),
            "tp3":      round(tp3,  6),
            "rr":       round(rr,   2),
        }

    except Exception as e:
        log.error(f"Kripto analiz hatası [{sembol}]: {e}")
        return None


# ── TARAMA ────────────────────────────────────────────

def tara() -> list[dict]:
    """Tüm coinleri tara, sinyal verenleri döndür."""
    log.info(f"Kripto taraması başlıyor — {len(KRIPTO['coinler'])} coin...")
    sonuclar = []

    for sembol in KRIPTO["coinler"]:
        r = analiz_et(sembol)
        if r:
            yon_em = "⬆️ LONG" if r["yon"] == "LONG" else "⬇️ SHORT"
            log.info(f"  ✅ {sembol} — {yon_em} | Puan: {r['puan']}/100 | R/R: {r['rr']}")
            sonuclar.append(r)
        time.sleep(0.5)

    sonuclar.sort(key=lambda x: x["puan"], reverse=True)
    log.info(f"Kripto tarama bitti — {len(sonuclar)} sinyal")
    return sonuclar


# ── MESAJLAR ──────────────────────────────────────────

def sinyal_mesaji(sonuclar: list[dict]) -> str:
    if not sonuclar:
        return (
            f"🪙 <b>KRİPTO — TEKNİK TARAMA</b>\n"
            f"🕐 {simdi()}\n\n"
            f"Bu taramada sinyal bulunamadı."
        )

    satirlar = [
        f"🪙 <b>KRİPTO — TEKNİK TARAMA</b>",
        f"🕐 {simdi()} | {len(sonuclar)} sinyal\n",
    ]

    for s in sonuclar:
        yon_em = "🟢 LONG ⬆️" if s["yon"] == "LONG" else "🔴 SHORT ⬇️"
        d = s["detay"]
        satirlar.append(
            f"{yon_em} <b>{s['isim']}</b> | Puan: {s['puan']}/100\n"
            f"   Fiyat: <b>{s['fiyat']:.4f} USDT</b> | RSI(4h): {s['rsi_4h']} | R/R: 1:{s['rr']}\n"
            f"   🔴 Stop: {s['stop']:.4f}\n"
            f"   🎯 TP1: {s['tp1']:.4f} | TP2: {s['tp2']:.4f} | TP3: {s['tp3']:.4f}\n"
            f"   1D:{'✅' if d.get('1d_trend') else '❌'} "
            f"4H:{'✅' if d.get('4h_trend') else '❌'} "
            f"RSI:{'✅' if d.get('4h_rsi') else '❌'} "
            f"MACD4H:{'✅' if d.get('4h_macd') else '❌'} "
            f"MACD1H:{'✅' if d.get('1h_macd') else '❌'}\n"
        )

    return "\n".join(satirlar)


# ── ANA FONKSİYON ─────────────────────────────────────

def calistir():
    log.info("=== Kripto başlıyor ===")

    sonuclar = tara()
    gonder(sinyal_mesaji(sonuclar))

    for s in sonuclar:
        acildi = pozisyon_ac(
            kategori = KATEGORI,
            ticker   = s["sembol"],
            fiyat    = s["fiyat"],
            yon      = s["yon"],
            stop     = s["stop"],
            tp1      = s["tp1"],
            tp2      = s["tp2"],
            tp3      = s["tp3"],
            puan     = s["puan"],
            notlar   = f"RSI:{s['rsi_4h']} RR:{s['rr']}",
        )
        if acildi:
            log.info(f"Sim pozisyon: {s['sembol']} {s['yon']} @ {s['fiyat']:.4f}")

    kapananlar = guncelle(KATEGORI)
    for poz in kapananlar.get(KATEGORI, []):
        gonder(uyari_mesaji(KATEGORI, poz))

    gonder(rapor_mesaji(KATEGORI, "KRİPTO", "🪙"))
    log.info("=== Kripto bitti ===")


# ── DOĞRUDAN ÇALIŞTIRMA ───────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        komut = sys.argv[1].upper()

        if komut == "TEST" and len(sys.argv) > 2:
            sembol = sys.argv[2].upper()
            if not sembol.endswith("USDT"):
                sembol += "USDT"
            print(f"\nTest: {sembol}")
            r = analiz_et(sembol)
            if r:
                print(f"✅ {r['yon']} Sinyali! Puan: {r['puan']}/100")
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
            gonder(rapor_mesaji(KATEGORI, "KRİPTO", "🪙"))
            print("Rapor gönderildi")

        elif komut == "SIM":
            print(rapor_mesaji(KATEGORI, "KRİPTO", "🪙"))

        elif komut == "OZET":
            from simulasyon import ozet_kaydet
            ozet_kaydet(KATEGORI)

    else:
        calistir()
