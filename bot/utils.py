from __future__ import annotations

import math
from datetime import UTC, datetime


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def round_step(value: float, step: float) -> float:
    if step <= 0:
        return value
    precision = max(0, int(round(-math.log10(step), 0)))
    stepped = math.floor(value / step) * step
    return round(stepped, precision)
