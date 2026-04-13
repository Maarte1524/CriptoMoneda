from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd


SignalType = Literal["long", "short", "flat"]


@dataclass(slots=True)
class StrategySignal:
    signal: SignalType
    score: float
    reason: str
    stop_loss: float
    take_profit: float


class Strategy:
    name: str = "base"

    def evaluate(self, frame_15m: pd.DataFrame, frame_1h: pd.DataFrame, frame_4h: pd.DataFrame) -> StrategySignal:
        raise NotImplementedError
