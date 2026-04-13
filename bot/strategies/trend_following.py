from __future__ import annotations

import pandas as pd


def generate_signal(df: pd.DataFrame) -> tuple[str, float, str]:
    row = df.iloc[-1]
    prev = df.iloc[-2]
    vol_ok = row['volume'] > row['vol_ma20']
    adx_ok = row['adx'] >= 18

    if row['close'] > row['ema200'] and prev['ema20'] <= prev['ema50'] and row['ema20'] > row['ema50'] and vol_ok and adx_ok:
        return 'long', 0.9, 'ema_bull_cross_adx_volume'
    if row['close'] < row['ema200'] and prev['ema20'] >= prev['ema50'] and row['ema20'] < row['ema50'] and vol_ok and adx_ok:
        return 'short', 0.9, 'ema_bear_cross_adx_volume'
    return 'flat', 0.0, 'no_signal'
