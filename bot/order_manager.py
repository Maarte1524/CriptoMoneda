from __future__ import annotations

import asyncio

from loguru import logger

from bot.utils import round_step


class OrderManager:
    def __init__(self, data_feed, execution_cfg):
        self.data_feed = data_feed
        self.cfg = execution_cfg

    async def place_entry_order(self, symbol: str, side: str, qty: float, price: float, step_size: float = 0.0001):
        rounded_qty = round_step(qty, step_size)
        params = {}
        order_side = "buy" if side == "long" else "sell"

        if self.cfg.default_order_type == "limit":
            order = await self.data_feed.exchange.create_order(symbol, "limit", order_side, rounded_qty, price, params)
            await asyncio.sleep(self.cfg.limit_order_timeout_seconds)
            refreshed = await self.data_feed.exchange.fetch_order(order["id"], symbol)
            if refreshed.get("status") != "closed":
                await self.data_feed.exchange.cancel_order(order["id"], symbol)
                logger.warning("Cancelled stale limit order {} {}", symbol, order["id"])
            return refreshed

        return await self.data_feed.exchange.create_order(symbol, "market", order_side, rounded_qty, None, params)

    async def emergency_exit(self, symbol: str, side: str, qty: float):
        close_side = "sell" if side == "long" else "buy"
        return await self.data_feed.exchange.create_order(symbol, "market", close_side, qty, None, {})
