from __future__ import annotations

import pandas as pd


def generate_signal(df: pd.DataFrame) -> tuple[str, float, str]:
    row = df.shift(1).iloc[-1]
    prev = df.shift(1).iloc[-2]
    atr_expansion = row["atr"] > prev["atr"] * 1.02
    vol_ok = row["volume"] > row["vol_avg"] * 1.2
    if row["close"] > prev["donchian_high"] and atr_expansion and vol_ok:
        return "long", 0.7, "donchian_breakout_up"
    if row["close"] < prev["donchian_low"] and atr_expansion and vol_ok:
        return "short", 0.7, "donchian_breakout_down"
    return "flat", 0.0, "no_edge"
