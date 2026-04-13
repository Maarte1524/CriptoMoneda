from __future__ import annotations

import pandas as pd

from bot.strategies import breakout, mean_reversion, trend_following


STRATEGIES = {
    'trend_following': trend_following.generate_signal,
    'mean_reversion': mean_reversion.generate_signal,
    'breakout': breakout.generate_signal,
}


def generate_signal(df: pd.DataFrame, weights: dict[str, float] | None = None) -> tuple[str, float, str]:
    weights = weights or {k: 1.0 for k in STRATEGIES}
    votes: dict[str, float] = {'long': 0.0, 'short': 0.0}
    reasons: list[str] = []
    for name, fn in STRATEGIES.items():
        side, score, reason = fn(df)
        reasons.append(f'{name}:{side}:{reason}')
        if side in votes:
            votes[side] += score * weights.get(name, 1.0)

    if votes['long'] >= 1.4 and votes['long'] > votes['short']:
        return 'long', min(votes['long'] / 3, 1.0), ';'.join(reasons)
    if votes['short'] >= 1.4 and votes['short'] > votes['long']:
        return 'short', min(votes['short'] / 3, 1.0), ';'.join(reasons)
    return 'flat', 0.0, ';'.join(reasons)
