import hashlib
import hmac
import os
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

try:
    import yfinance as yf
    HAS_YF = True
except Exception:
    yf = None
    HAS_YF = False

st.set_page_config(page_title="CAPITAL QUANT v2", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .block-container { padding: 0.3rem 0.8rem 0.8rem 0.8rem !important; max-width: 100% !important; }
    html, body, [class*="css"] { font-size: 18px !important; }
    .stApp { background: radial-gradient(circle at top center, #0a2558 0%, #040d21 65%, #020712 100%) !important; color: #fff !important; }
    header, footer, #MainMenu {visibility: hidden;}
    .top-bar { background: linear-gradient(90deg, #061533, #0c275e, #061533); border: 1px solid #2563eb; border-radius: 8px; padding: 8px 15px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
    .brand-title { font-size: 26px !important; font-weight: 800; color: #fff; }
    .live-badge { color: #4ade80; font-weight: 700; font-size: 17px !important; }
    .card-header { font-size: 19px !important; font-weight: 800; color: #93c5fd; border-bottom: 1px solid #1e3a8a; padding-bottom: 4px; margin-bottom: 6px; text-transform: uppercase; }
    .module-container { background: rgba(6, 20, 48, 0.85); border: 1px solid #2563eb; border-radius: 10px; padding: 15px; margin-bottom: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
    div.stButton > button { background: linear-gradient(180deg, #2563eb, #1d4ed8) !important; color: #fff !important; border: 1px solid #60a5fa !important; border-radius: 6px !important; font-size: 18px !important; font-weight: 700 !important; padding: 6px 12px !important; }
    .stTextInput input, div[data-baseweb="select"] > div { background-color: #07193d !important; color: #fff !important; border: 1px solid #3b82f6 !important; font-size: 18px !important; }
    div[data-testid="stDataFrame"] { border: 1px solid #2563eb !important; border-radius: 8px !important; background-color: #ffffff !important; }
    .metric-box { background: #061430; border: 1px solid #2563eb; border-radius: 8px; padding: 10px 12px; text-align: center; }
    .metric-label { font-size: 16px !important; color: #93c5fd; margin-bottom: 2px; font-weight: 700; }
    .metric-val { font-size: 26px !important; font-weight: 900; color: #fff; }
</style>
""", unsafe_allow_html=True)

def _get_secret_or_env(key: str) -> str:
    val = os.getenv(key, "")
    try:
        if key in st.secrets and str(st.secrets[key]).strip():
            val = str(st.secrets[key])
    except Exception:
        pass
    return val.strip()

def _require_owner_access() -> None:
    expected = _get_secret_or_env("APP_ACCESS_PASSWORD")
    if not expected:
        return
    if st.session_state.get("cq_authenticated") is True:
        return

    st.markdown("<div class='top-bar'><div class='brand-title'>CAPITAL QUANT v2</div><div class='live-badge'>Private Terminal Lock</div></div>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        st.markdown("<div class='module-container' style='margin-top: 40px;'>", unsafe_allow_html=True)
        st.markdown("<div class='card-header'>🔒 PRIVATE ACCESS REQUIRED</div>", unsafe_allow_html=True)
        entered = st.text_input("访问密码", type="password", placeholder="输入访问密码解锁终端")
        if st.button("解锁进入", use_container_width=True):
            if hmac.compare_digest(entered.strip(), expected):
                st.session_state["cq_authenticated"] = True
                st.rerun()
            else:
                st.error("密码不正确")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

_require_owner_access()

DEFAULT_TICKERS = ["NVDA", "GOOGL", "TSM", "AMD", "MSFT", "META", "AMZN", "AAPL", "ASML", "TSLA", "CBRS", "SPCX", "CEG", "SMCI", "MPWR", "MRVL", "NFLX", "QQQ", "VUAG.L", "EQQQ.L", "NG.L"]

FALLBACK_DATA = {
    "NG.L": {"name": "National Grid", "price": 1279.00, "prev": 1267.00, "pe": 16.1, "mcap": "85.3B"},
    "NVDA": {"name": "NVIDIA", "price": 125.53, "prev": 145.98, "pe": 13.5, "mcap": "3.03T"},
    "GOOGL": {"name": "Alphabet", "price": 265.29, "prev": 284.78, "pe": 15.1, "mcap": "3.54T"},
    "TSM": {"name": "TSMC", "price": 318.71, "prev": 352.09, "pe": 25.4, "mcap": "2.02T"},
    "AMD": {"name": "AMD", "price": 509.52, "prev": 499.04, "pe": 108.8, "mcap": "825B"},
    "MSFT": {"name": "Microsoft", "price": 484.52, "prev": 501.61, "pe": 28.5, "mcap": "4.06T"},
    "META": {"name": "Meta", "price": 560.84, "prev": 589.15, "pe": 22.0, "mcap": "1.63T"},
    "AMZN": {"name": "Amazon", "price": 246.82, "prev": 259.30, "pe": 21.7, "mcap": "2.81T"},
    "AAPL": {"name": "Apple", "price": 342.56, "prev": 342.37, "pe": 39.1, "mcap": "5.31T"},
    "ASML": {"name": "ASML", "price": 1517.98, "prev": 1424.75, "pe": 37.3, "mcap": "605B"},
    "TSLA": {"name": "Tesla", "price": 304.41, "prev": 338.22, "pe": 418.7, "mcap": "1.21T"},
    "CBRS": {"name": "Cerebras Systems", "price": 102.36, "prev": 101.00, "pe": None, "mcap": "20.7B"},
    "SPCX": {"name": "SpaceX", "price": 139.11, "prev": 137.65, "pe": 233.0, "mcap": "1.87T"},
    "CEG": {"name": "Constellation", "price": 265.50, "prev": 258.00, "pe": 32.5, "mcap": "85B"},
    "SMCI": {"name": "Super Micro", "price": 28.88, "prev": 27.50, "pe": 14.2, "mcap": "16B"},
    "MPWR": {"name": "Monolithic", "price": 1190.46, "prev": 1160.00, "pe": 78.4, "mcap": "57B"},
    "MRVL": {"name": "Marvell", "price": 141.99, "prev": 136.50, "pe": 65.2, "mcap": "122B"},
    "NFLX": {"name": "Netflix", "price": 845.20, "prev": 830.00, "pe": 45.6, "mcap": "362B"},
    "QQQ": {"name": "QQQ ETF", "price": 512.40, "prev": 506.80, "pe": None, "mcap": "ETF"},
    "VUAG.L": {"name": "Vanguard S&P", "price": 108.54, "prev": 107.66, "pe": None, "mcap": "ETF"},
    "EQQQ.L": {"name": "Invesco EQQQ", "price": 405.70, "prev": 402.15, "pe": None, "mcap": "ETF"}
}

if "page" not in st.session_state:
    st.session_state["page"] = "Market Watch"

if "tickers" not in st.session_state:
    saved_t = st.query_params.get("watchlist", "")
    if saved_t:
        st.session_state["tickers"] = [x.strip().upper() for x in saved_t.split(",") if x.strip()]
    else:
        st.session_state["tickers"] = DEFAULT_TICKERS.copy()

if "selected_ticker" not in st.session_state:
    st.session_state["selected_ticker"] = st.session_state["tickers"][0] if st.session_state["tickers"] else "NVDA"

if "use_live_api" not in st.session_state:
    st.session_state["use_live_api"] = True

if "chart_period" not in st.session_state:
    st.session_state["chart_period"] = "6个月"

if "show_walls" not in st.session_state:
    st.session_state["show_walls"] = True

if "show_all_strikes" not in st.session_state:
    st.session_state["show_all_strikes"] = False

if "opt_persistent_cache" not in st.session_state:
    st.session_state["opt_persistent_cache"] = {}

if "stock_natal_registry" not in st.session_state:
    st.session_state["stock_natal_registry"] = {}

def sync_watchlist_to_url():
    st.query_params["watchlist"] = ",".join(st.session_state.tickers)

def select_ticker_with_natal_first(symbol: str, target_page: str | None = None) -> dict[str, Any]:
    """每支个股被选进来的第一步：先找/定它的命盘，再进入后续行情与走势计算"""
    clean_sym = symbol.upper().strip() or "NVDA"
    if clean_sym not in st.session_state.tickers:
        st.session_state.tickers.append(clean_sym)
        sync_watchlist_to_url()
    st.session_state.selected_ticker = clean_sym
    natal_profile = resolve_stock_natal_chart(clean_sym)
    if target_page:
        st.session_state.page = target_page
    return natal_profile

def safe_col_sum(df, col_name):
    if df is None or df.empty or col_name not in df.columns:
        return 0
    return int(pd.to_numeric(df[col_name], errors="coerce").fillna(0).sum())

def _is_valid_chain_pair(cdf: pd.DataFrame, pdf: pd.DataFrame) -> bool:
    if cdf is None or pdf is None or cdf.empty or pdf.empty:
        return False
    if "strike" not in cdf.columns or "strike" not in pdf.columns:
        return False
    c_strikes = pd.to_numeric(cdf["strike"], errors="coerce").dropna()
    p_strikes = pd.to_numeric(pdf["strike"], errors="coerce").dropna()
    return (not c_strikes.empty) and (not p_strikes.empty) and ((c_strikes > 0).any()) and ((p_strikes > 0).any())

def _parse_float_clean(val):
    if val is None:
        return None
    s = str(val).replace("$", "").replace(",", "").replace("%", "").replace("+", "").strip()
    if s in ("", "--", "N/A", "None", "null"):
        return None
    try:
        return float(s)
    except Exception:
        return None

# ==================== 1. STOCK & ANALYSIS ENGINE (LOCKED TO NASDAQ) ====================

def _build_nasdaq_headers() -> dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.nasdaq.com",
        "Referer": "https://www.nasdaq.com/",
    }

def _query_nasdaq_stock_quote(symbol: str) -> dict[str, Any] | None:
    if "." in symbol:
        return None
    clean_sym = symbol.upper().strip()
    headers = _build_nasdaq_headers()
    asset_classes = ["etf", "stocks"] if clean_sym in ["QQQ", "SPY", "IWM", "DIA", "TLT"] else ["stocks", "etf"]

    for ac in asset_classes:
        try:
            url_info = f"https://api.nasdaq.com/api/quote/{clean_sym}/info?assetclass={ac}"
            res = requests.get(url_info, headers=headers, timeout=3.5)
            if res.status_code != 200:
                continue
            d = res.json().get("data")
            if not isinstance(d, dict) or not d.get("primaryData"):
                continue

            pdata = d.get("primaryData", {})
            key_stats = d.get("keyStats", {}) if isinstance(d.get("keyStats"), dict) else {}
            last_price = _parse_float_clean(pdata.get("lastSalePrice"))
            net_chg = _parse_float_clean(pdata.get("netChange"))
            if last_price is None or last_price <= 0:
                continue

            prev_price = round(last_price - net_chg, 4) if net_chg is not None else last_price
            high52, low52, mcap = None, None, None

            hl_obj = key_stats.get("fiftyTwoWeekHighLow", {})
            if isinstance(hl_obj, dict) and hl_obj.get("value"):
                parts = str(hl_obj["value"]).split("/")
                if len(parts) == 2:
                    high52 = _parse_float_clean(parts[0])
                    low52 = _parse_float_clean(parts[1])

            mcap_obj = key_stats.get("MarketCap", {})
            if isinstance(mcap_obj, dict) and mcap_obj.get("value"):
                mcap = str(mcap_obj["value"]).strip()

            return {
                "assetclass": ac,
                "name": d.get("companyName") or clean_sym,
                "price": float(last_price),
                "prev": float(prev_price),
                "high52": high52,
                "low52": low52,
                "mcap": mcap,
            }
        except Exception:
            continue
    return None

def _query_nasdaq_stock_candles(symbol: str, days_back: int = 365) -> pd.DataFrame:
    if "." in symbol:
        return pd.DataFrame()
    clean_sym = symbol.upper().strip()
    to_dt = datetime.today().strftime("%Y-%m-%d")
    from_dt = (datetime.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    headers = _build_nasdaq_headers()
    ac_order = ["etf", "stocks"] if clean_sym in ["QQQ", "SPY", "IWM", "DIA", "TLT"] else ["stocks", "etf"]

    for ac in ac_order:
        try:
            url_hist = (
                f"https://api.nasdaq.com/api/quote/{clean_sym}/historical"
                f"?assetclass={ac}&fromdate={from_dt}&limit=1500&todate={to_dt}"
            )
            h_res = requests.get(url_hist, headers=headers, timeout=4.0)
            if h_res.status_code != 200:
                continue
            rows = h_res.json().get("data", {}).get("tradesTable", {}).get("rows", [])
            if not isinstance(rows, list) or not rows:
                continue
            records = []
            for row in reversed(rows):
                c_val = _parse_float_clean(row.get("close"))
                h_val = _parse_float_clean(row.get("high"))
                l_val = _parse_float_clean(row.get("low"))
                d_str = str(row.get("date", "")).strip()
                if c_val is not None and d_str:
                    try:
                        dt_parsed = datetime.strptime(d_str, "%m/%d/%Y")
                        records.append({
                            "Date": dt_parsed,
                            "Close": float(c_val),
                            "High": float(h_val) if h_val is not None else float(c_val),
                            "Low": float(l_val) if l_val is not None else float(c_val),
                        })
                    except Exception:
                        continue
            if records:
                return pd.DataFrame(records).sort_values("Date").reset_index(drop=True)
        except Exception:
            continue
    return pd.DataFrame()

def _query_yahoo_stock_fallback(symbol: str) -> dict[str, Any] | None:
    if not HAS_YF:
        return None
    try:
        tk = yf.Ticker(symbol)
        hist = tk.history(period="1y", interval="1d")
        if hist is None or hist.empty or "Close" not in hist.columns:
            return None
        closes = [float(x) for x in hist["Close"].dropna().tolist()]
        if len(closes) < 2:
            return None
        return {
            "price": closes[-1],
            "prev": closes[-2],
            "closes": closes,
            "high52": float(hist["High"].max()) if "High" in hist.columns else max(closes),
            "low52": float(hist["Low"].min()) if "Low" in hist.columns else min(closes),
        }
    except Exception:
        return None

def _calc_indicators_from_closes(closes, last_price, prev_price, high52=None, low52=None):
    ma20 = sum(closes[-20:]) / min(20, len(closes))
    ma50 = sum(closes[-50:]) / min(50, len(closes))
    ma200 = sum(closes[-200:]) / min(200, len(closes))
    recent_slice = closes[-20:] if len(closes) >= 20 else closes
    recent_high = max(recent_slice) if recent_slice else float(last_price)
    recent_low = min(recent_slice) if recent_slice else float(last_price)
    h52 = high52 if high52 is not None else max(closes)
    l52 = low52 if low52 is not None else min(closes)

    rsi = 50.0
    if len(closes) > 15:
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [d for d in deltas[-14:] if d > 0]
        losses = [-d for d in deltas[-14:] if d < 0]
        avg_gain = sum(gains) / 14 if gains else 0.0
        avg_loss = sum(losses) / 14 if losses else 0.0
        if avg_loss > 0:
            rsi = 100 - (100 / (1 + (avg_gain / avg_loss)))
        elif avg_gain > 0:
            rsi = 100.0

    return {
        "price": round(float(last_price), 2),
        "prev": round(float(prev_price), 2),
        "ma20": round(float(ma20), 2),
        "ma50": round(float(ma50), 2),
        "ma200": round(float(ma200), 2),
        "recent_high": round(float(recent_high), 2),
        "recent_low": round(float(recent_low), 2),
        "high52": round(float(h52), 2),
        "low52": round(float(l52), 2),
        "rsi": round(float(rsi), 1),
    }

@st.cache_data(ttl=180, show_spinner=False)
def fetch_stock_metrics(symbol, live=True):
    fb = FALLBACK_DATA.get(symbol, {"name": symbol, "price": 150.0, "prev": 148.0, "pe": 25.0, "mcap": "100B"})
    if not live:
        return {
            "name": fb["name"], "price": fb["price"], "prev": fb["prev"],
            "ma20": fb["price"] * 0.98, "ma50": fb["price"] * 0.95, "ma200": fb["price"] * 0.88,
            "recent_high": fb["price"] * 1.08, "recent_low": fb["price"] * 0.92,
            "high52": fb["price"] * 1.15, "low52": fb["price"] * 0.80, "rsi": 55.0,
            "pe": fb.get("pe"), "eps": 5.0, "mcap": fb.get("mcap", "100B"), "src": "OFFLINE",
        }

    nq_quote = _query_nasdaq_stock_quote(symbol)
    if nq_quote:
        nq_candles = _query_nasdaq_stock_candles(symbol, days_back=365)
        if not nq_candles.empty:
            closes = list(nq_candles["Close"])
            if round(closes[-1], 2) != round(nq_quote["price"], 2):
                closes.append(nq_quote["price"])
            h52 = nq_quote.get("high52") or float(nq_candles["High"].max())
            l52 = nq_quote.get("low52") or float(nq_candles["Low"].min())
        else:
            yf_hist_fb = _query_yahoo_stock_fallback(symbol)
            closes = list(yf_hist_fb["closes"]) if yf_hist_fb else [nq_quote["prev"], nq_quote["price"]]
            if round(closes[-1], 2) != round(nq_quote["price"], 2):
                closes.append(nq_quote["price"])
            h52 = nq_quote.get("high52") or (yf_hist_fb.get("high52") if yf_hist_fb else max(closes))
            l52 = nq_quote.get("low52") or (yf_hist_fb.get("low52") if yf_hist_fb else min(closes))

        calc = _calc_indicators_from_closes(closes, nq_quote["price"], nq_quote["prev"], h52, l52)
        calc.update({
            "name": nq_quote.get("name") or fb.get("name", symbol),
            "pe": fb.get("pe", 25.0),
            "eps": 5.0,
            "mcap": nq_quote.get("mcap") or fb.get("mcap", "100B"),
            "src": "NQ",
        })
        return calc

    yf_res = _query_yahoo_stock_fallback(symbol)
    if yf_res:
        calc = _calc_indicators_from_closes(
            yf_res["closes"], yf_res["price"], yf_res["prev"],
            yf_res.get("high52"), yf_res.get("low52")
        )
        calc.update({
            "name": fb.get("name", symbol),
            "pe": fb.get("pe", 25.0),
            "eps": 5.0,
            "mcap": fb.get("mcap", "100B"),
            "src": "YH",
        })
        return calc

    p = fb["price"]
    prev = fb["prev"]
    return {
        "name": fb["name"], "price": p, "prev": prev,
        "ma20": p * 0.98, "ma50": p * 0.95, "ma200": p * 0.88,
        "recent_high": p * 1.08, "recent_low": p * 0.92,
        "high52": p * 1.15, "low52": p * 0.80, "rsi": 55.0,
        "pe": fb.get("pe"), "eps": 5.0, "mcap": fb.get("mcap", "100B"), "src": "FB",
    }

@st.cache_data(ttl=180, show_spinner=False)
def fetch_history_df(symbol, period_str, current_price):
    pmap = {"1日": "1d", "1星期": "5d", "1个月": "1mo", "3个月": "3mo", "6个月": "6mo", "1年": "1y", "全部": "max"}
    yfp = pmap.get(period_str, "6mo")
    days_back = {"1d": 5, "5d": 10, "1mo": 32, "3mo": 95, "6mo": 185, "1y": 365, "max": 1825}.get(yfp, 185)

    if yfp != "1d" and "." not in symbol:
        nq_df = _query_nasdaq_stock_candles(symbol, days_back=days_back)
        if not nq_df.empty:
            df_out = nq_df[["Date", "Close"]].copy()
            if current_price and current_price > 0 and round(float(df_out["Close"].iloc[-1]), 2) != round(float(current_price), 2):
                df_out = pd.concat(
                    [df_out, pd.DataFrame({"Date": [datetime.today()], "Close": [float(current_price)]})],
                    ignore_index=True
                )
            return df_out

    if HAS_YF:
        try:
            tk = yf.Ticker(symbol)
            interval_str = "5m" if yfp == "1d" else "1d"
            hist = tk.history(period=yfp, interval=interval_str)
            if hist is not None and not hist.empty and "Close" in hist.columns:
                df_h = hist[["Close"]].dropna().reset_index()
                dt_col = df_h.columns[0]
                df_h = df_h.rename(columns={dt_col: "Date"})
                df_h["Date"] = pd.to_datetime(df_h["Date"]).dt.tz_localize(None)
                return df_h[["Date", "Close"]]
        except Exception:
            pass

    ndays = {"1d": 2, "5d": 7, "1mo": 21, "3mo": 63, "6mo": 120}.get(yfp, 250)
    np.random.seed(abs(hash(symbol + period_str)) % 10000)
    dates = pd.date_range(end=datetime.today(), periods=ndays, freq="B")
    prices = current_price * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, size=len(dates))))
    return pd.DataFrame({"Date": dates, "Close": prices * (current_price / prices[-1])})

@st.cache_data(ttl=300, show_spinner=False)
def fetch_cycle_anchor_prices(symbol: str, fallback_spot: float) -> dict[str, Any]:
    """
    自动从历史日线提取两个实盘固定坐标：
    1) 11月中旬（11月10日~20日）的收盘基准锚点价（不再随当日现价浮动）
    2) 上周（周一~周五）的真实最低价与最高价，用于校准12月中旬低位
    """
    now_dt = datetime.today()
    df_hist = pd.DataFrame()

    if "." not in symbol:
        df_hist = _query_nasdaq_stock_candles(symbol, days_back=60)

    if (df_hist is None or df_hist.empty) and HAS_YF:
        try:
            tk = yf.Ticker(symbol)
            yh = tk.history(period="3mo", interval="1d")
            if yh is not None and not yh.empty and "Close" in yh.columns:
                tmp = yh.reset_index()
                dt_col = tmp.columns[0]
                df_hist = pd.DataFrame({
                    "Date": pd.to_datetime(tmp[dt_col]).dt.tz_localize(None),
                    "Close": pd.to_numeric(tmp["Close"], errors="coerce"),
                    "High": pd.to_numeric(tmp.get("High", tmp["Close"]), errors="coerce"),
                    "Low": pd.to_numeric(tmp.get("Low", tmp["Close"]), errors="coerce"),
                }).dropna(subset=["Date", "Close"])
        except Exception:
            pass

    cur_monday = (now_dt - timedelta(days=now_dt.weekday())).date()
    last_monday = cur_monday - timedelta(days=7)
    last_sunday = cur_monday - timedelta(days=1)

    mid_nov_anchor = float(fallback_spot)
    mid_nov_label = "现价兜底"
    last_week_low = round(float(fallback_spot) * 0.94, 2) if fallback_spot > 0 else 0.0
    last_week_high = round(float(fallback_spot) * 1.03, 2) if fallback_spot > 0 else 0.0
    last_week_date_str = ""

    if df_hist is not None and not df_hist.empty:
        df_hist = df_hist.sort_values("Date").reset_index(drop=True)
        df_hist["d_only"] = pd.to_datetime(df_hist["Date"]).dt.date

        # 1. 提取当年11月中旬（11月10日 ~ 11月20日）真实收盘均值作为固定基准锚点
        nov_mid_df = df_hist[
            (pd.to_datetime(df_hist["Date"]).dt.year == now_dt.year)
            & (pd.to_datetime(df_hist["Date"]).dt.month == 11)
            & (pd.to_datetime(df_hist["Date"]).dt.day >= 10)
            & (pd.to_datetime(df_hist["Date"]).dt.day <= 20)
        ]
        if nov_mid_df.empty:
            nov_mid_df = df_hist[
                (pd.to_datetime(df_hist["Date"]).dt.year == now_dt.year)
                & (pd.to_datetime(df_hist["Date"]).dt.month == 11)
            ]
        if not nov_mid_df.empty:
            mid_nov_anchor = round(float(nov_mid_df["Close"].mean()), 2)
            d_min = nov_mid_df["d_only"].min().strftime("%m/%d")
            d_max = nov_mid_df["d_only"].max().strftime("%m/%d")
            mid_nov_label = f"11月中实盘({d_min}-{d_max})"

        # 2. 提取上周真实最低价
        lw_df = df_hist[(df_hist["d_only"] >= last_monday) & (df_hist["d_only"] <= last_sunday)]
        if lw_df.empty and len(df_hist) >= 6:
            lw_df = df_hist.iloc[-6:-1]
        if not lw_df.empty:
            low_col = "Low" if "Low" in lw_df.columns and lw_df["Low"].notna().any() else "Close"
            high_col = "High" if "High" in lw_df.columns and lw_df["High"].notna().any() else "Close"
            min_idx = lw_df[low_col].idxmin()
            last_week_low = round(float(lw_df.loc[min_idx, low_col]), 2)
            last_week_high = round(float(lw_df[high_col].max()), 2)
            last_week_date_str = lw_df.loc[min_idx, "d_only"].strftime("%m/%d")

    return {
        "mid_nov_anchor": mid_nov_anchor,
        "mid_nov_label": mid_nov_label,
        "last_week_low": last_week_low,
        "last_week_high": last_week_high,
        "last_week_date_str": last_week_date_str,
    }

# ==================== 2. OPTIONS ENGINE (CBOE + NASDAQ + YAHOO REAL AGGREGATOR) ====================

def _parse_occ_option_symbol(occ_sym: str) -> tuple[str | None, str | None, float | None]:
    """解析标准 OCC 期权代码，例如 NVDA261127C00170000 -> ('2026-11-27', 'C', 170.0)"""
    s = str(occ_sym or "").strip().upper()
    if len(s) < 15:
        return None, None, None
    tail = s[-15:]
    date_part = tail[:6]
    cp_flag = tail[6]
    strike_part = tail[7:]
    if cp_flag not in ("C", "P") or not date_part.isdigit() or not strike_part.isdigit():
        return None, None, None
    try:
        exp_str = f"20{date_part[:2]}-{date_part[2:4]}-{date_part[4:6]}"
        datetime.strptime(exp_str, "%Y-%m-%d")
        strike_val = int(strike_part) / 1000.0
        return exp_str, cp_flag, strike_val
    except Exception:
        return None, None, None

@st.cache_data(ttl=120, show_spinner=False)
def _query_cboe_realtime_bundle(symbol: str) -> tuple[list[str], dict[str, tuple[pd.DataFrame, pd.DataFrame]], str]:
    """直连 CBOE 公开延迟期权链 JSON 接口（含真实 OI + 盘中 Volume + Gamma）"""
    if "." in symbol:
        return [], {}, "非美股无 CBOE 链"
    clean_sym = symbol.upper().strip()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.cboe.com/",
    }
    urls = [
        f"https://cdn.cboe.com/api/global/delayed_quotes/options/{clean_sym}.json",
        f"https://cdn.cboe.com/api/global/delayed_quotes/options/_{clean_sym}.json",
    ]
    for u in urls:
        try:
            res = requests.get(u, headers=headers, timeout=4.5)
            if res.status_code != 200:
                continue
            payload = res.json()
            opts = payload.get("data", {}).get("options", [])
            if not isinstance(opts, list) or not opts:
                continue

            grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
            for item in opts:
                occ = item.get("option", "")
                exp_str, cp_flag, strike_val = _parse_occ_option_symbol(occ)
                if not exp_str or not cp_flag or not strike_val or strike_val <= 0:
                    continue
                oi = int(_parse_float_clean(item.get("open_interest")) or 0)
                vol = int(_parse_float_clean(item.get("volume")) or 0)
                last_px = float(_parse_float_clean(item.get("last_trade_price")) or _parse_float_clean(item.get("ask")) or 0.0)
                gamma = float(_parse_float_clean(item.get("gamma")) or 0.0)
                delta = float(_parse_float_clean(item.get("delta")) or 0.0)
                rec = {
                    "strike": float(strike_val),
                    "lastPrice": last_px,
                    "openInterest": oi,
                    "volume": vol,
                    "gamma": gamma,
                    "delta": delta,
                }
                grouped.setdefault(exp_str, {"C": [], "P": []})[cp_flag].append(rec)

            today_date = datetime.today().date()
            valid_exps = sorted([
                d for d in grouped.keys()
                if datetime.strptime(d, "%Y-%m-%d").date() >= today_date
            ])[:12]

            day_map: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}
            for d_str in valid_exps:
                cdf = pd.DataFrame(grouped[d_str]["C"])
                pdf = pd.DataFrame(grouped[d_str]["P"])
                if _is_valid_chain_pair(cdf, pdf):
                    day_map[d_str] = (cdf, pdf)

            if day_map:
                return sorted(day_map.keys()), day_map, f"CBOE 实时链 ({len(day_map)}期)"
        except Exception:
            continue
    return [], {}, "CBOE 未返回"

@st.cache_data(ttl=120, show_spinner=False)
def _query_nasdaq_option_bundle(symbol: str) -> tuple[list[str], dict[str, tuple[pd.DataFrame, pd.DataFrame]], str]:
    """Nasdaq 官方期权链接口备份与交叉补充"""
    if "." in symbol:
        return [], {}, "非美股无 Nasdaq 链"
    clean_sym = symbol.upper().strip()
    headers = _build_nasdaq_headers()
    ac_list = ["etf", "stocks"] if clean_sym in ["QQQ", "SPY", "IWM", "DIA", "TLT"] else ["stocks", "etf"]

    for ac in ac_list:
        try:
            url = f"https://api.nasdaq.com/api/quote/{clean_sym}/option-chain?assetclass={ac}&limit=1000&money=all"
            res = requests.get(url, headers=headers, timeout=4.5)
            if res.status_code != 200:
                continue
            rows = res.json().get("data", {}).get("table", {}).get("rows", [])
            if not isinstance(rows, list) or not rows:
                continue

            grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
            cur_exp = None
            for r in rows:
                if r.get("expirygroup"):
                    try:
                        dt_g = datetime.strptime(str(r["expirygroup"]).strip(), "%B %d, %Y")
                        cur_exp = dt_g.strftime("%Y-%m-%d")
                    except Exception:
                        pass
                drill = str(r.get("drillDownURL", ""))
                exp_from_url = None
                if "/" in drill:
                    parts = [p for p in drill.split("/") if p]
                    if parts:
                        exp_c, _, _ = _parse_occ_option_symbol(parts[-1])
                        exp_from_url = exp_c
                exp_str = exp_from_url or cur_exp
                strike_val = _parse_float_clean(r.get("strike"))
                if not exp_str or not strike_val or strike_val <= 0:
                    continue

                c_oi = int(_parse_float_clean(r.get("c_Openinterest")) or 0)
                c_vol = int(_parse_float_clean(r.get("c_Volume")) or 0)
                c_last = float(_parse_float_clean(r.get("c_Last")) or 0.0)
                p_oi = int(_parse_float_clean(r.get("p_Openinterest")) or 0)
                p_vol = int(_parse_float_clean(r.get("p_Volume")) or 0)
                p_last = float(_parse_float_clean(r.get("p_Last")) or 0.0)

                grouped.setdefault(exp_str, {"C": [], "P": []})
                grouped[exp_str]["C"].append({"strike": strike_val, "lastPrice": c_last, "openInterest": c_oi, "volume": c_vol, "gamma": 0.0})
                grouped[exp_str]["P"].append({"strike": strike_val, "lastPrice": p_last, "openInterest": p_oi, "volume": p_vol, "gamma": 0.0})

            today_date = datetime.today().date()
            valid_exps = sorted([
                d for d in grouped.keys()
                if datetime.strptime(d, "%Y-%m-%d").date() >= today_date
            ])[:12]
            day_map: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}
            for d_str in valid_exps:
                cdf = pd.DataFrame(grouped[d_str]["C"])
                pdf = pd.DataFrame(grouped[d_str]["P"])
                if _is_valid_chain_pair(cdf, pdf):
                    day_map[d_str] = (cdf, pdf)
            if day_map:
                return sorted(day_map.keys()), day_map, f"Nasdaq 链 ({len(day_map)}期)"
        except Exception:
            continue
    return [], {}, "Nasdaq 未返回"

def _normalize_yf_option_side(df_raw: pd.DataFrame) -> pd.DataFrame:
    if df_raw is None or df_raw.empty or "strike" not in df_raw.columns:
        return pd.DataFrame()
    out = pd.DataFrame()
    out["strike"] = pd.to_numeric(df_raw["strike"], errors="coerce")
    out["lastPrice"] = pd.to_numeric(df_raw.get("lastPrice", 0.0), errors="coerce").fillna(0.0)
    out["openInterest"] = pd.to_numeric(df_raw.get("openInterest", 0), errors="coerce").fillna(0).astype(int)
    out["volume"] = pd.to_numeric(df_raw.get("volume", 0), errors="coerce").fillna(0).astype(int)
    out["gamma"] = 0.0
    out = out.dropna(subset=["strike"])
    return out[out["strike"] > 0].reset_index(drop=True)

@st.cache_data(ttl=180, show_spinner=False)
def _query_yahoo_yfinance_bundle(symbol: str) -> tuple[list[str], dict[str, tuple[pd.DataFrame, pd.DataFrame]], str]:
    if "." in symbol:
        return [], {}, "非美股代码无美式期权链"
    if not HAS_YF:
        return [], {}, "未安装 yfinance"

    clean_sym = symbol.upper().strip()
    try:
        tk = yf.Ticker(clean_sym)
        raw_exps = list(tk.options or [])
        if not raw_exps:
            return [], {}, "Yahoo 未返回到期日"

        today_date = datetime.today().date()
        future_exps = [d for d in sorted(set(raw_exps)) if datetime.strptime(d, "%Y-%m-%d").date() >= today_date]
        target_exps = (future_exps if future_exps else sorted(set(raw_exps)))[:10]

        day_map: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}
        for d_str in target_exps:
            try:
                chain = tk.option_chain(d_str)
                cdf = _normalize_yf_option_side(chain.calls)
                pdf = _normalize_yf_option_side(chain.puts)
                if _is_valid_chain_pair(cdf, pdf):
                    day_map[d_str] = (cdf, pdf)
            except Exception:
                continue

        if day_map:
            return sorted(set(target_exps) | set(day_map.keys())), day_map, f"Yahoo 链 ({len(day_map)}期)"
        return target_exps, {}, "Yahoo 链为空"
    except Exception as e:
        return [], {}, f"Yahoo 异常: {str(e)[:35]}"

def _collect_multi_source_options(symbol: str) -> tuple[list[str], dict[str, dict[str, Any]], int, str, str]:
    """三路真实期权源聚合：CBOE 实时链 -> Nasdaq 链 -> Yahoo 链 + 本地缓存兜底"""
    cboe_days, cboe_map, cboe_msg = _query_cboe_realtime_bundle(symbol)
    nq_days, nq_map, nq_msg = ([], {}, "") if len(cboe_map) >= 6 else _query_nasdaq_option_bundle(symbol)
    yh_days, yh_map, yh_msg = ([], {}, "") if (len(cboe_map) + len(nq_map)) >= 6 else _query_yahoo_yfinance_bundle(symbol)

    cache_store: dict[str, dict[str, Any]] = st.session_state["opt_persistent_cache"]
    prev_entry = cache_store.get(symbol, {})
    prev_by_day: dict[str, dict[str, Any]] = prev_entry.get("by_day", {})
    prev_days: list[str] = prev_entry.get("days", [])

    merged_by_day: dict[str, dict[str, Any]] = {}
    for d_key, rec in prev_by_day.items():
        if _is_valid_chain_pair(rec.get("cdf"), rec.get("pdf")):
            merged_by_day[d_key] = {"cdf": rec["cdf"].copy(), "pdf": rec["pdf"].copy(), "source": "CACHE"}

    for src_tag, src_map in [("YH", yh_map), ("NQ", nq_map), ("CBOE", cboe_map)]:
        for d_key, (cdf, pdf) in src_map.items():
            if _is_valid_chain_pair(cdf, pdf):
                merged_by_day[d_key] = {"cdf": cdf.copy(), "pdf": pdf.copy(), "source": src_tag}

    merged_days = sorted(set(cboe_days) | set(nq_days) | set(yh_days) | set(prev_days) | set(merged_by_day.keys()))
    now_str = datetime.now().strftime("%H:%M:%S")
    live_hits = len(cboe_map) + len(nq_map) + len(yh_map)
    cache_time_label = now_str if live_hits > 0 else prev_entry.get("updated_at", "")

    if cboe_map:
        status_msg = cboe_msg
    elif nq_map:
        status_msg = nq_msg
    elif yh_map:
        status_msg = yh_msg
    else:
        status_msg = f"缓存兜底 ({cboe_msg}/{yh_msg})"

    if merged_days or merged_by_day:
        cache_store[symbol] = {
            "days": merged_days,
            "by_day": merged_by_day,
            "updated_at": cache_time_label or now_str,
        }

    return merged_days, merged_by_day, len(merged_by_day), status_msg, cache_time_label

def fetch_real_option_chain_for_date(symbol, target_dt_timestamp=None, spot=None):
    all_days, combined_by_day, _, _, _ = _collect_multi_source_options(symbol)
    exp_ts_list: list[int] = []
    for d_str in all_days:
        try:
            dt_obj = datetime.strptime(d_str, "%Y-%m-%d").replace(hour=16, minute=0, second=0)
            exp_ts_list.append(int(dt_obj.timestamp()))
        except Exception:
            continue

    if not combined_by_day:
        return exp_ts_list, pd.DataFrame(), pd.DataFrame()

    if target_dt_timestamp:
        req_day = datetime.fromtimestamp(int(target_dt_timestamp)).strftime("%Y-%m-%d")
        rec = combined_by_day.get(req_day)
        if rec and _is_valid_chain_pair(rec["cdf"], rec["pdf"]):
            return exp_ts_list, rec["cdf"], rec["pdf"]
        return exp_ts_list, pd.DataFrame(), pd.DataFrame()

    first_valid_day = next((d for d in all_days if d in combined_by_day), None)
    if first_valid_day:
        rec = combined_by_day[first_valid_day]
        return exp_ts_list, rec["cdf"], rec["pdf"]

    return exp_ts_list, pd.DataFrame(), pd.DataFrame()

def _build_company_real_day_keys(real_day_keys: list[str], base_dt: datetime, max_cols: int = 10) -> list[str]:
    today_date = base_dt.date()
    unique_sorted = sorted({d for d in (real_day_keys or []) if d})
    active_or_future = [
        d for d in unique_sorted
        if datetime.strptime(d, "%Y-%m-%d").date() >= today_date
    ]
    chosen = active_or_future if active_or_future else unique_sorted
    return chosen[:max_cols]

def _score_wall_strength(df: pd.DataFrame, delta_days: int = 3) -> pd.DataFrame:
    """真实墙强度评分 = 隔夜未平仓 OI + 盘中实时成交量 Volume 权重"""
    out = df.copy()
    oi_s = pd.to_numeric(out.get("openInterest", 0), errors="coerce").fillna(0.0)
    vol_s = pd.to_numeric(out.get("volume", 0), errors="coerce").fillna(0.0)
    vol_weight = 1.6 if delta_days <= 7 else 0.9
    out["wall_power"] = oi_s + vol_s * vol_weight
    return out

def extract_top3_walls(col_cdf, col_pdf, curr_p, delta_days: int = 3):
    if not _is_valid_chain_pair(col_cdf, col_pdf):
        return [], None, [], None

    cdf_scored = _score_wall_strength(col_cdf, delta_days=delta_days)
    pdf_scored = _score_wall_strength(col_pdf, delta_days=delta_days)

    cdf_clean = cdf_scored.sort_values("wall_power", ascending=False).drop_duplicates(subset=["strike"])
    pdf_clean = pdf_scored.sort_values("wall_power", ascending=False).drop_duplicates(subset=["strike"])

    # 上方 Call Wall：保持贴近现价的主力博弈区（近端 -4% ~ +12%，远端 -2% ~ +18%）
    if delta_days <= 7:
        c_min_bound, c_max_bound = curr_p * 0.96, curr_p * 1.12
    else:
        c_min_bound, c_max_bound = curr_p * 0.98, curr_p * 1.18

    above_df = cdf_clean[(cdf_clean["strike"] >= c_min_bound) & (cdf_clean["strike"] <= c_max_bound)].copy()
    if len(above_df) < 3:
        above_df = cdf_clean[(cdf_clean["strike"] >= curr_p * 0.94) & (cdf_clean["strike"] <= curr_p * 1.25)].copy()
    if above_df.empty:
        above_df = cdf_clean.copy()

    top3_calls = (
        above_df.sort_values(by="wall_power", ascending=False)
        .head(3)
        .sort_values(by="strike", ascending=False)
    )
    c_top_list = [(float(r["strike"]), int(r["wall_power"])) for _, r in top3_calls.iterrows()]
    call_wall_val = max(c_top_list, key=lambda x: x[1])[0] if c_top_list else None

    # 下方 Put Wall：严格在现价下方，恢复到机构真实防守区（近端 -22% ~ -3%，远端 -28% ~ -5%）
    if delta_days <= 7:
        p_min_bound, p_max_bound = curr_p * 0.78, curr_p * 0.97
    else:
        p_min_bound, p_max_bound = curr_p * 0.72, curr_p * 0.95

    below_df = pdf_clean[(pdf_clean["strike"] >= p_min_bound) & (pdf_clean["strike"] <= p_max_bound)].copy()
    if len(below_df) < 3:
        below_df = pdf_clean[(pdf_clean["strike"] >= curr_p * 0.68) & (pdf_clean["strike"] < curr_p)].copy()
    if below_df.empty:
        below_df = pdf_clean[pdf_clean["strike"] < curr_p].copy()
    if below_df.empty:
        below_df = pdf_clean.copy()

    top3_puts = (
        below_df.sort_values(by="wall_power", ascending=False)
        .head(3)
        .sort_values(by="strike", ascending=True)
    )
    p_bot_list = [(float(r["strike"]), int(r["wall_power"])) for _, r in top3_puts.iterrows()]
    put_wall_val = max(p_bot_list, key=lambda x: x[1])[0] if p_bot_list else None

    return c_top_list, call_wall_val, p_bot_list, put_wall_val

def compute_aggregate_real_walls(combined_by_day: dict[str, dict[str, Any]], spot: float) -> dict[str, Any]:
    """全期限合并计算真实累计 Call Wall 与 Put Wall"""
    c_frames, p_frames = [], []
    for _, rec in combined_by_day.items():
        cdf, pdf = rec.get("cdf"), rec.get("pdf")
        if _is_valid_chain_pair(cdf, pdf):
            c_frames.append(cdf[["strike", "openInterest", "volume"]].copy())
            p_frames.append(pdf[["strike", "openInterest", "volume"]].copy())
    if not c_frames or not p_frames or spot <= 0:
        return {"call_walls": [], "put_walls": []}

    c_all = pd.concat(c_frames, ignore_index=True).groupby("strike", as_index=False).sum()
    p_all = pd.concat(p_frames, ignore_index=True).groupby("strike", as_index=False).sum()
    c_all["power"] = c_all["openInterest"] + c_all["volume"] * 1.3
    p_all["power"] = p_all["openInterest"] + p_all["volume"] * 1.3

    c_band = c_all[(c_all["strike"] >= spot * 0.94) & (c_all["strike"] <= spot * 1.15)].sort_values("power", ascending=False).head(3)
    p_band = p_all[(p_all["strike"] >= spot * 0.75) & (p_all["strike"] <= spot * 0.97)].sort_values("power", ascending=False).head(3)

    c_list = [(float(r["strike"]), int(r["power"]), float(r["strike"]) < spot) for _, r in c_band.iterrows()]
    p_list = [(float(r["strike"]), int(r["power"]), float(r["strike"]) > spot) for _, r in p_band.iterrows()]
    return {"call_walls": c_list, "put_walls": p_list}

def pull_and_filter_real_expirations_locally(symbol: str, spot: float) -> tuple[list[dict[str, Any]], bool, int, str, str, dict[str, Any]]:
    today = datetime.today()
    all_days, combined_by_day, live_count, status_msg, cache_time = _collect_multi_source_options(symbol)
    chosen_days = _build_company_real_day_keys(all_days, today, max_cols=10)
    agg_walls = compute_aggregate_real_walls(combined_by_day, spot)

    cols_data = []
    has_any_real_data = False

    for d_key in chosen_days:
        dt = datetime.strptime(d_key, "%Y-%m-%d")
        delta_days = (dt.date() - today.date()).days
        is_today = (delta_days == 0)

        if delta_days == 0:
            tag = "今天到期"
        elif delta_days < 0:
            tag = f"{abs(delta_days)}天前"
        else:
            tag = f"+{delta_days}天到期"

        rec = combined_by_day.get(d_key, {})
        col_cdf = rec.get("cdf", pd.DataFrame())
        col_pdf = rec.get("pdf", pd.DataFrame())
        has_chain = _is_valid_chain_pair(col_cdf, col_pdf)
        if has_chain:
            has_any_real_data = True

        if has_chain:
            c_top_list, call_wall_val, p_bot_list, put_wall_val = extract_top3_walls(col_cdf, col_pdf, spot, delta_days=max(0, delta_days))
            raw_mp = (
                round((spot * 0.55 + call_wall_val * 0.25 + put_wall_val * 0.20), 2)
                if (call_wall_val is not None and put_wall_val is not None)
                else None
            )
            call_wall_px_label = f"Call {call_wall_val:g}" if call_wall_val is not None else "Call —"
            put_wall_px_label = f"Put {put_wall_val:g}" if put_wall_val is not None else "Put —"
        else:
            c_top_list, call_wall_val, p_bot_list, put_wall_val = [], None, [], None
            raw_mp = None
            call_wall_px_label = "Call —"
            put_wall_px_label = "Put —"

        cols_data.append({
            "day_key": d_key,
            "date": dt,
            "date_str": dt.strftime("%d/%m"),
            "tag": tag,
            "exp_label": tag,
            "call_wall_px_label": call_wall_px_label,
            "put_wall_px_label": put_wall_px_label,
            "is_today": is_today,
            "delta": delta_days,
            "has_chain": has_chain,
            "c_top": c_top_list,
            "p_bot": p_bot_list,
            "call_wall": call_wall_val,
            "max_pain": raw_mp,
            "spot": spot,
            "put_wall": put_wall_val,
        })

    return cols_data, has_any_real_data, live_count, status_msg, cache_time, agg_walls

def build_custom_option_matrix_html(symbol, spot):
    cols_data, has_any_real_data, live_count, status_msg, cache_time, agg_walls = pull_and_filter_real_expirations_locally(symbol, spot)

    all_vals = []
    for c in cols_data:
        for v in [c["call_wall"], c["max_pain"], c["spot"], c["put_wall"]]:
            if v is not None:
                all_vals.append(v)
    if not all_vals:
        all_vals = [spot * 0.95, spot, spot * 1.05]

    v_min = min(all_vals)
    v_max = max(all_vals)
    v_span = (v_max - v_min) if v_max != v_min else max(spot * 0.05, 5.0)
    y_low = v_min - v_span * 0.25
    y_high = v_max + v_span * 0.25

    layout_cols = 10
    col_w = 128
    left_axis_w = 96
    total_chart_w = layout_cols * col_w
    header_h = 54
    top3_h = 99
    svg_h = 246
    bot3_h = 99
    footer_h = 48

    def val_to_y(v):
        ratio = (v - y_low) / (y_high - y_low)
        return round(svg_h - (ratio * (svg_h - 36) + 18), 1)

    svg_elements = ""
    y_ticks_html = ""
    num_ticks = 5
    for t_i in range(num_ticks + 1):
        tick_val = y_low + (y_high - y_low) * (t_i / num_ticks)
        ty = val_to_y(tick_val)
        svg_elements += f"<line x1='0' y1='{ty}' x2='{total_chart_w}' y2='{ty}' stroke='#e2e8f0' stroke-width='1' stroke-dasharray='4,4' />"
        y_ticks_html += f"<div style='position:absolute; top:{ty - 9}px; right:6px; font-size:13px; font-weight:800; color:#334155;'>{tick_val:.1f}</div>"

    for idx in range(layout_cols):
        x_left = idx * col_w
        if idx < len(cols_data) and cols_data[idx]["is_today"]:
            svg_elements += f"<rect x='{x_left}' y='0' width='{col_w}' height='{svg_h}' fill='rgba(250, 204, 21, 0.16)' />"
        svg_elements += f"<line x1='{x_left + col_w}' y1='0' x2='{x_left + col_w}' y2='{svg_h}' stroke='#cbd5e1' stroke-width='1' />"

    pts_call, pts_mp, pts_spot, pts_put = [], [], [], []
    for idx, c in enumerate(cols_data):
        cx = round(idx * col_w + col_w / 2, 1)
        if c["call_wall"] is not None:
            pts_call.append((cx, val_to_y(c["call_wall"]), c["call_wall"]))
        if c["max_pain"] is not None:
            pts_mp.append((cx, val_to_y(c["max_pain"]), c["max_pain"]))
        if c["spot"] is not None:
            pts_spot.append((cx, val_to_y(c["spot"]), c["spot"]))
        if c["put_wall"] is not None:
            pts_put.append((cx, val_to_y(c["put_wall"]), c["put_wall"]))

    def draw_polyline(pts, color, width=2.8, dash=""):
        if len(pts) < 2:
            return ""
        p_str = " ".join([f"{x},{y}" for x, y, _ in pts])
        dash_attr = f"stroke-dasharray='{dash}'" if dash else ""
        return f"<polyline fill='none' stroke='{color}' stroke-width='{width}' {dash_attr} points='{p_str}' />"

    svg_elements += draw_polyline(pts_call, "#16a34a", 3.0)
    svg_elements += draw_polyline(pts_put, "#dc2626", 3.0)
    svg_elements += draw_polyline(pts_mp, "#2563eb", 2.4, "4,3")
    svg_elements += draw_polyline(pts_spot, "#0f172a", 3.6)

    for cx, cy, val in pts_call:
        svg_elements += f"<circle cx='{cx}' cy='{cy}' r='4.5' fill='#16a34a' stroke='#fff' stroke-width='1.2' />"
        svg_elements += f"<text x='{cx}' y='{cy - 8}' text-anchor='middle' font-size='13' font-weight='900' fill='#15803d'>{val:g}</text>"

    for px, py, pval in pts_put:
        svg_elements += f"<circle cx='{px}' cy='{py}' r='4.5' fill='#dc2626' stroke='#fff' stroke-width='1.2' />"
        svg_elements += f"<text x='{px}' y='{py + 16}' text-anchor='middle' font-size='13' font-weight='900' fill='#b91c1c'>{pval:g}</text>"

    for mx, my, mval in pts_mp:
        svg_elements += f"<circle cx='{mx}' cy='{my}' r='4' fill='#2563eb' />"
        svg_elements += f"<text x='{mx}' y='{my - 8}' text-anchor='middle' font-size='12.5' font-weight='800' fill='#1d4ed8'>{mval:g}</text>"

    for sx, sy, sval in pts_spot:
        svg_elements += f"<circle cx='{sx}' cy='{sy}' r='5' fill='#0f172a' stroke='#facc15' stroke-width='1.5' />"
        svg_elements += f"<text x='{sx}' y='{sy + 17}' text-anchor='middle' font-size='13.5' font-weight='900' fill='#0f172a'>{sval:g}</text>"

    cache_tag = f" | 缓存:{cache_time}" if cache_time else ""
    status_badge = f"{status_msg}{cache_tag}"

    agg_c_str = " / ".join([f"${k:g}{'(已冲破转支撑)' if broken else ''}" for k, _, broken in agg_walls.get("call_walls", [])]) or "—"
    agg_p_str = " / ".join([f"${k:g}" for k, _, _ in agg_walls.get("put_walls", [])]) or "—"

    html = f"""
    <div style="background:#ffffff; border:2px solid #1e293b; border-radius:8px; padding:8px 10px; font-family:sans-serif; color:#0f172a; width:100%; box-sizing:border-box; overflow:hidden;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px; padding-bottom:4px; border-bottom:1px solid #cbd5e1; height:28px; box-sizing:border-box;">
            <div style="font-size:15px; font-weight:900; color:#0f172a;">
                📊 {symbol} 真实期权墙矩阵 ({status_badge} | Spot: <span style="background:#fef08a; padding:1px 6px; border-radius:4px;">${spot:.2f}</span>)
            </div>
            <div style="display:flex; gap:16px; font-size:13px; font-weight:900;">
                <span style="color:#16a34a;">━━ Call Wall (OI+实时量)</span>
                <span style="color:#2563eb;">╌╌ Max Pain</span>
                <span style="color:#0f172a;">━━ Spot</span>
                <span style="color:#dc2626;">━━ Put Wall (OI+实时量)</span>
            </div>
        </div>
        <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:5px; padding:3px 8px; margin-bottom:6px; font-size:12.5px; font-weight:800; display:flex; justify-content:space-between;">
            <span style="color:#15803d;">🟢 全期限累计主力 Call 墙 Top3: {agg_c_str}</span>
            <span style="color:#b91c1c;">🔴 全期限累计主力 Put 墙 Top3: {agg_p_str}</span>
        </div>

        <div style="display:flex; width:100%;">
            <div style="width:{left_axis_w}px; flex-shrink:0; border-right:2px solid #1e293b; display:flex; flex-direction:column; box-sizing:border-box;">
                <div style="height:{header_h}px; border-bottom:1px solid #cbd5e1; display:flex; flex-direction:column; align-items:center; justify-content:center; font-weight:900; font-size:13px; background:#f8fafc; box-sizing:border-box;">
                    <span>到期日</span>
                    <span style="font-size:10.5px; font-weight:800; color:#15803d;">Call Wall 价</span>
                </div>
                <div style="height:{top3_h}px; border-bottom:2px solid #1e293b; display:flex; flex-direction:column; align-items:center; justify-content:center; font-weight:900; font-size:13px; color:#15803d; background:#f0fdf4; text-align:center; box-sizing:border-box;">
                    <span>上3档 Call</span>
                    <span style="font-size:10.5px; font-weight:800;">OI+实时量加权</span>
                </div>
                <div style="height:{svg_h}px; position:relative; border-bottom:2px solid #1e293b; background:#ffffff; box-sizing:border-box;">
                    {y_ticks_html}
                </div>
                <div style="height:{bot3_h}px; border-bottom:1px solid #cbd5e1; display:flex; flex-direction:column; align-items:center; justify-content:center; font-weight:900; font-size:13px; color:#b91c1c; background:#fef2f2; text-align:center; box-sizing:border-box;">
                    <span>下3档 Put</span>
                    <span style="font-size:10.5px; font-weight:800;">OI+实时量加权</span>
                </div>
                <div style="height:{footer_h}px; display:flex; flex-direction:column; align-items:center; justify-content:center; font-weight:900; font-size:13px; background:#f8fafc; box-sizing:border-box;">
                    <span>到期轴</span>
                    <span style="font-size:10.5px; font-weight:800; color:#b91c1c;">Put Wall 价</span>
                </div>
            </div>

            <div style="display:flex; flex:1; min-width:0;">
    """

    for c in cols_data:
        bg_col = "background:#fef08a;" if c["is_today"] else ""
        bg_cell = "background:rgba(254,240,138,0.25);" if c["is_today"] else "background:#ffffff;"

        c_rows_html = ""
        if c["c_top"]:
            for k_val, oi_val in c["c_top"]:
                is_max_c = (k_val == c["call_wall"])
                hi_style = "background:#dcfce7; font-weight:900; color:#14532d;" if is_max_c else "font-weight:800; color:#0f172a;"
                c_rows_html += f"""
                    <div style="height:33px; border-bottom:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center; padding:0 6px; font-size:13px; box-sizing:border-box; {hi_style}">
                        <span>{k_val:g}</span>
                        <span style="color:#cbd5e1;">|</span>
                        <span>{oi_val:,}</span>
                    </div>
                """
        else:
            c_rows_html = """
                <div style="height:99px; display:flex; align-items:center; justify-content:center; font-size:13px; color:#64748b; font-weight:800;">
                    无真实链数据
                </div>
            """

        p_rows_html = ""
        if c["p_bot"]:
            for k_val, oi_val in c["p_bot"]:
                is_max_p = (k_val == c["put_wall"])
                hi_style = "background:#fee2e2; font-weight:900; color:#7f1d1d;" if is_max_p else "font-weight:800; color:#0f172a;"
                p_rows_html += f"""
                    <div style="height:33px; border-bottom:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center; padding:0 6px; font-size:13px; box-sizing:border-box; {hi_style}">
                        <span>{k_val:g}</span>
                        <span style="color:#cbd5e1;">|</span>
                        <span>{oi_val:,}</span>
                    </div>
                """
        else:
            p_rows_html = """
                <div style="height:99px; display:flex; align-items:center; justify-content:center; font-size:13px; color:#64748b; font-weight:800;">
                    无真实链数据
                </div>
            """

        html += f"""
                <div style="flex:1; min-width:0; border-right:1px solid #cbd5e1; box-sizing:border-box; display:flex; flex-direction:column;">
                    <div style="height:{header_h}px; border-bottom:1px solid #cbd5e1; display:flex; flex-direction:column; align-items:center; justify-content:center; box-sizing:border-box; {bg_col}">
                        <span style="font-size:12.5px; font-weight:900; color:#0f172a;">{c['date_str']} <span style="color:#475569; font-size:10.5px;">{c['exp_label']}</span></span>
                        <span style="font-size:11.5px; font-weight:900; color:#15803d;">{c['call_wall_px_label']}</span>
                    </div>
                    <div style="height:{top3_h}px; border-bottom:2px solid #1e293b; box-sizing:border-box; {bg_cell}">
                        {c_rows_html}
                    </div>
                    <div style="height:{svg_h}px; border-bottom:2px solid #1e293b; box-sizing:border-box; {bg_cell}"></div>
                    <div style="height:{bot3_h}px; border-bottom:1px solid #cbd5e1; box-sizing:border-box; {bg_cell}">
                        {p_rows_html}
                    </div>
                    <div style="height:{footer_h}px; display:flex; flex-direction:column; align-items:center; justify-content:center; box-sizing:border-box; {bg_col}">
                        <span style="font-size:12.5px; font-weight:900; color:#0f172a;">{c['date_str']}</span>
                        <span style="font-size:11.5px; font-weight:900; color:#b91c1c;">{c['put_wall_px_label']}</span>
                    </div>
                </div>
        """

    for _ in range(max(0, layout_cols - len(cols_data))):
        html += f"""
                <div style="flex:1; min-width:0; border-right:1px solid #e2e8f0; box-sizing:border-box; display:flex; flex-direction:column; background:#fafafa;">
                    <div style="height:{header_h}px; border-bottom:1px solid #e2e8f0; display:flex; align-items:center; justify-content:center; font-size:11px; color:#94a3b8;">—</div>
                    <div style="height:{top3_h}px; border-bottom:2px solid #1e293b;"></div>
                    <div style="height:{svg_h}px; border-bottom:2px solid #1e293b;"></div>
                    <div style="height:{bot3_h}px; border-bottom:1px solid #e2e8f0;"></div>
                    <div style="height:{footer_h}px; display:flex; align-items:center; justify-content:center; font-size:11px; color:#94a3b8;">—</div>
                </div>
        """

    offset_up = svg_h + bot3_h + footer_h
    html += f"""
            </div>
        </div>

        <div style="position:relative; margin-top:-{offset_up}px; margin-left:{left_axis_w}px; width:calc(100% - {left_axis_w}px); height:{svg_h}px; pointer-events:none;">
            <svg width="{total_chart_w}" height="{svg_h}" viewBox="0 0 {total_chart_w} {svg_h}" style="width:100%; height:100%;" xmlns="http://www.w3.org/2000/svg">
                {svg_elements}
            </svg>
        </div>
        <div style="height:{bot3_h + footer_h}px;"></div>
    </div>
    """
    return html

# ==================== 3. PERIOD 9 LI-FIRE MACRO (30%) + NATAL GANZHI DOMINANT (70%) ====================

TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

TIANGAN_ELEMENT = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
}

DIZHI_ELEMENT = {
    "寅": "木", "卯": "木",
    "巳": "火", "午": "火",
    "辰": "土", "戌": "土", "丑": "土", "未": "土",
    "申": "金", "酉": "金",
    "亥": "水", "子": "水",
}

GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
OVERCOMES = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

CLASH_PAIRS = {
    frozenset({"子", "午"}),
    frozenset({"丑", "未"}),
    frozenset({"寅", "申"}),
    frozenset({"卯", "酉"}),
    frozenset({"辰", "戌"}),
    frozenset({"巳", "亥"}),
}

SIX_HARMONY_PAIRS = {
    frozenset({"子", "丑"}),
    frozenset({"寅", "亥"}),
    frozenset({"卯", "戌"}),
    frozenset({"辰", "酉"}),
    frozenset({"巳", "申"}),
    frozenset({"午", "未"}),
}

PUNISHMENT_PAIRS = {
    frozenset({"子", "卯"}),
    frozenset({"寅", "巳"}),
    frozenset({"巳", "申"}),
    frozenset({"寅", "申"}),
    frozenset({"丑", "戌"}),
    frozenset({"戌", "未"}),
    frozenset({"丑", "未"}),
}

SOLAR_MONTH_TO_ZHI_IDX = {
    2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7,
    8: 8, 9: 9, 10: 10, 11: 11, 12: 0, 1: 1,
}

STOCK_NATAL_SEEDS: dict[str, dict[str, Any]] = {
    "NVDA": {"gan": "丙", "zhi": "午", "role": "离火算力引擎", "earnings": [2, 5, 8, 11]},
    "AMD": {"gan": "丁", "zhi": "巳", "role": "离火进攻芯片", "earnings": [2, 5, 8, 11]},
    "TSM": {"gan": "庚", "zhi": "申", "role": "金旺晶圆制造", "earnings": [1, 4, 7, 10]},
    "ASML": {"gan": "辛", "zhi": "酉", "role": "精金光刻核心", "earnings": [1, 4, 7, 10]},
    "MSFT": {"gan": "壬", "zhi": "子", "role": "水润云与生态", "earnings": [1, 4, 7, 10]},
    "GOOGL": {"gan": "甲", "zhi": "寅", "role": "甲木搜索与AI", "earnings": [2, 4, 7, 10]},
    "META": {"gan": "乙", "zhi": "卯", "role": "乙木流量与社交", "earnings": [2, 4, 7, 10]},
    "AMZN": {"gan": "戊", "zhi": "戌", "role": "厚土云与零售", "earnings": [2, 4, 7, 10]},
    "AAPL": {"gan": "癸", "zhi": "亥", "role": "癸水消费终端", "earnings": [2, 5, 8, 11]},
    "TSLA": {"gan": "丙", "zhi": "戌", "role": "火库高波动先锋", "earnings": [1, 4, 7, 10]},
    "NFLX": {"gan": "丁", "zhi": "未", "role": "火土内容订阅", "earnings": [1, 4, 7, 10]},
    "MRVL": {"gan": "庚", "zhi": "辰", "role": "金库网络与定制芯片", "earnings": [3, 6, 9, 12]},
    "MPWR": {"gan": "辛", "zhi": "丑", "role": "金土电源管理", "earnings": [2, 5, 8, 11]},
    "SMCI": {"gan": "甲", "zhi": "申", "role": "木金机架高弹性", "earnings": [2, 5, 8, 11]},
    "CEG": {"gan": "己", "zhi": "未", "role": "土旺基荷电力", "earnings": [2, 5, 8, 11]},
    "CBRS": {"gan": "壬", "zhi": "申", "role": "水金晶圆级算力", "earnings": [3, 6, 9, 12]},
    "SPCX": {"gan": "戊", "zhi": "寅", "role": "土木航天发射", "earnings": [2, 5, 8, 11]},
    "NG.L": {"gan": "己", "zhi": "丑", "role": "稳土公用事业", "earnings": [5, 11]},
    "QQQ": {"gan": "甲", "zhi": "午", "role": "木火成长指数", "earnings": [1, 4, 7, 10]},
    "VUAG.L": {"gan": "戊", "zhi": "辰", "role": "稳土标普宽基", "earnings": [1, 4, 7, 10]},
    "EQQQ.L": {"gan": "乙", "zhi": "巳", "role": "木火纳指宽基", "earnings": [1, 4, 7, 10]},
}

PERIOD9_LI_FIRE_MONTHS = {
    1:  {"base_tech": 50.0, "real": 74.0, "tag": "冬末重配", "desc": "新年流动性回流·整固"},
    2:  {"base_tech": 54.0, "real": 68.0, "tag": "春初脉冲", "desc": "离火启暖·财报预期窗"},
    3:  {"base_tech": 50.0, "real": 54.0, "tag": "季末税窗", "desc": "3月底税季卖盘+季末调仓"},
    4:  {"base_tech": 56.0, "real": 65.0, "tag": "税后回流", "desc": "新财年资金回补"},
    5:  {"base_tech": 53.0, "real": 66.0, "tag": "夏前节律", "desc": "离火渐旺·春末休整"},
    6:  {"base_tech": 52.0, "real": 60.0, "tag": "年中整固", "desc": "年中再平衡"},
    7:  {"base_tech": 57.0, "real": 63.0, "tag": "中报节律", "desc": "盛夏中报窗·假期交织"},
    8:  {"base_tech": 55.0, "real": 44.0, "tag": "离火震荡", "desc": "盛夏后离火偏躁·防追高"},
    9:  {"base_tech": 51.0, "real": 52.0, "tag": "冲月清洗", "desc": "9月中旬冲月清洗+四巫换仓"},
    10: {"base_tech": 58.0, "real": 76.0, "tag": "旺月兑现", "desc": "旺月财报与业绩兑现"},
    11: {"base_tech": 54.0, "real": 86.0, "tag": "成果入库", "desc": "感恩节假期+实盘筹划"},
    12: {"base_tech": 49.0, "real": 62.0, "tag": "刑月税假", "desc": "12月中旬年底税务+圣诞长假"},
}

def _year_to_ganzhi(year: int) -> tuple[str, str]:
    offset = year - 1984
    return TIANGAN[offset % 10], DIZHI[offset % 12]

def _solar_month_ganzhi(year: int, month: int) -> tuple[str, str]:
    gz_year = year - 1 if month == 1 else year
    y_gan, _ = _year_to_ganzhi(gz_year)
    y_gan_idx = TIANGAN.index(y_gan)
    start_gan_idx = ((y_gan_idx % 5) * 2 + 2) % 10
    month_step = 11 if month == 1 else (month - 2)
    m_gan = TIANGAN[(start_gan_idx + month_step) % 10]
    m_zhi = DIZHI[SOLAR_MONTH_TO_ZHI_IDX[month]]
    return m_gan, m_zhi

def evaluate_period9_li_fire_affinity(stock_el: str, stock_zhi: str) -> dict[str, Any]:
    if stock_el == "火":
        bonus = 8.0
        vol_mult = 1.18
        tag = "离火当运·比和共振"
        desc = "本命属火顺九紫离火大运，顺风弹性强，冲刑月波动更显著"
    elif stock_el == "木":
        bonus = 6.5
        vol_mult = 1.12
        tag = "木生离火·顺势泄秀"
        desc = "木生离火得大运之气，遇合生月易走强，逢冲克月亦会回踩"
    elif stock_el == "土":
        bonus = 4.0
        vol_mult = 0.92
        tag = "火生厚土·承接稳健"
        desc = "离火生土得大运滋养，波动相对收敛，承接力较稳"
    elif stock_el == "金":
        bonus = -5.5
        vol_mult = 1.20
        tag = "离火炼金·波段分化"
        desc = "火克金受离火淬炼，遇冲克月易深蹲，得生扶/合月易反弹"
    else:
        bonus = -4.0
        vol_mult = 1.16
        tag = "水火既济·冲克明显"
        desc = "水火相激，得合生则顺，逢冲刑克则回撤较明显"

    if stock_zhi == "午":
        bonus += 2.0
        tag += "(午火归位)"
    elif stock_zhi == "子":
        bonus -= 2.0
        tag += "(子午水火冲)"

    return {
        "era_name": "九紫离火运 (2024-2043)",
        "era_bonus": round(bonus, 1),
        "vol_mult": vol_mult,
        "era_tag": tag,
        "era_desc": desc,
    }

def _ganzhi_pair_interaction(
    base_gan: str,
    base_zhi: str,
    base_el: str,
    other_gan: str,
    other_zhi: str,
    context_prefix: str,
) -> tuple[float, str]:
    other_el = TIANGAN_ELEMENT[other_gan]
    score = 0.0
    tags = []

    pair_zhi = frozenset({base_zhi, other_zhi})
    if pair_zhi in CLASH_PAIRS:
        score -= 17.0
        tags.append(f"{context_prefix}{base_zhi}{other_zhi}相冲")
    elif pair_zhi in PUNISHMENT_PAIRS:
        score -= 13.5
        tags.append(f"{context_prefix}{base_zhi}{other_zhi}相刑")
    elif pair_zhi in SIX_HARMONY_PAIRS:
        score += 15.5
        tags.append(f"{context_prefix}{base_zhi}{other_zhi}六合")
    elif base_zhi == other_zhi:
        score += 8.5
        tags.append(f"{context_prefix}同支{other_zhi}")

    if GENERATES.get(other_el) == base_el:
        score += 12.0
        tags.append(f"{context_prefix}{other_el}生本命{base_el}")
    elif GENERATES.get(base_el) == other_el:
        score -= 5.0
        tags.append(f"{context_prefix}本命{base_el}泄{other_el}")
    elif OVERCOMES.get(other_el) == base_el:
        score -= 14.0
        tags.append(f"{context_prefix}{other_el}克本命{base_el}")
    elif OVERCOMES.get(base_el) == other_el:
        score += 7.5
        tags.append(f"{context_prefix}本命{base_el}制{other_el}")
    elif other_el == base_el:
        score += 6.5
        tags.append(f"{context_prefix}比和{base_el}")

    if not tags:
        tags.append(f"{context_prefix}平和")
    return score, "·".join(tags[:2])

def resolve_stock_natal_chart(symbol: str, ref_dt: datetime | None = None) -> dict[str, Any]:
    clean_sym = symbol.upper().strip() or "NVDA"
    now_dt = ref_dt or datetime.today()
    cur_y_gan, cur_y_zhi = _year_to_ganzhi(now_dt.year)

    if clean_sym in STOCK_NATAL_SEEDS:
        seed = STOCK_NATAL_SEEDS[clean_sym]
        gan = seed["gan"]
        zhi = seed["zhi"]
        role = seed["role"]
        earnings_months = list(seed["earnings"])
        source_mode = "命盘档案库"
    else:
        digest = hashlib.sha256(clean_sym.encode("utf-8")).hexdigest()
        seed_int = int(digest[:12], 16)
        gan = TIANGAN[seed_int % 10]
        zhi = DIZHI[(seed_int // 10) % 12]
        el_name = TIANGAN_ELEMENT[gan]
        role = f"{el_name}象自动推演命盘"
        q_offset = seed_int % 3
        earnings_months = sorted({12 if m > 12 else m for m in [1 + q_offset, 4 + q_offset, 7 + q_offset, 10 + q_offset]})
        source_mode = "自动推演命盘"

    element = TIANGAN_ELEMENT[gan]
    zhi_element = DIZHI_ELEMENT[zhi]
    era_info = evaluate_period9_li_fire_affinity(element, zhi)
    year_delta, year_note = _ganzhi_pair_interaction(
        gan, zhi, element, cur_y_gan, cur_y_zhi, context_prefix="年"
    )

    profile = {
        "symbol": clean_sym,
        "gan": gan,
        "zhi": zhi,
        "ganzhi": f"{gan}{zhi}",
        "element": element,
        "zhi_element": zhi_element,
        "role": role,
        "earnings_months": earnings_months,
        "source_mode": source_mode,
        "era_name": era_info["era_name"],
        "era_bonus": era_info["era_bonus"],
        "vol_mult": era_info["vol_mult"],
        "era_tag": era_info["era_tag"],
        "era_desc": era_info["era_desc"],
        "cur_year_ganzhi": f"{cur_y_gan}{cur_y_zhi}",
        "cur_year_delta": round(year_delta, 1),
        "cur_year_note": year_note,
        "resolved_at": now_dt.strftime("%H:%M:%S"),
    }
    st.session_state["stock_natal_registry"][clean_sym] = profile
    return profile

def get_earnings_phase_status(
    y_num: int,
    m_num: int,
    e_months: list[int],
    ref_dt: datetime | None = None,
) -> dict[str, Any]:
    now_dt = ref_dt or datetime.today()
    cur_ym = now_dt.year * 12 + now_dt.month
    cell_ym = y_num * 12 + m_num
    prev_m = 12 if m_num == 1 else (m_num - 1)
    next_m = 1 if m_num == 12 else (m_num + 1)

    is_earnings_month = m_num in e_months
    is_post_earnings_now = (cell_ym == cur_ym) and is_earnings_month and (now_dt.day >= 15)
    is_pre_earnings = (next_m in e_months) and not is_post_earnings_now

    if is_post_earnings_now:
        delta = -2.0
        label = "财报刚出·消化期"
        note = "财报刚发布·消化重定价"
        flow_prefix = "财报后资金风向："
    elif is_pre_earnings:
        delta = 3.0
        label = "财报前窗"
        note = "财报前抢跑/预期窗"
        flow_prefix = "财报前资金风向："
    elif is_earnings_month:
        delta = 2.0
        label = "财报月"
        note = "财报日波动窗"
        flow_prefix = "财报期资金风向："
    elif prev_m in e_months:
        delta = -2.5
        label = "财报后消化"
        note = "财报后兑现消化"
        flow_prefix = "财报后资金风向："
    else:
        delta = 0.0
        label = ""
        note = ""
        flow_prefix = "近期资金风向："

    return {
        "delta": delta,
        "label": label,
        "note": note,
        "flow_prefix": flow_prefix,
        "is_pre_earnings": is_pre_earnings,
        "is_earnings_month": is_earnings_month,
        "is_post_earnings_now": is_post_earnings_now,
    }

def _macro_calendar_factors(
    y_num: int,
    m_num: int,
    e_months: list[int],
    ref_dt: datetime | None = None,
) -> dict[str, Any]:
    tax_delta = 0.0
    holiday_delta = 0.0
    quarter_delta = 0.0
    notes: list[str] = []

    e_info = get_earnings_phase_status(y_num, m_num, e_months, ref_dt=ref_dt)
    earnings_delta = e_info["delta"]

    if m_num == 3:
        tax_delta = -11.0
        quarter_delta = -4.0
        notes.append("3月底税季卖盘(-11)+季末调仓(-4)")
    elif m_num == 12:
        tax_delta = -8.0
        holiday_delta = -7.0
        notes.append("12月中旬年底税务(-8)+圣诞长假(-7)")
    elif m_num == 9:
        tax_delta = -8.0
        quarter_delta = -4.0
        notes.append("9月中旬冲月清洗(-8)+四巫换仓(-4)")
    elif m_num == 11:
        holiday_delta = -6.0
        notes.append("11月感恩节假期(-6)")
    elif m_num == 1:
        holiday_delta = -5.0
        notes.append("1月初跨年长假余波(-5)")
    elif m_num in (5, 7):
        holiday_delta = -4.5
        notes.append(f"{m_num}月长假流动性回落(-4.5)")

    if e_info["note"]:
        notes.append(e_info["note"])

    return {
        "tax_delta": tax_delta,
        "holiday_delta": holiday_delta,
        "quarter_delta": quarter_delta,
        "earnings_delta": earnings_delta,
        "is_pre_earnings": e_info["is_pre_earnings"],
        "is_earnings_month": e_info["is_earnings_month"],
        "is_post_earnings_now": e_info["is_post_earnings_now"],
        "phase_label": e_info["label"],
        "flow_prefix": e_info["flow_prefix"],
        "note": " | ".join(notes) if notes else "离火运常规节律",
    }

def evaluate_flow_radar(
    symbol: str,
    m_data: dict[str, Any],
    cdf: pd.DataFrame,
    pdf: pd.DataFrame,
    phase_prefix: str = "近期资金风向：",
    post_earnings_mode: bool = False,
) -> dict[str, str]:
    price = float(m_data.get("price", 0.0))
    ma20 = float(m_data.get("ma20", price))
    ma50 = float(m_data.get("ma50", price))
    rsi = float(m_data.get("rsi", 50.0))

    flow_score = 0.0
    reasons: list[str] = []

    if post_earnings_mode:
        reasons.append("近期财报刚落地，市场处于财报后消化与重定价阶段")

    if price > 0 and ma20 > 0:
        if price >= ma20 and ma20 >= ma50:
            flow_score += 1.5
            reasons.append("股价站稳短期均线，回踩有承接")
        elif price < ma20 and price < ma50:
            flow_score -= 1.5
            reasons.append("股价跌破短期均线，短线承压")
        else:
            reasons.append("股价在均线附近震荡")

    if rsi >= 72:
        flow_score -= 1.0
        reasons.append("短线情绪偏热，防资金顺势兑现")
    elif rsi <= 35:
        flow_score += 0.5
        reasons.append("短线跌出超卖区，留意低位承接")

    if _is_valid_chain_pair(cdf, pdf) and price > 0:
        _, c_wall, _, p_wall = extract_top3_walls(cdf, pdf, price)
        coi = safe_col_sum(cdf, "openInterest")
        poi = safe_col_sum(pdf, "openInterest")
        pcr = (poi / coi) if coi > 0 else 1.0

        if c_wall is not None and p_wall is not None:
            up_room = (c_wall - price) / price
            dn_room = (price - p_wall) / price
            if pcr <= 0.85 and up_room >= 0.05:
                flow_score += 1.5
                reasons.append("期权上方留有空间，偏多博弈占优")
            elif pcr >= 1.15 or dn_room <= 0.04:
                flow_score -= 1.5
                reasons.append("期权下方防守偏重，资金更偏防险")
            else:
                reasons.append("期权上下防守相对均衡")

    if flow_score >= 1.5:
        return {
            "prefix": phase_prefix,
            "state": "偏进场",
            "badge": "🟢 偏进场（财报后资金在回补/托底）" if post_earnings_mode else "🟢 偏进场（资金在提前布局/托底）",
            "color": "#4ade80",
            "short_tag": "偏进场",
            "explain": "；".join(reasons[:2]) if reasons else "价格与持仓结构偏稳，资金有回补迹象。",
            "advice": "若企稳可按节奏分批，急拉不追高。",
        }
    elif flow_score <= -1.5:
        return {
            "prefix": phase_prefix,
            "state": "偏撤退",
            "badge": "🔴 偏撤退（财报后资金偏防险/消化波动）" if post_earnings_mode else "🔴 偏撤退（资金在提前减仓/买保险）",
            "color": "#f87171",
            "short_tag": "偏撤退",
            "explain": "；".join(reasons[:2]) if reasons else "反弹承压或防守力量偏重，资金更偏防风险。",
            "advice": "波动期不盲目接飞刀，等止跌企稳再按低位限价单节奏执行。",
        }
    else:
        return {
            "prefix": phase_prefix,
            "state": "在拉锯",
            "badge": "🟡 在拉锯（财报刚出完，多空正在消化业绩与指引）" if post_earnings_mode else "🟡 在拉锯（多空都在等待明确方向）",
            "color": "#facc15",
            "short_tag": "在拉锯",
            "explain": "；".join(reasons[:2]) if reasons else "多空正在重新定价，方向尚未完全明朗。",
            "advice": "少折腾、先看消化节奏，等关键支撑/阻力位确认后再动手。",
        }

def _estimate_range_anchored_price(
    anchor_px: float,
    tech_score: float,
    m_data: dict[str, Any] | None = None,
    last_week_low: float = 0.0,
    month_num: int = 0,
) -> float:
    """
    以 11月中旬实盘价格为固定基准锚点（50分位置），不再随当日盘中价格漂移；
    计算 12月低位时，结合上周真实低位的回撤幅度进行双重校准。
    """
    if anchor_px <= 0:
        return 0.0

    m_info = m_data or {}
    r_high = float(m_info.get("recent_high") or 0.0)
    h52 = float(m_info.get("high52") or 0.0)
    l52 = float(m_info.get("low52") or 0.0)

    default_floor = anchor_px * 0.84
    if last_week_low > 0 and last_week_low < anchor_px:
        lw_drop_pct = (anchor_px - last_week_low) / anchor_px
        projected_deep_floor = last_week_low * (1.0 - max(0.03, min(0.08, lw_drop_pct * 0.65)))
        floor_px = max(anchor_px * 0.76, min(default_floor, projected_deep_floor))
    elif l52 > 0 and l52 < anchor_px:
        floor_px = max(anchor_px * 0.78, min(default_floor, anchor_px * 0.65 + l52 * 0.35))
    else:
        floor_px = default_floor
    floor_px = min(floor_px, anchor_px * 0.93)

    default_ceil = anchor_px * 1.24
    ref_top = max(r_high, h52 * 0.95) if (r_high > 0 or h52 > 0) else default_ceil
    if ref_top > anchor_px * 1.05:
        ceil_px = min(anchor_px * 1.42, max(default_ceil, anchor_px * 0.55 + ref_top * 0.45))
    else:
        ceil_px = default_ceil

    neutral_score = 50.0
    if tech_score <= neutral_score:
        ratio = max(0.0, min(1.0, (tech_score - 8.0) / (neutral_score - 8.0)))
        est = floor_px + (anchor_px - floor_px) * ratio
        if month_num == 12 and last_week_low > 0:
            dec_mid_ref = last_week_low * (0.94 + 0.04 * ratio)
            est = round(est * 0.45 + dec_mid_ref * 0.55, 2)
    else:
        ratio = max(0.0, min(1.0, (tech_score - neutral_score) / (98.0 - neutral_score)))
        est = anchor_px + (ceil_px - anchor_px) * ratio

    return round(est, 2)

def _fmt_price_ref(val: float, symbol: str = "") -> str:
    clean_sym = symbol.upper().strip()
    prefix = "£" if clean_sym.endswith(".L") else "$"
    if val >= 100:
        return f"≈{prefix}{val:.0f}"
    return f"≈{prefix}{val:.2f}"

def build_rolling_12m_cycle_rows(
    symbol: str,
    start_year: int,
    start_month: int,
    m_data: dict[str, Any] | None = None,
    cdf: pd.DataFrame | None = None,
    pdf: pd.DataFrame | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    now_dt = datetime.today()
    natal = resolve_stock_natal_chart(symbol, ref_dt=now_dt)

    s_gan = natal["gan"]
    s_zhi = natal["zhi"]
    s_el = natal["element"]
    e_months = natal["earnings_months"]
    era_bonus = float(natal["era_bonus"])
    vol_mult = float(natal["vol_mult"])
    spot = float((m_data or {}).get("price") or 0.0)

    anchor_info = fetch_cycle_anchor_prices(symbol, spot)
    base_anchor_px = float(anchor_info["mid_nov_anchor"]) if anchor_info["mid_nov_anchor"] > 0 else spot
    last_week_low = float(anchor_info["last_week_low"])

    cur_phase = get_earnings_phase_status(start_year, start_month, e_months, ref_dt=now_dt)
    flow_info = evaluate_flow_radar(
        symbol,
        m_data or {},
        cdf if cdf is not None else pd.DataFrame(),
        pdf if pdf is not None else pd.DataFrame(),
        phase_prefix=cur_phase["flow_prefix"],
        post_earnings_mode=cur_phase["is_post_earnings_now"],
    )

    rows = []
    for step in range(12):
        total_m = (start_year * 12 + (start_month - 1)) + step
        y_num = total_m // 12
        m_num = (total_m % 12) + 1

        y_gan, y_zhi = _year_to_ganzhi(y_num)
        m_gan, m_zhi = _solar_month_ganzhi(y_num, m_num)

        p9_m = PERIOD9_LI_FIRE_MONTHS[m_num]
        dist = _macro_calendar_factors(y_num, m_num, e_months, ref_dt=now_dt)

        yr_delta, yr_note = _ganzhi_pair_interaction(s_gan, s_zhi, s_el, y_gan, y_zhi, context_prefix="年")
        mo_delta, mo_note = _ganzhi_pair_interaction(s_gan, s_zhi, s_el, m_gan, m_zhi, context_prefix="月")

        natal_cycle_score = (mo_delta * 1.35 + yr_delta * 0.65) * vol_mult
        macro_bg_score = era_bonus * 0.75

        earn_adj = dist["earnings_delta"]
        if dist["is_pre_earnings"] and flow_info["state"] == "偏撤退":
            earn_adj -= 2.0
        elif dist["is_pre_earnings"] and flow_info["state"] == "偏进场":
            earn_adj += 1.5

        raw_score = (
            p9_m["base_tech"]
            + macro_bg_score
            + natal_cycle_score
            + dist["tax_delta"]
            + dist["holiday_delta"]
            + dist["quarter_delta"]
            + earn_adj
        )
        tech_score = round(max(8.0, min(98.0, raw_score)), 1)

        real_score = round(
            max(
                12.0,
                min(
                    98.0,
                    p9_m["real"]
                    + mo_delta * 0.35
                    + yr_delta * 0.20
                    + (dist["tax_delta"] + dist["holiday_delta"] + dist["quarter_delta"]) * 0.35,
                ),
            ),
            1,
        )

        approx_px = _estimate_range_anchored_price(
            base_anchor_px,
            tech_score,
            m_data,
            last_week_low=last_week_low,
            month_num=m_num,
        )
        approx_str = _fmt_price_ref(approx_px, symbol) if base_anchor_px > 0 else ""

        if m_num == 9:
            stance = "冲月清洗·四巫窗"
            action_hint = "急洗坑分批低吸布局"
            badge_color = "#dc2626"
        elif m_num == 12:
            stance = "年底税务·圣诞长假"
            action_hint = "防年末兑现/控仓避险"
            badge_color = "#dc2626"
        elif m_num == 3:
            stance = "3月底税季+季末窗"
            action_hint = "深蹲回踩留意分批低吸"
            badge_color = "#dc2626"
        elif dist["is_post_earnings_now"]:
            stance = "财报刚出·消化中"
            action_hint = "等财报波动消化/守纪律"
            badge_color = "#38bdf8"
        elif dist["is_pre_earnings"]:
            stance = f"财报前窗·{flow_info['short_tag']}"
            action_hint = "防冲高兑现 / 不盲目追高" if flow_info["state"] == "偏撤退" else "留意抢跑节奏 / 控仓"
            badge_color = "#f59e0b"
        elif tech_score >= 72:
            stance = "干支顺势·强旺窗"
            action_hint = "顺势波段 / 分批兑现"
            badge_color = "#16a34a"
        elif tech_score >= 45:
            stance = "干支蓄势·平衡窗"
            action_hint = "回踩分批 / 守现金"
            badge_color = "#2563eb"
        else:
            stance = "冲克承压·防回踩"
            action_hint = "控仓防冲 / 留意低吸"
            badge_color = "#dc2626"

        short_yr = str(y_num)[2:]
        x_label = f"{short_yr}年{m_num}月({m_gan}{m_zhi})"
        pt_text = f"{tech_score:.0f}分 · {approx_str}" if approx_str else f"{tech_score:.0f}分"
        factor_line = f"{mo_note} | {yr_note} | {dist['note']}"

        rows.append({
            "step": step,
            "year_num": y_num,
            "month_num": m_num,
            "x_label": x_label,
            "pt_text": pt_text,
            "short_title": f"{y_num}年{m_num}月",
            "y_ganzhi": f"{y_gan}{y_zhi}",
            "m_ganzhi": f"{m_gan}{m_zhi}",
            "rhythm_tag": p9_m["tag"],
            "rhythm_desc": p9_m["desc"],
            "factor_line": factor_line,
            "tech_score": tech_score,
            "real_score": real_score,
            "approx_price": approx_px,
            "approx_str": approx_str,
            "stance": stance,
            "action_hint": action_hint,
            "badge_color": badge_color,
            "is_pre_earnings": dist["is_pre_earnings"],
            "is_earnings_month": dist["is_earnings_month"],
            "is_post_earnings_now": dist["is_post_earnings_now"],
            "phase_label": dist["phase_label"],
        })

    avg_tech = round(sum(r["tech_score"] for r in rows) / len(rows), 1)
    peak_row = max(rows, key=lambda x: x["tech_score"])
    trough_row = min(rows, key=lambda x: x["tech_score"])
    dec_row = next((r for r in rows if r["month_num"] == 12), None)
    dec_low_str = dec_row["approx_str"] if dec_row else "—"

    price_range_str = ""
    if base_anchor_px > 0:
        min_px = min(r["approx_price"] for r in rows)
        max_px = max(r["approx_price"] for r in rows)
        price_range_str = f" | 区间参考价: <b>{_fmt_price_ref(min_px, symbol)} ~ {_fmt_price_ref(max_px, symbol)}</b>"

    meta_info = {
        **natal,
        "year_ganzhi": natal["cur_year_ganzhi"],
        "avg_tech": avg_tech,
        "peak_label": f"{peak_row['short_title']}({peak_row['tech_score']:.0f}分 {peak_row['approx_str']})",
        "trough_label": f"{trough_row['short_title']}({trough_row['tech_score']:.0f}分 {trough_row['approx_str']})",
        "price_range_str": price_range_str,
        "phase_label": cur_phase["label"],
        "flow_info": flow_info,
        "mid_nov_anchor_str": _fmt_price_ref(base_anchor_px, symbol),
        "mid_nov_label": anchor_info["mid_nov_label"],
        "last_week_low_str": _fmt_price_ref(last_week_low, symbol),
        "last_week_date_str": anchor_info["last_week_date_str"],
        "dec_low_str": dec_low_str,
    }
    return rows, meta_info

def render_12m_cycle_block_above_options(
    symbol: str,
    m_data: dict[str, Any] | None = None,
    cdf: pd.DataFrame | None = None,
    pdf: pd.DataFrame | None = None,
):
    now_dt = datetime.today()
    cur_year = now_dt.year
    cur_month = now_dt.month

    rows, meta_info = build_rolling_12m_cycle_rows(symbol, cur_year, cur_month, m_data=m_data, cdf=cdf, pdf=pdf)
    e_str = "、".join([f"{m}月" for m in meta_info["earnings_months"]])
    end_row = rows[-1]
    flow = meta_info["flow_info"]
    cur_phase_txt = f" | 当前阶段: <b>{meta_info['phase_label']}</b>" if meta_info.get("phase_label") else ""
    lw_dt_txt = f"({meta_info['last_week_date_str']})" if meta_info.get("last_week_date_str") else ""

    st.markdown("<div class='module-container' style='padding:12px 14px; margin-bottom:10px;'>", unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([4.8, 1.8])
    show_real_line = h_col2.toggle("显示虚实套利对比线", value=True, key=f"cycle_real_{symbol}")

    h_col1.markdown(
        f"<div class='card-header' style='margin-bottom:2px;'>🧭 {symbol} 未来12个月滚动能量表 (3分大运税务假期 · 7分个股干支冲合 | 定盘: <b>{meta_info['ganzhi']}·{meta_info['element']}</b> · {meta_info['role']})</div>"
        f"<div style='font-size:13.5px; color:#cbd5e1;'>大运背景: <b>{meta_info['era_name']}（{meta_info['era_tag']}）</b> | 现年柱: <b>{meta_info['year_ganzhi']}({meta_info['cur_year_note']})</b> | 区间: <b>{cur_year}年{cur_month}月 → {end_row['year_num']}年{end_row['month_num']}月</b> | 财报季: <b>{e_str}</b>{cur_phase_txt}<br>"
        f"📌 固定锚点({meta_info['mid_nov_label']}): <b style='color:#facc15;'>{meta_info['mid_nov_anchor_str']}</b> | 上周低位{lw_dt_txt}: <b style='color:#38bdf8;'>{meta_info['last_week_low_str']}</b> | 推算12月中低位: <b style='color:#f87171;'>{meta_info['dec_low_str']}</b> | 高:<b>{meta_info['peak_label']}</b> / 低:<b>{meta_info['trough_label']}</b>{meta_info['price_range_str']}</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<div style='background:#07193d; border:1.5px solid {flow['color']}; border-radius:8px; padding:8px 12px; margin:6px 0 8px 0;'>"
        f"<div style='font-size:14.5px; font-weight:900; color:{flow['color']};'>{flow['prefix']}{flow['badge']}</div>"
        f"<div style='font-size:12.5px; color:#e2e8f0; margin-top:2px;'>白话看点：{flow['explain']}（大运背景：{meta_info['era_desc']}）</div>"
        f"<div style='font-size:12.5px; color:#93c5fd; font-weight:800; margin-top:2px;'>操作提醒：{flow['advice']}（注：以11月中旬实盘价格为固定锚点，并结合上周真实低位校准12月中低位，非精确预测）</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    x_labels = [r["x_label"] for r in rows]
    y_tech = [r["tech_score"] for r in rows]
    y_real = [r["real_score"] for r in rows]
    pt_labels = [r["pt_text"] for r in rows]

    fig_12m = go.Figure()
    fig_12m.add_trace(go.Scatter(
        x=x_labels,
        y=y_tech,
        mode="lines+markers+text",
        name=f"{symbol} (70%个股干支 + 30%离火/税假)",
        text=pt_labels,
        textposition="top center",
        line=dict(color="#f97316", width=3.2),
        marker=dict(size=10, color="#f97316", line=dict(color="#ffffff", width=1.5)),
    ))
    if show_real_line:
        fig_12m.add_trace(go.Scatter(
            x=x_labels,
            y=y_real,
            mode="lines+markers+text",
            name="稳健/现金流基准 (实)",
            text=[f"{v:.0f}" for v in y_real],
            textposition="bottom center",
            line=dict(color="#16a34a", width=2.8),
            marker=dict(size=8, color="#22c55e", line=dict(color="#ffffff", width=1.4)),
        ))

    fig_12m.add_vrect(
        x0=-0.45,
        x1=0.45,
        fillcolor="rgba(250, 204, 21, 0.22)",
        line_width=0,
    )
    fig_12m.add_annotation(
        x=0,
        y=102,
        xref="x",
        yref="y",
        text=f"本月起点({cur_month}月)",
        showarrow=False,
        xanchor="center",
        yanchor="top",
        font=dict(color="#b45309", size=11.5),
        bgcolor="rgba(254, 240, 138, 0.92)",
    )

    for r in rows:
        idx_step = r["step"]
        if r["month_num"] == 9:
            fig_12m.add_vrect(x0=idx_step - 0.45, x1=idx_step + 0.45, fillcolor="rgba(239, 68, 68, 0.14)", line_width=0)
            fig_12m.add_annotation(x=idx_step, y=102, xref="x", yref="y", text="冲月清洗", showarrow=False, xanchor="center", yanchor="top", font=dict(color="#b91c1c", size=11), bgcolor="rgba(254, 226, 226, 0.92)")
        elif r["month_num"] == 12:
            fig_12m.add_vrect(x0=idx_step - 0.45, x1=idx_step + 0.45, fillcolor="rgba(59, 130, 246, 0.14)", line_width=0)
            fig_12m.add_annotation(x=idx_step, y=102, xref="x", yref="y", text="年底税务/长假", showarrow=False, xanchor="center", yanchor="top", font=dict(color="#1d4ed8", size=11), bgcolor="rgba(219, 234, 254, 0.92)")
        elif r["month_num"] == 3:
            fig_12m.add_vrect(x0=idx_step - 0.45, x1=idx_step + 0.45, fillcolor="rgba(239, 68, 68, 0.12)", line_width=0)
            fig_12m.add_annotation(x=idx_step, y=102, xref="x", yref="y", text="3月底税季低点", showarrow=False, xanchor="center", yanchor="top", font=dict(color="#b91c1c", size=11), bgcolor="rgba(254, 226, 226, 0.92)")
        elif r["is_post_earnings_now"]:
            fig_12m.add_annotation(x=idx_step, y=93, xref="x", yref="y", text="财报刚出·消化中", showarrow=False, xanchor="center", yanchor="top", font=dict(color="#0369a1", size=10.5), bgcolor="rgba(224, 242, 254, 0.94)")
        elif r["is_pre_earnings"]:
            fig_12m.add_annotation(x=idx_step, y=93, xref="x", yref="y", text=f"财报前窗·{flow['short_tag']}", showarrow=False, xanchor="center", yanchor="top", font=dict(color="#b45309", size=10.5), bgcolor="rgba(254, 243, 199, 0.92)")

    fig_12m.update_layout(
        template="plotly_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        height=285,
        font=dict(size=12, color="#0f172a"),
        margin=dict(l=12, r=12, t=42, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="left", x=0),
    )
    fig_12m.update_yaxes(range=[0, 110], gridcolor="#e2e8f0")
    st.plotly_chart(fig_12m, width="stretch")

    cards_html = "<div style='display:grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap:8px; margin-top:4px;'>"
    for r in rows:
        is_first = (r["step"] == 0)
        is_wash_m = (r["month_num"] in (3, 9, 12))
        is_pre = r["is_pre_earnings"]
        is_post_now = r["is_post_earnings_now"]

        if is_first:
            border_css = "border: 2.5px solid #facc15; box-shadow: 0 0 10px rgba(250,204,21,0.35);"
        elif is_wash_m:
            border_css = "border: 2px solid #ef4444; box-shadow: 0 0 8px rgba(239,68,68,0.28);"
        elif is_post_now:
            border_css = "border: 2px solid #38bdf8; box-shadow: 0 0 8px rgba(56,189,248,0.28);"
        elif is_pre:
            border_css = "border: 2px solid #f59e0b; box-shadow: 0 0 8px rgba(245,158,11,0.25);"
        else:
            border_css = "border: 1px solid #3b82f6;"

        tag_badge = ""
        if is_first:
            tag_badge = "<span style='background:#facc15; color:#000; font-size:11px; font-weight:900; padding:1px 5px; border-radius:4px; margin-left:4px;'>本月</span>"
        if r["month_num"] == 9:
            tag_badge += "<span style='background:#ef4444; color:#fff; font-size:11px; font-weight:900; padding:1px 5px; border-radius:4px; margin-left:4px;'>冲月</span>"
        elif r["month_num"] == 12:
            tag_badge += "<span style='background:#2563eb; color:#fff; font-size:11px; font-weight:900; padding:1px 5px; border-radius:4px; margin-left:4px;'>税假</span>"
        elif r["month_num"] == 3:
            tag_badge += "<span style='background:#ef4444; color:#fff; font-size:11px; font-weight:900; padding:1px 5px; border-radius:4px; margin-left:4px;'>税谷</span>"
        elif is_post_now:
            tag_badge += "<span style='background:#38bdf8; color:#000; font-size:11px; font-weight:900; padding:1px 5px; border-radius:4px; margin-left:4px;'>财报刚出</span>"
        elif is_pre:
            tag_badge += f"<span style='background:#f59e0b; color:#000; font-size:11px; font-weight:900; padding:1px 5px; border-radius:4px; margin-left:4px;'>前窗·{flow['short_tag']}</span>"
        elif r["is_earnings_month"]:
            tag_badge += "<span style='background:#38bdf8; color:#000; font-size:11px; font-weight:900; padding:1px 5px; border-radius:4px; margin-left:4px;'>财报月</span>"

        px_badge = f" <span style='color:#e2e8f0; font-size:12px;'>({r['approx_str']})</span>" if r["approx_str"] else ""

        cards_html += (
            f"<div style='background:#07193d; {border_css} border-radius:7px; padding:8px; color:#fff;'>"
            f"<div style='display:flex; justify-content:space-between; align-items:center;'>"
            f"<span style='font-size:14px; font-weight:900; color:#93c5fd;'>{r['short_title']}({r['y_ganzhi']}·{r['m_ganzhi']}){tag_badge}</span>"
            f"<span style='font-size:14.5px; font-weight:900; color:{r['badge_color']};'>{r['tech_score']:.0f}分{px_badge}</span>"
            f"</div>"
            f"<div style='font-size:12px; color:#facc15; font-weight:800; margin-top:2px;'>{r['rhythm_tag']} · {r['rhythm_desc']}</div>"
            f"<div style='font-size:11.5px; color:#cbd5e1; margin-top:2px;'>{r['factor_line']} | 实盘:{r['real_score']:.0f}</div>"
            f"<div style='font-size:12px; font-weight:800; color:#4ade80; border-top:1px solid #1e3a8a; margin-top:4px; padding-top:4px;'>"
            f"{r['stance']}｜{r['action_hint']}"
            f"</div>"
            f"</div>"
        )
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== TOP BAR & NAVIGATION ====================

active_natal = resolve_stock_natal_chart(st.session_state.selected_ticker)

top_bar_html = "<div class='top-bar'><div class='brand-title'>CAPITAL QUANT v2</div><div class='live-badge'>Auto-Sync Every 3m (180s) | " + datetime.now().strftime('%b %d, %Y %H:%M:%S') + " | 3/7 Macro-Natal Model</div></div>"
st.markdown(top_bar_html, unsafe_allow_html=True)

n1, n2, n3, n4 = st.columns([1.3, 1.3, 1.6, 2.2])
if n1.button("1. Market Watch", use_container_width=True):
    st.session_state.page = "Market Watch"
    st.rerun()
if n2.button("2. Stock Analysis", use_container_width=True):
    select_ticker_with_natal_first(st.session_state.selected_ticker, target_page="Stock Analysis")
    st.rerun()
if n3.button("3. Options Intelligence", use_container_width=True):
    select_ticker_with_natal_first(st.session_state.selected_ticker, target_page="Options Intelligence")
    st.rerun()
st.session_state.use_live_api = n4.toggle("启用行情接口", value=st.session_state.use_live_api)

st.markdown("<div style='border-bottom: 1px solid #1e3a8a; margin: 4px 0 6px 0;'></div>", unsafe_allow_html=True)

# ==================== PAGE 1: MARKET WATCH ====================
@st.fragment(run_every=180)
def render_native_market_watch():
    c1, c2, c3, c4 = st.columns([2.0, 2.2, 1.2, 1.3])
    c1.markdown("### Market Watch")
    new_t = c2.text_input("Add", placeholder="输入任意代码 (美股如 PLTR, 英股如 BP.L)", label_visibility="collapsed").strip().upper()
    if c3.button("ADD TICKER", use_container_width=True) and new_t:
        if new_t not in st.session_state.tickers:
            select_ticker_with_natal_first(new_t)
            st.success(f"已先定命盘并添加: {new_t}")
            st.rerun()
        else:
            st.warning("该代码已存在自选列表中！")
    if c4.button("MANUAL REFRESH", use_container_width=True):
        st.cache_data.clear()
        st.session_state["opt_persistent_cache"] = {}
        st.session_state["stock_natal_registry"] = {}
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
        rows.append({
            "COMPANY CODE": sym,
            "SRC": d.get("src", ""),
            "TODAY PRICE": d["price"],
            "YESTERDAY PRICE": d["prev"],
            "CHANGE": chg,
            "% CHANGE": pct,
            "MA20": d["ma20"],
            "MA50": d["ma50"],
            "MA200": d["ma200"],
            "PE RATE": str(d['pe']) if d['pe'] else "None",
            "YEARLY HIGH": d["high52"],
            "YEARLY LOW": d["low52"],
            "RSI (14)": d["rsi"]
        })

    df_watch = pd.DataFrame(rows)
    def style_watch(val, col):
        base = "background-color: #07193d; font-size: 18px; font-weight: 700;"
        if col in ["CHANGE", "% CHANGE"]:
            color_str = "#4ade80" if val > 0 else ("#f87171" if val < 0 else "#fff")
            return base + " color: " + color_str + ";"
        if col == "RSI (14)":
            bg_col = "#dc2626" if val >= 70 else ("#eab308" if val <= 40 else "#16a34a")
            fg_col = "#000" if val <= 40 else "#fff"
            return "background-color: " + bg_col + "; color: " + fg_col + "; font-size: 18px; font-weight: 800;"
        if col == "COMPANY CODE":
            return base + " color: #60a5fa; font-weight: 900;"
        if col == "SRC":
            c_src = "#4ade80" if val == "NQ" else ("#38bdf8" if val == "YH" else "#f87171")
            return base + " color: " + c_src + "; font-size: 14px;"
        if col == "TODAY PRICE":
            return base + " color: #facc15; font-weight: 800;"
        return base + " color: #fff;"

    fmt = {"TODAY PRICE": "{:.2f}", "YESTERDAY PRICE": "{:.2f}", "CHANGE": "{:+.2f}", "% CHANGE": "{:+.2f}%", "MA20": "{:.2f}", "MA50": "{:.2f}", "MA200": "{:.2f}", "YEARLY HIGH": "{:.2f}", "YEARLY LOW": "{:.2f}", "RSI (14)": "{:.1f}"}
    styled_df = df_watch.style.apply(lambda c: [style_watch(v, c.name) for v in c], axis=0).format(fmt)

    full_table_height = (len(df_watch) + 1) * 42 + 12
    event = st.dataframe(styled_df, use_container_width=True, height=full_table_height, row_height=42, hide_index=True, on_select="rerun", selection_mode="single-row")

    if event and event.selection and "rows" in event.selection and len(event.selection.rows) > 0:
        selected_idx = event.selection.rows[0]
        if selected_idx < len(df_watch):
            picked_sym = df_watch.iloc[selected_idx]["COMPANY CODE"]
            select_ticker_with_natal_first(picked_sym, target_page="Stock Analysis")
            st.rerun()

    b1, b2, b3 = st.columns([2.4, 2.2, 2.4])
    if b1.button("OPEN COMPANY ANALYSIS (" + st.session_state.selected_ticker + ") >", use_container_width=True):
        select_ticker_with_natal_first(st.session_state.selected_ticker, target_page="Stock Analysis")
        st.rerun()
    del_sym = b2.selectbox("移除", ["选择要删除的代码..."] + st.session_state.tickers, label_visibility="collapsed")
    if del_sym != "选择要删除的代码...":
        st.session_state.tickers.remove(del_sym)
        sync_watchlist_to_url()
        st.rerun()
    summary_html = "<div style='text-align:right; padding-top:4px; font-size:17px; font-weight:800;'><span style='color:#4ade80;'>▲ " + str(gainers) + " Gainers</span> | <span style='color:#f87171;'>● " + str(losers) + " Losers</span> | Total: " + str(len(df_watch)) + "</div>"
    b3.markdown(summary_html, unsafe_allow_html=True)

if st.session_state.page == "Market Watch":
    render_native_market_watch()

# ==================== PAGE 2: STOCK ANALYSIS ====================
elif st.session_state.page == "Stock Analysis":
    t1, t2, t3, t4 = st.columns([2.0, 2.4, 2.2, 1.2])
    t1.markdown("### Stock Analysis")
    idx = st.session_state.tickers.index(st.session_state.selected_ticker) if st.session_state.selected_ticker in st.session_state.tickers else 0
    chosen = t2.selectbox("标的", st.session_state.tickers, index=idx, label_visibility="collapsed")
    if chosen != st.session_state.selected_ticker:
        select_ticker_with_natal_first(chosen)
        st.rerun()
    if t3.button("OPTIONS INTELLIGENCE V2.0 >", use_container_width=True):
        select_ticker_with_natal_first(st.session_state.selected_ticker, target_page="Options Intelligence")
        st.rerun()
    if t4.button("← BACK", use_container_width=True):
        st.session_state.page = "Market Watch"
        st.rerun()

    sym = select_ticker_with_natal_first(st.session_state.selected_ticker)["symbol"]
    m = fetch_stock_metrics(sym, live=st.session_state.use_live_api)
    cur_price = float(m["price"])

    col_c, col_l = st.columns([2.5, 1.1])
    with col_c:
        card_title_html = "<div class='card-header'>" + sym + " — " + m.get('name', sym) + " | Price Chart (" + m.get('src', '') + ")</div>"
        st.markdown(card_title_html, unsafe_allow_html=True)

        active_p = st.session_state.chart_period
        periods = ["1日", "1星期", "1个月", "3个月", "6个月", "1年", "全部"]

        style_overrides = "<style>"
        for p in periods:
            if p == active_p:
                style_overrides += f"div[data-testid='stButton'] > button[kind='secondary']:has(p:contains('{p}')) {{ background: linear-gradient(180deg, #facc15, #eab308) !important; color: #000 !important; border: 1px solid #fef08a !important; font-weight: 900 !important; }}"
        style_overrides += "</style>"
        st.markdown(style_overrides, unsafe_allow_html=True)

        p_cols = st.columns(len(periods) + 1)
        for i, p in enumerate(periods):
            if p_cols[i].button(p, use_container_width=True, key="p_" + p):
                st.session_state.chart_period = p
                st.rerun()

        st.session_state.show_walls = p_cols[-1].toggle("真实期权墙 (Wall)", value=st.session_state.show_walls)

        hdf = fetch_history_df(sym, st.session_state.chart_period, cur_price)

        real_call_wall = None
        real_put_wall = None
        if st.session_state.show_walls and st.session_state.use_live_api:
            _, opt_cdf, opt_pdf = fetch_real_option_chain_for_date(sym, spot=cur_price)
            _, real_call_wall, _, real_put_wall = extract_top3_walls(opt_cdf, opt_pdf, cur_price)

        if st.session_state.show_walls:
            if real_call_wall is not None and real_put_wall is not None:
                call_wall_series = pd.Series([float(real_call_wall)] * len(hdf), index=hdf.index)
                put_wall_series = pd.Series([float(real_put_wall)] * len(hdf), index=hdf.index)
                wall_source_tag = "多源真实期权墙"
            else:
                rolling_mid = hdf['Close'].rolling(window=5, min_periods=1).mean()
                call_wall_series = rolling_mid * 1.07
                put_wall_series = rolling_mid * 0.93
                wall_source_tag = "均线±7%参考"
            c_min = min(hdf["Close"].min(), put_wall_series.min())
            c_max = max(hdf["Close"].max(), call_wall_series.max())
        else:
            call_wall_series = None
            put_wall_series = None
            wall_source_tag = ""
            c_min = hdf["Close"].min()
            c_max = hdf["Close"].max()

        margin = (c_max - c_min) * 0.08 if c_max != c_min else c_min * 0.01
        y_min = c_min - margin
        y_max = c_max + margin

        fig = go.Figure(go.Scatter(x=hdf["Date"], y=hdf["Close"], mode="lines", line=dict(color="#0284c7", width=2.5), showlegend=False))

        if st.session_state.show_walls and call_wall_series is not None and put_wall_series is not None:
            latest_call_val = float(call_wall_series.iloc[-1])
            latest_put_val = float(put_wall_series.iloc[-1])

            fig.add_trace(go.Scatter(
                x=hdf["Date"], y=call_wall_series, mode='lines',
                name=f"CALL Wall: ${latest_call_val:.2f}",
                line=dict(color='#16a34a', width=2, dash='dash')
            ))
            fig.add_annotation(
                x=hdf["Date"].iloc[-1], y=latest_call_val,
                text=f" 🟢 CALL Wall ({wall_source_tag}): ${latest_call_val:.2f} ",
                showarrow=False, xanchor="left", yanchor="middle",
                font=dict(color="#16a34a", size=12, family="sans-serif")
            )

            fig.add_trace(go.Scatter(
                x=hdf["Date"], y=put_wall_series, mode='lines',
                name=f"PUT Wall: ${latest_put_val:.2f}",
                line=dict(color='#dc2626', width=2, dash='dash'),
                fill='tonexty', fillcolor='rgba(22, 163, 74, 0.04)'
            ))
            fig.add_annotation(
                x=hdf["Date"].iloc[-1], y=latest_put_val,
                text=f" 🔴 PUT Wall ({wall_source_tag}): ${latest_put_val:.2f} ",
                showarrow=False, xanchor="left", yanchor="middle",
                font=dict(color="#dc2626", size=12, family="sans-serif")
            )

        fig.add_hline(
            y=cur_price,
            line_dash="dash",
            line_color="#64748b",
            line_width=2,
            annotation_text=f" {cur_price:.2f} ",
            annotation_position="right",
            annotation_font=dict(color="#fff", size=14),
            annotation_bgcolor="#334155"
        )

        fig.update_layout(
            template="plotly_white", paper_bgcolor="#fff", plot_bgcolor="#fff",
            xaxis_rangeslider_visible=False, height=390,
            font=dict(size=15, color="#1e293b"),
            margin=dict(l=10, r=175, t=10, b=10), showlegend=False
        )
        fig.update_yaxes(side="right", gridcolor="#e2e8f0", range=[y_min, y_max])
        st.plotly_chart(fig, width="stretch")

    with col_l:
        st.markdown("<div class='card-header'>PRICE LEVEL LADDER</div>", unsafe_allow_html=True)
        rows_html = ""
        for pct in [20, 15, 12, 10, 8, 6, 0, -6, -8, -10, -12, -15, -18, -20]:
            lbl = "CURRENT" if pct == 0 else (("+" + str(pct)) if pct > 0 else str(pct)) + "%"
            tp = round(cur_price * (1 + pct / 100.0), 2)
            bg = "#eab308" if pct == 0 else "#07193d"
            fg = "#000" if pct == 0 else ("#4ade80" if pct > 0 else "#f87171")
            fw = "900" if pct == 0 else "700"
            rows_html += "<tr style='background:" + bg + ";border-bottom:1px solid #1e3a8a;'><td style='padding:7px 8px;color:" + fg + ";font-weight:" + fw + ";font-size:13px;'>" + lbl + "</td><td style='padding:7px 8px;color:" + fg + ";font-weight:" + fw + ";font-size:13px;text-align:right;'>" + f"{tp:.2f}" + "</td></tr>"

        html_box = "<div style='background:#061430;border:1px solid #2563eb;border-radius:8px;height:480px;overflow-y:auto;padding:3px;'><table style='width:100%;border-collapse:collapse;font-family:sans-serif;'><thead><tr style='border-bottom:2px solid #1e3a8a;color:#93c5fd;font-size:13px;position:sticky;top:0;background:#061430;'><th style='padding:6px 8px;text-align:left;'>LEVEL</th><th style='padding:6px 8px;text-align:right;'>TARGET PRICE</th></tr></thead><tbody>" + rows_html + "</tbody></table></div>"
        st.components.v1.html(html_box, height=495)

    prev_val = float(m["prev"])
    chg = round(cur_price - prev_val, 2)
    pct_c = round((chg / prev_val) * 100, 2) if prev_val else 0.0
    cc = "#4ade80" if chg >= 0 else "#f87171"
    k1, k2, k3, k4, k5, k6 = st.columns(6)

    k1.markdown("<div class='metric-box'><div class='metric-label'>Current Price</div><div class='metric-val'>" + f"{cur_price:.2f}" + " <span style='font-size:17px;color:" + cc + ";'>(" + f"{pct_c:+.2f}" + "%)</span></div></div>", unsafe_allow_html=True)
    k2.markdown("<div class='metric-box'><div class='metric-label'>52W High</div><div class='metric-val'>" + f"{float(m.get('high52', cur_price)):.2f}" + "</div></div>", unsafe_allow_html=True)
    k3.markdown("<div class='metric-box'><div class='metric-label'>52W Low</div><div class='metric-val'>" + f"{float(m.get('low52', cur_price)):.2f}" + "</div></div>", unsafe_allow_html=True)
    k4.markdown("<div class='metric-box'><div class='metric-label'>Market Cap</div><div class='metric-val'>" + str(m.get('mcap', 'N/A')) + "</div></div>", unsafe_allow_html=True)
    k5.markdown("<div class='metric-box'><div class='metric-label'>P/E / EPS</div><div class='metric-val'>" + (str(m.get('pe', 'N/A')) if m.get('pe') else 'N/A') + " / " + str(m.get('eps', 'N/A')) + "</div></div>", unsafe_allow_html=True)
    k6.markdown("<div class='metric-box'><div class='metric-label'>RSI (14)</div><div class='metric-val' style='color:#38bdf8;'>" + f"{float(m.get('rsi', 50.0)):.1f}" + "</div></div>", unsafe_allow_html=True)

# ==================== PAGE 3: OPTIONS INTELLIGENCE ====================
elif st.session_state.page == "Options Intelligence":
    o1, o2, o3, o4 = st.columns([2.3, 2.1, 1.5, 1.5])
    o1.markdown("### CAPITAL QUANT — OPTIONS INTELLIGENCE V2.0")
    idx = st.session_state.tickers.index(st.session_state.selected_ticker) if st.session_state.selected_ticker in st.session_state.tickers else 0
    chosen_o = o2.selectbox("期权标的", st.session_state.tickers, index=idx, label_visibility="collapsed")
    if chosen_o != st.session_state.selected_ticker:
        select_ticker_with_natal_first(chosen_o)
        st.rerun()
    if o3.button("← Stock Analysis", use_container_width=True):
        select_ticker_with_natal_first(st.session_state.selected_ticker, target_page="Stock Analysis")
        st.rerun()
    if o4.button("Market Watch", use_container_width=True):
        st.session_state.page = "Market Watch"
        st.rerun()

    sym = select_ticker_with_natal_first(st.session_state.selected_ticker)["symbol"]
    m_opt = fetch_stock_metrics(sym, live=st.session_state.use_live_api)
    spot = float(m_opt["price"])
    _, cdf, pdf = fetch_real_option_chain_for_date(sym, spot=spot)

    render_12m_cycle_block_above_options(sym, m_data=m_opt, cdf=cdf, pdf=pdf)

    matrix_html = build_custom_option_matrix_html(sym, spot)
    st.components.v1.html(matrix_html, height=665, scrolling=False)

    st.markdown("<div class='module-container'>", unsafe_allow_html=True)
    hdr_c1, hdr_c2 = st.columns([4.5, 1.5])
    hdr_c1.markdown("<div class='card-header'>📊 多源期权库真实核心行权价明细 (Call vs Put 权利金与未平仓对比 | 现价 ±30% 波段全覆盖)</div>", unsafe_allow_html=True)
    st.session_state.show_all_strikes = hdr_c2.toggle("显示全链所有行权价", value=st.session_state.show_all_strikes)

    has_real_chain = _is_valid_chain_pair(cdf, pdf)
    if has_real_chain:
        cdf_unique = cdf.sort_values("openInterest", ascending=False).drop_duplicates(subset=["strike"]).copy()
        pdf_unique = pdf.sort_values("openInterest", ascending=False).drop_duplicates(subset=["strike"]).copy()
        coi = safe_col_sum(cdf_unique, "openInterest")
        poi = safe_col_sum(pdf_unique, "openInterest")
        cvol = safe_col_sum(cdf_unique, "volume")
        pvol = safe_col_sum(pdf_unique, "volume")
        pcr = round(poi / coi, 2) if coi > 0 else 0.0
    else:
        cdf_unique, pdf_unique = pd.DataFrame(), pd.DataFrame()
        coi, poi, cvol, pvol, pcr = 0, 0, 0, 0, 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.markdown("<div class='metric-box'><div class='metric-label'>Call / Put Volume</div><div class='metric-val'>" + (f"{cvol:,} / {pvol:,}" if has_real_chain else "N/A") + "</div></div>", unsafe_allow_html=True)
    m2.markdown("<div class='metric-box'><div class='metric-label'>Put / Call OI Ratio</div><div class='metric-val' style='color:#facc15;'>" + (f"{pcr:.2f}" if (has_real_chain and coi > 0) else "N/A") + "</div></div>", unsafe_allow_html=True)
    m3.markdown("<div class='metric-box'><div class='metric-label'>Spot Price (现价)</div><div class='metric-val' style='color:#38bdf8;'>" + f"${spot:.2f}" + "</div></div>", unsafe_allow_html=True)
    m4.markdown("<div class='metric-box'><div class='metric-label'>数据来源状态</div><div class='metric-val' style='color:#4ade80;'>" + ("多源链已接入" if has_real_chain else "待期权链返回") + "</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if has_real_chain:
        cf = cdf_unique.set_index("strike")
        pf = pdf_unique.set_index("strike")
        common_strikes = sorted(list(set(cf.index).intersection(set(pf.index))))

        if st.session_state.show_all_strikes:
            strikes = common_strikes
        else:
            band_strikes = [k for k in common_strikes if spot * 0.70 <= k <= spot * 1.30]
            if not band_strikes:
                band_strikes = common_strikes
            if len(band_strikes) > 45:
                scored = sorted(
                    band_strikes,
                    key=lambda k: int(cf.loc[k].get("openInterest", 0)) + int(pf.loc[k].get("openInterest", 0)),
                    reverse=True
                )
                strikes = sorted(scored[:45])
            else:
                strikes = band_strikes

        s_rows = []
        for k in strikes:
            cr = cf.loc[k]
            pr = pf.loc[k]
            s_rows.append({
                "CALL OI": f"{int(cr.get('openInterest', 0)):,}",
                "CALL 权利金": f"${float(cr.get('lastPrice', 0.0)):.2f}",
                "STRIKE 行权价": f"${float(k):.2f}",
                "PUT 权利金": f"${float(pr.get('lastPrice', 0.0)):.2f}",
                "PUT OI": f"{int(pr.get('openInterest', 0)):,}"
            })
        if s_rows:
            dfs = pd.DataFrame(s_rows)
            st.markdown("""
            <style>
                table.table-white { width: 100%; background-color: #ffffff !important; color: #0f172a !important; border-collapse: collapse; font-family: sans-serif; border-radius: 6px; overflow: hidden; }
                table.table-white th { background-color: #f1f5f9 !important; color: #1e293b !important; font-weight: 900; padding: 9px 12px; border-bottom: 2px solid #cbd5e1; text-align: center; font-size: 16px; }
                table.table-white td { background-color: #ffffff !important; color: #0f172a !important; padding: 8px 12px; border-bottom: 1px solid #e2e8f0; font-size: 16px; font-weight: 800; text-align: center; }
                table.table-white tr:hover td { background-color: #f8fafc !important; }
            </style>
            """, unsafe_allow_html=True)
            st.markdown(dfs.to_html(index=False, classes="table-white"), unsafe_allow_html=True)
        else:
            st.info("期权库当前未返回匹配行权价明细，未使用预设模拟价格。")
    else:
        st.info("当前暂未返回真实期权链数据（未启用任何预设模拟价格）。")
    st.markdown("</div>", unsafe_allow_html=True)
