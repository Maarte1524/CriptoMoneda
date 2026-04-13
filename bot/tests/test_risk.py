from bot.risk_manager import RiskManager


class DummyCfg:
    risk_per_trade = 0.01
    max_open_positions = 4
    max_exposure_per_asset = 0.25
    max_total_exposure = 0.85
    daily_drawdown_limit = -0.03
    weekly_drawdown_limit = -0.07
    cooldown_hours_after_3_losses = 24


def test_position_size_is_positive() -> None:
    rm = RiskManager(DummyCfg())
    qty = rm.compute_position_size(10000, 100, 98, 0.8, 0.01)
    assert qty > 0
