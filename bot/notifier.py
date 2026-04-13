from __future__ import annotations

import asyncio
import os

from loguru import logger
from telegram import Bot


class Notifier:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.bot = Bot(token=token) if token else None

    async def notify(self, message: str) -> None:
        logger.info(message)
        if not self.enabled or not self.bot or not self.chat_id:
            return
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message)
        except Exception as exc:  # pragma: no cover
            logger.error(f"Telegram error: {exc}")

    def notify_sync(self, message: str) -> None:
        asyncio.run(self.notify(message))
