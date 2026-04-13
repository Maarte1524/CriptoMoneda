from __future__ import annotations

import pandas as pd


def generate_signal(df: pd.DataFrame) -> tuple[str, float, str]:
    row = df.shift(1).iloc[-1]
    if row["close"] > row["ema200"] and row["ema20"] > row["ema50"] and row["adx"] > 20 and row["volume"] > row["vol_avg"]:
        return "long", 0.75, "trend_following_confirmed"
    if row["close"] < row["ema200"] and row["ema20"] < row["ema50"] and row["adx"] > 20 and row["volume"] > row["vol_avg"]:
        return "short", 0.75, "trend_following_confirmed"
    return "flat", 0.0, "no_edge"
