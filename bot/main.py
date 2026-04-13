from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os

import websockets
from loguru import logger

from bot.config import AppConfig, load_config
from bot.data_feed import BinanceGateway, enrich_indicators
from bot.db import DB
from bot.notifier import Notifier
from bot.order_manager import OrderManager
from bot.portfolio import Portfolio, Position
from bot.risk_manager import RiskManager
from bot.strategies import combined_signal
from bot.utils import GracefulShutdown, setup_logging, utc_now

if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class CorrelationState:
    def __init__(self) -> None:
        self.matrix: dict[tuple[str, str], float] = {}
        self.lock = asyncio.Lock()

    async def get(self, a: str, b: str) -> float:
        async with self.lock:
            return self.matrix.get((a, b), self.matrix.get((b, a), 0.0))

    async def set_many(self, rows: dict[tuple[str, str], float]) -> None:
        async with self.lock:
            self.matrix.update(rows)


class WSHealth:
    def __init__(self) -> None:
        self.last_msg_ts: float = 0
        self.degraded = False


def market_regime(df) -> str:
    last = df.shift(1).iloc[-1]
    if last["adx"] > 25 and last["ema20"] > last["ema50"]:
        return "bull"
    if last["adx"] > 25 and last["ema20"] < last["ema50"]:
        return "bear"
    if last["volatility"] > df["volatility"].rolling(50).mean().shift(1).iloc[-1]:
        return "high_vol"
    return "range"


async def correlation_worker(gateway: BinanceGateway, symbols: list[str], state: CorrelationState, stop_event: asyncio.Event, refresh_seconds: int) -> None:
    while not stop_event.is_set():
        rows: dict[tuple[str, str], float] = {}
        data = {}
        for s in symbols:
            df = await gateway.fetch_ohlcv(s, "15m", 120)
            data[s] = df["close"].pct_change().dropna()
        for i, a in enumerate(symbols):
            for b in symbols[i + 1 :]:
                corr = data[a].corr(data[b]) if not data[a].empty and not data[b].empty else 0.0
                rows[(a, b)] = float(corr if corr == corr else 0.0)
        await state.set_many(rows)
        await asyncio.sleep(refresh_seconds)


async def websocket_heartbeat_worker(ws_health: WSHealth, stop_event: asyncio.Event) -> None:
    # stream de referencia de mercado para watchdog operativo
    url = "wss://stream.binance.com:9443/ws/btcusdt@miniTicker"
    while not stop_event.is_set():
        try:
            async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                ws_health.last_msg_ts = asyncio.get_running_loop().time()
                while not stop_event.is_set():
                    raw = await asyncio.wait_for(ws.recv(), timeout=30)
                    _ = json.loads(raw)
                    ws_health.last_msg_ts = asyncio.get_running_loop().time()
                    ws_health.degraded = False
        except Exception as exc:
            ws_health.degraded = True
            logger.warning(f"WS heartbeat reconexión: {exc}")
            await asyncio.sleep(3)


async def watchdog_worker(
    cfg: AppConfig,
    gateway: BinanceGateway,
    ws_health: WSHealth,
    notifier: Notifier,
    stop_event: asyncio.Event,
) -> None:
    while not stop_event.is_set():
        now = asyncio.get_running_loop().time()
        if gateway.last_ok_ts and (now - gateway.last_ok_ts) > cfg.monitoring.heartbeat_timeout_seconds:
            logger.warning("Watchdog detectó feed REST estancado; reconectando gateway...")
            await gateway.reconnect()
        if ws_health.last_msg_ts and (now - ws_health.last_msg_ts) > cfg.monitoring.heartbeat_timeout_seconds:
            if not ws_health.degraded:
                ws_health.degraded = True
                await notifier.notify("ALERTA: WebSocket degradado por timeout de heartbeat")
            logger.warning("Heartbeat WS degradado")
        await asyncio.sleep(cfg.monitoring.watchdog_poll_seconds)


async def safe_shutdown(
    db: DB,
    orders: OrderManager,
    portfolio: Portfolio,
    risk: RiskManager,
    notifier: Notifier,
) -> None:
    risk.trigger_kill_switch()  # 1) detener nuevas entradas

    # 2) cancelar órdenes pendientes (placeholder para integración por símbolo)
    for symbol, pos in list(portfolio.open_positions.items()):
        try:
            # 3) cerrar posiciones abiertas
            exit_side = "sell" if pos.side == "long" else "buy"
            exit_order = await orders.place_market_exit(symbol, exit_side, pos.qty)
            exit_price = float(exit_order["price"])
            pnl = (exit_price - pos.entry) * pos.qty if pos.side == "long" else (pos.entry - exit_price) * pos.qty
            portfolio.register_close(symbol, pnl)
            await db.execute(
                "UPDATE trades SET status='CLOSED', exit=?, pnl=?, exit_reason=? WHERE symbol=? AND status='OPEN'",
                (exit_price, pnl, "kill_switch_shutdown", symbol),
            )
            await notifier.notify(f"CLOSE {symbol} por kill switch, pnl={pnl:.4f}")
            del portfolio.open_positions[symbol]
        except Exception as exc:
            logger.error(f"Error en cierre de emergencia {symbol}: {exc}")

    # 4) persistir estado final
    await db.execute(
        "INSERT INTO events (ts, level, event_type, payload) VALUES (?,?,?,?)",
        (utc_now().isoformat(), "INFO", "shutdown", "safe_shutdown_completed"),
    )


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
    await db.init()
    notifier = Notifier(enabled=cfg.alerts.telegram_enabled)
    gateway = BinanceGateway(mode=cfg.mode, market_type=cfg.market_type)
    orders = OrderManager(gateway, cfg.execution, mode=cfg.mode)
    risk = RiskManager(cfg.risk)
    portfolio = Portfolio()
    stop = GracefulShutdown()
    stop.install()
    corr_state = CorrelationState()
    ws_health = WSHealth()

    if args.kill:
        risk.trigger_kill_switch()
        await notifier.notify("KILL SWITCH manual activado: trading detenido.")

    await notifier.notify(f"Bot iniciado en modo={cfg.mode}")

    bg_tasks = [
        asyncio.create_task(correlation_worker(gateway, cfg.symbols, corr_state, stop.stop_event, cfg.monitoring.correlation_refresh_seconds)),
        asyncio.create_task(websocket_heartbeat_worker(ws_health, stop.stop_event)),
        asyncio.create_task(watchdog_worker(cfg, gateway, ws_health, notifier, stop.stop_event)),
    ]

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

                corr_count = 0
                for open_symbol, open_side in active_sides.items():
                    if open_side == side and abs(await corr_state.get(symbol, open_symbol)) > 0.75:
                        corr_count += 1
                if corr_count >= 2:
                    logger.info(f"Señal descartada por correlación alta: {symbol}")
                    continue

                row = df_15m.iloc[-1]
                entry = float(row["close"])
                atr = float(row["atr"])
                stop_loss = entry - cfg.risk.atr_stop_multiple * atr if side == "long" else entry + cfg.risk.atr_stop_multiple * atr
                take_profit = entry + (entry - stop_loss) * cfg.risk.min_rr if side == "long" else entry - (stop_loss - entry) * cfg.risk.min_rr

                qty = risk.position_size(portfolio.equity, entry, stop_loss, atr, confidence, float(row["volatility"]))
                if qty <= 0:
                    continue

                await orders.place_limit(symbol, "buy" if side == "long" else "sell", qty, entry)
                portfolio.open_positions[symbol] = Position(symbol, side, qty, entry, stop_loss, take_profit, "combined_signal")
                await db.execute(
                    "INSERT INTO trades (ts,symbol,side,strategy,entry_reason,qty,entry,stop_loss,take_profit,status) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (utc_now().isoformat(), symbol, side, "combined_signal", reason, qty, entry, stop_loss, take_profit, "OPEN"),
                )
                await notifier.notify(f"OPEN {symbol} {side} qty={qty:.4f} entry={entry:.4f} conf={confidence:.2f} regime={regime}")

                await db.execute(
                    "INSERT INTO signals (ts,symbol,strategy,signal,confidence,context,discarded_reason) VALUES (?,?,?,?,?,?,?)",
                    (utc_now().isoformat(), symbol, "combined_signal", side, confidence, regime, ""),
                )

            await asyncio.sleep(20)
    finally:
        stop.stop_event.set()
        await safe_shutdown(db, orders, portfolio, risk, notifier)
        for task in bg_tasks:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        await gateway.close()  # 5) cerrar conexiones correctamente


if __name__ == "__main__":
    asyncio.run(run())
