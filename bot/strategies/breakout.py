from __future__ import annotations

import pandas as pd


def generate_signal(df: pd.DataFrame) -> tuple[str, float, str]:
    recent = df.iloc[-20:]
    row = df.iloc[-1]
    donchian_high = recent['high'].max()
    donchian_low = recent['low'].min()
    vol_ok = row['volume'] > row['vol_ma20'] * 1.2
    atr_expanding = row['atr14'] > df.iloc[-5:]['atr14'].mean()

    if row['close'] >= donchian_high and vol_ok and atr_expanding:
        return 'long', 0.8, 'donchian_breakout_up'
    if row['close'] <= donchian_low and vol_ok and atr_expanding:
        return 'short', 0.8, 'donchian_breakout_down'
    return 'flat', 0.0, 'no_signal'
