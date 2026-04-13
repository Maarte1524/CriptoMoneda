from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def quantize(value: float, step: float) -> float:
    return float((Decimal(str(value)) / Decimal(str(step))).to_integral_value(rounding=ROUND_DOWN) * Decimal(str(step)))


def rr_from_prices(entry: float, stop: float, take: float, side: str) -> float:
    risk = abs(entry - stop)
    reward = (take - entry) if side == 'long' else (entry - take)
    return reward / risk if risk else 0.0
