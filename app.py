import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
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
    "EQQQ.L": {"name": "Invesco EQQQ", "price": 405.70, "prev": 402.15, "pe": None, "mcap": "ETF"},
}

PRESET_STOCK_BIRTHDAYS = {
    "NVDA": "1993-04-05",
    "AMD": "1969-05-01",
    "TSM": "1987-02-21",
    "ASML": "1984-03-23",
    "MSFT": "1975-04-04",
    "GOOGL": "1998-09-04",
    "META": "2004-02-04",
    "AMZN": "1994-07-05",
    "AAPL": "1976-04-01",
    "TSLA": "2003-07-01",
    "NFLX": "1997-08-29",
    "MRVL": "1995-05-14",
    "MPWR": "1997-08-22",
    "SMCI": "1993-09-16",
    "CEG": "1999-04-30",
    "CBRS": "2016-05-01",
    "SPCX": "2002-03-14",
    "NG.L": "1990-03-26",
    "QQQ": "1999-03-10",
    "VUAG.L": "2019-05-21",
    "EQQQ.L": "2002-12-03",
}

BIRTHDAY_CACHE_FILE = Path("company_birthdays_cache.json")

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

if "stock_birthdays" not in st.session_state:
    st.session_state["stock_birthdays"] = PRESET_STOCK_BIRTHDAYS.copy()

if "stock_birthday_sources" not in st.session_state:
    st.session_state["stock_birthday_sources"] = {k: "内置出生日" for k in PRESET_STOCK_BIRTHDAYS}

if "flow_manual_overrides" not in st.session_state:
    st.session_state["flow_manual_overrides"] = {}

if "calc_refresh_nonce" not in st.session_state:
    st.session_state["calc_refresh_nonce"] = 0


def _load_birthday_cache() -> dict[str, dict[str, str]]:
    if BIRTHDAY_CACHE_FILE.exists():
        try:
            data = json.loads(BIRTHDAY_CACHE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def _save_birthday_cache(cache: dict[str, dict[str, str]]) -> None:
    try:
        BIRTHDAY_CACHE_FILE.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _ts_or_str_to_ymd(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, (int, float)) and val > 0:
        try:
            ts = float(val) / 1000.0 if float(val) > 1e12 else float(val)
            dt_obj = datetime.utcfromtimestamp(ts)
            if 1800 <= dt_obj.year <= datetime.today().year:
                return dt_obj.strftime("%Y-%m-%d")
        except Exception:
            return None
    s = str(val).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s[:19], fmt).strftime("%Y-%m-%d")
        except Exception:
            continue
    return None


def auto_find_company_birthday(symbol: str, force_lookup: bool = False) -> tuple[str, str]:
    clean_sym = str(symbol or "").upper().strip()
    if not clean_sym:
        return "1985-01-01", "默认兜底"

    b_map = st.session_state.setdefault("stock_birthdays", {})
    src_map = st.session_state.setdefault("stock_birthday_sources", {})

    if not force_lookup and clean_sym in b_map and b_map[clean_sym]:
        return b_map[clean_sym], src_map.get(clean_sym, "已登记出生日")

    if clean_sym in PRESET_STOCK_BIRTHDAYS and not force_lookup:
        d_p = PRESET_STOCK_BIRTHDAYS[clean_sym]
        s_p = "内置出生日"
        b_map[clean_sym] = d_p
        src_map[clean_sym] = s_p
        return d_p, s_p

    disk_cache = _load_birthday_cache()
    if not force_lookup and clean_sym in disk_cache and disk_cache[clean_sym].get("date"):
        d_c = disk_cache[clean_sym]["date"]
        s_c = disk_cache[clean_sym].get("source", "本地缓存出生日")
        b_map[clean_sym] = d_c
        src_map[clean_sym] = s_c
        return d_c, s_c

    if HAS_YF:
        try:
            tk = yf.Ticker(clean_sym)
            info: dict[str, Any] = {}
            try:
                info = tk.info or {}
            except Exception:
                info = {}

            for key in ("dateOfIncorporation", "fundInceptionDate", "firstTradeDateEpochUtc"):
                parsed = _ts_or_str_to_ymd(info.get(key))
                if parsed:
                    src_name = {
                        "dateOfIncorporation": "自动抓取(公司成立/注册日)",
                        "fundInceptionDate": "自动抓取(ETF成立日)",
                        "firstTradeDateEpochUtc": "自动抓取(最早上市日)",
                    }[key]
                    disk_cache[clean_sym] = {"date": parsed, "source": src_name}
                    _save_birthday_cache(disk_cache)
                    b_map[clean_sym] = parsed
                    src_map[clean_sym] = src_name
                    return parsed, src_name

            hist_max = tk.history(period="max", interval="1d")
            if hist_max is not None and not hist_max.empty:
                first_dt = pd.to_datetime(hist_max.index[0]).tz_localize(None)
                parsed_hist = first_dt.strftime("%Y-%m-%d")
                src_hist = "自动抓取(历史最早K线日·待核对)"
                disk_cache[clean_sym] = {"date": parsed_hist, "source": src_hist}
                _save_birthday_cache(disk_cache)
                b_map[clean_sym] = parsed_hist
                src_map[clean_sym] = src_hist
                return parsed_hist, src_hist
        except Exception:
            pass

    fb_dt, _ = _parse_birthday_str("", clean_sym)
    fb_str = fb_dt.strftime("%Y-%m-%d")
    fb_src = "自动兜底日(未查到·建议手动核对)"
    b_map[clean_sym] = fb_str
    src_map[clean_sym] = fb_src
    return fb_str, fb_src


def bump_calc_nonce() -> int:
    st.session_state["calc_refresh_nonce"] = int(st.session_state.get("calc_refresh_nonce", 0)) + 1
    return st.session_state["calc_refresh_nonce"]


def sync_watchlist_to_url():
    st.query_params["watchlist"] = ",".join(st.session_state.tickers)


def select_ticker_with_natal_first(symbol: str, target_page: str | None = None, manual_bday: str = "") -> dict[str, Any]:
    clean_sym = symbol.upper().strip() or "NVDA"
    if clean_sym not in st.session_state.tickers:
        st.session_state.tickers.append(clean_sym)
        sync_watchlist_to_url()
    if manual_bday.strip():
        st.session_state.setdefault("stock_birthdays", {})[clean_sym] = manual_bday.strip()
        st.session_state.setdefault("stock_birthday_sources", {})[clean_sym] = "添加时手动指定出生日"
        disk_cache = _load_birthday_cache()
        disk_cache[clean_sym] = {"date": manual_bday.strip(), "source": "添加时手动指定出生日"}
        _save_birthday_cache(disk_cache)
    else:
        auto_find_company_birthday(clean_sym)

    st.session_state.selected_ticker = clean_sym
    st.session_state.get("stock_natal_registry", {}).pop(clean_sym, None)
    bump_calc_nonce()
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


@st.cache_data(ttl=45, show_spinner=False)
def fetch_stock_metrics(symbol, live=True, refresh_nonce: int = 0):
    _ = refresh_nonce
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


@st.cache_data(ttl=45, show_spinner=False)
def fetch_history_df(symbol, period_str, current_price, refresh_nonce: int = 0):
    _ = refresh_nonce
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


# ==================== 2. OPTIONS ENGINE (CBOE + NASDAQ + YAHOO REAL AGGREGATOR) ====================

def _parse_occ_option_symbol(occ_sym: str) -> tuple[str | None, str | None, float | None]:
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
def _query_cboe_realtime_bundle(symbol: str, refresh_nonce: int = 0) -> tuple[list[str], dict[str, tuple[pd.DataFrame, pd.DataFrame]], str]:
    _ = refresh_nonce
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
def _query_nasdaq_option_bundle(symbol: str, refresh_nonce: int = 0) -> tuple[list[str], dict[str, tuple[pd.DataFrame, pd.DataFrame]], str]:
    _ = refresh_nonce
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


@st.cache_data(ttl=120, show_spinner=False)
def _query_yahoo_yfinance_bundle(symbol: str, refresh_nonce: int = 0) -> tuple[list[str], dict[str, tuple[pd.DataFrame, pd.DataFrame]], str]:
    _ = refresh_nonce
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
    nonce = int(st.session_state.get("calc_refresh_nonce", 0))
    cboe_days, cboe_map, cboe_msg = _query_cboe_realtime_bundle(symbol, refresh_nonce=nonce)
    nq_days, nq_map, _ = ([], {}, "") if len(cboe_map) >= 6 else _query_nasdaq_option_bundle(symbol, refresh_nonce=nonce)
    yh_days, yh_map, yh_msg = ([], {}, "") if (len(cboe_map) + len(nq_map)) >= 6 else _query_yahoo_yfinance_bundle(symbol, refresh_nonce=nonce)

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
        status_msg = f"Nasdaq 链 ({len(nq_map)}期)"
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

    if delta_days <= 7:
        p_min_bound, p_max_bound = curr_p * 0.85, curr_p * 1.005
    else:
        p_min_bound, p_max_bound = curr_p * 0.72, curr_p * 0.95

    below_df = pdf_clean[(pdf_clean["strike"] >= p_min_bound) & (pdf_clean["strike"] <= p_max_bound)].copy()
    if len(below_df) < 3:
        below_df = pdf_clean[(pdf_clean["strike"] >= curr_p * 0.70) & (pdf_clean["strike"] <= curr_p * 1.01)].copy()
    if below_df.empty:
        below_df = pdf_clean[pdf_clean["strike"] <= curr_p * 1.01].copy()
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
    p_band = p_all[(p_all["strike"] >= spot * 0.75) & (p_all["strike"] <= spot * 0.99)].sort_values("power", ascending=False).head(3)

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
    cols_data, _, _, status_msg, cache_time, agg_walls = pull_and_filter_real_expirations_locally(symbol, spot)

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


# ==================== 3. 个股五行主导(70%) + 月份环境(30%) 双向节律引擎 ====================

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
    frozenset({"子", "午"}), frozenset({"丑", "未"}), frozenset({"寅", "申"}),
    frozenset({"卯", "酉"}), frozenset({"辰", "戌"}), frozenset({"巳", "亥"}),
}
SIX_HARMONY_PAIRS = {
    frozenset({"子", "丑"}), frozenset({"寅", "亥"}), frozenset({"卯", "戌"}),
    frozenset({"辰", "酉"}), frozenset({"巳", "申"}), frozenset({"午", "未"}),
}
PUNISHMENT_PAIRS = {
    frozenset({"寅", "巳"}), frozenset({"巳", "申"}), frozenset({"丑", "戌"}),
    frozenset({"戌", "未"}), frozenset({"子", "卯"}),
}

MODEL_MONTH_ANCHORS: dict[int, dict[str, Any]] = {
    1:  {"zhi": "丑", "stage": "破后新生", "top_label": "新品回暖·底部整固", "virtual_base": 45.0, "real_base": 75.0, "zone": "rebound", "tone": "green",  "action": "吸筹"},
    2:  {"zhi": "寅", "stage": "水木起势", "top_label": "开春起势·资金回流", "virtual_base": 58.0, "real_base": 78.0, "zone": "rising",  "tone": "green",  "action": "吸筹"},
    3:  {"zhi": "卯", "stage": "木气生发", "top_label": "季末拉锯·节奏切换", "virtual_base": 52.0, "real_base": 76.0, "zone": "rising",  "tone": "yellow", "action": "洗盘·拉锯"},
    4:  {"zhi": "辰", "stage": "春末整固", "top_label": "财报前瞻·稳步推进", "virtual_base": 62.0, "real_base": 80.0, "zone": "steady",  "tone": "green",  "action": "吸筹"},
    5:  {"zhi": "巳", "stage": "火木渐旺", "top_label": "算力波动·顺势扩张", "virtual_base": 72.0, "real_base": 84.0, "zone": "peak",    "tone": "green",  "action": "吸筹"},
    6:  {"zhi": "午", "stage": "纯火冲高", "top_label": "年中冲高·高波兑现", "virtual_base": 78.0, "real_base": 82.0, "zone": "peak",    "tone": "yellow", "action": "洗盘·拉锯"},
    7:  {"zhi": "未", "stage": "火土交接", "top_label": "暑期调仓·防冲克",   "virtual_base": 55.0, "real_base": 74.0, "zone": "trap",    "tone": "yellow", "action": "洗盘·拉锯"},
    8:  {"zhi": "申", "stage": "财报震荡", "top_label": "财报前震荡·蓄势布局", "virtual_base": 75.0, "real_base": 30.0, "zone": "rising",  "tone": "yellow", "action": "洗盘·拉锯"},
    9:  {"zhi": "酉", "stage": "冲月清洗", "top_label": "冲月清洗·黄金坑",   "virtual_base": 20.0, "real_base": 45.0, "zone": "wash",    "tone": "green",  "action": "吸筹"},
    10: {"zhi": "戌", "stage": "旺月爆发", "top_label": "财报旺月·利润兑现", "virtual_base": 90.0, "real_base": 80.0, "zone": "peak",    "tone": "green",  "action": "吸筹"},
    11: {"zhi": "亥", "stage": "成果入库", "top_label": "口碑发酵·稳定增长", "virtual_base": 65.0, "real_base": 95.0, "zone": "trap",    "tone": "green",  "action": "吸筹"},
    12: {"zhi": "子", "stage": "刑月重塑", "top_label": "天克地冲·避险保本", "virtual_base": 10.0, "real_base": 60.0, "zone": "severe",  "tone": "red",    "action": "派发"},
}

NINE_FIRE_YEAR_FACTOR: dict[int, float] = {
    2024: 0.92,
    2025: 0.98,
    2026: 1.00,
    2027: 0.90,
    2028: 0.94,
    2029: 0.96,
}

LOW_VOL_DEFENSIVE_TICKERS = {"NG.L", "VUAG.L", "QQQ", "EQQQ.L", "SPY", "DIA", "TLT"}


def _year_ganzhi(year: int, month: int) -> tuple[str, str]:
    gz_year = year - 1 if month == 1 else year
    offset = gz_year - 1984
    return TIANGAN[offset % 10], DIZHI[offset % 12]


def _month_ganzhi(year: int, month: int) -> tuple[str, str]:
    gz_year = year - 1 if month == 1 else year
    y_gan, _ = _year_ganzhi(gz_year, 6)
    start_gan_idx = ((TIANGAN.index(y_gan) % 5) * 2 + 2) % 10
    step = 11 if month == 1 else (month - 2)
    m_gan = TIANGAN[(start_gan_idx + step) % 10]
    m_zhi = MODEL_MONTH_ANCHORS[month]["zhi"]
    return m_gan, m_zhi


def _parse_birthday_str(b_str: str, fallback_sym: str) -> tuple[datetime, str]:
    raw = str(b_str or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            dt_p = datetime.strptime(raw, fmt)
            return dt_p, f"出生日 {dt_p.strftime('%Y-%m-%d')}"
        except Exception:
            continue
    digest = hashlib.sha256(fallback_sym.encode("utf-8")).hexdigest()
    day_offset = int(digest[:8], 16) % 14000
    dt_fb = datetime(1985, 1, 1) + timedelta(days=day_offset)
    return dt_fb, f"默认出生日 {dt_fb.strftime('%Y-%m-%d')}"


def _date_to_day_ganzhi(dt_obj: datetime) -> tuple[str, str]:
    y, m, d = dt_obj.year, dt_obj.month, dt_obj.day
    a = (14 - m) // 12
    y_adj = y + 4800 - a
    m_adj = m + 12 * a - 3
    jdn = d + (153 * m_adj + 2) // 5 + 365 * y_adj + y_adj // 4 - y_adj // 100 + y_adj // 400 - 32045
    diff = jdn - 2445733
    return TIANGAN[diff % 10], DIZHI[diff % 12]


def _pts_to_arrow_str(pts: float) -> str:
    if pts >= 12:
        return f"↑↑ {pts:+.1f}点"
    if pts > 1.5:
        return f"↗ {pts:+.1f}点"
    if pts >= -1.5:
        return f"→ {pts:+.1f}点"
    if pts > -12:
        return f"↘ {pts:+.1f}点"
    return f"↓↓ {pts:+.1f}点"


def _element_relation_delta(stock_el: str, target_el: str) -> float:
    if not stock_el or not target_el:
        return 0.0
    if stock_el == target_el:
        return 4.5
    if GENERATES.get(target_el) == stock_el:
        return 6.5
    if GENERATES.get(stock_el) == target_el:
        return -3.5
    if OVERCOMES.get(target_el) == stock_el:
        return -6.0
    if OVERCOMES.get(stock_el) == target_el:
        return 2.5
    return 0.0


def _stock_ganzhi_signature(symbol: str, d_gan: str, d_zhi: str, y_birth_zhi: str) -> dict[str, Any]:
    d_el = TIANGAN_ELEMENT[d_gan]
    d_zhi_el = DIZHI_ELEMENT[d_zhi]
    b_y_el = DIZHI_ELEMENT[y_birth_zhi]

    profile_table: dict[str, tuple[str, str, float]] = {
        "甲": ("水", "金", 1.15),
        "乙": ("水", "金", 1.05),
        "丙": ("木", "水", 1.20),
        "丁": ("木", "水", 1.08),
        "戊": ("火", "木", 1.00),
        "己": ("火", "木", 0.92),
        "庚": ("土", "火", 1.12),
        "辛": ("土", "火", 0.98),
        "壬": ("金", "土", 1.10),
        "癸": ("金", "土", 0.95),
    }
    favored_el, avoid_el, vol_sens = profile_table.get(d_gan, ("木", "金", 1.0))

    digest = hashlib.md5(f"{symbol}:{d_gan}{d_zhi}:{y_birth_zhi}".encode("utf-8")).hexdigest()
    phase_shift = ((int(digest[:4], 16) % 12) - 6) * 1.4
    amp_factor = 0.85 + (int(digest[4:8], 16) % 31) / 100.0

    return {
        "d_el": d_el,
        "d_zhi_el": d_zhi_el,
        "b_y_el": b_y_el,
        "favored_el": favored_el,
        "avoid_el": avoid_el,
        "vol_sens": vol_sens * amp_factor,
        "phase_shift": phase_shift,
    }


def resolve_stock_natal_chart(symbol: str, ref_dt: datetime | None = None) -> dict[str, Any]:
    clean_sym = symbol.upper().strip() or "NVDA"
    now_dt = ref_dt or datetime.today()
    b_str, b_src = auto_find_company_birthday(clean_sym)
    b_dt, b_label = _parse_birthday_str(b_str, clean_sym)

    d_gan, d_zhi = _date_to_day_ganzhi(b_dt)
    b_y_gan, b_y_zhi = _year_ganzhi(b_dt.year, b_dt.month)
    element = TIANGAN_ELEMENT[d_gan]
    zhi_element = DIZHI_ELEMENT[d_zhi]
    sig = _stock_ganzhi_signature(clean_sym, d_gan, d_zhi, b_y_zhi)

    cur_y_gan, cur_y_zhi = _year_ganzhi(now_dt.year, now_dt.month)
    gz_yr_num = now_dt.year - 1 if now_dt.month == 1 else now_dt.year
    yr_factor = NINE_FIRE_YEAR_FACTOR.get(gz_yr_num, 0.95)
    era_phase = (
        f"九紫离火大运·{clean_sym}({d_gan}{d_zhi}·{element}命)五行主导70%"
        if gz_yr_num == 2026
        else f"{gz_yr_num}年·{clean_sym}({d_gan}{d_zhi}·{element}命)五行主导70%"
    )

    profile = {
        "symbol": clean_sym,
        "birthday": b_dt.strftime("%Y-%m-%d"),
        "birthday_mode": f"{b_label}（{b_src}）",
        "birthday_source": b_src,
        "gan": d_gan,
        "zhi": d_zhi,
        "ganzhi": f"{d_gan}{d_zhi}",
        "birth_year_ganzhi": f"{b_y_gan}{b_y_zhi}",
        "element": element,
        "zhi_element": zhi_element,
        "favored_element": sig["favored_el"],
        "avoid_element": sig["avoid_el"],
        "era_name": "九紫离火运 (2024-2043)",
        "era_phase": era_phase,
        "era_trend": f"{element}行主导·喜{sig['favored_el']}·忌{sig['avoid_el']}",
        "cur_year_ganzhi": f"{cur_y_gan}{cur_y_zhi}",
        "resolved_at": now_dt.strftime("%H:%M:%S"),
    }
    st.session_state["stock_natal_registry"][clean_sym] = profile
    return profile


def _qualitative_month_adjust(
    symbol: str,
    y_num: int,
    m_num: int,
    y_gan: str,
    y_zhi: str,
    m_gan: str,
    m_zhi: str,
    d_gan: str,
    d_zhi: str,
    b_y_zhi: str,
    virtual_base: float,
    real_base: float,
) -> tuple[float, float, str]:
    """
    月份/流月大环境占 30%，个股自身天干地支五行生克冲合占 70%。
    """
    _ = y_gan
    gz_year = y_num - 1 if m_num == 1 else y_num
    yr_factor = NINE_FIRE_YEAR_FACTOR.get(gz_year, 0.95)

    m_gan_el = TIANGAN_ELEMENT[m_gan]
    m_zhi_el = DIZHI_ELEMENT[m_zhi]
    y_zhi_el = DIZHI_ELEMENT[y_zhi]

    sig = _stock_ganzhi_signature(symbol, d_gan, d_zhi, b_y_zhi)
    d_el = sig["d_el"]
    d_zhi_el = sig["d_zhi_el"]

    # 1. 月份背景分量（30% 权重）
    month_v_part = virtual_base * (0.90 + 0.10 * yr_factor)
    month_r_part = real_base * (0.94 + 0.06 * yr_factor)

    # 2. 个股自身五行分量（70% 权重）
    gan_rel_m = _element_relation_delta(d_el, m_gan_el) * 1.4
    zhi_rel_m = _element_relation_delta(d_zhi_el, m_zhi_el) * 1.2
    year_rel_d = _element_relation_delta(d_el, y_zhi_el) * 0.6

    fav_hit = 0.0
    if m_gan_el == sig["favored_el"] or m_zhi_el == sig["favored_el"]:
        fav_hit += 10.0
    if m_gan_el == sig["avoid_el"] or m_zhi_el == sig["avoid_el"]:
        fav_hit -= 10.5

    clash_合_delta_v = 0.0
    clash_合_delta_r = 0.0
    tags: list[str] = [f"{d_gan}{d_zhi}·{d_el}命"]

    if m_zhi == d_zhi:
        clash_合_delta_v -= 8.0
        clash_合_delta_r -= 4.0
        tags.append("日支伏吟")
    if frozenset({d_zhi, m_zhi}) in CLASH_PAIRS:
        clash_合_delta_v -= 16.0
        clash_合_delta_r -= 8.5
        tags.append(f"{d_zhi}{m_zhi}相冲")
    if frozenset({d_zhi, m_zhi}) in SIX_HARMONY_PAIRS:
        clash_合_delta_v += 11.5
        clash_合_delta_r += 7.0
        tags.append(f"{d_zhi}{m_zhi}六合")
    if frozenset({d_zhi, m_zhi}) in PUNISHMENT_PAIRS:
        clash_合_delta_v -= 12.0
        clash_合_delta_r -= 6.0
        tags.append(f"{d_zhi}{m_zhi}相刑")

    if frozenset({b_y_zhi, m_zhi}) in CLASH_PAIRS:
        clash_合_delta_v -= 7.5
        clash_合_delta_r -= 4.0
        tags.append("年支逢冲")
    elif frozenset({b_y_zhi, m_zhi}) in SIX_HARMONY_PAIRS:
        clash_合_delta_v += 5.5
        clash_合_delta_r += 3.0
        tags.append("年支逢合")

    stock_wave = np.sin(
        (m_num + (TIANGAN.index(d_gan) % 5) * 1.1 + (DIZHI.index(d_zhi) % 4) * 0.8) * 1.05
    ) * 10.0

    if m_gan_el == sig["favored_el"]:
        tags.append(f"得{m_gan_el}助")
    elif m_gan_el == sig["avoid_el"]:
        tags.append(f"忌{m_gan_el}旺")
    elif gan_rel_m >= 5.0:
        tags.append(f"{m_gan_el}生/助{d_el}")
    elif gan_rel_m <= -5.0:
        tags.append(f"{m_gan_el}克{d_el}")

    stock_v_part = 52.0 + (
        (gan_rel_m + zhi_rel_m + year_rel_d + fav_hit) * sig["vol_sens"]
        + clash_合_delta_v
        + stock_wave
        + sig["phase_shift"]
    )
    stock_r_part = 62.0 + (
        (zhi_rel_m * 0.8 + gan_rel_m * 0.5 + fav_hit * 0.7) * (0.85 + 0.15 * sig["vol_sens"])
        + clash_合_delta_r
        + stock_wave * 0.65
        + sig["phase_shift"] * 0.6
    )

    v_final = round(max(10.0, min(95.0, float(0.30 * month_v_part + 0.70 * stock_v_part))), 1)
    r_final = round(max(20.0, min(95.0, float(0.30 * month_r_part + 0.70 * stock_r_part))), 1)
    return v_final, r_final, "·".join(tags[:4])


def build_12m_stock_series(
    symbol: str,
    custom_date: str = "",
    ref_dt: datetime | None = None,
    m_data: dict[str, Any] | None = None,
    cdf: pd.DataFrame | None = None,
    pdf: pd.DataFrame | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    now = ref_dt or datetime.today()
    clean_sym = symbol.upper().strip() or "NVDA"
    natal = resolve_stock_natal_chart(clean_sym, ref_dt=now)
    if custom_date.strip():
        b_dt, _ = _parse_birthday_str(custom_date.strip(), clean_sym)
        d_gan, d_zhi = _date_to_day_ganzhi(b_dt)
        b_y_gan, b_y_zhi = _year_ganzhi(b_dt.year, b_dt.month)
        d_el = TIANGAN_ELEMENT[d_gan]
        sig = _stock_ganzhi_signature(clean_sym, d_gan, d_zhi, b_y_zhi)
        natal = {
            **natal,
            "birthday": b_dt.strftime("%Y-%m-%d"),
            "gan": d_gan,
            "zhi": d_zhi,
            "ganzhi": f"{d_gan}{d_zhi}",
            "birth_year_ganzhi": f"{b_y_gan}{b_y_zhi}",
            "element": d_el,
            "favored_element": sig["favored_el"],
            "avoid_element": sig["avoid_el"],
        }
    else:
        b_dt, _ = _parse_birthday_str(natal["birthday"], clean_sym)
        _, b_y_zhi = _year_ganzhi(b_dt.year, b_dt.month)
        d_gan, d_zhi, d_el = natal["gan"], natal["zhi"], natal["element"]

    start_ym_idx = (now.year * 12 + (now.month - 1)) - 1
    cur_ym_idx = now.year * 12 + (now.month - 1)
    is_low_vol = clean_sym in LOW_VOL_DEFENSIVE_TICKERS

    rows: list[dict[str, Any]] = []
    for col_idx in range(12):
        ym_idx = start_ym_idx + col_idx
        y_num = ym_idx // 12
        m_num = (ym_idx % 12) + 1

        y_gan, y_zhi = _year_ganzhi(y_num, m_num)
        m_gan, m_zhi = _month_ganzhi(y_num, m_num)
        anchor = MODEL_MONTH_ANCHORS[m_num]

        total_score, flow_score, rel_text = _qualitative_month_adjust(
            symbol=clean_sym,
            y_num=y_num,
            m_num=m_num,
            y_gan=y_gan,
            y_zhi=y_zhi,
            m_gan=m_gan,
            m_zhi=m_zhi,
            d_gan=d_gan,
            d_zhi=d_zhi,
            b_y_zhi=b_y_zhi,
            virtual_base=float(anchor["virtual_base"]),
            real_base=float(anchor["real_base"]),
        )

        base_pts = (total_score - 50.0) * 0.42
        vol_scale = 0.72 if is_low_vol else 1.05
        short_adj = 0.0
        if col_idx in (1, 2) and m_data:
            rsi_val = float(m_data.get("rsi") or 50.0)
            if rsi_val >= 65:
                short_adj += 1.5
            elif rsi_val <= 35:
                short_adj -= 1.5
        if col_idx in (1, 2) and cdf is not None and pdf is not None and _is_valid_chain_pair(cdf, pdf):
            coi = safe_col_sum(cdf, "openInterest")
            poi = safe_col_sum(pdf, "openInterest")
            if coi > 0:
                pcr_v = poi / coi
                if pcr_v >= 1.25:
                    short_adj -= 2.0
                elif pcr_v <= 0.75:
                    short_adj += 2.0

        flow_pts = round(max(-22.0, min(22.0, base_pts * vol_scale + short_adj)), 1)

        if col_idx == 0:
            slot_role = "上月回顾"
            col_tag = "第1栏·上月"
        elif ym_idx == cur_ym_idx:
            slot_role = "本月基准"
            col_tag = "第2栏·本月"
        else:
            slot_role = "顺延推演"
            col_tag = f"第{col_idx + 1}栏"

        avg_power = (total_score + flow_score) / 2.0
        if avg_power >= 74.0:
            positioning = f"{d_el}行顺势走强"
            trend_out = f"📈 {d_el}旺·{anchor['stage']}"
        elif total_score <= 25.0 or flow_score <= 45.0:
            positioning = f"{d_el}行受阻防御"
            trend_out = f"📉 {d_el}弱·{anchor['stage']}"
        elif total_score < 45.0 and flow_score >= 65.0:
            positioning = f"{d_el}虚弱实稳吸筹"
            trend_out = f"↘ {d_el}分歧·{anchor['stage']}"
        elif total_score >= 65.0 and flow_score < 60.0:
            positioning = f"{d_el}虚强实紧兑现"
            trend_out = f"↔ {d_el}拉锯·{anchor['stage']}"
        else:
            positioning = f"{d_el}行自身节律推进"
            trend_out = f"↗ {d_el}行·{anchor['stage']}"

        override_key = f"{clean_sym}_{y_num}-{m_num:02d}"
        flow_tone = st.session_state.get("flow_manual_overrides", {}).get(override_key, anchor["tone"])
        action_label = {"green": "吸筹", "yellow": "洗盘·拉锯", "red": "派发"}[flow_tone]

        rows.append({
            "col_idx": col_idx,
            "col_tag": col_tag,
            "ym_idx": ym_idx,
            "year_num": y_num,
            "month_num": m_num,
            "ym_str": f"{y_num}-{m_num:02d}",
            "slot_role": slot_role,
            "y_ganzhi": f"{y_gan}{y_zhi}",
            "m_ganzhi": f"{m_gan}{m_zhi}",
            "stage": anchor["stage"],
            "zone": anchor["zone"],
            "total_score": total_score,
            "flow_score": flow_score,
            "flow_pts": flow_pts,
            "flow_arrow": _pts_to_arrow_str(flow_pts),
            "inst_top_label": anchor["top_label"],
            "rel_text": rel_text,
            "positioning": positioning,
            "trend_out": trend_out,
            "flow_tone": flow_tone,
            "action_label": action_label,
            "override_key": override_key,
            "upper_x": f"{col_tag}<br>{str(y_num)[2:]}年{y_num}-{m_num:02d} ({m_gan}{m_zhi})<br><b>{d_el}·{anchor['stage']}</b>",
            "lower_x": f"{str(y_num)[2:]}年{m_num}月 ({m_gan}{m_zhi})<br><b>{anchor['top_label']}</b>",
        })

    alerts: list[str] = []
    for i, r in enumerate(rows):
        nxt = rows[i + 1] if i + 1 < len(rows) else None
        early_shift = False
        alert_txt = ""
        if nxt and (nxt["total_score"] <= 25.0 or nxt["zone"] in ("severe", "wash")):
            early_shift = True
            alert_txt = f"⚡ 提早~15天作用：{clean_sym}({d_el}命) 下月({nxt['month_num']}月·{nxt['m_ganzhi']})红线={nxt['total_score']:.0f}（{nxt['rel_text']}），注意提前调仓"
        elif r["total_score"] <= 20.0 or r["zone"] == "severe":
            early_shift = True
            alert_txt = f"⚡ 提早~15天作用：{clean_sym}({d_el}命) 当月（{r['rel_text']}），注意节奏切换"
        r["early_shift"] = early_shift
        r["early_alert"] = alert_txt
        if r["col_idx"] in (1, 2) and alert_txt:
            alerts.append(alert_txt)

    cur_row = rows[1] if len(rows) > 1 else rows[0]
    meta_out = {
        **natal,
        "col1_label": f"{rows[0]['year_num']}年{rows[0]['month_num']}月({rows[0]['m_ganzhi']}·{rows[0]['stage']})",
        "col2_label": f"{rows[1]['year_num']}年{rows[1]['month_num']}月({rows[1]['m_ganzhi']}·{rows[1]['stage']})",
        "cur_positioning": cur_row["positioning"],
        "cur_trend_out": cur_row["trend_out"],
        "cur_split_desc": f"红线(虚)={cur_row['total_score']:.1f} · 绿线(实)={cur_row['flow_score']:.1f} ({cur_row['rel_text']})",
        "alerts": alerts,
    }
    return rows, meta_out


def render_12m_cycle_block_above_options(
    symbol: str,
    m_data: dict[str, Any] | None = None,
    cdf: pd.DataFrame | None = None,
    pdf: pd.DataFrame | None = None,
):
    now_dt = datetime.today()
    rows, meta = build_12m_stock_series(symbol, ref_dt=now_dt, m_data=m_data, cdf=cdf, pdf=pdf)

    st.markdown("<div class='module-container' style='padding:12px 14px; margin-bottom:10px;'>", unsafe_allow_html=True)

    top_h1, top_h2 = st.columns([4.2, 2.2])
    top_h1.markdown(
        f"<div class='card-header' style='margin-bottom:2px;'>🧭 {symbol} [{meta['ganzhi']}·{meta['element']}命] 虚实双向12月能量面板 · 五行70%主导</div>"
        f"<div style='font-size:13.5px; color:#cbd5e1;'>"
        f"大运与五行: <b>{meta['era_name']} · {meta['era_phase']}（{meta['era_trend']}）</b> | "
        f"标的命盘: <b>{meta['birthday_mode']} · 日柱 {meta['ganzhi']}({meta['element']}命)</b><br>"
        f"本月状态: <b><span style='color:#93c5fd;'>{meta['cur_split_desc']}</span></b> | "
        f"本月定位与走势: <b><span style='color:#facc15;'>{meta['cur_positioning']}</span> · <span style='color:#4ade80;'>{meta['cur_trend_out']}</span></b><br>"
        f"时间轴: <b>第1栏={meta['col1_label']}</b> → <b>第2栏={meta['col2_label']}</b> → 往后逐月顺延共12个月"
        f"</div>",
        unsafe_allow_html=True,
    )

    with top_h2:
        with st.expander("🎂 校准出生日期 · 调整红黄绿资金灯", expanded=False):
            new_bday = st.text_input("出生日期 (YYYY-MM-DD)", value=meta["birthday"], key=f"bday_in_{symbol}")
            b_c1, b_c2 = st.columns(2)
            if b_c1.button("保存手动出生日", key=f"bday_btn_{symbol}", use_container_width=True):
                st.session_state["stock_birthdays"][symbol] = new_bday.strip()
                st.session_state["stock_birthday_sources"][symbol] = "手动校准出生日"
                disk_c = _load_birthday_cache()
                disk_c[symbol] = {"date": new_bday.strip(), "source": "手动校准出生日"}
                _save_birthday_cache(disk_c)
                st.session_state["stock_natal_registry"].pop(symbol, None)
                bump_calc_nonce()
                st.rerun()
            if b_c2.button("重新自动查找", key=f"bday_auto_btn_{symbol}", use_container_width=True):
                auto_find_company_birthday(symbol, force_lookup=True)
                st.session_state["stock_natal_registry"].pop(symbol, None)
                bump_calc_nonce()
                st.rerun()

            m_opts = [f"{r['ym_str']} ({r['m_ganzhi']}·{r['stage']})" for r in rows]
            pick_m = st.selectbox("选择月份调资金灯", m_opts, index=1, key=f"flow_m_sel_{symbol}")
            pick_idx = m_opts.index(pick_m)
            cur_tone = rows[pick_idx]["flow_tone"]
            tone_map_cn = {"green": "🟢 绿(吸筹)", "yellow": "🟡 黄(洗盘·拉锯)", "red": "🔴 红(派发)"}
            rev_tone_map = {v: k for k, v in tone_map_cn.items()}
            chosen_tone_cn = st.radio(
                "资金/造市商状态",
                list(tone_map_cn.values()),
                index=list(tone_map_cn.keys()).index(cur_tone),
                key=f"flow_tone_radio_{symbol}_{pick_idx}",
            )
            if st.button("保存该月资金灯", key=f"flow_save_btn_{symbol}", use_container_width=True):
                st.session_state["flow_manual_overrides"][rows[pick_idx]["override_key"]] = rev_tone_map[chosen_tone_cn]
                st.rerun()

    if meta["alerts"]:
        st.markdown(
            f"<div style='background:#1e1b4b; border:1px solid #facc15; border-radius:7px; padding:6px 10px; margin:6px 0; font-size:13px; color:#fde047; font-weight:800;'>"
            + " ｜ ".join(meta["alerts"])
            + "</div>",
            unsafe_allow_html=True,
        )

    upper_x = [r["upper_x"] for r in rows]
    red_y = [r["total_score"] for r in rows]
    green_y = [r["flow_score"] for r in rows]
    upper_hover = [
        f"{r['upper_x']}<br>红线(虚/波动节奏): {r['total_score']:.1f}<br>绿线(实/稳健节奏): {r['flow_score']:.1f}<br>五行依据: {r['rel_text']}<extra></extra>"
        for r in rows
    ]

    fig_upper = go.Figure()
    fig_upper.add_trace(go.Scatter(
        x=upper_x,
        y=red_y,
        mode="lines+markers+text",
        name=f"{symbol} 红线(虚/波动节奏)",
        text=[f"{v:.0f}" for v in red_y],
        textposition="top center",
        textfont=dict(size=12.5, color="#b91c1c"),
        line=dict(color="#ef4444", width=3.0),
        marker=dict(size=9, color="#ef4444", line=dict(color="#ffffff", width=1.2)),
        hovertemplate=upper_hover,
    ))
    fig_upper.add_trace(go.Scatter(
        x=upper_x,
        y=green_y,
        mode="lines+markers+text",
        name=f"{symbol} 绿线(实/稳健节奏)",
        text=[f"{v:.0f}" for v in green_y],
        textposition="bottom center",
        textfont=dict(size=12, color="#15803d"),
        line=dict(color="#16a34a", width=3.0),
        marker=dict(size=9, color="#16a34a", line=dict(color="#ffffff", width=1.2)),
        hovertemplate="%{x}<br>绿线指数: %{y:.1f}<extra></extra>",
    ))
    fig_upper.add_vrect(x0=-0.45, x1=0.45, fillcolor="rgba(148, 163, 184, 0.16)", line_width=0)
    fig_upper.add_vrect(x0=0.55, x1=1.45, fillcolor="rgba(250, 204, 21, 0.20)", line_width=0)

    for r in rows:
        if r["early_shift"]:
            below_y = max(6.0, min(red_y[r["col_idx"]], green_y[r["col_idx"]]) - 11.0)
            fig_upper.add_annotation(
                x=r["upper_x"],
                y=below_y,
                text="⚡提早~15天",
                showarrow=False,
                yanchor="top",
                font=dict(size=10, color="#b45309"),
                bgcolor="rgba(254, 243, 199, 0.94)",
            )

    fig_upper.update_layout(
        title=dict(text=f"① 上轨：{symbol} [{meta['ganzhi']}({meta['element']}命)] 五行70%主导12个月能量曲线", font=dict(size=13.5, color="#0f172a")),
        template="plotly_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        height=320,
        margin=dict(l=20, r=16, t=56, b=66),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig_upper.update_xaxes(tickfont=dict(size=10.5, color="#0f172a"))
    fig_upper.update_yaxes(range=[0, 108], title="能量指数 (0-100)", gridcolor="#e2e8f0")
    st.plotly_chart(fig_upper, use_container_width=True)

    lower_x = [r["lower_x"] for r in rows]
    lower_y = [r["flow_pts"] for r in rows]
    lower_arrows = [r["flow_arrow"] for r in rows]
    tone_to_hex = {"green": "#16a34a", "yellow": "#eab308", "red": "#dc2626"}
    lower_colors = [tone_to_hex.get(r["flow_tone"], "#eab308") for r in rows]

    fig_lower = go.Figure()
    fig_lower.add_hline(y=0, line_dash="dot", line_color="#64748b", line_width=1.2)
    fig_lower.add_trace(go.Scatter(
        x=lower_x,
        y=lower_y,
        mode="lines+markers+text",
        name="资金与波动点数",
        text=lower_arrows,
        textposition="top center",
        textfont=dict(size=12, color="#0f172a"),
        line=dict(color="#334155", width=2.4, dash="dash"),
        marker=dict(size=13, color=lower_colors, line=dict(color="#0f172a", width=1.5)),
        hovertemplate="%{x}<br>资金箭头: %{text}<extra></extra>",
    ))
    fig_lower.add_vrect(x0=-0.45, x1=0.45, fillcolor="rgba(148, 163, 184, 0.16)", line_width=0)
    fig_lower.add_vrect(x0=0.55, x1=1.45, fillcolor="rgba(250, 204, 21, 0.20)", line_width=0)

    fig_lower.update_layout(
        title=dict(text=f"② 下轨：{symbol} [{meta['element']}命] 逐月柱干支与资金弹性（🟢吸筹 · 🟡洗盘·拉锯 · 🔴派发）", font=dict(size=13.5, color="#0f172a")),
        template="plotly_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        height=275,
        margin=dict(l=20, r=16, t=44, b=58),
        showlegend=False,
    )
    fig_lower.update_xaxes(tickfont=dict(size=10.5, color="#0f172a"))
    fig_lower.update_yaxes(range=[-28, 28], title="波动点数", gridcolor="#e2e8f0")
    st.plotly_chart(fig_lower, use_container_width=True)

    strip_html = "<div style='display:grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap:7px; margin-top:4px;'>"
    for r in rows:
        tone_dot = {"green": "🟢", "yellow": "🟡", "red": "🔴"}[r["flow_tone"]]
        tone_badge = f"{tone_dot} {r['action_label']}"
        tone_col = {"green": "#4ade80", "yellow": "#facc15", "red": "#f87171"}[r["flow_tone"]]
        border_c = "2px solid #facc15" if r["slot_role"] == "本月基准" else ("1.5px dashed #94a3b8" if r["col_idx"] == 0 else "1px solid #3b82f6")
        strip_html += (
            f"<div style='background:#07193d; border:{border_c}; border-radius:7px; padding:7px 8px; color:#fff;'>"
            f"<div style='display:flex; justify-content:space-between; font-size:12.5px; font-weight:900;'>"
            f"<span style='color:#93c5fd;'>{r['ym_str']} ({r['m_ganzhi']})</span>"
            f"<span style='color:{tone_col};'>{tone_badge}</span>"
            f"</div>"
            f"<div style='font-size:11.5px; color:#fb923c; font-weight:800; margin-top:2px;'>{r['positioning']} · {r['trend_out']}</div>"
            f"<div style='font-size:11px; color:#cbd5e1; margin-top:1px;'>红线(虚): {r['total_score']:.1f} · 绿线(实): {r['flow_score']:.1f}</div>"
            f"<div style='font-size:11px; color:#4ade80; margin-top:1px;'>五行: {r['rel_text']}</div>"
            f"<div style='font-size:11px; color:#e2e8f0; margin-top:1px;'>下轨: {r['flow_arrow']} · {r['inst_top_label']}</div>"
            f"</div>"
        )
    strip_html += "</div>"
    st.markdown(strip_html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ==================== TOP BAR & NAVIGATION ====================

active_natal = resolve_stock_natal_chart(st.session_state.selected_ticker)

top_bar_html = "<div class='top-bar'><div class='brand-title'>CAPITAL QUANT v2</div><div class='live-badge'>Auto-Sync Every 3m (180s) | " + datetime.now().strftime('%b %d, %Y %H:%M:%S') + " | 70% Stock Element Engine</div></div>"
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
    c1, c2, c3, c4, c5 = st.columns([1.6, 1.8, 1.4, 1.1, 1.2])
    c1.markdown("### Market Watch")
    new_t = c2.text_input("Add", placeholder="新股票代码 (如 PLTR, BP.L)", label_visibility="collapsed").strip().upper()
    new_bday = c3.text_input("Bday", placeholder="出生日可选 YYYY-MM-DD", label_visibility="collapsed").strip()
    if c4.button("ADD TICKER", use_container_width=True) and new_t:
        if new_t not in st.session_state.tickers:
            p_res = select_ticker_with_natal_first(new_t, manual_bday=new_bday)
            st.success(f"已自动定命盘并添加 {new_t}：{p_res['birthday']}（{p_res['ganzhi']}·{p_res['element']}命 · {p_res['birthday_source']}）")
            st.rerun()
        else:
            st.warning("该代码已存在自选列表中！")
    if c5.button("MANUAL REFRESH", use_container_width=True):
        st.cache_data.clear()
        st.session_state["opt_persistent_cache"] = {}
        st.session_state["stock_natal_registry"] = {}
        bump_calc_nonce()
        st.rerun()

    nonce = int(st.session_state.get("calc_refresh_nonce", 0))
    rows = []
    gainers = 0
    losers = 0
    for sym in st.session_state.tickers:
        d = fetch_stock_metrics(sym, live=st.session_state.use_live_api, refresh_nonce=nonce)
        nat = resolve_stock_natal_chart(sym)
        chg = round(d["price"] - d["prev"], 2)
        pct = round((chg / d["prev"]) * 100, 2) if d["prev"] else 0.0
        if chg > 0:
            gainers += 1
        elif chg < 0:
            losers += 1
        rows.append({
            "COMPANY CODE": sym,
            "五行命盘": f"{nat['ganzhi']}·{nat['element']}命",
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
        if col == "五行命盘":
            return base + " color: #facc15; font-size: 15px; font-weight: 800;"
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

    sym = resolve_stock_natal_chart(st.session_state.selected_ticker)["symbol"]
    nonce = int(st.session_state.get("calc_refresh_nonce", 0))
    m = fetch_stock_metrics(sym, live=st.session_state.use_live_api, refresh_nonce=nonce)
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

        hdf = fetch_history_df(sym, st.session_state.chart_period, cur_price, refresh_nonce=nonce)

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

    sym = resolve_stock_natal_chart(st.session_state.selected_ticker)["symbol"]
    nonce = int(st.session_state.get("calc_refresh_nonce", 0))
    m_opt = fetch_stock_metrics(sym, live=st.session_state.use_live_api, refresh_nonce=nonce)
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
