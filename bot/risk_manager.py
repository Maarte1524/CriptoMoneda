from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from bot.config import RiskConfig
from bot.portfolio import Portfolio
from bot.utils import utc_now


@dataclass
class RiskDecision:
    approved: bool
    reason: str


class RiskManager:
    def __init__(self, cfg: RiskConfig) -> None:
        self.cfg = cfg
        self.daily_start_equity: float | None = None
        self.weekly_start_equity: float | None = None
        self.cooldowns: dict[str, object] = {}
        self.kill_switch = False

    def reset_periods_if_needed(self, equity: float) -> None:
        now = utc_now()
        if self.daily_start_equity is None:
            self.daily_start_equity = equity
        if self.weekly_start_equity is None:
            self.weekly_start_equity = equity
        if now.weekday() == 0 and now.hour == 0:
            self.weekly_start_equity = equity

    def check_circuit_breakers(self, portfolio: Portfolio) -> RiskDecision:
        self.reset_periods_if_needed(portfolio.equity)
        daily_dd = (portfolio.equity - float(self.daily_start_equity)) / float(self.daily_start_equity)
        weekly_dd = (portfolio.equity - float(self.weekly_start_equity)) / float(self.weekly_start_equity)
        if daily_dd <= self.cfg.daily_drawdown_limit:
            return RiskDecision(False, f"daily_drawdown_limit_hit:{daily_dd:.3f}")
        if weekly_dd <= self.cfg.weekly_drawdown_limit:
            return RiskDecision(False, f"weekly_drawdown_limit_hit:{weekly_dd:.3f}")
        if self.kill_switch:
            return RiskDecision(False, "kill_switch_active")
        return RiskDecision(True, "ok")

    def pre_trade_check(self, portfolio: Portfolio, symbol: str) -> RiskDecision:
        if len(portfolio.open_positions) >= self.cfg.max_open_positions:
            return RiskDecision(False, "max_open_positions")
        c = portfolio.consecutive_losses_by_symbol.get(symbol, 0)
        if c >= self.cfg.consecutive_losses_for_cooldown:
            until = utc_now() + timedelta(hours=self.cfg.cooldown_hours)
            self.cooldowns[symbol] = until
            return RiskDecision(False, f"cooldown_active_{symbol}")
        if symbol in self.cooldowns and utc_now() < self.cooldowns[symbol]:
            return RiskDecision(False, f"cooldown_active_{symbol}")
        return self.check_circuit_breakers(portfolio)

    def position_size(
        self,
        equity: float,
        entry: float,
        stop_loss: float,
        atr: float,
        confidence: float,
        volatility: float,
    ) -> float:
        risk_budget = equity * self.cfg.risk_per_trade
        stop_dist = max(abs(entry - stop_loss), atr * 0.8)
        raw_qty = risk_budget / stop_dist if stop_dist else 0
        vol_factor = max(0.4, 1 - (volatility * 4))
        conf_factor = max(0.5, min(1.2, confidence))
        return max(0.0, raw_qty * vol_factor * conf_factor)

    def trigger_kill_switch(self) -> None:
        self.kill_switch = True
