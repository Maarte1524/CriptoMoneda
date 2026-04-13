from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class BacktestResult:
    total_return: float
    cagr: float
    sharpe: float
    sortino: float
    max_drawdown: float
    win_rate: float
    avg_win_loss: float
    profit_factor: float
    expectancy: float
    trades: int


class Backtester:
    def __init__(self, fee_bps: int, slippage_bps: int, spread_bps: int) -> None:
        self.fee = fee_bps / 10_000
        self.slippage = slippage_bps / 10_000
        self.spread = spread_bps / 10_000

    def run(self, df: pd.DataFrame, signals: pd.Series) -> BacktestResult:
        # Anti-lookahead: la orden ejecuta en vela i usando señal cerrada de i-1
        exec_signals = signals.shift(1).fillna("flat")
        rets = []
        pos = 0
        for i in range(1, len(df)):
            if exec_signals.iloc[i] == "long":
                pos = 1
            elif exec_signals.iloc[i] == "short":
                pos = -1
            gross = pos * ((df["close"].iloc[i] / df["close"].iloc[i - 1]) - 1)
            cost = (self.fee + self.slippage + self.spread) if exec_signals.iloc[i] != "flat" else 0
            rets.append(gross - cost)

        r = pd.Series(rets).fillna(0)
        equity = (1 + r).cumprod()
        total_return = equity.iloc[-1] - 1 if len(equity) else 0
        years = max(len(r) / (365 * 24 * 4), 1 / 365)
        cagr = (1 + total_return) ** (1 / years) - 1 if total_return > -1 else -1
        sharpe = (r.mean() / r.std() * math.sqrt(365 * 24 * 4)) if r.std() > 0 else 0
        downside = r[r < 0]
        sortino = (r.mean() / downside.std() * math.sqrt(365 * 24 * 4)) if downside.std() > 0 else 0
        dd = (equity / equity.cummax() - 1).min() if len(equity) else 0
        wins = r[r > 0]
        losses = r[r < 0]
        win_rate = len(wins) / len(r[r != 0]) if len(r[r != 0]) else 0
        avg_win_loss = abs(wins.mean() / losses.mean()) if len(wins) and len(losses) else 0
        profit_factor = abs(wins.sum() / losses.sum()) if len(losses) else np.inf
        expectancy = r.mean()
        trades = len(r[r != 0])
        return BacktestResult(total_return, cagr, sharpe, sortino, float(dd), win_rate, avg_win_loss, float(profit_factor), expectancy, trades)
