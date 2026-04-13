from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from bot.strategies.combined_signal import generate_signal


@dataclass
class BacktestResult:
    total_return: float
    cagr: float
    sharpe: float
    sortino: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    expectancy: float
    trades: int


class Backtester:
    def run(self, df: pd.DataFrame, fee_bps: float = 8, slippage_bps: float = 5) -> BacktestResult:
        equity = 1.0
        curve: list[float] = [equity]
        pnls: list[float] = []
        for i in range(220, len(df) - 1):
            window = df.iloc[: i + 1]
            side, score, _ = generate_signal(window)
            if side == 'flat' or score < 0.5:
                curve.append(equity)
                continue
            ret = (df.iloc[i + 1]['close'] - df.iloc[i]['close']) / df.iloc[i]['close']
            if side == 'short':
                ret *= -1
            cost = (fee_bps + slippage_bps) / 10_000
            pnl = ret - cost
            equity *= (1 + pnl)
            pnls.append(pnl)
            curve.append(equity)

        arr = np.array(pnls) if pnls else np.array([0.0])
        mean = float(np.mean(arr))
        std = float(np.std(arr)) if float(np.std(arr)) > 1e-9 else 1.0
        downside = arr[arr < 0]
        dstd = float(np.std(downside)) if len(downside) else 1.0
        years = max(len(df) / (365 * 24 * 4), 1e-6)
        cagr = math.pow(max(equity, 1e-6), 1 / years) - 1
        peak = -1e9
        mdd = 0.0
        for v in curve:
            peak = max(peak, v)
            dd = (v - peak) / peak
            mdd = min(mdd, dd)
        wins = arr[arr > 0]
        losses = arr[arr < 0]
        pf = float(wins.sum() / abs(losses.sum())) if losses.sum() != 0 else 0.0
        wr = float(len(wins) / max(len(arr), 1))
        expectancy = float(arr.mean())
        return BacktestResult(
            total_return=equity - 1,
            cagr=cagr,
            sharpe=(mean / std) * math.sqrt(365 * 24 * 4),
            sortino=(mean / dstd) * math.sqrt(365 * 24 * 4),
            max_drawdown=mdd,
            win_rate=wr,
            profit_factor=pf,
            expectancy=expectancy,
            trades=len(pnls),
        )
