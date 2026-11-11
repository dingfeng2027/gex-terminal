import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm
import matplotlib.pyplot as plt

# 1. 页面基本配置与全局 CSS 样式
st.set_page_config(
    page_title="CAPITAL QUANT v2 - Pro Terminal",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
<style>
    html, body, [class*="css"] {
        font-size: 18px !important;
    }
    .big-price {
        font-size: 20px !important;
        font-weight: 700 !important;
    }
    div.stVerticalBlock > div.stElementContainer {
        margin-bottom: -12px !important;
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

# --- 辅助计算函数：Black-Scholes Gamma ---
def get_bs_gamma(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return norm.pdf(d1) / (S * sigma * np.sqrt(T))

# --- 期权 GEX 与期权链核心函数（不使用会导致序列化报错的缓存） ---
def fetch_gex_and_chain(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        history = ticker.history(period="1y")
        if history.empty:
            return None, None, None, None, None, None, None, None, None
            
        spot_price = history['Close'].iloc[-1]
        expirations = ticker.options
        if not expirations:
            return spot_price, None, None, None, None, None, None, None, history
            
        nearest_exp = expirations[0]
        opt_chain = ticker.option_chain(nearest_exp)
        
        all_options = []
        today = pd.Timestamp.today()
        r = 0.045
        
        for exp in expirations[:5]:
            t_days = (pd.to_datetime(exp) - today).days
            if t_days <= 0:
                continue
            T = t_days / 365.0
            opt = ticker.option_chain(exp)
            
            calls = opt.calls.copy()
            calls['is_call'] = True
            calls['T'] = T
            puts = opt.puts.copy()
            puts['is_call'] = False
            puts['T'] = T
            all_options.append(calls)
            all_options.append(puts)
            
        if not all_options:
            return spot_price, None, None, None, None, None, nearest_exp, opt_chain, history
            
        df = pd.concat(all_options, ignore_index=True)
        df = df[df['openInterest'] > 0].copy()
        df = df[(df['strike'] >= spot_price * 0.7) & (df['strike'] <= spot_price * 1.3)]
        
        gex_records = []
        for _, row in df.iterrows():
            iv = row['impliedVolatility']
            K = row['strike']
            T = row['T']
            oi = row['openInterest']
            is_call = row['is_call']
            
            gamma = get_bs_gamma(spot_price, K, T, r, iv)
            dollar_gamma = gamma * oi * 100 * (spot_price ** 2) * 0.01
            if not is_call:
                dollar_gamma = -dollar_gamma
                
            gex_records.append({'strike': K, 'gex': dollar_gamma})
            
        df_gex = pd.DataFrame(gex_records)
        gex_by_strike = df_gex.groupby('strike')['gex'].sum().reset_index().sort_values('strike')
        
        calls_above = gex_by_strike[gex_by_strike['strike'] >= spot_price]
        call_wall = calls_above.loc[calls_above['gex'].idxmax()]['strike'] if not calls_above.empty else None
        
        puts_below = gex_by_strike[gex_by_strike['strike'] <= spot_price]
        put_wall = puts_below.loc[puts_below['gex'].idxmin()]['strike'] if not puts_below.empty else None
        
        gex_by_strike['cum_gex'] = gex_by_strike['gex'].cumsum()
        zero_crossings = np.where(np.diff(np.sign(gex_by_strike['cum_gex'])))[0]
        gamma_flip = gex_by_strike.iloc[zero_crossings[0]]['strike'] if len(zero_crossings) > 0 else spot_price
        
        return spot_price, call_wall, put_wall, gamma_flip, gex_by_strike, gex_by_strike['gex'].sum(), nearest_exp, opt_chain, history
    except Exception as e:
        return None, None, None, None, None, None, None, None, None


# ==========================================
# 顶部导航栏切换
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
                
                # 点击公司名称按钮，直接无缝跳转到第二页分析该股票
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
# 视图二：Stock Analysis & Options Chain 深度终端
# ==========================================
else:
    st.markdown("### 🎯 **Stock Analysis & Options Microstructure Terminal**")
    
    if st.session_state.selected_stock not in st.session_state.watchlist:
        st.session_state.selected_stock = st.session_state.watchlist[0]
        
    selected_analysis_stock = st.selectbox(
        "Select Stock for Deep Analysis", 
        st.session_state.watchlist,
        index=st.session_state.watchlist.index(st.session_state.selected_stock)
    )
    st.session_state.selected_stock = selected_analysis_stock
    
    with st.spinner(f"Loading data and options chain for {selected_analysis_stock}..."):
        spot, c_wall, p_wall, g_flip, df_gex, net_gex, nearest_exp, opt_chain, hist_df = fetch_gex_and_chain(selected_analysis_stock)
        
    if spot is None:
        st.error(f"Failed to load data for {selected_analysis_stock}.")
    else:
        tab_chart, tab_gex, tab_chain = st.tabs([
            "📈 Price Chart & MA", 
            "📊 Gamma & Walls Analysis", 
            f"📋 Options Chain Details ({nearest_exp})"
        ])
        
        with tab_chart:
            st.markdown(f"#### 📉 {selected_analysis_stock} — Daily Price & Moving Averages")
            fig_p, ax_p = plt.subplots(figsize=(10, 4))
            ax_p.plot(hist_df.index, hist_df['Close'], label='Close Price', color='cyan', linewidth=1.5)
            if len(hist_df) >= 20:
                ax_p.plot(hist_df.index, hist_df['Close'].rolling(20).mean(), label='MA20', color='yellow', linestyle='--')
            if len(hist_df) >= 50:
                ax_p.plot(hist_df.index, hist_df['Close'].rolling(50).mean(), label='MA50', color='orange', linestyle='--')
            if len(hist_df) >= 200:
                ax_p.plot(hist_df.index, hist_df['Close'].rolling(200).mean(), label='MA200', color='magenta', linestyle='--')
            ax_p.set_ylabel("Price ($)")
            ax_p.legend(loc='upper left')
            ax_p.grid(True, alpha=0.3)
            st.pyplot(fig_p)
            
            st.markdown("#### 📊 Price Level Percentage Ladders")
            ladder_cols = st.columns(6)
            percentages = [30, 20, 10, 5, -5, -10]
            for i, p in enumerate(percentages):
                val = spot * (1 + p / 100.0)
                with ladder_cols[i]:
                    st.metric(f"{p:+d}%", f"${val:.2f}")

        with tab_gex:
            net_mil = net_gex / 1e6 if net_gex else 0
            st.markdown(f"### 💡 Market Regime Diagnosis: `{net_mil:+.2f} M$ / 1% Move`")
            if net_mil > 0:
                st.success("【Positive Gamma Regime】：Dealers trade mean-reversion. Low volatility and range-bound defensive structure.")
            else:
                st.warning("【Negative Gamma Regime】：Dealers chase momentum. High volatility breakout or acceleration risk.")
                
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Spot Price", f"${spot:.2f}")
            m2.metric("Call Wall (Resistance)", f"${c_wall}" if c_wall else "N/A")
            m3.metric("Put Wall (Support)", f"${p_wall}" if p_wall else "N/A")
            m4.metric("Gamma Flip Line", f"${g_flip:.2f}" if g_flip else "N/A")
                
            if df_gex is not None and not df_gex.empty:
                st.markdown("### 📊 Dealer Net Gamma Exposure Profile (GEX by Strike)")
                fig, ax = plt.subplots(figsize=(10, 4))
                colors = ['green' if x >= 0 else 'red' for x in df_gex['gex']]
                ax.bar(df_gex['strike'], df_gex['gex'] / 1e6, color=colors, width=1.0, alpha=0.7)
                
                ax.axvline(spot, color='blue', linestyle='--', linewidth=2, label=f'Spot: ${spot:.2f}')
                if c_wall:
                    ax.axvline(c_wall, color='darkgreen', linestyle=':', linewidth=2, label=f'Call Wall: ${c_wall}')
                if p_wall:
                    ax.axvline(p_wall, color='darkred', linestyle=':', linewidth=2, label=f'Put Wall: ${p_wall}')
                if g_flip:
                    ax.axvline(g_flip, color='orange', linestyle='-', linewidth=2, label=f'Gamma Flip: ${g_flip:.2f}')
                    
                ax.set_xlabel("Strike Price ($)")
                ax.set_ylabel("Net GEX ($ Millions)")
                ax.legend(loc='upper right')
                ax.grid(True, alpha=0.3)
                st.pyplot(fig)
                
        with tab_chain:
            st.markdown(f"### 🟢 Call Options (Calls) — Expiry: {nearest_exp}")
            if opt_chain is not None and not opt_chain.calls.empty:
                calls_df = opt_chain.calls[['strike', 'lastPrice', 'bid', 'ask', 'impliedVolatility', 'volume', 'openInterest']]
                calls_df.columns = ['Strike ($)', 'Last ($)', 'Bid ($)', 'Ask ($)', 'IV', 'Volume', 'Open Interest']
                st.dataframe(calls_df, use_container_width=True)
            else:
                st.info("No Call options available.")
                
            st.markdown(f"### 🔴 Put Options (Puts) — Expiry: {nearest_exp}")
            if opt_chain is not None and not opt_chain.puts.empty:
                puts_df = opt_chain.puts[['strike', 'lastPrice', 'bid', 'ask', 'impliedVolatility', 'volume', 'openInterest']]
                puts_df.columns = ['Strike ($)', 'Last ($)', 'Bid ($)', 'Ask ($)', 'IV', 'Volume', 'Open Interest']
                st.dataframe(puts_df, use_container_width=True)
            else:
                st.info("No Put options available.")
