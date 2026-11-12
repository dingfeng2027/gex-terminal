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

FALLBACK_DATA = {}

FALLBACK_DATA["NVDA"] = {
    "name": "NVIDIA Corp", "price": 177.34, "prev": 186.64,
    "ma20": 209.10, "ma50": 219.01, "ma200": 204.62,
    "pe": 22.43, "high52": 195.95, "low52": 86.62,
    "rsi": 38.7, "eps": 8.31, "mcap": "4.60T"
}

FALLBACK_DATA["GOOGL"] = {
    "name": "Alphabet Inc", "price": 288.93, "prev": 284.78,
    "ma20": 314.25, "ma50": 331.77, "ma200": 339.32,
    "pe": 15.09, "high52": 303.14, "low52": 142.66,
    "rsi": 55.9, "eps": 19.14, "mcap": "3.54T"
}

FALLBACK_DATA["TSM"] = {
    "name": "TSMC", "price": 391.23, "prev": 375.44,
    "ma20": 413.78, "ma50": 431.12, "ma200": 401.76,
    "pe": 25.36, "high52": 475.59, "low52": 260.50,
    "rsi": 62.3, "eps": 15.42, "mcap": "2.02T"
}

FALLBACK_DATA["AMD"] = {
    "name": "Advanced Micro Devices", "price": 509.52, "prev": 449.04,
    "ma20": 523.06, "ma50": 547.69, "ma200": 417.23,
    "pe": 108.81, "high52": 607.31, "low52": 128.20,
    "rsi": 72.5, "eps": 4.68, "mcap": "825B"
}

FALLBACK_DATA["MSFT"] = {
    "name": "Microsoft", "price": 546.89, "prev": 530.61,
    "ma20": 531.69, "ma50": 517.31, "ma200": 440.25,
    "pe": 28.55, "high52": 567.20, "low52": 349.70,
    "rsi": 64.1, "eps": 19.15, "mcap": "4.06T"
}

FALLBACK_DATA["META"] = {
    "name": "Meta Platforms", "price": 644.30, "prev": 610.15,
    "ma20": 657.74, "ma50": 676.24, "ma200": 631.87,
    "pe": 21.99, "high52": 740.91, "low52": 476.50,
    "rsi": 59.4, "eps": 29.30, "mcap": "1.63T"
}

FALLBACK_DATA["AMZN"] = {
    "name": "Amazon.com", "price": 268.44, "prev": 259.30,
    "ma20": 254.72, "ma50": 253.99, "ma200": 244.09,
    "pe": 21.70, "high52": 287.38, "low52": 161.67,
    "rsi": 57.8, "eps": 12.37, "mcap": "2.81T"
}

FALLBACK_DATA["AAPL"] = {
    "name": "Apple Inc", "price": 351.39, "prev": 342.37,
    "ma20": 343.91, "ma50": 336.65, "ma200": 299.32,
    "pe": 39.13, "high52": 377.41, "low52": 169.21,
    "rsi": 61.6, "eps": 8.98, "mcap": "5.31T"
}

FALLBACK_DATA["ASML"] = {
    "name": "ASML Holding", "price": 1517.98, "prev": 1424.75,
    "ma20": 1587.93, "ma50": 1673.69, "ma200": 1600.79,
    "pe": 37.34, "high52": 1823.54, "low52": 946.11,
    "rsi": 66.2, "eps": 40.65, "mcap": "605B"
}

FALLBACK_DATA["TSLA"] = {
    "name": "Tesla Inc", "price": 381.01, "prev": 358.22,
