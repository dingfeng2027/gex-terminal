import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="CAPITAL QUANT v2", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .block-container { padding: 0.6rem 1.2rem 1.5rem 1.2rem !important; max-width: 100% !important; }
    html, body, [class*="css"] { font-size: 22px !important; }
    .stApp { background: radial-gradient(circle at top center, #0a2558 0%, #040d21 65%, #020712 100%) !important; color: #fff !important; }
    header, footer, #MainMenu {visibility: hidden;}
    .top-bar { background: linear-gradient(90deg, #061533, #0c275e, #061533); border: 1px solid #2563eb; border-radius: 8px; padding: 14px 22px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
    .brand-title { font-size: 30px !important; font-weight: 800; color: #fff; }
    .live-badge { color: #4ade80; font-weight: 700; font-size: 20px !important; }
    .card-header { font-size: 22px !important; font-weight: 800; color: #93c5fd; border-bottom: 1px solid #1e3a8a; padding-bottom: 6px; margin-bottom: 10px; text-transform: uppercase; }
    div.stButton > button { background: linear-gradient(180deg, #2563eb, #1d4ed8) !important; color: #fff !important; border: 1px solid #60a5fa !important; border-radius: 6px !important; font-size: 20px !important; font-weight: 700 !important; padding: 10px 16px !important; }
    .stTextInput input, div[data-baseweb="select"] > div { background-color: #07193d !important; color: #fff !important; border: 1px solid #3b82f6 !important; font-size: 20px !important; }
    div[data-testid="stDataFrame"] { border: 1px solid #2563eb !important; border-radius: 8px !important; background-color: #061430 !important; }
    .metric-box { background: #061430; border: 1px solid #2563eb; border-radius: 8px; padding: 12px 16px; text-align: center; }
    .metric-label { font-size: 19px !important; color: #93c5fd; margin-bottom: 4px; font-weight: 700; }
    .metric-val { font-size: 30px !important; font-weight: 900; color: #fff; }
</style>
""", unsafe_allow_html=True)

DEFAULT_TICKERS = ["NVDA", "GOOGL", "TSM", "AMD", "MSFT", "META", "AMZN", "AAPL", "ASML", "TSLA", "VUAG.L", "EQQQ.L"]

FALLBACK_DATA = {
    "NVDA": {"name": "NVIDIA Corp", "price": 177.34, "prev": 186.64, "ma20": 209.10, "ma50": 219.01, "ma200": 204.62, "pe": 22.43, "high52": 195.95, "low52": 86.62, "rsi": 38.7, "eps": 8.31, "mcap": "4.60T"},
    "GOOGL": {"name": "Alphabet Inc", "price": 288.93, "prev": 284.78, "ma20": 314.25, "ma50": 331.77, "ma200": 339.32, "pe": 15.09, "high52": 303.14, "low52": 142.66, "rsi": 55.9, "eps": 19.14, "mcap": "3.54T"},
    "TSM": {"name": "TSMC", "price": 391.23, "prev": 375.44, "ma20": 413.78, "ma50": 431.12, "ma200": 401.76, "pe": 25.36, "high52": 475.59, "low52": 260.50, "rsi": 62.3, "eps": 15.42, "mcap": "2.02T"},
    "AMD": {"name": "Advanced Micro Devices", "price": 509.52, "prev": 449.04, "ma20": 523.06, "ma50": 547.69, "ma200": 417.23, "pe": 108.81, "high52": 607.31, "low52": 128.20, "rsi": 72.5, "eps": 4.68, "mcap": "825B"},
    "MSFT": {"name": "Microsoft", "price": 546.89, "prev": 530.61, "ma20": 531.69, "ma50": 517.31, "ma200": 440.25, "pe": 28.55, "high52": 567.20, "low52": 349.70, "rsi": 64.1, "eps": 19.15, "mcap": "4.06T"},
    "META": {"name": "Meta Platforms", "price": 644.30, "prev": 610.15, "ma20": 657.74, "ma50": 676.24, "ma200": 631.87, "pe": 21.99, "high52": 740.91, "low52": 476.50, "rsi": 59.4, "eps": 29.30, "mcap": "1.63T"},
    "AMZN": {"name": "Amazon.com", "price": 268.44, "prev": 259.30, "ma20": 254.72, "ma50": 253.99, "ma200": 244.09, "pe": 21.70, "high52": 287.38, "low52": 161.67, "rsi": 57.8, "eps": 12.37, "mcap": "2.81T"},
    "AAPL": {"name": "Apple Inc", "price": 351.39, "prev": 342.37, "ma20": 343.91, "ma50": 336.65, "ma200": 299.32, "pe": 39.13, "high52": 377.41, "low52": 169.21, "rsi": 61.6, "eps": 8.98, "mcap": "5.31T"},
    "ASML": {"name": "ASML Holding", "price": 1517.98, "prev": 1424.75, "ma20": 1587.93, "ma50": 1673.69, "ma200": 1600.79, "pe": 37.34, "high52": 1823.54, "low52": 946.11, "rsi": 66.2, "eps": 40.65, "mcap": "605B"},
    "TSLA": {"name": "Tesla Inc", "price": 381.01, "prev": 358.22, "ma20": 380.57, "ma50": 372.78, "ma200": 383.52, "pe": 418.73, "high52": 488.54, "low52": 217.20, "rsi": 58.5, "eps": 0.91, "mcap": "1.21T"},
    "VUAG.L": {"name": "Vanguard S&P 500", "price": 108.54, "prev": 107.66, "ma20": 111.06, "ma50": 111.29, "ma200": 105.44, "pe": None, "high52": 114.69, "low52": 92.65, "rsi": 52.1, "eps": 0.0, "mcap": "ETF"},
    "EQQQ.L": {"name": "Invesco EQQQ", "price": 405.70, "prev": 402.15, "ma20": 416.32, "ma50": 415.87, "ma200": 392.14, "pe": None, "high52": 427.63, "low52": 331.20, "rsi": 54.7, "eps": 0.0, "mcap": "ETF"}
}

for k, v in [("page", "Market Watch"), ("tickers", DEFAULT_TICKERS.copy()), ("selected_ticker", "NVDA"), ("use_live_api", False), ("chart_period", "6个月")]:
    if k not in st.session_state:
        st.session_state[k] = v

@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock_metrics(symbol, live=False):
    fb = FALLBACK_DATA.get(symbol, {"name": f"{symbol} Holdings", "price": 150.0, "prev": 148.0, "ma20": 145.0, "ma50": 140.0, "ma200": 130.0, "pe": 25.0, "high52": 180.0, "low52": 100.0, "rsi": 55.0, "eps": 6.0, "mcap": "120B"})
    if not live:
        return fb
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="1y")
        if hist.empty or len(hist) < 2:
            return fb
        c = hist["Close"]
        delta = c.diff()
        rs = delta.clip(lower=0).rolling(14).mean() / (-delta.clip(upper=0).rolling(14).mean())
        rsi_val = (100 - 100 / (1 + rs)).iloc[-1]
        info = t.info or {}
        pe = info.get("trailingPE")
        eps = info.get("trailingEps")
        mc = info.get("marketCap")
        mcap = f"{mc/1e12:.2f}T" if (mc and mc >= 1e12) else (f"{mc/1e9:.1f}B" if mc else fb["mcap"])
        return {
            "name": info.get("shortName") or fb["name"],
            "price": round(float(c.iloc[-1]), 2), "prev": round(float(c.iloc[-2]), 2),
            "ma20": round(float(c.tail(20).mean()), 2), "ma50": round(float(c.tail(50).mean()), 2), "ma200": round(float(c.tail(200).mean()), 2),
            "high52": round(float(hist["High"].max()), 2), "low52": round(float(hist["Low"].min()), 2),
            "rsi": round(float(rsi_val), 1) if pd.notna(rsi_val) else 50.0,
            "pe": round(float(pe), 2) if (pe and pd.notna(pe)) else fb["pe"],
            "eps": round(float(eps), 2) if (eps and pd.notna(eps)) else fb["eps"],
            "mcap": mcap
        }
    except Exception:
        return fb

@st.cache_data(ttl=300, show_spinner=False)
def fetch_history_df(symbol, period_str, current_price):
    pmap = {"1日": "1d", "1星期": "5d", "3星期": "1mo", "1个月": "1mo", "6个月": "6mo", "1年": "1y", "全部": "max"}
    yfp = pmap.get(period_str, "6mo")
    try:
        hist = yf.Ticker(symbol).history(period=yfp)
        if not hist.empty:
            return hist.reset_index()
    except Exception:
        pass
    ndays = {"1d": 2, "5d": 7, "1mo": 21, "6mo": 120}.get(yfp, 250)
    np.random.seed(abs(hash(symbol + period_str)) % 10000)
    dates = pd.date_range(end=datetime.today(), periods=ndays, freq="B")
    prices = current_price * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, size=len(dates))))
    return pd.DataFrame({"Date": dates, "Close": prices * (current_price / prices[-1])})

@st.cache_data(ttl=
