"""
gunluk_tara.py — Tüm taramaları sırayla çalıştırır.
GitHub Actions bu dosyayı otomatik çalıştırır.

SABAH  (10:30): BIST teknik + kripto + metal + temel takip
OGLE   (12:30): BIST teknik + kripto + metal + temel takip
AKSAM1 (15:30): BIST rapor + kripto tarama
AKSAM2 (16:30): Kapanış öncesi tüm raporlar
KRIPTO (her 2 saatte bir 7/24): Sadece kripto tarama
"""

import sys
import os
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("gunluk.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

def calistir(komut, modul_adi):
    """Bir modülü verilen komutla çalıştır."""
    log.info(f"▶ {modul_adi} {komut} başlıyor...")
    try:
        if modul_adi == "bist_trade":
            import bist_trade
            if komut == "TARA":    bist_trade.calistir()
            elif komut == "RAPOR":
                from simulasyon import guncelle
                from telegram_bot import gonder
                from simulasyon import rapor_mesaji, uyari_mesaji
                kapananlar = guncelle("bist_trade")
                for p in kapananlar.get("bist_trade", []):
                    gonder(uyari_mesaji("bist_trade", p))
                gonder(rapor_mesaji("bist_trade", "BIST TRADE", "📈"))

        elif modul_adi == "kripto":
            import kripto
            if komut == "TARA":    kripto.calistir()
            elif komut == "RAPOR":
                from simulasyon import guncelle, rapor_mesaji, uyari_mesaji
                from telegram_bot import gonder
                kapananlar = guncelle("kripto")
                for p in kapananlar.get("kripto", []):
                    gonder(uyari_mesaji("kripto", p))
                gonder(rapor_mesaji("kripto", "KRİPTO", "🪙"))

        elif modul_adi == "altin_gumus":
            import altin_gumus
            if komut == "TARA":    altin_gumus.calistir()
            elif komut == "RAPOR": altin_gumus.calistir()

        elif modul_adi == "bist_temel":
            import bist_temel
            if komut == "TAKIP":   bist_temel.gunluk_takip()
            elif komut == "TARA":
                secilen = bist_temel.tam_tarama()
                mesaj   = bist_temel._tarama_mesaji(secilen)
                from telegram_bot import gonder
                from simulasyon import pozisyon_ac, rapor_mesaji
                gonder(mesaj)
                # Simülasyona pozisyon aç
                for s in secilen:
                    if s.get("fiyat"):
                        tp1 = s["fiyat"] * 1.15
                        tp2 = s["fiyat"] * 1.25
                        tp3 = s.get("hedef") or s["fiyat"] * 1.40
                        pozisyon_ac(
                            kategori = "bist_temel",
                            ticker   = s["ticker"],
                            fiyat    = s["fiyat"],
                            yon      = "LONG",
                            stop     = None,
                            tp1      = round(tp1, 2),
                            tp2      = round(tp2, 2),
                            tp3      = round(tp3, 2),
                            puan     = s["puan"],
                            notlar   = f"Hedef:{s.get('hedef',0):.2f} Pot:{s.get('potansiyel',0)*100:.1f}%",
                        )
                gonder(rapor_mesaji("bist_temel", "BIST TEMEL", "📊"))

        log.info(f"✅ {modul_adi} {komut} tamamlandı")
    except Exception as e:
        log.error(f"❌ {modul_adi} {komut} hatası: {e}")

def sabah():
    """10:30 — Sabah taraması (BIST + Kripto + Metal + Temel fiyat takip)"""
    log.info("=" * 50)
    log.info("SABAH TARAMASI BAŞLIYOR")
    log.info("=" * 50)
    calistir("TARA",   "bist_trade")
    calistir("TARA",   "kripto")
    calistir("TARA",   "altin_gumus")
    _sim_ozet_gonder("SABAH")
    log.info("Sabah taraması tamamlandı")

def ogle():
    """12:30 — Tam tarama + simülasyon güncelleme"""
    log.info("=" * 50)
    log.info("ÖĞLE TARAMASI BAŞLIYOR")
    log.info("=" * 50)
    calistir("TARA",  "bist_trade")
    calistir("TARA",  "kripto")
    calistir("TARA",  "altin_gumus")
    _sim_ozet_gonder("ÖĞLE")
    log.info("Öğle taraması tamamlandı")

def aksam():
    """18:30 — Tüm raporlar"""
    log.info("=" * 50)
    log.info("AKŞAM RAPORU BAŞLIYOR")
    log.info("=" * 50)
    calistir("RAPOR", "bist_trade")
    calistir("RAPOR", "kripto")
    calistir("RAPOR", "altin_gumus")
    log.info("Akşam raporu tamamlandı")

def _sim_ozet_gonder(etiket: str):
    """Her taramanın sonunda tüm açık pozisyonların anlık durumunu gönder."""
    try:
        from simulasyon import yukle, istatistik
        from telegram_bot import gonder

        sim = yukle()
        zaman = datetime.now().strftime('%d.%m.%Y %H:%M')
        satirlar = [
            f"📊 <b>{etiket} — PORTFÖY DURUMU</b>",
            f"🕐 {zaman}\n"
        ]

        kat_bilgi = {
            "bist_trade": "📈 BIST Teknik",
            "bist_temel": "📊 BIST Temel",
            "kripto":     "🪙 Kripto",
            "metal":      "🥇 Emtia",
        }

        toplam_kz = 0
        for kat, isim in kat_bilgi.items():
            acik = sim.get(kat, {}).get("acik", [])
            if not acik:
                continue
            satirlar.append(f"<b>{isim}</b>")
            for p in acik:
                kz_tl  = p.get("kz_tl", 0)
                kz_pct = p.get("kz_pct", 0)
                em     = "🟢" if kz_tl >= 0 else "🔴"
                yon    = "⬆️" if p.get("yon","LONG")=="LONG" else "⬇️"
                tp1ok  = "✅" if p.get("tp1_gecildi") else "⬜"
                tp2ok  = "✅" if p.get("tp2_gecildi") else "⬜"
                satirlar.append(
                    f"  {em}{yon} <b>{p['ticker']}</b> | {kz_pct*100:+.2f}% ({kz_tl:+,.0f} TL)"
                    + "\n"
                    + f"     TP1{tp1ok} TP2{tp2ok} | Stop: {p.get('stop', '—')}"
                )
                toplam_kz += kz_tl

        em_top = "🟢" if toplam_kz >= 0 else "🔴"
        em_top = "🟢" if toplam_kz >= 0 else "🔴"
        satirlar.append(f"{em_top} <b>Toplam Acik K/Z: {toplam_kz:+,.0f} TL</b>")
        gonder("\n".join(satirlar))
        log.info(f"Portfoy ozeti gonderildi: {toplam_kz:+,.0f} TL")
    except Exception as e:
        log.error(f"Portföy özeti hatası: {e}")


def kripto_tara():
    """Kripto tarama — her 2 saatte bir"""
    log.info("=" * 50)
    log.info("KRİPTO TARAMASI BAŞLIYOR")
    log.info("=" * 50)
    calistir("TARA", "kripto")
    log.info("Kripto taraması tamamlandı")

def aksam1():
    """15:30 — BIST güncelleme + kripto"""
    log.info("=" * 50)
    log.info("15:30 GÜNCELLEMESİ BAŞLIYOR")
    log.info("=" * 50)
    calistir("RAPOR", "bist_trade")
    calistir("TARA",  "kripto")
    _sim_ozet_gonder("15:30")
    log.info("15:30 güncellemesi tamamlandı")

def aksam2():
    """16:30 — Kapanış öncesi son güncelleme"""
    log.info("=" * 50)
    log.info("16:30 GÜNCELLEMESİ BAŞLIYOR")
    log.info("=" * 50)
    calistir("RAPOR", "bist_trade")
    calistir("RAPOR", "kripto")
    calistir("TARA",  "altin_gumus")
    _sim_ozet_gonder("16:30 KAPANIŞ")
    log.info("16:30 güncellemesi tamamlandı")


if __name__ == "__main__":
    saat = datetime.now().hour

    if len(sys.argv) > 1:
        komut = sys.argv[1].upper()
        if komut == "SABAH":    sabah()
        elif komut == "OGLE":   ogle()
        elif komut == "AKSAM":  aksam()
        elif komut == "AKSAM1": aksam1()
        elif komut == "AKSAM2": aksam2()
        elif komut == "KRIPTO": kripto_tara()

        elif komut == "HEPSI":
            sabah(); ogle(); aksam1(); aksam2()
    else:
        # Saate göre otomatik karar ver
        if saat < 11:
            sabah()
        elif saat < 16:
            ogle()
        else:
            aksam()
