from __future__ import annotations

import asyncio
import signal
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger


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
    logger.add(
        Path(log_dir) / "bot.log",
        level="INFO",
        rotation="25 MB",
        retention="14 days",
        enqueue=True,
        serialize=False,
    )
    logger.add(
        Path(log_dir) / "bot.json.log",
        level="INFO",
        rotation="25 MB",
        retention="14 days",
        enqueue=True,
        serialize=True,
    )
