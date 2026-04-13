from __future__ import annotations

import pandas as pd

from bot.strategies.base import Strategy, StrategySignal


class TrendFollowingStrategy(Strategy):
    name = "trend_following"

    def evaluate(self, frame_15m: pd.DataFrame, frame_1h: pd.DataFrame, frame_4h: pd.DataFrame) -> StrategySignal:
        row = frame_15m.iloc[-1]
        prev = frame_15m.iloc[-2]
        bullish_context = frame_1h.iloc[-1]["close"] > frame_1h.iloc[-1]["ema200"] and frame_4h.iloc[-1]["close"] > frame_4h.iloc[-1]["ema200"]
        bearish_context = frame_1h.iloc[-1]["close"] < frame_1h.iloc[-1]["ema200"] and frame_4h.iloc[-1]["close"] < frame_4h.iloc[-1]["ema200"]

        volume_ok = row["volume"] > row["avg_volume20"]
        adx_ok = row["adx14"] >= 20
        atr = float(row["atr14"])

        if row["close"] > row["ema200"] and prev["ema20"] <= prev["ema50"] and row["ema20"] > row["ema50"] and row["rsi14"] > 50 and bullish_context and volume_ok and adx_ok:
            sl = float(row["close"] - (1.5 * atr))
            tp = float(row["close"] + (3.0 * atr))
            return StrategySignal("long", 0.82, "EMA cross + ADX + volume + HTF trend", sl, tp)

        if row["close"] < row["ema200"] and prev["ema20"] >= prev["ema50"] and row["ema20"] < row["ema50"] and row["rsi14"] < 50 and bearish_context and volume_ok and adx_ok:
            sl = float(row["close"] + (1.5 * atr))
            tp = float(row["close"] - (3.0 * atr))
            return StrategySignal("short", 0.82, "EMA bearish cross + ADX + volume + HTF trend", sl, tp)

        return StrategySignal("flat", 0.0, "No trend-following edge", 0.0, 0.0)
