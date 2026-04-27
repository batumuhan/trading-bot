"""
utils.py — Ortak yardımcı fonksiyonlar ve indikatörler

Kaynak: Murphy, Kaufman, Shannon, Brooks kitaplarından alınan metodoloji
"""

import pandas as pd
import numpy as np
from datetime import datetime


# ── GENEL YARDIMCILAR ─────────────────────────────────

def simdi() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M")

def sf(v) -> float | None:
    """Güvenli float — hata veya NaN ise None döner."""
    if v is None:
        return None
    try:
        f = float(v)
        return None if (f != f) else f
    except:
        return None

def para(v: float) -> str:
    if v is None: return "— TL"
    return f"{v:+,.0f} TL"

def yuzde(v: float) -> str:
    if v is None: return "—%"
    return f"{v*100:+.2f}%"

def em(v: float) -> str:
    """Kar/zarar emojisi."""
    return "🟢" if v >= 0 else "🔴"


# ── TEKNİK İNDİKATÖRLER ───────────────────────────────
# Kaynak: Murphy "Technical Analysis of Financial Markets"

def ema(seri: pd.Series, n: int) -> pd.Series:
    """Exponential Moving Average."""
    return seri.ewm(span=n, adjust=False).mean()

def rsi(seri: pd.Series, n: int = 14) -> pd.Series:
    """
    RSI — Wilder formülü.
    Kaynak: Murphy Bölüm 10
    """
    delta = seri.diff()
    kazan = delta.clip(lower=0).ewm(com=n-1, min_periods=n).mean()
    kayip = (-delta.clip(upper=0)).ewm(com=n-1, min_periods=n).mean()
    rs = kazan / kayip.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def macd(seri: pd.Series, h=12, y=26, s=9):
    """
    MACD — hızlı EMA - yavaş EMA, sinyal ve histogram.
    Kaynak: Murphy Bölüm 10
    Döner: (macd_line, signal_line, histogram)
    """
    m = ema(seri, h) - ema(seri, y)
    sig = ema(m, s)
    return m, sig, m - sig

def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """
    ATR — Average True Range.
    Kaynak: Kaufman "Trading Systems and Methods"
    Stop mesafesini volatiliteye göre belirlemek için kullanılır.
    """
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(com=n-1, min_periods=n).mean()

def bollinger(seri: pd.Series, n: int = 20, k: float = 2.0):
    """
    Bollinger Bantları.
    Döner: (orta, üst, alt)
    """
    orta = seri.rolling(n).mean()
    std  = seri.rolling(n).std()
    return orta, orta + k*std, orta - k*std

def hacim_artti(hacim: pd.Series, n: int = 20, kati: float = 1.2) -> bool:
    """
    Murphy: Hacim trend onayı için kritik.
    Son mum hacmi, n günlük ortalamanın kati katından büyük mü?
    """
    if len(hacim) < n + 1:
        return False
    ort = float(hacim.iloc[-n-1:-1].mean())
    son = float(hacim.iloc[-1])
    return son > ort * kati

def trend_yukari(ema_h: pd.Series, ema_y: pd.Series) -> bool:
    """
    Shannon: Hızlı EMA yavaş EMA'nın üstündeyse yükseliş trendi.
    """
    return float(ema_h.iloc[-1]) > float(ema_y.iloc[-1])

def macd_pozitif_kesisim(hist: pd.Series) -> bool:
    """
    Brooks: Momentum dönüşü — histogram negatiften pozitife geçiyor mu?
    """
    if len(hist) < 2:
        return False
    return float(hist.iloc[-1]) > 0 and float(hist.iloc[-2]) <= 0

def macd_negatif_kesisim(hist: pd.Series) -> bool:
    """
    Histogram pozitiften negatife geçiyor mu? (SHORT için)
    """
    if len(hist) < 2:
        return False
    return float(hist.iloc[-1]) < 0 and float(hist.iloc[-2]) >= 0


# ── VERİ ÇEKME ────────────────────────────────────────

def yf_ohlcv(sembol: str, periyot: str = "6mo", aralik: str = "1d"):
    """
    yfinance ile OHLCV verisi çek.
    sembol: 'AKBNK.IS', 'GC=F', 'BTC-USD' vb.
    """
    import yfinance as yf
    try:
        d = yf.download(sembol, period=periyot, interval=aralik,
                        progress=False, auto_adjust=True)
        if d.empty:
            return None
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        # Sütun isimlerini küçük harfe çevir
        d.columns = [c.lower() for c in d.columns]
        return d
    except Exception as e:
        return None

def yf_fiyat(sembol: str) -> float | None:
    """Tek sembol için anlık fiyat."""
    d = yf_ohlcv(sembol, periyot="2d", aralik="1d")
    if d is None or d.empty:
        return None
    v = d["close"].iloc[-1]
    return float(v.iloc[0]) if hasattr(v, "iloc") else float(v)

def binance_ohlcv(sembol: str, interval: str = "1d", limit: int = 200):
    """
    Binance public API — OHLCV verisi.
    interval: '1d', '4h', '1h', '15m'
    """
    import requests
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": sembol, "interval": interval, "limit": limit},
            timeout=10
        )
        r.raise_for_status()
        df = pd.DataFrame(r.json(), columns=[
            "ts","open","high","low","close","volume",
            "close_time","quote_vol","trades","taker_base","taker_quote","ignore"
        ])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        df = df.set_index("ts")
        for c in ["open","high","low","close","volume"]:
            df[c] = pd.to_numeric(df[c])
        return df[["open","high","low","close","volume"]]
    except Exception as e:
        return None

def binance_fiyat(sembol: str) -> float | None:
    """Anlık Binance fiyatı."""
    import requests
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": sembol}, timeout=5
        )
        return float(r.json()["price"])
    except:
        return None
