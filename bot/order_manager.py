from __future__ import annotations

from dataclasses import dataclass

from bot.utils import quantize


@dataclass
class SymbolRules:
    tick_size: float
    lot_size: float
    min_qty: float
    min_notional: float


class OrderManager:
    def __init__(self) -> None:
        self.open_orders: dict[str, dict] = {}

    def normalize(self, price: float, qty: float, rules: SymbolRules) -> tuple[float, float]:
        q_price = quantize(price, rules.tick_size)
        q_qty = max(quantize(qty, rules.lot_size), rules.min_qty)
        return q_price, q_qty

    def validate(self, price: float, qty: float, rules: SymbolRules) -> tuple[bool, str]:
        if qty < rules.min_qty:
            return False, 'qty_below_min_qty'
        if price * qty < rules.min_notional:
            return False, 'notional_below_min_notional'
        return True, 'ok'
