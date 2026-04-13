from __future__ import annotations

import asyncio
from dataclasses import dataclass

import ccxt.async_support as ccxt
import pandas as pd
from ta.trend import ADXIndicator, EMAIndicator, MACD, SMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands
from ta.momentum import RSIIndicator
from ta.volume import VolumeWeightedAveragePrice


@dataclass(slots=True)
class MarketSnapshot:
    symbol: str
    price: float
    spread: float
    volatility: float
    momentum: float
    frame: pd.DataFrame


class BinanceDataFeed:
    def __init__(self, api_key: str, api_secret: str, market_type: str, testnet: bool) -> None:
        options = {"defaultType": market_type}
        self.exchange = ccxt.binance(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
                "options": options,
            }
        )
        if testnet:
            self.exchange.set_sandbox_mode(True)

    async def close(self) -> None:
        await self.exchange.close()

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        rows = await self.exchange.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)
        frame = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True)
        return frame

    async def compute_features(self, frame: pd.DataFrame) -> pd.DataFrame:
        out = frame.copy()
        out["ema20"] = EMAIndicator(close=out["close"], window=20).ema_indicator()
        out["ema50"] = EMAIndicator(close=out["close"], window=50).ema_indicator()
        out["ema200"] = EMAIndicator(close=out["close"], window=200).ema_indicator()
        out["sma20"] = SMAIndicator(close=out["close"], window=20).sma_indicator()
        out["rsi14"] = RSIIndicator(close=out["close"], window=14).rsi()
        out["atr14"] = AverageTrueRange(high=out["high"], low=out["low"], close=out["close"], window=14).average_true_range()
        out["adx14"] = ADXIndicator(high=out["high"], low=out["low"], close=out["close"], window=14).adx()
        bb = BollingerBands(close=out["close"], window=20, window_dev=2)
        out["bb_upper"] = bb.bollinger_hband()
        out["bb_lower"] = bb.bollinger_lband()
        macd = MACD(close=out["close"])
        out["macd"] = macd.macd()
        out["macd_signal"] = macd.macd_signal()
        out["vwap"] = VolumeWeightedAveragePrice(
            high=out["high"], low=out["low"], close=out["close"], volume=out["volume"], window=20
        ).volume_weighted_average_price()
        out["avg_volume20"] = out["volume"].rolling(20).mean()
        out["returns"] = out["close"].pct_change()
        out["volatility20"] = out["returns"].rolling(20).std()
        return out

    async def snapshot(self, symbol: str, timeframe: str) -> MarketSnapshot:
        order_book, ohlcv = await asyncio.gather(
            self.exchange.fetch_order_book(symbol),
            self.fetch_ohlcv(symbol, timeframe=timeframe, limit=500),
        )
        frame = await self.compute_features(ohlcv)
        last = frame.iloc[-1]
        best_bid = order_book["bids"][0][0] if order_book["bids"] else last["close"]
        best_ask = order_book["asks"][0][0] if order_book["asks"] else last["close"]
        spread = (best_ask - best_bid) / max(best_bid, 1e-9)
        return MarketSnapshot(
            symbol=symbol,
            price=float(last["close"]),
            spread=float(spread),
            volatility=float(last["volatility20"]),
            momentum=float(last["rsi14"]),
            frame=frame,
        )
