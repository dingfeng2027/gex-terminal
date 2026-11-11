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

# --- 期权 GEX 与期权链核心函数 ---
def fetch_gex_and_chain(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        history = ticker.history(period="1y")
        if history.empty:
            return None, None, None, None, None, None, None, None, None, None
            
        spot_price = history['Close'].iloc[-1]
        info = ticker.info
        
        expirations = ticker.options
        if not expirations:
            return spot_price, None, None, None, None, None, None, None, history, info
            
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
            return spot_price, None, None, None, None, None, nearest_exp, opt_chain, history, info
            
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
        
        return spot_price, call_wall, put_wall, gamma_flip, gex_by_strike, gex_by_strike['gex'].sum(), nearest_exp, opt_chain, history, info
    except Exception as e:
        return None, None, None, None, None, None, None, None, None, None


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
# 视图二：Stock Analysis 终端（完美契合截图364格式）
# ==========================================
else:
    c_head1, c_head2 = st.columns([3, 1])
    with c_head1:
        st.markdown("### 🎯 **Stock Analysis & Options Microstructure Terminal**")
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
        
    with st.spinner(f"Loading data for {selected_analysis_stock}..."):
        spot, c_wall, p_wall, g_flip, df_gex, net_gex, nearest_exp, opt_chain, hist_df, info_dict = fetch_gex_and_chain(selected_analysis_stock)
        
    if spot is None:
        st.error(f"Failed to load data for {selected_analysis_stock}.")
    else:
        # 顶级标签页切换
        sub_tab = st.radio(
            "Analysis View", 
            ["Price Chart & Price Level", "Gamma & Walls Analysis", f"Options Chain ({nearest_exp})"],
            horizontal=True,
            label_visibility="collapsed"
        )
        st.markdown("---")
        
        if sub_tab == "Price Chart & Price Level":
            # 黄金比例分栏：左侧 Trading 212 风格虚线图表，右侧精细价格阶梯挂单面板
            col_chart, col_price_level = st.columns([2.6, 1.2])
            
            with col_chart:
                st.markdown(f"#### 📉 {selected_analysis_stock} — Price Chart & Moving Averages")
                fig_p, ax_p = plt.subplots(figsize=(8, 4.5))
                # 使用 Trading 212 经典的明亮青色曲线和多重虚线 MA 均线
                ax_p.plot(hist_df.index, hist_df['Close'], label='Close Price', color='#00ffff', linewidth=1.8)
                if len(hist_df) >= 20:
                    ax_p.plot(hist_df.index, hist_df['Close'].rolling(20).mean(), label='MA20', color='#facc15', linestyle='--', linewidth=1.2)
                if len(hist_df) >= 50:
                    ax_p.plot(hist_df.index, hist_df['Close'].rolling(50).mean(), label='MA50', color='#fb923c', linestyle='--', linewidth=1.2)
                if len(hist_df) >= 200:
                    ax_p.plot(hist_df.index, hist_df['Close'].rolling(200).mean(), label='MA200', color='#e879f9', linestyle='--', linewidth=1.2)
                
                ax_p.set_facecolor('#0b0f19')
                fig_p.patch.set_facecolor('#0b0f19')
                ax_p.tick_params(colors='white')
                ax_p.xaxis.label.set_color('white')
                ax_p.yaxis.label.set_color('white')
                ax_p.legend(loc='upper left', fontsize='small', facecolor='#111827', edgecolor='none', labelcolor='white')
                ax_p.grid(True, color='#1f2937', alpha=0.5, linestyle=':')
                st.pyplot(fig_p)

            with col_price_level:
                st.markdown("#### 📊 **PRICE LEVEL** (Limit Orders)")
                st.markdown("<hr style='margin: 0px 0px 8px 0px;'>", unsafe_allow_html=True)
                
                # 按照你的要求：上下波动 20%, 15%, 12%, 10%, 8%, 6%, CURRENT, 以及负向
                percentages = [20, 15, 12, 10, 8, 6, 0, -6, -8, -10, -12, -15, -20]
                
                for p in percentages:
                    target_price = spot * (1 + p / 100.0)
                    if p == 0:
                        st.markdown(f"""
                        <div style="background-color: #1e3a8a; padding: 6px 10px; border-radius: 4px; margin-bottom: 3px; display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: #facc15; font-weight: bold; font-size: 14px;">CURRENT</span>
                            <span style="color: #facc15; font-weight: bold; font-size: 14px;">${target_price:.2f}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        label_str = f"{p:+d}%"
                        st.markdown(f"""
                        <div style="background-color: #111827; border: 1px solid #374151; padding: 4px 10px; border-radius: 3px; margin-bottom: 2px; display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: { '#34d399' if p > 0 else '#f87171' }; font-weight: bold; font-size: 13px;">{label_str}</span>
                            <span style="color: #ffffff; font-weight: 500; font-size: 13px;">${target_price:.2f}</span>
                        </div>
                        """, unsafe_allow_html=True)

            st.markdown("---")
            
            # 3. 完美放置在图表和 PRICE LEVEL 下方的 KEY DATA 关键数据面板
            st.markdown("#### 📌 **KEY DATA**")
            kd1, kd2, kd3 = st.columns(3)
            prev_close = hist_df['Close'].iloc[-2] if len(hist_df) > 1 else spot
            chg_pct = ((spot - prev_close) / prev_close) * 100
            chg_val = spot - prev_close
            
            with kd1:
                st.metric("Current Price", f"${spot:.2f}", f"{chg_val:+.2f} ({chg_pct:+.2f}%)")
                st.metric("Day High", f"${hist_df['High'].iloc[-1]:.2f}")
            with kd2:
                st.metric("52 Week High", f"${hist_df['High'].max():.2f}")
                st.metric("52 Week Low", f"${hist_df['Low'].min():.2f}")
            with kd3:
                pe_val = info_dict.get('trailingPE', 'N/A') if info_dict else 'N/A'
                pe_str = f"{pe_val:.2f}" if isinstance(pe_val, (int, float)) else "N/A"
                st.metric("P/E Ratio", pe_str)
                
                delta_s = hist_df['Close'].diff()
                gain_s = (delta_s.where(delta_s > 0, 0)).rolling(14).mean().iloc[-1]
                loss_s = (-delta_s.where(delta_s < 0, 0)).rolling(14).mean().iloc[-1]
                rsi_v = 100 - (100 / (1 + (gain_s / loss_s))) if loss_s != 0 else 50.0
                st.metric("RSI (14)", f"{rsi_v:.1f}")

        elif sub_tab == "Gamma & Walls Analysis":
            net_mil = net_gex / 1e6 if net_gex else 0
            st.markdown(f"### 💡 Market Regime: `{net_mil:+.2f} M$ / 1% Move`")
            if net_mil > 0:
                st.success("【Positive Gamma Regime】：Dealers trade mean-reversion. Defensive range-bound structure.")
            else:
                st.warning("【Negative Gamma Regime】：Dealers chase momentum. High volatility breakout risk.")
                
            gm1, gm2, gm3, gm4 = st.columns(4)
            gm1.metric("Spot", f"${spot:.2f}")
            gm2.metric("Call Wall", f"${c_wall}" if c_wall else "N/A")
            gm3.metric("Put Wall", f"${p_wall}" if p_wall else "N/A")
            gm4.metric("Gamma Flip", f"${g_flip:.2f}" if g_flip else "N/A")
                
            if df_gex is not None and not df_gex.empty:
                fig, ax = plt.subplots(figsize=(10, 4))
                colors = ['green' if x >= 0 else 'red' for x in df_gex['gex']]
                ax.bar(df_gex['strike'], df_gex['gex'] / 1e6, color=colors, width=1.0, alpha=0.7)
                ax.axvline(spot, color='blue', linestyle='--', label=f'Spot: ${spot:.2f}')
                if c_wall: ax.axvline(c_wall, color='darkgreen', linestyle=':', label=f'Call Wall: ${c_wall}')
                if p_wall: ax.axvline(p_wall, color='darkred', linestyle=':', label=f'Put Wall: ${p_wall}')
                ax.set_xlabel("Strike ($)")
                ax.set_ylabel("Net GEX ($M)")
                ax.legend(loc='upper right')
                ax.grid(True, alpha=0.3)
                st.pyplot(fig)
                
        else:
            st.markdown(f"#### 🟢 Call Options — Expiry: {nearest_exp}")
            if opt_chain is not None and not opt_chain.calls.empty:
                calls_df = opt_chain.calls[['strike', 'lastPrice', 'bid', 'ask', 'impliedVolatility', 'volume', 'openInterest']]
                calls_df.columns = ['Strike', 'Last', 'Bid', 'Ask', 'IV', 'Vol', 'OI']
                st.dataframe(calls_df, use_container_width=True)
            else:
                st.info("No Call options available.")
                
            st.markdown(f"#### 🔴 Put Options — Expiry: {nearest_exp}")
            if opt_chain is not None and not opt_chain.puts.empty:
                puts_df = opt_chain.puts[['strike', 'lastPrice', 'bid', 'ask', 'impliedVolatility', 'volume', 'openInterest']]
                puts_df.columns = ['Strike', 'Last', 'Bid', 'Ask', 'IV', 'Vol', 'OI']
                st.dataframe(puts_df, use_container_width=True)
            else:
                st.info("No Put options available.")
