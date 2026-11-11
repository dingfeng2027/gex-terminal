import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

# 1. 页面基本配置
st.set_page_config(
    page_title="CAPITAL QUANT v2 - Pro Terminal",
    page_icon="📈",
    layout="wide"
)

# 2. 初始化全局状态
if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["NVDA", "GOOGL", "TSM", "AMD", "MSFT", "META", "AMZN", "AAPL", "ASML", "TSLA", "VUAG.L", "EQQQ.L"]

if "nav_mode" not in st.session_state:
    st.session_state.nav_mode = "Market Watch"

if "selected_stock" not in st.session_state:
    st.session_state.selected_stock = "NVDA"

if "timeframe" not in st.session_state:
    st.session_state.timeframe = "1年"

# --- 数据抓取函数 ---
@st.cache_data(ttl=300)
def fetch_stock_data(ticker_symbol, period_str):
    try:
        ticker = yf.Ticker(ticker_symbol)
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
            hist = ticker.history(period="1y")
            
        spot_price = hist['Close'].iloc[-1]
        hist_1y = ticker.history(period="1y")
        if hist_1y.empty:
            hist_1y = hist
            
        return spot_price, hist, hist_1y
    except Exception as e:
        return None, None, None


# ==========================================
# 顶部导航栏
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
            st.markdown(f"**{h}**")
            
    st.markdown("<hr style='margin: 5px 0px 10px 0px;'>", unsafe_allow_html=True)
    
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
                
                row_cols = st.columns(cols_width)
                with row_cols[0]:
                    clean_sym = symbol.split('.')[0]
                    if st.button(f"🟡 {clean_sym}", key=f"nav_{symbol}"):
                        st.session_state.selected_stock = symbol
                        st.session_state.nav_mode = "Stock Analysis & Options Chain"
                        st.rerun()
                with row_cols[1]:
                    st.markdown(f"${curr:.2f}")
                with row_cols[2]:
                    st.markdown(f"${prev:.2f}")
                with row_cols[3]:
                    color_txt = "🟢" if pct >= 0 else "🔴"
                    st.markdown(f"{color_txt} {pct:+.2f}%")
                with row_cols[4]:
                    st.markdown(f"{change:+.2f}")
                with row_cols[5]:
                    st.markdown(f"${ma20:.2f}")
                with row_cols[6]:
                    st.markdown(f"${ma50:.2f}")
                with row_cols[7]:
                    st.markdown(f"${ma200:.2f}")
                with row_cols[8]:
                    st.markdown(f"${high_52w:.2f}")
                with row_cols[9]:
                    st.markdown(f"${low_52w:.2f}")
                with row_cols[10]:
                    st.markdown(f"{rsi:.1f}")
                with row_cols[11]:
                    if st.button("🗑️", key=f"del_{symbol}"):
                        st.session_state.watchlist.remove(symbol)
                        st.rerun()
        except Exception as e:
            continue


# ==========================================
# 视图二：Stock Analysis 终端
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
    
    spot, hist_df, hist_1y = fetch_stock_data(selected_analysis_stock, st.session_state.timeframe)
    
    if spot is None or hist_df is None:
        st.error(f"Failed to load market data for {selected_analysis_stock}.")
    else:
        # 左右两栏布局
        col_chart, col_price_level = st.columns([2.8, 1.2])
        
        with col_chart:
            st.markdown(f"#### 📈 **{selected_analysis_stock} — Price Trend**")
            
            fig_p, ax_p = plt.subplots(figsize=(8, 3.5))
            ax_p.plot(hist_df.index, hist_df['Close'], label='Close Price', color='#00d2ff', linewidth=2.0)
            ax_p.fill_between(hist_df.index, hist_df['Close'], hist_df['Close'].min() * 0.95, color='#0284c7', alpha=0.15)
            
            ax_p.set_facecolor('#0d111a')
            fig_p.patch.set_facecolor('#060913')
            ax_p.tick_params(colors='#9ca3af', labelsize=9)
            ax_p.grid(True, color='#1f2937', alpha=0.5, linestyle=':')
            for spine in ax_p.spines.values():
                spine.set_color('#374151')
                
            st.pyplot(fig_p)
            
            # 图表下方的时间周期按钮
            tf_cols = st.columns(6)
            tf_list = ["1天", "1个星期", "1个月", "3个月", "1年", "全部"]
            for i, tf in enumerate(tf_list):
                with tf_cols[i]:
                    if st.button(tf, key=f"tf_{tf}", use_container_width=True):
                        st.session_state.timeframe = tf
                        st.rerun()

        with col_price_level:
            st.markdown("#### 📊 **PRICE LEVEL**")
            st.markdown("---")
            
            # 严格控制间距的 PRICE LEVEL 列表
            percentages = [20, 15, 12, 10, 8, 6, 0, -6, -8, -10, -12, -15, -20]
            for p in percentages:
                target_price = spot * (1 + p / 100.0)
                if p == 0:
                    st.info(f"**CURRENT: ${target_price:.2f}**")
                else:
                    label_str = f"{p:+d}%"
                    st.write(f"{label_str}  ->  ${target_price:.2f}")

        st.markdown("---")
        
        # ==========================================
        # KEY DATA 关键数据面板（严格分成 4 个部分，使用原生安全组件）
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

        with st.container():
            # 第一部分：价格与变动摘要 (4个指标)
            st.markdown("**1. 价格与变动摘要**")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("今天价格", f"${curr_price:.2f}")
            c2.metric("昨天价格", f"${prev_price:.2f}")
            c3.metric("变动参数", f"{chg_val:+.2f}")
            c4.metric("变动指数", f"{chg_pct:+.2f}%")
            
            st.markdown("---")
            
            # 第二部分：均线数据 (3个指标)
            st.markdown("**2. 均线数据 (Moving Averages)**")
            m1, m2, m3 = st.columns(3)
            m1.metric("20日均价", f"${ma20_val:.2f}")
            m2.metric("50日均价", f"${ma50_val:.2f}")
            m3.metric("200日均价", f"${ma200_val:.2f}")
            
            st.markdown("---")
            
            # 第三部分：年内高低 (2个指标)
            st.markdown("**3. 年内高低 (52-Week Range)**")
            r1, r2 = st.columns(2)
            r1.metric("年内最高", f"${high_year:.2f}")
            r2.metric("年内最低", f"${low_year:.2f}")
            
            st.markdown("---")
            
            # 第四部分：购买指数 (1个指标)
            st.markdown("**4. 购买指数 (Buying Index)**")
            b1, _ = st.columns([1, 3])
            b1.metric("购买指数 (RSI 14)", f"{rsi_v:.1f}")
