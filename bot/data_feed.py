from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

import ccxt.async_support as ccxt
import numpy as np
import pandas as pd
import pandas_ta as ta
from loguru import logger


@dataclass
class MarketSnapshot:
    symbol: str
    timeframe: str
    df: pd.DataFrame


class BinanceGateway:
    def __init__(self, mode: str = "paper", market_type: str = "spot") -> None:
        self.mode = mode
        self.market_type = market_type
        self.last_ok_ts: float = 0
        self.exchange = self._build_exchange()

    def _build_exchange(self):
        ex = ccxt.binance({
            "apiKey": os.getenv("BINANCE_API_KEY", ""),
            "secret": os.getenv("BINANCE_API_SECRET", ""),
            "enableRateLimit": True,
            "options": {"defaultType": self.market_type},
        })
        if self.mode == "testnet":
            ex.set_sandbox_mode(True)
        return ex

    async def reconnect(self) -> None:
        try:
            await self.exchange.close()
        except Exception:
            pass
        self.exchange = self._build_exchange()
        await self.exchange.load_markets()
        logger.warning("BinanceGateway reconectado por watchdog")

    async def close(self) -> None:
        await self.exchange.close()

    async def fetch_balance(self) -> dict:
        res = await self.exchange.fetch_balance()
        self.last_ok_ts = asyncio.get_running_loop().time()
        return res

    async def fetch_ticker(self, symbol: str) -> dict:
        res = await self.exchange.fetch_ticker(symbol)
        self.last_ok_ts = asyncio.get_running_loop().time()
        return res

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 300) -> pd.DataFrame:
        for attempt in range(5):
            try:
                rows = await self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
                df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
                df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
                self.last_ok_ts = asyncio.get_running_loop().time()
                return df
            except Exception as exc:
                sleep_s = 1.5**attempt
                logger.warning(f"OHLCV error {symbol}/{timeframe}: {exc}. retry={attempt}")
                await asyncio.sleep(sleep_s)
        raise RuntimeError(f"Failed to fetch OHLCV for {symbol}")


def enrich_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ema20"] = ta.ema(out["close"], length=20)
    out["ema50"] = ta.ema(out["close"], length=50)
    out["ema200"] = ta.ema(out["close"], length=200)
    out["sma20"] = ta.sma(out["close"], length=20)
    out["rsi"] = ta.rsi(out["close"], length=14)
    out["atr"] = ta.atr(out["high"], out["low"], out["close"], length=14)
    bb = ta.bbands(out["close"], length=20, std=2)
    out["bb_high"] = bb["BBU_20_2.0"]
    out["bb_low"] = bb["BBL_20_2.0"]
    out["bb_mid"] = bb["BBM_20_2.0"]
    macd = ta.macd(out["close"])
    out["macd"] = macd["MACD_12_26_9"]
    out["macd_signal"] = macd["MACDs_12_26_9"]
    out["adx"] = ta.adx(out["high"], out["low"], out["close"], length=14)["ADX_14"]
    out["vwap"] = ta.vwap(out["high"], out["low"], out["close"], out["volume"])
    out["vol_avg"] = out["volume"].rolling(20).mean()
    out["returns"] = out["close"].pct_change()
    out["volatility"] = out["returns"].rolling(20).std() * np.sqrt(20)
    out["donchian_high"] = out["high"].rolling(20).max()
    out["donchian_low"] = out["low"].rolling(20).min()
    return out
