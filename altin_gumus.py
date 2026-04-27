"""
altin_gumus.py — Altın ve Gümüş Teknik + Makro Analiz

Tek başına çalışır: python altin_gumus.py
Ya da main.py tarafından çağrılır.

Özellikler:
- Gram altın/gümüş TL cinsinden takip
- Stop yok — uzun vadeli pozisyon
- TP: ATR bazlı + en yakın direnç seviyesiyle hizalanmış
- Makro: Dolar trendi (DXY/USDTRY) + web'den haber taraması
- Murphy Intermarket: Dolar güçlenirse altın baskı altında
"""

import time
import logging
import sys
import os
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import METAL, SIM_POZISYON_TL
from utils import (
    sf, simdi, para, yuzde, em,
    ema, rsi, macd, atr,
    trend_yukari, macd_pozitif_kesisim,
    yf_ohlcv, yf_fiyat,
)
from simulasyon import pozisyon_ac, guncelle, rapor_mesaji, uyari_mesaji
from telegram_bot import gonder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("altin_gumus.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

KATEGORI = "metal"


# ── DOLAR KURU VE TRENDİ ──────────────────────────────

def dolar_kur_ve_trend() -> tuple[float, str]:
    """
    USDTRY kurundan hem kur değerini hem trendi çek.
    Murphy Intermarket: Dolar güçlü → Altın baskı altında
    Döner: (kur, trend) — trend: 'YUKARI', 'ASAGI', 'NÖTR'
    """
    try:
        d = yf_ohlcv("USDTRY=X", periyot="3mo", aralik="1d")
        if d is None or len(d) < 30:
            return None, "NÖTR"

        kur     = float(d["close"].iloc[-1])
        ema20   = ema(d["close"], 20)
        ema50   = ema(d["close"], 50)

        if float(ema20.iloc[-1]) > float(ema50.iloc[-1]):
            trend = "YUKARI"   # Dolar güçleniyor → Altın için olumsuz
        else:
            trend = "ASAGI"    # Dolar zayıflıyor → Altın için olumlu

        log.info(f"Dolar kuru: {kur:.2f} TL | Trend: {trend}")
        return kur, trend

    except Exception as e:
        log.error(f"Dolar kuru hatası: {e}")
        return None, "NÖTR"


# ── MAKRO HABER TARAMASI ──────────────────────────────

def makro_haber_skoru() -> tuple[int, list[str]]:
    """
    Web'den güncel altın/makro haberlerini çek.
    Pozitif haberler: Fed faiz indirimi, enflasyon artışı, jeopolitik risk
    Negatif haberler: Fed faiz artışı, dolar güçlenmesi, risk iştahı artışı

    Döner: (skor, haberler) — skor: -20 ile +20 arası
    """
    skor   = 0
    haberler = []

    pozitif_kelimeler = [
        "fed rate cut", "interest rate cut", "inflation rise", "inflation high",
        "geopolitical", "war", "crisis", "recession", "safe haven",
        "gold rally", "gold surge", "gold bull", "faiz indirimi",
        "enflasyon artış", "altın yükseliş",
    ]
    negatif_kelimeler = [
        "fed rate hike", "interest rate hike", "rate increase",
        "dollar strong", "dollar rally", "risk on", "gold falls",
        "gold drop", "gold bear", "faiz artışı", "dolar güçlen",
    ]

    try:
        # RSS haber kaynakları
        kaynaklar = [
            "https://feeds.bloomberg.com/markets/news.rss",
            "https://www.investing.com/rss/news_25.rss",   # Gold news
            "https://feeds.reuters.com/reuters/businessNews",
        ]

        for url in kaynaklar:
            try:
                r = requests.get(url, timeout=8,
                                headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code != 200:
                    continue

                metin = r.text.lower()

                for kelime in pozitif_kelimeler:
                    if kelime.lower() in metin:
                        skor += 5
                        haberler.append(f"🟢 {kelime}")
                        break

                for kelime in negatif_kelimeler:
                    if kelime.lower() in metin:
                        skor -= 5
                        haberler.append(f"🔴 {kelime}")
                        break

            except:
                continue

        skor = max(-20, min(20, skor))   # -20 ile +20 arasında tut

    except Exception as e:
        log.error(f"Haber tarama hatası: {e}")

    return skor, haberler[:5]


# ── DİRENÇ SEVİYELERİ ────────────────────────────────

def direnc_seviyeleri(df, fiyat: float, atr_son: float) -> list[float]:
    """
    Son 6 ayın yüksek noktalarından pivot direnç seviyeleri bul.
    ATR bazlı TP'ler bu seviyelere hizalanır.
    Kaynak: Murphy - Destek/Direnç analizi
    """
    try:
        yuksekler = df["high"].values
        direncler = []

        # Swing high: her iki taraftan da yüksek olan noktalar
        for i in range(2, len(yuksekler) - 2):
            if (yuksekler[i] > yuksekler[i-1] and
                yuksekler[i] > yuksekler[i-2] and
                yuksekler[i] > yuksekler[i+1] and
                yuksekler[i] > yuksekler[i+2]):
                direncler.append(float(yuksekler[i]))

        # Fiyatın üstündeki direnç seviyelerini bul
        ust_direncler = sorted([d for d in direncler if d > fiyat])

        # ATR bazlı TP'leri hesapla
        tp1_atr = fiyat + METAL["tp1_atr"] * atr_son
        tp2_atr = fiyat + METAL["tp2_atr"] * atr_son
        tp3_atr = fiyat + METAL["tp3_atr"] * atr_son

        # En yakın dirençle hizala
        def en_yakin_direnc(hedef, direncler, tolerans=0.03):
            """Hedefe en yakın direnci bul, yoksa ATR hedefini kullan."""
            for d in direncler:
                if abs(d - hedef) / hedef <= tolerans:
                    return d
            return hedef

        if ust_direncler:
            tp1 = en_yakin_direnc(tp1_atr, ust_direncler)
            tp2 = en_yakin_direnc(tp2_atr, ust_direncler)
            tp3 = en_yakin_direnc(tp3_atr, ust_direncler)
        else:
            tp1, tp2, tp3 = tp1_atr, tp2_atr, tp3_atr

        # Sırala — tp1 < tp2 < tp3
        tpler = sorted(set([tp1, tp2, tp3]))
        while len(tpler) < 3:
            tpler.append(tpler[-1] * 1.02)

        return [round(t, 2) for t in tpler[:3]]

    except Exception as e:
        log.error(f"Direnç hesaplama hatası: {e}")
        atr_son = atr_son or fiyat * 0.01
        return [
            round(fiyat + METAL["tp1_atr"] * atr_son, 2),
            round(fiyat + METAL["tp2_atr"] * atr_son, 2),
            round(fiyat + METAL["tp3_atr"] * atr_son, 2),
        ]


# ── METAL FİYATI TL ───────────────────────────────────

def gram_fiyat_tl(metal_kodu: str, kur: float) -> tuple[float | None, object | None]:
    """
    Metal fiyatını USD/troy oz'dan TL/gram'a çevir.
    1 troy oz = 31.1035 gram
    """
    try:
        sembol = METAL["varliklar"][metal_kodu]
        d = yf_ohlcv(sembol, periyot="6mo", aralik="1d")
        if d is None or len(d) < 30:
            return None, None

        # USD/oz → TL/gram
        carpan = kur / 31.1035
        d_tl = d.copy()
        for col in ["open", "high", "low", "close"]:
            if col in d_tl.columns:
                d_tl[col] = d_tl[col] * carpan

        fiyat = float(d_tl["close"].iloc[-1])
        return fiyat, d_tl

    except Exception as e:
        log.error(f"Metal fiyat hatası [{metal_kodu}]: {e}")
        return None, None


# ── TEKNİK ANALİZ ─────────────────────────────────────

def _analiz_ham(metal_kodu: str, kur: float, dolar_trend: str,
                haber_skoru: int) -> dict | None:
    """Ham analiz — min_puan eşiği kontrolü olmadan tüm veriyi döndürür."""
    try:
        fiyat, df_tl = gram_fiyat_tl(metal_kodu, kur)
        if fiyat is None or df_tl is None:
            return None
        cfg = METAL
        ema20_v  = ema(df_tl["close"], cfg["ema_hizli"])
        ema50_v  = ema(df_tl["close"], cfg["ema_yavas"])
        rsi_v    = rsi(df_tl["close"], cfg["rsi_periyot"])
        _, _, hist = macd(df_tl["close"])
        atr_v    = atr(df_tl["high"], df_tl["low"], df_tl["close"], cfg["atr_periyot"])
        rsi_son  = float(rsi_v.iloc[-1])
        atr_son  = float(atr_v.iloc[-1])
        trend_ok = trend_yukari(ema20_v, ema50_v)
        rsi_ok   = 45 <= rsi_son <= 70
        macd_ok  = macd_pozitif_kesisim(hist)
        ema20_son  = float(ema20_v.iloc[-1])
        ema20_prev = float(ema20_v.iloc[-5])
        haftalik_yukari = ema20_son > ema20_prev
        teknik_puan = 0
        if trend_ok:        teknik_puan += 25
        if rsi_ok:          teknik_puan += 20
        if macd_ok:         teknik_puan += 25
        if haftalik_yukari: teknik_puan += 10
        makro_puan = 0
        dolar_ok = dolar_trend == "ASAGI"
        haber_ok = haber_skoru > 0
        if dolar_ok:  makro_puan += 10
        if haber_ok:  makro_puan += min(10, haber_skoru)
        toplam_puan = teknik_puan + makro_puan
        tpler = direnc_seviyeleri(df_tl, fiyat, atr_son)
        return {
            "metal": metal_kodu, "fiyat": round(fiyat, 2),
            "puan": toplam_puan, "teknik_puan": teknik_puan,
            "makro_puan": makro_puan, "rsi": round(rsi_son, 1),
            "atr": round(atr_son, 2), "trend_ok": trend_ok,
            "rsi_ok": rsi_ok, "macd_ok": macd_ok,
            "haftalik_ok": haftalik_yukari, "dolar_trend": dolar_trend,
            "dolar_ok": dolar_ok, "haber_skoru": haber_skoru,
            "tp1": tpler[0], "tp2": tpler[1], "tp3": tpler[2],
            "stop": None, "haberler": [],
        }
    except Exception as e:
        log.error(f"Ham analiz hatası [{metal_kodu}]: {e}")
        return None


def analiz_et(metal_kodu: str, kur: float, dolar_trend: str,
              haber_skoru: int) -> dict | None:
    """
    Altın/Gümüş için teknik + makro analiz.
    Stop yok — uzun vadeli pozisyon.

    Puanlama (toplam 100):
      Teknik (80 puan):
        Trend (EMA20>EMA50)     → 25 puan
        RSI 45-65 arası         → 20 puan
        MACD pozitif kesişim    → 25 puan
        Haftalık trend          → 10 puan
      Makro (20 puan):
        Dolar zayıf (ASAGI)     → 10 puan
        Olumlu haberler         → 10 puan
    """
    try:
        fiyat, df_tl = gram_fiyat_tl(metal_kodu, kur)
        if fiyat is None or df_tl is None:
            return None

        cfg = METAL

        # Teknik indikatörler
        ema20_v  = ema(df_tl["close"], cfg["ema_hizli"])
        ema50_v  = ema(df_tl["close"], cfg["ema_yavas"])
        rsi_v    = rsi(df_tl["close"], cfg["rsi_periyot"])
        _, _, hist = macd(df_tl["close"])
        atr_v    = atr(df_tl["high"], df_tl["low"], df_tl["close"], cfg["atr_periyot"])

        rsi_son  = float(rsi_v.iloc[-1])
        atr_son  = float(atr_v.iloc[-1])
        trend_ok = trend_yukari(ema20_v, ema50_v)
        rsi_ok   = 45 <= rsi_son <= 70   # Altın için RSI aralığı biraz geniş
        macd_ok  = macd_pozitif_kesisim(hist)

        # Haftalık trend — 5 günlük EMA eğimi
        ema20_son  = float(ema20_v.iloc[-1])
        ema20_prev = float(ema20_v.iloc[-5])
        haftalik_yukari = ema20_son > ema20_prev

        # Teknik puan
        teknik_puan = 0
        if trend_ok:        teknik_puan += 25
        if rsi_ok:          teknik_puan += 20
        if macd_ok:         teknik_puan += 25
        if haftalik_yukari: teknik_puan += 10

        # Makro puan
        makro_puan = 0
        dolar_ok   = dolar_trend == "ASAGI"   # Dolar zayıf → Altın lehine
        haber_ok   = haber_skoru > 0

        if dolar_ok:  makro_puan += 10
        if haber_ok:  makro_puan += min(10, haber_skoru)

        toplam_puan = teknik_puan + makro_puan

        if toplam_puan < cfg["min_puan"]:
            return None

        # TP seviyeleri: ATR + direnç hizalaması
        tpler = direnc_seviyeleri(df_tl, fiyat, atr_son)

        return {
            "metal":          metal_kodu,
            "fiyat":          round(fiyat, 2),
            "puan":           toplam_puan,
            "teknik_puan":    teknik_puan,
            "makro_puan":     makro_puan,
            "rsi":            round(rsi_son, 1),
            "atr":            round(atr_son, 2),
            "trend_ok":       trend_ok,
            "rsi_ok":         rsi_ok,
            "macd_ok":        macd_ok,
            "haftalik_ok":    haftalik_yukari,
            "dolar_trend":    dolar_trend,
            "dolar_ok":       dolar_ok,
            "haber_skoru":    haber_skoru,
            "tp1":            tpler[0],
            "tp2":            tpler[1],
            "tp3":            tpler[2],
            "stop":           None,   # Stop yok — uzun vade
        }

    except Exception as e:
        log.error(f"Metal analiz hatası [{metal_kodu}]: {e}")
        return None


# ── TARAMA ────────────────────────────────────────────

def tara() -> tuple[list[dict], list[dict], float]:
    """
    Döner: (sinyaller, tum_sonuclar, kur)
    Sinyal olmasa bile tüm metallerin durumu döner.
    """
    log.info("Altın/Gümüş taraması başlıyor...")

    kur, dolar_trend = dolar_kur_ve_trend()
    if kur is None:
        log.error("Dolar kuru çekilemedi")
        return [], [], 0

    haber_skoru, haberler = makro_haber_skoru()
    log.info(f"Haber skoru: {haber_skoru} | Haberler: {haberler}")

    sinyaller = []
    tum_sonuclar = []

    for metal in METAL["varliklar"].keys():
        # Önce ham analizi yap (eşik kontrolü olmadan)
        r = _analiz_ham(metal, kur, dolar_trend, haber_skoru)
        if r:
            r["haberler"] = haberler
            r["kur"]      = round(kur, 2)
            tum_sonuclar.append(r)
            if r["puan"] >= METAL["min_puan"]:
                sinyaller.append(r)
                log.info(f"  ✅ {metal} — Puan: {r['puan']}/100 SİNYAL")
            else:
                log.info(f"  ⚪ {metal} — Puan: {r['puan']}/100 (eşik: {METAL['min_puan']})")
        time.sleep(0.5)

    log.info(f"Metal tarama bitti — {len(sinyaller)} sinyal, {len(tum_sonuclar)} takip")
    return sinyaller, tum_sonuclar, kur


# ── MESAJLAR ──────────────────────────────────────────

def sinyal_mesaji(sonuclar: list[dict], tum_sonuclar: list[dict] = None, kur: float = None) -> str:
    kur_str = f"Kur: {kur:.2f} TL" if kur else ""
    baslik = [
        f"🥇 <b>ALTIN/GÜMÜŞ — TEKNİK + MAKRO</b>",
        f"🕐 {simdi()} | {kur_str}\n",
    ]

    if not sonuclar:
        # Sinyal yok ama tüm metallerin durumunu göster
        satirlar = baslik + ["⚪ <b>Bu taramada sinyal yok</b> (min puan: 55)\n"]
        if tum_sonuclar:
            satirlar.append("<b>Metal Durumları:</b>")
            for s in tum_sonuclar:
                emoji_map = {"ALTIN": "🥇", "GUMUS": "🥈", "PLATIN": "⬜", "PALADYUM": "🔘"}
                isim_em = emoji_map.get(s["metal"], "🔘")
                bar = "▓" * (s["puan"] // 10) + "░" * (10 - s["puan"] // 10)
                satirlar.append(
                    f"{isim_em} <b>{s['metal']}</b> — {s['puan']}/100 [{bar}]\n"
                    f"   Fiyat: {s['fiyat']:.2f} TL/gram\n"
                    f"   Trend:{'✅' if s['trend_ok'] else '❌'} "
                    f"RSI({s['rsi']}):{'✅' if s['rsi_ok'] else '❌'} "
                    f"MACD:{'✅' if s['macd_ok'] else '❌'} "
                    f"Dolar {s['dolar_trend']}:{'✅' if s['dolar_ok'] else '❌'}\n"
                )
        return "\n".join(satirlar)

    kur_str = f"Kur: {kur:.2f} TL" if kur else ""
    satirlar = [
        f"🥇 <b>ALTIN/GÜMÜŞ — TEKNİK + MAKRO</b>",
        f"🕐 {simdi()} | {kur_str}\n",
    ]

    for s in sonuclar:
        dolar_em  = "🟢" if s["dolar_ok"] else "🔴"
        haber_em  = "🟢" if s["haber_skoru"] > 0 else ("🔴" if s["haber_skoru"] < 0 else "⚪")
        emoji_map = {"ALTIN": "🥇", "GUMUS": "🥈", "PLATIN": "⬜", "PALADYUM": "🔘"}
        isim_em   = emoji_map.get(s["metal"], "🔘")

        satirlar.append(
            f"{isim_em} <b>{s['metal']}</b> | Puan: {s['puan']}/100\n"
            f"   Fiyat: <b>{s['fiyat']:.2f} TL/gram</b>\n"
            f"   🎯 TP1: {s['tp1']:.2f} | TP2: {s['tp2']:.2f} | TP3: {s['tp3']:.2f}\n"
            f"   Teknik ({s['teknik_puan']}): "
            f"Trend:{'✅' if s['trend_ok'] else '❌'} "
            f"RSI({s['rsi']}):{'✅' if s['rsi_ok'] else '❌'} "
            f"MACD:{'✅' if s['macd_ok'] else '❌'} "
            f"Haftalık:{'✅' if s['haftalik_ok'] else '❌'}\n"
            f"   Makro ({s['makro_puan']}): "
            f"Dolar {s['dolar_trend']} {dolar_em} | "
            f"Haberler {haber_em} ({s['haber_skoru']:+})\n"
            f"   ⚠️ Stop yok — uzun vadeli pozisyon\n"
        )

        if s.get("haberler"):
            satirlar.append(f"   📰 " + " | ".join(s["haberler"][:3]))
            satirlar.append("")

    return "\n".join(satirlar)


# ── ANA FONKSİYON ─────────────────────────────────────

def calistir():
    log.info("=== Altın/Gümüş başlıyor ===")

    kur, dolar_trend = dolar_kur_ve_trend()
    if kur is None:
        gonder("⚠️ Altın/Gümüş: Dolar kuru çekilemedi")
        return

    haber_skoru, haberler = makro_haber_skoru()
    sinyaller, tum_sonuclar, kur = tara()

    gonder(sinyal_mesaji(sinyaller, tum_sonuclar, kur))

    for s in sinyaller:
        acildi = pozisyon_ac(
            kategori = KATEGORI,
            ticker   = s["metal"],
            fiyat    = s["fiyat"],
            yon      = "LONG",
            stop     = None,        # Stop yok
            tp1      = s["tp1"],
            tp2      = s["tp2"],
            tp3      = s["tp3"],
            puan     = s["puan"],
            notlar   = f"Kur:{kur:.2f} Dolar:{dolar_trend} Haber:{haber_skoru:+}",
        )
        if acildi:
            log.info(f"Sim pozisyon: {s['metal']} @ {s['fiyat']:.2f} TL/gram")

    kapananlar = guncelle(KATEGORI)
    for poz in kapananlar.get(KATEGORI, []):
        gonder(uyari_mesaji(KATEGORI, poz))

    gonder(rapor_mesaji(KATEGORI, "ALTIN/GÜMÜŞ", "🥇"))
    log.info("=== Altın/Gümüş bitti ===")


# ── DOĞRUDAN ÇALIŞTIRMA ───────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        komut = sys.argv[1].upper()

        if komut == "TEST":
            kur, trend = dolar_kur_ve_trend()
            print(f"Dolar kuru: {kur:.2f} TL | Trend: {trend}")
            haber_skoru, haberler = makro_haber_skoru()
            print(f"Haber skoru: {haber_skoru} | Haberler: {haberler}")
            for metal in METAL["varliklar"].keys():
                r = analiz_et(metal, kur, trend, haber_skoru)
                if r:
                    print(f"\n✅ {metal} — Puan: {r['puan']}/100 | Fiyat: {r['fiyat']:.2f} TL/gram")
                    print(f"   TP1: {r['tp1']:.2f} | TP2: {r['tp2']:.2f} | TP3: {r['tp3']:.2f}")
                else:
                    print(f"\n❌ {metal} — Sinyal yok")

        elif komut == "TARA":
            sinyaller, tum_sonuclar, kur = tara()
            print(sinyal_mesaji(sinyaller, tum_sonuclar, kur))

        elif komut == "RAPOR":
            kapananlar = guncelle(KATEGORI)
            for poz in kapananlar.get(KATEGORI, []):
                gonder(uyari_mesaji(KATEGORI, poz))
            gonder(rapor_mesaji(KATEGORI, "ALTIN/GÜMÜŞ", "🥇"))
            print("Rapor gönderildi")

        elif komut == "SIM":
            print(rapor_mesaji(KATEGORI, "ALTIN/GÜMÜŞ", "🥇"))

        elif komut == "OZET":
            from simulasyon import ozet_kaydet
            ozet_kaydet(KATEGORI)

    else:
        calistir()
