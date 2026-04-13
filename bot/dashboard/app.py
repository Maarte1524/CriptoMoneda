from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path("data/trading.db")


@st.cache_data(ttl=10)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not DB_PATH.exists():
        return pd.DataFrame(), pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    trades = pd.read_sql_query("SELECT * FROM trades", conn)
    signals = pd.read_sql_query("SELECT * FROM signals", conn)
    conn.close()
    return trades, signals


st.set_page_config(page_title="CriptoMoneda Dashboard", layout="wide")
st.title("CriptoMoneda Monitoring Dashboard")

trades_df, signals_df = load_data()

col1, col2, col3 = st.columns(3)
col1.metric("Total trades", len(trades_df))
col2.metric("Signals", len(signals_df))
col3.metric("Win rate", f"{(trades_df['pnl'] > 0).mean() * 100:.2f}%" if len(trades_df) else "0.00%")

st.subheader("Últimas señales")
st.dataframe(signals_df.tail(100), use_container_width=True)

st.subheader("Histórico de operaciones")
st.dataframe(trades_df.tail(100), use_container_width=True)
