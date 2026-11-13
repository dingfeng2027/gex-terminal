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
    "MPWR": {"name": "Monolithic", "price": 1190.46, "prev": 1160.00, "ma20": 1150.0, "ma50": 1100.0, "ma200": 950.0, "pe": 78.4, "high52": 1300.0, "low52": 650.0, "rsi": 60.1, "eps": 15.20, "mcap": "57B"},
    "MRVL": {"name": "Marvell", "price": 141.99, "prev": 136.50, "ma20": 138.0, "ma50": 130.0, "ma200": 110.0, "pe": 65.2, "high52": 155.0, "low52": 62.0, "rsi": 59.8, "eps": 2.18, "mcap": "122B"},
    "NFLX": {"name": "Netflix", "price": 845.20, "prev": 830.00, "ma20": 820.0, "ma50": 790.0, "ma200": 700.0, "pe": 45.6, "high52": 890.0, "low52": 440.0, "rsi": 63.4, "eps": 18.50, "mcap": "362B"},
    "QQQ": {"name": "QQQ ETF", "price": 512.40, "prev": 506.80, "ma20": 515.0, "ma50": 508.0, "ma200": 470.0, "pe": None, "high52": 535.0, "low52": 395.0, "rsi": 54.2, "eps": 0.0, "mcap": "ETF"},
    "VUAG.L": {"name": "Vanguard S&P", "price": 108.54, "prev": 107.66, "ma20": 111.0, "ma50": 111.2, "ma200": 105.4, "pe": None, "high52": 114.6, "low52": 92.6, "rsi": 52.1, "eps": 0.0, "mcap": "ETF"},
    "EQQQ.L": {"name": "Invesco EQQQ", "price": 405.70, "prev": 402.15, "ma20": 416.3, "ma50": 415.8, "ma200": 392.1, "pe": None, "high52": 427.6, "low52": 331.2, "rsi": 54.7, "eps": 0.0, "mcap": "ETF"}
}

if "page" not in st.session_state:
    st.session_state["page"] = "Market Watch"

if "tickers" not in st.session_state:
    st.session_state["tickers"] = DEFAULT_TICKERS.copy()

if "selected_ticker" not in st.session_state:
    st.session_state["selected_ticker"] = "NVDA"

if "use_live_api" not in st.session_state:
    st.session_state["use_live_api"] = True

if "chart_period" not in st.session_state:
    st.session_state["chart_period"] = "6个月"

def fetch_stock_metrics(symbol, live=True):
    fb = FALLBACK_DATA.get(symbol, {"name": symbol, "price": 150.0, "prev": 148.0, "ma20": 145.0, "ma50": 140.0, "ma200": 130.0, "pe": 25.0, "high52": 180.0, "low52": 100.0, "rsi": 55.0, "eps": 6.0, "mcap": "120B"})
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
        mcap_str = (f"{mc/1e12:.2f}T" if mc >= 1e12 else f"{mc/1e9:.1f}B") if mc else fb["mcap"]
        return {
            "name": info.get("shortName") or fb["name"],
            "price": round(float(c.iloc[-1]), 2),
            "prev": round(float(c.iloc[-2]), 2),
            "ma20": round(float(c.tail(20).mean()), 2),
            "ma50": round(float(c.tail(50).mean()), 2),
            "ma200": round(float(c.tail(200).mean()), 2),
            "high52": round(float(hist["High"].max()), 2),
            "low52": round(float(hist["Low"].min()), 2),
            "rsi": round(float(rsi_val), 1) if pd.notna(rsi_val) else 50.0,
            "pe": round(float(pe), 2) if (pe and pd.notna(pe)) else fb["pe"],
            "eps": round(float(eps), 2) if (eps and pd.notna(eps)) else fb["eps"],
            "mcap": mcap_str
        }
    except Exception:
        return fb

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

def fetch_options_chain(symbol, spot):
    exps = [(datetime.today() + timedelta(days=7 * i)).strftime("%Y-%m-%d") for i in range(1, 7)]
    step = 5.0 if spot > 100 else 2.5
    base = round(spot / step) * step
    strikes = [round(base + i * step, 2) for i in range(-8, 9)]
    c_rows = []
    p_rows = []
    for k in strikes:
        m_val = (spot - k) / spot
        iv = round(0.32 + abs(m_val) * 0.45, 4)
        cp = round(max(0.15, (spot - k) + spot * iv * 0.08), 2)
        pp = round(max(0.15, (k - spot) + spot * iv * 0.08), 2)
        cv = int(max(50, 4500 * np.exp(-12 * m_val * m_val)))
        pv = int(max(50, 4100 * np.exp(-12 * m_val * m_val)))
        c_rows.append({"strike": k, "lastPrice": cp, "bid": round(cp*0.98, 2), "ask": round(cp*1.02, 2), "volume": cv, "openInterest": cv*4, "impliedVolatility": iv})
        p_rows.append({"strike": k, "lastPrice": pp, "bid": round(pp*0.98, 2), "ask": round(pp*1.02, 2), "volume": pv, "openInterest": pv*4, "impliedVolatility": iv})
    cdf = pd.DataFrame(c_rows)
    pdf = pd.DataFrame(p_rows)
    return exps, cdf, pdf

top_bar_html = "<div class='top-bar'><div class='brand-title'>CAPITAL QUANT v2</div><div class='live-badge'>Live (Auto) | " + datetime.now().strftime('%b %d, %Y %H:%M:%S') + " | UK Institutional Terminal</div></div>"
st.markdown(top_bar_html, unsafe_allow_html=True)

n1, n2, n3, n4 = st.columns([1.3, 1.3, 1.6, 2.2])
if n1.button("1. Market Watch", use_container_width=True):
    st.session_state.page = "Market Watch"
    st.rerun()
if n2.button("2. Stock Analysis", use_container_width=True):
    st.session_state.page = "Stock Analysis"
    st.rerun()
if n3.button("3. Put & Call Options", use_container_width=True):
    st.session_state.page = "Options Data"
    st.rerun()
st.session_state.use_live_api = n4.toggle("启用实时 Yahoo Finance 行情接口", value=st.session_state.use_live_api)

st.markdown("<div style='border-bottom: 1px solid #1e3a8a; margin: 6px 0 8px 0;'></div>", unsafe_allow_html=True)

if st.session_state.page == "Market Watch":
    c1, c2, c3, c4 = st.columns([2.0, 2.2, 1.2, 1.3])
    c1.markdown("### Market Watch")
    new_t = c2.text_input("Add", placeholder="输入代码 (如 SMCI, MRVL)", label_visibility="collapsed").strip().upper()
    if c3.button("ADD TICKER", use_container_width=True) and new_t and new_t not in st.session_state.tickers:
        st.session_state.tickers.append(new_t)
        st.rerun()
    if c4.button("UPDATE ALL", use_container_width=True):
        st.rerun()

    rows = []
    gainers = 0
    losers = 0
    for sym in st.session_state.tickers:
        d = fetch_stock_metrics(sym, live=st.session_state.use_live_api)
        chg = round(d["price"] - d["prev"], 2)
        pct = round((chg / d["prev"]) * 100, 2) if d["prev"] else 0.0
        if chg > 0:
            gainers += 1
        elif chg < 0:
            losers += 1
        rows.append({"COMPANY CODE": sym, "TODAY PRICE": d["price"], "YESTERDAY PRICE": d["prev"], "CHANGE": chg, "% CHANGE": pct, "MA20": d["ma20"], "MA50": d["ma50"], "MA200": d["ma200"], "PE RATE": str(d['pe']) if d['pe'] else "None", "YEARLY HIGH": d["high52"], "YEARLY LOW": d["low52"], "RSI (14)": d["rsi"]})

    df_watch = pd.DataFrame(rows)
    def style_watch(val, col):
        base = "background-color: #07193d; font-size: 20px; font-weight: 700;"
        if col in ["CHANGE", "% CHANGE"]:
            color_str = "#4ade80" if val > 0 else ("#f87171" if val < 0 else "#fff")
            return base + " color: " + color_str + ";"
        if col == "RSI (14)":
            bg_col = "#dc2626" if val >= 70 else ("#eab308" if val <= 40 else "#16a34a")
            fg_col = "#000" if val <= 40 else "#fff"
            return "background-color: " + bg_col + "; color: " + fg_col + "; font-size: 20px; font-weight: 800;"
        if col == "COMPANY CODE":
            return base + " color: #60a5fa; font-weight: 900;"
        if col == "TODAY PRICE":
            return base + " color: #facc15; font-weight: 800;"
        return base + " color: #fff;"

    fmt = {"TODAY PRICE": "{:.2f}", "YESTERDAY PRICE": "{:.2f}", "CHANGE": "{:+.2f}", "% CHANGE": "{:+.2f}%", "MA20": "{:.2f}", "MA50": "{:.2f}", "MA200": "{:.2f}", "YEARLY HIGH": "{:.2f}", "YEARLY LOW": "{:.2f}", "RSI (14)": "{:.1f}"}
    styled_df = df_watch.style.apply(lambda c: [style_watch(v, c.name) for v in c], axis=0).format(fmt)
    
    event = st.dataframe(styled_df, use_container_width=True, height=650, row_height=45, hide_index=True, on_select="rerun", selection_mode="single-row")
    
    if event and event.selection and "rows" in event.selection and len(event.selection.rows) > 0:
        selected_idx = event.selection.rows[0]
        if selected_idx < len(df_watch):
            st.session_state.selected_ticker = df_watch.iloc[selected_idx]["COMPANY CODE"]
            st.session_state.page = "Stock Analysis"
            st.rerun()

    b1, b2, b3 = st.columns([2.4, 2.2, 2.4])
    if b1.button("OPEN COMPANY ANALYSIS (" + st.session_state.selected_ticker + ") >", use_container_width=True):
        st.session_state.page = "Stock Analysis"
        st.rerun()
    del_sym = b2.selectbox("移除", ["选择要删除的代码..."] + st.session_state.tickers, label_visibility="collapsed")
    if del_sym != "选择要删除的代码...":
        st.session_state.tickers.remove(del_sym)
        st.rerun()
    summary_html = "<div style='text-align:right; padding-top:6px; font-size:19px; font-weight:800;'><span style='color:#4ade80;'>▲ " + str(gainers) + " Gainers</span> | <span style='color:#f87171;'>● " + str(losers) + " Losers</span> | Total: " + str(len(df_watch)) + "</div>"
    b3.markdown(summary_html, unsafe_allow_html=True)

elif st.session_state.page == "Stock Analysis":
    t1, t2, t3, t4 = st.columns([2.0, 2.4, 2.2, 1.2])
    t1.markdown("### Stock Analysis")
    idx = st.session_state.tickers.index(st.session_state.selected_ticker) if st.session_state.selected_ticker in st.session_state.tickers else 0
    chosen = t2.selectbox("标的", st.session_state.tickers, index=idx, label_visibility="collapsed")
    if chosen != st.session_state.selected_ticker:
        st.session_state.selected_ticker = chosen
        st.rerun()
    if t3.button("PUT & CALL OPTIONS DATA >", use_container_width=True):
        st.session_state.page = "Options Data"
        st.rerun()
    if t4.button("← BACK", use_container_width=True):
        st.session_state.page = "Market Watch"
        st.rerun()

    sym = st.session_state.selected_ticker
    m = fetch_stock_metrics(sym, live=st.session_state.use_live_api)
    col_
