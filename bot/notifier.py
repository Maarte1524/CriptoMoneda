from __future__ import annotations

import asyncio

from loguru import logger


class Notifier:
    def __init__(self, enabled_console: bool = True):
        self.enabled_console = enabled_console

    async def send(self, message: str) -> None:
        if self.enabled_console:
            logger.info(message)
        await asyncio.sleep(0)
