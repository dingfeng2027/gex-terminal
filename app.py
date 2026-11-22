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

if "opt_persistent_cache" not in st.session_state:
    st.session_state["opt_persistent_cache"] = {}

def sync_watchlist_to_url():
    st.query_params["watchlist"] = ",".join(st.session_state.tickers)

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

# ==================== 2. OPTIONS ENGINE (LOCKED TO YAHOO YFINANCE) ====================

def _normalize_yf_option_side(df_raw: pd.DataFrame) -> pd.DataFrame:
    if df_raw is None or df_raw.empty or "strike" not in df_raw.columns:
        return pd.DataFrame()
    out = pd.DataFrame()
    out["strike"] = pd.to_numeric(df_raw["strike"], errors="coerce")
    out["lastPrice"] = pd.to_numeric(df_raw.get("lastPrice", 0.0), errors="coerce").fillna(0.0)
    out["openInterest"] = pd.to_numeric(df_raw.get("openInterest", 0), errors="coerce").fillna(0).astype(int)
    out["volume"] = pd.to_numeric(df_raw.get("volume", 0), errors="coerce").fillna(0).astype(int)
    out = out.dropna(subset=["strike"])
    return out[out["strike"] > 0].reset_index(drop=True)

@st.cache_data(ttl=300, show_spinner=False)
def _query_yahoo_yfinance_bundle(symbol: str) -> tuple[list[str], dict[str, tuple[pd.DataFrame, pd.DataFrame]], str]:
    if "." in symbol:
        return [], {}, "非美股代码无 Yahoo 美式期权链"
    if not HAS_YF:
        return [], {}, "未安装 yfinance 库"

    clean_sym = symbol.upper().strip()
    try:
        tk = yf.Ticker(clean_sym)
        raw_exps = list(tk.options or [])
        if not raw_exps:
            return [], {}, "Yahoo 未返回到期日列表"

        today_date = datetime.today().date()
        future_exps = [d for d in sorted(set(raw_exps)) if datetime.strptime(d, "%Y-%m-%d").date() >= today_date]
        target_exps = (future_exps if future_exps else sorted(set(raw_exps)))[:10]

        day_map: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}
        last_err = ""
        for d_str in target_exps:
            try:
                chain = tk.option_chain(d_str)
                cdf = _normalize_yf_option_side(chain.calls)
                pdf = _normalize_yf_option_side(chain.puts)
                if _is_valid_chain_pair(cdf, pdf):
                    day_map[d_str] = (cdf, pdf)
            except Exception as sub_e:
                last_err = str(sub_e)[:45]
                continue

        if day_map:
            return sorted(set(target_exps) | set(day_map.keys())), day_map, f"Yahoo 成功 ({len(day_map)}期)"
        return target_exps, {}, f"Yahoo 链解析为空 ({last_err or '空链'})"
    except Exception as e:
        return [], {}, f"Yahoo 异常: {str(e)[:45]}"

def _collect_yahoo_with_cache(symbol: str) -> tuple[list[str], dict[str, dict[str, Any]], int, str, str]:
    yh_days, yh_map, status_msg = _query_yahoo_yfinance_bundle(symbol)

    cache_store: dict[str, dict[str, Any]] = st.session_state["opt_persistent_cache"]
    prev_entry = cache_store.get(symbol, {})
    prev_by_day: dict[str, dict[str, Any]] = prev_entry.get("by_day", {})
    prev_days: list[str] = prev_entry.get("days", [])

    merged_by_day: dict[str, dict[str, Any]] = {}
    for d_key, rec in prev_by_day.items():
        if _is_valid_chain_pair(rec.get("cdf"), rec.get("pdf")):
            merged_by_day[d_key] = {
                "cdf": rec["cdf"].copy(),
                "pdf": rec["pdf"].copy(),
                "source": "CACHE",
            }

    for d_key, (cdf, pdf) in yh_map.items():
        if _is_valid_chain_pair(cdf, pdf):
            merged_by_day[d_key] = {
                "cdf": cdf.copy(),
                "pdf": pdf.copy(),
                "source": "YH",
            }

    merged_days = sorted(set(yh_days) | set(prev_days) | set(merged_by_day.keys()))
    now_str = datetime.now().strftime("%H:%M:%S")
    cache_time_label = now_str if yh_map else prev_entry.get("updated_at", "")

    if merged_days or merged_by_day:
        cache_store[symbol] = {
            "days": merged_days,
            "by_day": merged_by_day,
            "updated_at": cache_time_label or now_str,
        }

    return merged_days, merged_by_day, len(yh_map), status_msg, cache_time_label

def fetch_real_option_chain_for_date(symbol, target_dt_timestamp=None, spot=None):
    all_days, combined_by_day, _, _, _ = _collect_yahoo_with_cache(symbol)
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

def extract_top3_walls(col_cdf, col_pdf, curr_p):
    if not _is_valid_chain_pair(col_cdf, col_pdf):
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

def pull_and_filter_real_expirations_locally(symbol: str, spot: float) -> tuple[list[dict[str, Any]], bool, int, str, str]:
    today = datetime.today()
    all_days, combined_by_day, yh_count, status_msg, cache_time = _collect_yahoo_with_cache(symbol)
    chosen_days = _build_company_real_day_keys(all_days, today, max_cols=10)

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
            c_top_list, call_wall_val, p_bot_list, put_wall_val = extract_top3_walls(col_cdf, col_pdf, spot)
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

    return cols_data, has_any_real_data, yh_count, status_msg, cache_time

def build_custom_option_matrix_html(symbol, spot):
    cols_data, has_any_real_data, yh_count, status_msg, cache_time = pull_and_filter_real_expirations_locally(symbol, spot)

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

    html = f"""
    <div style="background:#ffffff; border:2px solid #1e293b; border-radius:8px; padding:8px 10px; font-family:sans-serif; color:#0f172a; width:100%; box-sizing:border-box; overflow:hidden;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; padding-bottom:4px; border-bottom:2px solid #cbd5e1; height:30px; box-sizing:border-box;">
            <div style="font-size:15.5px; font-weight:900; color:#0f172a;">
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

# ==================== 3. OBJECTIVE CYCLE, STRONG DISTURBANCES & FLOW RADAR ====================

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

SOLAR_MONTH_TO_ZHI_IDX = {
    2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7,
    8: 8, 9: 9, 10: 10, 11: 11, 12: 0, 1: 1,
}

# 常见标的财报季月份映射（其余代码按哈希推演）
KNOWN_EARNINGS_MONTHS: dict[str, list[int]] = {
    "NVDA": [2, 5, 8, 11],
    "AMD": [2, 5, 8, 11],
    "TSM": [1, 4, 7, 10],
    "ASML": [1, 4, 7, 10],
    "MSFT": [1, 4, 7, 10],
    "GOOGL": [2, 4, 7, 10],
    "META": [2, 4, 7, 10],
    "AMZN": [2, 4, 7, 10],
    "AAPL": [2, 5, 8, 11],
    "TSLA": [1, 4, 7, 10],
    "NFLX": [1, 4, 7, 10],
    "MRVL": [3, 6, 9, 12],
    "MPWR": [2, 5, 8, 11],
    "SMCI": [2, 5, 8, 11],
    "CEG": [2, 5, 8, 11],
}

# 客观月份底色（已取消主观“5月盘中调仓”，保留3月底税务结算低点、9月冲月、12月刑月）
SOLAR_MONTH_RHYTHM = {
    1:  {"tech": 46.0, "real": 75.0, "tag": "年初重配", "desc": "新年流动性回流·底部整固"},
    2:  {"tech": 62.0, "real": 68.0, "tag": "春初脉冲", "desc": "财报季展开·预期博弈"},
    3:  {"tech": 22.0, "real": 52.0, "tag": "税务低点", "desc": "3月底税务结算·深蹲低吸"},
    4:  {"tech": 68.0, "real": 64.0, "tag": "税后回流", "desc": "新财年资金回补·Q1财报"},
    5:  {"tech": 64.0, "real": 66.0, "tag": "夏前过渡", "desc": "Q1财报消化·春末流动性切换"},
    6:  {"tech": 62.0, "real": 58.0, "tag": "年中整固", "desc": "年中再平衡·夏初观望"},
    7:  {"tech": 80.0, "real": 62.0, "tag": "中报冲刺", "desc": "中报窗口·业绩与指引博弈"},
    8:  {"tech": 74.0, "real": 36.0, "tag": "夏末波动", "desc": "暑期流动性偏薄·财报震荡"},
    9:  {"tech": 22.0, "real": 45.0, "tag": "冲月清洗", "desc": "冲月深蹲·黄金坑布局"},
    10: {"tech": 86.0, "real": 78.0, "tag": "旺月财报", "desc": "Q3财报旺月·趋势与兑现"},
    11: {"tech": 65.0, "real": 92.0, "tag": "年底筹划", "desc": "感恩节假期·实盘与税务筹划"},
    12: {"tech": 14.0, "real": 60.0, "tag": "刑月税务", "desc": "年底税务结算+圣诞假期·防破月"},
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

def auto_infer_stock_ganzhi(symbol: str) -> dict[str, Any]:
    clean_sym = symbol.upper().strip()
    digest = hashlib.sha256(clean_sym.encode("utf-8")).hexdigest()
    seed_int = int(digest[:12], 16)

    gan = TIANGAN[seed_int % 10]
    zhi = DIZHI[(seed_int // 10) % 12]
    element = TIANGAN_ELEMENT[gan]
    zhi_element = DIZHI_ELEMENT[zhi]

    if clean_sym in KNOWN_EARNINGS_MONTHS:
        earnings_months = KNOWN_EARNINGS_MONTHS[clean_sym]
    else:
        q_offset = (seed_int % 3)
        earnings_months = sorted({12 if m > 12 else m for m in [1 + q_offset, 4 + q_offset, 7 + q_offset, 10 + q_offset]})

    return {
        "symbol": clean_sym,
        "gan": gan,
        "zhi": zhi,
        "ganzhi": f"{gan}{zhi}",
        "element": element,
        "zhi_element": zhi_element,
        "earnings_months": earnings_months,
    }

def _ganzhi_month_interaction(stock_gan: str, stock_zhi: str, stock_el: str, m_gan: str, m_zhi: str) -> tuple[float, str]:
    m_el = TIANGAN_ELEMENT[m_gan]
    score = 0.0
    tags = []

    pair_zhi = frozenset({stock_zhi, m_zhi})
    if pair_zhi in CLASH_PAIRS:
        score -= 6.5
        tags.append(f"{stock_zhi}{m_zhi}相冲")
    elif pair_zhi in SIX_HARMONY_PAIRS:
        score += 5.5
        tags.append(f"{stock_zhi}{m_zhi}六合")
    elif stock_zhi == m_zhi:
        score += 3.0
        tags.append(f"同支{m_zhi}")

    if GENERATES.get(m_el) == stock_el:
        score += 4.5
        tags.append(f"月{m_el}生股{stock_el}")
    elif GENERATES.get(stock_el) == m_el:
        score -= 2.0
        tags.append(f"股{stock_el}泄气")
    elif OVERCOMES.get(m_el) == stock_el:
        score -= 5.0
        tags.append(f"月{m_el}克股{stock_el}")
    elif OVERCOMES.get(stock_el) == m_el:
        score += 2.5
        tags.append(f"股克月{m_el}")
    elif m_el == stock_el:
        score += 2.5
        tags.append(f"比和{stock_el}")

    if not tags:
        tags.append("干支平和")
    return score, "·".join(tags[:2])

def _strong_disturbance_factors(m_num: int, e_months: list[int], gz_delta: float) -> dict[str, Any]:
    """
    计算三大强扰动因子：
    1. 税务结算（3月底财年/税务低点、11-12月年底税务筹划/换手）
    2. 假期节日（12月底-1月初圣诞/新年、5月底春末假期、7月初假日、11月底感恩节）
    3. 个股财报周期（重点强化“财报前一个月资金抢跑/预期博弈”，兼顾财报当月与财报后消化）
    """
    tax_delta = 0.0
    holiday_delta = 0.0
    earnings_delta = 0.0
    notes: list[str] = []

    is_pre_earnings = False
    is_earnings_month = m_num in e_months
    next_m = 1 if m_num == 12 else (m_num + 1)
    prev_m = 12 if m_num == 1 else (m_num - 1)
    if next_m in e_months:
        is_pre_earnings = True

    # 1. 税务结算
    if m_num == 3:
        tax_delta = -6.0
        notes.append("税务结算低点")
    elif m_num in (11, 12):
        tax_delta = -3.5
        notes.append("年底税务筹划")

    # 2. 假期节日
    if m_num in (12, 1):
        holiday_delta = -2.5
        notes.append("圣诞/新年假期")
    elif m_num == 5:
        holiday_delta = -1.5
        notes.append("5月底春末假期")
    elif m_num == 7:
        holiday_delta = -1.5
        notes.append("7月初假日流动")
    elif m_num == 11:
        holiday_delta = -2.0
        notes.append("感恩节假期")

    # 3. 财报周期（重点强化财报前一个月：资金抢跑 / 预期博弈）
    if is_pre_earnings:
        # 财报前一个月：抢跑与预期博弈影响大，若干支受克则防预期提前兑现/震荡
        earnings_delta = 5.0 if gz_delta >= -2.0 else 2.0
        notes.append("财报前抢跑/预期窗")
    elif is_earnings_month:
        earnings_delta = 3.5 if gz_delta >= -3.0 else -1.5
        notes.append("财报日波动窗")
    elif prev_m in e_months:
        earnings_delta = -3.0
        notes.append("财报后兑现消化")

    return {
        "tax_delta": tax_delta,
        "holiday_delta": holiday_delta,
        "earnings_delta": earnings_delta,
        "is_pre_earnings": is_pre_earnings,
        "is_earnings_month": is_earnings_month,
        "note": " | ".join(notes) if notes else "常规节律",
    }

def evaluate_pre_earnings_flow_radar(symbol: str, m_data: dict[str, Any], cdf: pd.DataFrame, pdf: pd.DataFrame) -> dict[str, str]:
    """
    用大白话判断财报前一个月资金倾向：偏进场 / 偏撤退 / 在拉锯
    结合价格均线强弱与期权买卖防守力量，翻译成小白也能看懂的红/红/黄状态灯与提醒。
    """
    price = float(m_data.get("price", 0.0))
    ma20 = float(m_data.get("ma20", price))
    ma50 = float(m_data.get("ma50", price))
    rsi = float(m_data.get("rsi", 50.0))

    flow_score = 0.0
    reasons: list[str] = []

    if price > 0 and ma20 > 0:
        if price >= ma20 and ma20 >= ma50:
            flow_score += 1.5
            reasons.append("股价站稳短期均线，回踩有承接")
        elif price < ma20 and price < ma50:
            flow_score -= 1.5
            reasons.append("股价跌破短期均线，冲高乏力")
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
            "state": "偏进场",
            "badge": "🟢 偏进场（资金在提前布局/托底）",
            "color": "#4ade80",
            "short_tag": "偏进场",
            "explain": "；".join(reasons[:2]) if reasons else "价格与持仓结构偏稳，资金有提前卡位迹象。",
            "advice": "可按既定节奏顺势或等回踩低吸，但别在急拉时盲目追高。",
        }
    elif flow_score <= -1.5:
        return {
            "state": "偏撤退",
            "badge": "🔴 偏撤退（资金在提前减仓/买保险）",
            "color": "#f87171",
            "short_tag": "偏撤退",
            "explain": "；".join(reasons[:2]) if reasons else "反弹承压或防守力量偏重，资金更倾向提前锁利或防风险。",
            "advice": "管住手、别追高！有浮盈可按分批止盈纪律先收一部分，想买多等低位限价单。",
        }
    else:
        return {
            "state": "在拉锯",
            "badge": "🟡 在拉锯（多空都在等财报开牌）",
            "color": "#facc15",
            "short_tag": "在拉锯",
            "explain": "；".join(reasons[:2]) if reasons else "买卖双方还在试探，大资金没亮出明确方向。",
            "advice": "少折腾、看戏为主，等财报前后方向或关键价位出来了再动手。",
        }

def build_rolling_12m_cycle_rows(
    symbol: str,
    start_year: int,
    start_month: int,
    m_data: dict[str, Any] | None = None,
    cdf: pd.DataFrame | None = None,
    pdf: pd.DataFrame | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    auto_info = auto_infer_stock_ganzhi(symbol)
    s_gan = auto_info["gan"]
    s_zhi = auto_info["zhi"]
    s_el = auto_info["element"]
    e_months = auto_info["earnings_months"]

    flow_info = evaluate_pre_earnings_flow_radar(
        symbol,
        m_data or {},
        cdf if cdf is not None else pd.DataFrame(),
        pdf if pdf is not None else pd.DataFrame(),
    )

    rows = []
    for step in range(12):
        total_m = (start_year * 12 + (start_month - 1)) + step
        y_num = total_m // 12
        m_num = (total_m % 12) + 1

        m_gan, m_zhi = _solar_month_ganzhi(y_num, m_num)
        rhythm = SOLAR_MONTH_RHYTHM[m_num]
        gz_delta, gz_note = _ganzhi_month_interaction(s_gan, s_zhi, s_el, m_gan, m_zhi)
        dist = _strong_disturbance_factors(m_num, e_months, gz_delta)

        # 在3月税务低点、9月冲月、12月刑月，压制单股上冲幅度，确保低谷明显
        if m_num in (3, 9, 12):
            effective_gz = min(gz_delta * 0.5, 2.0)
            effective_earn = min(dist["earnings_delta"], 0.0)
        else:
            effective_gz = gz_delta
            effective_earn = dist["earnings_delta"]

        # 财报前一个月若资金偏撤退，略微降温抢跑分数，防盲目看高
        if dist["is_pre_earnings"] and flow_info["state"] == "偏撤退":
            effective_earn -= 2.0
        elif dist["is_pre_earnings"] and flow_info["state"] == "偏进场":
            effective_earn += 1.5

        total_adj = effective_gz + dist["tax_delta"] + dist["holiday_delta"] + effective_earn
        tech_score = round(max(8.0, min(98.0, rhythm["tech"] + total_adj)), 1)
        real_score = round(max(12.0, min(98.0, rhythm["real"] + gz_delta * 0.35 + dist["tax_delta"] * 0.3)), 1)

        if m_num == 3:
            stance = "税务结算低点"
            action_hint = "3月底分批低吸布局"
            badge_color = "#dc2626"
        elif dist["is_pre_earnings"]:
            stance = f"财报前窗·{flow_info['short_tag']}"
            action_hint = "防冲高兑现 / 不盲目追高" if flow_info["state"] == "偏撤退" else "留意抢跑节奏 / 控仓"
            badge_color = "#f59e0b"
        elif tech_score >= 70:
            stance = "旺月顺势"
            action_hint = "利润兑现 / 防冲高"
            badge_color = "#16a34a"
        elif tech_score >= 45:
            stance = "入库/蓄势"
            action_hint = "回踩分批 / 守现金"
            badge_color = "#2563eb"
        else:
            stance = "冲刑清洗"
            action_hint = "防破月 / 黄金坑低吸"
            badge_color = "#dc2626"

        short_yr = str(y_num)[2:]
        x_label = f"{short_yr}年{m_num}月({m_gan}{m_zhi})"
        factor_line = f"{gz_note} | {dist['note']}"

        rows.append({
            "step": step,
            "year_num": y_num,
            "month_num": m_num,
            "x_label": x_label,
            "short_title": f"{y_num}年{m_num}月",
            "m_ganzhi": f"{m_gan}{m_zhi}",
            "rhythm_tag": rhythm["tag"],
            "rhythm_desc": rhythm["desc"],
            "factor_line": factor_line,
            "tech_score": tech_score,
            "real_score": real_score,
            "stance": stance,
            "action_hint": action_hint,
            "badge_color": badge_color,
            "is_pre_earnings": dist["is_pre_earnings"],
            "is_earnings_month": dist["is_earnings_month"],
        })

    avg_tech = round(sum(r["tech_score"] for r in rows) / len(rows), 1)
    peak_row = max(rows, key=lambda x: x["tech_score"])
    trough_row = min(rows, key=lambda x: x["tech_score"])
    y_gan, y_zhi = _year_to_ganzhi(start_year)

    meta_info = {
        **auto_info,
        "year_ganzhi": f"{y_gan}{y_zhi}",
        "avg_tech": avg_tech,
        "peak_label": f"{peak_row['short_title']}({peak_row['tech_score']:.0f}分)",
        "trough_label": f"{trough_row['short_title']}({trough_row['tech_score']:.0f}分)",
        "flow_info": flow_info,
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

    st.markdown("<div class='module-container' style='padding:12px 14px; margin-bottom:10px;'>", unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([4.8, 1.8])
    show_real_line = h_col2.toggle("显示虚实套利对比线", value=True, key=f"cycle_real_{symbol}")

    h_col1.markdown(
        f"<div class='card-header' style='margin-bottom:2px;'>🧭 {symbol} 未来12个月滚动能量表 (1974 虎盘 × 个股干支: <b>{meta_info['ganzhi']}·{meta_info['element']}</b>)</div>"
        f"<div style='font-size:13.5px; color:#cbd5e1;'>滚动区间: <b>{cur_year}年{cur_month}月 (首月) → {end_row['year_num']}年{end_row['month_num']}月</b> | 流年: <b>{meta_info['year_ganzhi']}</b> | 财报季: <b>{e_str}</b> | 12月均分: <b>{meta_info['avg_tech']:.1f}</b> (高:{meta_info['peak_label']} / 低:{meta_info['trough_label']})</div>",
        unsafe_allow_html=True,
    )

    # 财报前一个月资金风向小卡片（大白话三行提示）
    st.markdown(
        f"<div style='background:#07193d; border:1.5px solid {flow['color']}; border-radius:8px; padding:8px 12px; margin:6px 0 8px 0;'>"
        f"<div style='font-size:14.5px; font-weight:900; color:{flow['color']};'>财报前资金风向：{flow['badge']}</div>"
        f"<div style='font-size:12.5px; color:#e2e8f0; margin-top:2px;'>白话看点：{flow['explain']}</div>"
        f"<div style='font-size:12.5px; color:#93c5fd; font-weight:800; margin-top:2px;'>操作提醒：{flow['advice']}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    x_labels = [r["x_label"] for r in rows]
    y_tech = [r["tech_score"] for r in rows]
    y_real = [r["real_score"] for r in rows]

    fig_12m = go.Figure()
    fig_12m.add_trace(go.Scatter(
        x=x_labels,
        y=y_tech,
        mode="lines+markers+text",
        name=f"{symbol} 综合节律分 (虚)",
        text=[f"{v:.0f}" for v in y_tech],
        textposition="top center",
        line=dict(color="#f97316", width=3.2),
        marker=dict(size=9, color="#f97316", line=dict(color="#ffffff", width=1.5)),
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
        y=103,
        xref="x",
        yref="y",
        text=f"本月起点({cur_month}月)",
        showarrow=False,
        xanchor="center",
        yanchor="top",
        font=dict(color="#b45309", size=12),
        bgcolor="rgba(254, 240, 138, 0.9)",
    )

    for r in rows:
        idx_step = r["step"]
        if r["month_num"] == 3:
            fig_12m.add_vrect(
                x0=idx_step - 0.45,
                x1=idx_step + 0.45,
                fillcolor="rgba(239, 68, 68, 0.14)",
                line_width=0,
            )
            fig_12m.add_annotation(
                x=idx_step,
                y=103,
                xref="x",
                yref="y",
                text="3月底税务低点",
                showarrow=False,
                xanchor="center",
                yanchor="top",
                font=dict(color="#b91c1c", size=11.5),
                bgcolor="rgba(254, 226, 226, 0.92)",
            )
        elif r["is_pre_earnings"]:
            fig_12m.add_annotation(
                x=idx_step,
                y=96,
                xref="x",
                yref="y",
                text=f"财报前窗·{flow['short_tag']}",
                showarrow=False,
                xanchor="center",
                yanchor="top",
                font=dict(color="#b45309", size=11),
                bgcolor="rgba(254, 243, 199, 0.92)",
            )

    fig_12m.update_layout(
        template="plotly_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        height=265,
        font=dict(size=12.5, color="#0f172a"),
        margin=dict(l=12, r=12, t=26, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig_12m.update_yaxes(range=[0, 108], gridcolor="#e2e8f0")
    st.plotly_chart(fig_12m, width="stretch")

    cards_html = "<div style='display:grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap:8px; margin-top:4px;'>"
    for r in rows:
        is_first = (r["step"] == 0)
        is_mar_low = (r["month_num"] == 3)
        is_pre = r["is_pre_earnings"]

        if is_first:
            border_css = "border: 2.5px solid #facc15; box-shadow: 0 0 10px rgba(250,204,21,0.35);"
        elif is_mar_low:
            border_css = "border: 2px solid #ef4444; box-shadow: 0 0 8px rgba(239,68,68,0.28);"
        elif is_pre:
            border_css = "border: 2px solid #f59e0b; box-shadow: 0 0 8px rgba(245,158,11,0.25);"
        else:
            border_css = "border: 1px solid #3b82f6;"

        tag_badge = ""
        if is_first:
            tag_badge = "<span style='background:#facc15; color:#000; font-size:11px; font-weight:900; padding:1px 5px; border-radius:4px; margin-left:4px;'>本月</span>"
        elif is_mar_low:
            tag_badge = "<span style='background:#ef4444; color:#fff; font-size:11px; font-weight:900; padding:1px 5px; border-radius:4px; margin-left:4px;'>税谷</span>"
        elif is_pre:
            tag_badge = f"<span style='background:#f59e0b; color:#000; font-size:11px; font-weight:900; padding:1px 5px; border-radius:4px; margin-left:4px;'>前窗·{flow['short_tag']}</span>"
        elif r["is_earnings_month"]:
            tag_badge = "<span style='background:#38bdf8; color:#000; font-size:11px; font-weight:900; padding:1px 5px; border-radius:4px; margin-left:4px;'>财报月</span>"

        cards_html += (
            f"<div style='background:#07193d; {border_css} border-radius:7px; padding:8px; color:#fff;'>"
            f"<div style='display:flex; justify-content:space-between; align-items:center;'>"
            f"<span style='font-size:14.5px; font-weight:900; color:#93c5fd;'>{r['short_title']}({r['m_ganzhi']}){tag_badge}</span>"
            f"<span style='font-size:14.5px; font-weight:900; color:{r['badge_color']};'>{r['tech_score']:.0f}分</span>"
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

top_bar_html = "<div class='top-bar'><div class='brand-title'>CAPITAL QUANT v2</div><div class='live-badge'>Auto-Sync Every 3m (180s) | " + datetime.now().strftime('%b %d, %Y %H:%M:%S') + " | Nasdaq Stock + Yahoo Options</div></div>"
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
            st.session_state.tickers.append(new_t)
            sync_watchlist_to_url()
            st.success(f"已添加并记住: {new_t}")
            st.rerun()
        else:
            st.warning("该代码已存在自选列表中！")
    if c4.button("MANUAL REFRESH", use_container_width=True):
        st.cache_data.clear()
        st.session_state["opt_persistent_cache"] = {}
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
                wall_source_tag = "Yahoo真实期权墙"
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
    _, cdf, pdf = fetch_real_option_chain_for_date(sym, spot=spot)

    render_12m_cycle_block_above_options(sym, m_data=m_opt, cdf=cdf, pdf=pdf)

    matrix_html = build_custom_option_matrix_html(sym, spot)
    st.components.v1.html(matrix_html, height=665, scrolling=False)

    st.markdown("<div class='module-container'>", unsafe_allow_html=True)
    hdr_c1, hdr_c2 = st.columns([4.5, 1.5])
    hdr_c1.markdown("<div class='card-header'>📊 Yahoo 期权库真实核心行权价明细 (Call vs Put 权利金与未平仓对比 | 现价 ±30% 波段全覆盖)</div>", unsafe_allow_html=True)
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
    m4.markdown("<div class='metric-box'><div class='metric-label'>数据来源状态</div><div class='metric-val' style='color:#4ade80;'>" + ("Yahoo 链已接入" if has_real_chain else "待 Yahoo 返回期权链") + "</div></div>", unsafe_allow_html=True)

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
            st.info("Yahoo 期权库当前未返回匹配行权价明细，未使用预设模拟价格。")
    else:
        st.info("Yahoo Finance 当前暂未返回真实期权链数据（未启用任何预设模拟价格）。")
    st.markdown("</div>", unsafe_allow_html=True)
