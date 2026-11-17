import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta

# ================= PAGE CONFIG & GLOBAL STYLING =================
st.set_page_config(
    page_title="CAPITAL QUANT Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .stApp { background-color: #0b0f19; color: #f8fafc; }
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        padding: 16px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 10px;
    }
    .metric-value { font-size: 24px; font-weight: bold; color: #38bdf8; }
    .metric-label { font-size: 13px; color: #94a3b8; margin-bottom: 5px; }
    .stSidebar { background-color: #0f172a; border-right: 1px solid #1e293b; }
    </style>
""", unsafe_allow_html=True)

# ================= PERSISTENT STATE MANAGEMENT =================
# 初始化自选股记忆列表，防止添加新标的时丢失
if "watchlist_tickers" not in st.session_state:
    st.session_state.watchlist_tickers = ["NVDA", "TSLA", "AAPL", "MSFT", "GOOGL", "AMZN", "AMD"]

if "user_limit_orders" not in st.session_state:
    st.session_state.user_limit_orders = {
        "NVDA": [146.20, 142.40, 131.40]
    }

# ================= SIDEBAR NAVIGATION & WATCHLIST =================
st.sidebar.title("⚡ CAPITAL QUANT")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "选择终端模块", 
    [
        "📊 1. Price Chart & Levels", 
        "🔍 2. Options Intelligence", 
        "💼 3. Trade Execution & Plan"
    ]
)

st.sidebar.markdown("### 📋 自选标的管理")
selected_ticker = st.sidebar.selectbox("选择监控标的", st.session_state.watchlist_tickers)

# 永久记忆添加标的功能
new_ticker_input = st.sidebar.text_input("➕ 添加新标的代码 (如 META, SMCI):")
if st.sidebar.button("确认添加标的"):
    if new_ticker_input:
        cleaned = new_ticker_input.upper().strip()
        if cleaned not in st.session_state.watchlist_tickers:
            st.session_state.watchlist_tickers.append(cleaned)
            st.success(f"成功添加: {cleaned}")
            st.rerun()
        else:
            st.warning("该标的已经在自选列表中了！")

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ 全局显示设置")
show_walls_global = st.sidebar.checkbox("图表叠加机构期权防守通道 (Wall)", value=True)

# ================= DATA LOADER =================
@st.cache_data(ttl=3600)
def load_market_data(ticker_symbol):
    try:
        df = yf.download(ticker_symbol, period="6mo", interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception:
        return pd.DataFrame()

df = load_market_data(selected_ticker)
if df.empty:
    st.error(f"无法获取 [{selected_ticker}] 的市场数据，请检查代码拼写或网络连接。")
    st.stop()

latest_close = float(df['Close'].iloc[-1])
ma20 = float(df['Close'].rolling(20).mean().iloc[-1])

# ================= PAGE 1: PRICE CHART & LEVELS =================
if page == "📊 1. Price Chart & Levels":
    st.markdown(f"### 📊 {selected_ticker} 价格行为与机构限价位监控终端")
    
    # 顶部关键指标卡片
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>当前收盘 (Spot)</div><div class='metric-value'>${latest_close:.2f}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>20日均线 (MA20)</div><div class='metric-value'>${ma20:.2f}</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>核心机构支撑 (PUT Wall)</div><div class='metric-value' style='color:#00E676;'>${latest_close * 0.90:.2f}</div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>核心机构阻力 (CALL Wall)</div><div class='metric-value' style='color:#FF4B4B;'>${latest_close * 1.08:.2f}</div></div>", unsafe_allow_html=True)

    st.markdown("---")

    # 绘制主图 K线图与技术线
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K线'
    ))
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'].rolling(20).mean(), mode='lines', name='MA20', line=dict(color='#FACC15', width=1.5)))

    # 动态限价买入线 (6% ~ 20%)
    limit_levels = [0.94, 0.90, 0.88, 0.86, 0.80]
    colors = ['#38bdf8', '#00E676', '#10b981', '#f59e0b', '#ef4444']
    for idx, lvl in enumerate(limit_levels):
        target_price = latest_close * lvl
        fig.add_hline(y=target_price, line_dash="dash", line_color=colors[idx], 
                      annotation_text=f"分批买入 -{(1-lvl)*100:.1f}% (${target_price:.2f})", 
                      annotation_position="bottom right")

    # 叠加期权墙通道
    if show_walls_global:
        rolling_mid = df['Close'].rolling(window=5, min_periods=1).mean()
        call_wall_series = rolling_mid * 1.08
        put_wall_series = rolling_mid * 0.90

        fig.add_trace(go.Scatter(
            x=df.index, y=call_wall_series, mode='lines',
            name=f"CALL Wall 阻力轨 (${call_wall_series.iloc[-1]:.2f})",
            line=dict(color='#FF4B4B', width=1.8, dash='dash')
        ))
        fig.add_trace(go.Scatter(
            x=df.index, y=put_wall_series, mode='lines',
            name=f"PUT Wall 支撑轨 (${put_wall_series.iloc[-1]:.2f})",
            line=dict(color='#00E676', width=1.8, dash='dash'),
            fill='tonexty', fillcolor='rgba(0, 230, 118, 0.03)'
        ))

    fig.update_layout(
        template='plotly_dark', height=580,
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15, 23, 42, 0.6)'
    )
    st.plotly_chart(fig, use_container_width=True)

# ================= PAGE 2: OPTIONS INTELLIGENCE =================
elif page == "🔍 2. Options Intelligence":
    st.markdown(f"### 🔍 {selected_ticker} 期权结构、Gamma 敞口与机构防守墙情报")
    
    gamma_flip = round(latest_close * 0.92, 2)
    put_wall = round(latest_close * 0.90, 2)
    call_wall = round(latest_close * 1.08, 2)
    max_pain = round(latest_close * 1.01, 2)

    # 模块 3: 摘要卡片
    st.markdown("#### MODULE 3: GAMMA & MARKET MAKER HEDGING INTELLIGENCE")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Gamma Flip Point</div><div class='metric-value'>${gamma_flip}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>PUT Wall (Support)</div><div class='metric-value' style='color:#00E676;'>${put_wall}</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>CALL Wall (Resistance)</div><div class='metric-value' style='color:#FF4B4B;'>${call_wall}</div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Dealer Gamma Bias</div><div class='metric-value'>Positive (Long)</div></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("##### 📊 做市商 Gamma 敞口与支撑阻力分布")
    
    strikes = np.linspace(latest_close * 0.85, latest_close * 1.15, 13)
    gamma_values = np.random.randint(1000, 1600, size=len(strikes))
    
    fig_gamma = go.Figure(go.Bar(
        x=[f"${s:.2f}" for s in strikes], y=gamma_values,
        marker_color=['#38bdf8' if s >= latest_close else '#3b82f6' for s in strikes]
    ))
    fig_gamma.update_layout(
        template='plotly_dark', height=300,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15, 23, 42, 0.6)'
    )
    st.plotly_chart(fig_gamma, use_container_width=True)

    st.markdown("---")

    # 模块 4: 模拟 Open Interest 与 Max Pain
    st.markdown("#### MODULE 4: OPEN INTEREST (OI) TRACKER & MAX PAIN")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Theoretical Max Pain</div><div class='metric-value'>${max_pain}</div></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Max PUT OI Strike</div><div class='metric-value' style='color:#00E676;'>${put_wall}</div></div>", unsafe_allow_html=True)
    with m3:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Max CALL OI Strike</div><div class='metric-value' style='color:#FF4B4B;'>${call_wall}</div></div>", unsafe_allow_html=True)

    # 绘制双向 Open Interest 柱状图
    oi_strikes = np.linspace(latest_close * 0.90, latest_close * 1.10, 9)
    call_oi = np.random.randint(10000, 20000, size=len(oi_strikes))
    put_oi = np.random.randint(10000, 20000, size=len(oi_strikes))

    fig_oi = go.Figure()
    fig_oi.add_trace(go.Bar(x=[f"${s:.2f}" for s in oi_strikes], y=call_oi, name='Call OI (看涨持仓)', marker_color='#00E676'))
    fig_oi.add_trace(go.Bar(x=[f"${s:.2f}" for s in oi_strikes], y=put_oi, name='Put OI (看跌持仓)', marker_color='#FF4B4B'))
    fig_oi.update_layout(
        barmode='group',
        template='plotly_dark', height=320,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15, 23, 42, 0.6)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_oi, use_container_width=True)

    st.markdown("---")

    # 近 30 日 CALL / PUT Wall 演变轨迹图
    st.markdown("##### 📈 近 30 日机构防守线 (PUT Wall) 与阻力线 (CALL Wall) 演变轨迹")
    
    hist_30 = df.tail(30).copy()
    hist_30['PUT_Wall'] = hist_30['Close'].rolling(window=5, min_periods=1).mean() * 0.90
    hist_30['CALL_Wall'] = hist_30['Close'].rolling(window=5, min_periods=1).mean() * 1.08

    fig_wall_trend = go.Figure()
    fig_wall_trend.add_trace(go.Scatter(
        x=hist_30.index, y=hist_30['CALL_Wall'], mode='lines+markers',
        name='CALL Wall (阻力线)', line=dict(color='#FF4B4B', width=2), marker=dict(size=5)
    ))
    fig_wall_trend.add_trace(go.Scatter(
        x=hist_30.index, y=hist_30['Close'], mode='lines',
        name='标的实际股价 (Spot)', line=dict(color='#FACC15', width=2.5)
    ))
    fig_wall_trend.add_trace(go.Scatter(
        x=hist_30.index, y=hist_30['PUT_Wall'], mode='lines+markers',
        name='PUT Wall (防守支撑线)', line=dict(color='#00E676', width=2), marker=dict(size=5)
    ))

    fig_wall_trend.update_layout(
        template='plotly_dark', height=340,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15, 23, 42, 0.6)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(title="价格 ($)", gridcolor='rgba(255,255,255,0.08)'),
        xaxis=dict(gridcolor='rgba(255,255,255,0.05)')
    )
    st.plotly_chart(fig_wall_trend, use_container_width=True)

# ================= PAGE 3: TRADE EXECUTION & PLAN =================
elif page == "💼 3. Trade Execution & Plan":
    st.markdown(f"### 💼 {selected_ticker} 分批建仓与期权对冲执行计划")
    st.markdown("在此模块管理当前标的的限价挂单、分批仓位分配以及极端行情应急预案。")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🎯 当前分批挂单目标价设置")
        current_orders = st.session_state.user_limit_orders.get(selected_ticker, [146.20, 142.40, 131.40])
        
        o1 = st.number_input("第一档主力防线 ($)", value=float(current_orders[0]), format="%.2f")
        o2 = st.number_input("第二档加仓防线 ($)", value=float(current_orders[1]), format="%.2f")
        o3 = st.number_input("第三档黄金坑底仓 ($)", value=float(current_orders[2]), format="%.2f")
        
        if st.button("保存挂单参数"):
            st.session_state.user_limit_orders[selected_ticker] = [o1, o2, o3]
            st.success("挂单参数已成功保存并同步！")
            
    with col2:
        st.markdown("#### 🛡️ 风险风控备忘检查")
        st.info(f"当前标的收盘价: **${latest_close:.2f}**")
        st.markdown("""
        * **纪律一**：单笔建仓总资金控制在总仓位的 20% 以内。
        * **纪律二**：若跌破核心 `PUT Wall`，启动期权展期或牛市看跌价差（Bull Put Spread）对冲。
        * **纪律三**：避免情绪化追高，严守金字塔分批挂单原则。
        """)
