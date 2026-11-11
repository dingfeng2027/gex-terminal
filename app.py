import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm
import matplotlib.pyplot as plt

# 1. 页面基本配置
st.set_page_config(
    page_title="Market Watch & GEX Terminal",
    page_icon="📈",
    layout="wide"
)

# 2. 初始化自选股列表
if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["NVDA", "AMD", "AMZN", "TSLA", "GOOGL"]

if "selected_stock" not in st.session_state:
    st.session_state.selected_stock = None

def get_bs_gamma(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return norm.pdf(d1) / (S * sigma * np.sqrt(T))

@st.cache_data(ttl=600)
def fetch_gex_data(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    history = ticker.history(period="1d")
    if history.empty:
        return None, None, None, None, None, None
        
    spot_price = history['Close'].iloc[-1]
    expirations = ticker.options
    if not expirations:
        return spot_price, None, None, None, None, None
        
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
        return spot_price, None, None, None, None, None
        
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
    
    return spot_price, call_wall, put_wall, gamma_flip, gex_by_strike, gex_by_strike['gex'].sum()

# --- 视图一：Market Watch 看板 ---
if st.session_state.selected_stock is None:
    st.title("📊 Market Watch & Options Radar")
    st.markdown("点击下方任意个股名称，进入该资产的专属期权对冲与 Gamma 深度看板。")
    
    st.sidebar.header("⚙️ 自选股管理")
    new_ticker = st.sidebar.text_input("添加新股票代码 (例如: AAPL, MSFT)").upper()
    if st.sidebar.button("➕ 添加到 Watchlist"):
        if new_ticker and new_ticker not in st.session_state.watchlist:
            st.session_state.watchlist.append(new_ticker)
            st.success(f"已成功添加 {new_ticker}")
            st.rerun()
            
    if st.sidebar.button("🗑️ 重置默认自选股"):
        st.session_state.watchlist = ["NVDA", "AMD", "AMZN", "TSLA", "GOOGL"]
        st.rerun()

    st.markdown("---")
    st.subheader("📌 我的自选股列表")
    
    cols = st.columns(3)
    for idx, symbol in enumerate(st.session_state.watchlist):
        with cols[idx % 3]:
            with st.container(border=True):
                st.markdown(f"### 🚀 {symbol}")
                try:
                    t_obj = yf.Ticker(symbol)
                    hist = t_obj.history(period="2d")
                    if not hist.empty:
                        curr_p = hist['Close'].iloc[-1]
                        prev_p = hist['Close'].iloc[-2]
                        chg = ((curr_p - prev_p) / prev_p) * 100
                        st.metric(label="当前价格", value=f"${curr_p:.2f}", delta=f"{chg:+.2f}%")
                    else:
                        st.write("数据加载中...")
                except:
                    st.write("无法获取实时行情")
                
                if st.button(f"进入 {symbol} 专属面板 ➔", key=f"btn_{symbol}"):
                    st.session_state.selected_stock = symbol
                    st.rerun()

# --- 视图二：个股专属分析面板 ---
else:
    symbol = st.session_state.selected_stock
    
    if st.button("⬅ 返回 Market Watch 看板"):
        st.session_state.selected_stock = None
        st.rerun()
        
    st.title(f"🎯 {symbol} — 专属期权对冲与力场分析面板")
    
    with st.spinner(f"正在深度计算 {symbol} 的期权 Gamma 结构，请稍候..."):
        spot, c_wall, p_wall, g_flip, df_gex, net_gex = fetch_gex_data(symbol)
        
    if spot is None:
        st.error(f"未能成功获取 {symbol} 的行情数据。")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("当前正股价格 (Spot)", f"${spot:.2f}")
        m2.metric("上方最大阻力 (Call Wall)", f"${c_wall}" if c_wall else "暂无")
        m3.metric("下方最大支撑 (Put Wall)", f"${p_wall}" if p_wall else "暂无")
        m4.metric("变盘转折线 (Gamma Flip)", f"${g_flip:.2f}" if g_flip else "暂无")
        
        st.markdown("---")
        net_mil = net_gex / 1e6 if net_gex else 0
        st.markdown(f"### 💡 做市商对冲体制诊断：`{net_mil:+.2f} M$ / 1% 波动`")
        if net_mil > 0:
            st.success("【正 Gamma 体制】：做市商高抛低吸，震荡防守，下跌有强支撑。")
        else:
            st.warning("【负 Gamma 体制】：做市商追涨杀跌，波动放大，谨防加速。")
            
        if df_gex is not None and not df_gex.empty:
            st.markdown("### 📊 Dealer Gamma 暴露分布直方图 (GEX Profile)")
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
