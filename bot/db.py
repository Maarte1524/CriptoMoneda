from __future__ import annotations

from pathlib import Path
from typing import Any

import aiosqlite


class DB:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def init(self) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    entry_reason TEXT,
                    exit_reason TEXT,
                    qty REAL NOT NULL,
                    entry REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    exit REAL,
                    pnl REAL,
                    status TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    context TEXT NOT NULL,
                    discarded_reason TEXT
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    level TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                """
            )
            await conn.commit()

    async def execute(self, sql: str, params: tuple[Any, ...]) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(sql, params)
            await conn.commit()

    async def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute(sql, params)
            rows = await cur.fetchall()
            return rows
