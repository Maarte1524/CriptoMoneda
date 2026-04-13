from __future__ import annotations

import pandas as pd

from bot.strategies.base import Strategy, StrategySignal


class BreakoutStrategy(Strategy):
    name = "breakout"

    def evaluate(self, frame_15m: pd.DataFrame, frame_1h: pd.DataFrame, frame_4h: pd.DataFrame) -> StrategySignal:
        row = frame_15m.iloc[-1]
        lookback = frame_15m.tail(21)
        prev_max = float(lookback["high"].iloc[:-1].max())
        prev_min = float(lookback["low"].iloc[:-1].min())
        atr = float(row["atr14"])
        volume_multiplier = row["volume"] / max(row["avg_volume20"], 1e-9)

        if row["close"] > prev_max and volume_multiplier > 1.4 and row["atr14"] > frame_15m["atr14"].tail(50).mean():
            sl = float(row["close"] - 1.5 * atr)
            tp = float(row["close"] + 3.0 * atr)
            return StrategySignal("long", 0.76, "Range breakout with volume/ATR confirmation", sl, tp)

        if row["close"] < prev_min and volume_multiplier > 1.4 and row["atr14"] > frame_15m["atr14"].tail(50).mean():
            sl = float(row["close"] + 1.5 * atr)
            tp = float(row["close"] - 3.0 * atr)
            return StrategySignal("short", 0.76, "Breakdown with volume/ATR confirmation", sl, tp)

        return StrategySignal("flat", 0.0, "No breakout edge", 0.0, 0.0)
