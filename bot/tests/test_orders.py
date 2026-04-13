import pytest

from bot.config import ExecutionConfig
from bot.order_manager import OrderManager


class DummyExchange:
    async def load_markets(self):
        return {
            "BTC/USDT": {
                "precision": {"amount": 3, "price": 2},
                "limits": {"amount": {"min": 0.001}, "cost": {"min": 5}},
            }
        }


class DummyGateway:
    def __init__(self):
        self.exchange = DummyExchange()

    async def fetch_ticker(self, symbol: str):
        return {"last": 100}


def test_quantize() -> None:
    assert OrderManager.quantize(1.2345, 0.01) == 1.23


@pytest.mark.asyncio
async def test_paper_market_exit() -> None:
    om = OrderManager(DummyGateway(), ExecutionConfig(), mode="paper")
    result = await om.place_market_exit("BTC/USDT", "sell", 1)
    assert result["status"] == "closed"
