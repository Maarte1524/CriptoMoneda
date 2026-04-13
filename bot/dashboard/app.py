from __future__ import annotations

import sqlite3

import pandas as pd
import streamlit as st

st.set_page_config(page_title="CriptoMoneda Bot", layout="wide")
st.title("Trading Bot Monitor")

conn = sqlite3.connect("data/trading.db")
trades = pd.read_sql_query("SELECT * FROM trades ORDER BY id DESC LIMIT 500", conn)
signals = pd.read_sql_query("SELECT * FROM signals ORDER BY id DESC LIMIT 500", conn)

open_trades = trades[trades["status"] == "OPEN"] if not trades.empty else pd.DataFrame()
closed = trades[trades["status"] == "CLOSED"] if not trades.empty else pd.DataFrame()

pnl = closed["pnl"].fillna(0).sum() if not closed.empty else 0
win_rate = (closed["pnl"] > 0).mean() if not closed.empty else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("PnL acumulado", f"{pnl:.2f} USDT")
c2.metric("Posiciones abiertas", len(open_trades))
c3.metric("Win rate", f"{win_rate*100:.2f}%")
c4.metric("Señales (500)", len(signals))

st.subheader("Posiciones abiertas")
st.dataframe(open_trades, use_container_width=True)

st.subheader("Histórico de trades")
st.dataframe(trades, use_container_width=True)

if not closed.empty:
    st.subheader("PnL por par")
    st.bar_chart(closed.groupby("symbol", as_index=False)["pnl"].sum().set_index("symbol"))
