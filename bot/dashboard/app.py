from __future__ import annotations

import sqlite3

import pandas as pd
import streamlit as st

st.set_page_config(page_title='CriptoMoneda Dashboard', layout='wide')
st.title('CriptoMoneda - Trading Monitor')

conn = sqlite3.connect('data/trading.db')
trades = pd.read_sql_query('SELECT * FROM trades ORDER BY id DESC LIMIT 500', conn)
events = pd.read_sql_query('SELECT * FROM events ORDER BY id DESC LIMIT 200', conn)

col1, col2, col3 = st.columns(3)
if not trades.empty:
    pnl = trades['pnl'].fillna(0)
    col1.metric('PnL acumulado', f"{pnl.sum():.2f}")
    col2.metric('Win rate', f"{(pnl.gt(0).mean() * 100):.2f}%")
    col3.metric('Trades', len(trades))

st.subheader('Últimos trades')
st.dataframe(trades, use_container_width=True)
st.subheader('Eventos del sistema')
st.dataframe(events, use_container_width=True)
