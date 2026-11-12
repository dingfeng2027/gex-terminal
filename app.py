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

def fetch_stock_metrics(symbol, live=False):
    fb = FALLBACK_DATA.get(symbol, {"name": symbol + " Holdings", "price": 150.0, "prev": 148.0, "ma20": 145.0, "ma50": 140.0, "ma200": 130.0, "pe": 25.0, "high52": 180.0, "low52": 100.0, "rsi": 55.0, "eps": 6.0, "mcap": "120B"})
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
            "price": round(float(c.iloc[-1]), 2), "prev": round(float(c.iloc[-2]), 2),
            "ma20": round(float(c.tail(20).mean()), 2), "ma50": round(float(c.tail(50).mean()), 2), "ma200": round(float(c.tail(200).mean()), 2),
            "high52": round(float(hist["High"].max()), 2), "low52": round(float(hist["Low"].min()), 2),
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
    c_rows, p_rows = [], []
    for k in strikes:
        m_val = (spot - k) / spot
        iv = round(0.32 + abs(m_val) * 0.45, 4)
        cp = round(max(0.15, (spot - k) + spot * iv * 0.08), 2)
        pp = round(max(0.15, (k - spot) + spot * iv * 0.08), 2)
        cv = int(max(50, 4500 * np.exp(-12 * m_val * m_val)))
        pv = int(max(50, 4100 * np.exp(-12 * m_val * m_val)))
        c_rows.append({"strike": k, "lastPrice": cp, "bid": round(cp*0.98, 2), "ask": round(cp*1.02, 2), "volume": cv, "openInterest": cv*4, "impliedVolatility": iv})
        p_rows.append({"strike": k, "lastPrice": pp, "bid": round(pp*0.98, 2), "ask": round(pp*1.02, 2), "volume": pv, "openInterest": pv*4, "impliedVolatility": iv})
    return exps, pd.DataFrame(c_rows), pd.DataFrame(p_rows)

top_bar_html = "<div class='top-bar'><div class='brand-title'>CAPITAL QUANT v2</div><div class='live-badge'>Live | " + datetime.now().strftime('%b %d, %Y %H:%M:%S') + " | UK Institutional Terminal</div></div>"
st.markdown(top_bar_html, unsafe_allow_html=True)

n1, n2, n3, n4 = st.columns([1.3, 1.3, 1.6, 2.2])
if n1.button("1. Market Watch", use_container_width=True): st.session_state.page = "Market Watch"; st.rerun()
if n2.button("2. Stock Analysis", use_container_width=True): st.session_state.page = "Stock Analysis"; st.rerun()
if n3.button("3. Put & Call Options", use_container_width=True): st.session_state.page = "Options Data"; st.rerun()
st.session_state.use_live_api = n4.toggle("启用实时 Yahoo Finance 行情接口", value=st.session_state.use_live_api)
st.markdown("---")

if st.session_state.page == "Market Watch":
    c1, c2, c3, c4 = st.columns([2.0, 2.2, 1.2, 1.3])
    c1.markdown("### Market Watch")
    new_t = c2.text_input("Add", placeholder="输入代码 (如 SMCI, MRVL)", label_visibility="collapsed").strip().upper()
    if c3.button("ADD TICKER", use_container_width=True) and new_t and new_t not in st.session_state.tickers:
        st.session_state.tickers.append(new_t); st.rerun()
    if c4.button("UPDATE ALL", use_container_width=True):
        st.rerun()

    st.markdown("💡 **操作提示**：点击表格左侧勾选框或任意一行公司，即可进入 **Stock Analysis** 查看详细技术面与阶梯价位。")
    rows, gainers, losers = [], 0, 0
    for sym in st.session_state.tickers:
        d = fetch_stock_metrics(sym, live=st.session_state.use_live_api)
        chg = round(d["price"] - d["prev"], 2)
        pct = round((chg / d["prev"]) * 100, 2) if d["prev"] else 0.0
        gainers += (1 if chg > 0 else 0)
        losers += (1 if chg < 0 else 0)
        rows.append({"COMPANY CODE": sym, "TODAY PRICE": d["price"], "YESTERDAY PRICE": d["prev"], "CHANGE": chg, "% CHANGE": pct, "MA20": d["ma20"], "MA50": d["ma50"], "MA200": d["ma200"], "PE RATE": str(d['pe']) if d['pe'] else "None", "YEARLY HIGH": d["high52"], "YEARLY LOW": d["low52"], "RSI (14)": d["rsi"]})

    df_watch = pd.DataFrame(rows)
    def style_watch(val, col):
        base = "background-color: #07193d; font-size: 22px; font-weight: 700;"
        if col in ["CHANGE", "% CHANGE"]:
            color_str = "#4ade80" if val > 0 else ("#f87171" if val < 0 else "#fff")
            return base + " color: " + color_str + ";"
        if col == "RSI (14)":
            bg_col = "#dc2626" if val >= 70 else ("#eab308" if val <= 40 else "#16a34a")
            fg_col = "#000" if val <= 40 else "#fff"
            return "background-color: " + bg_col + "; color: " + fg_col + "; font-size: 22px; font-weight: 800;"
        if col == "COMPANY CODE": return base + " color: #60a5fa; font-weight: 900;"
        if col == "TODAY PRICE": return base + " color: #facc15; font-weight: 800;"
        return base + " color: #fff;"

    fmt = {"TODAY PRICE": "{:.2f}", "YESTERDAY PRICE": "{:.2f}", "CHANGE": "{:+.2f}", "% CHANGE": "{:+.2f}%", "MA20": "{:.2f}", "MA50": "{:.2f}", "MA200": "{:.2f}", "YEARLY HIGH": "{:.2f}", "YEARLY LOW": "{:.2f}", "RSI (14)": "{:.1f}"}
    styled_df = df_watch.style.apply(lambda c: [style_watch(v, c.name) for v in c], axis=0).format(fmt)
    event = st.dataframe(styled_df, use_container_width=True, height=500, row_height=48, hide_index=True, on_select="rerun", selection_mode="single-row")
    if event and event.selection and len(event.selection.rows) > 0:
        st.session_state.selected_ticker = df_watch.iloc[event.selection.rows[0]]["COMPANY CODE"]
        st.session_state.page = "Stock Analysis"; st.rerun()

    b1, b2, b3 = st.columns([2.4, 2.2, 2.4])
    if b1.button("OPEN COMPANY ANALYSIS (" + st.session_state.selected_ticker + ") >", use_container_width=True):
        st.session_state.page = "Stock Analysis"; st.rerun()
    del_sym = b2.selectbox("移除", ["选择要删除的代码..."] + st.session_state.tickers, label_visibility="collapsed")
    if del_sym != "选择要删除的代码...":
        st.session_state.tickers.remove(del_sym); st.rerun()
    summary_html = "<div style='text-align:right; padding-top:6px; font-size:21px; font-weight:800;'><span style='color:#4ade80;'>▲ " + str(gainers) + " Gainers</span> | <span style='color:#f87171;'>● " + str(losers) + " Losers</span> | Total: " + str(len(df_watch)) + "</div>"
    b3.markdown(summary_html, unsafe_allow_html=True)

elif st.session_state.page == "Stock Analysis":
    t1, t2, t3, t4 = st.columns([2.0, 2.4, 2.2, 1.2])
    t1.markdown("### Stock Analysis")
    idx = st.session_state.tickers.index(st.session_state.selected_ticker) if st.session_state.selected_ticker in st.session_state.tickers else 0
    chosen = t2.selectbox("标的", st.session_state.tickers, index=idx, label_visibility="collapsed")
    if chosen != st.session_state.selected_ticker:
        st.session_state.selected_ticker = chosen; st.rerun()
    if t3.button("PUT & CALL OPTIONS DATA >", use_container_width=True):
        st.session_state.page = "Options Data"; st.rerun()
    if t4.button("← BACK", use_container_width=True):
        st.session_state.page = "Market Watch"; st.rerun()

    sym = st.session_state.selected_ticker
    m = fetch_stock_metrics(sym, live=st.session_state.use_live_api)
    col_c, col_l = st.columns([2.5, 1.1])
    with col_c:
        card_title_html = "<div class='card-header'>" + sym + " — " + m['name'] + " | Price Chart</div>"
        st.markdown(card_title_html, unsafe_allow_html=True)
        periods = ["1日", "1星期", "3星期", "1个月", "6个月", "1年", "全部"]
        p_cols = st.columns(len(periods))
        for i, p in enumerate(periods):
            if p_cols[i].button(p, use_container_width=True, key="p_" + p):
                st.session_state.chart_period = p; st.rerun()
        hdf = fetch_history_df(sym, st.session_state.chart_period, m["price"])
        fig = go.Figure(go.Scatter(x=hdf["Date"], y=hdf["Close"], mode="lines", line=dict(color="#0284c7", width=2.5)))
        fig.add_hline(y=m["price"], line_dash="dash", line_color="#64748b", annotation_text=" " + str(m['price']) + " ", annotation_position="right", annotation_font=dict(color="#fff", size=15), annotation_bgcolor="#334155")
        fig.update_layout(template="plotly_white", paper_bgcolor="#fff", plot_bgcolor="#fff", xaxis_rangeslider_visible=False, height=455, font=dict(size=18, color="#1e293b"), margin=dict(l=10, r=70, t=10, b=10), showlegend=False)
        fig.update_yaxes(side="right", gridcolor="#e2e8f0")
        st.plotly_chart(fig, use_container_width=True)

    with col_l:
        st.markdown("<div class='card-header'>PRICE LEVEL LADDER</div>", unsafe_allow_html=True)
        rows_html = ""
        for pct in [20, 15, 12, 10, 8, 6, 0, -6, -8, -10, -12, -15, -18, -20]:
            lbl = "CURRENT" if pct == 0 else (("+" + str(pct)) if pct > 0 else str(pct)) + "%"
            tp = round(m["price"] * (1 + pct / 100.0), 2)
            bg = "#eab308" if pct == 0 else "#07193d"
            fg = "#000" if pct == 0 else ("#4ade80" if pct > 0 else "#f87171")
            fw = "900" if pct == 0 else "700"
            rows_html += "<tr style='background:" + bg + ";border-bottom:1px solid #1e3a8a;'><td style='padding:7px 10px;color:" + fg + ";font-weight:" + fw + ";font-size:14px;'>" + lbl + "</td><td style='padding:7px 10px;color:" + fg + ";font-weight:" + fw + ";font-size:14px;text-align:right;'>" + f"{tp:.2f}" + "</td></tr>"
        html_box = "<div style='background:#061430;border:1px solid #2563eb;border-radius:8px;height:520px;overflow-y:auto;padding:2px;'><table style='width:100%;border-collapse:collapse;font-family:sans-serif;'><thead><tr style='border-bottom:2px solid #1e3a8a;color:#93c5fd;font-size:14px;position:sticky;top:0;background:#061430;'><th style='padding:7px 10px;text-align:left;'>LEVEL</th><th style='padding:7px 10px;text-align:right;'>TARGET PRICE</th></tr></thead><tbody>" + rows_html + "</tbody></table></div>"
        st.components.v1.html(html_box, height=535)

    chg = round(m["price"] - m["prev"], 2)
    pct_c = round((chg / m["prev"]) * 100, 2) if m["prev"] else 0.0
    cc = "#4ade80" if chg >= 0 else "#f87171"
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    
    k1.markdown("<div class='metric-box'><div class='metric-label'>Current Price</div><div class='metric-val'>" + f"{m['price']:.2f}" + " <span style='font-size:20px;color:" + cc + ";'>(" + f"{pct_c:+.2f}" + "%)</span></div></div>", unsafe_allow_html=True)
    k2.markdown("<div class='metric-box'><div class='metric-label'>52W High</div><div class='metric-val'>" + f"{m['high52']:.2f}" + "</div></div>", unsafe_allow_html=True)
    k3.markdown("<div class='metric-box'><div class='metric-label'>52W Low</div><div class='metric-val'>" + f"{m['low52']:.2f}" + "</div></div>", unsafe_allow_html=True)
    k4.markdown("<div class='metric-box'><div class='metric-label'>Market Cap</div><div class='metric-val'>" + str(m['mcap']) + "</div></div>", unsafe_allow_html=True)
    k5.markdown("<div class='metric-box'><div class='metric-label'>P/E / EPS</div><div class='metric-val'>" + (str(m['pe']) if m['pe'] else 'N/A') + " / " + str(m['eps']) + "</div></div>", unsafe_allow_html=True)
    k6.markdown("<div class='metric-box'><div class='metric-label'>RSI (14)</div><div class='metric-val' style='color:#38bdf8;'>" + f"{m['rsi']:.1f}" + "</div></div>", unsafe_allow_html=True)

elif st.session_state.page == "Options Data":
    o1, o2, o3, o4 = st.columns([2.3, 2.1, 1.5, 1.5])
    o1.markdown("### Put & Call Option Data")
    idx = st.session_state.tickers.index(st.session_state.selected_ticker) if st.session_state.selected_ticker in st.session_state.tickers else 0
    chosen_o = o2.selectbox("期权标的", st.session_state.tickers, index=idx, label_visibility="collapsed")
    if chosen_o != st.session_state.selected_ticker:
        st.session_state.selected_ticker = chosen_o; st.rerun()
    if o3.button("← Stock Analysis", use_container_width=True): st.session_state.page = "Stock Analysis"; st.rerun()
    if o4.button("Market Watch", use_container_width=True): st.session_state.page = "Market Watch"; st.rerun()

    sym = st.session_state.selected_ticker
    spot = fetch_stock_metrics(sym, live=st.session_state.use_live_api)["price"]
    exps, cdf, pdf = fetch_options_chain(sym, spot)
    ec, ic = st.columns([1.6, 3.4])
    ec.selectbox("到期日 (Expiration)", exps, index=0)
    ic.markdown("<div style='padding-top:28px;font-size:21px;font-weight:700;color:#93c5fd;'>标的现价: <span style='color:#facc15;font-size:30px;'>$" + f"{spot:.2f}" + "</span> | 🟡 量化仿真期权链</div>", unsafe_allow_html=True)

    cdf["dist"] = (cdf["strike"] - spot).abs()
    strikes = cdf.nsmallest(15, "dist")["strike"].sort_values().tolist()
    cf, pf = cdf[cdf["strike"].isin(strikes)].set_index("strike"), pdf[pdf["strike"].isin(strikes)].set_index("strike")
    coi, poi = int(cf["openInterest"].sum()), int(pf["openInterest"].sum())
    pcr = round(poi / coi, 2) if coi > 0 else 1.0
    iv_avg = round(float(cf["impliedVolatility"].mean()) * 100, 1)
    mp_strike = min(strikes, key=lambda k: sum(max(0, k-s)*cf.loc[s,"openInterest"] + max(0, s-k)*pf.loc[s,"openInterest"] for s in strikes))

    m1, m2, m3, m4 = st.columns(4)
    m1.markdown("<div class='metric-box'><div class='metric-label'>Put / Call OI Ratio</div><div class='metric-val'>" + f"{pcr:.2f}" + "</div></div>", unsafe_allow_html=True)
    m2.markdown("<div class='metric-box'><div class='metric-label'>Avg IV</div><div class='metric-val' style='color:#38bdf8;'>" + f"{iv_avg:.1f}" + "%</div></div>", unsafe_allow_html=True)
    m3.markdown("<div class='metric-box'><div class='metric-label'>Max Pain Strike</div><div class='metric-val' style='color:#facc15;'>$" + f"{mp_strike:.2f}" + "</div></div>", unsafe_allow_html=True)
    m4.markdown("<div class='metric-box'><div class='metric-label'>Total OI (Call / Put)</div><div class='metric-val'>" + f"{coi:,}" + " / " + f"{poi:,}" + "</div></div>", unsafe_allow_html=True)

    atm = min(strikes, key=lambda x: abs(x - spot))
    s_rows = []
    for k in strikes:
        cr, pr = cf.loc[k], pf.loc[k]
        s_rows.append({"CALL OI": int(cr["openInterest"]), "CALL VOL": int(cr["volume"]), "CALL IV": f"{cr['impliedVolatility']*100:.1f}%", "CALL BID": float(cr["bid"]), "CALL ASK": float(cr["ask"]), "CALL LAST": float(cr["lastPrice"]), "STRIKE": float(k), "PUT LAST": float(pr["lastPrice"]), "PUT BID": float(pr["bid"]), "PUT ASK": float(pr["ask"]), "PUT IV": f"{pr['impliedVolatility']*100:.1f}%", "PUT VOL": int(pr["volume"]), "PUT OI": int(pr["openInterest"])})
    dfs = pd.DataFrame(s_rows)

    def style_opt(row):
        is_atm = (row["STRIKE"] == atm)
        res = []
        for col in row.index:
            if col == "STRIKE": res.append("background:#eab308;color:#000;font-size:22px;font-weight:900;" if is_atm else "background:#1e3a8a;color:#fff;font-size:22px;font-weight:800;")
            elif col.startswith("CALL"): res.append("background:" + ("#0c2b1e" if row["STRIKE"] < spot else "#07193d") + ";color:#86efac;font-size:20px;font-weight:700;")
            else: res.append("background:" + ("#2d1218" if row["STRIKE"] > spot else "#07193d") + ";color:#fca5a5;font-size:20px;font-weight:700;")
        return res

    st.markdown("<div class='card-header'>T-SHAPED STRADDLE OPTIONS CHAIN</div>", unsafe_allow_html=True)
    st.dataframe(dfs.style.apply(style_opt, axis=1).format({"CALL BID": "{:.2f}", "CALL ASK": "{:.2f}", "CALL LAST": "{:.2f}", "STRIKE": "{:.2f}", "PUT LAST": "{:.2f}", "PUT BID": "{:.2f}", "PUT ASK": "{:.2f}"}), use_container_width=True, height=500, row_height=50, hide_index=True)

    fig_oi = go.Figure([go.Bar(x=dfs["STRIKE"], y=dfs["CALL OI"], name="Call OI", marker_color="#22c55e"), go.Bar(x=dfs["STRIKE"], y=dfs["PUT OI"], name="Put OI", marker_color="#ef4444")])
    fig_oi.add_vline(x=spot, line_dash="dash", line_color="#facc15", annotation_text="Spot: " + f"{spot:.2f}")
    fig_oi.update_layout(barmode="group", template="plotly_dark", paper_bgcolor="rgba(6,20,48,0.95)", plot_bgcolor="rgba(4,14,34,0.98)", height=320, font=dict(size=18, color="#fff"), margin=dict(l=10, r=10, t=25, b=10))
    st.plotly_chart(fig_oi, use_container_width=True)
