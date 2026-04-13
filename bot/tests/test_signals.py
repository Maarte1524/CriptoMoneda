import pandas as pd

from bot.strategies.trend_following import TrendFollowingStrategy


def test_trend_signal_returns_valid_signal() -> None:
    base = {
        "open": [100] * 250,
        "high": [101] * 250,
        "low": [99] * 250,
        "close": [100 + i * 0.1 for i in range(250)],
        "volume": [200] * 250,
        "ema20": [99 + i * 0.1 for i in range(250)],
        "ema50": [98 + i * 0.08 for i in range(250)],
        "ema200": [90 + i * 0.02 for i in range(250)],
        "rsi14": [55] * 250,
        "atr14": [1.0] * 250,
        "adx14": [25] * 250,
        "avg_volume20": [100] * 250,
    }
    frame = pd.DataFrame(base)
    strategy = TrendFollowingStrategy()
    signal = strategy.evaluate(frame, frame, frame)
    assert signal.signal in {"long", "short", "flat"}
