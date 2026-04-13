from __future__ import annotations

import asyncio
from typing import Any

import ccxt.async_support as ccxt
import pandas as pd
from ta.trend import ADXIndicator, EMAIndicator, MACD, SMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands
from ta.momentum import RSIIndicator


class BinanceDataFeed:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False) -> None:
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'},
        })
        if testnet:
            self.exchange.set_sandbox_mode(True)

    async def load_markets(self) -> None:
        await self.exchange.load_markets()

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        rows = await self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(rows, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ms', utc=True)
        return self._add_indicators(df)

    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['ema20'] = EMAIndicator(df['close'], 20).ema_indicator()
        df['ema50'] = EMAIndicator(df['close'], 50).ema_indicator()
        df['ema200'] = EMAIndicator(df['close'], 200).ema_indicator()
        df['sma20'] = SMAIndicator(df['close'], 20).sma_indicator()
        df['rsi14'] = RSIIndicator(df['close'], 14).rsi()
        df['atr14'] = AverageTrueRange(df['high'], df['low'], df['close'], 14).average_true_range()
        macd = MACD(df['close'])
        df['macd'] = macd.macd_diff()
        df['adx'] = ADXIndicator(df['high'], df['low'], df['close']).adx()
        bb = BollingerBands(df['close'], window=20, window_dev=2)
        df['bb_h'] = bb.bollinger_hband()
        df['bb_l'] = bb.bollinger_lband()
        df['vol_ma20'] = df['volume'].rolling(20).mean()
        df['vwap'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()
        return df

    async def safe_close(self) -> None:
        await self.exchange.close()

    async def retry(self, coro, attempts: int = 5, delay: float = 0.5) -> Any:
        for i in range(attempts):
            try:
                return await coro()
            except Exception:
                if i == attempts - 1:
                    raise
                await asyncio.sleep(delay * (2 ** i))
