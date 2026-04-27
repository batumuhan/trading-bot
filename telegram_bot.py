"""
telegram_bot.py — Telegram mesaj gönderici

Tüm modüller bu modülü import eder.
"""

import asyncio
import logging
from telegram import Bot
from telegram.constants import ParseMode
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

log = logging.getLogger(__name__)


async def _gonder(metin: str):
    bot = Bot(token=TELEGRAM_TOKEN)
    # Telegram 4096 karakter limiti — uzun mesajları böl
    for i in range(0, len(metin), 4000):
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=metin[i:i+4000],
            parse_mode=ParseMode.HTML,
        )
        if len(metin) > 4000:
            await asyncio.sleep(0.5)

def gonder(metin: str):
    """Senkron wrapper — her modülden çağrılır."""
    try:
        asyncio.run(_gonder(metin))
        log.info(f"Telegram gönderildi ({len(metin)} karakter)")
    except Exception as e:
        log.error(f"Telegram hatası: {e}")

def test_mesaj():
    """Bağlantı testi."""
    gonder("✅ <b>Bot bağlantısı başarılı!</b>")
