import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="CAPITAL QUANT Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Dark Theme Custom Styling
st.markdown("""
    <style>
    .stApp { background-color: #0b0f19; color: #f8fafc; }
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        padding: 18px;
        border-radius: 10px;
        text-align: center;
    }
    .metric-value { font-size: 26px; font-weight: bold; color: #38bdf8; }
    .metric-label { font-size: 13px; color: #94a3b8; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# ================= SIDEBAR & NAVIGATION =================
st.sidebar.title("⚡ CAPITAL QUANT")
st.sidebar.markdown("---")
page = st.sidebar.radio("选择终端模块", ["📊 1. Price Chart & Levels", "🔍 2. Options Intelligence"])

watchlist = st.sidebar.selectbox("选择监控标的", ["NVDA", "TSLA", "AAPL", "MSFT", "GOOGL"])

@st.cache_data(ttl=3600)
def load_data(ticker_symbol):
    try:
        df = yf.download(ticker_symbol, period="6mo", interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception:
        return pd.DataFrame()

df = load_data(watchlist)
if df.empty:
    st.error(f"无法获取 {watchlist} 的实时数据，请检查网络。")
    st.stop()

latest_close = float(df['Close'].iloc[-1])

# ================= PAGE 1: PRICE CHART & LEVELS =================
if page == "📊 1. Price Chart & Levels":
    st.markdown(f"### 📊 {watchlist} 价格行为与机构限价位监控终端")
    
    # 顶部指标卡
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>当前收盘 (Spot)</div><div class='metric-value'>${latest_close:.2f}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>20日均线 (MA20)</div><div class='metric-value'>${df['Close'].rolling(20).mean().iloc[-1]:.2f}</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>建议第一主力支撑</div><div class='metric-value' style='color:#00E676;'>${latest_close * 0.90:.2f}</div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>建议第一阻力目标</div><div class='metric-value' style='color:#FF4B4B;'>${latest_close * 1.08:.2f}</div></div>", unsafe_allow_html=True)

    st.markdown("---")

    # 主图绘制
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
                      annotation_text=f"限价买入位 -{(1-lvl)*100:.1f}% (${target_price:.2f})", 
                      annotation_position="bottom right")

    # === 新增功能 1：Price Chart 叠加期权墙通道开关 ===
    show_walls = st.sidebar.checkbox("图表叠加机构期权防守通道", value=True)
    if show_walls:
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
    st.markdown(f"### 🔍 {watchlist} 期权结构、Gamma 敞口与机构防守墙情报")
    
    # 模拟真实期权结构计算
    gamma_flip = round(latest_close * 0.92, 2)
    put_wall = round(latest_close * 0.86, 2)
    call_wall = round(latest_close * 1.04, 2)
    max_pain = round(latest_close * 1.01, 2)

    # 模块 3: 期权摘要卡片
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
    
    # 绘制模拟 Gamma 分布图
    strikes = np.linspace(latest_close * 0.85, latest_close * 1.15, 13)
    gamma_values = np.random.randint(1000, 1600, size=len(strikes))
    
    fig_gamma = go.Figure(go.Bar(
        x=[f"${s:.2f}" for s in strikes], y=gamma_values,
        marker_color=['#38bdf8' if s >= latest_close else '#3b82f6' for s in strikes]
    ))
    fig_gamma.update_layout(
        template='plotly_dark', height=320,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15, 23, 42, 0.6)'
    )
    st.plotly_chart(fig_gamma, use_container_width=True)

    st.markdown("---")

    # === 新增功能 2：近 30 日 CALL / PUT Wall 历史爬升轨迹图 ===
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
