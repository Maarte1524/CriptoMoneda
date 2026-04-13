from __future__ import annotations

import asyncio
from decimal import Decimal, ROUND_DOWN

from loguru import logger

from bot.config import ExecutionConfig
from bot.data_feed import BinanceGateway


class OrderManager:
    def __init__(self, gateway: BinanceGateway, cfg: ExecutionConfig, mode: str = "paper") -> None:
        self.gateway = gateway
        self.cfg = cfg
        self.mode = mode

    @staticmethod
    def quantize(value: float, step: float) -> float:
        return float((Decimal(str(value)) / Decimal(str(step))).quantize(0, rounding=ROUND_DOWN) * Decimal(str(step)))

    async def place_limit(self, symbol: str, side: str, qty: float, price: float) -> dict:
        if self.mode == "paper":
            return {"id": f"paper-{symbol}", "status": "closed", "filled": qty, "price": price}
        for i in range(self.cfg.max_retries):
            try:
                return await self.gateway.exchange.create_order(symbol, "limit", side, qty, price)
            except Exception as exc:
                wait = self.cfg.retry_backoff_base**i
                logger.warning(f"Order retry={i} {symbol} {side} error={exc}")
                await asyncio.sleep(wait)
        raise RuntimeError("place_limit_failed")

    async def place_market_exit(self, symbol: str, side: str, qty: float) -> dict:
        if self.mode == "paper":
            ticker = await self.gateway.fetch_ticker(symbol)
            return {"id": f"paper-exit-{symbol}", "status": "closed", "filled": qty, "price": ticker["last"]}
        return await self.gateway.exchange.create_order(symbol, "market", side, qty)
