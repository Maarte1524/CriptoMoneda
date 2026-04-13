from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, SecretStr, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    binance_api_key: SecretStr = Field(alias="BINANCE_API_KEY")
    binance_api_secret: SecretStr = Field(alias="BINANCE_API_SECRET")
    telegram_bot_token: SecretStr | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = Field(default=None, alias="TELEGRAM_CHAT_ID")
    mode: Literal["paper", "testnet", "live"] = Field(default="paper", alias="MODE")


class RiskConfig(BaseModel):
    risk_per_trade: float = 0.01
    max_open_positions: int = 4
    max_exposure_per_asset: float = 0.25
    max_total_exposure: float = 0.85
    daily_drawdown_limit: float = -0.03
    weekly_drawdown_limit: float = -0.07
    cooldown_hours_after_3_losses: int = 24
    panic_equity_drop_pct: float = 0.1


class ExecutionConfig(BaseModel):
    default_order_type: Literal["limit", "market"] = "limit"
    limit_order_timeout_seconds: int = 45
    max_slippage_bps: int = 8
    retry_attempts: int = 5
    retry_backoff_seconds: float = 1.5


class AlertConfig(BaseModel):
    telegram_enabled: bool = True
    console_enabled: bool = True


class BacktestConfig(BaseModel):
    fee_bps: float = 10.0
    slippage_bps: float = 6.0
    initial_capital: float = 10000.0
    min_trades_for_confidence: int = 200


class TimeframeConfig(BaseModel):
    execution: str = "15m"
    confirm: list[str] = Field(default_factory=lambda: ["1h", "4h"])


class BotConfig(BaseModel):
    pairs: list[str]
    mode: Literal["paper", "testnet", "live"] = "paper"
    strategy: str = "combined_signal"
    market_type: Literal["spot", "futures"] = "spot"
    use_testnet: bool = True
    timeframes: TimeframeConfig = Field(default_factory=TimeframeConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    alerts: AlertConfig = Field(default_factory=AlertConfig)
    backtesting: BacktestConfig = Field(default_factory=BacktestConfig)
    data_dir: Path = Path("data")
    log_dir: Path = Path("logs")
    db_path: Path = Path("data/trading.db")

    @model_validator(mode="after")
    def ensure_paths(self) -> "BotConfig":
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return self


def load_config(path: str | Path = "config.yaml") -> tuple[EnvSettings, BotConfig]:
    load_dotenv()
    try:
        env = EnvSettings()
    except ValidationError as exc:
        raise RuntimeError(f"Invalid .env configuration: {exc}") from exc

    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"config file not found: {cfg_path}")

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    try:
        bot_cfg = BotConfig(**raw)
    except ValidationError as exc:
        raise RuntimeError(f"Invalid config.yaml configuration: {exc}") from exc

    if env.mode != bot_cfg.mode:
        bot_cfg.mode = env.mode

    return env, bot_cfg
