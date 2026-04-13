from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_schema()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    qty REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    status TEXT NOT NULL,
                    pnl REAL DEFAULT 0,
                    reason TEXT
                );

                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    score REAL NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    level TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                """
            )
