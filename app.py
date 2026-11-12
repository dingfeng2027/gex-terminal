import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

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

DEFAULT_TICKERS = ["NVDA", "GOOGL", "TSM", "AMD", "MSFT", "META", "AMZN", "AAPL", "ASML", "TSLA", "VUAG.L", "EQQQ.L"]

FALLBACK_DATA = {
    "NVDA": {"name": "NVIDIA Corporation", "price": 177.34, "prev": 186.64, "ma20": 209.10, "ma50": 219.01, "ma200": 204.62, "pe": 22.43, "high52": 195.95, "low52": 86.62, "rsi": 38.7, "eps": 8.31, "mcap": "4.60T"},
    "GOOGL": {"name": "Alphabet Inc.", "price": 288.93, "prev": 284.78, "ma20": 314.25, "ma50": 331.77, "ma200": 339.32, "pe": 15.09, "high52": 303.14, "low52": 142.66, "rsi": 55.9, "eps": 19.14, "mcap": "3.54T"},
    "TSM": {"name": "Taiwan Semiconductor", "price": 391.23, "prev": 375.44, "ma20": 413.78, "ma50": 431.12, "ma200": 401.76, "pe": 25.36, "high52": 475.59, "low52": 260.50, "rsi": 62.3, "eps": 15.42, "mcap": "2.02T"},
    "AMD": {"name": "Advanced Micro Devices", "price": 509.52, "prev": 449.04, "ma20": 523.06, "ma50": 547.69, "ma200": 417.23, "pe": 108.81, "high52": 607.31, "low52": 128.20, "rsi": 72.5, "eps": 4.68, "mcap": "825B"},
    "MSFT": {"name": "Microsoft Corporation", "price": 546.89, "prev": 530.61, "ma20": 531.69, "ma50": 517.31, "ma200": 440.25, "pe": 28.55, "high52": 567.20, "low52": 349.70, "rsi": 64.1, "eps": 19.15, "mcap": "4.06T"},
    "META": {"name": "Meta Platforms Inc.", "price": 644.30, "prev": 610.15, "ma20": 657.74, "ma50": 676.24, "ma200": 631.87, "pe": 21.99, "high52": 740.91, "low52": 476.50, "rsi": 59.4, "eps": 29.30, "mcap": "1.63T"},
    "AMZN": {"name": "Amazon.com Inc.", "price": 268.44, "prev": 259.30, "ma20": 254.72, "ma50": 253.99, "ma200": 244.09, "pe": 21.70, "high52": 287.38, "low52": 161.67, "rsi": 57.8, "eps": 12.37, "mcap": "2.81T"},
    "AAPL": {"name": "Apple Inc.", "price": 351.39, "prev": 342.37, "ma20": 343.91, "ma50": 336.65, "ma200": 299.32, "pe": 39.13, "high52": 377.41, "low52": 169.21, "rsi": 61.6, "eps": 8.98, "mcap": "5.31T"},
    "ASML": {"name": "ASML Holding N.V.", "price": 1517.98, "prev": 1424.75, "ma20": 1587.93, "ma50": 1673.69, "ma200": 1600.79, "pe": 37.34, "high52": 1823.54, "low52": 946.11, "rsi": 66.2, "eps": 40.65, "mcap": "605B"},
    "TSLA": {"name": "Tesla Inc.", "price": 381.01, "prev": 358.22, "ma20": 380.57, "ma50": 372.78, "ma200": 383.52, "pe": 418.73, "high52": 488.54, "low52": 217.20, "rsi": 58.5, "eps": 0.91, "mcap": "1.21T"},
    "VUAG.L": {"name": "Vanguard S&P 500 UCITS", "price": 108.54, "prev": 107.66, "ma20": 111.06, "ma50": 111.29, "ma200": 105.44, "pe": None, "high52": 114.69, "low52": 92.65, "rsi": 52.1, "eps": 0.0, "mcap": "ETF"},
    "EQQQ.L": {"name": "Invesco EQQQ NASDAQ-100", "price": 405.70, "prev": 402.15, "ma20": 416.32, "ma50": 415.87, "ma200": 392.14, "pe": None, "high52": 427.63, "low52": 331.20, "rsi": 54.7, "eps": 0.0, "mcap": "ETF"}
}

if "page" not in st.session_state:
    st.session_state.page = "Market Watch"
if "tickers" not in st.session_state:
    st.session_state.tickers = DEFAULT_TICKERS.copy()
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = "NVDA"
if "use_live_api" not in st.session_state:
    st.session_state.use_live_api = False
if "chart_period" not in st.session_state:
    st.session_state.chart_period = "6个月"

def compute_rsi(series, period=14):
    try:
        delta = series.diff()
        gain = delta.clip(lower=0).rolling(window=period).mean()
        loss = -delta.clip(upper=0).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        val = rsi.iloc[-1]
        return round(float(val), 1) if pd.notna(val) else 50.0
    except Exception:
        return 50.0

@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock_metrics(symbol, live=False):
    fb = FALLBACK_DATA.get(symbol, {
        "name": f"{symbol} Holdings", "price": 150.00, "prev": 148.00,
        "ma20": 145.00, "ma50": 140.00, "ma200": 130.00, "pe": 25.0,
        "high52": 180.00, "low52": 100.00, "rsi": 55.0, "eps": 6.0, "mcap": "120B"
    })
    if not live:
        return fb
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="1y")
        if hist.empty or len(hist) < 2:
            return fb
        close = hist["Close"]
        price, prev = round(float(close.iloc[-1]), 2), round(float(close.iloc[-2]), 2)
        ma20, ma50, ma200 = round(float(close.tail(20).mean()), 2), round(float(close.tail(50).mean()), 2), round(float(close.tail(200).mean()), 2)
        high52, low52 = round(float(hist["High"].max()), 2), round(float(hist["Low"].min()), 2)
        rsi = compute_rsi(close, 14)
        info = t.info or {}
        pe = info.get("trailingPE")
        pe = round(float(pe), 2) if (pe and pd.notna(pe)) else fb["pe"]
        eps = info.get("trailingEps")
        eps = round(float(eps), 2) if (eps and pd.notna(eps)) else fb["eps"]
        name = info.get("shortName") or fb["name"]
        mcap_raw = info.get("marketCap")
        mcap = f"{mcap_raw/1e12:.2f}T" if (mcap_raw and mcap_raw >= 1e12) else (f"{mcap_raw/1e9:.1f}B" if mcap_raw else fb["mcap"])
        return {"name": name, "price": price, "prev": prev, "ma20": ma20, "ma50": ma50, "ma200": ma200, "pe": pe, "high52": high52, "low52": low52, "rsi": rsi, "eps": eps, "mcap": mcap}
    except Exception:
        return fb

@st.cache_data(ttl=300, show_spinner=False)
def fetch_history_df(symbol, period_str, current_price):
    period_map = {"1日": "1d", "1星期": "5d", "3星期": "1mo", "1个月": "1mo", "6个月": "6mo", "1年": "1y", "全部": "max"}
    yf_period = period_map.get(period_str, "6mo")
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period=yf_period)
        if not hist.empty:
            hist = hist.reset_index()
            return hist
    except Exception:
        pass
    
    if yf_period == "1d":
        n_days = 2
    elif yf_period == "5d":
        n_days = 7
    elif yf_period == "1mo":
        n_days = 21
    elif yf_period == "6mo":
        n_days = 120
    else:
        n_days = 250
        
    np.random.seed(abs(hash(symbol + period_str)) % 10000)
    dates = pd.date_range(end=datetime.today(), periods=n_days, freq="B")
    prices = current_price * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, size=len(dates))))
    prices = prices * (current_price / prices[-1])
    df = pd.DataFrame({"Date": dates, "Close": prices})
    return df

@st.cache_data(ttl=300, show_spinner=False)
def fetch_options_chain(symbol, spot_price):
    exps = [(datetime.today() + timedelta(days=7 * i)).strftime("%Y-%m-%d") for i in range(1, 7)]
    step = 5.0 if spot_price > 100 else 2.5
    base_strike = round(spot_price / step) * step
    strikes = [round(base_strike + i * step, 2) for i in range(-8, 9)]
    calls_rows, puts_rows = [], []
    for k in strikes:
        moneyness = (spot_price - k) / spot_price
        iv = round(0.32 + abs(moneyness) * 0.45, 4)
        c_p = round(max(0.15, (spot_price - k) + spot_price * iv * 0.08), 2)
        p_p = round(max(0.15, (k - spot_price) + spot_price * iv * 0.08), 2)
        c_v = int(max(50, 4500 *
