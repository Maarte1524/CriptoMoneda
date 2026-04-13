from __future__ import annotations

import argparse
import asyncio
import signal
from pathlib import Path

from loguru import logger

from bot.backtester import Backtester
from bot.config import load_config
from bot.data_feed import BinanceDataFeed
from bot.db import DB
from bot.notifier import Notifier
from bot.portfolio import Portfolio, Position
from bot.risk_manager import RiskManager
from bot.strategies.combined_signal import generate_signal
from bot.utils import utc_now

RUNNING = True


def setup_logging() -> None:
    Path('logs').mkdir(exist_ok=True)
    logger.remove()
    logger.add('logs/bot.log', rotation='20 MB', retention=10, enqueue=True)
    logger.add('logs/bot.json', serialize=True, rotation='20 MB', retention=10, enqueue=True)


async def run_bot(kill: bool = False) -> None:
    global RUNNING
    setup_logging()
    env, cfg = load_config()
    db = DB()
    portfolio = Portfolio()
    risk = RiskManager(cfg.risk)
    notifier = Notifier(
        token=env.telegram_bot_token.get_secret_value() if env.telegram_bot_token else None,
        chat_id=env.telegram_chat_id,
    )
    feed = BinanceDataFeed(
        api_key=env.binance_api_key.get_secret_value(),
        api_secret=env.binance_api_secret.get_secret_value(),
        testnet=cfg.mode == 'testnet',
    )
    await feed.load_markets()

    if kill:
        await notifier.send('KILL SWITCH activado: cancelar órdenes y detener trading.')
        return

    while RUNNING:
        for symbol in cfg.symbols:
            can_open, reason = risk.can_open(portfolio, symbol, int(utc_now().timestamp()))
            if not can_open:
                db.execute("INSERT INTO events(ts, level, event, payload) VALUES(?,?,?,?)", (utc_now().isoformat(), 'WARNING', reason, symbol))
                continue
            df = await feed.retry(lambda: feed.fetch_ohlcv(symbol, cfg.base_timeframe, 400))
            side, score, signal_reason = generate_signal(df)
            if side == 'flat':
                continue
            row = df.iloc[-1]
            entry = float(row['close'])
            stop = entry - row['atr14'] * cfg.strategy.atr_stop_multiple if side == 'long' else entry + row['atr14'] * cfg.strategy.atr_stop_multiple
            take = entry + (entry - stop) * cfg.strategy.min_rr if side == 'long' else entry - (stop - entry) * cfg.strategy.min_rr
            qty = risk.size_position(portfolio.equity, entry, float(stop), score, vol_factor=max(float(row['atr14'] / entry), 0.5))
            if qty <= 0:
                continue
            portfolio.upsert_position(Position(symbol=symbol, side=side, qty=qty, entry=entry, stop=float(stop), take=float(take), strategy='combined_signal'))
            db.execute(
                "INSERT INTO trades(ts,symbol,strategy,side,qty,entry,stop,take,reason_in) VALUES(?,?,?,?,?,?,?,?,?)",
                (utc_now().isoformat(), symbol, 'combined_signal', side, qty, entry, float(stop), float(take), signal_reason),
            )
            await notifier.send(f'OPEN {symbol} {side} qty={qty:.6f} entry={entry:.4f} stop={stop:.4f} take={take:.4f}')
        await asyncio.sleep(cfg.poll_interval_sec)
    await feed.safe_close()


def handle_signal(*_: object) -> None:
    global RUNNING
    RUNNING = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='CriptoMoneda bot')
    parser.add_argument('--paper', action='store_true', help='Forzar modo paper')
    parser.add_argument('--kill', action='store_true', help='Activar kill switch')
    parser.add_argument('--backtest', action='store_true', help='Ejecutar backtest rápido')
    parser.add_argument('--symbol', default='BTCUSDT')
    return parser.parse_args()


async def run_backtest(symbol: str) -> None:
    env, _ = load_config()
    feed = BinanceDataFeed(env.binance_api_key.get_secret_value(), env.binance_api_secret.get_secret_value(), testnet=True)
    await feed.load_markets()
    df = await feed.fetch_ohlcv(symbol, '15m', 1500)
    result = Backtester().run(df)
    logger.info(result)
    await feed.safe_close()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    args = parse_args()
    if args.backtest:
        asyncio.run(run_backtest(args.symbol))
    else:
        asyncio.run(run_bot(kill=args.kill))
