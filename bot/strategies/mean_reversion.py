from __future__ import annotations

import pandas as pd


def generate_signal(df: pd.DataFrame) -> tuple[str, float, str]:
    row = df.shift(1).iloc[-1]
    if row["adx"] > 18:
        return "flat", 0.0, "avoid_mean_reversion_in_trend"
    if row["close"] < row["bb_low"] and row["rsi"] < 35 and row["close"] < row["vwap"]:
        return "long", 0.65, "bb_rsi_vwap_oversold"
    if row["close"] > row["bb_high"] and row["rsi"] > 65 and row["close"] > row["vwap"]:
        return "short", 0.65, "bb_rsi_vwap_overbought"
    return "flat", 0.0, "no_edge"
