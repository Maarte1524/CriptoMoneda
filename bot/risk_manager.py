from __future__ import annotations

from collections import defaultdict

from bot.config import RiskConfig
from bot.portfolio import Portfolio


class RiskManager:
    def __init__(self, cfg: RiskConfig) -> None:
        self.cfg = cfg
        self.loss_streak: dict[str, int] = defaultdict(int)
        self.cooldown_until: dict[str, int] = {}

    def can_open(self, portfolio: Portfolio, symbol: str, ts_epoch: int) -> tuple[bool, str]:
        if len(portfolio.positions) >= self.cfg.max_open_positions:
            return False, 'max_open_positions'
        if portfolio.daily_pnl / max(portfolio.initial_equity, 1) <= self.cfg.daily_drawdown_limit:
            return False, 'daily_circuit_breaker'
        if portfolio.weekly_pnl / max(portfolio.initial_equity, 1) <= self.cfg.weekly_drawdown_limit:
            return False, 'weekly_circuit_breaker'
        if symbol in self.cooldown_until and ts_epoch < self.cooldown_until[symbol]:
            return False, 'symbol_cooldown'
        return True, 'ok'

    def size_position(self, equity: float, entry: float, stop: float, signal_score: float, vol_factor: float) -> float:
        risk_capital = equity * self.cfg.risk_per_trade
        distance = abs(entry - stop)
        if distance <= 0:
            return 0.0
        quality_factor = min(max(signal_score, 0.5), 1.5)
        vol_adjust = min(max(vol_factor, 0.5), 1.5)
        return (risk_capital * quality_factor / vol_adjust) / distance

    def register_trade_result(self, symbol: str, pnl: float, ts_epoch: int) -> None:
        if pnl < 0:
            self.loss_streak[symbol] += 1
            if self.loss_streak[symbol] >= self.cfg.consecutive_losses_for_cooldown:
                self.cooldown_until[symbol] = ts_epoch + self.cfg.cooldown_hours * 3600
        else:
            self.loss_streak[symbol] = 0
