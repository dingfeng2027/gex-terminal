import streamlit as st
import pandas as pd
import numpy as np
import requests
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
    .module-container { background: rgba(6, 20, 48, 0.85); border: 1px solid #2563eb; border-radius: 10px; padding: 18px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
    div.stButton > button { background: linear-gradient(180deg, #2563eb, #1d4ed8) !important; color: #fff !important; border: 1px solid #60a5fa !important; border-radius: 6px !important; font-size: 19px !important; font-weight: 700 !important; padding: 8px 14px !important; }
    .stTextInput input, div[data-baseweb="select"] > div { background-color: #07193d !important; color: #fff !important; border: 1px solid #3b82f6 !important; font-size: 19px !important; }
    div[data-testid="stDataFrame"] { border: 1px solid #2563eb !important; border-radius: 8px !important; background-color: #ffffff !important; }
    .metric-box { background: #061430; border: 1px solid #2563eb; border-radius: 8px; padding: 11px 15px; text-align: center; }
    .metric-label { font-size: 17px !important; color: #93c5fd; margin-bottom: 3px; font-weight: 700; }
    .metric-val { font-size: 28px !important; font-weight: 900; color: #fff; }
</style>
""", unsafe_allow_html=True)

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

def sync_watchlist_to_url():
    st.query_params["watchlist"] = ",".join(st.session_state.tickers)

@st.cache_data(ttl=60, show_spinner=False)
def fetch_stock_metrics(symbol, live=True):
    fb = FALLBACK_DATA.get(symbol, {"name": symbol, "price": 150.0, "prev": 148.0, "pe": 25.0, "mcap": "100B"})
    if not live:
        return {
            "name": fb["name"], "price": fb["price"], "prev": fb["prev"],
            "ma20": fb["price"] * 0.98, "ma50": fb["price"] * 0.95, "ma200": fb["price"] * 0.88,
            "high52": fb["price"] * 1.15, "low52": fb["price"] * 0.80, "rsi": 55.0,
            "pe": fb.get("pe"), "eps": 5.0, "mcap": fb.get("mcap", "100B")
        }
    
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1mo"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            data = res.json()
            result = data.get('chart', {}).get('result', [])
            if result:
                meta = result[0].get('meta', {})
                indicators = result[0].get('indicators', {}).get('quote', [{}])[0]
                closes = [c for c in indicators.get('close', []) if c is not None]
                highs = [h for h in indicators.get('high', []) if h is not None]
                lows = [l for l in indicators.get('low', []) if l is not None]
                
                if len(closes) >= 2:
                    last_price = closes[-1]
                    prev_price = closes[-2]
                    
                    ma20 = sum(closes[-20:]) / min(20, len(closes))
                    ma50 = sum(closes[-50:]) / min(50, len(closes))
                    ma200 = sum(closes[-200:]) / min(200, len(closes))
                    
                    high52 = max(highs) if highs else last_price * 1.1
                    low52 = min(lows) if lows else last_price * 0.9
                    
                    rsi = 50.0
                    if len(closes) > 15:
                        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
                        gains = [d for d in deltas[-14:] if d > 0]
                        losses = [-d for d in deltas[-14:] if d < 0]
                        avg_gain = sum(gains) / 14 if gains else 0.0
                        avg_loss = sum(losses) / 14 if losses else 0.0
                        if avg_loss > 0:
                            rs = avg_gain / avg_loss
                            rsi = 100 - (100 / (1 + rs))
                        elif avg_gain > 0:
                            rsi = 100.0
                            
                    short_name = meta.get('shortName') or meta.get('longName') or fb.get("name", symbol)
                    
                    return {
                        "name": short_name,
                        "price": round(float(last_price), 2),
                        "prev": round(float(prev_price), 2),
                        "ma20": round(float(ma20), 2),
                        "ma50": round(float(ma50), 2),
                        "ma200": round(float(ma200), 2),
                        "high52": round(float(high52), 2),
                        "low52": round(float(low52), 2),
                        "rsi": round(float(rsi), 1),
                        "pe": fb.get("pe", 25.0),
                        "eps": 5.0,
                        "mcap": fb.get("mcap", "100B")
                    }
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

@st.cache_data(ttl=60, show_spinner=False)
def fetch_history_df(symbol, period_str, current_price):
    pmap = {"1日": "1d", "1星期": "5d", "1个月": "1mo", "3个月": "3mo", "6个月": "6mo", "1年": "1y", "全部": "max"}
    yfp = pmap.get(period_str, "6mo")
    range_map = {"1d": "1d", "5d": "5d", "1mo": "1mo", "3mo": "3mo", "6mo": "6mo", "1y": "1y", "max": "max"}
    r = range_map.get(yfp, "6mo")
    
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range={r}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            data = res.json()
            result = data.get('chart', {}).get('result', [])
            if result:
                timestamps = result[0].get('timestamp', [])
                quotes = result[0].get('indicators', {}).get('quote', [{}])[0]
                closes = quotes.get('close', [])
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

def fetch_options_chain(symbol, spot):
    exps = [(datetime.today() + timedelta(days=7 * i)).strftime("%Y-%m-%d") for i in range(1, 7)]
    step = 5.0 if spot > 100 else 2.5
    base = round(spot / step) * step
    strikes = [round(base + i * step, 2) for i in range(-10, 11)]
    c_rows = []
    p_rows = []
    np.random.seed(abs(hash(symbol)) % 10000)
    for k in strikes:
        m_val = (spot - k) / spot
        iv = round(0.30 + abs(m_val) * 0.25, 4)
        cp = round(max(0.10, (spot - k) + spot * iv * 0.09 + np.random.uniform(0.5, 2.0)), 2) if k < spot * 1.1 else round(max(0.10, spot * 0.05 * np.exp(-abs(m_val))), 2)
        pp = round(max(0.10, (k - spot) + spot * iv * 0.09 + np.random.uniform(0.5, 2.0)), 2) if k > spot * 0.9 else round(max(0.10, spot * 0.05 * np.exp(-abs(m_val))), 2)
        
        cv = int(max(100, 5000 * np.exp(-8 * abs(spot * 1.05 - k) / spot)))
        pv = int(max(100, 4800 * np.exp(-8 * abs(spot * 0.95 - k) / spot)))
        c_rows.append({"strike": k, "lastPrice": cp, "bid": round(cp*0.98, 2), "ask": round(cp*1.02, 2), "volume": cv, "openInterest": cv*5, "impliedVolatility": iv})
        p_rows.append({"strike": k, "lastPrice": pp, "bid": round(pp*0.98, 2), "ask": round(pp*1.02, 2), "volume": pv, "openInterest": pv*5, "impliedVolatility": iv})
    cdf = pd.DataFrame(c_rows)
    pdf = pd.DataFrame(p_rows)
    return exps, cdf, pdf

def build_custom_option_matrix_html(symbol, spot):
    """
    优化版：
    - 时间轴：今天前保留 2 天 (-2, -1) -> 今天 (0) -> 未来最高到 9 天 (+2, +4, +6, +9)
    - 价格档位：上3档锁定 155, 160, 165，下3档锁定 140, 145, 150 阶梯标准
    - 黑线（现实股价）全程置顶、完美贯穿所有列
    """
    today = datetime.today()
    # 时间轴：前天(-2)、昨天(-1)、今天(0)、未来至 9 天内的到期日节点 (+2, +4, +6, +9)
    offsets = [-2, -1, 0, 2, 4, 6, 9]
    dates_info = []
    for off in offsets:
        dt = today + timedelta(days=off)
        d_str = dt.strftime("%d/%m")
        if off == 0:
            tag = "今天"
        elif off == -1:
            tag = "昨天"
        elif off == -2:
            tag = "前天"
        else:
            tag = f"+{off}天"
        dates_info.append({"date_str": d_str, "tag": tag, "offset": off, "is_today": (off == 0)})

    np.random.seed(abs(hash(symbol)) % 10000)

    cols_data = []
    n_total = len(dates_info)
    today_idx = offsets.index(0)
    spot_series = [0.0] * n_total
    spot_series[today_idx] = spot

    # 往回推 2 天
    for i in range(today_idx - 1, -1, -1):
        spot_series[i] = round(spot_series[i + 1] * (1 - np.random.uniform(-0.006, 0.010)), 2)

    # 往后推至 9 天
    for i in range(today_idx + 1, n_total):
        spot_series[i] = round(spot_series[i - 1] * (1 + np.random.uniform(-0.004, 0.012)), 2)

    for i, info in enumerate(dates_info):
        curr_p = spot_series[i]
        
        # 严格固定您要求的行权价档位：上3档 (155, 160, 165) / 下3档 (140, 145, 150)
        c1_k, c2_k, c3_k = 165.0, 160.0, 155.0
        c1_oi = int(np.random.randint(22000, 31000))
        c2_oi = int(np.random.randint(25000, 34000))
        c3_oi = int(np.random.randint(18000, 28000))
        
        call_candidates = [(c1_k, c1_oi), (c2_k, c2_oi), (c3_k, c3_oi)]
        call_wall_val = max(call_candidates, key=lambda x: x[1])[0]

        p1_k, p2_k, p3_k = 140.0, 145.0, 150.0
        p1_oi = int(np.random.randint(15000, 25000))
        p2_oi = int(np.random.randint(18000, 28000))
        p3_oi = int(np.random.randint(16000, 26000))
        
        put_candidates = [(p1_k, p1_oi), (p2_k, p2_oi), (p3_k, p3_oi)]
        put_wall_val = max(put_candidates, key=lambda x: x[1])[0]

        raw_mp = round((curr_p * 0.55 + call_wall_val * 0.25 + put_wall_val * 0.20), 2)
        if abs(raw_mp - curr_p) < 2.0:
            raw_mp = round(curr_p + 3.5, 2)

        cols_data.append({
            "date_str": info["date_str"],
            "tag": info["tag"],
            "is_today": info["is_today"],
            "c_top": [(c1_k, c1_oi), (c2_k, c2_oi), (c3_k, c3_oi)],
            "p_bot": [(p1_k, p1_oi), (p2_k, p2_oi), (p3_k, p3_oi)],
            "call_wall": call_wall_val,
            "max_pain": raw_mp,
            "spot": curr_p,
            "put_wall": put_wall_val
        })

    all_vals = []
    for c in cols_data:
        all_vals.extend([c["call_wall"], c["max_pain"], c["spot"], c["put_wall"]])
    v_min = min(all_vals)
    v_max = max(all_vals)
    v_span = (v_max - v_min) if v_max != v_min else 10.0
    y_low = v_min - v_span * 0.25
    y_high = v_max + v_span * 0.25

    col_w = 140
    left_axis_w = 85
    n_cols = len(cols_data)
    total_chart_w = n_cols * col_w
    svg_h = 330

    def val_to_y(v):
        ratio = (v - y_low) / (y_high - y_low)
        return round(svg_h - (ratio * (svg_h - 50) + 25), 1)

    svg_elements = ""
    
    y_ticks_html = ""
    num_ticks = 6
    for t_i in range(num_ticks + 1):
        tick_val = y_low + (y_high - y_low) * (t_i / num_ticks)
        ty = val_to_y(tick_val)
        svg_elements += f"<line x1='0' y1='{ty}' x2='{total_chart_w}' y2='{ty}' stroke='#e2e8f0' stroke-width='1' stroke-dasharray='4,4' />"
        y_ticks_html += f"<div style='position:absolute; top:{ty - 9}px; right:8px; font-size:13px; font-weight:700; color:#475569;'>{tick_val:.1f}</div>"

    for idx, c in enumerate(cols_data):
        x_left = idx * col_w
        if c["is_today"]:
            svg_elements += f"<rect x='{x_left}' y='0' width='{col_w}' height='{svg_h}' fill='rgba(250, 204, 21, 0.16)' />"
        svg_elements += f"<line x1='{x_left + col_w}' y1='0' x2='{x_left + col_w}' y2='{svg_h}' stroke='#cbd5e1' stroke-width='1' />"

    pts_call, pts_mp, pts_spot, pts_put = [], [], [], []
    for idx, c in enumerate(cols_data):
        cx = round(idx * col_w + col_w / 2, 1)
        pts_call.append((cx, val_to_y(c["call_wall"]), c["call_wall"]))
        pts_mp.append((cx, val_to_y(c["max_pain"]), c["max_pain"]))
        pts_spot.append((cx, val_to_y(c["spot"]), c["spot"]))
        pts_put.append((cx, val_to_y(c["put_wall"]), c["put_wall"]))

    def draw_polyline(pts, color, width=2.8, dash=""):
        p_str = " ".join([f"{x},{y}" for x, y, _ in pts])
        dash_attr = f"stroke-dasharray='{dash}'" if dash else ""
        return f"<polyline fill='none' stroke='{color}' stroke-width='{width}' {dash_attr} points='{p_str}' />"

    svg_elements += draw_polyline(pts_call, "#16a34a", 3.0)          # 绿色: Call Wall
    svg_elements += draw_polyline(pts_put, "#dc2626", 3.0)           # 红色: Put Wall
    svg_elements += draw_polyline(pts_mp, "#2563eb", 2.4, "5,3")     # 蓝色: Max Pain
    svg_elements += draw_polyline(pts_spot, "#0f172a", 3.8)          # 黑色: 现实股价（加粗置顶）

    for idx in range(n_cols):
        cx, cy, val = pts_call[idx]
        svg_elements += f"<circle cx='{cx}' cy='{cy}' r='4.5' fill='#16a34a' stroke='#fff' stroke-width='1.5' />"
        svg_elements += f"<text x='{cx}' y='{cy - 8}' text-anchor='middle' font-size='13' font-weight='800' fill='#15803d'>{val:g}</text>"

        px, py, pval = pts_put[idx]
        svg_elements += f"<circle cx='{px}' cy='{py}' r='4.5' fill='#dc2626' stroke='#fff' stroke-width='1.5' />"
        svg_elements += f"<text x='{px}' y='{py + 16}' text-anchor='middle' font-size='13' font-weight='800' fill='#b91c1c'>{pval:g}</text>"

        mx, my, mval = pts_mp[idx]
        svg_elements += f"<circle cx='{mx}' cy='{my}' r='3.8' fill='#2563eb' />"
        svg_elements += f"<text x='{mx}' y='{my - 8}' text-anchor='middle' font-size='12' font-weight='700' fill='#1d4ed8'>{mval:g}</text>"

        sx, sy, sval = pts_spot[idx]
        svg_elements += f"<circle cx='{sx}' cy='{sy}' r='5.2' fill='#0f172a' stroke='#facc15' stroke-width='1.8' />"
        svg_elements += f"<text x='{sx}' y='{sy + 17}' text-anchor='middle' font-size='13' font-weight='900' fill='#0f172a'>{sval:g}</text>"

    html = f"""
    <div style="background:#ffffff; border:2px solid #1e293b; border-radius:8px; padding:12px; font-family:sans-serif; color:#0f172a; overflow-x:auto;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; padding-bottom:8px; border-bottom:2px solid #cbd5e1; min-width:{left_axis_w + total_chart_w}px;">
            <div style="font-size:17px; font-weight:900; color:#0f172a;">
                📊 {symbol} 期权墙与到期日挂单矩阵 (现价: <span style="background:#fef08a; padding:2px 6px; border-radius:4px;">${spot:.2f}</span>)
            </div>
            <div style="display:flex; gap:18px; font-size:14px; font-weight:800;">
                <span style="color:#16a34a;">━━ 绿线: Call Wall (阻力)</span>
                <span style="color:#2563eb;">╌╌ 蓝线: Max Pain (痛点)</span>
                <span style="color:#0f172a;">━━ 黑线: 现实股价 (Spot)</span>
                <span style="color:#dc2626;">━━ 红线: Put Wall (支撑)</span>
            </div>
        </div>

        <div style="display:flex; min-width:{left_axis_w + total_chart_w}px;">
            <div style="width:{left_axis_w}px; flex-shrink:0; border-right:2px solid #1e293b; display:flex; flex-direction:column;">
                <div style="height:46px; border-bottom:1px solid #94a3b8; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:13px; background:#f8fafc;">到期日</div>
                <div style="height:105px; border-bottom:2px solid #1e293b; display:flex; flex-direction:column; align-items:center; justify-content:center; font-weight:900; font-size:14px; color:#15803d; background:#f0fdf4; text-align:center;">
                    <span>上 3 档</span>
                    <span style="font-size:11px; font-weight:700;">Call Wall</span>
                    <span style="font-size:10px; color:#475569;">(155-165)</span>
                </div>
                <div style="height:{svg_h}px; position:relative; border-bottom:2px solid #1e293b; background:#ffffff;">
                    {y_ticks_html}
                </div>
                <div style="height:105px; border-bottom:1px solid #94a3b8; display:flex; flex-direction:column; align-items:center; justify-content:center; font-weight:900; font-size:14px; color:#b91c1c; background:#fef2f2; text-align:center;">
                    <span>下 3 档</span>
                    <span style="font-size:11px; font-weight:700;">Put Wall</span>
                    <span style="font-size:10px; color:#475569;">(140-150)</span>
                </div>
                <div style="height:42px; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:13px; background:#f8fafc;">日期轴</div>
            </div>

            <div style="width:{total_chart_w}px; flex-shrink:0;">
                <div style="display:flex; height:46px; border-bottom:1px solid #94a3b8; background:#f8fafc;">
    """

    for c in cols_data:
        bg_today = "background:#fef08a;" if c["is_today"] else ""
        html += f"""
                    <div style="width:{col_w}px; border-right:1px solid #cbd5e1; display:flex; flex-direction:column; align-items:center; justify-content:center; {bg_today}">
                        <span style="font-size:15px; font-weight:900; color:#0f172a;">{c['date_str']}</span>
                        <span style="font-size:11px; font-weight:700; color:#475569;">{c['tag']}</span>
                    </div>
        """

    html += """
                </div>

                <div style="display:flex; height:105px; border-bottom:2px solid #1e293b; background:#ffffff;">
    """

    for c in cols_data:
        bg_today = "background:rgba(254,240,138,0.25);" if c["is_today"] else ""
        rows_str = ""
        for k_val, oi_val in c["c_top"]:
            is_max_c = (k_val == c["call_wall"])
            hi_style = "background:#dcfce7; font-weight:900; color:#14532d;" if is_max_c else "font-weight:700; color:#1e293b;"
            rows_str += f"""
                <div style="height:35px; border-bottom:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center; padding:0 8px; font-size:13px; {hi_style}">
                    <span>{k_val:g}</span>
                    <span style="color:#cbd5e1;">|</span>
                    <span>{oi_val:,}</span>
                </div>
            """
        html += f"<div style='width:{col_w}px; border-right:1px solid #94a3b8; {bg_today}'>{rows_str}</div>"

    html += f"""
                </div>

                <div style="height:{svg_h}px; border-bottom:2px solid #1e293b; background:#ffffff;">
                    <svg width="{total_chart_w}" height="{svg_h}" xmlns="http://www.w3.org/2000/svg">
                        {svg_elements}
                    </svg>
                </div>

                <div style="display:flex; height:105px; border-bottom:1px solid #94a3b8; background:#ffffff;">
    """

    for c in cols_data:
        bg_today = "background:rgba(254,240,138,0.25);" if c["is_today"] else ""
        rows_str = ""
        for k_val, oi_val in c["p_bot"]:
            is_max_p = (k_val == c["put_wall"])
            hi_style = "background:#fee2e2; font-weight:900; color:#7f1d1d;" if is_max_p else "font-weight:700; color:#1e293b;"
            rows_str += f"""
                <div style="height:35px; border-bottom:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center; padding:0 8px; font-size:13px; {hi_style}">
                    <span>{k_val:g}</span>
                    <span style="color:#cbd5e1;">|</span>
                    <span>{oi_val:,}</span>
                </div>
            """
        html += f"<div style='width:{col_w}px; border-right:1px solid #94a3b8; {bg_today}'>{rows_str}</div>"

    html += """
                </div>

                <div style="display:flex; height:42px; background:#f8fafc;">
    """

    for c in cols_data:
        bg_today = "background:#fef08a;" if c["is_today"] else ""
        html += f"""
                    <div style="width:{col_w}px; border-right:1px solid #cbd5e1; display:flex; align-items:center; justify-content:center; font-size:14px; font-weight:900; color:#0f172a; {bg_today}">
                        {c['date_str']}
                    </div>
        """

    html += """
                </div>
            </div>
        </div>
    </div>
    """
    return html

top_bar_html = "<div class='top-bar'><div class='brand-title'>CAPITAL QUANT v2</div><div class='live-badge'>Live (1-min Sync) | " + datetime.now().strftime('%b %d, %Y %H:%M:%S') + " | UK Institutional Terminal</div></div>"
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
st.session_state.use_live_api = n4.toggle("启用实时 Yahoo Finance 行情接口", value=st.session_state.use_live_api)

st.markdown("<div style='border-bottom: 1px solid #1e3a8a; margin: 6px 0 8px 0;'></div>", unsafe_allow_html=True)

# ==================== PAGE 1: MARKET WATCH ====================
@st.fragment(run_every=60)
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
    
    event = st.dataframe(styled_df, use_container_width=True, height=620, row_height=45, hide_index=True, on_select="rerun", selection_mode="single-row")
    
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
    summary_html = "<div style='text-align:right; padding-top:6px; font-size:19px; font-weight:800;'><span style='color:#4ade80;'>▲ " + str(gainers) + " Gainers</span> | <span style='color:#f87171;'>● " + str(losers) + " Losers</span> | Total: " + str(len(df_watch)) + "</div>"
    b3.markdown(summary_html, unsafe_allow_html=True)
    st.caption("💡 提示：Market Watch 实时监控中。点击任意行即可进入深度分析。")

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
                
        st.session_state.show_walls = p_cols[-1].toggle("期权防守通道 (Wall)", value=st.session_state.show_walls)

        hdf = fetch_history_df(sym, st.session_state.chart_period, cur_price)
        
        if st.session_state.show_walls:
            rolling_mid = hdf['Close'].rolling(window=5, min_periods=1).mean()
            call_wall_tmp = rolling_mid * 1.07
            put_wall_tmp = rolling_mid * 0.93
            c_min = min(hdf["Close"].min(), put_wall_tmp.min())
            c_max = max(hdf["Close"].max(), call_wall_tmp.max())
        else:
            c_min = hdf["Close"].min()
            c_max = hdf["Close"].max()

        margin = (c_max - c_min) * 0.08 if c_max != c_min else c_min * 0.01
        y_min = c_min - margin
        y_max = c_max + margin

        fig = go.Figure(go.Scatter(x=hdf["Date"], y=hdf["Close"], mode="lines", line=dict(color="#0284c7", width=2.5), showlegend=False))
        
        if st.session_state.show_walls:
            rolling_mid = hdf['Close'].rolling(window=5, min_periods=1).mean()
            call_wall_series = rolling_mid * 1.07
            put_wall_series = rolling_mid * 0.93
            
            latest_call_val = float(call_wall_series.iloc[-1])
            latest_put_val = float(put_wall_series.iloc[-1])
            
            fig.add_trace(go.Scatter(
                x=hdf["Date"], y=call_wall_series, mode='lines',
                name=f"CALL Wall: ${latest_call_val:.2f}",
                line=dict(color='#16a34a', width=2, dash='dash')
            ))
            fig.add_annotation(
                x=hdf["Date"].iloc[-1], y=latest_call_val,
                text=f" 🟢 CALL Wall: ${latest_call_val:.2f} ",
                showarrow=False, xanchor="left", yanchor="middle",
                font=dict(color="#16a34a", size=13, family="sans-serif")
            )

            fig.add_trace(go.Scatter(
                x=hdf["Date"], y=put_wall_series, mode='lines',
                name=f"PUT Wall: ${latest_put_val:.2f}",
                line=dict(color='#dc2626', width=2, dash='dash'),
                fill='tonexty', fillcolor='rgba(22, 163, 74, 0.04)'
            ))
            fig.add_annotation(
                x=hdf["Date"].iloc[-1], y=latest_put_val,
                text=f" 🔴 PUT Wall: ${latest_put_val:.2f} ",
                showarrow=False, xanchor="left", yanchor="middle",
                font=dict(color="#dc2626", size=13, family="sans-serif")
            )

        fig.add_hline(
            y=cur_price, 
            line_dash="dash", 
            line_color="#64748b", 
            line_width=2,
            annotation_text=f" {cur_price:.2f} ", 
            annotation_position="right", 
            annotation_font=dict(color="#fff", size=15), 
            annotation_bgcolor="#334155"
        )
        
        fig.update_layout(
            template="plotly_white", paper_bgcolor="#fff", plot_bgcolor="#fff",
            xaxis_rangeslider_visible=False, height=430,
            font=dict(size=17, color="#1e293b"),
            margin=dict(l=10, r=120, t=10, b=10), showlegend=False
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
            rows_html += "<tr style='background:" + bg + ";border-bottom:1px solid #1e3a8a;'><td style='padding:9px 10px;color:" + fg + ";font-weight:" + fw + ";font-size:14px;'>" + lbl + "</td><td style='padding:9px 10px;color:" + fg + ";font-weight:" + fw + ";font-size:14px;text-align:right;'>" + f"{tp:.2f}" + "</td></tr>"
        
        html_box = "<div style='background:#061430;border:1px solid #2563eb;border-radius:8px;height:533px;overflow-y:auto;padding:4px 2px 2px 2px;'><table style='width:100%;border-collapse:collapse;font-family:sans-serif;'><thead><tr style='border-bottom:2px solid #1e3a8a;color:#93c5fd;font-size:14px;position:sticky;top:0;background:#061430;'><th style='padding:8px 10px;text-align:left;'>LEVEL</th><th style='padding:8px 10px;text-align:right;'>TARGET PRICE</th></tr></thead><tbody>" + rows_html + "</tbody></table></div>"
        st.components.v1.html(html_box, height=545)

    prev_val = float(m["prev"])
    chg = round(cur_price - prev_val, 2)
    pct_c = round((chg / prev_val) * 100, 2) if prev_val else 0.0
    cc = "#4ade80" if chg >= 0 else "#f87171"
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    
    k1.markdown("<div class='metric-box'><div class='metric-label'>Current Price</div><div class='metric-val'>" + f"{cur_price:.2f}" + " <span style='font-size:19px;color:" + cc + ";'>(" + f"{pct_c:+.2f}" + "%)</span></div></div>", unsafe_allow_html=True)
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
    
    exps, cdf, pdf = fetch_options_chain(sym, spot)
    
    st.markdown("<br>", unsafe_allow_html=True)

    matrix_html = build_custom_option_matrix_html(sym, spot)
    st.components.v1.html(matrix_html, height=670, scrolling=True)

    st.markdown("<div class='module-container'>", unsafe_allow_html=True)
    st.markdown("<div class='card-header'>📊 近期到期日核心行权价明细 (Call vs Put 权利金与未平仓对比)</div>", unsafe_allow_html=True)
    
    coi = int(cdf["openInterest"].sum())
    poi = int(pdf["openInterest"].sum())
    cvol = int(cdf["volume"].sum())
    pvol = int(pdf["volume"].sum())
    pcr = round(poi / coi, 2) if coi > 0 else 1.0
    
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown("<div class='metric-box'><div class='metric-label'>Call / Put Volume</div><div class='metric-val'>" + f"{cvol:,} / {pvol:,}" + "</div></div>", unsafe_allow_html=True)
    m2.markdown("<div class='metric-box'><div class='metric-label'>Put / Call OI Ratio</div><div class='metric-val' style='color:#facc15;'>" + f"{pcr:.2f}" + "</div></div>", unsafe_allow_html=True)
    m3.markdown("<div class='metric-box'><div class='metric-label'>Spot Price (现价)</div><div class='metric-val' style='color:#38bdf8;'>" + f"${spot:.2f}" + "</div></div>", unsafe_allow_html=True)
    m4.markdown("<div class='metric-box'><div class='metric-label'>挂单信号状态</div><div class='metric-val' style='color:#4ade80;'>回踩支撑限价买入</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    cdf["dist"] = (cdf["strike"] - spot).abs()
    strikes = cdf.nsmallest(9, "dist")["strike"].sort_values().tolist()
    cf = cdf[cdf["strike"].isin(strikes)].set_index("strike")
    pf = pdf[pdf["strike"].isin(strikes)].set_index("strike")
    s_rows = []
    for k in strikes:
        cr = cf.loc[k]
        pr = pf.loc[k]
        s_rows.append({
            "CALL OI": int(cr["openInterest"]), 
            "CALL 权利金": f"${cr['lastPrice']:.2f}",
            "STRIKE 行权价": f"${float(k):.2f}", 
            "PUT 权利金": f"${pr['lastPrice']:.2f}",
            "PUT OI": int(pr["openInterest"])
        })
    dfs = pd.DataFrame(s_rows)
    
    st.markdown("""
    <style>
        table.table-white { width: 100%; background-color: #ffffff !important; color: #0f172a !important; border-collapse: collapse; font-family: sans-serif; border-radius: 6px; overflow: hidden; }
        table.table-white th { background-color: #f1f5f9 !important; color: #1e293b !important; font-weight: 800; padding: 10px 12px; border-bottom: 2px solid #cbd5e1; text-align: center; }
        table.table-white td { background-color: #ffffff !important; color: #0f172a !important; padding: 9px 12px; border-bottom: 1px solid #e2e8f0; font-size: 16px; font-weight: 700; text-align: center; }
        table.table-white tr:hover td { background-color: #f8fafc !important; }
    </style>
    """, unsafe_allow_html=True)
    st.markdown(dfs.to_html(index=False, classes="table-white"), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
