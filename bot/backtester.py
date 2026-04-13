from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from bot.strategies.base import Strategy


@dataclass(slots=True)
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
    def __init__(self, strategy: Strategy, fee_bps: float, slippage_bps: float, initial_capital: float):
        self.strategy = strategy
        self.fee_bps = fee_bps / 10_000
        self.slippage_bps = slippage_bps / 10_000
        self.initial_capital = initial_capital

    def run(self, frame_15m: pd.DataFrame, frame_1h: pd.DataFrame, frame_4h: pd.DataFrame) -> BacktestResult:
        equity = self.initial_capital
        equity_curve = [equity]
        pnls: list[float] = []

        for idx in range(210, len(frame_15m) - 2):
            signal = self.strategy.evaluate(frame_15m.iloc[: idx + 1], frame_1h, frame_4h)
            if signal.signal == "flat":
                equity_curve.append(equity)
                continue

            entry = float(frame_15m.iloc[idx + 1]["open"])
            exit_px = float(frame_15m.iloc[idx + 2]["close"])
            sign = 1 if signal.signal == "long" else -1
            gross = (exit_px - entry) * sign
            net = gross - (entry * (self.fee_bps + self.slippage_bps))
            pnl = net * 10
            equity += pnl
            pnls.append(pnl)
            equity_curve.append(equity)

        return self._metrics(np.array(equity_curve), np.array(pnls))

    def _metrics(self, equity_curve: np.ndarray, pnls: np.ndarray) -> BacktestResult:
        rets = np.diff(equity_curve) / np.maximum(equity_curve[:-1], 1e-9)
        downside = rets[rets < 0]
        years = max(len(rets) / (365 * 24 * 4), 1 / 365)
        total_return = float((equity_curve[-1] / equity_curve[0]) - 1)
        cagr = float((equity_curve[-1] / equity_curve[0]) ** (1 / years) - 1)
        sharpe = float((np.mean(rets) / (np.std(rets) + 1e-9)) * np.sqrt(365 * 24 * 4))
        sortino = float((np.mean(rets) / (np.std(downside) + 1e-9)) * np.sqrt(365 * 24 * 4))
        running_max = np.maximum.accumulate(equity_curve)
        drawdowns = (equity_curve / np.maximum(running_max, 1e-9)) - 1
        max_dd = float(drawdowns.min())
        wins = pnls[pnls > 0]
        losses = pnls[pnls < 0]
        win_rate = float((len(wins) / len(pnls)) if len(pnls) else 0.0)
        avg_win_loss = float((wins.mean() / abs(losses.mean())) if len(wins) and len(losses) else 0.0)
        profit_factor = float((wins.sum() / abs(losses.sum())) if len(losses) else 0.0)
        expectancy = float(pnls.mean()) if len(pnls) else 0.0

        return BacktestResult(
            total_return=total_return,
            cagr=cagr,
            sharpe=sharpe,
            sortino=sortino,
            max_drawdown=max_dd,
            win_rate=win_rate,
            avg_win_loss=avg_win_loss,
            profit_factor=profit_factor,
            expectancy=expectancy,
            trades=len(pnls),
        )
