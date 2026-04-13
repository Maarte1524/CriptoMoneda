from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

import ccxt.async_support as ccxt
import numpy as np
import pandas as pd
from loguru import logger
from ta.momentum import RSIIndicator
from ta.trend import ADXIndicator, EMAIndicator, MACD, SMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands
from ta.volume import VolumeWeightedAveragePrice


@dataclass
class MarketSnapshot:
    symbol: str
    timeframe: str
    df: pd.DataFrame


class BinanceGateway:
    def __init__(self, mode: str = "paper", market_type: str = "spot") -> None:
        self.mode = mode
        self.market_type = market_type
        self.exchange = ccxt.binance({
            "apiKey": os.getenv("BINANCE_API_KEY", ""),
            "secret": os.getenv("BINANCE_API_SECRET", ""),
            "enableRateLimit": True,
            "options": {"defaultType": market_type},
        })
        if mode == "testnet":
            self.exchange.set_sandbox_mode(True)

    async def close(self) -> None:
        await self.exchange.close()

    async def fetch_balance(self) -> dict:
        return await self.exchange.fetch_balance()

    async def fetch_ticker(self, symbol: str) -> dict:
        return await self.exchange.fetch_ticker(symbol)

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 300) -> pd.DataFrame:
        for attempt in range(5):
            try:
                rows = await self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
                df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
                df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
                return df
            except Exception as exc:
                sleep_s = (1.5 ** attempt)
                logger.warning(f"OHLCV error {symbol}/{timeframe}: {exc}. retry={attempt}")
                await asyncio.sleep(sleep_s)
        raise RuntimeError(f"Failed to fetch OHLCV for {symbol}")


def enrich_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ema20"] = EMAIndicator(out["close"], window=20).ema_indicator()
    out["ema50"] = EMAIndicator(out["close"], window=50).ema_indicator()
    out["ema200"] = EMAIndicator(out["close"], window=200).ema_indicator()
    out["sma20"] = SMAIndicator(out["close"], window=20).sma_indicator()
    out["rsi"] = RSIIndicator(out["close"], window=14).rsi()
    out["atr"] = AverageTrueRange(out["high"], out["low"], out["close"], window=14).average_true_range()
    bb = BollingerBands(out["close"], window=20, window_dev=2)
    out["bb_high"] = bb.bollinger_hband()
    out["bb_low"] = bb.bollinger_lband()
    out["bb_mid"] = bb.bollinger_mavg()
    macd = MACD(out["close"])
    out["macd"] = macd.macd()
    out["macd_signal"] = macd.macd_signal()
    out["adx"] = ADXIndicator(out["high"], out["low"], out["close"], window=14).adx()
    out["vwap"] = VolumeWeightedAveragePrice(
        out["high"], out["low"], out["close"], out["volume"], window=14
    ).volume_weighted_average_price()
    out["vol_avg"] = out["volume"].rolling(20).mean()
    out["returns"] = out["close"].pct_change()
    out["volatility"] = out["returns"].rolling(20).std() * np.sqrt(20)
    out["donchian_high"] = out["high"].rolling(20).max()
    out["donchian_low"] = out["low"].rolling(20).min()
    return out
