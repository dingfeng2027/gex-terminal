import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm
import matplotlib.pyplot as plt

# 1. 页面基本配置与全局专业暗色终端样式
st.set_page_config(
    page_title="CAPITAL QUANT v2 - Pro Terminal",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
<style>
    html, body, [class*="css"] {
        font-size: 16px !important;
        background-color: #060913;
        color: #f3f4f6;
    }
    .big-price {
        font-size: 20px !important;
        font-weight: 700 !important;
    }
    div.stVerticalBlock > div.stElementContainer {
        margin-bottom: -6px !important;
    }
</style>
""", unsafe_allow_html=True)

# 2. 初始化全局状态
if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["NVDA", "GOOGL", "TSM", "AMD", "MSFT", "META", "AMZN", "AAPL", "ASML", "TSLA", "VUAG.L", "EQQQ.L"]

if "nav_mode" not in st.session_state:
    st.session_state.nav_mode = "Market Watch"

if "selected_stock" not in st.session_state:
    st.session_state.selected_stock = "NVDA"

if "timeframe" not in st.session_state:
    st.session_state.timeframe = "1年"

# --- 数据抓取核心函数 ---
@st.cache_data(ttl=300)
def fetch_stock_data(ticker_symbol, period_str):
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # 映射时间周期
        p_map = {
            "1天": "1d",
            "1个星期": "5d",
            "1个月": "1mo",
            "3个月": "3mo",
            "1年": "1y",
            "全部": "max"
        }
        yf_period = p_map.get(period_str, "1y")
        
        hist = ticker.history(period=yf_period)
        if hist.empty:
            return None, None, None
            
        spot_price = hist['Close'].iloc[-1]
        
        # 获取完整1年历史用于计算均线和高低点
        hist_1y = ticker.history(period="1y")
        if hist_1y.empty:
            hist_1y = hist
            
        return spot_price, hist, hist_1y
    except Exception as e:
        return None, None, None


# ==========================================
# 顶部全局导航栏
# ==========================================
st.markdown("### 📊 CAPITAL QUANT v2 &nbsp; | &nbsp; **Pro Trading Terminal**")

nav_options = ["Market Watch", "Stock Analysis & Options Chain"]
nav_tab = st.radio(
    "Navigation", 
    nav_options, 
    index=nav_options.index(st.session_state.nav_mode) if st.session_state.nav_mode in nav_options else 0,
    horizontal=True,
    label_visibility="collapsed"
)
st.session_state.nav_mode = nav_tab

st.markdown("---")

# ==========================================
# 视图一：Market Watch 看板
# ==========================================
if st.session_state.nav_mode == "Market Watch":
    col_input, col_add, col_update = st.columns([4, 1.5, 1.5])
    with col_input:
        new_ticker = st.text_input("Add Ticker", placeholder="e.g. NVDA, AAPL", label_visibility="collapsed").upper()
    with col_add:
        if st.button("➕ ADD TICKER", use_container_width=True):
            if new_ticker and new_ticker not in st.session_state.watchlist:
                st.session_state.watchlist.append(new_ticker)
                st.rerun()
    with col_update:
        if st.button("🔄 UPDATE ALL", use_container_width=True):
            st.rerun()

    st.markdown("#### 📌 Portfolio & Watchlist Matrix")
    
    cols_width = [1.3, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1, 0.8]
    
    h_cols = st.columns(cols_width)
    headers = [
        "公司名称", "今天价格", "昨天价格", "价格变动", "变动点数", 
        "20日均价", "50日均价", "200日均价", "年内最高", "年内最低", 
        "购买指数", "删除"
    ]
    
    for i, h in enumerate(headers):
        with h_cols[i]:
            st.markdown(f"<span style='font-size:16px; font-weight:bold;'>{h}</span>", unsafe_allow_html=True)
            
    st.markdown("<hr style='margin: 5px 0px 10px 0px;'>", unsafe_allow_html=True)
    
    gainers_count = 0
    losers_count = 0
    
    for symbol in st.session_state.watchlist:
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="1y")
            if not hist.empty and len(hist) >= 1:
                curr = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2] if len(hist) > 1 else curr
                
                if pd.isna(curr) or pd.isna(prev):
                    continue
                    
                change = curr - prev
                pct = (change / prev) * 100 if prev != 0 else 0
                
                ma20 = hist['Close'].rolling(20).mean().iloc[-1] if len(hist) >= 20 else curr
                ma50 = hist['Close'].rolling(50).mean().iloc[-1] if len(hist) >= 50 else curr
                ma200 = hist['Close'].rolling(200).mean().iloc[-1] if len(hist) >= 200 else curr
                
                high_52w = hist['High'].max()
                low_52w = hist['Low'].min()
                
                delta_series = hist['Close'].diff()
                gain = (delta_series.where(delta_series > 0, 0)).rolling(14).mean().iloc[-1]
                loss = (-delta_series.where(delta_series < 0, 0)).rolling(14).mean().iloc[-1]
                rs = gain / loss if loss != 0 else 1
                rsi = 100 - (100 / (1 + rs)) if not pd.isna(rs) else 50.0
                
                if pct >= 0:
                    gainers_count += 1
                else:
                    losers_count += 1
                    
                row_cols = st.columns(cols_width)
                
                # 点击公司名称，无缝跳转到第二页分析该股票
                with row_cols[0]:
                    clean_sym = symbol.split('.')[0]
                    if st.button(f"🟡 {clean_sym}", key=f"nav_{symbol}"):
                        st.session_state.selected_stock = symbol
                        st.session_state.nav_mode = "Stock Analysis & Options Chain"
                        st.rerun()
                with row_cols[1]:
                    st.markdown(f"<span class='big-price'>${curr:.2f}</span>", unsafe_allow_html=True)
                with row_cols[2]:
                    st.markdown(f"<span class='big-price'>${prev:.2f}</span>", unsafe_allow_html=True)
                with row_cols[3]:
                    color_txt = "🟢" if pct >= 0 else "🔴"
                    st.markdown(f"<span style='font-size:17px; font-weight:bold;'>{color_txt} {pct:+.2f}%</span>", unsafe_allow_html=True)
                with row_cols[4]:
                    st.markdown(f"<span style='font-size:17px; font-weight:bold;'>{change:+.2f}</span>", unsafe_allow_html=True)
                with row_cols[5]:
                    st.markdown(f"<span style='font-size:17px;'>${ma20:.2f}</span>", unsafe_allow_html=True)
                with row_cols[6]:
                    st.markdown(f"<span style='font-size:17px;'>${ma50:.2f}</span>", unsafe_allow_html=True)
                with row_cols[7]:
                    st.markdown(f"<span style='font-size:17px;'>${ma200:.2f}</span>", unsafe_allow_html=True)
                with row_cols[8]:
                    st.markdown(f"<span style='font-size:17px;'>${high_52w:.2f}</span>", unsafe_allow_html=True)
                with row_cols[9]:
                    st.markdown(f"<span style='font-size:17px;'>${low_52w:.2f}</span>", unsafe_allow_html=True)
                with row_cols[10]:
                    badge_color = "green" if rsi < 70 else "red"
                    st.markdown(f":{badge_color}[<span style='font-size:18px; font-weight:bold;'>{rsi:.1f}</span>]", unsafe_allow_html=True)
                with row_cols[11]:
                    if st.button("🗑️", key=f"del_{symbol}"):
                        st.session_state.watchlist.remove(symbol)
                        st.rerun()
                        
        except Exception as e:
            continue
            
    st.markdown("---")
    s1, s2, s3 = st.columns(3)
    s1.success(f"🟢 Gainers: {gainers_count}")
    s2.error(f"🔴 Losers: {losers_count}")
    s3.info(f"📊 Total Symbols: {len(st.session_state.watchlist)}")


# ==========================================
# 视图二：Stock Analysis 终端（完全重新编写的现代化布局）
# ==========================================
else:
    c_head1, c_head2 = st.columns([3, 1])
    with c_head1:
        st.markdown("### 🎯 **Stock Analysis & Limit Orders Terminal**")
    with c_head2:
        if st.session_state.selected_stock not in st.session_state.watchlist:
            st.session_state.selected_stock = st.session_state.watchlist[0]
            
        selected_analysis_stock = st.selectbox(
            "Select Stock", 
            st.session_state.watchlist,
            index=st.session_state.watchlist.index(st.session_state.selected_stock),
            label_visibility="collapsed"
        )
        st.session_state.selected_stock = selected_analysis_stock
        
    st.markdown("---")
    
    # 获取当前选中股票的数据
    spot, hist_df, hist_1y = fetch_stock_data(selected_analysis_stock, st.session_state.timeframe)
    
    if spot is None or hist_df is None:
        st.error(f"Failed to load market data for {selected_analysis_stock}.")
    else:
        # 黄金比例左右两栏：左侧 Trading 212 图表与时间周期按钮，右侧 PRICE LEVEL 阶梯挂单面板
        col_chart, col_price_level = st.columns([2.7, 1.2])
        
        with col_chart:
            st.markdown(f"#### 📈 **{selected_analysis_stock} — Price Trend & Trading 212 Chart**")
            
            # 绘制 Trading 212 风格的单根青色走势线+半透明渐变面积图
            fig_p, ax_p = plt.subplots(figsize=(8, 4.2))
            
            ax_p.plot(hist_df.index, hist_df['Close'], label='Close Price', color='#00d2ff', linewidth=2.2)
            ax_p.fill_between(hist_df.index, hist_df['Close'], hist_df['Close'].min() * 0.95, color='#0284c7', alpha=0.18)
            
            ax_p.set_facecolor('#0d111a')
            fig_p.patch.set_facecolor('#060913')
            ax_p.tick_params(colors='#9ca3af', labelsize=10)
            ax_p.xaxis.label.set_color('#9ca3af')
            ax_p.yaxis.label.set_color('#9ca3af')
            ax_p.grid(True, color='#1f2937', alpha=0.6, linestyle=':')
            
            for spine in ax_p.spines.values():
                spine.set_color('#374151')
                
            st.pyplot(fig_p)
            
            # 图表下方可点击的时间周期按钮
            st.markdown("<div style='font-size: 14px; color: #9ca3af; margin-bottom: 4px;'>Timeframe Selection:</div>", unsafe_allow_html=True)
            tf_cols = st.columns(6)
            tf_list = ["1天", "1个星期", "1个月", "3个月", "1年", "全部"]
            
            for i, tf in enumerate(tf_list):
                with tf_cols[i]:
                    btn_type = "primary" if st.session_state.timeframe == tf else "secondary"
                    if st.button(tf, key=f"tf_{tf}", use_container_width=True):
                        st.session_state.timeframe = tf
                        st.rerun()

        with col_price_level:
            st.markdown("#### 📊 **PRICE LEVEL** (Limit Orders)")
            st.markdown("<hr style='margin: 0px 0px 8px 0px; border-color: #1f2937;'>", unsafe_allow_html=True)
            
            # 要求的上下波动挂单百分比：20%, 15%, 12%, 10%, 8%, 6%, CURRENT, 以及负向
            percentages = [20, 15, 12, 10, 8, 6, 0, -6, -8, -10, -12, -15, -20]
            
            for p in percentages:
                target_price = spot * (1 + p / 100.0)
                if p == 0:
                    st.markdown(f"""
                    <div style="background-color: #1e3a8a; padding: 7px 12px; border-radius: 5px; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #3b82f6;">
                        <span style="color: #facc15; font-weight: bold; font-size: 14px;">CURRENT</span>
                        <span style="color: #facc15; font-weight: bold; font-size: 15px;">${target_price:.2f}</span>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    label_str = f"{p:+d}%"
                    st.markdown(f"""
                    <div style="background-color: #111827; border: 1px solid #1f2937; padding: 5px 12px; border-radius: 4px; margin-bottom: 3px; display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: {'#34d399' if p > 0 else '#f87171'}; font-weight: bold; font-size: 13px;">{label_str}</span>
                        <span style="color: #ffffff; font-weight: 500; font-size: 14px;">${target_price:.2f}</span>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # ==========================================
        # 3. KEY DATA 关键数据面板（严格分成 4 个部分纵向排列）
        # ==========================================
        st.markdown("#### 📌 **KEY DATA**")
        
        curr_price = spot
        prev_price = hist_1y['Close'].iloc[-2] if len(hist_1y) > 1 else spot
        chg_val = curr_price - prev_price
        chg_pct = (chg_val / prev_price) * 100 if prev_price != 0 else 0
        
        ma20_val = hist_1y['Close'].rolling(20).mean().iloc[-1] if len(hist_1y) >= 20 else curr_price
        ma50_val = hist_1y['Close'].rolling(50).mean().iloc[-1] if len(hist_1y) >= 50 else curr_price
        ma200_val = hist_1y['Close'].rolling(200).mean().iloc[-1] if len(hist_1y) >= 200 else curr_price
        
        high_year = hist_1y['High'].max()
        low_year = hist_1y['Low'].min()
        
        delta_s = hist_1y['Close'].diff()
        gain_s = (delta_s.where(delta_s > 0, 0)).rolling(14).mean().iloc[-1]
        loss_s = (-delta_s.where(delta_s < 0, 0)).rolling(14).mean().iloc[-1]
        rsi_v = 100 - (100 / (1 + (gain_s / loss_s))) if loss_s != 0 else 50.0

        st.markdown(f"""
        <div style="background-color: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 16px 20px;">
            <!-- 第一部分：4个指标 -->
            <div style="font-weight: bold; color: #38bdf8; font-size: 14px; margin-bottom: 6px;">1. Price & Change Summary</div>
            <table style="width: 100%; color: #f3f4f6; font-size: 15px; border-collapse: collapse; margin-bottom: 12px;">
                <tr>
                    <td style="padding: 6px 0; width: 25%;"><strong>今天价格:</strong> <span style="color: #38bdf8; font-weight: bold;">${curr_price:.2f}</span></td>
                    <td style="padding: 6px 0; width: 25%;"><strong>昨天价格:</strong> <span>${prev_price:.2f}</span></td>
                    <td style="padding: 6px 0; width: 25%;"><strong>变动参数:</strong> <span style="color: {'#34d399' if chg_val >= 0 else '#f87171'}; font-weight: bold;">{chg_val:+.2f}</span></td>
                    <td style="padding: 6px 0; width: 25%;"><strong>变动指数:</strong> <span style="color: {'#34d399' if chg_pct >= 0 else '#f87171'}; font-weight: bold;">{chg_pct:+.2f}%</span></td>
                </tr>
            </table>
            
            <hr style="border-color: #1f2937; margin: 8px 0;">
            
            <!-- 第二部分：3个指标 (均价) -->
            <div style="font-weight: bold; color: #38bdf8; font-size: 14px; margin-bottom: 6px;">2. Moving Averages</div>
            <table style="width: 100%; color: #f3f4f6; font-size: 15px; border-collapse: collapse; margin-bottom: 12px;">
                <tr>
                    <td style="padding: 6px 0; width: 33%;"><strong>20日均价:</strong> <span>${ma20_val:.2f}</span></td>
                    <td style="padding: 6px 0; width: 33%;"><strong>50日均价:</strong> <span>${ma50_val:.2f}</span></td>
                    <td style="padding: 6px 0; width: 33%;"><strong>200日均价:</strong> <span>${ma200_val:.2f}</span></td>
                </tr>
            </table>
            
            <hr style="border-color: #1f2937; margin: 8px 0;">
            
            <!-- 第三部分：2个指标 (年内高低) -->
            <div style="font-weight: bold; color: #38bdf8; font-size: 14px; margin-bottom: 6px;">3. 52-Week Range</div>
            <table style="width: 100%; color: #f3f4f6; font-size: 15px; border-collapse: collapse; margin-bottom: 12px;">
                <tr>
                    <td style="padding: 6px 0; width: 50%;"><strong>年内最高:</strong> <span style="color: #34d399; font-weight: bold;">${high_year:.2f}</span></td>
                    <td style="padding: 6px 0; width: 50%;"><strong>年内最低:</strong> <span style="color: #f87171; font-weight: bold;">${low_year:.2f}</span></td>
                </tr>
            </table>
            
            <hr style="border-color: #1f2937; margin: 8px 0;">
            
            <!-- 第四部分：1个指标 (购买指数) -->
            <div style="font-weight: bold; color: #38bdf8; font-size: 14px; margin-bottom: 6px;">4. Buying Index</div>
            <table style="width: 100%; color: #f3f4f6; font-size: 15px; border-collapse: collapse;">
                <tr>
                    <td style="padding: 6px 0;"><strong>购买指数 (RSI 14):</strong> &nbsp;<span style="background-color: {'#065f46' if rsi_v < 70 else '#991b1b'}; color: white; padding: 3px 12px; border-radius: 4px; font-weight: bold;">{rsi_v:.1f}</span></td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)
