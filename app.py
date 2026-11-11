import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm
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

if "selected_stock" not in st.session_state:
    st.session_state.selected_stock = None

# --- 辅助计算函数：Black-Scholes Gamma ---
def get_bs_gamma(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return norm.pdf(d1) / (S * sigma * np.sqrt(T))

# --- 期权 GEX 分析核心函数 ---
@st.cache_data(ttl=600)
def fetch_gex_and_chain(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    history = ticker.history(period="1d")
    if history.empty:
        return None, None, None, None, None, None, None, None
        
    spot_price = history['Close'].iloc[-1]
    expirations = ticker.options
    if not expirations:
        return spot_price, None, None, None, None, None, None, None
        
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
        return spot_price, None, None, None, None, None, nearest_exp, opt_chain
        
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
    
    return spot_price, call_wall, put_wall, gamma_flip, gex_by_strike, gex_by_strike['gex'].sum(), nearest_exp, opt_chain

# ==========================================
# 视图一：CAPITAL QUANT v2 — Market Watch 看板
# ==========================================
if st.session_state.selected_stock is None:
    c_title, c_live = st.columns([6, 2])
    with c_title:
        st.markdown("### 📊 CAPITAL QUANT v2 &nbsp; | &nbsp; **Market Watch**")
    with c_live:
        st.markdown("🟢 **Live Terminal** &nbsp; | &nbsp; ⚡ Ready")
        
    st.markdown("---")
    
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
            st.cache_data.clear()
            st.rerun()

    st.markdown("#### 📌 Portfolio & Watchlist Matrix")
    
    table_data = []
    gainers_count = 0
    losers_count = 0
    
    for symbol in st.session_state.watchlist:
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="1y")
            if not hist.empty:
                curr = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2] if len(hist) > 1 else curr
                change = curr - prev
                pct = (change / prev) * 100
                
                ma20 = hist['Close'].rolling(20).mean().iloc[-1] if len(hist) >= 20 else curr
                ma50 = hist['Close'].rolling(50).mean().iloc[-1] if len(hist) >= 50 else curr
                ma200 = hist['Close'].rolling(200).mean().iloc[-1] if len(hist) >= 200 else curr
                
                high_52w = hist['High'].max()
                low_52w = hist['Low'].min()
                
                delta_series = hist['Close'].diff()
                gain = (delta_series.where(delta_series > 0, 0)).rolling(14).mean().iloc[-1]
                loss = (-delta_series.where(delta_series < 0, 0)).rolling(14).mean().iloc[-1]
                rs = gain / loss if loss != 0 else 1
                rsi = 100 - (100 / (1 + rs))
                
                info = t.info
                pe = info.get('trailingPE', 'None')
                pe_str = f"{pe:.2f}" if isinstance(pe, (int, float)) else "None"
                
                if pct >= 0:
                    gainers_count += 1
                else:
                    losers_count += 1
                    
                table_data.append({
                    "Symbol": symbol,
                    "Today Price": f"${curr:.2f}",
                    "Yesterday": f"${prev:.2f}",
                    "Change": f"{change:+.2f}",
                    "Change %": f"{pct:+.2f}%",
                    "MA20": f"${ma20:.2f}",
                    "MA50": f"${ma50:.2f}",
                    "MA200": f"${ma200:.2f}",
                    "PE Rate": pe_str,
                    "Yearly High": f"${high_52w:.2f}",
                    "Yearly Low": f"${low_52w:.2f}",
                    "RSI (14)": f"{rsi:.1f}",
                    "raw_pct": pct
                })
        except:
            continue
            
    if table_data:
        df_display = pd.DataFrame(table_data)
        
        for idx, row in df_display.iterrows():
            c_sym, c_p, c_y, c_chg, c_pct, c_ma20, c_ma50, c_high, c_low, c_rsi, c_act = st.columns([1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1, 1])
            
            with c_sym:
                if st.button(f"🚀 {row['Symbol']}", key=f"nav_{row['Symbol']}"):
                    st.session_state.selected_stock = row['Symbol']
                    st.rerun()
            with c_p:
                st.write(row['Today Price'])
            with c_y:
                st.write(row['Yesterday'])
            with c_chg:
                color_txt = "🟢" if row['raw_pct'] >= 0 else "🔴"
                st.write(f"{color_txt} {row['Change']}")
            with c_pct:
                st.write(row['Change %'])
            with c_ma20:
                st.write(row['MA20'])
            with c_ma50:
                st.write(row['MA50'])
            with c_high:
                st.write(row['Yearly High'])
            with c_low:
                st.write(row['Yearly Low'])
            with c_rsi:
                rsi_val = float(row['RSI (14)'])
                badge_color = "green" if rsi_val < 70 else "red"
                st.markdown(f":{badge_color}[**{row['RSI (14)']}**]")
            with c_act:
                if st.button("🗑️", key=f"del_{row['Symbol']}"):
                    st.session_state.watchlist.remove(row['Symbol'])
                    st.rerun()
        
        st.markdown("---")
        s1, s2, s3 = st.columns(3)
        s1.success(f"🟢 Gainers: {gainers_count}")
        s2.error(f"🔴 Losers: {losers_count}")
        s3.info(f"📊 Total Symbols: {len(st.session_state.watchlist)}")

# ==========================================
# 视图二：个股专属分析面板（包含 GEX 墙与期权链明细）
# ==========================================
else:
    symbol = st.session_state.selected_stock
    
    if st.button("⬅ Return to Market Watch"):
        st.session_state.selected_stock = None
        st.rerun()
        
    st.title(f"🎯 {symbol} — Professional Options GEX & Chain Terminal")
    
    with st.spinner(f"Computing Options Microstructure & Chains for {symbol}..."):
        spot, c_wall, p_wall, g_flip, df_gex, net_gex, nearest_exp, opt_chain = fetch_gex_and_chain(symbol)
        
    if spot is None:
        st.error(f"Failed to fetch market data for {symbol}.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Spot Price", f"${spot:.2f}")
        m2.metric("Call Wall (Resistance)", f"${c_wall}" if c_wall else "N/A")
        m3.metric("Put Wall (Support)", f"${p_wall}" if p_wall else "N/A")
        m4.metric("Gamma Flip Line", f"${g_flip:.2f}" if g_flip else "N/A")
        
        st.markdown("---")
        
        tab_gex, tab_chain = st.tabs(["📊 Gamma & Walls Analysis", f"📋 Options Chain Details ({nearest_exp})"])
        
        with tab_gex:
            net_mil = net_gex / 1e6 if net_gex else 0
            st.markdown(f"### 💡 Market Regime Diagnosis: `{net_mil:+.2f} M$ / 1% Move`")
            if net_mil > 0:
                st.success("【Positive Gamma Regime】：Dealers trade mean-reversion. Low volatility and range-bound defensive structure.")
            else:
                st.warning("【Negative Gamma Regime】：Dealers chase momentum. High volatility breakout or acceleration risk.")
                
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
