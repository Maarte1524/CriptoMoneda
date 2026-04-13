import pytest

pytest.importorskip('pydantic')

from bot.config import RiskConfig
from bot.portfolio import Portfolio
from bot.risk_manager import RiskManager


def test_daily_circuit_breaker_blocks_new_trades() -> None:
    cfg = RiskConfig(daily_drawdown_limit=-0.03)
    rm = RiskManager(cfg)
    pf = Portfolio()
    pf.daily_pnl = -500
    can_open, reason = rm.can_open(pf, 'BTCUSDT', 0)
    assert not can_open
    assert reason == 'daily_circuit_breaker'
