import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="CAPITAL QUANT v2", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .block-container { padding: 0.4rem 1rem 1rem 1rem !important; max-width: 100% !important; }
    html, body, [class*="css"] { font-size: 20px !important; }
    .stApp { background: radial-gradient(circle at top center, #0a2558 0%, #040d21 65%, #020712 100%) !important; color: #fff !important; }
    header, footer, #MainMenu {visibility: hidden;}
    .top-bar { background: linear-gradient(90deg, #061533, #0c275e, #061533); border: 1px solid #2563eb; border-radius: 8px; padding: 10px 18px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
    .brand-title { font-size: 28px !important; font-weight: 800; color: #fff; }
    .live-badge { color: #4ade80; font-weight: 700; font-size: 19px !important; }
    .card-header { font-size: 21px !important; font-weight: 800; color: #93c5fd; border-bottom: 1px solid #1e3a8a; padding-bottom: 5px; margin-bottom: 8px; text-transform: uppercase; }
    div.stButton > button { background: linear-gradient(180deg, #2563eb, #1d4ed8) !important; color: #fff !important; border: 1px solid #60a5fa !important; border-radius: 6px !important; font-size: 19px !important; font-weight: 700 !important; padding: 8px 14px !important; }
    .stTextInput input, div[data-baseweb="select"] > div { background-color: #07193d !important; color: #fff !important; border: 1px solid #3b82f6 !important; font-size: 19px !important; }
    div[data-testid="stDataFrame"] { border: 1px solid #2563eb !important; border-radius: 8px !important; background-color: #061430 !important; }
    .metric-box { background: #061430; border: 1px solid #2563eb; border-radius: 8px; padding: 11px 15px; text-align: center; }
    .metric-label { font-size: 17px !important; color: #93c5fd; margin-bottom: 3px; font-weight: 700; }
    .metric-val { font-size: 28px !important; font-weight: 900; color: #fff; }
</style>
""", unsafe_allow_html=True)

DEFAULT_TICKERS = ["NVDA", "GOOGL", "TSM", "AMD", "MSFT", "META", "AMZN", "AAPL", "ASML", "TSLA", "CEG", "SMCI", "MPWR", "MRVL", "NFLX", "QQQ", "VUAG.L", "EQQQ.L"]

FALLBACK_DATA = {
    "NVDA": {"name": "NVIDIA", "price": 177.34, "prev": 186.64, "ma20": 209.1, "ma50": 219.0, "ma200": 204.6, "pe": 22.4, "high52": 195.9, "low52": 86.6, "rsi": 38.7, "eps": 8.31, "mcap": "4.60T"},
    "GOOGL": {"name": "Alphabet", "price": 288.93, "prev": 284.78, "ma20": 314.2, "ma50": 331.7, "ma200": 339.3, "pe": 15.1, "high52": 303.1, "low52": 142.6, "rsi": 55.9, "eps": 19.14, "mcap": "3.54T"},
    "TSM": {"name": "TSMC", "price": 391.23, "prev": 375.44, "ma20": 413.7, "ma50": 431.1, "ma200": 401.7, "pe": 25.4, "high52": 475.5, "low52": 260.5, "rsi": 62.3, "eps": 15.42, "mcap": "2.02T"},
    "AMD": {"name": "AMD", "price": 509.52, "prev": 449.04, "ma20": 523.0, "ma50": 547.6, "ma200": 417.2, "pe": 108.8, "high52": 607.3, "low52": 128.2, "rsi": 72.5, "eps": 4.68, "mcap": "825B"},
    "MSFT": {"name": "Microsoft", "price": 546.89, "prev": 530.61, "ma20": 531.6, "ma50": 517.3, "ma200": 440.2, "pe": 28.5, "high52": 567.2, "low52": 349.7, "rsi": 64.1, "eps": 19.15, "mcap": "4.06T"},
    "META": {"name": "Meta", "price": 644.30, "prev": 610.15, "ma20": 657.7, "ma50": 676.2, "ma200": 631.8, "pe": 22.0, "high52": 740.9, "low52": 476.5, "rsi": 59.4, "eps": 29.30, "mcap": "1.63T"},
    "AMZN": {"name": "Amazon", "price": 268.44, "prev": 259.30, "ma20": 254.7, "ma50": 253.9, "ma200": 244.0, "pe": 21.7, "high52": 287.3, "low52": 161.6, "rsi": 57.8, "eps": 12.37, "mcap": "2.81T"},
    "AAPL": {"name": "Apple", "price": 351.39, "prev": 342.37, "ma20": 343.9, "ma50": 336.6, "ma200": 299.3, "pe": 39.1, "high52": 377.4, "low52": 169.2, "rsi": 61.6, "eps": 8.98, "mcap": "5.31T"},
    "ASML": {"name": "ASML", "price": 1517.98, "prev": 1424.75, "ma20": 1587.9, "ma50": 1673.6, "ma200": 1600.7, "pe": 37.3, "high52": 1823.5, "low52": 946.1, "rsi": 66.2, "eps": 40.65, "mcap": "605B"},
    "TSLA": {"name": "Tesla", "price": 381.01, "prev": 358.22, "ma20": 380.5, "ma50": 372.7, "ma200": 383.5, "pe": 418.7, "high52": 488.5, "low52": 217.2, "rsi": 58.5, "eps": 0.91, "mcap": "1.21T"},
    "CEG": {"name": "Constellation", "price": 265.50, "prev": 258.00, "ma20": 260.0, "ma50": 250.0, "ma200": 220.0, "pe": 32.5, "high52": 290.0, "low52": 150.0, "rsi": 58.0, "eps": 8.15, "mcap": "85B"},
    "SMCI": {"name": "Super Micro", "price": 28.88, "prev": 27.50, "ma20": 30.1, "ma50": 35.2, "ma200": 45.0, "pe": 14.2, "high52": 118.8, "low52": 17.2, "rsi": 46.5, "eps": 2.03, "mcap": "16B"},
    "MPWR": {"name": "Monolithic", "price": 1190.46, "prev": 1160.00, "ma20": 1
