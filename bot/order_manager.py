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
        if step <= 0:
            return value
        return float((Decimal(str(value)) / Decimal(str(step))).quantize(0, rounding=ROUND_DOWN) * Decimal(str(step)))

    async def normalize_order(self, symbol: str, qty: float, price: float) -> tuple[float, float]:
        markets = await self.gateway.exchange.load_markets()
        market = markets[symbol]
        step = float(market.get("precision", {}).get("amount") and 10 ** (-market["precision"]["amount"]) or 0.000001)
        tick = float(market.get("precision", {}).get("price") and 10 ** (-market["precision"]["price"]) or 0.000001)
        min_qty = float(market.get("limits", {}).get("amount", {}).get("min") or step)
        min_notional = float(market.get("limits", {}).get("cost", {}).get("min") or 5)

        qty_q = max(self.quantize(qty, step), min_qty)
        price_q = self.quantize(price, tick)
        if qty_q * price_q < min_notional:
            qty_q = self.quantize(min_notional / max(price_q, 1e-8), step)
        return qty_q, price_q

    async def place_limit(self, symbol: str, side: str, qty: float, price: float) -> dict:
        qty, price = await self.normalize_order(symbol, qty, price)
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
        qty, _ = await self.normalize_order(symbol, qty, 1.0)
        if self.mode == "paper":
            ticker = await self.gateway.fetch_ticker(symbol)
            return {"id": f"paper-exit-{symbol}", "status": "closed", "filled": qty, "price": ticker["last"]}
        return await self.gateway.exchange.create_order(symbol, "market", side, qty)
