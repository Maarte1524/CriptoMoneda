from __future__ import annotations

import pandas as pd

from bot.strategies.base import Strategy, StrategySignal


class MeanReversionStrategy(Strategy):
    name = "mean_reversion"

    def evaluate(self, frame_15m: pd.DataFrame, frame_1h: pd.DataFrame, frame_4h: pd.DataFrame) -> StrategySignal:
        row = frame_15m.iloc[-1]
        atr = float(row["atr14"])
        if row["adx14"] > 18:
            return StrategySignal("flat", 0.0, "Strong trend detected; mean reversion disabled", 0.0, 0.0)

        if row["close"] < row["bb_lower"] and row["rsi14"] < 35 and row["close"] < row["vwap"]:
            sl = float(row["close"] - 1.2 * atr)
            tp = float(row["sma20"])
            return StrategySignal("long", 0.68, "Lower band oversold reversion", sl, tp)

        if row["close"] > row["bb_upper"] and row["rsi14"] > 65 and row["close"] > row["vwap"]:
            sl = float(row["close"] + 1.2 * atr)
            tp = float(row["sma20"])
            return StrategySignal("short", 0.68, "Upper band overbought reversion", sl, tp)

        return StrategySignal("flat", 0.0, "No mean-reversion edge", 0.0, 0.0)
