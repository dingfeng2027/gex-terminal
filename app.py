import hmac
import os
import time
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

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

def _get_app_password() -> str:
    pwd = os.getenv("APP_ACCESS_PASSWORD", "")
    try:
        if "APP_ACCESS_PASSWORD" in st.secrets and str(st.secrets["APP_ACCESS_PASSWORD"]).strip():
            pwd = str(st.secrets["APP_ACCESS_PASSWORD"])
    except Exception:
        pass
    return pwd.strip()

def _require_owner_access() -> None:
    expected = _get_app_password()
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
    "NVDA": {"name": "NVIDIA", "price": 156.14, "prev": 162.85, "pe": 22.4, "mcap": "3.77T"},
    "GOOGL": {"name": "Alphabet", "price": 288.93, "prev": 284.78, "pe": 15.1, "mcap": "3.54T"},
    "TSM": {"name": "TSMC", "price": 391.23, "prev": 375.44, "pe": 25.4, "mcap": "2.02T"},
    "AMD": {"name": "AMD", "price": 509.52, "prev": 499.04, "pe": 108.8, "mcap": "825B"},
    "MSFT": {"name": "Microsoft", "price": 546.89, "prev": 530.61, "pe": 28.5, "mcap": "4.06T"},
    "META": {"name": "Meta", "price": 644.30, "prev": 610.15, "pe": 22.0, "mcap": "1.63T"},
    "AMZN": {"name": "Amazon", "price": 268.44, "prev": 259.30, "pe": 21.7, "mcap": "2.81T"},
    "AAPL": {"name": "Apple", "price": 351.39, "prev": 342.37, "pe": 39.1, "mcap": "5.31T"},
    "ASML": {"name": "ASML", "price": 1517.98, "prev": 1424.75, "pe": 37.3, "mcap": "605B"},
    "TSLA": {"name": "Tesla", "price": 381.01, "prev": 358.22, "pe": 418.7, "mcap": "1.21T"},
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

if "opt_local_store" not in st.session_state:
    st.session_state["opt_local_store"] = {}

def sync_watchlist_to_url():
    st.query_params["watchlist"] = ",".join(st.session_state.tickers)

def safe_col_sum(df, col_name):
    if df is None or df.empty or col_name not in df.columns:
        return 0
    return int(pd.to_numeric(df[col_name], errors="coerce").fillna(0).sum())

def get_marketdata_token() -> str:
    token = os.getenv("MARKETDATA_API_TOKEN", "")
    try:
        if "MARKETDATA_API_TOKEN" in st.secrets and str(st.secrets["MARKETDATA_API_TOKEN"]).strip():
            token = str(st.secrets["MARKETDATA_API_TOKEN"])
    except Exception:
        pass
    return token.strip()

def get_nasdaq_credentials():
    api_key = os.getenv("NASDAQ_API_KEY", "")
    bearer = os.getenv("NASDAQ_BEARER_TOKEN", "")
    try:
        if "NASDAQ_API_KEY" in st.secrets and str(st.secrets["NASDAQ_API_KEY"]).strip():
            api_key = str(st.secrets["NASDAQ_API_KEY"])
        if "NASDAQ_BEARER_TOKEN" in st.secrets and str(st.secrets["NASDAQ_BEARER_TOKEN"]).strip():
            bearer = str(st.secrets["NASDAQ_BEARER_TOKEN"])
    except Exception:
        pass
    return api_key.strip(), bearer.strip()

def _build_nasdaq_headers():
    api_key, bearer = get_nasdaq_credentials()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.nasdaq.com/"
    }
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    elif api_key:
        headers["X-Api-Key"] = api_key
    return api_key, bearer, headers

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

def _query_yahoo_chart_payload(symbol, range_str="1y", interval_str="1d"):
    hosts = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]
    headers_list = [
        {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"},
        {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15"}
    ]
    for idx, host in enumerate(hosts):
        url = f"https://{host}/v8/finance/chart/{symbol}?interval={interval_str}&range={range_str}"
        headers = headers_list[idx % len(headers_list)]
        try:
            res = requests.get(url, headers=headers, timeout=2.5)
            if res.status_code == 200:
                data = res.json()
                result = data.get("chart", {}).get("result", [])
                if result:
                    return result[0]
        except Exception:
            continue
    return None

def _query_nasdaq_stock_data(symbol):
    if "." in symbol:
        return None
    clean_sym = symbol.upper()
    _, _, headers = _build_nasdaq_headers()

    asset_classes = ["etf", "stocks"] if clean_sym in ["QQQ", "SPY", "IWM", "DIA", "TLT"] else ["stocks", "etf"]
    info_data = None

    for ac in asset_classes:
        try:
            url_info = f"https://api.nasdaq.com/api/quote/{clean_sym}/info?assetclass={ac}"
            res = requests.get(url_info, headers=headers, timeout=2.5)
            if res.status_code == 200:
                d = res.json().get("data")
                if isinstance(d, dict) and d.get("primaryData"):
                    info_data = (ac, d)
                    break
        except Exception:
            continue

    if not info_data:
        return None

    ac, d = info_data
    pdata = d.get("primaryData", {})
    key_stats = d.get("keyStats", {}) if isinstance(d.get("keyStats"), dict) else {}

    last_price = _parse_float_clean(pdata.get("lastSalePrice"))
    net_chg = _parse_float_clean(pdata.get("netChange"))
    if last_price is None:
        return None

    prev_price = round(last_price - net_chg, 4) if net_chg is not None else last_price
    short_name = d.get("companyName") or clean_sym

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

    closes = []
    try:
        to_dt = datetime.today().strftime("%Y-%m-%d")
        from_dt = (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")
        url_hist = f"https://api.nasdaq.com/api/quote/{clean_sym}/historical?assetclass={ac}&fromdate={from_dt}&limit=300&todate={to_dt}"
        h_res = requests.get(url_hist, headers=headers, timeout=3.0)
        if h_res.status_code == 200:
            rows = h_res.json().get("data", {}).get("tradesTable", {}).get("rows", [])
            if isinstance(rows, list) and rows:
                for r in reversed(rows):
                    c_val = _parse_float_clean(r.get("close"))
                    if c_val is not None:
                        closes.append(c_val)
    except Exception:
        pass

    if not closes:
        closes = [prev_price, last_price]
    else:
        closes.append(last_price)

    return {
        "name": short_name,
        "price": last_price,
        "prev": prev_price,
        "closes": closes,
        "high52": high52,
        "low52": low52,
        "mcap": mcap
    }

def _calc_indicators_from_closes(closes, last_price, prev_price, high52=None, low52=None):
    ma20 = sum(closes[-20:]) / min(20, len(closes))
    ma50 = sum(closes[-50:]) / min(50, len(closes))
    ma200 = sum(closes[-200:]) / min(200, len(closes))

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
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        elif avg_gain > 0:
            rsi = 100.0

    return {
        "price": round(float(last_price), 2),
        "prev": round(float(prev_price), 2),
        "ma20": round(float(ma20), 2),
        "ma50": round(float(ma50), 2),
        "ma200": round(float(ma200), 2),
        "high52": round(float(h52), 2),
        "low52": round(float(l52), 2),
        "rsi": round(float(rsi), 1)
    }

@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock_metrics(symbol, live=True):
    fb = FALLBACK_DATA.get(symbol, {"name": symbol, "price": 150.0, "prev": 148.0, "pe": 25.0, "mcap": "100B"})
    if not live:
        return {
            "name": fb["name"], "price": fb["price"], "prev": fb["prev"],
            "ma20": fb["price"] * 0.98, "ma50": fb["price"] * 0.95, "ma200": fb["price"] * 0.88,
            "high52": fb["price"] * 1.15, "low52": fb["price"] * 0.80, "rsi": 55.0,
            "pe": fb.get("pe"), "eps": 5.0, "mcap": fb.get("mcap", "100B")
        }

    nasdaq_res = _query_nasdaq_stock_data(symbol)
    if nasdaq_res:
        calc = _calc_indicators_from_closes(
            nasdaq_res["closes"],
            nasdaq_res["price"],
            nasdaq_res["prev"],
            nasdaq_res.get("high52"),
            nasdaq_res.get("low52")
        )
        calc.update({
            "name": nasdaq_res["name"],
            "pe": fb.get("pe", 25.0),
            "eps": 5.0,
            "mcap": nasdaq_res.get("mcap") or fb.get("mcap", "100B")
        })
        return calc

    result_item = _query_yahoo_chart_payload(symbol, range_str="1y", interval_str="1d")
    if result_item:
        try:
            meta = result_item.get("meta", {})
            indicators = result_item.get("indicators", {}).get("quote", [{}])[0]
            closes = [c for c in indicators.get("close", []) if c is not None]
            highs = [h for h in indicators.get("high", []) if h is not None]
            lows = [l for l in indicators.get("low", []) if l is not None]

            meta_price = meta.get("regularMarketPrice")
            meta_prev = meta.get("chartPreviousClose") or meta.get("previousClose")

            if len(closes) >= 2:
                last_price = float(meta_price) if meta_price is not None else float(closes[-1])
                prev_price = float(meta_prev) if meta_prev is not None else float(closes[-2])
                high52 = max(highs) if highs else None
                low52 = min(lows) if lows else None
                short_name = meta.get("shortName") or meta.get("longName") or fb.get("name", symbol)

                calc = _calc_indicators_from_closes(closes, last_price, prev_price, high52, low52)
                calc.update({
                    "name": short_name,
                    "pe": fb.get("pe", 25.0),
                    "eps": 5.0,
                    "mcap": fb.get("mcap", "100B")
                })
                return calc
        except Exception:
            pass

    p = fb["price"]
    prev = fb["prev"]
    return {
        "name": fb["name"], "price": p, "prev": prev,
        "ma20": p * 0.98, "ma50": p * 0.95, "ma200": p * 0.88,
        "high52": p * 1.15, "low52": p * 0.80, "rsi": 55.0,
        "pe": fb.get("pe"), "eps": 5.0, "mcap": fb.get("mcap", "100B")
    }

@st.cache_data(ttl=300, show_spinner=False)
def fetch_history_df(symbol, period_str, current_price):
    pmap = {"1日": "1d", "1星期": "5d", "1个月": "1mo", "3个月": "3mo", "6个月": "6mo", "1年": "1y", "全部": "max"}
    yfp = pmap.get(period_str, "6mo")
    range_map = {"1d": "1d", "5d": "5d", "1mo": "1mo", "3mo": "3mo", "6mo": "6mo", "1y": "1y", "max": "max"}
    r = range_map.get(yfp, "6mo")
    interval_str = "5m" if r == "1d" else "1d"

    if "." not in symbol:
        clean_sym = symbol.upper()
        days_back = {"1d": 5, "5d": 10, "1mo": 32, "3mo": 95, "6mo": 185, "1y": 365, "max": 1825}.get(yfp, 185)
        to_dt = datetime.today().strftime("%Y-%m-%d")
        from_dt = (datetime.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        _, _, headers = _build_nasdaq_headers()
        ac = "etf" if clean_sym in ["QQQ", "SPY", "IWM", "DIA", "TLT"] else "stocks"
        try:
            url_hist = f"https://api.nasdaq.com/api/quote/{clean_sym}/historical?assetclass={ac}&fromdate={from_dt}&limit=1500&todate={to_dt}"
            h_res = requests.get(url_hist, headers=headers, timeout=3.0)
            if h_res.status_code == 200:
                rows = h_res.json().get("data", {}).get("tradesTable", {}).get("rows", [])
                if isinstance(rows, list) and rows:
                    records = []
                    for row in reversed(rows):
                        c_val = _parse_float_clean(row.get("close"))
                        d_str = str(row.get("date", "")).strip()
                        if c_val is not None and d_str:
                            try:
                                dt_parsed = datetime.strptime(d_str, "%m/%d/%Y")
                                records.append((dt_parsed, c_val))
                            except Exception:
                                continue
                    if records:
                        dates, prices = zip(*records)
                        return pd.DataFrame({"Date": list(dates), "Close": list(prices)})
        except Exception:
            pass

    result_item = _query_yahoo_chart_payload(symbol, range_str=r, interval_str=interval_str)
    if result_item:
        try:
            timestamps = result_item.get("timestamp", [])
            quotes = result_item.get("indicators", {}).get("quote", [{}])[0]
            closes = quotes.get("close", [])
            if timestamps and closes:
                valid_data = [(datetime.fromtimestamp(ts), c) for ts, c in zip(timestamps, closes) if c is not None]
                if valid_data:
                    dates, prices = zip(*valid_data)
                    return pd.DataFrame({"Date": list(dates), "Close": list(prices)})
        except Exception:
            pass

    ndays = {"1d": 2, "5d": 7, "1mo": 21, "3mo": 63, "6mo": 120}.get(yfp, 250)
    np.random.seed(abs(hash(symbol + period_str)) % 10000)
    dates = pd.date_range(end=datetime.today(), periods=ndays, freq="B")
    prices = current_price * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, size=len(dates))))
    return pd.DataFrame({"Date": dates, "Close": prices * (current_price / prices[-1])})

def _marketdata_get(path: str, params: dict[str, Any] | None = None, max_retries: int = 2) -> tuple[int, dict[str, Any]]:
    token = get_marketdata_token()
    if not token:
        return 0, {}
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    url = f"https://api.marketdata.app/v1{path}"
    last_resp = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, params=params or {}, timeout=12)
            last_resp = resp
            if resp.status_code != 429:
                break
            if attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))
        except Exception:
            return 0, {}
    if last_resp is None:
        return 0, {}
    try:
        data = last_resp.json()
    except Exception:
        data = {}
    return last_resp.status_code, data

@st.cache_data(ttl=300, show_spinner=False)
def _query_marketdata_expirations(symbol: str) -> list[int]:
    if not get_marketdata_token() or "." in symbol:
        return []
    clean_sym = symbol.upper().strip()
    status_exp, exp_payload = _marketdata_get(f"/options/expirations/{clean_sym}/")
    exp_timestamps: list[int] = []
    if status_exp == 200 and exp_payload.get("s") == "ok":
        for d_str in sorted({str(x) for x in (exp_payload.get("expirations") or []) if x}):
            try:
                dt_obj = datetime.strptime(d_str[:10], "%Y-%m-%d").replace(hour=16, minute=0, second=0)
                exp_timestamps.append(int(dt_obj.timestamp()))
            except Exception:
                continue
    return exp_timestamps

@st.cache_data(ttl=300, show_spinner=False)
def _query_marketdata_single_chain(symbol: str, target_exp_str: str, spot: float | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not get_marketdata_token() or "." in symbol or not target_exp_str:
        return pd.DataFrame(), pd.DataFrame()
    clean_sym = symbol.upper().strip()
    params: dict[str, Any] = {"expiration": target_exp_str}
    if spot and spot > 0:
        params["strike"] = f"{round(spot * 0.70, 2)}-{round(spot * 1.30, 2)}"

    status_chain, chain_payload = _marketdata_get(f"/options/chain/{clean_sym}/", params=params)
    if status_chain != 200 or chain_payload.get("s") != "ok":
        return pd.DataFrame(), pd.DataFrame()

    strikes = chain_payload.get("strike") or []
    sides = chain_payload.get("side") or []
    lasts = chain_payload.get("last") or []
    bids = chain_payload.get("bid") or []
    asks = chain_payload.get("ask") or []
    ois = chain_payload.get("openInterest") or []
    vols = chain_payload.get("volume") or []

    c_rows, p_rows = [], []
    for i in range(len(strikes)):
        k = strikes[i]
        if k is None:
            continue
        side = str(sides[i] if i < len(sides) else "").lower()
        last_v = lasts[i] if i < len(lasts) else None
        bid_v = bids[i] if i < len(bids) else None
        ask_v = asks[i] if i < len(asks) else None
        price_v = float(last_v) if last_v is not None else (
            round((float(bid_v) + float(ask_v)) / 2, 2) if (bid_v is not None and ask_v is not None) else 0.0
        )
        rec = {
            "strike": float(k),
            "lastPrice": price_v,
            "openInterest": int(ois[i]) if i < len(ois) and ois[i] is not None else 0,
            "volume": int(vols[i]) if i < len(vols) and vols[i] is not None else 0,
        }
        if side == "call":
            c_rows.append(rec)
        elif side == "put":
            p_rows.append(rec)

    if c_rows and p_rows:
        return pd.DataFrame(c_rows), pd.DataFrame(p_rows)
    return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def _query_yahoo_options_api(symbol, target_dt_timestamp=None):
    headers_list = [
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Accept': 'application/json,text/plain,*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': f'https://finance.yahoo.com/quote/{symbol}/options/'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15',
            'Accept': 'application/json,text/plain,*/*',
            'Accept-Language': 'en-US,en;q=0.9'
        }
    ]
    hosts = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]

    for attempt in range(2):
        host = hosts[attempt % len(hosts)]
        headers = headers_list[attempt % len(headers_list)]
        url = f"https://{host}/v7/finance/options/{symbol}"
        if target_dt_timestamp:
            url += f"?date={target_dt_timestamp}"
        try:
            res = requests.get(url, headers=headers, timeout=2.5)
            if res.status_code == 200:
                data = res.json()
                result = data.get('optionChain', {}).get('result', [])
                if result:
                    r_opt = result[0]
                    exp_dates = sorted([int(x) for x in r_opt.get('expirationDates', []) if x])
                    options_data = r_opt.get('options', [])
                    if options_data:
                        calls = options_data[0].get('calls', [])
                        puts = options_data[0].get('puts', [])

                        cdf = pd.DataFrame([{
                            "strike": float(c.get("strike")),
                            "lastPrice": float(c.get("lastPrice") or 0.0),
                            "openInterest": int(c.get("openInterest") or 0),
                            "volume": int(c.get("volume") or 0)
                        } for c in calls if c.get("strike") is not None])

                        pdf = pd.DataFrame([{
                            "strike": float(p.get("strike")),
                            "lastPrice": float(p.get("lastPrice") or 0.0),
                            "openInterest": int(p.get("openInterest") or 0),
                            "volume": int(p.get("volume") or 0)
                        } for p in puts if p.get("strike") is not None])

                        if not cdf.empty and not pdf.empty:
                            return exp_dates, cdf, pdf
        except Exception:
            continue
    return [], pd.DataFrame(), pd.DataFrame()

def _extract_nasdaq_expirations(data_obj):
    exp_set = set()
    if not isinstance(data_obj, dict):
        return []

    date_formats = ["%b %d, %Y", "%B %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]

    def try_add_date_str(val):
        if not val:
            return
        s = str(val).strip()
        for fmt in date_formats:
            try:
                dt = datetime.strptime(s[:20], fmt)
                exp_set.add(int(dt.timestamp()))
                return
            except Exception:
                continue

    for key in ["expirationDates", "expirations", "expiryDates"]:
        arr = data_obj.get(key)
        if isinstance(arr, list):
            for item in arr:
                if isinstance(item, (int, float)) and item > 1_000_000_000:
                    exp_set.add(int(item))
                elif isinstance(item, dict):
                    for sub_k in ["date", "value", "label", "expiry"]:
                        try_add_date_str(item.get(sub_k))
                else:
                    try_add_date_str(item)

    filters = data_obj.get("filterlist") or data_obj.get("filters")
    if isinstance(filters, dict):
        for f_val in filters.values():
            if isinstance(f_val, list):
                for item in f_val:
                    if isinstance(item, dict):
                        try_add_date_str(item.get("value") or item.get("label") or item.get("date"))
                    else:
                        try_add_date_str(item)

    rows = data_obj.get("table", {}).get("rows") if isinstance(data_obj.get("table"), dict) else None
    if isinstance(rows, list):
        for r in rows:
            if isinstance(r, dict):
                for k, v in r.items():
                    if any(w in k.lower() for w in ["expir", "expiry", "date"]):
                        try_add_date_str(v)

    return sorted(exp_set)

@st.cache_data(ttl=300, show_spinner=False)
def _query_nasdaq_options_api(symbol, target_dt_timestamp=None):
    clean_sym = symbol.split(".")[0].upper()
    api_key, _, headers = _build_nasdaq_headers()

    date_query = ""
    target_date_str = None
    if target_dt_timestamp:
        dt_obj = datetime.fromtimestamp(target_dt_timestamp)
        target_date_str = dt_obj.strftime("%Y-%m-%d")
        d_from = (dt_obj - timedelta(days=3)).strftime("%Y-%m-%d")
        d_to = (dt_obj + timedelta(days=5)).strftime("%Y-%m-%d")
        date_query = f"&fromdate={d_from}&todate={d_to}&expiry={target_date_str}"

    endpoints = [
        f"https://api.nasdaq.com/api/quote/{clean_sym}/option-chain?assetclass=stocks&limit=200{date_query}",
        f"https://api.nasdaq.com/api/quote/{clean_sym}/option-chain?assetclass=stocks&limit=200"
    ]
    if api_key:
        endpoints.insert(0, f"https://data.nasdaq.com/api/v3/datatables/NDAQ/CHAIN?offset=delayed&symbol={clean_sym}&api_key={api_key}")

    def parse_num(val, is_int=False):
        if val is None:
            return 0 if is_int else 0.0
        s = str(val).replace("$", "").replace(",", "").strip()
        if s in ("", "--", "N/A", "None", "null"):
            return 0 if is_int else 0.0
        try:
            f_val = float(s)
            return int(round(f_val)) if is_int else f_val
        except Exception:
            return 0 if is_int else 0.0

    def find_field(row_dict, prefix_list, keyword_list):
        for k, v in row_dict.items():
            kl = k.lower()
            if any(kl.startswith(p) for p in prefix_list) and any(kw in kl for kw in keyword_list):
                if v not in (None, "", "--"):
                    return v
        return None

    for url in endpoints:
        try:
            res = requests.get(url, headers=headers, timeout=3.0)
            if res.status_code != 200:
                continue
            payload = res.json()

            datatable = payload.get("datatable", {})
            if isinstance(datatable, dict) and datatable.get("data") and datatable.get("columns"):
                cols = [c.get("name") for c in datatable["columns"]]
                rows_raw = [dict(zip(cols, r)) for r in datatable["data"]]
                c_rows, p_rows, exp_set = [], [], set()
                for item in rows_raw:
                    strike = item.get("strikePrice") or item.get("strike")
                    if strike is None:
                        continue
                    opt_type = str(item.get("optionType") or item.get("type") or "").upper()
                    exp_str = str(item.get("expiration") or "")
                    if exp_str:
                        try:
                            exp_set.add(int(datetime.strptime(exp_str[:10], "%Y-%m-%d").timestamp()))
                        except Exception:
                            pass
                    rec = {
                        "strike": parse_num(strike, False),
                        "lastPrice": parse_num(item.get("lastPrice"), False),
                        "openInterest": parse_num(item.get("openInterest"), True),
                        "volume": parse_num(item.get("volume"), True),
                    }
                    if opt_type.startswith("C"):
                        c_rows.append(rec)
                    elif opt_type.startswith("P"):
                        p_rows.append(rec)
                if c_rows and p_rows:
                    return sorted(exp_set), pd.DataFrame(c_rows), pd.DataFrame(p_rows)

            data_obj = payload.get("data", {})
            extracted_exps = _extract_nasdaq_expirations(data_obj)
            chain_rows = data_obj.get("table", {}).get("rows") if isinstance(data_obj, dict) else None
            if isinstance(chain_rows, list) and chain_rows:
                matched_rows = []
                if target_date_str:
                    for r in chain_rows:
                        if not isinstance(r, dict):
                            continue
                        row_exp_txt = " ".join(str(v) for k, v in r.items() if any(w in k.lower() for w in ["expir", "expiry", "date"]))
                        if target_date_str in row_exp_txt:
                            matched_rows.append(r)
                rows_to_parse = matched_rows if matched_rows else chain_rows

                c_rows, p_rows = [], []
                for r in rows_to_parse:
                    if not isinstance(r, dict):
                        continue
                    strike_raw = r.get("strike") or r.get("Strike")
                    strike_val = parse_num(strike_raw, False)
                    if strike_val <= 0:
                        continue

                    c_oi_raw = find_field(r, ["c_", "call"], ["openinterest", "open_interest", "oi"])
                    p_oi_raw = find_field(r, ["p_", "put"], ["openinterest", "open_interest", "oi"])
                    c_last_raw = find_field(r, ["c_", "call"], ["last", "bid", "ask"])
                    p_last_raw = find_field(r, ["p_", "put"], ["last", "bid", "ask"])
                    c_vol_raw = find_field(r, ["c_", "call"], ["volume", "vol"])
                    p_vol_raw = find_field(r, ["p_", "put"], ["volume", "vol"])

                    c_rows.append({
                        "strike": strike_val,
                        "lastPrice": parse_num(c_last_raw, False),
                        "openInterest": parse_num(c_oi_raw, True),
                        "volume": parse_num(c_vol_raw, True),
                    })
                    p_rows.append({
                        "strike": strike_val,
                        "lastPrice": parse_num(p_last_raw, False),
                        "openInterest": parse_num(p_oi_raw, True),
                        "volume": parse_num(p_vol_raw, True),
                    })
                if c_rows and p_rows:
                    return extracted_exps, pd.DataFrame(c_rows), pd.DataFrame(p_rows)
        except Exception:
            continue

    return [], pd.DataFrame(), pd.DataFrame()

def fetch_real_option_chain_for_date(symbol, target_dt_timestamp=None, spot=None):
    """单到期日拉取（严格隔离日期，不使用跨日结算兜底）"""
    md_exp = _query_marketdata_expirations(symbol)
    if get_marketdata_token() and "." not in symbol:
        target_exp_str = (
            datetime.fromtimestamp(int(target_dt_timestamp)).strftime("%Y-%m-%d")
            if target_dt_timestamp
            else (datetime.fromtimestamp(md_exp[0]).strftime("%Y-%m-%d") if md_exp else "")
        )
        md_cdf, md_pdf = _query_marketdata_single_chain(symbol, target_exp_str, spot=spot)
        if not md_cdf.empty and not md_pdf.empty:
            return md_exp, md_cdf, md_pdf
        if md_exp:
            return md_exp, pd.DataFrame(), pd.DataFrame()

    exp_dates, cdf, pdf = _query_nasdaq_options_api(symbol, target_dt_timestamp)
    if not cdf.empty and not pdf.empty:
        return exp_dates, cdf, pdf

    y_exp, y_cdf, y_pdf = _query_yahoo_options_api(symbol, target_dt_timestamp)
    if not y_cdf.empty and not y_pdf.empty:
        return y_exp, y_cdf, y_pdf

    merged_exps = sorted(set(md_exp or []) | set(exp_dates or []) | set(y_exp or []))
    return merged_exps, pd.DataFrame(), pd.DataFrame()

def _build_10_separate_exp_timestamps(real_exp_timestamps, base_dt):
    pool = []
    seen_days = set()

    for ts in sorted(real_exp_timestamps or []):
        try:
            d_key = datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d")
            if d_key not in seen_days:
                seen_days.add(d_key)
                pool.append(int(ts))
        except Exception:
            continue

    cursor = base_dt
    while len(pool) < 10:
        cursor = cursor + timedelta(days=1)
        if cursor.weekday() in [0, 2, 4]:
            d_key = cursor.strftime("%Y-%m-%d")
            if d_key not in seen_days:
                seen_days.add(d_key)
                pool.append(int(cursor.replace(hour=16, minute=0, second=0).timestamp()))

    return pool[:10]

def extract_top3_walls(col_cdf, col_pdf, curr_p):
    """在现价上下 5%~30% 区间内筛选前 3 档最大未平仓压力位/支撑位"""
    if col_cdf is None or col_pdf is None or col_cdf.empty or col_pdf.empty:
        return [], None, [], None

    cdf_clean = col_cdf.sort_values("openInterest", ascending=False).drop_duplicates(subset=["strike"])
    pdf_clean = col_pdf.sort_values("openInterest", ascending=False).drop_duplicates(subset=["strike"])

    c_min_bound = curr_p * 1.05
    c_max_bound = curr_p * 1.30
    above_df = cdf_clean[(cdf_clean["strike"] >= c_min_bound) & (cdf_clean["strike"] <= c_max_bound)].copy()
    if above_df.empty:
        above_df = cdf_clean[cdf_clean["strike"] > curr_p].copy()
    if above_df.empty:
        above_df = cdf_clean.copy()

    top3_calls = (
        above_df.sort_values(by="openInterest", ascending=False)
        .head(3)
        .sort_values(by="strike", ascending=False)
    )
    c_top_list = [(float(r["strike"]), int(r["openInterest"])) for _, r in top3_calls.iterrows()]
    call_wall_val = max(c_top_list, key=lambda x: x[1])[0] if c_top_list else None

    p_min_bound = curr_p * 0.70
    p_max_bound = curr_p * 0.95
    below_df = pdf_clean[(pdf_clean["strike"] >= p_min_bound) & (pdf_clean["strike"] <= p_max_bound)].copy()
    if below_df.empty:
        below_df = pdf_clean[pdf_clean["strike"] < curr_p].copy()
    if below_df.empty:
        below_df = pdf_clean.copy()

    top3_puts = (
        below_df.sort_values(by="openInterest", ascending=False)
        .head(3)
        .sort_values(by="strike", ascending=True)
    )
    p_bot_list = [(float(r["strike"]), int(r["openInterest"])) for _, r in top3_puts.iterrows()]
    put_wall_val = max(p_bot_list, key=lambda x: x[1])[0] if p_bot_list else None

    return c_top_list, call_wall_val, p_bot_list, put_wall_val

def pull_and_filter_10_expirations_locally(symbol: str, spot: float, real_exp_timestamps=None) -> tuple[list[dict[str, Any]], bool]:
    """第一步：每次更新先把 10 个到期日逐一回调到本地容器；第二步：在本地统一筛选与计算"""
    today = datetime.today()
    if real_exp_timestamps is None:
        real_exp_timestamps, _, _ = fetch_real_option_chain_for_date(symbol, spot=spot)

    exp_10 = _build_10_separate_exp_timestamps(real_exp_timestamps, today)
    batch_key = f"{symbol}_{today.strftime('%Y-%m-%d')}"
    local_batch: dict[str, dict[str, Any]] = st.session_state["opt_local_store"].get(batch_key, {})

    for idx, ts_target in enumerate(exp_10):
        d_key = datetime.fromtimestamp(int(ts_target)).strftime("%Y-%m-%d")
        if d_key not in local_batch:
            if idx > 0 and get_marketdata_token():
                time.sleep(0.15)
            _, col_cdf, col_pdf = fetch_real_option_chain_for_date(symbol, ts_target, spot=spot)
            local_batch[d_key] = {
                "ts": int(ts_target),
                "cdf": col_cdf.copy() if not col_cdf.empty else pd.DataFrame(),
                "pdf": col_pdf.copy() if not col_pdf.empty else pd.DataFrame(),
                "has_chain": (not col_cdf.empty and not col_pdf.empty),
                "pulled_at": datetime.now().strftime("%H:%M:%S"),
            }

    st.session_state["opt_local_store"][batch_key] = local_batch

    cols_data = []
    nearest_idx = 0
    min_abs_diff = 999999
    has_any_real_data = False

    for idx, ts_target in enumerate(exp_10):
        dt = datetime.fromtimestamp(int(ts_target))
        d_key = dt.strftime("%Y-%m-%d")
        delta_days = (dt.date() - today.date()).days
        if abs(delta_days) < min_abs_diff:
            min_abs_diff = abs(delta_days)
            nearest_idx = idx

        if delta_days == 0:
            tag = "今天到期"
        elif delta_days < 0:
            tag = f"{abs(delta_days)}天前"
        else:
            tag = f"+{delta_days}天到期"

        rec = local_batch.get(d_key, {})
        col_cdf = rec.get("cdf", pd.DataFrame())
        col_pdf = rec.get("pdf", pd.DataFrame())
        has_chain = bool(rec.get("has_chain"))
        if has_chain:
            has_any_real_data = True

        c_top_list, call_wall_val, p_bot_list, put_wall_val = extract_top3_walls(col_cdf, col_pdf, spot)
        raw_mp = (
            round((spot * 0.55 + call_wall_val * 0.25 + put_wall_val * 0.20), 2)
            if (call_wall_val is not None and put_wall_val is not None)
            else None
        )

        call_wall_px_label = f"Call {call_wall_val:g}" if call_wall_val is not None else "Call —"
        put_wall_px_label = f"Put {put_wall_val:g}" if put_wall_val is not None else "Put —"

        cols_data.append({
            "ts": int(ts_target),
            "date": dt,
            "date_str": dt.strftime("%d/%m"),
            "tag": tag,
            "exp_label": tag,
            "call_wall_px_label": call_wall_px_label,
            "put_wall_px_label": put_wall_px_label,
            "is_today": False,
            "delta": delta_days,
            "has_chain": has_chain,
            "c_top": c_top_list,
            "p_bot": p_bot_list,
            "call_wall": call_wall_val,
            "max_pain": raw_mp,
            "spot": spot,
            "put_wall": put_wall_val,
        })

    if cols_data:
        cols_data[nearest_idx]["is_today"] = True

    return cols_data, has_any_real_data

def build_custom_option_matrix_html(symbol, spot, real_exp_timestamps=None):
    cols_data, has_any_real_data = pull_and_filter_10_expirations_locally(
        symbol, spot, real_exp_timestamps=real_exp_timestamps
    )

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

    col_w = 128
    left_axis_w = 96
    n_cols = len(cols_data)
    total_chart_w = n_cols * col_w
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

    for idx, c in enumerate(cols_data):
        x_left = idx * col_w
        if c["is_today"]:
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

    src_name = "Market Data 真实链" if get_marketdata_token() else "API Key 真实链"
    status_badge = f"{src_name} | 本地10期回调筛选 | ±5%~30% 波段区间" if has_any_real_data else "接口暂未返回真实链"

    html = f"""
    <div style="background:#ffffff; border:2px solid #1e293b; border-radius:8px; padding:8px 10px; font-family:sans-serif; color:#0f172a; width:100%; box-sizing:border-box; overflow:hidden;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; padding-bottom:4px; border-bottom:2px solid #cbd5e1; height:30px; box-sizing:border-box;">
            <div style="font-size:16px; font-weight:900; color:#0f172a;">
                📊 {symbol} 期权墙矩阵 ({status_badge} | Spot: <span style="background:#fef08a; padding:1px 6px; border-radius:4px;">${spot:.2f}</span>)
            </div>
            <div style="display:flex; gap:16px; font-size:13px; font-weight:900;">
                <span style="color:#16a34a;">━━ Call Wall</span>
                <span style="color:#2563eb;">╌╌ Max Pain</span>
                <span style="color:#0f172a;">━━ Spot</span>
                <span style="color:#dc2626;">━━ Put Wall</span>
            </div>
        </div>

        <div style="display:flex; width:100%;">
            <div style="width:{left_axis_w}px; flex-shrink:0; border-right:2px solid #1e293b; display:flex; flex-direction:column; box-sizing:border-box;">
                <div style="height:{header_h}px; border-bottom:1px solid #cbd5e1; display:flex; flex-direction:column; align-items:center; justify-content:center; font-weight:900; font-size:13px; background:#f8fafc; box-sizing:border-box;">
                    <span>到期日</span>
                    <span style="font-size:10.5px; font-weight:800; color:#15803d;">Call Wall 价</span>
                </div>
                <div style="height:{top3_h}px; border-bottom:2px solid #1e293b; display:flex; flex-direction:column; align-items:center; justify-content:center; font-weight:900; font-size:13px; color:#15803d; background:#f0fdf4; text-align:center; box-sizing:border-box;">
                    <span>上3档 Call</span>
                    <span style="font-size:11px; font-weight:800;">+5% ~ +30%</span>
                </div>
                <div style="height:{svg_h}px; position:relative; border-bottom:2px solid #1e293b; background:#ffffff; box-sizing:border-box;">
                    {y_ticks_html}
                </div>
                <div style="height:{bot3_h}px; border-bottom:1px solid #cbd5e1; display:flex; flex-direction:column; align-items:center; justify-content:center; font-weight:900; font-size:13px; color:#b91c1c; background:#fef2f2; text-align:center; box-sizing:border-box;">
                    <span>下3档 Put</span>
                    <span style="font-size:11px; font-weight:800;">-5% ~ -30%</span>
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

    offset_up = svg_h + bot3_h + footer_h
    html += f"""
            </div>
        </div>

        <div style="position:relative; margin-top:-{offset_up}px; margin-left:{left_axis_w}px; width:calc(100% - {left_axis_w}px); height:{svg_h}px; pointer-events:none;">
            <svg width="{total_chart_w}" height="{svg_h}" viewBox="0 0 {total_chart_w} {svg_h}" preserveAspectRatio="none" style="width:100%; height:100%;" xmlns="http://www.w3.org/2000/svg">
                {svg_elements}
            </svg>
        </div>
        <div style="height:{bot3_h + footer_h}px;"></div>
    </div>
    """
    return html

top_bar_html = "<div class='top-bar'><div class='brand-title'>CAPITAL QUANT v2</div><div class='live-badge'>Auto-Sync Every 5m (300s) | " + datetime.now().strftime('%b %d, %Y %H:%M:%S') + " | UK Institutional Terminal</div></div>"
st.markdown(top_bar_html, unsafe_allow_html=True)

n1, n2, n3, n4 = st.columns([1.3, 1.3, 1.6, 2.2])
if n1.button("1. Market Watch", use_container_width=True):
    st.session_state.page = "Market Watch"
    st.rerun()
if n2.button("2. Stock Analysis", use_container_width=True):
    st.session_state.page = "Stock Analysis"
    st.rerun()
if n3.button("3. Options Intelligence", use_container_width=True):
    st.session_state.page = "Options Intelligence"
    st.rerun()
st.session_state.use_live_api = n4.toggle("启用 API Key 行情接口", value=st.session_state.use_live_api)

st.markdown("<div style='border-bottom: 1px solid #1e3a8a; margin: 4px 0 6px 0;'></div>", unsafe_allow_html=True)

# ==================== PAGE 1: MARKET WATCH ====================
@st.fragment(run_every=300)
def render_native_market_watch():
    c1, c2, c3, c4 = st.columns([2.0, 2.2, 1.2, 1.3])
    c1.markdown("### Market Watch")
    new_t = c2.text_input("Add", placeholder="输入任意代码 (美股如 PLTR, 英股如 BP.L)", label_visibility="collapsed").strip().upper()
    if c3.button("ADD TICKER", use_container_width=True) and new_t:
        if new_t not in st.session_state.tickers:
            st.session_state.tickers.append(new_t)
            sync_watchlist_to_url()
            st.success(f"已添加并记住: {new_t}")
            st.rerun()
        else:
            st.warning("该代码已存在自选列表中！")
    if c4.button("MANUAL REFRESH", use_container_width=True):
        st.cache_data.clear()
        st.session_state["opt_local_store"] = {}
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
        st.session_state.selected_ticker = chosen
        st.rerun()
    if t3.button("OPTIONS INTELLIGENCE V2.0 >", use_container_width=True):
        st.session_state.page = "Options Intelligence"
        st.rerun()
    if t4.button("← BACK", use_container_width=True):
        st.session_state.page = "Market Watch"
        st.rerun()

    sym = st.session_state.selected_ticker
    m = fetch_stock_metrics(sym, live=st.session_state.use_live_api)
    cur_price = float(m["price"])

    col_c, col_l = st.columns([2.5, 1.1])
    with col_c:
        card_title_html = "<div class='card-header'>" + sym + " — " + m.get('name', sym) + " | Price Chart</div>"
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
                wall_source_tag = "真实期权墙"
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
        st.plotly_chart(fig, use_container_width=True)

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
        st.session_state.selected_ticker = chosen_o
        st.rerun()
    if o3.button("← Stock Analysis", use_container_width=True):
        st.session_state.page = "Stock Analysis"
        st.rerun()
    if o4.button("Market Watch", use_container_width=True):
        st.session_state.page = "Market Watch"
        st.rerun()

    sym = st.session_state.selected_ticker
    m_opt = fetch_stock_metrics(sym, live=st.session_state.use_live_api)
    spot = float(m_opt["price"])

    base_exp_dates, cdf, pdf = fetch_real_option_chain_for_date(sym, spot=spot)

    matrix_html = build_custom_option_matrix_html(sym, spot, real_exp_timestamps=base_exp_dates)
    st.components.v1.html(matrix_html, height=665, scrolling=False)

    st.markdown("<div class='module-container'>", unsafe_allow_html=True)
    hdr_c1, hdr_c2 = st.columns([4.5, 1.5])
    hdr_c1.markdown("<div class='card-header'>📊 期权库真实核心行权价明细 (Call vs Put 权利金与未平仓对比 | 现价 ±30% 波段全覆盖)</div>", unsafe_allow_html=True)
    st.session_state.show_all_strikes = hdr_c2.toggle("显示全链所有行权价", value=st.session_state.show_all_strikes)

    has_real_chain = (not cdf.empty and not pdf.empty)
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
    m4.markdown("<div class='metric-box'><div class='metric-label'>数据来源状态</div><div class='metric-val' style='color:#4ade80;'>" + ("真实链已接入" if has_real_chain else "待接口返回真实链") + "</div></div>", unsafe_allow_html=True)

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
        st.info("Yahoo 与 Nasdaq 接口当前均未返回真实期权链数据（未启用任何预设模拟价格）。请确认 Streamlit Secrets 中已配置 `MARKETDATA_API_TOKEN`。")
    st.markdown("</div>", unsafe_allow_html=True)
