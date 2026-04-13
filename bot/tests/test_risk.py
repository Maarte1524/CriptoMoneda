from bot.config import RiskConfig
from bot.portfolio import Portfolio
from bot.risk_manager import RiskManager


def test_position_size_positive() -> None:
    rm = RiskManager(RiskConfig())
    qty = rm.position_size(10000, 100, 97, 2, 0.8, 0.03)
    assert qty > 0


def test_pre_trade_max_positions() -> None:
    rm = RiskManager(RiskConfig(max_open_positions=1))
    p = Portfolio()
    p.open_positions = {"BTC/USDT": object()}  # type: ignore[assignment]
    assert rm.pre_trade_check(p, "ETH/USDT").approved is False
