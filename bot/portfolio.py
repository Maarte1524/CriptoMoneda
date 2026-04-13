from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Position:
    symbol: str
    side: str
    qty: float
    entry: float
    stop: float
    take: float
    strategy: str


class Portfolio:
    def __init__(self, equity: float = 10_000.0) -> None:
        self.initial_equity = equity
        self.cash = equity
        self.positions: dict[str, Position] = {}
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0

    def upsert_position(self, pos: Position) -> None:
        self.positions[pos.symbol] = pos

    def close_position(self, symbol: str, exit_price: float) -> float:
        pos = self.positions.pop(symbol)
        pnl = (exit_price - pos.entry) * pos.qty if pos.side == 'long' else (pos.entry - exit_price) * pos.qty
        self.cash += pnl
        self.daily_pnl += pnl
        self.weekly_pnl += pnl
        return pnl

    @property
    def equity(self) -> float:
        return self.cash
