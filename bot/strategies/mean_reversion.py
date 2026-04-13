from __future__ import annotations

import pandas as pd


def generate_signal(df: pd.DataFrame) -> tuple[str, float, str]:
    row = df.iloc[-1]
    if row['adx'] > 20:
        return 'flat', 0.0, 'trend_too_strong'
    if row['close'] < row['bb_l'] and row['rsi14'] < 35 and row['close'] < row['vwap']:
        return 'long', 0.7, 'bb_rsi_vwap_reversion'
    if row['close'] > row['bb_h'] and row['rsi14'] > 65 and row['close'] > row['vwap']:
        return 'short', 0.7, 'bb_rsi_vwap_reversion'
    return 'flat', 0.0, 'no_signal'
