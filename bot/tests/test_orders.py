from bot.order_manager import OrderManager, SymbolRules


def test_order_validation_min_notional() -> None:
    om = OrderManager()
    rules = SymbolRules(tick_size=0.1, lot_size=0.001, min_qty=0.001, min_notional=10)
    ok, reason = om.validate(price=100, qty=0.001, rules=rules)
    assert not ok
    assert reason == 'notional_below_min_notional'
