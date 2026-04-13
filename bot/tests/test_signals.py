import pandas as pd

from bot.strategies.trend_following import generate_signal


def test_trend_following_long_signal() -> None:
    df = pd.DataFrame([
        {"close": 100, "ema200": 90, "ema20": 101, "ema50": 95, "adx": 25, "volume": 200, "vol_avg": 100}
    ])
    side, conf, _ = generate_signal(df)
    assert side == "long"
    assert conf > 0
