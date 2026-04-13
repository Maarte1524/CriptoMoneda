from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from bot.utils import clamp


@dataclass(slots=True)
class OpenPosition:
    symbol: str
    side: str
    notional: float


@dataclass
class RiskState:
    equity_start_day: float
    equity_start_week: float
    consecutive_losses: dict[str, int] = field(default_factory=dict)
    cooldown_until: dict[str, datetime] = field(default_factory=dict)


class RiskManager:
    def __init__(self, risk_cfg):
        self.cfg = risk_cfg
        self.state = RiskState(equity_start_day=0.0, equity_start_week=0.0)

    def bootstrap(self, equity: float) -> None:
        self.state.equity_start_day = equity
        self.state.equity_start_week = equity

    def check_circuit_breakers(self, equity: float) -> tuple[bool, str]:
        day_return = (equity / max(self.state.equity_start_day, 1e-9)) - 1.0
        week_return = (equity / max(self.state.equity_start_week, 1e-9)) - 1.0
        if day_return <= self.cfg.daily_drawdown_limit:
            return False, "Daily drawdown circuit breaker triggered"
        if week_return <= self.cfg.weekly_drawdown_limit:
            return False, "Weekly drawdown circuit breaker triggered"
        return True, "Risk checks passed"

    def can_trade_symbol(self, symbol: str) -> tuple[bool, str]:
        now = datetime.now(UTC)
        if symbol in self.state.cooldown_until and now < self.state.cooldown_until[symbol]:
            return False, f"Symbol {symbol} cooling down until {self.state.cooldown_until[symbol]}"
        return True, "Symbol allowed"

    def validate_portfolio_exposure(
        self,
        equity: float,
        symbol: str,
        new_notional: float,
        open_positions: list[OpenPosition],
    ) -> tuple[bool, str]:
        if len(open_positions) >= self.cfg.max_open_positions:
            return False, "Max open positions reached"

        total_open_notional = sum(p.notional for p in open_positions)
        symbol_open_notional = sum(p.notional for p in open_positions if p.symbol == symbol)

        new_total_exposure = (total_open_notional + new_notional) / max(equity, 1e-9)
        new_symbol_exposure = (symbol_open_notional + new_notional) / max(equity, 1e-9)

        if new_symbol_exposure > self.cfg.max_exposure_per_asset:
            return False, "Per-asset exposure exceeded"
        if new_total_exposure > self.cfg.max_total_exposure:
            return False, "Total exposure exceeded"
        return True, "Exposure checks passed"

    def compute_position_size(
        self,
        equity: float,
        entry: float,
        stop: float,
        signal_score: float,
        volatility: float,
    ) -> float:
        risk_budget = equity * self.cfg.risk_per_trade
        stop_distance = abs(entry - stop)
        raw_qty = risk_budget / max(stop_distance, 1e-9)

        score_factor = clamp(signal_score, 0.4, 1.0)
        vol_factor = clamp(1.0 - (volatility * 4.0), 0.35, 1.0)
        qty = raw_qty * score_factor * vol_factor
        return max(qty, 0.0)

    def register_trade_result(self, symbol: str, pnl: float) -> None:
        losses = self.state.consecutive_losses.get(symbol, 0)
        if pnl < 0:
            losses += 1
            self.state.consecutive_losses[symbol] = losses
            if losses >= 3:
                self.state.cooldown_until[symbol] = datetime.now(UTC) + timedelta(hours=self.cfg.cooldown_hours_after_3_losses)
        else:
            self.state.consecutive_losses[symbol] = 0
