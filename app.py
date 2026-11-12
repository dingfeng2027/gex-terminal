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

if "page" not in st.session_state: st.session_state.page = "Market Watch"
if "tickers" not in st.session_state: st.session_state.tickers = DEFAULT_TICKERS.copy()
if "selected_ticker" not in st.session_state: st.session_state.selected_ticker = "NVDA"
if "use_live_api" not in st.session_state: st.session_state.use_live_api = False
if "chart_period" not in st.session_state: st.session_state.chart_period = "6个月"

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
        c_v = int(max(50, 4500 * np.exp(-12 * moneyness**2)))
        p_v = int(max(50, 4100 * np.exp(-12 * moneyness**2)))
        calls_rows.append({"strike": k, "lastPrice": c_p, "bid": round(c_p*0.98, 2), "ask": round(c_p*1.02, 2), "volume": c_v, "openInterest": c_v * 4, "impliedVolatility": iv})
        puts_rows.append({"strike": k, "lastPrice": p_p, "bid": round(p_p*0.98, 2), "ask": round(p_p*1.02, 2), "volume": p_v, "openInterest": p_v * 4, "impliedVolatility": iv})
    return exps, exps[0], pd.DataFrame(calls_rows), pd.DataFrame(puts_rows), False

now_str = datetime.now().strftime("%b %d, %Y %H:%M:%S")
st.markdown(f"""
<div class="top-bar">
    <div class="brand-title">CAPITAL QUANT v2</div>
    <div class="live-badge">Live | {now_str} | UK Institutional Terminal</div>
</div>
""", unsafe_allow_html=True)

nav1, nav2, nav3, nav4 = st.columns([1.3, 1.3, 1.6, 2.2])
with nav1:
    if st.button("1. Market Watch", use_container_width=True): st.session_state.page = "Market Watch"; st.rerun()
with nav2:
    if st.button("2. Stock Analysis", use_container_width=True): st.session_state.page = "Stock Analysis"; st.rerun()
with nav3:
    if st.button("3. Put & Call Options", use_container_width=True): st.session_state.page = "Options Data"; st.rerun()
with nav4:
    st.session_state.use_live_api = st.toggle("启用实时 Yahoo Finance 行情接口", value=st.session_state.use_live_api)

st.markdown("---")

if st.session_state.page == "Market Watch":
    c_title, c_input, c_add, c_refresh = st.columns([2.0, 2.2, 1.2, 1.3])
    with c_title: st.markdown("### Market Watch")
    with c_input: new_ticker = st.text_input("Add Ticker", placeholder="输入代码 (如 SMCI, MRVL)", label_visibility="collapsed").strip().upper()
    with c_add:
        if st.button("ADD TICKER", use_container_width=True):
            if new_ticker and new_ticker not in st.session_state.tickers:
                st.session_state.tickers.append(new_ticker); st.rerun()
    with c_refresh:
        if st.button("UPDATE ALL", use_container_width=True): st.cache_data.clear(); st.rerun()

    st.markdown("💡 **操作提示**：点击表格左侧勾选框或任意一行公司，即可自动进入第 2 页 **Stock Analysis** 查看详细技术面与阶梯价位。")

    rows, gainers, losers = [], 0, 0
    for sym in st.session_state.tickers:
        d = fetch_stock_metrics(sym, live=st.session_state.use_live_api)
        chg = round(d["price"] - d["prev"], 2)
        pct = round((chg / d["prev"]) * 100, 2) if d["prev"] else 0.0
        if chg > 0: gainers += 1
        elif chg < 0: losers += 1
        rows.append({
            "COMPANY CODE": sym,
            "TODAY PRICE": d["price"],
            "YESTERDAY PRICE": d["prev"],
            "CHANGE": chg,
            "% CHANGE": pct,
            "MA20": d["ma20"],
            "MA50": d["ma50"],
            "MA200": d["ma200"],
            "PE RATE": f"{d['pe']:.2f}" if d["pe"] else "None",
            "YEARLY HIGH": d["high52"],
            "YEARLY LOW": d["low52"],
            "RSI (14)": d["rsi"]
        })

    df_watch = pd.DataFrame(rows)

    def style_watch_table(val, col_name):
        base = "background-color: #07193d; font-size: 22px; font-weight: 700;"
        if col_name in ["CHANGE", "% CHANGE"]:
            color = "#4ade80" if val > 0 else ("#f87171" if val < 0 else "#ffffff")
            return base + " color: " + color + ";"
        if col_name == "RSI (14)":
            if val >= 70: return "background-color: #dc2626; color: #ffffff; font-size: 22px; font-weight: 800;"
            elif val <= 40: return "background-color: #eab308; color: #000000; font-size: 22px; font-weight: 800;"
            else: return "background-color: #16a34a; color: #ffffff; font-size: 22px; font-weight: 800;"
        if col_name == "COMPANY CODE": return base + " color: #60a5fa; font-weight: 900;"
        if col_name == "TODAY PRICE": return base + " color: #facc15; font-weight: 800;"
        return base + " color: #ffffff;"

    styled_df = df_watch.style.apply(lambda col: [style_watch_table(v, col.name) for v in col], axis=0).format({
        "TODAY PRICE": "{:.2f}", "YESTERDAY PRICE": "{:.2f}", "CHANGE": "{:+.2f}", "% CHANGE": "{:+.2f}%",
        "MA20": "{:.2f}", "MA50": "{:.2f}", "MA200": "{:.2f}", "YEARLY HIGH": "{:.2f}", "YEARLY LOW": "{:.2f}", "RSI (14)": "{:.1f}"
    })

    event = st.dataframe(styled_df, use_container_width=True, height=500, row_height=48, hide_index=True, on_select="rerun", selection_mode="single-row")

    if event and event.selection and len(event.selection.rows) > 0:
        st.session_state.selected_ticker = df_watch.iloc[event.selection.rows[0]]["COMPANY CODE"]
        st.session_state.page = "Stock Analysis"
        st.rerun()

    b_left, b_mid, b_right = st.columns([2.4, 2.2, 2.4])
    with b_left:
        if st.button(f"OPEN COMPANY ANALYSIS ({st.session_state.selected_ticker}) >", use_container_width=True):
            st.session_state.page = "Stock Analysis"; st.rerun()
    with b_mid:
        del_sym = st.selectbox("移除自选股", ["选择要删除的代码..."] + st.session_state.tickers, label_visibility="collapsed")
        if del_sym != "选择要删除的代码...":
            st.session_state.tickers.remove(del_sym)
            st.rerun()
    with b_right:
        st.markdown(f"<div style='text-align:right; padding-top:6px; font-size:21px; font-weight:800;'><span style='color:#4ade80;'>▲ {gainers} Gainers</span> &nbsp;|&nbsp; <span style='color:#f87171;'>● {losers} Losers</span> &nbsp;|&nbsp; Total: {len(df_watch)}</div>", unsafe_allow_html=True)

elif st.session_state.page == "Stock Analysis":
    top_l, top_sel, top_opt, top_back = st.columns([2.0, 2.4, 2.2, 1.2])
    with top_l: st.markdown("### Stock Analysis")
    with top_sel:
        current_idx = st.session_state.tickers.index(st.session_state.selected_ticker) if st.session_state.selected_ticker in st.session_state.tickers else 0
        chosen = st.selectbox("选择分析标的", st.session_state.tickers, index=current_idx, label_visibility="collapsed")
        if chosen != st.session_state.selected_ticker: st.session_state.selected_ticker = chosen; st.rerun()
    with top_opt:
        if st.button("PUT & CALL OPTIONS DATA >", use_container_width=True): st.session_state.page = "Options Data"; st.rerun()
    with top_back:
        if st.button("← BACK", use_container_width=True): st.session_state.page = "Market Watch"; st.rerun()

    sym = st.session_state.selected_ticker
    metrics = fetch_stock_metrics(sym, live=st.session_state.use_live_api)

    col_chart, col_levels = st.columns([2.5, 1.1])
    with col_chart:
        st.markdown(f"<div class='card-header'>{sym} — {metrics['name']} | Price Chart & Historical Range</div>", unsafe_allow_html=True)
        
        # 水平排列胶囊按钮
        periods = ["1日", "1星期", "3星期", "1个月", "6个月", "1年", "全部"]
        p_cols = st.columns(len(periods))
        for idx, p in enumerate(periods):
            with p_cols[idx]:
                is_selected = (st.session_state.chart_period == p)
                btn_bg = "#ffffff" if is_selected else "linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%)"
                btn_fg = "#000000" if is_selected else "#ffffff"
                btn_fw = "900" if is_selected else "700"
                
                st.markdown(f"""
                <style>
                div.stButton > button[data-baseweb="button"]:nth-of-type({idx+1}) {{
                    background: {btn_bg} !important;
                    color: {btn_fg} !important;
                    font-weight: {btn_fw} !important;
                }}
                </style>
                """, unsafe_allow_html=True)
                
                if st.button(p, use_container_width=True, key=f"period_btn_{p}"):
                    st.session_state.chart_period = p
                    st.rerun()

        hist_df = fetch_history_df(sym, st.session_state.chart_period, metrics["price"])
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist_df["Date"], y=hist_df["Close"], mode="lines", line=dict(color="#0284c7", width=2.5), name="Price"))
        fig.add_hline(y=metrics["price"], line_dash="dash", line_color="#64748b", line_width=1.5, annotation_text=f"  {metrics['price']:.2f}  ", annotation_position="right", annotation_font=dict(color="#ffffff", size=15), annotation_bgcolor="#334155")

        # 将高度精确锁定为 455 像素
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            xaxis_rangeslider_visible=False,
            height=455,
            font=dict(size=18, color="#1e293b"),
            margin=dict(l=10, r=70, t=10, b=10),
            showlegend=False
        )
        fig.update_xaxes(gridcolor="#e2e8f0", zerolinecolor="#e2e8f0")
        fig.update_yaxes(gridcolor="#e2e8f0", zerolinecolor="#e2e8f0", side="right")
        st.plotly_chart(fig, use_container_width=True)

    with col_levels:
        st.markdown("<div class='card-header'>PRICE LEVEL LADDER</div>", unsafe_allow_html=True)
        curr = metrics["price"]
        pct_list = [20, 15, 12, 10, 8, 6, 0, -6, -8, -10, -12, -15, -18, -20]
        
        # 使用完全可控的 HTML 表格来渲染阶梯价位，高度锁定 455 像素，实现像素级完美对齐
        html_table = """
        <div style="background-color: #061430; border: 1px solid #2563eb; border-radius: 8px; height: 455px; overflow-y: auto; padding: 4px;">
            <table style="width: 100%; border-collapse: collapse; font-family: 'Segoe UI', sans-serif;">
                <thead>
                    <tr style="border-bottom: 2px solid #1e3a8a; color: #93c5fd; font-size: 18px; text-align: left;">
                        <th style="padding: 10px 12px; font-weight: 800;">LEVEL</th>
                        <th style="padding: 10px 12px; font-weight: 800; text-align: right;">TARGET PRICE</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for pct in pct_list:
            label = "CURRENT" if pct == 0 else f"{pct:+d}%"
            target_p = round(curr * (1 + pct / 100.0), 2)
            
            if pct == 0:
                row_bg = "#eab308"
                text_color = "#000000"
                font_weight = "900"
                font_size = "21px"
            elif pct > 0:
                row_bg = "#07193d"
                text_color = "#4ade80"
                font_weight = "700"
                font_size = "20px"
            else:
                row_bg = "#07193d"
                text_color = "#f87171"
                font_weight = "700"
                font_size = "20px"
                
            html_table += f"""
                    <tr style="background-color: {row_bg}; border-bottom: 1px solid #1e3a8a;">
                        <td style="padding: 8.5px 12px; color: {text_color}; font-weight: {font_weight}; font-size: {font_size};">{label}</td>
                        <td style="padding: 8.5px 12px; color: {text_color}; font-weight: {font_weight}; font-size: {font_size}; text-align: right;">{target_p:.2f}</td>
                    </tr>
            """
            
        html_table += """
                </tbody>
            </table>
        </div>
        """
        st.markdown(html_table, unsafe_allow_html=True)

    chg = round(metrics["price"] - metrics["prev"], 2)
    pct_chg = round((chg / metrics["prev"]) * 100, 2) if metrics["prev"] else 0.0
    c_col = "#4ade80" if chg >= 0 else "#f87171"
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.markdown(f"<div class='metric-box'><div class='metric-label'>Current Price</div><div class='metric-val'>{metrics['price']:.2f} <span style='font-size:20px;color:{c_col};'>({pct_chg:+.2f}%)</span></div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='metric-box'><div class='metric-label'>52 Week High</div><div class='metric-val'>{metrics['high52']:.2f}</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='metric-box'><div class='metric-label'>52 Week Low</div><div class='metric-val'>{metrics['low52']:.2f}</div></div>", unsafe_allow_html=True)
    k4.markdown(f"<div class='metric-box'><div class='metric-label'>Market Cap</div><div class='metric-val'>{metrics['mcap']}</div></div>", unsafe_allow_html=True)
    k5.markdown(f"<div class='metric-box'><div class='metric-label'>P/E Ratio / EPS</div><div class='metric-val'>{metrics['pe'] if metrics['pe'] else 'N/A'} / {metrics['eps']}</div></div>", unsafe_allow_html=True)
    k6.markdown(f"<div class='metric-box'><div class='metric-label'>RSI (14)</div><div class='metric-val' style='color:#38bdf8;'>{metrics['rsi']:.1f}</div></div>", unsafe_allow_html=True)

elif st.session_state.page == "Options Data":
    o_title, o_sel, o_back2, o_back1 = st.columns([2.3, 2.1, 1.5, 1.5])
    with o_title: st.markdown("### Put & Call Option Data")
    with o_sel:
        current_idx = st.session_state.tickers.index(st.session_state.selected_ticker) if st.session_state.selected_ticker in st.session_state.tickers else 0
        chosen_opt = st.selectbox("选择期权标的", st.session_state.tickers, index=current_idx, label_visibility="collapsed")
        if chosen_opt != st.session_state.selected_ticker: st.session_state.selected_ticker = chosen_opt; st.rerun()
    with o_back2:
        if st.button("← Stock Analysis", use_container_width=True): st.session_state.page = "Stock Analysis"; st.rerun()
    with o_back1:
        if st.button("Market Watch", use_container_width=True): st.session_state.page = "Market Watch"; st.rerun()

    sym = st.session_state.selected_ticker
    metrics = fetch_stock_metrics(sym, live=st.session_state.use_live_api)
    spot = metrics["price"]
    exps, default_exp, calls_df, puts_df, is_real_opt = fetch_options_chain(sym, spot)

    exp_col, info_col = st.columns([1.6, 3.4])
    with exp_col: selected_exp = st.selectbox("选择到期日 (Expiration Date)", exps, index=0)
    with info_col:
        data_tag = "🟢 实时期权链数据 (Yahoo Options)" if is_real_opt else "🟡 量化模型仿真期权链"
        st.markdown(f"<div style='padding-top:28px; font-size:21px; font-weight:700; color:#93c5fd;'>标的现价: <span style='color:#facc15;font-size:30px;'>${spot:.2f}</span> &nbsp;|&nbsp; {data_tag}</div>", unsafe_allow_html=True)

    calls_sub, puts_sub = calls_df.copy(), puts_df.copy()
    calls_sub["dist"] = (calls_sub["strike"] - spot).abs()
    closest_strikes = calls_sub.nsmallest(15, "dist")["strike"].sort_values().tolist()
    c_filt = calls_sub[calls_sub["strike"].isin(closest_strikes)].set_index("strike")
    p_filt = puts_sub[puts_sub["strike"].isin(closest_strikes)].set_index("strike")

    total_call_oi = int(c_filt["openInterest"].fillna(0).sum())
    total_put_oi = int(p_filt["openInterest"].fillna(0).sum())
    pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 1.0
    avg_iv = round(float(c_filt["impliedVolatility"].fillna(0.3).mean()) * 100, 1)

    min_pain_val, max_pain_strike = float("inf"), spot
    for k in closest_strikes:
        c_loss = sum(max(0, k - s) * c_filt.loc[s, "openInterest"] for s in closest_strikes if s in c_filt.index)
        p_loss = sum(max(0, s - k) * p_filt.loc[s, "openInterest"] for s in closest_strikes if s in p_filt.index)
        if (c_loss + p_loss) < min_pain_val:
            min_pain_val = c_loss + p_loss; max_pain_strike = k

    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f"<div class='metric-box'><div class='metric-label'>Put / Call OI Ratio</div><div class='metric-val'>{pcr:.2f}</div></div>", unsafe_allow_html=True)
    m2.markdown(f"<div class='metric-box'><div class='metric-label'>Implied Volatility (Avg IV)</div><div class='metric-val' style='color:#38bdf8;'>{avg_iv:.1f}%</div></div>", unsafe_allow_html=True)
    m3.markdown(f"<div class='metric-box'><div class='metric-label'>Max Pain Strike</div><div class='metric-val' style='color:#facc15;'>${max_pain_strike:.2f}</div></div>", unsafe_allow_html=True)
    m4.markdown(f"<div class='metric-box'><div class='metric-label'>Total Active OI (Calls / Puts)</div><div class='metric-val'>{total_call_oi:,} / {total_put_oi:,}</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    straddle_rows = []
    atm_strike = min(closest_strikes, key=lambda x: abs(x - spot)) if closest_strikes else spot

    for k in closest_strikes:
        c_r = c_filt.loc[k] if k in c_filt.index else {}
        p_r = p_filt.loc[k] if k in p_filt.index else {}
        if isinstance(c_r, pd.DataFrame): c_r = c_r.iloc[0]
        if isinstance(p_r, pd.DataFrame): p_r = p_r.iloc[0]
        straddle_rows.append({
            "CALL OI": int(c_r.get("openInterest", 0) or 0), "CALL VOL": int(c_r.get("volume", 0) or 0),
            "CALL IV": f"{float(c_r.get('impliedVolatility', 0) or 0)*100:.1f}%", "CALL BID": float(c_r.get("bid", 0) or 0),
            "CALL ASK": float(c_r.get("ask", 0) or 0), "CALL LAST": float(c_r.get("lastPrice", 0) or 0),
            "STRIKE": float(k), "PUT LAST": float(p_r.get("lastPrice", 0) or 0), "PUT BID": float(p_r.get("bid", 0) or 0),
            "PUT ASK": float(p_r.get("ask", 0) or 0), "PUT IV": f"{float(p_r.get('impliedVolatility', 0) or 0)*100:.1f}%",
            "PUT VOL": int(p_r.get("volume", 0) or 0), "PUT OI": int(p_r.get("openInterest", 0) or 0),
        })

    df_straddle = pd.DataFrame(straddle_rows)

    def style_options_chain(row):
        styles, is_atm = [], (row["STRIKE"] == atm_strike)
        for col in row.index:
            if col == "STRIKE":
                styles.append("background-color: #eab308; color: #000000; font-size: 22px; font-weight: 900;" if is_atm else "background-color: #1e3a8a; color: #ffffff; font-size: 22px; font-weight: 800;")
            elif col.startswith("CALL"):
                styles.append(f"background-color: {'#0c2b1e' if row['STRIKE'] < spot else '#07193d'}; color: #86efac; font-size: 20px; font-weight: 700;")
            else:
                styles.append(f"background-color: {'#2d1218' if row['STRIKE'] > spot else '#07193d'}; color: #fca5a5; font-size: 20px; font-weight: 700;")
        return styles

    st.markdown("<div class='card-header'>T-SHAPED STRADDLE OPTIONS CHAIN (LEFT: CALLS | CENTER: STRIKE | RIGHT: PUTS)</div>", unsafe_allow_html=True)
    st.dataframe(df_straddle.style.apply(style_options_chain, axis=1).format({
        "CALL BID": "{:.2f}", "CALL ASK": "{:.2f}", "CALL LAST": "{:.2f}", "STRIKE": "{:.2f}",
        "PUT LAST": "{:.2f}", "PUT BID": "{:.2f}", "PUT ASK": "{:.2f}"
    }), use_container_width=True, height=500, row_height=50, hide_index=True)

    st.markdown("<div class='card-header'>OPEN INTEREST DISTRIBUTION BY STRIKE (CALLS VS PUTS)</div>", unsafe_allow_html=True)
    fig_oi = go.Figure()
    fig_oi.add_trace(go.Bar(x=df_straddle["STRIKE"], y=df_straddle["CALL OI"], name="Call Open Interest", marker_color="#22c55e"))
    fig_oi.add_trace(go.Bar(x=df_straddle["STRIKE"], y=df_straddle["PUT OI"], name="Put Open Interest", marker_color="#ef4444"))
    fig_oi.add_vline(x=spot, line_dash="dash", line_color="#facc15", annotation_text=f"Spot: {spot:.2f}")
    fig_oi.update_layout(barmode="group", template="plotly_dark", paper_bgcolor="rgba(6, 20, 48, 0.95)", plot_bgcolor="rgba(4, 14, 34, 0.98)", height=320, font=dict(size=18, color="#ffffff"), margin=dict(l=10, r=10, t=25, b=10))
    st.plotly_chart(fig_oi, use_container_width=True)
