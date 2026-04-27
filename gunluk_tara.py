"""
gunluk_tara.py — Tüm taramaları sırayla çalıştırır.
Görev Zamanlayıcı bu dosyayı günde 3 kez çalıştırır.

Sabah (09:10): BIST teknik + kripto + metal + temel takip
Öğle (13:00):  Kripto + güncelleme
Akşam (18:30): Tüm raporlar + güncelleme
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

        log.info(f"✅ {modul_adi} {komut} tamamlandı")
    except Exception as e:
        log.error(f"❌ {modul_adi} {komut} hatası: {e}")

def sabah():
    """09:10 — Tüm taramalar"""
    log.info("=" * 50)
    log.info("SABAH TARAMASI BAŞLIYOR")
    log.info("=" * 50)
    calistir("TARA",   "bist_trade")
    calistir("TARA",   "kripto")
    calistir("TARA",   "altin_gumus")
    calistir("TAKIP",  "bist_temel")
    log.info("Sabah taraması tamamlandı")

def ogle():
    """13:00 — Kripto + güncelleme"""
    log.info("=" * 50)
    log.info("ÖĞLE GÜNCELLEMESİ BAŞLIYOR")
    log.info("=" * 50)
    calistir("RAPOR", "kripto")
    calistir("RAPOR", "bist_trade")
    log.info("Öğle güncellemesi tamamlandı")

def aksam():
    """18:30 — Tüm raporlar"""
    log.info("=" * 50)
    log.info("AKŞAM RAPORU BAŞLIYOR")
    log.info("=" * 50)
    calistir("RAPOR", "bist_trade")
    calistir("RAPOR", "kripto")
    calistir("RAPOR", "altin_gumus")
    calistir("TAKIP", "bist_temel")
    log.info("Akşam raporu tamamlandı")

def kripto_tara():
    """Kripto tarama — her 2 saatte bir"""
    log.info("=" * 50)
    log.info("KRİPTO TARAMASI BAŞLIYOR")
    log.info("=" * 50)
    calistir("TARA", "kripto")
    log.info("Kripto taraması tamamlandı")


if __name__ == "__main__":
    saat = datetime.now().hour

    if len(sys.argv) > 1:
        komut = sys.argv[1].upper()
        if komut == "SABAH":    sabah()
        elif komut == "OGLE":   ogle()
        elif komut == "AKSAM":  aksam()
        elif komut == "KRIPTO": kripto_tara()
        elif komut == "HEPSI":
            sabah(); ogle(); aksam()
    else:
        # Saate göre otomatik karar ver
        if saat < 11:
            sabah()
        elif saat < 16:
            ogle()
        else:
            aksam()
