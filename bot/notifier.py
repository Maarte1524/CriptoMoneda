from __future__ import annotations

from loguru import logger
from telegram import Bot


class Notifier:
    def __init__(self, token: str | None, chat_id: str | None) -> None:
        self.chat_id = chat_id
        self.bot = Bot(token=token) if token else None

    async def send(self, msg: str) -> None:
        logger.info(msg)
        if self.bot and self.chat_id:
            try:
                await self.bot.send_message(chat_id=self.chat_id, text=msg)
            except Exception as exc:
                logger.warning(f'Telegram fallback consola: {exc}')
