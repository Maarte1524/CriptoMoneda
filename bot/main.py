from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict

from loguru import logger

from bot.config import load_config
from bot.data_feed import BinanceGateway, enrich_indicators
from bot.db import DB
from bot.notifier import Notifier
from bot.order_manager import OrderManager
from bot.portfolio import Portfolio, Position
from bot.risk_manager import RiskManager
from bot.strategies import combined_signal
from bot.utils import GracefulShutdown, setup_logging, utc_now


def market_regime(df) -> str:
    last = df.iloc[-1]
    if last["adx"] > 25 and last["ema20"] > last["ema50"]:
        return "bull"
    if last["adx"] > 25 and last["ema20"] < last["ema50"]:
        return "bear"
    if last["volatility"] > df["volatility"].rolling(50).mean().iloc[-1]:
        return "high_vol"
    return "range"


def correlation_penalty(symbol: str, side: str, active_sides: dict[str, str]) -> float:
    risk_buckets = {
        "macro": {"BTC/USDT", "ETH/USDT"},
        "aggressive": {"SOL/USDT", "XRP/USDT", "DOGE/USDT", "TON/USDT", "ADA/USDT", "LINK/USDT"},
    }
    bucket = "macro" if symbol in risk_buckets["macro"] else "aggressive"
    same_side = sum(1 for s, sd in active_sides.items() if sd == side and (s in risk_buckets[bucket]))
    if same_side >= 2:
        return 0.5
    return 1.0


async def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", action="store_true")
    parser.add_argument("--kill", action="store_true")
    args = parser.parse_args()

    cfg = load_config()
    if args.paper:
        cfg.mode = "paper"

    setup_logging(cfg.log_dir)
    db = DB(cfg.db_path)
    notifier = Notifier(enabled=cfg.alerts.telegram_enabled)
    gateway = BinanceGateway(mode=cfg.mode, market_type=cfg.market_type)
    orders = OrderManager(gateway, cfg.execution, mode=cfg.mode)
    risk = RiskManager(cfg.risk)
    portfolio = Portfolio()
    stop = GracefulShutdown()
    stop.install()

    if args.kill:
        risk.trigger_kill_switch()
        await notifier.notify("KILL SWITCH manual activado: trading detenido.")

    await notifier.notify(f"Bot iniciado en modo={cfg.mode}")

    try:
        while not stop.stop_event.is_set():
            active_sides = {s: p.side for s, p in portfolio.open_positions.items()}
            for symbol in cfg.symbols:
                check = risk.pre_trade_check(portfolio, symbol)
                if not check.approved:
                    logger.warning(f"Trade bloqueado {symbol}: {check.reason}")
                    continue

                df_15m = enrich_indicators(await gateway.fetch_ohlcv(symbol, cfg.timeframe_execution))
                df_1h = enrich_indicators(await gateway.fetch_ohlcv(symbol, cfg.timeframe_confirm_1))
                df_4h = enrich_indicators(await gateway.fetch_ohlcv(symbol, cfg.timeframe_confirm_2))
                regime = market_regime(df_15m)

                side, confidence, reason = combined_signal.generate_signal(df_15m)
                if side == "flat":
                    continue
                if market_regime(df_1h) == "bear" and side == "long":
                    continue
                if market_regime(df_4h) == "bear" and side == "long":
                    continue

                row = df_15m.iloc[-1]
                entry = float(row["close"])
                atr = float(row["atr"])
                stop_loss = entry - cfg.risk.atr_stop_multiple * atr if side == "long" else entry + cfg.risk.atr_stop_multiple * atr
                take_profit = entry + (entry - stop_loss) * cfg.risk.min_rr if side == "long" else entry - (stop_loss - entry) * cfg.risk.min_rr

                corr_factor = correlation_penalty(symbol, side, active_sides)
                qty = risk.position_size(portfolio.equity, entry, stop_loss, atr, confidence * corr_factor, float(row["volatility"]))
                if qty <= 0:
                    continue

                order = await orders.place_limit(symbol, "buy" if side == "long" else "sell", qty, entry)
                portfolio.open_positions[symbol] = Position(symbol, side, qty, entry, stop_loss, take_profit, "combined_signal")
                db.execute(
                    "INSERT INTO trades (ts,symbol,side,strategy,entry_reason,qty,entry,stop_loss,take_profit,status) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (utc_now().isoformat(), symbol, side, "combined_signal", reason, qty, entry, stop_loss, take_profit, "OPEN"),
                )
                await notifier.notify(f"OPEN {symbol} {side} qty={qty:.4f} entry={entry:.4f} conf={confidence:.2f} regime={regime}")

                db.execute(
                    "INSERT INTO signals (ts,symbol,strategy,signal,confidence,context,discarded_reason) VALUES (?,?,?,?,?,?,?)",
                    (utc_now().isoformat(), symbol, "combined_signal", side, confidence, regime, ""),
                )

            await asyncio.sleep(20)
    finally:
        await gateway.close()


if __name__ == "__main__":
    asyncio.run(run())
