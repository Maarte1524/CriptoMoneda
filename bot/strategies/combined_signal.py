from __future__ import annotations

from collections import Counter

import pandas as pd

from bot.strategies import breakout, mean_reversion, trend_following


STRATEGY_WEIGHT = {
    "trend_following": 1.1,
    "breakout": 1.0,
    "mean_reversion": 0.9,
}


def generate_signal(df: pd.DataFrame) -> tuple[str, float, str]:
    votes: list[tuple[str, float, str, str]] = []
    for name, fn in {
        "trend_following": trend_following.generate_signal,
        "breakout": breakout.generate_signal,
        "mean_reversion": mean_reversion.generate_signal,
    }.items():
        side, conf, reason = fn(df)
        if side != "flat":
            votes.append((side, conf * STRATEGY_WEIGHT[name], reason, name))

    if len(votes) < 2:
        return "flat", 0.0, "need_2_of_3_alignment"

    side_counts = Counter(v[0] for v in votes)
    top_side, count = side_counts.most_common(1)[0]
    if count < 2:
        return "flat", 0.0, "conflicting_signals"

    confidence = sum(v[1] for v in votes if v[0] == top_side) / count
    reasons = ",".join(v[2] for v in votes if v[0] == top_side)
    return top_side, float(min(confidence, 0.95)), f"combined:{reasons}"
