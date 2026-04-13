from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from bot.strategies.base import Strategy, StrategySignal


class CombinedSignalStrategy(Strategy):
    name = "combined_signal"

    def __init__(self, strategies: Iterable[Strategy]):
        self.strategies = list(strategies)

    def evaluate(self, frame_15m: pd.DataFrame, frame_1h: pd.DataFrame, frame_4h: pd.DataFrame) -> StrategySignal:
        votes = {"long": [], "short": []}
        for strategy in self.strategies:
            signal = strategy.evaluate(frame_15m, frame_1h, frame_4h)
            if signal.signal in ("long", "short"):
                votes[signal.signal].append(signal)

        for side in ("long", "short"):
            if len(votes[side]) >= 2:
                score = sum(s.score for s in votes[side]) / len(votes[side])
                best = max(votes[side], key=lambda s: s.score)
                reason = " + ".join(s.reason for s in votes[side])
                return StrategySignal(side, score, reason, best.stop_loss, best.take_profit)

        return StrategySignal("flat", 0.0, "Less than 2 aligned signals", 0.0, 0.0)
