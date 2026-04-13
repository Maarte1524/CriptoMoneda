from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    binance_api_key: SecretStr = Field(alias='BINANCE_API_KEY')
    binance_api_secret: SecretStr = Field(alias='BINANCE_API_SECRET')
    telegram_bot_token: SecretStr | None = Field(default=None, alias='TELEGRAM_BOT_TOKEN')
    telegram_chat_id: str | None = Field(default=None, alias='TELEGRAM_CHAT_ID')
    mode: Literal['paper', 'testnet', 'live'] = Field(default='paper', alias='MODE')


class RiskConfig(BaseModel):
    risk_per_trade: float = 0.01
    max_open_positions: int = 4
    max_exposure_per_symbol: float = 0.25
    max_total_exposure: float = 0.8
    daily_drawdown_limit: float = -0.03
    weekly_drawdown_limit: float = -0.07
    consecutive_losses_for_cooldown: int = 3
    cooldown_hours: int = 24


class ExecutionConfig(BaseModel):
    default_order_type: Literal['limit', 'market'] = 'limit'
    limit_timeout_sec: int = 60
    slippage_bps_limit: float = 10
    retry_attempts: int = 5
    retry_backoff_sec: float = 0.5


class StrategyConfig(BaseModel):
    active: str = 'combined_signal'
    min_rr: float = 2.0
    atr_stop_multiple: float = 1.5
    trailing_start_r: float = 1.5


class AppConfig(BaseModel):
    symbols: list[str]
    mode: Literal['paper', 'testnet', 'live']
    market_type: Literal['spot', 'futures'] = 'spot'
    base_timeframe: str = '15m'
    trend_timeframes: list[str] = ['1h', '4h']
    poll_interval_sec: int = 20
    strategy: StrategyConfig
    risk: RiskConfig
    execution: ExecutionConfig

    @field_validator('symbols')
    @classmethod
    def validate_symbols(cls, value: list[str]) -> list[str]:
        allowed = {'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'LINKUSDT', 'TONUSDT'}
        invalid = [s for s in value if s not in allowed]
        if invalid:
            raise ValueError(f'Símbolos no permitidos: {invalid}')
        return value


def load_config(path: str | Path = 'config.yaml') -> tuple[EnvSettings, AppConfig]:
    load_dotenv()
    env = EnvSettings()
    with Path(path).open('r', encoding='utf-8') as fh:
        data = yaml.safe_load(fh)
    try:
        app = AppConfig.model_validate(data)
    except ValidationError as exc:
        raise RuntimeError(f'config.yaml inválido: {exc}') from exc
    if env.mode != app.mode:
        app.mode = env.mode
    return env, app
