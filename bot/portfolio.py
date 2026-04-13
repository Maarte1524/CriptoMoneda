from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Position:
    symbol: str
    side: str
    qty: float
    entry: float
    stop_loss: float
    take_profit: float
    strategy: str
    risk_r: float = 1.0


@dataclass
class Portfolio:
    equity: float = 10_000.0
    cash: float = 10_000.0
    open_positions: dict[str, Position] = field(default_factory=dict)
    closed_pnls: list[float] = field(default_factory=list)
    consecutive_losses_by_symbol: dict[str, int] = field(default_factory=dict)

    def register_close(self, symbol: str, pnl: float) -> None:
        self.closed_pnls.append(pnl)
        if pnl < 0:
            self.consecutive_losses_by_symbol[symbol] = self.consecutive_losses_by_symbol.get(symbol, 0) + 1
        else:
            self.consecutive_losses_by_symbol[symbol] = 0
        self.equity += pnl
        self.cash += pnl
