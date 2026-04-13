import pytest

pd = pytest.importorskip('pandas')

from bot.strategies.combined_signal import generate_signal


def test_combined_signal_returns_valid_side() -> None:
    df = pd.DataFrame({
        'high': [1 + i * 0.01 for i in range(260)],
        'low': [0.9 + i * 0.01 for i in range(260)],
        'close': [1 + i * 0.01 for i in range(260)],
        'volume': [1000 + i for i in range(260)],
        'ema20': [1 + i * 0.01 for i in range(260)],
        'ema50': [0.9 + i * 0.01 for i in range(260)],
        'ema200': [0.8 + i * 0.01 for i in range(260)],
        'sma20': [1 + i * 0.01 for i in range(260)],
        'rsi14': [55 for _ in range(260)],
        'atr14': [0.02 for _ in range(260)],
        'macd': [0.1 for _ in range(260)],
        'adx': [25 for _ in range(260)],
        'bb_h': [2 for _ in range(260)],
        'bb_l': [0.5 for _ in range(260)],
        'vol_ma20': [900 for _ in range(260)],
        'vwap': [1 for _ in range(260)],
    })
    side, _, _ = generate_signal(df)
    assert side in {'long', 'short', 'flat'}
