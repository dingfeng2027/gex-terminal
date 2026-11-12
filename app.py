import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ---------------------------------------------------------
# 1. 页面基础配置与 22px 特大字号样式
# ---------------------------------------------------------
st.set_page_config(page_title="CAPITAL QUANT v2", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .block-container {
        padding-top: 0.6rem !important; padding-bottom: 1.5rem !important;
        padding-left: 1.2rem !important; padding-right: 1.2rem !important;
        max-width: 100% !important;
    }
    html, body, [class*="css"] { font-size: 22px !important; }
    .stApp {
        background: radial-gradient(circle at top center, #0a2558 0%, #040d21 65%, #020712 100%) !important;
        color: #ffffff !important;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
    }
    header, footer, #MainMenu {visibility: hidden;}

    .top-bar {
        background: linear-gradient(90deg, #061533 0%, #0c275e 50%, #061533 100%);
        border: 1px solid #2563eb; border-radius: 8px; padding: 14px 22px;
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.6); width: 100%;
    }
    .brand-title { font-size: 30px !important; font-weight: 800; letter-spacing: 1px; color: #ffffff; }
    .live-badge { color: #4ade80; font-weight: 700; font-size: 20px !important; }

    .card-header {
        font-size: 22px !important; font-weight: 800; letter-spacing: 0.8px;
        color: #93c5fd; border-bottom: 1px solid #1e3a8a; padding-bottom: 6px;
        margin-bottom: 10px; text-transform: uppercase;
    }

    div.stButton > button {
        background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: #ffffff !important; border: 1px solid #60a5fa !important;
        border-radius: 6px !important; font-size: 20px !important; font-weight: 700 !important;
        padding: 10px 16px !important;
    }
    div.stButton > button:hover { background: linear-gradient(180deg, #3b82f6 0%, #2563eb 100%) !important; }

    .stTextInput input, div[data-baseweb="select"] > div {
        background-color: #07193d !important; color: #ffffff !important;
        border: 1px solid #3b82f6 !important; font-size: 20px !important;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid #2563eb !important; border-radius: 8px !important;
        background-color: #061430 !important; width: 100% !important;
    }
    .metric-box {
        background: #061430; border: 1px solid #2563eb; border-radius: 8px;
        padding: 12px 16px; text-align: center;
    }
    .metric-label { font-size: 19px !important; color: #93c5fd; margin-bottom: 4px; font-weight: 700; }
    .metric-val { font-size: 30px !important; font-weight: 900; color: #ffffff; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 初始化配置与数据字典
# ---------------------------------------------------------
DEFAULT_TICKERS = ["NVDA", "GOOGL", "TSM", "AMD", "MSFT", "META", "AMZN", "AAPL", "ASML", "TSLA", "VUAG.L", "EQQQ.L"]

FALLBACK_DATA = {
    "NVDA":   {"name": "NVIDIA Corporation", "price": 177.34, "prev": 186.64, "ma20": 209.10, "ma50": 219.01, "ma200": 204.62, "pe": 22.43, "high52": 195.95, "low52": 86.62, "rsi": 38.7, "eps": 8.31, "mcap": "4.60T"},
    "GOOGL":  {"name": "Alphabet Inc.", "price": 288.93, "prev": 284.78, "ma20": 314.25, "ma50": 331.77, "ma200": 339.32, "pe": 15.09, "high52": 303.14, "low52": 142.66, "rsi": 55.9, "eps": 19.14, "mcap": "3.54T"},
    "TSM":    {"name": "Taiwan Semiconductor", "price": 391.23, "prev": 375.44, "ma20": 413.78, "ma50": 431.12, "ma200": 401.76, "pe": 25.36, "high52": 475.59, "low52": 260.50, "rsi": 62.3, "eps": 15.42, "mcap": "2.02T"},
    "AMD":    {"name": "Advanced Micro Devices", "price": 509.52, "prev": 449.04, "ma20": 523.06, "ma50": 547.69, "ma200": 417.23, "pe": 108.81, "high52": 607.31, "low52": 128.20, "rsi": 72.5, "eps": 4.68, "mcap": "825B"},
    "MSFT":   {"name": "Microsoft Corporation", "price": 546.89, "prev": 530.61, "ma20": 531.69, "ma50": 517.31, "ma200": 440.25, "pe": 28.55, "high52": 567.20, "low52": 349.70, "rsi": 64.1, "eps": 19.15, "mcap": "4.06T"},
    "META":   {"name": "Meta Platforms Inc.", "price": 644.30, "prev": 610.15, "ma20": 657.74, "ma50": 676.24, "ma200": 631.87, "pe": 21.99, "high52": 740.91, "low52": 476.50, "rsi": 59.4, "eps": 29.30, "mcap": "1.63T"},
    "AMZN":   {"name": "Amazon.com Inc.", "price": 268.44, "prev": 259.30, "ma20": 254.72, "ma50": 253.99, "ma200": 244.09, "pe": 21.70, "high52": 287.38, "low52": 161.67, "rsi": 57.8, "eps": 12.37, "mcap": "2.81T"},
    "AAPL":   {"name": "Apple Inc.", "price": 351.39, "prev": 342.37, "ma20": 343.91, "ma50": 336.65, "ma200": 299.32, "pe": 39.13, "high52": 377.41, "low
