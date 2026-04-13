from __future__ import annotations

import asyncio
import os
import re
import signal
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

SECRET_PATTERNS = [
    re.compile(r"(BINANCE_API_KEY=)([^\s]+)"),
    re.compile(r"(BINANCE_API_SECRET=)([^\s]+)"),
    re.compile(r"(TELEGRAM_BOT_TOKEN=)([^\s]+)"),
]


def sanitize(text: str) -> str:
    safe = text
    for pattern in SECRET_PATTERNS:
        safe = pattern.sub(r"\1***", safe)
    for env_key in ["BINANCE_API_KEY", "BINANCE_API_SECRET", "TELEGRAM_BOT_TOKEN"]:
        val = os.getenv(env_key)
        if val:
            safe = safe.replace(val, "***")
    return safe


class GracefulShutdown:
    def __init__(self) -> None:
        self.stop_event = asyncio.Event()

    def install(self) -> None:
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._handler)

    def _handler(self, signum, _frame) -> None:  # type: ignore[no-untyped-def]
        logger.warning(f"Signal received: {signum}. Stopping bot safely.")
        self.stop_event.set()


def utc_now() -> datetime:
    return datetime.now(UTC)


def setup_logging(log_dir: str) -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    logger.remove()

    def patch(record: dict) -> None:
        record["message"] = sanitize(record["message"])

    patched = logger.patch(patch)
    patched.add(
        Path(log_dir) / "bot.log",
        level="INFO",
        rotation="25 MB",
        retention="14 days",
        enqueue=True,
        serialize=False,
    )
    patched.add(
        Path(log_dir) / "bot.json.log",
        level="INFO",
        rotation="25 MB",
        retention="14 days",
        enqueue=True,
        serialize=True,
    )
