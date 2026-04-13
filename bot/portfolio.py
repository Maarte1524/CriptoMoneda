from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Position:
    symbol: str
    side: str
    qty: float
    entry_price: float
    stop_loss: float
    take_profit: float


class Portfolio:
    def __init__(self, starting_equity: float):
        self.equity = starting_equity
        self.positions: dict[str, Position] = {}
        self.closed_pnls: list[float] = []

    def open_position(self, position: Position) -> None:
        self.positions[position.symbol] = position

    def close_position(self, symbol: str, exit_price: float) -> float:
        pos = self.positions.pop(symbol)
        sign = 1 if pos.side == "long" else -1
        pnl = (exit_price - pos.entry_price) * pos.qty * sign
        self.equity += pnl
        self.closed_pnls.append(pnl)
        return pnl
