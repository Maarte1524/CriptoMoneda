from __future__ import annotations

import argparse
import asyncio
import signal

from loguru import logger

from bot.config import load_config
from bot.data_feed import BinanceDataFeed
from bot.db import Database
from bot.notifier import Notifier
from bot.order_manager import OrderManager
from bot.portfolio import Portfolio, Position
from bot.risk_manager import OpenPosition, RiskManager
from bot.strategies.breakout import BreakoutStrategy
from bot.strategies.combined_signal import CombinedSignalStrategy
from bot.strategies.mean_reversion import MeanReversionStrategy
from bot.strategies.trend_following import TrendFollowingStrategy
from bot.utils import utc_now_iso


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CriptoMoneda trading bot")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--paper", action="store_true")
    parser.add_argument("--kill", action="store_true", help="panic kill switch")
    return parser


async def run_bot(args) -> None:
    env, cfg = load_config(args.config)
    logger.add(cfg.log_dir / "bot.log", rotation="20 MB", retention=10, enqueue=True)

    db = Database(cfg.db_path)
    notifier = Notifier(enabled_console=cfg.alerts.console_enabled)

    data_feed = BinanceDataFeed(
        api_key=env.binance_api_key.get_secret_value(),
        api_secret=env.binance_api_secret.get_secret_value(),
        market_type=cfg.market_type,
        testnet=(cfg.mode in {"paper", "testnet"} or cfg.use_testnet),
    )
    order_manager = OrderManager(data_feed, cfg.execution)

    strategies = [TrendFollowingStrategy(), BreakoutStrategy(), MeanReversionStrategy()]
    strategy = CombinedSignalStrategy(strategies)

    portfolio = Portfolio(starting_equity=cfg.backtesting.initial_capital)
    risk = RiskManager(cfg.risk)
    risk.bootstrap(portfolio.equity)

    stop_event = asyncio.Event()

    def _stop(*_):
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _stop)

    if args.kill:
        for symbol, pos in list(portfolio.positions.items()):
            await order_manager.emergency_exit(symbol, pos.side, pos.qty)
        await notifier.send("KILL SWITCH executed: closed positions and stopped trading.")
        await data_feed.close()
        return

    while not stop_event.is_set():
        safe_to_trade, reason = risk.check_circuit_breakers(portfolio.equity)
        if not safe_to_trade:
            await notifier.send(f"Circuit breaker: {reason}")
            await asyncio.sleep(60)
            continue

        for symbol in cfg.pairs:
            can_trade, why = risk.can_trade_symbol(symbol)
            if not can_trade:
                logger.warning(why)
                continue

            frame_15 = await data_feed.fetch_ohlcv(symbol, cfg.timeframes.execution, limit=500)
            frame_1h = await data_feed.fetch_ohlcv(symbol, cfg.timeframes.confirm[0], limit=500)
            frame_4h = await data_feed.fetch_ohlcv(symbol, cfg.timeframes.confirm[1], limit=500)
            frame_15 = await data_feed.compute_features(frame_15)
            frame_1h = await data_feed.compute_features(frame_1h)
            frame_4h = await data_feed.compute_features(frame_4h)

            signal_obj = strategy.evaluate(frame_15, frame_1h, frame_4h)
            if signal_obj.signal == "flat":
                continue

            entry = float(frame_15.iloc[-1]["close"])
            qty = risk.compute_position_size(
                equity=portfolio.equity,
                entry=entry,
                stop=signal_obj.stop_loss,
                signal_score=signal_obj.score,
                volatility=float(frame_15.iloc[-1]["volatility20"]),
            )
            notional = qty * entry
            exposure_ok, exposure_msg = risk.validate_portfolio_exposure(
                portfolio.equity,
                symbol,
                notional,
                [OpenPosition(p.symbol, p.side, p.qty * p.entry_price) for p in portfolio.positions.values()],
            )
            if not exposure_ok:
                logger.warning("Risk block for {}: {}", symbol, exposure_msg)
                continue

            if args.paper or cfg.mode == "paper":
                portfolio.open_position(
                    Position(
                        symbol=symbol,
                        side=signal_obj.signal,
                        qty=qty,
                        entry_price=entry,
                        stop_loss=signal_obj.stop_loss,
                        take_profit=signal_obj.take_profit,
                    )
                )
                await notifier.send(f"PAPER OPEN {symbol} {signal_obj.signal} qty={qty:.6f} reason={signal_obj.reason}")
            else:
                await order_manager.place_entry_order(symbol, signal_obj.signal, qty, entry)

            with db.connect() as conn:
                conn.execute(
                    "INSERT INTO signals(ts,symbol,strategy,signal,score,payload_json) VALUES(?,?,?,?,?,?)",
                    (utc_now_iso(), symbol, strategy.name, signal_obj.signal, signal_obj.score, signal_obj.reason),
                )

        await asyncio.sleep(30)

    await data_feed.close()


def main() -> None:
    args = build_parser().parse_args()
    asyncio.run(run_bot(args))


if __name__ == "__main__":
    main()
