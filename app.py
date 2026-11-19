import os
import time
from datetime import date
from typing import Any

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Options & Market Watch (Tablet)",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==============================================================================
# 1. 配置与密钥读取（优先读取 st.secrets / 环境变量，支持页面临时输入测试）
# ==============================================================================
MASSIVE_BASE_URL = "https://api.massive.com"

DEFAULT_TICKERS = [
    "NVDA", "GOOGL", "AMZN", "MSFT", "META", "TSLA", "TSM", "AMD",
    "BRK.B", "CEG", "LLY", "SMCI", "MPWR", "MRVL", "SPCX", "CBRS",
]

FALLBACK_SPOT: dict[str, float] = {
    "NVDA": 142.50,
    "GOOGL": 176.20,
    "AMZN": 208.40,
    "MSFT": 424.00,
    "META": 582.00,
    "TSLA": 345.00,
    "TSM": 192.00,
    "AMD": 141.00,
    "BRK.B": 465.00,
    "CEG": 248.00,
    "LLY": 785.00,
    "SMCI": 46.50,
    "MPWR": 640.00,
    "MRVL": 92.00,
    "SPCX": 120.00,
    "CBRS": 35.00,
}


def get_api_key() -> str:
    """按优先级获取 Massive API Key：Session临时覆盖 -> st.secrets -> 环境变量。"""
    session_key = st.session_state.get("temp_massive_api_key", "").strip()
    if session_key:
        return session_key

    try:
        if "MASSIVE_API_KEY" in st.secrets and str(st.secrets["MASSIVE_API_KEY"]).strip():
            return str(st.secrets["MASSIVE_API_KEY"]).strip()
    except Exception:
        pass

    return os.getenv("MASSIVE_API_KEY", "").strip()


# ==============================================================================
# 2. Session State 初始化
# ==============================================================================
if "page" not in st.session_state:
    st.session_state.page = "Market Watch"

if "tickers" not in st.session_state:
    st.session_state.tickers = list(DEFAULT_TICKERS)

if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = "NVDA"

# 只有点击“进入”或主动点击“请求/刷新当前标的”时才写入该字段，实现按需懒加载
if "active_option_symbol" not in st.session_state:
    st.session_state.active_option_symbol = None


def enter_ticker_options(symbol: str):
    """选中单只股票并进入 Options Intelligence，同时激活该标的的按需请求。"""
    sym = symbol.upper().strip()
    st.session_state.selected_ticker = sym
    st.session_state.active_option_symbol = sym
    st.session_state.page = "Options Intelligence"


# ==============================================================================
# 3. 轻量 Market Watch 行情获取（保持现有轻量思路，不扫全表期权）
# ==============================================================================
@st.cache_data(ttl=60, show_spinner=False)
def fetch_watch_quotes(symbols: tuple[str, ...]) -> pd.DataFrame:
    """获取自选股基础现价与涨跌幅（优先用公开 chart 接口，失败回退兜底价）。"""
    rows: list[dict[str, Any]] = []
    headers = {"User-Agent": "Mozilla/5.0"}

    for sym in symbols:
        clean_sym = sym.replace(".", "-")
        price = FALLBACK_SPOT.get(sym, 100.0)
        prev_close = price
        source = "Fallback"

        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{clean_sym}"
            resp = requests.get(
                url,
                params={"range": "5d", "interval": "1d"},
                headers=headers,
                timeout=8,
            )
            if resp.status_code == 200:
                payload = resp.json()
                result = (payload.get("chart", {}).get("result") or [{}])[0]
                meta = result.get("meta", {})
                regular_price = meta.get("regularMarketPrice")
                chart_prev = meta.get("chartPreviousClose") or meta.get("previousClose")
                if regular_price is not None:
                    price = float(regular_price)
                    prev_close = float(chart_prev) if chart_prev else price
                    source = "Yahoo 5d"
        except Exception:
            pass

        chg_pct = ((price - prev_close) / prev_close * 100.0) if prev_close else 0.0
        rows.append(
            {
                "COMPANY CODE": sym,
                "SPOT": round(price, 2),
                "CHG %": round(chg_pct, 2),
                "DATA SRC": source,
            }
        )

    return pd.DataFrame(rows)


# ==============================================================================
# 4. Massive 期权合约与链数据拉取（仅在单只股票被激活时调用）
# ==============================================================================
def _massive_get(path: str, params: dict[str, Any], api_key: str) -> tuple[int, dict[str, Any]]:
    """统一封装 Massive GET 请求，返回 (status_code, json_dict)。"""
    q = dict(params)
    q["apiKey"] = api_key
    url = f"{MASSIVE_BASE_URL}{path}"
    resp = requests.get(url, params=q, timeout=15)
    try:
        data = resp.json()
    except Exception:
        data = {"raw_text": resp.text[:500]}
    return resp.status_code, data


@st.cache_data(ttl=180, show_spinner=False)
def fetch_massive_expirations(
    symbol: str, api_key: str, max_expirations: int = 10
) -> tuple[list[str], dict[str, Any]]:
    """
    拉取单只股票未来最多 max_expirations 个到期日。
    免费 Key 联调阶段默认只翻少量页，避免触发 429 或消耗过多请求。
    """
    diag: dict[str, Any] = {
        "endpoint": "/v3/reference/options/contracts",
        "status_code": None,
        "pages_fetched": 0,
        "contracts_seen": 0,
        "error": None,
    }
    if not api_key:
        diag["error"] = "未检测到 MASSIVE_API_KEY"
        return [], diag

    today_str = date.today().isoformat()
    exp_set: set[str] = set()
    next_url: str | None = None

    params: dict[str, Any] = {
        "underlying_ticker": symbol.upper().strip(),
        "expired": "false",
        "expiration_date.gte": today_str,
        "order": "asc",
        "sort": "expiration_date",
        "limit": 250,
        "apiKey": api_key,
    }

    # 最多翻 3 页，拿到足够多的未来到期日即停
    for page_idx in range(3):
        try:
            if page_idx == 0:
                resp = requests.get(
                    f"{MASSIVE_BASE_URL}/v3/reference/options/contracts",
                    params=params,
                    timeout=15,
                )
            elif next_url:
                sep = "&" if "?" in next_url else "?"
                target = next_url if "apiKey=" in next_url else f"{next_url}{sep}apiKey={api_key}"
                resp = requests.get(target, timeout=15)
            else:
                break

            diag["status_code"] = resp.status_code
            diag["pages_fetched"] = page_idx + 1

            if resp.status_code != 200:
                diag["error"] = resp.text[:300]
                break

            payload = resp.json()
            results = payload.get("results") or []
            diag["contracts_seen"] += len(results)

            for item in results:
                exp_val = item.get("expiration_date")
                if exp_val and exp_val >= today_str:
                    exp_set.add(exp_val)

            if len(exp_set) >= max_expirations and len(results) < 250:
                break

            next_url = payload.get("next_url")
            if not next_url or len(exp_set) >= max_expirations * 2:
                break

            time.sleep(0.25)
        except Exception as exc:
            diag["error"] = str(exc)
            break

    sorted_exps = sorted(exp_set)[:max_expirations]
    return sorted_exps, diag


@st.cache_data(ttl=180, show_spinner=False)
def fetch_massive_chain_for_expiration(
    symbol: str,
    expiration: str,
    spot: float,
    api_key: str,
    window_pct: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """
    拉取某只股票、某个到期日、现价窗口附近的期权合约与快照信息。
    先尝试 /v3/snapshot/options/{underlyingAsset}（若套餐支持），
    若无快照权限或返回为空，则回退到 /v3/reference/options/contracts 合约列表。
    """
    sym = symbol.upper().strip()
    low_strike = round(spot * (1.0 - window_pct), 2) if spot > 0 else 0.0
    high_strike = round(spot * (1.0 + window_pct), 2) if spot > 0 else 999999.0

    meta_info: dict[str, Any] = {
        "expiration": expiration,
        "source_endpoint": None,
        "status_code": None,
        "note": "",
    }

    if not api_key:
        meta_info["note"] = "缺少 MASSIVE_API_KEY"
        return pd.DataFrame(), pd.DataFrame(), meta_info

    # 1. 优先尝试期权快照接口
    snap_params: dict[str, Any] = {
        "expiration_date": expiration,
        "strike_price.gte": low_strike,
        "strike_price.lte": high_strike,
        "limit": 250,
    }
    status, payload = _massive_get(f"/v3/snapshot/options/{sym}", snap_params, api_key)
    meta_info["status_code"] = status

    if status == 200 and payload.get("results"):
        meta_info["source_endpoint"] = "/v3/snapshot/options/{sym}"
        calls_rows: list[dict[str, Any]] = []
        puts_rows: list[dict[str, Any]] = []

        for item in payload["results"]:
            details = item.get("details") or {}
            day = item.get("day") or {}
            last_quote = item.get("last_quote") or {}
            last_trade = item.get("last_trade") or {}

            ctype = (details.get("contract_type") or "").lower()
            strike = details.get("strike_price")
            if strike is None:
                continue

            mid_or_last = (
                last_trade.get("price")
                or day.get("close")
                or last_quote.get("midpoint")
                or 0.0
            )
            row = {
                "strike": float(strike),
                "lastPrice": float(mid_or_last or 0.0),
                "openInterest": int(item.get("open_interest") or 0),
                "volume": int(day.get("volume") or 0),
                "iv": round(float(item.get("implied_volatility") or 0.0) * 100, 1)
                if item.get("implied_volatility")
                else None,
            }
            if ctype == "call":
                calls_rows.append(row)
            elif ctype == "put":
                puts_rows.append(row)

        return (
            pd.DataFrame(calls_rows),
            pd.DataFrame(puts_rows),
            meta_info,
        )

    # 2. 若快照接口未开通或免费档受限，回退到参考合约接口（确保行权价梯队仍可展示）
    ref_params: dict[str, Any] = {
        "underlying_ticker": sym,
        "expiration_date": expiration,
        "strike_price.gte": low_strike,
        "strike_price.lte": high_strike,
        "limit": 250,
    }
    ref_status, ref_payload = _massive_get("/v3/reference/options/contracts", ref_params, api_key)
    meta_info["status_code"] = ref_status
    meta_info["source_endpoint"] = "/v3/reference/options/contracts (fallback)"

    if ref_status == 200 and ref_payload.get("results"):
        calls_rows = []
        puts_rows = []
        for item in ref_payload["results"]:
            ctype = (item.get("contract_type") or "").lower()
            strike = item.get("strike_price")
            if strike is None:
                continue
            row = {
                "strike": float(strike),
                "lastPrice": None,
                "openInterest": None,
                "volume": None,
                "iv": None,
            }
            if ctype == "call":
                calls_rows.append(row)
            elif ctype == "put":
                puts_rows.append(row)

        meta_info["note"] = "当前使用合约列表接口（若需权利金/OI/IV，请确认快照接口套餐权限）"
        return pd.DataFrame(calls_rows), pd.DataFrame(puts_rows), meta_info

    meta_info["note"] = str(payload.get("error") or payload.get("message") or ref_payload)[:200]
    return pd.DataFrame(), pd.DataFrame(), meta_info


# ==============================================================================
# 5. 现价上下各 3 档行权价过滤器
# ==============================================================================
def filter_near_spot_strikes(
    df: pd.DataFrame, spot: float, n_each_side: int = 3
) -> pd.DataFrame:
    """只保留现价上下各 n_each_side 档行权价。"""
    if df.empty or "strike" not in df.columns:
        return df

    work = df.copy()
    work["strike"] = pd.to_numeric(work["strike"], errors="coerce")
    work = work.dropna(subset=["strike"]).drop_duplicates(subset=["strike"]).sort_values("strike")

    if not spot or spot <= 0:
        return work.head(n_each_side * 2 + 1).reset_index(drop=True)

    above = work[work["strike"] >= spot].head(n_each_side)
    below = work[work["strike"] < spot].tail(n_each_side)

    combined = pd.concat([below, above], ignore_index=True)
    return (
        combined.drop_duplicates(subset=["strike"])
        .sort_values("strike")
        .reset_index(drop=True)
    )


@st.cache_data(ttl=180, show_spinner=False)
def fetch_10_expirations_near_spot(
    symbol: str,
    spot: float,
    api_key: str,
    max_expirations: int = 10,
    n_each_side: int = 3,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """
    仅在单只股票被激活时调用：
    拉取未来最多 max_expirations 个到期日，每个到期日筛出现价上下各 n_each_side 档。
    """
    exps, exp_diag = fetch_massive_expirations(symbol, api_key=api_key, max_expirations=max_expirations)
    bundle: dict[str, dict[str, Any]] = {}

    for idx, exp in enumerate(exps):
        if idx > 0:
            time.sleep(0.15)
        cdf, pdf, chain_meta = fetch_massive_chain_for_expiration(
            symbol=symbol,
            expiration=exp,
            spot=spot,
            api_key=api_key,
            window_pct=0.15,
        )
        bundle[exp] = {
            "calls": filter_near_spot_strikes(cdf, spot=spot, n_each_side=n_each_side),
            "puts": filter_near_spot_strikes(pdf, spot=spot, n_each_side=n_each_side),
            "meta": chain_meta,
        }

    return bundle, exp_diag


# ==============================================================================
# 6. 顶部导航与 API Key 快速状态栏
# ==============================================================================
nav_col1, nav_col2, nav_col3 = st.columns([2, 2, 2])
with nav_col1:
    if st.button(
        "📋 Market Watch",
        use_container_width=True,
        type="primary" if st.session_state.page == "Market Watch" else "secondary",
    ):
        st.session_state.page = "Market Watch"
        st.rerun()

with nav_col2:
    if st.button(
        "🎯 Options Intelligence",
        use_container_width=True,
        type="primary" if st.session_state.page == "Options Intelligence" else "secondary",
    ):
        st.session_state.page = "Options Intelligence"
        st.rerun()

with nav_col3:
    key_present = bool(get_api_key())
    st.markdown(
        f"**Massive Key:** `{'已配置' if key_present else '未配置'}` ｜ **当前标的:** `{st.session_state.selected_ticker}`"
    )

with st.expander("🔑 Massive API Key 配置 / 临时测试（仅当前会话内存）", expanded=not bool(get_api_key())):
    st.caption(
        "建议把 `MASSIVE_API_KEY` 写入 Streamlit Secrets 或环境变量；若想在平板上临时测免费 Key，可贴入下方（刷新后若未写 Secrets 需重填）。"
    )
    entered_key = st.text_input(
        "MASSIVE_API_KEY",
        value=st.session_state.get("temp_massive_api_key", ""),
        type="password",
        placeholder="粘贴你的 Massive API Key",
    )
    c_save, c_clear = st.columns([1, 1])
    if c_save.button("应用当前 Key", use_container_width=True):
        st.session_state.temp_massive_api_key = entered_key.strip()
        fetch_massive_expirations.clear()
        fetch_massive_chain_for_expiration.clear()
        fetch_10_expirations_near_spot.clear()
        st.rerun()
    if c_clear.button("清除临时 Key", use_container_width=True):
        st.session_state.temp_massive_api_key = ""
        st.rerun()

st.divider()

# ==============================================================================
# 7. 页面一：Market Watch（保持轻量与现有数据逻辑，点选跳转才激活期权请求）
# ==============================================================================
if st.session_state.page == "Market Watch":
    st.subheader("Market Watch（轻量列表，点击股票进入后才请求期权数据）")

    col_add, col_ref = st.columns([3, 1])
    with col_add:
        new_sym = st.text_input("添加自选代码", placeholder="例如 PLTR、COIN", label_visibility="collapsed")
    with col_ref:
        if st.button("🔄 刷新列表", use_container_width=True):
            fetch_watch_quotes.clear()
            st.rerun()

    if new_sym:
        clean_new = new_sym.upper().strip()
        if clean_new and clean_new not in st.session_state.tickers:
            st.session_state.tickers.append(clean_new)
            st.rerun()

    df_watch = fetch_watch_quotes(tuple(st.session_state.tickers))

    event = st.dataframe(
        df_watch,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    if event and event.selection and event.selection.rows:
        row_idx = event.selection.rows[0]
        if 0 <= row_idx < len(df_watch):
            picked = str(df_watch.iloc[row_idx]["COMPANY CODE"])
            st.session_state.selected_ticker = picked
            st.info(f"已选中 **{picked}**（现价 `{df_watch.iloc[row_idx]['SPOT']}`）。点击下方按钮进入并请求该股票期权：")
            if st.button(f"🚀 进入 {picked} 期权面板并请求数据", type="primary", use_container_width=True):
                enter_ticker_options(picked)
                st.rerun()

# ==============================================================================
# 8. 页面二：Options Intelligence（仅对已激活的单只股票拉取最多 10 期 + 上下 3 档）
# ==============================================================================
else:
    st.subheader("Options Intelligence（按需单只股票 · 最多 10 个到期日 · 每期上下各 3 档）")

    df_watch_quick = fetch_watch_quotes(tuple(st.session_state.tickers))
    spot_map = dict(zip(df_watch_quick["COMPANY CODE"], df_watch_quick["SPOT"]))

    col_sel, col_act, col_refresh = st.columns([2.2, 1.8, 1.5])
    with col_sel:
        current_sel = st.session_state.selected_ticker
        ticker_list = list(st.session_state.tickers)
        if current_sel not in ticker_list:
            ticker_list.insert(0, current_sel)
        chosen_sym = st.selectbox(
            "选择股票",
            options=ticker_list,
            index=ticker_list.index(current_sel),
        )
        st.session_state.selected_ticker = chosen_sym

    default_spot = float(spot_map.get(chosen_sym, FALLBACK_SPOT.get(chosen_sym, 100.0)))
    spot_input = col_act.number_input(
        "正股现价基准（筛上下 3 档）",
        min_value=0.01,
        value=round(default_spot, 2),
        step=0.5,
    )

    with col_refresh:
        st.write("")
        st.write("")
        if st.button("🔄 请求/更新该股票 10 期", type="primary", use_container_width=True):
            st.session_state.active_option_symbol = chosen_sym
            fetch_massive_expirations.clear()
            fetch_massive_chain_for_expiration.clear()
            fetch_10_expirations_near_spot.clear()
            st.rerun()

    active_sym = st.session_state.active_option_symbol

    # 若用户通过顶部导航直接切到本页且尚未激活当前选中股票，自动激活当前选中的单只股票
    if active_sym != chosen_sym:
        st.session_state.active_option_symbol = chosen_sym
        active_sym = chosen_sym

    api_key = get_api_key()
    if not api_key:
        st.warning("请先在上方填入或配置 `MASSIVE_API_KEY`，再请求期权数据。")
        st.stop()

    with st.spinner(f"正在请求 {active_sym} 未来最多 10 个到期日（现价上下各 3 档）..."):
        bundle, exp_diag = fetch_10_expirations_near_spot(
            symbol=active_sym,
            spot=float(spot_input),
            api_key=api_key,
            max_expirations=10,
            n_each_side=3,
        )

    with st.expander("📡 Massive 接口诊断信息（免费 Key 联调查看）", expanded=not bool(bundle)):
        st.json(exp_diag)

    if not bundle:
        st.error(
            f"未能拉取到 `{active_sym}` 的到期日/期权数据。请展开上方“Massive 接口诊断信息”查看 HTTP 状态码与错误信息（例如免费档速率限制或权限提示）。"
        )
        st.stop()

    exp_dates = list(bundle.keys())
    st.success(f"已拉齐 `{active_sym}` 共 **{len(exp_dates)}** 个未来到期日（每期只保留现价 `{spot_input:.2f}` 上下各 **3** 档行权价）。")

    selected_exp = st.selectbox("选择到期日查看上下各 3 档挂单参考", options=exp_dates, index=0)

    day_data = bundle[selected_exp]
    cdf_3: pd.DataFrame = day_data["calls"]
    pdf_3: pd.DataFrame = day_data["puts"]
    day_meta: dict[str, Any] = day_data.get("meta") or {}

    if day_meta.get("note"):
        st.caption(f"提示：{day_meta['note']}（来源：{day_meta.get('source_endpoint')}）")

    c_cols = ["strike", "lastPrice", "openInterest", "volume", "iv"]
    p_cols = ["strike", "lastPrice", "openInterest", "volume", "iv"]

    c_clean = cdf_3[[c for c in c_cols if c in cdf_3.columns]].rename(
        columns={
            "lastPrice": "CALL 价",
            "openInterest": "CALL OI",
            "volume": "CALL 量",
            "iv": "CALL IV%",
        }
    )
    p_clean = pdf_3[[c for c in p_cols if c in pdf_3.columns]].rename(
        columns={
            "lastPrice": "PUT 价",
            "openInterest": "PUT OI",
            "volume": "PUT 量",
            "iv": "PUT IV%",
        }
    )

    if c_clean.empty and p_clean.empty:
        st.info(f"{selected_exp} 在现价 `{spot_input:.2f}` 附近暂无返回合约。")
    else:
        merged = (
            pd.merge(c_clean, p_clean, on="strike", how="outer")
            .sort_values("strike")
            .reset_index(drop=True)
        )
        merged["相对现价"] = merged["strike"].apply(
            lambda k: "现价上方" if k >= spot_input else "现价下方"
        )
        st.markdown(f"#### `{active_sym}` · 到期日 `{selected_exp}`（现价上下各 3 档）")
        st.dataframe(merged, use_container_width=True, hide_index=True)

    with st.expander(f"查看全部 {len(exp_dates)} 个到期日汇总（上下各 3 档）", expanded=False):
        for exp_d in exp_dates:
            sub_c = bundle[exp_d]["calls"]
            sub_p = bundle[exp_d]["puts"]
            st.markdown(f"**到期日：{exp_d}**")
            m_sub = (
                pd.merge(
                    sub_c[["strike", "lastPrice", "openInterest"]].rename(
                        columns={"lastPrice": "Call价", "openInterest": "Call OI"}
                    )
                    if not sub_c.empty
                    else pd.DataFrame(columns=["strike", "Call价", "Call OI"]),
                    sub_p[["strike", "lastPrice", "openInterest"]].rename(
                        columns={"lastPrice": "Put价", "openInterest": "Put OI"}
                    )
                    if not sub_p.empty
                    else pd.DataFrame(columns=["strike", "Put价", "Put OI"]),
                    on="strike",
                    how="outer",
                )
                .sort_values("strike")
                .reset_index(drop=True)
            )
            st.dataframe(m_sub, use_container_width=True, hide_index=True)
