from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator


class RiskConfig(BaseModel):
    risk_per_trade: float = Field(default=0.01, gt=0, le=0.02)
    max_open_positions: int = 4
    max_exposure_per_pair: float = 0.25
    max_total_exposure: float = 0.8
    daily_drawdown_limit: float = -0.03
    weekly_drawdown_limit: float = -0.07
    consecutive_losses_for_cooldown: int = 3
    cooldown_hours: int = 24
    atr_stop_multiple: float = 1.5
    min_rr: float = 2.0
    trail_activation_r: float = 1.5


class ExecutionConfig(BaseModel):
    limit_offset_bps: int = 3
    max_slippage_bps: int = 15
    order_timeout_seconds: int = 45
    max_retries: int = 5
    retry_backoff_base: float = 1.8


class AlertConfig(BaseModel):
    telegram_enabled: bool = True
    console_enabled: bool = True


class BacktestConfig(BaseModel):
    fee_bps: int = 10
    slippage_bps: int = 5
    spread_bps: int = 2
    min_trades_threshold: int = 200
    train_ratio: float = 0.6
    validation_ratio: float = 0.2


class AppConfig(BaseModel):
    mode: Literal["paper", "testnet", "live"] = "paper"
    market_type: Literal["spot", "futures"] = "spot"
    symbols: list[str]
    strategy: str = "combined_signal"
    timeframe_execution: str = "15m"
    timeframe_confirm_1: str = "1h"
    timeframe_confirm_2: str = "4h"
    db_path: str = "data/trading.db"
    log_dir: str = "logs"
    risk: RiskConfig = RiskConfig()
    execution: ExecutionConfig = ExecutionConfig()
    alerts: AlertConfig = AlertConfig()
    backtest: BacktestConfig = BacktestConfig()

    @model_validator(mode="after")
    def validate_ratios(self) -> "AppConfig":
        if (self.backtest.train_ratio + self.backtest.validation_ratio) >= 1:
            raise ValueError("train_ratio + validation_ratio must be < 1")
        return self


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    load_dotenv()
    with Path(path).open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return AppConfig(**raw)
